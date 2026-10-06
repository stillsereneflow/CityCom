import os
import sys
import json
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
    get_twin_compliance,
)
from citypulse.control.actions import ActionExecutor

OUT_DIR = Path(r"D:\CityCom-astra\submission\video\src\sumo_screenshots\twin")
BOUNDS = (2400, 950, 3300, 1900)

state_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.xml.gz"
meta_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.json"
routes_path = r"D:\CityCom-astra\submission\video\src\twin_demand.rou.xml"
r = 4
hyp_pos = 755.3

cmd = base_cmd("sumo-gui") + [
    "-a", f"{get_vtypes_file('twin')},{get_det_file()},{get_tls_file()}",
    "-r", routes_path,
    "--seed", str(r),
    "--load-state", state_path,
    "--window-size", "960,720",
    "--start",
    "--delay", "15",
]

print("Starting twin with route file...", flush=True)
traci.start(cmd)
view_id = traci.gui.getIDList()[0]
traci.gui.setBoundary(view_id, *BOUNDS)

t0 = traci.simulation.getTime()

meta = json.load(open(meta_path, encoding="utf-8"))
cs = ControlState.from_dict(meta["control_state"])
cs.apply(traci)

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

control = get_control()
compliance = get_twin_compliance()
act = ActionExecutor(control, compliance, cs)

for k in range(1, 35):
    traci.simulationStep()
    t = traci.simulation.getTime()
    act.step(traci)

    if int(round(t)) % 10 == 0:
        shot_path = str(OUT_DIR / f"shot_{int(round(t)):04d}.png")
        traci.gui.screenshot(view_id, shot_path)
        print(f"Twin t={t:.1f}, veh={traci.vehicle.getIDCount()}, shot saved", flush=True)

traci.simulationStep()
traci.close(False)
subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
print("Twin test with route file succeeded completely!", flush=True)
