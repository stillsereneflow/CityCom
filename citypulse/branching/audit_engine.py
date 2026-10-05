"""Preregistered offline decision audit branching engine.

Provides branch workers for Twin branches, Proxy branches, and calibration branches,
as specified in Part A of docs/oct6-audit-and-pilot2-plan.md.
Each branch runs in an independent OS process loaded from a snapshot without RNG state.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os

# Binding environment variables (prompt.md line 3)
os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from pathlib import Path
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from citypulse.sim import (
    ControlState,
    get_control,
    get_twin_compliance,
    proxy_cmd,
    twin_cmd,
)
from citypulse.control.actions import ActionExecutor
from citypulse.twin.demand_stream import TwinDemandStream

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
HORIZON_STEPS = 900
T_D = 5100.0

# Missing-queue experiment (docs/oct11-missing-queue-plan.md rev 2): frozen edge lists and queue trace.
QUEUE_EDGES_FILE = Path(__file__).resolve().parents[2] / "results" / "missing_queue" / "upstream_edges.json"
BLOCKER_ID_PREFIXES = ("hyp_", "incident_")   # hyp_blocker_* (Twin) / incident_* (Proxy) are blockers, not queue
_QUEUE_EDGES_CACHE: Dict[str, Any] = {}

# Fixed per-route rates in synth5 (decision 2026-10-03b / 2026-10-03c)
ROUTE_SPECS = [
    {
        "key": "tko_in_bypass->out",
        "flow_vph": 2100.0,
        "edges": "tko_insert tko_in tko_1 tko_vms ktb_w1 ms_on_ktb_w2 ktb_w2 ktb_w3 ktb_n1 dv_off_ktb_n1 ktb_n2 rejoin out",
        "depart_lane": "free",
        "depart_speed": "max",
    },
    {
        "key": "tko_in_arterial->out",
        "flow_vph": 700.0,
        "edges": "tko_insert tko_in tko_1 tko_vms tko_a1 ms_on_ktr_w1 ktr_w1 ktr_w2 ktr_w3 ktr_w4 ktr_w5 ktr_w6 rejoin out",
        "depart_lane": "free",
        "depart_speed": "max",
    },
    {
        "key": "x1_in->x1_out",
        "flow_vph": 400.0,
        "edges": "x1_in x1_out",
        "depart_lane": "best",
        "depart_speed": "max",
    },
    {
        "key": "x2_in->x2_out",
        "flow_vph": 400.0,
        "edges": "x2_in x2_out",
        "depart_lane": "best",
        "depart_speed": "max",
    },
    {
        "key": "x3_in->x3_out",
        "flow_vph": 400.0,
        "edges": "x3_in x3_out",
        "depart_lane": "best",
        "depart_speed": "max",
    },
    {
        "key": "x4_in->x4_out",
        "flow_vph": 400.0,
        "edges": "x4_in x4_out",
        "depart_lane": "best",
        "depart_speed": "max",
    },
]


def D_T_seed(seed: int, r: int) -> int:
    """Twin future demand seed: D_T(r) = 900000 + 1000 * seed + r."""
    return 900000 + 1000 * int(seed) + int(r)


def D_P_seed(seed: int, m: int) -> int:
    """Proxy future demand seed: D_P(m) = 800000 + 1000 * seed + m."""
    return 800000 + 1000 * int(seed) + int(m)


def veh_digest(tc) -> Tuple[str, int]:
    """sha256 digest of running vehicles' state (id, lane, position, speed)."""
    import hashlib
    lines = [f"t={tc.simulation.getTime():.1f}"]
    ids = sorted(tc.vehicle.getIDList())
    for v in ids:
        lines.append(
            f"{v}|{tc.vehicle.getLaneID(v)}|{tc.vehicle.getLanePosition(v):.3f}|"
            f"{tc.vehicle.getSpeed(v):.3f}"
        )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(), len(ids)


def strip_rng_state_from_xml(xml_path: Path) -> bool:
    """Ensure state XML has no <rngState> elements. Return True if modified."""
    import gzip
    import re

    raw = xml_path.read_bytes()
    is_gz = raw[:2] == b"\x1f\x8b"
    if is_gz:
        content = gzip.decompress(raw).decode("utf-8")
    else:
        content = raw.decode("utf-8")

    if "<rngState" not in content:
        return False

    cleaned = re.sub(r"<rngState.*?</rngState>\s*", "", content, flags=re.DOTALL)
    if is_gz:
        xml_path.write_bytes(gzip.compress(cleaned.encode("utf-8")))
    else:
        xml_path.write_text(cleaned, encoding="utf-8")
    return True


