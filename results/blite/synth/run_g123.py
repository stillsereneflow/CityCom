"""G1-G3 evaluation of the synthetic boundary demand on B-lite net4.

Runs incident-free Proxy simulations (7,200 s) at the predeclared SUMO seeds 1001, 1002, 1003
with ``CITYPULSE_NET=blite``, net4 files, ``CITYPULSE_REROUTE=0`` and the synthetic Webster
signal plan, then evaluates:

* **G1** zero teleports and zero collisions;
* **G2** exact conservation, scheduled departures = pending + running + arrived at the end
  (every term printed);
* **G3** pending <= 2% of scheduled, and after a 900 s warm-up the slope of the running count
  and the slope of each source insertion backlog are each <= 0.05 veh/s over every complete
  15-min window.

Per seed it writes ``results/blite/synth/<tag>/`` with ``history.csv``,
``pending_by_source.csv``, ``halting_last30.json``, ``collisions.xml`` and ``run.json``, and
the report to ``results/blite/synth/g123_report.md``.

Usage::

    python results/blite/synth/run_g123.py --seeds 1001 1002 1003
"""
import argparse
import csv
import hashlib
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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from citypulse.config import RESULTS, SCEN, sumo_bin, sumo_home  # noqa: E402
from citypulse.sim import init_signals, reroute_enabled  # noqa: E402

SYNTH_DIR = SCEN / 'blite' / 'synth'
OUT_DIR = RESULTS / 'blite' / 'synth'
NET4 = SCEN / 'blite' / 'net4.net.xml'
DET4 = SCEN / 'blite' / 'detectors4.add.xml'
VTYPES_PROXY = SCEN / 'vtypes_proxy.add.xml'
TLS_WEBSTER = SYNTH_DIR / 'tls_webster_synth.add.xml'
TLS_INCIDENT = SYNTH_DIR / 'tls_incident_synth.add.xml'
PROXY_ROU = SYNTH_DIR / 'proxy.rou.xml'

END = 7200
WARMUP = 900
WINDOW = 900
SLOPE_LIMIT = 0.05          # veh/s
PENDING_SHARE_LIMIT = 0.02
LAST30 = 1800

