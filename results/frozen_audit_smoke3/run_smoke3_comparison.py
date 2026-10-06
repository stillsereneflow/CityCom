"""Smoke3 evidence: compare the 6 branch rows with the frozen development audit parquets.

The development audit (seeds 4201-4208) is the reference: ``results/audit/raw.parquet`` carries the
Twin belief-B rows and the shared Proxy rows, ``results/audit/sens/raw_sens.parquet`` the D300
variant rows. Every J and vehicle digest below is read from the parquet files, never retyped.
Writes ``results/frozen_audit_smoke3/smoke3_comparison.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "results" / "frozen_audit_smoke3" / "raw.parquet"
AUDIT = ROOT / "results" / "audit" / "raw.parquet"
SENS = ROOT / "results" / "audit" / "sens" / "raw_sens.parquet"
SEED, REP, ACTIONS = 4201, 1, ["A0", "A3"]


def main() -> int:
    smoke = pd.read_parquet(SMOKE)
    audit = pd.read_parquet(AUDIT)
    sens = pd.read_parquet(SENS)

    def pick(df, world, actions, variant=None):
        sub = df[(df["seed"] == SEED) & (df["replication"] == REP) & (df["action"].isin(actions))]
        sub = sub[sub["world"] == world]
        if variant is not None:
            sub = sub[sub["variant"] == variant]
        return sub

    reference = pd.concat([
        pick(audit, "twin", ACTIONS).assign(label="B"),
        pick(sens, "twin", ACTIONS, variant="D300").assign(label="D300"),
        pick(audit, "proxy", ACTIONS).assign(label="proxy"),
    ], ignore_index=True)

    def key(world, label, action):
        return (world, label, int(SEED), int(REP), action)

    ref = {key(r["world"], r["label"], r["action"]): r for _, r in reference.iterrows()}
    rows, ok_all = [], True
    for _, r in smoke.sort_values(["world", "belief", "action"], na_position="first").iterrows():
        label = "proxy" if r["world"] == "proxy" else str(r["belief"])
        k = key(r["world"], label, r["action"])
        ref_row = ref.get(k)
        if ref_row is None:
            ok_all = False
            rows.append({"key": list(k), "match": False, "reason": "no reference row"})
            continue
        j_match = abs(float(r["J"]) - float(ref_row["J"])) < 1e-9
        d_match = str(r["digest"]) == str(ref_row["veh_digest"])
        ok_all = ok_all and j_match and d_match
        rows.append({
            "world": r["world"], "belief": label, "seed": int(r["seed"]),
            "replication": int(r["replication"]), "action": r["action"],
            "smoke3_J": float(r["J"]), "audit_J": float(ref_row["J"]),
            "smoke3_digest": str(r["digest"]), "audit_digest": str(ref_row["veh_digest"]),
            "J_match": bool(j_match), "digest_match": bool(d_match),
            "status": str(r["status"]),
        })

    report = {
        "smoke3_rows": int(len(smoke)), "reference_rows": int(len(reference)),
        "source": {"B": "results/audit/raw.parquet", "D300": "results/audit/sens/raw_sens.parquet",
                   "proxy": "results/audit/raw.parquet"},
        "seed": SEED, "replication": REP, "actions": ACTIONS,
        "rows": rows, "n_rows": len(rows), "n_matched": sum(1 for r in rows if r.get("match", True)
                                                            and r.get("J_match") and r.get("digest_match")),
        "passed": bool(ok_all and len(rows) == 6),
    }
    (ROOT / "results" / "frozen_audit_smoke3" / "smoke3_comparison.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    for r in rows:
        print(f"{r['world']:5s} {r['belief']:5s} {r['action']}  J {r['smoke3_J']!r} vs {r['audit_J']!r}  "
              f"digest {r['smoke3_digest'][:16]} vs {r['audit_digest'][:16]}  "
              f"J={'ok' if r['J_match'] else 'MISMATCH'} digest={'ok' if r['digest_match'] else 'MISMATCH'}")
    print(f"smoke3 comparison: {report['n_matched']}/{report['n_rows']} rows equal on J and digest; "
          f"passed={report['passed']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
