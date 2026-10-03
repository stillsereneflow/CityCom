"""B-lite generator: curated two-route corridor (simplified research model).

Geometry is grounded in Hong Kong TD data: the node polyline runs through the real detector
lat/lon projected with the v4 network's projection, and every edge length is real chainage
(shortest path on scenarios/kwuntong/net_bounded_v4.net.xml between detector edges/positions).
"Simplified research model, geometry and detectors grounded in Hong Kong data; not a calibrated
replica."  See docs/blite-spec.md.
"""
import argparse
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib

from citypulse.config import sumo_bin
from citypulse.scenario_blite import CONTROL

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "scenarios" / "kwuntong" / "blite"
V4NET = ROOT / "scenarios" / "kwuntong" / "net_bounded_v4.net.xml"
V4MAP = ROOT / "scenarios" / "kwuntong" / "v4" / "detector_map.json"
# (edge id, TD lanes from data/hk/raw/archive/2026-09-29.csv, speed km/h, detectors in route order)
LOWER_SEQ = [("tko_in", 2, 70, ("AID07105",)), ("tko_1", 3, 70, ("AID07106",)),
             ("tko_vms", 3, 70, ()), ("tko_a1", 3, 70, ("AID07107",)),
             ("ktr_w1", 4, 50, ("AID07108",)), ("ktr_w2", 4, 50, ("AID07109",)),
             ("ktr_w3", 2, 50, ("AID07110",)), ("ktr_w4", 3, 50, ("AID07111", "AID07112")),
             ("ktr_w5", 4, 50, ("AID07113",)), ("ktr_w6", 6, 50, ("AID07114",)),
             ("rejoin", 3, 70, ()), ("out", 3, 70, ())]
UPPER_SEQ = [("ktb_w1", 2, 70, ("AID02105",)), ("ktb_w2", 3, 70, ("AID02106", "AID02107")),
             ("ktb_w3", 3, 70, ("AID02108",)),
             ("ktb_n1", 3, 80, ("AID02109", "AID02110", "AID02111")),
             ("ktb_n2", 2, 80, ("AID02112", "AID02113", "AID02114", "AID02115"))]
LOW_NODES = ["src", "j1", "j2", "D", "j3", "S1", "S2", "S3", "S4", "j4", "M", "j5", "sink"]
UP_NODES = ["D", "A1", "A2", "A3", "A4", "M"]
SIGNALS = [("S1", "ktr_w1", "ktr_w2"), ("S2", "ktr_w2", "ktr_w3"),
           ("S3", "ktr_w3", "ktr_w4"), ("S4", "ktr_w4", "ktr_w5")]
TAIL, DUR = {"rejoin": 300.0, "out": 200.0}, (45, 15)
RAMP_ON, RAMP_OFF, XSTUB, XLANES, RAMPSPEED = 300.0, 200.0, 200.0, 2, 50
ENTRY_MIN, ROAD_PRIORITY, RAMP_PRIORITY, LATERAL = 300.0, 2, 1, 14.0
# Design flow of one merge/diverge lane.  A ramp is sized by its peak 15-minute slice volume
# at scale 1.0: lanes = max(1, ceil(peak_vph / MERGE_LANE_FLOW)).  1,500 veh/h per lane is the
# standard merge-lane design flow.  A ramp wider than the lane rise/drop its main edge already
# provides gets a SECTION-metre add-lane section (merge) or diverge section; main edges keep
# their TD lane counts at the detectors.
MERGE_LANE_FLOW, SECTION = 1500.0, 200.0
MERGE_EDGES = ("rejoin", "out")            # detector-free edges at merge M
SECTION_PREFIX = ("ms_on_", "dv_off_")
# Junction M merges the two carriageways lane-preservingly: every lane that arrives at M --
# the 6 arterial lanes of ktr_w6 and the 2 bypass lanes of ktb_n2 -- keeps a lane of its own
# in `rejoin`, so the two approaches share no target lane, there are no foe links between
# them and neither yields.  `rejoin` (and `out`, which must be at least as wide) is
# therefore sized by the incoming lanes, not by the merge volume:
# lanes(ktr_w6) + lanes(ktb_n2) = 6 + 2 = 8.  A grade-separated merge of two carriageways is
# not a point conflict.
MERGE_IN = ("ktr_w6", "ktb_n2")
# The generator's per-junction stub ramps exist for every junction of the sequence, but an
# on-ramp merging at M itself would have to share a `rejoin` lane with one of the two
# carriageways (rejoin is exactly as wide as their inflow), i.e. it would re-create the
# shared target lane / foe link this correction removes, and take a 9th lane that no
# carriageway needs.  `on_rejoin` is demand-free (demand.json has no `on_rejoin` flow), is
# referenced by no detector, route or CONTROL edge, so the M-point stub on-ramp is not built.
# The demand-free off-ramp stubs off_ktr_w6 / off_ktb_n2 are diverges off one edge and stay.
SKIP_RAMPS = ("on_rejoin",)
# Junction M merges the 6-lane arterial ktr_w6 with the 2-lane bypass ktb_n2.  netconvert
# gives the right of way to the higher-priority edge; with both edges at ROAD_PRIORITY all
# six ktr_w6 -> rejoin connections came out minor ('m') and every ktb_n2 -> rejoin
# connection major, i.e. the arterial yielded to the bypass (probe report section 8.1).
# net3 raised the arterial one priority point above the bypass; net4 makes M lane-preserving
# instead (see MERGE_IN), so no approach yields whatever the priorities are.  Kept so the
# built edge priorities stay identical to net3.
MERGE_MAJOR = {"ktr_w6": ROAD_PRIORITY + 1}
# Yellow time carved out of the preceding green at every green -> red transition; the
# cycle length is unchanged (probe report section 8.3).
YELLOW = 3

