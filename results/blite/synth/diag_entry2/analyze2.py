"""Assemble the E/F/G/H/I entry-capacity diagnostics under results/blite/synth/diag_entry2/.

Copy of ``results/blite/synth/diag_entry/analyze.py``, extended with:

* the E/F/G table identical to ``diag_entry/report.md`` section 1 (pending, G1-G3, per-lane
  flow on ``tko_in``/``tko_vms``/``ktb_w1``, halting on ``tko_1``/``tko_vms``/``ktb_w1``);
* the H/I entry-capacity read-out: the 5-min ``tko_in`` throughput series, the best plateau
  over 3 consecutive bins, and the demand level at which the backlog first exceeds 50 veh;
* the weave read-out: lane changes on ``tko_1``/``tko_vms``, per-lane mean speed at 5-min and
  1-min resolution, and the minor/major split at junction D (``tko_a1`` lanes).

Usage::

    python results/blite/synth/diag_entry2/analyze2.py
"""
import csv
import json
from pathlib import Path

DIAG = Path(__file__).resolve().parent
D1 = DIAG.parent / 'diag_entry'

TAGS = ('E', 'F', 'G', 'H', 'I')
RAMP_TAGS = ('H', 'I')
DET_ORDER = ['dk_tko_in_0', 'dk_tko_in_1', 'dk_tko_vms_0', 'dk_tko_vms_1', 'dk_tko_vms_2',
             'dk_ktb_w1_0', 'dk_ktb_w1_1', 'dk_tko_a1_0', 'dk_tko_a1_1', 'dk_tko_a1_2',
             'dk_tko_1_0', 'dk_tko_1_1', 'dk_tko_1_2']
SPEED_LANES = ['tko_vms_0', 'tko_vms_1', 'tko_vms_2', 'tko_1_0', 'tko_1_1', 'tko_1_2']


