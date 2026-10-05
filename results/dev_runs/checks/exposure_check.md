# Realised SHK/DET exposure check (read-only)

Script: `results/dev_runs/checks/exposure_check.py`; machine-readable result: `results/dev_runs/checks/exposure_check.json`. Windows: scenario [4500, 5400), trigger [4500, 5700], baseline [3600, 4500).

Trigger under test (`citypulse/twin/event.py`, `citypulse/twin/service.py`): B = 0.5*(r_U^o - r_D^o) + 0.5*(r_D^v - r_U^v) on (U, D) = (AID02109, AID02111), r = (obs - twin)/sigma with sigma from `results/event_pilot/impl/sigma_event.json`; B >= 3 at two ticks exactly 30 s apart; a missing interval resets the streak.

## 1. SHK

`proxy_truth.q` is the count of vehicles in the previous completed 30 s interval (`citypulse/sim.py:read_detectors`), so a row at tick t covers [t-30, t); the [4500, 5400) sum therefore covers [4470, 5400). `rou.xml vehicle@depart` is the *scheduled* departure from the file named in `run_info.json["routes"]`.

| seed | routes file (run_info) | sched. UPPER dep SHK/NOI | Δ% | realised q AID07105 SHK/NOI | Δ% | realised q AID02105 SHK/NOI | Δ% | ktb_n1 halt max | B max | #B≥3 | longest B-streak | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4401 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 733/696 | +5.3 | 556/527 | +5.5 | 0 | 2.97 | 0 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4402 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 739/701 | +5.4 | 553/520 | +6.3 | 0 | 3.16 | 2 | 1 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4403 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 749/702 | +6.7 | 563/526 | +7.0 | 0 | 3.27 | 2 | 1 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4404 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 741/705 | +5.1 | 557/532 | +4.7 | 0 | 3.25 | 1 | 1 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4405 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 742/701 | +5.8 | 564/525 | +7.4 | 0 | 2.63 | 0 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4406 | `proxy_shock.rou.xml` | 724/561 | +29.1 | 750/695 | +7.9 | 560/525 | +6.7 | 0 | 2.95 | 0 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |

Where the un-served window demand goes (`proxy_truth.parquet` q sums at the entry detector AID07105; the scheduled full-run totals are from the two route files). The two route files are seed-independent, so the scheduled columns repeat across seeds; the seed enters through SUMO's insertion/route randomness:

| seed | q AID07105 [4500,5400) SHK/NOI | q AID07105 [5400,7200) SHK/NOI | q AID07105 full run SHK/NOI | sched. UPPER full run SHK/NOI |
|---|---|---|---|---|
| 4401 | 733/696 | 1512/1453 | 5696/5605 | 4330/4254 |
| 4402 | 739/701 | 1501/1451 | 5692/5602 | 4330/4254 |
| 4403 | 749/702 | 1493/1446 | 5694/5602 | 4330/4254 |
| 4404 | 741/705 | 1495/1438 | 5688/5594 | 4330/4254 |
| 4405 | 742/701 | 1502/1454 | 5696/5605 | 4330/4254 |
| 4406 | 750/695 | 1491/1457 | 5697/5607 | 4330/4254 |

Scheduled departures in the window by route class (SHK file / NOI file, Δ%):

| seed | UPPER ktb | LOWER ktr | stubs x* | ALL |
|---|---|---|---|---|
| 4401 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |
| 4402 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |
| 4403 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |
| 4404 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |
| 4405 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |
| 4406 | 724/561 (+29.1%) | 201/168 (+19.6%) | 418/423 (-1.2%) | 1343/1152 (+16.6%) |

Corridor state, SHK vs NOI (`proxy_halting.parquet`, `proxy_truth.parquet`), mean/max over [4500, 5700]:

