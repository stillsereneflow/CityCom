"""Step 1 diagnostics: run the Proxy alone and locate entry backlog and internal jams.

Outputs results/net_diag_<tag>.json:
  totals (inserted, arrived, running, pending, teleports), per-source demand vs inserted,
  per-edge waiting time over time (first jam onset), detector flow fit vs HK counts (GEH).
"""
import argparse
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

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
    a = ap.parse_args()
    net = sumolib.net.readNet(str(NET_FILE))
    demand_src = route_sources(a.routes)
    traci.start(proxy_cmd(1, a.routes, a.extra.split()), label="diag")
    tc = traci.getConnection("diag")
    init_signals(tc)
    loops = detector_loops()
    inserted_src = Counter()
    det_count = defaultdict(int)
    wait_hist = defaultdict(list)   # edge -> [(t, halting)]
    teleports = 0
    for k in range(1, a.t_end + 1):
        tc.simulationStep()
        for v in tc.simulation.getDepartedIDList():
            inserted_src[tc.vehicle.getRoute(v)[0]] += 1
        teleports += tc.simulation.getStartingTeleportNumber()
        for aid, ids in loops.items():
            for lid in ids:
                det_count[aid] += tc.inductionloop.getLastStepVehicleNumber(lid)
        if k % SAMPLE == 0:
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
              "arrived_total": tc.simulation.getArrivedNumber(), "running_end": tc.vehicle.getIDCount(),
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
    info = json.load(open(SCEN / "demand_info.json"))
    m = json.load(open(SCEN / "detector_map.json", encoding="utf-8"))["mapped"]
    by_edge = defaultdict(list)
    for d in m:
        by_edge[d["edge"]].append(det_count[d["id"]] * 3600 / a.t_end)
    fit = []
    for e, target in info["edge_counts_vph"].items():
        if e in by_edge:
            sim = sum(by_edge[e]) / len(by_edge[e])
            fit.append({"edge": e, "target_vph": target * info["scale"], "sim_vph": sim,
                        "geh": geh(sim, target * info["scale"])})
    geh_ok = sum(f["geh"] < 5 for f in fit) / max(len(fit), 1)
    out = {"tag": a.tag, "scale": info["scale"], "totals": totals, "geh_lt5_share": geh_ok,
           "sources": srcs, "jams": jams[:40], "fit": fit}
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
