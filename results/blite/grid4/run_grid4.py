"""Predeclared scale grid runner for B-lite baseline on net4.

1. Waits for results/blite/net4/READY (at most 40 minutes, checks every 60s).
2. Applies Webster timings to net4 using tls_base4.add.xml and scale-1.0 demand -> results/blite/grid4/tls_webster4.add.xml.
3. Sweeps grid 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4 from largest down.
   Uses demand files from results/blite/grid/demand_sNNN/.
   Runs Proxy 7,200s, evaluates G1-G3.
   Stops at the first scale that passes G1-G3.
4. At that scale:
   - G4: run run_two_worlds (CITYPULSE_NET=blite, net4) 7,200s with B-lite incident, snapshot at 4800s.
         Calculate bottleneck index from observed detectors (AID02109, AID02111), threshold 3 for 2 intervals.
         Run no-incident run for false-alarm check.
   - G5: branching from t=4800 snapshot with actions A0-A4, 15-min horizon, 4 seeds, point-blockage hypothesis.
         Check VMS diverted count >= 5% of TKO stream.
         Check corridor delay mean +- sd, and >= 2 sd of paired spread.
   - If G4 or G5 fails, continue down grid.
5. Generates results/blite/grid4/report.md starting with MODEL: ... and ending with REPORT DONE.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from citypulse.config import RESULTS, SCEN, sumo_bin, sumo_home
from citypulse.sim import init_signals


def calc_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def wait_for_ready(ready_path, max_wait_sec=2400, poll_sec=60):
    ready_path = Path(ready_path)
    start_time = time.time()
    print(f"Waiting for {ready_path} (timeout: {max_wait_sec}s)...")
    while time.time() - start_time < max_wait_sec:
        if ready_path.exists():
            print(f"READY file detected at {ready_path} after {time.time() - start_time:.1f}s.")
            return True
        time.sleep(poll_sec)
    print(f"Timeout waiting for {ready_path} after {max_wait_sec}s.")
    return False


def run_webster(net_path, routes_path, out_tls, log_path=None):
    """Run SUMO tools/tlsCycleAdaptation.py to generate Webster signal plans."""
    net_path = Path(net_path).resolve()
    routes_path = Path(routes_path).resolve()
    out_tls = Path(out_tls).resolve()
    out_tls.parent.mkdir(parents=True, exist_ok=True)
    if log_path is None:
        log_path = out_tls.with_suffix('.log')
    else:
        log_path = Path(log_path).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    tool = Path(sumo_home()) / 'tools' / 'tlsCycleAdaptation.py'
    cmd = [
        sys.executable, str(tool),
        '-n', str(net_path),
        '-r', str(routes_path),
        '-o', str(out_tls),
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


def run_proxy_simulation(tag, end=7200, scale=1.0, seed=1, net_path=None, routes_path=None,
                         tls_path=None, det_path=None, vtypes_path=None, grid_root=None):
    """Run Proxy simulation for end seconds, record E1 intervals, history, halting, and evaluate G1-G3."""
    grid_root = Path(grid_root or (RESULTS / 'blite' / 'grid4')).resolve()
    directory = grid_root / tag
    directory.mkdir(parents=True, exist_ok=True)

    net_path = Path(net_path or (SCEN / 'blite' / 'net4.net.xml')).resolve()
    routes_path = Path(routes_path).resolve()
    tls_path = Path(tls_path or (grid_root / 'tls_webster4.add.xml')).resolve()
    det_path = Path(det_path or (SCEN / 'blite' / 'detectors4.add.xml')).resolve()
    vtypes_path = Path(vtypes_path or (SCEN / 'vtypes_proxy.add.xml')).resolve()

    # Create run-specific detectors4.add.xml pointing to directory/e1.xml
    e1_file = directory / 'e1.xml'
    det_tree = ET.parse(det_path)
    det_root = det_tree.getroot()
    for d in det_root:
        d.set('file', str(e1_file))
    run_det_file = directory / 'detectors4.add.xml'
    det_tree.write(run_det_file, encoding='utf-8')

    # Parse vehicles to map vid -> (entry_edge, depart_time)
    vehicles = {}
    routes_tree = ET.parse(routes_path)
    for v in routes_tree.getroot().iter('vehicle'):
        vid = v.get('id')
        dep = float(v.get('depart'))
        r = v.find('route')
        entry_edge = r.get('edges').split()[0]
        vehicles[vid] = (entry_edge, dep)

    departures = sorted(dep for _, dep in vehicles.values())
    loaded_vehicles = len(vehicles)

    cmd = [
        sumo_bin('sumo'),
        '-n', str(net_path),
        '-a', f'{vtypes_path},{run_det_file},{tls_path}',
        '-r', str(routes_path),
        '--seed', str(seed),
        '--step-length', '1',
        '--no-step-log', 'true',
        '--no-warnings', 'true',
        '--time-to-teleport', '-1',
        '--collision.action', 'warn',
        '--device.rerouting.probability', '0.3',
        '--device.rerouting.period', '60',
        '--end', str(end),
        '--error-log', str(directory / 'sumo.log'),
    ]

    import libsumo as tc
    started = time.monotonic()
    tc.start(cmd)
    init_signals(tc)

    inserted = Counter()
    arrived = 0
    teleports = 0
    history = [{'time': 0, 'running': 0, 'pending': 0, 'loaded_due': 0, 'inserted': 0, 'arrived': 0}]
    pending_by_gate = Counter()
    pending_rows = []

    last15_threshold = end - 900
    last15_step_halting = Counter()
    last15_sample_halting = Counter()
    last15_max_halting = Counter()
    last15_sample_count = 0
    last15_step_count = 0

    try:
        for k in range(1, end + 1):
            tc.simulationStep()
            for vid in tc.simulation.getDepartedIDList():
                if vid in vehicles:
                    inserted[vehicles[vid][0]] += 1
            arrived += tc.simulation.getArrivedNumber()
            teleports += tc.simulation.getStartingTeleportNumber()

            if k > last15_threshold:
                last15_step_count += 1
                for eid in tc.edge.getIDList():
                    if not eid.startswith(':'):
                        h = tc.edge.getLastStepHaltingNumber(eid)
                        if h > 0:
                            last15_step_halting[eid] += h
                            if h > last15_max_halting[eid]:
                                last15_max_halting[eid] = h

                if k % 60 == 0:
                    last15_sample_count += 1
                    for eid in tc.edge.getIDList():
                        if not eid.startswith(':'):
                            h = tc.edge.getLastStepHaltingNumber(eid)
                            if h > 0:
                                last15_sample_halting[eid] += h

            if k % 60 == 0:
                pending_vids = tc.simulation.getPendingVehicles()
                pending_counts = Counter(vehicles[vid][0] for vid in pending_vids if vid in vehicles)
                total_pending = len(pending_vids)
                due = int(np.searchsorted(departures, k, side='left'))
                running = tc.vehicle.getIDCount()

                for gate, cnt in pending_counts.items():
                    pending_rows.append({'time': k, 'gate': gate, 'pending': cnt})

                history.append({
                    'time': k,
                    'running': running,
                    'pending': total_pending,
                    'loaded_due': due,
                    'inserted': sum(inserted.values()),
                    'arrived': arrived,
                })
                pending_by_gate = pending_counts
    finally:
        tc.close()

    wall_sec = time.monotonic() - started

    with (directory / 'history.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'running', 'pending', 'loaded_due', 'inserted', 'arrived'])
        writer.writeheader()
        writer.writerows(history)

    if pending_rows:
        with (directory / 'pending.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'gate', 'pending'])
            writer.writeheader()
            writer.writerows(pending_rows)

    halting_summary = []
    all_halt_edges = set(last15_step_halting.keys()) | set(last15_sample_halting.keys())
    for eid in sorted(all_halt_edges):
        step_sum = last15_step_halting[eid]
        sample_sum = last15_sample_halting[eid]
        peak = last15_max_halting[eid]
        mean_step = step_sum / max(last15_step_count, 1)
        mean_sample = sample_sum / max(last15_sample_count, 1)
        halting_summary.append({
            'edge': eid,
            'step_sum': step_sum,
            'step_mean': round(mean_step, 2),
            'sample_sum': sample_sum,
            'sample_mean': round(mean_sample, 2),
            'peak': peak,
        })
    halting_summary.sort(key=lambda x: x['step_sum'], reverse=True)
    (directory / 'halting_last15.json').write_text(json.dumps(halting_summary, indent=2), encoding='utf-8')

    running_end = history[-1]['running']
    pending_end = history[-1]['pending']
    total_inserted = sum(inserted.values())

    g1_pass = (teleports == 0)
    internal_acc_err = abs(total_inserted - (arrived + running_end))
    pending_acc_err = abs(loaded_vehicles - (total_inserted + pending_end))
    g2_pass = (internal_acc_err == 0 and pending_acc_err <= 5)

    pending_share = pending_end / max(loaded_vehicles, 1)
    last_15 = [h for h in history if h['time'] >= end - 900]
    if len(last_15) >= 2:
        running_slope = float(np.polyfit([h['time'] for h in last_15], [h['running'] for h in last_15], 1)[0])
        pending_slope = float(np.polyfit([h['time'] for h in last_15], [h['pending'] for h in last_15], 1)[0])
    else:
        running_slope, pending_slope = 0.0, 0.0

    queue_growing = pending_slope > 0.05 or running_slope > 0.1
    g3_pass = (pending_share <= 0.02) and not queue_growing

    run_meta = {
        'tag': tag,
        'scale': scale,
        'duration_s': end,
        'wall_seconds': round(wall_sec, 3),
        'loaded_vehicles': loaded_vehicles,
        'inserted': total_inserted,
        'arrived': arrived,
        'running_end': running_end,
        'pending_end': pending_end,
        'pending_share_end': pending_share,
        'teleports': teleports,
        'accounting_reconciled': g2_pass,
        'internal_accounting_error': internal_acc_err,
        'pending_accounting_error': pending_acc_err,
        'running_last15_slope': running_slope,
        'pending_last15_slope': pending_slope,
        'pending_by_gate_end': dict(pending_by_gate),
        'top_halting_edges': halting_summary[:10],
        'g1_pass': bool(g1_pass),
        'g2_pass': bool(g2_pass),
        'g3_pass': bool(g3_pass),
        'all_gates_pass': bool(g1_pass and g2_pass and g3_pass),
    }

    (directory / 'run.json').write_text(json.dumps(run_meta, indent=2), encoding='utf-8')
    return run_meta


def geh(m, c):
    if m + c <= 0:
        return 0.0
    return math.sqrt(2.0 * ((m - c) ** 2) / (m + c))


def evaluate_calibration_gap(run_dir, profile_path, detector_map_path):
    run_dir = Path(run_dir)
    e1_path = run_dir / 'e1.xml'
    profile = json.loads(Path(profile_path).read_text(encoding='utf-8'))
    det_map = json.loads(Path(detector_map_path).read_text(encoding='utf-8'))
    mapped_ids = {d['id'] for d in det_map['mapped']}

    tree = ET.parse(e1_path)
    root = tree.getroot()
    intervals_by_det = Counter()
    sum_flow = Counter()
    weighted_speed = Counter()
    speed_vol = Counter()
    sum_occ = Counter()
    occ_counts = Counter()

    for interval in root.iter('interval'):
        begin = float(interval.get('begin'))
        end = float(interval.get('end'))
        if begin < 3600 or end > 7200:
            continue
        det_id_full = interval.get('id')
        aid = det_id_full.rsplit('_', 1)[0]
        if aid not in mapped_ids:
            continue

        n_veh = int(interval.get('nVehContrib', 0))
        speed = float(interval.get('speed', -1.0))
        occ = float(interval.get('occupancy', 0.0))

        bin_idx = int((begin - 3600) // 300)
        bin_time = f'08:{bin_idx * 5:02d}'
        key = (aid, bin_time)

        intervals_by_det[key] += 1
        sum_flow[key] += n_veh
        if speed >= 0 and n_veh > 0:
            weighted_speed[key] += speed * n_veh
            speed_vol[key] += n_veh
        sum_occ[key] += occ
        occ_counts[key] += 1

    sim = {}
    for key in intervals_by_det:
        aid, tm = key
        flow_vph = sum_flow[key] * 12.0
        avg_speed_kmh = (weighted_speed[key] / speed_vol[key] * 3.6) if speed_vol[key] > 0 else np.nan
        avg_occ = sum_occ[key] / max(occ_counts[key], 1)
        sim[key] = {
            'flow_vph': flow_vph,
            'speed_kmh': avg_speed_kmh,
            'occ': avg_occ,
        }

    rows = []
    for minute in range(0, 60, 5):
        tm = f'08:{minute:02d}'
        for aid in sorted(mapped_ids):
            p = profile.get(aid, {}).get(tm)
            if not p or (aid, tm) not in sim:
                continue
            s = sim[aid, tm]
            obs_flow = p['flow_vph']['median']
            sim_flow = s['flow_vph']
            g = geh(sim_flow, obs_flow)
            obs_speed = p['speed_kmh']['median'] if p.get('speed_kmh') else None
            sim_speed = s['speed_kmh']
            spd_err = abs(sim_speed - obs_speed) if (obs_speed is not None and np.isfinite(sim_speed)) else np.nan
            obs_occ = p['occ']['median'] if p.get('occ') else None
            sim_occ = s['occ']
            occ_err = abs(sim_occ - obs_occ) if obs_occ is not None else np.nan
            obs_cong = (obs_speed is not None and obs_speed < 30 and obs_occ is not None and obs_occ > 20)
            sim_cong = (sim_speed is not None and sim_speed < 30 and sim_occ > 20)
            cong_agree = (obs_cong == sim_cong)

            rows.append({
                'detector': aid,
                'bin_start': tm,
                'obs_flow': obs_flow,
                'sim_flow': sim_flow,
                'geh': g,
                'obs_speed': obs_speed,
                'sim_speed': sim_speed,
                'speed_error': spd_err,
                'obs_occ': obs_occ,
                'sim_occ': sim_occ,
                'occ_error': occ_err,
                'congestion_agreement': cong_agree,
            })

    gehs = [r['geh'] for r in rows]
    spd_errs = [r['speed_error'] for r in rows if np.isfinite(r['speed_error'])]
    cong_agrees = [r['congestion_agreement'] for r in rows]

    gap_summary = {
        'total_cells': len(rows),
        'geh_lt5_share': float(np.mean([g < 5.0 for g in gehs])) if gehs else 0.0,
        'speed_mae': float(np.mean(spd_errs)) if spd_errs else 0.0,
        'congestion_agreement': float(np.mean(cong_agrees)) if cong_agrees else 0.0,
    }
    (run_dir / 'gap_metrics.json').write_text(json.dumps(gap_summary, indent=2), encoding='utf-8')
    return gap_summary


def compute_bottleneck_index(t_df, u="AID02109", d="AID02111", t_cal=(600, 4200)):
    """Divergence statistic on observed data only (residual = observation - Twin)."""
    a = t_df[t_df.detector == u].set_index("t")
    b = t_df[t_df.detector == d].set_index("t")
    out = {}
    for name, x in (("U", a), ("D", b)):
        for k in ("o", "v"):
            r = x[f"obs_{k}"] - x[f"twin_{k}"]
            cal = r.loc[t_cal[0]:t_cal[1]].dropna()
            mad = 1.4826 * np.median(np.abs(cal - cal.median()))
            if mad == 0 or np.isnan(mad):
                mad = 1.0
            med = cal.median() if len(cal) > 0 else 0.0
            out[f"r_{name}_{k}"] = (r - med) / mad
    B = 0.5 * (out["r_U_o"] - out["r_D_o"]) + 0.5 * (out["r_D_v"].fillna(0) - out["r_U_v"].fillna(0))
    return B, out


def evaluate_crossing(B, threshold=3.0, consecutive=2):
    """Find first time B >= threshold for `consecutive` intervals."""
    B_sorted = B.dropna().sort_index()
    times = B_sorted.index.tolist()
    vals = B_sorted.values.tolist()
    count = 0
    first_time = None
    for t_step, v in zip(times, vals):
        if v >= threshold:
            count += 1
            if count >= consecutive:
                first_time = t_step
                break
        else:
            count = 0
    return first_time, B_sorted


def evaluate_g4_g5_at_scale(scale, tag, grid_root, demand_dir):
    """Evaluate G4 (incident visibility) and G5 (intervention authority) at the chosen scale."""
    import pandas as pd
    from citypulse.branching.engine import run_branches

    grid_root = Path(grid_root)
    demand_dir = Path(demand_dir)
    routes_proxy = demand_dir / 'proxy.rou.xml'
    routes_twin = demand_dir / 'twin_cand.rou.xml'

    inc_run_name = f"{tag}_twoworld_incident"
    noinc_run_name = f"{tag}_twoworld_noincident"
    inc_run_dir = grid_root / inc_run_name
    noinc_run_dir = grid_root / noinc_run_name

    env = dict(os.environ)
    env["CITYPULSE_NET"] = "blite"
    env["CITYPULSE_BLITE_REV"] = "4"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"

    print(f"\n[G4] Running two_worlds with incident for 7,200s (scale {scale}, snapshot 4800s)...")
    cmd_inc = [
        sys.executable, "-m", "citypulse.experiments.run_two_worlds",
        "--run", f"blite/grid4/{inc_run_name}",
        "--t-end", "7200",
        "--port", "5567",
        "--twin-snapshot", "4800",
        "--routes", str(routes_proxy),
        "--twin-routes", str(routes_twin),
    ]
    t0 = time.time()
    subprocess.run(cmd_inc, env=env, check=True, cwd=REPO_ROOT)
    inc_wall = time.time() - t0
    print(f"Incident two_worlds completed in {inc_wall:.1f}s.")

    print(f"\n[G4] Running two_worlds without incident for 7,200s (false-alarm check)...")
    cmd_noinc = [
        sys.executable, "-m", "citypulse.experiments.run_two_worlds",
        "--run", f"blite/grid4/{noinc_run_name}",
        "--t-end", "7200",
        "--port", "5569",
        "--no-incident",
        "--routes", str(routes_proxy),
        "--twin-routes", str(routes_twin),
    ]
    t0 = time.time()
    subprocess.run(cmd_noinc, env=env, check=True, cwd=REPO_ROOT)
    noinc_wall = time.time() - t0
    print(f"No-incident two_worlds completed in {noinc_wall:.1f}s.")

    # Compute bottleneck index
    t_inc = pd.read_parquet(inc_run_dir / "twin" / "twin_log.parquet")
    t_noinc = pd.read_parquet(noinc_run_dir / "twin" / "twin_log.parquet")

    B_inc, _ = compute_bottleneck_index(t_inc, u="AID02109", d="AID02111", t_cal=(600, 4200))
    B_noinc, _ = compute_bottleneck_index(t_noinc, u="AID02109", d="AID02111", t_cal=(600, 4200))

    crossing_time_inc, b_inc_series = evaluate_crossing(B_inc, threshold=3.0, consecutive=2)
    crossing_time_noinc, b_noinc_series = evaluate_crossing(B_noinc, threshold=3.0, consecutive=2)

    g4_detected = (crossing_time_inc is not None and crossing_time_inc >= 4500)
    g4_no_false_alarm = (crossing_time_noinc is None)
    g4_pass = bool(g4_detected and g4_no_false_alarm)

    g4_details = {
        "scale": scale,
        "tag": tag,
        "incident_start_s": 4500.0,
        "incident_crossing_time_s": crossing_time_inc,
        "noincident_crossing_time_s": crossing_time_noinc,
        "false_alarm": (crossing_time_noinc is not None),
        "g4_pass": g4_pass,
        "inc_wall_s": round(inc_wall, 1),
        "noinc_wall_s": round(noinc_wall, 1),
    }
    print(f"G4 Evaluation: detected at t={crossing_time_inc}s, false_alarm={crossing_time_noinc is not None}, PASS={g4_pass}")

    # G5 (intervention authority)
    print(f"\n[G5] Running branching from snapshot at t=4800s (actions A0-A4, 4 seeds, 15-min horizon)...")
    snap_state = inc_run_dir / "twin" / "twin_state_4800.xml.gz"
    snap_meta = inc_run_dir / "twin" / "twin_state_4800.json"

    HYP_BLOCK = {
        "edge": "ktb_n1",
        "lanes_closed": [0, 1],
        "mode": "blocker",
        "pos": 755.3,
        "duration": 3600,
        "source": "midpoint of observed detectors AID02109 (455.7m) and AID02111 (1054.9m)",
    }
    ACTIONS = ["A0", "A1", "A2", "A3", "A4"]
    SEEDS = [2, 3, 4, 5]

    branch_results = {}
    for s in SEEDS:
        res, wall_b = run_branches(snap_state, snap_meta, ACTIONS, horizons=[900], hypothesis=HYP_BLOCK, seed=s, workers=1)
        branch_results[s] = res

    # Analyze G5
    # 1. VMS diverted count
    a2_diverted = [next(r["n_diverted"] for r in branch_results[s] if r["action"] == "A2") for s in SEEDS]
    mean_a2_diverted = float(np.mean(a2_diverted))

    # TKO stream over 15 min [4800, 5700]:
    tree_twin = ET.parse(routes_twin)
    tko_stream_15m = 0
    for v in tree_twin.getroot().iter('vehicle'):
        dep = float(v.get('depart'))
        if 4800 <= dep <= 5700:
            r = v.find('route')
            if r is not None and r.get('edges').split()[0] == 'tko_in':
                tko_stream_15m += 1

    vms_share = (mean_a2_diverted / max(tko_stream_15m, 1))
    vms_diverted_pass = bool(vms_share >= 0.05)

    # 2. Corridor delay per action mean +- sd
    action_stats = {}
    corr_delays_by_action = {}
    for a in ACTIONS:
        vals = [next(r["kpis"][900]["corridor_delay_vh"] for r in branch_results[s] if r["action"] == a) for s in SEEDS]
        corr_delays_by_action[a] = vals
        action_stats[a] = {
            "mean": float(np.mean(vals)),
            "sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
            "values": vals,
        }

    # 3. Paired seed spread: difference against A0 per seed
    a0_vals = corr_delays_by_action["A0"]
    action_diff_stats = {}
    significant_actions = []
    for a in ["A1", "A2", "A3", "A4"]:
        diffs = [corr_delays_by_action[a][i] - a0_vals[i] for i in range(len(SEEDS))]
        mean_diff = float(np.mean(diffs))
        sd_paired = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
        threshold_diff = 2.0 * sd_paired
        is_sig = abs(mean_diff) > threshold_diff
        action_diff_stats[a] = {
            "mean_diff": mean_diff,
            "paired_sd": sd_paired,
            "threshold": threshold_diff,
            "significant": bool(is_sig),
        }
        if is_sig:
            significant_actions.append(a)

    g5_pass = bool(vms_diverted_pass and len(significant_actions) > 0)

    g5_details = {
        "scale": scale,
        "tag": tag,
        "tko_stream_15m": tko_stream_15m,
        "mean_a2_diverted": mean_a2_diverted,
        "vms_diverted_share": vms_share,
        "vms_diverted_pass": vms_diverted_pass,
        "action_stats": action_stats,
        "action_diff_stats": action_diff_stats,
        "significant_actions": significant_actions,
        "g5_pass": g5_pass,
    }
    print(f"G5 Evaluation: VMS share={vms_share*100:.1f}%, significant_actions={significant_actions}, PASS={g5_pass}")

    eval_summary = {
        "scale": scale,
        "tag": tag,
        "g4": g4_details,
        "g5": g5_details,
        "all_gates_pass": bool(g4_pass and g5_pass),
    }
    (grid_root / f"{tag}_gates_g4_g5.json").write_text(json.dumps(eval_summary, indent=2), encoding="utf-8")
    return eval_summary


def generate_final_report(grid_results, chosen_scale_data, out_path):
    """Generate results/blite/grid4/report.md matching required specifications."""
    out_path = Path(out_path)
    lines = [
        "MODEL: Gemini 3.8 Flash\n",
        "# B-lite Predeclared Scale Grid Report on Network net4\n",
        "## 1. Overview\n",
        "This report documents the baseline evaluation of the B-lite simplified research model on network net4 (`scenarios/kwuntong/blite/net4.net.xml`), featuring a lane-preserving merge M. Baseline acceptance gates G1–G5 are evaluated across the predeclared scale grid (**1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4**) per the decision rule in `docs/decision-2026-10-03.md`.\n",
        "Signal timings were generated via SUMO's `tlsCycleAdaptation.py` using `tls_base4.add.xml` (program \"0\" with yellows) as the base and scale-1.0 demand, written scenarios-free to `results/blite/grid4/tls_webster4.add.xml`. All simulation runs use 7,200 s duration, teleport disabled (`--time-to-teleport -1`), collision action warn, and dynamic rerouting (prob=0.3, period=60s).\n",
        "---",
        "",
        "## 2. Predeclared Scale Grid Evaluation (Gates G1–G3)\n",
        "| Scale | Tag | Loaded | Inserted | Arrived | Running (end) | Pending (end) | Pending Share | Teleports | Accounting Reconciled | Running Slope (vps) | Pending Slope (vps) | G1 | G2 | G3 | Overall G1–G3 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for item in grid_results:
        m = item['meta']
        sc = m['scale']
        tag = m['tag']
        loaded = f"{m['loaded_vehicles']:,}"
        ins = f"{m['inserted']:,}"
        arr = f"{m['arrived']:,}"
        run_end = f"{m['running_end']:,}"
        pend_end = f"{m['pending_end']:,}"
        pend_share = f"{m['pending_share_end']*100:.1f}%"
        tele = m['teleports']
        acc = "**PASS**" if m['accounting_reconciled'] else "**FAIL**"
        r_slope = f"{m['running_last15_slope']:+.4f}"
        p_slope = f"{m['pending_last15_slope']:+.4f}"
        g1 = "**PASS**" if m['g1_pass'] else "**FAIL**"
        g2 = "**PASS**" if m['g2_pass'] else "**FAIL**"
        g3 = "**PASS**" if m['g3_pass'] else "**FAIL**"
        overall = "**PASS**" if m['all_gates_pass'] else "**FAIL**"
        lines.append(f"| **{sc}** | `{tag}` | {loaded} | {ins} | {arr} | {run_end} | {pend_end} | {pend_share} | {tele} | {acc} | {r_slope} | {p_slope} | {g1} | {g2} | {g3} | {overall} |")

    lines.extend([
        "",
        "### G1–G3 Gate Definitions:",
        "- **G1 (Zero teleports):** 0 teleports recorded.",
        "- **G2 (Vehicle accounting):** `inserted == arrived + running_end` and `abs(loaded - (inserted + pending_end)) <= 5`.",
        "- **G3 (Insertion queue stability):** `pending_share <= 2.0%` and no growing queue (`pending_slope <= 0.05` and `running_slope <= 0.1`).",
        "",
        "---",
        "",
        "## 3. Calibration Gap (08:00–09:00, Informational Only)\n",
        "Evaluated across the 21 mapped TD detectors over twelve 5-minute intervals (252 cells):",
        "",
        "| Scale | Evaluated Cells | GEH < 5 Share | Speed MAE (km/h) | Congestion State Agreement |",
        "|---|---|---|---|---|",
    ])

    for item in grid_results:
        m = item['meta']
        gap = item['gap']
        sc = m['scale']
        cells = gap['total_cells']
        geh_sh = f"{gap['geh_lt5_share']*100:.2f}%"
        spd_mae = f"{gap['speed_mae']:.2f} km/h"
        cong_agr = f"{gap['congestion_agreement']*100:.2f}%"
        lines.append(f"| **{sc}** | {cells} | {geh_sh} | {spd_mae} | {cong_agr} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Gates G4 and G5 Details\n",
    ])

    if chosen_scale_data is not None:
        sc = chosen_scale_data['scale']
        tag = chosen_scale_data['tag']
        g4 = chosen_scale_data['g4']
        g5 = chosen_scale_data['g5']

        lines.extend([
            f"### Evaluated at Scale {sc} (`{tag}`):\n",
            "#### Gate G4: Incident Visibility",
            "- **Incident Section:** `ktb_n1` (lanes 0, 1 blocked, pos 900 m, $t = 4,500–5,400$ s)",
            "- **Observed Detector Pair:** Upstream `AID02109` (@ 455.7 m), Downstream `AID02111` (@ 1054.9 m) (`AID02110` hidden by 1-in-3 sensor emulator rule)",
            f"- **Pre-incident Calibration Window:** $t = 600–4,200$ s",
            f"- **Detection Criterion:** Divergence index $B(t) \\ge 3.0$ for 2 consecutive 30-s intervals",
            f"- **Incident Crossing Time:** $t = {g4['incident_crossing_time_s']} $ s ({'detected during incident' if g4['incident_crossing_time_s'] and g4['incident_crossing_time_s'] >= 4500 else 'not detected'})",
            f"- **No-incident False Alarm Check:** {'No crossing observed (0 false alarms)' if not g4['false_alarm'] else 'False alarm crossing detected'}",
            f"- **Gate G4 Result:** **{'PASS' if g4['g4_pass'] else 'FAIL'}**\n",
            "#### Gate G5: Intervention Authority",
            f"- **Snapshot Source:** Twin state saved at $t = 4,800$ s from the scale {sc} incident run",
            f"- **Evaluation Setup:** Actions A0–A4, 15-min horizon (900 s), 4 seeds (2, 3, 4, 5)",
            f"- **Capacity Loss Hypothesis:** Point-blockage on `ktb_n1` at midpoint of observed detector segment (pos 755.3 m), lanes 0 and 1 closed",
            f"- **VMS Diverted Reach:** {g5['mean_a2_diverted']:.1f} veh ({g5['vms_diverted_share']*100:.1f}% of TKO stream {g5['tko_stream_15m']} veh; required $\\ge 5\\%$) -> **{'PASS' if g5['vms_diverted_pass'] else 'FAIL'}**",
            "",
            "Corridor Delay ($veh\\cdot h$) across 4 seeds:",
            "",
            "| Action | Description | Mean Delay ($veh\\cdot h$) | Std Dev | Difference vs A0 | Paired Spread ($2\\cdot \\sigma_{paired}$) | Significant ($> 2\\sigma_{paired}$)? |",
            "|---|---|---:|---:|---:|---:|---|",
        ])

        act_desc = {
            "A0": "Do nothing (re-open baseline)",
            "A1": "Predefined incident signal timing (P_inc)",
            "A2": "VMS diversion at tko_vms via corridor B",
            "A3": "Combined A1 + A2",
            "A4": "VMS diversion with strong messaging (boosted compliance)",
        }
        for a in ["A0", "A1", "A2", "A3", "A4"]:
            st_a = g5['action_stats'][a]
            m_del = f"{st_a['mean']:.2f}"
            sd_del = f"{st_a['sd']:.2f}"
            if a == "A0":
                lines.append(f"| **{a}** | {act_desc[a]} | {m_del} | {sd_del} | baseline | — | — |")
            else:
                df = g5['action_diff_stats'][a]
                m_diff = f"{df['mean_diff']:+.2f}"
                p_thresh = f"{df['threshold']:.2f}"
                sig = "**YES**" if df['significant'] else "NO"
                lines.append(f"| **{a}** | {act_desc[a]} | {m_del} | {sd_del} | {m_diff} | {p_thresh} | {sig} |")

        lines.extend([
            "",
            f"- **Gate G5 Result:** **{'PASS' if g5['g5_pass'] else 'FAIL'}**\n",
        ])
    else:
        lines.append("No scale passed Gates G1–G3, so Gates G4 and G5 were not reached.\n")

    lines.extend([
        "---",
        "",
        "## 5. Frozen Candidate Decision and Artifacts\n",
    ])

    if chosen_scale_data is not None and chosen_scale_data.get('all_gates_pass'):
        sc = chosen_scale_data['scale']
        tag = chosen_scale_data['tag']
        demand_dir = RESULTS / "blite" / "grid" / f"demand_{tag}"
        net_path = SCEN / "blite" / "net4.net.xml"
        proxy_rou = demand_dir / "proxy.rou.xml"
        twin_cand = demand_dir / "twin_cand.rou.xml"
        tls_webster = RESULTS / "blite" / "grid4" / "tls_webster4.add.xml"
        tls_base = SCEN / "blite" / "tls_base4.add.xml"
        tls_incident = SCEN / "blite" / "tls_incident4.add.xml"
        det_path = SCEN / "blite" / "detectors4.add.xml"
        det_map_path = SCEN / "blite" / "detector_map.json"

        lines.extend([
            f"**CHOSEN BASELINE SCALE:** **{sc}** (`{tag}`)\n",
            "All baseline acceptance gates G1–G5 pass at this scale.\n",
            "### Frozen Candidate Files & Hashes (SHA-256):\n",
            "| Component | File Path | SHA-256 Checksum |",
            "|---|---|---|",
            f"| **Network** | `{net_path.as_posix()}` | `{calc_sha256(net_path)}` |",
            f"| **Signal Plan (Webster)** | `{tls_webster.as_posix()}` | `{calc_sha256(tls_webster)}` |",
            f"| **Signal Plan (Base 0)** | `{tls_base.as_posix()}` | `{calc_sha256(tls_base)}` |",
            f"| **Signal Plan (Incident P_inc)** | `{tls_incident.as_posix()}` | `{calc_sha256(tls_incident)}` |",
            f"| **Detectors Additional** | `{det_path.as_posix()}` | `{calc_sha256(det_path)}` |",
            f"| **Detector Map** | `{det_map_path.as_posix()}` | `{calc_sha256(det_map_path)}` |",
            f"| **Proxy Demand** | `{proxy_rou.as_posix()}` | `{calc_sha256(proxy_rou)}` |",
            f"| **Twin Candidates** | `{twin_cand.as_posix()}` | `{calc_sha256(twin_cand)}` |",
            "",
            "### Predeclared Seeds and Simulation Parameters:\n",
            "- **Simulation Duration:** `7,200 s`",
            "- **Proxy Simulation Seed:** `1`",
            "- **Twin Simulation Seed:** `2`",
            "- **Twin Demand RNG Seed:** `202`",
            "- **Sensor Seed:** `77`",
            "- **Branching Seeds:** `[2, 3, 4, 5]`",
            "- **Device Rerouting Probability:** `0.3`, **Period:** `60 s`",
            "- **Time to Teleport:** `-1` (disabled)",
            "- **Collision Action:** `warn`",
        ])
    else:
        lines.append("**Decision:** no scale passes all gates G1–G5.\n")

    lines.extend([
        "",
        "REPORT DONE\n"
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {out_path}")


def main():
    grid_root = Path(RESULTS / 'blite' / 'grid4').resolve()
    grid_root.mkdir(parents=True, exist_ok=True)
    obs_profile = Path(RESULTS / 'obs' / 'obs_profile.json').resolve()
    det_map = Path(SCEN / 'blite' / 'detector_map.json').resolve()
    net4 = Path(SCEN / 'blite' / 'net4.net.xml').resolve()
    tls_webster4 = grid_root / 'tls_webster4.add.xml'
    ready_file = Path(RESULTS / 'blite' / 'net4' / 'READY').resolve()

    # Step 1: Wait for READY file
    print("=== Step 1: Waiting for net4 READY signal ===")
    if not wait_for_ready(ready_file, max_wait_sec=2400, poll_sec=30):
        print("READY file not found within budget. Terminating.")
        report_file = grid_root / "report.md"
        report_file.write_text("MODEL: Gemini 3.8 Flash\n\nresults/blite/net4/READY did not appear within 40 minutes.\n\nREPORT DONE\n", encoding="utf-8")
        sys.exit(1)

    # Step 2: Generate Webster signal plan on net4 using scale 1.0 demand
    print("\n=== Step 2: Applying Webster Timings on net4 ===")
    d100_dir = Path(RESULTS / 'blite' / 'grid' / 'demand_s100').resolve()
    if not tls_webster4.exists():
        print(f"Running tlsCycleAdaptation for Webster timings on net4 using {d100_dir / 'proxy.rou.xml'}...")
        run_webster(net4, d100_dir / 'proxy.rou.xml', tls_webster4)
    print(f"Webster signal plan ready: {tls_webster4}")

    # Step 3: Predeclared Scale Grid Evaluation
    GRID_SCALES = [
        (1.0, "s100"),
        (0.9, "s090"),
        (0.8, "s080"),
        (0.7, "s070"),
        (0.6, "s060"),
        (0.5, "s050"),
        (0.4, "s040"),
    ]

    grid_results = []
    chosen_scale_data = None

    for sc, tag in GRID_SCALES:
        print(f"\n==================================================")
        print(f"=== Evaluating Grid Scale {sc} ({tag}) on net4 ===")
        print(f"==================================================")
        scale_demand_dir = Path(RESULTS / 'blite' / 'grid' / f"demand_{tag}").resolve()

        run_dir = grid_root / tag
        meta = run_proxy_simulation(tag, end=7200, scale=sc, seed=1, net_path=net4,
                                    routes_path=scale_demand_dir / 'proxy.rou.xml',
                                    tls_path=tls_webster4, grid_root=grid_root)
        gap = evaluate_calibration_gap(run_dir, obs_profile, det_map)
        grid_results.append({'meta': meta, 'gap': gap})

        print(f"Scale {sc} ({tag}): Pending={meta['pending_end']} ({meta['pending_share_end']*100:.1f}%), "
              f"P_slope={meta['pending_last15_slope']:+.4f}, R_slope={meta['running_last15_slope']:+.4f}, "
              f"G1={meta['g1_pass']}, G2={meta['g2_pass']}, G3={meta['g3_pass']} -> Overall G1-G3: {meta['all_gates_pass']}")

        if meta['all_gates_pass']:
            print(f"\n>>> Scale {sc} ({tag}) PASSED G1-G3! Evaluating G4 & G5...")
            eval_g4_g5 = evaluate_g4_g5_at_scale(sc, tag, grid_root, scale_demand_dir)
            if eval_g4_g5['all_gates_pass']:
                print(f"\n>>> Scale {sc} ({tag}) PASSED ALL GATES G1-G5! Freezing baseline at scale {sc}.")
                chosen_scale_data = {
                    'scale': sc,
                    'tag': tag,
                    'g4': eval_g4_g5['g4'],
                    'g5': eval_g4_g5['g5'],
                    'all_gates_pass': True,
                }
                break
            else:
                print(f">>> Scale {sc} ({tag}) FAILED G4 or G5. Continuing down grid...")
                chosen_scale_data = {
                    'scale': sc,
                    'tag': tag,
                    'g4': eval_g4_g5['g4'],
                    'g5': eval_g4_g5['g5'],
                    'all_gates_pass': False,
                }

    # Step 4: Write final report
    report_file = grid_root / "report.md"
    generate_final_report(grid_results, chosen_scale_data, report_file)


if __name__ == "__main__":
    main()
