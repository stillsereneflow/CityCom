"""B-lite demand builder: 1-D flow balance, 15-min slices, congested entry and diverge split."""
import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np

from citypulse.config import RESULTS, SCEN

# Corridor structure grounded in docs/blite-spec.md
EDGES_BYPASS = ['ktb_w1', 'ktb_w2', 'ktb_w3', 'ktb_n1', 'ktb_n2']
DETS_BYPASS = [
    ['AID02105'],
    ['AID02106', 'AID02107'],
    ['AID02108'],
    ['AID02109', 'AID02110', 'AID02111'],
    ['AID02112', 'AID02113', 'AID02114', 'AID02115']
]

EDGES_ARTERIAL = ['tko_a1', 'ktr_w1', 'ktr_w2', 'ktr_w3', 'ktr_w4', 'ktr_w5', 'ktr_w6']
DETS_ARTERIAL = [
    ['AID07107'],
    ['AID07108'],
    ['AID07109'],
    ['AID07110'],
    ['AID07111', 'AID07112'],
    ['AID07113'],
    ['AID07114']
]

CROSS_STREETS = ['x1', 'x2', 'x3', 'x4']
DEFAULT_CROSS_STREET_VPH = 400.0
RAMP_CAPACITY_VPH = 1800.0


def extract_slice_detector_targets(profile, slice_idx, detectors):
    """Extract 15-minute slice flow, p75, speed and occupancy for given detectors."""
    t0 = slice_idx * 900
    times = [f'{7 + (t0 + i * 300) // 3600:02d}:{(t0 + i * 300) % 3600 // 60:02d}' for i in range(3)]
    targets = {}
    for d in detectors:
        rows = [profile.get(d, {}).get(t) for t in times if t in profile.get(d, {})]
        good = [r for r in rows if r and r.get('speed_kmh') and r.get('occ')]
        cong = any(r['speed_kmh']['median'] < 30 and r['occ']['median'] > 20 for r in good)
        med = float(np.mean([r['flow_vph']['median'] for r in rows])) if rows else 0.0
        p75 = float(np.mean([r['flow_vph']['p75'] for r in rows])) if rows else 0.0
        targets[d] = {
            'id': d,
            'available': bool(rows),
            'congested': cong,
            'flow': med,
            'p75': p75,
        }
    return targets


def determine_congested_entry(median, p75, congested, target=None):
    """Entry tko_in from AID07105: congested, so median bounded by p75."""
    if not congested:
        flow = median
        gate_class = 'measured'
        basis = f'direct detector on gate edge, uncongested; flow = {flow:.1f} veh/h'
    else:
        lower = median
        upper = max(p75, median)
        if target is not None:
            flow = float(np.clip(target, lower, upper))
        else:
            flow = upper
        gate_class = 'measured_congested'
        basis = f'direct detector on gate edge, congested; demand in [{lower:.1f}, {upper:.1f}] veh/h'
    return {
        'flow_vph': float(flow),
        'class': gate_class,
        'lower_vph': float(median if congested else median),
        'upper_vph': float(p75 if congested else median),
        'basis': basis,
        'congested': bool(congested),
    }


def fit_diverge_split(bypass_target, arterial_target, entry_flow=None, entry_bounds=None,
                      bypass_ramp_net=0.0, arterial_ramp_net=0.0):
    """Least-squares diverge split fitting to bypass and arterial targets."""
    eff_b = max(0.0, bypass_target - bypass_ramp_net)
    eff_a = max(0.0, arterial_target - arterial_ramp_net)
    denom = eff_b + eff_a
    if denom > 0:
        alpha = eff_b / denom
    else:
        alpha = 0.5

    if entry_flow is not None:
        f_in = entry_flow
    elif entry_bounds is not None:
        low, high = entry_bounds
        f_in = float(np.clip(denom, low, high))
    else:
        f_in = denom

    f_b = alpha * f_in
    f_a = (1.0 - alpha) * f_in
    return {
        'alpha': float(alpha),
        'entry_flow': float(f_in),
        'bypass_flow': float(f_b),
        'arterial_flow': float(f_a),
    }