| seed | ktb_w3 halt SHK/NOI | ktb_n1 halt SHK/NOI | o AID02109 SHK/NOI | o AID02111 SHK/NOI |
|---|---|---|---|---|
| 4401 | 0/0 | 0.00 max 0/0.00 max 0 | 6.00/6.03 | 2.34/2.01 |
| 4402 | 0/0 | 0.00 max 0/0.00 max 0 | 6.41/5.83 | 2.33/2.26 |
| 4403 | 0/0 | 0.00 max 0/0.00 max 0 | 6.49/5.90 | 2.24/2.09 |
| 4404 | 0/0 | 0.00 max 0/0.00 max 0 | 6.10/5.74 | 2.07/2.16 |
| 4405 | 0/0 | 0.00 max 0/0.00 max 0 | 6.39/6.14 | 2.12/2.26 |
| 4406 | 0/0 | 0.00 max 0/0.00 max 0 | 6.19/5.83 | 1.81/2.03 |

## 2. DET

| seed | `sensor_fault` (run_info) | last valid pre-4500 (q,v,o) | window const/valid/equals | t=4500 already frozen | NOI o std (n unique) | B max | #B≥3 | verdict |
|---|---|---|---|---|---|---|---|---|
| 4401 | `AID02109:stuck:4500:5400` | 16, 73.251, 6.453 @ t=4470 | True/True/True | True | 2.920 (28) | 2.47 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4402 | `AID02109:stuck:4500:5400` | 20, 69.392, 2.087 @ t=4470 | True/True/True | True | 1.875 (30) | 2.31 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4403 | `AID02109:stuck:4500:5400` | 13, 73.587, 3.907 @ t=4470 | True/True/True | True | 2.177 (29) | 2.61 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4404 | `AID02109:stuck:4500:5400` | 20, 67.596, 6.702 @ t=4470 | True/True/True | True | 2.065 (30) | 2.28 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4405 | `AID02109:stuck:4500:5400` | 17, 74.898, 2.921 @ t=4470 | True/True/True | True | 2.542 (28) | 2.11 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |
| 4406 | `AID02109:stuck:4500:5400` | 20, 68.698, 6.334 @ t=4470 | True/True/True | True | 2.885 (28) | 2.82 | 0 | injected, no bottleneck signature (trigger limitation at this magnitude) |

`--sensor-fault AID02109:stuck:4500:5400` is inclusive at both ends, so the frozen span is the 31 ticks 4500..5400; the constancy check above uses (4500, 5400] (30 ticks) and the `t=4500` column shows that the tick at 4500 already carries the frozen value. The paired NOI run of the same seed is the control (obs_o std 1.9-2.9 over 28-30 distinct values).

Recomputed residual terms (mean over [4500, 5700], from `twin_log.parquet` + `sigma_event.json`; `trigger_log.parquet` does not log them). Validation: Recomputed B equals trigger_log.parquet B at every tick of the 18 SHK/DET/NOI EVT runs (downweight empty), so the residual decomposition above is exact for them. The INC runs are excluded: they set event.downweight = 5.0 on both pair detectors once the fault hypothesis is adopted, which shrinks the logged B by 5x.

