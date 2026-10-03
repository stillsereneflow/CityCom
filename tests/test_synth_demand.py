"""Unit tests for the synthetic B-lite net4 boundary demand (decision 2026-10-03b)."""
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from citypulse.demand.blite_demand import (  # noqa: E402
    DETS_ARTERIAL,
    DETS_BYPASS,
    EDGES_ARTERIAL,
    EDGES_BYPASS,
)
from citypulse.demand.synth_demand import (  # noqa: E402
    BYPASS_SHARE,
    CROSS_STREETS,
    DEFAULT_CROSS_STREET_VPH,
    N_SLICES,
    SHOCK_FACTOR,
    TKO_IN_VPH,
    build_synthetic_slices,
    generate_synth_files,
)

RAMP_EDGES = {f'{pre}_{e}' for e in EDGES_BYPASS + EDGES_ARTERIAL for pre in ('on', 'off')}

BYPASS_CHAIN = {'ktb_w1', 'ktb_w2', 'ktb_w3', 'ktb_n1', 'ktb_n2'}
ARTERIAL_CHAIN = {'tko_a1', 'ktr_w1', 'ktr_w2', 'ktr_w3', 'ktr_w4', 'ktr_w5', 'ktr_w6'}


def parse_routes(path):
    tree = ET.parse(path)
    out = []
    for v in tree.getroot().iter('vehicle'):
        out.append({
            'id': v.get('id'),
            'depart': float(v.get('depart')),
            'type': v.get('type'),
            'edges': v.find('route').get('edges').split(),
        })
    return out


def source_of(edges):
    return edges[0]


def main_source_counts(vehicles):
    return Counter(source_of(v['edges']) for v in vehicles)


def test_tko_in_total_and_split():
    """tko_in carries 2,800 veh/h split 75% bypass / 25% arterial, all to `out`."""
    slices = build_synthetic_slices(shock=False)
    for s in slices:
        # demand.json holds hourly rates; the route writer scales each slice by 900/3600
        bypass = s['od_flows']['tko_in_bypass->out']
        arterial = s['od_flows']['tko_in_arterial->out']
        assert abs(bypass + arterial - TKO_IN_VPH) < 1e-9
        assert abs(bypass - TKO_IN_VPH * BYPASS_SHARE) < 1e-9
        assert abs(arterial - TKO_IN_VPH * (1 - BYPASS_SHARE)) < 1e-9
        assert abs(bypass / (bypass + arterial) - BYPASS_SHARE) < 1e-12
        assert abs(s['split']['alpha_bypass'] - BYPASS_SHARE) < 1e-9
        assert s['split']['basis'] == '75% bypass / 25% arterial, all to out'


def test_cross_street_totals():
    """Each cross-street stub carries 400 veh/h and only gets a straight-across route."""
    slices = build_synthetic_slices(shock=False)
    for x in CROSS_STREETS:
        for s in slices:
            assert abs(s['od_flows'][f'{x}_in->{x}_out'] - DEFAULT_CROSS_STREET_VPH) < 1e-9
            for key in s['od_flows']:
                if key.startswith(f'{x}_in->'):
                    assert key == f'{x}_in->{x}_out'


def test_ramps_zero():
    """Every intermediate on/off ramp is exactly zero in the assumed demand."""
    for s in build_synthetic_slices(shock=False):
        for r in s['ramps']:
            assert r['flow_vph'] == 0.0, r
        for key, fl in s['od_flows'].items():
            orig = key.split('->')[0]
            assert orig not in RAMP_EDGES, key
            assert fl >= 0.0


