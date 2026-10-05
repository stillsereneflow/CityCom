"""Development-runs outcomes analyzer: outcomes 1-9 of docs/oct13-dev-runs-plan.md (revision 2).

Reads run artefacts only -- no simulation, no SUMO, no Proxy, no re-scoring of forecasts. Run layout:
``run_info.json``, ``queue_forecasts.json``, ``proxy/`` and ``twin/{twin_log.parquet,
assim_log.parquet, event_log.jsonl, replacement_log.jsonl, state_trace.jsonl, twin_stats.json,
trigger_log.parquet}``; development runs add one level, ``<runs-dir>/<run_name>/attempt_<n>/``.

Log semantics (citypulse/twin/service.py, citypulse/twin/event.py):
* a **library** evaluation is an ``event_log.jsonl`` row logged in SUSPECTED_EVENT or DEGRADED
  (``EventRuntime.evaluate``); a **clearance** evaluation is a row logged in EVENT_ASSIMILATION
  (``EventRuntime.evaluate_clearance``);
* a **failed** evaluation is a row written by ``EventRuntime._fail``: empty ``hypotheses`` and an
  ``error`` exclusion; failures are counted, never dropped;
* an **adoption** is a successful library row with ``adopted`` true; ``forced`` marks the labelled
  integration test (``--event-force-hstar``), which is never evidence;
* a clearance record carries ``t_dec`` (the row time), ``tau_c`` (``tau_c_best``, the look-back the
  runner lifted at ``t_dec - tau_c``) and therefore ``t_clr = t_dec - tau_c``; the live release is
  the EVENT_ASSIMILATION -> RECOVERY transition in ``state_trace.jsonl``;
* ``state_trace.jsonl`` spells give exposure minutes, recovery spells and DEGRADED spells; the last
  spell is right-censored at the run's ``t_end``.

CLI: ``python -m citypulse.experiments.dev_outcomes analyze --runs-dir DIR [--slots FILE] --out DIR``.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from citypulse.twin import event as evmod

T_END_DEFAULT = 7200.0
T_ONSET = 4500.0                 # INC onset
T_CLEAR = 5400.0                 # INC clearance
T_LATE = 6300.0                  # late-decision bound (t_dec > 6300)
DELAY_CENSOR_S = 2700.0          # INC runs without an adoption: right-censored at the 7,200-s horizon
INCIDENT_EDGE = "ktb_n1"
INCIDENT_KS = (2, 1.0)
MARKS_5MIN = tuple(float(t) for t in range(4500, 6601, 300))    # 8 issue marks, 5-min horizon
MARKS_15MIN = tuple(float(t) for t in range(4500, 6301, 300))   # 7 issue marks, 15-min horizon
HORIZON_5MIN, HORIZON_15MIN = 300.0, 900.0
BLOCK_S, N_CHANNELS = evmod.BLOCK_S, len(evmod.CHANNELS)
NON_INCIDENT = ("NOI", "SHK", "DET")
STATES = (evmod.SUSPECTED, evmod.DEGRADED, evmod.EVENT, evmod.RECOVERY)
COMPLETE_STATUSES = ("complete", "complete_flagged", "complete-but-flagged", "complete_but_flagged")
EVT, CONV = "evt", "conv"


# --------------------------------------------------------------------------------------- plumbing
def _num(x):
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _read_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _f(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        return f"{x:.{nd}f}".rstrip("0").rstrip(".")
    if isinstance(x, (dict, list, tuple)):
        return json.dumps(x, default=str)
    return str(x)


def _table(headers, rows):
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_f(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------ run discovery
def run_dir_for(runs_dir, name, attempt=None):
    """The run directory of one slot: ``<runs-dir>/<name>/attempt_<n>`` or ``<runs-dir>/<name>``."""
    base = Path(runs_dir) / str(name)
    if attempt is not None:
        a = str(attempt)
        cand = base / (a if a.startswith("attempt_") else f"attempt_{a}")
        if (cand / "run_info.json").exists():
            return cand
    if (base / "run_info.json").exists():
        return base
    atts = [p for p in base.glob("attempt_*") if (p / "run_info.json").exists()]
    atts.sort(key=lambda p: int("".join(c for c in p.name if c.isdigit()) or 0))
    return atts[-1] if atts else None


def load_slots(path):
    """Read ``slots.json`` tolerantly: {slots: [...]}, {name: {...}} or [{...}].

    Each slot yields name, status and the counted attempt (``counted_attempt`` / ``attempt`` /
    ``counted`` / ``attempt_dir``); the driver's exact spelling is not fixed yet.
    """
    raw = _read_json(path)
    if isinstance(raw, dict) and isinstance(raw.get("slots"), (list, dict)):
        raw = raw["slots"]
    if isinstance(raw, dict):
        items = [dict(v, name=k) if isinstance(v, dict) else {"name": k, "status": v}
                 for k, v in raw.items()]
    elif isinstance(raw, list):
        items = list(raw)
    else:
        raise ValueError(f"unsupported slots.json structure in {path}")
    out = []
    for it in items:
        name = it.get("name") or it.get("run_name") or it.get("slot") or it.get("id")
        att = it.get("counted_attempt", it.get("latest_attempt",
                                              it.get("attempt", it.get("counted",
                                                                       it.get("attempt_dir")))))
        out.append({"name": name, "status": str(it.get("status") or it.get("state") or "").lower(),
                    "attempt": att, "raw": it})
    return out


def discover(runs_dir, slots_path=None):
    """(entries in statistics, accounting rows for every slot)."""
    runs_dir, entries, accounting = Path(runs_dir), [], []
    if slots_path:
        for s in load_slots(slots_path):
            d = run_dir_for(runs_dir, s["name"], s["attempt"]) if s["name"] else None
            ok = s["status"] in COMPLETE_STATUSES and d is not None
            accounting.append({"slot": s["name"], "status": s["status"], "attempt": s["attempt"],
                               "run_dir": None if d is None else str(d), "in_statistics": bool(ok),
                               "note": "" if d is not None else "no run directory found"})
            if ok:
                entries.append({"name": s["name"], "run_dir": d, "status": s["status"]})
        return entries, accounting
    if runs_dir.is_dir():
        for child in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            rd = run_dir_for(runs_dir, child.name)
            if rd is None:
                continue
            accounting.append({"slot": child.name, "status": "not_declared",
                               "attempt": rd.name if rd.name.startswith("attempt_") else None,
                               "run_dir": str(rd), "in_statistics": True,
                               "note": "no --slots: every run directory enters statistics"})
            entries.append({"name": child.name, "run_dir": rd, "status": "not_declared"})
    return entries, accounting


# ------------------------------------------------------------------------------------ run artefacts
def load_run(entry):
    run_dir = Path(entry["run_dir"])
    info = _read_json(run_dir / "run_info.json") or {}
    twin = run_dir / "twin"
    q = run_dir / "queue_forecasts.json"
    if not q.exists():
        q = twin / "queue_forecasts.json"
    return {"name": entry["name"], "dir": str(run_dir), "status": entry.get("status"), "info": info,
            "scenario": str(info.get("scenario") or "").upper(),
            "arm": str(info.get("arm") or "").lower(), "seed": info.get("seed"),
            "t_end": float(_num(info.get("t_end")) or T_END_DEFAULT),
            "grid": info.get("event_grid"), "force_hstar": info.get("event_force_hstar"),
            "run_forced": bool(info.get("event_force_hstar")),
            "event_rows": _read_jsonl(twin / "event_log.jsonl"),
            "transitions": _read_jsonl(twin / "state_trace.jsonl"),
            "replacements": _read_jsonl(twin / "replacement_log.jsonl"),
            "stats": _read_json(twin / "twin_stats.json") or {},
            "queue": _read_json(q), "twin_log": twin / "twin_log.parquet"}


def log_grid(run):
    """(detector ids, tick times) from ``twin_log.parquet``; ([], []) when it is missing."""
    p = run["twin_log"]
    if not p.exists():
        return [], []
    df = pd.read_parquet(p, columns=["t", "detector"])
    return sorted(df["detector"].unique().tolist()), sorted(float(t) for t in df["t"].unique())


def support_size(row, dets, ticks):
    """|O| of an evaluation row: complete 120-s blocks x detectors x channels, minus exclusions.

    The library rows log ``n_O`` per hypothesis; the clearance rows do not, so |O| is derived here
    from the logged exclusions and the run's tick grid (validated against ``n_O`` by the tests).
    """
    t_on, t_end = _num(row.get("t_on")), _num(row.get("t"))
    if t_on is None or t_end is None or not dets or not ticks:
        return None
    blocks = {}
    for t in ticks:
        if t_on < t <= t_end:
            blocks.setdefault(int(t // BLOCK_S), []).append(t)
    complete = sum(1 for ts in blocks.values() if len(ts) == 4)
    excluded = sum(v for k, v in (row.get("excluded") or {}).items()
                   if k != "partial_block" and isinstance(v, (int, float)))
    return complete * len(dets) * N_CHANNELS - excluded


def row_support(row, dets, ticks):
    hyps = row.get("hypotheses") or []
    if hyps and hyps[0].get("n_O") is not None:
        return int(hyps[0]["n_O"]), "logged"
    d = support_size(row, dets, ticks)
    return d, (None if d is None else "derived")


def hyp_of(row):
    hid = row.get("h_star")
    for h in row.get("hypotheses") or []:
        if h.get("id") == hid:
            return h
    return None


def timing_class(t):
    """Outcome 2 classes: pre-onset < 4,500; during the incident [4,500, 5,400); post-clearance."""
    if t is None:
        return None
    return ("pre_onset" if t < T_ONSET else
            ("during_incident" if t < T_CLEAR else "post_clearance"))


def failure_reason(row):
    err = str((row.get("excluded") or {}).get("error") or "unknown")
    if "no ring snapshot" in err:
        return "no_ring_snapshot"
    return (err.split(":")[0].strip() or "unknown")[:60]


def evaluation_counts(rows):
    """Outcome 1/8: library and clearance evaluations, attempted / successful / failed by reason."""
    out = {}
    for kind in ("library", "clearance"):
        out[kind] = {"attempted": 0, "successful": 0, "failed": 0, "failed_reasons": {}}
    for r in rows:
        kind = "clearance" if r.get("state") == evmod.EVENT else "library"
        rec = out[kind]
        rec["attempted"] += 1
        if r.get("hypotheses"):
            rec["successful"] += 1
        else:
            rec["failed"] += 1
            why = failure_reason(r)
            rec["failed_reasons"][why] = rec["failed_reasons"].get(why, 0) + 1
    return out


def episodes(run):
    """Every SUSPECTED_EVENT episode: entry, exit, evaluations, adoptions, clearance records."""
    trans, rows, out = run["transitions"], run["event_rows"], []
    starts = [i for i, tr in enumerate(trans) if tr.get("to") == evmod.SUSPECTED]
    for n, i in enumerate(starts):
        j = starts[n + 1] if n + 1 < len(starts) else len(trans)
        seg = trans[i:j]
        t0 = float(trans[i]["t"])
        t_next = float(trans[starts[n + 1]]["t"]) if n + 1 < len(starts) else None
        exit_tr = next((tr for tr in seg if tr.get("to") == evmod.NORMAL), None)
        evs = [r for r in rows
               if float(r["t"]) >= t0 and (t_next is None or float(r["t"]) < t_next)]
        lib = [r for r in evs if r.get("state") != evmod.EVENT and r.get("hypotheses")]
        clr = [r for r in evs if r.get("state") == evmod.EVENT]
        adopted = [r for r in lib if r.get("adopted")]
        clear_tr = next((tr for tr in seg if tr.get("from") == evmod.EVENT
                         and tr.get("to") == evmod.RECOVERY), None)
        decision_t = None if clear_tr is None else float(clear_tr["t"])
        records = []
        for r in clr:
            t = float(r["t"])
            tau = _num(r.get("tau_c_best", r.get("tau_c")))
            records.append({"t_dec": t, "tau_c": tau, "t_clr": None if tau is None else t - tau,
                            "p_clear": _num(r.get("p_clear")), "successful": bool(r.get("hypotheses")),
                            "decided": decision_t is not None and abs(t - decision_t) < 1e-9,
                            "excluded": r.get("excluded") or {}})
        last = (exit_tr is None and n + 1 == len(starts))
        out.append({"t_start": t0, "t_exit": None if exit_tr is None else float(exit_tr["t"]),
                    "exit_reason": None if exit_tr is None else exit_tr.get("reason"),
                    "library_evals": lib, "library_failed": len(evs) - len(lib) - len(clr),
                    "clearance_records": records, "adoptions": adopted,
                    "t_adopt": None if not adopted else float(adopted[0]["t"]),
                    "forced_adoption": bool(adopted and adopted[0].get("forced")),
                    "open_at_horizon": last,
                    "state_at_horizon": (trans[-1].get("to") if trans else evmod.NORMAL) if last else None})
    return out


def state_spells(transitions, t_end):
    """Non-NORMAL spells from the state trace; the last one is censored at ``t_end``."""
    spells, cur, t_cur = [], evmod.NORMAL, 0.0
    for tr in transitions:
        t = float(tr["t"])
        if cur != evmod.NORMAL:
            spells.append({"state": cur, "enter": t_cur, "exit": t, "duration_s": t - t_cur,
                           "exit_reason": tr.get("reason"), "censored": False})
        cur, t_cur = tr.get("to"), t
    if cur != evmod.NORMAL:
        spells.append({"state": cur, "enter": t_cur, "exit": None, "duration_s": t_end - t_cur,
                       "exit_reason": None, "censored": True})
    return spells


def exposure(run):
    """Outcome 1: alarm events, minutes per state, evaluations. None for the CONV arm."""
    if run["arm"] != EVT:
        return None
    ev = run["stats"].get("event") or {}
    spells = state_spells(run["transitions"], run["t_end"])
    evals = evaluation_counts(run["event_rows"])
    return {"alarm_events": sum(1 for tr in run["transitions"] if tr.get("to") == evmod.SUSPECTED
                                and tr.get("reason") == "trigger_alarm"),
            "alarm_ticks": ev.get("n_alarms"),
            "minutes": {s: sum(sp["duration_s"] for sp in spells if sp["state"] == s) / 60.0
                        for s in STATES},
            "library": evals["library"], "clearance": evals["clearance"]}


# --------------------------------------------------------------------------------------- outcomes
def adoption_records(run):
    """Every adoption row of a run with its identification fields and timing class."""
    out = []
    for ep in episodes(run):
        for row in ep["adoptions"]:
            h = hyp_of(row) or {}
            p = dict(h.get("params") or {})
            gap = _num(row.get("gap_vs_demand"))
            forced = bool(row.get("forced"))
            k = None if not p.get("lanes_closed") else len(p["lanes_closed"])
            out.append({"run": run["name"], "scenario": run["scenario"], "seed": run["seed"],
                        "t": float(row["t"]), "h_star": row.get("h_star"), "family": h.get("family"),
                        "edge": p.get("edge"), "k": k, "s": _num(p.get("speed_factor")),
                        "gap_vs_demand": gap, "gap_gt_ln10": None if gap is None else gap > evmod.TAU_LR,
                        "forced": forced, "natural": (not forced) and gap is not None
                        and gap > evmod.TAU_LR,
                        "location_correct": p.get("edge") == INCIDENT_EDGE,
                        "exact_ks": (k, _num(p.get("speed_factor"))) == INCIDENT_KS,
                        "episode_start": ep["t_start"], "timing_class": timing_class(float(row["t"])),
                        "run_forced": run["run_forced"]})
    return out


def clearance_episodes(run, adoptions):
    """Outcome 5: one row per adoption episode, with t_dec / tau_c / t_clr and its labels."""
    out = []
    by_start = {}
    for a in adoptions:
        by_start.setdefault(a["episode_start"], a)
    for ep in episodes(run):
        if ep["t_adopt"] is None:
            continue
        a = by_start.get(ep["t_start"], {})
        dec = next((r for r in ep["clearance_records"] if r["decided"]), None)
        timing = timing_class(ep["t_adopt"])
        rec = {"run": run["name"], "scenario": run["scenario"], "seed": run["seed"],
               "episode_start": ep["t_start"], "t_adopt": ep["t_adopt"],
               "h_star": a.get("h_star"), "timing_class": timing,
               "forced_adoption": ep["forced_adoption"], "run_forced": run["run_forced"],
               "n_clearance_records": len(ep["clearance_records"]),
               "n_clearance_failed": sum(1 for r in ep["clearance_records"] if not r["successful"]),
               "t_dec": None if dec is None else dec["t_dec"],
               "tau_c": None if dec is None else dec["tau_c"],
               "t_clr": None if dec is None else dec["t_clr"],
               "p_clear": None if dec is None else dec["p_clear"],
               "clearance_records": ep["clearance_records"],
               "outcome": ("cleared" if dec is not None else
                           ("overdue_right_censored" if ep["state_at_horizon"] == evmod.EVENT
                            else "ended_without_clearance")),
               "labels_apply": (run["scenario"] == "INC" and not ep["forced_adoption"]
                                and timing == "during_incident")}
        if rec["labels_apply"] and dec is not None:
            rec["premature_inference"] = rec["t_clr"] < T_CLEAR
            rec["premature_live_release"] = rec["t_dec"] < T_CLEAR
            rec["late"] = rec["t_dec"] > T_LATE
        elif run["scenario"] == "INC" and timing == "during_incident" and dec is not None:
            # a forced-run episode: the plan's labels do not apply, the same numbers are kept
            rec["premature_inference"] = rec["t_clr"] < T_CLEAR
            rec["premature_live_release"] = rec["t_dec"] < T_CLEAR
            rec["late"] = rec["t_dec"] > T_LATE
        out.append(rec)
    return out


def recovery_spells(run):
    """Outcome 6: completed / interrupted by a new trigger / censored at 7,200 s."""
    out = []
    for sp in state_spells(run["transitions"], run["t_end"]):
        if sp["state"] != evmod.RECOVERY:
            continue
        if sp["censored"]:
            cls = "censored"
        elif sp["exit_reason"] == "recovery_complete":
            cls = "completed"
        elif sp["exit_reason"] == "trigger_alarm":
            cls = "interrupted_by_trigger"
        else:
            cls = f"other:{sp['exit_reason']}"
        out.append(dict(sp, run=run["name"], scenario=run["scenario"], spell_class=cls))
    return out


def degraded_spells(run):
    """Outcome 7: resolved by adoption / scheduled timeout / censored; exit at entry + 900 s."""
    out = []
    for sp in state_spells(run["transitions"], run["t_end"]):
        if sp["state"] != evmod.DEGRADED:
            continue
        reason = sp["exit_reason"] or ""
        if sp["censored"]:
            cls = "censored"
        elif reason.startswith("adopted_"):
            cls = "resolved_by_adoption"
        elif reason == "unexplained_anomaly":
            cls = "scheduled_timeout"
        else:
            cls = f"other:{reason}"
        out.append(dict(sp, run=run["name"], scenario=run["scenario"], spell_class=cls,
                        exit_at_entry_plus_900=(None if sp["exit"] is None
                                                else abs(sp["duration_s"] - evmod.DEGRADED_MAX) < 1e-9)))
    return out


def non_incident_rows(run):
    """Outcome 4: per successful library evaluation in SHK (demand family / false-alarm path) and
    DET (fault on AID02109, type stuck)."""
    if run["scenario"] not in ("SHK", "DET"):
        return []
    trans = run["transitions"]
    fa = {float(x["t"]): x for x in (run["stats"].get("event") or {}).get("false_alarms") or []}
    out = []
    for r in run["event_rows"]:
        if not r.get("hypotheses") or r.get("state") == evmod.EVENT:
            continue
        t = float(r["t"])
        h, p = hyp_of(r) or {}, {}
        p = dict(h.get("params") or {})
        tr = next((x for x in trans if abs(float(x["t"]) - t) < 1e-9
                   and x.get("from") in (evmod.SUSPECTED, evmod.DEGRADED)), None)
        reason = (tr or {}).get("reason") or ""
        out.append({"run": run["name"], "scenario": run["scenario"], "t": t,
                    "h_star": r.get("h_star"), "family": h.get("family"),
                    "map_is_demand": h.get("family") == "demand",
                    "false_alarm_path": reason.startswith("false_alarm_demand_f"),
                    "m_written": _num((fa.get(t) or {}).get("factor")),
                    "returned_to_normal": reason.startswith("false_alarm_demand_f")
                    and (tr or {}).get("to") == evmod.NORMAL,
                    "detector": p.get("detector"), "fault_type": p.get("type"),
                    "map_is_aid02109": p.get("detector") == evmod.PAIR_U,
                    "map_is_stuck": p.get("type") == "stuck",
                    "fault_path": reason.startswith("detector_fault_")})
    return out


def exclusion_rows(run, dets, ticks):
    """Outcome 8: |O| and exclusions by reason for every library and clearance evaluation."""
    out = []
    for r in run["event_rows"]:
        kind = "clearance" if r.get("state") == evmod.EVENT else "library"
        n_o, src = row_support(r, dets, ticks)
        exc = r.get("excluded") or {}
        out.append({"run": run["name"], "kind": kind, "t": float(r["t"]),
                    "state": r.get("state"), "successful": bool(r.get("hypotheses")),
                    "n_O": n_o, "n_O_source": src, "excluded": exc,
                    "excluded_total": sum(v for k, v in exc.items()
                                          if k != "partial_block" and isinstance(v, (int, float))),
                    "error": exc.get("error")})
    return out


def forecast_cells(run):
    """Outcome 9: the required cells (8 x 5-min, 7 x 15-min) of one run; missing cell = failure."""
    q = run["queue"] or {}
    fc = q.get("forecasts") or {}
    twin = Path(run["dir"]) / "twin"
    cells, failures = [], []
    for horizon, marks, dt in (("5min", MARKS_5MIN, HORIZON_5MIN),
                               ("15min", MARKS_15MIN, HORIZON_15MIN)):
        for mark in marks:
            entry = fc.get(str(int(mark))) or {}
            sub = entry.get(horizon) or {}
            problems = []
            if not q:
                problems.append("missing_queue_forecasts_json")
            if not sub:
                problems.append("missing_forecast_entry")
            for suffix in (".json", ".xml.gz"):
                if not (twin / f"twin_state_{int(mark)}{suffix}").exists():
                    problems.append("missing_snapshot")
            pred, truth = _num(sub.get("pred")), _num(sub.get("truth"))
            if sub:
                if pred is None:
                    problems.append("missing_prediction")
                if truth is None:
                    problems.append("missing_truth")
                if _num(sub.get("target_t")) is not None \
                        and abs(_num(sub["target_t"]) - (mark + dt)) > 1e-6:
                    problems.append("wrong_target_t")
                if pred is not None and truth is not None and _num(sub.get("err")) is None:
                    problems.append("missing_error")
            problems = sorted(set(problems))
            cell = {"run": run["name"], "scenario": run["scenario"], "arm": run["arm"],
                    "seed": run["seed"], "horizon": horizon, "mark": mark, "target_t": mark + dt,
                    "pred": pred, "truth": truth, "err": _num(sub.get("err")),
                    "complete": not problems, "problems": problems}
            cells.append(cell)
            if problems:
                failures.append({"run": run["name"], "scenario": run["scenario"], "arm": run["arm"],
                                 "seed": run["seed"], "horizon": horizon, "mark": mark,
                                 "reasons": problems})
    return cells, failures


def analyse_run(run):
    """Every outcome of one run, with its own denominators."""
    dets, ticks = log_grid(run)
    adoptions = adoption_records(run)
    natural = [a for a in adoptions if a["natural"]]
    evals = evaluation_counts(run["event_rows"])
    cells, ffail = forecast_cells(run)
    defects = []
    for a in adoptions:
        if not a["forced"] and not a["natural"]:
            defects.append(f"adoption at {a['t']} is not forced but gap <= ln 10")
    out = {"name": run["name"], "dir": run["dir"], "status": run["status"],
           "scenario": run["scenario"], "arm": run["arm"], "seed": run["seed"],
           "t_end": run["t_end"], "grid": run["grid"], "force_hstar": run["force_hstar"],
           "run_forced": run["run_forced"], "evaluations": evals, "adoptions": adoptions,
           "exposure": exposure(run), "clearance": clearance_episodes(run, adoptions),
           "recovery_spells": recovery_spells(run), "degraded_spells": degraded_spells(run),
           "non_incident": non_incident_rows(run), "exclusions": exclusion_rows(run, dets, ticks),
           "forecast_cells": cells, "forecast_failures": ffail, "defects": defects,
           "n_episodes": len(episodes(run))}
    if run["arm"] == EVT:
        lib_ok = evals["library"]["successful"]
        out["natural_adoption"] = {
            "applicable": run["scenario"] == "INC",
            "n": len(natural) if run["scenario"] == "INC" else None,
            "n_forced": sum(1 for a in adoptions if a["forced"]) if run["scenario"] == "INC" else None,
            "any": (len(natural) > 0) if run["scenario"] == "INC" else None,
            "first_t": natural[0]["t"] if (natural and run["scenario"] == "INC") else None,
            "delay_s": (natural[0]["t"] - T_ONSET) if (natural and run["scenario"] == "INC") else None,
            "delay_censored_at": (DELAY_CENSOR_S if (run["scenario"] == "INC" and not natural)
                                  else None),
            "denominator_successful_library_evals": lib_ok,
            "rate": (len(natural) / lib_ok) if (run["scenario"] == "INC" and lib_ok) else None}
        false_ad = [a for a in adoptions if not a["forced"]]
        out["false_adoption"] = {
            "applicable": run["scenario"] in NON_INCIDENT,
            "n": len(false_ad) if run["scenario"] in NON_INCIDENT else None,
            "denominator_successful_library_evals": lib_ok,
            "rate": (len(false_ad) / lib_ok) if (run["scenario"] in NON_INCIDENT and lib_ok) else None}
    else:
        out["natural_adoption"] = out["false_adoption"] = None
    return out


def analyse(entries):
    runs = [analyse_run(load_run(e)) for e in entries]
    failures = [f for r in runs for f in r["forecast_failures"]]
    return {"runs": runs, "failures": failures}


# ----------------------------------------------------------------------------------------- pooling
def _sum_evals(recs):
    out = {"attempted": 0, "successful": 0, "failed": 0, "failed_reasons": {}}
    for r in recs:
        for k in ("attempted", "successful", "failed"):
            out[k] += r.get(k, 0)
        for why, n in (r.get("failed_reasons") or {}).items():
            out["failed_reasons"][why] = out["failed_reasons"].get(why, 0) + n
    return out


def _counts(xs):
    out = {}
    for x in xs:
        out[str(x)] = out.get(str(x), 0) + 1
    return dict(sorted(out.items()))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else sum(xs) / len(xs)


def pool_scenario(ev):
    """Pooled numbers of one scenario over its EVT runs, each with its denominator."""
    p = {"n_evt_runs": len(ev), "minutes": {}, "excluded_reasons": {}}
    p["alarm_events"] = sum((r["exposure"] or {}).get("alarm_events") or 0 for r in ev)
    for s in STATES:
        p["minutes"][s] = sum((r["exposure"] or {}).get("minutes", {}).get(s, 0.0) for r in ev)
    p["library"] = _sum_evals([r["evaluations"]["library"] for r in ev])
    p["clearance"] = _sum_evals([r["evaluations"]["clearance"] for r in ev])
    lib_ok = p["library"]["successful"]
    nat = [a for r in ev for a in r["adoptions"] if a["natural"]]
    with_ad = sum(1 for r in ev if r["natural_adoption"] and r["natural_adoption"]["any"])
    p["natural_adoption"] = {
        "n": len(nat), "n_forced": sum(1 for r in ev for a in r["adoptions"] if a["forced"]),
        "runs_with_adoption": with_ad, "n_runs": len(ev),
        "runs_censored": len(ev) - with_ad,
        "denominator_successful_library_evals": lib_ok,
        "rate": None if not lib_ok else len(nat) / lib_ok,
        "timing_classes": _counts(a["timing_class"] for a in nat),
        "location_correct": sum(1 for a in nat if a["location_correct"]),
        "exact_ks": sum(1 for a in nat if a["exact_ks"]),
        "ks_values": _counts(f"k{a['k']}_s{a['s']}" for a in nat),
        "from_forced_runs": sum(1 for a in nat if a["run_forced"])}
    false_ad = [a for r in ev for a in r["adoptions"] if not a["forced"]]
    p["false_adoption"] = {"n": len(false_ad), "runs_with_adoption": sum(
        1 for r in ev if r["false_adoption"] and r["false_adoption"]["n"]),
        "n_runs": len(ev), "denominator_successful_library_evals": lib_ok,
        "rate": None if not lib_ok else len(false_ad) / lib_ok}
    ni = [x for r in ev for x in r["non_incident"]]
    p["non_incident"] = {"n_evals": len(ni), "map_is_demand": sum(1 for x in ni if x["map_is_demand"]),
                         "false_alarm_path": sum(1 for x in ni if x["false_alarm_path"]),
                         "returned_to_normal": sum(1 for x in ni if x["returned_to_normal"]),
                         "map_is_aid02109": sum(1 for x in ni if x["map_is_aid02109"]),
                         "map_is_stuck": sum(1 for x in ni if x["map_is_stuck"])}
    eps = [x for r in ev for x in r["clearance"]]
    p["clearance_episodes"] = {
        "n": len(eps), "timing_classes": _counts(x["timing_class"] for x in eps),
        "outcomes": _counts(x["outcome"] for x in eps),
        "labelled": sum(1 for x in eps if x["labels_apply"])}
    for flag in ("premature_inference", "premature_live_release", "late"):
        p["clearance_episodes"][flag] = sum(1 for x in eps if x.get(flag))
        p["clearance_episodes"][flag + "_labelled"] = sum(1 for x in eps
                                                          if x["labels_apply"] and x.get(flag))
        p["clearance_episodes"][flag + "_forced"] = sum(1 for x in eps
                                                        if not x["labels_apply"] and x.get(flag))
    rec = [x for r in ev for x in r["recovery_spells"]]
    p["recovery_spells"] = {"n": len(rec), "classes": _counts(x["spell_class"] for x in rec),
                            "duration_s": {c: [x["duration_s"] for x in rec if x["spell_class"] == c]
                                           for c in sorted({x["spell_class"] for x in rec})}}
    deg = [x for r in ev for x in r["degraded_spells"]]
    p["degraded_spells"] = {"n": len(deg), "classes": _counts(x["spell_class"] for x in deg),
                            "exit_at_entry_plus_900": sum(1 for x in deg
                                                          if x["exit_at_entry_plus_900"]),
                            "live_covered": any(x["spell_class"] == "scheduled_timeout"
                                                and x["exit_at_entry_plus_900"] for x in deg)}
    ex = [x for r in ev for x in r["exclusions"]]
    for kind in ("library", "clearance"):
        rows = [x for x in ex if x["kind"] == kind]
        p[f"exclusions_{kind}"] = {
            "n_evals": len(rows), "n_successful": sum(1 for x in rows if x["successful"]),
            "n_O": [x["n_O"] for x in rows],
            "reasons": {k: sum(x["excluded"].get(k, 0) for x in rows)
                        for k in sorted({k for x in rows for k in x["excluded"]})}}
    return p


def pooled(runs):
    out = {}
    for scen in sorted({r["scenario"] for r in runs}):
        out[scen] = pool_scenario([r for r in runs if r["arm"] == EVT and r["scenario"] == scen])
        out[scen]["n_runs"] = sum(1 for r in runs if r["scenario"] == scen)
    return out


def forecast_summary(runs):
    """Outcome 9 pooled: per arm/scenario/horizon and the paired EVT - CONV differences."""
    cells = [c for r in runs for c in r["forecast_cells"]]
    groups = {}
    for c in cells:
        groups.setdefault((c["arm"], c["scenario"], c["horizon"]), []).append(c)
    arms = []
    for (arm, scen, hz), cs in sorted(groups.items()):
        comp = [c for c in cs if c["complete"] and c["err"] is not None]
        errs = [c["err"] for c in comp]
        arms.append({"arm": arm, "scenario": scen, "horizon": hz, "required_cells": len(cs),
                     "complete_cells": len(comp), "failed_cells": len(cs) - len(comp),
                     "denominator_cells": len(errs), "mae": _mean([abs(e) for e in errs]),
                     "mean_signed_error": _mean(errs)})
    index = {(c["scenario"], c["seed"], c["horizon"], c["mark"], c["arm"]): c for c in cells}
    pairs = {}
    for (scen, seed, hz, mark, arm), c in index.items():
        if arm != EVT or not c["complete"] or c["err"] is None:
            continue
        o = index.get((scen, seed, hz, mark, CONV))
        if o is None or not o["complete"] or o["err"] is None:
            continue
        pairs.setdefault((scen, hz, seed), []).append(abs(c["err"]) - abs(o["err"]))
    per_seed = [{"scenario": k[0], "horizon": k[1], "seed": k[2], "n_pairs": len(v),
                 "mean_evt_minus_conv_abs_error": _mean(v)} for k, v in sorted(pairs.items())]
    flat = {}
    for (scen, hz, seed), v in pairs.items():
        flat.setdefault((scen, hz), []).extend(v)
    overall = [{"scenario": k[0], "horizon": k[1], "n_pairs": len(v),
                "mean_evt_minus_conv_abs_error": _mean(v)} for k, v in sorted(flat.items())]
    return {"arms": arms, "pairs_per_seed": per_seed, "pairs_pooled": overall}


# ------------------------------------------------------------------------------------------ report
def _recs(rows, cols):
    return [[r.get(c) for c in cols] for r in rows]


def build_report(res, accounting, pools, fsum):
    runs, L = res["runs"], []
    L.append("# Development-runs outcomes (docs/oct13-dev-runs-plan.md revision 2, outcomes 1-9)\n")
    L.append(f"Runs analysed: {len(runs)}. Descriptive counts and means only: no inference, no "
             "acceptance criteria, no tuning. Every rate carries its denominator.\n")
    L.append("## Accounting\n")
    L.append(_table(["slot", "status", "attempt", "run_dir", "in_statistics", "note"],
                    _recs(accounting, ["slot", "status", "attempt", "run_dir", "in_statistics",
                                       "note"])))
    L.append("\n## Outcome 1: exposure\n")
    L.append(_table(["run", "scenario", "arm", "seed", "alarm_events", "alarm_ticks", "min_SUSPECTED",
                     "min_DEGRADED", "min_EVENT", "min_RECOVERY", "lib_attempted", "lib_successful",
                     "lib_failed", "clr_attempted", "clr_successful", "clr_failed"],
                    [[r["name"], r["scenario"], r["arm"], r["seed"],
                      (r["exposure"] or {}).get("alarm_events"), (r["exposure"] or {}).get("alarm_ticks"),
                      *[(r["exposure"] or {}).get("minutes", {}).get(s) for s in STATES],
                      r["evaluations"]["library"]["attempted"], r["evaluations"]["library"]["successful"],
                      r["evaluations"]["library"]["failed"], r["evaluations"]["clearance"]["attempted"],
                      r["evaluations"]["clearance"]["successful"],
                      r["evaluations"]["clearance"]["failed"]] for r in runs]))
    L.append("\nPooled per scenario (EVT runs):\n")
    L.append(_table(["scenario", "n_runs", "n_evt_runs", "alarm_events", "min_SUSPECTED", "min_DEGRADED",
                     "min_EVENT", "min_RECOVERY", "lib_a/s/f", "clr_a/s/f"],
                    [[s, p["n_runs"], p["n_evt_runs"], p["alarm_events"],
                      *[p["minutes"][x] for x in STATES],
                      f'{p["library"]["attempted"]}/{p["library"]["successful"]}/{p["library"]["failed"]}',
                      f'{p["clearance"]["attempted"]}/{p["clearance"]["successful"]}/'
                      f'{p["clearance"]["failed"]}'] for s, p in pools.items()]))
    L.append("\n## Outcome 2: natural adoption (INC, EVT)\n")
    inc = [r for r in runs if r["scenario"] == "INC" and r["arm"] == EVT]
    L.append(_table(["run", "successful_library_evals", "natural_adoptions", "rate", "any",
                     "first_t", "timing_class", "delay_s", "delay_censored_at", "forced_adoptions"],
                    [[r["name"], r["natural_adoption"]["denominator_successful_library_evals"],
                      r["natural_adoption"]["n"], r["natural_adoption"]["rate"],
                      r["natural_adoption"]["any"], r["natural_adoption"]["first_t"],
                      (next((a["timing_class"] for a in r["adoptions"] if a["natural"]), None)),
                      r["natural_adoption"]["delay_s"], r["natural_adoption"]["delay_censored_at"],
                      r["natural_adoption"]["n_forced"]] for r in inc]))
    p = pools.get("INC", {})
    n = p.get("natural_adoption", {})
    if not n:
        L.append("\nNo INC runs analysed: no natural-adoption numbers.\n")
    else:
        L.append(f"\nPooled INC: {n.get('runs_with_adoption')}/{n.get('n_runs')} runs with an "
                 f"adoption; {n.get('runs_censored')} right-censored at {_f(DELAY_CENSOR_S)} s. "
                 f"Adoptions {n.get('n')} / {n.get('denominator_successful_library_evals')} successful "
                 f"library evaluations = {_f(n.get('rate'))}. Timing classes: "
                 f"{n.get('timing_classes')}. From forced runs: {n.get('from_forced_runs')}.\n")
    nat = [a for r in inc for a in r["adoptions"] if a["natural"]]
    L.append("\nIdentification over all natural INC adoptions:\n")
    L.append(_table(["run", "t", "h_star", "edge", "k", "s", "gap_vs_demand", "gap_gt_ln10",
                     "location_correct", "exact_ks", "timing_class", "forced"],
                    _recs(nat, ["run", "t", "h_star", "edge", "k", "s", "gap_vs_demand",
                                "gap_gt_ln10", "location_correct", "exact_ks", "timing_class",
                                "forced"])))
    if n:
        L.append(f"\nLocation correct (edge {INCIDENT_EDGE}): {n.get('location_correct')}/"
                 f"{n.get('n')}. Exact (k, s) = {INCIDENT_KS}: {n.get('exact_ks')}/{n.get('n')}. "
                 f"(k, s) values: {n.get('ks_values')}.\n")
    L.append("\n## Outcome 3: false adoption (NOI / SHK / DET, EVT)\n")
    L.append(_table(["run", "scenario", "successful_library_evals", "adoptions", "rate"],
                    [[r["name"], r["scenario"], r["false_adoption"]["denominator_successful_library_evals"],
                      r["false_adoption"]["n"], r["false_adoption"]["rate"]]
                     for r in runs if r["arm"] == EVT and r["scenario"] in NON_INCIDENT]))
    for s in NON_INCIDENT:
        if s not in pools:
            L.append(f"\n{s}: no runs analysed.\n")
            continue
        f = pools[s]["false_adoption"]
        L.append(f"\n{s}: {f.get('n')} adoptions / "
                 f"{f.get('denominator_successful_library_evals')} successful library evaluations = "
                 f"{_f(f.get('rate'))}; {f.get('runs_with_adoption')}/{f.get('n_runs')} runs with an "
                 "adoption.\n")
    L.append("\n## Outcome 4: non-incident handling, per successful library evaluation\n")
    L.append(_table(["run", "scenario", "t", "h_star", "family", "map_is_demand", "false_alarm_path",
                     "m_written", "returned_to_normal", "detector", "fault_type", "map_is_aid02109",
                     "map_is_stuck", "fault_path"],
                    _recs([x for r in runs for x in r["non_incident"]],
                          ["run", "scenario", "t", "h_star", "family", "map_is_demand",
                           "false_alarm_path", "m_written", "returned_to_normal", "detector",
                           "fault_type", "map_is_aid02109", "map_is_stuck", "fault_path"])))
    for s in ("SHK", "DET"):
        if s not in pools:
            L.append(f"\n{s}: no runs analysed.\n")
            continue
        ni = pools[s]["non_incident"]
        L.append(f"\n{s}: {ni.get('n_evals')} successful library evaluations; MAP in the demand "
                 f"family {ni.get('map_is_demand')}; false-alarm path {ni.get('false_alarm_path')} "
                 f"(returned to NORMAL {ni.get('returned_to_normal')}); MAP fault on "
                 f"{evmod.PAIR_U} {ni.get('map_is_aid02109')}, type stuck {ni.get('map_is_stuck')}.\n")
    L.append("\n## Outcome 5: clearance per adoption episode\n")
    L.append(_table(["run", "scenario", "seed", "episode_start", "t_adopt", "h_star", "timing_class",
                     "forced_adoption", "run_forced", "n_clearance_records", "t_dec", "tau_c", "t_clr",
                     "p_clear", "outcome", "labels_apply", "premature_inference",
                     "premature_live_release", "late"],
                    _recs([x for r in runs for x in r["clearance"]],
                          ["run", "scenario", "seed", "episode_start", "t_adopt", "h_star",
                           "timing_class", "forced_adoption", "run_forced", "n_clearance_records",
                           "t_dec", "tau_c", "t_clr", "p_clear", "outcome", "labels_apply",
                           "premature_inference", "premature_live_release", "late"])))
    L.append("\nEvery executed clearance record (t_dec, tau_c, t_clr, p_clear) is in outcomes.json "
             "under `clearance_records`; the episode row uses the deciding record.\n")
    for s, pp in pools.items():
        c = pp["clearance_episodes"]
        if not c["n"]:
            continue
        L.append(f"\n{s}: {c['n']} adoption episodes; timing classes {c['timing_classes']}; outcomes "
                 f"{c['outcomes']}; labelled (natural INC during the incident) {c['labelled']}: "
                 f"premature inference {c['premature_inference_labelled']}, premature live release "
                 f"{c['premature_live_release_labelled']}, late {c['late_labelled']}; forced-run "
                 f"episodes with the same numbers: {c['premature_inference_forced']}/"
                 f"{c['premature_live_release_forced']}/{c['late_forced']}.\n")
    L.append("\n## Outcome 6: recovery spells\n")
    L.append(_table(["run", "scenario", "enter", "exit", "duration_s", "spell_class", "exit_reason"],
                    _recs([x for r in runs for x in r["recovery_spells"]],
                          ["run", "scenario", "enter", "exit", "duration_s", "spell_class",
                           "exit_reason"])))
    for s, pp in pools.items():
        c = pp["recovery_spells"]
        if c["n"]:
            L.append(f"\n{s}: {c['n']} spells; {c['classes']}; durations "
                     f"{ {k: [_f(x) for x in v] for k, v in c['duration_s'].items()} }.\n")
    L.append("\n## Outcome 7: DEGRADED spells (live)\n")
    L.append(_table(["run", "scenario", "enter", "exit", "duration_s", "spell_class",
                     "exit_at_entry_plus_900", "exit_reason"],
                    _recs([x for r in runs for x in r["degraded_spells"]],
                          ["run", "scenario", "enter", "exit", "duration_s", "spell_class",
                           "exit_at_entry_plus_900", "exit_reason"])))
    for s, pp in pools.items():
        if not pp["n_evt_runs"]:
            continue
        c = pp["degraded_spells"]
        L.append(f"\n{s}: {c['n']} spells; {c['classes']}; exits at entry + "
                 f"{_f(evmod.DEGRADED_MAX)} s exactly: {c['exit_at_entry_plus_900']}; exit "
                 f"live-covered: {'yes' if c['live_covered'] else 'no'}.\n")
    L.append("\n## Outcome 8: exclusions\n")
    L.append(_table(["run", "kind", "t", "state", "successful", "n_O", "n_O_source",
                     "excluded_total", "excluded", "error"],
                    _recs([x for r in runs for x in r["exclusions"]],
                          ["run", "kind", "t", "state", "successful", "n_O", "n_O_source",
                           "excluded_total", "excluded", "error"])))
    for s, pp in pools.items():
        for kind in ("library", "clearance"):
            e = pp[f"exclusions_{kind}"]
            if e["n_evals"]:
                L.append(f"\n{s} {kind}: {e['n_evals']} evaluations ({e['n_successful']} successful); "
                         f"|O| {e['n_O']}; exclusions by reason {e['reasons']}.\n")
    L.append("\n## Outcome 9: forecasts (halting on ktb_w3 + ktb_n1, scored offline)\n")
    L.append(_table(["arm", "scenario", "horizon", "required_cells", "complete_cells", "failed_cells",
                     "denominator_cells", "mae", "mean_signed_error"],
                    _recs(fsum["arms"], ["arm", "scenario", "horizon", "required_cells",
                                         "complete_cells", "failed_cells", "denominator_cells", "mae",
                                         "mean_signed_error"])))
    L.append("\nPaired EVT - CONV absolute-error differences, per seed (complete pairs only):\n")
    L.append(_table(["scenario", "horizon", "seed", "n_pairs", "mean_evt_minus_conv_abs_error"],
                    _recs(fsum["pairs_per_seed"], ["scenario", "horizon", "seed", "n_pairs",
                                                   "mean_evt_minus_conv_abs_error"])))
    L.append("\nPaired, pooled over seeds (complete pairs only):\n")
    L.append(_table(["scenario", "horizon", "n_pairs", "mean_evt_minus_conv_abs_error"],
                    _recs(fsum["pairs_pooled"], ["scenario", "horizon", "n_pairs",
                                                 "mean_evt_minus_conv_abs_error"])))
    L.append("\n## Failures\n")
    if res["failures"]:
        L.append(_table(["run", "scenario", "arm", "seed", "horizon", "mark", "reasons"],
                        _recs(res["failures"], ["run", "scenario", "arm", "seed", "horizon", "mark",
                                                "reasons"])))
    else:
        L.append("No required forecast cell is missing or failed.\n")
    failed = {f"{r['name']}": r["evaluations"] for r in runs
              if r["evaluations"]["library"]["failed"] or r["evaluations"]["clearance"]["failed"]}
    for name, e in failed.items():
        L.append(f"\nFailed evaluations in {name}: library {e['library']['failed']} "
                 f"{e['library']['failed_reasons']}, clearance {e['clearance']['failed']} "
                 f"{e['clearance']['failed_reasons']}.\n")
    defects = [f"{r['name']}: {d}" for r in runs for d in r["defects"]]
    L.append("\nDefects: " + ("; ".join(defects) if defects else "none recorded") + "\n")
    return "\n".join(L)


def write_outputs(out_dir, res, accounting, pools, fsum):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"runs": {r["name"]: r for r in res["runs"]}, "pooled": pools,
               "forecasts": fsum, "accounting": accounting, "failures": res["failures"],
               "definitions": {"t_onset": T_ONSET, "t_clear": T_CLEAR, "t_late": T_LATE,
                               "delay_censor_s": DELAY_CENSOR_S,
                               "degraded_exit_s": evmod.DEGRADED_MAX,
                               "incident_edge": INCIDENT_EDGE, "incident_ks": list(INCIDENT_KS),
                               "marks_5min": list(MARKS_5MIN), "marks_15min": list(MARKS_15MIN)}}
    (out_dir / "outcomes.json").write_text(json.dumps(payload, indent=1, default=str),
                                           encoding="utf-8")
    (out_dir / "report.md").write_text(build_report(res, accounting, pools, fsum), encoding="utf-8")
    return out_dir


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dev_outcomes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="analyse development-run artefacts (no simulation)")
    a.add_argument("--runs-dir", required=True)
    a.add_argument("--slots", default=None, help="slots.json; only complete/complete_flagged count")
    a.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    entries, accounting = discover(args.runs_dir, args.slots)
    res = analyse(entries)
    pools = pooled(res["runs"])
    fsum = forecast_summary(res["runs"])
    out_dir = write_outputs(args.out, res, accounting, pools, fsum)
    print(json.dumps({"runs_analysed": len(res["runs"]), "slots": len(accounting),
                      "forecast_failures": len(res["failures"]), "out": str(out_dir)}))
    return res


if __name__ == "__main__":
    main()
