"""Preregistered offline decision audit (report2 §K, §L / docs/oct6-audit-and-pilot2-plan.md).

Pipeline:
1. Verify fresh seeds 4201-4208 are not used in existing results.
2. Two-world INC runs for seeds 4201-4208 (Twin CONV NA-300 + factor 0.85; Proxy INC 4500-5400s; snapshots at 5100s without RNG).
3. Compute corrected-G4 alarm times and latency t_d - alarm.
4. Run RNG check on seed 4201 (determinism and seed divergence) -> results/audit/rng_check.json.
5. Generate resampled Proxy/Twin future demand and run audit branches (Twin R1/R2, Proxy M1/M2, Calibration floor 7-12).
6. Save raw J table to results/audit/raw.parquet BEFORE any metric computation.
7. Compute per-seed and pooled metrics (BEE, Regret, Top-1, Spearman, Kendall, CRN corr, CIs, bootstrap, floor).
8. Generate results/audit/report.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os

# Binding environment variables (prompt.md line 3)
os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from citypulse.branching.audit_engine import (
    ACTIONS,
    HORIZON_STEPS,
    ROUTE_SPECS,
    T_D,
    D_P_seed,
    D_T_seed,
    build_proxy_resampled_routes,
    run_proxy_branch_jobs,
    run_twin_branch_jobs,
    strip_future_departures_from_proxy_snapshot,
    strip_rng_state_from_xml,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCEN5_DIR = REPO_ROOT / "scenarios" / "kwuntong" / "blite" / "synth5"
PROXY_ROU = SCEN5_DIR / "proxy.rou.xml"
TWIN_CAND_ROU = SCEN5_DIR / "twin_cand.rou.xml"
SIGMA_DEV = REPO_ROOT / "results" / "assim" / "na300" / "sigma300_dev.json"
SIGMA_EVENT = REPO_ROOT / "results" / "event_pilot" / "impl" / "sigma_event.json"
AUDIT_DIR = REPO_ROOT / "results" / "audit"

AUDIT_SEEDS = [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]
TWIN_BASE_FACTOR = 0.85
BOUNDARY_DETECTOR = "AID07106"
TWIN_SEED = 2
DEMAND_SEED = 202


def check_fresh_seeds(seeds: List[int] = AUDIT_SEEDS) -> Tuple[bool, List[str]]:
    """Verify that seeds 4201-4208 do not appear as experiment seeds in existing results."""
    found = []
    results_dir = REPO_ROOT / "results"
    if not results_dir.exists():
        return True, []

    for s in seeds:
        s_str = str(s)
        for root, dirs, files in os.walk(results_dir):
            if "audit" in root:
                continue
            for d in dirs:
                if f"_{s_str}" in d or f"-{s_str}" in d or d == s_str:
                    found.append(f"Directory {os.path.join(root, d)}")
            for f in files:
                if f.endswith(".json") or f.endswith(".parquet") or f.endswith(".csv"):
                    if f"_{s_str}." in f or f"-{s_str}." in f:
                        found.append(f"File {os.path.join(root, f)}")
    return len(found) == 0, found


def compute_alarm_for_twin_log(twin_log_path: Path, sigma_path: Path = SIGMA_EVENT) -> Dict[str, Any]:
    """Offline corrected-G4 trigger on twin_log.parquet.

    B >= 3.0 at two timestamps exactly 30s apart, missing interval resets.
    """
    df = pd.read_parquet(twin_log_path)
    with open(sigma_path, "r", encoding="utf-8") as fh:
        raw_sigma = json.load(fh)
    sigma_data = raw_sigma.get("sigma", raw_sigma)
    sig_u_o = float(sigma_data["AID02109"]["o"])
    sig_u_v = float(sigma_data["AID02109"]["v"])
    sig_d_o = float(sigma_data["AID02111"]["o"])
    sig_d_v = float(sigma_data["AID02111"]["v"])

    u_df = df[df["detector"] == "AID02109"].sort_values("t")
    d_df = df[df["detector"] == "AID02111"].sort_values("t")
    merged = pd.merge(u_df, d_df, on="t", suffixes=("_u", "_d")).sort_values("t")

    streak = 0
    last_t = None
    first_alarm_t = None
    all_alarms = []

    for _, row in merged.iterrows():
        t = float(row["t"])
        # Check validity
        if not bool(row["obs_valid_u"]) or not bool(row["obs_valid_d"]):
            streak = 0
            last_t = t
            continue
        if pd.isna(row["obs_o_u"]) or pd.isna(row["obs_o_d"]):
            streak = 0
            last_t = t
            continue

        r_u_o = (float(row["obs_o_u"]) - float(row["twin_o_u"])) / sig_u_o
        r_d_o = (float(row["obs_o_d"]) - float(row["twin_o_d"])) / sig_d_o
        r_u_v = (
            (float(row["obs_v_u"]) - float(row["twin_v_u"])) / sig_u_v
            if pd.notna(row["obs_v_u"]) and pd.notna(row["twin_v_u"])
            else 0.0
        )
        r_d_v = (
            (float(row["obs_v_d"]) - float(row["twin_v_d"])) / sig_d_v
            if pd.notna(row["obs_v_d"]) and pd.notna(row["twin_v_d"])
            else 0.0
        )

        B = 0.5 * (r_u_o - r_d_o) + 0.5 * (r_d_v - r_u_v)
        if B >= 3.0:
            if last_t is not None and abs(t - last_t - 30.0) < 1e-4:
                streak += 1
            else:
                streak = 1
        else:
            streak = 0
        last_t = t

        if streak >= 2:
            all_alarms.append(t)
            if first_alarm_t is None:
                first_alarm_t = t

    latency = (T_D - first_alarm_t) if first_alarm_t is not None else None
    return {
        "first_alarm_t": first_alarm_t,
        "latency_s": latency,
        "latency_ok": (latency >= 120.0) if latency is not None else False,
        "n_alarm_intervals": len(all_alarms),
    }


def run_twoworld_batch(
    seeds: List[int],
    runs_dir: Path,
    base_port: int = 5600,
    t_end: float = 7200.0,
) -> Dict[int, Any]:
    """Launch a batch of up to 4 Twin + Proxy two-world INC runs (<= 8 SUMO processes)."""
    env = dict(
        os.environ,
        CITYPULSE_NET="blite",
        CITYPULSE_BLITE_REV="5",
        CITYPULSE_REROUTE="0",
        PYTHONDONTWRITEBYTECODE="1",
        OPENBLAS_NUM_THREADS="1",
    )
    procs = []
    t0 = time.time()
    for i, s in enumerate(seeds):
        s_dir = runs_dir / f"seed_{s}"
        twin_dir = s_dir / "twin"
        proxy_dir = s_dir / "proxy"
        twin_dir.mkdir(parents=True, exist_ok=True)
        proxy_dir.mkdir(parents=True, exist_ok=True)
        port = base_port + i * 2
        ep = f"tcp://127.0.0.1:{port}"

        targs = [
            sys.executable,
            "-m",
            "citypulse.twin.service",
            "--endpoint",
            ep,
            "--out",
            str(twin_dir),
            "--seed",
            str(TWIN_SEED),
            "--demand-seed",
            str(DEMAND_SEED),
            "--demand-path",
            str(TWIN_CAND_ROU),
            "--assim",
            "normal300",
            "--boundary-detector",
            BOUNDARY_DETECTOR,
            "--sigma-json",
            str(SIGMA_DEV),
            "--twin-base-factor",
            str(TWIN_BASE_FACTOR),
            "--snapshot-times",
            str(int(T_D)),
        ]
        pargs = [
            sys.executable,
            "-m",
            "citypulse.proxy.service",
            "--endpoint",
            ep,
            "--out",
            str(proxy_dir),
            "--seed",
            str(s),
            "--sensor-seed",
            "77",
            "--t-end",
            str(int(t_end)),
            "--routes",
            str(PROXY_ROU),
            "--proxy-snapshot-times",
            str(int(T_D)),
        ]
        twin_p = subprocess.Popen(targs, env=env, cwd=str(REPO_ROOT))
        procs.append((s, s_dir, twin_p, pargs))

    time.sleep(2)
    proxy_procs = []
    for s, s_dir, twin_p, pargs in procs:
        p_proc = subprocess.Popen(pargs, env=env, cwd=str(REPO_ROOT))
        proxy_procs.append((s, s_dir, twin_p, p_proc))

    results = {}
    for s, s_dir, twin_p, proxy_p in proxy_procs:
        rc_p, rc_t = proxy_p.wait(), twin_p.wait()
        wall = round(time.time() - t0, 1)
        if rc_p != 0 or rc_t != 0:
            raise RuntimeError(f"Two-world run failed for seed {s}: proxy_rc={rc_p}, twin_rc={rc_t}")

        twin_state = s_dir / "twin" / f"twin_state_{int(T_D)}.xml.gz"
        proxy_state = s_dir / "proxy" / f"proxy_state_{int(T_D)}.xml.gz"
        strip_rng_state_from_xml(twin_state)
        strip_rng_state_from_xml(proxy_state)
        strip_future_departures_from_proxy_snapshot(proxy_state, T_D)

        alarm_info = compute_alarm_for_twin_log(s_dir / "twin" / "twin_log.parquet")
        info = {
            "seed": s,
            "wall_s": wall,
            "proxy_rc": rc_p,
            "twin_rc": rc_t,
            "alarm": alarm_info,
            "twin_state": str(twin_state),
            "twin_meta": str(s_dir / "twin" / f"twin_state_{int(T_D)}.json"),
            "proxy_state": str(proxy_state),
        }
        with open(s_dir / "two_world_info.json", "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=2)
        results[s] = info
    return results


def run_rng_check(seed_info: Dict[str, Any], out_path: Path) -> Dict[str, Any]:
    """Execute the preregistered RNG checks on seed 4201.

    (i) a different --seed gives a different trajectory;
    (ii) identical inputs give identical J and an identical vehicle digest.
    """
    seed = int(seed_info["seed"])
    twin_state = seed_info["twin_state"]
    twin_meta = seed_info["twin_meta"]
    proxy_state = seed_info["proxy_state"]

    # Proxy routes for check
    temp_dir = AUDIT_DIR / "scratch_rng"
    temp_dir.mkdir(parents=True, exist_ok=True)
    r_m1 = temp_dir / "proxy_m1.rou.xml"
    r_m2 = temp_dir / "proxy_m2.rou.xml"
    orig_ids_m1, _ = build_proxy_resampled_routes(PROXY_ROU, r_m1, seed=seed, m=1)
    orig_ids_m2, _ = build_proxy_resampled_routes(PROXY_ROU, r_m2, seed=seed, m=2)

    # 1. Twin tests
    job_t1_a = {"state": twin_state, "meta": twin_meta, "seed": seed, "r": 1, "action": "A0", "horizon": 900}
    job_t1_b = {"state": twin_state, "meta": twin_meta, "seed": seed, "r": 1, "action": "A0", "horizon": 900}
    job_t2 = {"state": twin_state, "meta": twin_meta, "seed": seed, "r": 2, "action": "A0", "horizon": 900}

    res_t = run_twin_branch_jobs([job_t1_a, job_t1_b, job_t2], workers=3)
    res_t1_a, res_t1_b, res_t2 = res_t[0], res_t[1], res_t[2]

    twin_identical_inputs_match = (
        res_t1_a.get("status") == "ok"
        and res_t1_b.get("status") == "ok"
        and res_t1_a["J"] == res_t1_b["J"]
        and res_t1_a["veh_digest"] == res_t1_b["veh_digest"]
    )
    twin_diff_seed_differs = (
        res_t2.get("status") == "ok"
        and (res_t1_a["veh_digest"] != res_t2["veh_digest"] or res_t1_a["J"] != res_t2["J"])
    )

    # 2. Proxy tests
    job_p1_a = {
        "state": proxy_state,
        "routes": str(r_m1),
        "orig_future_ids": list(orig_ids_m1),
        "seed": seed,
        "m": 1,
        "action": "A0",
        "horizon": 900,
        "world": "proxy",
    }
    job_p1_b = {
        "state": proxy_state,
        "routes": str(r_m1),
        "orig_future_ids": list(orig_ids_m1),
        "seed": seed,
        "m": 1,
        "action": "A0",
        "horizon": 900,
        "world": "proxy",
    }
    job_p2 = {
        "state": proxy_state,
        "routes": str(r_m2),
        "orig_future_ids": list(orig_ids_m2),
        "seed": seed,
        "m": 2,
        "action": "A0",
        "horizon": 900,
        "world": "proxy",
    }

    res_p = run_proxy_branch_jobs([job_p1_a, job_p1_b, job_p2], workers=3)
    res_p1_a, res_p1_b, res_p2 = res_p[0], res_p[1], res_p[2]

    proxy_identical_inputs_match = (
        res_p1_a.get("status") == "ok"
        and res_p1_b.get("status") == "ok"
        and res_p1_a["J"] == res_p1_b["J"]
        and res_p1_a["veh_digest"] == res_p1_b["veh_digest"]
    )
    proxy_diff_seed_differs = (
        res_p2.get("status") == "ok"
        and (res_p1_a["veh_digest"] != res_p2["veh_digest"] or res_p1_a["J"] != res_p2["J"])
    )

    passed = (
        twin_identical_inputs_match
        and twin_diff_seed_differs
        and proxy_identical_inputs_match
        and proxy_diff_seed_differs
    )

    report = {
        "passed": bool(passed),
        "seed": seed,
        "twin": {
            "identical_match": bool(twin_identical_inputs_match),
            "diff_seed_differs": bool(twin_diff_seed_differs),
            "r1_a_digest": res_t1_a["veh_digest"],
            "r1_b_digest": res_t1_b["veh_digest"],
            "r2_digest": res_t2["veh_digest"],
            "r1_a_J": res_t1_a["J"],
            "r1_b_J": res_t1_b["J"],
            "r2_J": res_t2["J"],
        },
        "proxy": {
            "identical_match": bool(proxy_identical_inputs_match),
            "diff_seed_differs": bool(proxy_diff_seed_differs),
            "m1_a_digest": res_p1_a["veh_digest"],
            "m1_b_digest": res_p1_b["veh_digest"],
            "m2_digest": res_p2["veh_digest"],
            "m1_a_J": res_p1_a["J"],
            "m1_b_J": res_p1_b["J"],
            "m2_J": res_p2["J"],
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    return report


def rankdata(a: Any) -> np.ndarray:
    arr = np.asarray(a)
    order = np.argsort(arr)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(arr) + 1)
    for val in np.unique(arr):
        idx = np.where(arr == val)[0]
        if len(idx) > 1:
            ranks[idx] = ranks[idx].mean()
    return ranks


def spearman_rho(x: Any, y: Any) -> float:
    rx, ry = rankdata(x), rankdata(y)
    std_x, std_y = np.std(rx), np.std(ry)
    if std_x == 0 or std_y == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def kendall_tau(x: Any, y: Any) -> float:
    n = len(x)
    concordant, discordant = 0, 0
    t_x, t_y = 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            elif dx == 0:
                t_x += 1
            elif dy == 0:
                t_y += 1
            elif (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1
    denom = math.sqrt((concordant + discordant + t_x) * (concordant + discordant + t_y))
    return float((concordant - discordant) / denom) if denom > 0 else 0.0


def t_critical_95(df: int) -> float:
    """Exact two-sided 95% critical value for Student's t distribution with df degrees of freedom."""
    t_table = {
        1: 12.7062,
        2: 4.3027,
        3: 3.1824,
        4: 2.7764,
        5: 2.5706,
        6: 2.4469,
        7: 2.364624,
        8: 2.306004,
        9: 2.262157,
        10: 2.228139,
    }
    return t_table.get(df, 1.95996)


