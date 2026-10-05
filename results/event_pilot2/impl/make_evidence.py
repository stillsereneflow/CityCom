"""Pilot-2 artefact-based mechanics evidence (docs/oct6-audit-and-pilot2-plan.md part B).

Every check is labelled **live** (exercised inside a real pilot-2 two-world run), **direct** (measured
on the run artefacts or by an extra replay) or **unit** (pinned by tests/test_event.py). Nothing here
re-runs a two-world simulation; the replay-based checks 2/4/7 live in ``check_replays.py``.

Reads:  results/event_pilot2/runs/<run>/{run_info.json,twin/*}
Writes: results/event_pilot2/evidence/{check1_firewall,check3_identical_support,check5_freeze,
        check6_adoption_threshold,check8_clearance,check9_nonincident,check10_degraded,
        adoption_summary}.json
Usage:  python results/event_pilot2/impl/make_evidence.py
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.experiments.event_pilot import degraded_durations  # noqa: E402
from citypulse.twin import event as ev  # noqa: E402

RUNS = REPO / "results/event_pilot2/runs"
EVIDENCE = REPO / "results/event_pilot2/evidence"
FORCED = ("evtforce_inc_4101", "evtforce_inc_4102", "evtforce_inc_4103")
INC_EVT = ("evt_inc_4101", "evt_inc_4102", "evt_inc_4103")
INC_CONV = ("conv_inc_4101", "conv_inc_4102", "conv_inc_4103")
NOI_EVT = ("evt_noi_4101", "evt_noi_4102", "evt_noi_4103")
FROZEN_STATES = (ev.SUSPECTED, ev.EVENT)


def jload(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_dir(name):
    return RUNS / name


def existing(names):
    return [n for n in names if (run_dir(n) / "run_info.json").exists()]


def stats_of(name):
    return jload(run_dir(name) / "twin/twin_stats.json", {}) or {}


def event_of(name):
    return (stats_of(name).get("event") or {})


def transitions_of(name):
    return event_of(name).get("transitions") or []


def event_rows(name):
    return jsonl(run_dir(name) / "twin/event_log.jsonl")


def write(name, obj):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    print(f"wrote evidence/{name}")


# ------------------------------------------------------------------ check 1: firewall
def check1():
    runs = existing(INC_EVT + INC_CONV + NOI_EVT + FORCED)
    cols, bad = {}, []
    for n in runs:
        p = run_dir(n) / "twin/twin_log.parquet"
        if not p.exists():
            continue
        c = list(pd.read_parquet(p).columns)
        cols[n] = c
        bad += [f"{n}:{x}" for x in c if "proxy" in x.lower() or "truth" in x.lower()]
    src = {f: (REPO / f).read_text(encoding="utf-8")
           for f in ("citypulse/twin/event.py", "citypulse/twin/service.py")}
    imports_proxy = {f: ("citypulse.proxy" in t or "from citypulse import proxy" in t)
                     for f, t in src.items()}
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/test_firewall.py", "-q"],
                          cwd=str(REPO), capture_output=True, text=True)
    out = {
        "check": "1", "name": "firewall_integrity", "label": "direct (unit: tests/test_firewall.py)",
        "twin_log_columns": cols,
        "truth_or_proxy_columns_found": bad,
        "twin_modules_import_proxy": imports_proxy,
        "test_firewall": {"returncode": proc.returncode,
                          "tail": (proc.stdout or "").strip().splitlines()[-1:]},
        "n_runs_inspected": len(cols),
    }
    out["passed"] = bool(not bad and not any(imports_proxy.values()) and proc.returncode == 0)
    write("check1_firewall.json", out)
    return out


# ------------------------------------------------------------------ check 3: identical support
def check3():
    runs = existing(INC_EVT + NOI_EVT + FORCED)
    per_run, violations = {}, []
    for n in runs:
        rows = event_rows(n)
        n_o, clearance_rows = [], 0
        for r in rows:
            if not r.get("hypotheses"):
                continue
            if any("n_O" not in h for h in r["hypotheses"]):
                clearance_rows += 1        # clearance rows carry logL/post but not n_O
                continue
            s = {h["n_O"] for h in r["hypotheses"]}
            n_o.append({"t": r["t"], "state": r["state"], "n_O": sorted(s),
                        "n_hypotheses": len(r["hypotheses"]),
                        "identical": len(s) == 1})
            if len(s) != 1:
                violations.append({"run": n, "t": r["t"], "n_O": sorted(s)})
        per_run[n] = {"n_evaluations": len(rows), "n_scored": len(n_o),
                      "n_clearance_rows": clearance_rows, "rows": n_o}
    out = {
        "check": "3", "name": "identical_scoring_support",
        "label": "direct (event_log.jsonl) + unit (tests/test_event.py)",
        "runs": per_run, "violations": violations,
        "rule": "every hypothesis of an evaluation reports the same n_O (the intersection support O)",
    }
    out["passed"] = bool(not violations and any(v["n_scored"] for v in per_run.values()))
    write("check3_identical_support.json", out)
    return out


# ------------------------------------------------------------------ check 5: regional freeze
def state_at(transitions, t):
    """The state in force at t, from the transition trace."""
    st = ev.NORMAL
    for tr in transitions:
        if float(tr["t"]) <= float(t) + 1e-9:
            st = tr["to"]
        else:
            break
    return st


def check5():
    runs = existing(INC_EVT + FORCED)
    per_run, violations = {}, []
    for n in runs:
        tr = transitions_of(n)
        ap = run_dir(n) / "twin/assim_log.parquet"
        if not ap.exists():
            continue
        a = pd.read_parquet(ap)
        frozen = a[a["reason"] == "frozen"]
        slow = a[a["reason"] == "degraded_slow"]
        m_frozen = [float(x) for x in frozen["m"]]
        # every frozen tick must sit inside a SUSPECTED/EVENT interval and hold one single m
        states = [state_at(tr, t) for t in frozen["t"]]
        wrong_state = [{"t": float(t), "state": s} for t, s in zip(frozen["t"], states)
                       if s not in FROZEN_STATES]
        spread = None if not m_frozen else round(max(m_frozen) - min(m_frozen), 12)
        # the m written into the ring/snapshot metas during a freeze must equal that constant
        snap_m = {}
        for p in sorted(run_dir(n).glob("twin/twin_state_*.json")):
            meta = jload(p, {})
            t = float(meta.get("t"))
            st = state_at(tr, t)
            if st in FROZEN_STATES:
                snap_m[str(int(t))] = {"state": st, "m": (meta.get("m") or {}).get(ev.BASE_FACTOR_ENTRY)}
        snap_vals = {round(v["m"], 12) for v in snap_m.values() if v["m"] is not None}
        if spread not in (None, 0.0):
            violations.append({"run": n, "frozen_m_spread": spread, "m_values": sorted(set(m_frozen))})
        if wrong_state:
            violations.append({"run": n, "frozen_tick_outside_suspected_or_event": wrong_state})
        if len(snap_vals) > 1:
            violations.append({"run": n, "frozen_snapshot_m_values": sorted(snap_vals)})
        per_run[n] = {
            "frozen_ticks": int(len(frozen)), "frozen_m_values": sorted(set(m_frozen)),
            "frozen_m_spread": spread,
            "degraded_slow_ticks": int(len(slow)),
            "degraded_slow_m_values": sorted({round(float(x), 6) for x in slow["m"]}),
            "snapshots_during_freeze": snap_m,
            "transitions": tr,
        }
    out = {
        "check": "5", "name": "exact_regional_freeze",
        "label": "direct (assim_log.parquet + twin_state_*.json + state_trace) + unit",
        "rule": ("while SUSPECTED_EVENT or EVENT_ASSIMILATION the frozen entry's m is held exactly "
                 "(reason `frozen`); DEGRADED's slow rule is the only frozen-state update and is "
                 "logged as `degraded_slow`"),
        "runs": per_run, "violations": violations,
    }
    out["passed"] = bool(not violations and any(v["frozen_ticks"] for v in per_run.values()))
    write("check5_freeze.json", out)
    return out


# ------------------------------------------------------------------ check 6: adoption threshold
def check6():
    runs = existing(INC_EVT + NOI_EVT + FORCED)
    rows, violations = [], []
    for n in runs:
        for r in event_rows(n):
            if not r.get("hypotheses") or r.get("h_star") is None or r.get("p_clear") is not None:
                continue
            fam = next((h["family"] for h in r["hypotheses"] if h["id"] == r["h_star"]), None)
            rec = {"run": n, "t": r["t"], "state": r["state"], "h_star": r["h_star"], "family": fam,
                   "gap_vs_demand": r["gap_vs_demand"], "adopted": r["adopted"],
                   "forced": bool(r.get("forced"))}
            rows.append(rec)
            if r["adopted"]:
                if r.get("forced"):
                    continue                      # labelled integration test, reported separately
                if fam != "incident" or not (r["gap_vs_demand"] > math.log(10.0)):
                    violations.append(rec)
    out = {
        "check": "6", "name": "threshold_respecting_adoption",
        "label": "unit (rule) + direct (audit of every adopted row on disk)",
        "rule": "natural adoption requires h* in the incident family and gap > ln 10 = 2.302585",
        "tau_lr": ev.TAU_LR,
        "natural_adoptions": [r for r in rows if r["adopted"] and not r["forced"]],
        "forced_adoptions": [r for r in rows if r["adopted"] and r["forced"]],
        "rows": rows, "violations": violations,
    }
    out["passed"] = bool(not violations)
    write("check6_adoption_threshold.json", out)
    return out


# ------------------------------------------------------------------ check 8: clearance rules
def recovery_spells(tr):
    out, t0 = [], None
    for x in tr:
        if x["to"] == ev.RECOVERY:
            t0 = float(x["t"])
        elif x["from"] == ev.RECOVERY and t0 is not None:
            out.append({"enter": t0, "exit": float(x["t"]), "duration_s": float(x["t"]) - t0,
                        "reason": x["reason"]})
            t0 = None
    if t0 is not None:
        out.append({"enter": t0, "exit": None, "duration_s": None, "reason": "still_in_recovery"})
    return out


def recovery_blockers(name, t_enter, t_exit):
    """Why a RECOVERY spell did or did not exit: the 60-s exit-condition counters."""
    tp = run_dir(name) / "twin/trigger_log.parquet"
    lp = run_dir(name) / "twin/twin_log.parquet"
    if not tp.exists() or not lp.exists():
        return None
    tr = pd.read_parquet(tp).set_index("t")
    tl = pd.read_parquet(lp)
    obs = tl[tl.detector.isin([ev.PAIR_U, ev.PAIR_D])].pivot(index="t", columns="detector",
                                                             values="obs_o")
    df = tr.join(obs)
    end = float(t_exit) if t_exit is not None else float(df.index.max())
    sub = df[(df.index >= float(t_enter)) & (df.index <= end)]
    ticks = sub[[int(round(t)) % 60 == 0 for t in sub.index]]      # recovery_tick cadence
    return {
        "ticks": int(len(ticks)),
        "ticks_b_below_1.5": int((ticks["B"] < ev.B_EXIT).sum()),
        "ticks_b_at_or_above_1.5": int((ticks["B"] >= ev.B_EXIT).sum()),
        "ticks_b_null": int(ticks["B"].isna().sum()),
        "ticks_o_u_below_15": int((ticks[ev.PAIR_U] < ev.O_CRIT).sum()),
        "ticks_o_d_below_15": int((ticks[ev.PAIR_D] < ev.O_CRIT).sum()),
        "ticks_both_o_below_15": int(((ticks[ev.PAIR_U] < ev.O_CRIT)
                                      & (ticks[ev.PAIR_D] < ev.O_CRIT)).sum()),
    }


def check8():
    runs = existing(FORCED) or existing(INC_EVT)
    per_run, violations = {}, []
    for n in runs:
        tr = transitions_of(n)
        rows = event_rows(n)
        clear_rows = [r for r in rows if r.get("p_clear") is not None]
        spell = recovery_spells(tr)
        enter = next((x for x in tr if x["to"] == ev.EVENT), None)
        reps = jsonl(run_dir(n) / "twin/replacement_log.jsonl")
        clear_rep = [r for r in reps if r["kind"] == "clearance"]
        if enter is None:
            continue
        # every RECOVERY entry must be preceded by two consecutive clearance evaluations > 0.7
        spells = []
        for rec in [x for x in tr if x["to"] == ev.RECOVERY]:
            pre = [r for r in clear_rows if float(r["t"]) <= float(rec["t"]) + 1e-9]
            last_two = pre[-2:]
            two_above = bool(len(last_two) == 2 and all(r["p_clear"] > ev.P_CLEAR_THRESHOLD
                                                        for r in last_two))
            exit_tr = next((x for x in tr if x["from"] == ev.RECOVERY and x["t"] >= rec["t"]), None)
            sp = next((s for s in spell if s["enter"] == rec["t"]), {})
            duration = sp.get("duration_s")
            blockers = recovery_blockers(n, rec["t"], None if exit_tr is None else exit_tr["t"])
            spells.append({
                "recovery_enter": rec["t"],
                "p_clear_last_two": [r["p_clear"] for r in last_two],
                "two_consecutive_above_0.7": two_above,
                "recovery_exit": None if exit_tr is None else exit_tr["t"],
                "recovery_exit_reason": None if exit_tr is None else exit_tr["reason"],
                "duration_s": duration,
                "duration_at_least_180": bool(duration is None or duration >= ev.RECOVERY_MIN),
                "blockers": blockers,
            })
            if not two_above:
                violations.append({"run": n, "t": rec["t"],
                                   "why": "recovery not preceded by two p_clear > 0.7"})
            if duration is not None and duration < ev.RECOVERY_MIN:
                violations.append({"run": n, "t": rec["t"], "why": "recovery shorter than 180 s"})
        if not clear_rep:
            violations.append({"run": n, "why": "no clearance replacement logged"})
        per_run[n] = {
            "adopted_at": enter["t"], "adoption_reason": enter["reason"],
            "clearance_evaluations": [{"t": r["t"], "p_clear": r["p_clear"],
                                       "tau_c_best": r.get("tau_c_best")} for r in clear_rows],
            "recovery_spells": spells,
            "recovery_enter": spells[0]["recovery_enter"] if spells else None,
            "recovery_exit": spells[0]["recovery_exit"] if spells else None,
            "recovery_exit_reason": spells[0]["recovery_exit_reason"] if spells else None,
            "two_consecutive_above_0.7_before_recovery":
                spells[0]["two_consecutive_above_0.7"] if spells else False,
            "recovery_min_ok": all(s["duration_at_least_180"] for s in spells) if spells else False,
            "clearance_replacements": clear_rep,
            "n_evaluations": len(rows),
        }
    out = {
        "check": "8", "name": "clearance_rules",
        "label": "live (forced-adoption runs' event/state/replacement logs) + unit",
        "rule": ("two consecutive p_clear > 0.7 -> lift the restriction, replay from S(tau_c - delta), "
                 "mask the pair, RECOVERY >= 180 s, exit on the unmasked B < 1.5 for 3 min and both "
                 "ends o < 15%"),
        "runs": per_run, "violations": violations,
    }
    spells = [s for v in per_run.values() for s in v["recovery_spells"]]
    out["n_recovery_spells"] = len(spells)
    out["n_spells_exited_recovery_complete"] = sum(
        1 for s in spells if s["recovery_exit_reason"] == "recovery_complete")
    out["n_spells_still_in_recovery_at_horizon"] = sum(1 for s in spells if s["recovery_exit"] is None)
    out["n_spells_left_by_new_trigger"] = sum(
        1 for s in spells if s["recovery_exit_reason"] == "trigger_alarm")
    out["caveat"] = ("the rules hold in every spell; the exit conditions were met inside the horizon "
                     "in %d of %d spells (the others were still in RECOVERY at t = 7,200 s, or left it "
                     "through a new trigger after unmasking, which the spec allows)"
                     % (out["n_spells_exited_recovery_complete"], len(spells)))
    out["passed"] = bool(per_run and not violations)
    write("check8_clearance.json", out)
    return out


# ------------------------------------------------------------------ check 9: non-incident rejection
def check9():
    per_run, violations = {}, []
    for n in existing(NOI_EVT):
        e = event_of(n)
        rows = event_rows(n)
        adopted = [r for r in rows if r.get("adopted")]
        per_run[n] = {"n_alarms": e.get("n_alarms"), "n_eval": e.get("n_eval"),
                      "n_replacements": e.get("n_replacements"), "n_adopted": len(adopted),
                      "false_alarms": e.get("false_alarms"), "unexplained": e.get("unexplained"),
                      "state": e.get("state"), "transitions": e.get("transitions")}
        if adopted or e.get("n_replacements"):
            violations.append({"run": n, "n_adopted": len(adopted)})
    out = {
        "check": "9", "name": "non_incident_rejection", "label": "direct (NOI EVT runs)",
        "note": ("pilot 2 runs NOI only (part B, 'Runs'); SHK and DET were pilot-1 controls and are not "
                 "re-run here, so no SHK/DET adoption count is claimed for pilot 2"),
        "runs": per_run, "violations": violations,
    }
    out["passed"] = bool(per_run and not violations)
    write("check9_nonincident.json", out)
    return out


# ------------------------------------------------------------------ check 10: bounded DEGRADED
def check10():
    per_run, violations = {}, []
    for n in existing(INC_EVT + FORCED):
        tr = transitions_of(n)
        spells = degraded_durations(tr)
        per_run[n] = {"spells": spells, "max_duration_s": max([s["duration_s"] for s in spells
                                                              if s["duration_s"] is not None],
                                                             default=None),
                      "degraded_exit": event_of(n).get("degraded_exit")}
        for s in spells:
            if s["duration_s"] is not None and s["duration_s"] > ev.DEGRADED_MAX:
                violations.append({"run": n, "spell": s})
    out = {
        "check": "10", "name": "bounded_unresolved_handling",
        "label": ("unit (scheduled exit at entry + 900 s; no DEGRADED spell occurred in any pilot-2 "
                  "run, so it was not exercised live)"),
        "rule": "DEGRADED leaves at exactly entry + 900 s on the 30-s tick (pilot 2); <= 15 min",
        "runs": per_run, "violations": violations,
        "live_exercised": any(v["spells"] for v in per_run.values()),
        "unit_tests": ["tests/test_event.py::test_degraded_exit_is_scheduled_at_exactly_entry_plus_900"
                       "_and_needs_no_evaluation",
                       "tests/test_event.py::test_degraded_tick_is_inert_in_the_pilot1_mode",
                       "tests/test_event.py::test_degraded_still_adopts_just_before_the_scheduled_exit"],
    }
    out["passed"] = bool(not violations)
    write("check10_degraded.json", out)
    return out


def best_of_family(row, family):
    hs = [h for h in row["hypotheses"] if h["family"] == family]
    if not hs:
        return None
    return max(hs, key=lambda h: h["post"])


def incident_gap(row):
    """The incident family's own reading: best incident member and its log-posterior gap vs demand."""
    inc, dem = best_of_family(row, "incident"), best_of_family(row, "demand")
    if inc is None or dem is None or inc["post"] <= 0 or dem["post"] <= 0:
        return None
    return {"h_inc_best": inc["id"], "params": inc["params"], "post_inc_best": inc["post"],
            "h_demand_best": dem["id"], "post_demand_best": dem["post"],
            "log_gap_inc_vs_demand": math.log(inc["post"]) - math.log(dem["post"]),
            "log_gap_inc_vs_map": math.log(inc["post"]) - math.log(max(h["post"]
                                                                       for h in row["hypotheses"]))}


