import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
sys.path.insert(0, r"D:\CityCom-astra")

from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import D_T_seed

meta_path = r"D:\CityCom-astra\results\frozen_audit\runs\seed_4501\twin\twin_state_5100.json"
meta = json.load(open(meta_path, encoding="utf-8"))

seed = 4501
r = 4
t0 = 5100.0
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

# Collect all due vehicles up to 5700
vehicles = []
for k in range(1, 601):
    t_cur = t0 + k
    for vid, edges in stream.due(t_cur):
        vehicles.append((t_cur, vid, edges))

print(f"Generated {len(vehicles)} Twin demand vehicles for [5100, 5700].")

# Write to XML
root = ET.Element("routes")
for dep, vid, edges in vehicles:
    v = ET.SubElement(root, "vehicle", id=vid, depart=f"{dep:.1f}", type="tdist", departLane="best", departSpeed="max")
    ET.SubElement(v, "route", edges=" ".join(edges))

out_path = Path(r"D:\CityCom-astra\submission\video\src\twin_demand.rou.xml")
tree = ET.ElementTree(root)
ET.indent(tree, space="  ")
tree.write(out_path, encoding="utf-8", xml_declaration=True)
print(f"Saved route file to {out_path}.")
