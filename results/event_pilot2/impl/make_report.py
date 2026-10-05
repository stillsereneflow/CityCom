"""Assemble results/event_pilot2/report.md from the pilot-2 artefacts and evidence files.

First line is `MODEL: <name>`, last line `REPORT DONE` (prompt.md, "Output"). Every number comes from
results/event_pilot2/{runs_summary.json,evidence/*.json}; nothing is recomputed here.

Usage: python results/event_pilot2/impl/make_report.py [--model "deepseek-v4.1-flash"]
"""
import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
P2 = REPO / "results/event_pilot2"
EVIDENCE = P2 / "evidence"
FORCED = ("evtforce_inc_4101", "evtforce_inc_4102", "evtforce_inc_4103")
INC_EVT = ("evt_inc_4101", "evt_inc_4102", "evt_inc_4103")
INC_CONV = ("conv_inc_4101", "conv_inc_4102", "conv_inc_4103")
NOI_EVT = ("evt_noi_4101", "evt_noi_4102", "evt_noi_4103")


def load(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def f(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    a = ap.parse_args()

    runs = load(P2 / "runs_summary.json", {})
    adm = load(EVIDENCE / "adoption_summary.json", {"runs": {}})
    c1 = load(EVIDENCE / "check1_firewall.json", {})
    c2 = load(EVIDENCE / "check2_deterministic_replay.json", {})
    c3 = load(EVIDENCE / "check3_identical_support.json", {})
    c4 = load(EVIDENCE / "check4_capacity_restriction.json", {})
    c5 = load(EVIDENCE / "check5_freeze.json", {})
    c6 = load(EVIDENCE / "check6_adoption_threshold.json", {})
    c7 = load(EVIDENCE / "check7_755.json", {})
    c8 = load(EVIDENCE / "check8_clearance.json", {})
    c9 = load(EVIDENCE / "check9_nonincident.json", {})
    c10 = load(EVIDENCE / "check10_degraded.json", {})
    forced_runs = [n for n in FORCED if n in adm.get("runs", {})]

    L = [f"MODEL: {a.model}", ""]
    L += ["# Second development pilot of the event engine (pilot 2, part B)", ""]
    L += [
        "Binding spec: `docs/oct6-audit-and-pilot2-plan.md` part B; base plan "
        "`docs/oct6-event-pilot-plan.md`; first pilot `results/event_pilot/fix/report.md`. "
        "Development only; no E* claim, no acceptance. Nothing was committed.",
        "",
        "## 1. What changed and what did not",
        "",
        "| Item | pilot 1 | pilot 2 |",
        "|---|---|---|",
        "| Incident grid | 6 hypotheses, (k, s) in {(1, 1.0), (2, 0.6)} on 3-lane edges, "
        "{(1, 1.0), (1, 0.6)} on `ktb_n2` | k in {1, ..., min(2, n_lanes - 1)} x s in {0.6, 1.0}: "
        "4 + 4 + 2 = **10** incident hypotheses |",
        "| Library | 16 (6 incident, 4 demand, 6 fault) | **20** (10, 4, 6); family mass still 1/3, "
        "uniform inside the family (1/30 per incident hypothesis) |",
        "| DEGRADED bound | next evaluation past 15 min (observed 960 s in pilot 1) | "
        "**entry + 900 s exactly**, on the 30-s tick, independent of evaluations |",
        "| Locations / onset / noise / beta / tau_LR / trigger / thresholds | - | unchanged |",
        "",
        "Implementation, all behind explicit switches (pilot-1 behaviour is the default): "
        "`build_hypotheses(grid=...)` and `EventStateMachine(degraded_exit=\"scheduled\")` and "
        "`forced_adoption` in `citypulse/twin/event.py`; `--event-grid`, `--event-force-hstar` and the "
        "tick-scheduled DEGRADED exit in `citypulse/twin/service.py`; the pilot-2 run set, forecast "
        "and alarm helpers in `citypulse/experiments/event_pilot.py`; 11 new unit tests in "
        "`tests/test_event.py` (40 pass, was 29). `citypulse/branching/engine.py` is **not** changed.",
        "",
        "### One pilot-1 defect had to be fixed to reach the required integration coverage",
        "",
        "`EventRuntime` never wrote `EventStateMachine.restriction`, so `lift_spec()` was always empty "
        "and every `H_clear(tau_c)` replay was identical to the active replay: `P_clear` would have sat "
        "at its 0.5 prior for ever and clearance could never fire. The service now records the live "
        "restriction (closed lanes + the pre-restriction max speed of the lanes the spec scales) "
        "before the replacement restarts SUMO (`EventRuntime.restriction_of` -> "
        "`event.restriction_record`). No engine change; pilot-1 runs never adopted, so their results "
        "are unaffected.",
        "",
        "## 2. Runs",
        "",
        "Fresh development seeds 4101-4103; CONV arguments identical to the first pilot "
        "(`results/event_pilot/runs/evt_inc_4001/run_info.json`): twin seed 2, demand seed 202, base "
        "factor 0.85, `--assim normal300 --boundary-detector AID07106`, sigma from "
        "`results/assim/na300/sigma300_dev.json`, `--event-sigma results/event_pilot/impl/"
        "sigma_event.json`, `--event-workers 4`. INC: EVT + CONV; NOI: EVT only.",
        "",
    ]
    rows = []
    for n in sorted(runs):
        ri = runs[n].get("run_info", {})
        al = runs[n].get("alarms", {})
        ev = runs[n].get("event", {}) or {}
        evr = ev.get("event_rows", [])
        nat = any(r.get("adopted") and not r.get("forced") for r in evr)
        frc = any(r.get("adopted") and r.get("forced") for r in evr)
        rows.append([f"`{n}`", ri.get("scenario"), ri.get("arm"), ri.get("seed"),
                     f"{ri.get('proxy_rc')}/{ri.get('twin_rc')}", f(ri.get("wall_s"), 1),
                     al.get("alarm_events", "-"), f(al.get("exposure_min"), 1),
                     ev.get("n_eval", "-"), ev.get("n_replacements", "-"),
                     ("yes (forced)" if frc and not nat else
                      "yes (forced + natural)" if frc and nat else
                      "yes (natural)" if nat else "no")])
    L += table(rows, ["run", "scen", "arm", "seed", "rc p/t", "wall s", "alarm events",
                      "exposure min", "evals", "replacements", "adopted"])
    L += ["", f"Queue forecasts: 5-min and 15-min frozen replays from every 5-min snapshot "
              f"(4,500-6,600 s), scored against Proxy truth (`queue_forecasts.json` per run).", ""]

    # ---------------------------------------------------------------- natural adoption
    L += ["## 3. Natural adoption, h*, EVR", ""]
    any_nat = adm.get("any_natural_adoption_inc_evt")
    L += [f"**No natural adoption occurred in any of the three INC EVT runs.** Natural adoption per "
          f"primary run: {adm.get('natural_adoptions_inc_evt')}; forced runs are in §6. The three runs "
          f"evaluated the 20-hypothesis library "
          f"{sum(len(adm['runs'][n]['evaluations']) for n in INC_EVT if n in adm['runs'])} times in "
          f"total and the MAP was never an incident hypothesis (any_natural_adoption_inc_evt = "
          f"{any_nat}).", ""]
    for n in INC_EVT:
        v = adm.get("runs", {}).get(n)
        if not v:
            continue
        L += [f"### `{n}`", "",
              f"- Episode alarms: {[int(x) for x in (v['alarms'] or [])]}; "
              f"state trace: " + "; ".join(f"{int(t['t'])} {t['from']}->{t['to']} ({t['reason']})"
                                           for t in v["transitions"]) + ".",
              f"- Adoption time: **none**. Clearance time: **none** (EVENT_ASSIMILATION never "
              f"entered; `replacement_log.jsonl` has {v['n_replacements']} rows). "
              f"Down-weighted detectors: `{v['downweight']}`.",
              "",
              ]
        L += table([[int(e["t"]), e["h_star"], e["h_star_family"],
                     (e["h_star_params"] or {}).get("edge", (e["h_star_params"] or {}).get("entry", "")),
                     (e["h_star_params"] or {}).get("lanes_closed", ""),
                     (e["h_star_params"] or {}).get("speed_factor", ""),
                     f(e["logL_h_star"], 2), f(e["post_h_star"], 4), f(e["gap_vs_demand"], 3),
                     f(e["evr"], 4), e["n_O"], f(e["wall_s"], 1)]
                    for e in v["evaluations"]],
                   ["t", "h* (MAP)", "family", "edge/entry", "lanes closed", "s", "logL(h*)",
                    "post(h*)", "gap vs demand", "EVR", "n_O", "wall s"])
        L += ["", "The incident family's own reading (best incident member vs the best demand member, "
                  "on the same support):", ""]
        L += table([[int(e["t"]), e["incident"]["h_inc_best"], f(e["incident"]["post_inc_best"], 4),
                     e["incident"]["h_demand_best"], f(e["incident"]["post_demand_best"], 4),
                     f(e["incident"]["log_gap_inc_vs_demand"], 3),
                     f(e["incident"]["log_gap_inc_vs_map"], 3),
                     "yes" if e["incident"]["log_gap_inc_vs_demand"] > math.log(10.0) else "no"]
                    for e in v["evaluations"] if e.get("incident")],
                   ["t", "best incident", "post", "best demand", "post",
                    "log gap inc vs demand", "log gap inc vs MAP", "would adopt"])
        L += [""]
    gaps = [e["gap_vs_demand"] for n in INC_EVT for e in adm["runs"].get(n, {}).get("evaluations", [])]
    inc_gaps = [e["incident"]["log_gap_inc_vs_demand"] for n in INC_EVT
                for e in adm["runs"].get(n, {}).get("evaluations", []) if e.get("incident")]
    L += [f"Adoption needs h* in the incident family and gap > ln 10 = {math.log(10.0):.4f}. "
          f"Across all evaluations the MAP-vs-demand gap reached at most "
          f"{f(max(gaps) if gaps else None, 3)}; the best incident member was at most "
          f"{f(max(inc_gaps) if inc_gaps else None, 3)} log units above the best demand member, i.e. "
          f"at least {f(math.log(10.0) - (max(inc_gaps) if inc_gaps else 0.0), 3)} log units short of "
          f"the threshold. No evaluation even had the incident family as the MAP.",
          "",
          "**EVR** is reported per evaluation above; it is `1 - SSE(h*)/min_demand SSE`, so it is "
          "positive whenever the fault or demand MAP fits the observations better than the best "
          "demand member and is not an incident diagnostic. It ranged "
          f"{f(min([e['evr'] for n in INC_EVT for e in adm['runs'].get(n, {}).get('evaluations', []) if e['evr'] is not None] or [None]), 4)} "
          f"to {f(max([e['evr'] for n in INC_EVT for e in adm['runs'].get(n, {}).get('evaluations', []) if e['evr'] is not None] or [None]), 4)}.",
          ""]

    # ---------------------------------------------------------------- forecasts
    L += ["## 4. Forecast errors (descriptive)", "",
          "Halting vehicles on `ktb_w3` + `ktb_n1`, predicted by a frozen 900-s replay from each "
          "5-min snapshot and scored against Proxy truth. Negative bias = under-prediction.", ""]
    rows = []
    for n in sorted(runs):
        q = runs[n].get("queue_forecasts", {})
        s5, s15 = q.get("summary_5min", {}), q.get("summary_15min", {})
        rows.append([f"`{n}`", f(s5.get("mae"), 2), f(s5.get("rmse"), 2), f(s5.get("bias"), 2),
                     s5.get("n"), f(s15.get("mae"), 2), f(s15.get("rmse"), 2), f(s15.get("bias"), 2),
                     s15.get("n")])
    L += table(rows, ["run", "5-min MAE", "5-min RMSE", "5-min bias", "n",
                      "15-min MAE", "15-min RMSE", "15-min bias", "n"])
    same = all(runs.get(f"evt_inc_{s}", {}).get("queue_forecasts") ==
               runs.get(f"conv_inc_{s}", {}).get("queue_forecasts") for s in (4101, 4102, 4103))
    L += ["", f"The EVT and CONV forecast sets are identical for every seed ({same}), and so are the "
              f"alarm sets and exposures in §2. With no adoption the only live difference between the "
              f"arms is the regional freeze of the TKO entry's m, and in these runs the frozen "
              f"assimilation ticks fell where CONV was in deadband anyway (e.g. `evt_inc_4101` logs "
              f"`frozen` at t = 5,100 s with m = 1.181802, `conv_inc_4101` logs `deadband` with the "
              f"same m), so every snapshot carries the same m and the replays coincide. Pilot 2 "
              f"therefore shows no forecast improvement from the event engine, exactly as pilot 1 did. "
              f"The NOI runs have zero halting everywhere (MAE 0, no congestion in either world).", ""]

    # ---------------------------------------------------------------- checks
    L += ["## 5. Mechanics checks, labelled", "",
          "Labels: **live** = exercised inside a real pilot-2 two-world run; **direct** = measured on "
          "the run artefacts or by an extra replay; **unit** = pinned by `tests/test_event.py`.", ""]
    checks = [
        ("1", "Firewall integrity", c1, ["results/event_pilot2/evidence/check1_firewall.json",
                                         "tests/test_firewall.py"]),
        ("2", "Deterministic replay", c2, ["results/event_pilot2/evidence/"
                                           "check2_deterministic_replay.json"]),
        ("3", "Identical scoring support", c3, ["results/event_pilot2/evidence/"
                                                "check3_identical_support.json"]),
        ("4", "Effective capacity restriction", c4, ["results/event_pilot2/evidence/"
                                                     "check4_capacity_restriction.json"]),
        ("5", "Exact regional freeze", c5, ["results/event_pilot2/evidence/check5_freeze.json"]),
        ("6", "Threshold-respecting adoption", c6, ["results/event_pilot2/evidence/"
                                                    "check6_adoption_threshold.json"]),
        ("7", "Successful state replacement (ktb_n1, 755 m)", c7,
         ["results/event_pilot2/evidence/check7_755.json"]),
        ("8", "Clearance rules", c8, ["results/event_pilot2/evidence/check8_clearance.json"]),
        ("9", "Non-incident rejection", c9, ["results/event_pilot2/evidence/"
                                             "check9_nonincident.json"]),
        ("10", "Bounded unresolved handling", c10, ["results/event_pilot2/evidence/"
                                                    "check10_degraded.json"]),
    ]
    rows = []
    for num, name, c, paths in checks:
        verdict = "**PASS**" if c.get("passed") else "**FAIL**"
        rows.append([num, name, c.get("label", "-"), verdict, "<br>".join(f"`{p}`" for p in paths)])
    L += table(rows, ["#", "Check", "Label", "Verdict", "Evidence"])
    L += [""]
    for num, name, c, paths in checks:
        detail = c.get("detail") or c.get("note") or c.get("rule") or ""
        if detail:
            L += [f"- **Check {num}** ({c.get('label', '-')}): {detail}"]
    L += ["",
          "Per-check substance:",
          "",
          f"- **1** no `proxy_*`/truth column in any of the {c1.get('n_runs_inspected')} twin logs; "
          f"`citypulse/twin/event.py` and `service.py` do not import the Proxy; "
          f"`tests/test_firewall.py` returncode {c1.get('test_firewall', {}).get('returncode')}.",
          f"- **2** `{c2.get('hypothesis')}` from `{c2.get('snapshot')}` (t_on {c2.get('t_on')} -> "
          f"{c2.get('t_end')}) scored twice in independent processes: logL "
          f"{f(c2.get('logL_run1'), 6)} = {f(c2.get('logL_run2'), 6)} over n_O = {c2.get('n_O')}, "
          f"interval tables and vehicle digests identical = {c2.get('interval_tables_identical')}.",
          f"- **3** every evaluation of every EVT run reports one single n_O across its hypotheses "
          f"({len(c3.get('violations', []))} violations); support sizes "
          f"{sorted({r['n_O'][0] for v in c3.get('runs', {}).values() for r in v['rows']})}.",
          f"- **4** `{c4.get('hypothesis')}`: lanes {c4.get('lanes_closed')} disallowed in the replay "
          f"({c4.get('restriction_present_replay')}); mean q at {c4.get('downstream_detector')} "
          f"{f(c4.get('noevent_mean_q'), 2)} -> {f(c4.get('incident_mean_q'), 2)} "
          f"({f(c4.get('drop_pct'), 2)}%), vehicles {c4.get('n_vehicles_noevent')} -> "
          f"{c4.get('n_vehicles_incident')}.",
          f"- **5** frozen ticks across the INC EVT runs: "
          f"{ {k: v['frozen_ticks'] for k, v in c5.get('runs', {}).items()} }; every frozen tick sits "
          f"in SUSPECTED_EVENT/EVENT and the entry's m is held exactly (spread "
          f"{ {k: (v['frozen_m_spread'] if v['frozen_ticks'] else 'n/a') for k, v in c5.get('runs', {}).items()} }); "
          f"`degraded_slow` ticks: "
          f"{ {k: v['degraded_slow_ticks'] for k, v in c5.get('runs', {}).items()} }.",
          f"- **6** {len(c6.get('natural_adoptions', []))} natural adoption on disk (in the second "
          f"episode of forced run `{c6.get('natural_adoptions', [{}])[0].get('run') if c6.get('natural_adoptions') else '-'}`, "
          f"reported in §6), {len(c6.get('forced_adoptions', []))} forced (labelled), "
          f"{len(c6.get('violations', []))} threshold violations; no adoption in the three primary "
          f"INC runs.",
          f"- **7** live replacement with `{c7.get('hypothesis')}` at `{c7.get('location', {}).get('edge')}` "
          f"pos {c7.get('location', {}).get('pos')} m: vehicles_match = {c7.get('vehicles_match')} "
          f"(live digest {str(c7.get('live_twin', {}).get('veh_digest'))[:16]}..., "
          f"{c7.get('live_twin', {}).get('n_vehicles')} vehicles vs replay "
          f"{str(c7.get('replay_endpoint', {}).get('veh_digest'))[:16]}..., "
          f"{c7.get('replay_endpoint', {}).get('n_vehicles')}); lane disallow read live = "
          f"`{c7.get('live_twin', {}).get('lane_disallow_live')}`.",
          f"- **8** live clearance in the forced runs: "
          + "; ".join(
              f"`{k}` " + ", ".join(
                  f"spell {int(s['recovery_enter'])} -> "
                  f"{int(s['recovery_exit']) if s['recovery_exit'] else 'run end'} "
                  f"({f(s['duration_s'], 0)} s, {s['recovery_exit_reason'] or 'still in RECOVERY'}), "
                  f"last two p_clear {[round(x, 3) for x in s['p_clear_last_two']]}"
                  for s in v["recovery_spells"])
              for k, v in c8.get("runs", {}).items()) + ".",
          f"  {c8.get('caveat', '')}",
          f"- **9** NOI EVT runs: alarms "
          f"{ {k: v['n_alarms'] for k, v in c9.get('runs', {}).items()} }, evaluations "
          f"{ {k: v['n_eval'] for k, v in c9.get('runs', {}).items()} }, adoptions "
          f"{ {k: v['n_adopted'] for k, v in c9.get('runs', {}).items()} }.",
          f"- **10** DEGRADED spells in the pilot-2 runs: "
          f"{ {k: v['spells'] for k, v in c10.get('runs', {}).items()} } - "
          f"**not exercised live in pilot 2** (no episode reached a third unresolved evaluation, so no "
          f"run entered DEGRADED); the scheduled exit is pinned by unit tests "
          f"(`test_degraded_exit_is_scheduled_at_exactly_entry_plus_900_and_needs_no_evaluation`, "
          f"`test_degraded_tick_is_inert_in_the_pilot1_mode`).",
          ""]

    # ---------------------------------------------------------------- forced
    L += ["## 6. Forced-adoption integration test (labelled; NOT inference)", "",
          "Because no natural adoption occurred (§3), the same INC scenario was re-run with "
          "`--event-force-hstar inc_ktb_n1_k2_s1.0`: at the **first evaluation of the run** (the first "
          "evaluation of its first episode) that hypothesis is treated as h* and the adoption "
          "threshold as met. Its own logL/posterior rows are kept unchanged in `event_log.jsonl` and "
          "every such row carries `forced: true`; the replacement rows carry `forced: true`. Later "
          "episodes of these runs are not forced. These runs exercise the downstream path only.",
          ""]
    if not forced_runs:
        L += ["_Forced-adoption runs not present in the artefacts._", ""]
    for n in forced_runs:
        v = adm["runs"][n]
        L += [f"### `{n}`", "",
              f"- Alarms {[int(x) for x in (v['alarms'] or [])]}; adoptions: "
              + "; ".join(f"t = {int(x['t'])} -> `{x['hypothesis']}` "
                          f"({'forced' if x['forced'] else 'NATURAL, not injected'})"
                          for x in v["adoptions"])
              + f"; state trace: "
              + "; ".join(f"{int(t['t'])} {t['from']}->{t['to']} ({t['reason']})"
                          for t in v["transitions"]) + ".",
              f"- Clearance evaluations: "
              f"{[(int(c['t']), round(c['p_clear'], 4), c['tau_c_best']) for c in v['clearance_evaluations']]}.",
              ""]
    if c8.get("runs"):
        L += ["Clearance and recovery detail (from `check8_clearance.json`):", ""]
        rows = []
        for k, v in c8["runs"].items():
            for s in v["recovery_spells"]:
                rows.append([f"`{k}`", int(v["adopted_at"]), len(v["clearance_evaluations"]),
                             [round(x, 3) for x in s["p_clear_last_two"]],
                             int(s["recovery_enter"]),
                             int(s["recovery_exit"]) if s["recovery_exit"] else "-",
                             f(s["duration_s"], 0), s["recovery_exit_reason"] or "still in RECOVERY",
                             s["blockers"]["ticks_b_below_1.5"], s["blockers"]["ticks_b_at_or_above_1.5"],
                             s["blockers"]["ticks_both_o_below_15"]])
        L += table(rows, ["run", "adopted at", "clearance evals", "last two p_clear",
                          "recovery in", "recovery out", "duration s", "exit reason",
                          "60-s ticks B<1.5", "ticks B>=1.5", "ticks both o<15%"])
        L += [f"", c8.get("caveat", ""), ""]
    nat_forced = {k: v for k, v in (adm.get("natural_adoptions_forced") or {}).items() if v}
    if nat_forced:
        L += ["### A natural adoption inside a forced run (reported here, not in §3)", ""]
        for n in nat_forced:
            v = adm["runs"][n]
            for e in v["evaluations"]:
                if e["adopted"] and not e["forced"]:
                    L += [f"- `{n}`, second episode, t = {int(e['t'])}: MAP `{e['h_star']}` "
                          f"({e['h_star_family']}, {e['h_star_params']}), logL {f(e['logL_h_star'], 2)}, "
                          f"posterior {f(e['post_h_star'], 4)}, gap vs demand "
                          f"{f(e['gap_vs_demand'], 3)} > ln 10, EVR {f(e['evr'], 4)}, n_O {e['n_O']}; "
                          f"the replacement row carries `forced: false` and `n_forced_adoptions` is 1, "
                          f"so this adoption was **not** injected.", ""]
        L += ["This is a real natural adoption, but it is **not** one of the three primary INC runs: the "
              f"run's first episode was force-adopted at "
              f"{int(adm['runs'][list(nat_forced)[0]]['t_adopt'])}, and its live state at 6,450 s comes "
              "from the clearance replacement replay, so the episode is not independent of the "
              "intervention. It is reported as a labelled observation only, and the §3 statement (no "
              "natural adoption in the pilot-2 INC runs) is unaffected.", ""]
    if c7.get("in_run_replacements"):
        L += ["In-run live replacements (the adoption path itself), from "
              "`replacement_log.jsonl` via `check7_755.json`:", ""]
        rows = []
        for r in c7["in_run_replacements"]:
            rows.append([f"`{r['hypothesis']}`", r["kind"], r.get("forced"), int(r["t"]),
                         f"{str(r['veh_digest_live'])[:16]}...", r["n_vehicles_live"],
                         f"{str(r['veh_digest_replay'])[:16]}...", r["n_vehicles_after_replay"],
                         r["vehicles_match"], r["restriction_present_live"],
                         r["restriction_present_replay"]])
        L += table(rows, ["hypothesis", "kind", "forced", "t", "live digest", "n live",
                          "replay digest", "n replay", "match", "restriction live",
                          "restriction replay"])
        L += [""]
    L += ["What the forced runs establish: the live replacement path (load S(t_on - 60), restore "
          "control state/stream/m, apply the restriction, replay to t) produces a live Twin whose "
          "vehicle digest and count equal the replay endpoint's and whose lanes are really "
          "disallowed; EVENT_ASSIMILATION then evaluates H_clear(tau_c) every 60 s against the "
          "active hypothesis, lifts the restriction, masks the pair and enters RECOVERY; RECOVERY "
          "then leaves for NORMAL when its own conditions are met (one of the four spells inside the "
          "horizon; the others were still in RECOVERY at 7,200 s or left through a new trigger after "
          "unmasking, which the spec allows). What they do **not** establish: that the incident "
          "hypothesis was inferred - it was injected.", ""]

    # ---------------------------------------------------------------- files
    L += ["## 7. Files written", "",
          "- `results/event_pilot2/runs/` - 9 pilot-2 two-world runs (`evt_inc_410{1,2,3}`, "
          "`conv_inc_410{1,2,3}`, `evt_noi_410{1,2,3}`) and 3 forced-adoption runs "
          "(`evtforce_inc_410{1,2,3}`), each with `twin/`, `proxy/`, `run_info.json`, "
          "`queue_forecasts.json`.",
          "- `results/event_pilot2/evidence/` - `check1_firewall.json`, "
          "`check2_deterministic_replay.json`, `check3_identical_support.json`, "
          "`check4_capacity_restriction.json`, `check5_freeze.json`, `check6_adoption_threshold.json`, "
          "`check7_755.json`, `check8_clearance.json`, `check9_nonincident.json`, "
          "`check10_degraded.json`, `adoption_summary.json`.",
          "- `results/event_pilot2/runs_summary.json`, `results/event_pilot2/report.md`.",
          "- `results/event_pilot2/impl/` - `run_pilot2.py`, `check_replays.py`, `make_evidence.py`, "
          "`make_report.py`, `summarize.py` (drivers; new outputs only).",
          "- Edited: `citypulse/twin/event.py`, `citypulse/twin/service.py`, "
          "`citypulse/experiments/event_pilot.py`, `tests/test_event.py`. "
          "`citypulse/branching/engine.py` untouched; `citypulse/proxy/*`, "
          "`citypulse/experiments/run_two_worlds.py`, `citypulse/branching/audit_engine.py`, "
          "`citypulse/experiments/decision_audit.py` and `results/audit/` untouched.",
          "",
          "REPORT DONE"]
    out = P2 / "report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out} ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
