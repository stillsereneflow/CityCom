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
from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import D_T_seed

OUT_DIR = Path(r"D:\CityCom-astra\submission\video\src\sumo_screenshots\twin")
OUT_DIR.mkdir(parents=True, exist_ok=True)
BOUNDS = (2400, 950, 3300, 1900)

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
    "--delay", "10",
]

print("Starting Twin Chunk 1 (5110 -> 5250)...", flush=True)
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

for k in range(1, 151): # 5101 to 5250
    stream.insert_due(traci, t0 + k)
    traci.simulationStep()
    t = traci.simulation.getTime()
    act.step(traci)

    if int(round(t)) % 10 == 0:
        shot_path = str(OUT_DIR / f"shot_{int(round(t)):04d}.png")
        traci.gui.screenshot(view_id, shot_path)
        if int(round(t)) % 50 == 0:
            print(f"  Twin t={t:.1f}", flush=True)

traci.simulationStep()
traci.close(False)
subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
print("Twin Chunk 1 complete!", flush=True)
