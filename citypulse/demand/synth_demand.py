"""Synthetic boundary demand builder for the B-lite net4 benchmark (decision 2026-10-03b).

The demand is *scenario-assumed*, not estimated:

* constant 2,800 veh/h at ``tko_in``, 75% to the bypass corridor and 25% to the
  arterial corridor, all ending at ``out``;
* every intermediate on/off ramp at 0;
* 400 veh/h on each cross-street stub ``xN_in`` straight across to ``xN_out``;
* horizon 0-7,200 s in eight 900 s slices.

The route/vehicle writing code is shared with :mod:`citypulse.demand.blite_demand`
(``generate_demand_files`` / ``get_route_edges``), so the Twin Poisson-thinning stream
consumes ``twin_cand.rou.xml`` unchanged.

A demand-shock control ``proxy_shock.rou.xml`` is identical except that ``tko_in`` is
+30% (3,640 veh/h, same split) from 4,500 to 5,400 s.
"""
import argparse
import json
from collections import defaultdict, deque
from pathlib import Path

from citypulse.config import SCEN
from citypulse.demand.blite_demand import (
    CROSS_STREETS,
    DEFAULT_CROSS_STREET_VPH,
    DETS_ARTERIAL,
    DETS_BYPASS,
    EDGES_ARTERIAL,
    EDGES_BYPASS,
    determine_congested_entry,
    fit_diverge_split,
    get_route_edges,
    solve_corridor_ramps,
)

# Scenario-assumed boundary conditions (decision 2026-10-03b).
TKO_IN_VPH = 2800.0
BYPASS_SHARE = 0.75
HORIZON_S = 7200.0
SLICE_S = 900.0
N_SLICES = 8

SHOCK_START_S = 4500.0
SHOCK_END_S = 5400.0
SHOCK_FACTOR = 1.30

PROXY_SEED = 1001
TWIN_SEED = 2202
TWIN_CAND_SCALE = 1.5

ENTRY_DETECTOR = 'AID07105'

SYNTH_DIR = SCEN / 'blite' / 'synth'
NET4 = SCEN / 'blite' / 'net4.net.xml'

# --- net5 (decision 2026-10-03c): the same synthetic demand with the insertion stub ------
SYNTH5_DIR = SCEN / 'blite' / 'synth5'
NET5 = SCEN / 'blite' / 'net5.net.xml'
INSERT_EDGE = 'tko_insert'
TKO_ENTRY = 'tko_in'
# route files copied into synth5/; the signal plans are copied byte-for-byte because the
# net5 link indices at S1-S4 are identical to net4's (tls_base5 == tls_base4).
SYNTH5_ROUTE_FILES = ('proxy.rou.xml', 'proxy_shock.rou.xml', 'twin_cand.rou.xml')
SYNTH5_TLS_FILES = ('tls_webster_synth.add.xml', 'tls_incident_synth.add.xml')

_NET_CACHE = {}
_PAIR_CACHE = {}


def _net(net_path=NET4):
    """Lazily read net4 with sumolib (cached)."""
    key = str(net_path)
    if key not in _NET_CACHE:
        import sumolib
        _NET_CACHE[key] = sumolib.net.readNet(key)
    return _NET_CACHE[key]


def _intermediate_edges(u, v, net_path=NET4):
    """Shortest external-edge path from edge `u` to edge `v` in the network (BFS)."""
    key = (str(net_path), u, v)
    if key in _PAIR_CACHE:
        return _PAIR_CACHE[key]
    net = _net(net_path)
    queue = deque([(u, [u])])
    seen = {u}
    path = None
    while queue:
        cur, p = queue.popleft()
        if cur == v:
            path = p
            break
        for e in net.getEdge(cur).getOutgoing():
            nid = e.getID()
            if nid.startswith(':') or nid in seen:
                continue
            seen.add(nid)
            queue.append((nid, p + [nid]))
    if path is None:
        raise ValueError(f'no path between edges {u!r} and {v!r} in {net_path}')
    _PAIR_CACHE[key] = path
    return path


def expand_corridor_edges(edges, net_path=NET4):
    """Expand a chain of external corridor edges into a route SUMO accepts.

    ``blite_demand.get_route_edges`` returns the corridor chain without the lane-level
    merge/diverge edges that net4 inserts (``ms_*``, ``dv_*``); SUMO rejects such a route
    ("no connection between edge X and edge Y").  This inserts the missing edges, which
    reproduces the route shapes of the existing ``scenarios/kwuntong/blite/demand`` files.
    """
    full = [edges[0]]
    for u, v in zip(edges, edges[1:]):
        full.extend(_intermediate_edges(u, v, net_path)[1:])
    return full


