MODEL: deepseek-v4.1-flash

# Second development pilot of the event engine (pilot 2, part B)

Binding spec: `docs/oct6-audit-and-pilot2-plan.md` part B; base plan `docs/oct6-event-pilot-plan.md`; first pilot `results/event_pilot/fix/report.md`. Development only; no E* claim, no acceptance. Nothing was committed.

## 1. What changed and what did not

| Item | pilot 1 | pilot 2 |
|---|---|---|
| Incident grid | 6 hypotheses, (k, s) in {(1, 1.0), (2, 0.6)} on 3-lane edges, {(1, 1.0), (1, 0.6)} on `ktb_n2` | k in {1, ..., min(2, n_lanes - 1)} x s in {0.6, 1.0}: 4 + 4 + 2 = **10** incident hypotheses |
| Library | 16 (6 incident, 4 demand, 6 fault) | **20** (10, 4, 6); family mass still 1/3, uniform inside the family (1/30 per incident hypothesis) |
| DEGRADED bound | next evaluation past 15 min (observed 960 s in pilot 1) | **entry + 900 s exactly**, on the 30-s tick, independent of evaluations |
| Locations / onset / noise / beta / tau_LR / trigger / thresholds | - | unchanged |

Implementation, all behind explicit switches (pilot-1 behaviour is the default): `build_hypotheses(grid=...)` and `EventStateMachine(degraded_exit="scheduled")` and `forced_adoption` in `citypulse/twin/event.py`; `--event-grid`, `--event-force-hstar` and the tick-scheduled DEGRADED exit in `citypulse/twin/service.py`; the pilot-2 run set, forecast and alarm helpers in `citypulse/experiments/event_pilot.py`; 11 new unit tests in `tests/test_event.py` (40 pass, was 29). `citypulse/branching/engine.py` is **not** changed.

### One pilot-1 defect had to be fixed to reach the required integration coverage

`EventRuntime` never wrote `EventStateMachine.restriction`, so `lift_spec()` was always empty and every `H_clear(tau_c)` replay was identical to the active replay: `P_clear` would have sat at its 0.5 prior for ever and clearance could never fire. The service now records the live restriction (closed lanes + the pre-restriction max speed of the lanes the spec scales) before the replacement restarts SUMO (`EventRuntime.restriction_of` -> `event.restriction_record`). No engine change; pilot-1 runs never adopted, so their results are unaffected.

## 2. Runs

Fresh development seeds 4101-4103; CONV arguments identical to the first pilot (`results/event_pilot/runs/evt_inc_4001/run_info.json`): twin seed 2, demand seed 202, base factor 0.85, `--assim normal300 --boundary-detector AID07106`, sigma from `results/assim/na300/sigma300_dev.json`, `--event-sigma results/event_pilot/impl/sigma_event.json`, `--event-workers 4`. INC: EVT + CONV; NOI: EVT only.

| run | scen | arm | seed | rc p/t | wall s | alarm events | exposure min | evals | replacements | adopted |
|---|---|---|---|---|---|---|---|---|---|---|
| `conv_inc_4101` | INC | conv | 4101 | 0/0 | 57.4 | 2 | 9.5 | None | None | no |
| `conv_inc_4102` | INC | conv | 4102 | 0/0 | 53.8 | 4 | 8.0 | None | None | no |
| `conv_inc_4103` | INC | conv | 4103 | 0/0 | 68.0 | 3 | 11.0 | None | None | no |
| `evt_inc_4101` | INC | evt | 4101 | 0/0 | 106.4 | 2 | 9.5 | 4 | 0 | no |
| `evt_inc_4102` | INC | evt | 4102 | 0/0 | 102.0 | 4 | 8.0 | 4 | 0 | no |
| `evt_inc_4103` | INC | evt | 4103 | 0/0 | 126.4 | 3 | 11.0 | 5 | 0 | no |
| `evt_noi_4101` | NOI | evt | 4101 | 0/0 | 63.2 | 0 | 0.0 | 0 | 0 | no |
| `evt_noi_4102` | NOI | evt | 4102 | 0/0 | 59.3 | 0 | 0.0 | 0 | 0 | no |
| `evt_noi_4103` | NOI | evt | 4103 | 0/0 | 71.1 | 0 | 0.0 | 0 | 0 | no |
| `evtforce_inc_4101` | INC | evt | 4101 | 0/0 | 209.2 | 2 | 9.5 | 7 | 4 | yes (forced + natural) |
| `evtforce_inc_4102` | INC | evt | 4102 | 0/0 | 199.7 | 4 | 8.5 | 7 | 2 | yes (forced) |
| `evtforce_inc_4103` | INC | evt | 4103 | 0/0 | 209.2 | 3 | 11.0 | 9 | 2 | yes (forced) |

