# UNAUDITED: written by GPT-6 Astra (run stopped by the user 2026-10-03); under review by dsh/agy-flash.
"""Small instrument tests: rates, lane weighting, interval endpoint and missing data."""
import numpy as np
import pandas as pd
import sys

from citypulse.demand.bounded import slice_targets
from citypulse.experiments.obs_metrics import aggregate, geh
from citypulse.config import RESULTS


def test_aggregate_uses_counts_and_ten_completed_periods():
    rows = []
    for t in range(0, 300, 30):
        rows.extend([dict(detector='D', lane='D_0', begin=t, end=t + 30, q=2, speed=36, occ=10),
                     dict(detector='D', lane='D_1', begin=t, end=t + 30, q=1, speed=72, occ=20)])
    periods, bins = aggregate(pd.DataFrame(rows))
    assert len(periods) == 10 and len(bins) == 1
    b = bins.iloc[0]
    assert b.q == 30 and b.flow_vph == 360
    assert b.speed_kmh == 48 and b.occ == 15 and b.n_periods == 10
    assert b.bin_start == '07:00'


def test_zero_flow_is_not_zero_speed():
    raw = pd.DataFrame([dict(detector='D', lane='D_0', begin=3600, end=3630, q=0, speed=-3.6, occ=0)])
    _, b = aggregate(raw)
    assert b.iloc[0].flow_vph == 0 and np.isnan(b.iloc[0].speed_kmh)
    assert b.iloc[0].bin_start == '08:00'


def test_profile_missing_bins_do_not_become_zero_and_discharge_is_flagged():
    profile = {'D': {'08:05': {'flow_vph': {'median': 1000, 'p75': 1200},
                              'speed_kmh': {'median': 20}, 'occ': {'median': 30}}}}
    rows = slice_targets(profile, [{'id': 'D', 'edge': 'e'}, {'id': 'M', 'edge': 'm'}], 3600)
    assert rows[0]['flow'] == 1000 and rows[0]['congested']
    assert not rows[1]['available']
    assert geh(1200, 1000) == np.sqrt(2 * 200 ** 2 / 2200)


def test_fit_matches_independent_linear_least_squares_and_bounds():
    sys.path.insert(0, str(RESULTS / 'astra_step1' / 'packages'))
    from scipy.optimize import lsq_linear
    from citypulse.demand.bounded import fit
    matrix = np.array([[1., 0., 1.], [0., 1., 1.]])
    y, prior, reg = np.array([900., 600.]), np.array([100., 100., 100.]), 0.03
    targets = [{'flow': f, 'p75': f, 'available': True, 'congested': False} for f in y]
    actual, report = fit(matrix, targets, prior, 1.1, regularization=reg)
    penalty = np.diag(np.sqrt(reg / (prior + 1)))
    a = np.vstack([matrix / np.sqrt(y)[:, None], penalty])
    b = np.concatenate([np.sqrt(y), penalty @ prior])
    trusted = lsq_linear(a, b, bounds=(0, np.inf), tol=1e-12)
    assert report['success'] and np.min(actual) >= 0
    np.testing.assert_allclose(matrix @ actual, matrix @ trusted.x, atol=0.002)
    assert abs(np.linalg.norm(a @ actual - b) ** 2 - np.linalg.norm(a @ trusted.x - b) ** 2) < 1e-6


class MockEdge:
    def __init__(self, eid, lanes=1, name='', etype='highway.secondary', outgoing=None, incoming=None):
        self.eid = eid
        self.lanes = lanes
        self.name = name
        self.etype = etype
        self.outgoing = outgoing or {}
        self.incoming = incoming or {}

    def getID(self):
        return self.eid

    def getLaneNumber(self):
        return self.lanes

    def getName(self):
        return self.name

    def getType(self):
        return self.etype

    def getOutgoing(self):
        return self.outgoing

    def getIncoming(self):
        return self.incoming


class MockConnection:
    def getFromLane(self):
        return self
    def getToLane(self):
        return self
    def allows(self, vclass):
        return True


class MockNet:
    def __init__(self, edges):
        self.edges = {e.getID(): e for e in edges}

    def getEdge(self, eid):
        return self.edges[eid]

    def getEdges(self):
        return list(self.edges.values())


