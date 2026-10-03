# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Reproducible corridor crop; no lane, speed, priority or signal tuning."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import sumolib

from citypulse.config import BBOX, RESULTS, SCEN, sumo_bin
from citypulse.scenario import CONTROL

OUT = RESULTS / 'bounded'
NET = SCEN / 'net_bounded.net.xml'
NAMES = ('Kwun Tong Bypass', 'Kwun Tong Road', 'Kai Fuk Road', 'Tseung Kwan O Road')
# Crop stubs whose OSM way continues past the one-hop fragment the crop keeps: {edge id: metres of
# same-named continuation to retain}. `1132732705` (Kai Tin Road) is 0.49 m in net_full and 10.88 m
# after the v2 connection rebuild; OSM tags the way lanes=1, destination=Kai Tin Road, maxspeed=70 and
# net_full carries 13.13 m + 322.74 m of it beyond the stub. 158 b01 routes end on the fragment, so
# dropping it would invalidate them; extending keeps them valid and gives the exit real road.
STUB_REPAIRS = {'1132732705': 300.0}


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def adjacent(e, incoming=False):
    return [x for x, cs in (e.getIncoming() if incoming else e.getOutgoing()).items()
            if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs)]


def repair_stubs(full, keep, out, repairs=STUB_REPAIRS):
    """Turn fake dead-end crop stubs into exits with real road behind them.

    The one-hop rule below keeps the first fragment of a named side road but not its continuation, so
    the fragment is a sink while the road physically carries on. For each `{stub: metres}` entry this
    walks the unpruned extract `full` outward along passenger-usable, same-named successors (taking the
    longest branch where the road forks) and keeps them until that continuation reaches `metres`, then
    writes the plain `.nod/.edg/.con` patch files netconvert needs to add those edges to a crop of a
    network that does not contain them (`-n/-e/-x`). `keep` is extended in place; returns (args, evidence)."""
    if not repairs:
        return [], {}
    import subprocess as sp
    import xml.etree.ElementTree as ET
    prefix = out / 'full_plain'
    if not (out / 'full_plain.edg.xml').exists():
        sp.run([sumo_bin('netconvert'), '-s', str(SCEN / 'net_full.net.xml'),
                '--plain-output-prefix', str(prefix), '--plain-output.lanes', 'true',
                '--no-warnings', 'true'], check=True,
               stdout=(out / 'netconvert_full_plain.log').open('w'),
               stderr=sp.STDOUT)
    plain_nod = ET.parse(str(out / 'full_plain.nod.xml')).getroot()
    plain_edg = ET.parse(str(out / 'full_plain.edg.xml')).getroot()
    plain_con = ET.parse(str(out / 'full_plain.con.xml')).getroot()
    added, evidence = [], {}
    for stub, min_m in sorted(repairs.items()):
        if not full.hasEdge(stub):
            continue
        name = full.getEdge(stub).getName() or ''
        cur, got, chain = full.getEdge(stub), 0.0, []
        while got < min_m:
            # A same-named fork (Kai Tin Road splits at node 994194695) is not ambiguous road: take the
            # longest branch, which is the one OSM's `destination=Kai Tin Road` mainline follows.
            nxt = sorted((x for x in adjacent(cur) if (x.getName() or '') == name),
                         key=lambda x: -x.getLength())
            if not nxt:
                break
            cur = nxt[0]
            chain.append(cur.getID())
            got += cur.getLength()
        if not chain:
            continue
        for eid in chain:
            if eid not in keep:
                keep.add(eid)
        added += chain
        evidence[stub] = {'road': name, 'stub_length_m': round(full.getEdge(stub).getLength(), 2),
                          'kept_edges': [[e, round(full.getEdge(e).getLength(), 2)] for e in chain],
                          'continuation_m': round(got, 2), 'target_m': min_m}
    if not added:
        return [], evidence
    scope = set(added) | set(repairs)
    nodes, edges = set(), set(added)
    for eid in added:
        e = full.getEdge(eid)
        nodes.update((e.getFromNode().getID(), e.getToNode().getID()))
    root = ET.Element('nodes')
    for n in plain_nod.findall('node'):
        if n.get('id') in nodes:
            root.append(n)
    ET.ElementTree(root).write(str(out / 'stub_patch.nod.xml'), encoding='utf-8', xml_declaration=True)
    root = ET.Element('edges')
    for e in plain_edg.findall('edge'):
        if e.get('id') in edges:
            root.append(e)
    ET.ElementTree(root).write(str(out / 'stub_patch.edg.xml'), encoding='utf-8', xml_declaration=True)
    root = ET.Element('connections')
    for c in plain_con.findall('connection'):
        if c.get('from') in scope and c.get('to') in scope:
            root.append(c)
    ET.ElementTree(root).write(str(out / 'stub_patch.con.xml'), encoding='utf-8', xml_declaration=True)
    args = ['-n', str(out / 'stub_patch.nod.xml'), '-e', str(out / 'stub_patch.edg.xml'),
            '-x', str(out / 'stub_patch.con.xml')]
    return args, evidence


