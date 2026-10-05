"""Frozen offline decision audit collection driver (docs/oct16-frozen-audit-plan.md)."""
from __future__ import annotations

import argparse, gzip, hashlib, json, os, subprocess, sys, time
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


def check_seeds(results_dir: Path, target_seeds: List[int], exclude_dirs: Optional[List[Path]] = None) -> Dict[str, Any]:
    used: Dict[str, List[str]] = {}
    tset, s_strs = set(target_seeds), {str(s) for s in target_seeds}
    ex_paths = [p.resolve() for p in (exclude_dirs or [])]
    if results_dir.exists():
        for p in results_dir.rglob("*"):
            resolved = p.resolve()
            if any(resolved == ex or ex in resolved.parents for ex in ex_paths):
                continue
            for s in tset:
                if str(s) in p.name:
                    used.setdefault(str(p), []).append(f"name_{s}")
            if p.is_file() and p.suffix == ".json" and p.name != "seed_check.json":
                try:
                    def scan(obj: Any) -> None:
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k.lower() in ("seed", "seeds") and (v in tset or str(v) in s_strs):
                                    used.setdefault(str(p), []).append(f"json_seed_{v}")
                                scan(v)
                        elif isinstance(obj, list):
                            for it in obj: scan(it)
                    scan(json.loads(p.read_text(encoding="utf-8")))
                except Exception: pass
            elif p.is_file() and p.suffix == ".parquet":
                try:
                    if "seed" in pq.read_schema(p).names:
                        col = pd.read_parquet(p, columns=["seed"])["seed"]
                        found = set(col.unique()) & tset
                        if found:
                            used.setdefault(str(p), []).append(f"parquet_seed_{sorted(found)}")
                except Exception: pass
    return {"passed": len(used) == 0, "clean": len(used) == 0, "seeds_checked": target_seeds, "matches": used}


def build_provenance(driver_path: Path, allow_dirty: bool = False, seeds: Optional[List[int]] = None) -> Dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    status_out = subprocess.run(["git", "status", "--porcelain", "citypulse/"], cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    driver_rel = driver_path.relative_to(REPO_ROOT).as_posix() if driver_path.is_relative_to(REPO_ROOT) else str(driver_path)
    status_driver = subprocess.run(["git", "status", "--porcelain", driver_rel], cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    dirty_text = "\n".join(filter(None, [status_out, status_driver]))
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
    return {"git_head": head, "git_status_citypulse": status_out, "git_status_driver": status_driver,
            "allow_dirty": allow_dirty, "file_hashes": hashes, "effective_command_lines": commands}


def is_infra_error(res: Dict[str, Any]) -> bool:
    if res.get("status") != "error": return False
    return any(k in (str(res.get("error", "")) + " " + str(res.get("reason", ""))).lower() for k in INFRA_KEYWORDS)


def find_seed_run_dir(seed: int, out_dir: Path) -> Path:
    for c in [out_dir / "runs" / f"seed_{seed}", REPO_ROOT / "results" / "audit" / "runs" / f"seed_{seed}"]:
        if c.exists() and (c / "twin" / f"twin_state_{int(T_D)}.xml.gz").exists(): return c
    raise FileNotFoundError(f"Snapshots for seed {seed} not found under {out_dir}/runs or results/audit/runs")


def cmd_prepare(seeds: List[int], out_dir: Path, allow_dirty: bool = False, smoke: bool = False) -> None:
    if smoke and any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")
    out_dir.mkdir(parents=True, exist_ok=True)
    res = check_seeds(REPO_ROOT / "results", seeds, exclude_dirs=[out_dir])
    (out_dir / "seed_check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    if not res["passed"]:
        if smoke:
            print(f"[smoke] Seed check reported matches as expected for smoke: {len(res['matches'])} files")
        else:
            raise SystemExit(f"Seed check FAILED: {res['matches']}")
    prov = build_provenance(Path(__file__), allow_dirty=allow_dirty, seeds=seeds)
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Prepare finished: seed_check.json and provenance.json written to {out_dir}")


def cmd_twoworld(seeds: List[int], out_dir: Path, smoke: bool = False) -> None:
    if any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: twoworld cannot be run on frozen seeds 4501-4508 in this session.")
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_twoworld_batch(seeds, runs_dir)
    print(f"Twoworld complete for seeds {seeds} in {runs_dir}")


def cmd_rngcheck(seed: int, out_dir: Path, smoke: bool = False) -> None:
    if seed in FROZEN_SEEDS:
        raise SystemExit("Error: rngcheck cannot be run on frozen seeds 4501-4508 in this session.")
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
    if not rep["passed"]:
        raise SystemExit("STOPPING: RNG check failed per preregistered protocol.")
    print(f"RNG check passed for seed {seed}")


def cmd_branches(seeds: List[int], out_dir: Path, workers: int = 8, smoke: bool = False) -> None:
    if any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: branches cannot be run on frozen seeds 4501-4508 in this session.")
    if smoke and any(s in FROZEN_SEEDS for s in seeds):
        raise SystemExit("Error: --smoke flag refused when seeds include 4501-4508.")

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
    for s in seeds:
        s_dir = find_seed_run_dir(s, out_dir)
        tw_state = str(s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz")
        tw_meta = str(s_dir / "twin" / f"twin_state_{int(T_D)}.json")
        px_state = str(s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz")

        for b in beliefs:
            h_clear = 5400.0 if b == "D300" else None
            for r in twin_reps:
                for a in twin_actions:
                    twin_jobs.append({"state": tw_state, "meta": tw_meta, "seed": s, "r": r, "action": a,
                                      "horizon": HORIZON_STEPS, "variant": b, "hyp_pos": 755.3,
                                      "hyp_clear_time": h_clear, "queue_trace": True})

        for m in proxy_reps + calib_reps:
            w_name = "calibration" if m in calib_reps else "proxy"
            act_list = calib_actions if m in calib_reps else proxy_actions
            rt_path = routes_dir / f"proxy_s{s}_m{m}.rou.xml"
            orig_ids, _ = build_proxy_resampled_routes(PROXY_ROU, rt_path, seed=s, m=m, t_d=T_D, horizon=HORIZON_STEPS)
            for a in act_list:
                proxy_jobs.append({"state": px_state, "routes": str(rt_path), "orig_future_ids": list(orig_ids),
                                   "seed": s, "m": m, "action": a, "horizon": HORIZON_STEPS, "world": w_name,
                                   "queue_trace": True})

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
    if args.subcommand == "prepare": cmd_prepare(args.seeds, args.out, allow_dirty=args.allow_dirty, smoke=args.smoke)
    elif args.subcommand == "twoworld": cmd_twoworld(args.seeds, args.out, smoke=args.smoke)
    elif args.subcommand == "rngcheck":
        target = args.seed if args.seeds is None or len(args.seeds) == 0 else args.seeds[0]
        cmd_rngcheck(target, args.out, smoke=args.smoke)
    elif args.subcommand == "branches": cmd_branches(args.seeds, args.out, workers=args.workers, smoke=args.smoke)
    elif args.subcommand == "statehistory": cmd_statehistory(args.seeds, args.out, workers=args.workers, smoke=args.smoke)


if __name__ == "__main__":
    main()