| seed | scenario | r_U^o | r_D^o | r_U^v | r_D^v | occ term | speed term | B recon | max abs r_U^o |
|---|---|---|---|---|---|---|---|---|---|
| 4401 | DET | +0.529 | -0.077 | +0.210 | -0.015 | +0.303 | -0.112 | +0.191 | 1.569 |
| 4402 | DET | -0.662 | +0.029 | -0.195 | -0.121 | -0.345 | +0.037 | -0.308 | 2.140 |
| 4403 | DET | -0.195 | -0.117 | +0.254 | +0.025 | -0.039 | -0.114 | -0.153 | 3.293 |
| 4404 | DET | +0.584 | +0.161 | -0.512 | -0.098 | +0.211 | +0.207 | +0.418 | 2.007 |
| 4405 | DET | -0.356 | -0.109 | +0.285 | -0.003 | -0.124 | -0.144 | -0.268 | 1.978 |
| 4406 | DET | +0.405 | -0.004 | -0.347 | +0.083 | +0.204 | +0.215 | +0.419 | 2.366 |
| 4401 | SHK | +0.450 | +0.166 | -0.498 | -0.089 | +0.142 | +0.204 | +0.347 | 2.990 |
| 4402 | SHK | +0.367 | +0.125 | -0.336 | -0.008 | +0.121 | +0.164 | +0.285 | 2.237 |
| 4403 | SHK | +0.546 | +0.094 | -0.420 | -0.045 | +0.226 | +0.188 | +0.413 | 2.415 |
| 4404 | SHK | +0.656 | +0.044 | -0.663 | -0.311 | +0.306 | +0.176 | +0.482 | 3.093 |
| 4405 | SHK | +0.506 | +0.183 | -0.395 | -0.249 | +0.162 | +0.073 | +0.235 | 2.306 |
| 4406 | SHK | +0.329 | -0.191 | -0.524 | +0.229 | +0.260 | +0.376 | +0.636 | 1.925 |
| 4401 | NOI | +0.412 | +0.107 | -0.373 | +0.056 | +0.152 | +0.214 | +0.366 | 3.373 |
| 4402 | NOI | +0.319 | +0.333 | -0.462 | -0.163 | -0.007 | +0.149 | +0.142 | 2.254 |
| 4403 | NOI | +0.314 | +0.090 | -0.173 | -0.065 | +0.112 | +0.054 | +0.166 | 2.107 |
| 4404 | NOI | +0.487 | +0.024 | -0.508 | -0.270 | +0.232 | +0.119 | +0.350 | 2.194 |
| 4405 | NOI | +0.436 | +0.150 | -0.459 | -0.212 | +0.143 | +0.124 | +0.267 | 2.763 |
| 4406 | NOI | +0.250 | -0.059 | -0.358 | +0.161 | +0.155 | +0.260 | +0.415 | 2.646 |

## 3. Trigger internals over [4500, 5700] (`trigger_log.parquet`) and the INC comparison

| run | B max (t) | #B≥3 | B≥3 timestamps | longest streak | signature | missing intervals | resets (reason) | alarms |
|---|---|---|---|---|---|---|---|---|
| SHK EVT 4401 | 2.97 (4620) | 0 | - | 0 | False | 4 | - | 0 |
| SHK EVT 4402 | 3.16 (5460) | 2 | 4800,5460 | 1 | False | 5 | 4830:missing_interval:obs_invalid; 5490:B_below_threshold | 0 |
| SHK EVT 4403 | 3.27 (4770) | 2 | 4770,5610 | 1 | False | 3 | 4800:B_below_threshold; 5640:B_below_threshold | 0 |
| SHK EVT 4404 | 3.25 (5580) | 1 | 5580 | 1 | False | 6 | 5610:B_below_threshold | 0 |
| SHK EVT 4405 | 2.63 (4770) | 0 | - | 0 | False | 4 | - | 0 |
| SHK EVT 4406 | 2.95 (4860) | 0 | - | 0 | False | 5 | - | 0 |
| DET EVT 4401 | 2.47 (5520) | 0 | - | 0 | False | 3 | - | 0 |
| DET EVT 4402 | 2.31 (5580) | 0 | - | 0 | False | 2 | - | 0 |
| DET EVT 4403 | 2.61 (4770) | 0 | - | 0 | False | 2 | - | 0 |
| DET EVT 4404 | 2.28 (5490) | 0 | - | 0 | False | 2 | - | 0 |
| DET EVT 4405 | 2.11 (5580) | 0 | - | 0 | False | 5 | - | 0 |
| DET EVT 4406 | 2.82 (4980) | 0 | - | 0 | False | 2 | - | 0 |
| NOI EVT 4401 | 4.08 (5100) | 1 | 5100 | 1 | False | 5 | 5130:B_below_threshold | 0 |
| NOI EVT 4402 | 2.80 (4950) | 0 | - | 0 | False | 2 | - | 0 |
| NOI EVT 4403 | 2.71 (4770) | 0 | - | 0 | False | 4 | - | 0 |
| NOI EVT 4404 | 2.40 (5700) | 0 | - | 0 | False | 6 | - | 0 |
| NOI EVT 4405 | 3.94 (5340) | 1 | 5340 | 1 | False | 3 | 5370:B_below_threshold | 0 |
| NOI EVT 4406 | 2.56 (4860) | 0 | - | 0 | False | 5 | - | 0 |
| INC EVT 4401 | 7.10 (5010) | 7 | 4620,4860,4890,4920,4950,4980,5010 | 6 | True | 3 | 4650:B_below_threshold; 5040:missing_interval:obs_invalid | 5 |
| INC EVT 4402 | 6.68 (5010) | 5 | 4860,4950,4980,5010,5070 | 3 | True | 2 | 4890:B_below_threshold; 5040:missing_interval:obs_invalid; 5100:B_below_threshold | 2 |
| INC EVT 4403 | 6.79 (5010) | 8 | 4800,4860,4890,4920,4950,4980,5010,5070 | 6 | True | 1 | 4830:B_below_threshold; 5040:missing_interval:obs_invalid; 5100:B_below_threshold | 5 |
| INC EVT 4404 | 9.48 (5040) | 9 | 4860,4890,4920,4980,5010,5040,5220,5250,5370 | 3 | True | 4 | 4950:missing_interval:obs_invalid; 5070:B_below_threshold; 5280:B_below_threshold; 5400:B_below_threshold | 5 |
| INC EVT 4405 | 11.16 (5010) | 9 | 4770,4890,4920,4950,4980,5010,5040,5070,5400 | 7 | True | 1 | 4800:B_below_threshold; 5100:B_below_threshold; 5430:B_below_threshold | 6 |
| INC EVT 4406 | 16.28 (5160) | 11 | 4860,4890,4950,4980,5010,5040,5070,5100,5160,5280,5430 | 6 | True | 3 | 4920:B_below_threshold; 5130:missing_interval:obs_invalid; 5190:B_below_threshold; 5310:B_below_threshold; 5460:B_below_threshold | 6 |

