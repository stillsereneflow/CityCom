"""Frozen offline decision audit collection driver (docs/oct16-frozen-audit-plan.md)."""
from __future__ import annotations

import argparse, gzip, hashlib, json, os, platform, subprocess, sys, time
import multiprocessing as mp
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

for k, v in [("CITYPULSE_NET", "blite"), ("CITYPULSE_BLITE_REV", "5"), ("CITYPULSE_REROUTE", "0"),
             ("PYTHONDONTWRITEBYTECODE", "1"), ("OPENBLAS_NUM_THREADS", "1")]:
    os.environ.setdefault(k, v)

import pandas as pd
import pyarrow.parquet as pq

from citypulse import sim
from citypulse.sim import proxy_cmd, twin_cmd
from citypulse.twin.demand_stream import TwinDemandStream
from citypulse.branching.audit_engine import (
    ACTIONS, HORIZON_STEPS, ROUTE_SPECS, T_D, run_twin_branch_jobs, run_proxy_branch_jobs, load_queue_edges
)
from citypulse.experiments.decision_audit import (
    REPO_ROOT, SCEN5_DIR, PROXY_ROU, TWIN_CAND_ROU, SIGMA_DEV, SIGMA_EVENT,
    TWIN_SEED, DEMAND_SEED, TWIN_BASE_FACTOR, BOUNDARY_DETECTOR,
    run_twoworld_batch, run_rng_isolation_check, build_proxy_resampled_routes,
    strip_future_departures_from_proxy_snapshot, strip_rng_state_from_xml, compute_alarm_for_twin_log
)
from citypulse.experiments.dev_runs import INFRA_KEYWORDS, file_sha256
from citypulse.experiments.mq_replay import aggregate_q_counts, parse_proxy_pending, load_upstream_edge_specs

DEFAULT_SEEDS = [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]
FROZEN_SEEDS, DEFAULT_OUT = set(DEFAULT_SEEDS), REPO_ROOT / "results" / "frozen_audit"
PRODUCTION_SEED = DEFAULT_SEEDS[0]
FREEZE_MANIFEST_PATH = REPO_ROOT / "results" / "freeze" / "freeze_manifest.json"
RUNTIME_ENV_KEYS = ("CITYPULSE_NET", "CITYPULSE_BLITE_REV", "CITYPULSE_REROUTE",
                    "OPENBLAS_NUM_THREADS", "PYTHONDONTWRITEBYTECODE")


class RngBindingError(RuntimeError):
    """The RNG isolation record is missing, failed, or no longer binds to this collection."""


