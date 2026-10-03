"""Diagnose the ``tko_in`` insertion backlog on synthetic B-lite net4 (seed 1001, 7,200 s).

Variants (all incident-free, same G1-G3 evaluation as ``results/blite/synth/run_g123.py``):

* **A** baseline, ``departLane="best"``, net4          -- reuse the existing g123_seed1001 run;
* **B** route copy with ``departLane="free"``;
* **C** route copy with ``departLane="random"``;
* **D** net copy with one extra connection, ``tko_in`` lane 0 -> ``tko_1`` lane 1
  (netconvert ``--connection-files`` patch), ``departLane="best"`` kept.

Writes everything under ``results/blite/synth/diag_entry/`` only; no frozen file is touched.
Extra instrumentation on top of ``run_g123.run_seed``: per-lane E1 counts on ``tko_in`` /
``tko_1`` / ``tko_vms`` / ``ktb_w1`` over the last hour, and halting means for ``tko_1``,
``tko_vms``, ``ktb_w1`` (and ``tko_in``) over the last 30 min.

Usage::

    python results/blite/synth/diag_entry/run_diag.py --build
    python results/blite/synth/diag_entry/run_diag.py --variant B
    python results/blite/synth/diag_entry/run_diag.py --summary
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DIAG = Path(__file__).resolve().parent
REPO_ROOT = DIAG.parents[3]
SYNTH_OUT = REPO_ROOT / 'results' / 'blite' / 'synth'
if str(SYNTH_OUT) not in sys.path:
    sys.path.insert(0, str(SYNTH_OUT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_g123 as G  # noqa: E402  (same-directory module: reuses window_slopes + constants)
from citypulse.config import SCEN, sumo_bin, sumo_home  # noqa: E402
from citypulse.sim import init_signals  # noqa: E402

VAR = DIAG / 'variants'
NET4 = SCEN / 'blite' / 'net4.net.xml'
VTYPES_PROXY = SCEN / 'vtypes_proxy.add.xml'
TLS_WEBSTER = SCEN / 'blite' / 'synth' / 'tls_webster_synth.add.xml'
PROXY_ROU = SCEN / 'blite' / 'synth' / 'proxy.rou.xml'

END = G.END
LAST30 = G.LAST30
LAST_HOUR = 3600
SEED = 1001

# (detector id, lane, position).  Positions are mid-lane, well inside every lane length.
DET_LANES = [
    ('dk_tko_in_0', 'tko_in_0', 150.0),
    ('dk_tko_in_1', 'tko_in_1', 150.0),
    ('dk_tko_1_0', 'tko_1_0', 130.0),
    ('dk_tko_1_1', 'tko_1_1', 130.0),
    ('dk_tko_1_2', 'tko_1_2', 130.0),
    ('dk_tko_vms_0', 'tko_vms_0', 180.0),
    ('dk_tko_vms_1', 'tko_vms_1', 180.0),
    ('dk_tko_vms_2', 'tko_vms_2', 180.0),
    ('dk_ktb_w1_0', 'ktb_w1_0', 300.0),
    ('dk_ktb_w1_1', 'ktb_w1_1', 300.0),
]
HALT_EDGES = ['tko_in', 'tko_1', 'tko_vms', 'ktb_w1']

VARIANTS = {
    'A': {'routes': PROXY_ROU, 'net': NET4, 'change': 'baseline, departLane="best" (existing run)'},
    'B': {'routes': VAR / 'proxy_free.rou.xml', 'net': NET4, 'change': 'departLane="free"'},
    'C': {'routes': VAR / 'proxy_random.rou.xml', 'net': NET4, 'change': 'departLane="random"'},
    'D': {'routes': PROXY_ROU, 'net': VAR / 'net4_D.net.xml',
          'change': 'extra connection tko_in_0 -> tko_1_1, departLane="best"'},
}


def build_variants():
    """Create the B/C route copies and the D net copy (netconvert connection patch)."""
    VAR.mkdir(parents=True, exist_ok=True)
    src = PROXY_ROU.read_text(encoding='utf-8')
    n_best = src.count('departLane="best"')
    for tag, lane in (('B', 'free'), ('C', 'random')):
        out = VAR / f'proxy_{lane}.rou.xml'
        out.write_text(src.replace('departLane="best"', f'departLane="{lane}"'), encoding='utf-8')
        print(f'[build] {out} ({n_best} departLane="best" -> "{lane}")')

    con = VAR / 'extra.con.xml'
    con.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<connections>\n'
        '    <connection from="tko_in" to="tko_1" fromLane="0" toLane="1"/>\n'
        '</connections>\n', encoding='utf-8')
    env = dict(os.environ, SUMO_HOME=sumo_home())
    out_net = VAR / 'net4_D.net.xml'
    cmd = [sumo_bin('netconvert'), '--sumo-net-file', str(NET4),
           '--connection-files', str(con), '--output-file', str(out_net), '--no-warnings', 'true']
    print('[build]', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)
    root = ET.parse(out_net).getroot()
    added = [(c.get('from'), c.get('fromLane'), c.get('to'), c.get('toLane'))
             for c in root.findall('connection')
             if c.get('from') == 'tko_in' and c.get('to') == 'tko_1']
    print('[build] tko_in -> tko_1 connections in D:', added)


def write_dets(run_dir):
    root = ET.Element('additional')
    for did, lane, pos in DET_LANES:
        ET.SubElement(root, 'inductionLoop', {
            'id': did, 'lane': lane, 'pos': str(pos), 'period': str(LAST_HOUR),
            'file': str(run_dir / 'e1diag.xml')})
    ET.indent(ET.ElementTree(root), space='    ')
    path = run_dir / 'diag_dets.add.xml'
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    return path


def sumo_cmd(run_dir, seed, routes, net, det_file):
    cmd = [
        sumo_bin('sumo'),
        '-n', str(net),
        '-a', f'{VTYPES_PROXY},{det_file},{TLS_WEBSTER}',
        '-r', str(routes),
        '--seed', str(seed),
        '--step-length', '1',
        '--no-step-log', 'true',
        '--no-warnings', 'true',
        '--time-to-teleport', '-1',
        '--collision.action', 'warn',
        '--collision-output', str(run_dir / 'collisions.xml'),
        '--end', str(END),
        '--error-log', str(run_dir / 'sumo.log'),
    ]
    if G.reroute_enabled():
        cmd += ['--device.rerouting.probability', '0.3', '--device.rerouting.period', '60']
    return cmd


def run_variant(tag, routes=None, net=None, seed=SEED):
    import libsumo as tc

    routes = Path(routes or VARIANTS[tag]['routes'])
    net = Path(net or VARIANTS[tag]['net'])
    run_dir = DIAG / tag
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    vehicles = {}
    for v in ET.parse(routes).getroot().iter('vehicle'):
        vehicles[v.get('id')] = (v.find('route').get('edges').split()[0], float(v.get('depart')))
    departures = sorted(d for _, d in vehicles.values())
    sources = sorted({src for src, _ in vehicles.values()})

    det_file = write_dets(run_dir)
    cmd = sumo_cmd(run_dir, seed, routes, net, det_file)
    print(' '.join(cmd), flush=True)

    teleports = 0
    arrived = 0
    out_reached = set()
    history = []
    backlog = defaultdict(dict)
    total_pending = {}
    lane_flow = Counter()          # detector id -> vehicles in the last hour
    lane_flow_full = Counter()     # detector id -> vehicles over the whole run
    lane_entries = Counter()       # lane id -> vehicle entries in the last hour (cross-check)
    seen_on_lane = {}
    halt_sum = Counter()
    halt_peak = Counter()
    halt_steps = 0
    flush_arrivals = None
    pre_flush_running = None

    started = time.monotonic()
    tc.start(cmd)
    try:
        init_signals(tc)
        for k in range(1, END + 1):
            tc.simulationStep()
            teleports += int(tc.simulation.getStartingTeleportNumber())
            teleports += int(tc.simulation.getEndingTeleportNumber())
            arrived += int(tc.simulation.getArrivedNumber())
            for vid in tc.edge.getLastStepVehicleIDs('out'):
                out_reached.add(vid)

            for did, lane, _ in DET_LANES:
                n = int(tc.inductionloop.getLastStepVehicleNumber(did))
                lane_flow_full[did] += n
                if k > END - LAST_HOUR:
                    lane_flow[did] += n
                cur = set(tc.lane.getLastStepVehicleIDs(lane))
                prev = seen_on_lane.get(lane, set())
                if k > END - LAST_HOUR:
                    lane_entries[lane] += len(cur - prev)
                seen_on_lane[lane] = cur

            if k > END - LAST30:
                halt_steps += 1
                for eid in HALT_EDGES:
                    h = int(tc.edge.getLastStepHaltingNumber(eid))
                    halt_sum[eid] += h
                    if h > halt_peak[eid]:
                        halt_peak[eid] = h

            if k % 60 == 0:
                pending_vids = list(tc.simulation.getPendingVehicles())
                by_source = Counter(vehicles[vid][0] for vid in pending_vids if vid in vehicles)
                for src in sources:
                    backlog[src][k] = by_source.get(src, 0)
                total_pending[k] = len(pending_vids)
                history.append({
                    'time': k,
                    'scheduled_due': int(np.searchsorted(departures, k, side='left')),
                    'running': int(tc.vehicle.getIDCount()),
                    'pending_total': len(pending_vids),
                    **{f'pending_{src}': by_source.get(src, 0) for src in sources},
                    'arrived': arrived,
                    'discharge_out': len(out_reached),
                })
                if k == END:
                    pre_flush_running = int(tc.vehicle.getIDCount())

        # Mirrors run_g123: one extra step so departures at the horizon are registered.
        tc.simulationStep()
        arrived += int(tc.simulation.getArrivedNumber())
        teleports += int(tc.simulation.getStartingTeleportNumber())
        teleports += int(tc.simulation.getEndingTeleportNumber())
        end_running = int(tc.vehicle.getIDCount())
        end_pending = len(list(tc.simulation.getPendingVehicles()))
        collisions = len(list(tc.simulation.getCollisions()))
        flush_arrivals = arrived - history[-1]['arrived']
    finally:
        tc.close()
    wall = time.monotonic() - started

    with (run_dir / 'history.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)
    with (run_dir / 'pending_by_source.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['time', 'source', 'pending'])
        for src in sources:
            for t in sorted(backlog[src]):
                writer.writerow([t, src, backlog[src][t]])

    scheduled_end = int(np.searchsorted(departures, END, side='left'))
    conservation_gap = scheduled_end - (end_pending + end_running + arrived)
    pending_share = end_pending / max(scheduled_end, 1)
    running_windows = G.window_slopes({h['time']: h['running'] for h in history})
    backlog_windows = {src: G.window_slopes(backlog[src]) for src in sources}
    g1_pass = (teleports == 0 and collisions == 0)
    g2_pass = (conservation_gap == 0)
    g3_pass = bool(
        pending_share <= G.PENDING_SHARE_LIMIT
        and all(w['pass'] for w in running_windows)
        and all(w['pass'] for rows in backlog_windows.values() for w in rows)
    )

    per_lane = {}
    for did, lane, _ in DET_LANES:
        per_lane[did] = {
            'lane': lane,
            'last_hour': lane_flow[did],
            'last_hour_vph': lane_flow[did] * 3600.0 / LAST_HOUR,
            'full_run': lane_flow_full[did],
            'lane_entries_last_hour': lane_entries[lane],
        }
    halting = {e: {'mean_last30': round(halt_sum[e] / max(halt_steps, 1), 3),
                   'max_last30': int(halt_peak[e])} for e in HALT_EDGES}

    meta = {
        'tag': tag,
        'seed': seed,
        'change': VARIANTS[tag]['change'],
        'routes': str(routes),
        'net': str(net),
        'wall_seconds': round(wall, 2),
        'loaded_vehicles': len(vehicles),
        'scheduled_departures': scheduled_end,
        'pre_flush_running': pre_flush_running,
        'running_end': end_running,
        'pending_end': end_pending,
        'arrived_end': arrived,
        'flush_arrivals': flush_arrivals,
        'out_end': len(out_reached),
        'discharge_out_vph': len(out_reached) / (END / 3600.0),
        'conservation_gap': conservation_gap,
        'teleports': int(teleports),
        'collisions': int(collisions),
        'pending_share': pending_share,
        'g1_pass': bool(g1_pass),
        'g2_pass': bool(g2_pass),
        'g3_pass': bool(g3_pass),
        'all_gates_pass': bool(g1_pass and g2_pass and g3_pass),
        'backlog_windows_tko_in': backlog_windows.get('tko_in', []),
        'running_windows': running_windows,
        'per_lane': per_lane,
        'halting': halting,
        'sources': sources,
    }
    (run_dir / 'run.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps({k: meta[k] for k in (
        'tag', 'scheduled_departures', 'pending_end', 'running_end', 'arrived_end',
        'conservation_gap', 'teleports', 'collisions', 'g1_pass', 'g2_pass', 'g3_pass',
        'discharge_out_vph')}, indent=2), flush=True)
    return meta


def summary(tags=('A', 'B', 'C', 'D')):
    rows = []
    for tag in tags:
        p = DIAG / tag / 'run.json'
        if tag == 'A' and not p.exists():
            p = SYNTH_OUT / 'g123_seed1001' / 'run.json'
        if not p.exists():
            print(f'[summary] missing {p}')
            continue
        rows.append(json.loads(p.read_text(encoding='utf-8')))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description='tko_in insertion-backlog diagnostics.')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--variant')
    ap.add_argument('--summary', action='store_true')
    args = ap.parse_args(argv)

    os.environ.setdefault('CITYPULSE_NET', 'blite')
    os.environ.setdefault('CITYPULSE_BLITE_REV', '4')
    os.environ.setdefault('CITYPULSE_REROUTE', '0')

    if args.build:
        build_variants()
    if args.variant:
        run_variant(args.variant)
    if args.summary:
        for m in summary():
            print(json.dumps(m, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
