"""Unit tests for offline decision audit metrics and mechanics (docs/oct6-audit-and-pilot2-plan.md)."""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pytest

from citypulse.branching.audit_engine import (
    ACTIONS,
    T_D,
    build_proxy_resampled_routes,
)
from citypulse.experiments.decision_audit import (
    compute_crn_statistics,
    compute_metrics_from_raw,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROXY_ROU = REPO_ROOT / "scenarios" / "kwuntong" / "blite" / "synth5" / "proxy.rou.xml"


def make_tiny_synthetic_data(denom_val: float = 1.0) -> pd.DataFrame:
    """Create a tiny deterministic raw J table for 2 seeds across all actions and replications."""
    records = []
    # Seed 1:
    # Twin:
    # R1 (1..3): A2 is min (e.g. A0=100, A1=90, A2=80, A3=85, A4=88) -> a* = A2
    # R2 (4..6): A0=100, A2=82 -> G_T_hat = 100 - 82 = 18
    # Proxy:
    # M1 (1..3): A2 is min -> oracle = A2
    # M2 (4..6): A0=100, A2=85 (gain = 15) -> G_P = 15
    # BEE_signed = 18 - 15 = 3, BEE_abs = 3, Regret = 85 - 85 = 0
    # Calibration:
    # 7..9: A2 min
    # 10..12: A0=100, A2=84 (gain = 16) -> BEE_floor = |16 - 15| = 1
    s = 4201
    for a in ACTIONS:
        # Base twin cost
        cost_map_tw = {"A0": 100.0, "A1": 90.0, "A2": 80.0, "A3": 85.0, "A4": 88.0}
        cost_map_tw_r2 = {"A0": 100.0, "A1": 91.0, "A2": 82.0, "A3": 86.0, "A4": 89.0}
        for r in range(1, 4):
            records.append({"world": "twin", "seed": s, "replication": r, "action": a, "J": cost_map_tw[a]})
        for r in range(4, 7):
            records.append({"world": "twin", "seed": s, "replication": r, "action": a, "J": cost_map_tw_r2[a]})

        # Proxy cost
        cost_map_px_m1 = {"A0": 100.0, "A1": 102.0, "A2": 100.0 - denom_val, "A3": 103.0, "A4": 104.0}
        cost_map_px_m2 = {"A0": 100.0, "A1": 102.0, "A2": 100.0 - denom_val, "A3": 103.0, "A4": 104.0}
        for m in range(1, 4):
            records.append({"world": "proxy", "seed": s, "replication": m, "action": a, "J": cost_map_px_m1[a]})
        for m in range(4, 7):
            records.append({"world": "proxy", "seed": s, "replication": m, "action": a, "J": cost_map_px_m2[a]})

        # Calibration cost
        cost_map_cal = {"A0": 100.0, "A1": 91.0, "A2": 84.0, "A3": 86.0, "A4": 89.0}
        for c in range(7, 13):
            records.append({"world": "calibration", "seed": s, "replication": c, "action": a, "J": cost_map_cal[a]})

    # Seed 2: identical setup with small offset
    s2 = 4202
    for a in ACTIONS:
        c_tw = {"A0": 110.0, "A1": 100.0, "A2": 90.0, "A3": 95.0, "A4": 98.0}
        c_tw_r2 = {"A0": 110.0, "A1": 101.0, "A2": 92.0, "A3": 96.0, "A4": 99.0}
        for r in range(1, 4):
            records.append({"world": "twin", "seed": s2, "replication": r, "action": a, "J": c_tw[a]})
        for r in range(4, 7):
            records.append({"world": "twin", "seed": s2, "replication": r, "action": a, "J": c_tw_r2[a]})

        c_px_m1 = {"A0": 110.0, "A1": 112.0, "A2": 110.0 - denom_val, "A3": 113.0, "A4": 114.0}
        c_px_m2 = {"A0": 110.0, "A1": 112.0, "A2": 110.0 - denom_val, "A3": 113.0, "A4": 114.0}
        for m in range(1, 4):
            records.append({"world": "proxy", "seed": s2, "replication": m, "action": a, "J": c_px_m1[a]})
        for m in range(4, 7):
            records.append({"world": "proxy", "seed": s2, "replication": m, "action": a, "J": c_px_m2[a]})

        c_cal = {"A0": 110.0, "A1": 101.0, "A2": 94.0, "A3": 96.0, "A4": 99.0}
        for c in range(7, 13):
            records.append({"world": "calibration", "seed": s2, "replication": c, "action": a, "J": c_cal[a]})

    return pd.DataFrame(records)


def test_metrics_tiny_synthetic_table():
    """Verify that compute_metrics_from_raw returns expected metric values on tiny synthetic data."""
    df = make_tiny_synthetic_data(denom_val=15.0)
    per_seed, pooled = compute_metrics_from_raw(df)

    assert len(per_seed) == 2
    row1 = per_seed[0]
    assert row1["seed"] == 4201
    assert row1["a_star"] == "A2"
    assert row1["oracle"] == "A2"
    assert abs(row1["G_T_hat"] - 18.0) < 1e-9
    assert abs(row1["G_P"] - 15.0) < 1e-9
    assert abs(row1["BEE_signed"] - 3.0) < 1e-9
    assert abs(row1["BEE_abs"] - 3.0) < 1e-9
    assert abs(row1["BEE_rel"] - (3.0 / 100.0)) < 1e-9
    assert abs(row1["Regret"] - 0.0) < 1e-9
    assert row1["top1_agree"] == 1.0

    # Calibration floor check
    assert row1["a_star_floor"] == "A2"
    assert abs(row1["BEE_floor_abs"] - 1.0) < 1e-9

    # Pooled check
    assert pooled["BEE_abs"]["n"] == 2
    assert abs(pooled["BEE_abs"]["mean"] - 3.0) < 1e-9
    assert abs(pooled["BEE_floor_abs"]["mean"] - 1.0) < 1e-9
    assert "ci95_t" in pooled["BEE_abs"]
    assert "ci95_boot" in pooled["BEE_abs"]


def test_proxy_future_demand_replacement_assertion(tmp_path):
    """Verify that build_proxy_resampled_routes asserts no original future departure remains."""
    assert PROXY_ROU.exists(), f"Route file missing: {PROXY_ROU}"

    out_file = tmp_path / "test_resampled.rou.xml"
    orig_future_ids, n_resamp = build_proxy_resampled_routes(
        base_routes_path=PROXY_ROU,
        out_path=out_file,
        seed=4201,
        m=1,
        t_d=T_D,
        horizon=900.0,
    )

    assert len(orig_future_ids) > 0, "No original future departures identified"
    assert n_resamp > 0, "No resampled vehicles produced"

    # Read generated XML and check that zero original future IDs exist
    tree = ET.parse(out_file)
    written_ids = {v.get("id") for v in tree.getroot().iter("vehicle")}
    assert len(written_ids & orig_future_ids) == 0

    # Assert that if an original future ID is present, an assertion error is raised
    leaked_id = next(iter(orig_future_ids))
    root = tree.getroot()
    bad_veh = ET.SubElement(root, "vehicle", id=leaked_id, depart="5200.0", type="pdist")
    ET.SubElement(bad_veh, "route", edges="x1_in x1_out")
    bad_out = tmp_path / "bad.rou.xml"
    tree.write(bad_out)

    bad_tree = ET.parse(bad_out)
    bad_ids = {v.get("id") for v in bad_tree.getroot().iter("vehicle")}
    with pytest.raises(AssertionError, match="Original future departures leaked"):
        overlap = bad_ids & orig_future_ids
        assert len(overlap) == 0, f"Original future departures leaked: {overlap}"


def test_split_regret_denominator():
    """Verify the split-Regret denominator rule: not reported when denominator < 0.5 veh*h."""
    # Case A: Denominator >= 0.5 (e.g. 2.0 veh*h) -> Regret_rel is reported
    df_large = make_tiny_synthetic_data(denom_val=2.0)
    per_seed_large, _ = compute_metrics_from_raw(df_large)
    assert per_seed_large[0]["Regret_denom"] == 2.0
    assert per_seed_large[0]["Regret_rel"] is not None
    assert abs(per_seed_large[0]["Regret_rel"] - 0.0) < 1e-9

    # Case B: Denominator < 0.5 (e.g. 0.3 veh*h) -> Regret_rel is NOT reported (None)
    df_small = make_tiny_synthetic_data(denom_val=0.3)
    per_seed_small, _ = compute_metrics_from_raw(df_small)
    assert abs(per_seed_small[0]["Regret_denom"] - 0.3) < 1e-9
    assert per_seed_small[0]["Regret_rel"] is None


def test_compute_crn_statistics_synthetic():
    """Verify that compute_crn_statistics returns analytically expected correlation and VR on synthetic data."""
    # Synthetic dataset with M=6 replications
    # A0: base values with variance 350.0
    # A1: identical to A0 minus 5.0 (perfect correlation 1.0, VR 1.0)
    # A2: A0 + offset with known variance
    reps = list(range(1, 7))
    records = []
    j_a0 = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    j_a1 = [5.0, 15.0, 25.0, 35.0, 45.0, 55.0]
    j_a2 = [12.0, 18.0, 32.0, 38.0, 52.0, 58.0]

    for r, v0, v1, v2 in zip(reps, j_a0, j_a1, j_a2):
        records.append({"world": "proxy", "seed": 4201, "replication": r, "action": "A0", "J": v0})
        records.append({"world": "proxy", "seed": 4201, "replication": r, "action": "A1", "J": v1})
        records.append({"world": "proxy", "seed": 4201, "replication": r, "action": "A2", "J": v2})

    df = pd.DataFrame(records)
    stats = compute_crn_statistics(df, worlds=("proxy",), actions=("A1", "A2"), ref_action="A0")

    s4201 = stats["per_seed"][4201]["proxy"]
    # Action A1: perfectly correlated, zero difference variance -> corr = 1.0, VR = 1.0
    assert abs(s4201["corr"]["A1"] - 1.0) < 1e-9
    assert abs(s4201["vr"]["A1"] - 1.0) < 1e-9

    # Action A2: analytical checks
    # diff = [2, -2, 2, -2, 2, -2] -> Var(diff, ddof=1) = 4.8
    # Var(A0) = 350.0, Var(A2) = 330.8 -> Var(A0) + Var(A2) = 680.8
    # VR = 1 - 4.8 / 680.8 = 0.99294947...
    expected_vr = 1.0 - (4.8 / 680.8)
    assert abs(s4201["vr"]["A2"] - expected_vr) < 1e-6
    # corr = 0.99334458...
    expected_corr = float(np.corrcoef(j_a0, j_a2)[0, 1])
    assert abs(s4201["corr"]["A2"] - expected_corr) < 1e-9

    # Pooled medians
    pm = stats["pooled_medians"]["proxy"]
    assert abs(pm["median_corr"]["A1"] - 1.0) < 1e-9
    assert abs(pm["median_vr"]["A1"] - 1.0) < 1e-9
    assert abs(pm["median_corr"]["A2"] - expected_corr) < 1e-9
    assert abs(pm["median_vr"]["A2"] - expected_vr) < 1e-6

