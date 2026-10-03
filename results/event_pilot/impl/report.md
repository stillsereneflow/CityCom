MODEL: deepseek-v4.1-flash

# Event-aware assimilation (mechanics pilot): implementation, tests and smoke status

Worktree `D:/CityCom-astra` (nothing committed). Binding spec: `docs/oct6-event-pilot-plan.md`,
section "Event-aware assimilation". Python `D:/CityCom/.venv/Scripts/python.exe` (SUMO 1.27.1,
traci/libsumo); env `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`, `CITYPULSE_NET=blite`,
`CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`.

## 0. Execution status (read this first)

**The implementation, the tests and the run harness are complete; no command could be executed in
this session.** Every tool call that needs an OS process failed for the whole session with the same
host-level error, verbatim:

```
Error: subprocess-local: Windows Job runner exited with exit code 3221225794 before proving its managed range empty
```

`3221225794` = `0xC0000142` (`STATUS_DLL_INIT_FAILED`): the Windows job runner that the harness uses
to start any process could not initialise, so `pwsh`, `glob`/`grep` (ripgrep subprocesses), foreground
and background shell jobs, and a delegated subagent all failed identically. The `read`/`write`/`edit`
tools use an in-process filesystem backend and kept working, which is how this implementation was
written and reviewed. Consequences, stated plainly:

* `pytest tests/test_event.py` **was not run**; §3 lists the 22 tests and what each pins, but their
  pass/fail state is unverified.
* `results/event_pilot/impl/sigma_event.json` **could not be computed** (it needs to read the
  `twin_log.parquet` files of `results/assim/na300/ol_4001..4003`); `compute_sigma_event.py` is ready
  and is the first step of the sequence below.
* The two-world INC smoke run **was not run**; §5 describes the exact run and the checks it performs.
* `EVENT_READY` therefore carries no sha256 values (they cannot be computed without a process); it
  records the command that writes them.

Everything that produces the missing artefacts is one command:

```pwsh
D:/CityCom/.venv/Scripts/python.exe results/event_pilot/impl/run_all.py
```

which runs, in order, `compute_sigma_event.py` (sigma) -> `pytest tests/test_event.py` (tests) ->
`run_event_smoke.py` (the INC smoke run) -> `check_replay.py` (mechanics checks 2 and 4) ->
`summarise_smoke.py` (the log summary) -> `make_ready.py` (`EVENT_READY`), logging each step to
`results/event_pilot/impl/run_all.log`. Nothing in the implementation depends on this session.

## 1. Changes (file:line)

