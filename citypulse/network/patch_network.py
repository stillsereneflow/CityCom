"""Step 1: build the corridor network used by all worlds from net_full.net.xml.

1. Keep motorway/trunk edges + every edge named Kwun Tong Road / Kai Fuk / Kwun Tong Bypass
   + 1-hop side-street stubs (edges of any class touching a kept edge), so side-street traffic enters
   through a junction instead of spawning mid-arterial.
2. Lane counts from TD: where a TD detector reports MORE lanes than the SUMO edge, set numLanes to
   the TD count and propagate along the same-name simple chain (1 in / 1 out) up to CHAIN_M metres.
   Fewer TD lanes than SUMO is left alone (detectors may not cover turn lanes).
3. netconvert -s net_full --keep-edges.input-file ... -e patch.edg.xml -o <out>.
Writes scenarios/kwuntong/{keep_edges.txt, lane_patch.edg.xml, lane_patch.json}.

Connection recomputation (defect fix, 2026-10-03): feeding `-s net_full -e patch.edg.xml` only changes
`numLanes`; netconvert keeps the `<connection>` elements it read from net_full, so lanes that the patch
adds get no successor and the widened road still operates as one lane per junction (see
`results/bounded/tko/tko_report.md` section 1). The build is therefore staged:

  A. prune net_full (keep edges + signal-node patch) to a scratch network;
  B. export stage A to plain XML and raise `numLanes` in the `.edg.xml`;
  C. drop from the `.con.xml` every connection whose `from` or `to` is such a widened edge, then rebuild
     with `netconvert -n -e -x [-t] [-i] --tls.default-type static`, so netconvert recomputes those
     connections (and their internal lanes) from the new lane counts while the untouched connections and
     the TLS programs are carried over from the plain export.

Inbound connection fix (2026-10-03, v4): stage C used to drop only `from in widened`, so an edge that was
widened 1 -> 3 lanes still received traffic on the single lane its un-widened upstream edge happened to
feed (`1132732696_2 -> 1132732693_0` on TKO Road). The drop now also removes `to in widened`: the links
into a widened edge are recomputed from the upstream lane counts too, which is what fans traffic across
the new lanes. Netconvert does not touch signal plans on its own, so the matching `.tll.xml` link records
are removed with them and the phase states of a program that lost its highest link are truncated
(`_drop_patched_connections`), otherwise netconvert aborts with
`Invalid linkIndex N for traffic light 'X' with M links`.
"""
import argparse
import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

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


def fill_gaps(net, keep, mapped, td, patch, max_m=800.0):
    """Edges on the same named road between two detector edges of the same road and bound get at least
    min(lanes reported by the two detectors). Grounded in TD: both bracketing detectors see that many
    lanes, so a narrower piece in between is an OSM tagging artefact (e.g. an 82 m two-lane piece
    between two three-lane TD sections on Tseung Kwan O Road)."""
    groups = defaultdict(list)
    for d in mapped:
        groups[(d["road"], d["bound"])].append(d)
    fills = []
    for (road, bound), ds in groups.items():
        for a in ds:
            for b in ds:
                if a["edge"] == b["edge"]:
                    continue
                path, _ = net.getShortestPath(net.getEdge(a["edge"]), net.getEdge(b["edge"]))
                if not path or sum(e.getLength() for e in path[1:-1]) > max_m:
                    continue
                inner = path[1:-1]
                if not inner or any(road.lower() not in (e.getName() or "").lower() for e in inner):
                    continue
                n = min(td.get(a["id"], net.getEdge(a["edge"]).getLaneNumber()),
                        td.get(b["id"], net.getEdge(b["edge"]).getLaneNumber()))
                for e in inner:
                    if e.getID() in keep and max(e.getLaneNumber(), patch.get(e.getID(), 0)) < n:
                        patch[e.getID()] = n
                        fills.append({"edge": e.getID(), "from_lanes": e.getLaneNumber(), "to_lanes": n,
                                      "between": [a["id"], b["id"]]})
    return fills


def _netconvert(args, log_name, check=True):
    """Run netconvert with its stderr captured in results/<log_name>; return the CompletedProcess."""
    with open(RESULTS / log_name, "w") as fh:
        return subprocess.run([sumo_bin("netconvert")] + args, check=check, stderr=fh)