def strip_future_departures_from_proxy_snapshot(xml_path: Path, t_d: float = T_D) -> int:
    """Remove any vehicle and route with depart > t_d from proxy state file."""
    import gzip

    with gzip.open(xml_path, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()

    parent_map = {c: p for p in root.iter() for c in p}
    future_routes = set()
    removed = 0
    for v in list(root.findall(".//vehicle")):
        if float(v.get("depart", 0.0)) > t_d:
            r_id = v.get("route")
            if r_id:
                future_routes.add(r_id)
            p = parent_map.get(v)
            if p is not None:
                p.remove(v)
                removed += 1
    for r in list(root.findall(".//route")):
        if r.get("id") in future_routes:
            p = parent_map.get(r)
            if p is not None:
                p.remove(r)

    with gzip.open(xml_path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)
    return removed


def build_proxy_resampled_routes(
    base_routes_path: Path,
    out_path: Path,
    seed: int,
    m: int,
    t_d: float = T_D,
    horizon: float = HORIZON_STEPS,
) -> Tuple[Set[str], int]:
    """Create resampled Proxy future departures for t in [t_d, t_d + horizon].

    Removes all departures scheduled after t_d from the base route file and inserts
    a re-sampled stream from the same per-route rates with seed D_P(m).
    Asserts that no original future departure remains.
    Returns (orig_future_ids, num_resampled_vehicles).
    """
    base_tree = ET.parse(base_routes_path)
    base_root = base_tree.getroot()

    orig_future_ids: Set[str] = set()
    for v in base_root.iter("vehicle"):
        dep = float(v.get("depart", 0.0))
        if dep > t_d:
            orig_future_ids.add(v.get("id"))

    # Sample future departures
    d_seed = D_P_seed(seed, m)
    rng = np.random.default_rng(d_seed)

    vehicles: List[Tuple[float, str, str, str, str]] = []
    v_idx = 0
    for spec in ROUTE_SPECS:
        vph = spec["flow_vph"]
        expected_n = vph * (horizon / 3600.0)
        n_veh = int(rng.poisson(expected_n))
        if n_veh > 0:
            departs = rng.uniform(t_d, t_d + horizon, n_veh)
            for dep in departs:
                vid = f"resamp_{m}_{v_idx}"
                v_idx += 1
                vehicles.append(
                    (float(dep), vid, spec["edges"], spec["depart_lane"], spec["depart_speed"])
                )

    vehicles.sort(key=lambda x: x[0])

    # Build new routes XML with ONLY resampled vehicles for t > t_d
    root = ET.Element("routes")
    for dep, vid, edges, dlane, dspeed in vehicles:
        v = ET.SubElement(
            root,
            "vehicle",
            id=vid,
            depart=f"{dep:.3f}",
            type="pdist",
            departLane=dlane,
            departSpeed=dspeed,
        )
        ET.SubElement(v, "route", edges=edges)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)

    # Verification assertion
    written_ids = {v.get("id") for v in root.iter("vehicle")}
    overlap = written_ids & orig_future_ids
    assert len(overlap) == 0, f"Original future departures leaked into routes: {overlap}"

    return orig_future_ids, len(vehicles)


