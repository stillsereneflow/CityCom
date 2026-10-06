"""Record real SUMO-GUI runs for Proxy and Twin worlds (seed 4501, replication 4, A0)."""
import os
import sys
import time
import json
import subprocess
from pathlib import Path

# Binding environment variables (prompt.md lines 15-18)
os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

sys.path.insert(0, r"D:\CityCom-astra")

import traci
from citypulse.sim import (
    ControlState,
    base_cmd,
    get_vtypes_file,
    get_det_file,
    get_tls_file,
    get_control,
    get_twin_compliance,
)
from citypulse.control.actions import ActionExecutor
from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import D_T_seed

# Output directory for raw screenshots
OUT_DIR = Path(r"D:\CityCom-astra\submission\video\src\sumo_screenshots")
PROXY_DIR = OUT_DIR / "proxy"
TWIN_DIR = OUT_DIR / "twin"
PROXY_DIR.mkdir(parents=True, exist_ok=True)
TWIN_DIR.mkdir(parents=True, exist_ok=True)

BOUNDS = (2400, 950, 3300, 1900)

def record_proxy():
    print("=== Recording Proxy World (Seed 4501, m=4, A0) ===", flush=True)
    state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\proxy\proxy_state_5100.xml.gz"
    routes_path = r"D:\CityCom-astra\results\frozen_audit\routes\proxy_s4501_m4.rou.xml"
    seed = 4

    cmd = base_cmd("sumo-gui") + [
        "-a", f"{get_vtypes_file('proxy')},{get_det_file()},{get_tls_file()}",
        "-r", routes_path,
        "--seed", str(seed),
        "--load-state", state_path,
        "--window-size", "960,720",
        "--start",
        "--delay", "20",
        "--log", r"D:\CityCom-astra\submission\video\src\sumo_proxy_log.txt",
        "--error-log", r"D:\CityCom-astra\submission\video\src\sumo_proxy_err.txt",
    ]

    traci.start(cmd)
    view_id = traci.gui.getIDList()[0]
    traci.gui.setBoundary(view_id, *BOUNDS)
    
    control = get_control()
    compliance = 0.35
    cs = ControlState()
    act = ActionExecutor(control, compliance, cs)
    
    t0 = traci.simulation.getTime()
    print(f"Proxy initialized at t={t0:.1f}", flush=True)

    # Initial screenshot at 5100
    shot_path = str(PROXY_DIR / f"shot_{int(round(t0)):04d}.png")
    traci.gui.screenshot(view_id, shot_path)
    traci.simulationStep()
    t = traci.simulation.getTime()

    horizon = 600 # 5100 to 5700
    # Step from 5101 to 5700
    for k in range(2, horizon + 1):
        traci.simulationStep()
        t = traci.simulation.getTime()
        
        # Truth schedule clearance at 5,400 s
        if t >= 5400.0:
            for vid in ("incident_0", "incident_1"):
                try:
                    if vid in traci.vehicle.getIDList() and traci.vehicle.isStopped(vid):
                        traci.vehicle.resume(vid)
                except Exception:
                    pass
        act.step(traci)
        
        if int(round(t)) % 10 == 0:
            shot_path = str(PROXY_DIR / f"shot_{int(round(t)):04d}.png")
            traci.gui.screenshot(view_id, shot_path)
            if int(round(t)) % 50 == 0:
                print(f"  Proxy t={t:.1f}, veh={traci.vehicle.getIDCount()}", flush=True)

    traci.simulationStep()
    traci.close(False)
    subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
    print("Proxy recording complete.", flush=True)


def record_twin():
    print("=== Recording Twin World (Seed 4501, r=4, A0) ===", flush=True)
    state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.xml.gz"
    meta_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.json"
    r = 4
    seed = 4501
    hyp_pos = 755.3

    cmd = base_cmd("sumo-gui") + [
        "-a", f"{get_vtypes_file('twin')},{get_det_file()},{get_tls_file()}",
        "--seed", str(r),
        "--load-state", state_path,
        "--window-size", "960,720",
        "--start",
        "--delay", "20",
        "--log", r"D:\CityCom-astra\submission\video\src\sumo_twin_log.txt",
        "--error-log", r"D:\CityCom-astra\submission\video\src\sumo_twin_err.txt",
    ]

    traci.start(cmd)
    view_id = traci.gui.getIDList()[0]
    traci.gui.setBoundary(view_id, *BOUNDS)
    
    t0 = traci.simulation.getTime()
    print(f"Twin initialized at t={t0:.1f}", flush=True)

    meta = json.load(open(meta_path, encoding="utf-8"))
    cs = ControlState.from_dict(meta["control_state"])
    cs.apply(traci)

    # Insert belief-B blockers: ktb_n1 lanes 0-1 blocked at hyp_pos
    if "hyp_route" not in traci.route.getIDList():
        traci.route.add("hyp_route", ["ktb_n1"])
    for ln in (0, 1):
        vid = f"hyp_blocker_{ln}"
        traci.vehicle.add(
            vid,
            "hyp_route",
            typeID="t_car",
            departLane=str(ln),
            departPos=str(hyp_pos - 1),
            departSpeed="0",
        )
        traci.vehicle.setStop(
            vid,
            "ktb_n1",
            pos=hyp_pos,
            laneIndex=ln,
            duration=3600.0,
        )
        traci.vehicle.setLaneChangeMode(vid, 0)

    # Restore demand stream
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

    control = get_control()
    compliance = get_twin_compliance()
    act = ActionExecutor(control, compliance, cs)
    
    # Initial screenshot at 5100
    shot_path = str(TWIN_DIR / f"shot_{int(round(t0)):04d}.png")
    traci.gui.screenshot(view_id, shot_path)
    stream.insert_due(traci, t0 + 1)
    traci.simulationStep()
    t = traci.simulation.getTime()

    horizon = 600 # 5100 to 5700
    for k in range(2, horizon + 1):
        stream.insert_due(traci, t0 + k)
        traci.simulationStep()
        t = traci.simulation.getTime()
        act.step(traci)

        if int(round(t)) % 10 == 0:
            shot_path = str(TWIN_DIR / f"shot_{int(round(t)):04d}.png")
            traci.gui.screenshot(view_id, shot_path)
            if int(round(t)) % 50 == 0:
                print(f"  Twin t={t:.1f}, veh={traci.vehicle.getIDCount()}", flush=True)

    traci.simulationStep()
    traci.close(False)
    subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
    print("Twin recording complete.", flush=True)


if __name__ == "__main__":
    t_start = time.time()
    record_proxy()
    time.sleep(1.0)
    record_twin()
    print(f"All recordings completed in {time.time() - t_start:.2f} s", flush=True)
