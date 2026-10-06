import os
import sys
import time

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
]

print("Starting traci...", flush=True)
traci.start(cmd)
view_id = traci.gui.getIDList()[0]
traci.gui.setBoundary(view_id, 2400, 950, 3300, 1900)

for step_idx in range(25):
    t0 = time.time()
    traci.simulationStep()
    t = traci.simulation.getTime()
    dt = time.time() - t0
    print(f"Step {step_idx}: t={t}, dt={dt:.4f}s", flush=True)
    if step_idx in (2, 10, 20):
        png = rf"D:\CityCom-astra\submission\video\frames_check\shot_{step_idx}.png"
        traci.gui.screenshot(view_id, png)
        print(f"Requested screenshot at step {step_idx}", flush=True)

traci.simulationStep()
traci.close()
print("All done successfully!", flush=True)