def load(tag):
    p = DIAG / tag / 'run.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def rows_csv(path):
    with path.open(encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def fnum(x, nd=0):
    return f'{x:,.{nd}f}'


def section(title):
    print()
    print('=' * 100)
    print(title)
    print('=' * 100)


def main():
    metas = {t: load(t) for t in TAGS}

    section('1. Run table (E/F/G same columns as diag_entry/report.md section 1; H/I = ramp)')
    hdr = ('tag', 'change', 'sched', 'pending', 'running', 'arrived', 'gap', 'tele', 'coll',
           'pend%', 'G1', 'G2', 'G3', 'discharge_out_vph', 'wall_s')
    print(' | '.join(hdr))
    for t in TAGS:
        m = metas[t]
        if m is None:
            print(f'{t} | MISSING')
            continue
        print(' | '.join([
            t, m['change'], fnum(m['scheduled_departures']), fnum(m['pending_end']),
            fnum(m['running_end']), fnum(m['arrived_end']), str(m['conservation_gap']),
            str(m['teleports']), str(m['collisions']), f"{m['pending_share']:.2%}",
            'PASS' if m['g1_pass'] else 'FAIL', 'PASS' if m['g2_pass'] else 'FAIL',
            'PASS' if m['g3_pass'] else 'FAIL', f"{m['discharge_out_vph']:.0f}",
            str(m['wall_seconds'])]))

    section('2. tko_in backlog slope per complete 15-min window (veh/s, limit +0.05)')
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        ws = m['backlog_windows_tko_in']
        print(f"{t}: " + '  '.join(f"{w['window'][0]:.0f}-{w['window'][1]:.0f}={w['slope']:+.5f}"
                                   f"{'' if w['pass'] else '!'}" for w in ws))

    section('3. Per-lane E1 flow, last hour 3600-7200 s (veh/h)')
    print('tag | ' + ' | '.join(DET_ORDER))
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        print(f"{t} | " + ' | '.join(f"{m['per_lane'][d]['last_hour_vph']:.0f}"
                                     for d in DET_ORDER))
    print()
    print('edge sums (veh/h), last hour:')
    print('tag | tko_in | tko_1 | tko_vms | ktb_w1 | tko_a1')
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        def s(pref):
            return sum(m['per_lane'][d]['last_hour_vph'] for d in DET_ORDER if d.startswith(pref))
        print(f"{t} | {s('dk_tko_in'):.0f} | {s('dk_tko_1'):.0f} | {s('dk_tko_vms'):.0f} | "
              f"{s('dk_ktb_w1'):.0f} | {s('dk_tko_a1'):.0f}")

    section('3b. Instrument cross-check: E1 tko_in flow (intervals <= 7200 s) vs SUMO insertions')
    print('tag | scheduled | inserted_tko_in | E1_tko_in | E1-last-hour | inserted-last-hour')
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        e1_total = sum(iv['n'] for d in ('dk_tko_in_0', 'dk_tko_in_1')
                       for iv in m['per_lane'][d]['bins300'])
        e1_lh = m['per_lane']['dk_tko_in_0']['last_hour'] + m['per_lane']['dk_tko_in_1']['last_hour']
        ins_lh = sum(w['inserted'] for w in m['bins300_tko_in'] if w['t0'] >= 3600)
        print(f"{t} | {m['scheduled_departures']} | {m['insertions_by_source'].get('tko_in', 0)} | "
              f"{e1_total} | {e1_lh} | {ins_lh}")

    section('4. Halting, last 30 min: mean / max vehicles (tko_in, tko_1, tko_vms, ktb_w1)')
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        print(f"{t}: " + '  '.join(
            f"{e}={m['halting'][e]['mean_last30']:.3f}/{m['halting'][e]['max_last30']}"
            for e in ('tko_in', 'tko_1', 'tko_vms', 'ktb_w1')))
    print()
    print('weave edges, last 30 min, per-lane halting from halt_per_min.csv (mean/max):')
    for t in TAGS:
        p = DIAG / t / 'halt_per_min.csv'
        if not p.exists():
            continue
        rows = [r for r in rows_csv(p) if int(r['time']) > 7200 - 1800]
        out = []
        for lane in SPEED_LANES:
            vals = [int(r[lane]) for r in rows]
            out.append(f"{lane}={sum(vals)/len(vals):.2f}/{max(vals)}")
        print(f"{t}: " + '  '.join(out))

    section('5. H/I entry capacity (5-min tko_in throughput, veh/h; warm-up 0-900 s excluded)')
    for t in RAMP_TAGS:
        m = metas[t]
        if m is None:
            continue
        print(f'--- {t}: {m["change"]}')
        print('bin(s)        demand_mid  E1_vph  inserted_vph  veh')
        for w in m['bins300_tko_in']:
            print(f"{w['t0']:5.0f}-{w['t1']:5.0f}  {w['demand_vph']:8.0f}  {w['vph']:6.1f}  "
                  f"{w['inserted_vph']:12.1f}  {w['n']:4d}")
        pl = m['entry_capacity_plateau']
        pli = m['entry_capacity_plateau_inserted']
        print(f"plateau (E1, max 3 consecutive bins): {pl['t0']:.0f}-{pl['t1']:.0f} s, "
              f"{pl['vph']:.1f} veh/h over {pl['veh']} veh")
        print(f"plateau (insertions, same rule):      {pli['t0']:.0f}-{pli['t1']:.0f} s, "
              f"{pli['vph']:.1f} veh/h over {pli['veh']} veh")
        print(f"backlog > 20 veh: {m['backlog_onset_20']}")
        print(f"backlog > 50 veh: {m['backlog_onset_50']}")
        print(f"max pending tko_in: {m['max_pending_tko_in']} at t={m['peak_pending_time']} s; "
              f"pending_end_tko_in={m['pending_end_tko_in']}")
        print(f"insertions by source: {m['insertions_by_source']}")

    section('6. Weave: lane changes and per-lane mean speed (E and F, tko_1 / tko_vms)')
    for t in ('E', 'F', 'G'):
        m = metas[t]
        if m is None:
            continue
        print(f"{t}: lane changes whole run on tko_1={m['lane_changes']['tko_1']}, "
              f"tko_vms={m['lane_changes']['tko_vms']}")
    print()
    print('per-lane mean speed (m/s), 5-min bins, from speed_bins300.csv:')
    for t in ('E',):
        p = DIAG / t / 'speed_bins300.csv'
        if not p.exists():
            continue
        rows = rows_csv(p)
        bins = sorted({int(r['t0']) for r in rows})
        print(f'--- {t}')
        print('bin(s)      ' + '  '.join(f'{l:>10}' for l in SPEED_LANES))
        for b in bins:
            vals = {r['lane']: r for r in rows if int(r['t0']) == b}
            print(f'{b:5d}-{b+300:5d}  ' + '  '.join(
                f"{float(vals[l]['mean_speed_ms']):10.2f}" for l in SPEED_LANES))
    print()
    print('1-min resolution excerpt, tko_vms lanes, E (from speed_per_min.csv):')
    for t in ('E',):
        p = DIAG / t / 'speed_per_min.csv'
        if not p.exists():
            continue
        rows = rows_csv(p)
        for lo, hi in ((5400, 6000), (6900, 7200)):
            print(f'--- {t}: {lo}-{hi} s')
            print('   t   tko_vms_0  tko_vms_1  tko_vms_2   tko_1_0  tko_1_1  tko_1_2')
            for r in rows:
                k = int(r['time'])
                if lo < k <= hi:
                    print(f"{k:5d}  " + '  '.join(
                        f"{float(r[l]):9.2f}" for l in SPEED_LANES))
    print()
    print('tko_vms per-lane mean speed, whole run, vehicle-weighted by 5-min bins '
          '(mean of the 5-min values, last hour, and last 30 min):')
    for t in ('E', 'F', 'G'):
        p = DIAG / t / 'speed_bins300.csv'
        if not p.exists():
            continue
        rows = rows_csv(p)
        out = []
        for lane in ('tko_vms_0', 'tko_vms_1', 'tko_vms_2'):
            sel = [float(r['mean_speed_ms']) for r in rows
                   if r['lane'] == lane and float(r['mean_speed_ms']) == float(r['mean_speed_ms'])]
            lh = [float(r['mean_speed_ms']) for r in rows
                  if r['lane'] == lane and int(r['t0']) >= 3600
                  and float(r['mean_speed_ms']) == float(r['mean_speed_ms'])]
            out.append(f"{lane}={sum(sel)/len(sel):.2f}/{sum(lh)/len(lh):.2f}")
        print(f"{t}: " + '  '.join(out) + '  (run / last hour)')

    section('7. Junction D minor vs major movements (last hour, veh/h)')
    print('tko_vms_0 -> tko_a1_0 (minor), tko_vms_1 -> tko_a1_1 (minor), '
          'tko_vms_2 -> tko_a1_2 (major),')
    print('tko_vms_1 -> ktb_w1_0 (major), tko_vms_2 -> ktb_w1_1 (major)')
    for t in TAGS:
        m = metas[t]
        if m is None:
            continue
        pl = m['per_lane']
        print(f"{t}: a1 minor0={pl['dk_tko_a1_0']['last_hour_vph']:.0f} "
              f"minor1={pl['dk_tko_a1_1']['last_hour_vph']:.0f} "
              f"major2={pl['dk_tko_a1_2']['last_hour_vph']:.0f} | "
              f"ktb_w1_0={pl['dk_ktb_w1_0']['last_hour_vph']:.0f} "
              f"ktb_w1_1={pl['dk_ktb_w1_1']['last_hour_vph']:.0f}")

    section('8. Pending tko_in per minute (last 30 min), E/F/G/H/I')
    for t in TAGS:
        p = DIAG / t / 'history.csv'
        if not p.exists():
            continue
        rows = rows_csv(p)
        sel = [r for r in rows if int(r['time']) > 5400]
        print(f"{t}: " + '  '.join(f"{r['time']}:{r['pending_tko_in']}"
                                   for r in sel[::10]))

    section('9. Baseline comparison (diag_entry B/C and frozen A)')
    for tag, path in (('A(frozen)', D1.parent / 'g123_seed1001' / 'run.json'),
                      ('B', D1 / 'B' / 'run.json'), ('C', D1 / 'C' / 'run.json')):
        if path.exists():
            m = json.loads(path.read_text(encoding='utf-8'))
            print(f"{tag}: pending={m['pending_end']} discharge={m['discharge_out_vph']:.0f} "
                  f"g3={'PASS' if m['g3_pass'] else 'FAIL'} "
                  f"halting={m.get('halting', {})}")


if __name__ == '__main__':
    main()
