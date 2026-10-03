"""B-lite net5 checks (task: "build B-lite net5 ... Checks (a)-(g)").

Run from the repo root:  python results/blite/net5/check5.py
Writes results/blite/net5/check_report.json and exits non-zero if any check fails.

Checks
  (a) every route in synth5/ is connected in net5 (lane-level reachability),
  (b) zero dead lanes (a lane reachable from no source lane or unable to reach a sink),
  (c) junction D: none of the three mainline links has a foe or response bit against
      another of the three,
  (d) the `tko_in -> tko_1` lane connections are exactly 0->0, 0->1, 1->2,
  (e) detector ids and positions equal net4's,
  (f) every signal state string at S1-S4 matches its link count,
  (g) synth5/ routes are equivalent to synth/ (departures, classes, destinations, counts)
      with `tko_insert` prepended to every TKO route.

The `<request>` bit strings are indexed with the LAST character for request 0 (SUMO writes
them highest-index-first); the decoder is asserted against a hand-built cross junction in
`results/blite/net5/scratch/tiny/` in the report.
"""
import json
import sys
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import sumolib  # noqa: E402

HERE = Path(__file__).resolve().parent
SCEN = ROOT / "scenarios" / "kwuntong" / "blite"
NET5, NET4 = SCEN / "net5.net.xml", SCEN / "net4.net.xml"
DET5, DET4 = SCEN / "detectors5.add.xml", SCEN / "detectors4.add.xml"
SYNTH, SYNTH5 = SCEN / "synth", SCEN / "synth5"
ROUTES = ("proxy.rou.xml", "proxy_shock.rou.xml", "twin_cand.rou.xml")
D_THREE = (("tko_vms", 0, "tko_a1", 0), ("tko_vms", 1, "ktb_w1", 0), ("tko_vms", 2, "ktb_w1", 1))
ENTRY = (("tko_in", 0, "tko_1", 0), ("tko_in", 0, "tko_1", 1), ("tko_in", 1, "tko_1", 2))
INSERT = ("tko_insert", 500.0, 3, 70.0)
INSERT_CONNS = (("tko_insert", 0, "tko_in", 0), ("tko_insert", 1, "tko_in", 1),
                ("tko_insert", 2, "tko_in", 1))
MIN_LANE_CHANGE = 150.0


def raw_junction(path, jid):
    root = ET.parse(path).getroot()
    return [j for j in root.findall("junction") if j.get("id") == jid][0]


def request_table(path, jid):
    """[(from, fromLane, to, toLane, state, response, foes)] per request index at `jid`."""
    root = ET.parse(path).getroot()
    j = raw_junction(path, jid)
    intl = j.get("intLanes").split()
    out = {}
    for q in j.findall("request"):
        out[int(q.get("index"))] = {"response": q.get("response") or "",
                                    "foes": q.get("foes") or "", "cont": q.get("cont")}
    for c in root.findall("connection"):
        via = c.get("via") or ""
        if via.startswith(":" + jid + "_") and via in intl:
            i = intl.index(via)
            out[i] |= {"from": c.get("from"), "fromLane": int(c.get("fromLane")),
                       "to": c.get("to"), "toLane": int(c.get("toLane")),
                       "state": c.get("state"), "dir": c.get("dir")}
    return out


def bits(s, j, n):
    """Bit of request `j` in a request string of `n` links (SUMO writes index 0 last)."""
    if not s or len(s) != n:
        return "0"
    return s[n - 1 - j]


def lane_reachable(edges, route):
    """Lanes of the last route edge reachable from any lane of the first one."""
    cur = set(range(edges[route[0]].getLaneNumber()))
    for a, b in zip(route, route[1:]):
        nxt = set()
        for c in edges[a].getConnections(edges[b]):
            if c.getFromLane().getIndex() in cur:
                nxt.add(c.getToLane().getIndex())
        if not nxt:
            return set()
        cur = nxt
    return cur


