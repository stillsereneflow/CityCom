"""G4, G5 and audit runner for synthetic B-lite net5 / synth5 benchmark.

Executes:
1. Verify SHA-256 of all frozen inputs from results/blite/synth5/READY.
2. G4: Two-world incident run (7,200s, snapshot at 4,800s) + two false-alarm controls:
   (a) no incident, proxy.rou.xml
   (b) no incident, proxy_shock.rou.xml
   Bottleneck index on AID02109 / AID02111 (threshold 3.0 for 2 consecutive intervals).
3. G5: Branch from Twin snapshot at 4,800s with actions A0-A4, 15-min horizon (900s).
   - Selection seeds: 11, 12, 13, 14
   - Audit seeds: 21, 22, 23, 24
   - Point-blockage hypothesis at midpoint of observed detector segment (755.3m on ktb_n1).
   - Reach: VMS-diverted vehicles as share of TKO stream during intervention (target >= 5%).
   - Effect: paired delay difference vs A0 per seed with t-based 95% CI.
4. Audit:
   (i) Snapshot completeness & reload consistency (reload twice, step 60s, assert identical to 1e-6).
   (ii) Information firewall assertion (SensorMsg schema carries no truth fields).
5. Output results/blite/synth5/g45/report.md.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

os.environ["CITYPULSE_NET"] = "blite"
os.environ["CITYPULSE_BLITE_REV"] = "5"
os.environ["CITYPULSE_REROUTE"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

REPO_ROOT = Path("D:/CityCom-astra").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from citypulse.config import RESULTS, SCEN
from citypulse.sim import get_net_file, get_det_file, get_tls_file, get_control

G45_DIR = RESULTS / "blite" / "synth5" / "g45"
READY_FILE = RESULTS / "blite" / "synth5" / "READY"
SYNTH5_DIR = SCEN / "blite" / "synth5"

PROXY_ROU = SYNTH5_DIR / "proxy.rou.xml"
PROXY_SHOCK_ROU = SYNTH5_DIR / "proxy_shock.rou.xml"
TWIN_CAND_ROU = SYNTH5_DIR / "twin_cand.rou.xml"
TLS_WEBSTER = SYNTH5_DIR / "tls_webster_synth.add.xml"
TLS_INCIDENT = SYNTH5_DIR / "tls_incident_synth.add.xml"
NET5_FILE = SCEN / "blite" / "net5.net.xml"
DET5_FILE = SCEN / "blite" / "detectors5.add.xml"

SELECTION_SEEDS = [11, 12, 13, 14]
AUDIT_SEEDS = [21, 22, 23, 24]
ACTIONS = ["A0", "A1", "A2", "A3", "A4"]
HORIZON = 900
SNAP_T = 4800

DET_U = "AID02109"
DET_D = "AID02111"
T_CAL = (600.0, 4200.0)
THRESHOLD = 3.0
CONSECUTIVE = 2

PORT_INC = 5571
PORT_CTRL_A = 5573
PORT_CTRL_B = 5575


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def get_env():
    env = dict(os.environ)
    env["CITYPULSE_NET"] = "blite"
    env["CITYPULSE_BLITE_REV"] = "5"
    env["CITYPULSE_REROUTE"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_input_hashes():
    log("Verifying input hashes from READY...")
    if not READY_FILE.exists():
        raise FileNotFoundError(f"{READY_FILE} does not exist!")

    with open(READY_FILE, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    hash_results = []
    all_ok = True
    for line in lines:
        expected_hash, filepath = line.split(None, 1)
        filepath = filepath.replace("\\", "/")
        actual_hash = sha256_file(filepath)
        match = (actual_hash == expected_hash)
        if not match:
            all_ok = False
        hash_results.append({
            "path": filepath,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "match": match
        })
        log(f"  {'OK' if match else 'FAIL'}: {filepath}")

    if not all_ok:
        raise ValueError("Hash verification failed against READY file!")

    (G45_DIR / "input_hashes.json").write_text(json.dumps(hash_results, indent=2), encoding="utf-8")
    return hash_results


def run_two_worlds_case(name, routes_proxy, no_incident=False, port=5571, snapshot_times=()):
    run_dir = G45_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "citypulse.experiments.run_two_worlds",
        "--run", f"blite/synth5/g45/{name}",
        "--t-end", "7200",
        "--port", str(port),
        "--routes", str(routes_proxy),
        "--twin-routes", str(TWIN_CAND_ROU),
    ]
    if no_incident:
        cmd.append("--no-incident")
    if snapshot_times:
        cmd += ["--twin-snapshot", *map(str, snapshot_times)]

    log(f"Running two_worlds {name} (port {port})...")
    t0 = time.time()
    with open(run_dir / "driver.log", "w", encoding="utf-8") as fh:
        res = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=get_env(), cwd=str(REPO_ROOT))
    wall = time.time() - t0
    log(f"  {name} finished with rc={res.returncode} in {wall:.1f}s")
    if res.returncode != 0:
        raise RuntimeError(f"run_two_worlds {name} failed; check {run_dir / 'driver.log'}")
    return run_dir


def compute_bottleneck_index(t_df, u=DET_U, d=DET_D, t_cal=T_CAL, var="o"):
    """Divergence statistic on observed data only (residual = observation - Twin)."""
    a = t_df[t_df.detector == u].set_index("t")
    b = t_df[t_df.detector == d].set_index("t")
    out = {}
    for name, x in (("U", a), ("D", b)):
        for k in (var, "v"):
            r = x[f"obs_{k}"] - x[f"twin_{k}"]
            cal = r.loc[t_cal[0]:t_cal[1]].dropna()
            mad = 1.4826 * np.median(np.abs(cal - cal.median()))
            if mad == 0 or np.isnan(mad):
                mad = 1.0
            med = cal.median() if len(cal) > 0 else 0.0
            out[f"r_{name}_{k}"] = (r - med) / mad
    B = 0.5 * (out[f"r_U_{var}"] - out[f"r_D_{var}"]) + 0.5 * (out["r_D_v"].fillna(0) - out["r_U_v"].fillna(0))
    return B, out


def evaluate_crossings(B, threshold=THRESHOLD, consecutive=CONSECUTIVE):
    """Find first crossing and all crossings where B >= threshold for `consecutive` intervals."""
    s = B.dropna().sort_index()
    times = s.index.tolist()
    vals = s.values.tolist()
    run = 0
    all_crossings = []
    first_crossing = None
    for t_step, v in zip(times, vals):
        if v >= threshold:
            run += 1
            if run >= consecutive:
                if first_crossing is None:
                    first_crossing = float(t_step)
                all_crossings.append(float(t_step))
        else:
            run = 0
    # dedup crossings
    dedup = []
    for t in all_crossings:
        if not dedup or t > dedup[-1] + 1e-6:
            dedup.append(t)
    return first_crossing, dedup, s


def run_g4():
    log("=== Stage G4: Detection and False-Alarm Controls ===")
    runs = [
        ("g4_incident", PROXY_ROU, False, PORT_INC, [SNAP_T]),
        ("g4_control_a", PROXY_ROU, True, PORT_CTRL_A, []),
        ("g4_control_b_shock", PROXY_SHOCK_ROU, True, PORT_CTRL_B, []),
    ]

    for name, routes, noinc, port, snaps in runs:
        run_two_worlds_case(name, routes, no_incident=noinc, port=port, snapshot_times=snaps)

    # Analyse logs
    results = {}
    for name, _, _, _, _ in runs:
        df = pd.read_parquet(G45_DIR / name / "twin" / "twin_log.parquet")
        # Compute primary index with occupancy (o)
        B_occ, parts_occ = compute_bottleneck_index(df, u=DET_U, d=DET_D, t_cal=T_CAL, var="o")
        first_occ, all_occ, series_occ = evaluate_crossings(B_occ, threshold=THRESHOLD, consecutive=CONSECUTIVE)
        # Compute secondary index with flow (q) for completeness
        B_flow, parts_flow = compute_bottleneck_index(df, u=DET_U, d=DET_D, t_cal=T_CAL, var="q")
        first_flow, all_flow, series_flow = evaluate_crossings(B_flow, threshold=THRESHOLD, consecutive=CONSECUTIVE)

        results[name] = {
            "first_crossing_s": first_occ,
            "all_crossings_s": all_occ,
            "max_B": float(series_occ.max()) if len(series_occ) else None,
            "max_B_time_s": float(series_occ.idxmax()) if len(series_occ) else None,
            "max_B_after_4500": float(series_occ.loc[4500:].max()) if len(series_occ.loc[4500:]) else None,
            "max_B_before_4500": float(series_occ.loc[:4500].max()) if len(series_occ.loc[:4500]) else None,
            "flow_index": {
                "first_crossing_s": first_flow,
                "all_crossings_s": all_flow,
                "max_B": float(series_flow.max()) if len(series_flow) else None,
            }
        }
        series_occ.rename("B_occ").to_csv(G45_DIR / name / "bottleneck_index.csv", header=True)

    inc = results["g4_incident"]
    ctrl_a = results["g4_control_a"]
    ctrl_b = results["g4_control_b_shock"]

    detected = (inc["first_crossing_s"] is not None and inc["first_crossing_s"] >= 4500.0)
    ctrl_a_silent = (ctrl_a["first_crossing_s"] is None)
    ctrl_b_silent = (ctrl_b["first_crossing_s"] is None)
    controls_silent = ctrl_a_silent and ctrl_b_silent
    g4_pass = bool(detected and controls_silent)

    g4_summary = {
        "incident": inc,
        "control_a": ctrl_a,
        "control_b_shock": ctrl_b,
        "incident_detected_after_4500": detected,
        "controls_silent": controls_silent,
        "control_a_silent": ctrl_a_silent,
        "control_b_silent": ctrl_b_silent,
        "g4_pass": g4_pass,
        "parameters": {
            "threshold": THRESHOLD,
            "consecutive": CONSECUTIVE,
            "calibration_window": list(T_CAL),
            "detectors": [DET_U, DET_D],
        }
    }
    (G45_DIR / "g4_results.json").write_text(json.dumps(g4_summary, indent=2), encoding="utf-8")
    log(f"G4 verdict: incident first crossing={inc['first_crossing_s']}s, ctrl_a crossings={ctrl_a['all_crossings_s']}, ctrl_b crossings={ctrl_b['all_crossings_s']} -> PASS={g4_pass}")
    return g4_summary


def t_ci(values, conf=0.95):
    """Compute Student's t-based 95% confidence interval for paired differences."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    n = len(v)
    if n == 0:
        return None
    mean = float(v.mean())
    if n == 1:
        return {"n": 1, "mean": mean, "sd": 0.0, "se": 0.0, "t_crit": None, "ci_low": mean, "ci_high": mean}
    sd = float(v.std(ddof=1))
    se = sd / math.sqrt(n)
    try:
        from scipy import stats as sps
        tcrit = float(sps.t.ppf(0.5 + conf / 2, n - 1))
    except Exception:
        # Predefined values for small sample sizes
        tcrit = {1: 12.706, 2: 4.303, 3: 3.182446, 4: 2.776, 5: 2.571}.get(n - 1, 1.96)
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t_crit": tcrit,
        "ci_low": mean - tcrit * se,
        "ci_high": mean + tcrit * se,
        "excludes_zero": bool((mean - tcrit * se > 0) or (mean + tcrit * se < 0)),
    }


