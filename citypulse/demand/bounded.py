# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Independent, profile-fitted boundary OD realizations; no internal spawning."""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import numpy as np
import sumolib

from citypulse.config import RESULTS, SCEN
from citypulse.network.bounded import NET, OUT, adjacent, save, sha
from citypulse.scenario import CONTROL
from citypulse.demand.bounded_gates import gate_priors


def candidates(net, gates, mapped, seed):
    rng = np.random.default_rng(seed)
    starts = [g['edge'] for g in gates if g['direction'] == 'entry' and g['authorized_source']]
    ends = [g['edge'] for g in gates if g['direction'] == 'exit' and g['authorized_source']]
    vias = sorted({d['edge'] for d in mapped})
    rng.shuffle(vias)
    routes = set()
    cache = {}

    def path(a, b):
        if (a, b) not in cache:
            p, cost = net.getFastestPath(net.getEdge(a), net.getEdge(b), vClass='passenger')
            cache[a, b] = (tuple(e.getID() for e in p), cost) if p else ((), 1e9)
        return cache[a, b]

    for a in starts:
        for b in ends:
            base, cost = path(a, b)
            if not base or a == b:
                continue
            options = [base]
            for v in vias:
                left, lc = path(a, v)
                right, rc = path(v, b)
                if left and right and lc + rc <= max(cost * 1.8, cost + 180):
                    options.append(left + right[1:])
            # Explicit intervention alternatives with the same OD, including full arterial path.
            left, _ = path(a, CONTROL['vms_edge'])
            right, _ = path(CONTROL['rejoin_edge'], b)
            if left and right:
                options.append(left + tuple(CONTROL['corridor_b'][1:]) + right[1:])
                mid1, _ = path(CONTROL['vms_edge'], CONTROL['vms_target_edge'])
                mid2, _ = path(CONTROL['vms_target_edge'], CONTROL['rejoin_edge'])
                if mid1 and mid2:
                    options.append(left + mid1[1:] + mid2[1:] + right[1:])
            for r in options:
                if len(set(r)) == len(r) and any(d['edge'] in r for d in mapped):
                    routes.add(r)
    # Independent candidate populations retain one randomly chosen geometry for each
    # (OD, detector signature, bypass/arterial) class. Shared infrastructure is public.
    groups = defaultdict(list)
    for r in sorted(routes):
        signature = tuple(d['id'] for d in mapped if d['edge'] in r)
        groups[r[0], r[-1], signature, CONTROL['vms_target_edge'] in r].append(r)
    return [rs[int(rng.integers(len(rs)))] for rs in groups.values()]


def slice_targets(profile, mapped, start):
    values = []
    for d in mapped:
        rows = [profile.get(d['id'], {}).get(f'{7 + t // 3600:02d}:{t % 3600 // 60:02d}')
                for t in range(start, start + 900, 300)]
        rows = [r for r in rows if r]
        good = [r for r in rows if r.get('speed_kmh')]
        congestion = any(r['speed_kmh']['median'] < 30 and r['occ']['median'] > 20 for r in good)
        values.append({'id': d['id'], 'edge': d['edge'], 'available': bool(rows),
                       'congested': congestion,
                       'flow': float(np.mean([r['flow_vph']['median'] for r in rows])) if rows else 0,
                       'p75': float(np.mean([r['flow_vph']['p75'] for r in rows])) if rows else 0})
    return values


