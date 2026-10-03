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

    for gate in gates:
        eid = gate['edge']
        edge = net.getEdge(eid)
        lanes = edge.getLaneNumber()
        cap = lanes * ENTRY_LANE_CAPACITY_VPH

        if gate['direction'] != 'entry' or not gate.get('authorized_source', True):
            records.append({'edge': eid, 'direction': gate['direction'], 'near': [], 'other': [],
                            'prior_vph': 0.0, 'identified': False, 'capacity_vph': cap,
                            'basis': 'unauthorized or exit gate; zero prior'})
            continue

        corridor = is_corridor_road(edge)

        # Direct detector on gate
        if gate.get('detectors'):
            did = gate['detectors'][0]
            t = target.get(did)
            if t:
                val = t['p75'] * arrival_factor if t['congested'] else t['flow']
                rec = {'edge': eid, 'direction': 'entry', 'near': [did], 'other': [],
                       'prior_vph': min(val, cap), 'identified': t['available'] and not t['congested'],
                       'capacity_vph': cap, 'basis': 'direct detector on gate'}
                records.append(rec)
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
            records.append({'edge': eid, 'direction': 'entry', 'near': [d['id'] for d in unique_down],
                            'other': [], 'prior_vph': 0.0, 'identified': False, 'capacity_vph': cap,
                            'basis': 'diverging branches or opposite carriageways; zero prior'})
            continue

        down_det = unique_down[0]
        c_road, c_bound = down_det['road'], down_det['bound']

        # Find upstream detector on same carriageway
        outs = [nxt for nxt, cs in edge.getOutgoing().items()
                if any(c.getFromLane().allows('passenger') and c.getToLane().allows('passenger') for c in cs)]
        up_det = find_upstream(outs, c_road, c_bound, eid)

        if up_det is None:
            if corridor:
                # Boundary crossing of corridor road before first detector
                t = target.get(down_det['id'], {'flow': 0, 'p75': 0, 'congested': False, 'available': False})
                val = t['p75'] * arrival_factor if t['congested'] else t['flow']
                rec = {'edge': eid, 'direction': 'entry', 'near': [down_det['id']], 'other': [],
                       'prior_vph': val, 'identified': t['available'] and not t['congested'],
                       'capacity_vph': cap, 'basis': 'corridor boundary crossing; downstream entry detector'}
                records.append(rec)
                pair_groups['corridor_entry', down_det['id']].append(rec)
            else:
                # Side street with missing upstream detector: do not guess
                records.append({'edge': eid, 'direction': 'entry', 'near': [down_det['id']], 'other': [],
                                'prior_vph': 0.0, 'identified': False, 'capacity_vph': cap,
                                'basis': 'side-street with missing upstream detector; unidentified, zero prior'})
            continue

        # Both down_det and up_det exist
        dt = target.get(down_det['id'], {'flow': 0, 'p75': 0, 'congested': False, 'available': False})
        ut = target.get(up_det['id'], {'flow': 0, 'p75': 0, 'congested': False, 'available': False})
        if dt['congested'] or ut['congested'] or not dt['available'] or not ut['available']:
            records.append({'edge': eid, 'direction': 'entry', 'near': [down_det['id']],
                            'other': [up_det['id']], 'prior_vph': 0.0, 'identified': False, 'capacity_vph': cap,
                            'basis': 'congested or missing detector; unidentified, zero prior'})
            continue

        balance = max(0.0, dt['flow'] - ut['flow'])
        rec = {'edge': eid, 'direction': 'entry', 'near': [down_det['id']], 'other': [up_det['id']],
               'prior_vph': balance, 'identified': True, 'capacity_vph': cap,
               'basis': 'flow balance between bracketing detectors on same carriageway'}
        records.append(rec)
        pair_groups['balance', up_det['id'], down_det['id']].append(rec)

    # Split shared pairs by lane count
    for group_key, recs in pair_groups.items():
        if len(recs) > 1:
            total_lanes = sum(net.getEdge(r['edge']).getLaneNumber() for r in recs)
            for r in recs:
                r['prior_vph'] *= net.getEdge(r['edge']).getLaneNumber() / total_lanes

    # Cap each gate's demand at physical entry capacity
    for r in records:
        r['prior_vph'] = float(min(r['prior_vph'], r['capacity_vph']))

    return records