def test_entry_sources_capacity_and_unjustified_prior_zero():
    from citypulse.demand.bounded_gates import ENTRY_LANE_CAPACITY_VPH
    from citypulse.demand.bounded import fit
    assert ENTRY_LANE_CAPACITY_VPH == 1800

    routes = [['gate_corridor', 'mid', 'exit'], ['gate_unjustified', 'mid', 'exit']]
    active_gates = ['gate_corridor', 'gate_unjustified']
    routes_by_gate = {'gate_corridor': [0], 'gate_unjustified': [1]}
    gm = np.array([[1.0, 0.0], [0.0, 1.0]])
    gc = np.array([1800.0, 0.0])
    route_prior = np.array([1200.0, 0.0])
    bounds = [(0.0, 1800.0), (0.0, 0.0)]
    caps_tuple = (gm, gc, active_gates, routes_by_gate, bounds)

    matrix = np.array([[1.0, 1.0]])
    targets = [{'flow': 5000.0, 'p75': 5000.0, 'available': True, 'congested': False}]
    weights, report = fit(matrix, targets, route_prior, 1.1, gate_caps=caps_tuple)

    assert weights[1] == 0.0, "Unjustified gate must have 0 demand"
    assert weights[0] <= 1800.0 + 1e-4, f"Corridor gate demand must be capped at 1800, got {weights[0]}"


def test_gate_priors_flow_balance_and_diverging_unidentified():
    import pytest
    from citypulse.demand.bounded_gates import gate_priors
    conn = [MockConnection()]
    e_down = MockEdge('e_down', lanes=3, name='Kwun Tong Road', etype='highway.primary')
    e_mid = MockEdge('e_mid', lanes=3, name='Kwun Tong Road', etype='highway.primary', outgoing={e_down: conn})
    e_up = MockEdge('e_up', lanes=3, name='Kwun Tong Road', etype='highway.primary', outgoing={e_mid: conn})
    e_down.incoming = {e_mid: conn}
    e_mid.incoming = {e_up: conn}

    gate1 = MockEdge('g1', lanes=1, name='Side 1', etype='highway.secondary', outgoing={e_mid: conn})
    gate2 = MockEdge('g2', lanes=2, name='Side 2', etype='highway.secondary', outgoing={e_mid: conn})
    e_mid.incoming[gate1] = conn
    e_mid.incoming[gate2] = conn

    e_opp = MockEdge('e_opp', lanes=3, name='Kwun Tong Road Eastbound', etype='highway.primary')
    gate_div = MockEdge('g_div', lanes=1, name='Diverging', etype='highway.secondary', outgoing={e_mid: conn, e_opp: conn})

    net = MockNet([e_down, e_mid, e_up, gate1, gate2, e_opp, gate_div])
    mapped = [{'id': 'D_UP', 'edge': 'e_up', 'road': 'Kwun Tong Road', 'bound': 'Westbound'},
              {'id': 'D_DOWN', 'edge': 'e_down', 'road': 'Kwun Tong Road', 'bound': 'Westbound'},
              {'id': 'D_OPP', 'edge': 'e_opp', 'road': 'Kwun Tong Road', 'bound': 'Eastbound'}]

    gates = [{'edge': 'g1', 'direction': 'entry', 'detectors': [], 'authorized_source': True},
             {'edge': 'g2', 'direction': 'entry', 'detectors': [], 'authorized_source': True},
             {'edge': 'g_div', 'direction': 'entry', 'detectors': [], 'authorized_source': True}]

    # Normal flow balance: downstream 2000, upstream 1100 -> balance 900
    # Gate 1 has 1 lane, Gate 2 has 2 lanes -> total 3 lanes -> g1 gets 300, g2 gets 600
    targets = [{'id': 'D_UP', 'flow': 1100.0, 'p75': 1100.0, 'available': True, 'congested': False},
               {'id': 'D_DOWN', 'flow': 2000.0, 'p75': 2000.0, 'available': True, 'congested': False},
               {'id': 'D_OPP', 'flow': 1500.0, 'p75': 1500.0, 'available': True, 'congested': False}]

    priors = gate_priors(net, gates, mapped, targets, 1.1)
    p_by_edge = {p['edge']: p for p in priors}

    assert p_by_edge['g1']['identified'] and p_by_edge['g1']['prior_vph'] == pytest.approx(300.0)
    assert p_by_edge['g2']['identified'] and p_by_edge['g2']['prior_vph'] == pytest.approx(600.0)
    assert not p_by_edge['g_div']['identified'] and p_by_edge['g_div']['prior_vph'] == 0.0

    # Upstream detector is congested -> unidentified, no prior
    targets_cong = [{'id': 'D_UP', 'flow': 1100.0, 'p75': 1500.0, 'available': True, 'congested': True},
                    {'id': 'D_DOWN', 'flow': 2000.0, 'p75': 2000.0, 'available': True, 'congested': False},
                    {'id': 'D_OPP', 'flow': 1500.0, 'p75': 1500.0, 'available': True, 'congested': False}]
    priors_cong = gate_priors(net, gates, mapped, targets_cong, 1.1)
    p_cong = {p['edge']: p for p in priors_cong}
    assert not p_cong['g1']['identified'] and p_cong['g1']['prior_vph'] == 0.0