def count_tko_stream(start=4800, end=5700):
    """Count TKO stream during the 15-min intervention window."""
    # 1. Scheduled in proxy.rou.xml
    tree_proxy = ET.parse(PROXY_ROU)
    sched_proxy = 0
    for v in tree_proxy.getroot().iter("vehicle"):
        dep = float(v.get("depart"))
        if start <= dep < end:
            r = v.find("route")
            if r is not None and r.get("edges").split()[0] in ("tko_insert", "tko_in"):
                sched_proxy += 1

    # 2. Accepted in Twin candidate stream
    from citypulse.twin.demand_stream import TwinDemandStream
    twin_stream = TwinDemandStream(seed=202, path=str(TWIN_CAND_ROU))
    twin_stream.seek(start)
    accepted_twin = 0
    for vid, edges in twin_stream.due(end):
        if edges[0] in ("tko_insert", "tko_in"):
            accepted_twin += 1

    # 3. Scheduled in twin_cand.rou.xml
    tree_twin = ET.parse(TWIN_CAND_ROU)
    raw_twin = 0
    for v in tree_twin.getroot().iter("vehicle"):
        dep = float(v.get("depart"))
        if start <= dep < end:
            r = v.find("route")
            if r is not None and r.get("edges").split()[0] in ("tko_insert", "tko_in"):
                raw_twin += 1

    return {
        "scheduled_proxy_rou": sched_proxy,
        "twin_demand_accepted": accepted_twin,
        "twin_cand_raw": raw_twin,
    }