Missing intervals are `B = NaN` in `trigger_log.parquet`; the reason column is not logged, so it is re-derived from `twin_log.parquet` with the precedence of `event.bottleneck_index` (`obs_invalid` when `obs_valid` is false, `obs_null` when `obs_q`/`obs_o` is null, `twin_null` when `twin_q` is null, `reading_missing` when the detector row is absent). `signature` is True only when B >= 3 at two consecutive 30 s ticks, i.e. the trigger's own firing condition.

## 4. Conclusions

**SHK: injected, no bottleneck signature (trigger limitation at this magnitude)**

- The +30 % demand shock is present in the route file the Proxy loaded (scheduled UPPER departures +29.1 % in [4500, 5400)), but the realised flow past the corridor entry (AID07105 on tko_in) and the upper branch (AID02105 on ktb_w1) rises only ~+5-7 %: the shared entry is already at capacity in the paired NOI control (2784-2820 veh/h vs 2932-3000 veh/h under the shock, i.e. ~+5 %), so the extra vehicles queue and are released over the following ~30 min (the SHK-NOI gap at AID07105 stays positive to 7200 and the full-run totals converge on the scheduled totals: +91 realised vs +74 scheduled). No halting appears on ktb_n1/ktb_w3 (max 0 in all 6 seeds, against 74-143 in the INC runs) and B never reaches 3 at two consecutive ticks, so the trigger was never exposed to a +30 % shock at the detectors. In 3 of 6 seeds there are isolated single-tick B >= 3 excursions (max 3.27); the NOI control has the same kind of excursion (up to 4.08 in seed 4401) and the trigger requires two consecutive ticks, so these are not a bottleneck signature.
- `routes_file`: proxy_shock.rou.xml in all 6 EVT and 6 CONV run_info.json
- `scheduled_UPPER_delta_pct`: [29.06, 29.06, 29.06, 29.06, 29.06, 29.06]
- `realised_AID02105_delta_pct`: [5.5, 6.35, 7.03, 4.7, 7.43, 6.67]
- `realised_AID07105_delta_pct`: [5.32, 5.42, 6.7, 5.11, 5.85, 7.91]
- `realised_entry_flow_vph`: [2932.0, 2956.0, 2996.0, 2964.0, 2968.0, 3000.0]
- `noi_entry_flow_vph`: [2784.0, 2804.0, 2808.0, 2820.0, 2804.0, 2780.0]
- `realised_over_scheduled_ratio`: [0.189, 0.219, 0.242, 0.162, 0.256, 0.23]
- `B_max_per_seed`: [2.9743, 3.1607, 3.265, 3.2471, 2.6263, 2.9463]
- `n_B_ge_3_per_seed`: [0, 2, 2, 1, 0, 0]
- `signature_present_per_seed`: [False, False, False, False, False, False]
- `halting_ktb_n1_max`: [0, 0, 0, 0, 0, 0]

