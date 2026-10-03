"""Tests for observation dataset module (obs_set)."""
import json
import pandas as pd
import pytest

from citypulse.hkdata.obs_set import (
    aggregate_to_bins,
    build_profile,
    load_detector_map,
    process_period_records,
    run,
    time_to_sec,
)


@pytest.fixture
def synthetic_data(tmp_path):
    det_map_data = {
        "mapped": [
            {"id": "D1", "edge": "edge_1", "n_lanes": 2},
            {"id": "D2", "edge": "edge_2", "n_lanes": 2},
        ]
    }
    map_file = tmp_path / "detector_map.json"
    map_file.write_text(json.dumps(det_map_data), encoding="utf-8")

    rows = [
        # D1, 07:00:00 inside window, all valid
        {"date": "2026-09-21", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 1", "speed": 60.0, "occupancy": 10.0, "volume": 2.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-21", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 2", "speed": 80.0, "occupancy": 20.0, "volume": 3.0, "sd": 1.0, "valid": "Y"},

        # D1, 07:00:30 inside window, one invalid lane -> entire period dropped
        {"date": "2026-09-21", "period_from": "07:00:30", "period_to": "07:01:00", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 1", "speed": 50.0, "occupancy": 12.0, "volume": 1.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-21", "period_from": "07:00:30", "period_to": "07:01:00", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 2", "speed": 50.0, "occupancy": 12.0, "volume": 1.0, "sd": 1.0, "valid": "N"},

        # D1, 07:01:00 inside window, all valid
        {"date": "2026-09-21", "period_from": "07:01:00", "period_to": "07:01:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 1", "speed": 70.0, "occupancy": 14.0, "volume": 4.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-21", "period_from": "07:01:00", "period_to": "07:01:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 2", "speed": 70.0, "occupancy": 16.0, "volume": 1.0, "sd": 1.0, "valid": "Y"},

        # D1, 06:55:00 outside window -> dropped
        {"date": "2026-09-21", "period_from": "06:55:00", "period_to": "06:55:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 1", "speed": 60.0, "occupancy": 5.0, "volume": 2.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-21", "period_from": "06:55:00", "period_to": "06:55:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 2", "speed": 60.0, "occupancy": 5.0, "volume": 2.0, "sd": 1.0, "valid": "Y"},

        # D2, 07:00:00 inside window, all valid
        {"date": "2026-09-21", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D2",
         "direction": "S", "lane_id": "Lane 1", "speed": 100.0, "occupancy": 5.0, "volume": 10.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-21", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D2",
         "direction": "S", "lane_id": "Lane 2", "speed": 100.0, "occupancy": 5.0, "volume": 10.0, "sd": 1.0, "valid": "Y"},
    ]

    holdout_rows = [
        # D1, 07:00:00 on holdout day
        {"date": "2026-09-29", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 1", "speed": 65.0, "occupancy": 8.0, "volume": 5.0, "sd": 1.0, "valid": "Y"},
        {"date": "2026-09-29", "period_from": "07:00:00", "period_to": "07:00:30", "detector_id": "D1",
         "direction": "N", "lane_id": "Lane 2", "speed": 75.0, "occupancy": 12.0, "volume": 5.0, "sd": 1.0, "valid": "Y"},
    ]

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    calib_csv = raw_dir / "2026-09-21.csv"
    pd.DataFrame(rows).to_csv(calib_csv, index=False)
    holdout_csv = raw_dir / "2026-09-29.csv"
    pd.DataFrame(holdout_rows).to_csv(holdout_csv, index=False)

    return {
        "raw_dir": raw_dir,
        "map_file": map_file,
        "det_map": {"D1": "edge_1", "D2": "edge_2"},
        "df_calib": pd.DataFrame(rows),
        "df_holdout": pd.DataFrame(holdout_rows),
    }


def test_invalid_lane_period_dropped(synthetic_data):
    det_map = synthetic_data["det_map"]
    start_sec, end_sec = time_to_sec("07:00"), time_to_sec("09:00")
    agg, counts = process_period_records(synthetic_data["df_calib"], det_map, start_sec, end_sec)

    # 1. Check invalid-lane period dropped
    assert counts["invalid_lane"] == 1
    assert "07:00:30" not in agg["period_from"].values

    # Check outside-window period dropped
    assert counts["outside_window"] == 1
    assert "06:55:00" not in agg["period_from"].values


def test_lane_aggregation(synthetic_data):
    det_map = synthetic_data["det_map"]
    start_sec, end_sec = time_to_sec("07:00"), time_to_sec("09:00")
    agg, _ = process_period_records(synthetic_data["df_calib"], det_map, start_sec, end_sec)

    # 2. Check lane aggregation (flow sum, volume-weighted speed, mean occupancy)
    p1 = agg[(agg["detector"] == "D1") & (agg["period_from"] == "07:00:00")].iloc[0]
    assert p1["flow"] == 5.0  # 2 + 3
    assert abs(p1["speed"] - 72.0) < 1e-6  # (60*2 + 80*3) / 5
    assert abs(p1["occ"] - 15.0) < 1e-6  # (10 + 20) / 2
    assert p1["edge"] == "edge_1"


def test_bin_aggregation_and_splits(synthetic_data):
    det_map = synthetic_data["det_map"]
    start_sec, end_sec = time_to_sec("07:00"), time_to_sec("09:00")
    agg_c, _ = process_period_records(synthetic_data["df_calib"], det_map, start_sec, end_sec)
    agg_h, _ = process_period_records(synthetic_data["df_holdout"], det_map, start_sec, end_sec)

    combined = pd.concat([agg_c, agg_h], ignore_index=True)
    df_bins = aggregate_to_bins(combined, bin_sec=300, start_sec=start_sec, calib_dates={"2026-09-21"})

    # 3. Check bin flow_vph = mean 30 s flow * 120
    d1_bin = df_bins[(df_bins["detector"] == "D1") & (df_bins["date"] == "2026-09-21")].iloc[0]
    # mean 30-s flow is (5 + 5) / 2 = 5.0 -> flow_vph = 5.0 * 120 = 600.0
    assert d1_bin["flow_vph"] == 600.0
    assert abs(d1_bin["speed_kmh"] - 71.0) < 1e-6
    assert abs(d1_bin["occ"] - 15.0) < 1e-6

    # 4. Check coverage: 2 valid periods in 300s bin (max 10) -> 0.2
    assert d1_bin["n_periods"] == 2
    assert abs(d1_bin["coverage"] - 0.2) < 1e-6

    # 5. Check split labels
    assert d1_bin["split"] == "calib"
    d1_holdout = df_bins[(df_bins["detector"] == "D1") & (df_bins["date"] == "2026-09-29")].iloc[0]
    assert d1_holdout["split"] == "holdout"


def test_end_to_end_run(synthetic_data, tmp_path):
    out_dir = tmp_path / "out"
    run(
        calib=["2026-09-21"],
        holdout=["2026-09-29"],
        start="07:00",
        end="09:00",
        bin_size=300,
        raw_dir=synthetic_data["raw_dir"],
        det_map_path=synthetic_data["map_file"],
        out_dir=out_dir,
    )

    parquet_file = out_dir / "obs_bins.parquet"
    assert parquet_file.exists()
    df_p = pd.read_parquet(parquet_file)
    expected_cols = ["date", "detector", "edge", "bin_start", "flow_vph", "speed_kmh", "occ", "n_periods", "coverage", "split"]
    assert list(df_p.columns) == expected_cols

    json_file = out_dir / "obs_profile.json"
    assert json_file.exists()
    with open(json_file, "r", encoding="utf-8") as f:
        profile = json.load(f)
    assert "meta" in profile
    assert profile["meta"]["dropped_periods"]["invalid_lane"] == 1
    assert profile["meta"]["dropped_periods"]["outside_window"] == 1