def test_generate_files_totals_split_and_ramps():
    """End-to-end: written route files reproduce the assumed totals, split and zero ramps.

    Vehicle counts are Poisson draws, so each aggregate is checked against a 5-sigma band.
    """
    import shutil

    out = ROOT / 'results' / 'blite' / 'synth' / '_test_tmp'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    generate_synth_files(out_dir=out)

    for name in ('proxy.rou.xml', 'twin_cand.rou.xml', 'proxy_shock.rou.xml', 'demand.json'):
        assert (out / name).exists(), name

    proxy = parse_routes(out / 'proxy.rou.xml')
    assert all(v['type'] == 'pdist' for v in proxy)
    assert all(0.0 <= v['depart'] <= 7200.0 for v in proxy)
    # 2800 veh/h * 2 h + 4 * 400 veh/h * 2 h = 5600 + 3200 = 8800
    assert abs(len(proxy) - 8800) < 5 * (8800 ** 0.5)

    counts = main_source_counts(proxy)
    assert set(counts) == {'tko_in', 'x1_in', 'x2_in', 'x3_in', 'x4_in'}
    assert abs(counts['tko_in'] - 5600) < 5 * (5600 ** 0.5)
    for x in CROSS_STREETS:
        assert abs(counts[f'{x}_in'] - 800) < 5 * (800 ** 0.5)

    tko_veh = [v for v in proxy if v['edges'][0] == 'tko_in']
    bypass = [v for v in tko_veh if BYPASS_CHAIN & set(v['edges'])]
    arterial = [v for v in tko_veh if ARTERIAL_CHAIN & set(v['edges'])]
    assert len(bypass) + len(arterial) == len(tko_veh)
    # net4's lane-level merge/diverge edges are inserted so SUMO accepts the route
    assert 'ms_on_ktb_w2' in bypass[0]['edges'] and 'dv_off_ktb_n1' in bypass[0]['edges']
    assert 'ms_on_ktr_w1' in arterial[0]['edges']
    share = len(bypass) / len(tko_veh)
    sigma = (BYPASS_SHARE * (1 - BYPASS_SHARE) / len(tko_veh)) ** 0.5
    assert abs(share - BYPASS_SHARE) < 5 * sigma, share

    assert all(v['edges'][-1] == 'out' for v in tko_veh)
    for v in proxy:
        assert not (RAMP_EDGES & set(v['edges'])), v
        if v['edges'][0].startswith('x'):
            assert v['edges'] == [v['edges'][0], f"{v['edges'][0][:2]}_out"], v

    twin = parse_routes(out / 'twin_cand.rou.xml')
    assert all(v['type'] == 'tdist' for v in twin)
    # Twin candidate pool is 1.5x the Proxy stream.
    assert abs(len(twin) / len(proxy) - 1.5) < 5 * 0.02
    twin_counts = main_source_counts(twin)
    assert abs(twin_counts['tko_in'] / counts['tko_in'] - 1.5) < 5 * 0.03
    assert abs(twin_counts['x1_in'] / counts['x1_in'] - 1.5) < 5 * 0.05

    # Shock control: +30% at tko_in from 4,500 to 5,400 s, everything else identical.
    base = parse_routes(out / 'proxy.rou.xml')
    shock = parse_routes(out / 'proxy_shock.rou.xml')
    in_shock = lambda vs: [v for v in vs if 4500.0 <= v['depart'] <= 5400.0]
    base_window = len(in_shock([v for v in base if v['edges'][0] == 'tko_in']))
    shock_window = len(in_shock([v for v in shock if v['edges'][0] == 'tko_in']))
    assert abs(shock_window / base_window - SHOCK_FACTOR) < 5 * 0.04
    for v in shock:
        assert not (RAMP_EDGES & set(v['edges'])), v

    # demand.json carries the assumed boundary conditions.
    dj = json.loads((out / 'demand.json').read_text(encoding='utf-8'))
    assert dj['meta']['proxy_seed'] == 1001
    assert dj['meta']['twin_seed'] == 2202
    assert dj['meta']['twin_cand_scale'] == 1.5
    assert dj['meta']['tko_in_vph'] == TKO_IN_VPH
    assert abs(dj['meta']['bypass_share'] - BYPASS_SHARE) < 1e-9
    assert len(dj['slices']) == N_SLICES
    assert abs(dj['slices'][5]['entry']['flow_vph'] - TKO_IN_VPH) < 1e-9
    djs = json.loads((out / 'demand_shock.json').read_text(encoding='utf-8'))
    assert abs(djs['slices'][5]['entry']['flow_vph'] - TKO_IN_VPH * SHOCK_FACTOR) < 1e-9
    assert abs(djs['slices'][4]['entry']['flow_vph'] - TKO_IN_VPH) < 1e-9
    assert abs(djs['slices'][6]['entry']['flow_vph'] - TKO_IN_VPH) < 1e-9

    for leftover in ('proxy.rou.xml', 'twin_cand.rou.xml', 'demand.json'):
        if (out / '_shock' / leftover).exists():
            raise AssertionError(f'scratch dir left behind: {leftover}')
    assert not (out / '_shock').exists()
    shutil.rmtree(out, ignore_errors=True)


if __name__ == '__main__':
    test_tko_in_total_and_split()
    test_cross_street_totals()
    test_ramps_zero()
    test_generate_files_totals_split_and_ramps()
    print('all synthetic demand tests passed')
