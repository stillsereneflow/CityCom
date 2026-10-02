"""Minimal snapshot branching engine (Twin side only).

Same Twin snapshot -> one OS process per candidate action -> rollout -> KPIs at checkpoints.
Each branch: new SUMO process with --load-state (in-process loadState was rejected by the snapshot
tests), then re-apply what the state file does not keep (snapshot tests): lane closures/speeds and the capacity
hypothesis. Vehicles waiting for insertion ARE kept by the state (they reappear after the first step). Demand continues from the
Twin's own candidate stream (same seed in every branch = common random numbers). The Proxy is never
touched: this module must not import citypulse.proxy (tests/test_firewall.py).

KPI definitions (all over [t_snap, t_snap + h]):
  delay_vh    total vehicle delay in veh*h = sum of SUMO timeLoss gained by every vehicle in the
              network during the window (last value sampled every SAMPLE s; arrivals use their last
              sample, so each arrival can be under-counted by < SAMPLE s) + insertion-backlog waiting
  arrived     vehicles that finished their trip
  backlog_end vehicles waiting for insertion at the end of the window
  halt_inc    mean number of halting vehicles on the hypothesised incident edge
  corridor_delay_vh  timeLoss gained only by vehicles whose route uses the VMS target corridor edge or any
              corridor-B edge (the population an incident response can affect); excludes the entry
              backlog, which in the D1–D4 network dominates delay_vh and is unrelated to the incident

Hypothesis modes (Twin-side capacity-loss representation, supplied by the caller):
  "disallow": lanes closed over the whole edge (lane.setDisallowed)
  "blocker":  Twin-owned stopped vehicles at a point (vehicle.setStop), like a physical blockage
"""
import json
import multiprocessing as mp
import time
from pathlib import Path

from citypulse.scenario import CONTROL, TWIN_ASSUMED_COMPLIANCE

SAMPLE = 10


def _worker(job):
    import libsumo as tc  # one libsumo instance per process
    from citypulse.control.actions import ActionExecutor
    from citypulse.sim import ControlState, twin_cmd
    from citypulse.twin.demand_stream import TwinDemandStream

    t_wall0 = time.time()
    meta = json.load(open(job["meta"]))
    cmd = twin_cmd(job["seed"], ["--load-state", job["state"]])
    tc.start(cmd)
    t0 = tc.simulation.getTime()
    cs = ControlState.from_dict(meta["control_state"])
    cs.apply(tc)
    hyp = job.get("hypothesis")
    if hyp and hyp.get("mode", "disallow") == "disallow":
        for ln in hyp["lanes_closed"]:
            lane = f"{hyp['edge']}_{ln}"
            tc.lane.setDisallowed(lane, ["passenger", "bus", "truck", "trailer", "delivery"])
            cs.lane_disallow[lane] = ["passenger", "bus", "truck", "trailer", "delivery"]
    elif hyp and hyp["mode"] == "blocker":
        tc.route.add("hyp_route", [hyp["edge"]])
        for ln in hyp["lanes_closed"]:
            vid = f"hyp_blocker_{ln}"
            tc.vehicle.add(vid, "hyp_route", typeID="t_car", departLane=str(ln), departPos=str(hyp["pos"] - 1),
                           departSpeed="0")
            tc.vehicle.setStop(vid, hyp["edge"], pos=hyp["pos"], laneIndex=ln, duration=hyp.get("duration", 3600))
            tc.vehicle.setLaneChangeMode(vid, 0)
    stream = TwinDemandStream(seed=meta["demand_seed"])
    stream.seek(t0)
    act = ActionExecutor(CONTROL, job.get("compliance", TWIN_ASSUMED_COMPLIANCE), cs)
    if job["action"] != "A0":
        act.apply(tc, job["action"])
    t_setup = time.time() - t_wall0

    tl0 = {v: tc.vehicle.getTimeLoss(v) for v in tc.vehicle.getIDList()}
    last_tl = dict(tl0)
    corr = set(CONTROL["corridor_b"]) | {CONTROL["vms_target_edge"]}
    affected = {}   # vid -> bool, decided once from the route

    def is_affected(v):
        if v not in affected:
            affected[v] = (not v.startswith("hyp_")) and bool(corr.intersection(tc.vehicle.getRoute(v)))
        return affected[v]

    for v in tl0:
        is_affected(v)
    arrived, backlog_s, halt_sum, halt_n = 0, 0.0, 0, 0
    checkpoints = sorted(job["horizons"])
    kpis = {}
    horizon = checkpoints[-1]
    inc_edge = hyp["edge"] if hyp else CONTROL["vms_target_edge"]
    pending_after_first = None
    for k in range(1, horizon + 1):
        stream.insert_due(tc, t0 + k)
        tc.simulationStep()
        if k == 1:
            pending_after_first = len(tc.simulation.getPendingVehicles())
        act.step(tc)
        arrived += tc.simulation.getArrivedNumber()
        backlog_s += len(tc.simulation.getPendingVehicles())
        if k % SAMPLE == 0:
            for v in tc.vehicle.getIDList():
                last_tl[v] = tc.vehicle.getTimeLoss(v)
                is_affected(v)
            halt_sum += tc.edge.getLastStepHaltingNumber(inc_edge)
            halt_n += 1
        if k in checkpoints:
            delay_s = sum(last_tl.values()) - sum(tl0.values()) + backlog_s
            corr_s = sum(last_tl[v] - tl0.get(v, 0.0) for v in last_tl if affected.get(v))
            kpis[k] = {"delay_vh": delay_s / 3600.0, "corridor_delay_vh": corr_s / 3600.0,
                       "n_affected": sum(affected.values()), "arrived": arrived,
                       "backlog_end": len(tc.simulation.getPendingVehicles()),
                       "halt_inc": halt_sum / max(halt_n, 1), "running": tc.vehicle.getIDCount()}
    tc.close()
    return {"action": job["action"], "kpis": kpis, "t_snap": t0, "pending_after_first_step": pending_after_first,
            "n_pending_meta": len(meta["pending"]), "n_diverted": act.n_diverted,
            "wall_s": time.time() - t_wall0, "setup_s": t_setup}


def run_branches(state, meta, actions, horizons=(300, 600, 900), hypothesis=None, seed=2, workers=None,
                 compliance=TWIN_ASSUMED_COMPLIANCE):
    jobs = [{"state": str(state), "meta": str(meta), "action": a, "horizons": list(horizons),
             "hypothesis": hypothesis, "seed": seed, "compliance": compliance} for a in actions]
    t = time.time()
    if workers == 1:
        res = [_worker(j) for j in jobs]
    else:
        with mp.get_context("spawn").Pool(workers or len(jobs)) as pool:
            res = pool.map(_worker, jobs)
    return res, time.time() - t
