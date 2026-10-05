"""Frozen offline decision audit analyzer (docs/oct16-frozen-audit-plan.md).

Reads a collected frozen-audit directory (``raw.parquet``, ``state_history.parquet``, ``rng_check.json``)
and computes exactly the preregistered estimands, per seed and over seeds, with the audit v2 CRN
correction (``results/audit/v2/report.md``); no simulation.

Usage: python -m citypulse.experiments.frozen_audit_analyze analyze --dir results/frozen_audit
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from citypulse.experiments.decision_audit import (
    compute_crn_statistics, kendall_tau, spearman_rho, t_critical_95)

ACTIONS: Tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4")
WORLDS: Tuple[str, ...] = ("twin", "proxy", "calibration")
REPS_BY_WORLD: Dict[str, Tuple[int, ...]] = {
    "twin": (1, 2, 3, 4, 5, 6), "proxy": (1, 2, 3, 4, 5, 6), "calibration": (7, 8, 9, 10, 11, 12)}
SEL_REPS, EVAL_REPS = (1, 2, 3), (4, 5, 6)
CAL_SEL_REPS, CAL_EVAL_REPS = (7, 8, 9), (10, 11, 12)
PRIMARY_BELIEF, SECONDARY_BELIEF = "B", "D300"
CLEAR_TARGET, REGRET_DENOM_MIN = 5400.0, 0.5

# Claim boundary of docs/oct16-frozen-audit-plan.md ("Purpose and claim boundary"), verbatim.
CLAIM_BOUNDARY = (
    "This is a confirmation of a laboratory, scenario-specific result: one corridor, one "
    "incident type, one decision time, the H_G5 hypothesis world. The submission may report "
    "these numbers as such. It may not present them as reliable incident inference, accurate "
    "benefit prediction in general, real-world effectiveness, or event-assimilation superiority")

METRIC_KEYS: Tuple[str, ...] = (
    "G_T_hat", "G_P", "BEE_signed", "BEE_abs", "BEE_rel", "BEE_signed_rel", "BEE_signed_unsplit",
    "BEE_abs_unsplit", "BEE_rel_unsplit", "Regret", "Regret_denom", "Regret_rel", "Regret_unsplit",
    "Regret_denom_unsplit", "Regret_rel_unsplit", "top1_agree", "top1_r2_m2_agree", "spearman_rho",
    "kendall_tau", "BEE_floor_signed", "BEE_floor_abs", "BEE_floor_rel", "G_T_A3", "G_P_A3", "BEE_A3")
FLOOR_KEYS = ("BEE_floor_signed", "BEE_floor_abs", "BEE_floor_rel")
UNSPLIT_KEYS = tuple(k for k in METRIC_KEYS if k.endswith("_unsplit"))


def _finite(v: Any) -> bool:
    if v is None:
        return False
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return not math.isnan(f) and math.isfinite(f)


def load_inputs(directory: Path) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Dict[str, Any]]:
    """Load raw.parquet (required); state_history.parquet and rng_check.json are descriptive."""
    d = Path(directory)
    return (normalize_raw(pd.read_parquet(d / "raw.parquet")),
            pd.read_parquet(d / "state_history.parquet") if (d / "state_history.parquet").exists() else None,
            json.loads((d / "rng_check.json").read_text(encoding="utf-8")) if (d / "rng_check.json").exists() else {})


def normalize_raw(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "belief" not in df.columns:
        df["belief"] = PRIMARY_BELIEF
    df["belief"] = df["belief"].fillna(PRIMARY_BELIEF).astype(str)
    if "status" not in df.columns:
        df["status"] = "ok"
    df["status"] = df["status"].fillna("").astype(str)
    df[["world", "action"]] = df[["world", "action"]].astype(str)
    df[["seed", "replication"]] = df[["seed", "replication"]].astype(int)
    df["J"] = pd.to_numeric(df["J"], errors="coerce")
    return df


def rows_for(df: pd.DataFrame, world: str, belief: Optional[str] = None) -> pd.DataFrame:
    """Rows of one world; the belief label selects Twin rows only (Proxy/Calibration are shared)."""
    sub = df[df["world"] == world]
    return sub[sub["belief"] == belief] if (belief is not None and world == "twin") else sub


def clearance_ok(row: pd.Series) -> Tuple[bool, str]:
    """D300 technical-failure check: both blockers placed and released, clearance at 5,400 s."""
    release_times: List[float] = []
    saw_release = False
    for col in ("blocker_release_0", "blocker_release_1"):
        if col not in row.index or pd.isna(row[col]):
            continue
        ev = row[col]
        if isinstance(ev, str):
            try:
                ev = json.loads(ev)
            except json.JSONDecodeError:
                return False, f"{col} unreadable"
        if not isinstance(ev, dict) or ev.get("released") is not True:
            return False, f"{col} not released"
        saw_release = True
        release_times += [float(ev[k]) for k in ("resumed_at", "checked_at") if _finite(ev.get(k))]
    if "blocker_release_0" in row.index and "blocker_release_1" in row.index and not saw_release:
        return False, "no release evidence"
    clear = row.get("actual_clear_time")
    clear = float(clear) if _finite(clear) else (max(release_times) if release_times else None)
    if clear is None:
        return False, "no clearance time evidence"
    if clear < CLEAR_TARGET - 1e-6:
        return False, f"clearance at {clear} < {CLEAR_TARGET}"
    for col in ("blocker_pos_0", "blocker_pos_1"):
        if col in row.index and not _finite(row[col]):
            return False, f"{col} missing"
    if "blocker_edge" in row.index and not pd.isna(row["blocker_edge"]) and str(row["blocker_edge"]) != "ktb_n1":
        return False, f"blocker_edge {row['blocker_edge']} != ktb_n1"
    return True, "ok"


def validate_world(df: pd.DataFrame, belief: str, world: str, seeds: Sequence[int],
                   require_clearance: bool = False) -> Tuple[Dict[int, Dict[str, Any]], List[int]]:
    """Unique (action, replication) keys, finite J, status ok, complete 5 x N grid per seed."""
    sub = rows_for(df, world, belief)
    want = {(a, r) for a in ACTIONS for r in REPS_BY_WORLD[world]}
    records: Dict[int, Dict[str, Any]] = {}
    complete: List[int] = []
    for s in seeds:
        rec = records[int(s)] = {"complete": False, "n_ok": 0, "reason": None, "notes": []}
        s_rows = sub[sub["seed"] == s]
        if s_rows.empty:
            rec["reason"] = "no rows"
            continue
        dup = s_rows[s_rows.duplicated(["action", "replication"], keep=False)]
        if not dup.empty:
            # the plan requires unique (action, replication) keys: any duplicate excludes the seed
            conflicting = dup.groupby(["action", "replication"])["J"].nunique(dropna=False).max() > 1
            rec["reason"] = ("duplicate (action, replication) keys with conflicting J" if conflicting
                             else "duplicate (action, replication) keys")
            continue
        ok = s_rows[(s_rows["status"] == "ok") & np.isfinite(s_rows["J"])]
        if require_clearance:
            failed = [i for i, r in ok.iterrows() if not clearance_ok(r)[0]]
            if failed:
                why = sorted({clearance_ok(ok.loc[i])[1] for i in failed})
                rec["reason"] = f"technical failure: clearance evidence ({len(failed)} rows: {', '.join(why)})"
                continue
        rec["n_ok"] = int(len(ok))
        missing = want - set(zip(ok["action"], ok["replication"]))
        if missing:
            rec["reason"] = f"incomplete {world} grid: {len(ok)}/{len(want)} ok rows ({len(missing)} cells missing)"
            continue
        rec["complete"] = True
        complete.append(int(s))
    return records, complete


def pivot_ok(df: pd.DataFrame, belief: str, world: str, seed: int) -> pd.DataFrame:
    sub = rows_for(df, world, belief)
    sub = sub[(sub["seed"] == seed) & (sub["status"] == "ok") & np.isfinite(sub["J"])]
    return sub.drop_duplicates(["action", "replication"], keep="first").pivot(
        index="replication", columns="action", values="J").reindex(
        index=list(REPS_BY_WORLD[world]), columns=list(ACTIONS))


def seed_metrics(tw: pd.DataFrame, px: pd.DataFrame, cal: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """Estimands 1-5 for one seed (Twin belief rows vs shared Proxy/Calibration rows)."""
    j_t_r1, j_t_r2, j_t_all = tw.loc[list(SEL_REPS)].mean(), tw.loc[list(EVAL_REPS)].mean(), tw.mean()
    a_star, a_uns = str(j_t_r1.idxmin()), str(j_t_all.idxmin())
    g_t, g_t_uns = float(j_t_r2["A0"] - j_t_r2[a_star]), float(j_t_all["A0"] - j_t_all[a_uns])
    j_p_m1, j_p_m2, j_p_all = px.loc[list(SEL_REPS)].mean(), px.loc[list(EVAL_REPS)].mean(), px.mean()
    oracle, oracle_uns = str(j_p_m1.idxmin()), str(j_p_all.idxmin())
    g_p, g_p_uns = float(j_p_m2["A0"] - j_p_m2[a_star]), float(j_p_all["A0"] - j_p_all[a_uns])
    a0_m2, a0_all = float(j_p_m2["A0"]), float(j_p_all["A0"])
    bee, bee_uns = g_t - g_p, g_t_uns - g_p_uns
    regret, denom = float(j_p_m2[a_star] - j_p_m2[oracle]), float(j_p_m2["A0"] - j_p_m2[oracle])
    regret_uns, denom_uns = float(j_p_all[a_uns] - j_p_all[oracle_uns]), float(j_p_all["A0"] - j_p_all[oracle_uns])
    row: Dict[str, Any] = {
        "a_star": a_star, "oracle": oracle, "a_star_unsplit": a_uns, "oracle_unsplit": oracle_uns,
        "a_star_floor": None, "G_T_hat": g_t, "G_P": g_p, "BEE_signed": bee, "BEE_abs": abs(bee),
        "BEE_rel": abs(bee) / a0_m2 if a0_m2 > 0 else None, "BEE_signed_rel": bee / a0_m2 if a0_m2 > 0 else None,
        "BEE_signed_unsplit": bee_uns, "BEE_abs_unsplit": abs(bee_uns),
        "BEE_rel_unsplit": abs(bee_uns) / a0_all if a0_all > 0 else None,
        "Regret": regret, "Regret_denom": denom, "Regret_rel": regret / denom if denom >= REGRET_DENOM_MIN else None,
        "Regret_unsplit": regret_uns, "Regret_denom_unsplit": denom_uns,
        "Regret_rel_unsplit": regret_uns / denom_uns if denom_uns >= REGRET_DENOM_MIN else None,
        "top1_agree": 1.0 if a_star == oracle else 0.0,
        "top1_r2_m2_agree": 1.0 if str(j_t_r2.idxmin()) == str(j_p_m2.idxmin()) else 0.0,
        "spearman_rho": spearman_rho([float(j_t_r2[a]) for a in ACTIONS], [float(j_p_m2[a]) for a in ACTIONS]),
        "kendall_tau": kendall_tau([float(j_t_r2[a]) for a in ACTIONS], [float(j_p_m2[a]) for a in ACTIONS]),
        "BEE_floor_signed": None, "BEE_floor_abs": None, "BEE_floor_rel": None,
        "G_T_A3": float(j_t_r2["A0"] - j_t_r2["A3"]), "G_P_A3": float(j_p_m2["A0"] - j_p_m2["A3"]),
        "J_T_r1": {a: float(j_t_r1[a]) for a in ACTIONS}, "J_T_r2": {a: float(j_t_r2[a]) for a in ACTIONS},
        "J_P_m1": {a: float(j_p_m1[a]) for a in ACTIONS}, "J_P_m2": {a: float(j_p_m2[a]) for a in ACTIONS}}
    row["BEE_A3"] = row["G_T_A3"] - row["G_P_A3"]
    if cal is not None:
        j_c_sel, j_c_ev = cal.loc[list(CAL_SEL_REPS)].mean(), cal.loc[list(CAL_EVAL_REPS)].mean()
        a_floor = str(j_c_sel.idxmin())
        floor = float(j_c_ev["A0"] - j_c_ev[a_floor]) - float(j_p_m2["A0"] - j_p_m2[a_floor])
        row.update({"a_star_floor": a_floor, "BEE_floor_signed": floor, "BEE_floor_abs": abs(floor),
                    "BEE_floor_rel": abs(floor) / a0_m2 if a0_m2 > 0 else None})
    return row


def summarize(values: Sequence[Any], seeds: Sequence[int], exclusions: Dict[str, List[int]]) -> Dict[str, Any]:
    """Paired t 95% CI over seeds plus a percentile bootstrap check; no interval when N < 2."""
    vals = [float(v) for v in values if _finite(v)]
    out: Dict[str, Any] = {"n": len(vals), "seeds": list(seeds), "exclusions": exclusions,
                           "mean": None, "std": None, "se": None, "ci95_t": None, "ci95_boot": None}
    if not vals:
        return out
    mean = float(np.mean(vals))
    std = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    se = std / math.sqrt(len(vals)) if len(vals) > 1 else 0.0
    out.update({"mean": mean, "std": std, "se": se})
    if len(vals) >= 2:
        t_crit = t_critical_95(len(vals) - 1)
        out["ci95_t"] = [mean - t_crit * se, mean + t_crit * se]
        rng = np.random.default_rng(42)
        boot = [float(np.mean(rng.choice(vals, size=len(vals), replace=True))) for _ in range(10000)]
        out["ci95_boot"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
    return out


def _exclusion_reason(seed: int, validation: Dict[str, Any], needs_cal: bool) -> str:
    for world in (("twin", "proxy", "calibration") if needs_cal else ("twin", "proxy")):
        rec = validation[world][0].get(seed)
        if rec is None or not rec["complete"]:
            return f"{world}: {rec['reason'] if rec else 'missing'}"
    return "metric not defined for this seed"


def compute_belief(df: pd.DataFrame, belief: str, seeds: Sequence[int]) -> Dict[str, Any]:
    """Validation plus estimands 1-5 (and the unsplit versions) for one Twin belief."""
    validation = {w: validate_world(df, belief, w, seeds, require_clearance=(belief == SECONDARY_BELIEF and w == "twin"))
                  for w in WORLDS}
    twin_ok, proxy_ok, cal_ok = (set(validation[w][1]) for w in WORLDS)
    per_seed: List[Dict[str, Any]] = []
    for s in sorted(twin_ok & proxy_ok):
        cal = pivot_ok(df, belief, "calibration", s) if s in cal_ok else None
        row = seed_metrics(pivot_ok(df, belief, "twin", s), pivot_ok(df, belief, "proxy", s), cal)
        row["seed"] = int(s)
        per_seed.append(row)
    have = {int(r["seed"]) for r in per_seed}
    pooled: Dict[str, Any] = {}
    for key in METRIC_KEYS:
        got, reasons = [r for r in per_seed if _finite(r.get(key))], {}
        for r in per_seed:
            if not _finite(r.get(key)):
                reason = ("Regret_rel not reported: denominator < 0.5 veh.h" if key == "Regret_rel"
                          else f"not available ({key})")
                reasons.setdefault(reason, []).append(int(r["seed"]))
        for s in [int(x) for x in seeds if int(x) not in have]:
            reasons.setdefault(_exclusion_reason(s, validation, key in FLOOR_KEYS), []).append(s)
        pooled[key] = summarize([r[key] for r in got], [int(r["seed"]) for r in got], reasons)
    return {"belief": belief, "validation": validation, "per_seed": per_seed, "pooled": pooled,
            "n_complete_seeds": len(per_seed), "complete_seeds": sorted(have)}


def crn_block(df: pd.DataFrame, belief: str, complete: Sequence[int]) -> Dict[str, Any]:
    """v2 paired CRN corr(a) and VR(a) per world, on complete seeds only."""
    keep = df[df["status"] == "ok"]
    keep = pd.concat([rows_for(keep, "twin", belief), keep[keep["world"] != "twin"]], ignore_index=True)
    keep = keep[keep["seed"].isin(list(complete))].drop_duplicates(
        ["world", "seed", "replication", "action"], keep="first")
    stats = compute_crn_statistics(keep)
    return {"per_seed": {str(k): v for k, v in stats["per_seed"].items()},
            "pooled_medians": stats["pooled_medians"]}


def state_history_summary(state: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """Descriptive only: no gating, unavailable pending counts reported as unknown."""
    if state is None or state.empty:
        return {"available": False, "n_rows": 0, "columns": [],
                "note": "state_history.parquet missing or empty; pending counts unknown"}

    def _cell(v: Any) -> Any:
        if isinstance(v, str) and v[:1] in "[{":
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                pass
        return "unknown" if (v is None or (not isinstance(v, (dict, list)) and pd.isna(v))) else v

    rows = [{str(k): _cell(v) for k, v in r.items()} for _, r in state.iterrows()]
    return {"available": True, "n_rows": len(rows), "columns": [str(c) for c in state.columns],
            "rows": rows,
            "note": "descriptive only; incident history: Proxy active since 4,500 s, Twin none (CONV)"}


def _fmt(v: Any, nd: int = 2) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k} {_fmt(x, nd)}" for k, x in sorted(v.items()))
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(x, nd) for x in v) + "]"
    return "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def _table(lines: List[str], header: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    lines.append("")


def _pooled_table(lines: List[str], pooled: Dict[str, Any], keys: Sequence[str]) -> None:
    rows = [[key, pooled[key]["n"], _fmt(pooled[key]["mean"], 3), _fmt(pooled[key]["ci95_t"], 3),
             _fmt(pooled[key]["ci95_boot"], 3),
             "; ".join(f"{r} ({len(s)}: {sorted(s)})" for r, s in sorted(pooled[key]["exclusions"].items()))
             or "none"] for key in keys]
    _table(lines, ["Metric", "N", "Mean", "Paired t 95% CI", "Percentile bootstrap 95% CI", "Exclusions"], rows)


def write_report(path: Path, bundle: Dict[str, Any]) -> None:
    primary, secondary = bundle["primary"], bundle["secondary"]
    lines = ["# Frozen offline decision audit: analysis", "", f"Input: `{bundle['dir']}`", "",
             f"Seeds: {bundle['seeds']} (N = {bundle['n_seeds']}). Decision time t_d = 5,100 s; horizon 900 s; "
             "J = total time spent (veh.h).", "", "## Claim boundary", "", "> " + CLAIM_BOUNDARY, "",
             "- The development audit's numbers (seeds 4201-4208) stay reported unchanged beside these, never pooled.",
             "- The calibration floor is reported beside BEE; it is never subtracted from BEE and no causal-gap "
             "interpretation is made.", "", "## 1. Validation", ""]
    for belief, block in ((PRIMARY_BELIEF, primary), (SECONDARY_BELIEF, secondary)):
        lines += [f"### Belief {belief}", ""]
        for world in WORLDS:
            recs, complete = block["validation"][world]
            bad = {s: r["reason"] for s, r in recs.items() if not r["complete"]}
            lines.append(f"- **{world}**: {len(complete)}/{len(recs)} complete seeds {sorted(complete)}; exclusions: "
                         f"{bad if bad else 'none'}")
        lines.append("")
    for belief, block in ((PRIMARY_BELIEF, primary), (SECONDARY_BELIEF, secondary)):
        lines += ["## 2. Primary, belief B" if belief == PRIMARY_BELIEF else
                  "## 3. Secondary, belief D300 (truth-assisted offline positive control)", "",
                  f"Complete seeds: {block['n_complete_seeds']} {block['complete_seeds']} "
                  "(common complete seeds for paired comparisons).", ""]
        _table(lines, ["Seed", "a* (R1)", "Oracle (M1)", "Top-1", "G_T(a*)", "G_P(a*)", "BEE signed", "BEE abs",
                       "BEE rel", "Regret", "Regret denom", "Regret rel", "Spearman", "Kendall", "Floor (abs)"],
               [[r["seed"], r["a_star"], r["oracle"], int(r["top1_agree"]), _fmt(r["G_T_hat"], 3), _fmt(r["G_P"], 3),
                 _fmt(r["BEE_signed"], 3), _fmt(r["BEE_abs"], 3), _fmt(r["BEE_rel"], 4), _fmt(r["Regret"], 3),
                 _fmt(r["Regret_denom"], 3), _fmt(r["Regret_rel"], 4), _fmt(r["spearman_rho"], 3),
                 _fmt(r["kendall_tau"], 3), _fmt(r["BEE_floor_abs"], 3)] for r in block["per_seed"]])
        lines += ["### Pooled over seeds", ""]
        _pooled_table(lines, block["pooled"], METRIC_KEYS)
        lines += ["### Unsplit versions (selection bias shown beside)", ""]
        _pooled_table(lines, block["pooled"], UNSPLIT_KEYS)
    lines += ["## 4. Fixed-A3 gain (R2 under B and D300 vs G_P(A3) on M2)", ""]
    for belief, block in ((PRIMARY_BELIEF, primary), (SECONDARY_BELIEF, secondary)):
        p = block["pooled"]
        lines.append(f"- **{belief}**: " + "; ".join(
            f"{k} = {_fmt(p[k]['mean'], 3)} {_fmt(p[k]['ci95_t'], 3)}" for k in ("G_T_A3", "G_P_A3", "BEE_A3")))
    lines += ["", "## 5. v2 paired CRN (corr(a), VR(a))", ""]
    meds = {b: bundle["crn"][b]["pooled_medians"] for b in (PRIMARY_BELIEF, SECONDARY_BELIEF)}
    _table(lines, ["Belief", "World", "Median corr", "Median VR", "Pooled median corr", "Pooled median VR"],
           [[b, w] + [_fmt((meds[b].get(w) or {}).get(k), 4) for k in ("median_corr", "median_vr",
                      "pooled_median_corr", "pooled_median_vr")] for b in meds for w in WORLDS if meds[b].get(w)])
    sh = bundle["state_history"]
    lines += ["## 6. State history (descriptive only, no gating)", ""]
    if not sh["available"]:
        lines.append(f"- {sh['note']}")
    else:
        lines += [f"- {sh['n_rows']} snapshot rows; identical displayed rows collapsed. Pending counts that are "
                  "unavailable are shown as unknown, never as zero.", f"- {sh['note']}", ""]
        cols = list(sh["columns"])
        if cols:
            _table(lines, cols, list(dict.fromkeys(tuple(_fmt(r.get(c)) for c in cols) for r in sh["rows"])))
    lines += ["## 7. RNG isolation check (descriptive)", "",
              f"- passed: {bundle['rng_check'].get('passed')}" if bundle["rng_check"] else "- rng_check.json missing",
              "", "No interval is reported for N < 2; no acceptance threshold applies.", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(directory: Path) -> Dict[str, Any]:
    raw, state, rng = load_inputs(directory)
    seeds = sorted(int(s) for s in raw["seed"].unique())
    primary, secondary = compute_belief(raw, PRIMARY_BELIEF, seeds), compute_belief(raw, SECONDARY_BELIEF, seeds)
    bundle = {"dir": str(directory), "claim_boundary": CLAIM_BOUNDARY, "seeds": seeds, "n_seeds": len(seeds),
              "primary_belief": PRIMARY_BELIEF, "secondary_belief": SECONDARY_BELIEF,
              "primary": primary, "secondary": secondary,
              "crn": {PRIMARY_BELIEF: crn_block(raw, PRIMARY_BELIEF, primary["complete_seeds"]),
                      SECONDARY_BELIEF: crn_block(raw, SECONDARY_BELIEF, secondary["complete_seeds"])},
              "state_history": state_history_summary(state), "rng_check": rng}
    (Path(directory) / "metrics.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    write_report(Path(directory) / "report.md", bundle)
    return bundle


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Frozen offline decision audit analyzer")
    a = ap.add_subparsers(dest="cmd", required=True).add_parser(
        "analyze", help="compute the preregistered estimands for a collected directory")
    a.add_argument("--dir", required=True, help="directory with raw.parquet/state_history.parquet/rng_check.json")
    bundle = analyze(Path(ap.parse_args(argv).dir))
    p = bundle["primary"]["pooled"]["BEE_signed"]
    print(f"analyze: {bundle['n_seeds']} seeds; primary complete {bundle['primary']['n_complete_seeds']}, "
          f"secondary complete {bundle['secondary']['n_complete_seeds']}; "
          f"BEE(B) = {_fmt(p['mean'], 3)} {_fmt(p['ci95_t'], 3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
