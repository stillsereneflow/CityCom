"""Render results/event_pilot/fix/report.md from summary.json and the evidence files.

Usage: python results/event_pilot/fix/make_report.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "results/event_pilot/fix"
SEEDS = ("4001", "4002", "4003")
MODEL = "deepseek-v4.1-flash"

TEST_EVENT = "29 passed"
TEST_ALL = ("96 passed, 3 skipped, 1 failed - `tests/test_sumo_integration.py::"
            "test_init_signals_resets_last_loaded_program`, which is pre-existing and unrelated: it "
            "asserts the SUMO TLS program after `init_signals` is `0` but the working tree's scenario "
            "loads `webster` (the untracked `scenarios/kwuntong/tls_webster_v3.add.xml` / "
            "`tls_webster_v4.add.xml` and the modified scenario files were already dirty before this "
            "task; the test imports neither `citypulse.twin.event` nor anything this change touches)")

DIFF = [
    ("citypulse/twin/event.py", "13-16", "module docstring: the residual is the observation against the hypothesis's prediction"),
    ("citypulse/twin/event.py", "265", "new `_REPLAY` sentinel: no fault-model value, score against the no-event replay"),
    ("citypulse/twin/event.py", "268-290", "`effective_obs` now returns the PREDICTION (stuck: anchor; zero: 0 for q/o, `_REPLAY` for v; noise/other: `_REPLAY` with c = 5), not a replacement for the observation"),
    ("citypulse/twin/event.py", "292-323", "`block_residual` computes (obs - prediction)/sigma; `no_anchor`/`obs_invalid`/`obs_null`/`twin_null`/`no_sigma` exclusions unchanged, so the identical-support rule is untouched"),
    ("citypulse/twin/event.py", "331-352", "new `logl_of_one`: logL of a single hypothesis over its own support (no demand family needed)"),
    ("tests/test_event.py", "179-295", "4 new tests: stuck and zero under a congested observation vs the anchor, noise unchanged, single-hypothesis logL"),
    ("results/event_pilot/impl/check_replay.py", "4-5, 96-108", "check 2 no longer calls `ev.evaluate` for one hypothesis (no demand family -> `max()` on an empty sequence); it accumulates logL with `ev.logl_of_one` and reports n_O"),
    ("results/event_pilot/impl/check_replay.py", "125", "check2 evidence records n_O for both runs"),
]

EVIDENCE = [
    ("results/event_pilot/fix/evidence/check2_deterministic_replay.json",
     "check 2: one hypothesis scored twice from the same snapshot"),
    ("results/event_pilot/fix/evidence/check4_capacity_restriction.json",
     "check 4: incident vs no-event replay, disallowed lanes and downstream flow at AID02111"),
    ("results/event_pilot/fix/evidence/check7_state_replacement.json",
     "check 7: the fixed runs' replacement logs (no adoption) and the empty control event logs"),
    ("results/event_pilot/fix/evidence/check7_live_replacement_mechanics.json",
     "check 7 mechanics, exercised directly on the pinned episode snapshot (digest, count, live lane disallow)"),
    ("results/event_pilot/fix/evidence/fault_likelihood_before_after.json",
     "the defect: stuck residuals on AID02109/AID02111, old formula vs fixed formula, and old/new stuck logL"),
    ("results/event_pilot/fix/summary.json",
     "every fixed run's state trace, evaluations, trigger log size and run_info"),
]


def h_star_label(ev_row):
    """h* with its location and severity (incident) or detector and type (fault)."""
    hid = ev_row["h_star"]
    h = next((h for h in ev_row["hypotheses"] if h["id"] == hid), None)
    if h is None:
        return hid
    p = h.get("params") or {}
    if h["family"] == "incident":
        return (f"`{hid}` edge {p.get('edge')} @ {p.get('pos')} m, lanes closed "
                f"{p.get('lanes_closed')}/{p.get('n_lanes')}, speed factor {p.get('speed_factor')}")
    if h["family"] == "fault":
        return f"`{hid}` detector {p.get('detector')}, type {p.get('type')}, c {p.get('c')}"
    if h["family"] == "demand":
        return f"`{hid}` entry {p.get('entry')}, factor {p.get('factor')}"
    return f"`{hid}`"


def top5(ev_row):
    rows = sorted(ev_row["hypotheses"], key=lambda h: -h["logL"])[:5]
    out = ["  | rank | hypothesis | family | logL | posterior | n_O |", "  |---|---|---|---|---|---|"]
    for i, h in enumerate(rows, start=1):
        out.append(f"  | {i} | `{h['id']}` | {h['family']} | {h['logL']:.2f} | {h['post']:.4f} | {h['n_O']} |")
    return out


def main():
    summary = json.loads((FIX / "summary.json").read_text(encoding="utf-8"))
    fault = json.loads((FIX / "evidence/fault_likelihood_before_after.json").read_text(encoding="utf-8"))
    check2 = json.loads((FIX / "evidence/check2_deterministic_replay.json").read_text(encoding="utf-8"))
    check4 = json.loads((FIX / "evidence/check4_capacity_restriction.json").read_text(encoding="utf-8"))
    check7 = json.loads((FIX / "evidence/check7_state_replacement.json").read_text(encoding="utf-8"))
    check7m = json.loads((FIX / "evidence/check7_live_replacement_mechanics.json").read_text(encoding="utf-8"))

    L = [f"MODEL: {MODEL}", "",
         "# Detector-fault likelihood: fix and re-run of the three EVT INC pilot runs", "",
         "## 1. The defect and the fix", "",
         "`effective_obs` replaced detector i's **actual observation** with the fault prediction (stuck: "
         "the anchor; zero: 0) and `block_residual` compared that replacement with the no-event Twin "
         "replay. The residual (anchor - twin_baseline) therefore did not depend on what detector i "
         "reported, so a stuck or zero hypothesis erased i's observed anomaly and explained it for free "
         "(report2 G.4 requires the observations of that detector to be scored *under the fault model*).", "",
         "The fix scores the observation against the prediction:", "",
         "| Fault | Residual on detector i | Other detectors |", "|---|---|---|",
         "| stuck | (obs - anchor)/sigma for q, v, o | (obs - twin_baseline)/sigma |",
         "| zero | (obs - 0)/sigma for q and o; v keeps the no-event replay value | (obs - twin_baseline)/sigma |",
         "| noise | (obs - twin_baseline)/sigma with c = 5 (unchanged) | (obs - twin_baseline)/sigma |", "",
         "The identical-support rule is untouched: the same `no_sigma` / `obs_invalid` / `obs_null` / "
         "`twin_null` / `no_anchor` returns in the same order, so O is the same set of "
         "(detector, block, channel) triples as before.", "",
         "### Diff summary", "", "| File | Lines | Change |", "|---|---|---|"]
    for f, ln, what in DIFF:
        L.append(f"| `{f}` | {ln} | {what} |")
    L += ["", "`citypulse/twin/service.py` was **not** changed: it already passes the pre-t_on anchor "
              "(`anchor_for(t_on)`) and the down-weight map, and the fix lives entirely in `event.py`.", "",
          "## 2. Tests", "",
          f"- `python -m pytest tests/test_event.py -q` -> **{TEST_EVENT}** (25 pre-existing + 4 new).",
          f"- Whole suite `python -m pytest tests/ -q` -> **{TEST_ALL}**.", "",
          "| Test | What it pins |", "|---|---|",
          "| `test_stuck_fault_scores_the_observation_against_the_anchor` | congested obs at U: stuck residuals "
          "(obs - anchor)/sigma = (23, -30, 23) and `logL(stuck) < logL(no-event baseline)`; obs == anchor: "
          "residuals 0 and `logL(stuck) > logL(baseline)`, and better than under congestion |",
          "| `test_zero_fault_scores_the_observation_against_zero` | congested obs: residuals (25, -25, 25) "
          "(v is the no-event replay residual, byte-identical to the baseline's) and `logL(zero) < logL(baseline)`; "
          "obs == anchor: `logL(zero) > logL(baseline)` |",
          "| `test_noise_fault_residual_is_unchanged` | noise residuals stay (obs - replay)/sigma = (13, -25, 13), "
          "c = 5 on U only, and logL keeps the -ln 5 normalisation |",
          "| `test_single_hypothesis_logl_needs_no_demand_family` | one hypothesis alone is scored directly: "
          "n_O = 6, logL = -4.0, deterministic |", "",
          "## 3. `check_replay.py` (checks 2 and 4)", "",
          "Evaluating a single hypothesis called `ev.evaluate`, which needs a demand family for "
          "`gap_vs_demand` and the EVR and crashed on `max()` of an empty sequence. Check 2 now "
          "accumulates the logL with the new `ev.logl_of_one`.", "",
          f"- **Check 2** (`{check2['hypothesis']}`, snapshot {check2['snapshot']}, t_on {check2['t_on']:.0f}, "
          f"t_end {check2['t_end']:.0f}): logL_run1 = logL_run2 = **{check2['logL_run1']:.9f}**, "
          f"n_O = {check2['n_O']}, veh_digest identical ({check2['digest_run1'][:16]}...), interval tables "
          f"identical: **{check2['identical']}**.",
          f"- **Check 4**: lanes closed {check4['lanes_closed']} disallowed in the replay "
          f"(`restriction_present` = {check4['restriction_present']}); mean q at {check4['downstream_detector']} "
          f"drops from {check4['noevent_mean_q']:.2f} (no-event) to {check4['incident_mean_q']:.2f} (incident), "
          f"{check4['drop_pct']:.2f}%, n_vehicles {check4['n_vehicles_noevent']} -> "
          f"{check4['n_vehicles_incident']}: **flow_drops = {check4['flow_drops']}**.", "",
          "## 4. The three re-run EVT INC seeds", "",
          "Same arguments as `results/event_pilot/runs/evt_inc_<seed>/run_info.json` (harness "
          "`citypulse.experiments.event_pilot.run_two_world`, scenario INC, arm evt, twin seed 2, demand "
          "seed 202, base factor 0.85, `--event on --event-workers 4`, "
          "`--event-sigma results/event_pilot/impl/sigma_event.json`); only the output directory moved to "
          "`results/event_pilot/fix/evt_inc_<seed>/`.", ""]

    for seed in SEEDS:
        s = summary["seeds"][seed]
        info, stats = s["run_info"], s["twin_stats"]
        ev_stat = stats.get("event") or {}
        evs = s["evaluations"]
        L += [f"### Seed {seed}", "",
              f"- `{s['run_dir']}`: proxy_rc {info['proxy_rc']}, twin_rc {info['twin_rc']}, wall "
              f"{info['wall_s']:.1f} s, t_end {info['t_end']:.0f} s, {stats['messages']} SensorMsgs, "
              f"{s['trigger_log_rows']} trigger intervals, {ev_stat.get('n_eval', 0)} hypothesis "
              f"evaluations ({ev_stat.get('wall_s', 0.0):.1f} s of replay wall time).",
              f"- Episode starts (`trigger_alarm`): {', '.join(f'{t:.0f}' for t in s['alarms']) or 'none'}; "
              f"alarm intervals (streak >= 2): {ev_stat.get('n_alarms', 0)}.",
              f"- Down-weighted detectors: `{json.dumps(ev_stat.get('downweight') or {})}`; unexplained "
              f"anomalies: `{json.dumps(ev_stat.get('unexplained') or [])}`.",
              f"- **Adoption time: none.** **Clearance time: none** (never entered EVENT_ASSIMILATION); "
              f"`replacement_log.jsonl` is empty ({s['n_replacements']} replacements).", "",
              "| t | from | to | reason |", "|---|---|---|---|"]
        for tr in s["state_trace"]:
            L.append(f"| {tr['t']:.0f} | {tr['from']} | {tr['to']} | `{tr['reason']}` |")
        L += ["", "| t | state | n_O | excluded | h* (location / severity) | logL(h*) | post(h*) | "
                  "gap vs demand | EVR | adopted | wall_s |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in evs:
            hs = next((h for h in r["hypotheses"] if h["id"] == r["h_star"]), None)
            n_o = r["hypotheses"][0]["n_O"] if r["hypotheses"] else 0
            ll = "" if hs is None else f"{hs['logL']:.2f}"
            po = "" if hs is None else f"{hs['post']:.4f}"
            gap = "" if r["gap_vs_demand"] is None else f"{r['gap_vs_demand']:.2f}"
            evr = "" if r["evr"] is None else f"{r['evr']:.4f}"
            L.append(f"| {r['t']:.0f} | {r['state']} | {n_o} | `{json.dumps(r['excluded'])}` | "
                     f"{h_star_label(r)} | {ll} | {po} | {gap} | {evr} | {r['adopted']} | {r['wall_s']:.1f} |")
        L.append("")
        for r in evs:
            L += [f"**Top-5 at t = {r['t']:.0f} s** (state {r['state']}, t_on {r['t_on']:.0f}, "
                  f"wall {r['wall_s']:.1f} s, excluded `{json.dumps(r['excluded'])}`):", ""]
            L += top5(r)
            L.append("")

    L += ["## 5. Controls (EVT NOI / SHK / DET)", "",
          "The control EVT runs had zero triggers, so no evaluation ran in them; they are unaffected by "
          "construction, because the likelihood is only reached from an evaluation and the fault-model "
          "branch is only reached inside it. Verified on disk: `event_log.jsonl` is 0 bytes / 0 rows in "
          "all nine control runs.", "",
          "| control run | event_log.jsonl bytes | rows |", "|---|---|---|"]
    for name, c in sorted(summary["controls"].items()):
        L.append(f"| `{name}` | {c['event_log_bytes']} | {c['event_log_rows']} |")
    L += ["", "## 6. What the fix changed (on-disk before/after)", "",
          "`flt_AID02109_stuck` is the hypothesis that used to explain every alarm. Its logL at the "
          "evaluation timestamps both the old and the fixed run scored:", "",
          "| seed | t | old (anchor - replay) | fixed (obs - anchor) | change |", "|---|---|---|---|---|"]
    for seed in SEEDS:
        for t, v in sorted(fault["per_seed"][seed]["stuck_logL_at_matched_evaluations"].items(),
                           key=lambda kv: float(kv[0])):
            old, new = v["old_formula"], v["fixed_formula"]
            L.append(f"| {seed} | {float(t):.0f} | {old:.2f} | {new:.2f} | {new - old:+.2f} |")
    L += ["", "Block residuals on AID02109 for seed 4001 at the first alarm (t = 4890 s, t_on = 4290 s), "
              "reconstructed from the run's logged observations and anchor "
              "(`evidence/fault_likelihood_before_after.json`):", "",
          "| block (120 s) | fixed q | fixed v | fixed o | old q | old v | old o |", "|---|---|---|---|---|---|---|"]
    rec = fault["per_seed"]["4001"]["stuck_block_residuals_on_the_faulting_detector"]["detectors"]["AID02109"]
    for b in sorted(rec["fixed_stuck_block_residuals"], key=int):
        fx, ol = rec["fixed_stuck_block_residuals"][b], rec["old_formula_block_residuals"][b]

        def fmt(v):
            return "-" if v is None else f"{v:.2f}"
        L.append(f"| {b} | {fmt(fx['q']['residual'])} | {fmt(fx['v']['residual'])} | {fmt(fx['o']['residual'])} | "
                 f"{fmt(ol['q'])} | {fmt(ol['v'])} | {fmt(ol['o'])} |")
    L += ["", "In the last block (4800-4890 s) the queue's speed drop is charged to the stuck hypothesis "
              "(v = -3.23 sigma, o = +2.47 sigma) whereas the old formula scored it as a near-perfect fit "
              "(v = +0.88, o = -1.25: the wrong sign).", "",
          "### Result of the re-run", "",
          "- The stuck hypothesis no longer wins a first evaluation: at the first alarm of each seed its "
          "logL fell by 1.9 to 10.7 units and it left the top-5 in seeds 4001 and 4003 (it still wins "
          "seed 4002's third evaluation at 5040 s and is runner-up in seed 4003 at 4950 s, where the "
          "observation has come back to the anchor level, which is what the stuck model predicts).",
          "- The MAP at the first evaluation is now `flt_AID02111_zero` in all three seeds: the downstream "
          "detector really reports q = 0 and o ~ 0 while queued, and the zero model predicts exactly that, "
          "so the two are indistinguishable on that detector alone. The remaining discriminators are the "
          "other detectors (scored against the no-event replay) and the temporal pattern.",
          "- The incident family stays close but does not clear the ln-10 gap: at seed 4001 t = 4890 s the "
          "top incident hypothesis `inc_ktb_n1_k1_s1` (edge ktb_n1 @ 503.1 m, 1 of 3 lanes closed, speed "
          "factor 1.0) is 3.6 log units behind `flt_AID02111_zero` (posterior 0.157 vs 0.387), and it is "
          "the top incident member at every evaluation of every seed. The demand family's total posterior "
          "peaks at 0.577 (seed 4001 t = 4920/4980 s), below the 0.6 twice-in-a-row rule, so no false "
          "alarm was written and `false_alarms` is empty. **No seed adopted an incident, so no clearance "
          "evaluation ran** (EVENT_ASSIMILATION was never entered); the state machine returned to NORMAL "
          "through `detector_fault_*` (and, in seed 4001, through `unresolved_3_evals` -> DEGRADED -> "
          "`unexplained_anomaly`).",
          "- EVR is reported per evaluation above; it is 0.09-0.15 for the zero-fault MAP and negative "
          "once the noise hypothesis (c = 5, out of scope by the spec) takes over.",
          "- **Remaining, out-of-scope degeneracies** (both are what the spec's own residual definitions "
          "imply, not the defect this task fixed): a queued detector reports q = 0 and o ~ 0, which is "
          "exactly what the zero model predicts, so `flt_AID02111_zero` is nearly free on AID02111; and "
          "the noise model keeps the observation but divides its residual by c = 5, so `flt_AID02109_noise` "
          "wins once AID02109's residuals grow (it takes over from 5040 s on). The incident replay has to "
          "beat both on the *other* detectors to be adopted, and it does not clear the ln-10 gap within "
          "the 1-3 evaluations each episode gets before the state machine acts on the MAP.", "",
          "## 7. Evidence files", "", "| File | Contents |", "|---|---|"]
    for path, what in EVIDENCE:
        L.append(f"| `{path}` | {what} |")
    L += ["", "## 8. Check 7", "",
          f"- No fixed run adopted, so no pilot adoption exercised the replacement path: "
          f"`adoption_happened = {str(check7['adoption_happened']).lower()}`, `replacement_log.jsonl` empty "
          f"in all three seeds.",
          f"- The mechanics are verified directly instead "
          f"(`evidence/check7_live_replacement_mechanics.json`, hypothesis `{check7m['hypothesis']}`, "
          f"snapshot `{check7m['snapshot']}`, t_on {check7m['t_on']:.0f} -> t_end {check7m['t_end']:.0f}): "
          f"the live Twin's vehicle digest `{check7m['live_twin']['veh_digest'][:16]}...` and count "
          f"{check7m['live_twin']['n_vehicles']} equal the replay endpoint's "
          f"(`{check7m['replay_endpoint']['veh_digest'][:16]}...`, {check7m['replay_endpoint']['n_vehicles']}); "
          f"the lane disallow read live is "
          f"`{json.dumps(check7m['live_twin']['lane_disallow_live'])}` and `restriction_present` is true in "
          f"both. **passed = {str(check7m['passed']).lower()}**.", "",
          "## 9. Files written", "",
          "- `results/event_pilot/fix/evt_inc_4001/`, `evt_inc_4002/`, `evt_inc_4003/` (twin + proxy logs, "
          "state traces, event logs, snapshots) - the three re-runs, old runs untouched.",
          "- `results/event_pilot/fix/evidence/` - the five evidence files above.",
          "- `results/event_pilot/fix/summary.json`, `results/event_pilot/fix/report.md`.",
          "- `results/event_pilot/fix/run_evt_inc.py`, `make_evidence.py`, `make_report.py`, "
          "`check7_live_replacement.py` - the drivers (new outputs under `fix/`).",
          "- Edited: `citypulse/twin/event.py`, `tests/test_event.py`, "
          "`results/event_pilot/impl/check_replay.py` (and its regenerated `impl/check_replay.json`).",
          "Nothing was committed.", "",
          "REPORT DONE"]
    (FIX / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {FIX / 'report.md'} ({len(L)} lines)")


if __name__ == "__main__":
    sys.exit(main())
