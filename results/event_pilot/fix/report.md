MODEL: deepseek-v4.1-flash

# Detector-fault likelihood: fix and re-run of the three EVT INC pilot runs

## 1. The defect and the fix

`effective_obs` replaced detector i's **actual observation** with the fault prediction (stuck: the anchor; zero: 0) and `block_residual` compared that replacement with the no-event Twin replay. The residual (anchor - twin_baseline) therefore did not depend on what detector i reported, so a stuck or zero hypothesis erased i's observed anomaly and explained it for free (report2 G.4 requires the observations of that detector to be scored *under the fault model*).

The fix scores the observation against the prediction:

| Fault | Residual on detector i | Other detectors |
|---|---|---|
| stuck | (obs - anchor)/sigma for q, v, o | (obs - twin_baseline)/sigma |
| zero | (obs - 0)/sigma for q and o; v keeps the no-event replay value | (obs - twin_baseline)/sigma |
| noise | (obs - twin_baseline)/sigma with c = 5 (unchanged) | (obs - twin_baseline)/sigma |

The identical-support rule is untouched: the same `no_sigma` / `obs_invalid` / `obs_null` / `twin_null` / `no_anchor` returns in the same order, so O is the same set of (detector, block, channel) triples as before.

### Diff summary

| File | Lines | Change |
|---|---|---|
| `citypulse/twin/event.py` | 13-16 | module docstring: the residual is the observation against the hypothesis's prediction |
| `citypulse/twin/event.py` | 265 | new `_REPLAY` sentinel: no fault-model value, score against the no-event replay |
| `citypulse/twin/event.py` | 268-290 | `effective_obs` now returns the PREDICTION (stuck: anchor; zero: 0 for q/o, `_REPLAY` for v; noise/other: `_REPLAY` with c = 5), not a replacement for the observation |
| `citypulse/twin/event.py` | 292-323 | `block_residual` computes (obs - prediction)/sigma; `no_anchor`/`obs_invalid`/`obs_null`/`twin_null`/`no_sigma` exclusions unchanged, so the identical-support rule is untouched |
| `citypulse/twin/event.py` | 331-352 | new `logl_of_one`: logL of a single hypothesis over its own support (no demand family needed) |
| `tests/test_event.py` | 179-295 | 4 new tests: stuck and zero under a congested observation vs the anchor, noise unchanged, single-hypothesis logL |
| `results/event_pilot/impl/check_replay.py` | 4-5, 96-108 | check 2 no longer calls `ev.evaluate` for one hypothesis (no demand family -> `max()` on an empty sequence); it accumulates logL with `ev.logl_of_one` and reports n_O |
| `results/event_pilot/impl/check_replay.py` | 125 | check2 evidence records n_O for both runs |

`citypulse/twin/service.py` was **not** changed: it already passes the pre-t_on anchor (`anchor_for(t_on)`) and the down-weight map, and the fix lives entirely in `event.py`.

## 2. Tests

- `python -m pytest tests/test_event.py -q` -> **29 passed** (25 pre-existing + 4 new).
- Whole suite `python -m pytest tests/ -q` -> **96 passed, 3 skipped, 1 failed - `tests/test_sumo_integration.py::test_init_signals_resets_last_loaded_program`, which is pre-existing and unrelated: it asserts the SUMO TLS program after `init_signals` is `0` but the working tree's scenario loads `webster` (the untracked `scenarios/kwuntong/tls_webster_v3.add.xml` / `tls_webster_v4.add.xml` and the modified scenario files were already dirty before this task; the test imports neither `citypulse.twin.event` nor anything this change touches)**.