def check_seeds(results_dir: Path, target_seeds: List[int], exclude_dirs: Optional[List[Path]] = None) -> Dict[str, Any]:
    used: Dict[str, List[str]] = {}
    scan_failures: Dict[str, str] = {}
    files_scanned: List[str] = []
    tset, s_strs = set(target_seeds), {str(s) for s in target_seeds}
    ex_paths = [p.resolve() for p in (exclude_dirs or [])]

    def scan_json(obj: Any, file_path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in ("seed", "seeds"):
                    if isinstance(v, (list, tuple, set)):
                        for item in v:
                            if item in tset or str(item) in s_strs:
                                used.setdefault(file_path, []).append(f"json_seed_{item}")
                    elif isinstance(v, dict):
                        for sub_k in v.keys():
                            if sub_k in tset or str(sub_k) in s_strs:
                                used.setdefault(file_path, []).append(f"json_seed_{sub_k}")
                    elif isinstance(v, (int, str)):
                        if v in tset or str(v) in s_strs:
                            used.setdefault(file_path, []).append(f"json_seed_{v}")
                scan_json(v, file_path)
        elif isinstance(obj, (list, tuple)):
            for it in obj:
                scan_json(it, file_path)

    if results_dir.exists():
        for p in sorted(results_dir.rglob("*")):
            resolved = p.resolve()
            if any(resolved == ex or ex in resolved.parents for ex in ex_paths):
                continue
            if not p.is_file():
                continue

            files_scanned.append(str(p))

            for s in tset:
                if str(s) in p.name:
                    used.setdefault(str(p), []).append(f"name_{s}")

            if p.suffix == ".json":
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    scan_json(data, str(p))
                except Exception as e:
                    scan_failures[str(p)] = f"{type(e).__name__}: {e}"

            elif p.suffix == ".parquet":
                try:
                    schema = pq.read_schema(p)
                    for sc in [c for c in schema.names if c.lower() == "seed"]:
                        col = pd.read_parquet(p, columns=[sc])[sc]
                        unique_vals = col.dropna().unique()
                        found = (set(unique_vals) & tset) | {int(x) for x in unique_vals if str(x).isdigit() and int(x) in tset}
                        if found:
                            used.setdefault(str(p), []).append(f"parquet_seed_{sorted(found)}")
                except Exception as e:
                    scan_failures[str(p)] = f"{type(e).__name__}: {e}"

    passed = (len(used) == 0) and (len(scan_failures) == 0)
    clean = (len(used) == 0)
    return {
        "passed": passed,
        "clean": clean,
        "seeds_checked": target_seeds,
        "files_scanned": files_scanned,
        "scan_failures": scan_failures,
        "matches": used,
    }


def runtime_environment() -> Dict[str, Any]:
    """The runtime that actually produced a collection, not the freeze record.

    Records the five environment variables that select the scenario/network, the interpreter and
    platform, every installed distribution version (which includes eclipse-sumo/libsumo/sumolib,
    numpy, pandas, pyarrow and pyzmq) and ``libsumo.getVersion()``.
    """
    import libsumo
    from importlib import metadata as importlib_metadata

    packages: Dict[str, str] = {}
    for dist in importlib_metadata.distributions():
        name = dist.metadata["Name"] if dist.metadata else None
        if name:
            packages[str(name)] = str(dist.version)
    return {
        "env": {key: os.environ.get(key) for key in RUNTIME_ENV_KEYS},
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": dict(sorted(packages.items())),
        "libsumo_version": list(libsumo.getVersion()),
    }


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def collection_fingerprint(out_dir: Path) -> Dict[str, Any]:
    """Fingerprint of the code, frozen assets and runtime environment of a collection.

    ``code`` is the sorted path -> sha256 map of every ``citypulse/**/*.py`` file (with its own
    combined hash), ``assets`` the current hashes of the paths listed in the freeze manifest's
    ``sha256_assets``, and ``runtime_environment()`` the actual environment. ``sha256`` is the
    combined hash over all three and is what the RNG binding records and compares. ``out_dir`` is
    recorded for provenance but is deliberately not part of any hash.
    """
    out_resolved = Path(out_dir).resolve()
    code_hashes = {p.relative_to(REPO_ROOT).as_posix(): file_sha256(p)
                   for p in sorted((REPO_ROOT / "citypulse").rglob("*.py"))
                   if out_resolved not in p.resolve().parents}
    manifest = (json.loads(FREEZE_MANIFEST_PATH.read_text(encoding="utf-8"))
                if FREEZE_MANIFEST_PATH.exists() else {})
    asset_hashes = {}
    for rel in sorted(manifest.get("sha256_assets", {})):
        asset_path = REPO_ROOT / rel
        asset_hashes[rel] = file_sha256(asset_path) if asset_path.exists() else None
    env = runtime_environment()
    payload = {"code": code_hashes, "assets": asset_hashes, "runtime_environment": env}
    return {
        "out_dir": str(out_dir),
        "code": code_hashes,
        "code_sha256": _sha256_json(code_hashes),
        "assets": asset_hashes,
        "assets_sha256": _sha256_json(asset_hashes),
        "runtime_environment": env,
        "sha256": _sha256_json(payload),
    }


def build_provenance(driver_path: Path, allow_dirty: bool = False, seeds: Optional[List[int]] = None) -> Dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    status_out = subprocess.run(["git", "status", "--porcelain", "citypulse/"], cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    driver_rel = driver_path.relative_to(REPO_ROOT).as_posix() if driver_path.is_relative_to(REPO_ROOT) else str(driver_path)
    status_driver = subprocess.run(["git", "status", "--porcelain", driver_rel], cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    dirty_text = "\n".join(filter(None, [status_out, status_driver]))
    clean_status = (len(dirty_text) == 0)
    if dirty_text and not allow_dirty:
        raise RuntimeError(f"Uncommitted changes in citypulse/ or driver:\n{dirty_text}\nUse --allow-dirty for smoke test.")

    tls_files = [Path(p.strip()) for p in str(sim.get_tls_file()).split(",") if p.strip()]
    files_to_hash = [
        REPO_ROOT / "citypulse/branching/audit_engine.py", REPO_ROOT / "citypulse/experiments/decision_audit.py",
        REPO_ROOT / "citypulse/twin/service.py", REPO_ROOT / "citypulse/twin/demand_stream.py",
        REPO_ROOT / "citypulse/proxy/service.py", driver_path.resolve(), SIGMA_DEV.resolve(), SIGMA_EVENT.resolve(),
        Path(sim.get_net_file()).resolve(), Path(sim.get_det_file()).resolve(), Path(sim.get_detector_map()).resolve(),
        PROXY_ROU.resolve(), TWIN_CAND_ROU.resolve(), Path(sim.get_vtypes_file("proxy")).resolve(),
        Path(sim.get_vtypes_file("twin")).resolve(), *[p.resolve() for p in tls_files],
    ]
    hashes = {(p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else str(p)): file_sha256(p)
              for p in files_to_hash if p.exists()}
    commands = {
        f"seed_{s}": {
            "twin": [sys.executable, "-m", "citypulse.twin.service", "--seed", str(TWIN_SEED), "--demand-seed", str(DEMAND_SEED),
                     "--demand-path", str(TWIN_CAND_ROU), "--assim", "normal300", "--boundary-detector", BOUNDARY_DETECTOR,
                     "--sigma-json", str(SIGMA_DEV), "--twin-base-factor", str(TWIN_BASE_FACTOR), "--snapshot-times", str(int(T_D))],
            "proxy": [sys.executable, "-m", "citypulse.proxy.service", "--seed", str(s), "--sensor-seed", "77", "--t-end", "7200",
                      "--routes", str(PROXY_ROU), "--proxy-snapshot-times", str(int(T_D))],
        } for s in (seeds or DEFAULT_SEEDS)
    }
    return {"git_head": head, "clean": clean_status, "git_clean": clean_status,
            "git_status_citypulse": status_out, "git_status_driver": status_driver,
            "allow_dirty": allow_dirty, "file_hashes": hashes, "effective_command_lines": commands}


def is_infra_error(res: Dict[str, Any]) -> bool:
    if res.get("status") != "error": return False
    return any(k in (str(res.get("error", "")) + " " + str(res.get("reason", ""))).lower() for k in INFRA_KEYWORDS)


def find_seed_run_dir(seed: int, out_dir: Path) -> Path:
    for c in [out_dir / "runs" / f"seed_{seed}", REPO_ROOT / "results" / "audit" / "runs" / f"seed_{seed}"]:
        if c.exists() and (c / "twin" / f"twin_state_{int(T_D)}.xml.gz").exists(): return c
    raise FileNotFoundError(f"Snapshots for seed {seed} not found under {out_dir}/runs or results/audit/runs")


def _has_run_data(out_dir: Path) -> bool:
    if not out_dir.exists():
        return False
    if (out_dir / "runs").exists() or (out_dir / "routes").exists():
        return True
    run_file_names = {
        "raw.parquet", "queue_trace.parquet", "state_history.parquet",
        "branch_inputs.json", "reruns.json", "two_world_info.json",
    }
    for name in run_file_names:
        if (out_dir / name).exists():
            return True
    return False


def cmd_prepare(seeds: List[int], out_dir: Path, allow_dirty: bool = False, smoke: bool = False) -> None:
    if smoke and any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")
    if out_dir.exists() and _has_run_data(out_dir):
        raise SystemExit(f"Refusing prepare: output directory {out_dir} already exists and contains run data.")
    res = check_seeds(REPO_ROOT / "results", seeds)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "seed_check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    if not res["passed"]:
        if smoke and len(res["scan_failures"]) == 0:
            print(f"[smoke] Seed check reported matches as expected for smoke: {len(res['matches'])} files")
        else:
            raise SystemExit(f"Seed check FAILED: matches={res['matches']}, scan_failures={res['scan_failures']}")
    prov = build_provenance(Path(__file__), allow_dirty=allow_dirty, seeds=seeds)
    prov["runtime_environment"] = runtime_environment()
    prov["collection_fingerprint"] = collection_fingerprint(out_dir)
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Prepare finished: seed_check.json and provenance.json (runtime environment + collection "
          f"fingerprint {prov['collection_fingerprint']['sha256']}) written to {out_dir}")


def cmd_twoworld(seeds: List[int], out_dir: Path, smoke: bool = False) -> None:
    if smoke and any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    base_port = 5600
    for i, s in enumerate(seeds):
        s_dir = runs_dir / f"seed_{s}"
        twin_dir = s_dir / "twin"
        proxy_dir = s_dir / "proxy"
        s_dir.mkdir(parents=True, exist_ok=True)
        port = base_port + i * 2
        ep = f"tcp://127.0.0.1:{port}"
        targs = [
            sys.executable, "-m", "citypulse.twin.service",
            "--endpoint", ep, "--out", str(twin_dir),
            "--seed", str(TWIN_SEED), "--demand-seed", str(DEMAND_SEED),
            "--demand-path", str(TWIN_CAND_ROU), "--assim", "normal300",
            "--boundary-detector", BOUNDARY_DETECTOR,
            "--sigma-json", str(SIGMA_DEV),
            "--twin-base-factor", str(TWIN_BASE_FACTOR),
            "--snapshot-times", str(int(T_D)),
        ]
        pargs = [
            sys.executable, "-m", "citypulse.proxy.service",
            "--endpoint", ep, "--out", str(proxy_dir),
            "--seed", str(s), "--sensor-seed", "77", "--t-end", "7200",
            "--routes", str(PROXY_ROU),
            "--proxy-snapshot-times", str(int(T_D)),
        ]
        cmd_file = s_dir / "commands.json"
        cmd_file.write_text(json.dumps({"twin": targs, "proxy": pargs}, indent=2), encoding="utf-8")

    run_twoworld_batch(seeds, runs_dir)
    print(f"Twoworld complete for seeds {seeds} in {runs_dir}")


def cmd_rngcheck(seed: int, out_dir: Path, smoke: bool = False) -> None:
    if smoke and seed in FROZEN_SEEDS:
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")
    prov_path = out_dir / "provenance.json"
    if not prov_path.exists():
        raise SystemExit(f"Refusing rngcheck: {prov_path} does not exist; run prepare first.")
    s_dir = find_seed_run_dir(seed, out_dir)
    info_file = s_dir / "two_world_info.json"
    if info_file.exists():
        info = json.loads(info_file.read_text(encoding="utf-8"))
    else:
        info = {"seed": seed, "twin_state": str(s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz"),
                "twin_meta": str(s_dir / "twin" / f"twin_state_{int(T_D)}.json"),
                "proxy_state": str(s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz")}
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = run_rng_isolation_check(info, out_dir / "rng_check.json", scratch_dir=out_dir / "scratch_rng")
    snap_hashes = {
        "twin_state": file_sha256(Path(info["twin_state"])),
        "twin_meta": file_sha256(Path(info["twin_meta"])),
        "proxy_state": file_sha256(Path(info["proxy_state"])),
    }
    rep["binding"] = {
        "provenance_sha256": file_sha256(prov_path),
        "fingerprint": collection_fingerprint(out_dir),
        "snapshot_hashes": snap_hashes,
    }
    (out_dir / "rng_check.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    if not rep["passed"]:
        raise SystemExit("STOPPING: RNG check failed per preregistered protocol.")
    print(f"RNG check passed for seed {seed}; bound to provenance {rep['binding']['provenance_sha256']} "
          f"and fingerprint {rep['binding']['fingerprint']['sha256']}")


def verify_rng_binding(out_dir: Path, seed: int) -> Dict[str, Any]:
    """The single RNG gate used by branches and by the production analyzer.

    Refuses (``RngBindingError`` with the precise reason) when ``rng_check.json`` is missing,
    unreadable, not passed, names the wrong seed, or is stale: its bound provenance hash, its
    recorded code/assets/environment fingerprint, the fingerprint in ``provenance.json``, or its
    snapshot hashes no longer match the current collection. The expected seed is 4501 for the
    production seeds and the smoke seed itself under ``--smoke``.
    """
    expected = PRODUCTION_SEED if int(seed) in FROZEN_SEEDS else int(seed)
    rng_path = out_dir / "rng_check.json"
    if not rng_path.exists():
        raise RngBindingError(f"rng_check.json is missing: {rng_path}")
    try:
        rng_data = json.loads(rng_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RngBindingError(f"rng_check.json is unreadable: {rng_path}: {type(e).__name__}: {e}")

    if rng_data.get("passed") is not True:
        raise RngBindingError(f"rng_check.json 'passed' is not true (passed={rng_data.get('passed')!r})")
    if rng_data.get("seed") != expected:
        raise RngBindingError(f"rng_check.json names seed {rng_data.get('seed')!r}, expected {expected}")

    binding = rng_data.get("binding")
    if not isinstance(binding, dict):
        raise RngBindingError("rng_check.json has no binding record "
                              "(provenance_sha256 / fingerprint / snapshot_hashes)")

    prov_path = out_dir / "provenance.json"
    if not prov_path.exists():
        raise RngBindingError(f"provenance.json is missing: {prov_path}")
    prov_sha = file_sha256(prov_path)
    if binding.get("provenance_sha256") != prov_sha:
        raise RngBindingError(f"stale provenance: rng_check.json binds provenance.json "
                              f"{binding.get('provenance_sha256')!r}, current file is {prov_sha}")

    recorded_fp = binding.get("fingerprint")
    if not isinstance(recorded_fp, dict):
        raise RngBindingError("rng_check.json binding has no fingerprint record")
    current_fp = collection_fingerprint(out_dir)
    if recorded_fp.get("sha256") != current_fp["sha256"]:
        raise RngBindingError(f"stale fingerprint: rng_check.json records {recorded_fp.get('sha256')!r}, "
                              f"current collection fingerprint is {current_fp['sha256']}")
    try:
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RngBindingError(f"provenance.json is unreadable: {prov_path}: {type(e).__name__}: {e}")
    prov_fp = prov.get("collection_fingerprint")
    if not isinstance(prov_fp, dict) or prov_fp.get("sha256") != current_fp["sha256"]:
        raise RngBindingError(f"stale fingerprint: provenance.json records "
                              f"{(prov_fp or {}).get('sha256')!r}, current collection fingerprint is "
                              f"{current_fp['sha256']}")

    snap_hashes = binding.get("snapshot_hashes")
    if not isinstance(snap_hashes, dict):
        raise RngBindingError("rng_check.json binding has no snapshot_hashes")
    try:
        s_dir = find_seed_run_dir(expected, out_dir)
    except FileNotFoundError as e:
        raise RngBindingError(f"snapshot files for seed {expected} are missing: {e}")

    expected_hashes = {
        "twin_state": file_sha256(s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz"),
        "twin_meta": file_sha256(s_dir / "twin" / f"twin_state_{int(T_D)}.json"),
        "proxy_state": file_sha256(s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz"),
    }
    for key, exp_hash in expected_hashes.items():
        if snap_hashes.get(key) != exp_hash:
            raise RngBindingError(f"stale snapshot hash for {key}: recorded {snap_hashes.get(key)!r} "
                                  f"!= current {exp_hash}")
    return rng_data


def cmd_branches(seeds: List[int], out_dir: Path, workers: int = 8, smoke: bool = False) -> None:
    if smoke and any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")

    py_files = sorted((REPO_ROOT / "citypulse").rglob("*.py"))
    code_hashes_before = {p.relative_to(REPO_ROOT).as_posix(): file_sha256(p) for p in py_files}

    # The gate runs before any branch: a missing, failed, wrong-seed or stale RNG record stops here.
    verify_rng_binding(out_dir, int(seeds[0]) if (smoke and seeds) else PRODUCTION_SEED)

    out_dir.mkdir(parents=True, exist_ok=True)
    routes_dir = out_dir / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    beliefs = ["B", "D300"]
    if smoke:
        twin_reps, twin_actions = [1], ["A0", "A3"]
        proxy_reps, proxy_actions = [1], ["A0", "A3"]
        calib_reps, calib_actions = [], []
    else:
        twin_reps, twin_actions = list(range(1, 7)), list(ACTIONS)
        proxy_reps, proxy_actions = list(range(1, 7)), list(ACTIONS)
        calib_reps, calib_actions = list(range(7, 13)), list(ACTIONS)

    twin_jobs, proxy_jobs = [], []
    branch_inputs = []

    for s in seeds:
        s_dir = find_seed_run_dir(s, out_dir)
        tw_state = str(s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz")
        tw_meta = str(s_dir / "twin" / f"twin_state_{int(T_D)}.json")
        px_state = str(s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz")
        tw_state_hash = file_sha256(Path(tw_state))
        tw_meta_hash = file_sha256(Path(tw_meta))
        px_state_hash = file_sha256(Path(px_state))

        for b in beliefs:
            h_clear = 5400.0 if b == "D300" else None
            for r in twin_reps:
                for a in twin_actions:
                    job = {"state": tw_state, "meta": tw_meta, "seed": s, "r": r, "action": a,
                           "horizon": HORIZON_STEPS, "variant": b, "hyp_pos": 755.3,
                           "hyp_clear_time": h_clear, "queue_trace": True}
                    twin_jobs.append(job)
                    branch_inputs.append({
                        "world": "twin",
                        "seed": s,
                        "state_path": tw_state,
                        "state_sha256": tw_state_hash,
                        "meta_sha256": tw_meta_hash,
                        "route_file": None,
                        "route_sha256": None,
                        "r/m": r,
                        "r": r,
                        "m": None,
                        "action": a,
                        "belief": b,
                        "hyp_clear_time": h_clear,
                    })

        for m in proxy_reps + calib_reps:
            w_name = "calibration" if m in calib_reps else "proxy"
            act_list = calib_actions if m in calib_reps else proxy_actions
            rt_path = routes_dir / f"proxy_s{s}_m{m}.rou.xml"
            orig_ids, _ = build_proxy_resampled_routes(PROXY_ROU, rt_path, seed=s, m=m, t_d=T_D, horizon=HORIZON_STEPS)
            rt_hash = file_sha256(rt_path)
            for a in act_list:
                job = {"state": px_state, "routes": str(rt_path), "orig_future_ids": list(orig_ids),
                       "seed": s, "m": m, "action": a, "horizon": HORIZON_STEPS, "world": w_name,
                       "queue_trace": True}
                proxy_jobs.append(job)
                branch_inputs.append({
                    "world": w_name,
                    "seed": s,
                    "state_path": px_state,
                    "state_sha256": px_state_hash,
                    "meta_sha256": None,
                    "route_file": str(rt_path),
                    "route_sha256": rt_hash,
                    "r/m": m,
                    "r": None,
                    "m": m,
                    "action": a,
                    "belief": None,
                    "hyp_clear_time": None,
                })

    (out_dir / "branch_inputs.json").write_text(json.dumps(branch_inputs, indent=2), encoding="utf-8")

    n_workers = max(1, min(int(workers), 8))
    twin_results = run_twin_branch_jobs(twin_jobs, workers=n_workers)
    proxy_results = run_proxy_branch_jobs(proxy_jobs, workers=n_workers)

    reruns, final_results = [], []
    for job, res in zip(twin_jobs, twin_results):
        if is_infra_error(res):
            rerun_res = run_twin_branch_jobs([job], workers=1)[0]
            reruns.append({"job": job, "first_attempt": res, "rerun": rerun_res})
            final_results.append(rerun_res)
        else:
            final_results.append(res)
    for job, res in zip(proxy_jobs, proxy_results):
        if is_infra_error(res):
            rerun_res = run_proxy_branch_jobs([job], workers=1)[0]
            reruns.append({"job": job, "first_attempt": res, "rerun": rerun_res})
            final_results.append(rerun_res)
        else:
            final_results.append(res)

    (out_dir / "reruns.json").write_text(json.dumps(reruns, indent=2, default=str), encoding="utf-8")

    raw_records, trace_records = [], []
    for r in final_results:
        rec = dict(r)
        trace = rec.pop("queue_trace", None)
        belief = rec.get("variant") if rec.get("world") == "twin" else None
        digest = rec.get("veh_digest") or rec.get("digest")
        rec["belief"], rec["digest"], rec["veh_digest"] = belief, digest, digest
        for k in ("blocker_release_0", "blocker_release_1"):
            if isinstance(rec.get(k), (dict, list)): rec[k] = json.dumps(rec[k])
        raw_records.append(rec)
        if trace:
            for snap in trace:
                s_row = {"world": rec.get("world"), "belief": belief, "seed": rec.get("seed"),
                         "replication": rec.get("replication"), "action": rec.get("action"), **snap}
                for k, v in s_row.items():
                    if isinstance(v, (dict, list)): s_row[k] = json.dumps(v)
                trace_records.append(s_row)

    pd.DataFrame(raw_records).to_parquet(out_dir / "raw.parquet", index=False)
    pd.DataFrame(trace_records).to_parquet(out_dir / "queue_trace.parquet", index=False)

    code_hashes_after = {p.relative_to(REPO_ROOT).as_posix(): file_sha256(p) for p in py_files}
    (out_dir / "code_hashes_before_after.json").write_text(
        json.dumps({
            "before": code_hashes_before,
            "after": code_hashes_after,
            "match": code_hashes_before == code_hashes_after,
        }, indent=2),
        encoding="utf-8"
    )

    print(f"Branches complete: raw.parquet ({len(raw_records)} rows), queue_trace.parquet ({len(trace_records)} rows)")


def _read_snapshot_worker(job: Dict[str, Any]) -> Dict[str, Any]:
    import libsumo as tc
    try:
        tc.start(job["cmd"])
        vehs = [(v, tc.vehicle.getRoadID(v), float(tc.vehicle.getSpeed(v))) for v in tc.vehicle.getIDList()]
        tc.close()
        return {"status": "ok", "vehicles": vehs}
    except Exception as e:
        try: tc.close()
        except Exception: pass
        return {"status": "error", "error": str(e), "reason": type(e).__name__}


def cmd_statehistory(seeds: List[int], out_dir: Path, workers: int = 4, smoke: bool = False) -> pd.DataFrame:
    q_edges, upstream_edges, extra_edges = load_upstream_edge_specs()
    stream = TwinDemandStream(seed=DEMAND_SEED, path=TWIN_CAND_ROU, base_factor=TWIN_BASE_FACTOR)
    cand_routes = {vid: edges for _, vid, edges in stream.cands}

    jobs, meta_info = [], []
    for s in seeds:
        s_dir = find_seed_run_dir(s, out_dir)
        p_state = s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz"
        jobs.append({"cmd": proxy_cmd(s, routes=str(PROXY_ROU), extra=["--load-state", str(p_state.resolve())])})
        meta_info.append({"seed": s, "world": "proxy", "p_state": p_state})

        t_state = s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz"
        t_meta = s_dir / "twin" / f"twin_state_{int(T_D)}.json"
        jobs.append({"cmd": twin_cmd(TWIN_SEED, ["--load-state", str(t_state.resolve())])})
        meta_info.append({"seed": s, "world": "twin", "t_meta": t_meta})

    ctx = mp.get_context("spawn")
    with ctx.Pool(min(workers, len(jobs))) as pool:
        read_res = pool.map(_read_snapshot_worker, jobs)

    rows = []
    for info, res in zip(meta_info, read_res):
        if res["status"] != "ok": raise RuntimeError(f"Failed to read snapshot: {res}")
        vehs = res["vehicles"]
        s, world = info["seed"], info["world"]
        incident_hist = "incident active since 4,500 s" if world == "proxy" else "none"

        pend_vids, pend_routes = None, None
        if world == "proxy":
            try: pend_vids, pend_routes = parse_proxy_pending(info["p_state"])
            except Exception: pass
        else:
            meta = json.loads(info["t_meta"].read_text(encoding="utf-8"))
            if "pending" in meta and meta["pending"] is not None:
                pend_vids = meta["pending"]
                pend_routes = meta.get("pending_routes") or {v: cand_routes.get(v, []) for v in pend_vids}

        counts = {e: 0 for e in q_edges + upstream_edges + extra_edges}
        for vid, road, sp in vehs:
            if not vid.startswith(("hyp_", "incident_")) and sp < 0.1 and road in counts:
                counts[road] += 1

        if pend_vids is not None and pend_routes is not None:
            q_set = set(q_edges)
            pending_q = sum(1 for v in pend_vids if any(e in q_set for e in pend_routes.get(v, [])))
            Q = sum(counts[e] for e in q_edges) + pending_q
        else:
            pending_q, Q = None, None

        rows.append({"seed": s, "world": world, "incident_history": incident_hist, **counts,
                     "pending_q": pending_q, "Q": Q, "ktb_n1_all_veh": sum(1 for v, r, _ in vehs if r == "ktb_n1")})

    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "state_history.parquet", index=False)
    print(f"State history complete: {len(df)} rows written to {out_dir / 'state_history.parquet'}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="Frozen offline decision audit collection driver")
    sub = ap.add_subparsers(dest="subcommand", required=True)

    for name in ["prepare", "twoworld", "branches", "statehistory"]:
        p = sub.add_parser(name)
        p.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
        p.add_argument("--out", type=Path, default=DEFAULT_OUT)
        p.add_argument("--smoke", action="store_true")
        if name == "prepare": p.add_argument("--allow-dirty", action="store_true")
        if name in ("branches", "statehistory"): p.add_argument("--workers", type=int, default=8 if name == "branches" else 4)

    p_rng = sub.add_parser("rngcheck")
    p_rng.add_argument("--seed", type=int, default=4501)
    p_rng.add_argument("--seeds", type=int, nargs="*", default=None)
    p_rng.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p_rng.add_argument("--smoke", action="store_true")

    args = ap.parse_args()
    try:
        if args.subcommand == "prepare": cmd_prepare(args.seeds, args.out, allow_dirty=args.allow_dirty, smoke=args.smoke)
        elif args.subcommand == "twoworld": cmd_twoworld(args.seeds, args.out, smoke=args.smoke)
        elif args.subcommand == "rngcheck":
            target = args.seed if args.seeds is None or len(args.seeds) == 0 else args.seeds[0]
            cmd_rngcheck(target, args.out, smoke=args.smoke)
        elif args.subcommand == "branches": cmd_branches(args.seeds, args.out, workers=args.workers, smoke=args.smoke)
        elif args.subcommand == "statehistory": cmd_statehistory(args.seeds, args.out, workers=args.workers, smoke=args.smoke)
    except RngBindingError as e:
        raise SystemExit(f"STOPPING: RNG binding refused: {e}")


if __name__ == "__main__":
    main()
