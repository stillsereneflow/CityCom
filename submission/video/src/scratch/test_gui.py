import os
import sys

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"

sys.path.insert(0, r"D:\CityCom-astra")

import traci
from citypulse.sim import base_cmd, get_vtypes_file, get_det_file, get_tls_file

cmd = base_cmd("sumo-gui") + [
    "-a", f"{get_vtypes_file('proxy')},{get_det_file()},{get_tls_file()}",
    "--seed", "4",
    "--start",
    "--quit-on-end",
]
print("CMD:", cmd)

try:
    traci.start(cmd)
    views = traci.gui.getIDList()
    print("Views:", views)
    if views:
        view_id = views[0]
        # test screenshot
        out_png = r"D:\CityCom-astra\submission\video\frames_check\test_shot.png"
        traci.gui.screenshot(view_id, out_png)
        traci.simulationStep()
        print("Screenshot command issued, stepped.")
    traci.close()
    print("Closed successfully.")
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