# ---------------------------------------------------------------------------------------
# net5 (decision 2026-10-03c, docs/decision-2026-10-03c-net5.md): the net4 corridor with
# (1) a repaired entry, (2) a repaired diverge at D and (3) a fixed upstream insertion stub.
# Built only with --net5; every net4 code path below is untouched.
# ---------------------------------------------------------------------------------------
# (1) Entry.  net4 gave tko_in lane 1 the only reachable bypass lane (1 -> 1, 1 -> 2), so
#     tko_in lane 0 could only reach the arterial.  net5 wires lane 0 to BOTH tko_1 lane 0
#     (arterial) and lane 1 (bypass), and lane 1 to lane 2 (bypass): both entry lanes then
#     have a direct bypass link and the arterial is reached from lane 0 (or by a lane change).
NET5_ENTRY = ((0, 0), (0, 1), (1, 2))
# (2) Diverge D.  Exactly three mainline links out of tko_vms; the two redundant arterial
#     links of net4 (1 -> tko_a1_1, 2 -> tko_a1_2) are gone.
NET5_D = ((0, "tko_a1", 0), (1, "ktb_w1", 0), (2, "ktb_w1", 1))
# `tko_a1` is placed on the side of tko_vms lane 0 -- in this lefthand network lane 0 is the
# LEFTMOST lane, and ktb_w1 leaves D on the left, so a straight tko_a1 (net4's chord from D
# to j3) sits on the RIGHT of the bypass lanes and the three links cross.  net5 gives
# tko_a1 an explicit shape that fans its lanes out on the left of the tko_vms axis over the
# first FAN_BACK metres and rejoins the original D -> j3 chord: the three connectors then
# leave the junction in lane order (tko_a1_0 leftmost, then ktb_w1_0, ktb_w1_1) and do not
# cross, and the downstream geometry, the j3 junction and the detector chainage are the
# net4 ones.
NET5_FAN_OUT, NET5_FAN_BACK, NET5_FAN_LATERAL = 25.0, 75.0, 12.0
# `tko_a1` lane 1 would have no incoming link at all (the mainline only feeds lane 0), i.e.
# it would be a dead lane.  The zero-demand on-ramp `on_tko_a1` therefore feeds both of the
# arterial's inner lanes (1 and 2) instead of lane 2 only; both links stay subordinate.
NET5_ON_A1_LANES = (1, 2)
# (3) Insertion stub: exactly 500 m, three lanes, 70 km/h, upstream of the unchanged 2-lane
#     tko_in, with a zipper merge 0 -> 0, 1 -> 1, 2 -> 1 (lane 2 drops into lane 1).
NET5_INSERT, NET5_INSERT_LANES, NET5_INSERT_SPEED = 500.0, 3, 70
NET5_INSERT_CONNS = ((0, 0), (1, 1), (2, 1))


def demand_peaks():
    """Peak 15-minute slice volumes (veh/h, scale 1.0) per ramp edge and through merge M.

    Ramps come straight from demand.json `ramps`.  M is not a detector edge, so its volume is
    the sum of the OD movements that pass it: every movement whose destination is the sink
    `out` (cross-street stubs stay at S1-S4 and never reach M).
    """
    d = json.loads((OUT / "demand" / "demand.json").read_text(encoding="utf-8"))
    if d["meta"]["scale"] != 1.0:
        raise SystemExit(f'demand.json is at scale {d["meta"]["scale"]}, need 1.0')
    ramps = {}
    for s in d["slices"]:
        for r in s["ramps"]:
            ramps[r["edge"]] = max(ramps.get(r["edge"], 0.0), r["flow_vph"])
    m_peak = max(sum(v for k, v in s["od_flows"].items() if k.rsplit("->", 1)[-1] == "out")
                 for s in d["slices"])
    return ramps, m_peak