def compute_ramp_balance(flow_upstream, flow_downstream, cong_u=False, cong_v=False, lanes=1):
    """1-D flow balance between consecutive main edges.
    Positive balance feeds on-ramp, negative balance feeds off-ramp.
    Congested or missing detector leaves ramp assumed [0, 1800 x lanes].
    """
    cap = lanes * RAMP_CAPACITY_VPH
    if cong_u or cong_v:
        return {
            'on_vph': 0.0,
            'off_vph': 0.0,
            'class': 'assumed',
            'range': [0.0, cap],
            'basis': f'congested or missing bracketing detector; declared range [0, {cap:.0f}] veh/h',
        }
    delta = flow_downstream - flow_upstream
    if delta > 0:
        return {
            'on_vph': float(delta),
            'off_vph': 0.0,
            'class': 'inferred',
            'range': [0.0, cap],
            'basis': f'observed balance (downstream - upstream) = {delta:.1f} veh/h',
        }
    elif delta < 0:
        return {
            'on_vph': 0.0,
            'off_vph': float(-delta),
            'class': 'inferred',
            'range': [0.0, cap],
            'basis': f'observed balance (upstream - downstream) = {-delta:.1f} veh/h',
        }
    else:
        return {
            'on_vph': 0.0,
            'off_vph': 0.0,
            'class': 'inferred',
            'range': [0.0, cap],
            'basis': 'zero balance between bracketing detectors',
        }


def solve_corridor_ramps(edge_chain, det_chain, det_targets, start_flow):
    """Solve ramps along a main edge chain and track flowing mixture."""
    ramps = []
    cur_flow = start_flow
    stream = {'start': start_flow}  # origin -> remaining flow
    od_flows = defaultdict(float)

    for i in range(1, len(edge_chain)):
        u, v = edge_chain[i - 1], edge_chain[i]
        dets_u, dets_v = det_chain[i - 1], det_chain[i]
        cong_u = any(det_targets[d]['congested'] for d in dets_u)
        cong_v = any(det_targets[d]['congested'] for d in dets_v)
        flow_v = float(np.mean([det_targets[d]['flow'] for d in dets_v]))

        bal = compute_ramp_balance(cur_flow, flow_v, cong_u, cong_v)
        on_ramp = f'on_{v}'
        off_ramp = f'off_{u}'

        ramps.append({
            'edge': on_ramp,
            'type': 'on',
            'between': [u, v],
            'flow_vph': bal['on_vph'],
            'class': bal['class'] if bal['on_vph'] > 0 else ('inferred' if bal['class'] == 'inferred' else 'assumed'),
            'range': bal['range'],
            'basis': bal['basis'],
        })
        ramps.append({
            'edge': off_ramp,
            'type': 'off',
            'between': [u, v],
            'flow_vph': bal['off_vph'],
            'class': bal['class'] if bal['off_vph'] > 0 else ('inferred' if bal['class'] == 'inferred' else 'assumed'),
            'range': bal['range'],
            'basis': bal['basis'],
        })

        if bal['off_vph'] > 0:
            tot = sum(stream.values())
            if tot > 0:
                frac = min(1.0, bal['off_vph'] / tot)
                for orig in list(stream.keys()):
                    out_f = stream[orig] * frac
                    od_flows[orig, off_ramp] += out_f
                    stream[orig] -= out_f
                    if stream[orig] <= 1e-9:
                        del stream[orig]
            cur_flow -= bal['off_vph']

        if bal['on_vph'] > 0:
            stream[on_ramp] = stream.get(on_ramp, 0.0) + bal['on_vph']
            cur_flow += bal['on_vph']

    for orig, rem in stream.items():
        od_flows[orig, 'out'] += rem

    return ramps, od_flows, cur_flow


