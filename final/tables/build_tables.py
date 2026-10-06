#!/usr/bin/env python
"""Final evidence tables (CSV + Markdown) from the collected CityCom results.

Reads stored artefacts only; runs no simulation and writes nothing outside final/tables/.

Every value is either read from a stored JSON (the JSON path is cited in the table caption
and in the README) or recomputed from a stored Parquet with the definition given in the
corresponding preregistration document:

  * development audit  : docs/oct6-audit-and-pilot2-plan.md part A (+ audit v2 protocol)
  * development D300   : same definitions, Twin branches from results/audit/sens/raw_sens.parquet
  * frozen test audit  : docs/oct16-frozen-audit-plan.md (stored pooled values are used)
  * replay diagnosis   : docs/oct10-replay-diagnosis-plan.md, recomputed at beta = 0.25
  * missing queue      : docs/oct11-missing-queue-plan.md

Numbers are full precision in CSV and rounded to 3 decimals in Markdown.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

ACTIONS = ["A0", "A1", "A2", "A3", "A4"]
R1, R2 = [1, 2, 3], [4, 5, 6]           # Twin selection / evaluation replications
M1, M2 = [1, 2, 3], [4, 5, 6]           # Proxy selection / evaluation replications
CAL_R1, CAL_R2 = [7, 8, 9], [10, 11, 12]  # calibration (Proxy-as-Twin) branches
BETA = 0.25                              # event-engine posterior temperature
LN10 = math.log(10.0)
NA = "n/a"

# Two-sided 95 % Student-t quantiles (df -> t).  df = 7 for the 8-seed audits.
T95 = {
    1: 12.706204736432095, 2: 4.302652729749537, 3: 3.182446305284263,
    4: 2.7764451051977987, 5: 2.570581835636314, 6: 2.446911851144969,
    7: 2.3646242515927844, 8: 2.3060041352041653, 9: 2.262157162798205,
    10: 2.228138851986273, 11: 2.201159225942619, 12: 2.178812829667228,
}


# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------
def jload(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def pload(rel: str) -> pd.DataFrame:
    return pd.read_parquet(ROOT / rel)


def fmt_md(value) -> str:
    """Markdown cell: floats to 3 decimals, everything else as text (pipes escaped)."""
    if value is None:
        return NA
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if math.isnan(value):
            return NA
        return f"{value:.3f}"
    return str(value).replace("|", "\\|")


def fmt_csv(value) -> str:
    """CSV cell: floats at full (round-trip) precision."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return repr(value)
    return str(value)


def write_table(name: str, caption: str, columns: list[str], rows: list[dict]) -> None:
    """Write one table as <name>.csv (full precision) and <name>.md (3 decimals)."""
    csv_path = HERE / f"{name}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([fmt_csv(row.get(col)) for col in columns])

    md_path = HERE / f"{name}.md"
    lines = [caption, "", "| " + " | ".join(c.replace("|", "\\|") for c in columns) + " |",
             "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(fmt_md(row.get(col)) for col in columns) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {csv_path.name} and {md_path.name}  ({len(rows)} rows)")


def distribution(values) -> str:
    """'A3 8/8' or 'A0 1/8; A1 2/8; A3 5/8' in A0..A4 order."""
    n = len(values)
    counts = {a: 0 for a in ACTIONS}
    for v in values:
        counts[v] += 1
    parts = [f"{a} {counts[a]}/{n}" for a in ACTIONS if counts[a]]
    return "; ".join(parts)