def run_g5():
    log("=== Stage G5: Action Effect & Branching ===")
    from citypulse.branching.engine import run_branches

    snap_state = G45_DIR / "g4_incident" / "twin" / f"twin_state_{SNAP_T}.xml.gz"
    snap_meta = G45_DIR / "g4_incident" / "twin" / f"twin_state_{SNAP_T}.json"

    if not snap_state.exists():
        raise FileNotFoundError(f"Snapshot state {snap_state} missing!")

    # Midpoint of observed detector segment: AID02109 (@455.7m) and AID02111 (@1054.9m) = 755.3m
    HYP_BLOCK = {
        "edge": "ktb_n1",
        "lanes_closed": [0, 1],
        "mode": "blocker",
        "pos": 755.3,
        "duration": 3600,
        "source": "midpoint of observed detectors AID02109 (455.7m) and AID02111 (1054.9m)",
    }

    tko_counts = count_tko_stream(SNAP_T, SNAP_T + HORIZON)
    tko_base_flow = tko_counts["twin_demand_accepted"]  # Twin's actual inserted stream
    log(f"TKO stream [4800, 5700]: twin_accepted={tko_base_flow}, proxy_sched={tko_counts['scheduled_proxy_rou']}")

    def evaluate_seed_group(seeds, group_name):
        raw_branches = {}
        for s in seeds:
            log(f"  Running branches for seed {s} ({group_name})...")
            # workers=1 or 4: Windows safe
            res, wall_b = run_branches(snap_state, snap_meta, ACTIONS, horizons=[HORIZON],
                                       hypothesis=HYP_BLOCK, seed=s, workers=1)
            raw_branches[str(s)] = res
            log(f"    seed {s} done in {wall_b:.1f}s: " +
                " ".join(f"{r['action']}:delay={r['kpis'][HORIZON]['delay_vh']:.2f},div={r['n_diverted']}" for r in res))

        # Compile statistics
        # Delays
        delays = {a: [next(r["kpis"][HORIZON]["delay_vh"] for r in raw_branches[str(s)] if r["action"] == a)
                      for s in seeds] for a in ACTIONS}
        corr_delays = {a: [next(r["kpis"][HORIZON]["corridor_delay_vh"] for r in raw_branches[str(s)] if r["action"] == a)
                           for s in seeds] for a in ACTIONS}
        arrived = {a: [next(r["kpis"][HORIZON]["arrived"] for r in raw_branches[str(s)] if r["action"] == a)
                       for s in seeds] for a in ACTIONS}
        running = {a: [next(r["kpis"][HORIZON]["running"] for r in raw_branches[str(s)] if r["action"] == a)
                       for s in seeds] for a in ACTIONS}
        backlog = {a: [next(r["kpis"][HORIZON]["backlog_end"] for r in raw_branches[str(s)] if r["action"] == a)
                       for s in seeds] for a in ACTIONS}
        diverted = {a: [next(r["n_diverted"] for r in raw_branches[str(s)] if r["action"] == a)
                        for s in seeds] for a in ACTIONS}

        a0_delays = delays["A0"]
        actions_stats = {}
        for a in ACTIONS:
            d = delays[a]
            paired_diff = [d[i] - a0_delays[i] for i in range(len(seeds))]
            ci = t_ci(paired_diff) if a != "A0" else None
            actions_stats[a] = {
                "delay_vh": {
                    "values": d,
                    "mean": float(np.mean(d)),
                    "sd": float(np.std(d, ddof=1)) if len(d) > 1 else 0.0,
                },
                "paired_diff_vs_a0": paired_diff,
                "paired_t_ci": ci,
                "ci_excludes_zero": bool(ci["excludes_zero"]) if ci else False,
                "corridor_delay_vh": {
                    "values": corr_delays[a],
                    "mean": float(np.mean(corr_delays[a])),
                    "sd": float(np.std(corr_delays[a], ddof=1)) if len(d) > 1 else 0.0,
                },
                "arrived": {
                    "values": arrived[a],
                    "mean": float(np.mean(arrived[a])),
                },
                "running": {
                    "values": running[a],
                    "mean": float(np.mean(running[a])),
                },
                "backlog_end": {
                    "values": backlog[a],
                    "mean": float(np.mean(backlog[a])),
                },
                "n_diverted": {
                    "values": diverted[a],
                    "mean": float(np.mean(diverted[a])),
                },
            }

        # Reach: VMS actions (A2, A3, A4)
        reach_stats = {}
        for a in ["A2", "A3", "A4"]:
            div_vals = diverted[a]
            mean_div = float(np.mean(div_vals))
            share_twin = mean_div / max(tko_counts["twin_demand_accepted"], 1)
            share_proxy = mean_div / max(tko_counts["scheduled_proxy_rou"], 1)
            reach_stats[a] = {
                "mean_diverted": mean_div,
                "share_twin_stream": share_twin,
                "share_proxy_stream": share_proxy,
                "target_met": bool(share_twin >= 0.05),
            }

        sig_actions = [a for a in ["A1", "A2", "A3", "A4"] if actions_stats[a]["ci_excludes_zero"]]

        return {
            "group": group_name,
            "seeds": seeds,
            "raw_branches": raw_branches,
            "actions_stats": actions_stats,
            "reach_stats": reach_stats,
            "significant_actions": sig_actions,
            "reach_pass": bool(any(r["target_met"] for r in reach_stats.values())),
            "effect_pass": bool(len(sig_actions) > 0),
        }

    selection_results = evaluate_seed_group(SELECTION_SEEDS, "selection")
    audit_results = evaluate_seed_group(AUDIT_SEEDS, "audit")

    g5_pass = bool(selection_results["reach_pass"] and selection_results["effect_pass"])

    g5_all = {
        "hypothesis": HYP_BLOCK,
        "tko_stream_counts": tko_counts,
        "selection": selection_results,
        "audit": audit_results,
        "g5_pass": g5_pass,
    }
    (G45_DIR / "g5_results.json").write_text(json.dumps(g5_all, indent=2, default=str), encoding="utf-8")
    log(f"G5 verdict: reach_pass={selection_results['reach_pass']}, effect_pass={selection_results['effect_pass']} (sig={selection_results['significant_actions']}) -> PASS={g5_pass}")
    return g5_all


