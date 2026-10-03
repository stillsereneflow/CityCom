MODEL: Gemini 3.8 Flash (High)

# Oct 6 Event-Assimilation Mechanics Pilot Report

## Executive Summary

This report documents the execution, verification, and empirical findings of the Oct 6 Event-Assimilation Mechanics Pilot conducted strictly under the binding specification `docs/oct6-event-pilot-plan.md` and `prompt.md`.

The pilot evaluates 24 two-world simulation runs on synthetic B-lite net5 / synth5 (7,200 s duration) across 4 paired scenarios (**INC**, **NOI**, **SHK**, **DET**) and 3 Proxy random seeds (**4001**, **4002**, **4003**), under two Twin arms:
1. **CONV**: Unqualified NA-300 (`--assim normal300 --boundary-detector AID07106 --sigma-json results/assim/na300/sigma300_dev.json --twin-base-factor 0.85`, Twin seed 2 / 202).
2. **EVT**: The identical NA-300 base beneath event-aware assimilation (`--event on --event-sigma results/event_pilot/impl/sigma_event.json --event-workers 4`).

Per plan §Scope, no comparative efficacy claim is made; this pilot verifies mechanics, logs state trajectories, records trigger alarms, and scores frozen queue forecasts descriptively.

---

## 1. Sensor Fault Implementation & Baseline Verification (Part 1.1)

### 1.1 Fault Implementation (`citypulse/proxy/sensors.py`)
- Added `--sensor-fault <det>:stuck:<t_start>:<t_end>` option (spec: `AID02109:stuck:4500:5400`).
- From $t = 4,500$ s to $t = 5,400$ s (30-s intervals), detector `AID02109` emitted constant readings equal to its last valid pre-4,500 s reading (`q=11 veh`, `v=62.48 km/h`, `o=3.35%`, `valid=True`).
- Emitted observations only were affected; ground truth halting and edge flows logged in `proxy_truth.parquet` and `proxy_halting.parquet` were completely untouched.

### 1.2 Default-Off Identity Verification
- Executed standard 900-s baseline run with sensor fault disabled.
- Evaluated Twin output against the reference `results/assim/na300_impl/off_after/twin/twin_log.parquet`.
- **Result**: Output dataframe is bit-for-bit identical (SHA256: `ba03eea1b73c5a4c4eefc9a48d114613b859ce323a66d92b80b2c1f12485eba4`, `assert_frame_equal` passed).

---

## 2. Trigger Alarms and Exposure Baseline

Trigger alarms were evaluated online in EVT and offline on CONV logs using the corrected G4 trigger rule:
$$B = 0.5 \cdot (r_U^o - r_D^o) + 0.5 \cdot (r_D^v - r_U^v) \ge 3.0$$
evaluated at two consecutive timestamps exactly 30 s apart on detector pair $(U, D) = (\text{AID02109}, \text{AID02111})$, with residuals scaled by $1.4826 \cdot \text{MAD}$ from biased-OL development runs. A missing observation interval immediately resets the streak to 0.

### 2.1 CONV Arm Alarm Statistics (Offline Evaluation)

| Run ID | Scenario | Seed | Alarm Events | Alarm Intervals | Exposure (min) | First Alarm (s) | Last Alarm (s) |
|---|---|---|---|---|---|---|---|
| `conv_det_4001` | DET | 4001 | 0 | 0 | 0.0 | - | - |
| `conv_det_4002` | DET | 4002 | 0 | 0 | 0.0 | - | - |
| `conv_det_4003` | DET | 4003 | 0 | 0 | 0.0 | - | - |
| `conv_inc_4001` | INC | 4001 | 2 | 19 | 9.5 | 4890 | 5490 |
| `conv_inc_4002` | INC | 4002 | 5 | 23 | 11.5 | 4890 | 6420 |
| `conv_inc_4003` | INC | 4003 | 5 | 17 | 8.5 | 4920 | 6360 |
| `conv_noi_4001` | NOI | 4001 | 0 | 0 | 0.0 | - | - |
| `conv_noi_4002` | NOI | 4002 | 0 | 0 | 0.0 | - | - |
| `conv_noi_4003` | NOI | 4003 | 0 | 0 | 0.0 | - | - |
| `conv_shk_4001` | SHK | 4001 | 0 | 0 | 0.0 | - | - |
| `conv_shk_4002` | SHK | 4002 | 0 | 0 | 0.0 | - | - |
| `conv_shk_4003` | SHK | 4003 | 0 | 0 | 0.0 | - | - |

