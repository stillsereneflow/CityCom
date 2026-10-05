"""Missing-queue experiment runner (docs/oct11-missing-queue-plan.md, revision 2).

compat   Baseline compatibility replay with the modified workers (default keys and queue_trace=True).
pilot    One Twin branch (default H-D, r = 1, A0/A3): blocker reuse, clearance evidence, queue trace.
grid     4 arms x seeds x 6 replications x 5 actions (Twin) + Proxy m = 1..12 branches; raw and
         queue-trace Parquet written before any summary.
analyze  Plan metrics (G_T(A3), G_P(A3), e, Delta_D, duration contrasts, a*, BEE, regret, Top-1,
         Spearman), completeness and failures, the classification order, metrics.json + report.md.
Only seeds whose C and H states exist under ``states/`` (written by the replay worker) can be gridded.
"""
from __future__ import annotations

import argparse
import json
import math
import os

# Binding environment variables (prompt.md line 3)
os.environ.update(CITYPULSE_NET="blite", CITYPULSE_BLITE_REV="5", CITYPULSE_REROUTE="0",
                  PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1")

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from citypulse.branching.audit_engine import (
    ACTIONS, HORIZON_STEPS, T_D,
    build_proxy_resampled_routes, run_proxy_branch_jobs, run_twin_branch_jobs,
)
from citypulse.experiments.decision_audit import AUDIT_DIR, compute_variant_decision_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
MQ_DIR = REPO_ROOT / "results" / "missing_queue"
STATES_DIR, RUNS_DIR, SCRATCH_DIR = MQ_DIR / "states", MQ_DIR / "runs", MQ_DIR / "scratch_dsh"
PROXY_ROU = REPO_ROOT / "scenarios" / "kwuntong" / "blite" / "synth5" / "proxy.rou.xml"
SEEDS = [4301, 4302, 4303, 4304]
ARMS = ("C-P", "C-D", "H-P", "H-D")
# arm -> (reuse_blockers, hyp_clear_time); C = conventional state (blockers inserted at t_d)
ARM_SPEC: Dict[str, Tuple[bool, Optional[float]]] = {
    "C-P": (False, None), "C-D": (False, 5400.0), "H-P": (True, None), "H-D": (True, 5400.0)}
HYP_POS = 755.3
DEFICIT_MAX = 5.0          # Q_P - Q_C <= 5 counts as no deficit
RESTORATION_MIN = 6.0      # Q_H - Q_C >= 6 is material restoration
SUPPORT_MEAN, REFUTATION_MEAN = -1.0, -0.5
LABELS = {"inconclusive_technical": "Inconclusive (technical)", "no_initial_deficit": "No initial deficit",
          "inconclusive_restoration": "Inconclusive (restoration)", "support": "Support",
          "refutation": "Refutation", "partial": "Partial"}

def twin_state_paths(states_dir: Path, seed: int, arm: str) -> Tuple[Path, Path]:
    """C/H state and meta for one seed (file stems fixed by the replay worker)."""
    base, stem = Path(states_dir) / f"seed_{seed}", "H" if arm.startswith("H") else "C"
    return base / f"{stem}_5100.xml.gz", base / f"{stem}_5100.json"

def build_twin_jobs(seeds: Sequence[int], states_dir: Path, arms: Sequence[str] = ARMS,
                    queue_trace: bool = True) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for s in seeds:
        for arm in arms:
            state, meta = twin_state_paths(states_dir, s, arm)
            if not (state.exists() and meta.exists()):
                raise FileNotFoundError(f"missing state/meta for seed {s} arm {arm}: {state} / {meta}")
            reuse, clear = ARM_SPEC[arm]
            jobs += [{"state": str(state), "meta": str(meta), "seed": int(s), "r": r, "action": a,
                      "horizon": HORIZON_STEPS, "variant": arm, "hyp_pos": HYP_POS,
                      "hyp_clear_time": clear, "branch_factor": None, "reuse_blockers": reuse,
                      "queue_trace": queue_trace} for r in range(1, 7) for a in ACTIONS]
    return jobs

def build_proxy_jobs(seeds: Sequence[int], runs_dir: Path, routes_dir: Path,
                     queue_trace: bool = True) -> List[Dict[str, Any]]:
    """Proxy m = 1..6 and calibration m = 7..12, exactly as the base audit builds them."""
    routes_dir = Path(routes_dir)
    routes_dir.mkdir(parents=True, exist_ok=True)
    jobs: List[Dict[str, Any]] = []
    for s in seeds:
        state = Path(runs_dir) / f"seed_{s}" / "proxy" / "proxy_state_5100.xml.gz"
        if not state.exists():
            raise FileNotFoundError(f"missing Proxy state for seed {s}: {state}")
        for m in range(1, 13):
            rt = routes_dir / f"proxy_s{s}_m{m}.rou.xml"
            orig_ids, _ = build_proxy_resampled_routes(PROXY_ROU, rt, seed=s, m=m, t_d=T_D,
                                                       horizon=HORIZON_STEPS)
            jobs += [{"state": str(state), "routes": str(rt), "orig_future_ids": list(orig_ids),
                      "seed": int(s), "m": m, "action": a, "horizon": HORIZON_STEPS,
                      "world": "calibration" if m >= 7 else "proxy", "queue_trace": queue_trace}
                     for a in ACTIONS]
    return jobs

def _split_results(results: Sequence[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Raw rows (one per branch) and long queue-trace rows; nested evidence JSON-encoded."""
    raw_rows, trace_rows = [], []
    for res in results:
        row = dict(res)
        trace = row.pop("queue_trace", None)
        for k in ("blocker_release_0", "blocker_release_1"):
            if isinstance(row.get(k), dict):
                row[k] = json.dumps(row[k], sort_keys=True)
        raw_rows.append(row)
        for snap in trace or []:
            trow = {k: res.get(k) for k in ("world", "arm", "seed", "replication", "action")}
            trow.update({k: (json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v)
                         for k, v in snap.items()})
            trace_rows.append(trow)
    return pd.DataFrame(raw_rows), pd.DataFrame(trace_rows)

def _failure_counts(raw_df: pd.DataFrame) -> List[Dict[str, Any]]:
    if raw_df.empty or "status" not in raw_df:
        return []
    bad = raw_df[raw_df["status"] != "ok"].copy()
    if bad.empty:
        return []
    bad["reason"] = bad["reason"].fillna("") if "reason" in bad else ""
    return [{"world": str(w), "status": str(st), "reason": str(rs), "n": int(len(g)),
             "seeds": sorted({int(x) for x in g["seed"]})}
            for (w, st, rs), g in bad.groupby(["world", "status", "reason"], dropna=False)]

def _incomplete_arms(raw_df: pd.DataFrame, seeds: Sequence[int], arms: Sequence[str]) -> List[str]:
    """A seed-arm needs all 5 actions x 6 replications with status ok (plan, Order/failures)."""
    out, twin = [], raw_df[raw_df["world"] == "twin"]
    for s in seeds:
        for arm in arms:
            ok = twin[(twin["seed"] == s) & (twin["arm"] == arm) & (twin["status"] == "ok")]
            actions = set(ok["action"].dropna()) if len(ok) else set()
            reps = {int(x) for x in ok["replication"].dropna()} if len(ok) else set()
            if len(ok) != 30 or actions != set(ACTIONS) or reps != set(range(1, 7)) or ok["J"].isna().any():
                out.append(f"seed {s} {arm}: {len(ok)}/30 ok rows "
                           f"(actions={sorted(actions)}, reps={sorted(reps)})")
    return out

def cmd_compat(out_path: Path, workers: int = 8, scratch_dir: Path = SCRATCH_DIR) -> Dict[str, Any]:
    """Replay stored baseline branches with the modified workers; J and digest must match exactly."""
    raw_df = pd.read_parquet(AUDIT_DIR / "raw.parquet")
    twin_jobs: List[Dict[str, Any]] = []
    for seed, r in ((4201, 1), (4202, 4)):
        with open(AUDIT_DIR / "runs" / f"seed_{seed}" / "two_world_info.json", encoding="utf-8") as fh:
            info = json.load(fh)
        twin_jobs += [{"state": info["twin_state"], "meta": info["twin_meta"], "seed": seed, "r": r,
                       "action": a, "horizon": HORIZON_STEPS, "variant": "compat", "hyp_pos": HYP_POS,
                       "hyp_clear_time": None, "branch_factor": None, "queue_trace": qt}
                      for a in ACTIONS for qt in (False, True)]
    with open(AUDIT_DIR / "runs" / "seed_4201" / "two_world_info.json", encoding="utf-8") as fh:
        info = json.load(fh)
    routes_dir = Path(scratch_dir) / "compat_routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    rt = routes_dir / "proxy_s4201_m1.rou.xml"
    orig_ids, _ = build_proxy_resampled_routes(PROXY_ROU, rt, seed=4201, m=1, t_d=T_D,
                                               horizon=HORIZON_STEPS)
    proxy_jobs = [{"state": info["proxy_state"], "routes": str(rt),
                   "orig_future_ids": list(orig_ids), "seed": 4201, "m": 1, "action": a,
                   "horizon": HORIZON_STEPS, "world": "proxy", "queue_trace": False}
                  for a in ACTIONS]

    print(f"compat: {len(twin_jobs)} Twin + {len(proxy_jobs)} Proxy branches, workers={workers}")
    results = (run_twin_branch_jobs(twin_jobs, workers=workers)
               + run_proxy_branch_jobs(proxy_jobs, workers=workers))
    rows, mismatches = [], []
    for res in results:
        s, r, a = int(res["seed"]), int(res["replication"]), str(res["action"])
        stored = raw_df[(raw_df["world"] == res["world"]) & (raw_df["seed"] == s)
                        & (raw_df["replication"] == r) & (raw_df["action"] == a)]
        if stored.empty:
            raise ValueError(f"no stored raw.parquet row for {res['world']} seed={s} r={r} {a}")
        stored = stored.iloc[0]
        j_ok = res.get("J") is not None and abs(float(res["J"]) - float(stored["J"])) < 1e-9
        d_ok = res.get("veh_digest") is not None and res["veh_digest"] == str(stored["veh_digest"])
        row = {"world": res["world"], "seed": s, "replication": r, "action": a,
               "phase": "queue_trace" if res.get("queue_trace") else "default",
               "stored_J": float(stored["J"]), "replayed_J": res.get("J"), "J_matches": bool(j_ok),
               "stored_digest": str(stored["veh_digest"]), "replayed_digest": res.get("veh_digest"),
               "digest_matches": bool(d_ok), "status": res.get("status"),
               "n_trace_rows": len(res.get("queue_trace") or []),
               "ok": bool(j_ok and d_ok and res.get("status") == "ok")}
        rows.append(row)
        mismatches += [] if row["ok"] else [row]
    summary = {"passed": not mismatches, "n_checked": len(rows),
               "n_ok": sum(1 for r in rows if r["ok"]), "n_mismatches": len(mismatches),
               "rows": rows, "mismatches": mismatches}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
    print(f"compat: {summary['n_ok']}/{summary['n_checked']} rows match; written {out_path}")
    if mismatches:
        raise RuntimeError(f"COMPAT CHECK FAILED: {len(mismatches)} rows differ; stopping")
    return summary

def cmd_pilot(seed: int, arm: str, replication: int, actions: Sequence[str], states_dir: Path,
              twin_state: Optional[str] = None, twin_meta: Optional[str] = None,
              workers: int = 2) -> List[Dict[str, Any]]:
    """One Twin branch: prints blocker reuse, clearance evidence and the queue trace."""
    reuse, clear = ARM_SPEC[arm]
    state, meta = (Path(twin_state), Path(twin_meta)) if twin_state and twin_meta \
        else twin_state_paths(states_dir, seed, arm)
    jobs = [{"state": str(state), "meta": str(meta), "seed": int(seed), "r": int(replication),
             "action": a, "horizon": HORIZON_STEPS, "variant": arm, "hyp_pos": HYP_POS,
             "hyp_clear_time": clear, "branch_factor": None, "reuse_blockers": reuse,
             "queue_trace": True} for a in actions]
    print(f"pilot: seed={seed} arm={arm} r={replication} actions={list(actions)} "
          f"reuse_blockers={reuse} hyp_clear_time={clear}\n  state={state}\n  meta={meta}")
    results = run_twin_branch_jobs(jobs, workers=max(1, min(int(workers), 8)))
    for res in results:
        print(f"\n[{res['action']}] status={res['status']} J={res.get('J')} "
              f"digest={str(res.get('veh_digest'))[:12]} error={res.get('error')}")
        for i in (0, 1):
            print(f"  blocker hyp_blocker_{i}: edge={res.get('blocker_edge')} "
                  f"lane={res.get(f'blocker_lane_{i}')} pos={res.get(f'blocker_pos_{i}')} "
                  f"t_stop={res.get(f'blocker_t_stop_{i}')}")
        print(f"  clearance: actual_clear_time={res.get('actual_clear_time')} "
              f"release_0={res.get('blocker_release_0')} release_1={res.get('blocker_release_1')}")
        trace = res.get("queue_trace") or []
        print(f"  queue trace ({len(trace)} timestamps): t halted_q halted_up halted_extra "
              f"pending_q Q blocker_halted")
        for snap in trace:
            print(f"    {snap['t']:.0f} {snap['halted_q']} {snap['halted_upstream']} "
                  f"{snap['halted_extra']} {snap['pending_q']} {snap['Q']} {snap['blocker_halted']}")
    return results

def cmd_grid(seeds: Sequence[int], arms: Sequence[str], states_dir: Path, runs_dir: Path,
             out_dir: Path, workers: int = 8, routes_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Run the full grid; raw and queue-trace Parquet are written before any summary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    twin_jobs = build_twin_jobs(seeds, states_dir, arms, queue_trace=True)
    proxy_jobs = build_proxy_jobs(seeds, runs_dir, routes_dir or SCRATCH_DIR / "routes",
                                  queue_trace=True)
    workers = max(1, min(int(workers), 8))          # <= 8 parallel SUMO processes
    print(f"grid: {len(twin_jobs)} Twin branches ({len(arms)} arms x {len(seeds)} seeds x 6 reps x 5 "
          f"actions) + {len(proxy_jobs)} Proxy/calibration branches; workers={workers}")

    results = list(run_twin_branch_jobs(twin_jobs, workers=workers)) \
        + list(run_proxy_branch_jobs(proxy_jobs, workers=workers))
    for res in results:   # the Twin worker reports its arm as `variant`; Proxy/calibration is its world
        res["arm"] = res.get("variant") if res.get("world") == "twin" else res.get("world")
    raw_df, trace_df = _split_results(results)
    raw_df.to_parquet(out_dir / "raw.parquet")
    trace_df.to_parquet(out_dir / "queue_trace.parquet")
    print(f"grid: wrote {len(raw_df)} raw rows to {out_dir / 'raw.parquet'} and {len(trace_df)} trace "
          f"rows to {out_dir / 'queue_trace.parquet'} BEFORE any summary")
    failures, incomplete = _failure_counts(raw_df), _incomplete_arms(raw_df, seeds, arms)
    for f in failures:
        print(f"  failure: world={f['world']} status={f['status']} reason={f['reason']} n={f['n']}")
    for inc in incomplete:
        print(f"  incomplete: {inc}")
    print(f"grid: {int((raw_df['status'] == 'ok').sum())}/{len(raw_df)} branches ok, "
          f"{len(incomplete)} incomplete seed-arms")
    return {"raw": raw_df, "trace": trace_df, "failures": failures, "incomplete_arms": incomplete}

def compute_plan_metrics(arm_metrics: Dict[str, Dict[str, Any]], seeds: Sequence[int]
                         ) -> List[Dict[str, Any]]:
    """Primary and secondary per-seed quantities of the plan (rev 2, Measurements)."""
    by_arm = {arm: {int(r["seed"]): r for r in m["per_seed"]} for arm, m in arm_metrics.items()}
    rows = []
    for s in seeds:
        row: Dict[str, Any] = {"seed": int(s), "G_P_A3": None, "delta_D": None,
                               "duration_contrast_C": None, "duration_contrast_H": None}
        for arm in ARMS:
            r = by_arm.get(arm, {}).get(int(s))
            if r is None:
                row[f"G_T_A3_{arm}"] = row[f"e_{arm}"] = None
                continue
            g_t = float(r["J_T_r2"]["A0"]) - float(r["J_T_r2"]["A3"])
            row["G_P_A3"] = float(r["J_P_m2"]["A0"]) - float(r["J_P_m2"]["A3"])
            row[f"G_T_A3_{arm}"], row[f"e_{arm}"] = g_t, abs(g_t - row["G_P_A3"])
            row[f"a_star_{arm}"], row[f"BEE_signed_{arm}"] = r["a_star"], r["BEE_signed"]
            row[f"Regret_{arm}"], row[f"top1_agree_{arm}"] = r["Regret"], r["top1_agree"]
            row[f"spearman_{arm}"] = r["spearman_rho"]
        if row["e_H-D"] is not None and row["e_C-D"] is not None:
            row["delta_D"] = row["e_H-D"] - row["e_C-D"]
        for prefix in ("C", "H"):
            a, b = row.get(f"G_T_A3_{prefix}-P"), row.get(f"G_T_A3_{prefix}-D")
            if a is not None and b is not None:
                row[f"duration_contrast_{prefix}"] = a - b
        rows.append(row)
    return rows

def classify_outcome(queue_td: Optional[pd.DataFrame], metrics: Dict[str, Any],
                     seeds: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """Preregistered classification order (plan rev 2, Predictions); stop at the first step that applies.

    Reads the queue table (seed, world in {proxy, C, H, live}, Q) and the metrics dict (gates_ok,
    incomplete_arms, per_seed[].delta_D). Returns the label and every step's inputs.
    """
    seeds = list(seeds or metrics.get("seeds") or [])
    if not seeds and queue_td is not None and len(queue_td):
        seeds = sorted(int(s) for s in queue_td["seed"].unique())
    n_required = max(1, math.ceil(0.75 * len(seeds))) if seeds else 1
    q: Dict[int, Dict[str, Optional[float]]] = {}
    for s in seeds:
        sub = queue_td[queue_td["seed"] == s] if queue_td is not None and len(queue_td) else None
        q[int(s)] = {w: (float(sub[sub["world"] == w]["Q"].mean())
                         if sub is not None and len(sub[sub["world"] == w]) else None)
                     for w in ("proxy", "C", "H")}
    deltas = {int(r["seed"]): r.get("delta_D") for r in metrics.get("per_seed", [])}
    missing_q = [int(s) for s in seeds if any(q[int(s)][w] is None for w in ("proxy", "C", "H"))]
    missing_d = [int(s) for s in seeds if deltas.get(int(s)) is None]
    inputs: Dict[str, Any] = {"step1": {
        "gates_ok": metrics.get("gates_ok"), "incomplete_arms": list(metrics.get("incomplete_arms") or []),
        "seeds_missing_queue": missing_q, "seeds_missing_delta_D": missing_d, "n_seeds": len(seeds)}}
    inputs["step1"]["applies"] = (inputs["step1"]["gates_ok"] is not True
                                  or bool(inputs["step1"]["incomplete_arms"]) or not seeds
                                  or bool(missing_q) or bool(missing_d))

    def ret(label: str, step: int) -> Dict[str, Any]:
        return {"label": label, "step": step, "n_required": n_required, "inputs": inputs}

    if inputs["step1"]["applies"]:
        return ret("inconclusive_technical", 1)
    step2 = {int(s): {"Q_P": q[int(s)]["proxy"], "Q_C": q[int(s)]["C"],
                      "diff": q[int(s)]["proxy"] - q[int(s)]["C"]} for s in seeds}
    for v in step2.values():
        v["no_deficit"] = v["diff"] <= DEFICIT_MAX
    n_no_deficit = sum(1 for v in step2.values() if v["no_deficit"])
    inputs["step2"] = {"per_seed": step2, "n_no_deficit": n_no_deficit, "n_required": n_required,
                       "applies": n_no_deficit >= n_required}
    if inputs["step2"]["applies"]:
        return ret("no_initial_deficit", 2)
    step3 = {int(s): {"Q_H": q[int(s)]["H"], "Q_C": q[int(s)]["C"],
                      "diff": q[int(s)]["H"] - q[int(s)]["C"],
                      "proxy_deficit": (q[int(s)]["proxy"] - q[int(s)]["C"]) > DEFICIT_MAX}
             for s in seeds}
    for v in step3.values():
        v["restored"] = v["diff"] >= RESTORATION_MIN
    n_restored = sum(1 for v in step3.values() if v["restored"] and v["proxy_deficit"])
    inputs["step3"] = {"per_seed": step3, "n_restored": n_restored, "n_required": n_required,
                       "applies": n_restored < n_required}
    if inputs["step3"]["applies"]:
        return ret("inconclusive_restoration", 3)
    per_seed_d = {int(s): float(deltas[int(s)]) for s in seeds}
    vals = list(per_seed_d.values())
    n_negative, mean_delta = sum(1 for v in vals if v < 0), float(np.mean(vals))
    inputs["step4"] = {"per_seed_delta_D": per_seed_d, "n_negative": n_negative,
                       "n_required": n_required, "mean_delta_D": mean_delta,
                       "applies": n_negative >= n_required and mean_delta <= SUPPORT_MEAN}
    if inputs["step4"]["applies"]:
        return ret("support", 4)
    inputs["step5"] = {"per_seed_delta_D": per_seed_d, "n_non_negative": len(vals) - n_negative,
                       "n_required": n_required, "mean_delta_D": mean_delta,
                       "applies": (len(vals) - n_negative) >= n_required or mean_delta > REFUTATION_MEAN}
    if inputs["step5"]["applies"]:
        return ret("refutation", 5)
    inputs["step6"] = {"applies": True}
    return ret("partial", 6)

def cmd_analyze(seeds: Sequence[int], out_dir: Path, raw_path: Optional[Path] = None,
                queue_td_path: Optional[Path] = None, gates_path: Optional[Path] = None
                ) -> Dict[str, Any]:
    """Plan metrics, completeness/failures, classification; writes metrics.json and report.md."""
    out_dir = Path(out_dir)
    raw_df = pd.read_parquet(Path(raw_path) if raw_path else out_dir / "raw.parquet")
    queue_td_path = Path(queue_td_path) if queue_td_path else MQ_DIR / "queue_td.parquet"
    gates_path = Path(gates_path) if gates_path else MQ_DIR / "gates.json"
    twin_rows = raw_df[raw_df["world"] == "twin"]
    arm_metrics = {arm: compute_variant_decision_metrics(raw_df, twin_rows[twin_rows["arm"] == arm],
                                                         arm, list(seeds)) for arm in ARMS}
    plan_rows = compute_plan_metrics(arm_metrics, seeds)
    incomplete, failures = _incomplete_arms(raw_df, seeds, ARMS), _failure_counts(raw_df)
    gates_ok: Optional[bool] = None
    if gates_path.exists():
        with open(gates_path, encoding="utf-8") as fh:
            gates_ok = _gates_passed(json.load(fh))
    queue_td = pd.read_parquet(queue_td_path) if queue_td_path.exists() else None
    classification = classify_outcome(queue_td, {
        "gates_ok": gates_ok, "incomplete_arms": incomplete, "per_seed": plan_rows,
        "seeds": list(seeds)})
    bundle = {"seeds": list(seeds), "arms": arm_metrics, "plan": plan_rows,
              "queue": _queue_rows(queue_td, seeds), "queue_td_path": str(queue_td_path),
              "queue_td_available": queue_td is not None, "gates_ok": gates_ok,
              "completeness": {"complete": not incomplete, "incomplete_arms": incomplete},
              "failures": failures, "classification": classification}
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, default=float)
    write_report(bundle, out_dir / "report.md")
    print(f"analyze: {LABELS[classification['label']]} (step {classification['step']}); written "
          f"{out_dir / 'metrics.json'} and {out_dir / 'report.md'}")
    return bundle

def _gates_passed(gates: Any) -> Optional[bool]:
    if not isinstance(gates, dict):
        return None
    for key in ("passed", "all_passed", "ok"):
        if key in gates:
            return bool(gates[key])
    if isinstance(gates.get("gates"), dict) and gates["gates"]:
        return all(bool(v.get("passed", v.get("ok", False))) if isinstance(v, dict) else bool(v)
                   for v in gates["gates"].values())
    return None

def _queue_rows(queue_td: Optional[pd.DataFrame], seeds: Sequence[int]) -> List[Dict[str, Any]]:
    rows = []
    for s in seeds:
        row: Dict[str, Any] = {"seed": int(s)}
        for w in ("proxy", "C", "H", "live"):
            sub = queue_td[(queue_td["seed"] == s) & (queue_td["world"] == w)] \
                if queue_td is not None and len(queue_td) else None
            row[f"Q_{w}"] = float(sub["Q"].mean()) if sub is not None and len(sub) else None
        for a, b, k in (("Q_proxy", "Q_C", "Q_P_minus_Q_C"), ("Q_H", "Q_C", "Q_H_minus_Q_C")):
            row[k] = row[a] - row[b] if row[a] is not None and row[b] is not None else None
        rows.append(row)
    return rows

def _fmt(v: Any, nd: int = 3) -> str:
    return "n/a" if v is None else f"{float(v):.{nd}f}"

def _table(lines: List[str], header: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]

def write_report(bundle: Dict[str, Any], out_file: Path) -> None:
    """Per-seed tables plus the inputs to every classification step."""
    L = ["# Missing-queue test: metrics and classification (plan rev 2)", "",
         f"Seeds: {bundle['seeds']}. Queue table: `{bundle['queue_td_path']}` "
         f"(available: {bundle['queue_td_available']}). Gates passed: {bundle['gates_ok']}.", "",
         "## Per-seed primary and secondary quantities", ""]
    _table(L, ["Seed", "Arm", "G_T(A3) R2", "e", "a*", "BEE signed", "Regret", "Top-1", "Spearman"],
           [[row["seed"], arm, _fmt(row.get(f"G_T_A3_{arm}")), _fmt(row.get(f"e_{arm}")),
             row.get(f"a_star_{arm}", "n/a"), _fmt(row.get(f"BEE_signed_{arm}")),
             _fmt(row.get(f"Regret_{arm}")), _fmt(row.get(f"top1_agree_{arm}"), 0),
             _fmt(row.get(f"spearman_{arm}"))] for row in bundle["plan"] for arm in ARMS])
    L.append("")
    _table(L, ["Seed", "G_P(A3) M2", "Delta_D = e(H-D) - e(C-D)", "Duration contrast C",
               "Duration contrast H"],
           [[row["seed"], _fmt(row.get("G_P_A3")), _fmt(row.get("delta_D")),
             _fmt(row.get("duration_contrast_C")), _fmt(row.get("duration_contrast_H"))]
            for row in bundle["plan"]])
    L += ["", "## Queue inputs (queue_td.parquet)", ""]
    _table(L, ["Seed", "Q_proxy", "Q_C", "Q_H", "Q_live", "Q_P - Q_C", "Q_H - Q_C"],
           [[row["seed"], _fmt(row.get("Q_proxy"), 1), _fmt(row.get("Q_C"), 1),
             _fmt(row.get("Q_H"), 1), _fmt(row.get("Q_live"), 1),
             _fmt(row.get("Q_P_minus_Q_C"), 1), _fmt(row.get("Q_H_minus_Q_C"), 1)]
            for row in bundle["queue"]])

    cls, inputs = bundle["classification"], bundle["classification"]["inputs"]
    L += ["", "## Classification (preregistered order; inputs printed at every step)", ""]
    s1 = inputs["step1"]
    L.append(f"1. Inconclusive (technical): gates_ok={s1['gates_ok']}, incomplete seed-arms="
             f"{s1['incomplete_arms']}, seeds missing queue={s1['seeds_missing_queue']}, seeds missing "
             f"Delta_D={s1['seeds_missing_delta_D']} -> applies={s1['applies']}")
    titles = {2: f"No initial deficit: Q_P - Q_C <= {DEFICIT_MAX:g}",
              3: f"Inconclusive (restoration): Q_H - Q_C >= {RESTORATION_MIN:g} on seeds with a deficit",
              4: f"Support: Delta_D < 0 and mean Delta_D <= {SUPPORT_MEAN:g}",
              5: f"Refutation: Delta_D >= 0, or mean Delta_D > {REFUTATION_MEAN:g}",
              6: "Otherwise partial"}
    for step in (2, 3, 4, 5, 6):
        key = f"step{step}"
        if key not in inputs:
            continue
        L.append(f"{step}. {titles[step]}: n_required={cls['n_required']} "
                 f"-> applies={inputs[key].get('applies', True)}")
        L.append("   inputs: " + json.dumps(inputs[key], sort_keys=True, default=str))
    L += ["", f"**Label: {LABELS[cls['label']]}** (first applicable step: {cls['step']})", "",
          "## Completeness and failures", "",
          f"Complete 5 x 6 Twin grid per seed-arm: {bundle['completeness']['complete']}"]
    L += [f"- incomplete: {inc}" for inc in bundle["completeness"]["incomplete_arms"]]
    L += [f"- world={f['world']} status={f['status']} reason={f['reason']} n={f['n']} seeds={f['seeds']}"
          for f in bundle["failures"]] or ["- no branch failures"]
    out_file.write_text("\n".join(L) + "\n", encoding="utf-8")

def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Missing-queue experiment runner (plan rev 2)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compat", help="baseline compatibility replay check")
    c.add_argument("--workers", type=int, default=8)
    c.add_argument("--out", default=str(MQ_DIR / "compat_check.json"))
    p = sub.add_parser("pilot", help="one Twin branch: reuse, clearance, queue trace")
    p.add_argument("--seed", type=int, default=4301)
    p.add_argument("--arm", default="H-D", choices=list(ARMS))
    p.add_argument("--replication", type=int, default=1)
    p.add_argument("--actions", nargs="+", default=["A0", "A3"])
    p.add_argument("--states-dir", default=str(STATES_DIR))
    p.add_argument("--twin-state", default=None, help="stand-in state (e.g. the seed 4201 C-equivalent)")
    p.add_argument("--twin-meta", default=None)
    p.add_argument("--workers", type=int, default=2)
    g = sub.add_parser("grid", help="full 4-arm grid + Proxy/calibration branches")
    g.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    g.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    g.add_argument("--states-dir", default=str(STATES_DIR))
    g.add_argument("--runs-dir", default=str(RUNS_DIR))
    g.add_argument("--out-dir", default=str(MQ_DIR))
    g.add_argument("--routes-dir", default=None)
    g.add_argument("--workers", type=int, default=8)
    a = sub.add_parser("analyze", help="plan metrics, classification, metrics.json + report.md")
    a.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    a.add_argument("--out-dir", default=str(MQ_DIR))
    a.add_argument("--raw", default=None)
    a.add_argument("--queue-td", default=None)
    a.add_argument("--gates", default=None)
    return ap.parse_args(argv)

def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    if args.cmd == "compat":
        cmd_compat(Path(args.out), workers=args.workers)
    elif args.cmd == "pilot":
        cmd_pilot(args.seed, args.arm, args.replication, args.actions, Path(args.states_dir),
                  twin_state=args.twin_state, twin_meta=args.twin_meta, workers=args.workers)
    elif args.cmd == "grid":
        cmd_grid(args.seeds, args.arms, Path(args.states_dir), Path(args.runs_dir), Path(args.out_dir),
                 workers=args.workers, routes_dir=Path(args.routes_dir) if args.routes_dir else None)
    elif args.cmd == "analyze":
        cmd_analyze(args.seeds, Path(args.out_dir), raw_path=Path(args.raw) if args.raw else None,
                    queue_td_path=Path(args.queue_td) if args.queue_td else None,
                    gates_path=Path(args.gates) if args.gates else None)

if __name__ == "__main__":
    main()
