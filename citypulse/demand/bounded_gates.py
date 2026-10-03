# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Observable gate priors from adjacent detector cross sections, with explicit uncertainty."""
from collections import defaultdict

import numpy as np

from citypulse.network.bounded import adjacent


# Standard saturation-flow assumption: 1,800 veh/h per lane.
ENTRY_LANE_CAPACITY_VPH = 1800
NAMES = ('Kwun Tong Bypass', 'Kwun Tong Road', 'Kai Fuk Road', 'Tseung Kwan O Road')
CORRIDOR_TYPES = ('highway.motorway', 'highway.trunk', 'highway.primary')


def is_corridor_road(edge):
    name = edge.getName() or ''
    t = edge.getType() or ''
    return any(s in name for s in NAMES) or any(t.startswith(prefix) for prefix in CORRIDOR_TYPES)


def cross_sections(net, edge, mapped, incoming=False):
    """Nearest detector on each connecting branch, stopping at the first cross section."""
    by_edge = defaultdict(list)
    for d in mapped:
        by_edge[d['edge']].append(d)
    found, seen, stack = set(), set(), [net.getEdge(edge)]
    while stack:
        e = stack.pop()
        if e.getID() in seen:
            continue
        seen.add(e.getID())
        if e.getID() in by_edge:
            ds = sorted(by_edge[e.getID()], key=lambda d: d['pos'], reverse=incoming)
            found.add(ds[0]['id'])
            continue
        stack.extend(adjacent(e, incoming))
    return sorted(found)


