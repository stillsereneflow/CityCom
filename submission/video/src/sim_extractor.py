"""Simulation data extractor for Segment 2 (Two Worlds).
Runs Proxy and Twin headlessly via libsumo in the frozen venv Python.
Records vehicle coordinates, speeds, and corridor halted counts every 10s from 5100 to 5700s.
Also extracts lane geometry of the Kwun Tong Bypass corridor from net5.net.xml via sumolib.
"""
import os
import sys
import json
import time
from pathlib import Path

# Ensure required environment variables
os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

ROOT = Path(r"D:\CityCom-astra")
sys.path.insert(0, str(ROOT))

from citypulse.sim import (
    ControlState,
    proxy_cmd,
    twin_cmd,
)
from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import D_T_seed

QUEUE_EDGES = ["ktb_w1", "ktb_w2", "ktb_w3", "ktb_n1"]
CORRIDOR_EDGES = ["ktb_w2", "ktb_w3", "ktb_n1", "dv_off_ktb_n1", "ktb_n2"]
BLOCKER_PREFIXES = ("hyp_", "incident_")


def extract_network_geometry():
    import sumolib
    net_path = ROOT / "scenarios" / "kwuntong" / "blite" / "net5.net.xml"
    net = sumolib.net.readNet(str(net_path))
    geometry = {}
    for eid in CORRIDOR_EDGES:
        edge = net.getEdge(eid)
        geometry[eid] = {
            "length": edge.getLength(),
            "lanes": [
                {
                    "id": lane.getID(),
                    "width": lane.getWidth(),
                    "shape": [list(pt) for pt in lane.getShape()]
                }
                for lane in edge.getLanes()
            ]
        }
    return geometry


def capture_snapshot(tc, t, blocker_keys):
    veh_ids = tc.vehicle.getIDList()
    vehicles = []
    corridor_halted = 0
    blockers = {}

    for vid in veh_ids:
        try:
            x, y = tc.vehicle.getPosition(vid)
            spd = float(tc.vehicle.getSpeed(vid))
            road = tc.vehicle.getRoadID(vid)
            lane_idx = int(tc.vehicle.getLaneIndex(vid))
            lane_pos = float(tc.vehicle.getLanePosition(vid))
            stopped = bool(tc.vehicle.isStopped(vid))
        except Exception:
            continue

        is_blk = vid.startswith(BLOCKER_PREFIXES)
        is_halt = (spd < 0.1) and (not is_blk)

        if is_halt and (road in QUEUE_EDGES):
            corridor_halted += 1

        if is_blk:
            blockers[vid] = {
                "pos": [round(x, 2), round(y, 2)],
                "road": road,
                "lane": lane_idx,
                "lane_pos": round(lane_pos, 2),
                "stopped": stopped,
                "speed": round(spd, 2)
            }
        else:
            # Save compact vehicle record for corridor & nearby area
            vehicles.append({
                "id": vid,
                "pos": [round(x, 2), round(y, 2)],
                "spd": round(spd, 2),
                "road": road,
                "halt": is_halt
            })

    return {
        "t": float(t),
        "total_veh": len(veh_ids),
        "corridor_halted": corridor_halted,
        "blockers": blockers,
        "vehicles": vehicles
    }


def run_proxy_sim():
    import libsumo as tc
    print("--- Running Proxy Simulation (Seed 4501, SUMO seed 4, A0) ---")
    state_path = str(ROOT / "results" / "frozen_audit" / "runs" / "seed_4501" / "proxy" / "proxy_state_5100.xml.gz")
    routes_path = str(ROOT / "results" / "frozen_audit" / "routes" / "proxy_s4501_m4.rou.xml")
    m = 4
    cmd = proxy_cmd(m, routes=routes_path, extra=["--load-state", state_path])
    tc.start(cmd)
    t0 = tc.simulation.getTime()

    snapshots = {}
    # Record t=5100s initial loaded state
    snapshots[int(round(t0))] = capture_snapshot(tc, t0, ("incident_0", "incident_1"))

    # Step from 5100 to 5700s
    for k in range(1, 601):
        tc.simulationStep()
        t = tc.simulation.getTime()
        
        # Resume incident after 5400s step
        if t >= 5400.0:
            for vid in ("incident_0", "incident_1"):
                if vid in tc.vehicle.getIDList() and tc.vehicle.isStopped(vid):
                    tc.vehicle.resume(vid)

        t_int = int(round(t))
        if t_int % 10 == 0:
            snapshots[t_int] = capture_snapshot(tc, t, ("incident_0", "incident_1"))

    tc.close()
    print(f"Proxy finished: captured {len(snapshots)} snapshots.")
    return snapshots


