# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Observable gate priors from adjacent detector cross sections, with explicit uncertainty."""
from collections import defaultdict

import numpy as np

from citypulse.network.bounded import adjacent


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
    records = []
    for gate in gates:
        incoming = gate['direction'] == 'exit'
        near = cross_sections(net, gate['edge'], mapped, incoming)
        # Gate's unobserved road joins a measured stream. Walk to first junction,
        # then find bracketing upstream sections on the other arms.
        cur, seen = net.getEdge(gate['edge']), set()
        other = set()
        while cur.getID() not in seen:
            seen.add(cur.getID())
            links = adjacent(cur, incoming)
            if not links or len(links) != 1:
                break
            nxt = links[0]
            for sibling in adjacent(nxt, not incoming):
                if sibling.getID() not in seen:
                    other.update(cross_sections(net, sibling.getID(), mapped, not incoming))
            if other:
                break
            cur = nxt
        def volume(ids):
            return sum((target[i]['p75'] * arrival_factor if target[i]['congested'] else target[i]['flow'])
                       for i in ids if target[i]['available'])
        value = max(0, volume(near) - volume(other))
        records.append({'edge': gate['edge'], 'direction': gate['direction'], 'near': near,
                        'other': sorted(other), 'prior_vph': value if gate['authorized_source'] else 0,
                        'basis': 'positive nearest-cross-section flow balance; shared access split by lane count',
                        'identified': bool(near) and not any(target[i]['congested'] for i in near + list(other))})
    groups = defaultdict(list)
    for r in records:
        groups[r['direction'], tuple(r['near']), tuple(r['other'])].append(r)
    for rs in groups.values():
        total_lanes = sum(net.getEdge(r['edge']).getLaneNumber() for r in rs)
        for r in rs:
            r['prior_vph'] *= net.getEdge(r['edge']).getLaneNumber() / total_lanes
    return records
