"""sigma for the amended boundary detector AID07106, by the frozen rule of the Oct 5 plan amendment.

Pools the valid paired 30-s flow residuals in veh/h, r = (obs_q - twin_q) * 120, for detector
AID07106, t in [900, 7200] s, from the OL development runs seeds 1001-1003 ONLY (the three run
directories are hard-coded; no evaluation-seed output is opened). No occupancy selection.

sigma = 1.4826 * median(|r - median(r)|).

Writes results/assim/eval_amend/sigma_dev_AID07106.json = {"AID07106": sigma} and
results/assim/eval_amend/sigma_report.md.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "results" / "assim" / "eval"
OUT = REPO / "results" / "assim" / "eval_amend"

DET = "AID07106"
T0, T1 = 900.0, 7200.0
SEEDS = (1001, 1002, 1003)
LOG = {s: EVAL / f"ol_{s}" / "twin" / "twin_log.parquet" for s in SEEDS}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def classify(df: pd.DataFrame) -> dict:
    """One pass over the run: window timestamps, AID07106 presence, and every exclusion reason."""
    ts = np.sort(df["t"].unique())
    ts = ts[(ts >= T0) & (ts <= T1)]
    x = df[(df["detector"] == DET) & (df["t"] >= T0) & (df["t"] <= T1)]
    reasons = {"missing_row_in_sensormsg": 0, "obs_invalid": 0, "obs_q_null": 0, "twin_q_null": 0}
    res = []
    for t, row in zip(x["t"].to_numpy(), x.to_dict("records")):
        if not bool(row["obs_valid"]):
            reasons["obs_invalid"] += 1
            continue
        if pd.isna(row["obs_q"]):
            reasons["obs_q_null"] += 1
            continue
        if pd.isna(row["twin_q"]):
            reasons["twin_q_null"] += 1
            continue
        res.append((float(row["obs_q"]) - float(row["twin_q"])) * 120.0)
    n_window = int(len(ts))
    n_rows = int(len(x))
    reasons["missing_row_in_sensormsg"] = n_window - n_rows
    return {"n_window": n_window, "n_rows": n_rows, "reasons": reasons,
            "n_valid": len(res), "residuals": res}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    per_seed, pooled = {}, []
    for s in SEEDS:
        p = LOG[s]
        assert p.parent.parent.name == f"ol_{s}" and s in (1001, 1002, 1003), p  # dev seeds only
        c = classify(pd.read_parquet(p))
        r = np.array(c.pop("residuals"), dtype=float)
        pooled.extend(r.tolist())
        med = float(np.median(r)) if len(r) else None
        mad = float(np.median(np.abs(r - med))) if len(r) else None
        per_seed[s] = {**c, "median": med, "mad": mad,
                       "sigma": (1.4826 * mad) if mad is not None else None,
                       "sha256": sha256(p)}

    arr = np.array(pooled, dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    sigma = 1.4826 * mad

    (OUT / "sigma_dev_AID07106.json").write_text(json.dumps({DET: sigma}, indent=1) + "\n",
                                                 encoding="utf-8")

    lines = []
    lines.append("# sigma for the amended boundary detector AID07106")
    lines.append("")
    lines.append("Frozen rule (`docs/oct5-normal-assim-plan.md`, Amendment 2026-10-03 20:15): pool the valid")
    lines.append("paired 30-s flow residuals in veh/h, `r = (obs_q - twin_q) * 120`, for detector AID07106,")
    lines.append(f"t in [{T0:.0f}, {T1:.0f}] s, from the OL development runs seeds 1001-1003 only; no occupancy")
    lines.append("selection; `sigma = 1.4826 * median(|r - median(r)|)`.")
    lines.append("")
    lines.append(f"**sigma(AID07106) = {sigma:.6f} veh/h**  (median = {med:.1f} veh/h, MAD = {mad:.1f} veh/h,")
    lines.append(f"pooled n = {len(arr)} residuals)")
    lines.append("")
    lines.append("## Counts per seed")
    lines.append("")
    lines.append("| Seed | window timestamps | AID07106 rows present | valid residuals | excluded: missing row | obs invalid | obs q null | twin q null | median (veh/h) | MAD (veh/h) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for s in SEEDS:
        d = per_seed[s]
        e = d["reasons"]
        lines.append(f"| {s} | {d['n_window']} | {d['n_rows']} | {d['n_valid']} | {e['missing_row_in_sensormsg']} | "
                     f"{e['obs_invalid']} | {e['obs_q_null']} | {e['twin_q_null']} | {d['median']:.1f} | {d['mad']:.1f} |")
    tot = {k: sum(per_seed[s]["reasons"][k] for s in SEEDS) for k in per_seed[SEEDS[0]]["reasons"]}
    lines.append(f"| **all** | **{sum(per_seed[s]['n_window'] for s in SEEDS)}** | "
                 f"**{sum(per_seed[s]['n_rows'] for s in SEEDS)}** | **{len(arr)}** | "
                 f"**{tot['missing_row_in_sensormsg']}** | **{tot['obs_invalid']}** | **{tot['obs_q_null']}** | "
                 f"**{tot['twin_q_null']}** | **{med:.1f}** | **{mad:.1f}** |")
    lines.append("")
    lines.append("Exclusion reasons, in the order they are applied:")
    lines.append("")
    lines.append("- **missing row**: the timestamp is in the window but `twin_log.parquet` has no AID07106 row at")
    lines.append("  all, i.e. the detector was not in that `SensorMsg` (outside the fixed observed set, or the")
    lines.append("  message never arrived).")
    lines.append("- **obs invalid**: the row exists but `obs_valid` is false (the sensor emulator's 5% loss).")
    lines.append("- **obs q null** / **twin q null**: the row is flagged valid (or is the Twin's own reading) but the")
    lines.append("  flow value is absent, so no residual can be formed.")
    lines.append("")
    lines.append("No occupancy-based selection was applied: occupancy plays no part in this estimate.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append("| Run | twin_log.parquet sha256 |")
    lines.append("|---|---|")
    for s in SEEDS:
        lines.append(f"| `results/assim/eval/ol_{s}` | `{per_seed[s]['sha256']}` |")
    lines.append("")
    lines.append("Only these three development runs were read; no evaluation-seed (3001-3004) output was opened.")
    lines.append("")
    lines.append("Note: these OL development runs were produced by `citypulse/experiments/normal_assim_eval.py`,")
    lines.append("whose as-predeclared launcher adds AID07105 to the Proxy's observed set. That patch changes the")
    lines.append("sensor RNG stream, but AID07106's own `twin_q` comes from the Twin's simulation (m = 1, no")
    lines.append("observation is consumed), so the paired residuals used here are the residuals of the runs the")
    lines.append("amendment names.")
    lines.append("")
    lines.append("SIGMA DONE")
    (OUT / "sigma_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"sigma": sigma, "median": med, "mad": mad, "n": len(arr),
                      "per_seed": {str(s): per_seed[s]["n_valid"] for s in SEEDS}}))


if __name__ == "__main__":
    main()