def pooled(values) -> dict:
    """Mean and 95 % t-CI over seeds (None entries dropped)."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    n = len(v)
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    mean = float(v.mean())
    if n < 2:
        return {"n": n, "mean": mean, "lo": mean, "hi": mean}
    se = float(v.std(ddof=1)) / math.sqrt(n)
    half = T95[n - 1] * se
    return {"n": n, "mean": mean, "lo": mean - half, "hi": mean + half}


def stored_pooled(entry) -> dict:
    """A stored pooled JSON entry -> {n, mean, lo, hi}."""
    lo, hi = entry["ci95_t"]
    return {"n": entry["n"], "mean": float(entry["mean"]), "lo": float(lo), "hi": float(hi)}


def agreement_count(values) -> str:
    """Top-1 agreement as an exact per-seed count 'k/n' (e.g. '7/8').

    Top-1 agreement is a 0/1 per-seed indicator, so a t-interval on its mean is not
    meaningful (it can exceed 1); only the count is reported.
    """
    v = [float(x) for x in values if x is not None]
    k = int(round(sum(v)))
    return f"{k}/{len(v)}"


def _rank(by_action: dict) -> dict:
    return {a: i for i, a in enumerate(sorted(ACTIONS, key=lambda a: by_action[a]))}


def _spearman(rt: dict, rp: dict) -> float:
    x = [rt[a] for a in ACTIONS]
    y = [rp[a] for a in ACTIONS]
    return float(np.corrcoef(x, y)[0, 1])


def _kendall(rt: dict, rp: dict) -> float:
    concordant = discordant = 0
    for i in range(len(ACTIONS)):
        for j in range(i + 1, len(ACTIONS)):
            a, b = ACTIONS[i], ACTIONS[j]
            prod = (rt[a] - rt[b]) * (rp[a] - rp[b])
            concordant += 1 if prod > 0 else 0
            discordant += 1 if prod < 0 else 0
    return (concordant - discordant) / (concordant + discordant)


# --------------------------------------------------------------------------------------
# t1 - frozen audit, per seed and belief
# --------------------------------------------------------------------------------------
def build_t1() -> None:
    metrics = jload("results/frozen_audit/metrics.json")
    columns = ["seed", "belief", "a_star", "oracle", "top1_agree", "G_T_hat", "G_P",
               "BEE_signed", "Regret", "spearman_rho", "kendall_tau",
               "BEE_floor_signed", "G_T_A3", "G_P_A3"]
    rows = []
    for belief, block in (("B (primary)", metrics["primary"]),
                          ("D300 (secondary)", metrics["secondary"])):
        for rec in block["per_seed"]:
            rows.append({
                "seed": rec["seed"],
                "belief": belief,
                "a_star": rec["a_star"],
                "oracle": rec["oracle"],
                "top1_agree": bool(rec["top1_agree"]),
                "G_T_hat": rec["G_T_hat"],
                "G_P": rec["G_P"],
                "BEE_signed": rec["BEE_signed"],
                "Regret": rec["Regret"],
                "spearman_rho": rec["spearman_rho"],
                "kendall_tau": rec["kendall_tau"],
                "BEE_floor_signed": rec["BEE_floor_signed"],
                "G_T_A3": rec["G_T_A3"],
                "G_P_A3": rec["G_P_A3"],
            })
    caption = ("Source: `results/frozen_audit/metrics.json` (`primary.per_seed` = belief B, "
               "`secondary.per_seed` = belief D300; every field read directly from that path); "
               "`top1_agree` is `a_star == oracle`, rendered as yes/no per seed; "
               "N = 16 rows (8 frozen test seeds 4501-4508 x 2 beliefs).")
    write_table("t1_frozen_per_seed", caption, columns, rows)


# --------------------------------------------------------------------------------------
# t2 - development audit vs frozen test audit, side by side (never pooled)
# --------------------------------------------------------------------------------------
def audit_per_seed(twin: pd.DataFrame, proxy: pd.DataFrame, cal: pd.DataFrame,
                   seeds: list[int]) -> pd.DataFrame:
    """Part A / audit v2 per-seed metrics (verified against the stored pooled JSONs)."""
    out = []
    for seed in seeds:
        t = twin[twin.seed == seed]
        p = proxy[proxy.seed == seed]
        c = cal[cal.seed == seed]

        def jm(df, reps, action):
            return float(df[df.replication.isin(reps) & (df.action == action)]["J"].mean())

        a_star = min(ACTIONS, key=lambda a: jm(t, R1, a))
        oracle = min(ACTIONS, key=lambda a: jm(p, M1, a))
        g_t = jm(t, R2, "A0") - jm(t, R2, a_star)
        g_p = jm(p, M2, "A0") - jm(p, M2, a_star)
        jp_a0 = jm(p, M2, "A0")
        regret = jm(p, M2, a_star) - jm(p, M2, oracle)
        denom = jp_a0 - jm(p, M2, oracle)
        rt = _rank({a: jm(t, R2, a) for a in ACTIONS})
        rp = _rank({a: jm(p, M2, a) for a in ACTIONS})
        a_floor = min(ACTIONS, key=lambda a: jm(c, CAL_R1, a))
        g_t_floor = jm(c, CAL_R2, "A0") - jm(c, CAL_R2, a_floor)
        g_p_floor = jm(p, M2, "A0") - jm(p, M2, a_floor)
        out.append({
            "seed": seed,
            "a_star": a_star,
            "oracle": oracle,
            "a_star_floor": a_floor,
            "top1_agree": 1.0 if a_star == oracle else 0.0,
            "G_T_hat": g_t,
            "G_P": g_p,
            "BEE_signed": g_t - g_p,
            "BEE_abs": abs(g_t - g_p),
            "BEE_rel": abs(g_t - g_p) / jp_a0,
            "Regret": regret,
            "Regret_rel": (regret / denom) if denom >= 0.5 else None,
            "spearman_rho": _spearman(rt, rp),
            "kendall_tau": _kendall(rt, rp),
            "BEE_floor_signed": g_t_floor - g_p_floor,
            "BEE_floor_abs": abs(g_t_floor - g_p_floor),
            "G_T_A3": jm(t, R2, "A0") - jm(t, R2, "A3"),
            "G_P_A3": jm(p, M2, "A0") - jm(p, M2, "A3"),
        })
    return pd.DataFrame(out)


def build_t2() -> None:
    dev_seeds = list(range(4201, 4209))
    frozen_seeds = list(range(4501, 4509))

    # -- development audit, belief B: stored pooled values (metrics_v2.json); the fixed-A3
    #    gains are not in that pooled block, so they are recomputed from raw.parquet.
    v2 = jload("results/audit/v2/metrics_v2.json")
    raw_dev = pload("results/audit/raw.parquet")
    dev_b_seed = audit_per_seed(raw_dev[raw_dev.world == "twin"],
                                raw_dev[raw_dev.world == "proxy"],
                                raw_dev[raw_dev.world == "calibration"], dev_seeds)
    dev_b = {
        "dist_a_star": distribution([r["a_star"] for r in v2["per_seed"]]),
        "dist_oracle": distribution([r["oracle"] for r in v2["per_seed"]]),
        "top1_agree": agreement_count([r["top1_agree"] for r in v2["per_seed"]]),
        "BEE_signed": stored_pooled(v2["pooled"]["BEE_signed"]),
        "BEE_abs": stored_pooled(v2["pooled"]["BEE_abs"]),
        "BEE_rel": stored_pooled(v2["pooled"]["BEE_rel"]),
        "Regret": stored_pooled(v2["pooled"]["Regret"]),
        "Regret_rel": stored_pooled(v2["pooled"]["Regret_rel"]),
        "spearman_rho": stored_pooled(v2["pooled"]["spearman_rho"]),
        "kendall_tau": stored_pooled(v2["pooled"]["kendall_tau"]),
        "BEE_floor_abs": stored_pooled(v2["pooled"]["BEE_floor_abs"]),
        "G_T_hat": pooled(dev_b_seed["G_T_hat"]),
        "G_P": pooled(dev_b_seed["G_P"]),
        "G_T_A3": pooled(dev_b_seed["G_T_A3"]),
        "G_P_A3": pooled(dev_b_seed["G_P_A3"]),
    }

    # -- development D300 (truth-assisted duration): recomputed from raw_sens.parquet with
    #    the same definitions; the Proxy and calibration branches are the audit's.
    sens = pload("results/audit/sens/raw_sens.parquet")
    dev_d_seed = audit_per_seed(sens[sens.variant == "D300"],
                                raw_dev[raw_dev.world == "proxy"],
                                raw_dev[raw_dev.world == "calibration"], dev_seeds)
    dev_d = {
        "dist_a_star": distribution(dev_d_seed["a_star"]),
        "dist_oracle": distribution(dev_d_seed["oracle"]),
        "top1_agree": agreement_count(dev_d_seed["top1_agree"]),
    }
    for key in ("BEE_signed", "BEE_abs", "BEE_rel", "Regret", "Regret_rel",
                "spearman_rho", "kendall_tau", "BEE_floor_abs", "G_T_hat", "G_P",
                "G_T_A3", "G_P_A3"):
        dev_d[key] = pooled(dev_d_seed[key])

    # -- frozen test audit: stored pooled values.
    fr = jload("results/frozen_audit/metrics.json")
    frozen = {}
    for tag, block in (("B", fr["primary"]), ("D300", fr["secondary"])):
        bundle = {
            "dist_a_star": distribution([r["a_star"] for r in block["per_seed"]]),
            "dist_oracle": distribution([r["oracle"] for r in block["per_seed"]]),
            "top1_agree": agreement_count([r["top1_agree"] for r in block["per_seed"]]),
        }
        for key in ("BEE_signed", "BEE_abs", "BEE_rel", "Regret", "Regret_rel",
                    "spearman_rho", "kendall_tau", "BEE_floor_abs", "G_T_hat", "G_P",
                    "G_T_A3", "G_P_A3"):
            bundle[key] = stored_pooled(block["pooled"][key])
        frozen[tag] = bundle

    columns = ["belief", "metric", "dev mean", "dev CI95 low", "dev CI95 high",
               "frozen mean", "frozen CI95 low", "frozen CI95 high",
               "difference (frozen - dev) [descriptive]"]
    metric_rows = [
        ("a* distribution (per seed)", "dist_a_star"),
        ("oracle distribution (per seed)", "dist_oracle"),
        ("oracle agreement Top-1", "top1_agree"),
        ("G_T_hat(a*) (veh.h)", "G_T_hat"),
        ("G_P(a*) (veh.h)", "G_P"),
        ("BEE signed (veh.h)", "BEE_signed"),
        ("|BEE| (veh.h)", "BEE_abs"),
        ("BEE_rel (|BEE| / J_P(A0))", "BEE_rel"),
        ("Regret (veh.h)", "Regret"),
        ("Regret_rel (split denominator)", "Regret_rel"),
        ("Spearman rho", "spearman_rho"),
        ("Kendall tau", "kendall_tau"),
        ("calibration floor |BEE| (veh.h)", "BEE_floor_abs"),
        ("fixed-A3 G_T_hat (veh.h)", "G_T_A3"),
        ("fixed-A3 G_P (veh.h)", "G_P_A3"),
    ]
    rows = []
    for belief, dev_bundle, frozen_bundle in (
            ("B (primary)", dev_b, frozen["B"]),
            ("D300 (secondary)", dev_d, frozen["D300"])):
        for label, key in metric_rows:
            if key.startswith("dist_"):
                rows.append({"belief": belief, "metric": label,
                             "dev mean": dev_bundle[key], "frozen mean": frozen_bundle[key],
                             "difference (frozen - dev) [descriptive]": NA})
                continue
            if key == "top1_agree":
                # a per-seed yes/no count: no interval (a t-CI on a 0/1 proportion is not
                # meaningful and can exceed 1) and no mean difference.
                rows.append({"belief": belief, "metric": label,
                             "dev mean": dev_bundle[key], "dev CI95 low": NA, "dev CI95 high": NA,
                             "frozen mean": frozen_bundle[key], "frozen CI95 low": NA,
                             "frozen CI95 high": NA,
                             "difference (frozen - dev) [descriptive]": NA})
                continue
            d, f = dev_bundle[key], frozen_bundle[key]
            rows.append({
                "belief": belief, "metric": label,
                "dev mean": d["mean"], "dev CI95 low": d["lo"], "dev CI95 high": d["hi"],
                "frozen mean": f["mean"], "frozen CI95 low": f["lo"], "frozen CI95 high": f["hi"],
                "difference (frozen - dev) [descriptive]": f["mean"] - d["mean"],
            })
    caption = (
        "Sources, side by side and never pooled. Development audit (seeds 4201-4208): belief B "
        "read from `results/audit/v2/metrics_v2.json` (`pooled`, `per_seed`), which has the pooled "
        "values; its G_T_hat/G_P/G_T_A3/G_P_A3 are not in that pooled block and are recomputed from "
        "`results/audit/raw.parquet` with the `docs/oct6-audit-and-pilot2-plan.md` part A definitions "
        "(the recomputation reproduces every overlapping metrics_v2 pooled value to < 1e-6). "
        "Development D300: recomputed from `results/audit/sens/raw_sens.parquet` (variant D300) with "
        "the same definitions; it reproduces `results/audit/sens/metrics_sens.json` variants.D300 "
        "per-seed values and pooled means exactly (max |mean diff| 7e-15), while the pooled t-CI bounds "
        "agree to 2.4e-7 (the sens report's t multiplier differs in the 8th digit). "
        "Frozen test audit (seeds 4501-4508): `results/frozen_audit/metrics.json` `primary.pooled` "
        "(B) and `secondary.pooled` (D300). The calibration floor uses the shared calibration branches, "
        "so its value is identical for B and D300. 'difference (frozen - dev)' is the difference of the "
        "two means only, descriptive, no test. G_T_hat(a*) equals the fixed-A3 G_T_hat under belief B "
        "because a* = A3 for all 16 B seeds (dev and frozen). "
        "Top-1 agreement is a per-seed yes/no indicator, so it is reported as the exact count k/8 "
        "with n/a interval and difference cells (a t-CI on a 0/1 proportion is not meaningful and "
        "can exceed 1). "
        "N = 8 seeds per audit column; 95 % t-CI over seeds (not for Top-1)."
    )
    write_table("t2_dev_vs_frozen_pooled", caption, columns, rows)


# --------------------------------------------------------------------------------------
# t3 - event-engine coverage
# --------------------------------------------------------------------------------------
def build_t3() -> None:
    out = jload("results/dev_runs/outcomes/outcomes.json")
    inc = out["pooled"]["INC"]
    shk = out["pooled"]["SHK"]
    det = out["pooled"]["DET"]
    noi = out["pooled"]["NOI"]

    rows = [
        {"mechanism": "Trigger on INC (G4 alarm -> SUSPECTED_EVENT)",
         "evidence level": "live natural",
         "count (denominator)":
             f"development seeds 4401-4406: {inc['alarm_events']} trigger episodes in "
             f"{inc['n_evt_runs']}/{inc['n_evt_runs']} EVT INC runs; "
             "pilot-2 seeds 4101-4103: 9 trigger episodes in 3/3 EVT INC runs (2/4/3)",
         "source": "results/dev_runs/outcomes/outcomes.json (pooled.INC.alarm_events); "
                   "results/event_pilot2/report.md s.2-s.3; docs/decision-2026-10-06-dev-runs.md"},

        {"mechanism": "Library evaluation (20 hypotheses)",
         "evidence level": "live natural",
         "count (denominator)":
             f"development: {inc['library']['successful']}/{inc['library']['attempted']} successful "
             f"evaluations, {inc['library']['failed']} failed, over {inc['n_evt_runs']} EVT INC runs; "
             "pilot-2: 13 evaluations in 3 runs (4/4/5)",
         "source": "results/dev_runs/outcomes/outcomes.json (pooled.INC.library, "
                   "exclusions_library); results/event_pilot2/report.md s.3"},

        {"mechanism": "Natural adoption",
         "evidence level": "live natural (negative)",
         "count (denominator)":
             f"development: {inc['natural_adoption']['runs_with_adoption']}/"
             f"{inc['natural_adoption']['n_runs']} runs, "
             f"{inc['natural_adoption']['n']}/"
             f"{inc['natural_adoption']['denominator_successful_library_evals']} successful "
             "evaluations (rate 0.0); pilot-2: 0/3 primary INC runs (0/13 evaluations); "
             "1 further natural adoption inside forced run evtforce_inc_4101 at 6,450 s, "
             "labelled non-independent",
         "source": "results/dev_runs/outcomes/outcomes.json (pooled.INC.natural_adoption); "
                   "results/event_pilot2/report.md s.3 and s.6"},

        {"mechanism": "Forced adoption + state replacement",
         "evidence level": "live forced (labelled, not inference)",
         "count (denominator)":
             "pilot-2: 3/3 forced runs adopted the injected h* (evtforce_inc_4101/2/3); "
             "4 replacement rows in total (3 forced + 1 natural adoption, plus clearance lifts); "
             "live vehicle digest = replay digest 4/4; live restriction applied 2/2 adoptions",
         "source": "results/event_pilot2/report.md s.6; "
                   "results/event_pilot2/evidence/check7_755.json"},

        {"mechanism": "Clearance",
         "evidence level": "live forced (labelled)",
         "count (denominator)":
             "pilot-2: 3/3 forced runs, 4 spells, 17 clearance evaluations (4/5/8); rules hold "
             "in 4/4 spells; all 3 primary forced spells released before the scenario's true "
             "clear at 5,400 s (premature); 1/4 recovery spells then completed",
         "source": "results/event_pilot2/report.md s.6; "
                   "results/event_pilot2/evidence/check8_clearance.json; "
                   "docs/decision-2026-10-06-dev-runs.md"},

        {"mechanism": "RECOVERY",
         "evidence level": "live forced (labelled)",
         "count (denominator)":
             "pilot-2: 4 spells in 3/3 forced runs; 1/4 completed normally inside the horizon "
             "(1,110 s, recovery_complete); 1/4 exited via a new trigger alarm (690 s); "
             "2/4 still in RECOVERY at 7,200 s",
         "source": "results/event_pilot2/report.md s.6; "
                   "results/event_pilot2/evidence/check8_clearance.json"},

        {"mechanism": "DEGRADED scheduled exit (entry + 900 s)",
         "evidence level": "unit only",
         "count (denominator)":
             "0/6 EVT runs (0/12 pilot-2 runs) entered DEGRADED, so the scheduled exit was not "
             "exercised live; pinned by 2 unit tests and check10_degraded.json (pilot 1 observed "
             "a 960-s live spell, a different run set)",
         "source": "results/event_pilot2/evidence/check10_degraded.json; "
                   "results/event_pilot2/report.md s.5 (check 10); "
                   "docs/decision-2026-10-06-dev-runs.md"},

        {"mechanism": "False-alarm path SHK",
         "evidence level": "not covered",
         "count (denominator)":
             f"development: {shk['alarm_events']} alarms and {shk['library']['attempted']} "
             f"evaluations in {shk['n_evt_runs']}/{shk['n_evt_runs']} EVT SHK runs; realised "
             "corridor flow +5-8 % (scheduled +29 %); pilot-2 did not re-run SHK",
         "source": "results/dev_runs/outcomes/outcomes.json (pooled.SHK); "
                   "docs/decision-2026-10-06-dev-runs.md"},

        {"mechanism": "Fault path DET",
         "evidence level": "not covered (scenario); fault hypotheses only evaluated inside INC",
         "count (denominator)":
             f"development DET: {det['alarm_events']} alarms and {det['library']['attempted']} "
             f"evaluations in {det['n_evt_runs']}/{det['n_evt_runs']} EVT DET runs "
             "(AID02109 stuck-at-normal injected exactly over 4,500-5,400 s, B < 2.9); "
             "separately, the fault family was evaluated live in INC and was the MAP in 13/25 "
             "evaluations",
         "source": "results/dev_runs/outcomes/outcomes.json (pooled.DET); "
                   "docs/decision-2026-10-06-dev-runs.md"},

        {"mechanism": "Forecasts (halting on ktb_w3 + ktb_n1)",
         "evidence level": "live natural (instrument-checked)",
         "count (denominator)":
             "development: 48 (5-min) + 42 (15-min) cells per arm, 0 failed; INC MAE 20.604 "
             "(5-min, 48 cells) / 18.833 (15-min, 42 cells), all under-prediction; EVT = CONV "
             "identical, 24/24 pairs; NOI/SHK/DET truth 0, so their 0 MAE is no accuracy "
             "evidence; pilot-2: 12 runs x 15 cells, INC MAE 7.88-25.75",
         "source": "results/dev_runs/outcomes/outcomes.json (forecasts.arms, pairs); "
                   "results/event_pilot2/report.md s.4; docs/decision-2026-10-06-dev-runs.md"},
    ]
    caption = ("Sources: `results/dev_runs/outcomes/outcomes.json`, `results/event_pilot2/report.md`, "
               "`docs/decision-2026-10-06-dev-runs.md` (counts read from the JSON where available, "
               "otherwise from the cited report sections); N = 10 mechanisms.")
    write_table("t3_event_engine_coverage", caption,
                ["mechanism", "evidence level", "count (denominator)", "source"], rows)


# --------------------------------------------------------------------------------------
# t4 - missing queue
# --------------------------------------------------------------------------------------
def build_t4() -> None:
    mq = jload("results/missing_queue/metrics.json")
    qtd = pload("results/missing_queue/queue_td.parquet")
    plan = {rec["seed"]: rec for rec in mq["plan"]}
    qrows = {rec["seed"]: rec for rec in mq["queue"]}

    rows = []
    for seed in mq["seeds"]:
        td = qtd[qtd.seed == seed]
        q_at_td = {w: float(td[td.world == w]["Q"].iloc[0]) for w in ("proxy", "C", "H")}
        # queue_td.parquet is the stored t_d queue; metrics.json queue[] is the same aggregate.
        assert q_at_td["proxy"] == qrows[seed]["Q_proxy"], seed
        assert q_at_td["C"] == qrows[seed]["Q_C"], seed
        assert q_at_td["H"] == qrows[seed]["Q_H"], seed
        rec = plan[seed]
        rows.append({
            "seed": seed,
            "Q_P (proxy)": q_at_td["proxy"],
            "Q_C (conventional)": q_at_td["C"],
            "Q_H (historical)": q_at_td["H"],
            "e(C-D)": rec["e_C-D"],
            "e(H-D)": rec["e_H-D"],
            "delta_D = e(H-D) - e(C-D)": rec["delta_D"],
            "duration contrast C (G_T(A3;-P) - G_T(A3;-D))": rec["duration_contrast_C"],
            "duration contrast H (G_T(A3;-P) - G_T(A3;-D))": rec["duration_contrast_H"],
            "classification": "study-level (see last row)",
        })
    cls = mq["classification"]
    step4 = cls["inputs"]["step4"]
    rows.append({
        "seed": "classification (all seeds)",
        "Q_P (proxy)": NA, "Q_C (conventional)": NA, "Q_H (historical)": NA,
        "e(C-D)": NA, "e(H-D)": NA, "delta_D = e(H-D) - e(C-D)": NA,
        "duration contrast C (G_T(A3;-P) - G_T(A3;-D))": NA,
        "duration contrast H (G_T(A3;-P) - G_T(A3;-D))": NA,
        "classification": (f"{cls['label']} (step {cls['step']} of the ordered rule): "
                           f"delta_D < 0 on {step4['n_negative']}/4 seeds, mean delta_D "
                           f"= {step4['mean_delta_D']:.3f} <= -1.0 veh.h"),
    })
    caption = ("Sources: Q_P/Q_C/Q_H read from `results/missing_queue/queue_td.parquet` at t_d "
               "(worlds proxy/C/H, column Q) and cross-checked against `results/missing_queue/"
               "metrics.json` `queue[]`; e(C-D), e(H-D), delta_D and the duration contrasts from "
               "`results/missing_queue/metrics.json` `plan[]`; the classification label from "
               "`results/missing_queue/metrics.json` `classification` (rule order in "
               "`docs/oct11-missing-queue-plan.md`). N = 4 seeds (4301-4304) + 1 classification row.")
    write_table("t4_missing_queue", caption,
                ["seed", "Q_P (proxy)", "Q_C (conventional)", "Q_H (historical)",
                 "e(C-D)", "e(H-D)", "delta_D = e(H-D) - e(C-D)",
                 "duration contrast C (G_T(A3;-P) - G_T(A3;-D))",
                 "duration contrast H (G_T(A3;-P) - G_T(A3;-D))", "classification"], rows)


# --------------------------------------------------------------------------------------
# t5 - replay diagnosis, recomputed at beta = 0.25
# --------------------------------------------------------------------------------------
VARIANT_LABELS = {
    "V0": "base",
    "VP": "representation diagnostic",
    "VT": "truth-assisted control (onset)",
    "VPT": "truth-assisted control",
    "VPL": "truth-assisted control (location)",
    "VPTL": "truth-assisted control",
    "VNF": "competition diagnostic",
    "VPTLNF": "truth-assisted control",
}
VARIANT_ORDER = ["V0", "VP", "VT", "VPT", "VPL", "VPTL", "VNF", "VPTLNF"]


def build_t5() -> None:
    raw = pload("results/replay_diag/raw.parquet")
    max_post_diff = max_gap_diff = 0.0
    adopt_diff = 0
    per_variant = {}
    for variant, grp in raw.groupby("variant"):
        evals = {}
        for eval_id, sub in grp.groupby("eval_id"):
            w = sub["prior"].to_numpy(dtype=float) * np.exp(BETA * sub["logL"].to_numpy(dtype=float))
            post = w / w.sum()
            # agreement check against the stored beta = 0.25 posterior
            max_post_diff = max(max_post_diff, float(np.abs(post - sub["post"].to_numpy(dtype=float)).max()))
            best_inc = float(post[sub["family"].to_numpy() == "incident"].max())
            best_dem = float(post[sub["family"].to_numpy() == "demand"].max())
            gap = math.log(best_inc) - math.log(best_dem)
            map_family = sub["family"].to_numpy()[int(np.argmax(post))]
            would = bool(map_family == "incident" and gap > LN10)
            stored_gap = float(sub["gap"].iloc[0])
            max_gap_diff = max(max_gap_diff, abs(gap - stored_gap))
            adopt_diff += int(would != bool(sub["would_adopt"].iloc[0]))
            evals[eval_id] = {"arm": sub["arm"].iloc[0], "gap": gap, "would": would,
                              "map_family": map_family}
        per_variant[variant] = evals

    rows = []
    for variant in VARIANT_ORDER:
        evals = per_variant[variant]
        inc = [e for e in evals.values() if e["arm"] == "INC"]
        noi = [e for e in evals.values() if e["arm"] == "NOI"]
        fam_counts = {f: 0 for f in ("incident", "demand", "fault")}
        for e in inc:
            fam_counts[e["map_family"]] += 1
        fam_str = "; ".join(f"{f} {fam_counts[f]}/{len(inc)}" for f in ("incident", "demand", "fault"))
        rows.append({
            "variant": variant,
            "label (oct10 plan)": VARIANT_LABELS[variant],
            "would-adopt INC (of 13)": f"{sum(e['would'] for e in inc)}/13",
            "would-adopt NOI (of 9)": f"{sum(e['would'] for e in noi)}/9",
            "INC-only median gap (log posterior)": float(np.median([e["gap"] for e in inc])),
            "INC MAP family (count)": fam_str,
        })
    caption = (
        "Source: `results/replay_diag/raw.parquet` recomputed with beta = 0.25 (posterior "
        "proportional to prior x exp(0.25 x logL), normalised over the hypotheses present in each "
        "variant/evaluation) by `final/tables/build_tables.py`; would-adopt = MAP in the incident "
        "family and gap = log P(best incident) - log max P(demand) > ln 10, as in "
        "`docs/oct10-replay-diagnosis-plan.md`; the variant labels are that plan's table. "
        f"Agreement with the stored columns: max |post - stored post| = {max_post_diff:.2e}, "
        f"max |gap - stored gap| = {max_gap_diff:.2e}, would-adopt differences = {adopt_diff}. "
        "N = 8 variants x 22 evaluations (13 INC, 9 NOI synthetic)."
    )
    write_table("t5_replay_diagnosis", caption,
                ["variant", "label (oct10 plan)", "would-adopt INC (of 13)",
                 "would-adopt NOI (of 9)", "INC-only median gap (log posterior)",
                 "INC MAP family (count)"], rows)


# --------------------------------------------------------------------------------------
# t6 - frozen audit integrity
# --------------------------------------------------------------------------------------
def build_t6() -> None:
    fr = pload("results/frozen_audit/raw.parquet")
    metrics = jload("results/frozen_audit/metrics.json")
    code = jload("results/frozen_audit/code_hashes_before_after.json")
    seed_check = jload("results/frozen_audit/seed_check.json")
    reruns = jload("results/frozen_audit/reruns.json")

    twin = fr[fr.world == "twin"]
    d300 = twin[twin.belief == "D300"]

    # rows per world / belief / status
    order = [("twin", "B"), ("twin", "D300"), ("proxy", None), ("calibration", None)]
    counts = []
    for world, belief in order:
        grp = fr[fr.world == world]
        if belief is None:
            grp = grp[grp.belief.isna()]
        else:
            grp = grp[grp.belief == belief]
        label = f"{world}/{'n/a' if belief is None else belief}"
        statuses = grp.groupby("status").size().to_dict()
        counts.append(f"{label}/" + ", ".join(f"{s} {n}" for s, n in sorted(statuses.items())))
    grid = "8 seeds x 6 replications x 5 actions"
    counts_str = "; ".join(counts) + f"; total {len(fr)} rows ({grid} per world/belief)"

    rng = metrics["rng_check"]
    rng_str = (
        f"passed = {str(rng['passed']).lower()} (seed {rng['seed']}); Twin: SUMO-seed-only differs = "
        f"{str(rng['twin']['sumo_seed_only']['differs']).lower()} "
        f"(dJ {rng['twin']['sumo_seed_only']['delta_J']:.3f}), "
        f"demand-only differs = {str(rng['twin']['demand_only']['differs']).lower()} "
        f"(dJ {rng['twin']['demand_only']['delta_J']:.3f}), identical inputs identical = "
        f"{str(rng['twin']['identical_inputs']['identical']).lower()}; Proxy: SUMO-seed-only differs = "
        f"{str(rng['proxy']['sumo_seed_only']['differs']).lower()}, demand-only differs = "
        f"{str(rng['proxy']['demand_only']['differs']).lower()}, identical inputs identical = "
        f"{str(rng['proxy']['identical_inputs']['identical']).lower()}"
    )

    rows = [
        {"check": "Rows per world / belief / status", "value": counts_str,
         "source": "results/frozen_audit/raw.parquet (groupby world, belief, status)"},

        {"check": "Reruns (infrastructure failures rerun once)",
         "value": f"{len(reruns)} reruns recorded (`reruns.json` = {json.dumps(reruns)}); "
                  "every branch row has a unique world/seed/replication/action key",
         "source": "results/frozen_audit/reruns.json; results/frozen_audit/raw.parquet"},

        {"check": "RNG isolation check", "value": rng_str,
         "source": "results/frozen_audit/metrics.json (`rng_check`), results/frozen_audit/rng_check.json"},

        {"check": "Code hashes before/after equal",
         "value": f"equal = {str(code['match']).lower()}; {len(code['before'])} files hashed, "
                  f"{sum(1 for k in code['before'] if code['before'][k] != code['after'].get(k))} differing",
         "source": "results/frozen_audit/code_hashes_before_after.json"},

        {"check": "Blocker placement range (lane, position, stop time)",
         "value": ("edge ktb_n1, requested 755.3 m, inserted at t_d = 5,100 s; 480 twin branch rows "
                   "(B 240, D300 240) x 2 blockers; lane 0 position "
                   f"{twin.blocker_pos_0.min():.4f}-{twin.blocker_pos_0.max():.4f} m, lane 1 position "
                   f"{twin.blocker_pos_1.min():.4f}-{twin.blocker_pos_1.max():.4f} m; lane 0 stop time "
                   f"{twin.blocker_t_stop_0.min():.0f}-{twin.blocker_t_stop_0.max():.0f} s, lane 1 stop "
                   f"time {twin.blocker_t_stop_1.min():.0f}-{twin.blocker_t_stop_1.max():.0f} s; "
                   "reuse_blockers = false in every twin row (blockers inserted by the branch)"),
         "source": "results/frozen_audit/raw.parquet (blocker_lane_*, blocker_pos_*, blocker_t_stop_*)"},

        {"check": "D300 release checks",
         "value": (f"{len(d300)} D300 twin rows x 2 lanes = {2 * len(d300)} release records, all "
                   "identical: present = true, stopped_at_clear = true, resumed = true, "
                   "resumed_at = 5400.0 s, stopped_after = false, checked_at = 5401.0 s, "
                   "released = true; actual_clear_time = 5400.0 s in "
                   f"{int(d300.actual_clear_time.notna().sum())}/{len(d300)} D300 rows"),
         "source": "results/frozen_audit/raw.parquet (blocker_release_0/1, actual_clear_time)"},

        {"check": "Seed-check result",
         "value": (f"passed = {str(seed_check['passed']).lower()}, "
                   f"clean = {str(seed_check['clean']).lower()}; "
                   f"{len(seed_check['seeds_checked'])} seeds checked "
                   f"({seed_check['seeds_checked'][0]}-{seed_check['seeds_checked'][-1]}), "
                   f"{len(seed_check['files_scanned'])} files scanned, "
                   f"{len(seed_check['matches'])} matches, "
                   f"{len(seed_check['scan_failures'])} scan failures"),
         "source": "results/frozen_audit/seed_check.json"},
    ]

    for path in sorted((ROOT / "results/frozen_audit/runs").glob("seed_*/two_world_info.json")):
        info = json.loads(path.read_text(encoding="utf-8"))
        alarm = info["alarm"]
        rows.append({
            "check": f"Alarm time seed {info['seed']} (t_d = 5,100 s)",
            "value": (f"first alarm {alarm['first_alarm_t']:.0f} s; latency "
                      f"{alarm['latency_s']:.0f} s; latency >= 120 s: "
                      f"{'yes' if alarm['latency_ok'] else 'no'}; "
                      f"{alarm['n_alarm_intervals']} alarm intervals"),
            "source": f"results/frozen_audit/runs/seed_{info['seed']}/two_world_info.json",
        })

    caption = ("Sources: `results/frozen_audit/raw.parquet`, `results/frozen_audit/metrics.json`, "
               "`results/frozen_audit/reruns.json`, `results/frozen_audit/code_hashes_before_after.json`, "
               "`results/frozen_audit/seed_check.json` and "
               "`results/frozen_audit/runs/seed_*/two_world_info.json`; "
               "N = 15 checks (7 integrity items + 8 per-seed alarm rows).")
    write_table("t6_frozen_validation", caption, ["check", "value", "source"], rows)


# --------------------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------------------
README = """# final/tables - evidence tables from the collected results

