"""Local, non-destructive step-1 consultation: audit inputs and build boundary routes.

Run with PYTHONDONTWRITEBYTECODE=1. Outputs only results/astra_step1/.
Boundary means no incoming/outgoing passenger connection in this cut network;
it is a diagnostic restriction, not evidence that every stub is a real OD gate.
"""
import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date

import numpy as np
import sumolib

from citypulse.config import HK_DIR, RESULTS, SCEN
from citypulse.demand.make_demand import detector_counts, edge_counts
from citypulse.experiments.net_diag import geh
from citypulse.network.patch_network import core_edges

OUT = RESULTS / "astra_step1"


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def routes(path):
    return [tuple(r.get("edges").split()) for r in ET.parse(path).iter("route")]


def connected(edge, incoming):
    links = edge.getIncoming() if incoming else edge.getOutgoing()
    return [e for e, cs in links.items() if any(
        c.getFromLane().allows("passenger") and c.getToLane().allows("passenger") for c in cs)]


def route_stats(net, path, targets, core):
    rr = routes(path)
    usage = Counter(e for r in rr for e in r)
    lengths = [sum(net.getEdge(e).getLength() for e in r) for r in rr]
    counts = set(targets)
    total_km = sum(lengths) / 1000
    counted_km = sum(net.getEdge(e).getLength() * n for e, n in usage.items() if e in counts) / 1000
    uturns = sum(any(c.getDirection() == "t" for a, b in zip(r, r[1:])
                     for c in net.getEdge(a).getOutgoing().get(net.getEdge(b), [])) for r in rr)
    fit = [{"edge": e, "route_count": usage[e], "target": t, "geh": geh(usage[e], t)}
           for e, t in targets.items()]
    return {"n": len(rr), "unique": len(set(rr)), "km_mean": float(np.mean(lengths) / 1000),
            "km_quantiles_0_25_50_75_95_100": (np.percentile(lengths, [0, 25, 50, 75, 95, 100]) / 1000).tolist(),
            "total_vehicle_km": total_km, "counted_vehicle_km": counted_km,
            "uncounted_vehicle_km": total_km - counted_km,
            "uses_noncore_share": sum(any(e not in core for e in r) for r in rr) / len(rr),
            "starts_noncore_share": sum(r[0] not in core for r in rr) / len(rr),
            "nonboundary_start_share": sum(bool(connected(net.getEdge(r[0]), True)) for r in rr) / len(rr),
            "both_boundary_share": sum(not connected(net.getEdge(r[0]), True)
                                       and not connected(net.getEdge(r[-1]), False) for r in rr) / len(rr),
            "direct_uturn_share": uturns / len(rr),
            "repeated_edge_share": sum(len(set(r)) < len(r) for r in rr) / len(rr),
            "fit": fit, "route_geh_lt5_share": sum(f["geh"] < 5 for f in fit) / len(fit)}