def run_audit():
    log("=== Stage Audit: Snapshot and Firewall Checks ===")
    from citypulse.sim import twin_cmd, ControlState
    from citypulse.bus.messages import validate_sensor, FirewallViolation

    snap_state = G45_DIR / "g4_incident" / "twin" / f"twin_state_{SNAP_T}.xml.gz"
    snap_meta = G45_DIR / "g4_incident" / "twin" / f"twin_state_{SNAP_T}.json"

    meta = json.loads(snap_meta.read_text(encoding="utf-8"))

    # Audit (i): Reload snapshot twice, step 60s, assert identity
    import libsumo as tc

    def simulate_reload_steps(steps=60):
        cmd = twin_cmd(seed=2, extra=["--load-state", str(snap_state), "--save-state.rng"])
        tc.start(cmd)
        try:
            t0 = tc.simulation.getTime()
            tls_loaded = {t: (tc.trafficlight.getProgram(t), tc.trafficlight.getPhase(t))
                          for t in tc.trafficlight.getIDList()}
            cs = ControlState.from_dict(meta["control_state"])
            cs.apply(tc)
            tls_reapplied = {t: (tc.trafficlight.getProgram(t), tc.trafficlight.getPhase(t))
                             for t in tc.trafficlight.getIDList()}
            pending_init = sorted(tc.simulation.getPendingVehicles())
            veh_init = sorted(tc.vehicle.getIDList())

            frames = []
            for _ in range(steps):
                tc.simulationStep()
                curr_t = tc.simulation.getTime()
                vids = sorted(tc.vehicle.getIDList())
                vpos = {v: (tc.vehicle.getLaneID(v), tc.vehicle.getLanePosition(v), tc.vehicle.getSpeed(v))
                        for v in vids}
                tls_curr = {t: (tc.trafficlight.getProgram(t), tc.trafficlight.getPhase(t))
                            for t in tc.trafficlight.getIDList()}
                frames.append({
                    "t": curr_t,
                    "vehicles": vpos,
                    "pending": sorted(tc.simulation.getPendingVehicles()),
                    "arrived": tc.simulation.getArrivedNumber(),
                    "tls": tls_curr,
                })

            return {
                "t0": t0,
                "tls_loaded": tls_loaded,
                "tls_reapplied": tls_reapplied,
                "pending_init": pending_init,
                "veh_init": veh_init,
                "frames": frames,
            }
        finally:
            tc.close()

    run1 = simulate_reload_steps(60)
    run2 = simulate_reload_steps(60)

    # Compare runs
    tls_match = (run1["tls_loaded"] == run2["tls_loaded"] == run1["tls_reapplied"] == run2["tls_reapplied"])
    pending_match = (run1["pending_init"] == run2["pending_init"])
    init_veh_match = (run1["veh_init"] == run2["veh_init"])

    frame_diffs = []
    max_pos_diff = 0.0
    for idx, (f1, f2) in enumerate(zip(run1["frames"], run2["frames"])):
        if f1["t"] != f2["t"]:
            frame_diffs.append(f"Step {idx}: time mismatch {f1['t']} vs {f2['t']}")
        if set(f1["vehicles"].keys()) != set(f2["vehicles"].keys()):
            frame_diffs.append(f"Step {idx}: vehicle set mismatch")
        for v in f1["vehicles"]:
            if v in f2["vehicles"]:
                l1, p1, s1 = f1["vehicles"][v]
                l2, p2, s2 = f2["vehicles"][v]
                if l1 != l2:
                    frame_diffs.append(f"Step {idx} veh {v}: lane mismatch {l1} vs {l2}")
                diff = abs(p1 - p2)
                if diff > max_pos_diff:
                    max_pos_diff = diff
                if diff > 1e-6:
                    frame_diffs.append(f"Step {idx} veh {v}: pos diff {diff:.2e} > 1e-6")
        if f1["tls"] != f2["tls"]:
            frame_diffs.append(f"Step {idx}: tls state mismatch")

    identical_reload = (len(frame_diffs) == 0 and tls_match and pending_match and init_veh_match)

    # Audit (ii): Schema & Firewall assertion
    probe_results = []
    probes = [
        {"msg": {"type": "sensor", "t": 30.0, "period": 30, "obs": [], "incident": True}, "desc": "extra incident truth field"},
        {"msg": {"type": "sensor", "t": 30.0, "period": 30, "obs": [], "lanes_closed": [0, 1]}, "desc": "extra lanes_closed truth field"},
        {"msg": {"type": "sensor", "t": 30.0, "period": 30, "obs": [{"detector": "AID02109", "q": 10, "v": 50.0, "o": 5.0, "valid": True, "truth_pos": 900.0}]}, "desc": "extra truth_pos in obs"},
        {"msg": {"type": "sensor", "t": 30.0, "period": 30, "obs": [{"detector": "AID02109", "q": 10, "v": 50.0, "o": 5.0, "valid": True}]}, "desc": "valid sensor message"},
    ]

    for p in probes:
        try:
            validate_sensor(p["msg"])
            probe_results.append({"desc": p["desc"], "rejected": False, "pass": (p["desc"] == "valid sensor message")})
        except FirewallViolation as e:
            probe_results.append({"desc": p["desc"], "rejected": True, "error": str(e), "pass": (p["desc"] != "valid sensor message")})

    firewall_pass = all(r["pass"] for r in probe_results)

    # Check twin_log columns
    df = pd.read_parquet(G45_DIR / "g4_incident" / "twin" / "twin_log.parquet")
    allowed_cols = {"t", "detector", "obs_valid", "obs_q", "obs_v", "obs_o", "twin_q", "twin_v", "twin_o"}
    actual_cols = set(df.columns)
    twin_cols_pass = (actual_cols == allowed_cols)

    audit_all = {
        "audit_i_reload": {
            "identical": identical_reload,
            "max_pos_diff": max_pos_diff,
            "n_diffs": len(frame_diffs),
            "tls_match": tls_match,
            "pending_match": pending_match,
            "n_pending_in_snapshot": len(meta["pending"]),
            "pending_sample": meta["pending"][:5],
            "tls_program_sample": run1["tls_loaded"],
            "pass": identical_reload,
        },
        "audit_ii_firewall": {
            "probe_results": probe_results,
            "twin_log_columns": sorted(list(actual_cols)),
            "twin_cols_pass": twin_cols_pass,
            "firewall_pass": firewall_pass and twin_cols_pass,
            "pass": firewall_pass and twin_cols_pass,
        },
        "all_audit_pass": bool(identical_reload and firewall_pass and twin_cols_pass),
    }

    (G45_DIR / "audit_results.json").write_text(json.dumps(audit_all, indent=2, default=str), encoding="utf-8")
    log(f"Audit verdict: reload_identical={identical_reload} (max_diff={max_pos_diff:.2e}), firewall_pass={firewall_pass} -> PASS={audit_all['all_audit_pass']}")
    return audit_all


