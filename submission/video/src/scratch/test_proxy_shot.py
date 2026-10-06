import os
import sys

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
    "--window-size", "960,800",
    "--start",
    "--quit-on-end",
]

print("Launching SUMO-GUI...")
traci.start(cmd)
view_id = traci.gui.getIDList()[0]
print("View ID:", view_id)
# Zoom on ktb_w3 -> ktb_n1
# Bounding box of ktb_w3 and ktb_n1 was roughly [2440, 980, 3280, 1870]
# Incident blockers hyp_pos = 755.3 on ktb_n1.
# Let's see the center of ktb_n1:
traci.gui.setBoundary(view_id, 2400, 950, 3300, 1900)
# Step once to apply state
traci.simulationStep()
t = traci.simulation.getTime()
print("Sim time:", t)
num_veh = traci.vehicle.getIDCount()
print("Vehicles count:", num_veh)

out_shot = r"D:\CityCom-astra\submission\video\frames_check\proxy_5101.png"
traci.gui.screenshot(view_id, out_shot)
traci.simulationStep()

traci.close()
print("Finished test_proxy_shot.")