| File | Lines | What |
|---|---|---|
| `citypulse/twin/event.py` | 1–83 | New module, pure logic. Constants of the spec (pair, threshold 3.0, 30-s interval, 120-s block, beta 0.25, ln 10, o_crit 15%, t_on lag 600 s, Delta 60 s, ring 900 s, cadences 60/120/60 s, DEGRADED 15 min, RECOVERY 180 s + 5-min kappa ramp, clear taus 60…300 s, p_clear 0.7, p_demand 0.6, c = 5) and the net5 incident geometry. |
| | 86–130 | `_num`, `_field`, `load_sigma`, `sigma_of` (with the detector down-weight multiplier). |
| | 134–158 | `bottleneck_index`: B = 0.5(r_U^o − r_D^o) + 0.5(r_D^v − r_U^v), r = (obs − twin)/sigma; speed nulls imputed 0, a lost occupancy packet (or a missing twin reading) makes the interval missing. |
| | 161–195 | `TriggerRule.step`: B >= 3 at two timestamps **exactly 30 s apart**, a gap/missing interval resets the streak, masked ticks compute B but never accumulate. |
| | 198–245 | `Hypothesis`, `build_hypotheses` (16 = 6 incident + 4 demand + 6 fault, family priors 1/3, uniform inside a family; ktb_n1 at 755 m, ktb_w3/ktb_n2 at their midpoints; 2-lane ktb_n2 uses k = 1 only), `entries_through` (the regional-freeze set). |
| | 248–307 | `block_of`, `candidate_blocks` (complete 120-s blocks in (t_on, t]), `effective_obs` (stuck/zero/noise fault models), `block_residual`, `_c_of`. |
| | 310–391 | `Evaluation` + `evaluate`: identical support O over every hypothesis, exclusions by reason, logL = Σ_O[−½(r/c)² − ln c], beta = 0.25 posterior (log-sum-exp), h*, gap vs the demand family, EVR = 1 − SSE_h*/min SSE_demand. |
| | 394–431 | `adoption_decision` (incident family and gap > ln 10), `demand_map`, `clearance_posterior` (0.5 active / 0.1 each clear), `clearance_analysis`. |
| | 435–647 | `Transition` and `EventStateMachine`: NORMAL / SUSPECTED_EVENT / DEGRADED / EVENT_ASSIMILATION / RECOVERY with every rule of the spec, `assim_mode()` (`frozen` / `slow` / `normal`) and `kappa_scale()` (DEGRADED kappa/4, RECOVERY 0->kappa ramp). |
| `citypulse/branching/engine.py` | 1–9 | Docstring note: `score_replays` is a new, independent entry point; `run_branches` is unchanged. |
| | 141–211 | `SCORE_VCLASSES`, `_apply_spec_at` (incident: lanes 0..k−1 disallowed + remaining lanes' max speed × s; demand: m := the absolute level f), `_lift_spec_at`, `restriction_present`, `veh_digest`. |
| | 214–281 | `_score_worker`: load S with `--load-state`, re-apply the control state, restore stream pointer/m/base factor, apply at `t_on`, lift at `t_lift`, replay to `t_end` with the same step order as the live Twin, return the Twin detector intervals, vehicle count and digest. |
| | 284–309 | `score_replays(state, meta, jobs, workers=8)`: spawn Pool, one process per hypothesis, results in job order. |
| `citypulse/twin/service.py` | 33–53 | Imports of the engine scoring entry point and `citypulse.twin.event`. |
| | 95–110 | `load_event_sigma`: `--event on` fails hard unless sigma exists for both pair detectors on o and v. |
| | 112–119 | `scaled_assimilator`: kappa/delta-scaled copy of the NA-300 assimilator (`assim.py` is frozen). |
| | 122–296 | `EventRuntime`: geometry from the live Twin (`init_twin`), observation history + stuck anchor, the 30-s snapshot ring with 15-min pruning inside `<out>/ring/` only, the pinned episode snapshot (`pin_episode`/`episode_paths`), hypothesis specs, `step` (trigger every 30 s, RECOVERY checks, state-machine evaluation when due), `evaluate` / `evaluate_clearance` with the failed-replay guard. |
| | 298–386 | The two evaluation paths (16 hypotheses; active + 5 clearance hypotheses), adoption/clearance handling. |
| | 396–484 | `replace_live` (fresh SUMO with `--load-state`, control state/stream/m restored, apply/lift replayed to t), `log_replacement`, log writing, `summary`. |
| | 487–595 | `run(..., event="off", event_sigma=None, event_workers=8)`: ring write + event step on every 30-s tick, NA-300 tick modified for the freeze (`frozen`, `degraded_slow`, the RECOVERY ramp), event logs and stats. With `--event off` the loop body is the previous code plus one `if ev is not None` test. |
| | 596–622 | CLI `--event {off,on}` (default off), `--event-sigma`, `--event-workers` (default 8). |
| `tests/test_event.py` | 1–426 | 22 pure tests (§3). |
| `results/event_pilot/impl/` | — | `compute_sigma_event.py`, `run_event_smoke.py`, `check_replay.py`, `summarise_smoke.py`, `make_ready.py`, `run_all.py`, `EVENT_READY`, this report. |

Not touched: `citypulse/twin/assim.py`, `citypulse/twin/demand_stream.py`, `citypulse/sim.py`,
`citypulse/proxy/*`, `citypulse/experiments/*` (agy-flash's files) and everything else.

## 2. Decisions where the spec left room (all documented, none tuned)

1. **Support O** is the set of (detector, block, channel) triples whose four 30-s intervals are valid
   in the observations **and** whose residual is computable under **every** hypothesis, so `n_O` is
   identical for all 16 hypotheses (check 3). Exclusions are counted by reason: `obs_invalid`,
   `obs_null`, `twin_null`, `no_sigma`, `no_anchor` (stuck fault with no pre-t_on reading),
   `partial_block` (a 120-s window that the evaluation time cuts short).
2. **Speed nulls** (a detector with q = 0 has no v) are a zero residual, not a missing interval — the
   corrected G4 diagnosis keeps the `.fillna(0)` imputation and only occupancy packet loss makes an
   interval missing.
3. **Blocks are absolute** 120-s windows (`floor(t/120)`), so the support does not move with `t_on`.
4. **Demand hypotheses are absolute levels** f (m := f), not factors on the Twin's current estimate;
   the grid contains 0.85, the imposed base factor, and the spec says "write the MAP f into m".
5. **A zero MAD** in sigma falls back to a per-channel floor (q 1.0, v 0.5 km/h, o 0.1 %) so no
   residual divides by zero; the fallback is recorded per detector in `sigma_event.json`.
6. **Clearance replays all start from S(t_on − Delta)** with the active h* applied at t_on; each
   clear hypothesis lifts the restriction at its own tau_c. Using S(tau_c − Delta) instead would
   either predate the adoption (no restriction to lift, degenerate comparison) or make the active
   hypothesis unreproducible, so the shared start is what keeps the six hypotheses on identical
   trajectories and identical support. This is the one deliberate deviation from the letter of the
   spec; it is flagged again in §6.
7. **Live state replacement** restarts the Twin's SUMO process with `--load-state` (the path verified
   in `results/assim/na300_impl/report.md` for branch replays) and replays to t with the same stream,
   so the live vehicle state is bit-identical to the scoring replay; `replacement_log.jsonl` records
   both the replay's and the live Twin's vehicle count and sha256 state digest.
8. **Detector-fault MAP** down-weights that detector by a factor 5 on sigma (trigger and likelihood)
   and returns to NORMAL, as the spec's "down-weight that detector" without further detail.
9. **DEGRADED logging**: every NA-300 tick under the slow rule logs `degraded_slow` (the underlying
   reason is still visible through `e_s`/`r`/`delta`); frozen ticks log `frozen` and keep m.
10. **The episode's replay start is pinned**: on entering SUSPECTED_EVENT, S(t_on − Delta) is copied
   out of the ring to `<out>/event_snapshot_<t>.{xml.gz,json}` and every evaluation of that episode
   replays from the pinned copy. The ring itself keeps exactly 15 min as specified, but 15 min is
   shorter than a long episode (SUSPECTED + DEGRADED + EVENT can outlive 900 s), so without the pin a
   late evaluation would lose its start snapshot. The pin also guarantees that all evaluations of one
   episode (and the live replacement) start from the identical state, which is what makes check 2 and
   the identical-support rule meaningful across evaluations.

## 3. Tests (`tests/test_event.py`, 22 tests, pure — no SUMO)

| Test | Pins |
|---|---|
| `test_trigger_streak_needs_two_exactly_30s_apart` | B >= 3 twice 30 s apart alarms; a low B resets |
| `test_trigger_missing_interval_resets_the_streak` | an invalid interval and a 60-s gap both restart the streak at 1 (no alarm) |
| `test_trigger_masked_and_speed_null_imputation` | masked ticks keep B but never accumulate; q = 0 / v = None is a zero residual |
| `test_trigger_needs_sigma` | no sigma -> no B, no streak |
| `test_hypothesis_library_count_and_priors` | 16 hypotheses, 6/4/6, family priors 1/3, uniform inside a family, unique ids |
| `test_incident_library_geometry` | ktb_n1 at 755 m, midpoints for ktb_w3/ktb_n2, k = 1..2 for 3-lane edges, k = 1 only for 2-lane ktb_n2 |
| `test_demand_and_fault_library` | f in {0.7, 0.85, 1.15, 1.3}; 2 detectors × 3 fault types; noise carries c = 5 |
| `test_freeze_entries_follow_the_candidate_routes` | the freeze set is the entries whose routes pass ktb_n1/ktb_w3/ktb_n2 |
| `test_logl_includes_the_c5_noise_normalisation` | logL = Σ[−½(r/c)² − ln c] with c = 5 on the noise detector only (U pays −ln 5 per triple) |
| `test_identical_support_is_the_intersection_over_every_hypothesis` | one hypothesis that cannot score a triple removes it for all (n_O identical), `no_anchor` counted |
| `test_identical_support_excludes_invalid_observations_and_partial_blocks` | `obs_invalid` and `partial_block` exclusions, n_O identical |
| `test_posterior_is_beta_scaled_and_evr_is_relative_to_the_demand_family` | log P = ln prior + 0.25 logL − logsumexp; gap and EVR definitions |
| `test_adoption_threshold_is_ln10_above_the_demand_family` | adopted only for an incident MAP with a demand gap > ln 10 (wide vs narrow vs wrong-family MAP) |
| `test_clearance_posterior_priors` | 0.5 active / 0.5 over the clears; a dominant active drives p_clear < 0.01 |
| `test_clearance_analysis_rows` | 6 rows, best tau_c, posteriors sum to 1 |
| `test_alarm_enters_suspected_with_t_on_and_freeze` | NORMAL -> SUSPECTED_EVENT, t_on = alarm − 600, freeze |
| `test_suspected_adopts_and_enters_event` | adoption -> EVENT_ASSIMILATION |
| `test_suspected_demand_family_twice_writes_m_and_returns_to_normal` | demand posterior > 0.6 twice in a row -> m := MAP f, unfreeze, false alarm, NORMAL; one in a row is not enough |
| `test_suspected_detector_fault_downweights_and_returns_to_normal` | fault MAP -> down-weight, unfreeze, NORMAL |
| `test_suspected_third_unresolved_evaluation_degrades` | n_eval >= 3 -> DEGRADED, kappa/4 and 2 sigma |
| `test_degraded_bounds_at_15_minutes_and_can_still_adopt` | DEGRADED can still adopt within 15 min; beyond it -> NORMAL + "unexplained anomaly" |
| `test_clearance_needs_two_consecutive_evaluations_above_threshold` | p_clear > 0.7 twice in a row -> RECOVERY + mask; a dip resets |
| `test_recovery_minimum_time_and_exit_conditions` | kappa ramp 0->1 over 5 min; >= 180 s; B < 1.5 for 3 min; o < 15% at both ends; a B spike resets |
| `test_masking_unmasks_when_both_ends_are_below_15pct_and_a_new_trigger_restarts` | masking/unmasking and a new trigger -> SUSPECTED_EVENT |
| `test_evaluation_periods` | first evaluation at the alarm, 60 s in SUSPECTED, 120 s in DEGRADED, `next_eval_at` |

Run (not executed here, see §0):

```pwsh
D:/CityCom/.venv/Scripts/python.exe -m pytest tests/test_event.py -q -p no:cacheprovider
```

## 4. sigma_event.json

`results/event_pilot/impl/compute_sigma_event.py` reads the three biased-OL development runs
(`results/assim/na300/ol_4001..4003/twin/twin_log.parquet`, `--twin-base-factor 0.85`, no incident),
keeps rows with `t >= 900 s` and `obs_valid`, and for every detector and channel x in {q, v, o}
computes `sigma = 1.4826 * median(|r − median(r)|)` with `r = obs_x − twin_x`. Units are the Twin's
(q per 30-s interval, v km/h, o %). Output: `{"sigma": {det: {q, v, o}}, pair, t_min, runs,
channel_floor, median, mad, n_residuals, fallbacks}`. **Not yet computed** (§0); the smoke run's
`--event on` refuses to start without it, which is deliberate (the same F5-style hard failure the
NA-300 boundary sigma uses).

## 5. Integration smoke (not yet run)

`results/event_pilot/impl/run_event_smoke.py --run event_pilot/impl/smoke_inc` launches the two worlds
the way `citypulse.experiments.run_two_worlds` does (Twin first, 2-s wait, then the Proxy; the only
channel between them is the ZeroMQ firewall). The incident lives in the Proxy only and is the default
(`--no-incident` is the NOI control):

* Twin: `-m citypulse.twin.service --seed 2 --demand-seed 202 --demand-path
  scenarios/kwuntong/blite/synth5/twin_cand.rou.xml --assim normal300 --boundary-detector AID07106
  --sigma-json results/assim/na300/sigma300_dev.json --twin-base-factor 0.85 --event on
  --event-sigma results/event_pilot/impl/sigma_event.json --event-workers 8
  --snapshot-times 4200 4800 5400 6000`.
* Proxy: `-c "from citypulse.proxy.service import main; main()" --seed 4001 --t-end 7200 --routes
  scenarios/kwuntong/blite/synth5/proxy.rou.xml` (INC: the 4,500–5,400 s `ktb_n1` lanes 0–1 blockage
  at 900 m, `citypulse/proxy/truth_blite.py`).

The persistent `--snapshot-times` files are what make the checks reproducible after the run (the ring
itself only keeps 15 min). Expected artefacts: `<run>/twin/event_log.jsonl` (one row per evaluation
with `t`, `state`, `t_on`, `hypotheses[{id, family, params, logL, post, n_O}]`, `h_star`,
`gap_vs_demand`, `evr`, `adopted`, `excluded`, `p_clear`, `wall_s`), `state_trace.jsonl`,
`trigger_log.parquet` (`t`, `B`, `streak`, `masked`), `replacement_log.jsonl` (snapshot, hypothesis,
vehicle count after replay, whether the restriction is present in the live Twin, and the live/replay
digest comparison), `assim_log.parquet` with the new `frozen`/`degraded_slow` reasons, and
`twin_stats.json` with the event summary (state, t_on, alarms, false alarms, unexplained, transitions,
freeze entries, lane counts, midpoints, replacements).

Then `check_replay.py` (snapshot 4800, incident applied at 4860, replay to 5400) reports:

* **check 2** — the incident hypothesis `inc_ktb_n1_k2_s0.6` scored twice in independent processes:
  identical logL, identical interval tables, identical vehicle digests;
* **check 4** — under that hypothesis the lanes are disallowed (`restriction_present`) and AID02111's
  mean flow over the replay window drops relative to the no-event replay, with the drop in per cent.

`summarise_smoke.py` prints the state trace, the per-evaluation rows, the adoption/clearance times,
the evaluation wall times (mean/max/total), the trigger diagnostics (number of 30-s ticks, number of
ticks with B >= 3, max B and when, masked ticks) and mechanics check 5 (m constant while frozen);
`summary.json` carries the same, plus the full assim log with the `frozen`/`degraded_slow` reasons.
If the trigger never reaches B >= 3 with the spec's sigma, `max_B` says so directly — that is an
accuracy finding to report, not a mechanics failure.

## 6. Known gaps and open risks

1. **Nothing was executed** (§0): tests, sigma and the smoke run are unverified. This is the dominant
   gap; the code was written and re-read carefully, but no runtime evidence exists in this session.
2. **Clearance replays start from S(t_on − Delta)** instead of S(tau_c − Delta) (§2.6).
3. **CUSUM, onset search, larger grids, learned localisation, calibrated severity and posterior
   calibration are deferred** by the spec; beta = 0.25 is explicitly uncalibrated and severity is a
   Twin configuration.
4. **A second episode** would build its `t_on − Delta` snapshot possibly inside the previous
   restriction (the meta then carries it and `cs.apply` restores it); the incident hypotheses would
   be applied on top rather than from a clean base. The smoke run has one episode.
5. **Down-weighting** is a sigma multiplier (×5) applied to the trigger and the likelihood; the spec
   does not say how the down-weight enters, so this is a documented choice.
6. **Wall time**: each evaluation is 16 (or 6) SUMO processes, so an evaluation costs seconds to tens
   of seconds and the Proxy waits on the REQ/REP socket. The spec allows this; `wall_s` is logged per
   evaluation and the run's wall time will be dominated by the ~20 evaluations of one episode.
7. **Ring size**: 15 min at 30-s cadence is ~30 state files (a few MB each, gzipped) under
   `<out>/ring/`; pruning only ever touches files inside that directory (checked with `resolve()`).
   The pinned episode snapshot (2 files per episode) lives in `<out>/` and is never pruned.
8. `EVENT_READY` has no hashes yet: they are written by
   `python results/event_pilot/impl/make_ready.py` once the host can start a process.

REPORT DONE