| Test | What it pins |
|---|---|
| `test_stuck_fault_scores_the_observation_against_the_anchor` | congested obs at U: stuck residuals (obs - anchor)/sigma = (23, -30, 23) and `logL(stuck) < logL(no-event baseline)`; obs == anchor: residuals 0 and `logL(stuck) > logL(baseline)`, and better than under congestion |
| `test_zero_fault_scores_the_observation_against_zero` | congested obs: residuals (25, -25, 25) (v is the no-event replay residual, byte-identical to the baseline's) and `logL(zero) < logL(baseline)`; obs == anchor: `logL(zero) > logL(baseline)` |
| `test_noise_fault_residual_is_unchanged` | noise residuals stay (obs - replay)/sigma = (13, -25, 13), c = 5 on U only, and logL keeps the -ln 5 normalisation |
| `test_single_hypothesis_logl_needs_no_demand_family` | one hypothesis alone is scored directly: n_O = 6, logL = -4.0, deterministic |

## 3. `check_replay.py` (checks 2 and 4)

Evaluating a single hypothesis called `ev.evaluate`, which needs a demand family for `gap_vs_demand` and the EVR and crashed on `max()` of an empty sequence. Check 2 now accumulates the logL with the new `ev.logl_of_one`.

- **Check 2** (`inc_ktb_n1_k2_s0.6`, snapshot twin_state_4800, t_on 4860, t_end 5400): logL_run1 = logL_run2 = **-527.610130418**, n_O = 138, veh_digest identical (6b7fee1a52f4531d...), interval tables identical: **True**.
- **Check 4**: lanes closed ['ktb_n1_0', 'ktb_n1_1'] disallowed in the replay (`restriction_present` = True); mean q at AID02111 drops from 7.22 (no-event) to 0.06 (incident), -99.23%, n_vehicles 324 -> 394: **flow_drops = True**.

## 4. The three re-run EVT INC seeds

Same arguments as `results/event_pilot/runs/evt_inc_<seed>/run_info.json` (harness `citypulse.experiments.event_pilot.run_two_world`, scenario INC, arm evt, twin seed 2, demand seed 202, base factor 0.85, `--event on --event-workers 4`, `--event-sigma results/event_pilot/impl/sigma_event.json`); only the output directory moved to `results/event_pilot/fix/evt_inc_<seed>/`.

### Seed 4001

- `results/event_pilot/fix/evt_inc_4001`: proxy_rc 0, twin_rc 0, wall 201.9 s, t_end 7200 s, 240 SensorMsgs, 240 trigger intervals, 13 hypothesis evaluations (154.2 s of replay wall time).
- Episode starts (`trigger_alarm`): 4890, 4920, 6090; alarm intervals (streak >= 2): 24.
- Down-weighted detectors: `{"AID02111": 5.0, "AID02109": 5.0}`; unexplained anomalies: `[{"t": 6000.0, "seconds": 960.0}]`.
- **Adoption time: none.** **Clearance time: none** (never entered EVENT_ASSIMILATION); `replacement_log.jsonl` is empty (0 replacements).

| t | from | to | reason |
|---|---|---|---|
| 4890 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 4890 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02111_zero` |
| 4920 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 5040 | SUSPECTED_EVENT | DEGRADED | `unresolved_3_evals` |
| 6000 | DEGRADED | NORMAL | `unexplained_anomaly` |
| 6090 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 6090 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02109_noise` |

| t | state | n_O | excluded | h* (location / severity) | logL(h*) | post(h*) | gap vs demand | EVR | adopted | wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 4890 | SUSPECTED_EVENT | 180 | `{"obs_invalid": 30}` | `flt_AID02111_zero` detector AID02111, type zero, c 1.0 | -35.09 | 0.3867 | 0.49 | 0.0929 | False | 11.1 |
| 4920 | SUSPECTED_EVENT | 144 | `{"partial_block": 84, "obs_invalid": 24}` | `dem_f1.15` entry tko_insert, factor 1.15 | -25.43 | 0.3051 | 0.00 | 0.0000 | False | 11.3 |
| 4980 | SUSPECTED_EVENT | 144 | `{"partial_block": 84, "obs_invalid": 24}` | `dem_f1.15` entry tko_insert, factor 1.15 | -25.43 | 0.3051 | 0.00 | 0.0000 | False | 12.4 |
| 5040 | SUSPECTED_EVENT | 177 | `{"partial_block": 84, "obs_invalid": 33}` | `dem_f1.15` entry tko_insert, factor 1.15 | -50.93 | 0.2777 | 0.00 | 0.0000 | False | 9.8 |
| 5160 | DEGRADED | 216 | `{"partial_block": 84, "obs_invalid": 36}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -69.97 | 1.0000 | 41.83 | -0.0081 | False | 10.3 |
| 5280 | DEGRADED | 249 | `{"partial_block": 84, "obs_invalid": 45}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -88.57 | 1.0000 | 86.22 | 0.0014 | False | 11.2 |
| 5400 | DEGRADED | 282 | `{"partial_block": 84, "obs_invalid": 54}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -107.84 | 1.0000 | 120.23 | -0.0001 | False | 10.4 |
| 5520 | DEGRADED | 321 | `{"partial_block": 84, "obs_invalid": 57}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -136.18 | 1.0000 | 171.18 | 0.0121 | False | 11.7 |
| 5640 | DEGRADED | 357 | `{"partial_block": 84, "obs_invalid": 63}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -192.27 | 1.0000 | 179.99 | 0.0029 | False | 12.1 |
| 5760 | DEGRADED | 393 | `{"partial_block": 84, "obs_invalid": 69}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -271.40 | 1.0000 | 180.68 | -0.0113 | False | 13.8 |
| 5880 | DEGRADED | 435 | `{"partial_block": 84, "obs_invalid": 69}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -362.84 | 1.0000 | 181.55 | -0.0270 | False | 15.1 |
| 6000 | DEGRADED | 468 | `{"partial_block": 84, "obs_invalid": 78}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -406.59 | 1.0000 | 183.57 | -0.0331 | False | 17.4 |
| 6090 | SUSPECTED_EVENT | 183 | `{"obs_invalid": 27}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -297.46 | 1.0000 | 18.37 | -0.0942 | False | 7.4 |

**Top-5 at t = 4890 s** (state SUSPECTED_EVENT, t_on 4290, wall 11.1 s, excluded `{"obs_invalid": 30}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02111_zero` | fault | -35.09 | 0.3867 | 180 |
  | 2 | `dem_f1.3` | demand | -38.68 | 0.2363 | 180 |
  | 3 | `inc_ktb_n1_k1_s1` | incident | -38.69 | 0.1570 | 180 |
  | 4 | `dem_f1.15` | demand | -40.17 | 0.1627 | 180 |
  | 5 | `flt_AID02111_stuck` | fault | -44.13 | 0.0403 | 180 |

**Top-5 at t = 4920 s** (state SUSPECTED_EVENT, t_on 4320, wall 11.3 s, excluded `{"partial_block": 84, "obs_invalid": 24}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `dem_f1.15` | demand | -25.43 | 0.3051 | 144 |
  | 2 | `dem_f1.3` | demand | -25.97 | 0.2672 | 144 |
  | 3 | `flt_AID02111_zero` | fault | -26.66 | 0.1495 | 144 |
  | 4 | `flt_AID02111_stuck` | fault | -26.77 | 0.1458 | 144 |
  | 5 | `inc_ktb_n1_k1_s1` | incident | -29.84 | 0.0676 | 144 |

**Top-5 at t = 4980 s** (state SUSPECTED_EVENT, t_on 4320, wall 12.4 s, excluded `{"partial_block": 84, "obs_invalid": 24}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `dem_f1.15` | demand | -25.43 | 0.3051 | 144 |
  | 2 | `dem_f1.3` | demand | -25.97 | 0.2672 | 144 |
  | 3 | `flt_AID02111_zero` | fault | -26.66 | 0.1495 | 144 |
  | 4 | `flt_AID02111_stuck` | fault | -26.77 | 0.1458 | 144 |
  | 5 | `inc_ktb_n1_k1_s1` | incident | -29.84 | 0.0676 | 144 |

**Top-5 at t = 5040 s** (state SUSPECTED_EVENT, t_on 4320, wall 9.8 s, excluded `{"partial_block": 84, "obs_invalid": 33}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -50.29 | 0.2172 | 177 |
  | 2 | `dem_f1.15` | demand | -50.93 | 0.2777 | 177 |
  | 3 | `inc_ktb_n1_k1_s1` | incident | -52.17 | 0.1357 | 177 |
  | 4 | `flt_AID02111_zero` | fault | -52.59 | 0.1223 | 177 |
  | 5 | `flt_AID02111_stuck` | fault | -52.75 | 0.1176 | 177 |

**Top-5 at t = 5160 s** (state DEGRADED, t_on 4320, wall 10.3 s, excluded `{"partial_block": 84, "obs_invalid": 36}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -69.97 | 1.0000 | 216 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -218.37 | 0.0000 | 216 |
  | 3 | `dem_f1.15` | demand | -238.92 | 0.0000 | 216 |
  | 4 | `dem_f1.3` | demand | -239.70 | 0.0000 | 216 |
  | 5 | `flt_AID02111_zero` | fault | -240.26 | 0.0000 | 216 |

**Top-5 at t = 5280 s** (state DEGRADED, t_on 4320, wall 11.2 s, excluded `{"partial_block": 84, "obs_invalid": 45}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -88.57 | 1.0000 | 249 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -390.84 | 0.0000 | 249 |
  | 3 | `flt_AID02111_zero` | fault | -433.89 | 0.0000 | 249 |
  | 4 | `flt_AID02111_stuck` | fault | -434.11 | 0.0000 | 249 |
  | 5 | `dem_f1.3` | demand | -435.08 | 0.0000 | 249 |

**Top-5 at t = 5400 s** (state DEGRADED, t_on 4320, wall 10.4 s, excluded `{"partial_block": 84, "obs_invalid": 54}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -107.84 | 1.0000 | 282 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -517.19 | 0.0000 | 282 |
  | 3 | `flt_AID02111_zero` | fault | -589.65 | 0.0000 | 282 |
  | 4 | `flt_AID02111_stuck` | fault | -589.93 | 0.0000 | 282 |
  | 5 | `dem_f1.3` | demand | -590.37 | 0.0000 | 282 |

**Top-5 at t = 5520 s** (state DEGRADED, t_on 4320, wall 11.7 s, excluded `{"partial_block": 84, "obs_invalid": 57}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -136.18 | 1.0000 | 321 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -694.47 | 0.0000 | 321 |
  | 3 | `inc_ktb_n2_k1_s1` | incident | -794.53 | 0.0000 | 321 |
  | 4 | `flt_AID02111_zero` | fault | -812.01 | 0.0000 | 321 |
  | 5 | `flt_AID02111_stuck` | fault | -812.15 | 0.0000 | 321 |

**Top-5 at t = 5640 s** (state DEGRADED, t_on 4320, wall 12.1 s, excluded `{"partial_block": 84, "obs_invalid": 63}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -192.27 | 1.0000 | 357 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -778.75 | 0.0000 | 357 |
  | 3 | `inc_ktb_n2_k1_s1` | incident | -859.76 | 0.0000 | 357 |
  | 4 | `flt_AID02111_zero` | fault | -910.59 | 0.0000 | 357 |
  | 5 | `flt_AID02111_stuck` | fault | -910.72 | 0.0000 | 357 |

**Top-5 at t = 5760 s** (state DEGRADED, t_on 4320, wall 13.8 s, excluded `{"partial_block": 84, "obs_invalid": 69}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -271.40 | 1.0000 | 393 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -859.85 | 0.0000 | 393 |
  | 3 | `inc_ktb_n2_k1_s1` | incident | -915.20 | 0.0000 | 393 |
  | 4 | `dem_f1.3` | demand | -995.75 | 0.0000 | 393 |
  | 5 | `flt_AID02111_zero` | fault | -1006.41 | 0.0000 | 393 |

**Top-5 at t = 5880 s** (state DEGRADED, t_on 4320, wall 15.1 s, excluded `{"partial_block": 84, "obs_invalid": 69}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -362.84 | 1.0000 | 435 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -968.45 | 0.0000 | 435 |
  | 3 | `inc_ktb_n2_k1_s1` | incident | -992.09 | 0.0000 | 435 |
  | 4 | `dem_f1.3` | demand | -1090.67 | 0.0000 | 435 |
  | 5 | `flt_AID02111_stuck` | fault | -1119.79 | 0.0000 | 435 |

**Top-5 at t = 6000 s** (state DEGRADED, t_on 4320, wall 17.4 s, excluded `{"partial_block": 84, "obs_invalid": 78}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -406.59 | 1.0000 | 468 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -1017.39 | 0.0000 | 468 |
  | 3 | `inc_ktb_n2_k1_s1` | incident | -1027.44 | 0.0000 | 468 |
  | 4 | `dem_f1.3` | demand | -1142.48 | 0.0000 | 468 |
  | 5 | `dem_f1.15` | demand | -1176.39 | 0.0000 | 468 |

**Top-5 at t = 6090 s** (state SUSPECTED_EVENT, t_on 5490, wall 7.4 s, excluded `{"obs_invalid": 27}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -297.46 | 1.0000 | 183 |
  | 2 | `inc_ktb_n2_k1_s1` | incident | -350.11 | 0.0000 | 183 |
  | 3 | `dem_f1.3` | demand | -372.54 | 0.0000 | 183 |
  | 4 | `inc_ktb_n1_k1_s1` | incident | -375.66 | 0.0000 | 183 |
  | 5 | `inc_ktb_n1_k2_s0.6` | incident | -392.48 | 0.0000 | 183 |

### Seed 4002

- `results/event_pilot/fix/evt_inc_4002`: proxy_rc 0, twin_rc 0, wall 95.1 s, t_end 7200 s, 240 SensorMsgs, 240 trigger intervals, 3 hypothesis evaluations (35.6 s of replay wall time).
- Episode starts (`trigger_alarm`): 4890, 4980; alarm intervals (streak >= 2): 4.
- Down-weighted detectors: `{"AID02111": 5.0, "AID02109": 5.0}`; unexplained anomalies: `[]`.
- **Adoption time: none.** **Clearance time: none** (never entered EVENT_ASSIMILATION); `replacement_log.jsonl` is empty (0 replacements).

| t | from | to | reason |
|---|---|---|---|
| 4890 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 4890 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02111_zero` |
| 4980 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 5040 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02109_stuck` |

| t | state | n_O | excluded | h* (location / severity) | logL(h*) | post(h*) | gap vs demand | EVR | adopted | wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 4890 | SUSPECTED_EVENT | 174 | `{"obs_invalid": 36}` | `flt_AID02111_zero` detector AID02111, type zero, c 1.0 | -37.18 | 0.4527 | 1.23 | 0.1493 | False | 11.2 |
| 4980 | SUSPECTED_EVENT | 138 | `{"partial_block": 84, "obs_invalid": 30}` | `dem_f1.3` entry tko_insert, factor 1.3 | -26.55 | 0.2846 | 0.00 | 0.0000 | False | 11.6 |
| 5040 | SUSPECTED_EVENT | 174 | `{"partial_block": 84, "obs_invalid": 36}` | `flt_AID02109_stuck` detector AID02109, type stuck, c 1.0 | -46.32 | 0.3866 | 1.51 | 0.1419 | False | 12.8 |

**Top-5 at t = 4890 s** (state SUSPECTED_EVENT, t_on 4290, wall 11.2 s, excluded `{"obs_invalid": 36}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02111_zero` | fault | -37.18 | 0.4527 | 174 |
  | 2 | `flt_AID02111_stuck` | fault | -41.15 | 0.1676 | 174 |
  | 3 | `dem_f1.15` | demand | -43.70 | 0.1330 | 174 |
  | 4 | `inc_ktb_n1_k1_s1` | incident | -44.43 | 0.0739 | 174 |
  | 5 | `dem_f1.3` | demand | -45.72 | 0.0801 | 174 |

**Top-5 at t = 4980 s** (state SUSPECTED_EVENT, t_on 4380, wall 11.6 s, excluded `{"partial_block": 84, "obs_invalid": 30}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `dem_f1.3` | demand | -26.55 | 0.2846 | 138 |
  | 2 | `flt_AID02111_stuck` | fault | -26.60 | 0.1875 | 138 |
  | 3 | `flt_AID02111_zero` | fault | -26.61 | 0.1870 | 138 |
  | 4 | `dem_f1.15` | demand | -28.21 | 0.1882 | 138 |
  | 5 | `flt_AID02109_stuck` | fault | -30.65 | 0.0682 | 138 |

**Top-5 at t = 5040 s** (state SUSPECTED_EVENT, t_on 4380, wall 12.8 s, excluded `{"partial_block": 84, "obs_invalid": 36}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_stuck` | fault | -46.32 | 0.3866 | 174 |
  | 2 | `flt_AID02109_noise` | fault | -48.00 | 0.2535 | 174 |
  | 3 | `flt_AID02111_zero` | fault | -51.40 | 0.1084 | 174 |
  | 4 | `flt_AID02111_stuck` | fault | -51.41 | 0.1083 | 174 |
  | 5 | `dem_f1.15` | demand | -53.97 | 0.0855 | 174 |

### Seed 4003

- `results/event_pilot/fix/evt_inc_4003`: proxy_rc 0, twin_rc 0, wall 96.5 s, t_end 7200 s, 240 SensorMsgs, 240 trigger intervals, 3 hypothesis evaluations (36.6 s of replay wall time).
- Episode starts (`trigger_alarm`): 4920, 4950; alarm intervals (streak >= 2): 4.
- Down-weighted detectors: `{"AID02111": 5.0, "AID02109": 5.0}`; unexplained anomalies: `[]`.
- **Adoption time: none.** **Clearance time: none** (never entered EVENT_ASSIMILATION); `replacement_log.jsonl` is empty (0 replacements).

| t | from | to | reason |
|---|---|---|---|
| 4920 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 4920 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02111_zero` |
| 4950 | NORMAL | SUSPECTED_EVENT | `trigger_alarm` |
| 5010 | SUSPECTED_EVENT | NORMAL | `detector_fault_AID02109_noise` |

| t | state | n_O | excluded | h* (location / severity) | logL(h*) | post(h*) | gap vs demand | EVR | adopted | wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 4920 | SUSPECTED_EVENT | 144 | `{"partial_block": 84, "obs_invalid": 24}` | `flt_AID02111_zero` detector AID02111, type zero, c 1.0 | -37.54 | 0.4078 | 1.30 | 0.1535 | False | 11.7 |
| 4950 | SUSPECTED_EVENT | 144 | `{"partial_block": 84, "obs_invalid": 24}` | `dem_f1.15` entry tko_insert, factor 1.15 | -35.43 | 0.3096 | 0.00 | 0.0000 | False | 11.9 |
| 5010 | SUSPECTED_EVENT | 183 | `{"partial_block": 42, "obs_invalid": 27}` | `flt_AID02109_noise` detector AID02109, type noise, c 5.0 | -57.15 | 0.9965 | 8.80 | 0.0480 | False | 13.0 |

**Top-5 at t = 4920 s** (state SUSPECTED_EVENT, t_on 4320, wall 11.7 s, excluded `{"partial_block": 84, "obs_invalid": 24}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02111_zero` | fault | -37.54 | 0.4078 | 144 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -40.16 | 0.2122 | 144 |
  | 3 | `flt_AID02111_stuck` | fault | -41.48 | 0.1524 | 144 |
  | 4 | `dem_f1.15` | demand | -44.35 | 0.1116 | 144 |
  | 5 | `flt_AID02111_noise` | fault | -47.25 | 0.0360 | 144 |

**Top-5 at t = 4950 s** (state SUSPECTED_EVENT, t_on 4350, wall 11.9 s, excluded `{"partial_block": 84, "obs_invalid": 24}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `dem_f1.15` | demand | -35.43 | 0.3096 | 144 |
  | 2 | `flt_AID02109_stuck` | fault | -36.28 | 0.1669 | 144 |
  | 3 | `flt_AID02111_zero` | fault | -36.32 | 0.1655 | 144 |
  | 4 | `flt_AID02111_stuck` | fault | -36.53 | 0.1568 | 144 |
  | 5 | `dem_f1.3` | demand | -39.70 | 0.1065 | 144 |

**Top-5 at t = 5010 s** (state SUSPECTED_EVENT, t_on 4350, wall 13.0 s, excluded `{"partial_block": 42, "obs_invalid": 27}`):

  | rank | hypothesis | family | logL | posterior | n_O |
  |---|---|---|---|---|---|
  | 1 | `flt_AID02109_noise` | fault | -57.15 | 0.9965 | 183 |
  | 2 | `inc_ktb_n1_k1_s1` | incident | -82.78 | 0.0016 | 183 |
  | 3 | `flt_AID02109_stuck` | fault | -84.95 | 0.0010 | 183 |
  | 4 | `flt_AID02111_zero` | fault | -89.03 | 0.0003 | 183 |
  | 5 | `flt_AID02111_stuck` | fault | -89.34 | 0.0003 | 183 |

## 5. Controls (EVT NOI / SHK / DET)

The control EVT runs had zero triggers, so no evaluation ran in them; they are unaffected by construction, because the likelihood is only reached from an evaluation and the fault-model branch is only reached inside it. Verified on disk: `event_log.jsonl` is 0 bytes / 0 rows in all nine control runs.

| control run | event_log.jsonl bytes | rows |
|---|---|---|
| `evt_det_4001` | 0 | 0 |
| `evt_det_4002` | 0 | 0 |
| `evt_det_4003` | 0 | 0 |
| `evt_noi_4001` | 0 | 0 |
| `evt_noi_4002` | 0 | 0 |
| `evt_noi_4003` | 0 | 0 |
| `evt_shk_4001` | 0 | 0 |
| `evt_shk_4002` | 0 | 0 |
| `evt_shk_4003` | 0 | 0 |

## 6. What the fix changed (on-disk before/after)

`flt_AID02109_stuck` is the hypothesis that used to explain every alarm. Its logL at the evaluation timestamps both the old and the fixed run scored:

| seed | t | old (anchor - replay) | fixed (obs - anchor) | change |
|---|---|---|---|---|
| 4001 | 4890 | -40.09 | -49.69 | -9.60 |
| 4001 | 5040 | -39.46 | -62.75 | -23.29 |
| 4002 | 4890 | -44.02 | -45.91 | -1.89 |
| 4002 | 4980 | -33.09 | -30.65 | +2.44 |
| 4002 | 5040 | -43.38 | -46.32 | -2.93 |
| 4003 | 4920 | -39.32 | -50.00 | -10.68 |

Block residuals on AID02109 for seed 4001 at the first alarm (t = 4890 s, t_on = 4290 s), reconstructed from the run's logged observations and anchor (`evidence/fault_likelihood_before_after.json`):

| block (120 s) | fixed q | fixed v | fixed o | old q | old v | old o |
|---|---|---|---|---|---|---|
| 36 | 0.08 | -0.70 | 1.54 | 0.04 | 0.42 | -1.22 |
| 37 | 0.04 | -0.95 | 1.54 | 0.04 | 0.31 | -1.10 |
| 38 | - | - | - | 0.42 | -0.03 | -0.72 |
| 39 | -0.25 | -0.68 | 1.13 | -0.08 | 0.51 | -1.25 |
| 40 | 0.42 | -3.23 | 2.47 | 0.17 | 0.88 | -1.25 |

In the last block (4800-4890 s) the queue's speed drop is charged to the stuck hypothesis (v = -3.23 sigma, o = +2.47 sigma) whereas the old formula scored it as a near-perfect fit (v = +0.88, o = -1.25: the wrong sign).

### Result of the re-run

- The stuck hypothesis no longer wins a first evaluation: at the first alarm of each seed its logL fell by 1.9 to 10.7 units and it left the top-5 in seeds 4001 and 4003 (it still wins seed 4002's third evaluation at 5040 s and is runner-up in seed 4003 at 4950 s, where the observation has come back to the anchor level, which is what the stuck model predicts).
- The MAP at the first evaluation is now `flt_AID02111_zero` in all three seeds: the downstream detector really reports q = 0 and o ~ 0 while queued, and the zero model predicts exactly that, so the two are indistinguishable on that detector alone. The remaining discriminators are the other detectors (scored against the no-event replay) and the temporal pattern.
- The incident family stays close but does not clear the ln-10 gap: at seed 4001 t = 4890 s the top incident hypothesis `inc_ktb_n1_k1_s1` (edge ktb_n1 @ 503.1 m, 1 of 3 lanes closed, speed factor 1.0) is 3.6 log units behind `flt_AID02111_zero` (posterior 0.157 vs 0.387), and it is the top incident member at every evaluation of every seed. The demand family's total posterior peaks at 0.577 (seed 4001 t = 4920/4980 s), below the 0.6 twice-in-a-row rule, so no false alarm was written and `false_alarms` is empty. **No seed adopted an incident, so no clearance evaluation ran** (EVENT_ASSIMILATION was never entered); the state machine returned to NORMAL through `detector_fault_*` (and, in seed 4001, through `unresolved_3_evals` -> DEGRADED -> `unexplained_anomaly`).
- EVR is reported per evaluation above; it is 0.09-0.15 for the zero-fault MAP and negative once the noise hypothesis (c = 5, out of scope by the spec) takes over.
- **Remaining, out-of-scope degeneracies** (both are what the spec's own residual definitions imply, not the defect this task fixed): a queued detector reports q = 0 and o ~ 0, which is exactly what the zero model predicts, so `flt_AID02111_zero` is nearly free on AID02111; and the noise model keeps the observation but divides its residual by c = 5, so `flt_AID02109_noise` wins once AID02109's residuals grow (it takes over from 5040 s on). The incident replay has to beat both on the *other* detectors to be adopted, and it does not clear the ln-10 gap within the 1-3 evaluations each episode gets before the state machine acts on the MAP.

## 7. Evidence files

| File | Contents |
|---|---|
| `results/event_pilot/fix/evidence/check2_deterministic_replay.json` | check 2: one hypothesis scored twice from the same snapshot |
| `results/event_pilot/fix/evidence/check4_capacity_restriction.json` | check 4: incident vs no-event replay, disallowed lanes and downstream flow at AID02111 |
| `results/event_pilot/fix/evidence/check7_state_replacement.json` | check 7: the fixed runs' replacement logs (no adoption) and the empty control event logs |
| `results/event_pilot/fix/evidence/check7_live_replacement_mechanics.json` | check 7 mechanics, exercised directly on the pinned episode snapshot (digest, count, live lane disallow) |
| `results/event_pilot/fix/evidence/fault_likelihood_before_after.json` | the defect: stuck residuals on AID02109/AID02111, old formula vs fixed formula, and old/new stuck logL |
| `results/event_pilot/fix/summary.json` | every fixed run's state trace, evaluations, trigger log size and run_info |

## 8. Check 7

- No fixed run adopted, so no pilot adoption exercised the replacement path: `adoption_happened = false`, `replacement_log.jsonl` empty in all three seeds.
- The mechanics are verified directly instead (`evidence/check7_live_replacement_mechanics.json`, hypothesis `inc_ktb_n1_k1_s1`, snapshot `event_snapshot_4230.xml.gz`, t_on 4290 -> t_end 4890): the live Twin's vehicle digest `1119eebc74f790bc...` and count 302 equal the replay endpoint's (`1119eebc74f790bc...`, 302); the lane disallow read live is `{"ktb_n1_0": ["passenger", "bus", "delivery", "truck", "trailer"]}` and `restriction_present` is true in both. **passed = true**.

## 9. Files written

- `results/event_pilot/fix/evt_inc_4001/`, `evt_inc_4002/`, `evt_inc_4003/` (twin + proxy logs, state traces, event logs, snapshots) - the three re-runs, old runs untouched.
- `results/event_pilot/fix/evidence/` - the five evidence files above.
- `results/event_pilot/fix/summary.json`, `results/event_pilot/fix/report.md`.
- `results/event_pilot/fix/run_evt_inc.py`, `make_evidence.py`, `make_report.py`, `check7_live_replacement.py` - the drivers (new outputs under `fix/`).
- Edited: `citypulse/twin/event.py`, `tests/test_event.py`, `results/event_pilot/impl/check_replay.py` (and its regenerated `impl/check_replay.json`).
Nothing was committed.

REPORT DONE