def run_twin_sim():
    import libsumo as tc
    print("--- Running Twin Simulation (Seed 4501, Rep 4, A0, Belief B) ---")
    state_path = str(ROOT / "results" / "frozen_audit" / "runs" / "seed_4501" / "twin" / "twin_state_5100.xml.gz")
    meta_path = str(ROOT / "results" / "frozen_audit" / "runs" / "seed_4501" / "twin" / "twin_state_5100.json")
    r = 4
    seed = 4501
    cmd = twin_cmd(r, extra=["--load-state", state_path])
    tc.start(cmd)
    t0 = tc.simulation.getTime()

    meta = json.load(open(meta_path, encoding="utf-8"))
    cs = ControlState.from_dict(meta["control_state"])
    cs.apply(tc)

    # Insert belief B blockers at 755.3 m on ktb_n1 lanes 0 and 1
    hyp_pos = 755.3
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

    # Demand stream restoration
    d_seed = D_T_seed(seed, r)
    cand_path = meta.get("demand_path")
    base_factor = meta.get("twin_base_factor") or 0.85
    stream = TwinDemandStream(
        seed=d_seed,
        path=cand_path,
        base_factor=base_factor,
    )
    stream.m = dict(meta.get("m") or {})
    stream.seek(t0)

    snapshots = {}
    # Record t=5100s initial state with blockers placed
    snap0 = capture_snapshot(tc, t0, ("hyp_blocker_0", "hyp_blocker_1"))
    # In SUMO, added vehicles become visible on the network after the first step; fill their known stop position at t=5100
    if not snap0["blockers"]:
        snap0["blockers"] = {
            "hyp_blocker_0": {"pos": [2597.19, 1673.22], "road": "ktb_n1", "lane": 0, "lane_pos": 755.3, "stopped": True, "speed": 0.0},
            "hyp_blocker_1": {"pos": [2599.68, 1675.23], "road": "ktb_n1", "lane": 1, "lane_pos": 755.3, "stopped": True, "speed": 0.0},
        }
    snapshots[int(round(t0))] = snap0

    # Step from 5100 to 5700s
    for k in range(1, 601):
        stream.insert_due(tc, t0 + k)
        tc.simulationStep()
        t = tc.simulation.getTime()

        t_int = int(round(t))
        if t_int % 10 == 0:
            snapshots[t_int] = capture_snapshot(tc, t, ("hyp_blocker_0", "hyp_blocker_1"))

    tc.close()
    print(f"Twin finished: captured {len(snapshots)} snapshots.")
    return snapshots


def main():
    t_start = time.time()
    print("Extracting network geometry...")
    geometry = extract_network_geometry()

    print("Running Proxy world...")
    proxy_snaps = run_proxy_sim()

    print("Running Twin world...")
    twin_snaps = run_twin_sim()

    out_file = Path(r"D:\CityCom-astra\submission\video\src\sim_trace_4501.json")
    out_data = {
        "geometry": geometry,
        "proxy": proxy_snaps,
        "twin": twin_snaps,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f)

    print(f"Extraction complete in {time.time() - t_start:.2f}s. Saved to {out_file}")

    # Print verification halted counts
    for t in (5100, 5400, 5700):
        p_halt = proxy_snaps[t]["corridor_halted"]
        t_halt = twin_snaps[t]["corridor_halted"]
        print(f"t={t}s: Proxy halted={p_halt}, Twin halted={t_halt}")


if __name__ == "__main__":
    main()