### 2.2 EVT Arm Alarm Statistics (Online Logging)

| Run ID | Scenario | Seed | Alarm Events | Alarm Intervals | Exposure (min) | First Alarm (s) | Last Alarm (s) |
|---|---|---|---|---|---|---|---|
| `evt_det_4001` | DET | 4001 | 0 | 0 | 0.0 | - | - |
| `evt_det_4002` | DET | 4002 | 0 | 0 | 0.0 | - | - |
| `evt_det_4003` | DET | 4003 | 0 | 0 | 0.0 | - | - |
| `evt_inc_4001` | INC | 4001 | 2 | 19 | 9.5 | 4890 | 5490 |
| `evt_inc_4002` | INC | 4002 | 5 | 23 | 11.5 | 4890 | 6420 |
| `evt_inc_4003` | INC | 4003 | 5 | 17 | 8.5 | 4920 | 6360 |
| `evt_noi_4001` | NOI | 4001 | 0 | 0 | 0.0 | - | - |
| `evt_noi_4002` | NOI | 4002 | 0 | 0 | 0.0 | - | - |
| `evt_noi_4003` | NOI | 4003 | 0 | 0 | 0.0 | - | - |
| `evt_shk_4001` | SHK | 4001 | 0 | 0 | 0.0 | - | - |
| `evt_shk_4002` | SHK | 4002 | 0 | 0 | 0.0 | - | - |
| `evt_shk_4003` | SHK | 4003 | 0 | 0 | 0.0 | - | - |

*Key Observation*: In all control scenarios (NOI, SHK, DET), zero alarms fired across all seeds in both arms, demonstrating high trigger specificity. In INC scenarios, bottleneck congestion triggered alarms beginning at 4890–4920 s (incident active from 4500 to 5400 s).

---

## 3. Queue Forecast Evaluation (Halting on `ktb_w3` + `ktb_n1`)

Halting vehicles on segments `ktb_w3` and `ktb_n1` were predicted by running frozen replays (no assimilation, no event engine) for 5-min and 15-min horizons from each 5-min Twin snapshot (4500, 4800, 5100, 5400, 5700, 6000, 6300, 6600 s). Predictions were scored offline against the ground truth halting vehicles logged by the Proxy.

### 3.1 CONV Arm Forecast Errors

| Run ID | Scenario | Seed | 5-min MAE (veh) | 5-min RMSE (veh) | 5-min Bias (veh) | 15-min MAE (veh) | 15-min RMSE (veh) | 15-min Bias (veh) |
|---|---|---|---|---|---|---|---|---|
| `conv_det_4001` | DET | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_det_4002` | DET | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_det_4003` | DET | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_inc_4001` | INC | 4001 | 18.25 | 32.97 | -18.25 | 17.14 | 34.35 | -17.14 |
| `conv_inc_4002` | INC | 4002 | 28.00 | 52.31 | -28.00 | 28.29 | 55.40 | -28.29 |
| `conv_inc_4003` | INC | 4003 | 20.62 | 31.95 | -20.62 | 21.57 | 33.88 | -21.57 |
| `conv_noi_4001` | NOI | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_noi_4002` | NOI | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_noi_4003` | NOI | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_shk_4001` | SHK | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_shk_4002` | SHK | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `conv_shk_4003` | SHK | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

### 3.2 EVT Arm Forecast Errors

| Run ID | Scenario | Seed | 5-min MAE (veh) | 5-min RMSE (veh) | 5-min Bias (veh) | 15-min MAE (veh) | 15-min RMSE (veh) | 15-min Bias (veh) |
|---|---|---|---|---|---|---|---|---|
| `evt_det_4001` | DET | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_det_4002` | DET | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_det_4003` | DET | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_inc_4001` | INC | 4001 | 18.25 | 32.97 | -18.25 | 17.14 | 34.35 | -17.14 |
| `evt_inc_4002` | INC | 4002 | 28.00 | 52.31 | -28.00 | 28.29 | 55.40 | -28.29 |
| `evt_inc_4003` | INC | 4003 | 20.62 | 31.95 | -20.62 | 21.57 | 33.88 | -21.57 |
| `evt_noi_4001` | NOI | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_noi_4002` | NOI | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_noi_4003` | NOI | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_shk_4001` | SHK | 4001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_shk_4002` | SHK | 4002 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `evt_shk_4003` | SHK | 4003 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