Queue forecasts: 5-min and 15-min frozen replays from every 5-min snapshot (4,500-6,600 s), scored against Proxy truth (`queue_forecasts.json` per run).

## 3. Natural adoption, h*, EVR

**No natural adoption occurred in any of the three INC EVT runs.** Natural adoption per primary run: {'evt_inc_4101': False, 'evt_inc_4102': False, 'evt_inc_4103': False}; forced runs are in §6. The three runs evaluated the 20-hypothesis library 13 times in total and the MAP was never an incident hypothesis (any_natural_adoption_inc_evt = False).

### `evt_inc_4101`

- Episode alarms: [5010, 5040, 5070, 5100, 5130, 5160]; state trace: 5010 NORMAL->SUSPECTED_EVENT (trigger_alarm); 5010 SUSPECTED_EVENT->NORMAL (detector_fault_AID02111_zero); 5040 NORMAL->SUSPECTED_EVENT (trigger_alarm); 5160 SUSPECTED_EVENT->NORMAL (detector_fault_AID02109_noise).
- Adoption time: **none**. Clearance time: **none** (EVENT_ASSIMILATION never entered; `replacement_log.jsonl` has 0 rows). Down-weighted detectors: `{'AID02111': 5.0, 'AID02109': 5.0}`.

| t | h* (MAP) | family | edge/entry | lanes closed | s | logL(h*) | post(h*) | gap vs demand | EVR | n_O | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5010 | flt_AID02111_zero | fault |  |  |  | -28.38 | 0.8014 | 2.124 | 0.2628 | 165 | 11.5 |
| 5040 | dem_f1.15 | demand | tko_insert |  |  | -21.36 | 0.3996 | 0.000 | 0.0000 | 135 | 10.4 |
| 5100 | dem_f1.15 | demand | tko_insert |  |  | -21.36 | 0.3996 | 0.000 | 0.0000 | 135 | 11.2 |
| 5160 | flt_AID02109_noise | fault |  |  |  | -49.52 | 0.9989 | 7.537 | -0.0389 | 174 | 12.2 |

The incident family's own reading (best incident member vs the best demand member, on the same support):

| t | best incident | post | best demand | post | log gap inc vs demand | log gap inc vs MAP | would adopt |
|---|---|---|---|---|---|---|---|
| 5010 | inc_ktb_n1_k1_s1 | 0.0274 | dem_f1.15 | 0.0958 | -1.252 | -3.376 | no |
| 5040 | inc_ktb_n1_k1_s1 | 0.0039 | dem_f1.15 | 0.3996 | -4.623 | -4.623 | no |
| 5100 | inc_ktb_n1_k1_s1 | 0.0039 | dem_f1.15 | 0.3996 | -4.623 | -4.623 | no |
| 5160 | inc_ktb_n1_k1_s1 | 0.0002 | dem_f1.15 | 0.0005 | -0.909 | -8.446 | no |

### `evt_inc_4102`

- Episode alarms: [4890, 4920, 4950, 4980, 5010, 5040]; state trace: 4890 NORMAL->SUSPECTED_EVENT (trigger_alarm); 4890 SUSPECTED_EVENT->NORMAL (detector_fault_AID02111_zero); 4920 NORMAL->SUSPECTED_EVENT (trigger_alarm); 5040 SUSPECTED_EVENT->NORMAL (detector_fault_AID02109_noise).
- Adoption time: **none**. Clearance time: **none** (EVENT_ASSIMILATION never entered; `replacement_log.jsonl` has 0 rows). Down-weighted detectors: `{'AID02111': 5.0, 'AID02109': 5.0}`.