def test_congested_detectors_aggregate_per_edge():
    from citypulse.demand.bounded import aggregate_edge_targets
    targets = [
        {'id': 'd1_a', 'edge': 'e1', 'flow': 3000.0, 'p75': 3200.0, 'available': True, 'congested': False},
        {'id': 'd1_b', 'edge': 'e1', 'flow': 2800.0, 'p75': 4000.0, 'available': True, 'congested': True},
        {'id': 'd2_a', 'edge': 'e2', 'flow': 2500.0, 'p75': 3500.0, 'available': True, 'congested': True},
        {'id': 'd2_b', 'edge': 'e2', 'flow': 2600.0, 'p75': 4500.0, 'available': True, 'congested': True},
    ]
    mapped_edges = ['e1', 'e1', 'e2', 'e2']
    routes = [['e1'], ['e2']]
    edge_matrix, edge_targets = aggregate_edge_targets(targets, mapped_edges, routes)

    assert edge_matrix.shape == (2, 2)
    assert edge_targets[0]['edge'] == 'e1'
    assert edge_targets[0]['flow'] == 3000.0
    assert not edge_targets[0]['congested']
    assert edge_targets[0]['p75'] == 0.0

    assert edge_targets[1]['edge'] == 'e2'
    assert edge_targets[1]['congested']
    assert edge_targets[1]['p75'] == 4000.0


def test_backlog_classification_downstream_congestion():
    from citypulse.experiments.obs_score import first_downstream_detectors
    conn = [MockConnection()]
    e_det = MockEdge('e_det', lanes=2)
    e_gate = MockEdge('e_gate', lanes=2, outgoing={e_det: conn})
    net = MockNet([e_det, e_gate])
    mapped = [{'id': 'DET_1', 'edge': 'e_det'}]

    downstream_map = first_downstream_detectors(net, mapped)
    assert downstream_map['e_gate'] == ['DET_1']

    profile_congested = {'DET_1': {'08:00': {'speed_kmh': {'median': 22.0}, 'occ': {'median': 28.0}}}}
    p = profile_congested['DET_1']['08:00']
    explained = p['speed_kmh']['median'] < 30 and p['occ']['median'] > 20
    assert explained is True

    profile_free = {'DET_1': {'08:00': {'speed_kmh': {'median': 45.0}, 'occ': {'median': 12.0}}}}
    p_free = profile_free['DET_1']['08:00']
    explained_free = p_free['speed_kmh']['median'] < 30 and p_free['occ']['median'] > 20
    assert explained_free is False


