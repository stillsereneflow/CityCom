"""Unit tests for dev_runs collection driver and verification logic."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from citypulse.experiments.dev_runs import (
    build_manifest, check_attempt_completeness, check_pairing,
    is_infrastructure_failure, run_check
)


def test_build_manifest():
    manifest = build_manifest()
    assert "expected_detector_ids" in manifest
    assert len(manifest["expected_detector_ids"]) == 14
    assert len(manifest["timestamps"]) == 240
    assert manifest["expected_observation_keys_count"] == 14 * 240
    assert manifest["required_snapshots"] == [4500, 4800, 5100, 5400, 5700, 6000, 6300, 6600]
    assert len(manifest["forecast_cells"]["5min"]) == 8
    assert len(manifest["forecast_cells"]["15min"]) == 7
    assert "run_info.json" in manifest["required_logs"]["common"]
    assert "twin/state_trace.jsonl" in manifest["required_logs"]["evt_only"]


def test_is_infrastructure_failure():
    # 0xC0000142 exit codes
    assert is_infrastructure_failure(-1073741502, 0, "", "")[0] is True
    assert is_infrastructure_failure(0, 3221225794, "", "")[0] is True

    # Stderr signatures
    assert is_infrastructure_failure(1, 0, "Address already in use", "")[0] is True
    assert is_infrastructure_failure(0, 1, "", "CreateProcess failed: Access is denied")[0] is True
    assert is_infrastructure_failure(1, 0, "No space left on device", "")[0] is True

    # Non-infrastructure failure
    is_infra, _ = is_infrastructure_failure(1, 0, "ValueError: invalid option", "")
    assert is_infra is False


def make_mock_twin_log(manifest: dict) -> pd.DataFrame:
    rows = []
    dets = manifest["expected_detector_ids"]
    ts = manifest["timestamps"]
    for t in ts:
        for d in dets:
            rows.append({
                "t": float(t),
                "detector": str(d),
                "obs_valid": True,
                "obs_q": 10,
                "obs_v": 45.0,
                "obs_o": 5.0,
                "twin_q": 10,
                "twin_v": 45.0,
                "twin_o": 5.0,
            })
    return pd.DataFrame(rows)


def create_mock_attempt(attempt_dir: Path, arm: str, manifest: dict,
                        rc_p: int = 0, rc_t: int = 0,
                        with_flagged_eval: bool = False,
                        missing_file: str = None,
                        corrupt_forecast: bool = False,
                        corrupt_twin_log: bool = False):
    twin_dir = attempt_dir / "twin"
    proxy_dir = attempt_dir / "proxy"
    twin_dir.mkdir(parents=True, exist_ok=True)
    proxy_dir.mkdir(parents=True, exist_ok=True)

    info = {
        "run_name": f"{arm}_noi_4401", "scenario": "NOI", "seed": 4401, "arm": arm,
        "proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": 50.0,
    }
    (attempt_dir / "run_info.json").write_text(json.dumps(info), encoding="utf-8")

    # Common logs
    (attempt_dir / "proxy_stdout.log").write_text("proxy stdout", encoding="utf-8")
    (attempt_dir / "proxy_stderr.log").write_text("", encoding="utf-8")
    (attempt_dir / "twin_stdout.log").write_text("twin stdout", encoding="utf-8")
    (attempt_dir / "twin_stderr.log").write_text("", encoding="utf-8")
    pd.DataFrame({"t": [30], "m": [1.0]}).to_parquet(twin_dir / "assim_log.parquet")

    # Forecasts
    forecasts = {}
    for t in manifest["required_snapshots"]:
        t_5, t_15 = t + 300, t + 900
        forecasts[str(t)] = {
            "5min": {"pred": 1, "truth": None if (corrupt_forecast and t == 4500) else 1},
            "15min": {"pred": 2, "truth": 2 if t_15 <= 7200 else None},
        }
    (attempt_dir / "queue_forecasts.json").write_text(json.dumps({"forecasts": forecasts}), encoding="utf-8")

    # Snapshots
    for t in manifest["required_snapshots"]:
        (twin_dir / f"twin_state_{t}.json").write_text("{}", encoding="utf-8")
        (twin_dir / f"twin_state_{t}.xml.gz").write_bytes(b"mock")

    # Twin log
    df_tl = make_mock_twin_log(manifest)
    if corrupt_twin_log:
        df_tl = df_tl.iloc[:-1]  # drop one row
    df_tl.to_parquet(twin_dir / "twin_log.parquet")

    # EVT logs
    if arm == "evt":
        (twin_dir / "state_trace.jsonl").write_text('{"t": 30, "state": "NORMAL"}\n', encoding="utf-8")
        (twin_dir / "replacement_log.jsonl").write_text("", encoding="utf-8")
        if with_flagged_eval:
            (twin_dir / "event_log.jsonl").write_text(
                json.dumps({"t": 4500, "excluded": {"error": "crashed replay"}}) + "\n",
                encoding="utf-8"
            )
        else:
            (twin_dir / "event_log.jsonl").write_text("", encoding="utf-8")

    if missing_file:
        target = attempt_dir / missing_file
        if target.exists():
            target.unlink()


def test_check_attempt_completeness_synthetic(tmp_path):
    manifest = build_manifest()

    # 1. Complete CONV attempt
    att_conv = tmp_path / "conv_att"
    create_mock_attempt(att_conv, "conv", manifest)
    res = check_attempt_completeness(att_conv, "conv", manifest)
    assert res["complete"] is True
    assert res["flagged"] is False
    assert len(res["reasons"]) == 0

    # 2. Complete EVT attempt
    att_evt = tmp_path / "evt_att"
    create_mock_attempt(att_evt, "evt", manifest)
    res = check_attempt_completeness(att_evt, "evt", manifest)
    assert res["complete"] is True
    assert res["flagged"] is False

    # 3. Complete-but-flagged EVT attempt
    att_flagged = tmp_path / "evt_flagged"
    create_mock_attempt(att_flagged, "evt", manifest, with_flagged_eval=True)
    res = check_attempt_completeness(att_flagged, "evt", manifest)
    assert res["complete"] is True
    assert res["flagged"] is True
    assert len(res["flag_reasons"]) == 1

    # 4. Incomplete: missing log file
    att_miss = tmp_path / "miss_att"
    create_mock_attempt(att_miss, "conv", manifest, missing_file="proxy_stdout.log")
    res = check_attempt_completeness(att_miss, "conv", manifest)
    assert res["complete"] is False

    # 5. Incomplete: non-zero return code
    att_rc = tmp_path / "rc_att"
    create_mock_attempt(att_rc, "conv", manifest, rc_p=1)
    res = check_attempt_completeness(att_rc, "conv", manifest)
    assert res["complete"] is False

    # 6. Incomplete: missing forecast truth
    att_fc = tmp_path / "fc_att"
    create_mock_attempt(att_fc, "conv", manifest, corrupt_forecast=True)
    res = check_attempt_completeness(att_fc, "conv", manifest)
    assert res["complete"] is False

    # 7. Incomplete: missing twin_log detector key
    att_tl = tmp_path / "tl_att"
    create_mock_attempt(att_tl, "conv", manifest, corrupt_twin_log=True)
    res = check_attempt_completeness(att_tl, "conv", manifest)
    assert res["complete"] is False


def test_check_pairing_synthetic(tmp_path):
    manifest = build_manifest()
    att_evt = tmp_path / "evt"
    att_conv = tmp_path / "conv"
    create_mock_attempt(att_evt, "evt", manifest)
    create_mock_attempt(att_conv, "conv", manifest)

    # 1. Exact match
    res = check_pairing(att_evt, att_conv)
    assert res["passed"] is True
    assert res["keys_match"] is True
    assert res["columns_match"]["obs_q"] is True
    assert len(res["mismatches"]) == 0

    # 2. Key mismatch
    df_mismatch = make_mock_twin_log(manifest)
    df_mismatch.loc[0, "detector"] = "DIFFERENT"
    df_mismatch.to_parquet(att_conv / "twin" / "twin_log.parquet")
    res = check_pairing(att_evt, att_conv)
    assert res["passed"] is False

    # 3. Value mismatch
    df_mismatch = make_mock_twin_log(manifest)
    df_mismatch.loc[0, "obs_q"] = 999
    df_mismatch.to_parquet(att_conv / "twin" / "twin_log.parquet")
    res = check_pairing(att_evt, att_conv)
    assert res["passed"] is False
    assert "obs_q: value mismatch on valid rows" in res["mismatches"]

    # 4. Null pattern mismatch
    df_mismatch = make_mock_twin_log(manifest)
    df_mismatch.loc[0, "obs_v"] = np.nan
    df_mismatch.to_parquet(att_conv / "twin" / "twin_log.parquet")
    res = check_pairing(att_evt, att_conv)
    assert res["passed"] is False
    assert "obs_v: null pattern mismatch" in res["mismatches"]


def test_slot_accounting_synthetic(tmp_path):
    manifest = build_manifest()
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "out"

    # Slot 1: complete attempt_1
    create_mock_attempt(runs_dir / "conv_noi_4401" / "attempt_1", "conv", manifest)

    # Slot 2: complete-but-flagged attempt_1
    create_mock_attempt(runs_dir / "evt_noi_4401" / "attempt_1", "evt", manifest, with_flagged_eval=True)

    # Slot 3: attempt_1 infra failure, attempt_2 complete
    create_mock_attempt(runs_dir / "conv_shk_4401" / "attempt_1", "conv", manifest, rc_p=-1073741502)
    create_mock_attempt(runs_dir / "conv_shk_4401" / "attempt_2", "conv", manifest)

    # Slot 4: attempt_1 non-infra failure -> permanently failed
    create_mock_attempt(runs_dir / "conv_det_4401" / "attempt_1", "conv", manifest, rc_p=1)

    # Slot 5: attempt_1 infra failure, attempt_2 incomplete -> permanently failed
    create_mock_attempt(runs_dir / "evt_det_4401" / "attempt_1", "evt", manifest, rc_p=-1073741502)
    create_mock_attempt(runs_dir / "evt_det_4401" / "attempt_2", "evt", manifest, rc_p=1)

    res = run_check(runs_dir, out_dir, manifest=manifest)
    summary = res["slots"]["summary"]
    slots = res["slots"]["slots"]

    assert summary["complete"] == 2  # conv_noi_4401 and conv_shk_4401
    assert summary["complete_but_flagged"] == 1  # evt_noi_4401
    assert summary["permanently_failed"] == 2  # conv_det_4401 and evt_det_4401

    assert slots["conv_noi_4401"]["status"] == "complete"
    assert slots["evt_noi_4401"]["status"] == "complete-but-flagged"
    assert slots["conv_shk_4401"]["status"] == "complete"
    assert slots["conv_det_4401"]["status"] == "permanently_failed"
    assert slots["evt_det_4401"]["status"] == "permanently_failed"