| t | h* (MAP) | family | edge/entry | lanes closed | s | logL(h*) | post(h*) | gap vs demand | EVR | n_O | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4890 | flt_AID02111_zero | fault |  |  |  | -42.74 | 0.5944 | 2.235 | 0.1982 | 177 | 11.0 |
| 4920 | dem_f1.15 | demand | tko_insert |  |  | -34.02 | 0.2295 | 0.000 | 0.0000 | 141 | 10.9 |
| 4980 | dem_f1.15 | demand | tko_insert |  |  | -34.02 | 0.2295 | 0.000 | 0.0000 | 141 | 11.3 |
| 5040 | flt_AID02109_noise | fault |  |  |  | -54.23 | 0.9992 | 8.427 | -0.0712 | 177 | 12.2 |

The incident family's own reading (best incident member vs the best demand member, on the same support):

| t | best incident | post | best demand | post | log gap inc vs demand | log gap inc vs MAP | would adopt |
|---|---|---|---|---|---|---|---|
| 4890 | inc_ktb_n1_k1_s1 | 0.0238 | dem_f1.15 | 0.0636 | -0.982 | -3.218 | no |
| 4920 | inc_ktb_n1_k1_s1 | 0.0146 | dem_f1.15 | 0.2295 | -2.752 | -2.752 | no |
| 4980 | inc_ktb_n1_k1_s1 | 0.0146 | dem_f1.15 | 0.2295 | -2.752 | -2.752 | no |
| 5040 | inc_ktb_n1_k1_s1 | 0.0001 | dem_f1.15 | 0.0002 | -0.835 | -9.263 | no |

### `evt_inc_4103`

- Episode alarms: [4860, 4890, 4920, 4950, 4980, 5010]; state trace: 4860 NORMAL->SUSPECTED_EVENT (trigger_alarm); 4860 SUSPECTED_EVENT->NORMAL (detector_fault_AID02111_stuck); 4890 NORMAL->SUSPECTED_EVENT (trigger_alarm); 4890 SUSPECTED_EVENT->NORMAL (detector_fault_AID02111_stuck); 4920 NORMAL->SUSPECTED_EVENT (trigger_alarm); 5040 SUSPECTED_EVENT->NORMAL (detector_fault_AID02109_noise).
- Adoption time: **none**. Clearance time: **none** (EVENT_ASSIMILATION never entered; `replacement_log.jsonl` has 0 rows). Down-weighted detectors: `{'AID02111': 5.0, 'AID02109': 5.0}`.

| t | h* (MAP) | family | edge/entry | lanes closed | s | logL(h*) | post(h*) | gap vs demand | EVR | n_O | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4860 | flt_AID02111_stuck | fault |  |  |  | -23.68 | 0.3487 | 0.114 | 0.0807 | 144 | 12.4 |
| 4890 | flt_AID02111_stuck | fault |  |  |  | -34.51 | 0.2588 | 0.239 | 0.0695 | 177 | 12.1 |
| 4920 | dem_f1.3 | demand | tko_insert |  |  | -29.90 | 0.4090 | 0.000 | 0.0000 | 141 | 12.1 |
| 4980 | dem_f1.3 | demand | tko_insert |  |  | -29.90 | 0.4090 | 0.000 | 0.0000 | 141 | 14.2 |
| 5040 | flt_AID02109_noise | fault |  |  |  | -54.08 | 0.5680 | 1.546 | -0.1036 | 177 | 20.1 |

The incident family's own reading (best incident member vs the best demand member, on the same support):

| t | best incident | post | best demand | post | log gap inc vs demand | log gap inc vs MAP | would adopt |
|---|---|---|---|---|---|---|---|
| 4860 | inc_ktb_n1_k1_s1 | 0.0202 | dem_f1.3 | 0.3111 | -2.737 | -2.851 | no |
| 4890 | inc_ktb_n1_k1_s1 | 0.0585 | dem_f1.15 | 0.2037 | -1.248 | -1.487 | no |
| 4920 | inc_ktb_n1_k1_s1 | 0.0525 | dem_f1.3 | 0.4090 | -2.052 | -2.052 | no |
| 4980 | inc_ktb_n1_k1_s1 | 0.0525 | dem_f1.3 | 0.4090 | -2.052 | -2.052 | no |
| 5040 | inc_ktb_n1_k1_s1 | 0.2191 | dem_f1.3 | 0.1210 | 0.593 | -0.953 | no |

