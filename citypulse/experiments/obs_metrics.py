# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Score canonical SUMO E1 XML against the calibration profile and held-out days."""
import json
import argparse
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from citypulse.config import RESULTS, SCEN
from citypulse.network.bounded import OUT, save


def geh(model, observed):
    return np.sqrt(2 * (model - observed) ** 2 / max(model + observed, 1e-12))


def read_e1(path):
    rows = []
    for _, x in ET.iterparse(path, events=['end']):
        if x.tag == 'interval':
            a = x.attrib
            rows.append({'detector': a['id'].rsplit('_', 1)[0], 'lane': a['id'],
                         'begin': float(a['begin']), 'end': float(a['end']),
                         'q': int(a['nVehContrib']), 'speed': float(a['speed']) * 3.6,
                         'occ': float(a['occupancy'])})
            x.clear()
    return pd.DataFrame(rows)


def aggregate(raw):
    raw = raw.copy()
    raw['weighted_speed'] = raw.q * raw.speed.clip(lower=0)
    periods = raw.groupby(['detector', 'begin'], as_index=False).agg(
        q=('q', 'sum'), weighted_speed=('weighted_speed', 'sum'), occ=('occ', 'mean'))
    periods['bin'] = (periods.begin // 300).astype(int)
    bins = periods.groupby(['detector', 'bin'], as_index=False).agg(
        q=('q', 'sum'), weighted_speed=('weighted_speed', 'sum'), occ=('occ', 'mean'),
        n_periods=('begin', 'count'))
    bins['flow_vph'] = bins.q * 12
    bins['speed_kmh'] = np.where(bins.q > 0, bins.weighted_speed / bins.q, np.nan)
    bins['bin_start'] = bins.bin.map(lambda t: f'{7 + t // 12:02d}:{t % 12 * 5:02d}')
    return periods, bins


def score(directory, metadata):
    profile = json.loads((RESULTS / 'obs' / 'obs_profile.json').read_text())
    mapped = json.loads((SCEN / 'detector_map.json').read_text())['mapped']
    raw = read_e1(directory / 'e1.xml')
    periods, bins = aggregate(raw)
    for name, frame in [('intervals', periods), ('bins', bins)]:
        frame.insert(0, 'tag', metadata['tag'])
        frame.to_csv(directory / f'{name}.csv', index=False)
    sim = bins.set_index(['detector', 'bin_start']).to_dict('index')
    observations = pd.read_parquet(RESULTS / 'obs' / 'obs_bins.parquet')
    hold = observations[observations.split == 'holdout']
    grid, exclusions, held = [], [], []
    retained = set(metadata['retained_detectors'])
    for d in mapped:
        aid = d['id']
        for minute in range(0, 60, 5):
            tm = f'08:{minute:02d}'
            p = profile.get(aid, {}).get(tm)
            if aid not in retained or not p:
                exclusions.append({'detector': aid, 'bin_start': tm, 'scope': 'simulation',
                                   'reason': 'outside_bounded_net' if aid not in retained else 'no_calibration_day_coverage_ge_0.3'})
                for day in profile['meta']['args']['holdout']:
                    exclusions.append({'detector': aid, 'bin_start': tm, 'day': day, 'scope': 'holdout',
                                       'reason': 'outside_bounded_net' if aid not in retained else 'no_calibration_predictor'})
                continue
            s = sim[aid, tm]
            assert s['n_periods'] == 10, (aid, tm, s)
            speed = p['speed_kmh']['median'] if p.get('speed_kmh') else None
            row = {'detector': aid, 'bin_start': tm, 'observed_flow': p['flow_vph']['median'],
                   'sim_flow': s['flow_vph'], 'geh': geh(s['flow_vph'], p['flow_vph']['median']),
                   'observed_speed': speed, 'sim_speed': s['speed_kmh'], 'observed_occ': p['occ']['median'],
                   'sim_occ': s['occ'], 'speed_error': abs(s['speed_kmh'] - speed) if speed is not None else np.nan,
                   'occ_error': abs(s['occ'] - p['occ']['median']),
                   'obs_congested': speed is not None and speed < 30 and p['occ']['median'] > 20,
                   'sim_congested': bool(s['speed_kmh'] < 30 and s['occ'] > 20),
                   'speed_available': speed is not None and np.isfinite(s['speed_kmh'])}
            row['state_agrees'] = row['speed_available'] and row['obs_congested'] == row['sim_congested']
            grid.append(row)
            if not row['speed_available']:
                exclusions.append({'detector': aid, 'bin_start': tm, 'scope': 'speed_only',
                                   'reason': 'no_simulated_crossing' if speed is not None else 'no_observed_speed',
                                   'acceptance': 'cell retained for flow; detector speed acceptance fails'})
            for day in profile['meta']['args']['holdout']:
                h = hold[(hold.detector == aid) & (hold.bin_start == tm) & (hold.date == day)]
                if h.empty or h.iloc[0].coverage < 0.3:
                    exclusions.append({'detector': aid, 'bin_start': tm, 'day': day, 'scope': 'holdout',
                                       'reason': 'missing_or_coverage_lt_0.3'})
                    continue
                h = h.iloc[0]
                held.append({'detector': aid, 'bin_start': tm, 'day': day,
                             'speed_error': abs(h.speed_kmh - speed) if speed is not None else np.nan,
                             'occ_error': abs(h.occ - p['occ']['median'])})
    cells, baseline = pd.DataFrame(grid), pd.DataFrame(held)
    per_detector = []
    for d in mapped:
        sub = cells[cells.detector == d['id']]
        h = baseline[baseline.detector == d['id']]
        if sub.empty:
            per_detector.append({'detector': d['id'], 'scored_cells': 0, 'reason': 'outside_bounded_net_or_no_coverage'})
            continue
        sim_mae = float(sub.speed_error.mean())
        hold_mae = float(h.speed_error.mean()) if len(h) else None
        complete = bool(sub.speed_available.all())
        per_detector.append({'detector': d['id'], 'scored_cells': len(sub),
                             'geh_lt5_share': float((sub.geh < 5).mean()),
                             'hourly_geh': float(geh(sub.sim_flow.mean(), sub.observed_flow.mean())),
                             'hourly_basis': 'mean rate over matched bins; complete hour only when scored_cells=12',
                             'speed_mae': sim_mae if np.isfinite(sim_mae) else None,
                             'speed_complete': complete, 'holdout_speed_mae': hold_mae,
                             'speed_pass': complete and hold_mae is not None and sim_mae <= hold_mae + 5,
                             'occ_mae': float(sub.occ_error.mean()),
                             'holdout_occ_mae': float(h.occ_error.mean()) if len(h) else None,
                             'holdout_cells': len(h), 'congestion_agreement': float(sub.state_agrees.mean())})
    for name, data in [('cells', cells), ('holdout_baseline', baseline),
                       ('detectors', pd.DataFrame(per_detector)), ('unscored', pd.DataFrame(exclusions))]:
        data.insert(0, 'tag', metadata['tag'])
        data.to_csv(directory / f'{name}.csv', index=False)
    # Separate observation-threshold sensitivity, never used to exclude sim outcomes.
    sensitivity = []
    for speed in (20, 30, 40):
        for occ in (10, 20, 30):
            agree = ((cells.observed_speed < speed) & (cells.observed_occ > occ)) == (
                (cells.sim_speed < speed) & (cells.sim_occ > occ))
            sensitivity.append({'speed_threshold': speed, 'occ_threshold': occ,
                                'agreement': float((agree & cells.speed_available).mean())})
    summary = {**metadata, 'scored_cells': len(cells), 'expected_cells': len(mapped) * 12,
               'unscored_simulation_cells': sum(x['scope'] == 'simulation' for x in exclusions),
               'unscored_holdout_cells': sum(x['scope'] == 'holdout' for x in exclusions),
               'missing_sim_speed_cells': int((~cells.speed_available).sum()),
               'flow_pass_cells': int((cells.geh < 5).sum()),
               'geh_count_units_lt5_share': float(np.mean([geh(s / 12, o / 12) < 5
                                                          for s, o in zip(cells.sim_flow, cells.observed_flow)])),
               'geh_lt5_share': float((cells.geh < 5).mean()),
               'hourly_geh_lt5_share': float(np.mean([x['hourly_geh'] < 5 for x in per_detector if x['scored_cells']])),
               'speed_mae': float(cells.speed_error.mean()), 'holdout_speed_mae': float(baseline.speed_error.mean()),
               'occ_mae': float(cells.occ_error.mean()), 'holdout_occ_mae': float(baseline.occ_error.mean()),
               'congestion_agreement': float(cells.state_agrees.mean()),
               'detectors_speed_pass': sum(x.get('speed_pass', False) for x in per_detector),
               'detectors_scored': sum(x['scored_cells'] > 0 for x in per_detector),
               'congestion_sensitivity': sensitivity, 'per_detector': per_detector}
    summary['acceptance'] = {'flow': summary['geh_lt5_share'] >= 0.8,
                             'speed': summary['detectors_speed_pass'] == summary['detectors_scored'],
                             'congestion': summary['congestion_agreement'] >= 0.75,
                             'backlog': metadata['unexplained_pending_share_max'] <= 0.02}
    summary['accepted'] = all(summary['acceptance'].values())
    save(directory / 'score.json', summary)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    args = ap.parse_args()
    directory = OUT / args.tag
    result = score(directory, json.loads((directory / 'run.json').read_text()))
    print(json.dumps({k: result[k] for k in ('tag', 'geh_lt5_share', 'speed_mae', 'occ_mae',
                     'congestion_agreement', 'detectors_speed_pass', 'pending_end', 'accepted')}))