Built by `final/tables/build_tables.py` (reads stored artefacts only; no simulation, no tuning).
Each table exists as `.csv` (full precision) and `.md` (pipe table, 3 decimals, one-line caption
with source and N).

| table | content | sources |
|---|---|---|
| `t1_frozen_per_seed` | frozen test audit, per seed and belief (B primary, D300 secondary): a*, oracle, Top-1, G_T_hat(a*), G_P(a*), BEE signed, regret, Spearman, Kendall, floor signed, fixed-A3 G_T and G_P | `results/frozen_audit/metrics.json` `primary.per_seed`, `secondary.per_seed` |
| `t2_dev_vs_frozen_pooled` | development audit (seeds 4201-4208) beside the frozen test audit (seeds 4501-4508), never pooled, with a descriptive frozen-minus-dev difference column; B and D300 blocks | development B: `results/audit/v2/metrics_v2.json` `pooled`/`per_seed`, with G_T_hat/G_P/G_T_A3/G_P_A3 recomputed from `results/audit/raw.parquet` (part A definitions); development D300: recomputed from `results/audit/sens/raw_sens.parquet` (variant D300); frozen: `results/frozen_audit/metrics.json` `primary.pooled`, `secondary.pooled` |
| `t3_event_engine_coverage` | event-engine mechanisms: evidence level (live natural / live forced / unit only / not covered), counts with denominators, source | `results/dev_runs/outcomes/outcomes.json`; `results/event_pilot2/report.md`; `docs/decision-2026-10-06-dev-runs.md` |
| `t4_missing_queue` | per seed Q_P, Q_C, Q_H at t_d, e(C-D), e(H-D), delta_D, duration contrast under C and H, and the study classification label | `results/missing_queue/queue_td.parquet`; `results/missing_queue/metrics.json` (`queue[]`, `plan[]`, `classification`) |
| `t5_replay_diagnosis` | per variant: would-adopt counts over the 13 INC and 9 NOI evaluations, INC-only median gap, MAP-family distribution, variant labels; recomputed at beta = 0.25 | `results/replay_diag/raw.parquet`; labels from `docs/oct10-replay-diagnosis-plan.md` |
| `t6_frozen_validation` | frozen-audit integrity: rows per world/belief/status, reruns, RNG check, code hashes before/after, blocker placement range, D300 release checks, seed check, alarm time and latency per seed | `results/frozen_audit/raw.parquet`, `metrics.json`, `reruns.json`, `code_hashes_before_after.json`, `seed_check.json`, `runs/seed_*/two_world_info.json` |