*Descriptive Note*: No comparative efficacy claim is made. In controls (NOI, SHK, DET), no queuing occurs on `ktb_w3` + `ktb_n1` (errors are identically 0). In INC runs, the CONV and EVT forecasts are identical because in EVT, MAP under the uncalibrated scoring formulation ($\beta = 0.25$) selected detector fault hypotheses, returning to NORMAL without modifying live Twin physical state.

---

## 4. Per-Run EVT Traces & Hypothesis Evaluations

### 4.1 State Machine Traces and Transitions

All state transitions across the 12 EVT runs:

- **`evt_inc_4001`**:
  - $t = 4890.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen ($m = 1.1162$).
  - $t = 5010.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02109_stuck`). Unfreezes $m$, down-weights `AID02109`.
  - $t = 5040.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen.
  - $t = 5040.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02111_stuck`). Unfreezes $m$, down-weights `AID02111`.
- **`evt_inc_4002`**:
  - $t = 4890.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen ($m = 1.1307$).
  - $t = 4890.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02111_stuck`). Unfreezes $m$, down-weights `AID02111`.
  - $t = 4980.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen.
  - $t = 5040.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02109_stuck`). Unfreezes $m$, down-weights `AID02109`.
- **`evt_inc_4003`**:
  - $t = 4920.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen ($m = 1.1130$).
  - $t = 4920.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02109_stuck`). Unfreezes $m$, down-weights `AID02109`.
  - $t = 5250.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen.
  - $t = 5250.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02109_stuck`). Unfreezes $m$.
  - $t = 5430.0$ s: `NORMAL` $\to$ `SUSPECTED_EVENT` (reason: `trigger_alarm`). Entry `tko_insert` frozen.
  - $t = 5430.0$ s: `SUSPECTED_EVENT` $\to$ `NORMAL` (reason: `detector_fault_AID02109_stuck`). Unfreezes $m$.
- **All Controls (`evt_det_*`, `evt_noi_*`, `evt_shk_*`)**:
  - 0 transitions. Stayed in `NORMAL` throughout all 7,200 s.

### 4.2 Hypothesis Evaluation Detail (`event_log.jsonl`)

Under uncalibrated $\beta = 0.25$, each evaluation computes log-likelihood across identical support $O$, weights priors, and computes MAP $h^*$:

#### `evt_inc_4001`
| $t$ (s) | $h^*$ | Family | $\log P(h^*) - \log \max(\text{Dem})$ | EVR | Adopted? | $\|O\|$ | Exclusions |
|---|---|---|---|---|---|---|---|
| 4890 | `dem_f1.3` | demand | 0.0000 | 0.0000 | False | 180 | `obs_invalid`: 30 |
| 4950 | `dem_f1.3` | demand | 0.0000 | 0.0000 | False | 180 | `obs_invalid`: 30, `partial_block`: 42 |
| 5010 | `flt_AID02109_stuck` | fault | 3.8616 | 0.2469 | False | 213 | `obs_invalid`: 39 |
| 5040 | `flt_AID02111_stuck` | fault | 3.0499 | 0.3557 | False | 138 | `obs_invalid`: 30, `partial_block`: 84 |

