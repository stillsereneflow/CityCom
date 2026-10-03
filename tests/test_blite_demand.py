"""Unit tests for B-lite demand builder: flow balance sign, congested-entry bounds, split fit, and conservation."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from citypulse.config import RESULTS
from citypulse.demand.blite_demand import (
    CROSS_STREETS,
    DEFAULT_CROSS_STREET_VPH,
    EDGES_ARTERIAL,
    EDGES_BYPASS,
    build_slice_demand,
    compute_ramp_balance,
    determine_congested_entry,
    fit_diverge_split,
    generate_demand_files,
    get_route_edges,
)


def test_flow_balance_sign():
    """Verify flow balance sign: positive balance feeds on-ramp, negative feeds off-ramp."""
    # Positive balance (downstream > upstream) -> on-ramp gets positive, off-ramp gets 0
    res_pos = compute_ramp_balance(flow_upstream=1000.0, flow_downstream=1450.0)
    assert res_pos['on_vph'] == 450.0
    assert res_pos['off_vph'] == 0.0
    assert res_pos['class'] == 'inferred'
    assert 'downstream - upstream' in res_pos['basis']

    # Negative balance (downstream < upstream) -> off-ramp gets positive, on-ramp gets 0
    res_neg = compute_ramp_balance(flow_upstream=1500.0, flow_downstream=1100.0)
    assert res_neg['on_vph'] == 0.0
    assert res_neg['off_vph'] == 400.0
    assert res_neg['class'] == 'inferred'
    assert 'upstream - downstream' in res_neg['basis']

    # Equal balance -> both 0
    res_zero = compute_ramp_balance(flow_upstream=1200.0, flow_downstream=1200.0)
    assert res_zero['on_vph'] == 0.0
    assert res_zero['off_vph'] == 0.0
    assert res_zero['class'] == 'inferred'

    # Congested bracketing detector -> assumed [0, 1800], 0 volume
    res_cong = compute_ramp_balance(flow_upstream=1000.0, flow_downstream=1500.0, cong_u=True)
    assert res_cong['on_vph'] == 0.0
    assert res_cong['off_vph'] == 0.0
    assert res_cong['class'] == 'assumed'
    assert res_cong['range'] == [0.0, 1800.0]


def test_congested_entry_bounds():
    """Verify congested-entry bounds: median bounded by p75."""
    # Uncongested entry: equals median
    res_uncong = determine_congested_entry(median=2800.0, p75=3100.0, congested=False)
    assert res_uncong['flow_vph'] == 2800.0
    assert res_uncong['class'] == 'measured'
    assert not res_uncong['congested']

    # Congested entry: bounded by p75
    res_cong = determine_congested_entry(median=2100.0, p75=2450.0, congested=True)
    assert res_cong['class'] == 'measured_congested'
    assert res_cong['congested']
    assert 2100.0 <= res_cong['flow_vph'] <= 2450.0

    # Congested with high target: clamped to p75
    res_high = determine_congested_entry(median=2000.0, p75=2300.0, congested=True, target=3500.0)
    assert res_high['flow_vph'] == 2300.0

    # Congested with low target: clamped to median
    res_low = determine_congested_entry(median=2000.0, p75=2300.0, congested=True, target=1500.0)
    assert res_low['flow_vph'] == 2000.0

    # Congested with target inside [median, p75]
    res_mid = determine_congested_entry(median=2000.0, p75=2300.0, congested=True, target=2150.0)
    assert res_mid['flow_vph'] == 2150.0


def test_split_fit_on_toy_example():
    """Verify diverge split least-squares fitting on toy examples."""
    # Toy example 1: direct branch observations
    toy1 = fit_diverge_split(bypass_target=300.0, arterial_target=700.0, entry_flow=1000.0)
    assert pytest.approx(toy1['alpha'], abs=1e-6) == 0.3
    assert pytest.approx(toy1['bypass_flow'], abs=1e-6) == 300.0
    assert pytest.approx(toy1['arterial_flow'], abs=1e-6) == 700.0

    # Toy example 2: fitted with ramp adjustments (downstream - net ramp = through flow)
    # Bypass: detector 500, on-ramp 100 -> net through 400
    # Arterial: detector 500, off-ramp 100 -> net through 600
    toy2 = fit_diverge_split(bypass_target=500.0, arterial_target=500.0,
                             entry_flow=1000.0,
                             bypass_ramp_net=100.0, arterial_ramp_net=-100.0)
    assert pytest.approx(toy2['alpha'], abs=1e-6) == 0.4
    assert pytest.approx(toy2['bypass_flow'], abs=1e-6) == 400.0
    assert pytest.approx(toy2['arterial_flow'], abs=1e-6) == 600.0

    # Toy example 3: bounded entry flow
    toy3 = fit_diverge_split(bypass_target=600.0, arterial_target=900.0,
                             entry_bounds=(1000.0, 1200.0))
    # Sum is 1500, clamped to upper bound 1200
    assert pytest.approx(toy3['entry_flow'], abs=1e-6) == 1200.0
    assert pytest.approx(toy3['alpha'], abs=1e-6) == 600.0 / 1500.0  # 0.4
    assert pytest.approx(toy3['bypass_flow'], abs=1e-6) == 480.0
    assert pytest.approx(toy3['arterial_flow'], abs=1e-6) == 720.0


def test_conservation():
    """Verify 1-D conservation: sum in = sum out per slice, up to Poisson draw."""
    profile_path = RESULTS / 'obs' / 'obs_profile.json'
    assert profile_path.exists(), f'Missing {profile_path}'
    profile = json.loads(profile_path.read_text(encoding='utf-8'))

    for s in range(8):
        s_data = build_slice_demand(profile, s, scale=1.0)
        tot_in = s_data['summary']['total_inflow_vph']
        tot_out = s_data['summary']['total_outflow_vph']
        assert abs(tot_in - tot_out) < 1e-6, f'Conservation violated in slice {s}: in={tot_in}, out={tot_out}'
        assert abs(s_data['summary']['conservation_delta']) < 1e-6

        # Check all reconstructed routes
        for od_key in s_data['od_flows']:
            orig, dest = od_key.split('->')
            edges = get_route_edges(orig, dest)
            assert len(edges) >= 2, f'Invalid route length for {od_key}: {edges}'
            if orig.startswith('x'):
                assert edges == [orig, dest]
            elif orig.startswith('tko_in'):
                assert edges[0] == 'tko_in'
                assert edges[1] == 'tko_1'
                assert edges[2] == 'tko_vms'
                assert edges[-1] == dest
            else:
                assert edges[0] == orig
                assert edges[-1] == dest


def test_demand_file_generation(tmp_path):
    """Verify generation of proxy.rou.xml, twin_cand.rou.xml, and demand.json."""
    profile_path = RESULTS / 'obs' / 'obs_profile.json'
    out_dir = tmp_path / 'blite_demand'

    res = generate_demand_files(profile_path, out_dir, scale=0.8, proxy_seed=1001, twin_seed=2202)
    assert (out_dir / 'demand.json').exists()
    assert (out_dir / 'proxy.rou.xml').exists()
    assert (out_dir / 'twin_cand.rou.xml').exists()

    d_json = json.loads((out_dir / 'demand.json').read_text(encoding='utf-8'))
    assert len(d_json['slices']) == 8
    assert d_json['meta']['scale'] == 0.8
    assert d_json['meta']['proxy_seed'] == 1001
    assert d_json['meta']['twin_seed'] == 2202

    # Check XML root and vehicle types
    proxy_tree = ET.parse(out_dir / 'proxy.rou.xml')
    proxy_root = proxy_tree.getroot()
    proxy_vehs = list(proxy_root.iter('vehicle'))
    assert len(proxy_vehs) > 0
    assert all(v.get('type') == 'pdist' for v in proxy_vehs)
    assert all(v.get('id').startswith('p') for v in proxy_vehs)

    twin_tree = ET.parse(out_dir / 'twin_cand.rou.xml')
    twin_root = twin_tree.getroot()
    twin_vehs = list(twin_root.iter('vehicle'))
    assert len(twin_vehs) > 0
    assert all(v.get('type') == 'tdist' for v in twin_vehs)
    assert all(v.get('id').startswith('t') for v in twin_vehs)

    # Twin candidate count should be approximately 1.5x proxy count
    ratio = len(twin_vehs) / len(proxy_vehs)
    assert 1.4 <= ratio <= 1.6, f'Twin ratio {ratio} out of expected ~1.5 range'