def compute_metrics_from_raw(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Compute per-seed and pooled audit metrics from raw J records."""
    seeds = sorted(df["seed"].unique())
    per_seed = []

    for s in seeds:
        sub = df[df["seed"] == s]

        # 1. Twin: R1 = 1..3, R2 = 4..6
        tw = sub[sub["world"] == "twin"]
        j_t_r1 = tw[tw["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
        j_t_r2 = tw[tw["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        j_t_all = tw.groupby("action")["J"].mean()

        a_star = str(j_t_r1.idxmin())
        a_star_unsplit = str(j_t_all.idxmin())
        g_t_hat = float(j_t_r2["A0"] - j_t_r2[a_star])
        g_t_hat_unsplit = float(j_t_all["A0"] - j_t_all[a_star_unsplit])

        # 2. Proxy: M1 = 1..3, M2 = 4..6
        px = sub[sub["world"] == "proxy"]
        j_p_m1 = px[px["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
        j_p_m2 = px[px["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        j_p_all = px.groupby("action")["J"].mean()

        oracle = str(j_p_m1.idxmin())
        oracle_unsplit = str(j_p_all.idxmin())
        g_p = float(j_p_m2["A0"] - j_p_m2[a_star])
        g_p_unsplit = float(j_p_all["A0"] - j_p_all[a_star_unsplit])
        j_p_a0_m2 = float(j_p_m2["A0"])
        j_p_a0_all = float(j_p_all["A0"])

        # Split BEE
        bee_signed = g_t_hat - g_p
        bee_abs = abs(bee_signed)
        bee_rel = bee_abs / j_p_a0_m2 if j_p_a0_m2 > 0 else None
        bee_signed_rel = bee_signed / j_p_a0_m2 if j_p_a0_m2 > 0 else None

        # Unsplit BEE
        bee_signed_unsplit = g_t_hat_unsplit - g_p_unsplit
        bee_abs_unsplit = abs(bee_signed_unsplit)
        bee_rel_unsplit = bee_abs_unsplit / j_p_a0_all if j_p_a0_all > 0 else None

        # Split Regret
        regret = float(j_p_m2[a_star] - j_p_m2[oracle])
        denom = float(j_p_m2["A0"] - j_p_m2[oracle])
        regret_rel = (regret / denom) if denom >= 0.5 else None

        # Unsplit Regret
        regret_unsplit = float(j_p_all[a_star_unsplit] - j_p_all[oracle_unsplit])
        denom_unsplit = float(j_p_all["A0"] - j_p_all[oracle_unsplit])
        regret_rel_unsplit = (regret_unsplit / denom_unsplit) if denom_unsplit >= 0.5 else None

        # 3. Calibration floor: Proxy seeds 7..12
        cal = sub[sub["world"] == "calibration"]
        j_c_sel = cal[cal["replication"].isin([7, 8, 9])].groupby("action")["J"].mean()
        j_c_est = cal[cal["replication"].isin([10, 11, 12])].groupby("action")["J"].mean()
        a_star_floor = str(j_c_sel.idxmin())
        g_hat_floor = float(j_c_est["A0"] - j_c_est[a_star_floor])
        g_p_floor = float(j_p_m2["A0"] - j_p_m2[a_star_floor])
        bee_floor_signed = g_hat_floor - g_p_floor
        bee_floor_abs = abs(bee_floor_signed)
        bee_floor_rel = bee_floor_abs / j_p_a0_m2 if j_p_a0_m2 > 0 else None

        # 4. Rankings (Twin on R2 vs Proxy on M2 across A0-A4)
        order_act = list(ACTIONS)
        t_vals = [float(j_t_r2[a]) for a in order_act]
        p_vals = [float(j_p_m2[a]) for a in order_act]

        top1_agree = 1.0 if a_star == oracle else 0.0
        top1_r2_m2_agree = 1.0 if (j_t_r2.idxmin() == j_p_m2.idxmin()) else 0.0

        rho = spearman_rho(t_vals, p_vals)
        tau = kendall_tau(t_vals, p_vals)

        # 5. CRN Correlation
        # Within each replication across actions, compute correlation matrix between replications
        pivot_px = px.pivot(index="replication", columns="action", values="J")
        corr_matrix = pivot_px.T.corr()
        crn_corrs = []
        for i in corr_matrix.columns:
            for j in corr_matrix.columns:
                if i < j and not math.isnan(corr_matrix.loc[i, j]):
                    crn_corrs.append(corr_matrix.loc[i, j])
        mean_crn_corr = float(np.mean(crn_corrs)) if crn_corrs else None

        row = {
            "seed": int(s),
            "a_star": a_star,
            "oracle": oracle,
            "a_star_unsplit": a_star_unsplit,
            "oracle_unsplit": oracle_unsplit,
            "a_star_floor": a_star_floor,
            "G_T_hat": g_t_hat,
            "G_P": g_p,
            "BEE_signed": bee_signed,
            "BEE_abs": bee_abs,
            "BEE_rel": bee_rel,
            "BEE_signed_rel": bee_signed_rel,
            "BEE_abs_unsplit": bee_abs_unsplit,
            "BEE_rel_unsplit": bee_rel_unsplit,
            "Regret": regret,
            "Regret_denom": denom,
            "Regret_rel": regret_rel,
            "Regret_unsplit": regret_unsplit,
            "Regret_denom_unsplit": denom_unsplit,
            "Regret_rel_unsplit": regret_rel_unsplit,
            "BEE_floor_signed": bee_floor_signed,
            "BEE_floor_abs": bee_floor_abs,
            "BEE_floor_rel": bee_floor_rel,
            "top1_agree": top1_agree,
            "top1_r2_m2_agree": top1_r2_m2_agree,
            "spearman_rho": float(rho),
            "kendall_tau": float(tau),
            "mean_crn_corr": mean_crn_corr,
            "J_T_r1": {a: float(j_t_r1[a]) for a in ACTIONS},
            "J_T_r2": {a: float(j_t_r2[a]) for a in ACTIONS},
            "J_P_m1": {a: float(j_p_m1[a]) for a in ACTIONS},
            "J_P_m2": {a: float(j_p_m2[a]) for a in ACTIONS},
        }
        per_seed.append(row)

    # Pooled metrics
    metric_keys = [
        "BEE_signed",
        "BEE_abs",
        "BEE_rel",
        "BEE_abs_unsplit",
        "BEE_rel_unsplit",
        "Regret",
        "Regret_rel",
        "Regret_unsplit",
        "Regret_rel_unsplit",
        "BEE_floor_signed",
        "BEE_floor_abs",
        "BEE_floor_rel",
        "top1_agree",
        "top1_r2_m2_agree",
        "spearman_rho",
        "kendall_tau",
        "mean_crn_corr",
    ]

    pooled: Dict[str, Any] = {}
    rng = np.random.default_rng(42)

    for k in metric_keys:
        vals = [r[k] for r in per_seed if r[k] is not None and not math.isnan(r[k])]
        n = len(vals)
        if n == 0:
            pooled[k] = {"n": 0, "mean": None}
            continue
        m = float(np.mean(vals))
        s = float(np.std(vals, ddof=1)) if n > 1 else 0.0
        se = s / math.sqrt(n) if n > 1 else 0.0

        # Paired t 95% CI
        if n > 1:
            t_crit = t_critical_95(n - 1)
            ci_t = (m - t_crit * se, m + t_crit * se)
        else:
            ci_t = (m, m)

        # Percentile bootstrap 95% CI (10000 resamples)
        if n > 1:
            boot_means = [float(np.mean(rng.choice(vals, size=n, replace=True))) for _ in range(10000)]
            ci_boot = (float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5)))
        else:
            ci_boot = (m, m)

        pooled[k] = {
            "n": n,
            "mean": m,
            "std": s,
            "se": se,
            "ci95_t": ci_t,
            "ci95_boot": ci_boot,
        }

    return per_seed, pooled


def main():
    ap = argparse.ArgumentParser(description="Preregistered offline decision audit")
    ap.add_argument("--workers", type=int, default=8, help="Max parallel SUMO workers")
    ap.add_argument("--skip-twoworld", action="store_true", help="Skip two-world runs if snapshots exist")
    args = ap.parse_args()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    runs_dir = AUDIT_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    print("=== Step 1: Fresh Seeds Check ===")
    ok, existing = check_fresh_seeds(AUDIT_SEEDS)
    if not ok:
        print(f"ERROR: Existing results use seeds {AUDIT_SEEDS}: {existing}")
        sys.exit(1)
    print(f"Seeds {AUDIT_SEEDS} confirmed fresh and unused.")

    print("\n=== Step 2: Two-World INC Runs ===")
    two_world_infos = {}
    needed_seeds = []
    for s in AUDIT_SEEDS:
        info_file = runs_dir / f"seed_{s}" / "two_world_info.json"
        if args.skip_twoworld and info_file.exists():
            print(f"Seed {s}: loading existing two-world result from {info_file}")
            with open(info_file, "r", encoding="utf-8") as fh:
                two_world_infos[s] = json.load(fh)
        else:
            needed_seeds.append(s)

    for i in range(0, len(needed_seeds), 4):
        batch = needed_seeds[i : i + 4]
        print(f"Running Two-world batch for seeds {batch} (<= 8 SUMO processes)...")
        b_res = run_twoworld_batch(batch, runs_dir, base_port=5600 + i * 10, t_end=7200.0)
        two_world_infos.update(b_res)
        for s, info in b_res.items():
            al = info["alarm"]
            print(
                f"  Done seed {s}: wall={info['wall_s']}s, first_alarm={al['first_alarm_t']}s, "
                f"latency={al['latency_s']}s (>=120s: {al['latency_ok']})"
            )

    for s, info in two_world_infos.items():
        strip_rng_state_from_xml(Path(info["twin_state"]))
        strip_rng_state_from_xml(Path(info["proxy_state"]))
        strip_future_departures_from_proxy_snapshot(Path(info["proxy_state"]), T_D)

    print("\n=== Step 3: RNG Check on Seed 4201 ===")
    rng_check_file = AUDIT_DIR / "rng_check.json"
    rng_res = run_rng_check(two_world_infos[4201], rng_check_file)
    print(f"RNG Check Result: passed={rng_res['passed']}")
    print(f"  Twin: match={rng_res['twin']['identical_match']}, differs={rng_res['twin']['diff_seed_differs']}")
    print(f"  Proxy: match={rng_res['proxy']['identical_match']}, differs={rng_res['proxy']['diff_seed_differs']}")
    if not rng_res["passed"]:
        print("STOPPING: RNG check failed per preregistered protocol.")
        sys.exit(1)

    print("\n=== Step 4 & 5: Generating Re-sampled Demand & Running Branches ===")
    all_raw_records = []
    failures: Dict[str, int] = {}

    branch_routes_dir = AUDIT_DIR / "routes"
    branch_routes_dir.mkdir(parents=True, exist_ok=True)

    twin_jobs: List[Dict[str, Any]] = []
    proxy_jobs: List[Dict[str, Any]] = []

    for seed in AUDIT_SEEDS:
        info = two_world_infos[seed]
        tw_state = info["twin_state"]
        tw_meta = info["twin_meta"]
        px_state = info["proxy_state"]

        # 1. Twin jobs: R1 (1..3) + R2 (4..6) x A0..A4
        for r in range(1, 7):
            for a in ACTIONS:
                twin_jobs.append(
                    {
                        "state": tw_state,
                        "meta": tw_meta,
                        "seed": seed,
                        "r": r,
                        "action": a,
                        "horizon": HORIZON_STEPS,
                    }
                )

        # 2. Proxy routes & jobs: M (1..6) and Calibration (7..12) x A0..A4
        for m in range(1, 13):
            is_calib = m >= 7
            world_name = "calibration" if is_calib else "proxy"
            rt_path = branch_routes_dir / f"proxy_s{seed}_m{m}.rou.xml"
            orig_ids, n_veh = build_proxy_resampled_routes(
                PROXY_ROU, rt_path, seed=seed, m=m, t_d=T_D, horizon=HORIZON_STEPS
            )
            for a in ACTIONS:
                proxy_jobs.append(
                    {
                        "state": px_state,
                        "routes": str(rt_path),
                        "orig_future_ids": list(orig_ids),
                        "seed": seed,
                        "m": m,
                        "action": a,
                        "horizon": HORIZON_STEPS,
                        "world": world_name,
                    }
                )

    print(f"Launching {len(twin_jobs)} Twin branch jobs on {args.workers} workers...")
    t0_tw = time.time()
    twin_results = run_twin_branch_jobs(twin_jobs, workers=args.workers)
    print(f"Twin branch jobs completed in {round(time.time() - t0_tw, 1)}s.")

    print(f"Launching {len(proxy_jobs)} Proxy branch jobs on {args.workers} workers...")
    t0_px = time.time()
    proxy_results = run_proxy_branch_jobs(proxy_jobs, workers=args.workers)
    print(f"Proxy branch jobs completed in {round(time.time() - t0_px, 1)}s.")

    for r in twin_results + proxy_results:
        if r.get("status") == "error":
            reason = r.get("reason", "UnknownError")
            failures[reason] = failures.get(reason, 0) + 1
        all_raw_records.append(r)

    # Step 6: Save raw.parquet BEFORE computing any metric
    raw_df = pd.DataFrame(all_raw_records)
    raw_parquet_path = AUDIT_DIR / "raw.parquet"
    raw_df.to_parquet(raw_parquet_path)
    print(f"\nSaved {len(raw_df)} raw records to {raw_parquet_path} (failures={sum(failures.values())})")

    # Step 7: Compute metrics
    per_seed, pooled = compute_metrics_from_raw(raw_df)
    with open(AUDIT_DIR / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"per_seed": per_seed, "pooled": pooled, "failures": failures}, fh, indent=2)

    # Step 8: Generate report.md
    generate_report(two_world_infos, rng_res, per_seed, pooled, failures, AUDIT_DIR / "report.md")
    print(f"\nAudit complete! Report written to {AUDIT_DIR / 'report.md'}")


def generate_report(
    two_world_infos: Dict[int, Any],
    rng_res: Dict[str, Any],
    per_seed: List[Dict[str, Any]],
    pooled: Dict[str, Any],
    failures: Dict[str, int],
    out_file: Path,
):
    """Write results/audit/report.md exactly conforming to specification."""
    lines = []
    lines.append("MODEL: Gemini 3.8 Flash (High)")
    lines.append("")
    lines.append("# Preregistered Offline Decision Audit Report")
    lines.append("")
    lines.append("This report documents the offline decision fidelity audit prescribed in `docs/oct6-audit-and-pilot2-plan.md` (Part A) and report2 §K–§L.")
    lines.append("As preregistered, this audit is an observational measurement of decision fidelity; no efficacy claims are made.")
    lines.append("")

    # 1. Fresh Seeds Check
    lines.append("## 1. Seed Verification")
    lines.append("")
    lines.append("- **Audit Seeds**: 4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208 (N = 8)")
    lines.append("- **Verification**: Checked against all prior runs in `results/`. None of seeds 4201–4208 were previously used.")
    lines.append("")

    # 2. Alarm Times & Latencies
    lines.append("## 2. Corrected-G4 Alarm Times and Latencies")
    lines.append("")
    lines.append("Decision timestamp: $t_d = 5,100$ s. Alarm detection requires $B \\ge 3.0$ at two timestamps exactly 30 s apart on Twin log (using $\\sigma$ from `results/event_pilot/impl/sigma_event.json`).")
    lines.append("")
    lines.append("| Seed | First Alarm $t_{\\text{alarm}}$ (s) | $t_d - t_{\\text{alarm}}$ (s) | $\\ge 120$ s Required | Alarm Intervals | Wall Time (s) |")
    lines.append("|---|---|---|---|---|---|")
    for s in AUDIT_SEEDS:
        info = two_world_infos[s]
        al = info["alarm"]
        a_t = f"{al['first_alarm_t']:.1f}" if al["first_alarm_t"] is not None else "None"
        lat = f"{al['latency_s']:.1f}" if al["latency_s"] is not None else "N/A"
        ok_str = "YES" if al["latency_ok"] else "NO"
        lines.append(f"| {s} | {a_t} | {lat} | {ok_str} | {al['n_alarm_intervals']} | {info['wall_s']} |")
    lines.append("")

    # 3. RNG Check
    lines.append("## 3. RNG Check on Seed 4201")
    lines.append("")
    lines.append(f"- **Overall Status**: **{'PASSED' if rng_res['passed'] else 'FAILED'}**")
    lines.append(f"- **Twin World**:")
    lines.append(f"  - (i) Different `--seed` (r=1 vs r=2) produces different trajectory: **{rng_res['twin']['diff_seed_differs']}** (digest `{rng_res['twin']['r1_a_digest'][:12]}...` vs `{rng_res['twin']['r2_digest'][:12]}...`)")
    lines.append(f"  - (ii) Identical inputs (r=1 run 1 vs run 2) reproduce identical J and vehicle digest: **{rng_res['twin']['identical_match']}** (J = {rng_res['twin']['r1_a_J']:.6f} veh·h, digest `{rng_res['twin']['r1_a_digest'][:12]}...`)")
    lines.append(f"- **Proxy World**:")
    lines.append(f"  - (i) Different `--seed` (m=1 vs m=2) produces different trajectory: **{rng_res['proxy']['diff_seed_differs']}** (digest `{rng_res['proxy']['m1_a_digest'][:12]}...` vs `{rng_res['proxy']['m2_digest'][:12]}...`)")
    lines.append(f"  - (ii) Identical inputs (m=1 run 1 vs run 2) reproduce identical J and vehicle digest: **{rng_res['proxy']['identical_match']}** (J = {rng_res['proxy']['m1_a_J']:.6f} veh·h, digest `{rng_res['proxy']['m1_a_digest'][:12]}...`)")
    lines.append("")

    # 4. Per-Seed Decisions and Metrics Table
    lines.append("## 4. Per-Seed Decision Audit Results")
    lines.append("")
    lines.append("| Seed | Twin $a^*$ | Proxy Oracle | $\\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE (abs) | BEE (rel) | Regret | Regret (rel) | BEE Floor |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in per_seed:
        g_t = f"{r['G_T_hat']:.2f}"
        g_p = f"{r['G_P']:.2f}"
        b_abs = f"{r['BEE_abs']:.2f}"
        b_rel = f"{r['BEE_rel']*100:.1f}%" if r["BEE_rel"] is not None else "N/A"
        reg = f"{r['Regret']:.2f}"
        reg_rel = f"{r['Regret_rel']*100:.1f}%" if r["Regret_rel"] is not None else "N/A (<0.5)"
        b_fl = f"{r['BEE_floor_abs']:.2f}"
        lines.append(f"| {r['seed']} | {r['a_star']} | {r['oracle']} | {g_t} | {g_p} | {b_abs} | {b_rel} | {reg} | {reg_rel} | {b_fl} |")
    lines.append("")

    # Action Cost Means
    lines.append("### Mean Action Costs $J$ (veh·h)")
    lines.append("")
    lines.append("#### Twin Evaluation $R_2$ (veh·h)")
    lines.append("| Seed | A0 | A1 | A2 | A3 | A4 | Selected $a^*$ |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in per_seed:
        jt = r["J_T_r2"]
        lines.append(f"| {r['seed']} | {jt['A0']:.2f} | {jt['A1']:.2f} | {jt['A2']:.2f} | {jt['A3']:.2f} | {jt['A4']:.2f} | {r['a_star']} |")
    lines.append("")

    lines.append("#### Proxy Evaluation $M_2$ (veh·h)")
    lines.append("| Seed | A0 | A1 | A2 | A3 | A4 | Oracle ($M_1$) |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in per_seed:
        jp = r["J_P_m2"]
        lines.append(f"| {r['seed']} | {jp['A0']:.2f} | {jp['A1']:.2f} | {jp['A2']:.2f} | {jp['A3']:.2f} | {jp['A4']:.2f} | {r['oracle']} |")
    lines.append("")

    # 5. Pooled Metrics
    lines.append("## 5. Pooled Metrics Summary (N = 8)")
    lines.append("")
    lines.append("| Metric | Mean | Std | Paired t 95% CI | Percentile Bootstrap 95% CI |")
    lines.append("|---|---|---|---|---|")

    display_metrics = [
        ("BEE (signed, veh·h)", "BEE_signed", ".2f"),
        ("BEE (absolute, veh·h)", "BEE_abs", ".2f"),
        ("BEE (relative to $J_P(A0)$)", "BEE_rel", ".1%"),
        ("BEE (unsplit abs, veh·h)", "BEE_abs_unsplit", ".2f"),
        ("BEE (unsplit rel)", "BEE_rel_unsplit", ".1%"),
        ("Regret (veh·h)", "Regret", ".2f"),
        ("Regret (rel, when denom $\\ge 0.5$)", "Regret_rel", ".1%"),
        ("Regret (unsplit, veh·h)", "Regret_unsplit", ".2f"),
        ("Monte Carlo BEE Floor (abs, veh·h)", "BEE_floor_abs", ".2f"),
        ("Monte Carlo BEE Floor (rel)", "BEE_floor_rel", ".1%"),
        ("Top-1 Agreement ($a^* ==$ Oracle)", "top1_agree", ".1%"),
        ("Top-1 Ranking Agreement ($R_2$ vs $M_2$)", "top1_r2_m2_agree", ".1%"),
        ("Spearman Rank Correlation $\\rho$", "spearman_rho", ".3f"),
        ("Kendall Tau $\\tau$", "kendall_tau", ".3f"),
        ("Mean CRN Correlation Across Actions", "mean_crn_corr", ".3f"),
    ]

    for label, key, fmt in display_metrics:
        p = pooled.get(key)
        if not p or p["n"] == 0 or p["mean"] is None:
            lines.append(f"| {label} | N/A | N/A | N/A | N/A |")
            continue
        m_val = format(p["mean"], fmt)
        s_val = format(p["std"], fmt)
        ci_t = f"[{format(p['ci95_t'][0], fmt)}, {format(p['ci95_t'][1], fmt)}]"
        ci_b = f"[{format(p['ci95_boot'][0], fmt)}, {format(p['ci95_boot'][1], fmt)}]"
        lines.append(f"| {label} | {m_val} | {s_val} | {ci_t} | {ci_b} |")
    lines.append("")

    # BEE vs BEE floor
    lines.append("### BEE vs Calibration Floor Comparison")
    lines.append("")
    bee_abs_m = pooled["BEE_abs"]["mean"]
    floor_abs_m = pooled["BEE_floor_abs"]["mean"]
    lines.append(f"- **Twin BEE Absolute**: {bee_abs_m:.2f} veh·h")
    lines.append(f"- **Monte Carlo Floor Absolute**: {floor_abs_m:.2f} veh·h")
    lines.append(f"- **Structural Gap (Twin BEE - Floor)**: {bee_abs_m - floor_abs_m:.2f} veh·h")
    lines.append("")

    # 6. Failures by reason
    lines.append("## 6. Execution Failures by Reason")
    lines.append("")
    if not failures or sum(failures.values()) == 0:
        lines.append("No failures recorded across all two-world and branch runs (0 failures).")
    else:
        for reason, count in failures.items():
            lines.append(f"- **{reason}**: {count}")
    lines.append("")

    # 7. File List
    lines.append("## 7. Artifact and Code Files")
    lines.append("")
    lines.append("- Modified files:")
    lines.append("  - `citypulse/proxy/service.py` (added `--proxy-snapshot-times`)")
    lines.append("  - `citypulse/experiments/run_two_worlds.py` (added `--proxy-snapshot-times`)")
    lines.append("- New implementation files:")
    lines.append("  - `citypulse/branching/audit_engine.py` (Twin, Proxy, and Calibration branch workers)")
    lines.append("  - `citypulse/experiments/decision_audit.py` (audit runner and pipeline)")
    lines.append("  - `tests/test_audit.py` (unit tests for metric calculations, assertion, and thresholds)")
    lines.append("- Results and data files:")
    lines.append("  - `results/audit/rng_check.json` (RNG check verification on seed 4201)")
    lines.append("  - `results/audit/raw.parquet` (raw J values for all 720 branch runs)")
    lines.append("  - `results/audit/metrics.json` (per-seed and pooled summary metrics)")
    lines.append("  - `results/audit/report.md` (this report)")
    lines.append("")
    lines.append("REPORT DONE")

    out_file.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
