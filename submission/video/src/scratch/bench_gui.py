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
    "--quit-on-end",
]

print("Starting traci...")
t0 = time.time()
traci.start(cmd)
print(f"Started in {time.time() - t0:.2f} s")
view_id = traci.gui.getIDList()[0]
traci.gui.setBoundary(view_id, 2400, 950, 3300, 1900)

for i in range(15):
    t_step0 = time.time()
    traci.simulationStep()
    t = traci.simulation.getTime()
    dt = time.time() - t_step0
    print(f"Step {i}: sim_time={t}, wall_dt={dt:.3f}s, veh={traci.vehicle.getIDCount()}")
    if i == 5:
        traci.gui.screenshot(view_id, r"D:\CityCom-astra\submission\video\frames_check\step5.png")
    if i == 10:
        traci.gui.screenshot(view_id, r"D:\CityCom-astra\submission\video\frames_check\step10.png")

traci.simulationStep()
traci.close()
print("Done.")
