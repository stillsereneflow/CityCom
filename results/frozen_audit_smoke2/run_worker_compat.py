"""Pre-collection smoke: re-run frozen development-audit Twin rows with the modified worker.

Twin B rows seed 4203 r5 A2 and seed 4207 r2 A4 (expected in results/audit/raw.parquet), and
D300 rows seed 4201 r1 A0/A3 (expected in results/audit/sens/raw_sens.parquet). J, digest and
every existing output field must stay byte-identical for these valid branches. Writes
results/frozen_audit_smoke2/worker_compat.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from citypulse.branching.audit_engine import (  # noqa: E402
    HORIZON_STEPS, blocker_placement_error, run_twin_branch_jobs)

RAW = ROOT / "results" / "audit" / "raw.parquet"
SENS = ROOT / "results" / "audit" / "sens" / "raw_sens.parquet"
RUNS = ROOT / "results" / "audit" / "runs"
OUT = ROOT / "results" / "frozen_audit_smoke2" / "worker_compat.json"

# (seed, replication, action, variant, hyp_clear_time, expected source)
CASES = [
    (4203, 5, "A2", "B", None, "raw"),
    (4207, 2, "A4", "B", None, "raw"),
    (4201, 1, "A0", "D300", 5400.0, "sens"),
    (4201, 1, "A3", "D300", 5400.0, "sens"),
]
EXISTING_FIELDS = ("world", "seed", "replication", "action", "J", "veh_digest", "n_vehicles", "status",
                   "variant", "hyp_pos", "hyp_clear_time", "branch_factor", "blocker_edge",
                   "blocker_lane_0", "blocker_pos_0", "blocker_t_stop_0", "blocker_lane_1",
                   "blocker_pos_1", "blocker_t_stop_1", "actual_clear_time")


def _num_eq(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) <= 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def expected_rows():
    raw = pd.read_parquet(RAW)
    sens = pd.read_parquet(SENS)
    out = {}
    for seed, r, a, variant, clear, src in CASES:
        if src == "raw":
            sub = raw[(raw["world"] == "twin") & (raw["seed"] == seed)
                      & (raw["replication"] == r) & (raw["action"] == a)]
        else:
            sub = sens[(sens["variant"] == variant) & (sens["seed"] == seed)
                       & (sens["replication"] == r) & (sens["action"] == a)]
        assert len(sub) == 1, (seed, r, a, src, len(sub))
        out[(seed, r, a, variant)] = sub.iloc[0].to_dict()
    return out


def main() -> int:
    exp = expected_rows()
    jobs = []
    for seed, r, a, variant, clear, _src in CASES:
        info = json.loads((RUNS / f"seed_{seed}" / "two_world_info.json").read_text(encoding="utf-8"))
        jobs.append({"state": info["twin_state"], "meta": info["twin_meta"], "seed": seed, "r": r,
                     "action": a, "horizon": HORIZON_STEPS, "variant": variant,
                     "hyp_pos": 755.3, "hyp_clear_time": clear, "branch_factor": None})

    results = run_twin_branch_jobs(jobs, workers=4)
    checks = []
    all_ok = True
    for res in results:
        key = (int(res["seed"]), int(res["replication"]), str(res["action"]), str(res["variant"]))
        row = exp[key]
        per = {"case": {"seed": key[0], "replication": key[1], "action": key[2], "variant": key[3]},
               "worker_pid": res.get("worker_pid"), "status": res.get("status"),
               "fields": {}, "ok": True}
        for f in EXISTING_FIELDS:
            if f not in row or pd.isna(row[f]):
                continue
            got, want = res.get(f), row[f]
            ok = (_num_eq(got, want) if f not in ("veh_digest", "status", "world", "variant")
                  else str(got) == str(want))
            per["fields"][f] = {"got": got, "expected": want, "ok": bool(ok)}
            per["ok"] = per["ok"] and bool(ok)
        # the measured placement itself must satisfy the placement rule and release evidence
        stops = {}
        for ln in (0, 1):
            stops[f"hyp_blocker_{ln}"] = {"edge": res.get(f"blocker_edge"),
                                          "lane": res.get(f"blocker_lane_{ln}"),
                                          "pos": res.get(f"blocker_pos_{ln}"),
                                          "time_stopped": res.get(f"blocker_t_stop_{ln}")}
        per["placement_error"] = blocker_placement_error(stops, 755.3)
        per["ok"] = per["ok"] and per["placement_error"] is None
        if res["variant"] == "D300":
            rel = [res.get("blocker_release_0"), res.get("blocker_release_1")]
            per["release_records"] = rel
            per["ok"] = per["ok"] and all(
                isinstance(e, dict) and e.get("resumed") is True and e.get("resumed_at") == 5400.0
                and e.get("released") is True and e.get("checked_at") == 5401.0 for e in rel)
        checks.append(per)
        all_ok = all_ok and per["ok"]

    report = {"source": {"B": "results/audit/raw.parquet", "D300": "results/audit/sens/raw_sens.parquet"},
              "worker": "citypulse/branching/audit_engine.py _twin_audit_worker (modified)",
              "fresh_process_per_branch": len({c["worker_pid"] for c in checks}) == len(checks),
              "n_cases": len(checks), "n_passed": sum(1 for c in checks if c["ok"]),
              "all_ok": bool(all_ok), "cases": checks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for c in checks:
        bad = [f for f, v in c["fields"].items() if not v["ok"]]
        print(f"{c['case']} ok={c['ok']} placement={c['placement_error']} mismatched={bad}")
    print(f"worker_compat: {report['n_passed']}/{report['n_cases']} passed -> {OUT}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
