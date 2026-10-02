"""Step 1: build the corridor network used by all worlds from net_full.net.xml.

1. Keep motorway/trunk edges + every edge named Kwun Tong Road / Kai Fuk / Kwun Tong Bypass
   + 1-hop side-street stubs (edges of any class touching a kept edge), so side-street traffic enters
   through a junction instead of spawning mid-arterial.
2. Lane counts from TD: where a TD detector reports MORE lanes than the SUMO edge, set numLanes to
   the TD count and propagate along the same-name simple chain (1 in / 1 out) up to CHAIN_M metres.
   Fewer TD lanes than SUMO is left alone (detectors may not cover turn lanes).
3. netconvert -s net_full --keep-edges.input-file ... -e patch.edg.xml -o net.net.xml
Writes scenarios/kwuntong/{keep_edges.txt, lane_patch.edg.xml, lane_patch.json}.
"""
import csv
import json
import subprocess
from collections import defaultdict

import sumolib

from citypulse.config import HK_DIR, NET_FILE, OSM_FILE, RESULTS, SCEN, sumo_bin
from citypulse.network.map_detectors import map_all

FULL = SCEN / "net_full.net.xml"
CORRIDOR_NAMES = ("Kwun Tong Road", "Kai Fuk", "Kwun Tong Bypass")
CHAIN_M = 600.0
SIGNAL_RADIUS_M = 30.0


def core_edges(net):
    return {e.getID() for e in net.getEdges()
            if any(k in e.getType() for k in ("motorway", "trunk"))
            or any(k in (e.getName() or "") for k in CORRIDOR_NAMES)}


def with_stubs(net, core):
    keep = set(core)
    for eid in core:
        e = net.getEdge(eid)
        for n in (e.getFromNode(), e.getToNode()):
            for x in list(n.getIncoming()) + list(n.getOutgoing()):
                if x.getFunction() != "internal":
                    keep.add(x.getID())
    return keep


def td_lane_counts():
    lanes = defaultdict(set)
    for f in sorted((HK_DIR / "raw").glob("*.csv")):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                lanes[r["detector_id"]].add(r["lane_id"])
    return {d: len(v) for d, v in lanes.items()}


def chain(net, e, direction):
    out, cur, dist = [], e, 0.0
    while dist < CHAIN_M:
        nxt = list(cur.getOutgoing()) if direction == "down" else list(cur.getIncoming())
        if len(nxt) != 1:
            break
        n = nxt[0]
        if (n.getName() or "") != (e.getName() or "") or len(n.getIncoming() if direction == "down" else n.getOutgoing()) != 1:
            break
        out.append(n)
        dist += n.getLength()
        cur = n
    return out


def signal_nodes(net, keep, radius=SIGNAL_RADIUS_M):
    """Priority junctions of the kept network where a minor road meets a kept major edge and OSM has a
    highway=traffic_signals node within `radius` m. These were signalised in OSM but lost their signal
    because the side streets beyond the stub (residential/service) are not in the extract."""
    import xml.etree.ElementTree as ET
    root = ET.parse(OSM_FILE).getroot()
    pts = []
    for n in root.iter("node"):
        if any(t.get("k") == "highway" and t.get("v") == "traffic_signals" for t in n.findall("tag")):
            pts.append(net.convertLonLat2XY(float(n.get("lon")), float(n.get("lat"))))
    out = set()
    for node in net.getNodes():
        if node.getType() not in ("priority", "right_before_left", "left_before_right"):
            continue
        edges = [e for e in list(node.getIncoming()) + list(node.getOutgoing()) if e.getID() in keep]
        if len(node.getIncoming()) < 2 or len(edges) < 3:
            continue
        x, y = node.getCoord()
        if any((x - px) ** 2 + (y - py) ** 2 <= radius ** 2 for px, py in pts):
            out.add(node.getID())
    return out


def main():
    net = sumolib.net.readNet(str(FULL))
    keep = with_stubs(net, core_edges(net))
    (SCEN / "keep_edges.txt").write_text("\n".join(sorted(keep)), encoding="utf-8")
    td = td_lane_counts()
    mapped, _ = map_all(net)
    patch, log = {}, []
    for d in mapped:
        n_td = td.get(d["id"], 0)
        e = net.getEdge(d["edge"])
        if n_td > e.getLaneNumber():
            for x in [e] + chain(net, e, "down") + chain(net, e, "up"):
                if x.getID() in keep and x.getLaneNumber() < n_td:
                    patch[x.getID()] = max(patch.get(x.getID(), 0), n_td)
            log.append({"detector": d["id"], "edge": e.getID(), "sumo_lanes": e.getLaneNumber(), "td_lanes": n_td})
    with open(SCEN / "lane_patch.edg.xml", "w", encoding="utf-8") as fh:
        fh.write("<edges>\n")
        for eid, n in sorted(patch.items()):
            fh.write(f'    <edge id="{eid}" numLanes="{n}"/>\n')
        fh.write("</edges>\n")
    json.dump({"detectors": log, "patched_edges": patch, "kept_edges": len(keep)},
              open(SCEN / "lane_patch.json", "w"), indent=1)
    sig = signal_nodes(net, keep)
    with open(SCEN / "signal_patch.nod.xml", "w", encoding="utf-8") as fh:
        fh.write("<nodes>\n")
        for nid in sorted(sig):
            fh.write(f'    <node id="{nid}" type="traffic_light"/>\n')
        fh.write("</nodes>\n")
    json.dump({"detectors": log, "patched_edges": patch, "kept_edges": len(keep), "signalised_nodes": sorted(sig)},
              open(SCEN / "lane_patch.json", "w"), indent=1)
    cmd = [sumo_bin("netconvert"), "-s", str(FULL), "--keep-edges.input-file", str(SCEN / "keep_edges.txt"),
           "--keep-edges.components", "1", "-e", str(SCEN / "lane_patch.edg.xml"),
           "-n", str(SCEN / "signal_patch.nod.xml"), "--tls.default-type", "static", "-o", str(NET_FILE)]
    with open(RESULTS / "netconvert_patch.log", "w") as fh:
        subprocess.run(cmd, check=True, stderr=fh)
    out = sumolib.net.readNet(str(NET_FILE))
    print(json.dumps({"kept_edges_requested": len(keep), "edges": len(out.getEdges()),
                      "tls": len(out.getTrafficLights()), "lane_patched_edges": len(patch),
                      "detectors_with_more_td_lanes": len(log)}))


if __name__ == "__main__":
    main()