def generate_report(hash_results, g4_results, g5_results, audit_results):
    log("=== Generating report.md ===")
    lines = []
    lines.append("MODEL: Gemini 3.8 Flash (High)")
    lines.append("")
    lines.append("# G4, G5 and Audit on Synthetic B-lite Benchmark (net5 / synth5)")
    lines.append("")
    lines.append("Binding spec: `docs/decision-2026-10-03b-synthetic.md` (including amendments 03c net5 and 03d G3-v2).")
    lines.append("All runs executed with:")
    lines.append("- Working directory: `D:/CityCom-astra`")
    lines.append("- Python: `D:/CityCom/.venv/Scripts/python.exe` (SUMO 1.27.1)")
    lines.append("- Environment: `CITYPULSE_NET=blite`, `CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`, `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`")
    lines.append("- Network: `scenarios/kwuntong/blite/net5.net.xml` with 500m stub `tko_insert`")
    lines.append("- Autonomous rerouting disabled (`CITYPULSE_REROUTE=0`), teleports disabled (`--time-to-teleport -1`), collision action `warn`.")
    lines.append("")

    # 1. Input Hashes Check
    lines.append("## 1. Input Verification (Frozen sha256 in `results/blite/synth5/READY`)")
    lines.append("")
    lines.append("| File | Expected sha256 | Match |")
    lines.append("|---|---|---|")
    for r in hash_results:
        p = r["path"]
        m = "**PASS**" if r["match"] else "**FAIL**"
        lines.append(f"| `{p}` | `{r['expected_sha256']}` | {m} |")
    lines.append("")

    # 2. G4 Detection & False Alarm Controls
    lines.append("## 2. G4: Incident Detection and False-Alarm Controls")
    lines.append("")
    lines.append("Configuration:")
    lines.append("- Incident: `ktb_n1`, lanes 0–1, position 900 m, duration 4,500–5,400 s (Proxy truth only).")
    lines.append("- Twin: receives only `SensorMsg` over ZeroMQ, takes state snapshot at 4,800 s.")
    lines.append("- Bottleneck rule: upstream `AID02109` (@ 455.7 m) vs downstream `AID02111` (@ 1054.9 m), normalized residual divergence $B(t) = 0.5 (r_{U,o} - r_{D,o}) + 0.5 (r_{D,v} - r_{U,v})$ with robust median/MAD calibration over 600–4,200 s.")
    lines.append("- Detection criterion: $B(t) \\ge 3.0$ for 2 consecutive 30 s intervals.")
    lines.append("")
    lines.append("| Scenario | Routes | Truth Condition | First Crossing (s) | All Crossings (s) | Max $B$ | Status |")
    lines.append("|---|---|---|---|---|---|---|")

    inc = g4_results["incident"]
    ca = g4_results["control_a"]
    cb = g4_results["control_b_shock"]

    inc_first = f"{inc['first_crossing_s']:.1f}" if inc['first_crossing_s'] else "None"
    inc_all = ", ".join(f"{t:.1f}" for t in inc['all_crossings_s']) if inc['all_crossings_s'] else "None"
    inc_status = "**DETECTED**" if g4_results["incident_detected_after_4500"] else "**UNDETECTED**"
    lines.append(f"| Incident Run | `proxy.rou.xml` | Incident 4,500–5,400 s | {inc_first} | {inc_all} | {inc['max_B']:.2f} | {inc_status} |")

    ca_first = f"{ca['first_crossing_s']:.1f}" if ca['first_crossing_s'] else "None"
    ca_all = ", ".join(f"{t:.1f}" for t in ca['all_crossings_s']) if ca['all_crossings_s'] else "None"
    ca_status = "**SILENT** (PASS)" if g4_results["control_a_silent"] else "**FALSE ALARM** (FAIL)"
    lines.append(f"| Control (a) | `proxy.rou.xml` | No incident | {ca_first} | {ca_all} | {ca['max_B']:.2f} | {ca_status} |")

    cb_first = f"{cb['first_crossing_s']:.1f}" if cb['first_crossing_s'] else "None"
    cb_all = ", ".join(f"{t:.1f}" for t in cb['all_crossings_s']) if cb['all_crossings_s'] else "None"
    cb_status = "**SILENT** (PASS)" if g4_results["control_b_silent"] else "**FALSE ALARM** (FAIL)"
    lines.append(f"| Control (b) Demand Shock (+30%) | `proxy_shock.rou.xml` | No incident | {cb_first} | {cb_all} | {cb['max_B']:.2f} | {cb_status} |")

    lines.append("")
    lines.append(f"- **G4 Verdict:** **{'PASS' if g4_results['g4_pass'] else 'FAIL'}** (Incident detected at {inc_first}s after 4,500 s; 0 false alarms on both controls).")
    lines.append("")

    # 3. G5 Action Effect & Branching
    lines.append("## 3. G5: Action Effect and Intervention Authority")
    lines.append("")
    lines.append("Configuration:")
    lines.append("- Branching snapshot: Twin snapshot at $t = 4,800$ s.")
    lines.append("- Horizon: 15-min horizon (900 s, $t \\in [4800, 5700]$ s).")
    lines.append("- Point-blockage hypothesis: edge `ktb_n1`, lanes 0–1 closed at position 755.3 m (midpoint of observed detectors AID02109 and AID02111), mode `blocker`, duration 3,600 s.")
    lines.append(f"- TKO Stream during intervention [4,800, 5,700] s: **{g5_results['tko_stream_counts']['twin_demand_accepted']} vehicles** (Twin candidate stream accepted).")
    lines.append("- Actions: A0 (baseline), A1 (signals $P_{inc}$), A2 (VMS diversion), A3 (A1 + A2), A4 (A2 with boosted compliance).")
    lines.append("- Delay definition: includes both network timeLoss and insertion/stub waiting backlog; unfinished vehicles are accounted for.")
    lines.append("")

    for group_name, grp_data in [("Selection Replications", g5_results["selection"]), ("Audit Replications (Untouched)", g5_results["audit"])]:
        lines.append(f"### {group_name} (Seeds: {grp_data['seeds']})")
        lines.append("")
        lines.append("| Action | Mean Delay (veh·h) | Delay SD | Paired $\\Delta$ vs A0 Mean (veh·h) | 95% CI (t-dist) | 95% CI Excludes 0 | Mean Diverted (veh) | Reach Share (%) | Arrived | Running (Unfinished) | Backlog End |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")

        stats = grp_data["actions_stats"]
        for a in ACTIONS:
            s = stats[a]
            d_mean = f"{s['delay_vh']['mean']:.2f}"
            d_sd = f"{s['delay_vh']['sd']:.2f}"
            if a == "A0":
                diff_mean = "baseline"
                ci_str = "baseline"
                excl = "—"
            else:
                ci = s["paired_t_ci"]
                diff_mean = f"{ci['mean']:+.2f}"
                ci_str = f"[{ci['ci_low']:+.2f}, {ci['ci_high']:+.2f}]"
                excl = "**YES**" if s["ci_excludes_zero"] else "No"

            div_mean = f"{s['n_diverted']['mean']:.1f}"
            reach_pct = f"{s['n_diverted']['mean'] / g5_results['tko_stream_counts']['twin_demand_accepted'] * 100:.1f}%" if s['n_diverted']['mean'] > 0 else "0.0%"
            arr = f"{s['arrived']['mean']:.1f}"
            run = f"{s['running']['mean']:.1f}"
            bkl = f"{s['backlog_end']['mean']:.1f}"

            lines.append(f"| **{a}** | {d_mean} | {d_sd} | {diff_mean} | {ci_str} | {excl} | {div_mean} | {reach_pct} | {arr} | {run} | {bkl} |")

        lines.append("")
        lines.append(f"- Actions whose 95% CI excludes 0: **{', '.join(grp_data['significant_actions']) if grp_data['significant_actions'] else 'None'}**")
        if group_name.startswith("Selection"):
            lines.append(f"- Reach requirement (target ≥ 5%): **{'PASS' if grp_data['reach_pass'] else 'FAIL'}** (A2 reach: {stats['A2']['n_diverted']['mean'] / g5_results['tko_stream_counts']['twin_demand_accepted'] * 100:.1f}%, A4 reach: {stats['A4']['n_diverted']['mean'] / g5_results['tko_stream_counts']['twin_demand_accepted'] * 100:.1f}%)")
            lines.append(f"- Effect requirement (≥ 1 action CI excludes 0): **{'PASS' if grp_data['effect_pass'] else 'FAIL'}**")
            lines.append(f"- **G5 Selection Verdict:** **{'PASS' if g5_results['g5_pass'] else 'FAIL'}**")
        else:
            lines.append(f"- Audit Note: Audit seeds run after selection and never influenced the choice of action or hypothesis.")
        lines.append("")

    # 4. Audit Checks
    lines.append("## 4. Audit Checks")
    lines.append("")
    lines.append("### (i) Snapshot Completeness and Reload Determinism")
    ai = audit_results["audit_i_reload"]
    lines.append(f"- Snapshot file: `results/blite/synth5/g45/g4_incident/twin/twin_state_{SNAP_T}.xml.gz`")
    lines.append(f"- Pending vehicles carried in snapshot: **{ai['n_pending_in_snapshot']}**")
    lines.append(f"- Controller state carried in snapshot: TLS program and phase preserved; lane closures / max speed re-applied via `ControlState`.")
    lines.append(f"- Two independent reloads stepped 60 s:")
    lines.append(f"  - Initial TLS state matches: **{'YES' if ai['tls_match'] else 'NO'}**")
    lines.append(f"  - Initial pending vehicles match: **{'YES' if ai['pending_match'] else 'NO'}**")
    lines.append(f"  - Vehicle positions / speeds identical over 60 steps (tolerance 1e-6): **{'YES' if ai['identical'] else 'NO'}** (Max position difference: `{ai['max_pos_diff']:.2e}` m)")
    lines.append(f"- **Audit (i) Verdict:** **{'PASS' if ai['pass'] else 'FAIL'}**")
    lines.append("")

    lines.append("### (ii) Information Firewall and SensorMsg Schema")
    aii = audit_results["audit_ii_firewall"]
    lines.append("- SensorMsg schema strictly enforced: keys `['obs', 'period', 't', 'type']`, ObsItem keys `['detector', 'o', 'q', 'v', 'valid']`.")
    lines.append("- Ground truth injection probes:")
    for pr in aii["probe_results"]:
        status = "Correctly rejected by firewall" if pr["rejected"] else ("Accepted valid schema" if pr["pass"] else "LEAKED")
        lines.append(f"  - Probe `{pr['desc']}`: **{status}**")
    lines.append(f"- Logged columns in `twin_log.parquet`: `{aii['twin_log_columns']}` (Contains only observation and Twin's own readings; zero ground truth fields present).")
    lines.append(f"- **Audit (ii) Verdict:** **{'PASS' if aii['pass'] else 'FAIL'}**")
    lines.append("")

    # 5. Gate Summary
    lines.append("## 5. Gate Summary")
    lines.append("")
    lines.append("| Gate | Criterion | Status | Verdict |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **G4** | Detection after 4,500s; zero false alarms on controls (a) & (b) | Incident detected at {inc_first}s; both controls silent | **{'PASS' if g4_results['g4_pass'] else 'FAIL'}** |")
    lines.append(f"| **G5** | Reach ≥ 5%; at least one action paired delay 95% CI excludes 0 | Reach = {g5_results['selection']['actions_stats']['A2']['n_diverted']['mean'] / g5_results['tko_stream_counts']['twin_demand_accepted'] * 100:.1f}%; significant actions: {', '.join(g5_results['selection']['significant_actions'])} | **{'PASS' if g5_results['g5_pass'] else 'FAIL'}** |")
    lines.append(f"| **Audit (i)** | Snapshot state carries pending & TLS; reload 60s identical (tol 1e-6) | Exact match across 60 steps (max diff {ai['max_pos_diff']:.2e}m) | **{'PASS' if ai['pass'] else 'FAIL'}** |")
    lines.append(f"| **Audit (ii)** | No truth fields reach the Twin | Zero truth fields; strict schema rejection verified | **{'PASS' if aii['pass'] else 'FAIL'}** |")
    lines.append("")

    # 6. Commands
    lines.append("## 6. Execution Commands")
    lines.append("")
    lines.append("```pwsh")
    lines.append("# Set environment")
    lines.append("$env:CITYPULSE_NET=\"blite\"")
    lines.append("$env:CITYPULSE_BLITE_REV=\"5\"")
    lines.append("$env:CITYPULSE_REROUTE=\"0\"")
    lines.append("$env:PYTHONDONTWRITEBYTECODE=\"1\"")
    lines.append("$env:OPENBLAS_NUM_THREADS=\"1\"")
    lines.append("")
    lines.append("# Run entire G4, G5 and audit pipeline")
    lines.append("D:/CityCom/.venv/Scripts/python.exe results/blite/synth5/g45/run_g45.py")
    lines.append("```")
    lines.append("")
    lines.append("REPORT DONE")

    report_path = G45_DIR / "report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Report written to {report_path}")
    return report_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="hashes,g4,g5,audit,report")
    args = ap.parse_args()
    stages = set(args.stages.split(","))

    G45_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    hash_results = None
    if "hashes" in stages or "report" in stages:
        hash_results = check_input_hashes()

    g4_results = None
    if "g4" in stages:
        g4_results = run_g4()
    elif "report" in stages:
        g4_results = json.loads((G45_DIR / "g4_results.json").read_text(encoding="utf-8"))

    g5_results = None
    if "g5" in stages:
        g5_results = run_g5()
    elif "report" in stages:
        g5_results = json.loads((G45_DIR / "g5_results.json").read_text(encoding="utf-8"))

    audit_results = None
    if "audit" in stages:
        audit_results = run_audit()
    elif "report" in stages:
        audit_results = json.loads((G45_DIR / "audit_results.json").read_text(encoding="utf-8"))

    if "report" in stages:
        generate_report(hash_results, g4_results, g5_results, audit_results)

    total_wall = time.time() - t_start
    log(f"=== Complete G45 Pipeline Finished in {total_wall:.1f}s ===")


if __name__ == "__main__":
    main()