## Verification performed while building

* The part A / audit v2 recomputation from `results/audit/raw.parquet` reproduces
  `results/audit/v2/metrics_v2.json` `pooled` and `per_seed` for every overlapping metric
  (max abs difference < 1e-6, exact for the rankings); this is what the development-B
  fixed-A3 rows use, since that pooled block does not contain them.
* The same definitions applied to `results/audit/sens/raw_sens.parquet` (variant D300)
  reproduce `results/audit/sens/metrics_sens.json` `variants.D300` per-seed values and pooled
  means exactly (max abs difference 7e-15; per-seed a*, oracle, G_T_hat, G_P, BEE, regret, Top-1,
  Spearman, Kendall). Its pooled t-CI bounds agree to 2.4e-7: the sens report's t multiplier
  differs from the exact t(0.975, 7) in the 8th digit, and the table uses the exact value
  (the same one that reproduces `metrics_v2.json` pooled exactly).
* The same definitions applied to `results/frozen_audit/raw.parquet` reproduce
  `results/frozen_audit/metrics.json` `primary.pooled` and `secondary.pooled` (all metrics,
  including the calibration floor and the fixed-A3 gains).
* The beta = 0.25 replay recomputation reproduces the stored `post`, `gap` and `would_adopt`
  columns of `results/replay_diag/raw.parquet` (agreement figures are printed in the t5 caption).