def route_edges(origin, destination, net_path=NET4):
    """``get_route_edges`` output expanded to a network-valid edge sequence."""
    return expand_corridor_edges(get_route_edges(origin, destination), net_path=net_path)


def synthetic_targets(tko_in_vph=TKO_IN_VPH, bypass_share=BYPASS_SHARE):
    """Detector-target dict that drives the shared corridor solver at the assumed boundaries.

    ``AID07105`` (the ``tko_in`` gate loop) is declared congested with
    ``median == p75 == tko_in_vph``, so :func:`determine_congested_entry` takes the entry
    verbatim.  Every corridor detector downstream of the diverge carries the *post-split*
    flow, so the 1-D balance in :func:`solve_corridor_ramps` reports zero ramps everywhere.
    """
    entry = float(tko_in_vph)
    bypass = entry * bypass_share
    arterial = entry * (1.0 - bypass_share)

    targets = {
        ENTRY_DETECTOR: {
            'id': ENTRY_DETECTOR,
            'available': True,
            'congested': True,
            'flow': entry,
            'p75': entry,
        },
    }
    for dets, flow in ((DETS_BYPASS, bypass), (DETS_ARTERIAL, arterial)):
        for chain in dets:
            for d in chain:
                targets[d] = {
                    'id': d,
                    'available': True,
                    'congested': False,
                    'flow': flow,
                    'p75': flow,
                }
    return targets


def synthetic_slice(slice_idx, *, tko_in_vph=TKO_IN_VPH, bypass_share=BYPASS_SHARE):
    """Build one 900 s slice of the assumed demand with the shared B-lite machinery.

    The per-slice ``flow_vph`` fields hold the hourly boundary rates; the route writer
    scales them by ``dur / 3600`` exactly as ``blite_demand.generate_demand_files`` does.
    """
    targets = synthetic_targets(tko_in_vph=tko_in_vph, bypass_share=bypass_share)
    entry = determine_congested_entry(
        targets[ENTRY_DETECTOR]['flow'], targets[ENTRY_DETECTOR]['p75'],
        targets[ENTRY_DETECTOR]['congested'],
        target=targets[ENTRY_DETECTOR]['flow'],
    )
    split = fit_diverge_split(
        bypass_target=targets[DETS_BYPASS[0][0]]['flow'],
        arterial_target=targets[DETS_ARTERIAL[0][0]]['flow'],
        entry_flow=entry['flow_vph'],
    )
    ramps_b, od_b, _ = solve_corridor_ramps(EDGES_BYPASS, DETS_BYPASS, targets, split['bypass_flow'])
    ramps_a, od_a, _ = solve_corridor_ramps(EDGES_ARTERIAL, DETS_ARTERIAL, targets, split['arterial_flow'])

    od_matrix = defaultdict(float)
    for (orig, dest), fl in od_b.items():
        o = 'tko_in_bypass' if orig == 'start' else orig
        od_matrix[o, dest] += fl
    for (orig, dest), fl in od_a.items():
        o = 'tko_in_arterial' if orig == 'start' else orig
        od_matrix[o, dest] += fl

    cross_stubs = []
    for x in CROSS_STREETS:
        fl = DEFAULT_CROSS_STREET_VPH
        cross_stubs.append({
            'edge': f'{x}_in',
            'exit': f'{x}_out',
            'flow_vph': fl,
            'class': 'assumed',
            'range': [0.0, 3600.0],
            'basis': f'scenario-assumed {fl:.0f} veh/h per stub',
        })
        od_matrix[f'{x}_in', f'{x}_out'] += fl

    t_start = slice_idx * SLICE_S
    t_end = (slice_idx + 1) * SLICE_S
    return {
        'slice_index': slice_idx,
        'start_s': t_start,
        'end_s': t_end,
        'entry': entry,
        'split': {
            'bypass_edge': 'ktb_w1',
            'arterial_edge': 'tko_a1',
            'alpha_bypass': split['alpha'],
            'alpha_arterial': 1.0 - split['alpha'],
            'bypass_flow_vph': split['bypass_flow'],
            'arterial_flow_vph': split['arterial_flow'],
            'method': 'scenario-assumed fixed split',
            'basis': f'{bypass_share:.0%} bypass / {1.0 - bypass_share:.0%} arterial, all to out',
        },
        'ramps': ramps_b + ramps_a,
        'cross_streets': cross_stubs,
        'od_flows': {f'{o}->{d}': fl for (o, d), fl in od_matrix.items()},
        'summary': {
            'total_inflow_vph': float(entry['flow_vph'] + len(CROSS_STREETS) * DEFAULT_CROSS_STREET_VPH),
            'total_outflow_vph': float(sum(fl for (_, d), fl in od_matrix.items() if d == 'out')
                                       + len(CROSS_STREETS) * DEFAULT_CROSS_STREET_VPH),
        },
    }


