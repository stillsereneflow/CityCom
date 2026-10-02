"""Step 1 diagnostics: run the Proxy alone and locate entry backlog and internal jams.

Outputs results/net_diag_<tag>.json:
  totals (inserted, arrived, running, pending, teleports), per-source demand vs inserted,
  per-edge waiting time over time (first jam onset), detector flow fit vs HK counts (GEH).
"""
import argparse
import json
import math
import hashlib
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import sumolib
import traci

from citypulse.config import NET_FILE, RESULTS, SCEN
from citypulse.sim import detector_loops, init_signals, proxy_cmd

SAMPLE = 60


def route_sources(routes):
    src = Counter()
    for v in ET.parse(routes).getroot().iter("vehicle"):
        r = v.find("route")
        if r is not None:
            src[r.get("edges").split()[0]] += 1
    return src


def geh(m, c):
    return math.sqrt(2 * (m - c) ** 2 / (m + c)) if m + c > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="diag")
    ap.add_argument("--t-end", type=int, default=3600)
    ap.add_argument("--routes", default=str(SCEN / "proxy.rou.xml"))
    ap.add_argument("--extra", default="", help="extra SUMO options as one string")
    ap.add_argument("--scenario", type=Path, default=SCEN)
    ap.add_argument("--libsumo", action="store_true")
    a = ap.parse_args()
    scenario = a.scenario.resolve()
    net_path = scenario / "net.net.xml"
    info = json.load(open(scenario / "demand_info.json"))
    m = json.load(open(scenario / "detector_map.json", encoding="utf-8"))["mapped"]
    net = sumolib.net.readNet(str(net_path))
    demand_src = route_sources(a.routes)
    cmd = proxy_cmd(1, a.routes, a.extra.split())
    cmd[cmd.index("-n") + 1] = str(net_path)
    cmd[cmd.index("-a") + 1] = ",".join(str(scenario / f) for f in
        ("vtypes_proxy.add.xml", "detectors.add.xml", "tls_incident.add.xml"))
    fingerprints = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (net_path, Path(a.routes), scenario / "demand_info.json", scenario / "detector_map.json")}
    if a.libsumo:
        import libsumo as tc
        tc.start(cmd)
    else:
        traci.start(cmd, label="diag")
        tc = traci.getConnection("diag")
    init_signals(tc)
    loops = {d["id"]: [f"{d['id']}_{i}" for i in range(d["n_lanes"])] for d in m}
    inserted_src = Counter()
    det_count = defaultdict(int)
    wait_hist = defaultdict(list)   # edge -> [(t, halting)]
    teleports = 0
    arrived = 0
    history, detector_intervals = [], []
    for k in range(1, a.t_end + 1):
        tc.simulationStep()
        for v in tc.simulation.getDepartedIDList():
            inserted_src[tc.vehicle.getRoute(v)[0]] += 1
        teleports += tc.simulation.getStartingTeleportNumber()
        arrived += tc.simulation.getArrivedNumber()
        if k % 30 == 0:
            counts = {aid: sum(tc.inductionloop.getLastIntervalVehicleNumber(lid) for lid in ids)
                      for aid, ids in loops.items()}
            for aid, count in counts.items():
                det_count[aid] += count
            detector_intervals.append({"end": k, "counts": counts})
        if k % SAMPLE == 0:
            history.append({"time": k, "running": tc.vehicle.getIDCount(),
                            "pending": len(tc.simulation.getPendingVehicles()),
                            "inserted": sum(inserted_src.values()), "arrived": arrived})
            for e in net.getEdges():
                h = tc.edge.getLastStepHaltingNumber(e.getID())
                if h:
                    wait_hist[e.getID()].append((k, h))
    pending = Counter()
    for v in tc.simulation.getPendingVehicles():
        try:
            pending[tc.vehicle.getRoute(v)[0]] += 1
        except traci.TraCIException:
            pending["?"] += 1
    totals = {"inserted": sum(inserted_src.values()), "loaded": sum(demand_src.values()),
              "arrived_total": arrived, "running_end": tc.vehicle.getIDCount(),
              "pending_end": len(tc.simulation.getPendingVehicles()), "teleports": teleports}
    tc.close()
    # sources
    srcs = []
    for e, n in demand_src.most_common():
        E = net.getEdge(e)
        srcs.append({"edge": e, "name": (E.getName() or "")[-30:], "type": E.getType(), "lanes": E.getLaneNumber(),
                     "length": round(E.getLength(), 1), "demand_vph": n * 3600 / a.t_end,
                     "inserted_vph": inserted_src[e] * 3600 / a.t_end, "pending_end": pending[e]})
    # jams: edges with sustained halting, ordered by first time halting >= 10
    jams = []
    for e, h in wait_hist.items():
        onset = next((t for t, x in h if x >= 10), None)
        if onset is not None:
            E = net.getEdge(e)
            jams.append({"edge": e, "name": (E.getName() or "")[-30:], "type": E.getType(),
                         "lanes": E.getLaneNumber(), "to_node": E.getToNode().getID(),
                         "to_type": E.getToNode().getType(), "onset_s": onset, "max_halting": max(x for _, x in h)})
    jams.sort(key=lambda j: j["onset_s"])
    # GEH vs HK targets (edge counts used by routeSampler, scaled)
    by_edge = defaultdict(list)
    for d in m:
        by_edge[d["edge"]].append(det_count[d["id"]] * 3600 / a.t_end)
    fit = []
    for e, target in info["edge_counts_vph"].items():
        if e in by_edge:
            sim = sum(by_edge[e]) / len(by_edge[e])
            fit.append({"edge": e, "target_vph": target, "sim_vph": sim,
                        "geh": geh(sim, target)})
    geh_ok = sum(f["geh"] < 5 for f in fit) / max(len(fit), 1)
    last = [h for h in history if h["time"] >= a.t_end - 900]
    import numpy as np
    slope = float(np.polyfit([h["time"] for h in last], [h["running"] for h in last], 1)[0])
    out = {"tag": a.tag, "scale": info["scale"], "totals": totals, "geh_lt5_share": geh_ok,
           "sources": srcs, "jams": jams[:40], "fit": fit, "history": history,
           "running_last15_slope_vps": slope, "running_last15_delta": last[-1]["running"] - last[0]["running"],
           "detector_intervals": detector_intervals, "input_sha256": fingerprints,
           "command": cmd, "count_method": "completed 30s E1 intervals", "mapped_detectors": len(m)}
    json.dump(out, open(RESULTS / f"net_diag_{a.tag}.json", "w"), indent=1)
    print(json.dumps({"totals": totals, "geh_lt5_share": round(geh_ok, 3), "n_jam_edges": len(jams)}))
    print("top backlog sources:")
    for s in sorted(srcs, key=lambda s: -s["pending_end"])[:10]:
        print("  ", s)
    print("first jams:")
    for j in jams[:12]:
        print("  ", j)


if __name__ == "__main__":
    main()
