import os
import sys
import json
import time

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

sys.path.insert(0, r"D:\CityCom-astra")

from citypulse.sim import (
    ControlState,
    get_control,
    get_twin_compliance,
    proxy_cmd,
    twin_cmd,
)
from citypulse.control.actions import ActionExecutor
from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import D_T_seed

QUEUE_EDGES = ["ktb_w1", "ktb_w2", "ktb_w3", "ktb_n1"]
BLOCKER_PREFIXES = ("hyp_", "incident_")

def run_proxy():
    import libsumo as tc
    print("--- Starting Proxy ---")
    state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\proxy\proxy_state_5100.xml.gz"
    routes_path = r"D:\CityCom-astra\results\frozen_audit\routes\proxy_s4501_m4.rou.xml"
    m = 4
    cmd = proxy_cmd(m, routes=routes_path, extra=["--load-state", state_path])
    tc.start(cmd)
    t0 = tc.simulation.getTime()
    print(f"Proxy loaded at t0={t0}")
    
    # Read t=5100 state before step
    veh_ids = tc.vehicle.getIDList()
    halted_count = 0
    for vid in veh_ids:
        if tc.vehicle.getSpeed(vid) < 0.1 and not vid.startswith(BLOCKER_PREFIXES):
            if tc.vehicle.getRoadID(vid) in QUEUE_EDGES:
                halted_count += 1
    print(f"Proxy t={t0}: total veh={len(veh_ids)}, halted on corridor={halted_count}")
    
    # Check incident vehicles
    for iv in ("incident_0", "incident_1"):
        if iv in veh_ids:
            print(f"  {iv}: road={tc.vehicle.getRoadID(iv)}, pos={tc.vehicle.getLanePosition(iv):.2f}, stopped={tc.vehicle.isStopped(iv)}")

    history = {int(round(t0)): halted_count}
    for k in range(1, 601):
        tc.simulationStep()
        t = tc.simulation.getTime()
        if t >= 5400.0:
            for vid in ("incident_0", "incident_1"):
                if vid in tc.vehicle.getIDList() and tc.vehicle.isStopped(vid):
                    tc.vehicle.resume(vid)
        if int(round(t)) % 10 == 0:
            cur_ids = tc.vehicle.getIDList()
            h_count = 0
            for vid in cur_ids:
                if tc.vehicle.getSpeed(vid) < 0.1 and not vid.startswith(BLOCKER_PREFIXES):
                    if tc.vehicle.getRoadID(vid) in QUEUE_EDGES:
                        h_count += 1
            history[int(round(t))] = h_count
            if int(round(t)) in (5100, 5400, 5700):
                print(f"Proxy t={t:.0f}: total veh={len(cur_ids)}, halted={h_count}")

    tc.close()
    return history

def run_twin():
    import libsumo as tc
    print("--- Starting Twin ---")
    state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.xml.gz"
    meta_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.json"
    r = 4
    seed = 4501
    cmd = twin_cmd(r, extra=["--load-state", state_path])
    tc.start(cmd)
    t0 = tc.simulation.getTime()
    print(f"Twin loaded at t0={t0}")

    meta = json.load(open(meta_path, encoding="utf-8"))
    cs = ControlState.from_dict(meta["control_state"])
    cs.apply(tc)

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

    # Read t=5100 state before step
    veh_ids = tc.vehicle.getIDList()
    halted_count = 0
    for vid in veh_ids:
        if tc.vehicle.getSpeed(vid) < 0.1 and not vid.startswith(BLOCKER_PREFIXES):
            if tc.vehicle.getRoadID(vid) in QUEUE_EDGES:
                halted_count += 1
    print(f"Twin t={t0}: total veh={len(veh_ids)}, halted on corridor={halted_count}")

    # Check hyp blockers
    for hb in ("hyp_blocker_0", "hyp_blocker_1"):
        if hb in veh_ids:
            print(f"  {hb}: road={tc.vehicle.getRoadID(hb)}, pos={tc.vehicle.getLanePosition(hb):.2f}, stopped={tc.vehicle.isStopped(hb)}")

    history = {int(round(t0)): halted_count}
    for k in range(1, 601):
        stream.insert_due(tc, t0 + k)
        tc.simulationStep()
        t = tc.simulation.getTime()
        if int(round(t)) % 10 == 0:
            cur_ids = tc.vehicle.getIDList()
            h_count = 0
            for vid in cur_ids:
                if tc.vehicle.getSpeed(vid) < 0.1 and not vid.startswith(BLOCKER_PREFIXES):
                    if tc.vehicle.getRoadID(vid) in QUEUE_EDGES:
                        h_count += 1
            history[int(round(t))] = h_count
            if int(round(t)) in (5100, 5400, 5700):
                print(f"Twin t={t:.0f}: total veh={len(cur_ids)}, halted={h_count}")

    tc.close()
    return history

if __name__ == "__main__":
    t0 = time.time()
    p_hist = run_proxy()
    print(f"Proxy finished in {time.time()-t0:.2f}s")
    t1 = time.time()
    t_hist = run_twin()
    print(f"Twin finished in {time.time()-t1:.2f}s")

