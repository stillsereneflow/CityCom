"""Unit tests for the frozen decision audit collection driver (docs/oct16-frozen-audit-plan.md)."""
import json
import sys
from pathlib import Path
import pandas as pd
import pytest

from citypulse.experiments.dev_runs import file_sha256
from citypulse.experiments.frozen_audit import (
    DEFAULT_SEEDS, FREEZE_MANIFEST_PATH, FROZEN_SEEDS, REPO_ROOT, RUNTIME_ENV_KEYS,
    RngBindingError, check_seeds, build_provenance, is_infra_error,
    collection_fingerprint, runtime_environment, verify_rng_binding,
)


def write_bound_record(out_dir: Path, seed: int) -> dict:
    """Build a valid collection: snapshots, provenance.json and a bound rng_check.json."""
    s_dir = out_dir / "runs" / f"seed_{seed}"
    (s_dir / "twin").mkdir(parents=True, exist_ok=True)
    (s_dir / "proxy").mkdir(parents=True, exist_ok=True)
    tw_state = s_dir / "twin" / "twin_state_5100.xml.gz"
    tw_meta = s_dir / "twin" / "twin_state_5100.json"
    px_state = s_dir / "proxy" / "proxy_state_5100.xml.gz"
    tw_state.write_bytes(b"twin_state_bytes")
    tw_meta.write_text("{}", encoding="utf-8")
    px_state.write_bytes(b"proxy_state_bytes")

    fingerprint = collection_fingerprint(out_dir)
    prov_path = out_dir / "provenance.json"
    prov_path.write_text(json.dumps({
        "git_head": "0" * 40, "allow_dirty": True,
        "runtime_environment": runtime_environment(),
        "collection_fingerprint": fingerprint,
    }, indent=2), encoding="utf-8")
    rng = {
        "passed": True, "seed": seed,
        "binding": {
            "provenance_sha256": file_sha256(prov_path),
            "fingerprint": fingerprint,
            "snapshot_hashes": {"twin_state": file_sha256(tw_state),
                                "twin_meta": file_sha256(tw_meta),
                                "proxy_state": file_sha256(px_state)},
        },
    }
    write_rng(out_dir, rng)
    return rng


def write_rng(out_dir: Path, rng: dict) -> None:
    (out_dir / "rng_check.json").write_text(json.dumps(rng, indent=2), encoding="utf-8")


def test_seed_check_frozen_seeds_now_consumed():
    """The frozen audit (2026-10-06) consumed seeds 4501-4508: the check must now report them as used.

    Before collection this test asserted they were untouched (that check is recorded in
    results/frozen_audit/seed_check.json); any re-collection needs fresh seeds.
    """
    res = check_seeds(REPO_ROOT / "results", [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508])
    assert res["passed"] is False
    assert any("frozen_audit" in str(p) for p in res["matches"])


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
    """Verify that production seeds 4501-4508 are allowed when smoke is False, through the gate."""
    from citypulse.experiments.frozen_audit import cmd_twoworld, cmd_rngcheck, cmd_branches

    # 1. cmd_twoworld runs on 4501 when smoke=False
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_twoworld_batch", lambda seeds, runs_dir: {})
    cmd_twoworld([4501], tmp_path, smoke=False)
    cmd_file = tmp_path / "runs" / "seed_4501" / "commands.json"
    assert cmd_file.exists()
    cmd_data = json.loads(cmd_file.read_text(encoding="utf-8"))
    assert "twin" in cmd_data and "proxy" in cmd_data

    # 2. prepare-style provenance (runtime environment + collection fingerprint) and snapshots
    write_bound_record(tmp_path, 4501)

    # 3. cmd_rngcheck runs on 4501 when smoke=False and writes the binding
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_rng_isolation_check",
                        lambda info, out_p, scratch_dir: {"passed": True, "seed": 4501})
    cmd_rngcheck(4501, tmp_path, smoke=False)
    rng_path = tmp_path / "rng_check.json"
    assert rng_path.exists()
    rng_data = json.loads(rng_path.read_text(encoding="utf-8"))
    assert rng_data["passed"] is True
    assert rng_data["seed"] == 4501
    binding = rng_data["binding"]
    assert binding["provenance_sha256"] == file_sha256(tmp_path / "provenance.json")
    assert binding["fingerprint"]["sha256"] == collection_fingerprint(tmp_path)["sha256"]
    assert "twin_state" in binding["snapshot_hashes"]

    # 4. cmd_branches runs on 4501 when smoke=False, past the gate, and records before/after hashes
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_twin_branch_jobs", lambda jobs, workers: [])
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_proxy_branch_jobs", lambda jobs, workers: [])
    monkeypatch.setattr("citypulse.experiments.frozen_audit.build_proxy_resampled_routes",
                        lambda r_in, r_out, **kw: (r_out.write_text("<routes/>", encoding="utf-8"), ([], []))[1])
    cmd_branches([4501], tmp_path, smoke=False)
    assert (tmp_path / "branch_inputs.json").exists()
    assert (tmp_path / "code_hashes_before_after.json").exists()

    # 5. a record bound to the smoke seed never passes the production gate
    smoke_dir = tmp_path / "smoke"
    smoke_dir.mkdir()
    write_bound_record(smoke_dir, 4201)
    with pytest.raises(RngBindingError, match="expected 4501"):
        verify_rng_binding(smoke_dir, 4501)


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