# ------------------------------------------------------------------ adoption / EVR summary
def adoption_summary():
    runs = existing(INC_EVT + FORCED)
    per_run = {}
    for n in runs:
        e = event_of(n)
        rows = event_rows(n)
        scored = [r for r in rows if r.get("hypotheses") and r.get("p_clear") is None]
        clear = [r for r in rows if r.get("p_clear") is not None]
        nat = [r for r in scored if r.get("adopted") and not r.get("forced")]
        frc = [r for r in scored if r.get("adopted") and r.get("forced")]
        adoptions = [{"t": float(t["t"]), "hypothesis": str(t["reason"]).split("adopted_", 1)[-1],
                      "forced": bool(next((r.get("forced") for r in scored
                                           if float(r["t"]) == float(t["t"])), False))}
                     for t in (e.get("transitions") or [])
                     if str(t.get("reason", "")).startswith("adopted_")]
        per_run[n] = {
            "run_info": jload(run_dir(n) / "run_info.json", {}),
            "alarms": e.get("alarms"), "n_alarms": e.get("n_alarms"), "n_eval": e.get("n_eval"),
            "transitions": e.get("transitions"),
            "adoptions": adoptions,
            "natural_adoption": bool(nat),
            "natural_adoption_rows": [{"t": r["t"], "h_star": r["h_star"],
                                       "gap_vs_demand": r["gap_vs_demand"], "evr": r["evr"]}
                                      for r in nat],
            "forced_adoption_rows": [{"t": r["t"], "h_star": r["h_star"], "evr": r["evr"]}
                                     for r in frc],
            "t_adopt": adoptions[0]["t"] if adoptions else None,
            "adopt_hyp": adoptions[0]["hypothesis"] if adoptions else None,
            "active_hyp": e.get("active_hyp"),
            "unexplained": e.get("unexplained"), "false_alarms": e.get("false_alarms"),
            "downweight": e.get("downweight"), "n_replacements": e.get("n_replacements"),
            "evaluations": [{
                "t": r["t"], "state": r["state"], "h_star": r["h_star"],
                "h_star_family": next((h["family"] for h in r["hypotheses"] if h["id"] == r["h_star"]),
                                      None),
                "h_star_params": next((h["params"] for h in r["hypotheses"] if h["id"] == r["h_star"]),
                                      None),
                "logL_h_star": next((h["logL"] for h in r["hypotheses"] if h["id"] == r["h_star"]),
                                    None),
                "post_h_star": next((h["post"] for h in r["hypotheses"] if h["id"] == r["h_star"]),
                                    None),
                "n_O": next((h["n_O"] for h in r["hypotheses"]), None),
                "gap_vs_demand": r["gap_vs_demand"], "evr": r["evr"], "adopted": r["adopted"],
                "forced": bool(r.get("forced")), "excluded": r.get("excluded"),
                "incident": incident_gap(r),
                "top5": sorted(r["hypotheses"], key=lambda h: -h["post"])[:5],
                "wall_s": r.get("wall_s")} for r in scored],
            "clearance_evaluations": [{"t": r["t"], "p_clear": r["p_clear"],
                                       "tau_c_best": r.get("tau_c_best"),
                                       "excluded": r.get("excluded")} for r in clear],
            "degraded_spells": degraded_durations(e.get("transitions") or []),
        }
    out = {"runs": per_run,
           "natural_adoptions": {n: v["natural_adoption"] for n, v in per_run.items()},
           "natural_adoptions_inc_evt": {n: per_run[n]["natural_adoption"]
                                         for n in INC_EVT if n in per_run},
           "any_natural_adoption_inc_evt": any(per_run[n]["natural_adoption"]
                                               for n in INC_EVT if n in per_run),
           "natural_adoptions_forced": {n: per_run[n]["natural_adoption"]
                                        for n in FORCED if n in per_run},
           "any_natural_adoption": any(v["natural_adoption"] for v in per_run.values())}
    write("adoption_summary.json", out)
    return out


def main():
    results = {"check1": check1(), "check3": check3(), "check5": check5(), "check6": check6(),
               "check8": check8(), "check9": check9(), "check10": check10()}
    summ = adoption_summary()
    print(json.dumps({k: v["passed"] for k, v in results.items()}, indent=1))
    print(json.dumps({"any_natural_adoption": summ["any_natural_adoption"],
                      "natural_adoptions": summ["natural_adoptions"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
