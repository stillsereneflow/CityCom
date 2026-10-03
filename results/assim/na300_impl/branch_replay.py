"""Branch replay from a Twin snapshot: vehicle-id comparison with the online Twin.

Runs the production branch engine (``citypulse.branching.engine.run_branches``, ``workers=1`` so the
recorder below is in effect) from a snapshot of an NA-300 run, with assimilation frozen: the branch
never assimilates, it takes ``m`` and the Twin base factor from the snapshot meta and continues the
candidate stream from ``stream_ptr`` (``seek(t0)``). The recorder wraps
``TwinDemandStream.insert_due``: it calls the original method unchanged and reconstructs the ids it
inserted from the same acceptance rule, so the recorded ids are the branch's own.

Then compares, for the window (t_snap, t_snap + horizon]:
  * the branch's inserted vehicle ids with the online Twin's (``twin_inserts.json``, written by
    online_logged.py, same acceptance recorder);
  * the branch's end-of-window insertion backlog with the online snapshot meta's ``pending`` length.

Usage: python branch_replay.py --run assim/na300_impl/replay4001_logged --t-snap 1800 --horizon 300
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.branching import engine  # noqa: E402
from citypulse.twin.demand_stream import TwinDemandStream  # noqa: E402

_orig_insert_due = TwinDemandStream.insert_due
INSERTS = []


def _recording_insert_due(self, tc, t, vtype="tdist"):
    ptr0 = self.ptr
    n = _orig_insert_due(self, tc, t, vtype)
    for i in range(ptr0, self.ptr):
        _dep, vid, edges = self.cands[i]
        if self.u[i] < self.acceptance(edges[0]):
            INSERTS.append({"t": float(t), "vid": vid, "entry": edges[0]})
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="online run dir relative to results/")
    ap.add_argument("--t-snap", type=float, default=1800.0)
    ap.add_argument("--horizon", type=int, default=300)
    ap.add_argument("--out", default=None, help="JSON report path (default <run>/branch_replay.json)")
    ap.add_argument("--override-m", type=float, default=None,
                    help="falsification only: replace meta m with this value (e.g. the pre-fix stale m)")
    ap.add_argument("--override-factor", type=float, default=None,
                    help="falsification only: replace the meta's Twin base factor")
    a = ap.parse_args()

    run = REPO / "results" / a.run
    twin = run / "twin"
    state = twin / f"twin_state_{int(a.t_snap)}.xml.gz"
    meta_path = twin / f"twin_state_{int(a.t_snap)}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if a.override_m is not None or a.override_factor is not None:
        if a.override_m is not None:
            meta["m"] = {"tko_insert": a.override_m}
        if a.override_factor is not None:
            meta["twin_base_factor"] = a.override_factor
        meta_path = twin / f"twin_state_{int(a.t_snap)}_override.json"
        meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    online = json.loads((twin / "twin_inserts.json").read_text(encoding="utf-8"))

    TwinDemandStream.insert_due = _recording_insert_due
    res, wall = engine.run_branches(state, meta_path, ["A0"], horizons=(a.horizon,), seed=2, workers=1)
    kpi = res[0]["kpis"][a.horizon]

    lo, hi = a.t_snap, a.t_snap + a.horizon
    online_ids = [r["vid"] for r in online if lo < r["t"] <= hi]
    branch_ids = [r["vid"] for r in INSERTS]

    meta_end = twin / f"twin_state_{int(hi)}.json"
    pending_online = None
    if meta_end.exists():
        pending_online = len(json.loads(meta_end.read_text(encoding="utf-8")).get("pending") or [])

    report = {
        "run": a.run, "t_snap": a.t_snap, "horizon": a.horizon, "wall_s": round(wall, 1),
        "meta_m": meta.get("m"), "meta_twin_base_factor": meta.get("twin_base_factor"),
        "override_m": a.override_m, "override_factor": a.override_factor,
        "n_online": len(online_ids), "n_branch": len(branch_ids),
        "ids_equal": online_ids == branch_ids,
        "sets_equal": set(online_ids) == set(branch_ids),
        "only_online": sorted(set(online_ids) - set(branch_ids))[:20],
        "only_branch": sorted(set(branch_ids) - set(online_ids))[:20],
        "branch_kpis": kpi, "branch_pending_after_first_step": res[0]["pending_after_first_step"],
        "meta_pending_at_snap": len(meta.get("pending") or []),
        "online_pending_at_window_end": pending_online,
        "branch_backlog_end": kpi.get("backlog_end"),
        "pending_match": (pending_online == kpi.get("backlog_end")) if pending_online is not None else None,
    }
    out = Path(a.out) if a.out else (run / "branch_replay.json")
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