def td_audit(mapped):
    output = []
    for path in sorted((HK_DIR / "raw" / "archive").glob("2026-09-*.csv")):
        if not ("2026-09-21" <= path.stem <= "2026-09-30") or date.fromisoformat(path.stem).weekday() > 4:
            continue
        lanes, periods, reasons = defaultdict(set), defaultdict(dict), Counter()
        seen = set()
        for r in csv.DictReader(path.open(encoding="utf-8")):
            aid = r["detector_id"]
            if aid not in mapped:
                continue
            lanes[aid].add(r["lane_id"])
            if not ("08:00:00" <= r["period_from"] < "09:00:00"):
                continue
            reasons["rows"] += 1
            key = (aid, r["period_from"], r["lane_id"])
            if key in seen:
                reasons["duplicate"] += 1
                continue
            seen.add(key)
            if r["valid"] != "Y":
                reasons["invalid"] += 1
                continue
            if any(not r[k] for k in ("speed", "occupancy", "volume")):
                reasons["missing_field"] += 1
                continue
            values = tuple(float(r[k]) for k in ("speed", "occupancy", "volume"))
            if any(v < 0 or not np.isfinite(v) for v in values) or values[1] > 100:
                reasons["out_of_range"] += 1
                continue
            periods[aid].setdefault(r["period_from"], {})[r["lane_id"]] = values
            reasons["valid_unique_rows"] += 1
        for aid, meta in mapped.items():
            good = [(t, list(v.values())) for t, v in periods[aid].items() if set(v) == lanes[aid]]
            # Complete-lane periods only; retain zero-flow periods for occupancy and rate.
            samples = []
            for t, vals in good:
                q = sum(x[2] for x in vals)
                speed = sum(x[0] * x[2] for x in vals) / q if q else None
                samples.append({"period_from": t, "q": q, "v": speed, "o": float(np.mean([x[1] for x in vals]))})
            positive = [x for x in samples if x["q"] > 0]
            vol = sum(x["q"] for x in samples)
            grid = {f"v<{v},o>{o}": sum(x["v"] < v and x["o"] > o for x in positive)
                    for v in (20, 30, 40) for o in (10, 20, 30)}
            output.append({"day": path.stem, "id": aid, "edge": meta["edge"],
                           "road": meta["road"], "bound": meta["bound"],
                           "expected_lanes": len(lanes[aid]), "periods_any_valid": len(periods[aid]),
                           "complete_periods": len(good), "missing_or_invalid_periods": 120 - len(periods[aid]),
                           "partial_periods_dropped": len(periods[aid]) - len(good),
                           "zero_flow_periods": len(samples) - len(positive),
                           "flow_vph": vol * 120 / len(good) if good else None,
                           "speed_kmh": sum(x["v"] * x["q"] for x in positive) / vol if vol else None,
                           "occupancy_pct": float(np.mean([x["o"] for x in samples])) if samples else None,
                           "congestion_grid_counts": grid, "samples": samples})
        save(f"td_quality_{path.stem}.json", dict(reasons))
    save("td_detectors.json", output)
    save("td_summary.json", [{k: v for k, v in r.items() if k != "samples"} for r in output])


def prepare(net, targets, core):
    incoming = [e for e in net.getEdges() if e.allows("passenger") and not connected(e, True)]
    outgoing = [e for e in net.getEdges() if e.allows("passenger") and not connected(e, False)]
    root = ET.Element("routes")
    rejected = Counter()
    accepted = set()
    for a in incoming:
        for b in outgoing:
            if a == b:
                rejected["same_edge"] += 1
                continue
            p, _ = net.getFastestPath(a, b, vClass="passenger")
            if not p:
                rejected["unreachable"] += 1
                continue
            r = tuple(e.getID() for e in p)
            if not set(r).intersection(targets):
                rejected["no_counted_edge"] += 1
                continue
            accepted.add(r)
    for k, r in enumerate(sorted(accepted)):
        ET.SubElement(root, "route", id=f"b{k}", edges=" ".join(r))
    ET.ElementTree(root).write(OUT / "boundary_candidates.rou.xml", encoding="utf-8", xml_declaration=True)
    covered = set(e for r in accepted for e in r)
    save("boundary_generation.json", {"entries": [e.getID() for e in incoming],
         "exits": [e.getID() for e in outgoing], "pairs": len(incoming) * len(outgoing),
         "rejected": dict(rejected), "accepted": len(accepted),
         "uncovered_targets": sorted(set(targets) - covered)})
    mapped = {d["id"]: d for d in json.loads((SCEN / "detector_map.json").read_text(encoding="utf-8"))["mapped"]}
    td_audit(mapped)
    fresh, nperiod = detector_counts("2026-09-29", 8, 9)
    fresh_edges = edge_counts(fresh)
    save("target_audit.json", {"periods_current": nperiod,
         "unmapped_old_targets": sorted(set(targets) - {d["edge"] for d in mapped.values()}),
         "fresh_edge_targets": fresh_edges,
         "existing": targets})
    inputs = list(SCEN.iterdir()) + list((HK_DIR / "raw" / "archive").glob("*.csv"))
    inputs += [RESULTS / "net_diag_g100.json", RESULTS / "net_diag_w100b.json"]
    if not (OUT / "input_sha256.json").exists():
        save("input_sha256.json", {str(p.relative_to(SCEN.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in inputs if p.is_file()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--routes", nargs="*", default=[])
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    net = sumolib.net.readNet(str(SCEN / "net.net.xml"))
    targets = json.loads((SCEN / "demand_info.json").read_text())["edge_counts_vph"]
    core = core_edges(net)
    if a.prepare:
        prepare(net, targets, core)
    for route in a.routes:
        from pathlib import Path
        path = Path(route)
        stats = route_stats(net, path, targets, core)
        save(path.stem + "_stats.json", stats)
        print(path.name, json.dumps({k: v for k, v in stats.items() if k != "fit"}))


if __name__ == "__main__":
    main()