def build_synthetic_slices(shock=False):
    """Eight constant slices; the shock variant scales ``tko_in`` over 4,500-5,400 s by +30%."""
    slices = []
    for i in range(N_SLICES):
        start = i * SLICE_S
        end = (i + 1) * SLICE_S
        entry = TKO_IN_VPH
        if shock and start >= SHOCK_START_S and end <= SHOCK_END_S:
            entry = TKO_IN_VPH * SHOCK_FACTOR
        s = synthetic_slice(i, tko_in_vph=entry)
        s['shock'] = bool(entry != TKO_IN_VPH)
        slices.append(s)
    return slices


def slices_to_demand_json(slices, proxy_seed=PROXY_SEED, twin_seed=TWIN_SEED,
                          twin_cand_scale=TWIN_CAND_SCALE, tag='synth', shock=False):
    return {
        'meta': {
            'model': 'synthetic boundary demand, decision 2026-10-03b',
            'tag': tag,
            'time_start': '00:00',
            'time_end': '02:00',
            'horizon_s': HORIZON_S,
            'slices': N_SLICES,
            'slice_duration_s': SLICE_S,
            'proxy_seed': proxy_seed,
            'twin_seed': twin_seed,
            'twin_cand_scale': twin_cand_scale,
            'tko_in_vph': TKO_IN_VPH,
            'bypass_share': BYPASS_SHARE,
            'arterial_share': 1.0 - BYPASS_SHARE,
            'intermediate_ramps_vph': 0.0,
            'cross_street_vph': DEFAULT_CROSS_STREET_VPH,
            'shock': {
                'start_s': SHOCK_START_S,
                'end_s': SHOCK_END_S,
                'factor': SHOCK_FACTOR,
                'tko_in_vph': TKO_IN_VPH * SHOCK_FACTOR,
            } if shock else None,
        },
        'slices': slices,
    }


def write_synthetic_slices(out_dir, slices, proxy_seed, twin_seed, tag='synth', shock=False):
    """Write proxy.rou.xml and twin_cand.rou.xml for a slice list, plus demand.json.

    Mirrors :func:`citypulse.demand.blite_demand.generate_demand_files`: the same Poisson
    draw order over the same OD keys, so the Twin candidate pool stays a 1.5x superset
    stream in the format the Twin thinning code already reads.
    """
    import xml.etree.ElementTree as ET

    import numpy as np

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for world, seed, cand_scale, vtype, prefix in [
        ('proxy', proxy_seed, 1.0, 'pdist', 'p'),
        ('twin', twin_seed, TWIN_CAND_SCALE, 'tdist', 't'),
    ]:
        rng = np.random.default_rng(seed)
        vehicles = []
        for s_data in slices:
            t_start = s_data['start_s']
            t_end = s_data['end_s']
            dur = t_end - t_start
            for od_key, flow_vph in s_data['od_flows'].items():
                orig, dest = od_key.split('->')
                edges = route_edges(orig, dest)
                expected_n = flow_vph * (dur / 3600.0) * cand_scale
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

    demand_json_data = slices_to_demand_json(slices, proxy_seed=proxy_seed, twin_seed=twin_seed,
                                             tag=tag, shock=shock)
    (out_dir / 'demand.json').write_text(json.dumps(demand_json_data, indent=2), encoding='utf-8')
    return demand_json_data


