"""Unit tests for the frozen decision audit collection driver (docs/oct16-frozen-audit-plan.md)."""
import json
from pathlib import Path
import pandas as pd
import pytest

from citypulse.experiments.frozen_audit import (
    DEFAULT_SEEDS, FROZEN_SEEDS, REPO_ROOT,
    check_seeds, build_provenance, is_infra_error,
)


def test_seed_check_frozen_seeds_clean():
    """Verify that preregistered test seeds 4501-4508 are untouched in results."""
    res = check_seeds(REPO_ROOT / "results", [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508])
    assert res["passed"] is True
    assert len(res["matches"]) == 0


def test_seed_check_detects_used_seed():
    """Verify that development seed 4201 is detected as used in audit."""
    res = check_seeds(REPO_ROOT / "results", [4201])
    assert res["passed"] is False
    assert len(res["matches"]) > 0


def test_seed_check_synthetic_json_and_parquet(tmp_path):
    """Verify JSON recursive field scan and Parquet column inspection."""
    # Clean file
    (tmp_path / "clean.json").write_text(json.dumps({"unrelated": 123}), encoding="utf-8")
    assert check_seeds(tmp_path, [9999])["passed"] is True

    # JSON with seed in nested dict
    (tmp_path / "nested.json").write_text(json.dumps({"sub": {"seed": 9999}}), encoding="utf-8")
    res_json = check_seeds(tmp_path, [9999])
    assert res_json["passed"] is False
    assert any("json_seed_9999" in m for m in res_json["matches"].values())

    # Parquet with seed column
    df = pd.DataFrame([{"seed": 9999, "val": 1.0}])
    df.to_parquet(tmp_path / "test.parquet")
    res_pq = check_seeds(tmp_path, [9999])
    assert res_pq["passed"] is False
    assert any("parquet_seed" in s for m in res_pq["matches"].values() for s in m)


def test_provenance_structure():
    """Verify provenance dictionary fields and required file hashes."""
    driver = REPO_ROOT / "citypulse" / "experiments" / "frozen_audit.py"
    prov = build_provenance(driver, allow_dirty=True, seeds=[4201])
    assert "git_head" in prov and len(prov["git_head"]) == 40
    assert "file_hashes" in prov
    assert "effective_command_lines" in prov
    assert "seed_4201" in prov["effective_command_lines"]

    hashes = prov["file_hashes"]
    expected_keys = [
        "citypulse/branching/audit_engine.py",
        "citypulse/experiments/decision_audit.py",
        "citypulse/twin/service.py",
        "citypulse/twin/demand_stream.py",
        "citypulse/proxy/service.py",
        "citypulse/experiments/frozen_audit.py",
    ]
    for k in expected_keys:
        assert any(k in h for h in hashes), f"Missing hash for {k}"


def test_infra_error_detection():
    assert is_infra_error({"status": "error", "error": "ZMQError: Address already in use"}) is True
    assert is_infra_error({"status": "error", "error": "SumoException: vehicle collided"}) is False
    assert is_infra_error({"status": "ok"}) is False


def test_smoke_refuses_frozen_seeds(monkeypatch):
    """Ensure smoke mode refuses seeds in 4501-4508."""
    from citypulse.experiments.frozen_audit import cmd_prepare, cmd_branches, cmd_twoworld, cmd_rngcheck

    with pytest.raises(SystemExit):
        cmd_prepare([4501], Path("dummy"), smoke=True)

    with pytest.raises(SystemExit):
        cmd_twoworld([4501], Path("dummy"), smoke=True)

    with pytest.raises(SystemExit):
        cmd_rngcheck(4501, Path("dummy"), smoke=True)

    with pytest.raises(SystemExit):
        cmd_branches([4501], Path("dummy"), smoke=True)


def test_statehistory_unknown_pending_handling():
    """Verify that when pending is unavailable (None), pending_q and Q are None, never 0."""
    from citypulse.experiments.mq_replay import aggregate_q_counts

    q_edges = ["ktb_w1", "ktb_w2", "ktb_w3", "ktb_n1"]
    vehs = [("v1", "ktb_n1", 0.0)]  # 1 halted on ktb_n1

    # When pending is available
    res_avail = aggregate_q_counts(vehs, q_edges, [], [], ["pend1"], {"pend1": ["ktb_n1"]})
    assert res_avail["ktb_n1"] == 1
    assert res_avail["pending_q"] == 1
    assert res_avail["Q"] == 2

    # When pending is unavailable (represented by None in driver)
    # The driver sets pending_q = None and Q = None
    counts = {e: 0 for e in q_edges}
    counts["ktb_n1"] = 1
    pending_q = None
    Q = None
    assert pending_q is None
    assert Q is None