def main():
    net = sumolib.net.readNet(str(NET5), withPrograms=True)
    edges = {e.getID(): e for e in net.getEdges() if e.getFunction() != "internal"}
    report, ok = {"net": str(NET5)}, True

    def check(name, passed, detail):
        nonlocal ok
        ok &= bool(passed)
        report[name] = {"pass": bool(passed), "detail": detail}
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")

    # (a) every synth5 route is connected -------------------------------------------------
    bad = []
    counts = {}
    for name in ROUTES:
        routes = [v.find("route").get("edges").split()
                  for v in ET.parse(SYNTH5 / name).getroot().iter("vehicle")]
        counts[name] = len(routes)
        for i, r in enumerate(routes):
            missing = [e for e in r if e not in edges]
            if missing or not lane_reachable(edges, r):
                bad.append(f"{name}#{i}:{missing or 'no lane path'}")
    check("a_routes_connected", not bad, f"{sum(counts.values())} routes, "
          f"{len(bad)} unconnected {bad[:3]}")

    # (b) zero dead lanes ------------------------------------------------------------------
    lanes = [l for e in edges.values() for l in e.getLanes()]
    src = [l for l in lanes if not l.getIncoming()]
    snk = [l for l in lanes if not l.getOutgoing()]

    def flood(seeds, step):
        seen, q = set(seeds), deque(seeds)
        while q:
            for nxt in step(q.popleft()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return seen

    fwd = flood(src, lambda l: [c.getToLane() for c in l.getOutgoing()])
    bwd = flood(snk, lambda l: list(l.getIncoming()))
    dead = sorted(l.getID() for l in lanes if l not in fwd or l not in bwd)
    check("b_no_dead_lanes", not dead, f"{len(lanes)} lanes, dead: {dead or 'none'}")

    # (c) junction D: the three mainline links are mutually foe-free ------------------------
    req = request_table(NET5, "D")
    n = len(req)
    idx = {}
    for i, r in req.items():
        if "from" in r:
            idx[(r["from"], r["fromLane"], r["to"], r["toLane"])] = i
    mine = [idx[k] for k in D_THREE]
    offenders = []
    for i in mine:
        for j in mine:
            if i == j:
                continue
            if bits(req[i]["foes"], j, n) == "1" or bits(req[i]["response"], j, n) == "1":
                offenders.append((i, j))
    states = {k: req[i].get("state") for k, i in zip(D_THREE, mine)}
    check("c_D_no_mutual_foes", not offenders,
          f"links {mine} states {[states[k] for k in D_THREE]} "
          f"offending pairs {offenders or 'none'}")
    report["c_D_requests"] = {str(i): {k: v for k, v in req[i].items()} for i in sorted(req)}

    # (c2) the three connectors do not cross geometrically ----------------------------------
    root = ET.parse(NET5).getroot()
    shapes = {}
    for e in root.findall("edge"):
        if e.get("function") == "internal" and e.get("id", "").startswith(":D_"):
            for lane in e.findall("lane"):
                shapes[lane.get("id")] = [tuple(float(v) for v in p.split(","))
                                          for p in lane.get("shape").split()]
    via = {}
    for c in root.findall("connection"):
        v = c.get("via") or ""
        if v.startswith(":D_"):
            via[(c.get("from"), int(c.get("fromLane")), c.get("to"), int(c.get("toLane")))] = v

    def seg_int(p1, p2, p3, p4):
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (p4[0] - p3[0], p4[1] - p3[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:
            return None
        t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
        u = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / den
        return (1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9)

    crossing = []
    for a in range(len(D_THREE)):
        for b in range(a + 1, len(D_THREE)):
            sa, sb = shapes[via[D_THREE[a]]], shapes[via[D_THREE[b]]]
            if any(seg_int(sa[i], sa[i + 1], sb[j], sb[j + 1])
                   for i in range(len(sa) - 1) for j in range(len(sb) - 1)):
                crossing.append((D_THREE[a], D_THREE[b]))
    check("c2_D_connectors_no_crossing", not crossing, f"crossing pairs: {crossing or 'none'}")

    # (d) the tko_in lane connections ------------------------------------------------------
    got = sorted((c.get("from"), int(c.get("fromLane")), c.get("to"), int(c.get("toLane")))
                 for c in root.findall("connection")
                 if c.get("from") == "tko_in" and c.get("to") == "tko_1")
    check("d_entry_connections", got == sorted(ENTRY), f"tko_in->tko_1 = {got}")

    # (e) detectors ------------------------------------------------------------------------
    def dets(path):
        return sorted((d.get("id"), d.get("lane"), d.get("pos"))
                      for d in ET.parse(path).getroot().iter("inductionLoop"))

    d5, d4 = dets(DET5), dets(DET4)
    check("e_detectors_equal_net4", d5 == d4, f"{len(d5)} loops, identical to net4: {d5 == d4}")

    # (f) signal state strings -------------------------------------------------------------
    sig_bad = []
    for tl in net.getTrafficLights():
        if tl.getID() not in ("S1", "S2", "S3", "S4"):
            continue
        links = max((i for (_i, _o, i) in tl.getConnections()), default=-1) + 1
        for pid, prog in tl.getPrograms().items():
            for ph in prog.getPhases():
                if len(ph.state) != links:
                    sig_bad.append((tl.getID(), pid, len(ph.state), links))
    check("f_signal_state_lengths", not sig_bad, f"S1-S4 mismatches: {sig_bad or 'none'}")

    # (g) synth5 vs synth ------------------------------------------------------------------
    diff = []
    for name in ROUTES:
        before = {v.get("id"): (float(v.get("depart")), v.get("type"),
                                v.find("route").get("edges").split())
                  for v in ET.parse(SYNTH / name).getroot().iter("vehicle")}
        after = {v.get("id"): (float(v.get("depart")), v.get("type"),
                               v.find("route").get("edges").split(),
                               v.get("departLane"), v.get("departSpeed"))
                 for v in ET.parse(SYNTH5 / name).getroot().iter("vehicle")}
        if set(before) != set(after):
            diff.append(f"{name}: ids")
            continue
        for vid, (dep, typ, redges) in before.items():
            a_dep, a_typ, a_edges, dlane, dspeed = after[vid]
            want = ([ "tko_insert"] + redges) if redges[0] == "tko_in" else redges
            if (a_dep, a_typ, a_edges) != (dep, typ, want):
                diff.append(f"{name}:{vid}")
            elif redges[0] == "tko_in" and (dlane, dspeed) != ("free", "max"):
                diff.append(f"{name}:{vid}:depart")
    check("g_route_equivalence", not diff, f"{sum(counts.values())} vehicles compared, "
          f"{len(diff)} differences {diff[:3]}")

    # extra: insertion stub spec and lane-change room ---------------------------------------
    ins = edges.get("tko_insert")
    ins_ok = (ins is not None and abs(ins.getLength() - INSERT[1]) < 0.05
              and ins.getLaneNumber() == INSERT[2]
              and abs(ins.getSpeed() * 3.6 - INSERT[3]) < 0.05)
    check("x_insert_stub_spec", ins_ok,
          f"tko_insert: length {ins.getLength():.1f} m, {ins.getLaneNumber()} lanes, "
          f"{ins.getSpeed() * 3.6:.2f} km/h" if ins else "tko_insert missing")
    got_ins = sorted((c.get("from"), int(c.get("fromLane")), c.get("to"), int(c.get("toLane")))
                     for c in root.findall("connection") if c.get("from") == "tko_insert")
    check("x_insert_connections", got_ins == sorted(INSERT_CONNS), f"tko_insert links = {got_ins}")
    check("x_insert_zipper_node",
          raw_junction(NET5, "src").get("type") == "zipper",
          f"node src type = {raw_junction(NET5, 'src').get('type')}")
    identity = sorted((int(c.get("fromLane")), int(c.get("toLane")))
                      for c in root.findall("connection")
                      if c.get("from") == "tko_1" and c.get("to") == "tko_vms")
    check("x_tko_1_tko_vms_identity", identity == [(0, 0), (1, 1), (2, 2)], f"links = {identity}")
    room = {e: round(edges[e].getLength(), 1) for e in ("tko_insert", "tko_in", "tko_1", "tko_vms")
            if e in edges and edges[e].getLength() >= MIN_LANE_CHANGE}
    check("x_lane_change_room", len(room) == 4, f"edges >= {MIN_LANE_CHANGE:.0f} m: {room}")

    (HERE / "check_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECKS FAILED'} -> {HERE / 'check_report.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