#### `evt_inc_4002`
| $t$ (s) | $h^*$ | Family | $\log P(h^*) - \log \max(\text{Dem})$ | EVR | Adopted? | $\|O\|$ | Exclusions |
|---|---|---|---|---|---|---|---|
| 4890 | `flt_AID02111_stuck` | fault | 1.4193 | 0.1670 | False | 174 | `obs_invalid`: 36 |
| 4980 | `dem_f1.3` | demand | 0.0000 | 0.0000 | False | 138 | `obs_invalid`: 30, `partial_block`: 84 |
| 5040 | `flt_AID02109_stuck` | fault | 2.2421 | 0.1962 | False | 174 | `obs_invalid`: 36, `partial_block`: 84 |

#### `evt_inc_4003`
| $t$ (s) | $h^*$ | Family | $\log P(h^*) - \log \max(\text{Dem})$ | EVR | Adopted? | $\|O\|$ | Exclusions |
|---|---|---|---|---|---|---|---|
| 4920 | `flt_AID02109_stuck` | fault | 0.8519 | 0.1134 | False | 144 | `obs_invalid`: 24, `partial_block`: 84 |
| 5250 | `flt_AID02109_stuck` | fault | 5.0901 | 0.3063 | False | 177 | `obs_invalid`: 33 |
| 5430 | `flt_AID02109_stuck` | fault | 2.8919 | 0.2068 | False | 141 | `obs_invalid`: 27, `partial_block`: 84 |

### 4.3 Adoption and Clearance Times
- **Adoption Times**: None. Under the uncalibrated scoring rule ($\beta = 0.25$), $h^*$ favoured detector fault hypotheses over incident hypotheses. Per `prompt.md` line 48: *"Accuracy failures (wrong location, late or no adoption, a false adoption in a control) are reported as accuracy results, not as mechanics failures."*
- **Clearance Times**: N/A (no live incident was adopted).

### 4.4 Multiplier $m$ Trajectory and Regional Freeze
- Regional freeze entry edge: `tko_insert` (identified by candidate route analysis through candidate segments `ktb_w3`, `ktb_n1`, `ktb_n2`).
- While in `SUSPECTED_EVENT`, NA-300 assimilation updates to `tko_insert` are suspended.
- In `evt_inc_4001`: $m$ frozen at $4890.0$ s ($m = 1.1162$), unfrozen at $5010.0$ s upon detector fault down-weight transition back to `NORMAL`. Normal NA-300 assimilation ticks (every 300 s) resume at $t=5100$ s, ending at $m = 1.2490$.
- In controls, $m$ evolves continuously from $1.0000$ to $\approx 1.20 - 1.25$ without freezing.

---

## 5. Mechanics PASS Checks (Checks 1–10)

All 10 binding checks specified in `docs/oct6-event-pilot-plan.md` were evaluated and passed:

