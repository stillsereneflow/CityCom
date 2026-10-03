"""Map TD detectors (lat/lon + bearing) onto SUMO edges and write E1 loops (one per lane).

Match rule: lane within RADIUS m of the detector, edge name contains the TD road name,
edge bearing at the projection point within MAX_BEARING_DIFF of the TD 'Rotation' field.
"""
import csv
import json
import math
from xml.sax.saxutils import quoteattr

import sumolib
from sumolib.geomhelper import polygonOffsetWithMinimumDistanceToPoint

from citypulse.config import BBOX, CORRIDOR_PREFIXES, HK_DIR, NET_FILE, SCEN, SENSOR_PERIOD

RADIUS = 40.0
MAX_BEARING_DIFF = 50.0


def bearing_at(shape, offset):
    """Compass bearing (deg, clockwise from north) of a polyline at a given offset."""
    acc = 0.0
    for (x1, y1), (x2, y2) in zip(shape[:-1], shape[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if acc + seg >= offset or (x2, y2) == shape[-1]:
            return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360
        acc += seg
    return 0.0


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def road_token(road_en):
    return road_en.split(" near ")[0].split(" at ")[0].split(" - ")[0].strip()


def load_detectors():
    out = []
    with open(HK_DIR / "detector_locations.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
            if not r["AID_ID_Number"].startswith(CORRIDOR_PREFIXES):
                continue
            if not (BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]):
                continue
            out.append({"id": r["AID_ID_Number"], "lat": lat, "lon": lon, "bearing": float(r["Rotation"]),
                        "road": road_token(r["Road_EN"]), "bound": r["Road_EN"].split(" - ")[-1].strip()})
    return out


def map_all(net):
    mapped, unmapped = [], []
    for d in load_detectors():
        x, y = net.convertLonLat2XY(d["lon"], d["lat"])
        best = None
        for lane, dist in net.getNeighboringLanes(x, y, RADIUS):
            edge = lane.getEdge()
            if edge.getFunction() == "internal" or d["road"].lower() not in (edge.getName() or "").lower():
                continue
            off = polygonOffsetWithMinimumDistanceToPoint((x, y), lane.getShape(), perpendicular=False)
            if angdiff(bearing_at(lane.getShape(), off), d["bearing"]) > MAX_BEARING_DIFF:
                continue
            if best is None or dist < best[1]:
                best = (edge, dist, off)
        if best is None:
            unmapped.append(d)
            continue
        edge, dist, off = best
        mapped.append({**d, "edge": edge.getID(), "dist_m": round(dist, 1), "pos": round(off, 1),
                       "n_lanes": edge.getLaneNumber()})
    return mapped, unmapped


def write_additional(mapped, path, lane_lens=None):
    lens = lane_lens if lane_lens is not None else sumolib_lane_len
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<additional>\n")
        for m in mapped:
            for i in range(m["n_lanes"]):
                lane_len = lens[(m["edge"], i)]
                pos = min(max(m["pos"], 1.0), max(0.1, lane_len - 0.5))
                fh.write(f'    <inductionLoop id={quoteattr(f"{m["id"]}_{i}")} lane="{m["edge"]}_{i}" '
                         f'pos="{pos:.1f}" period="{SENSOR_PERIOD}" file="NUL"/>\n')
        fh.write("</additional>\n")


sumolib_lane_len = {}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Map TD detectors to SUMO network")
    ap.add_argument("--net", default=str(NET_FILE), help="SUMO network file")
    ap.add_argument("--output-detectors", default=str(SCEN / "detectors.add.xml"), help="Output detectors XML file")
    ap.add_argument("--output-map", default=str(SCEN / "detector_map.json"), help="Output detector map JSON file")
    args = ap.parse_args(argv)

    net = sumolib.net.readNet(args.net)
    lane_lens = {}
    for e in net.getEdges():
        for ln in e.getLanes():
            lane_lens[(e.getID(), ln.getIndex())] = ln.getLength()
            sumolib_lane_len[(e.getID(), ln.getIndex())] = ln.getLength()
    mapped, unmapped = map_all(net)
    write_additional(mapped, args.output_detectors, lane_lens)
    with open(args.output_map, "w", encoding="utf-8") as fh:
        json.dump({"mapped": mapped, "unmapped": unmapped}, fh, indent=1, ensure_ascii=False)
    print(f"mapped {len(mapped)} / {len(mapped) + len(unmapped)} detectors")
    for u in unmapped:
        print("  unmapped:", u["id"], u["road"], u["bound"])


if __name__ == "__main__":
    main()
