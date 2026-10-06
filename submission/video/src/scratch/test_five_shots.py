import os
import sys
import subprocess

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
sys.path.insert(0, r"D:\CityCom-astra")

import traci
from citypulse.sim import base_cmd, get_vtypes_file, get_det_file, get_tls_file

state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\proxy\proxy_state_5100.xml.gz"
routes_path = r"D:\CityCom-astra\results\frozen_audit\routes\proxy_s4501_m4.rou.xml"

cmd = base_cmd("sumo-gui") + [
    "-a", f"{get_vtypes_file('proxy')},{get_det_file()},{get_tls_file()}",
    "-r", routes_path,
    "--seed", "4",
    "--load-state", state_path,
    "--window-size", "960,720",
    "--start",
    "--log", r"D:\CityCom-astra\submission\video\src\sumo_log.txt",
    "--error-log", r"D:\CityCom-astra\submission\video\src\sumo_err.txt",
]

print("Starting traci...", flush=True)
traci.start(cmd)
view_id = traci.gui.getIDList()[0]
traci.gui.setBoundary(view_id, 2400, 950, 3300, 1900)

for step_idx in range(50):
    traci.simulationStep()
    t = traci.simulation.getTime()
    if step_idx % 10 == 0:
        png = rf"D:\CityCom-astra\submission\video\frames_check\multi_{step_idx}.png"
        traci.gui.screenshot(view_id, png)
        print(f"Step {step_idx}: t={t}, shot requested", flush=True)

traci.simulationStep()
traci.close(False)
subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
print("All 5 screenshots done!", flush=True)