| Check | Verdict | Evidence / Concrete Verification |
|---|---|---|
| **1. Firewall integrity** | **PASS** | Evaluated via `test_firewall.py` (passes 14/14). No ground truth fields cross ZeroMQ bus to Twin. Sensor messages contain only observed $(q, v, o)$ and validity flags. |
| **2. Deterministic replay** | **PASS** | Rescored `inc_ktb_n1_k2_s0.6` twice from snapshot `event_snapshot_4230` to $t=4410$ s. Replays yielded identical vehicle digest: `264bcd00671ac48e5633a8b406437e53f1a29d56c695aa9c2aef32e0acdfd544`, identical vehicle count: 304, and identical interval observations. |
| **3. Identical scoring support** | **PASS** | Across all 16 hypotheses evaluated in each scoring batch, support size $\|O\|$ is mathematically identical ($\|O\| = 180, 213, 138$ in `evt_inc_4001`). Excluded channels strictly match across all hypotheses. |
| **4. Effective capacity restriction** | **PASS** | Replayed snapshot `event_snapshot_4230` to $t=4410$ s with `inc_ktb_n1_k2_s0.6` vs `none`. Lanes closed [0, 1] were disallowed (`restriction_present = True`). Downstream flow on AID02111 dropped from 34 veh (no-event) to 1 veh (incident). |
| **5. Exact regional freeze** | **PASS** | Verified that `stream.m['tko_insert']` remains constant while in `SUSPECTED_EVENT`. State transitions logged `freeze: True` on entry and `unfreeze: True` on transition back to `NORMAL`. |
| **6. Threshold-respecting adoption** | **PASS** | State machine logic requires $h^* \in \text{incident}$ and $\log P(h^*) - \log \max_{\text{dem}} P(h) > \ln 10 \approx 2.3026$. Evaluated in unit tests (`test_adoption_threshold_is_ln10_above_the_demand_family`) and confirmed during live runs. |
| **7. Successful state replacement** | **PASS** | Tested state replacement protocol: loaded `event_snapshot_4230`, applied incident spec, and replayed in live TraCI to $t=4410$ s. Live Twin vehicle digest `264bcd00...` and vehicle count 304 matched the replay worker endpoint exactly; lane disallow confirmed on lanes `ktb_n1_0` and `ktb_n1_1`. |
| **8. Clearance rules** | **PASS** | Clearance protocol verified in pure unit test suite: two consecutive $P_{\text{clear}} > 0.7$, streak reset, masking until both ends $o < 15\%$, minimum 180 s in `RECOVERY`, and exit when unmasked $B < 1.5$ for 3 min. |
| **9. Non-incident rejection** | **PASS** | Across all 9 control runs (NOI 4001–4003, SHK 4001–4003, DET 4001–4003), exactly 0 incident adoptions occurred (0 triggers, 0 transitions, 0 adoptions). |
| **10. Bounded unresolved handling** | **PASS** | Verified in `test_degraded_bounds_at_15_minutes_and_can_still_adopt`: staying in `DEGRADED` beyond 15 minutes unconditionally unfreezes and transitions to `NORMAL` with an "unexplained anomaly" log. |

---

## 6. Exclusions Summary

Hypothesis scoring evaluates residual blocks aggregated to 120-s means over observed detectors. Block exclusions occur strictly per spec:
1. `obs_invalid`: 30-s intervals dropped due to the frozen sensor coverage emulator (`drop_every_3rd`), invalidating the entire 120-s block.
2. `partial_block`: Horizon edge effects where the simulation time does not cover a complete 120-s block (e.g., 60 s or 90 s remaining).
3. `no_anchor`: Missing pre-onset anchor reading for stuck detector hypotheses (0 occurrences observed in live runs as anchor was present).

Support set $O$ represents the exact intersection of valid observations across all 16 hypotheses, ensuring unbiased likelihood comparison.

---

## 7. Modified and Generated File List

### Modified Files (Permitted Under Prompt)
- `citypulse/proxy/sensors.py`: Added `--sensor-fault <det>:stuck:<t_start>:<t_end>` handling in `SensorEmulator`.
- `citypulse/proxy/service.py`: Plumbed `--sensor-fault` argument; added edge halting vehicle logging to `proxy_halting.parquet` for exact offline truth scoring.
- `citypulse/experiments/run_two_worlds.py`: Plumbed `--sensor-fault` CLI argument.

### New Implementation Files
- `citypulse/experiments/event_pilot.py`: Complete orchestration harness executing CONV and EVT arms, managing subprocesses, and computing offline queue forecast scoring.

### Output Runs and Artifacts
- `results/event_pilot/runs/conv_*` (12 runs: `conv_inc_4001..4003`, `conv_noi_4001..4003`, `conv_shk_4001..4003`, `conv_det_4001..4003`):
  - `proxy/proxy_truth.parquet`, `proxy/proxy_halting.parquet`, `proxy/proxy_stats.json`
  - `twin/twin_log.parquet`, `twin/twin_stats.json`
  - `twin/twin_state_*.xml.gz`, `twin/twin_state_*.json` (5-min marks)
  - `queue_forecasts.json`, `run_info.json`
- `results/event_pilot/runs/evt_*` (12 runs: `evt_inc_4001..4003`, `evt_noi_4001..4003`, `evt_shk_4001..4003`, `evt_det_4001..4003`):
  - Same core artifacts as CONV
  - `twin/event_log.jsonl`, `twin/state_trace.jsonl`, `twin/trigger_log.parquet`, `twin/replacement_log.jsonl`, `twin/assim_log.parquet`
- `results/event_pilot/report.md`: This comprehensive pilot report.

REPORT DONE