def fit(matrix, targets, prior, arrival_factor, feedback=None, regularization=0.03, gate_data=None):
    # Congested counts are discharge, excluded from static count equality. A boundary
    # arrival lower-bound scenario uses upper-quartile discharge, explicitly not identified.
    from scipy.optimize import minimize
    y = np.array([x['flow'] for x in targets])
    valid = np.array([x['available'] and not x['congested'] for x in targets])
    if feedback is not None:
        y *= feedback
    scale = np.sqrt(np.maximum(y, 120))
    a, b = matrix[valid] / scale[valid, None], y[valid] / scale[valid]
    if gate_data is not None:
        gm, gy, weight = gate_data
        gs = np.sqrt(np.maximum(gy, 120) / weight)
        a, b = np.vstack([a, gm / gs[:, None]]), np.concatenate([b, gy / gs])
    lower = np.array([x['p75'] * arrival_factor if x['congested'] else 0 for x in targets])
    c = matrix / np.sqrt(np.maximum(lower, 120))[:, None]
    low = lower / np.sqrt(np.maximum(lower, 120))
    # Prior is uniform over identified OD/signature classes; regularization keeps alternatives.
    def objective(x):
        res = a @ x - b
        short = np.minimum(c @ x - low, 0)
        delta = x - prior
        return (res @ res + short @ short + regularization * np.sum(delta * delta / (prior + 1)),
                2 * (a.T @ res + c.T @ short + regularization * delta / (prior + 1)))
    result = minimize(objective, prior, jac=True, bounds=[(0, None)] * len(prior),
                      method='L-BFGS-B', options={'maxiter': 1200, 'ftol': 1e-10})
    return result.x, {'success': bool(result.success), 'message': str(result.message),
                      'objective': float(result.fun), 'max_negative': float(max(0, -result.x.min()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    ap.add_argument('--world', choices=['proxy', 'twin'], default='proxy')
    ap.add_argument('--arrival-factor', type=float, default=1.1)
    ap.add_argument('--regularization', type=float, default=0.03)
    ap.add_argument('--feedback', help='Prior simulation directory, calibration medians only')
    ap.add_argument('--gate-weight', type=float, default=0, help='Weight of uncertain local flow-balance priors')
    args = ap.parse_args()
    # Reuse already-installed local SciPy; never writes into the shared interpreter.
    sys.path.insert(0, str(RESULTS / 'astra_step1' / 'packages'))
    directory = OUT / args.tag
    directory.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((OUT / 'network.json').read_text(encoding='utf-8'))
    profile = json.loads((RESULTS / 'obs' / 'obs_profile.json').read_text())
    net = sumolib.net.readNet(str(NET))
    mapped = [d for d in json.loads((SCEN / 'detector_map.json').read_text())['mapped'] if net.hasEdge(d['edge'])]
    seed = 1101 if args.world == 'proxy' else 2202
    rng = np.random.default_rng(seed + 77)
    routes = candidates(net, metadata['gates'], mapped, seed)
    matrix = np.array([[float(d['edge'] in r) for r in routes] for d in mapped])
    assert len(routes) and np.all(matrix.sum(axis=1) > 0), 'Uncovered retained detector'
    prior = np.full(len(routes), 30.0)
    feedback = None
    if args.feedback:
        import pandas as pd
        bins = pd.read_csv(OUT / args.feedback / 'bins.csv')
        feedback = bins.set_index(['detector', 'bin_start'])['flow_vph'].to_dict()
    vehicles, slices, gate_rows = [], [], []
    candidate_root = ET.Element('routes')
    for i, r in enumerate(routes):
        ET.SubElement(candidate_root, 'route', id=f'{args.world}_c{i}', edges=' '.join(r))
    ET.ElementTree(candidate_root).write(directory / 'candidates.rou.xml', encoding='utf-8')
    for start in range(0, 7200, 900):
        targets = slice_targets(profile, mapped, start)
        correction = None
        if feedback is not None:
            correction = []
            for x in targets:
                vals = [feedback.get((x['id'], f'{7 + t // 3600:02d}:{t % 3600 // 60:02d}'))
                        for t in range(start, start + 900, 300)]
                vals = [v for v in vals if v is not None]
                correction.append(float(np.clip(x['flow'] / max(np.mean(vals), 120), 0.7, 1.4)) if vals else 1)
            correction = np.array(correction)
        priors = gate_priors(net, metadata['gates'], mapped, targets, args.arrival_factor)
        gate_data = None
        if args.gate_weight:
            usable = [g for g in priors if g['near'] and g['direction'] == 'entry']
            gm = np.array([[float(r[0] == g['edge']) for r in routes] for g in usable])
            gate_data = gm, np.array([g['prior_vph'] for g in usable]), args.gate_weight
        weights, solver = fit(matrix, targets, prior, args.arrival_factor, correction, args.regularization, gate_data)
        fitted = matrix @ weights
        slices.append({'start': start, 'end': start + 900, 'solver': solver, 'targets': [
            {**x, 'planned_vph': float(q)} for x, q in zip(targets, fitted)]})
        gate_rates = defaultdict(float)
        scale = 1 if args.world == 'proxy' else 1.5
        for r, q in zip(routes, weights):
            gate_rates['entry', r[0]] += q
            gate_rates['exit', r[-1]] += q
            for depart in rng.uniform(start, start + 900, rng.poisson(q * 0.25 * scale)):
                vehicles.append((float(depart), r))
        for g, estimate in zip(metadata['gates'], priors):
            gate_rows.append({**g, 'start': start, 'vph': gate_rates[g['direction'], g['edge']],
                              'flow_balance_prior': estimate})
    root = ET.Element('routes')
    prefix = 'p' if args.world == 'proxy' else 't'
    for i, (depart, route) in enumerate(sorted(vehicles)):
        v = ET.SubElement(root, 'vehicle', id=f'{prefix}{i}', depart=f'{depart:.3f}',
                          type='pdist' if prefix == 'p' else 'tdist', departLane='best', departSpeed='max')
        ET.SubElement(v, 'route', edges=' '.join(route))
    ET.ElementTree(root).write(directory / 'demand.rou.xml', encoding='utf-8')
    save(directory / 'demand.json', {'tag': args.tag, 'world': args.world, 'seed': seed,
         'arrival_factor': args.arrival_factor, 'regularization': args.regularization,
         'gate_weight': args.gate_weight,
         'feedback': args.feedback, 'candidate_count': len(routes), 'vehicles': len(vehicles),
         'profile_sha256': sha(RESULTS / 'obs' / 'obs_profile.json'), 'network_sha256': sha(NET),
         'code_sha256': {str(p): sha(p) for p in (__file__, __import__('citypulse.demand.bounded_gates', fromlist=['x']).__file__)},
         'route_sha256': sha(directory / 'demand.rou.xml'), 'slices': slices, 'gates': gate_rows,
         'congested_arrivals': 'p75 discharge times scenario factor is a lower-bound prior, not an arrival measurement',
         'twin_contract': 'Independent seed/candidate selection/Poisson departures; TwinDemandStream(path=..., scale=1.5), stream seed 202'})
    print(args.tag, len(routes), 'candidates', len(vehicles), 'vehicles')


if __name__ == '__main__':
    main()