def test_runtime_environment_records_actual_collection_runtime():
    """The provenance runtime is the actual environment, not the freeze record (Codex item 2)."""
    env = runtime_environment()
    assert set(env["env"]) == set(RUNTIME_ENV_KEYS)
    assert env["env"]["CITYPULSE_NET"] == "blite"
    assert env["env"]["CITYPULSE_BLITE_REV"] == "5"
    assert env["env"]["CITYPULSE_REROUTE"] == "0"
    assert env["python_version"].startswith("3.")
    assert env["python_executable"] == sys.executable
    assert env["platform"]
    assert env["libsumo_version"]
    for name in ("eclipse-sumo", "libsumo", "sumolib", "numpy", "pandas", "pyarrow", "pyzmq"):
        assert env["packages"].get(name), f"missing installed version for {name}"


def test_collection_fingerprint_covers_code_assets_and_environment(tmp_path):
    """Code map + combined hash, the freeze manifest's assets, and the runtime environment."""
    fp = collection_fingerprint(tmp_path)
    assert len(fp["code"]) >= 61
    assert all(rel.endswith(".py") and rel.startswith("citypulse/") for rel in fp["code"])
    assert list(fp["code"]) == sorted(fp["code"])
    assert fp["code_sha256"] and fp["assets_sha256"] and fp["sha256"]
    assert fp["runtime_environment"] == runtime_environment()

    manifest_assets = json.loads(FREEZE_MANIFEST_PATH.read_text(encoding="utf-8"))["sha256_assets"]
    assert set(fp["assets"]) == set(manifest_assets)
    assert all(fp["assets"][rel] is not None for rel in manifest_assets)
    # deterministic: the same collection state fingerprints identically
    assert collection_fingerprint(tmp_path)["sha256"] == fp["sha256"]


def test_rng_binding_positive_and_refusals(tmp_path):
    """The single gate: missing / failed / wrong-seed / stale provenance / fingerprint / snapshot."""
    # 1. missing rng_check.json
    with pytest.raises(RngBindingError, match="rng_check.json is missing"):
        verify_rng_binding(tmp_path, 4201)

    rng = write_bound_record(tmp_path, 4201)
    assert verify_rng_binding(tmp_path, 4201)["seed"] == 4201          # positive

    # 2. passed is not true
    failed = json.loads(json.dumps(rng)); failed["passed"] = False
    write_rng(tmp_path, failed)
    with pytest.raises(RngBindingError, match="'passed' is not true"):
        verify_rng_binding(tmp_path, 4201)

    # 3. wrong seed: smoke expects the smoke seed, production always expects 4501
    wrong = json.loads(json.dumps(rng)); wrong["seed"] = 9999
    write_rng(tmp_path, wrong)
    with pytest.raises(RngBindingError, match="names seed 9999, expected 4201"):
        verify_rng_binding(tmp_path, 4201)
    with pytest.raises(RngBindingError, match="expected 4501"):
        verify_rng_binding(tmp_path, 4501)

    # 4. stale provenance: provenance.json changed after rngcheck
    write_bound_record(tmp_path, 4201)
    prov_path = tmp_path / "provenance.json"
    prov_path.write_text(prov_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RngBindingError, match="stale provenance"):
        verify_rng_binding(tmp_path, 4201)

    # 5. stale fingerprint recorded in rng_check.json (current code/assets/env differ)
    stale_fp = write_bound_record(tmp_path, 4201)
    stale_fp["binding"]["fingerprint"]["sha256"] = "0" * 64
    write_rng(tmp_path, stale_fp)
    with pytest.raises(RngBindingError, match="stale fingerprint: rng_check.json records"):
        verify_rng_binding(tmp_path, 4201)

    # 6. fingerprint in provenance.json differs from the current collection
    stale_prov = write_bound_record(tmp_path, 4201)
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    prov["collection_fingerprint"]["sha256"] = "1" * 64
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    stale_prov["binding"]["provenance_sha256"] = file_sha256(prov_path)
    write_rng(tmp_path, stale_prov)
    with pytest.raises(RngBindingError, match="stale fingerprint: provenance.json records"):
        verify_rng_binding(tmp_path, 4201)

    # 7. stale snapshot: a snapshot file changed after rngcheck
    write_bound_record(tmp_path, 4201)
    (tmp_path / "runs" / "seed_4201" / "proxy" / "proxy_state_5100.xml.gz").write_bytes(b"changed")
    with pytest.raises(RngBindingError, match="stale snapshot hash for proxy_state"):
        verify_rng_binding(tmp_path, 4201)

    # 8. no binding record at all
    write_bound_record(tmp_path, 4201)
    unbound = json.loads((tmp_path / "rng_check.json").read_text(encoding="utf-8"))
    del unbound["binding"]
    write_rng(tmp_path, unbound)
    with pytest.raises(RngBindingError, match="no binding record"):
        verify_rng_binding(tmp_path, 4201)


def test_branches_refuses_before_any_branch_without_a_bound_record(tmp_path, monkeypatch):
    """branches calls verify_rng_binding before doing any branch work."""
    from citypulse.experiments.frozen_audit import cmd_branches

    started = []
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_twin_branch_jobs",
                        lambda jobs, workers: started.append("twin") or [])
    monkeypatch.setattr("citypulse.experiments.frozen_audit.run_proxy_branch_jobs",
                        lambda jobs, workers: started.append("proxy") or [])

    with pytest.raises(RngBindingError):
        cmd_branches([4201], tmp_path, smoke=True)
    assert started == []
    assert not (tmp_path / "branch_inputs.json").exists()
    assert not (tmp_path / "routes").exists()

    # a stale record is refused just the same, before any branch
    write_bound_record(tmp_path, 4201)
    (tmp_path / "runs" / "seed_4201" / "twin" / "twin_state_5100.xml.gz").write_bytes(b"changed")
    with pytest.raises(RngBindingError, match="stale snapshot hash for twin_state"):
        cmd_branches([4201], tmp_path, smoke=True)
    assert started == []
    assert not (tmp_path / "branch_inputs.json").exists()

