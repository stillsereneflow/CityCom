"""Tests for citypulse.experiments.dev_outcomes (outcomes 1-9 of docs/oct13-dev-runs-plan.md rev 2).

Synthetic log fixtures only: no SUMO, no Proxy, no run. Every definition boundary the plan fixes is
pinned: adoption exactly at 4,500 and at 5,400, t_clr exactly 5,400, t_dec exactly 6,300, the
right-censored delay, the DEGRADED exit at entry + 900 s against an early adoption, a recovery spell
interrupted by a trigger, zero successful library evaluations -> N/A, and a missing forecast cell ->
failure (never a smaller denominator).
"""
import json
import math

import pandas as pd

from citypulse.experiments import dev_outcomes as do

DETS = [f"AID{i:05d}" for i in range(1, 15)]
TICKS = [float(t) for t in range(30, 7201, 30)]
EVENT = "EVENT_ASSIMILATION"


# ------------------------------------------------------------------------------------- fixtures
def tr(t, frm, to, reason):
    return {"t": float(t), "from": frm, "to": to, "reason": reason}


def hyp(hid="inc_ktb_n1_k2_s1", family="incident", params=None, n_O=165):
    p = {"edge": "ktb_n1", "lanes_closed": [0, 1], "n_lanes": 3, "speed_factor": 1.0}
    p.update(params or {})
    h = {"id": hid, "family": family, "params": p, "prior": 0.03, "logL": -1.0, "post": 0.1}
    if n_O is not None:
        h["n_O"] = n_O
    return h


def lib_row(t, t_on=4200.0, h_star="inc_ktb_n1_k2_s1", adopted=False, gap=2.0, forced=None,
            excluded=None, error=None, h=None, state="SUSPECTED_EVENT"):
    if error is not None:
        return {"t": float(t), "state": state, "t_on": t_on, "hypotheses": [], "h_star": None,
                "gap_vs_demand": None, "evr": None, "adopted": False, "excluded": {"error": error},
                "p_clear": None, "wall_s": 0.0}
    row = {"t": float(t), "state": state, "t_on": t_on,
           "hypotheses": [h or hyp(h_star), hyp("dem_f1.15", "demand", {"factor": 1.15}, n_O=None)],
           "h_star": h_star, "gap_vs_demand": gap, "evr": 0.1, "adopted": bool(adopted),
           "excluded": excluded or {}, "p_clear": None, "wall_s": 1.0}
    if forced is not None:
        row["forced"] = bool(forced)
    return row


def clr_row(t, t_on, p_clear=0.9, tau_c=60.0, excluded=None, error=None):
    if error is not None:
        return {"t": float(t), "state": EVENT, "t_on": t_on, "hypotheses": [], "h_star": None,
                "gap_vs_demand": None, "evr": None, "adopted": False, "excluded": {"error": error},
                "p_clear": None, "wall_s": 0.0}
    return {"t": float(t), "state": EVENT, "t_on": t_on,
            "hypotheses": [{"id": "active", "family": "active", "params": {}, "logL": -1.0,
                            "post": 0.5}],
            "h_star": "active", "gap_vs_demand": None, "evr": None, "adopted": False,
            "excluded": excluded or {}, "p_clear": p_clear, "wall_s": 1.0, "tau_c": tau_c,
            "tau_c_best": tau_c}


def queue_forecasts(missing=(), blank_truth=()):
    """All required cells present; `missing` = (horizon, mark) absent, `blank_truth` null truth."""
    out = {"forecasts": {}, "summary_5min": {}, "summary_15min": {}}
    for horizon, marks, dt in (("5min", do.MARKS_5MIN, 300.0), ("15min", do.MARKS_15MIN, 900.0)):
        for mark in marks:
            entry = out["forecasts"].setdefault(str(int(mark)), {})
            if (horizon, mark) in missing:
                continue
            truth = None if (horizon, mark) in blank_truth else 8.0
            entry[horizon] = {"target_t": mark + dt, "pred": 10.0, "truth": truth,
                              "err": None if truth is None else 2.0}
    return out


