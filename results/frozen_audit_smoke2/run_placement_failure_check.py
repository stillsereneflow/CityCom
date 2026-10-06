"""Pre-collection smoke: the measured-placement gate of _twin_audit_worker (Codex item 5).

Two checks, no frozen seed touched:
1. ``blocker_placement_error`` on each failure kind (missing blocker, wrong edge, wrong lane,
   position out of tolerance, non-finite position) and on a valid pair;
2. one real SUMO branch (seed 4203 r5 A2) run with ``horizon=1``, i.e. ended before either
   blocker was observed stopped: the worker must return status ``blockers_not_placed`` with no
   J/digest instead of a successful row.
Writes results/frozen_audit_smoke2/placement_failure_check.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from citypulse.branching.audit_engine import (  # noqa: E402
    blocker_placement_error, run_twin_branch_jobs)

OUT = ROOT / "results" / "frozen_audit_smoke2" / "placement_failure_check.json"
HYP = 755.3


def stop(edge="ktb_n1", lane=0, pos=755.282, t=5104.0):
    return {"edge": edge, "lane": lane, "pos": pos, "time_stopped": t}


def main() -> int:
    good = {"hyp_blocker_0": stop(lane=0, pos=755.282), "hyp_blocker_1": stop(lane=1, pos=755.29)}
    helper_cases = [
        ("valid pair", good, None),
        ("blocker 0 never stopped", {"hyp_blocker_1": stop(lane=1)}, "never stopped"),
        ("blocker 1 never stopped", {"hyp_blocker_0": stop(lane=0)}, "never stopped"),
        ("blocker 0 wrong edge", {**good, "hyp_blocker_0": stop(edge="ktb_w1")}, "not ktb_n1"),
        ("blocker 1 wrong lane", {**good, "hyp_blocker_1": stop(lane=0)}, "not 1"),
        ("blocker 0 out of tolerance", {**good, "hyp_blocker_0": stop(pos=750.0)}, "not within 1 m"),
        ("blocker 1 no position", {**good, "hyp_blocker_1": stop(lane=1, pos=None)}, "no measured position"),
    ]
    helper = []
    ok = True
    for label, stops, needle in helper_cases:
        err = blocker_placement_error(stops, HYP)
        passed = (err is None) if needle is None else (err is not None and needle in err)
        helper.append({"case": label, "error": err, "ok": bool(passed)})
        ok = ok and passed

    info = json.loads((ROOT / "results" / "audit" / "runs" / "seed_4203"
                       / "two_world_info.json").read_text(encoding="utf-8"))
    job = {"state": info["twin_state"], "meta": info["twin_meta"], "seed": 4203, "r": 5, "action": "A2",
           "horizon": 1, "variant": "B", "hyp_pos": HYP, "hyp_clear_time": None, "branch_factor": None}
    res = run_twin_branch_jobs([job], workers=1)[0]
    branch_ok = (res.get("status") == "blockers_not_placed" and res.get("J") is None
                 and res.get("veh_digest") is None and res.get("reason") == "blockers_not_placed")
    ok = ok and branch_ok

    report = {"helper_cases": helper, "helper_all_ok": all(c["ok"] for c in helper),
              "short_horizon_branch": {"job": {"seed": 4203, "replication": 5, "action": "A2",
                                               "horizon": 1},
                                       "status": res.get("status"), "J": res.get("J"),
                                       "veh_digest": res.get("veh_digest"), "error": res.get("error"),
                                       "ok": bool(branch_ok)},
              "all_ok": bool(ok)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for c in helper:
        print(f"helper {c['case']}: ok={c['ok']} error={c['error']}")
    print(f"short-horizon branch: status={res.get('status')} J={res.get('J')} error={res.get('error')}")
    print(f"placement_failure_check: all_ok={ok} -> {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
