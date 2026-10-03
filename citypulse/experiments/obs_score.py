# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Proxy-only bounded run, authoritative E1 XML, raw entry backlog and observation score."""
import argparse
import csv
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np

from citypulse.config import RESULTS, SCEN
from citypulse.network.bounded import NET, OUT, save, sha
from citypulse.sim import init_signals, proxy_cmd


def first_downstream_detectors(net, mapped):
    det_by_edge = {}
    for d in mapped:
        det_by_edge.setdefault(d['edge'], []).append(d['id'])
    mapping = {}
    for edge in net.getEdges():
        eid = edge.getID()
        if eid in det_by_edge:
            mapping[eid] = det_by_edge[eid]
            continue
        queue = [edge]
        seen = {eid}
        found = []
        while queue:
            cur = queue.pop(0)
            if cur.getID() != eid and cur.getID() in det_by_edge:
                found = det_by_edge[cur.getID()]
                break
            for nxt, cs in cur.getOutgoing().items():
                if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs):
                    if nxt.getID() not in seen:
                        seen.add(nxt.getID())
                        queue.append(nxt)
        mapping[eid] = found
    return mapping


def run(tag, end=7200, net_path=None, net_meta_path=None):
    import sumolib
    net_path = Path(net_path or NET).resolve()
    net_meta_path = Path(net_meta_path or (OUT / 'network.json')).resolve()
    directory = OUT / tag
    routes = directory / 'demand.rou.xml'
    network = json.loads(net_meta_path.read_text(encoding='utf-8'))
    profile = json.loads((RESULTS / 'obs' / 'obs_profile.json').read_text())
    retained = set(network['retained_detectors'])
    net = sumolib.net.readNet(str(net_path))
    mapped = [d for d in json.loads((SCEN / 'detector_map.json').read_text())['mapped'] if d['id'] in retained]
    downstream_map = first_downstream_detectors(net, mapped)
    entry_gates = [g['edge'] for g in network['gates'] if g['direction'] == 'entry']
    downstream_detectors = {gate: downstream_map.get(gate, []) for gate in entry_gates}
    root = ET.Element('additional')
    for d in ET.parse(SCEN / 'detectors.add.xml').getroot():
        if d.get('id').rsplit('_', 1)[0] in retained:
            lane_id = d.get('lane')
            try:
                lane = net.getLane(lane_id)
                pos = float(d.get('pos'))
                if pos >= lane.getLength():
                    d.set('pos', f'{max(0.1, lane.getLength() - 0.5):.2f}')
            except Exception:
                pass
            d.set('file', str((directory / 'e1.xml').resolve()))
            root.append(d)
    detector_file = directory / 'detectors.add.xml'
    ET.ElementTree(root).write(detector_file, encoding='utf-8')
    vehicles = {v.get('id'): (v.find('route').get('edges').split()[0], float(v.get('depart')))
                for v in ET.parse(routes).iter('vehicle')}
    cmd = proxy_cmd(1, routes)
    cmd[cmd.index('-n') + 1] = str(net_path)
    # netconvert may renumber cropped signal links; use its preserved program 0.
    cmd[cmd.index('-a') + 1] = f'{SCEN / "vtypes_proxy.add.xml"},{detector_file}'
    cmd += ['--end', str(end), '--error-log', str(directory / 'sumo.log')]
    save(directory / 'run_inputs.json', {'tag': tag, 'command': cmd, 'network_path': str(net_path), 'network_meta_path': str(net_meta_path), 'input_sha256': {
        str(p): sha(p) for p in (net_path, net_meta_path, routes, SCEN / 'vtypes_proxy.add.xml', SCEN / 'detector_map.json',
                                 RESULTS / 'obs' / 'obs_profile.json', RESULTS / 'obs' / 'obs_bins.parquet') if Path(p).exists()}})
    import libsumo as tc
    started = time.monotonic()
    tc.start(cmd)
    init_signals(tc)
    inserted, arrived, teleports = Counter(), 0, 0
    history = [{'time': 0, 'running': 0, 'pending': 0, 'explained_pending': 0, 'unexplained_pending': 0, 'loaded_due': 0}]
    pending_rows, jams, blocked = [], Counter(), []
    departures = sorted(dep for _, dep in vehicles.values())
    try:
        for k in range(1, end + 1):
            tc.simulationStep()
            for vid in tc.simulation.getDepartedIDList():
                inserted[vehicles[vid][0]] += 1
            arrived += tc.simulation.getArrivedNumber()
            teleports += tc.simulation.getStartingTeleportNumber()
            if k % 60:
                continue
            pending = Counter(vehicles[vid][0] for vid in tc.simulation.getPendingVehicles())
            tm = f'{7 + (k - 1) // 3600:02d}:{((k - 1) % 3600 // 300) * 5:02d}'
            explained_pending, unexplained_pending = 0, 0
            for gate in entry_gates:
                ps = [profile.get(aid, {}).get(tm) for aid in downstream_detectors.get(gate, [])]
                good = [p for p in ps if p and p.get('speed_kmh') and p.get('occ')]
                explained = any(p['speed_kmh']['median'] < 30 and p['occ']['median'] > 20 for p in good)
                if explained:
                    explained_pending += pending[gate]
                else:
                    unexplained_pending += pending[gate]
                pending_rows.append({'time': k, 'gate': gate, 'pending': pending[gate],
                                     'boundary_congestion_evidence': explained, 'bin_start': tm})
            due = int(np.searchsorted(departures, k, side='left'))
            history.append({'time': k, 'running': tc.vehicle.getIDCount(), 'pending': sum(pending.values()),
                            'explained_pending': explained_pending,
                            'unexplained_pending': unexplained_pending, 'loaded_due': due,
                            'inserted': sum(inserted.values()), 'arrived': arrived})
            for eid in tc.edge.getIDList():
                if not eid.startswith(':'):
                    jams[eid] += tc.edge.getLastStepHaltingNumber(eid)
            if k % 900 == 0:
                stopped = sorted(((tc.vehicle.getWaitingTime(v), v) for v in tc.vehicle.getIDList()), reverse=True)
                for wait, vid in stopped[:30]:
                    route = tc.vehicle.getRoute(vid)
                    index = tc.vehicle.getRouteIndex(vid)
                    blocked.append({'time': k, 'id': vid, 'waiting_seconds': wait,
                                     'lane': tc.vehicle.getLaneID(vid), 'pos': tc.vehicle.getLanePosition(vid),
                                     'route_next': route[index:index + 8], 'next_tls': tc.vehicle.getNextTLS(vid)[:2]})
    finally:
        tc.close()
    for name, data in [('history', history), ('pending', pending_rows)]:
        fields = list(dict.fromkeys(key for row in data for key in row))
        with (directory / f'{name}.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['tag'] + fields)
            writer.writeheader()
            writer.writerows({'tag': tag, **row} for row in data)
    last = [h for h in history if h['time'] >= end - 900]
    metadata = {'tag': tag, 'duration': end, 'wall_seconds': time.monotonic() - started,
                'network_path': str(net_path),
                'network_sha256': sha(net_path),
                'network_meta_path': str(net_meta_path),
                'network_meta_sha256': sha(net_meta_path) if net_meta_path.exists() else None,
                'retained_detectors': sorted(retained), 'loaded_vehicles': len(vehicles),
                'inserted': sum(inserted.values()), 'arrived': arrived, 'teleports': teleports,
                'running_end': history[-1]['running'], 'pending_end': history[-1]['pending'],
                'explained_pending_end': history[-1]['explained_pending'],
                'unexplained_pending_end': history[-1]['unexplained_pending'],
                'explained_pending_share_end': history[-1]['explained_pending'] / max(len(vehicles), 1),
                'unexplained_pending_share_end': history[-1]['unexplained_pending'] / max(len(vehicles), 1),
                'unexplained_pending_share_max': max(h['unexplained_pending'] / max(h['loaded_due'], 1) for h in history),
                'running_last15_slope_vps': float(np.polyfit([h['time'] for h in last], [h['running'] for h in last], 1)[0]) if len(last) >= 2 else 0.0,
                'running_last15_delta': (last[-1]['running'] - last[0]['running']) if len(last) >= 1 else 0,
                'last15_samples': len(last), 'top_halting_sample_sums': jams.most_common(20),
                'count_method': 'SUMO E1 XML nVehContrib, completed 30-second intervals; GEH on vph',
                'input_sha256': json.loads((directory / 'run_inputs.json').read_text())['input_sha256']}
    save(directory / 'run.json', metadata)
    save(directory / 'blocked.json', blocked)
    if end == 7200:
        # libsumo and pyarrow ship colliding Arrow DLLs on Windows; score in a fresh process.
        metrics_cmd = [sys.executable, '-m', 'citypulse.experiments.obs_metrics', '--tag', tag,
                       '--net', str(net_path), '--net-meta', str(net_meta_path)]
        subprocess.run(metrics_cmd, check=True)
    print(json.dumps({k: v for k, v in metadata.items() if k in (
        'tag', 'loaded_vehicles', 'inserted', 'pending_end', 'explained_pending_end', 'unexplained_pending_end',
        'geh_lt5_share', 'speed_mae', 'occ_mae', 'congestion_agreement', 'detectors_speed_pass', 'accepted', 'wall_seconds')}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    ap.add_argument('--end', type=int, default=7200, help='Use a separate tag for a short pilot')
    ap.add_argument('--net', default=str(NET), help='Network file to use')
    ap.add_argument('--net-meta', default=str(OUT / 'network.json'), help='Network metadata JSON file')
    args = ap.parse_args(argv)
    run(args.tag, args.end, net_path=args.net, net_meta_path=args.net_meta)


if __name__ == '__main__':
    main()