def make_run(tmp_path, name="evt_inc_4401", scenario="INC", arm="evt", seed=4401, transitions=(),
             event_rows=(), stats=None, qf=None, snapshots=True, twin_log=True, t_end=7200.0,
             force_hstar=None, replacements=()):
    d = tmp_path / name
    (d / "twin").mkdir(parents=True, exist_ok=True)
    (d / "run_info.json").write_text(json.dumps(
        {"run_name": name, "scenario": scenario, "arm": arm, "seed": seed, "t_end": t_end,
         "event_grid": "pilot2", "event_force_hstar": force_hstar}), encoding="utf-8")
    for fname, rows in (("event_log.jsonl", event_rows), ("state_trace.jsonl", transitions),
                        ("replacement_log.jsonl", replacements)):
        (d / "twin" / fname).write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (d / "twin" / "twin_stats.json").write_text(json.dumps(stats or {}), encoding="utf-8")
    if twin_log:
        pd.DataFrame({"t": [t for t in TICKS for _ in DETS], "detector": DETS * len(TICKS)}).to_parquet(
            d / "twin" / "twin_log.parquet")
    if snapshots:
        for mark in do.MARKS_5MIN:
            (d / "twin" / f"twin_state_{int(mark)}.json").write_text("{}", encoding="utf-8")
            (d / "twin" / f"twin_state_{int(mark)}.xml.gz").write_bytes(b"")
    if qf is not None:
        (d / "queue_forecasts.json").write_text(json.dumps(qf), encoding="utf-8")
    return d


def run_of(d, name="run"):
    return do.analyse_run(do.load_run({"name": name, "run_dir": d, "status": "not_declared"}))