Adoption needs h* in the incident family and gap > ln 10 = 2.3026. Across all evaluations the MAP-vs-demand gap reached at most 8.427; the best incident member was at most 0.593 log units above the best demand member, i.e. at least 1.709 log units short of the threshold. No evaluation even had the incident family as the MAP.

**EVR** is reported per evaluation above; it is `1 - SSE(h*)/min_demand SSE`, so it is positive whenever the fault or demand MAP fits the observations better than the best demand member and is not an incident diagnostic. It ranged -0.1036 to 0.2628.

## 4. Forecast errors (descriptive)

Halting vehicles on `ktb_w3` + `ktb_n1`, predicted by a frozen 900-s replay from each 5-min snapshot and scored against Proxy truth. Negative bias = under-prediction.

| run | 5-min MAE | 5-min RMSE | 5-min bias | n | 15-min MAE | 15-min RMSE | 15-min bias | n |
|---|---|---|---|---|---|---|---|---|
| `conv_inc_4101` | 7.88 | 11.96 | -7.88 | 8 | 5.00 | 9.45 | -5.00 | 7 |
| `conv_inc_4102` | 24.12 | 44.81 | -24.12 | 8 | 24.29 | 47.33 | -24.29 | 7 |
| `conv_inc_4103` | 25.75 | 50.87 | -25.75 | 8 | 25.86 | 53.85 | -25.86 | 7 |
| `evt_inc_4101` | 7.88 | 11.96 | -7.88 | 8 | 5.00 | 9.45 | -5.00 | 7 |
| `evt_inc_4102` | 24.12 | 44.81 | -24.12 | 8 | 24.29 | 47.33 | -24.29 | 7 |
| `evt_inc_4103` | 25.75 | 50.87 | -25.75 | 8 | 25.86 | 53.85 | -25.86 | 7 |
| `evt_noi_4101` | 0.00 | 0.00 | 0.00 | 8 | 0.00 | 0.00 | 0.00 | 7 |
| `evt_noi_4102` | 0.00 | 0.00 | 0.00 | 8 | 0.00 | 0.00 | 0.00 | 7 |
| `evt_noi_4103` | 0.00 | 0.00 | 0.00 | 8 | 0.00 | 0.00 | 0.00 | 7 |
| `evtforce_inc_4101` | 6.50 | 10.16 | -6.50 | 8 | 6.57 | 10.32 | -3.43 | 7 |
| `evtforce_inc_4102` | 22.50 | 42.97 | -22.50 | 8 | 25.57 | 47.51 | -22.43 | 7 |
| `evtforce_inc_4103` | 24.12 | 50.62 | -23.88 | 8 | 23.71 | 53.03 | -23.71 | 7 |

The EVT and CONV forecast sets are identical for every seed (True), and so are the alarm sets and exposures in §2. With no adoption the only live difference between the arms is the regional freeze of the TKO entry's m, and in these runs the frozen assimilation ticks fell where CONV was in deadband anyway (e.g. `evt_inc_4101` logs `frozen` at t = 5,100 s with m = 1.181802, `conv_inc_4101` logs `deadband` with the same m), so every snapshot carries the same m and the replays coincide. Pilot 2 therefore shows no forecast improvement from the event engine, exactly as pilot 1 did. The NOI runs have zero halting everywhere (MAE 0, no congestion in either world).

## 5. Mechanics checks, labelled

Labels: **live** = exercised inside a real pilot-2 two-world run; **direct** = measured on the run artefacts or by an extra replay; **unit** = pinned by `tests/test_event.py`.

