"""Pilot-2 mechanics checks that need real replays: checks 2, 4 and 7 on the actual 755 m hypothesis.

Inputs are one pilot-2 INC EVT run's own artefacts: the episode snapshot the service pinned
(``event_snapshot_<t_on - 60>.xml.gz``), its ``event_log.jsonl`` (t_on and the first evaluation
time) and its ``twin_log.parquet`` (the observations the Proxy actually sent -- the same offline
substitution the pilot-1 check script used). Nothing is read from Proxy truth.

* **check 2 (direct)** -- the same hypothesis scored twice, in two independent SUMO processes, from
  the same snapshot at the same t: identical logL over the identical support, identical interval
  tables, identical vehicle digest.
* **check 4 (direct)** -- under the incident hypothesis the lanes are disallowed in the replay and
  the downstream flow (AID02111, downstream of ktb_n1) drops relative to the no-event replay.
* **check 7 (live + direct)** -- a live replacement with an incident hypothesis at ``ktb_n1`` 755 m:
  the replay endpoint's vehicle digest and count are compared with a live Twin that loaded the same
  snapshot, restored the control state / stream pointer / m and replayed to the same t_end with the
  same spec, and the lane disallow is read from the live process. The forced-adoption runs' own
  in-run replacement rows (``replacement_log.jsonl``) are copied in beside it: that is the live
  adoption path itself.

Usage: python results/event_pilot2/impl/check_replays.py [--run results/event_pilot2/runs/evt_inc_4101]
Writes: results/event_pilot2/evidence/check2_deterministic_replay.json
        results/event_pilot2/evidence/check4_capacity_restriction.json
        results/event_pilot2/evidence/check7_755.json
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.branching.engine import (  # noqa: E402
    _apply_spec_at,
    restriction_present,
    score_replays,
    veh_digest,
)
from citypulse.twin import event as ev  # noqa: E402

EVIDENCE = REPO / "results/event_pilot2/evidence"
SIGMA_JSON = REPO / "results/event_pilot/impl/sigma_event.json"
HYP = "inc_ktb_n1_k2_s1"        # ktb_n1, lanes 0-1 closed, speed factor 1.0, pos 755.0 m
DOWNSTREAM = ev.PAIR_D          # AID02111


def obs_from_twin_log(path):
    df = pd.read_parquet(path)
    hist = {}
    for row in df.itertuples():
        hist.setdefault(row.detector, {})[float(row.t)] = {
            "detector": row.detector, "q": None if pd.isna(row.obs_q) else row.obs_q,
            "v": None if pd.isna(row.obs_v) else row.obs_v,
            "o": None if pd.isna(row.obs_o) else row.obs_o, "valid": bool(row.obs_valid)}
    return hist


def anchor_from(obs_hist, t_on):
    anchor = {}
    for det, rows in obs_hist.items():
        vals = {}
        for t in sorted(rows, reverse=True):
            if t >= t_on:
                continue
            r = rows[t]
            if not r["valid"]:
                continue
            for x in ev.CHANNELS:
                if x not in vals and r[x] is not None:
                    vals[x] = r[x]
        anchor[det] = vals
    return anchor


def episode(run_dir):
    """(t_on, t_first_eval, snapshot state, snapshot meta) from the run's own event log."""
    rows = [json.loads(l) for l in (run_dir / "twin/event_log.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    first = next(r for r in rows if r.get("t_on") is not None)
    t_on, t_end = float(first["t_on"]), float(first["t"])
    snap_t = t_on - ev.DELTA_S
    st = run_dir / f"twin/event_snapshot_{int(snap_t)}.xml.gz"
    mt = run_dir / f"twin/event_snapshot_{int(snap_t)}.json"
    if not st.exists():                      # fall back to whatever the service pinned
        cands = sorted(run_dir.glob("twin/event_snapshot_*.xml.gz"))
        if not cands:
            raise FileNotFoundError(f"no episode snapshot in {run_dir}")
        st = cands[0]
        mt = st.with_suffix("").with_suffix(".json")
    return t_on, t_end, st, mt


def spec_of(hyp):
    p = dict(hyp.params)
    return {"kind": "incident", "edge": p["edge"], "lanes_closed": list(p["lanes_closed"]),
            "n_lanes": int(p["n_lanes"]), "speed_factor": float(p["speed_factor"]),
            "pos": p.get("pos")}


def job(tag, t_on, t_end, apply_spec, dets):
    return {"tag": tag, "t_on": t_on, "t_end": t_end, "detectors": dets, "apply": apply_spec,
            "lift": None, "t_lift": None}


def live_replacement(state, meta, t_on, t_end, spec, seed):
    """EventRuntime.replace_live's steps, verbatim, on a fresh traci connection (this process)."""
    import traci
    from citypulse.control.actions import ActionExecutor
    from citypulse.sim import ControlState, get_control, get_twin_compliance, twin_cmd
    from citypulse.twin.demand_stream import TwinDemandStream

    m = json.loads(Path(meta).read_text(encoding="utf-8"))
    traci.start(twin_cmd(seed, ["--save-state.rng", "--load-state", str(state)]), label="check7")
    tc = traci.getConnection("check7")
    cs = ControlState.from_dict(m["control_state"])
    cs.apply(tc)
    stream = TwinDemandStream(seed=m["demand_seed"], path=m.get("demand_path"),
                              base_factor=m.get("twin_base_factor") or 1.0)
    stream.m = dict(m.get("m") or {})
    if m.get("stream_ptr") is not None:
        stream.ptr = int(m["stream_ptr"])
    else:
        stream.seek(tc.simulation.getTime())
    act = ActionExecutor(get_control(), get_twin_compliance(), cs)
    t0 = tc.simulation.getTime()
    applied = False
    if t_on <= t0 + 1e-9:
        _apply_spec_at(tc, cs, stream, spec)
        applied = True
    while tc.simulation.getTime() < t_end - 1e-9:
        t_next = tc.simulation.getTime() + 1
        if not applied and t_next > t_on:
            _apply_spec_at(tc, cs, stream, spec)
            applied = True
        stream.insert_due(tc, t_next)
        tc.simulationStep()
        act.step(tc)
    digest, n_veh = veh_digest(tc)
    lanes = {f"{spec['edge']}_{i}": list(tc.lane.getDisallowed(f"{spec['edge']}_{i}"))
             for i in spec["lanes_closed"]}
    open_lanes = {f"{spec['edge']}_{i}": tc.lane.getMaxSpeed(f"{spec['edge']}_{i}")
                  for i in range(int(spec["n_lanes"])) if i not in spec["lanes_closed"]}
    present = restriction_present(tc, spec)
    t_live = tc.simulation.getTime()
    tc.close()
    return {"veh_digest": digest, "n_vehicles": n_veh, "restriction_present_live": present,
            "lane_disallow_live": lanes, "open_lane_maxspeed_live": open_lanes,
            "t_end_live": t_live, "applied": applied}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="results/event_pilot2/runs/evt_inc_4101")
    ap.add_argument("--hypothesis", default=HYP)
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--forced-run", default=None,
                    help="forced-adoption run whose in-run replacement rows are copied in")
    a = ap.parse_args()

    run_dir = REPO / a.run
    t_on, t_end, state, meta = episode(run_dir)
    hyps = ev.build_hypotheses(grid=ev.GRID_PILOT2)
    hyp = ev.find_hypothesis(hyps, a.hypothesis)
    spec = spec_of(hyp)
    obs_hist = obs_from_twin_log(run_dir / "twin/twin_log.parquet")
    anchor = anchor_from(obs_hist, t_on)
    sigma = ev.load_sigma(SIGMA_JSON)
    dets = sorted(obs_hist)
    print(f"run={run_dir.name} t_on={t_on} t_end={t_end} snapshot={state.name} hyp={hyp.id} "
          f"dets={len(dets)}")

    # one replay set serves all three checks: the hypothesis twice and the no-event baseline
    jobs = [job("run1", t_on, t_end, spec, dets), job("run2", t_on, t_end, spec, dets),
            job("noevent", t_on, t_end, {"kind": "none"}, dets)]
    res, wall = score_replays(state, meta, jobs, workers=3, seed=a.seed)
    r1, r2, r0 = res[0], res[1], res[2]

    # --- check 2: two independent scorings of the same hypothesis at the same t
    logls, n_os = [], []
    for r in (r1, r2):
        times = sorted({t for d in dets for t in r["intervals"].get(d, {})})
        ll, n_o = ev.logl_of_one(hyp, dets, times, obs_hist, {hyp.id: r["intervals"]}, sigma,
                                 t_on, t_end, anchor=anchor)
        logls.append(ll)
        n_os.append(n_o)
    check2 = {
        "check": "2", "name": "deterministic_replay", "label": "direct",
        "run": a.run, "snapshot": state.name, "t_on": t_on, "t_end": t_end,
        "hypothesis": hyp.id, "params": dict(hyp.params),
        "logL_run1": logls[0], "logL_run2": logls[1],
        "logL_identical": logls[0] == logls[1],
        "n_O": n_os[0], "n_O_run2": n_os[1],
        "digest_run1": r1["veh_digest"], "digest_run2": r2["veh_digest"],
        "digest_identical": r1["veh_digest"] == r2["veh_digest"],
        "interval_tables_identical": r1["intervals"] == r2["intervals"],
        "n_vehicles": r1["n_vehicles"], "wall_s": wall,
        "note": ("logL of one hypothesis over its own support (no demand family offline): the check is "
                 "that two independent SUMO processes reproduce it exactly, with the observations "
                 "substituted from the run's twin_log.parquet (what the Proxy sent)"),
    }
    check2["passed"] = bool(check2["logL_identical"] and check2["digest_identical"]
                            and check2["interval_tables_identical"] and n_os[0] > 0)

    # --- check 4: the incident replay restricts capacity and drops downstream flow
    def flow(r, det):
        vals = [x["q"] for x in r["intervals"].get(det, {}).values() if x["q"] is not None]
        return (sum(vals) / len(vals)) if vals else None, len(vals)

    inc_q, n_inc = flow(r1, DOWNSTREAM)
    noev_q, n_noev = flow(r0, DOWNSTREAM)
    lanes = [f"{spec['edge']}_{i}" for i in spec["lanes_closed"]]
    check4 = {
        "check": "4", "name": "effective_capacity_restriction", "label": "direct",
        "run": a.run, "snapshot": state.name, "t_on": t_on, "t_end": t_end,
        "hypothesis": hyp.id, "params": dict(hyp.params), "lanes_closed": lanes,
        "restriction_present_replay": bool(r1["restriction_present"]),
        "downstream_detector": DOWNSTREAM,
        "incident_mean_q": inc_q, "noevent_mean_q": noev_q,
        "incident_intervals": n_inc, "noevent_intervals": n_noev,
        "flow_drops": bool(inc_q is not None and noev_q is not None and inc_q < noev_q),
        "drop_pct": None if not noev_q else round(100.0 * (inc_q - noev_q) / noev_q, 2),
        "n_vehicles_incident": r1["n_vehicles"], "n_vehicles_noevent": r0["n_vehicles"],
    }
    check4["passed"] = bool(check4["restriction_present_replay"] and check4["flow_drops"])

    # --- check 7: live replacement at ktb_n1 755 m against the replay endpoint
    live = live_replacement(state, meta, t_on, t_end, spec, a.seed)
    forced_rows = []
    if a.forced_run:
        p = REPO / a.forced_run / "twin/replacement_log.jsonl"
        if p.exists():
            forced_rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
                           if l.strip()]
    check7 = {
        "check": "7", "name": "successful_state_replacement",
        "label": "live (forced-adoption runs, in-run replacement) + direct (mechanics, this script)",
        "hypothesis": hyp.id, "params": dict(hyp.params),
        "location": {"edge": spec["edge"], "pos": spec["pos"], "pos_kind": hyp.params["pos_kind"]},
        "run": a.run, "snapshot": state.name, "snapshot_meta": meta.name, "t_on": t_on, "t_end": t_end,
        "replay_endpoint": {"veh_digest": r1["veh_digest"], "n_vehicles": r1["n_vehicles"],
                            "restriction_present_replay": bool(r1["restriction_present"]),
                            "wall_s": r1["wall_s"]},
        "live_twin": live,
        "vehicles_match": bool(live["veh_digest"] == r1["veh_digest"]
                               and live["n_vehicles"] == r1["n_vehicles"]),
        "lane_disallow_present_live": bool(live["restriction_present_live"]),
        "in_run_replacements": forced_rows,
    }
    check7["passed"] = bool(check7["vehicles_match"] and check7["lane_disallow_present_live"]
                            and live["lane_disallow_live"]
                            and all(v for v in live["lane_disallow_live"].values()))

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name, obj in (("check2_deterministic_replay.json", check2),
                      ("check4_capacity_restriction.json", check4),
                      ("check7_755.json", check7)):
        (EVIDENCE / name).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
        print(f"{name}: passed={obj['passed']}")
    print(json.dumps({"check2": check2["passed"], "check4": check4["passed"],
                      "check7": check7["passed"], "logL": logls, "n_O": n_os,
                      "check7_vehicles_match": check7["vehicles_match"],
                      "check7_lane_disallow_live": live["lane_disallow_live"]}, default=str))
    return 0 if all(c["passed"] for c in (check2, check4, check7)) else 1


if __name__ == "__main__":
    sys.exit(main())