**DET: injected, no bottleneck signature (trigger limitation at this magnitude)**

- The fault is realised exactly as specified (constant, valid, equal to the last valid pre-4500 reading, while the paired NOI run varies), and it is applied to emitted observations only (Proxy truth at AID02109 still varies). The frozen reading is a plausible value, so the fault does not dominate the residual: the mean r_U^o over the window is within +-0.7 sigma_o in every seed, and the single-tick extremes (|r_U^o| = 1.6-3.3) are inside the paired NOI control's own range (2.1-3.4) on the same detector. B is half the *difference* of the two detectors' occupancy residuals plus a speed term whose stuck component has the opposite sign, so B never reaches 3 at two consecutive ticks. The sensor fault therefore does not create a bottleneck signature the corrected G4 rule could see.
- `sensor_fault`: AID02109:stuck:4500:5400 in all 6 EVT and 6 CONV run_info.json
- `stuck_constant_and_equal_to_last_valid_pre_4500`: [True, True, True, True, True, True]
- `B_max_per_seed`: [2.4707, 2.3085, 2.6081, 2.2795, 2.1098, 2.8155]
- `n_B_ge_3_per_seed`: [0, 0, 0, 0, 0, 0]
- `signature_present_per_seed`: [False, False, False, False, False, False]
- `max_abs_r_Uo_per_seed`: [1.5686, 2.1397, 3.2927, 2.0073, 1.9782, 2.3659]
- `max_abs_r_Uo_per_seed_NOI_control`: [3.3734, 2.2538, 2.1074, 2.1939, 2.7628, 2.646]

**INC reference**: The INC EVT runs show B up to 16.3, 5-11 ticks with B >= 3, streaks of 3-7 consecutive ticks and 2-6 alarms; the same code path does fire when a real bottleneck exists. Their trigger_log B is computed with event.downweight = 5.0 on both pair detectors once the fault hypothesis is adopted, so the logged B after adoption is 5x smaller than the raw residuals.

**NOI reference**: NOI EVT runs are the false-alarm control: 0-1 isolated ticks with B >= 3 (up to 4.08), never two consecutive, no alarm.

## 5. Inferred column meanings

- `proxy_truth.q`: citypulse/sim.py:read_detectors -- 'vehicles in the previous completed 30 s interval' summed over the detector's lanes, so the row at tick t covers [t-30, t); v is the count-weighted mean speed (km/h, NaN when q=0), o the mean lane occupancy (%).
- `proxy_halting.ktb_w3|ktb_n1`: TraCI edge.getLastStepHaltingNumber, sampled on the same 30 s ticks; halting_sum = ktb_w3 + ktb_n1.
- `twin_log.obs_*`: the SensorMsg reading as the Twin received it (Proxy truth passed through SensorEmulator, including any --sensor-fault); twin_* is the Twin's own state.
- `trigger_log.B`: event.bottleneck_index; NaN means the interval was missing (obs invalid / null occupancy / null twin reading / no sigma). The logged frame drops the 'why' reason and the residual terms, so both are recomputed here from twin_log + sigma_event.json.
- `rou.xml vehicle@depart`: scheduled departure time of the Proxy demand; SUMO may insert later when the entry is congested, so this is the *scheduled* shock and proxy_truth.q is the realised passage.