# ------------------------------------------------------------------- adoption timing boundaries
def test_adoption_exactly_at_onset_is_during_the_incident(tmp_path):
    d = make_run(tmp_path, transitions=[tr(4500, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm")],
                 event_rows=[lib_row(4500, adopted=True, gap=8.0)])
    r = run_of(d)
    a = r["adoptions"][0]
    assert a["timing_class"] == "during_incident" and a["natural"] is True
    assert r["natural_adoption"]["delay_s"] == 0.0
    assert r["clearance"][0]["labels_apply"] is True


def test_adoption_below_onset_is_pre_onset(tmp_path):
    d = make_run(tmp_path, transitions=[tr(4440, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm")],
                 event_rows=[lib_row(4440, adopted=True, gap=8.0)])
    a = run_of(d)["adoptions"][0]
    assert a["timing_class"] == "pre_onset" and a["natural"] is True


def test_adoption_exactly_at_clearance_is_post_clearance(tmp_path):
    d = make_run(tmp_path, transitions=[tr(5400, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm")],
                 event_rows=[lib_row(5400, adopted=True, gap=8.0)])
    r = run_of(d)
    assert r["adoptions"][0]["timing_class"] == "post_clearance"
    assert r["clearance"][0]["labels_apply"] is False


# ----------------------------------------------------------------------------- clearance labels
def test_t_clr_exactly_5400_is_not_premature_and_5399_is(tmp_path):
    def one(name, t_dec, tau_c):
        d = make_run(tmp_path, name=name,
                     transitions=[tr(4500, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                                  tr(4500, "SUSPECTED_EVENT", EVENT, "adopted_inc_ktb_n1_k2_s1"),
                                  tr(t_dec, EVENT, "RECOVERY", "cleared_two_consecutive")],
                     event_rows=[lib_row(4500, adopted=True, gap=8.0),
                                 clr_row(t_dec - 60, 4200, p_clear=0.9, tau_c=60.0),
                                 clr_row(t_dec, 4200, p_clear=0.99, tau_c=tau_c)])
        return run_of(d)["clearance"][0]

    at_bound = one("evt_inc_4401", 5700.0, 300.0)
    assert (at_bound["t_dec"], at_bound["tau_c"], at_bound["t_clr"]) == (5700.0, 300.0, 5400.0)
    assert at_bound["outcome"] == "cleared" and at_bound["labels_apply"] is True
    assert at_bound["premature_inference"] is False
    assert at_bound["premature_live_release"] is False and at_bound["late"] is False
    below = one("evt_inc_4402", 5699.0, 300.0)
    assert below["t_clr"] == 5399.0 and below["premature_inference"] is True
    assert below["premature_live_release"] is False


def test_t_dec_exactly_6300_is_not_late_and_6330_is(tmp_path):
    def one(name, t_dec):
        d = make_run(tmp_path, name=name,
                     transitions=[tr(4500, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                                  tr(4500, "SUSPECTED_EVENT", EVENT, "adopted_x"),
                                  tr(t_dec, EVENT, "RECOVERY", "cleared_two_consecutive")],
                     event_rows=[lib_row(4500, adopted=True, gap=8.0),
                                 clr_row(t_dec, 4200, tau_c=60.0)])
        return run_of(d)["clearance"][0]

    at_bound = one("evt_inc_4401", 6300.0)
    assert at_bound["t_dec"] == 6300.0 and at_bound["late"] is False
    assert at_bound["premature_live_release"] is False
    after = one("evt_inc_4402", 6330.0)
    assert after["t_dec"] == 6330.0 and after["late"] is True


def test_episode_still_in_event_at_horizon_is_overdue_right_censored(tmp_path):
    d = make_run(tmp_path,
                 transitions=[tr(4500, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(4500, "SUSPECTED_EVENT", EVENT, "adopted_x")],
                 event_rows=[lib_row(4500, adopted=True, gap=8.0),
                             clr_row(4560, 4200, p_clear=0.5, tau_c=60.0)])
    ep = run_of(d)["clearance"][0]
    assert ep["outcome"] == "overdue_right_censored"
    assert ep["t_dec"] is None and ep["t_clr"] is None
    assert "premature_inference" not in ep and ep["n_clearance_records"] == 1


def test_no_adoption_censors_the_delay_and_rates_are_zero(tmp_path):
    d = make_run(tmp_path, transitions=[tr(4800, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm")],
                 event_rows=[lib_row(4800)])
    r = run_of(d)
    n = r["natural_adoption"]
    assert n["n"] == 0 and n["any"] is False and n["delay_s"] is None
    assert n["delay_censored_at"] == 2700.0 and n["rate"] == 0.0
    assert n["denominator_successful_library_evals"] == 1
    assert r["adoptions"] == [] and r["clearance"] == []


def test_zero_successful_library_evaluations_is_na(tmp_path):
    d = make_run(tmp_path, scenario="NOI", name="evt_noi_4401")
    r = run_of(d)
    assert r["false_adoption"]["rate"] is None
    assert r["false_adoption"]["denominator_successful_library_evals"] == 0
    d2 = make_run(tmp_path, name="evt_inc_4402",
                  transitions=[tr(4800, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm")],
                  event_rows=[lib_row(4800, error="no ring snapshot at or before t=4740")])
    r2 = run_of(d2)
    assert r2["evaluations"]["library"] == {"attempted": 1, "successful": 0, "failed": 1,
                                            "failed_reasons": {"no_ring_snapshot": 1}}
    assert r2["natural_adoption"]["rate"] is None


def test_forced_adoption_is_kept_but_never_natural(tmp_path):
    d = make_run(tmp_path, name="evtforce_inc_4401", force_hstar="inc_ktb_n1_k2_s1",
                 transitions=[tr(5010, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(5010, "SUSPECTED_EVENT", EVENT, "adopted_inc_ktb_n1_k2_s1"),
                              tr(5130, EVENT, "RECOVERY", "cleared_two_consecutive")],
                 event_rows=[lib_row(5010, adopted=True, gap=math.log(10.0) + 1e-9, forced=True),
                             clr_row(5130, 4410, p_clear=0.99, tau_c=180.0)])
    r = run_of(d)
    assert r["run_forced"] is True and r["adoptions"][0]["forced"] is True
    assert r["adoptions"][0]["natural"] is False
    assert r["natural_adoption"]["n"] == 0 and r["natural_adoption"]["n_forced"] == 1
    ep = r["clearance"][0]
    assert ep["labels_apply"] is False and ep["premature_inference"] is True
    assert ep["t_clr"] == 4950.0 and ep["premature_live_release"] is True


# ----------------------------------------------------------------------------------- spell outcomes
def test_degraded_exit_at_entry_plus_900_and_early_adoption(tmp_path):
    d = make_run(tmp_path,
                 transitions=[tr(1000, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(1180, "SUSPECTED_EVENT", "DEGRADED", "unresolved_3_evals"),
                              tr(2080, "DEGRADED", "NORMAL", "unexplained_anomaly"),
                              tr(3000, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(3180, "SUSPECTED_EVENT", "DEGRADED", "unresolved_3_evals"),
                              tr(3700, "DEGRADED", EVENT, "adopted_x")])
    spells = run_of(d)["degraded_spells"]
    assert spells[0]["spell_class"] == "scheduled_timeout"
    assert spells[0]["duration_s"] == 900.0 and spells[0]["exit_at_entry_plus_900"] is True
    assert spells[1]["spell_class"] == "resolved_by_adoption"
    assert spells[1]["exit_at_entry_plus_900"] is False
    p = do.pool_scenario([run_of(d)])
    assert p["degraded_spells"]["live_covered"] is True
    assert p["degraded_spells"]["exit_at_entry_plus_900"] == 1


def test_degraded_spell_censored_at_horizon(tmp_path):
    d = make_run(tmp_path, transitions=[tr(1000, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                                        tr(1180, "SUSPECTED_EVENT", "DEGRADED", "unresolved_3_evals")])
    sp = run_of(d)["degraded_spells"][0]
    assert sp["spell_class"] == "censored" and sp["duration_s"] == 7200.0 - 1180.0
    assert do.pool_scenario([run_of(d)])["degraded_spells"]["live_covered"] is False


def test_recovery_spells_completed_interrupted_and_censored(tmp_path):
    d = make_run(tmp_path,
                 transitions=[tr(1000, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(1060, "SUSPECTED_EVENT", EVENT, "adopted_x"),
                              tr(2000, EVENT, "RECOVERY", "cleared_two_consecutive"),
                              tr(3000, "RECOVERY", "NORMAL", "recovery_complete"),
                              tr(4000, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(4060, "SUSPECTED_EVENT", EVENT, "adopted_x"),
                              tr(5000, EVENT, "RECOVERY", "cleared_two_consecutive"),
                              tr(5200, "RECOVERY", "SUSPECTED_EVENT", "trigger_alarm"),
                              tr(5260, "SUSPECTED_EVENT", EVENT, "adopted_x"),
                              tr(6000, EVENT, "RECOVERY", "cleared_two_consecutive")])
    spells = run_of(d)["recovery_spells"]
    assert [s["spell_class"] for s in spells] == ["completed", "interrupted_by_trigger", "censored"]
    assert [s["duration_s"] for s in spells] == [1000.0, 200.0, 1200.0]
    assert spells[1]["exit_reason"] == "trigger_alarm"


# -------------------------------------------------------------------------------- support / slots
def test_support_size_derivation_and_logged_n_O(tmp_path):
    d = make_run(tmp_path, transitions=[tr(4200, "NORMAL", "SUSPECTED_EVENT", "trigger_alarm"),
                                        tr(4200, "SUSPECTED_EVENT", EVENT, "adopted_x")],
                 event_rows=[lib_row(4500, t_on=4200, h=hyp(n_O=165)),
                             clr_row(4500, 4200, excluded={"obs_invalid": 5})])
    r = run_of(d)
    lib = next(x for x in r["exclusions"] if x["kind"] == "library")
    clr = next(x for x in r["exclusions"] if x["kind"] == "clearance")
    assert (lib["n_O"], lib["n_O_source"]) == (165, "logged")
    # 14 detectors x 1 complete 120-s block in (4200, 4500] x 3 channels - 5 exclusions = 37
    assert (clr["n_O"], clr["n_O_source"]) == (37, "derived")


def test_slots_gate_statistics_and_account_every_slot(tmp_path):
    make_run(tmp_path, name="evt_inc_4401")
    make_run(tmp_path, name="evt_inc_4402")
    slots = tmp_path / "slots.json"
    slots.write_text(json.dumps({"slots": [{"name": "evt_inc_4401", "status": "complete"},
                                           {"name": "evt_inc_4402", "status": "incomplete",
                                            "reason": "missing twin_log"}]}), encoding="utf-8")
    entries, accounting = do.discover(tmp_path, str(slots))
    assert [e["name"] for e in entries] == ["evt_inc_4401"]
    assert [a["in_statistics"] for a in accounting] == [True, False]
    assert [a["status"] for a in accounting] == ["complete", "incomplete"]


def test_slots_counted_attempt_selects_the_attempt_directory(tmp_path):
    name = "evt_inc_4401"
    make_run(tmp_path, name=f"{name}/attempt_1", seed=1)
    make_run(tmp_path, name=f"{name}/attempt_2", seed=2)
    slots = tmp_path / "slots.json"
    slots.write_text(json.dumps({name: {"status": "complete_flagged", "counted_attempt": 1}}),
                     encoding="utf-8")
    entries, accounting = do.discover(tmp_path, str(slots))
    assert entries[0]["run_dir"].name == "attempt_1"
    assert accounting[0]["in_statistics"] is True


def test_slots_in_the_driver_format(tmp_path):
    """results/dev_runs/slots.json as citypulse.experiments.dev_runs writes it."""
    make_run(tmp_path, name="evt_inc_4401/attempt_2", seed=2)
    make_run(tmp_path, name="evt_inc_4402")
    slots = tmp_path / "slots.json"
    slots.write_text(json.dumps({
        "summary": {"complete": 1, "complete_but_flagged": 1, "incomplete": 1,
                    "permanently_failed": 0},
        "slots": {"evt_inc_4401": {"status": "complete_but_flagged", "latest_attempt": 2,
                                   "attempts_count": 2, "reasons": []},
                  "evt_inc_4402": {"status": "permanently_failed", "latest_attempt": 1,
                                   "attempts_count": 2, "reasons": ["twin_rc=1"]}}}),
        encoding="utf-8")
    entries, accounting = do.discover(tmp_path, str(slots))
    assert [e["name"] for e in entries] == ["evt_inc_4401"]
    assert entries[0]["run_dir"].name == "attempt_2"
    assert [a["in_statistics"] for a in accounting] == [True, False]
    assert [a["status"] for a in accounting] == ["complete_but_flagged", "permanently_failed"]


# -------------------------------------------------------------------------------------- forecasts
def test_missing_forecast_cell_is_a_failure_never_a_smaller_denominator(tmp_path):
    d = make_run(tmp_path, qf=queue_forecasts(missing={("5min", 4800.0)},
                                              blank_truth={("15min", 6000.0)}))
    r = run_of(d)
    assert len(r["forecast_cells"]) == 8 + 7
    assert {(f["horizon"], f["mark"]) for f in r["forecast_failures"]} == {("5min", 4800.0),
                                                                          ("15min", 6000.0)}
    assert {tuple(f["reasons"]) for f in r["forecast_failures"]} == {("missing_forecast_entry",),
                                                                    ("missing_truth",)}
    s = do.forecast_summary([r])
    five = next(x for x in s["arms"] if x["horizon"] == "5min")
    fifteen = next(x for x in s["arms"] if x["horizon"] == "15min")
    assert (five["required_cells"], five["complete_cells"], five["failed_cells"]) == (8, 7, 1)
    assert (fifteen["required_cells"], fifteen["complete_cells"], fifteen["failed_cells"]) == (7, 6, 1)
    assert five["denominator_cells"] == 7


def test_missing_snapshot_and_missing_forecast_file_are_failures(tmp_path):
    d = make_run(tmp_path, snapshots=False, qf=None)
    r = run_of(d)
    assert len(r["forecast_failures"]) == 15
    assert all("missing_snapshot" in f["reasons"] for f in r["forecast_failures"])
    assert all("missing_queue_forecasts_json" in f["reasons"] for f in r["forecast_failures"])


def test_paired_difference_uses_complete_pairs_only(tmp_path):
    evt = run_of(make_run(tmp_path, name="evt_inc_4401", qf=queue_forecasts()), "evt")
    conv = run_of(make_run(tmp_path, name="conv_inc_4401", arm="conv",
                           qf=queue_forecasts(missing={("5min", 4800.0)})), "conv")
    s = do.forecast_summary([evt, conv])
    five = next(x for x in s["pairs_pooled"] if x["horizon"] == "5min")
    fifteen = next(x for x in s["pairs_pooled"] if x["horizon"] == "15min")
    assert five["n_pairs"] == 7 and fifteen["n_pairs"] == 7
    assert five["mean_evt_minus_conv_abs_error"] == 0.0
    assert len(s["pairs_per_seed"]) == 2


# ------------------------------------------------------------------------------------------- CLI
def test_cli_writes_outcomes_json_and_report(tmp_path):
    make_run(tmp_path, name="evt_inc_4401", qf=queue_forecasts())
    out = tmp_path / "out"
    do.main(["analyze", "--runs-dir", str(tmp_path), "--out", str(out)])
    payload = json.loads((out / "outcomes.json").read_text(encoding="utf-8"))
    report = (out / "report.md").read_text(encoding="utf-8")
    assert list(payload["runs"]) == ["evt_inc_4401"]
    assert payload["definitions"]["t_onset"] == 4500.0
    assert payload["accounting"][0]["in_statistics"] is True
    for section in ("## Accounting", "## Outcome 1: exposure", "## Outcome 2: natural adoption",
                    "## Outcome 3: false adoption", "## Outcome 4: non-incident handling",
                    "## Outcome 5: clearance", "## Outcome 6: recovery spells",
                    "## Outcome 7: DEGRADED spells", "## Outcome 8: exclusions",
                    "## Outcome 9: forecasts", "## Failures"):
        assert section in report