def generate_synth_files(out_dir=None, proxy_seed=PROXY_SEED, twin_seed=TWIN_SEED):
    """Write proxy.rou.xml, twin_cand.rou.xml, proxy_shock.rou.xml and demand.json."""
    out_dir = Path(out_dir or SYNTH_DIR)
    slices = build_synthetic_slices(shock=False)
    demand = write_synthetic_slices(out_dir, slices, proxy_seed, twin_seed)

    # Demand-shock control: same stream, +30% at tko_in over 4,500-5,400 s.
    shock_slices = build_synthetic_slices(shock=True)
    shock_root = out_dir / '_shock'
    write_synthetic_slices(shock_root, shock_slices, proxy_seed, twin_seed, tag='shock', shock=True)
    (out_dir / 'proxy_shock.rou.xml').write_bytes((shock_root / 'proxy.rou.xml').read_bytes())
    (out_dir / 'demand_shock.json').write_bytes((shock_root / 'demand.json').read_bytes())
    for leftover in ('proxy.rou.xml', 'twin_cand.rou.xml', 'demand.json'):
        (shock_root / leftover).unlink(missing_ok=True)
    shock_root.rmdir()
    return demand


def build_synth5(src_dir=None, out_dir=None):
    """Copy the synthetic route files with ``tko_insert`` prepended to every TKO route.

    Every vehicle whose route starts at ``tko_in`` (the corridor entry) gets the 500 m
    insertion stub in front of it and the net5 departure settings
    (``departLane="free"``, ``departSpeed="max"``); cross-street vehicles are untouched.
    Scheduled departure time, vehicle class, destination and the vehicle count are preserved
    exactly, and the function asserts that against the ``synth/`` source files.  The two
    signal plans are copied byte-for-byte (net5 does not move any link index).
    """
    import xml.etree.ElementTree as ET

    src_dir = Path(src_dir or SYNTH_DIR)
    out_dir = Path(out_dir or SYNTH5_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name in SYNTH5_ROUTE_FILES:
        tree = ET.parse(src_dir / name)
        root = tree.getroot()
        before = {}
        tko = 0
        for v in root.iter('vehicle'):
            route = v.find('route')
            edges = route.get('edges').split()
            before[v.get('id')] = (float(v.get('depart')), v.get('type'), edges[0], edges[-1])
            if edges[0] == TKO_ENTRY:
                route.set('edges', ' '.join([INSERT_EDGE] + edges))
                v.set('departLane', 'free')
                v.set('departSpeed', 'max')
                tko += 1
        ET.indent(tree, space='  ')
        tree.write(out_dir / name, encoding='utf-8', xml_declaration=True)

        after = ET.parse(out_dir / name).getroot()
        seen = {}
        for v in after.iter('vehicle'):
            edges = v.find('route').get('edges').split()
            seen[v.get('id')] = (float(v.get('depart')), v.get('type'), edges[0], edges[-1],
                                 v.get('departLane'), v.get('departSpeed'))
        assert set(seen) == set(before), f'{name}: vehicle ids changed'
        for vid, (dep, typ, src_edge, dest) in before.items():
            got = seen[vid]
            assert got[0] == dep and got[1] == typ and got[3] == dest, \
                f'{name}: {vid} depart/type/destination changed'
            if src_edge == TKO_ENTRY:
                assert got[2] == INSERT_EDGE, f'{name}: {vid} missing {INSERT_EDGE}'
                assert got[4] == 'free' and got[5] == 'max', f'{name}: {vid} departure settings'
            else:
                assert got[2] == src_edge, f'{name}: {vid} first edge {got[2]} != {src_edge}'
        stats[name] = {'vehicles': len(before), 'tko_routes': tko}
    for name in SYNTH5_TLS_FILES:
        (out_dir / name).write_bytes((src_dir / name).read_bytes())
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build synthetic B-lite net4 boundary demand.')
    ap.add_argument('--out-dir', default=str(SYNTH_DIR), help='Output directory')
    ap.add_argument('--proxy-seed', type=int, default=PROXY_SEED)
    ap.add_argument('--twin-seed', type=int, default=TWIN_SEED)
    ap.add_argument('--net5', action='store_true',
                    help='build scenarios/kwuntong/blite/synth5/ from the synth/ files '
                         '(tko_insert prepended to every TKO route)')
    args = ap.parse_args(argv)

    if args.net5:
        stats = build_synth5()
        for name, s in stats.items():
            print(f'{name}: {s["vehicles"]} vehicles, {s["tko_routes"]} TKO routes -> '
                  f'{INSERT_EDGE} prepended')
        print(f'synth5 written to {SYNTH5_DIR}')
        return stats

    generate_synth_files(out_dir=args.out_dir, proxy_seed=args.proxy_seed, twin_seed=args.twin_seed)
    print(f'Synthetic demand written to {args.out_dir}')
    return None


if __name__ == '__main__':
    main()