def test_network_path_and_hash_passed_through_and_recorded(tmp_path, monkeypatch):
    import json
    import hashlib
    from unittest.mock import MagicMock
    from citypulse.demand import bounded
    from citypulse.experiments import obs_score, obs_metrics

    fake_net = tmp_path / "custom.net.xml"
    fake_net.write_text("<net/>", encoding="utf-8")
    fake_meta = tmp_path / "custom_meta.json"
    fake_meta.write_text(json.dumps({"retained_detectors": ["AID02105"], "gates": []}), encoding="utf-8")
    expected_hash = hashlib.sha256(fake_net.read_bytes()).hexdigest()

    # 1. Test CLI argument passthrough across bounded, obs_score, obs_metrics
    import pytest
    monkeypatch.setattr("sumolib.net.readNet", lambda p: (_ for _ in ()).throw(ValueError(f"READNET:{p}")))
    with pytest.raises(ValueError, match=f"READNET:{str(fake_net.resolve()).replace('\\', '\\\\')}"):
        bounded.main(["--tag", "test_tag", "--net", str(fake_net), "--net-meta", str(fake_meta)])

    real_obs_run = obs_score.run
    mock_obs_run = MagicMock()
    monkeypatch.setattr(obs_score, "run", mock_obs_run)
    obs_score.main(["--tag", "test_tag", "--net", str(fake_net), "--net-meta", str(fake_meta)])
    mock_obs_run.assert_called_once_with("test_tag", 7200, net_path=str(fake_net), net_meta_path=str(fake_meta))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "run.json").write_text(json.dumps({"tag": "out", "retained_detectors": ["AID02105"]}), encoding="utf-8")
    monkeypatch.setattr(obs_metrics, "OUT", tmp_path)
    real_obs_metrics_score = obs_metrics.score
    mock_score = MagicMock(return_value={"tag": "out", "geh_lt5_share": 1.0, "speed_mae": 0.0, "occ_mae": 0.0,
                                         "congestion_agreement": 1.0, "detectors_speed_pass": 0, "pending_end": 0, "accepted": True})
    monkeypatch.setattr(obs_metrics, "score", mock_score)
    obs_metrics.main(["--tag", "out", "--net", str(fake_net), "--net-meta", str(fake_meta)])
    assert mock_score.call_args.kwargs["net_path"] == str(fake_net)
    assert mock_score.call_args.kwargs["net_meta_path"] == str(fake_meta)

    # 2. Test obs_score records network_path and network_sha256 in run.json & run_inputs.json
    (out_dir / "demand.rou.xml").write_text("<routes/>", encoding="utf-8")
    monkeypatch.setattr(obs_score, "OUT", tmp_path)
    monkeypatch.setattr(obs_score, "first_downstream_detectors", lambda n, m: {})
    mock_net_obj = MagicMock()
    mock_net_obj.getEdges.return_value = []
    monkeypatch.setattr("sumolib.net.readNet", lambda p: mock_net_obj)

    fake_tc = MagicMock()
    fake_tc.simulation.getDepartedIDList.return_value = []
    fake_tc.simulation.getArrivedNumber.return_value = 0
    fake_tc.simulation.getStartingTeleportNumber.return_value = 0
    fake_tc.simulation.getPendingVehicles.return_value = []
    fake_tc.vehicle.getIDCount.return_value = 0
    fake_tc.edge.getIDList.return_value = []
    monkeypatch.setitem(sys.modules, "libsumo", fake_tc)
    monkeypatch.setattr(obs_score, "init_signals", lambda tc: None)

    real_obs_run("out", end=1, net_path=fake_net, net_meta_path=fake_meta)

    run_json = json.loads((out_dir / "run.json").read_text())
    assert run_json["network_path"] == str(fake_net.resolve())
    assert run_json["network_sha256"] == expected_hash

    run_inputs_json = json.loads((out_dir / "run_inputs.json").read_text())
    assert run_inputs_json["network_path"] == str(fake_net.resolve())
    assert str(fake_net.resolve()) in run_inputs_json["input_sha256"]
    assert run_inputs_json["input_sha256"][str(fake_net.resolve())] == expected_hash

    # 3. Test obs_metrics records network_path in score.json
    raw_df = pd.DataFrame([dict(detector='AID02105', lane='AID02105_0', begin=3600, end=3630, q=1, speed=50, occ=10)])
    monkeypatch.setattr(obs_metrics, "read_e1", lambda p: raw_df)
    hold_df = pd.DataFrame([dict(detector='AID02105', bin_start=f'08:{m:02d}', date=day, split='holdout', speed_kmh=50.0, occ=10.0, coverage=1.0)
                            for m in range(0, 60, 5) for day in ['2026-09-29', '2026-09-30']])
    monkeypatch.setattr(pd, "read_parquet", lambda p: hold_df)
    bins = pd.DataFrame([dict(detector='AID02105', bin_start=f'08:{m:02d}', n_periods=10, flow_vph=120, speed_kmh=50.0, occ=10.0) for m in range(0, 60, 5)])
    monkeypatch.setattr(obs_metrics, "aggregate", lambda r: (pd.DataFrame(), bins))
    summary = real_obs_metrics_score(out_dir, run_json, net_path=fake_net, net_meta_path=fake_meta)
    score_json = json.loads((out_dir / "score.json").read_text())
    assert score_json["network_path"] == str(fake_net.resolve())
    assert score_json["network_sha256"] == expected_hash