def lanes_for(flow_vph):
    """Merge-lane rule: max(1, ceil(flow / MERGE_LANE_FLOW))."""
    return max(1, math.ceil(flow_vph / MERGE_LANE_FLOW))


def is_section(eid):
    return eid.startswith(SECTION_PREFIX)


def section_host(eid):
    """The main edge a merge/diverge section serves, else None."""
    return next((eid[len(p):] for p in SECTION_PREFIX if eid.startswith(p)), None)


def detector_chainage(net, dm):
    """Chainage (m) of every detector along its route, from shortest paths on v4."""
    def leg(a, b):
        if dm[a]["edge"] == dm[b]["edge"]:
            return dm[b]["pos"] - dm[a]["pos"]
        path, _ = net.getShortestPath(net.getEdge(dm[a]["edge"]), net.getEdge(dm[b]["edge"]))
        if path is None:
            raise SystemExit(f"no v4 path {a} -> {b}")
        return (net.getEdge(dm[a]["edge"]).getLength() - dm[a]["pos"]
                + sum(e.getLength() for e in path[1:-1]) + dm[b]["pos"])

    chain = {}
    for seq in (LOWER_SEQ, UPPER_SEQ):
        c, prev = 0.0, None
        for det in (d for _, _, _, ds in seq for d in ds):
            c += leg(prev, det) if prev else 0.0
            chain[det], prev = c, det
    return chain


def spans(net, seq, chain, dm):
    """Real-chainage span of every main edge: from the v4 edge start of its first detector to the
    v4 edge end of its last; real road with no detector is absorbed by the downstream edge."""
    out, prev_end = [], None
    for i, (eid, lanes, speed, dets) in enumerate(seq):
        start = prev_end if i else chain[dets[0]] - dm[dets[0]]["pos"]
        if dets:
            last = dets[-1]
            end = chain[last] - dm[last]["pos"] + net.getEdge(dm[last]["edge"]).getLength()
            if i == 0 and end - start < ENTRY_MIN:
                end = chain[seq[1][3][0]] - dm[seq[1][3][0]]["pos"]
        elif i + 1 < len(seq) and seq[i + 1][3]:
            end = chain[seq[i + 1][3][0]] - dm[seq[i + 1][3][0]]["pos"]
        else:
            end = start + TAIL[eid]
        out.append({"id": eid, "lanes": lanes, "td": lanes, "speed": speed, "dets": dets,
                    "start": start, "end": end, "len": end - start})
        prev_end = end
    return out


def insert_sections(seq, nodes, chain, ramp_lanes):
    """Split main edges so every multi-lane ramp has a merge or diverge section.

    Merge (`ms_on_<edge>`): the first SECTION metres of the downstream edge, carrying its TD
    lane count plus the ramp's n lanes; the ramp joins the section's outer n lanes and the
    section then drops back to the TD count.  Diverge (`dv_off_<edge>`): the last SECTION
    metres of the upstream edge, TD + n lanes; the off-ramp leaves from the added n lanes.
    A section is only needed where the main edge does not already gain/drop n lanes at that
    junction -- there the ramp uses that lane-add / lane-drop directly (no extra edge).  A
    detector inside a section moves onto it; its absolute chainage is unchanged and its loops
    stay on the first TD lanes (see `spans`/`td`).  Returns {main edge: merge section id} and
    {main edge: diverge section id}.
    """
    merge_sec, dv_sec = {}, {}
    i = 0
    while i < len(seq) - 1:
        u, v = seq[i], seq[i + 1]
        n_on = ramp_lanes.get("on_" + v["id"], 1)
        n_off = ramp_lanes.get("off_" + u["id"], 1)
        merge = n_on >= 2 and v["lanes"] - u["lanes"] < n_on
        diverge = n_off >= 2 and u["lanes"] - v["lanes"] < n_off
        if merge and diverge:
            raise SystemExit(f"merge and diverge section both needed at {u['id']} -> {v['id']}")
        if merge:
            cut = v["start"] + SECTION
            sec = {**v, "id": f"ms_on_{v['id']}", "lanes": v["lanes"] + n_on,
                   "start": v["start"], "end": cut, "len": SECTION,
                   "dets": [d for d in v["dets"] if chain[d] < cut]}
            v["dets"] = [d for d in v["dets"] if chain[d] >= cut]
            v["start"], v["len"] = cut, v["end"] - cut
            seq.insert(i + 1, sec)
            nodes.insert(i + 2, f"{v['id']}_ms")
            merge_sec[v["id"]] = sec["id"]
        elif diverge:
            cut = u["end"] - SECTION
            sec = {**u, "id": f"dv_off_{u['id']}", "lanes": u["lanes"] + n_off,
                   "start": cut, "end": u["end"], "len": SECTION,
                   "dets": [d for d in u["dets"] if chain[d] >= cut]}
            u["dets"] = [d for d in u["dets"] if chain[d] < cut]
            u["end"], u["len"] = cut, cut - u["start"]
            seq.insert(i + 1, sec)
            nodes.insert(i + 1, f"{u['id']}_dv")
            dv_sec[u["id"]] = sec["id"]
        i += 2 if (merge or diverge) else 1
    return merge_sec, dv_sec


