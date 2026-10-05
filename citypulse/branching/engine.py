"""Minimal snapshot branching engine (Twin side only).

Scoring replays (event-aware assimilation, docs/oct6-event-pilot-plan.md "Scoring"): a second,
independent entry point, ``score_replays``, replays one snapshot once per hypothesis and returns the
Twin detector intervals over [t_on, t_end], the vehicle count and a vehicle-state digest. It follows
the same conventions as ``_worker`` (state file, control state, stream pointer/m/base factor) but
shares no code path with it: ``run_branches`` is unchanged.

Same Twin snapshot -> one OS process per candidate action -> rollout -> KPIs at checkpoints.
Each branch: new SUMO process with --load-state (in-process loadState was rejected by the snapshot
tests), then re-apply what the state file does not keep (snapshot tests): lane closures/speeds and the capacity
hypothesis. Vehicles waiting for insertion ARE kept by the state (they reappear after the first step). Demand continues from the
Twin's own candidate stream (same seed in every branch = common random numbers), with the assimilated
multiplier `m` and the Twin base factor restored from the snapshot meta. The Proxy is never
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

from citypulse.sim import get_control, get_twin_compliance

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
    stream = TwinDemandStream(seed=meta["demand_seed"], path=meta.get("demand_path"),
                              base_factor=meta.get("twin_base_factor") or 1.0)
    stream.m = dict(meta.get("m") or {})   # assimilated multipliers travel with the snapshot
    stream.seek(t0)
    control = get_control()
    default_compliance = get_twin_compliance()
    compliance = job.get("compliance") if job.get("compliance") is not None else default_compliance
    act = ActionExecutor(control, compliance, cs)
    if job["action"] != "A0":
        act.apply(tc, job["action"])
    t_setup = time.time() - t_wall0

    tl0 = {v: tc.vehicle.getTimeLoss(v) for v in tc.vehicle.getIDList()}
    last_tl = dict(tl0)
    corr = set(control["corridor_b"]) | {control["vms_target_edge"]}
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
    inc_edge = hyp["edge"] if hyp else control["vms_target_edge"]
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
                 compliance=None):
    if compliance is None:
        compliance = get_twin_compliance()
    jobs = [{"state": str(state), "meta": str(meta), "action": a, "horizons": list(horizons),
             "hypothesis": hypothesis, "seed": seed, "compliance": compliance} for a in actions]
    t = time.time()
    if workers == 1:
        res = [_worker(j) for j in jobs]
    else:
        with mp.get_context("spawn").Pool(workers or len(jobs)) as pool:
            res = pool.map(_worker, jobs)
    return res, time.time() - t


# ------------------------------------------------------------------ scoring replays (event pilot)
SCORE_VCLASSES = ("passenger", "bus", "truck", "trailer", "delivery")


def _apply_spec_at(tc, cs, stream, spec):
    """Apply one event-pilot hypothesis to a running replay (incident or demand family).

    Incident, R_E (default): lanes 0..k-1 of the edge are disallowed and the remaining lanes' max speed
    is scaled by ``speed_factor`` (the state file keeps neither, so both are recorded in the control
    state).
    Incident, R_P (``spec["representation"] == "R_P"``, the oct10-replay-diagnosis representation): one
    stopped blocker vehicle per closed lane at ``pos`` -- the audit's H_G5 point blockage
    (``citypulse/branching/audit_engine.py`` ``_twin_audit_worker``: a vehicle inserted at pos - 1 and
    stopped at pos) -- and no lane is disallowed. The remaining lanes' max speed is scaled as in R_E.
    Demand: the entry's multiplier is set to the hypothesis level ``factor`` (an absolute demand level,
    the spec's "write the MAP f into m"), not a factor on the Twin's current estimate.
    """
    if not spec:
        return
    kind = spec.get("kind", "none")
    if kind == "incident":
        edge = spec["edge"]
        closed = list(spec.get("lanes_closed") or [])
        if spec.get("representation", "R_E") == "R_P":
            _place_blockers(tc, edge, closed, float(spec["pos"]))
        else:
            for ln in closed:
                lane = f"{edge}_{ln}"
                tc.lane.setDisallowed(lane, list(SCORE_VCLASSES))
                cs.lane_disallow[lane] = list(SCORE_VCLASSES)
        s = float(spec.get("speed_factor", 1.0))
        n = int(spec.get("n_lanes") or 0)
        if s != 1.0 and n > 0:
            for ln in range(n):
                if ln in closed:
                    continue
                lane = f"{edge}_{ln}"
                v0 = tc.lane.getMaxSpeed(lane)
                tc.lane.setMaxSpeed(lane, v0 * s)
                cs.lane_maxspeed[lane] = v0 * s
    elif kind == "demand":
        # the hypothesis is an absolute demand level f (the spec's "write the MAP f into m"), not a
        # factor on the Twin's current estimate
        stream.m[spec["entry"]] = float(spec["factor"])


def _place_blockers(tc, edge, lanes, pos):
    """R_P: one Twin-owned stopped vehicle per closed lane at ``pos`` (point blockage, no lane closure).

    The blocker is added with ``departPos = pos - 1`` and ``departSpeed = 0`` and stopped at ``pos``,
    exactly as the audit's H_G5 does; SUMO inserts it at the first step at which that position is free.
    """
    if "hyp_route" not in tc.route.getIDList():
        tc.route.add("hyp_route", [edge])
    for ln in lanes:
        vid = f"hyp_blocker_{ln}"
        if vid in tc.vehicle.getIDList():
            continue
        tc.vehicle.add(vid, "hyp_route", typeID="t_car", departLane=str(ln),
                       departPos=str(pos - 1), departSpeed="0")
        tc.vehicle.setStop(vid, edge, pos=pos, laneIndex=ln, duration=3600.0)
        tc.vehicle.setLaneChangeMode(vid, 0)


def _lift_spec_at(tc, cs, spec):
    """Remove a previously applied incident restriction (clearance replay)."""
    if not spec:
        return
    edge = spec.get("edge")
    for ln in spec.get("lanes_closed") or []:
        lane = f"{edge}_{ln}"
        tc.lane.setDisallowed(lane, [])
        cs.lane_disallow.pop(lane, None)
    for lane, v0 in (spec.get("base_speed") or {}).items():
        tc.lane.setMaxSpeed(lane, float(v0))
        cs.lane_maxspeed.pop(lane, None)


def restriction_present(tc, spec):
    """True when every lane the incident spec closes is disallowed in the live/replayed Twin."""
    if not spec or spec.get("kind") != "incident":
        return False
    for ln in spec.get("lanes_closed") or []:
        if not tc.lane.getDisallowed(f"{spec['edge']}_{ln}"):
            return False
    return True


def veh_digest(tc):
    """sha256 of the vehicle state at the current time (check 7: live Twin == replay endpoint)."""
    import hashlib
    lines = [f"t={tc.simulation.getTime():.1f}"]
    for v in tc.vehicle.getIDList():
        lines.append(f"{v}|{tc.vehicle.getLaneID(v)}|{tc.vehicle.getLanePosition(v):.3f}|"
                     f"{tc.vehicle.getSpeed(v):.3f}")
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(), len(tc.vehicle.getIDList())


def _score_worker(job):
    """One hypothesis in its own SUMO process: load the snapshot, restore, replay [t_on, t_end].

    ``t_on`` is when the hypothesis is applied; ``collect_from`` (default ``t_on``, so the default is
    unchanged) is the first instant whose detector intervals are kept -- the scoring window start. The
    two are separate so a hypothesis's intervention onset can differ from interval collection.
    """
    import libsumo as tc  # one libsumo instance per process
    from citypulse.control.actions import ActionExecutor
    from citypulse.sim import ControlState, twin_cmd, detector_loops, read_detectors
    from citypulse.twin.demand_stream import TwinDemandStream

    t_wall0 = time.time()
    meta = json.load(open(job["meta"]))
    tc.start(twin_cmd(job["seed"], ["--load-state", job["state"]]))
    try:
        t0 = tc.simulation.getTime()
        cs = ControlState.from_dict(meta["control_state"])
        cs.apply(tc)
        stream = TwinDemandStream(seed=meta["demand_seed"], path=meta.get("demand_path"),
                                  base_factor=meta.get("twin_base_factor") or 1.0)
        stream.m = dict(meta.get("m") or {})
        if meta.get("stream_ptr") is not None:
            stream.ptr = int(meta["stream_ptr"])
        else:
            stream.seek(t0)
        compliance = job.get("compliance")
        if compliance is None:
            compliance = get_twin_compliance()
        act = ActionExecutor(get_control(), compliance, cs)
        loops = detector_loops()
        dets = list(job.get("detectors") or [])
        t_on, t_end = float(job["t_on"]), float(job["t_end"])
        collect_from = float(job["collect_from"]) if job.get("collect_from") is not None else t_on
        t_lift = job.get("t_lift")
        apply_spec, lift_spec = job.get("apply"), job.get("lift")
        want_blockers = bool(apply_spec and apply_spec.get("kind") == "incident"
                             and apply_spec.get("representation", "R_E") == "R_P")
        applied = lifted = False
        if apply_spec is not None and t_on <= t0 + 1e-9:
            _apply_spec_at(tc, cs, stream, apply_spec)
            applied = True
        if lift_spec is not None and t_lift is not None and t_lift <= t0 + 1e-9:
            _lift_spec_at(tc, cs, lift_spec)
            lifted = True
        t_setup = time.time() - t_wall0
        intervals = {d: {} for d in dets}
        blockers = {}
        while tc.simulation.getTime() < t_end - 1e-9:
            t_next = tc.simulation.getTime() + 1
            if not applied and apply_spec is not None and t_next > t_on:
                _apply_spec_at(tc, cs, stream, apply_spec)
                applied = True
            if not lifted and lift_spec is not None and t_lift is not None and t_next > t_lift:
                _lift_spec_at(tc, cs, lift_spec)
                lifted = True
            stream.insert_due(tc, t_next)
            tc.simulationStep()
            act.step(tc)
            t = tc.simulation.getTime()
            if want_blockers:
                # record the actual R_P placement: edge, lane, position and the step it stopped
                for ln in apply_spec.get("lanes_closed") or []:
                    vid = f"hyp_blocker_{ln}"
                    if (vid not in blockers and vid in tc.vehicle.getIDList()
                            and tc.vehicle.isStopped(vid)):
                        blockers[vid] = {"edge": tc.vehicle.getRoadID(vid),
                                         "lane": int(tc.vehicle.getLaneIndex(vid)),
                                         "pos": float(tc.vehicle.getLanePosition(vid)),
                                         "t_stopped": float(t)}
            if t > collect_from + 1e-9 and abs(t - round(t / 30.0) * 30.0) < 1e-6:
                own = read_detectors(tc, loops)
                for d in dets:
                    row = own.get(d)
                    if row is not None:
                        intervals[d][float(t)] = {"q": row["q"], "v": row["v"], "o": row["o"]}
        digest, n_veh = veh_digest(tc)
        if want_blockers:
            # the blocker must still be stopped at the requested point at the end of the replay
            for vid, b in blockers.items():
                if vid in tc.vehicle.getIDList():
                    b["pos_at_end"] = float(tc.vehicle.getLanePosition(vid))
                    b["lane_at_end"] = int(tc.vehicle.getLaneIndex(vid))
                    b["stopped_at_end"] = bool(tc.vehicle.isStopped(vid))
                else:
                    b["pos_at_end"] = None
                    b["lane_at_end"] = None
                    b["stopped_at_end"] = False
        return {"tag": job.get("tag"), "t_snap": float(t0), "t_on": t_on, "t_end": float(t_end),
                "collect_from": collect_from, "intervals": intervals, "n_vehicles": n_veh,
                "veh_digest": digest, "blockers": blockers,
                "restriction_present": restriction_present(tc, apply_spec),
                "applied": applied, "lifted": lifted, "setup_s": t_setup,
                "wall_s": time.time() - t_wall0}
    finally:
        try:
            tc.close()
        except Exception:
            pass


def score_replays(state, meta, jobs, workers=8, seed=2, compliance=None):
    """Replay one snapshot once per job in parallel subprocesses (<= workers, default 8).

    Every job is ``{tag, t_on, t_end, detectors, apply, lift, t_lift}``; ``apply`` is applied at
    ``t_on`` and ``lift`` at ``t_lift`` (both optional). ``collect_from`` (optional, default ``t_on``)
    is the first instant whose detector intervals are kept, so a hypothesis's intervention onset can
    differ from the scoring window start. Returns ``(results, wall_s)`` with one result per job, in job
    order.
    """
    full = []
    for j in jobs:
        job = dict(j)
        job["state"] = str(state)
        job["meta"] = str(meta)
        job.setdefault("seed", seed)
        if compliance is not None:
            job["compliance"] = compliance
        full.append(job)
    if not full:
        return [], 0.0
    t0 = time.time()
    n = max(1, min(int(workers or 1), len(full)))
    if n == 1:
        res = [_score_worker(j) for j in full]
    else:
        with mp.get_context("spawn").Pool(n) as pool:
            res = pool.map(_score_worker, full)
    return res, time.time() - t0
