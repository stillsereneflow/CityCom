"""Evidence and per-seed summary for the fixed detector-fault likelihood.

Writes, under results/event_pilot/fix/:
  evidence/check2_deterministic_replay.json   (from impl/check_replay.json)
  evidence/check4_capacity_restriction.json   (from impl/check_replay.json)
  evidence/check7_state_replacement.json      (adoption / replacement log of the fixed runs)
  evidence/fault_likelihood_before_after.json (the stuck residual on AID02109 at the first alarm,
                                               old formula vs fixed formula, plus old/new logL)
  summary.json                                (everything the report renders)

Usage: python results/event_pilot/fix/make_evidence.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.twin import event as ev   # noqa: E402

FIX = REPO / "results/event_pilot/fix"
OLD_RUNS = REPO / "results/event_pilot/runs"
IMPL = REPO / "results/event_pilot/impl"
SEEDS = (4001, 4002, 4003)
FAULT_DETS = (ev.PAIR_U, ev.PAIR_D)
CONTROLS = [f"evt_{s}_{seed}" for s in ("noi", "shk", "det") for seed in SEEDS]


def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def obs_and_twin(run_dir):
    """The logged observations and the live Twin baseline, exactly as the service scored them."""
    df = pd.read_parquet(run_dir / "twin/twin_log.parquet")
    obs, twin, times = {}, {}, {}
    for row in df.itertuples():
        t = float(row.t)
        times.setdefault(row.detector, []).append(t)
        obs.setdefault(row.detector, {})[t] = {
            "detector": row.detector, "q": None if pd.isna(row.obs_q) else float(row.obs_q),
            "v": None if pd.isna(row.obs_v) else float(row.obs_v),
            "o": None if pd.isna(row.obs_o) else float(row.obs_o), "valid": bool(row.obs_valid)}
        twin.setdefault(row.detector, {})[t] = {
            "q": None if pd.isna(row.twin_q) else float(row.twin_q),
            "v": None if pd.isna(row.twin_v) else float(row.twin_v),
            "o": None if pd.isna(row.twin_o) else float(row.twin_o)}
    return obs, twin, times


def anchor_of(obs, t_on, dets=FAULT_DETS):
    anchor = {}
    for det in dets:
        vals = {}
        for t in sorted(obs.get(det, {}), reverse=True):
            if t >= t_on:
                continue
            r = obs[det][t]
            if not r["valid"]:
                continue
            for x in ev.CHANNELS:
                if x not in vals and r[x] is not None:
                    vals[x] = r[x]
        anchor[det] = vals
    return anchor


def hyp_by_id(hyps, hid):
    return next(h for h in hyps if h.id == hid)


def stuck_residuals(run_dir, t_on, t_eval, sigma):
    """The stuck hypothesis's block residuals on the faulting detector, old formula vs fixed.

    Fixed: (obs - anchor)/sigma, the code path of the fixed ``block_residual`` (the faulting
    detector's q/o do not need the replay). Old: (anchor - twin)/sigma, the value the defective code
    scored; the logged live-Twin baseline stands in for the no-event replay the old code used.
    """
    obs, twin, times = obs_and_twin(run_dir)
    anchor = anchor_of(obs, t_on)
    hyps = ev.build_hypotheses()
    replays = {h.id: twin for h in hyps}
    out = {"t_on": t_on, "t_eval": t_eval, "anchor": anchor, "detectors": {}}
    for det in FAULT_DETS:
        ts_all = sorted(times.get(det, []))
        complete, partial = ev.candidate_blocks([det], ts_all, t_on, t_eval)
        fixed, old = {}, {}
        for b, ts in sorted(complete.items()):
            fixed[str(b)], old[str(b)] = {}, {}
            for x in ev.CHANNELS:
                r, why = ev.block_residual(hyp_by_id(hyps, f"flt_{det}_stuck"), det, ts, x, obs,
                                           replays, sigma, anchor)
                fixed[str(b)][x] = {"residual": r, "excluded": why}
                s = ev.sigma_of(sigma, det, x)
                a = anchor.get(det, {}).get(x)
                vals = [twin[det][t][x] for t in ts if twin.get(det, {}).get(t, {}).get(x) is not None]
                old[str(b)][x] = (None if (s is None or a is None or not vals)
                                  else sum((a - w) / s for w in vals) / len(vals))
        out["detectors"][det] = {"fixed_stuck_block_residuals": fixed,
                                 "old_formula_block_residuals": old,
                                 "n_complete_blocks": len(complete),
                                 "n_partial_blocks": len(partial)}
    return out


def logl_by_t(rows, hid):
    """logL of one hypothesis at every evaluation timestamp of a run."""
    out = {}
    for r in rows:
        h = next((h for h in r["hypotheses"] if h["id"] == hid), None)
        if h is not None:
            out[round(float(r["t"]), 6)] = h["logL"]
    return out


def main():
    (FIX / "evidence").mkdir(parents=True, exist_ok=True)
    sigma = ev.load_sigma(IMPL / "sigma_event.json")
    check_replay = json.loads((IMPL / "check_replay.json").read_text(encoding="utf-8"))

    # ---- check 2 and check 4 evidence (mechanisms checks on the smoke snapshot) --------------
    c2 = dict(check_replay)
    c2.pop("check4_capacity_restriction", None)
    (FIX / "evidence/check2_deterministic_replay.json").write_text(
        json.dumps({"check": "2", "name": "deterministic_replay",
                    "source": "results/event_pilot/impl/check_replay.json",
                    "snapshot": check_replay["snapshot"], "t_on": check_replay["t_on"],
                    "t_end": check_replay["t_end"], "hypothesis": check_replay["hypothesis"],
                    **check_replay["check2_deterministic_replay"]}, indent=1), encoding="utf-8")
    (FIX / "evidence/check4_capacity_restriction.json").write_text(
        json.dumps({"check": "4", "name": "effective_capacity_restriction",
                    "source": "results/event_pilot/impl/check_replay.json",
                    "snapshot": check_replay["snapshot"], "t_on": check_replay["t_on"],
                    "t_end": check_replay["t_end"], "hypothesis": check_replay["hypothesis"],
                    **check_replay["check4_capacity_restriction"]}, indent=1), encoding="utf-8")

    # ---- check 7 evidence: the replacement log of the fixed runs -----------------------------
    check7 = {"check": "7", "name": "successful_state_replacement",
              "adoption_happened": False, "runs": {}, "controls": {}}
    for seed in SEEDS:
        run = FIX / f"evt_inc_{seed}"
        rows = read_jsonl(run / "twin/replacement_log.jsonl")
        trace = read_jsonl(run / "twin/state_trace.jsonl")
        adopted = [t for t in trace if "adopted_" in t.get("reason", "")]
        check7["runs"][f"evt_inc_{seed}"] = {
            "replacement_log_rows": rows, "n_replacements": len(rows),
            "adoption_transitions": adopted,
            "event_log_rows": len(read_jsonl(run / "twin/event_log.jsonl")),
            "note": ("no adoption: the MAP never left the fault/demand families with the ln-10 gap, so "
                     "the live-Twin digest/count vs the replay endpoint and the live lane disallow were "
                     "never exercised by these runs (replacement_log.jsonl is empty, 0 bytes)")}
        if rows:
            check7["adoption_happened"] = True
    for name in CONTROLS:
        p = OLD_RUNS / name / "twin/event_log.jsonl"
        check7["controls"][name] = {"event_log_bytes": p.stat().st_size if p.exists() else None,
                                    "event_log_rows": len(read_jsonl(p))}
    (FIX / "evidence/check7_state_replacement.json").write_text(json.dumps(check7, indent=1),
                                                               encoding="utf-8")

    # ---- the defect itself: old formula vs fixed formula at the first alarm ------------------
    fault_evidence = {"name": "fault_likelihood_before_after",
                      "defect": "effective_obs replaced detector i's observation with the fault "
                                "prediction and compared it with the no-event replay, so the stuck/"
                                "zero residual did not depend on what i reported",
                      "fix": "the observation is scored against the prediction: stuck (obs-anchor)/"
                             "sigma, zero (obs-0)/sigma for q and o (v keeps the replay), noise "
                             "(obs-replay)/sigma with c = 5",
                      "sigma_source": "results/event_pilot/impl/sigma_event.json",
                      "per_seed": {}}
    summary = {"seeds": {}, "controls": check7["controls"]}
    for seed in SEEDS:
        new_run = FIX / f"evt_inc_{seed}"
        old_run = OLD_RUNS / f"evt_inc_{seed}"
        new_rows = read_jsonl(new_run / "twin/event_log.jsonl")
        old_rows = read_jsonl(old_run / "twin/event_log.jsonl")
        trace = read_jsonl(new_run / "twin/state_trace.jsonl")
        alarms = [t["t"] for t in trace if t["reason"] == "trigger_alarm"]
        first = new_rows[0]
        t_on = float(first["t_on"])
        rec = stuck_residuals(new_run, t_on, float(first["t"]), sigma)
        old_l = logl_by_t(old_rows, f"flt_{ev.PAIR_U}_stuck")
        new_l = logl_by_t(new_rows, f"flt_{ev.PAIR_U}_stuck")
        matched = sorted(set(old_l) & set(new_l))
        fault_evidence["per_seed"][str(seed)] = {
            "first_alarm_t": float(first["t"]), "t_on": t_on,
            "stuck_block_residuals_on_the_faulting_detector": rec,
            "stuck_logL_at_matched_evaluations": {
                str(t): {"old_formula": old_l[t], "fixed_formula": new_l[t]} for t in matched},
            "note": "matched evaluations are the timestamps both the old and the fixed run evaluated; "
                    "the faulting detector's q/o residuals need no replay, so the fixed column is exact"}
        summary["seeds"][str(seed)] = {
            "run_dir": f"results/event_pilot/fix/evt_inc_{seed}",
            "run_info": json.loads((new_run / "run_info.json").read_text(encoding="utf-8")),
            "twin_stats": json.loads((new_run / "twin/twin_stats.json").read_text(encoding="utf-8")),
            "state_trace": trace, "alarms": alarms,
            "evaluations": new_rows,
            "old_evaluations": old_rows,
            "old_state_trace": read_jsonl(old_run / "twin/state_trace.jsonl"),
            "n_replacements": len(read_jsonl(new_run / "twin/replacement_log.jsonl")),
            "trigger_log_rows": int(len(pd.read_parquet(new_run / "twin/trigger_log.parquet"))),
        }
    (FIX / "evidence/fault_likelihood_before_after.json").write_text(
        json.dumps(fault_evidence, indent=1), encoding="utf-8")
    (FIX / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print("wrote evidence + summary.json")
    for seed in SEEDS:
        rec = fault_evidence["per_seed"][str(seed)]
        print(f"seed {seed}: first alarm {rec['first_alarm_t']:.0f}, t_on {rec['t_on']:.0f}, "
              f"stuck logL old/fixed at matched t: "
              f"{ {k: (round(v['old_formula'], 2), round(v['fixed_formula'], 2)) for k, v in rec['stuck_logL_at_matched_evaluations'].items()} }")


if __name__ == "__main__":
    main()