def make_polyline(points):
    """Interpolate/extrapolate (chainage -> XY) along a detector polyline."""
    pts = sorted(points)

    def at(c):
        (c0, p0), (c1, p1) = next(((a, b) for a, b in zip(pts, pts[1:]) if a[0] <= c <= b[0]),
                                  (pts[0], pts[1]) if c < pts[0][0] else (pts[-2], pts[-1]))
        f = 0.0 if c1 == c0 else (c - c0) / (c1 - c0)
        return (p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1]))
    return at


def unit(a, b):
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def left(d, off):
    return (-d[1] * off, d[0] * off)
def write_xml(path, root, rows):
    Path(path).write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<{root}>\n'
                          + "\n".join("    " + r for r in rows) + f"\n</{root}>\n", encoding="utf-8")


def tls_links(net_path):
    """tl id -> {linkIndex: (from-edge, to-edge, to-lane)} read back from a built network."""
    links = {}
    for c in ET.parse(net_path).getroot().findall("connection"):
        if c.get("tl"):
            links.setdefault(c.get("tl"), {})[int(c.get("linkIndex"))] = (
                c.get("from"), c.get("to"), int(c.get("toLane")))
    return links


def two_phase(per, dur, factor=1.0, fav=()):
    """Mainline green then cross green, each closed by a YELLOW s yellow.

    A link sharing a target lane with an earlier link of the same phase gets minor green
    'g' (the merge must yield), as netconvert does for lane drops.  Every green -> red
    transition is an intergreen: the yellow state turns that phase's greens to 'y', and
    its YELLOW seconds are taken out of that phase's green, so the cycle length is
    exactly the same as the two-phase plan it replaces.
    """
    n = max(per) + 1

    def state(cross):
        seen, out = set(), []
        for i in range(n):
            f, t, tl = per.get(i, ("", "", 0))
            out.append("r" if f.startswith("x") != cross else ("g" if (t, tl) in seen else "G"))
            seen.add((t, tl))
        return "".join(out)

    def yellow(st):
        return "".join("y" if ch in "Gg" else ch for ch in st)

    rows = []
    for st, d in zip((state(False), state(True)), dur):
        serves = (any(st[i] in "Gg" for i in range(n) if per.get(i, ("",))[0] in fav)
                  and "G" in st)
        green = int(round(d * factor if serves else max(5, d)))
        rows += [(green - YELLOW, st), (YELLOW, yellow(st))]
    return [f'<phase duration="{d:.0f}" state="{st}"/>' for d, st in rows]


def write_tll(net_path, path, program="0", dur=DUR, fav=(), factor=1.0):
    write_xml(path, "additional",
              [f'<tlLogic id="{t}" type="static" programID="{program}" offset="0">'
               + "".join(two_phase(per, dur, factor, fav)) + "</tlLogic>"
               for t, per in tls_links(net_path).items()])


def lane_map(ul, vl, spread=0):
    """Source lane -> target lane of one straight-through edge pair.

    Lanes 0..vl-1 keep their index; the rest are the lanes the junction drops.  Plain lane
    drops collapse every surplus lane into the target's last lane (netconvert's rule, kept
    for the mainline devices such as `off_ktr_w2`).  The `spread` outermost surplus lanes
    -- the lanes an on-ramp merge section gained and now has to shed -- each get a target
    lane of their own instead, outermost ramp lane to outermost target lane, so a
    multi-lane ramp is not funnelled into a single lane of the main edge.
    """
    m = [min(i, vl - 1) for i in range(ul)]
    surplus = list(range(vl, ul))
    for k, i in enumerate(reversed(surplus[:spread])):
        m[i] = max(0, vl - 1 - k)
    return m