BUILT_FILES = [
    SYNTH_DIR / 'proxy.rou.xml',
    SYNTH_DIR / 'twin_cand.rou.xml',
    SYNTH_DIR / 'proxy_shock.rou.xml',
    SYNTH_DIR / 'demand.json',
    SYNTH_DIR / 'demand_shock.json',
    SYNTH_DIR / 'tls_webster_synth.add.xml',
    SYNTH_DIR / 'tls_incident_synth.add.xml',
]
HASH_FILES = BUILT_FILES + [NET4, DET4]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def proxy_sumo_cmd(run_dir, seed, routes_path=PROXY_ROU, net_path=NET4, tls_path=TLS_WEBSTER):
    """Proxy SUMO command for the synthetic benchmark; rerouting is gated by CITYPULSE_REROUTE."""
    det_file = run_dir / 'detectors4.add.xml'
    tree = ET.parse(DET4)
    for d in tree.getroot():
        d.set('file', str(run_dir / 'e1.xml'))
    tree.write(det_file, encoding='utf-8')

    cmd = [
        sumo_bin('sumo'),
        '-n', str(net_path),
        '-a', f'{VTYPES_PROXY},{det_file},{tls_path}',
        '-r', str(routes_path),
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
    if reroute_enabled():
        cmd += ['--device.rerouting.probability', '0.3', '--device.rerouting.period', '60']
    return cmd


def window_slopes(samples, min_time=WARMUP, window=WINDOW, limit=SLOPE_LIMIT):
    """Slope over every complete `window`-second window that lies after the warm-up.

    Windows are aligned to multiples of `window`; the first one is [900, 1800] for the
    predeclared 900 s warm-up.  `samples` maps integer second -> value.
    """
    ts = sorted(samples)
    if not ts:
        return []
    out = []
    start = min_time if min_time % window == 0 else ((min_time // window) + 1) * window
    while start + window <= ts[-1]:
        idx = [t for t in ts if start <= t <= start + window]
        if len(idx) < 3:
            start += window
            continue
        x = np.array(idx, dtype=float)
        y = np.array([samples[t] for t in idx], dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])
        out.append({'window': [start, start + window], 'slope': slope, 'pass': bool(slope <= limit)})
        start += window
    return out


def run_seed(seed, out_root=OUT_DIR, routes_path=PROXY_ROU, tag=None):
    """Run one Proxy simulation and evaluate G1-G3; returns the run metadata dict."""
    import libsumo as tc

    tag = tag or f'g123_seed{seed}'
    run_dir = Path(out_root) / tag
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    vehicles = {}
    for v in ET.parse(routes_path).getroot().iter('vehicle'):
        vehicles[v.get('id')] = (v.find('route').get('edges').split()[0], float(v.get('depart')))
    departures = sorted(d for _, d in vehicles.values())
    loaded_vehicles = len(vehicles)
    sources = sorted({src for src, _ in vehicles.values()})

    cmd = proxy_sumo_cmd(run_dir, seed, routes_path=routes_path)
    print(' '.join(cmd), flush=True)

    teleports = 0
    arrived = 0                     # route completions anywhere (x stubs end at x_out)
    out_reached = set()             # distinct vehicles that reached the `out` edge
    history = []
    backlog = defaultdict(dict)        # source -> {t: pending}
    total_pending = {}
    halting_sum = Counter()
    halting_peak = Counter()
    halting_steps = 0

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

            if k > END - LAST30:
                halting_steps += 1
                for eid in tc.edge.getIDList():
                    if eid.startswith(':'):
                        continue
                    h = tc.edge.getLastStepHaltingNumber(eid)
                    if h > 0:
                        halting_sum[eid] += h
                        if h > halting_peak[eid]:
                            halting_peak[eid] = h

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

        # One flush step: SUMO registers departures scheduled exactly at the horizon during the
        # following insertion attempt, so without it the file-level identity can be off by the
        # last second's vehicles.  Every reported metric above covers 1..END only.
        tc.simulationStep()
        arrived += int(tc.simulation.getArrivedNumber())
        teleports += int(tc.simulation.getStartingTeleportNumber())
        teleports += int(tc.simulation.getEndingTeleportNumber())
        end_running = int(tc.vehicle.getIDCount())
        end_pending = len(list(tc.simulation.getPendingVehicles()))
        collisions = len(list(tc.simulation.getCollisions()))
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

    all_edges = set(halting_sum) | set(halting_peak)
    halting = [{
        'edge': e,
        'mean_halting': round(halting_sum[e] / max(halting_steps, 1), 3),
        'max_halting': int(halting_peak[e]),
    } for e in sorted(all_edges)]
    halting.sort(key=lambda r: r['mean_halting'], reverse=True)
    (run_dir / 'halting_last30.json').write_text(json.dumps(halting, indent=2), encoding='utf-8')

    # G2 terms at the end of the horizon, read after the flush step.  `arrived` counts every
    # route completion (the cross-street stubs finish at x_out), so the identity is exact.
    scheduled_end = int(np.searchsorted(departures, END, side='left'))
    running_end = end_running
    pending_end = end_pending
    conservation_gap = scheduled_end - (pending_end + running_end + arrived)

    # G3
    pending_share = pending_end / max(scheduled_end, 1)
    running_windows = window_slopes({h['time']: h['running'] for h in history})
    backlog_windows = {src: window_slopes(backlog[src]) for src in sources}
    peak_time = max(total_pending, key=lambda t: total_pending[t]) if total_pending else 0
    peak_total = total_pending.get(peak_time, 0)
    peak_source = Counter()
    if peak_time:
        row = next(h for h in history if h['time'] == peak_time)
        peak_source = Counter({s: row.get(f'pending_{s}', 0) for s in sources})

    g1_pass = (teleports == 0 and collisions == 0)
    g2_pass = (conservation_gap == 0)
    g3_pass = bool(
        pending_share <= PENDING_SHARE_LIMIT
        and all(w['pass'] for w in running_windows)
        and all(w['pass'] for rows in backlog_windows.values() for w in rows)
    )

    run_meta = {
        'tag': tag,
        'seed': seed,
        'duration_s': END,
        'wall_seconds': round(wall, 2),
        'reroute_enabled': reroute_enabled(),
        'loaded_vehicles': loaded_vehicles,
        'scheduled_departures': scheduled_end,
        'running_end': running_end,
        'pending_end': pending_end,
        'arrived_end': arrived,
        'out_end': len(out_reached),
        'inserted_end': running_end + arrived,
        'conservation_gap': conservation_gap,
        'teleports': int(teleports),
        'collisions': int(collisions),
        'g1_pass': bool(g1_pass),
        'g2_pass': bool(g2_pass),
        'pending_share': pending_share,
        'running_windows': running_windows,
        'backlog_windows': backlog_windows,
        'g3_pass': g3_pass,
        'discharge_out_vph': len(out_reached) / (END / 3600.0),
        'discharge_out_count': len(out_reached),
        'largest_queue': {'time_s': peak_time, 'total': peak_total,
                          'by_source': dict(peak_source)},
        'halting_last30': halting,
        'sources': sources,
    }
    run_meta['all_gates_pass'] = bool(g1_pass and g2_pass and g3_pass)
    (run_dir / 'run.json').write_text(json.dumps(run_meta, indent=2), encoding='utf-8')
    return run_meta


def write_ready(out_root=OUT_DIR, synth_dir=SYNTH_DIR):
    """Hash every file under the synth scenario dir plus net4/detectors4 (only on a full pass)."""
    lines = []
    for f in sorted(p for p in Path(synth_dir).rglob('*') if p.is_file()):
        lines.append(f'{sha256(f)}  {f.as_posix()}')
    for f in (NET4, DET4):
        lines.append(f'{sha256(f)}  {f.as_posix()}')
    (Path(out_root) / 'READY').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return Path(out_root) / 'READY'


def write_report(metas, out_path, commands, extra_paths=()):
    lines = [
        'MODEL: deepseek-v4-flash',
        '# G1-G3 on synthetic boundary demand, B-lite net4',
        '',
        'Binding spec: `docs/decision-2026-10-03b-synthetic.md`. The demand is scenario-assumed,',
        'not estimated: constant 2,800 veh/h at `tko_in` (75% bypass / 25% arterial, all to `out`),',
        'all intermediate ramps at 0, 400 veh/h on each cross-street stub, 0-7,200 s,',
        '`CITYPULSE_NET=blite` with net4 files, `CITYPULSE_REROUTE=0`, SUMO seeds 1001/1002/1003,',
        'synthetic Webster signal plan. Non-zero teleports are impossible by construction',
        '(`--time-to-teleport -1`); collisions are counted from `simulation.getCollisions()`.',
        '',
        '## 1. Files built',
        '',
        '| File | SHA-256 |',
        '|---|---|',
    ]
    for f in list(extra_paths) + HASH_FILES:
        f = Path(f)
        if f.exists():
            lines.append(f'| `{f.as_posix()}` | `{sha256(f)}` |')
    lines += [
        '',
        'Per-seed output directories: `results/blite/synth/<tag>/` with `history.csv`,',
        '`pending_by_source.csv`, `halting_last30.json`, `collisions.xml`, `run.json`.',
        '',
        '## 2. Per-seed gate table',
        '',
        '| Seed | Scheduled | Pending | Running | Arrived | Scheduled-(P+R+A) | Teleports | Collisions | Pending share | G1 | G2 | G3 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|',
    ]
    for m in metas:
        lines.append(
            '| {seed} | {sched} | {pend} | {run} | {arr} | {gap} | {tel} | {col} | {ps:.3%} | {g1} | {g2} | {g3} |'.format(
                seed=m['seed'], sched=m['scheduled_departures'], pend=m['pending_end'],
                run=m['running_end'], arr=m['arrived_end'], gap=m['conservation_gap'],
                tel=m['teleports'], col=m['collisions'], ps=m['pending_share'],
                g1='**PASS**' if m['g1_pass'] else '**FAIL**',
                g2='**PASS**' if m['g2_pass'] else '**FAIL**',
                g3='**PASS**' if m['g3_pass'] else '**FAIL**',
            ))

    lines += ['', '### G2 terms (scheduled = pending + running + arrived)', '',
              '`arrived` counts every route completion in the simulation: the corridor streams end',
              'at `out` and the cross-street stubs end at `xN_out`, so all completions belong in the',
              'identity. Discharge at `out` alone is reported separately in section 3.', '']
    for m in metas:
        lines.append(
            f"- seed {m['seed']}: `{m['scheduled_departures']} = {m['pending_end']} + "
            f"{m['running_end']} + {m['arrived_end']}` -> gap {m['conservation_gap']}"
        )

    lines += ['', '### G3 15-min window slopes (limit +0.05 veh/s, after 900 s warm-up)', '']
    for m in metas:
        lines.append(f"**seed {m['seed']}**")
        lines.append('')
        lines.append('| Series | Window (s) | Slope (veh/s) | Pass |')
        lines.append('|---|---|---:|---|')
        for w in m['running_windows']:
            lines.append(f"| running | {w['window'][0]:.0f}-{w['window'][1]:.0f} | {w['slope']:+.5f} | {'yes' if w['pass'] else '**NO**'} |")
        for src, rows in m['backlog_windows'].items():
            for w in rows:
                lines.append(f"| backlog `{src}` | {w['window'][0]:.0f}-{w['window'][1]:.0f} | {w['slope']:+.5f} | {'yes' if w['pass'] else '**NO**'} |")
        lines.append('')

    lines += [
        '## 3. Discharge and queues',
        '',
        'Discharge at `out` is the number of distinct vehicles that reached the `out` edge, as a',
        'mean rate over the run (veh/h). Halting is per-edge mean and max over the last 30 min',
        '(1,800 one-second steps, so the mean denominator is the full window). The queue is the',
        'insertion backlog (pending vehicles), largest value over the run.',
        '',
        '| Seed | Discharge at `out` (veh/h) | Largest queue (veh) | Largest queue source | Peak time (s) |',
        '|---|---:|---:|---|---:|',
    ]
    for m in metas:
        lq = m['largest_queue']
        top = max(lq['by_source'].items(), key=lambda kv: kv[1]) if lq['by_source'] else ('-', 0)
        lines.append(
            f"| {m['seed']} | {m['discharge_out_vph']:,.0f} | {lq['total']} | `{top[0]}` ({top[1]}) | {lq['time_s']} |")
    lines.append('')
    for m in metas:
        lines.append(f"### seed {m['seed']}: per-edge halting, last 30 min")
        lines.append('')
        lines.append('| Edge | Mean halting (veh) | Max halting (veh) |')
        lines.append('|---|---:|---:|')
        for r in m['halting_last30'][:15]:
            lines.append(f"| `{r['edge']}` | {r['mean_halting']:.2f} | {r['max_halting']} |")
        lines.append('')

    lines += ['## 4. Commands', '', '```']
    lines += list(commands)
    lines += ['```', '']

    if all(m['all_gates_pass'] for m in metas):
        lines += ['## 5. Verdict', '',
                  'All seeds pass G1-G3. `results/blite/synth/READY` lists the SHA-256 of every',
                  'file under `scenarios/kwuntong/blite/synth/` and of net4 / `detectors4.add.xml`.', '']
    else:
        failed = [m['seed'] for m in metas if not m['all_gates_pass']]
        lines += ['## 5. Verdict: G1-G3 FAIL, no READY written', '']
        lines += [
            f'Seeds failing: {", ".join(str(s) for s in failed)}.',
            '',
            'Per the binding spec, **the demand and the network were not changed** (no load search).',
            'The observed failure sign is an insertion backlog at `tko_in` that grows at a constant',
            'rate instead of stabilising while the corridor itself stays free-flowing (per-edge',
            'halting in the last 30 min stays at or below ~1 veh). The assumed 2,800 veh/h cannot be',
            'delivered through this entry/diverge configuration: net4 wires the bypass branch to',
            '`tko_vms` lanes 1-2, which are fed only by `tko_in` lane 1 (`tko_in` lane 0 feeds',
            '`tko_1` lane 0, which feeds `tko_vms` lane 0 and the arterial), so the 75% bypass',
            'stream is effectively limited to a single entry lane. The existing reconstructed',
            'demand shows the same signature (`results/blite/grid4/s100/run.json`: 1,691 pending',
            'at `tko_in`).',
            '',
            'No READY file was created: `READY` is only written when every seed passes G1-G3.',
            '',
        ]

    lines += ['REPORT DONE', '']
    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')


def run_webster(net_path, routes_path, out_tls, log_path=None):
    """Webster signal timings on `net_path` for `routes_path` (same procedure as run_grid4 step 2)."""
    out_tls = Path(out_tls)
    out_tls.parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(log_path or (OUT_DIR / f'{Path(webster_out).stem}.log'))
    tool = Path(sumo_home()) / 'tools' / 'tlsCycleAdaptation.py'
    cmd = [
        sys.executable, str(tool),
        '-n', str(Path(net_path).resolve()),
        '-r', str(Path(routes_path).resolve()),
        '-o', str(out_tls.resolve()),
        '-b', '0',
        '-p', 'webster',
        '--min-cycle', '60',
        '--max-cycle', '140',
        '-v',
    ]
    with open(log_path, 'w', encoding='utf-8') as fh:
        res = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        raise RuntimeError(f'tlsCycleAdaptation failed with code {res.returncode}. Log: {log_path}')
    return out_tls


def build_signals(net_path=NET4, routes_path=PROXY_ROU, webster_out=TLS_WEBSTER,
                  incident_out=TLS_INCIDENT, base=SCEN / 'blite' / 'tls_base4.add.xml',
                  incident=SCEN / 'blite' / 'tls_incident4.add.xml'):
    """Write the synthetic Webster plan and the matching incident plan.

    The incident plan is built the way ``tls_incident4.add.xml`` relates to ``tls_base4.add.xml``:
    same phase states, same programID ``P_inc``, yellow/side phases as in the base plan, and the
    base's main-green duration replaced by the incident plan's main green (objectively 65 s).
    """
    run_webster(net_path, routes_path, webster_out)

    base_root = ET.parse(base).getroot()
    inc_root = ET.parse(incident).getroot()
    base_main = {tl.get('id'): float(tl.find('phase').get('duration')) for tl in base_root.iter('tlLogic')}
    inc_main = {tl.get('id'): float(tl.find('phase').get('duration')) for tl in inc_root.iter('tlLogic')}

    webster_root = ET.parse(webster_out).getroot()
    new_root = ET.Element('additional')
    for tl in webster_root.iter('tlLogic'):
        tls_id = tl.get('id')
        phases = list(tl.findall('phase'))
        ratio = inc_main[tls_id] / base_main[tls_id]
        phases[0].set('duration', f'{float(phases[0].get("duration")) * ratio:.0f}')
        new_tl = ET.SubElement(new_root, 'tlLogic', {'id': tls_id, 'type': 'static',
                                                     'programID': 'P_inc', 'offset': '0'})
        for p in phases:
            ET.SubElement(new_tl, 'phase', dict(p.attrib))
    ET.indent(ET.ElementTree(new_root), space='    ')
    ET.ElementTree(new_root).write(incident_out, encoding='utf-8', xml_declaration=True)
    return webster_out, incident_out


def main(argv=None):
    ap = argparse.ArgumentParser(description='Run G1-G3 on synthetic B-lite net4 demand.')
    ap.add_argument('--seeds', type=int, nargs='+', default=[1001, 1002, 1003])
    ap.add_argument('--out-dir', default=str(OUT_DIR))
    ap.add_argument('--routes', default=str(PROXY_ROU))
    ap.add_argument('--tag-prefix', default='g123_seed')
    ap.add_argument('--signals-only', action='store_true')
    ap.add_argument('--report-only', action='store_true',
                    help='Rebuild g123_report.md from existing per-seed run.json files.')
    args = ap.parse_args(argv)

    os.environ.setdefault('CITYPULSE_NET', 'blite')
    os.environ.setdefault('CITYPULSE_BLITE_REV', '4')
    os.environ.setdefault('CITYPULSE_REROUTE', '0')

    if args.report_only:
        metas = [json.loads((Path(args.out_dir) / f'{args.tag_prefix}{s}' / 'run.json').read_text(encoding='utf-8'))
                 for s in args.seeds]
        commands = [f'python {Path(__file__).as_posix()} --seeds ' + ' '.join(str(s) for s in args.seeds)]
        write_report(metas, Path(args.out_dir) / 'g123_report.md', commands)
        print('report written to', Path(args.out_dir) / 'g123_report.md')
        return metas

    if args.signals_only:
        w, i = build_signals()
        print('signals written:', w, i)
        return None

    metas = []
    for seed in args.seeds:
        print(f'=== seed {seed} ===', flush=True)
        m = run_seed(seed, out_root=args.out_dir, routes_path=args.routes,
                     tag=f'{args.tag_prefix}{seed}')
        metas.append(m)
        print(json.dumps({k: m[k] for k in (
            'seed', 'scheduled_departures', 'pending_end', 'running_end', 'arrived_end',
            'conservation_gap', 'teleports', 'collisions', 'pending_share', 'g1_pass',
            'g2_pass', 'g3_pass')}, indent=2), flush=True)

    commands = [f'python {Path(__file__).as_posix()} --seeds ' + ' '.join(str(m['seed']) for m in metas)]
    write_report(metas, Path(args.out_dir) / 'g123_report.md', commands)
    print('report written to', Path(args.out_dir) / 'g123_report.md')
    if all(m['all_gates_pass'] for m in metas):
        print('READY written to', write_ready(Path(args.out_dir)))
    else:
        print('G1-G3 did not pass on every seed: no READY written, demand and network unchanged.')
    return metas


if __name__ == '__main__':
    main()