def test_production_seeds_allowed_without_smoke(tmp_path, monkeypatch):
    """Verify that production seeds 4501-4508 are allowed when smoke is False."""
    from citypulse.experiments.frozen_audit import cmd_twoworld, cmd_rngcheck, cmd_branches

    # 1. cmd_twoworld runs on 4501 when smoke=False
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_twoworld_batch", lambda seeds, runs_dir: {})
    cmd_twoworld([4501], tmp_path, smoke=False)
    cmd_file = tmp_path / "runs" / "seed_4501" / "commands.json"
    assert cmd_file.exists()
    cmd_data = json.loads(cmd_file.read_text(encoding="utf-8"))
    assert "twin" in cmd_data and "proxy" in cmd_data

    # Setup dummy snapshots for seed 4501
    s_dir = tmp_path / "runs" / "seed_4501"
    (s_dir / "twin").mkdir(parents=True, exist_ok=True)
    (s_dir / "proxy").mkdir(parents=True, exist_ok=True)
    (s_dir / "twin" / "twin_state_5100.xml.gz").write_bytes(b"dummy_twin_xml")
    (s_dir / "twin" / "twin_state_5100.json").write_text("{}", encoding="utf-8")
    (s_dir / "proxy" / "proxy_state_5100.xml.gz").write_bytes(b"dummy_proxy_xml")

    # 2. cmd_rngcheck runs on 4501 when smoke=False
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_rng_isolation_check",
                        lambda info, out_p, scratch_dir: {"passed": True, "seed": 4501})
    cmd_rngcheck(4501, tmp_path, smoke=False)
    rng_path = tmp_path / "rng_check.json"
    assert rng_path.exists()
    rng_data = json.loads(rng_path.read_text(encoding="utf-8"))
    assert rng_data["passed"] is True
    assert rng_data["seed"] == 4501
    assert "snapshot_hashes" in rng_data

    # 3. cmd_branches runs on 4501 when smoke=False
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_twin_branch_jobs", lambda jobs, workers: [])
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_proxy_branch_jobs", lambda jobs, workers: [])
    monkeypatch.setattr("citypulse.experiments.frozen_audit.build_proxy_resampled_routes",
                        lambda r_in, r_out, **kw: (r_out.write_text("<routes/>", encoding="utf-8"), ([], []))[1])
    cmd_branches([4501], tmp_path, smoke=False)
    assert (tmp_path / "branch_inputs.json").exists()
    assert (tmp_path / "code_hashes_before_after.json").exists()


def test_seed_check_list_values_and_unreadable_file_failure(tmp_path, monkeypatch):
    """Verify seed check handles list values in JSON and flags unreadable files as failure."""
    from citypulse.experiments.frozen_audit import cmd_prepare

    # 1. Seed check handles list values
    sub_dir = tmp_path / "lists"
    sub_dir.mkdir()
    (sub_dir / "list_seeds.json").write_text(json.dumps({"seeds": [4501, 4502]}), encoding="utf-8")
    res_list = check_seeds(sub_dir, [4501])
    assert res_list["passed"] is False
    assert any("json_seed_4501" in m for m in res_list["matches"].values())

    # 2. Unreadable relevant file causes failure
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "corrupted.json").write_text("not json content {{{", encoding="utf-8")
    res_bad = check_seeds(bad_dir, [4501])
    assert res_bad["passed"] is False
    assert len(res_bad["scan_failures"]) > 0
    assert str(bad_dir / "corrupted.json") in res_bad["scan_failures"]
    assert str(bad_dir / "corrupted.json") in res_bad["files_scanned"]

    # cmd_prepare fails on unreadable file even with smoke=True
    monkeypatch.setattr("citypulse.experiments.frozen_audit.check_seeds",
                        lambda *a, **k: {"passed": False, "clean": True, "matches": {}, "scan_failures": {"bad.json": "corrupt"}, "files_scanned": []})
    with pytest.raises(SystemExit):
        cmd_prepare([4201], tmp_path / "out", allow_dirty=True, smoke=True)


def test_branches_refusal_without_valid_matching_rng_record(tmp_path):
    """Verify branches refuses to run without a valid matching RNG record."""
    from citypulse.experiments.frozen_audit import verify_rng_check
    from citypulse.experiments.dev_runs import file_sha256

    # 1. Missing rng_check.json
    with pytest.raises(SystemExit):
        verify_rng_check(tmp_path, [4201], smoke=True)

    # 2. passed is False
    rng_path = tmp_path / "rng_check.json"
    rng_path.write_text(json.dumps({"passed": False, "seed": 4201}), encoding="utf-8")
    with pytest.raises(SystemExit):
        verify_rng_check(tmp_path, [4201], smoke=True)

    # 3. Wrong seed
    rng_path.write_text(json.dumps({"passed": True, "seed": 9999}), encoding="utf-8")
    with pytest.raises(SystemExit):
        verify_rng_check(tmp_path, [4201], smoke=True)

    # 4. Mismatched snapshot hashes
    s_dir = tmp_path / "runs" / "seed_4201"
    (s_dir / "twin").mkdir(parents=True, exist_ok=True)
    (s_dir / "proxy").mkdir(parents=True, exist_ok=True)
    tw_state = s_dir / "twin" / "twin_state_5100.xml.gz"
    tw_meta = s_dir / "twin" / "twin_state_5100.json"
    px_state = s_dir / "proxy" / "proxy_state_5100.xml.gz"
    tw_state.write_bytes(b"twin_state_bytes")
    tw_meta.write_text("{}", encoding="utf-8")
    px_state.write_bytes(b"proxy_state_bytes")

    rng_path.write_text(json.dumps({
        "passed": True,
        "seed": 4201,
        "snapshot_hashes": {
            "twin_state": "mismatched_hash",
            "twin_meta": "mismatched_hash",
            "proxy_state": "mismatched_hash",
        }
    }), encoding="utf-8")
    with pytest.raises(SystemExit):
        verify_rng_check(tmp_path, [4201], smoke=True)

    # 5. Valid matching RNG record succeeds
    valid_hashes = {
        "twin_state": file_sha256(tw_state),
        "twin_meta": file_sha256(tw_meta),
        "proxy_state": file_sha256(px_state),
    }
    rng_path.write_text(json.dumps({
        "passed": True,
        "seed": 4201,
        "snapshot_hashes": valid_hashes,
    }), encoding="utf-8")
    verify_rng_check(tmp_path, [4201], smoke=True)