def through(conns, U, ul, V, vl, off=None, off_lanes=1, on=None, on_lanes=1, spread=0):
    """Straight-through connections with each lane drop/rise merged at the junction.

    Mainline lane i keeps its index into V while V has it and collapses into V's last lane
    beyond that; V lanes the mainline cannot reach are fed by U's last lane (as netconvert
    does for a lane rise).  An n-lane on-ramp merges into V's outer n lanes and an n-lane
    off-ramp leaves from U's outer n lanes -- that is the lane-add/lane-drop a multi-lane ramp
    was sized for (where the main edge cannot provide it, a section edge sits in between and
    the ramp joins/leaves the section).  `spread` marks the `spread` outermost lanes of U as
    ramp lanes that must keep a target lane each when U drops back to vl lanes (see lane_map).
    """
    targets = lane_map(ul, vl, spread)
    covered = set(targets)
    conns += [(U, i, V, targets[i]) for i in range(ul)]
    conns += [(U, ul - 1, V, j) for j in range(vl) if j not in covered]
    if off:
        conns += [(U, ul - off_lanes + j, off, j) for j in range(off_lanes)]
    if on:
        conns += [(on, j, V, vl - on_lanes + j) for j in range(on_lanes)]


def build_graph(net, dm, ramp_peak, m_peak, net5=False):
    """Nodes, edges, connections and detector rows, all derived from real chainage."""
    ramp_lanes = {k: lanes_for(v) for k, v in ramp_peak.items()}
    chain = detector_chainage(net, dm)
    low, up = spans(net, LOWER_SEQ, chain, dm), spans(net, UPPER_SEQ, chain, dm)
    merge_by_id = {e["id"]: e for e in low + up}
    merge_in = [(eid, ramp_lanes.get(eid, 1) if eid.startswith("on_") else
                 merge_by_id[eid]["lanes"]) for eid in MERGE_IN]
    merge_off, m_lanes = {}, 0
    for eid, ln in merge_in:                  # lane-preserving M: every incoming lane keeps
        merge_off[eid], m_lanes = m_lanes, m_lanes + ln   # a lane of its own in `rejoin`
    for seq in (low, up):
        for e in seq:
            if e["id"] in MERGE_EDGES:
                e["lanes"] = m_lanes          # rejoin and out are as wide as their inflow
    low_nodes, up_nodes = list(LOW_NODES), list(UP_NODES)
    # junction pairs before sectioning: each one hosts off_<u> and on_<v> (ramps below)
    pairs = [(low[i]["id"], low[i + 1]["id"]) for i in range(len(low) - 1)]
    pairs += [("tko_vms", "ktb_w1")]                       # the upper route's diverge pair
    pairs += [(up[i]["id"], up[i + 1]["id"]) for i in range(len(up) - 1)]
    pairs += [("ktb_n2", "rejoin")]                        # the upper route's merge pair
    merge_sec, dv_sec = {}, {}
    for seq, nds in ((low, low_nodes), (up, up_nodes)):
        m, d = insert_sections(seq, nds, chain, ramp_lanes)
        merge_sec.update(m)
        dv_sec.update(d)
    by_id = {e["id"]: e for e in low + up}
    for seq, nds in ((low, low_nodes), (up, up_nodes)):
        for i, e in enumerate(seq):
            e["from"], e["to"] = nds[i], nds[i + 1]
    # polyline through the projected detector lat/lon, plus hand-built D (diverge), M (merge)
    xy = {k: net.convertLonLat2XY(m["lon"], m["lat"]) for k, m in dm.items()}
    low_pts = [(chain[d], xy[d]) for _, _, _, ds in LOWER_SEQ for d in ds]
    up_pts = [(chain[d], xy[d]) for _, _, _, ds in UPPER_SEQ for d in ds]
    m_end = by_id["rejoin"]["start"]
    d_xy = make_polyline(low_pts)(by_id["tko_vms"]["end"])
    up_pts.insert(0, (up[0]["start"], d_xy))
    m_low, m_up = make_polyline(low_pts)(m_end), make_polyline(up_pts)(up[-1]["end"])
    m_xy = ((m_low[0] + m_up[0]) / 2.0, (m_low[1] + m_up[1]) / 2.0)
    low_at = make_polyline(low_pts + [(m_end, m_xy)])
    up_at = make_polyline(up_pts + [(up[-1]["end"], m_xy)])
    node_xy = {"D": d_xy, "M": m_xy}
    for i, nd in enumerate(low_nodes):
        node_xy.setdefault(nd, low_at(low[0]["start"] if i == 0 else low[i - 1]["end"]))
    for i, nd in enumerate(up_nodes):
        node_xy.setdefault(nd, up_at(up[i - 1]["end"]))
    tail = unit((0, 0), add(unit(up_at(up[-1]["end"] - 50), m_xy), unit(low_at(m_end - 50), m_xy)))
    node_xy["j5"] = add(m_xy, tuple(TAIL["rejoin"] * v for v in tail))
    node_xy["sink"] = add(node_xy["j5"], tuple(TAIL["out"] * v for v in tail))
    low_ids = {e["id"] for e in low}
    at_of = lambda eid: low_at if eid in low_ids else up_at                     # noqa: E731
    edge_dir = lambda eid: unit(at_of(eid)(by_id[eid]["end"] - 10.0),           # noqa: E731
                                at_of(eid)(by_id[eid]["end"]))
    edges, conns, det_rows, map_rows = [], [], [], []
    for seq in (low, up):
        for e in seq:
            edges.append((e["id"], e["from"], e["to"], e["lanes"], e["speed"], e["len"],
                          MERGE_MAJOR.get(e["id"], ROAD_PRIORITY)))
            for det in e["dets"]:
                off, m = chain[det] - e["start"], dm[det]
                det_rows.append((det, e["id"], off, e["td"]))
                map_rows.append({k: m[k] for k in ("lat", "lon", "bearing", "road", "bound")}
                                | {"id": det, "edge": e["id"], "dist_m": 0.0,
                                   "pos": round(off, 1), "n_lanes": e["td"]})
    ramps = {}
    for u, v in pairs:
        # The junction hosting off_<u> / on_<v>.  A merge section moves the on-ramp's merge
        # point to the section head; a diverge section moves the off-ramp's take-off into the
        # section's added lanes (the section's far end).
        junction = (by_id[merge_sec[v]]["from"] if v in merge_sec
                    else by_id[dv_sec[u]]["to"] if u in dv_sec else by_id[v]["from"])
        base = node_xy[junction]
        for kind, eid in (("off", u), ("on", v)):
            key = kind + "_" + eid
            if key in ramps or key in SKIP_RAMPS:
                continue
            if net5 and key == "off_tko_vms":
                # net5 drops the D off-ramp stub: keeping it would need a fourth mainline
                # link out of tko_vms (the spec allows exactly three) and an unconnected
                # stub lane would be a dead lane.  Node and edge are not emitted at all.
                continue
            d, off_ramp = edge_dir(eid), kind == "off"
            sgn, length = (-1.0, RAMP_OFF) if off_ramp else (1.0, RAMP_ON)
            node = f"off_{eid}_end" if off_ramp else f"on_{eid}_src"
            frm, to = (junction, node) if off_ramp else (node, junction)
            end = add(base, add(tuple(sgn * length * w for w in d), left(d, -sgn * LATERAL)))
            edges.append((key, frm, to, ramp_lanes.get(key, 1), RAMPSPEED, length, RAMP_PRIORITY))
            ramps[key], node_xy[node] = eid, end
    for i, (s, u, _v) in enumerate(SIGNALS, start=1):
        perp, n = left(edge_dir(u), 1.0), node_xy[s]
        node_xy[f"x{i}_src"] = add(n, tuple(XSTUB * w for w in perp))
        node_xy[f"x{i}_sink"] = add(n, tuple(-XSTUB * w for w in perp))
        edges += [(f"x{i}_in", f"x{i}_src", s, XLANES, RAMPSPEED, XSTUB, 1),
                  (f"x{i}_out", s, f"x{i}_sink", XLANES, RAMPSPEED, XSTUB, 1)]
    for seq, nds in ((low, low_nodes), (up, up_nodes)):
        for i in range(len(seq) - 1):
            u, v, node = seq[i], seq[i + 1], nds[i + 1]
            if node == "D":                               # the stem splits into both routes
                if net5:
                    conns += [("tko_vms", fl, t, tl) for fl, t, tl in NET5_D]
                    conns += [("on_tko_a1", 0, "tko_a1", ln) for ln in NET5_ON_A1_LANES]
                    conns += [("on_ktb_w1", 0, "ktb_w1", 1)]
                else:
                    conns += [("tko_vms", 0, "tko_a1", 0), ("tko_vms", 1, "tko_a1", 1),
                              ("tko_vms", 2, "tko_a1", 2), ("tko_vms", 1, "ktb_w1", 0),
                              ("tko_vms", 2, "ktb_w1", 1), ("tko_vms", 2, "off_tko_vms", 0),
                              ("on_tko_a1", 0, "tko_a1", 2), ("on_ktb_w1", 0, "ktb_w1", 1)]
                continue
            if v["id"].startswith("ms_on_"):              # on-ramp joins the add-lane section
                off_key, on_key = f"off_{u['id']}", "on_" + section_host(v["id"])
            elif u["id"].startswith("dv_off_"):           # off-ramp takes the diverge lanes
                off_key, on_key = "off_" + section_host(u["id"]), f"on_{v['id']}"
            elif is_section(u["id"]) or is_section(v["id"]):
                off_key = on_key = None                   # continuation, no ramp
            else:
                off_key, on_key = f"off_{u['id']}", f"on_{v['id']}"
            off = off_key if off_key in ramps else None
            on = on_key if on_key in ramps else None
            if net5 and node == "j1":
                # (1) repaired entry: exactly 0->0, 0->1, 1->2 out of tko_in, plus the
                # unchanged zero-demand off-ramp take-off and the on_tko_1 merge.
                conns += [("tko_in", fl, "tko_1", tl) for fl, tl in NET5_ENTRY]
                conns += [("tko_in", 1, "off_tko_in", 0), ("on_tko_1", 0, "tko_1", 2)]
                continue
            if node == "M":
                # Lane-preserving carriageway merge: every incoming lane keeps a target lane
                # of its own in rejoin (the 6 arterial lanes, then the 2 bypass lanes, then
                # the stub on-ramp's lane), so no two approaches share a target lane, there
                # are no foe links and no approach yields.  Each carriageway still sheds its
                # own stub off-ramp.
                for eid, ln in merge_in:
                    conns += [(eid, k, "rejoin", merge_off[eid] + k) for k in range(ln)]
                for src, ul in (("ktr_w6", u["lanes"]),
                                ("ktb_n2", merge_by_id["ktb_n2"]["lanes"])):
                    key = "off_" + src
                    if key in ramps:
                        n_off = ramp_lanes.get(key, 1)
                        conns += [(src, ul - n_off + k, key, k) for k in range(n_off)]
                continue
            # A merge section sheds exactly the lanes its on-ramp added; spread those over
            # the main edge instead of funnelling them into the main edge's last lane.
            spread = (ramp_lanes.get("on_" + section_host(u["id"]), 0)
                      if u["id"].startswith("ms_on_") else 0)
            through(conns, u["id"], u["lanes"], v["id"], v["lanes"], off,
                    ramp_lanes.get(off, 1), on, ramp_lanes.get(on, 1), spread)
    for i in range(1, len(SIGNALS) + 1):
        through(conns, f"x{i}_in", XLANES, f"x{i}_out", XLANES)
    edge_shapes, node_type = {}, {s: "traffic_light" for s, _, _ in SIGNALS}
    if net5:
        # (3) insertion stub, exactly 500 m of three lanes at 70 km/h upstream of tko_in.
        src_xy, j1_xy = node_xy["src"], node_xy["j1"]
        d_in = unit(src_xy, j1_xy)
        ins_xy = (src_xy[0] - NET5_INSERT * d_in[0], src_xy[1] - NET5_INSERT * d_in[1])
        node_xy["ins_src"] = ins_xy
        node_type["src"] = "zipper"        # the 3 -> 2 zipper merge tko_insert -> tko_in
        edges.append(("tko_insert", "ins_src", "src", NET5_INSERT_LANES,
                      NET5_INSERT_SPEED, NET5_INSERT, ROAD_PRIORITY))
        conns += [("tko_insert", fl, "tko_in", tl) for fl, tl in NET5_INSERT_CONNS]
        # (2) the tko_a1 fan: leave D on the side of tko_vms lane 0, rejoin the net4 chord.
        d_xy, j3_xy = node_xy["D"], node_xy["j3"]
        d_vms = unit(node_xy["j2"], d_xy)
        n_left = left(d_vms, 1.0)
        p_out = add(d_xy, add(tuple(NET5_FAN_LATERAL * w for w in n_left),
                              tuple(NET5_FAN_OUT * w for w in d_vms)))
        d_a1 = unit(d_xy, j3_xy)
        p_back = add(d_xy, tuple(NET5_FAN_BACK * w for w in d_a1))
        edge_shapes["tko_a1"] = (d_xy, p_out, p_back, j3_xy)
    return {"node_xy": node_xy, "node_type": node_type,
            "edges": edges, "conns": conns, "det_rows": det_rows, "map_rows": map_rows,
            "edge_shapes": edge_shapes,
            "chain": chain, "low": low, "up": up, "merge_in": merge_in}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the B-lite network")
    ap.add_argument("--skip-netconvert", action="store_true")
    ap.add_argument("--tag", default="", help="output suffix, e.g. 2 -> net2.net.xml")
    ap.add_argument("--scratch", default=None,
                    help="directory for the netconvert inputs, the base signal programs are "
                         "still written next to the net; default: the scenario dir")
    ap.add_argument("--net5", action="store_true",
                    help="build the net5 revision (repaired entry + diverge D + tko_insert); "
                         "the net4 path is unchanged when this is off")
    args = ap.parse_args(argv)
    tag = args.tag
    OUT.mkdir(parents=True, exist_ok=True)
    scratch = Path(args.scratch).resolve() if args.scratch else OUT
    scratch.mkdir(parents=True, exist_ok=True)
    net = sumolib.net.readNet(str(V4NET))
    dm = {m["id"]: m for m in json.loads(V4MAP.read_text(encoding="utf-8"))["mapped"]}
    ramp_peak, m_peak = demand_peaks()
    g = build_graph(net, dm, ramp_peak, m_peak, net5=args.net5)
    node_xy, node_type, edges = g["node_xy"], g["node_type"], g["edges"]
    conns, det_rows, chain = g["conns"], g["det_rows"], g["chain"]
    shapes = g["edge_shapes"]
    nod = scratch / f"blite{tag}.nod.xml"
    edg = scratch / f"blite{tag}.edg.xml"
    con = scratch / f"blite{tag}.con.xml"
    net_file = OUT / f"net{tag}.net.xml"
    # net5 keeps the scenario directory to net5.net.xml / detectors5.add.xml only, so the
    # generated signal programs go next to the other netconvert inputs in the scratch dir.
    tls_dir = scratch if args.net5 else OUT
    base_tls = tls_dir / f"tls_base{tag}.add.xml"
    add = OUT / f"detectors{tag}.add.xml"
    write_xml(nod, "nodes",
              [f'<node id="{n}" x="{node_xy[n][0]:.2f}" y="{node_xy[n][1]:.2f}" '
               f'type="{node_type.get(n, "priority")}"/>' for n in node_xy])
    write_xml(edg, "edges",
              [f'<edge id="{e}" from="{f}" to="{t}" numLanes="{ln}" speed="{sp / 3.6:.2f}" '
               f'length="{le:.1f}" priority="{pr}"'
               + (f' shape="{" ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in shapes[e])}"'
                  if e in shapes else "")
               + "/>" for e, f, t, ln, sp, le, pr in edges])
    write_xml(con, "connections",
              [f'<connection from="{f}" to="{t}" fromLane="{fl}" toLane="{tl}"/>'
               for f, fl, t, tl in conns])
    if args.skip_netconvert:
        return
    base = [sumo_bin("netconvert"), "--node-files", str(nod), "--edge-files", str(edg),
            "--connection-files", str(con), "-o", str(net_file),
            "--lefthand", "--no-turnarounds", "--tls.default-type", "static",
            "--offset.disable-normalization", "true"]
    subprocess.run(base, check=True, cwd=str(ROOT))
    write_tll(net_file, base_tls)
    subprocess.run(base + ["--tllogic-files", str(base_tls)], check=True, cwd=str(ROOT))
    write_tll(net_file, tls_dir / f"tls_incident{tag}.add.xml", program="P_inc",
              fav=set(CONTROL["corridor_b"]), factor=1.5)
    with open(add, "w", encoding="utf-8") as fh:
        fh.write("<additional>\n")
        for det, eid, pos, lanes in det_rows:
            for ln in range(lanes):
                fh.write(f'    <inductionLoop id="{det}_{ln}" lane="{eid}_{ln}" pos="{pos:.1f}" '
                         f'period="30" file="NUL"/>\n')
        fh.write("</additional>\n")
    (scratch / f"detector_map{tag}.json").write_text(
        json.dumps({"mapped": g["map_rows"], "unmapped": []}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(f"B-lite: {len(edges)} edges, {len(node_xy)} nodes, {len(conns)} connections, "
          f"{len(det_rows)} detectors")
    main_lanes = {e["id"]: e["lanes"] for e in g["low"] + g["up"]}
    print(f"  merge M peak {m_peak:.0f} veh/h -> lane-preserving rejoin/out "
          f"{main_lanes['rejoin']} lanes = "
          + " + ".join(f"{eid} {ln}" for eid, ln in g["merge_in"]))
    for key in sorted(ramp_peak):
        n = max(1, math.ceil(ramp_peak[key] / MERGE_LANE_FLOW))
        print(f"  {key:>14} peak {ramp_peak[key]:7.1f} vph -> {n} lane(s)")
    for e in g["low"] + g["up"]:
        offs = [f"{d}@{chain[d] - e['start']:.1f}" for d in e["dets"]]
        print(f"  {e['id']:>8} {e['lanes']} lanes {e['len']:7.1f} m  {offs}")
    print(f"  shortest main edge {min(e['len'] for e in g['low'] + g['up']):.1f} m")


if __name__ == "__main__":
    main()