| # | Check | Label | Verdict | Evidence |
|---|---|---|---|---|
| 1 | Firewall integrity | direct (unit: tests/test_firewall.py) | **PASS** | `results/event_pilot2/evidence/check1_firewall.json`<br>`tests/test_firewall.py` |
| 2 | Deterministic replay | direct | **PASS** | `results/event_pilot2/evidence/check2_deterministic_replay.json` |
| 3 | Identical scoring support | direct (event_log.jsonl) + unit (tests/test_event.py) | **PASS** | `results/event_pilot2/evidence/check3_identical_support.json` |
| 4 | Effective capacity restriction | direct | **PASS** | `results/event_pilot2/evidence/check4_capacity_restriction.json` |
| 5 | Exact regional freeze | direct (assim_log.parquet + twin_state_*.json + state_trace) + unit | **PASS** | `results/event_pilot2/evidence/check5_freeze.json` |
| 6 | Threshold-respecting adoption | unit (rule) + direct (audit of every adopted row on disk) | **PASS** | `results/event_pilot2/evidence/check6_adoption_threshold.json` |
| 7 | Successful state replacement (ktb_n1, 755 m) | live (forced-adoption runs, in-run replacement) + direct (mechanics, this script) | **PASS** | `results/event_pilot2/evidence/check7_755.json` |
| 8 | Clearance rules | live (forced-adoption runs' event/state/replacement logs) + unit | **PASS** | `results/event_pilot2/evidence/check8_clearance.json` |
| 9 | Non-incident rejection | direct (NOI EVT runs) | **PASS** | `results/event_pilot2/evidence/check9_nonincident.json` |
| 10 | Bounded unresolved handling | unit (scheduled exit at entry + 900 s; no DEGRADED spell occurred in any pilot-2 run, so it was not exercised live) | **PASS** | `results/event_pilot2/evidence/check10_degraded.json` |

- **Check 2** (direct): logL of one hypothesis over its own support (no demand family offline): the check is that two independent SUMO processes reproduce it exactly, with the observations substituted from the run's twin_log.parquet (what the Proxy sent)
- **Check 3** (direct (event_log.jsonl) + unit (tests/test_event.py)): every hypothesis of an evaluation reports the same n_O (the intersection support O)
- **Check 5** (direct (assim_log.parquet + twin_state_*.json + state_trace) + unit): while SUSPECTED_EVENT or EVENT_ASSIMILATION the frozen entry's m is held exactly (reason `frozen`); DEGRADED's slow rule is the only frozen-state update and is logged as `degraded_slow`
- **Check 6** (unit (rule) + direct (audit of every adopted row on disk)): natural adoption requires h* in the incident family and gap > ln 10 = 2.302585
- **Check 8** (live (forced-adoption runs' event/state/replacement logs) + unit): two consecutive p_clear > 0.7 -> lift the restriction, replay from S(tau_c - delta), mask the pair, RECOVERY >= 180 s, exit on the unmasked B < 1.5 for 3 min and both ends o < 15%
- **Check 9** (direct (NOI EVT runs)): pilot 2 runs NOI only (part B, 'Runs'); SHK and DET were pilot-1 controls and are not re-run here, so no SHK/DET adoption count is claimed for pilot 2
- **Check 10** (unit (scheduled exit at entry + 900 s; no DEGRADED spell occurred in any pilot-2 run, so it was not exercised live)): DEGRADED leaves at exactly entry + 900 s on the 30-s tick (pilot 2); <= 15 min

Per-check substance:

- **1** no `proxy_*`/truth column in any of the 12 twin logs; `citypulse/twin/event.py` and `service.py` do not import the Proxy; `tests/test_firewall.py` returncode 0.
- **2** `inc_ktb_n1_k2_s1` from `event_snapshot_4350.xml.gz` (t_on 4410.0 -> 5010.0) scored twice in independent processes: logL -71.242849 = -71.242849 over n_O = 165, interval tables and vehicle digests identical = True.
- **3** every evaluation of every EVT run reports one single n_O across its hypotheses (0 violations); support sizes [123, 135, 141, 144, 153, 165, 174, 177].
- **4** `inc_ktb_n1_k2_s1`: lanes ['ktb_n1_0', 'ktb_n1_1'] disallowed in the replay (True); mean q at AID02111 7.35 -> 0.00 (-100.00%), vehicles 322 -> 359.
- **5** frozen ticks across the INC EVT runs: {'evt_inc_4101': 1, 'evt_inc_4102': 0, 'evt_inc_4103': 0, 'evtforce_inc_4101': 1, 'evtforce_inc_4102': 1, 'evtforce_inc_4103': 1}; every frozen tick sits in SUSPECTED_EVENT/EVENT and the entry's m is held exactly (spread {'evt_inc_4101': 0.0, 'evt_inc_4102': 'n/a', 'evt_inc_4103': 'n/a', 'evtforce_inc_4101': 0.0, 'evtforce_inc_4102': 0.0, 'evtforce_inc_4103': 0.0}); `degraded_slow` ticks: {'evt_inc_4101': 0, 'evt_inc_4102': 0, 'evt_inc_4103': 0, 'evtforce_inc_4101': 0, 'evtforce_inc_4102': 0, 'evtforce_inc_4103': 0}.
- **6** 1 natural adoption on disk (in the second episode of forced run `evtforce_inc_4101`, reported in §6), 3 forced (labelled), 0 threshold violations; no adoption in the three primary INC runs.
- **7** live replacement with `inc_ktb_n1_k2_s1` at `ktb_n1` pos 755.0 m: vehicles_match = True (live digest fb87651a3d729078..., 359 vehicles vs replay fb87651a3d729078..., 359); lane disallow read live = `{'ktb_n1_0': ['passenger', 'bus', 'delivery', 'truck', 'trailer'], 'ktb_n1_1': ['passenger', 'bus', 'delivery', 'truck', 'trailer']}`.
- **8** live clearance in the forced runs: `evtforce_inc_4101` spell 5130 -> 6240 (1110 s, recovery_complete), last two p_clear [0.957, 0.984], spell 6570 -> run end (- s, still in RECOVERY), last two p_clear [0.992, 1.0]; `evtforce_inc_4102` spell 5190 -> 5880 (690 s, trigger_alarm), last two p_clear [0.823, 0.825]; `evtforce_inc_4103` spell 5340 -> run end (- s, still in RECOVERY), last two p_clear [0.983, 0.983].
  the rules hold in every spell; the exit conditions were met inside the horizon in 1 of 4 spells (the others were still in RECOVERY at t = 7,200 s, or left it through a new trigger after unmasking, which the spec allows)
- **9** NOI EVT runs: alarms {'evt_noi_4101': 0, 'evt_noi_4102': 0, 'evt_noi_4103': 0}, evaluations {'evt_noi_4101': 0, 'evt_noi_4102': 0, 'evt_noi_4103': 0}, adoptions {'evt_noi_4101': 0, 'evt_noi_4102': 0, 'evt_noi_4103': 0}.
- **10** DEGRADED spells in the pilot-2 runs: {'evt_inc_4101': [], 'evt_inc_4102': [], 'evt_inc_4103': [], 'evtforce_inc_4101': [], 'evtforce_inc_4102': [], 'evtforce_inc_4103': []} - **not exercised live in pilot 2** (no episode reached a third unresolved evaluation, so no run entered DEGRADED); the scheduled exit is pinned by unit tests (`test_degraded_exit_is_scheduled_at_exactly_entry_plus_900_and_needs_no_evaluation`, `test_degraded_tick_is_inert_in_the_pilot1_mode`).

## 6. Forced-adoption integration test (labelled; NOT inference)

Because no natural adoption occurred (§3), the same INC scenario was re-run with `--event-force-hstar inc_ktb_n1_k2_s1.0`: at the **first evaluation of the run** (the first evaluation of its first episode) that hypothesis is treated as h* and the adoption threshold as met. Its own logL/posterior rows are kept unchanged in `event_log.jsonl` and every such row carries `forced: true`; the replacement rows carry `forced: true`. Later episodes of these runs are not forced. These runs exercise the downstream path only.

### `evtforce_inc_4101`

- Alarms [5010, 5040, 5070, 5100, 5130, 6420, 6450]; adoptions: t = 5010 -> `inc_ktb_n1_k2_s1` (forced); t = 6450 -> `inc_ktb_n2_k1_s1` (NATURAL, not injected); state trace: 5010 NORMAL->SUSPECTED_EVENT (trigger_alarm); 5010 SUSPECTED_EVENT->EVENT_ASSIMILATION (adopted_inc_ktb_n1_k2_s1); 5130 EVENT_ASSIMILATION->RECOVERY (cleared_two_consecutive); 6240 RECOVERY->NORMAL (recovery_complete); 6420 NORMAL->SUSPECTED_EVENT (trigger_alarm); 6420 SUSPECTED_EVENT->NORMAL (detector_fault_AID02111_noise); 6450 NORMAL->SUSPECTED_EVENT (trigger_alarm); 6450 SUSPECTED_EVENT->EVENT_ASSIMILATION (adopted_inc_ktb_n2_k1_s1); 6570 EVENT_ASSIMILATION->RECOVERY (cleared_two_consecutive).
- Clearance evaluations: [(5070, 0.9573, 300.0), (5130, 0.9843, 180.0), (6510, 0.9924, 240.0), (6570, 1.0, 240.0)].

### `evtforce_inc_4102`

- Alarms [4890, 4920, 4950, 4980, 5010, 5040, 5070, 5880]; adoptions: t = 4890 -> `inc_ktb_n1_k2_s1` (forced); state trace: 4890 NORMAL->SUSPECTED_EVENT (trigger_alarm); 4890 SUSPECTED_EVENT->EVENT_ASSIMILATION (adopted_inc_ktb_n1_k2_s1); 5190 EVENT_ASSIMILATION->RECOVERY (cleared_two_consecutive); 5880 RECOVERY->SUSPECTED_EVENT (trigger_alarm); 5880 SUSPECTED_EVENT->NORMAL (detector_fault_AID02109_noise).
- Clearance evaluations: [(4950, 0.7747, 180.0), (5010, 0.5622, 60.0), (5070, 0.5849, 120.0), (5130, 0.8234, 180.0), (5190, 0.8255, 240.0)].

### `evtforce_inc_4103`

- Alarms [4860, 4890, 4920, 4950, 4980, 5010, 5100, 5130, 5160, 5190, 5220, 5250, 5280, 5310, 5340]; adoptions: t = 4860 -> `inc_ktb_n1_k2_s1` (forced); state trace: 4860 NORMAL->SUSPECTED_EVENT (trigger_alarm); 4860 SUSPECTED_EVENT->EVENT_ASSIMILATION (adopted_inc_ktb_n1_k2_s1); 5340 EVENT_ASSIMILATION->RECOVERY (cleared_two_consecutive).
- Clearance evaluations: [(4920, 0.3185, 60.0), (4980, 0.3828, 120.0), (5040, 0.2417, 60.0), (5100, 0.3408, 120.0), (5160, 0.2645, 60.0), (5220, 0.3581, 60.0), (5280, 0.9826, 240.0), (5340, 0.9826, 300.0)].

Clearance and recovery detail (from `check8_clearance.json`):

| run | adopted at | clearance evals | last two p_clear | recovery in | recovery out | duration s | exit reason | 60-s ticks B<1.5 | ticks B>=1.5 | ticks both o<15% |
|---|---|---|---|---|---|---|---|---|---|---|
| `evtforce_inc_4101` | 5010 | 4 | [0.957, 0.984] | 5130 | 6240 | 1110 | recovery_complete | 10 | 9 | 2 |
| `evtforce_inc_4101` | 5010 | 4 | [0.992, 1.0] | 6570 | - | - | still in RECOVERY | 8 | 2 | 10 |
| `evtforce_inc_4102` | 4890 | 5 | [0.823, 0.825] | 5190 | 5880 | 690 | trigger_alarm | 4 | 7 | 2 |
| `evtforce_inc_4103` | 4860 | 8 | [0.983, 0.983] | 5340 | - | - | still in RECOVERY | 11 | 17 | 18 |

the rules hold in every spell; the exit conditions were met inside the horizon in 1 of 4 spells (the others were still in RECOVERY at t = 7,200 s, or left it through a new trigger after unmasking, which the spec allows)

### A natural adoption inside a forced run (reported here, not in §3)

- `evtforce_inc_4101`, second episode, t = 6450: MAP `inc_ktb_n2_k1_s1` (incident, {'edge': 'ktb_n2', 'lanes_closed': [0], 'n_lanes': 2, 'pos': 997.5, 'pos_kind': 'mid', 'speed_factor': 1.0}), logL -140.48, posterior 0.9864, gap vs demand 8.456 > ln 10, EVR 0.2106, n_O 153; the replacement row carries `forced: false` and `n_forced_adoptions` is 1, so this adoption was **not** injected.

This is a real natural adoption, but it is **not** one of the three primary INC runs: the run's first episode was force-adopted at 5010, and its live state at 6,450 s comes from the clearance replacement replay, so the episode is not independent of the intervention. It is reported as a labelled observation only, and the §3 statement (no natural adoption in the pilot-2 INC runs) is unaffected.

In-run live replacements (the adoption path itself), from `replacement_log.jsonl` via `check7_755.json`:

| hypothesis | kind | forced | t | live digest | n live | replay digest | n replay | match | restriction live | restriction replay |
|---|---|---|---|---|---|---|---|---|---|---|
| `inc_ktb_n1_k2_s1` | adoption | True | 5010 | fb87651a3d729078... | 359 | fb87651a3d729078... | 359 | True | True | True |
| `inc_ktb_n1_k2_s1` | clearance | False | 5130 | 3d180d7e25b5d5b8... | 390 | 3d180d7e25b5d5b8... | 390 | True | False | False |
| `inc_ktb_n2_k1_s1` | adoption | False | 6450 | 37c68a0b7728648a... | 424 | 37c68a0b7728648a... | 424 | True | True | True |
| `inc_ktb_n2_k1_s1` | clearance | False | 6570 | 5e11ba33e920647c... | 400 | 5e11ba33e920647c... | 400 | True | False | False |

What the forced runs establish: the live replacement path (load S(t_on - 60), restore control state/stream/m, apply the restriction, replay to t) produces a live Twin whose vehicle digest and count equal the replay endpoint's and whose lanes are really disallowed; EVENT_ASSIMILATION then evaluates H_clear(tau_c) every 60 s against the active hypothesis, lifts the restriction, masks the pair and enters RECOVERY; RECOVERY then leaves for NORMAL when its own conditions are met (one of the four spells inside the horizon; the others were still in RECOVERY at 7,200 s or left through a new trigger after unmasking, which the spec allows). What they do **not** establish: that the incident hypothesis was inferred - it was injected.

## 7. Files written

- `results/event_pilot2/runs/` - 9 pilot-2 two-world runs (`evt_inc_410{1,2,3}`, `conv_inc_410{1,2,3}`, `evt_noi_410{1,2,3}`) and 3 forced-adoption runs (`evtforce_inc_410{1,2,3}`), each with `twin/`, `proxy/`, `run_info.json`, `queue_forecasts.json`.
- `results/event_pilot2/evidence/` - `check1_firewall.json`, `check2_deterministic_replay.json`, `check3_identical_support.json`, `check4_capacity_restriction.json`, `check5_freeze.json`, `check6_adoption_threshold.json`, `check7_755.json`, `check8_clearance.json`, `check9_nonincident.json`, `check10_degraded.json`, `adoption_summary.json`.
- `results/event_pilot2/runs_summary.json`, `results/event_pilot2/report.md`.
- `results/event_pilot2/impl/` - `run_pilot2.py`, `check_replays.py`, `make_evidence.py`, `make_report.py`, `summarize.py` (drivers; new outputs only).
- Edited: `citypulse/twin/event.py`, `citypulse/twin/service.py`, `citypulse/experiments/event_pilot.py`, `tests/test_event.py`. `citypulse/branching/engine.py` untouched; `citypulse/proxy/*`, `citypulse/experiments/run_two_worlds.py`, `citypulse/branching/audit_engine.py`, `citypulse/experiments/decision_audit.py` and `results/audit/` untouched.

REPORT DONE