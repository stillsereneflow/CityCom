"""Check 7 mechanics, verified directly because no pilot run adopted an incident.

None of the three fixed EVT INC runs adopted (``replacement_log.jsonl`` is empty in all three), so
``EventRuntime.replace_live`` never ran in them. This script exercises the same path on the episode
snapshot the service actually pinned for seed 4001's first alarm (S(t_on - delta) = twin_state_4230):

* replay the incident hypothesis from that snapshot to t_end in a subprocess (the replay endpoint);
* load the same snapshot in a live Twin (traci), restore the control state / stream / m, apply the
  same spec, replay to the same t_end, and read the vehicle digest, the vehicle count and the lane
  disallow from the live process;
* compare the live Twin against the replay endpoint (the assertion check 7 makes).

Usage: python results/event_pilot/fix/check7_live_replacement.py
Writes: results/event_pilot/fix/evidence/check7_live_replacement_mechanics.json
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import traci                                                                    # noqa: E402
from citypulse.branching.engine import (_apply_spec_at, restriction_present,    # noqa: E402
                                        score_replays, veh_digest)
from citypulse.control.actions import ActionExecutor                            # noqa: E402
from citypulse.sim import ControlState, get_control, get_twin_compliance, twin_cmd   # noqa: E402
from citypulse.twin.demand_stream import TwinDemandStream                       # noqa: E402

FIX = REPO / "results/event_pilot/fix"
RUN = FIX / "evt_inc_4001/twin"
STATE = RUN / "event_snapshot_4230.xml.gz"
META = RUN / "event_snapshot_4230.json"
T_ON, T_END, SEED = 4290.0, 4890.0, 2
HYP = "inc_ktb_n1_k1_s1"
SPEC = {"kind": "incident", "edge": "ktb_n1", "lanes_closed": [0], "n_lanes": 3,
        "speed_factor": 1.0, "pos": 503.1}


def replay_endpoint():
    """The incident replay of the hypothesis, in subprocesses (libsumo never enters this process)."""
    job = {"tag": HYP, "t_on": T_ON, "t_end": T_END, "detectors": [], "apply": SPEC,
           "lift": None, "t_lift": None}
    res, wall = score_replays(STATE, META, [job, dict(job, tag=HYP + "_dup")], workers=2, seed=SEED)
    return res[0], res[1], wall


def live_replacement():
    """EventRuntime.replace_live's steps, verbatim, on a fresh traci connection."""
    meta = json.loads(META.read_text(encoding="utf-8"))
    traci.start(twin_cmd(SEED, ["--save-state.rng", "--load-state", str(STATE)]), label="livecheck")
    tc = traci.getConnection("livecheck")
    cs = ControlState.from_dict(meta["control_state"])
    cs.apply(tc)
    stream = TwinDemandStream(seed=meta["demand_seed"], path=meta.get("demand_path"),
                              base_factor=meta.get("twin_base_factor") or 1.0)
    stream.m = dict(meta.get("m") or {})
    if meta.get("stream_ptr") is not None:
        stream.ptr = int(meta["stream_ptr"])
    else:
        stream.seek(tc.simulation.getTime())
    act = ActionExecutor(get_control(), get_twin_compliance(), cs)
    t0 = tc.simulation.getTime()
    applied = False
    if T_ON <= t0 + 1e-9:
        _apply_spec_at(tc, cs, stream, SPEC)
        applied = True
    while tc.simulation.getTime() < T_END - 1e-9:
        t_next = tc.simulation.getTime() + 1
        if not applied and t_next > T_ON:
            _apply_spec_at(tc, cs, stream, SPEC)
            applied = True
        stream.insert_due(tc, t_next)
        tc.simulationStep()
        act.step(tc)
    digest, n_veh = veh_digest(tc)
    lanes = {f"{SPEC['edge']}_{i}": list(tc.lane.getDisallowed(f"{SPEC['edge']}_{i}"))
             for i in SPEC["lanes_closed"]}
    present = restriction_present(tc, SPEC)
    tc.close()
    return {"veh_digest": digest, "n_vehicles": n_veh, "restriction_present_live": present,
            "lane_disallow_live": lanes, "t_end_live": T_END, "applied": applied}


def main():
    rep, rep_dup, wall = replay_endpoint()
    live = live_replacement()
    out = {
        "check": "7", "name": "successful_state_replacement",
        "kind": "manual mechanics check: no pilot run adopted, so no adoption exercised this path",
        "run": "results/event_pilot/fix/evt_inc_4001", "snapshot": STATE.name,
        "snapshot_meta": META.name, "hypothesis": HYP, "params": SPEC, "t_on": T_ON, "t_end": T_END,
        "replay_endpoint": {"veh_digest": rep["veh_digest"], "n_vehicles": rep["n_vehicles"],
                            "restriction_present_replay": rep["restriction_present"],
                            "wall_s": rep["wall_s"], "wall_total_s": wall},
        "replay_endpoint_duplicate": {"veh_digest": rep_dup["veh_digest"],
                                      "n_vehicles": rep_dup["n_vehicles"],
                                      "identical_to_first": bool(rep_dup["veh_digest"] == rep["veh_digest"]
                                                                 and rep_dup["n_vehicles"] == rep["n_vehicles"])},
        "live_twin": live,
        "vehicles_match": bool(live["veh_digest"] == rep["veh_digest"]
                               and live["n_vehicles"] == rep["n_vehicles"]),
        "lane_disallow_present_live": bool(live["restriction_present_live"]),
        "passed": bool(live["veh_digest"] == rep["veh_digest"]
                       and live["n_vehicles"] == rep["n_vehicles"]
                       and live["restriction_present_live"]),
    }
    (FIX / "evidence").mkdir(parents=True, exist_ok=True)
    (FIX / "evidence/check7_live_replacement_mechanics.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("passed", "vehicles_match", "lane_disallow_present_live")}))
    print(json.dumps(out["replay_endpoint"]), json.dumps(out["live_twin"]))
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