def resolve_twin_job_overrides(job: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract and validate Twin branch overrides with baseline defaults preserved."""
    hyp_pos = float(job.get("hyp_pos", 755.3)) if job.get("hyp_pos") is not None else 755.3
    hyp_clear_time = float(job["hyp_clear_time"]) if job.get("hyp_clear_time") is not None else None
    meta = meta or {}
    job_factor = job.get("branch_factor")
    if job_factor is not None:
        branch_factor = float(job_factor)
    else:
        branch_factor = float(meta.get("twin_base_factor") or 0.85)
    return {
        "hyp_pos": hyp_pos,
        "hyp_clear_time": hyp_clear_time,
        "branch_factor": branch_factor,
    }


def load_queue_edges(path: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load the three frozen edge lists of results/missing_queue/upstream_edges.json."""
    key = str(path or QUEUE_EDGES_FILE)
    if key not in _QUEUE_EDGES_CACHE:
        with open(key, encoding="utf-8") as fh:
            data = json.load(fh)
        _QUEUE_EDGES_CACHE[key] = {
            "Q_edges": list(data["Q_edges"]),
            "upstream_spillback_edges": list(data["upstream_spillback_edges"]),
            "descriptive_extra_edges": list(data["descriptive_extra_edges"]),
        }
    return _QUEUE_EDGES_CACHE[key]


def queue_snapshot(tc, t: float, edges: Optional[Dict[str, List[str]]] = None,
                   pending: Optional[List[str]] = None) -> Dict[str, Any]:
    """Queue counts at time t for the missing-queue plan (rev 2, Measurements).

    Ordinary halted = speed < 0.1 m/s and id not a blocker (``hyp_blocker_*`` in the Twin,
    ``incident_*`` in the Proxy); counted per edge of the three frozen lists.
    ``pending`` is the pending-vehicle list, or None when ``getPendingVehicles()`` cannot be
    trusted (right after a loadState it returns 0); pending vehicles count when their route
    traverses a Q edge. Q = halted on Q_edges + pending on a Q edge.
    """
    edges = edges or load_queue_edges()
    halted: Dict[str, Dict[str, int]] = {"q": {}, "upstream": {}, "extra": {}}
    blocker_halted = 0
    for vid in tc.vehicle.getIDList():
        try:
            if tc.vehicle.getSpeed(vid) >= 0.1:
                continue
            eid = tc.vehicle.getRoadID(vid)
        except Exception:
            continue
        if vid.startswith(BLOCKER_ID_PREFIXES):
            blocker_halted += 1
            continue
        for key, edge_list in (("q", edges["Q_edges"]),
                               ("upstream", edges["upstream_spillback_edges"]),
                               ("extra", edges["descriptive_extra_edges"])):
            if eid in edge_list:
                halted[key][eid] = halted[key].get(eid, 0) + 1

    pending_q_ids: Optional[List[str]] = None
    pending_total: Optional[int] = None
    if pending is not None:
        pending_total = len(pending)
        q_set = set(edges["Q_edges"])
        pending_q_ids = []
        for vid in pending:
            try:
                if q_set.intersection(tc.vehicle.getRoute(vid)):
                    pending_q_ids.append(str(vid))
            except Exception:
                continue

    n_q = sum(halted["q"].values())
    return {
        "t": float(t),
        "halted_q": n_q,
        "halted_upstream": sum(halted["upstream"].values()),
        "halted_extra": sum(halted["extra"].values()),
        "halted_q_by_edge": halted["q"],
        "halted_upstream_by_edge": halted["upstream"],
        "halted_extra_by_edge": halted["extra"],
        "blocker_halted": blocker_halted,
        "pending_total": pending_total,
        "pending_q": None if pending_q_ids is None else len(pending_q_ids),
        "pending_q_ids": pending_q_ids,
        "Q": n_q + (0 if pending_q_ids is None else len(pending_q_ids)),
    }


def reused_blocker_error(tc, hyp_pos: float) -> Optional[str]:
    """Check the H state's blockers after loading (reuse_blockers=True); None if reusable."""
    for ln in (0, 1):
        vid = f"hyp_blocker_{ln}"
        try:
            if vid not in tc.vehicle.getIDList():
                return f"{vid} missing from the loaded state"
            road = tc.vehicle.getRoadID(vid)
            if road != "ktb_n1":
                return f"{vid} is on {road!r}, not ktb_n1"
            lane = int(tc.vehicle.getLaneIndex(vid))
            if lane != ln:
                return f"{vid} is on lane {lane}, not {ln}"
            pos = float(tc.vehicle.getLanePosition(vid))
            if abs(pos - float(hyp_pos)) > 1.0:
                return f"{vid} is at {pos:.3f} m, not within 1 m of {hyp_pos}"
            if not tc.vehicle.isStopped(vid):
                return f"{vid} is not stopped"
        except Exception as exc:
            return f"{vid} check failed: {type(exc).__name__}: {exc}"
    return None


def _twin_audit_worker(job: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one Twin audit branch in a new process."""
    import libsumo as tc

    t_wall0 = time.time()
    state_path = str(job["state"])
    meta_path = str(job["meta"])
    r = int(job["r"])
    seed = int(job["seed"])
    action = str(job["action"])
    horizon = int(job.get("horizon", HORIZON_STEPS))
    variant = str(job.get("variant", "B"))

    hyp_pos = float(job.get("hyp_pos", 755.3)) if job.get("hyp_pos") is not None else 755.3
    hyp_clear_time = float(job["hyp_clear_time"]) if job.get("hyp_clear_time") is not None else None
    job_branch_factor = job.get("branch_factor")
    reuse_blockers = bool(job.get("reuse_blockers", False))
    queue_trace = bool(job.get("queue_trace", False))

    cmd = twin_cmd(r, ["--load-state", state_path])
    try:
        tc.start(cmd)
        t0 = tc.simulation.getTime()

        meta = json.load(open(meta_path, encoding="utf-8"))
        cs = ControlState.from_dict(meta["control_state"])
        cs.apply(tc)

        # Apply H_G5 point blockage: ktb_n1 lanes 0-1 blocked at hyp_pos
        if reuse_blockers:
            # H arm: the blockers are already in the loaded state; never re-add them.
            blocker_error = reused_blocker_error(tc, hyp_pos)
            if blocker_error is not None:
                return {
                    "world": "twin",
                    "seed": seed,
                    "replication": r,
                    "action": action,
                    "J": None,
                    "veh_digest": None,
                    "error": blocker_error,
                    "reason": "blockers_missing",
                    "status": "blockers_missing",
                    "wall_s": time.time() - t_wall0,
                    "variant": variant,
                    "hyp_pos": hyp_pos,
                    "hyp_clear_time": hyp_clear_time,
                    "branch_factor": job_branch_factor,
                    "reuse_blockers": True,
                    "queue_trace": None,
                }
        else:
            if "hyp_route" not in tc.route.getIDList():
                tc.route.add("hyp_route", ["ktb_n1"])
            for ln in (0, 1):
                vid = f"hyp_blocker_{ln}"
                tc.vehicle.add(
                    vid,
                    "hyp_route",
                    typeID="t_car",
                    departLane=str(ln),
                    departPos=str(hyp_pos - 1),
                    departSpeed="0",
                )
                tc.vehicle.setStop(
                    vid,
                    "ktb_n1",
                    pos=hyp_pos,
                    laneIndex=ln,
                    duration=3600.0,
                )
                tc.vehicle.setLaneChangeMode(vid, 0)

        # Twin future demand: D_T(r) = 900000 + 1000 * seed + r
        d_seed = D_T_seed(seed, r)
        cand_path = meta.get("demand_path")
        if job_branch_factor is not None:
            base_factor = float(job_branch_factor)
        else:
            base_factor = meta.get("twin_base_factor") or 0.85
        stream = TwinDemandStream(
            seed=d_seed,
            path=cand_path,
            base_factor=base_factor,
        )
        stream.m = dict(meta.get("m") or {})
        stream.seek(t0)

        control = get_control()
        compliance = get_twin_compliance()
        act = ActionExecutor(control, compliance, cs)
        if action != "A0":
            act.apply(tc, action)

        total_veh_steps = 0
        blocker_stops: Dict[str, Dict[str, Any]] = {}
        actual_clear_time: Optional[float] = None
        release_evidence: Dict[str, Dict[str, Any]] = {}
        pending_release_check: List[str] = []
        release_done = False
        trace: List[Dict[str, Any]] = []
        edges = load_queue_edges() if queue_trace else None
        if queue_trace:
            # t = t_d: right after the load, before stepping; pending is unreadable here.
            trace.append(queue_snapshot(tc, t0, edges, pending=None))

        for k in range(1, horizon + 1):
            stream.insert_due(tc, t0 + k)
            tc.simulationStep()
            t = tc.simulation.getTime()

            # Verify releases from the previous step: a released blocker must not be stopped
            if pending_release_check:
                for vid in pending_release_check:
                    ev = release_evidence[vid]
                    present_after = vid in tc.vehicle.getIDList()
                    ev["stopped_after"] = bool(present_after and tc.vehicle.isStopped(vid))
                    ev["checked_at"] = t
                    # a blocker missing at clearance, or whose resume() raised, is a failed release
                    ev["released"] = bool(ev["resumed"] and present_after and not ev["stopped_after"])
                failed = [v for v in pending_release_check if not release_evidence[v]["released"]]
                pending_release_check = []
                if failed:
                    return {
                        "world": "twin",
                        "seed": seed,
                        "replication": r,
                        "action": action,
                        "J": None,
                        "veh_digest": None,
                        "error": f"blockers still stopped after resume: {failed}",
                        "reason": "clear_failed",
                        "status": "clear_failed",
                        "wall_s": time.time() - t_wall0,
                        "variant": variant,
                        "hyp_pos": hyp_pos,
                        "hyp_clear_time": hyp_clear_time,
                        "branch_factor": base_factor,
                        "reuse_blockers": reuse_blockers,
                        "actual_clear_time": actual_clear_time,
                        "blocker_release_0": release_evidence.get("hyp_blocker_0"),
                        "blocker_release_1": release_evidence.get("hyp_blocker_1"),
                        "queue_trace": trace if queue_trace else None,
                    }

            # Record actual blocker placement (edge, lane, pos, time stopped)
            if len(blocker_stops) < 2:
                for ln in (0, 1):
                    vid = f"hyp_blocker_{ln}"
                    if vid not in blocker_stops and vid in tc.vehicle.getIDList() and tc.vehicle.isStopped(vid):
                        blocker_stops[vid] = {
                            "edge": tc.vehicle.getRoadID(vid),
                            "lane": tc.vehicle.getLaneIndex(vid),
                            "pos": round(tc.vehicle.getLanePosition(vid), 4),
                            "time_stopped": t,
                        }

            if queue_trace and int(round(t)) % 60 == 0:
                trace.append(queue_snapshot(tc, t, edges, pending=list(tc.simulation.getPendingVehicles())))

            # Handle clearance override at absolute simulation time: resume after this step,
            # before advancing to the next second (plan: after the 5,400-s step).
            if hyp_clear_time is not None and t >= hyp_clear_time and not release_done:
                release_done = True
                for ln in (0, 1):
                    vid = f"hyp_blocker_{ln}"
                    ev: Dict[str, Any] = {
                        "present": vid in tc.vehicle.getIDList(),
                        "stopped_at_clear": False,
                        "resumed": False,
                        "resumed_at": None,
                        "stopped_after": None,
                        "checked_at": None,
                        "released": None,
                    }
                    release_evidence[vid] = ev
                    if ev["present"]:
                        ev["stopped_at_clear"] = bool(tc.vehicle.isStopped(vid))
                        if ev["stopped_at_clear"]:
                            try:
                                tc.vehicle.resume(vid)
                                ev["resumed"] = True
                                ev["resumed_at"] = t
                            except Exception as exc:
                                ev["error"] = f"{type(exc).__name__}: {exc}"
                        else:
                            ev["released"] = True
                    if ev["resumed"] or not ev["present"] or "error" in ev:
                        pending_release_check.append(vid)
                if any(ev["resumed"] for ev in release_evidence.values()):
                    actual_clear_time = t

            act.step(tc)
            n_run = tc.vehicle.getIDCount()
            n_pend = len(tc.simulation.getPendingVehicles())
            total_veh_steps += (n_run + n_pend)

        digest, n_veh = veh_digest(tc)
        J = total_veh_steps / 3600.0

        b0 = blocker_stops.get("hyp_blocker_0", {})
        b1 = blocker_stops.get("hyp_blocker_1", {})

        return {
            "world": "twin",
            "seed": seed,
            "replication": r,
            "action": action,
            "J": J,
            "veh_digest": digest,
            "n_vehicles": n_veh,
            "wall_s": time.time() - t_wall0,
            "status": "ok",
            "variant": variant,
            "hyp_pos": hyp_pos,
            "hyp_clear_time": hyp_clear_time,
            "branch_factor": base_factor,
            "reuse_blockers": reuse_blockers,
            "blocker_edge": "ktb_n1",
            "blocker_lane_0": 0,
            "blocker_pos_0": b0.get("pos"),
            "blocker_t_stop_0": b0.get("time_stopped"),
            "blocker_lane_1": 1,
            "blocker_pos_1": b1.get("pos"),
            "blocker_t_stop_1": b1.get("time_stopped"),
            "actual_clear_time": actual_clear_time,
            "blocker_release_0": release_evidence.get("hyp_blocker_0"),
            "blocker_release_1": release_evidence.get("hyp_blocker_1"),
            "queue_trace": trace if queue_trace else None,
        }
    except Exception as e:
        return {
            "world": "twin",
            "seed": seed,
            "replication": r,
            "action": action,
            "J": None,
            "veh_digest": None,
            "error": str(e),
            "reason": type(e).__name__,
            "status": "error",
            "wall_s": time.time() - t_wall0,
            "variant": variant,
            "hyp_pos": hyp_pos,
            "hyp_clear_time": hyp_clear_time,
            "branch_factor": job_branch_factor,
            "reuse_blockers": reuse_blockers,
            "queue_trace": None,
        }
    finally:
        try:
            tc.close()
        except Exception:
            pass


def _proxy_audit_worker(job: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one Proxy (or Calibration) audit branch in a new process."""
    import libsumo as tc

    t_wall0 = time.time()
    state_path = str(job["state"])
    routes_path = str(job["routes"])
    m = int(job["m"])
    seed = int(job["seed"])
    action = str(job["action"])
    horizon = int(job.get("horizon", HORIZON_STEPS))
    orig_future_ids = set(job.get("orig_future_ids") or [])
    world = str(job.get("world", "proxy"))
    queue_trace = bool(job.get("queue_trace", False))

    cmd = proxy_cmd(m, routes=routes_path, extra=["--load-state", state_path])
    try:
        tc.start(cmd)
        t0 = tc.simulation.getTime()

        control = get_control()
        # Hidden Proxy true compliance
        compliance = 0.35
        cs = ControlState()
        act = ActionExecutor(control, compliance, cs)
        if action != "A0":
            act.apply(tc, action)

        total_veh_steps = 0
        trace: List[Dict[str, Any]] = []
        edges = load_queue_edges() if queue_trace else None
        if queue_trace:
            # t = t_d: right after the load, before stepping; pending is unreadable here.
            trace.append(queue_snapshot(tc, t0, edges, pending=None))
        for k in range(1, horizon + 1):
            tc.simulationStep()
            t = tc.simulation.getTime()
            if queue_trace and int(round(t)) % 60 == 0:
                trace.append(queue_snapshot(tc, t, edges, pending=list(tc.simulation.getPendingVehicles())))
            # Truth schedule clearance at 5,400 s inside branch
            if t >= 5400.0:
                for vid in ("incident_0", "incident_1"):
                    if vid in tc.vehicle.getIDList() and tc.vehicle.isStopped(vid):
                        tc.vehicle.resume(vid)
            act.step(tc)

            # Assert no original future departure remains / entered
            if orig_future_ids:
                curr_ids = set(tc.vehicle.getIDList())
                leaked = curr_ids & orig_future_ids
                assert len(leaked) == 0, f"Original departure leaked: {leaked}"

            n_run = tc.vehicle.getIDCount()
            n_pend = len(tc.simulation.getPendingVehicles())
            total_veh_steps += (n_run + n_pend)

        digest, n_veh = veh_digest(tc)
        J = total_veh_steps / 3600.0
        return {
            "world": world,
            "seed": seed,
            "replication": m,
            "action": action,
            "J": J,
            "veh_digest": digest,
            "n_vehicles": n_veh,
            "wall_s": time.time() - t_wall0,
            "status": "ok",
            "queue_trace": trace if queue_trace else None,
        }
    except Exception as e:
        return {
            "world": world,
            "seed": seed,
            "replication": m,
            "action": action,
            "J": None,
            "veh_digest": None,
            "error": str(e),
            "reason": type(e).__name__,
            "status": "error",
            "wall_s": time.time() - t_wall0,
            "queue_trace": None,
        }
    finally:
        try:
            tc.close()
        except Exception:
            pass


def run_twin_branch_jobs(jobs: List[Dict[str, Any]], workers: int = 8) -> List[Dict[str, Any]]:
    """Run Twin audit branch jobs across workers."""
    if not jobs:
        return []
    n = max(1, min(int(workers), len(jobs)))
    if n == 1:
        return [_twin_audit_worker(j) for j in jobs]
    with mp.get_context("spawn").Pool(n) as pool:
        return pool.map(_twin_audit_worker, jobs)


def run_proxy_branch_jobs(jobs: List[Dict[str, Any]], workers: int = 8) -> List[Dict[str, Any]]:
    """Run Proxy / Calibration audit branch jobs across workers."""
    if not jobs:
        return []
    n = max(1, min(int(workers), len(jobs)))
    if n == 1:
        return [_proxy_audit_worker(j) for j in jobs]
    with mp.get_context("spawn").Pool(n) as pool:
        return pool.map(_proxy_audit_worker, jobs)