def gate_priors(net, gates, mapped, targets, arrival_factor):
    # arrival_factor is kept for API compatibility: congested direct detectors now use the raw
    # observed median..p75 discharge range instead of p75 x arrival_factor (B2).
    target = {x['id']: x for x in targets}
    det_by_edge = {}
    for d in mapped:
        det_by_edge.setdefault(d['edge'], []).append(d)

    def find_downstream(edge):
        queue = [edge]
        seen = {edge.getID()}
        reached = []
        while queue:
            cur = queue.pop(0)
            if cur.getID() != edge.getID() and cur.getID() in det_by_edge:
                reached.extend(det_by_edge[cur.getID()])
                continue
            for nxt, cs in cur.getOutgoing().items():
                if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs):
                    if nxt.getID() not in seen:
                        seen.add(nxt.getID())
                        queue.append(nxt)
        return reached

    def find_upstream(start_edges, road, bound, exclude_id):
        queue = list(start_edges)
        seen = {exclude_id} | {e.getID() for e in start_edges}
        while queue:
            cur = queue.pop(0)
            if cur.getID() in det_by_edge:
                matching = [d for d in det_by_edge[cur.getID()] if d['road'] == road and d['bound'] == bound]
                if matching:
                    return matching[0]
            for prev, cs in cur.getIncoming().items():
                if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs):
                    if prev.getID() not in seen:
                        seen.add(prev.getID())
                        queue.append(prev)
        return None

    records = []
    pair_groups = defaultdict(list)

    def entry_record(edge, near, other, capacity, gate_class, value, lower, upper, basis,
                     identified=False, range_basis=''):
        # Every gate carries exactly one class and its demand is confined to that class's bounds.
        return {'edge': edge, 'direction': 'entry', 'near': list(near), 'other': list(other),
                'capacity_vph': capacity, 'gate_class': gate_class,
                'prior_vph': float(max(value, 0.0)), 'lower_vph': float(max(lower, 0.0)),
                'upper_vph': float(max(upper, 0.0)), 'identified': bool(identified),
                'basis': basis, 'range_basis': range_basis}

    for gate in gates:
        eid = gate['edge']
        edge = net.getEdge(eid)
        lanes = edge.getLaneNumber()
        cap = lanes * ENTRY_LANE_CAPACITY_VPH
        assumed_range = (f'no identified inflow measurement; declared range [0, {cap:g} veh/h] '
                         f'= {lanes} lanes x {ENTRY_LANE_CAPACITY_VPH} veh/h')

        if gate['direction'] != 'entry' or not gate.get('authorized_source', True):
            records.append({'edge': eid, 'direction': gate['direction'], 'near': [], 'other': [],
                            'prior_vph': 0.0, 'identified': False, 'capacity_vph': cap,
                            'gate_class': 'assumed', 'lower_vph': 0.0, 'upper_vph': 0.0,
                            'basis': 'unauthorized or exit gate; zero prior',
                            'range_basis': 'not an authorized entry source; declared range [0, 0]'})
            continue

        corridor = is_corridor_road(edge)

        # Direct detector on the gate edge: the only class that measures gate demand itself.
        if gate.get('detectors'):
            did = gate['detectors'][0]
            t = target.get(did)
            if t and not t['available']:
                records.append(entry_record(eid, [did], [], cap, 'assumed', 0.0, 0.0, cap,
                                            'gate detector has no observed bin; declared range [0, lanes x 1800]',
                                            range_basis=assumed_range))
                continue
            if t and t['congested']:
                median = float(t['flow'])
                p75 = max(float(t['p75']), median)
                records.append(entry_record(eid, [did], [], cap, 'measured_congested', median, median, p75,
                                            'direct detector on gate edge, congested: a congested detector measures '
                                            'discharge, so demand is bounded by observed median (lower) and p75 '
                                            '(upper), not by the lane cap',
                                            range_basis=f'observed discharge range [{median:.1f}, {p75:.1f}] veh/h'))
                continue
            if t:
                flow = float(t['flow'])
                records.append(entry_record(eid, [did], [], cap, 'measured', flow, flow, flow,
                                            'direct detector on gate edge, uncongested; demand equals observed flow',
                                            identified=True,
                                            range_basis=f'observed flow = {flow:.1f} veh/h'))
                continue

        down_dets = find_downstream(edge)
        seen_ids = set()
        unique_down = []
        for d in down_dets:
            if d['id'] not in seen_ids:
                seen_ids.add(d['id'])
                unique_down.append(d)

        carriageways = {(d['road'], d['bound']) for d in unique_down}
        if len(carriageways) != 1 or len(unique_down) == 0:
            # Diverging branches or opposite carriageways: never sum
            records.append(entry_record(eid, [d['id'] for d in unique_down], [], cap, 'assumed', 0.0, 0.0, cap,
                                        'diverging branches or opposite carriageways; no single-carriageway '
                                        'measurement of gate inflow', range_basis=assumed_range))
            continue

        down_det = unique_down[0]
        c_road, c_bound = down_det['road'], down_det['bound']

        # Find upstream detector on same carriageway
        outs = [nxt for nxt, cs in edge.getOutgoing().items()
                if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs)]
        up_det = find_upstream(outs, c_road, c_bound, eid)

        if up_det is None:
            t = target.get(down_det['id'])
            if corridor and t and t['available'] and not t['congested']:
                # Boundary crossing of corridor road before the first detector: inflow is inferred from
                # the same-carriageway downstream detector.
                flow = min(float(t['flow']), cap)
                rec = entry_record(eid, [down_det['id']], [], cap, 'inferred', flow, 0.0, flow,
                                   'corridor boundary crossing; same-carriageway downstream detector, '
                                   'no upstream detector', identified=True,
                                   range_basis=f'observed downstream flow = {t["flow"]:.1f} veh/h')
                records.append(rec)
                pair_groups['inferred', down_det['id']].append(rec)
            else:
                records.append(entry_record(eid, [down_det['id']], [], cap, 'assumed', 0.0, 0.0, cap,
                                            'side-street, or corridor boundary crossing with congested or '
                                            'missing downstream detector', range_basis=assumed_range))
            continue

        # Both down_det and up_det exist
        dt = target.get(down_det['id'], {'flow': 0, 'p75': 0, 'congested': False, 'available': False})
        ut = target.get(up_det['id'], {'flow': 0, 'p75': 0, 'congested': False, 'available': False})
        if dt['congested'] or ut['congested'] or not dt['available'] or not ut['available']:
            records.append(entry_record(eid, [down_det['id']], [up_det['id']], cap, 'assumed', 0.0, 0.0, cap,
                                        'bracketing detectors congested or missing; no identified flow balance',
                                        range_basis=assumed_range))
            continue

        balance = max(0.0, float(dt['flow']) - float(ut['flow']))
        upper = min(balance, cap)
        rec = entry_record(eid, [down_det['id']], [up_det['id']], cap, 'inferred', upper, 0.0, upper,
                           'same-carriageway flow balance between bracketing detectors (downstream - upstream)',
                           identified=True, range_basis=f'observed balance = {balance:.1f} veh/h')
        records.append(rec)
        pair_groups['inferred', up_det['id'], down_det['id']].append(rec)

    # Split shared cross sections by lane count, bounds included
    for group_key, recs in pair_groups.items():
        if len(recs) > 1:
            total_lanes = sum(net.getEdge(r['edge']).getLaneNumber() for r in recs)
            for r in recs:
                fraction = net.getEdge(r['edge']).getLaneNumber() / total_lanes
                r['prior_vph'] *= fraction
                r['lower_vph'] *= fraction
                r['upper_vph'] *= fraction

    return records