def _run_stage_a(out):
    """Prune net_full down to the kept edges, apply the signal-node patch and raise the lane counts,
    without touching connections. This is the same netconvert call the script always made, so the
    pruned network and its connections are byte-for-byte the ones `net.net.xml` used to get."""
    _netconvert(["-s", str(FULL), "--keep-edges.input-file", str(SCEN / "keep_edges.txt"),
                 "--keep-edges.components", "1", "-e", str(SCEN / "lane_patch.edg.xml"),
                 "-n", str(SCEN / "signal_patch.nod.xml"),
                 "--tls.default-type", "static", "-o", str(out)], "netconvert_patch_stage_a.log")


def _export_plain(net_path, prefix):
    """Export a SUMO network to plain .nod/.edg/.con/.tll/.typ XML (this is what lets us edit the
    connections of a built network)."""
    _netconvert(["-s", str(net_path), "--plain-output-prefix", str(prefix),
                 "--plain-output.lanes", "true"], "netconvert_patch_plain.log")


def _apply_lane_patch(prefix, patch, baseline):
    """Set numLanes of the patched edges in the plain .edg.xml and return the set of widened edges.

    Lanes are only dropped from an edge that carries MORE <lane> children than the patched count; those
    extra lanes would otherwise survive the attribute change, and their leftovers are what makes
    netconvert reject the remaining connections as 'fromLane/toLane not found'."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(str(prefix) + ".edg.xml")
    widened = set()
    for e in tree.getroot().findall("edge"):
        eid = e.get("id")
        want = patch.get(eid)
        if want is None:
            continue
        lanes = e.findall("lane")
        if want < len(lanes):
            # Never narrow a road: net_full can already be wider than the TD count there.
            continue
        for lane in lanes[want:]:
            e.remove(lane)
        if want != baseline.get(eid, len(lanes)):
            widened.add(eid)
        e.set("numLanes", str(want))
    tree.write(str(prefix) + ".edg.xml", encoding="utf-8", xml_declaration=True)
    return widened


def _drop_patched_connections(prefix, patched):
    """Delete from .con.xml and .tll.xml the connections netconvert has to lay out again, so both sides of
    a widened edge are rebuilt from the new lane count.

    `from in patched` is the original v2 fix: a 1 -> 3 lane edge keeps the one connection it had in
    net_full, so its two new lanes get no successor and the junction still operates as one lane.

    `to in patched` is the v4 fix. An upstream edge that already carries the TD lane count in OSM was
    never patched, so its link into the widened edge was never rebuilt either and pinned the widened edge
    to one entry lane (`1132732696_2 -> 1132732693_0` on TKO Road, AID07107 capped at ~630 vph against a
    measured 3,030 vph). netconvert only re-derives connections of an edge that has NO loaded connection
    left (`NBEdge::computeConnections` is skipped for edges that come with a connection file), so dropping
    just the link into the widened edge leaves every other lane of that upstream edge unconnected (v4
    experiment: `98889700_1/2` and `818705769_1/2` dead). The whole outgoing connection set of those
    immediate upstream edges is therefore dropped, which is what makes netconvert recompute their fan-out
    across all their successors.

    Because a re-guess can also *drop* a movement OSM did provide (`1128468446` lost the second entry lane
    it had in v3), the recomputation is applied additively by `_merge_recomputed_connections`: the pass-1
    network's guesses are unioned with the links dropped here before the final rebuild, so the entry count
    of every widened edge can only grow. Edges that OSM marks as turn lanes keep their
    `changeLeft`/`changeRight` restriction from the plain .edg.xml.

    The `.tll.xml` (passed with -i) pins the same links as the `.con.xml`: a link record for a connection
    that no longer exists makes netconvert abort with `Connection from=... to=... not found`, and a
    program whose state strings are longer than its highest link index is rejected as well. Every tll link
    that is not in the surviving connection set is therefore removed, and the states of the programs that
    lost their highest index are truncated. A program that loses every link is dropped so netconvert
    regenerates it (this is the "regenerate the signal programs that lose links" escape hatch)."""
    import xml.etree.ElementTree as ET
    con_path = Path(str(prefix) + ".con.xml")
    tree = ET.parse(str(con_path))
    root = tree.getroot()
    connections = root.findall("connection")
    inbound = sorted({c.get("from") for c in connections if c.get("to") in patched})
    recompute = set(patched) | set(inbound)
    dropped, removed = set(), 0
    for c in connections:
        if c.get("from") in recompute:
            dropped.add(_con_key(c))
            root.remove(c)
            removed += 1
    tree.write(str(con_path), encoding="utf-8", xml_declaration=True)

    tll_path = Path(str(prefix) + ".tll.xml")
    if not tll_path.exists():
        return removed, dropped, inbound
    surviving = {_con_key(c) for c in root.findall("connection")}
    tree = ET.parse(str(tll_path))
    root = tree.getroot()
    lost = defaultdict(int)
    for c in list(root.findall("connection")):
        if _con_key(c) in dropped or _con_key(c) not in surviving:
            lost[c.get("tl")] += 1
            root.remove(c)
    index = defaultdict(set)
    for c in root.findall("connection"):
        index[c.get("tl")].add(int(c.get("linkIndex")))
    for t in list(root.findall("tlLogic")):
        tid = t.get("id")
        if tid not in lost:
            continue
        idx = index.get(tid, set())
        if not idx:
            root.remove(t)                      # netconvert regenerates a program with no links left
            continue
        want = max(idx) + 1
        for p in t.findall("phase"):
            state = p.get("state")
            if len(state) > want:
                p.set("state", state[:want])
    tree.write(str(tll_path), encoding="utf-8", xml_declaration=True)
    return removed, dropped, inbound


def _con_key(c):
    """Identity of a `<connection>`/tll link record: from, to and both lane indices."""
    return (c.get("from"), c.get("to"), c.get("fromLane"), c.get("toLane"))


def _rebuild_from_plain(prefix, out):
    """netconvert from the edited plain files. The signal-node patch is already inside the .nod.xml that
    stage A exported, so the reconstructed traffic lights keep the junction types the patch set."""
    args = ["-n", str(prefix) + ".nod.xml", "-e", str(prefix) + ".edg.xml",
            "-x", str(prefix) + ".con.xml"]
    for extra, flag in ((".typ.xml", "-t"), (".tll.xml", "-i")):
        if Path(str(prefix) + extra).exists():
            args += [flag, str(prefix) + extra]
    args += ["--tls.default-type", "static", "-o", str(out)]
    return _netconvert(args, "netconvert_patch.log")


def _merge_recomputed_connections(prefix, pass1, dropped):
    """Union the connections netconvert guessed in pass 1 with the ones stage A had, back into .con.xml.

    Only `from / to / fromLane / toLane` are copied; `tl`, `linkIndex`, `dir` and the internal-lane
    attributes are left for netconvert to derive, exactly as it did for the pass-1 guesses. Returns the
    number of connections added (0 when the recomputation was already a superset, in which case the caller
    does not need the second rebuild)."""
    import xml.etree.ElementTree as ET
    con_path = Path(str(prefix) + ".con.xml")
    tree = ET.parse(str(con_path))
    root = tree.getroot()
    have = {_con_key(c) for c in root.findall("connection")}
    recompute = {d[0] for d in dropped}
    candidates = [dict(zip(("from", "to", "fromLane", "toLane"), d)) for d in dropped]
    for c in ET.parse(str(pass1)).getroot().findall("connection"):
        if c.get("from") in recompute:
            candidates.append({k: c.get(k) for k in ("from", "to", "fromLane", "toLane")})
    added = 0
    for a in candidates:
        key = (a["from"], a["to"], a["fromLane"], a["toLane"])
        if None in key or key in have:
            continue
        ET.SubElement(root, "connection", a)
        have.add(key)
        added += 1
    if added:
        tree.write(str(con_path), encoding="utf-8", xml_declaration=True)
    return added


def _fill_widened_entries(prefix, patched):
    """Top up the lane-to-lane fan-out into every widened edge to `min(W lanes, upstream lanes)`.

    A re-guess is geometry-driven and can leave one upstream lane of a split junction doing something
    else (`494474297_1 -> 255261618_1` only, so `85649754` was entered on 3 of its 4 upstream lanes).
    Task check (b) asks for a widened edge to be entered on as many lanes as the upstream edge provides,
    so the missing lane→lane links are added explicitly: every other upstream lane that does not yet
    reach the widened edge is linked to the next free lane of that edge. Returns the number added."""
    import xml.etree.ElementTree as ET
    edg = ET.parse(str(prefix) + ".edg.xml").getroot()
    lanes = {e.get("id"): int(e.get("numLanes")) for e in edg.findall("edge")}
    con_path = Path(str(prefix) + ".con.xml")
    tree = ET.parse(str(con_path))
    root = tree.getroot()
    have, used = set(), defaultdict(set)
    for c in root.findall("connection"):
        have.add(_con_key(c))
        if c.get("fromLane") is not None and c.get("toLane") is not None:
            used[(c.get("from"), c.get("to"))].add(int(c.get("fromLane")))
    added = 0
    for W in sorted(patched):
        if W not in lanes:
            continue
        ups = sorted({c.get("from") for c in root.findall("connection") if c.get("to") == W})
        for u in ups:
            if u not in lanes:
                continue
            target = min(lanes[W], lanes[u])
            if len(used[(u, W)]) >= target:
                continue
            for i in range(lanes[u]):
                if len(used[(u, W)]) >= target:
                    break
                if i in used[(u, W)]:
                    continue
                to_lane = (i + len(used[(u, W)])) % lanes[W]
                key = (u, W, str(i), str(to_lane))
                if key in have:
                    continue
                ET.SubElement(root, "connection", {"from": u, "to": W,
                                                   "fromLane": str(i), "toLane": str(to_lane)})
                have.add(key)
                used[(u, W)].add(i)
                added += 1
    if added:
        tree.write(str(con_path), encoding="utf-8", xml_declaration=True)
    return added


def tls_programs(net_path):
    """{tls id: [(duration, state), ...]} — used to report which signal programs changed."""
    import xml.etree.ElementTree as ET
    root = ET.parse(str(net_path)).getroot()
    return {t.get("id"): [(p.get("duration"), p.get("state")) for p in t.findall("phase")]
            for t in root.findall("tlLogic")}


def build_network(patch, out, scratch, baseline):
    """Stages A–C above. Returns {'connections_removed', 'connections_added', 'connections_recomputed',
    'inbound_edges', 'edges_rewired', 'tls_changed'}."""
    out.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(scratch)
    scratch.parent.mkdir(parents=True, exist_ok=True)
    stage_a = scratch.with_name(scratch.stem + "_pruned.net.xml")
    prefix = scratch.with_name(scratch.stem + "_plain")
    _run_stage_a(stage_a)
    _export_plain(stage_a, prefix)
    before = tls_programs(stage_a)
    widened = _apply_lane_patch(prefix, patch, baseline)
    removed, dropped, inbound = _drop_patched_connections(prefix, widened)
    pass1 = out.with_name(out.name.replace(".net.xml", "") + "_pass1.net.xml")
    _rebuild_from_plain(prefix, pass1)
    added = _merge_recomputed_connections(prefix, pass1, dropped)
    filled = _fill_widened_entries(prefix, widened)
    if added or filled:
        _rebuild_from_plain(prefix, out)
    else:
        import shutil
        shutil.copy(pass1, out)
    after = tls_programs(out)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    return {"connections_removed": removed, "connections_added": added, "connections_filled": filled,
            "connections_recomputed": [list(d) for d in sorted(dropped)],
            "inbound_edges": inbound, "edges_rewired": sorted(widened),
            "tls_changed": changed, "stage_a": str(stage_a), "plain_prefix": str(prefix)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default=str(SCEN / "net_v2.net.xml"),
                    help="output network (default net_v2.net.xml; never overwrites net.net.xml)")
    ap.add_argument("--scratch", default=str(RESULTS / "bounded" / "lanes" / "patch_scratch"),
                    help="scratch prefix for the pruned net and its plain XML export")
    args = ap.parse_args()
    out = Path(args.output)
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
    gaps = fill_gaps(net, keep, mapped, td, patch)
    with open(SCEN / "lane_patch.edg.xml", "w", encoding="utf-8") as fh:
        fh.write("<edges>\n")
        for eid, n in sorted(patch.items()):
            fh.write(f'    <edge id="{eid}" numLanes="{n}"/>\n')
        fh.write("</edges>\n")
    sig = signal_nodes(net, keep)
    with open(SCEN / "signal_patch.nod.xml", "w", encoding="utf-8") as fh:
        fh.write("<nodes>\n")
        for nid in sorted(sig):
            fh.write(f'    <node id="{nid}" type="traffic_light"/>\n')
        fh.write("</nodes>\n")
    info = build_network(patch, out, args.scratch,
                         {e.getID(): e.getLaneNumber() for e in net.getEdges()})
    json.dump({"detectors": log, "gap_fills": gaps, "patched_edges": patch, "kept_edges": len(keep),
               "signalised_nodes": sorted(sig), "output": str(out), **{k: v for k, v in info.items()
               if k in ("connections_removed", "edges_rewired", "tls_changed")}},
              open(SCEN / "lane_patch.json", "w"), indent=1)
    built = sumolib.net.readNet(str(out))
    print(json.dumps({"kept_edges_requested": len(keep), "edges": len(built.getEdges()),
                      "tls": len(built.getTrafficLights()), "lane_patched_edges": len(patch),
                      "detectors_with_more_td_lanes": len(log), "gap_fills": len(gaps),
                      "connections_removed": info["connections_removed"],
                      "edges_rewired": len(info["edges_rewired"]),
                      "tls_changed": info["tls_changed"], "output": str(out)}))


def webster(routes, net_in=NET_FILE, net_out=None, add_out=None, pre=None, log=None, max_tries=8):
    """Replace static signal timings by SUMO tools/tlsCycleAdaptation.py (Webster) as program "0".
    Signals the tool cannot parse (joined clusters with several major greens on one index) are skipped
    and keep the netconvert timings. Returns the list of skipped signal ids.

    Every path can be given so a second build (e.g. net_v2 -> net_v3) can be fitted without touching
    the committed artifacts. The defaults reproduce the historical in-place behaviour exactly: read
    `net.net.xml`, write `tls_webster.add.xml`, stage `results/net_pre_webster.net.xml`, overwrite
    `net.net.xml`."""
    import shutil
    import sys
    from citypulse.config import sumo_home
    net_in = Path(net_in)
    net_out = Path(net_out) if net_out is not None else net_in
    add_out = Path(add_out) if add_out is not None else SCEN / "tls_webster.add.xml"
    pre = Path(pre) if pre is not None else RESULTS / "net_pre_webster.net.xml"
    log = Path(log) if log is not None else RESULTS / "tlsCycleAdaptation.log"
    add_out.parent.mkdir(parents=True, exist_ok=True)
    pre.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    tool = str(Path(sumo_home()) / "tools" / "tlsCycleAdaptation.py")
    skip = []
    for _ in range(max_tries):
        cmd = [sys.executable, tool, "-n", str(net_in), "-r", str(routes), "-o", str(add_out), "-b", "0",
               "-p", "0", "--min-cycle", "60", "--max-cycle", "140", "-v"] + (["--skip", ",".join(skip)] if skip else [])
        with open(log, "w") as fh:
            r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
        if r.returncode == 0:
            break
        last = [l for l in open(log) if l.startswith("tl-logic ID:")][-1]
        skip.append(last.split(":", 1)[1].strip())
    else:
        raise RuntimeError("tlsCycleAdaptation kept failing")
    shutil.copy(net_in, pre)
    net_out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sumo_bin("netconvert"), "-s", str(pre), "--tllogic-files", str(add_out), "-o", str(net_out)],
                   check=True, stderr=subprocess.DEVNULL)
    return skip


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--webster", help="route file for Webster signal timing (run after demand exists)")
    ap.add_argument("--net-in", default=str(NET_FILE), help="network to fit (default net.net.xml)")
    ap.add_argument("--net-out", default=None,
                    help="network to write (default --net-in; pass net_v3.net.xml to keep net_v2 intact)")
    ap.add_argument("--add-out", default=None,
                    help="tllogic-file to write (default scenarios/kwuntong/tls_webster.add.xml)")
    ap.add_argument("--pre", default=None,
                    help="staging copy of --net-in (default results/net_pre_webster.net.xml)")
    ap.add_argument("--log", default=None, help="tlsCycleAdaptation stdout log (default results/tlsCycleAdaptation.log)")
    a = ap.parse_args()
    if a.webster:
        print(json.dumps({"webster_skipped": webster(a.webster, a.net_in, a.net_out, a.add_out, a.pre, a.log)}))
    else:
        main()