def main(source=SCEN / 'net.net.xml', net=NET, out=OUT, extra=()):
    source, net, out = Path(source), Path(net), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = sumolib.net.readNet(str(source))
    full = sumolib.net.readNet(str(SCEN / 'net_full.net.xml'))
    core = {e.getID() for e in n.getEdges() if any(s in e.getName() for s in NAMES)}
    core.update(CONTROL['corridor_b'])
    core.add(CONTROL['vms_target_edge'])
    keep = set(core)
    # Only short connecting ramps between retained roads, not unrelated trunk corridors.
    for eid in sorted(core):
        stack = [(n.getEdge(eid), [], 0)]
        while stack:
            edge, path, dist = stack.pop()
            for nxt in adjacent(edge):
                nid = nxt.getID()
                if nid in core:
                    keep.update(path)
                elif nid not in path and dist + nxt.getLength() <= 600 and (
                        'link' in nxt.getType() or not nxt.getName()):
                    stack.append((nxt, path + [nid], dist + nxt.getLength()))
    # A one-edge representation of an actual named side road at its physical junction.
    # It is not automatically a demand source: route fitting must justify its volume.
    for eid in sorted(keep.copy()):
        e = n.getEdge(eid)
        for x in adjacent(e) + adjacent(e, True):
            if x.getName() and x.getID() not in keep:
                keep.add(x.getID())
    # The named-side-road rule above keeps the first fragment of a road but not its continuation; where
    # that leaves a fake dead end (Kai Tin Road), add the real road behind it. See STUB_REPAIRS.
    stub_args, stubs = repair_stubs(full, keep, out)
    # Explicit keeps. The ramp race above stops at a 600 m budget measured in the CROPPED geometry, so a
    # connection rebuild that changes junction shapes can drop a ramp the demand still uses. Callers that
    # compare two crops (e.g. the lane-connection fix) pin those ramps here instead of inheriting the
    # artefact.
    for eid in extra:
        keep.add(eid)
    (out / 'keep.txt').write_text('\n'.join(sorted(keep)), encoding='utf-8')
    # --junctions.minimal-shape: the default junction shapes are built from edge overlap, and pruning the
    # network to the corridor leaves several junctions so large that the edge between them collapses to
    # netconvert's 0.20 m floor (10 non-sink edges in net_bounded_v2, e.g. corridor edges 675826410#0,
    # 1133472552, 1133472559). Minimal shapes keep every retained edge at its real length; the
    # connections and the edge set are unchanged.
    cmd = [sumo_bin('netconvert'), '-s', str(source), '--keep-edges.input-file',
           str(out / 'keep.txt'), '--no-turnarounds', 'true',
           '--junctions.minimal-shape', 'true'] + stub_args + ['-o', str(net)]
    with (out / 'netconvert.log').open('w') as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=log)
    bn = sumolib.net.readNet(str(net))
    retained = {e.getID() for e in bn.getEdges()}
    assert set(CONTROL['corridor_b']) | {CONTROL['vms_target_edge']} <= retained
    assert all(bn.getEdge(b) in adjacent(bn.getEdge(a)) for a, b in zip(
        CONTROL['corridor_b'], CONTROL['corridor_b'][1:]))
    mapped = json.loads((SCEN / 'detector_map.json').read_text(encoding='utf-8'))['mapped']
    gates = []
    for e in bn.getEdges():
        for direction, incoming in [('entry', True), ('exit', False)]:
            if adjacent(e, incoming):
                continue
            original = n.getEdge(e.getID()) if n.hasEdge(e.getID()) else full.getEdge(e.getID())
            outside = [x.getID() for x in adjacent(original, incoming) if x.getID() not in retained]
            full_connections = []
            if full.hasEdge(e.getID()):
                full_connections = [x.getID() for x in adjacent(full.getEdge(e.getID()), incoming)]
            detector = [d['id'] for d in mapped if d['edge'] == e.getID()]
            node = e.getFromNode() if incoming else e.getToNode()
            lon, lat = bn.convertXY2LonLat(*node.getCoord())
            border_m = min(abs(lat - BBOX[0]), abs(lat - BBOX[2]),
                           abs(lon - BBOX[1]) * 0.925, abs(lon - BBOX[3]) * 0.925) * 111000
            outer = border_m < 120 and bool(e.getName())
            legitimate = bool(detector or outside or full_connections or outer)
            gates.append({'edge': e.getID(), 'direction': direction, 'road': e.getName(),
                          'length_m': e.getLength(), 'detectors': detector,
                          'outside_connections': outside, 'full_connections': full_connections,
                          'boundary_lonlat': [lon, lat], 'distance_to_extract_border_m': border_m,
                          'authorized_source': legitimate and bool(e.getName() or detector),
                          'basis': ('TD measured boundary' if detector else
                                    'Named major road crosses original extract border; nearest detector balance estimates volume' if outer else
                                    'Physical road continuation/junction; volume estimated jointly from detector flow balance'
                                    if legitimate else 'Unverified extraction dead end; zero demand'),
                          'core': e.getID() in core})
    # Preserve every detector and its mapped position when its edge survives.
    dropped = [{**d, 'reason': 'Outside named corridor and required connecting ramps'}
               for d in mapped if d['edge'] not in retained]
    save(out / 'network.json', {'tag': 'bounded_network_v1', 'source_sha256': sha(source),
         'network_sha256': sha(net), 'command': cmd, 'source_edges': len(n.getEdges()),
         'edges': len(retained), 'edge_km': sum(e.getLength() for e in bn.getEdges()) / 1000,
         'retained_detectors': [d['id'] for d in mapped if d['edge'] in retained],
         'stub_repairs': stubs,
         'dropped_detectors': dropped, 'gates': sorted(gates, key=lambda g: (g['direction'], g['edge']))})
    print(json.dumps({'edges': len(retained), 'detectors': len(mapped) - len(dropped),
                      'gates': len(gates), 'stub_repairs': stubs,
                      'dropped': [d['id'] for d in dropped]}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--source', default=str(SCEN / 'net.net.xml'), help='network to crop (netconvert -s)')
    ap.add_argument('--net', default=str(NET), help='output bounded network (default net_bounded.net.xml)')
    ap.add_argument('--out', default=str(OUT), help='directory for keep.txt/netconvert.log/network.json')
    ap.add_argument('--extra-edges', default='', help='comma-separated edge ids to force into the crop')
    a = ap.parse_args()
    main(a.source, a.net, a.out, [e for e in a.extra_edges.split(',') if e])
