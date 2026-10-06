"""Pre-collection smoke: re-run the analyzer self-test on the development seeds.

Input: results/frozen_audit_smoke/analyzer_selftest/ (raw.parquet built from results/audit/raw.parquet
belief B plus the D300 rows of results/audit/sens/raw_sens.parquet, state_history.parquet,
rng_check.json), copied unchanged into results/frozen_audit_smoke2/analyzer_selftest/ and analyzed
with the self-test override --seeds 4201..4208.

The sensitivity parquet carries no blocker release records, so the D300 release rule is applied
honestly: no release evidence is invented, D300 fails validation, and that is reported here.
Writes results/frozen_audit_smoke2/analyzer_selftest/selftest_comparison.json.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from citypulse.experiments.frozen_audit_analyze import analyze, parse_seeds  # noqa: E402

SRC = ROOT / "results" / "frozen_audit_smoke" / "analyzer_selftest"
DST = ROOT / "results" / "frozen_audit_smoke2" / "analyzer_selftest"

# Expected B numbers of results/audit/v2/report.md and results/audit/report.md (unchanged).
B_CHECKS = [
    ("BEE_signed (B)", ("pooled", "BEE_signed", "mean"), 1.6315393518518597, 0.005),
    ("BEE_signed t-CI low (B)", ("pooled", "BEE_signed", "ci95_t", 0), 1.0412214256936843, 0.005),
    ("BEE_signed t-CI high (B)", ("pooled", "BEE_signed", "ci95_t", 1), 2.2218572780100354, 0.005),
    ("BEE_abs (B)", ("pooled", "BEE_abs", "mean"), 1.6315393518518597, 0.005),
    ("floor abs (B)", ("pooled", "BEE_floor_abs", "mean"), 0.1807986111111166, 0.005),
    ("Regret (B)", ("pooled", "Regret", "mean"), 0.0289930555555582, 0.005),
    ("Spearman (B)", ("pooled", "spearman_rho", "mean"), 0.8499999999999999, 0.0005),
    ("Kendall (B)", ("pooled", "kendall_tau", "mean"), 0.75, 0.0005),
    ("CRN proxy median corr (B)", ("crn", "pooled_medians", "proxy", "pooled_median_corr"),
     0.9927414097913742, 0.0005),
    ("CRN twin median corr (B)", ("crn", "pooled_medians", "twin", "pooled_median_corr"),
     0.902741385807958, 0.0005),
]


def dig(bundle, path):
    node = bundle
    for key in path:
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list):
            node = node[key]
        else:
            return None
    return node


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    for name in ("raw.parquet", "state_history.parquet", "rng_check.json"):
        shutil.copy2(SRC / name, DST / name)

    bundle = analyze(DST, seeds=parse_seeds("4201..4208"))
    primary, secondary = bundle["primary"], bundle["secondary"]
    checks = []
    ok_all = True
    for label, path, expected, tol in B_CHECKS:
        got = dig(bundle, ("primary",) + path) if path[0] != "crn" else dig(bundle["crn"]["B"], path[1:])
        ok = got is not None and abs(float(got) - float(expected)) <= tol
        checks.append({"check": label, "ok": bool(ok), "got": got, "expected": expected, "tol": tol})
        ok_all = ok_all and ok

    a_star = [r["a_star"] for r in primary["per_seed"]]
    top1 = [r["top1_agree"] for r in primary["per_seed"]]
    extra = [
        {"check": "primary complete seeds = 8 (B)", "ok": primary["n_complete_seeds"] == 8,
         "got": primary["n_complete_seeds"], "expected": 8},
        {"check": "a* = A3 on all 8 seeds (B)", "ok": a_star == ["A3"] * 8, "got": a_star,
         "expected": "A3 x8"},
        {"check": "oracle agreement 7/8 (B)", "ok": sum(top1) == 7.0, "got": sum(top1), "expected": 7},
    ]
    for c in extra:
        c["tol"] = 0
        checks.append(c)
        ok_all = ok_all and c["ok"]

    d300_excl = secondary["validation"]["twin"][0]
    d300_reasons = sorted({r["reason"] for r in d300_excl.values()})
    d300_state = {
        "secondary_complete_seeds": secondary["n_complete_seeds"],
        "twin_world_reasons": d300_reasons,
        "statement": ("The self-test D300 rows come from results/audit/sens/raw_sens.parquet, which has "
                      "no blocker release records. The D300 rule (both blockers resumed at 5,400 s and "
                      "verified released at 5,401 s) is applied as written: no release evidence is "
                      "invented, so D300 fails validation for all 8 seeds and no D300 estimand is "
                      "computed on this input. The positive D300 path is covered by the unit tests and "
                      "by results/frozen_audit_smoke2/worker_compat.json, whose fresh D300 branches "
                      "carry the required release records."),
    }
    d300_fails = (secondary["n_complete_seeds"] == 0
                  and all("clearance evidence" in r for r in d300_reasons)
                  and all("release" in r for r in d300_reasons))
    ok_all = ok_all and d300_fails
    checks.append({"check": "D300 fails validation: no release records in the sensitivity input",
                   "ok": bool(d300_fails), "got": d300_reasons, "expected": "technical failure: "
                   "clearance evidence (release records missing)", "tol": 0})

    report = {"source": {"B": "results/audit/raw.parquet (belief B) + results/audit/v2/report.md",
                         "D300": "results/audit/sens/raw_sens.parquet variant D300 + results/audit/sens/report.md"},
              "input": str(DST.relative_to(ROOT)), "seeds": bundle["seeds"],
              "seed_source": bundle["seed_source"], "n_seeds": bundle["n_seeds"],
              "primary_complete_seeds": primary["n_complete_seeds"],
              "secondary_complete_seeds": secondary["n_complete_seeds"],
              "d300": d300_state,
              "n_checks": len(checks), "n_passed": sum(1 for c in checks if c["ok"]),
              "passed": bool(ok_all), "checks": checks}
    (DST / "selftest_comparison.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for c in checks:
        print(f"{c['check']}: ok={c['ok']} got={c['got']}")
    print(f"analyzer_selftest: {report['n_passed']}/{report['n_checks']} checks passed, "
          f"primary complete {primary['n_complete_seeds']}, secondary complete {secondary['n_complete_seeds']}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
