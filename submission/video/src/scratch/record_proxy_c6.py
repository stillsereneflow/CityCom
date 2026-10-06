import os
import sys
import subprocess
from pathlib import Path

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
sys.path.insert(0, r"D:\CityCom-astra")

import traci
from citypulse.sim import (
    ControlState,
    base_cmd,
    get_vtypes_file,
    get_det_file,
    get_tls_file,
    get_control,
)
from citypulse.control.actions import ActionExecutor

OUT_DIR = Path(r"D:\CityCom-astra\submission\video\src\sumo_screenshots\proxy")
BOUNDS = (2400, 950, 3300, 1900)

state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\proxy\proxy_state_5100.xml.gz"
routes_path = r"D:\CityCom-astra\results\frozen_audit\routes\proxy_s4501_m4.rou.xml"

cmd = base_cmd("sumo-gui") + [
    "-a", f"{get_vtypes_file('proxy')},{get_det_file()},{get_tls_file()}",
    "-r", routes_path,
    "--seed", "4",
    "--load-state", state_path,
    "--window-size", "960,720",
    "--start",
    "--delay", "10",
]

print("Starting Proxy Chunk 6 (5660 -> 5700)...", flush=True)
traci.start(cmd)
view_id = traci.gui.getIDList()[0]
traci.gui.setBoundary(view_id, *BOUNDS)

control = get_control()
compliance = 0.35
cs = ControlState()
act = ActionExecutor(control, compliance, cs)

t0 = traci.simulation.getTime()

# Fast forward 5100 to 5650
for _ in range(550):
    traci.simulationStep()
    t = traci.simulation.getTime()
    if t >= 5400.0:
        for vid in ("incident_0", "incident_1"):
            try:
                if vid in traci.vehicle.getIDList() and traci.vehicle.isStopped(vid):
                    traci.vehicle.resume(vid)
            except Exception:
                pass
    act.step(traci)

print(f"Fast forward reached t={t:.1f}, now recording 5660 -> 5700...", flush=True)
for _ in range(50):
    traci.simulationStep()
    t = traci.simulation.getTime()
    if t >= 5400.0:
        for vid in ("incident_0", "incident_1"):
            try:
                if vid in traci.vehicle.getIDList() and traci.vehicle.isStopped(vid):
                    traci.vehicle.resume(vid)
            except Exception:
                pass
    act.step(traci)

    if int(round(t)) % 10 == 0:
        shot_path = str(OUT_DIR / f"shot_{int(round(t)):04d}.png")
        traci.gui.screenshot(view_id, shot_path)
        print(f"  Proxy t={t:.1f}", flush=True)

traci.simulationStep()
traci.close(False)
subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
print("Proxy Chunk 6 done!", flush=True)
