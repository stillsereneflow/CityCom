"""Assemble the A/B/C/D diagnostics under results/blite/synth/diag_entry/ into one table."""
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

DIAG = Path(__file__).resolve().parent
SYNTH = DIAG.parent
A_RUN = DIAG / 'A' / 'run.json'
A_FROZEN = SYNTH / 'g123_seed1001' / 'run.json'
A_E1 = SYNTH / 'g123_seed1001' / 'e1.xml'


def baseline_e1():
    """Per-lane counts from the frozen seed-1001 E1 file (detectors4.add.xml, period 30 s)."""
    root = ET.parse(A_E1).getroot()
    last, full = defaultdict(int), defaultdict(int)
    for iv in root.iter('interval'):
        did = iv.get('id')
        b, e, n = float(iv.get('begin')), float(iv.get('end')), int(iv.get('nVehContrib'))
        full[did] += n
        if b >= 3600.0 and e <= 7200.0:
            last[did] += n
    return last, full


def main():
    rows = {}
    for tag in 'ABCD':
        p = DIAG / tag / 'run.json'
        if tag == 'A':
            p = p if p.exists() else A_FROZEN
        rows[tag] = json.loads(p.read_text(encoding='utf-8'))
        rows[tag]['_source'] = str(p)

    last, full = baseline_e1()
    print('baseline E1 (frozen seed 1001), last hour 3600-7200 s:')
    for did in ('AID07105_0', 'AID07105_1', 'AID07106_0', 'AID07106_1', 'AID07106_2',
                'AID07107_0', 'AID07107_1', 'AID07107_2', 'AID02105_0', 'AID02105_1'):
        print(f'  {did}: last_hour={last[did]} full_run={full[did]}')

    for tag, m in rows.items():
        print(f"\n==== {tag}: {m.get('change', 'baseline')}  [{m['_source']}]")
        for k in ('scheduled_departures', 'pending_end', 'running_end', 'arrived_end',
                  'conservation_gap', 'pre_flush_running', 'flush_arrivals',
                  'teleports', 'collisions', 'g1_pass', 'g2_pass', 'g3_pass',
                  'discharge_out_vph', 'pending_share', 'out_end', 'wall_seconds'):
            if k in m:
                print(f'   {k}: {m[k]}')
        print('   tko_in backlog windows:', [(w['window'], round(w['slope'], 5), w['pass'])
                                             for w in m.get('backlog_windows_tko_in', [])])
        if 'per_lane' in m:
            for did, v in m['per_lane'].items():
                print(f"   lane {v['lane']:<12} e1_last_hour={v['last_hour']:>5} "
                      f"({v['last_hour_vph']:>7.0f} vph) entries={v['lane_entries_last_hour']:>5} "
                      f"full={v['full_run']}")
        if 'halting' in m:
            print('   halting last30:', m['halting'])
        else:
            h = {r['edge']: r for r in json.loads(
                (SYNTH / 'g123_seed1001' / 'halting_last30.json').read_text(encoding='utf-8'))}
            print('   halting last30 (frozen, absent edge => 0):',
                  {e: {'mean': h[e]['mean_halting'], 'max': h[e]['max_halting']} if e in h
                   else {'mean': 0.0, 'max': 0} for e in ('tko_in', 'tko_1', 'tko_vms', 'ktb_w1')})


if __name__ == '__main__':
    main()