* Q_P/Q_C/Q_H from `results/missing_queue/queue_td.parquet` equal the `queue[]` aggregates in
  `results/missing_queue/metrics.json` (asserted in the script).
* Top-1 agreement (`a* == oracle`) is a per-seed 0/1 indicator: `t1_frozen_per_seed` shows it as
  yes/no per seed, and `t2_dev_vs_frozen_pooled` shows the exact per-seed count k/8 (B: dev 7/8,
  frozen 7/8; D300: dev 4/8, frozen 5/8) with n/a interval and difference cells, because a 95 %
  t-CI on that proportion is not meaningful and can exceed 1 (it did: 0.579-1.171). The counts
  equal the stored pooled means times 8 (`metrics_v2.json`, `results/frozen_audit/metrics.json`).

## Inferred values

No value in these tables is inferred beyond its source: every cell is either read from the
cited JSON path or recomputed from the cited Parquet with the cited definition. The only
choices made here are (a) the development-B source split described above, (b) the calibration
floor's comparison action (the floor's own R1-selected a*, which is what the stored audit
values use; the plan text is ambiguous, and using the main a* changes the dev pooled floor from
0.1808 to 0.2074), and (c) the ordering/labels of rows, which carry no numeric meaning.
"""


def main() -> None:
    build_t1()
    build_t2()
    build_t3()
    build_t4()
    build_t5()
    build_t6()
    (HERE / "README.md").write_text(README, encoding="utf-8")
    print("wrote README.md")


if __name__ == "__main__":
    main()
