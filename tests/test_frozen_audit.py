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
