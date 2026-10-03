"""Build Proxy and Twin demand from recorded TD counts.

Proxy and Twin get INDEPENDENT latent demand: different candidate route sets (randomTrips seed),
different routeSampler seeds, per-edge count perturbation for the Proxy only, different vehicle-type
distributions, and (at run time) dynamic rerouting only in the Proxy.

Twin demand is a candidate stream sampled at TWIN_CAND_SCALE x the counts; at run time each candidate
carries a uniform u and is inserted iff u < m / TWIN_CAND_SCALE (Poisson-thinning CRN, report2 §G.1).
"""
import argparse
import csv
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np

from citypulse.config import HK_DIR, NET_FILE, RESULTS, SCEN, sumo_home

TWIN_CAND_SCALE = 1.5


def detector_counts(day: str, h0: int, h1: int):
    """Mean per-detector flow (veh/h, all valid lanes) over [h0, h1) local time."""
    f = HK_DIR / "raw" / "archive" / f"{day}.csv"
    vol = defaultdict(float)
    periods = defaultdict(set)
    with open(f, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            hh = int(r["period_from"][:2])
            if not (h0 <= hh < h1) or r["valid"] != "Y" or not r["volume"]:
                continue
            vol[r["detector_id"]] += float(r["volume"])
            periods[r["detector_id"]].add(r["period_from"])
    # each period is 30 s
    return {d: vol[d] / (len(periods[d]) * 30.0) * 3600.0 for d in vol if periods[d]}, \
           {d: len(p) for d, p in periods.items()}


def edge_counts(det_flow):
    m = json.load(open(SCEN / "detector_map.json", encoding="utf-8"))["mapped"]
    by_edge = defaultdict(list)
    for d in m:
        if d["id"] in det_flow:
            by_edge[d["edge"]].append(det_flow[d["id"]])
    return {e: float(np.mean(v)) for e, v in by_edge.items()}


def write_edgedata(counts, path, duration):
    root = ET.Element("data")
    iv = ET.SubElement(root, "interval", begin="0", end=str(duration))
    for e, c in sorted(counts.items()):
        ET.SubElement(iv, "edge", id=e, entered=str(int(round(c * duration / 3600.0))))
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def tool(name):
    return str(Path(sumo_home()) / "tools" / name)


def candidate_routes(seed, path, duration):
    cmd = [sys.executable, tool("randomTrips.py"), "-n", str(NET_FILE), "-r", str(path),
           "-o", str(path.with_suffix(".trips.xml")), "-e", str(duration), "-p", "0.25",
           "--fringe-factor", "20", "--min-distance", "800", "--seed", str(seed), "--validate"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def route_sample(cand, edgedata, out, seed, prefix, vtype, log):
    cmd = [sys.executable, tool("routeSampler.py"), "-r", str(cand), "-d", str(edgedata), "-o", str(out),
           "--seed", str(seed), "--prefix", prefix, "--attributes", f'type="{vtype}" departLane="best" departSpeed="max"']
    with open(log, "w") as fh:
        subprocess.run(cmd, check=True, stdout=fh, stderr=subprocess.STDOUT)


def write_vtypes():
    """Proxy: IDM with sampled per-type parameters and a bus/truck share. Twin: Krauss, 2 classes."""
    rng = np.random.default_rng(7)
    p = ['<additional>', '  <vTypeDistribution id="pdist">']
    for k in range(12):
        tau, mingap = np.clip(rng.normal(1.2, 0.3), 0.6, 2.0), np.clip(rng.normal(2.0, 0.5), 1.0, 3.5)
        acc, dec = np.clip(rng.normal(2.2, 0.4), 1.2, 3.2), np.clip(rng.normal(4.0, 0.6), 2.8, 5.5)
        p.append(f'    <vType id="p_car{k}" vClass="passenger" carFollowModel="IDM" tau="{tau:.2f}" minGap="{mingap:.2f}" '
                 f'accel="{acc:.2f}" decel="{dec:.2f}" delta="4" lcAssertive="1.5" lcSpeedGain="1.5" '
                 f'speedFactor="normc(1.05,0.1,0.8,1.3)" probability="{0.85 / 12:.4f}"/>')
    p.append('    <vType id="p_bus" vClass="bus" carFollowModel="IDM" tau="1.5" minGap="2.5" accel="1.2" decel="3.5" '
             'length="12" lcAssertive="1.0" speedFactor="normc(0.95,0.05,0.8,1.1)" probability="0.07"/>')
    p.append('    <vType id="p_truck" vClass="truck" carFollowModel="IDM" tau="1.6" minGap="2.5" accel="1.0" decel="3.5" '
             'length="10" lcAssertive="1.0" speedFactor="normc(0.9,0.05,0.7,1.0)" probability="0.08"/>')
    p += ['  </vTypeDistribution>', '</additional>']
    (SCEN / "vtypes_proxy.add.xml").write_text("\n".join(p) + "\n", encoding="utf-8")
    t = ['<additional>', '  <vTypeDistribution id="tdist">',
         '    <vType id="t_car" vClass="passenger" carFollowModel="Krauss" sigma="0.5" tau="1.0" minGap="2.5" '
         'accel="2.6" decel="4.5" probability="0.9"/>',
         '    <vType id="t_truck" vClass="truck" carFollowModel="Krauss" sigma="0.5" tau="1.0" minGap="2.5" '
         'accel="1.3" decel="4.0" length="9" probability="0.1"/>',
         '  </vTypeDistribution>', '</additional>']
    (SCEN / "vtypes_twin.add.xml").write_text("\n".join(t) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="2026-09-29")
    ap.add_argument("--h0", type=int, default=8)
    ap.add_argument("--h1", type=int, default=9)
    ap.add_argument("--proxy-noise", type=float, default=0.10, help="lognormal sigma on Proxy edge counts")
    ap.add_argument("--scale", type=float, default=1.0, help="global demand scale (provisional, see docs)")
    a = ap.parse_args()
    duration = (a.h1 - a.h0) * 3600
    det_flow, n_per = detector_counts(a.day, a.h0, a.h1)
    counts = {e: c * a.scale for e, c in edge_counts(det_flow).items()}
    info = {"day": a.day, "window": [a.h0, a.h1], "scale": a.scale, "detectors_with_data": len(det_flow),
            "edges_with_counts": len(counts), "periods_per_detector_min": min(n_per.values()) if n_per else 0,
            "periods_per_detector_max": max(n_per.values()) if n_per else 0}
    rng = np.random.default_rng(101)
    proxy_counts = {e: c * float(rng.lognormal(0.0, a.proxy_noise)) for e, c in counts.items()}
    twin_counts = {e: c * TWIN_CAND_SCALE for e, c in counts.items()}
    write_edgedata(proxy_counts, SCEN / "counts_proxy.xml", duration)
    write_edgedata(twin_counts, SCEN / "counts_twin_cand.xml", duration)
    write_vtypes()
    candidate_routes(11, SCEN / "cand_proxy.rou.xml", duration)
    candidate_routes(22, SCEN / "cand_twin.rou.xml", duration)
    route_sample(SCEN / "cand_proxy.rou.xml", SCEN / "counts_proxy.xml", SCEN / "proxy.rou.xml", 1001, "p", "pdist",
                 RESULTS / "routesampler_proxy.log")
    route_sample(SCEN / "cand_twin.rou.xml", SCEN / "counts_twin_cand.xml", SCEN / "twin_cand.rou.xml", 2002, "t",
                 "tdist", RESULTS / "routesampler_twin.log")
    import hashlib
    info["input_sha256"] = {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                            (NET_FILE, SCEN / "detector_map.json", HK_DIR / "raw" / "archive" / f"{a.day}.csv")}
    json.dump({**info, "edge_counts_vph": counts}, open(SCEN / "demand_info.json", "w"), indent=1)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
