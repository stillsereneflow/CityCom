"""Development runs collection driver and verification.

Preregistered specification: docs/oct13-dev-runs-plan.md (rev 2).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, os, subprocess, sys, threading, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("CITYPULSE_NET", "blite")
os.environ.setdefault("CITYPULSE_BLITE_REV", "5")
os.environ.setdefault("CITYPULSE_REROUTE", "0")

import pandas as pd
from citypulse import sim
from citypulse.experiments.event_pilot import (
    REPO_ROOT, IMPL_DIR, SIGMA_DEV_PATH, PROXY_ROU, SHOCK_ROU, TWIN_CAND_ROU,
    BOUNDARY_DETECTOR, SNAPSHOT_MARKS, T_END, TWIN_SEED, DEMAND_SEED,
    TWIN_BASE_FACTOR, get_env, evaluate_queue_forecasts
)

DEV_SEEDS = [4401, 4402, 4403, 4404, 4405, 4406]
SCENARIOS, ARMS = ["INC", "NOI", "SHK", "DET"], ["evt", "conv"]
DEV_RUNS_DIR, PORT_BASE = REPO_ROOT / "results" / "dev_runs", 6400
INFRA_EXIT_CODES = {-1073741502, 3221225794, -1073741819, 3221225477, -1073741515}
INFRA_KEYWORDS = [
    "address already in use", "10048", "errno 98", "zmqerror: address already in use",
    "0xc0000142", "status_dll_init_failed", "winerror", "windowserror",
    "createprocess failed", "no space left on device", "disk full"
]


def get_slot_specs() -> List[Dict[str, Any]]:
    specs, idx = [], 1
    for s in DEV_SEEDS:
        for sc in SCENARIOS:
            for a in ARMS:
                specs.append({"name": f"{a}_{sc.lower()}_{s}", "scenario": sc, "seed": s, "arm": a, "port": PORT_BASE + idx})
                idx += 1
    return specs


def build_manifest() -> Dict[str, Any]:
    loops = sorted(sim.detector_loops().keys())
    exp_dets = [d for k, d in enumerate(loops) if k % 3 != 2]
    ts = [int(t) for t in range(30, int(T_END) + 1, 30)]
    return {
        "expected_detector_ids": exp_dets, "timestamps": ts,
        "expected_observation_keys_count": len(exp_dets) * len(ts),
        "required_snapshots": [int(t) for t in SNAPSHOT_MARKS],
        "snapshot_files": ["twin/twin_state_{t}.json", "twin/twin_state_{t}.xml.gz"],
        "forecast_cells": {"5min": [int(t) for t in SNAPSHOT_MARKS], "15min": [int(t) for t in SNAPSHOT_MARKS if t + 900 <= T_END]},
        "required_logs": {
            "common": ["run_info.json", "queue_forecasts.json", "proxy_stdout.log", "proxy_stderr.log",
                       "twin_stdout.log", "twin_stderr.log", "twin/twin_log.parquet", "twin/assim_log.parquet"],
            "evt_only": ["twin/state_trace.jsonl", "twin/event_log.jsonl", "twin/replacement_log.jsonl"],
        },
    }


def check_seeds(results_dir: Path, target_seeds: List[int] = DEV_SEEDS) -> Dict[str, Any]:
    used, tset = {}, set(target_seeds)
    if results_dir.exists():
        for p in results_dir.rglob("*"):
            if "dev_runs" in p.parts: continue
            for s in tset:
                if str(s) in p.name: used.setdefault(str(p), []).append(f"name_{s}")
            if p.is_file() and p.suffix == ".json":
                try:
                    def scan(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k.lower() == "seed" and v in tset: used.setdefault(str(p), []).append(f"json_seed_{v}")
                                scan(v)
                        elif isinstance(obj, list):
                            for item in obj: scan(item)
                    scan(json.loads(p.read_text(encoding="utf-8")))
                except Exception: pass
            elif p.is_file() and p.suffix == ".parquet":
                try:
                    import pyarrow.parquet as pq
                    if "seed" in pq.read_schema(p).names:
                        if any(pd.read_parquet(p, columns=["seed"])["seed"].isin(tset)):
                            used.setdefault(str(p), []).append("parquet_seed")
                except Exception: pass
    return {"passed": len(used) == 0, "seeds_checked": target_seeds, "matches": used}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_commands(scenario: str, seed: int, arm: str, port: int, attempt_dir: Path) -> Tuple[List[str], List[str]]:
    ep, snap_strs = f"tcp://127.0.0.1:{port}", [str(int(t)) for t in SNAPSHOT_MARKS]
    targs = [
        sys.executable, "-m", "citypulse.twin.service", "--endpoint", ep, "--out", str(attempt_dir / "twin"),
        "--seed", str(TWIN_SEED), "--demand-seed", str(DEMAND_SEED), "--snapshot-times", *snap_strs,
        "--demand-path", str(TWIN_CAND_ROU), "--assim", "normal300", "--boundary-detector", BOUNDARY_DETECTOR,
        "--sigma-json", str(SIGMA_DEV_PATH), "--twin-base-factor", str(TWIN_BASE_FACTOR),
    ]
    if arm.lower() == "evt":
        targs.extend(["--event", "on", "--event-sigma", str(IMPL_DIR / "sigma_event.json"), "--event-workers", "4", "--event-grid", "pilot2"])
    pargs = [
        sys.executable, "-m", "citypulse.proxy.service", "--endpoint", ep, "--out", str(attempt_dir / "proxy"),
        "--seed", str(seed), "--sensor-seed", "77", "--t-end", str(T_END),
        "--routes", str(SHOCK_ROU if scenario == "SHK" else PROXY_ROU),
    ]
    if scenario != "INC": pargs.append("--no-incident")
    if scenario == "DET": pargs.extend(["--sensor-fault", "AID02109:stuck:4500:5400"])
    return targs, pargs


def build_provenance(allow_dirty: bool = False) -> Dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    status_out = subprocess.run(["git", "status", "--porcelain", "citypulse/"], cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    if status_out and not allow_dirty:
        raise RuntimeError(f"Uncommitted changes in citypulse/:\n{status_out}\nUse --allow-dirty for smoke test.")
    tls_files = [Path(p.strip()) for p in str(sim.get_tls_file()).split(",") if p.strip()]
    files_to_hash = [
        REPO_ROOT / "citypulse/twin/event.py", REPO_ROOT / "citypulse/twin/service.py",
        REPO_ROOT / "citypulse/branching/engine.py", REPO_ROOT / "citypulse/twin/demand_stream.py",
        REPO_ROOT / "citypulse/experiments/event_pilot.py", REPO_ROOT / "citypulse/experiments/dev_runs.py",
        SIGMA_DEV_PATH, IMPL_DIR / "sigma_event.json", Path(sim.get_net_file()), Path(sim.get_det_file()),
        Path(sim.get_detector_map()), PROXY_ROU, SHOCK_ROU, TWIN_CAND_ROU, Path(sim.get_vtypes_file("proxy")),
        Path(sim.get_vtypes_file("twin")), *tls_files, REPO_ROOT / "citypulse/scenario_blite.py",
    ]
    hashes = {(p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else str(p)): file_sha256(p)
              for p in (Path(f).resolve() for f in files_to_hash)}
    commands = {s["name"]: {"twin": build_commands(s["scenario"], s["seed"], s["arm"], s["port"], Path("D:/dummy"))[0],
                            "proxy": build_commands(s["scenario"], s["seed"], s["arm"], s["port"], Path("D:/dummy"))[1]}
                for s in get_slot_specs()}
    return {"git_head": head, "git_status_citypulse": status_out, "allow_dirty": allow_dirty, "file_hashes": hashes, "commands": commands}


def is_infrastructure_failure(rc_p: int, rc_t: int, proxy_err: str, twin_err: str) -> Tuple[bool, str]:
    if rc_p in INFRA_EXIT_CODES: return True, f"proxy exit code {hex(rc_p & 0xFFFFFFFF)}"
    if rc_t in INFRA_EXIT_CODES: return True, f"twin exit code {hex(rc_t & 0xFFFFFFFF)}"
    err_text = (proxy_err + "\n" + twin_err).lower()
    for kw in INFRA_KEYWORDS:
        if kw in err_text: return True, f"signature keyword: {kw}"
    return False, "non-infrastructure failure"


def run_attempt(spec: Dict[str, Any], attempt_dir: Path, attempt_num: int = 1) -> Dict[str, Any]:
    (attempt_dir / "twin").mkdir(parents=True, exist_ok=True)
    (attempt_dir / "proxy").mkdir(parents=True, exist_ok=True)
    targs, pargs = build_commands(spec["scenario"], spec["seed"], spec["arm"], spec["port"], attempt_dir)
    p_out, p_err = open(attempt_dir / "proxy_stdout.log", "w", encoding="utf-8"), open(attempt_dir / "proxy_stderr.log", "w", encoding="utf-8")
    t_out, t_err = open(attempt_dir / "twin_stdout.log", "w", encoding="utf-8"), open(attempt_dir / "twin_stderr.log", "w", encoding="utf-8")
    t0 = time.time()
    twin_proc = subprocess.Popen(targs, stdout=t_out, stderr=t_err, env=get_env(), cwd=str(REPO_ROOT))
    time.sleep(2)
    proxy_proc = subprocess.Popen(pargs, stdout=p_out, stderr=p_err, env=get_env(), cwd=str(REPO_ROOT))
    rc_p, rc_t = proxy_proc.wait(), twin_proc.wait()
    wall = round(time.time() - t0, 1)
    for fh in (p_out, p_err, t_out, t_err): fh.close()
    info = {
        "run_name": spec["name"], "scenario": spec["scenario"], "seed": spec["seed"], "arm": spec["arm"],
        "attempt": attempt_num, "proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": wall, "t_end": T_END,
        "twin_seed": TWIN_SEED, "demand_seed": DEMAND_SEED, "twin_base_factor": TWIN_BASE_FACTOR,
        "boundary_detector": BOUNDARY_DETECTOR, "routes": str(SHOCK_ROU if spec["scenario"] == "SHK" else PROXY_ROU),
        "sensor_fault": "AID02109:stuck:4500:5400" if spec["scenario"] == "DET" else None,
        "incident": (spec["scenario"] == "INC"), "event_grid": "pilot2" if spec["arm"] == "evt" else None,
        "event_force_hstar": None, "event_sigma": str(IMPL_DIR / "sigma_event.json") if spec["arm"] == "evt" else None,
        "proxy_cmd": pargs, "twin_cmd": targs,
    }
    (attempt_dir / "run_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    if rc_p == 0 and rc_t == 0:
        try: evaluate_queue_forecasts(attempt_dir)
        except Exception as e: (attempt_dir / "forecast_err.log").write_text(str(e), encoding="utf-8")
    return info


def check_attempt_completeness(attempt_dir: Path, arm: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    reasons, checks = [], {}
    info_path = attempt_dir / "run_info.json"
    if not info_path.exists():
        return {"complete": False, "flagged": False, "reasons": ["Missing run_info.json"], "checks": {}}
    try: info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as e: return {"complete": False, "flagged": False, "reasons": [f"Corrupt run_info.json: {e}"], "checks": {}}
    rc_p, rc_t = info.get("proxy_rc"), info.get("twin_rc")
    if rc_p != 0 or rc_t != 0: reasons.append(f"Non-zero exit code: proxy_rc={rc_p}, twin_rc={rc_t}")
    checks["exit_codes"] = (rc_p == 0 and rc_t == 0)

    req_logs = list(manifest["required_logs"]["common"]) + (manifest["required_logs"]["evt_only"] if arm.lower() == "evt" else [])
    missing_logs = [l for l in req_logs if not (attempt_dir / l).exists()]
    if missing_logs: reasons.append(f"Missing required logs: {missing_logs}")
    checks["required_logs"] = (len(missing_logs) == 0)

    missing_snaps = [f.name for t in manifest["required_snapshots"] for f in [attempt_dir / tmpl.format(t=t) for tmpl in manifest["snapshot_files"]] if not f.exists()]
    if missing_snaps: reasons.append(f"Missing snapshots: {missing_snaps}")
    checks["snapshots"] = (len(missing_snaps) == 0)

    qf_path, fc_ok = attempt_dir / "queue_forecasts.json", True
    if not qf_path.exists(): fc_ok = False; reasons.append("Missing queue_forecasts.json")
    else:
        try:
            fcs = json.loads(qf_path.read_text(encoding="utf-8")).get("forecasts", {})
            for h, marks in [("5min", manifest["forecast_cells"]["5min"]), ("15min", manifest["forecast_cells"]["15min"])]:
                for t in marks:
                    cell = fcs.get(str(t), {}).get(h, {})
                    if cell.get("pred") is None or cell.get("truth") is None:
                        fc_ok = False; reasons.append(f"Missing {h} forecast/truth at t={t}")
        except Exception as e: fc_ok = False; reasons.append(f"Error parsing queue_forecasts.json: {e}")
    checks["forecast_cells"] = fc_ok

    tl_path, det_ok = attempt_dir / "twin" / "twin_log.parquet", True
    if not tl_path.exists(): det_ok = False; reasons.append("Missing twin_log.parquet")
    else:
        try:
            df = pd.read_parquet(tl_path, columns=["t", "detector"])
            exp_dets, exp_ts = set(manifest["expected_detector_ids"]), set(manifest["timestamps"])
            act_keys, exp_keys = set(zip(df["t"].astype(int), df["detector"].astype(str))), {(t, d) for t in exp_ts for d in exp_dets}
            if len(df) != len(exp_keys) or act_keys != exp_keys:
                det_ok = False; reasons.append(f"twin_log keys mismatch: {len(df)} rows vs {len(exp_keys)} expected")
        except Exception as e: det_ok = False; reasons.append(f"Error checking twin_log.parquet: {e}")
    checks["detector_keys"] = det_ok

    flagged, flag_reasons = False, []
    if arm.lower() == "evt":
        ev_log_path = attempt_dir / "twin" / "event_log.jsonl"
        if ev_log_path.exists():
            for line in ev_log_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        row = json.loads(line)
                        err = row.get("excluded", {}).get("error") if isinstance(row.get("excluded"), dict) else None
                        if err is not None: flagged = True; flag_reasons.append(f"t={row.get('t')}: {err}")
                    except Exception: pass
    return {"complete": (len(reasons) == 0), "flagged": flagged, "reasons": reasons, "flag_reasons": flag_reasons, "checks": checks}


def check_pairing(evt_attempt_dir: Path, conv_attempt_dir: Path) -> Dict[str, Any]:
    tl_evt, tl_conv = evt_attempt_dir / "twin" / "twin_log.parquet", conv_attempt_dir / "twin" / "twin_log.parquet"
    if not tl_evt.exists() or not tl_conv.exists():
        return {"passed": False, "mismatches": [f"Missing logs: EVT={tl_evt.exists()}, CONV={tl_conv.exists()}"]}
    df_evt = pd.read_parquet(tl_evt).sort_values(["t", "detector"]).reset_index(drop=True)
    df_conv = pd.read_parquet(tl_conv).sort_values(["t", "detector"]).reset_index(drop=True)
    keys_match = (len(df_evt) == len(df_conv) and (df_evt["t"] == df_conv["t"]).all() and (df_evt["detector"] == df_conv["detector"]).all())
    obs_cols = sorted([c for c in df_evt.columns if c.startswith("obs_")])
    cols_match = (obs_cols == sorted([c for c in df_conv.columns if c.startswith("obs_")]))
    mismatches, col_results = [], {}
    if not keys_match: mismatches.append("Keys (t, detector) mismatch between EVT and CONV")
    if not cols_match: mismatches.append("Observation columns mismatch")
    if keys_match and cols_match:
        for c in obs_cols:
            s_evt, s_conv = df_evt[c], df_conv[c]
            null_match = bool((s_evt.isna() == s_conv.isna()).all())
            val_match = bool((s_evt[~s_evt.isna()] == s_conv[~s_conv.isna()]).all()) if null_match else False
            col_results[c] = (null_match and val_match)
            if not null_match: mismatches.append(f"{c}: null pattern mismatch")
            elif not val_match: mismatches.append(f"{c}: value mismatch on valid rows")
    return {"passed": bool(keys_match and cols_match and len(mismatches) == 0), "keys_match": bool(keys_match),
            "keys_count": len(df_evt), "observation_columns": obs_cols, "columns_match": col_results, "mismatches": mismatches}


def execute_slot(spec: Dict[str, Any], runs_dir: Path, manifest: Dict[str, Any],
                 reruns_lock: threading.Lock, reruns_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    slot_dir = runs_dir / spec["name"]
    slot_dir.mkdir(parents=True, exist_ok=True)
    for att_name in ("attempt_1", "attempt_2"):
        att_dir = slot_dir / att_name
        if att_dir.exists() and check_attempt_completeness(att_dir, spec["arm"], manifest)["complete"]:
            return {"slot": spec["name"], "status": "already_complete", "attempt": att_name}

    att1_dir = slot_dir / "attempt_1"
    if not att1_dir.exists(): run_attempt(spec, att1_dir, attempt_num=1)
    res1 = check_attempt_completeness(att1_dir, spec["arm"], manifest)
    if res1["complete"]:
        return {"slot": spec["name"], "status": "complete" if not res1["flagged"] else "complete-but-flagged", "attempt": "attempt_1"}

    p_err = (att1_dir / "proxy_stderr.log").read_text(encoding="utf-8", errors="ignore") if (att1_dir / "proxy_stderr.log").exists() else ""
    t_err = (att1_dir / "twin_stderr.log").read_text(encoding="utf-8", errors="ignore") if (att1_dir / "twin_stderr.log").exists() else ""
    info1 = json.loads((att1_dir / "run_info.json").read_text(encoding="utf-8")) if (att1_dir / "run_info.json").exists() else {}
    is_infra, infra_reason = is_infrastructure_failure(info1.get("proxy_rc", -1), info1.get("twin_rc", -1), p_err, t_err)
    if not is_infra: return {"slot": spec["name"], "status": "permanently_failed", "reason": "Non-infrastructure failure in attempt_1"}

    att2_dir = slot_dir / "attempt_2"
    if not att2_dir.exists():
        rec = {"slot": spec["name"], "attempt_1": {"proxy_rc": info1.get("proxy_rc"), "twin_rc": info1.get("twin_rc"), "signature": infra_reason},
               "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        run_attempt(spec, att2_dir, attempt_num=2)
        info2 = json.loads((att2_dir / "run_info.json").read_text(encoding="utf-8")) if (att2_dir / "run_info.json").exists() else {}
        res2 = check_attempt_completeness(att2_dir, spec["arm"], manifest)
        rec["attempt_2"] = {"proxy_rc": info2.get("proxy_rc"), "twin_rc": info2.get("twin_rc"), "complete": res2["complete"]}
        with reruns_lock:
            reruns_data.append(rec)
            (runs_dir.parent / "reruns.json").write_text(json.dumps({"reruns": reruns_data}, indent=2), encoding="utf-8")

    res2 = check_attempt_completeness(att2_dir, spec["arm"], manifest)
    if res2["complete"]:
        return {"slot": spec["name"], "status": "complete" if not res2["flagged"] else "complete-but-flagged", "attempt": "attempt_2"}
    return {"slot": spec["name"], "status": "permanently_failed", "reason": "attempt_2 also incomplete"}


def run_check(runs_dir: Path, out_dir: Path, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if manifest is None:
        man_path = out_dir / "completeness_manifest.json"
        if not man_path.exists(): man_path = DEV_RUNS_DIR / "completeness_manifest.json"
        manifest = json.loads(man_path.read_text(encoding="utf-8"))

    slots, completeness_records = {}, {}
    for sdir in sorted([p for p in runs_dir.iterdir() if p.is_dir() and (p / "attempt_1").exists()]):
        sname, arm = sdir.name, sdir.name.split("_")[0]
        attempts, slot_status, reasons = {}, "incomplete", []
        for att_idx in (1, 2):
            att_path = sdir / f"attempt_{att_idx}"
            if att_path.exists():
                c_res = check_attempt_completeness(att_path, arm, manifest)
                attempts[f"attempt_{att_idx}"] = c_res
                if c_res["complete"]: slot_status = "complete" if not c_res["flagged"] else "complete-but-flagged"
                else: reasons.extend(c_res["reasons"])
        if slot_status == "incomplete":
            if "attempt_2" in attempts: slot_status = "permanently_failed"
            elif "attempt_1" in attempts:
                p_err = (sdir / "attempt_1" / "proxy_stderr.log").read_text(encoding="utf-8", errors="ignore") if (sdir / "attempt_1" / "proxy_stderr.log").exists() else ""
                t_err = (sdir / "attempt_1" / "twin_stderr.log").read_text(encoding="utf-8", errors="ignore") if (sdir / "attempt_1" / "twin_stderr.log").exists() else ""
                info1 = json.loads((sdir / "attempt_1" / "run_info.json").read_text(encoding="utf-8")) if (sdir / "attempt_1" / "run_info.json").exists() else {}
                is_infra, _ = is_infrastructure_failure(info1.get("proxy_rc", -1), info1.get("twin_rc", -1), p_err, t_err)
                if not is_infra: slot_status = "permanently_failed"
        slots[sname] = {"status": slot_status, "latest_attempt": len(attempts), "attempts_count": len(attempts), "reasons": reasons}
        completeness_records[sname] = {"status": slot_status, "attempts": attempts}

    summary = {"complete": 0, "complete_but_flagged": 0, "incomplete": 0, "permanently_failed": 0}
    for s in slots.values():
        st = s["status"].replace("-", "_")
        if st in summary: summary[st] += 1

    pairs, all_pairs_pass = {}, True
    for ss in sorted({("_".join(s.split("_")[1:])) for s in slots.keys()}):
        evt_name, conv_name = f"evt_{ss}", f"conv_{ss}"
        if evt_name in slots and conv_name in slots:
            def latest_att(sn):
                sd = runs_dir / sn
                return (sd / "attempt_2") if (sd / "attempt_2").exists() else (sd / "attempt_1")
            p_res = check_pairing(latest_att(evt_name), latest_att(conv_name))
            pairs[ss] = p_res
            if not p_res["passed"]: all_pairs_pass = False

    pairing_out = {"passed": all_pairs_pass, "pairs": pairs}
    completeness_out = {"summary": summary, "slots": completeness_records}
    slots_out = {"summary": summary, "slots": slots}
    for target in {out_dir, runs_dir}:
        (target / "pairing_check.json").write_text(json.dumps(pairing_out, indent=2), encoding="utf-8")
        (target / "completeness.json").write_text(json.dumps(completeness_out, indent=2), encoding="utf-8")
        (target / "slots.json").write_text(json.dumps(slots_out, indent=2), encoding="utf-8")
    return {"pairing": pairing_out, "completeness": completeness_out, "slots": slots_out}


def main():
    parser = argparse.ArgumentParser(description="Development runs driver.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--allow-dirty", action="store_true", help="Allow dirty working directory")
    p_prep.add_argument("--out-dir", type=Path, default=DEV_RUNS_DIR)

    p_coll = sub.add_parser("collect")
    p_coll.add_argument("--parallel", type=int, default=4)
    p_coll.add_argument("--runs-dir", type=Path, default=DEV_RUNS_DIR / "runs")
    p_coll.add_argument("--slots", type=str, default=None)
    p_coll.add_argument("--smoke", action="store_true")

    p_chk = sub.add_parser("check")
    p_chk.add_argument("--runs-dir", type=Path, default=DEV_RUNS_DIR / "runs")
    p_chk.add_argument("--out-dir", type=Path, default=DEV_RUNS_DIR)
    args = parser.parse_args()

    if args.command == "prepare":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        s_res = check_seeds(REPO_ROOT / "results")
        (args.out_dir / "seed_check.json").write_text(json.dumps(s_res, indent=2), encoding="utf-8")
        if not s_res["passed"]: raise RuntimeError(f"Seeds 4401-4406 already used: {s_res['matches']}")
        (args.out_dir / "provenance.json").write_text(json.dumps(build_provenance(args.allow_dirty), indent=2), encoding="utf-8")
        (args.out_dir / "completeness_manifest.json").write_text(json.dumps(build_manifest(), indent=2), encoding="utf-8")
        print("Prepare complete.")
    elif args.command == "collect":
        runs_dir = DEV_RUNS_DIR / "smoke" if args.smoke else args.runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)
        man_path = DEV_RUNS_DIR / "completeness_manifest.json"
        manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else build_manifest()
        specs = get_slot_specs()
        if args.smoke: specs = [s for s in specs if s["name"] in ("evt_noi_4401", "conv_noi_4401")]
        elif args.slots: specs = [s for s in specs if s["name"] in set(args.slots.split(","))]
        reruns_file, r_lock = DEV_RUNS_DIR / "reruns.json", threading.Lock()
        r_data = json.loads(reruns_file.read_text(encoding="utf-8")).get("reruns", []) if reruns_file.exists() else []
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as ex:
            futs = [ex.submit(execute_slot, sp, runs_dir, manifest, r_lock, r_data) for sp in specs]
            for f in futs: print(f"Slot {f.result().get('slot')}: {f.result().get('status')}")
    elif args.command == "check":
        res = run_check(args.runs_dir, args.out_dir)
        print(f"Check summary: {res['slots']['summary']}, pairing={res['pairing']['passed']}")


if __name__ == "__main__":
    main()
