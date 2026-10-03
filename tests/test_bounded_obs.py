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