def build_slice_demand(profile, slice_idx, scale=1.0):
    """Build all entry, split, ramp and cross-street demands for one 15-min slice."""
    all_dets = set(['AID07105', 'AID07106'])
    for ds in DETS_BYPASS + DETS_ARTERIAL:
        all_dets.update(ds)
    targets = extract_slice_detector_targets(profile, slice_idx, all_dets)

    # 1. Entry tko_in
    e_det = targets['AID07105']
    target_sum = targets['AID02105']['flow'] + targets['AID07107']['flow']
    entry = determine_congested_entry(e_det['flow'], e_det['p75'], e_det['congested'], target=target_sum)

    # 2. Split at diverge D
    q_b1 = targets['AID02105']['flow']
    q_a1 = targets['AID07107']['flow']
    split = fit_diverge_split(q_b1, q_a1, entry_flow=entry['flow_vph'])

    # 3. Ramps and OD flows along Bypass and Arterial
    ramps_b, od_b, end_b = solve_corridor_ramps(EDGES_BYPASS, DETS_BYPASS, targets, split['bypass_flow'])
    ramps_a, od_a, end_a = solve_corridor_ramps(EDGES_ARTERIAL, DETS_ARTERIAL, targets, split['arterial_flow'])

    # Map generic 'start' origin back to tko_in with route tags
    od_matrix = defaultdict(float)
    for (orig, dest), fl in od_b.items():
        o = 'tko_in_bypass' if orig == 'start' else orig
        od_matrix[o, dest] += fl
    for (orig, dest), fl in od_a.items():
        o = 'tko_in_arterial' if orig == 'start' else orig
        od_matrix[o, dest] += fl

    # 4. Cross streets S1-S4
    cross_stubs = []
    for x in CROSS_STREETS:
        xin, xout = f'{x}_in', f'{x}_out'
        fl = DEFAULT_CROSS_STREET_VPH
        cross_stubs.append({
            'edge': xin,
            'exit': xout,
            'flow_vph': fl,
            'class': 'assumed',
            'range': [0.0, 3600.0],
            'basis': f'scenario-assumed {fl:.0f} veh/h per stub',
        })
        od_matrix[xin, xout] += fl

    total_in = entry['flow_vph'] + sum(r['flow_vph'] for r in ramps_b if r['type'] == 'on') + \
               sum(r['flow_vph'] for r in ramps_a if r['type'] == 'on') + len(CROSS_STREETS) * DEFAULT_CROSS_STREET_VPH
    total_out = sum(fl for (o, d), fl in od_matrix.items() if d == 'out') + \
                sum(r['flow_vph'] for r in ramps_b if r['type'] == 'off') + \
                sum(r['flow_vph'] for r in ramps_a if r['type'] == 'off') + \
                len(CROSS_STREETS) * DEFAULT_CROSS_STREET_VPH

    return {
        'slice_index': slice_idx,
        'start_s': slice_idx * 900,
        'end_s': (slice_idx + 1) * 900,
        'entry': entry,
        'split': {
            'bypass_edge': 'ktb_w1',
            'arterial_edge': 'tko_a1',
            'alpha_bypass': split['alpha'],
            'alpha_arterial': 1.0 - split['alpha'],
            'bypass_flow_vph': split['bypass_flow'],
            'arterial_flow_vph': split['arterial_flow'],
            'method': 'least_squares',
            'basis': 'fitted per slice by least squares to AID02105 / AID07107',
        },
        'ramps': ramps_b + ramps_a,
        'cross_streets': cross_stubs,
        'od_flows': {f'{o}->{d}': fl for (o, d), fl in od_matrix.items()},
        'summary': {
            'total_inflow_vph': total_in,
            'total_outflow_vph': total_out,
            'conservation_delta': total_in - total_out,
        }
    }


