# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Reproducible corridor crop; no lane, speed, priority or signal tuning."""
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


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def adjacent(e, incoming=False):
    return [x for x, cs in (e.getIncoming() if incoming else e.getOutgoing()).items()
            if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = SCEN / 'net.net.xml'
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
    (OUT / 'keep.txt').write_text('\n'.join(sorted(keep)), encoding='utf-8')
    cmd = [sumo_bin('netconvert'), '-s', str(source), '--keep-edges.input-file',
           str(OUT / 'keep.txt'), '--no-turnarounds', 'true', '-o', str(NET)]
    with (OUT / 'netconvert.log').open('w') as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=log)
    bn = sumolib.net.readNet(str(NET))
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
            original = n.getEdge(e.getID())
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
    save(OUT / 'network.json', {'tag': 'bounded_network_v1', 'source_sha256': sha(source),
         'network_sha256': sha(NET), 'command': cmd, 'source_edges': len(n.getEdges()),
         'edges': len(retained), 'edge_km': sum(e.getLength() for e in bn.getEdges()) / 1000,
         'retained_detectors': [d['id'] for d in mapped if d['edge'] in retained],
         'dropped_detectors': dropped, 'gates': sorted(gates, key=lambda g: (g['direction'], g['edge']))})
    print(json.dumps({'edges': len(retained), 'detectors': len(mapped) - len(dropped),
                      'gates': len(gates), 'dropped': [d['id'] for d in dropped]}))


if __name__ == '__main__':
    main()