def get_route_edges(origin, destination):
    """Reconstruct exact edge sequence for an origin-destination pair in B-lite."""
    if origin.startswith('x') and destination.startswith('x'):
        return [origin, destination]

    # Handle tko_in entries
    if origin.startswith('tko_in'):
        prefix = ['tko_in', 'tko_1', 'tko_vms']
        if 'bypass' in origin:
            corridor = EDGES_BYPASS
        else:
            corridor = EDGES_ARTERIAL
        if destination == 'out':
            return prefix + corridor + ['rejoin', 'out']
        # Off-ramp destination: off_<upstream>
        off_up = destination.replace('off_', '')
        idx = corridor.index(off_up)
        return prefix + corridor[:idx + 1] + [destination]

    # Handle on-ramp entries
    on_down = origin.replace('on_', '')
    if on_down in EDGES_BYPASS:
        corridor = EDGES_BYPASS
    else:
        corridor = EDGES_ARTERIAL

    idx_start = corridor.index(on_down)
    if destination == 'out':
        return [origin] + corridor[idx_start:] + ['rejoin', 'out']

    off_up = destination.replace('off_', '')
    idx_end = corridor.index(off_up)
    return [origin] + corridor[idx_start:idx_end + 1] + [destination]


def generate_demand_files(profile_path, out_dir, scale=1.0, proxy_seed=1001, twin_seed=2202):
    """Generate proxy.rou.xml, twin_cand.rou.xml, and demand.json."""
    profile = json.loads(Path(profile_path).read_text(encoding='utf-8'))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    slices_data = []
    for s in range(8):
        slices_data.append(build_slice_demand(profile, s, scale=scale))

    # Write demand.json
    demand_json_data = {
        'meta': {
            'scale': scale,
            'time_start': '07:00',
            'time_end': '09:00',
            'slices': 8,
            'slice_duration_s': 900,
            'proxy_seed': proxy_seed,
            'twin_seed': twin_seed,
            'twin_cand_scale': 1.5,
        },
        'slices': slices_data,
    }
    (out_dir / 'demand.json').write_text(json.dumps(demand_json_data, indent=2), encoding='utf-8')

    # Generate routes for Proxy and Twin
    for world, seed, cand_scale, vtype, prefix in [
        ('proxy', proxy_seed, 1.0, 'pdist', 'p'),
        ('twin', twin_seed, 1.5, 'tdist', 't'),
    ]:
        rng = np.random.default_rng(seed)
        vehicles = []
        for s_idx, s_data in enumerate(slices_data):
            t_start = s_data['start_s']
            t_end = s_data['end_s']
            dur = t_end - t_start

            for od_key, flow_vph in s_data['od_flows'].items():
                orig, dest = od_key.split('->')
                edges = get_route_edges(orig, dest)
                expected_n = flow_vph * (dur / 3600.0) * scale * cand_scale
                n_veh = rng.poisson(expected_n)
                if n_veh > 0:
                    departs = rng.uniform(t_start, t_end, n_veh)
                    for dep in departs:
                        vehicles.append((float(dep), edges))

        vehicles.sort(key=lambda x: x[0])
        root = ET.Element('routes')
        for i, (dep, edges) in enumerate(vehicles):
            v = ET.SubElement(
                root, 'vehicle',
                id=f'{prefix}{i}',
                depart=f'{dep:.3f}',
                type=vtype,
                departLane='best',
                departSpeed='max'
            )
            ET.SubElement(v, 'route', edges=' '.join(edges))

        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        out_filename = 'proxy.rou.xml' if world == 'proxy' else 'twin_cand.rou.xml'
        tree.write(out_dir / out_filename, encoding='utf-8', xml_declaration=True)

    return demand_json_data


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build B-lite demand.')
    ap.add_argument('--scale', type=float, default=1.0, help='Demand multiplier scale')
    ap.add_argument('--out-dir', default=str(SCEN / 'blite' / 'demand'), help='Output demand directory')
    ap.add_argument('--profile', default=str(RESULTS / 'obs' / 'obs_profile.json'), help='Observation profile JSON')
    ap.add_argument('--proxy-seed', type=int, default=1001, help='Proxy demand RNG seed')
    ap.add_argument('--twin-seed', type=int, default=2202, help='Twin demand RNG seed')
    args = ap.parse_args(argv)

    generate_demand_files(args.profile, args.out_dir, scale=args.scale,
                          proxy_seed=args.proxy_seed, twin_seed=args.twin_seed)
    print(f'Demand generated successfully in {args.out_dir} at scale {args.scale}')


if __name__ == '__main__':
    main()
