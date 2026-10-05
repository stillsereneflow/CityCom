# Independent Check of Queue-Forecast Instrument in Development Runs

**Date:** 2026-10-05 21:32:36  
**Repository:** `D:\CityCom-astra`  
**Overall Status:** **PASS**

## 1. Independent Frozen Replay Readouts (Part 1)

Tested 9 snapshot conditions (`evt_inc_4401`, `conv_inc_4403`, `evt_inc_4406` at issue times 4800, 5100, 5400 s) loaded in fresh `libsumo` processes. ControlState and TwinDemandStream were re-applied/restored exactly as required.

| Run | Issue $t$ (s) | Loaded $t$ | Net Veh ($t_0$) | $t_0$ `ktb_w3` (all / halt) | $t_0$ `ktb_n1` (all / halt) | 5min Target $t$ | 5min Veh | 5min Halt (`w3` / `n1` / sum) | Saved Pred (5min) | 15min Target $t$ | 15min Veh | 15min Halt (`w3` / `n1` / sum) | Saved Pred (15min) | Match |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `evt_inc_4401` | 4800 | 4800 | 294 | 15 / 0 | 23 / 0 | 5100 | 327 | 0 / 0 / 0 | 0 | 5700 | 281 | 0 / 0 / 0 | 0 | PASS |
| `evt_inc_4401` | 5100 | 5100 | 326 | 7 / 0 | 30 / 0 | 5400 | 319 | 0 / 0 / 0 | 0 | 6000 | 336 | 0 / 0 / 0 | 0 | PASS |
| `evt_inc_4401` | 5400 | 5400 | 320 | 8 / 0 | 19 / 0 | 5700 | 268 | 0 / 0 / 0 | 0 | 6300 | 307 | 0 / 0 / 0 | 0 | PASS |
| `conv_inc_4403` | 4800 | 4800 | 287 | 11 / 0 | 34 / 0 | 5100 | 335 | 0 / 0 / 0 | 0 | 5700 | 286 | 0 / 0 / 0 | 0 | PASS |
| `conv_inc_4403` | 5100 | 5100 | 335 | 6 / 0 | 31 / 0 | 5400 | 330 | 0 / 0 / 0 | 0 | 6000 | 331 | 0 / 0 / 0 | 0 | PASS |
| `conv_inc_4403` | 5400 | 5400 | 330 | 11 / 0 | 26 / 0 | 5700 | 283 | 0 / 0 / 0 | 0 | 6300 | 315 | 0 / 0 / 0 | 0 | PASS |
| `evt_inc_4406` | 4800 | 4800 | 298 | 11 / 0 | 40 / 0 | 5100 | 332 | 0 / 0 / 0 | 0 | 5700 | 290 | 0 / 0 / 0 | 0 | PASS |
| `evt_inc_4406` | 5100 | 5100 | 334 | 11 / 0 | 30 / 0 | 5400 | 350 | 0 / 0 / 0 | 0 | 6000 | 324 | 0 / 0 / 0 | 0 | PASS |
| `evt_inc_4406` | 5400 | 5400 | 346 | 4 / 0 | 39 / 0 | 5700 | 294 | 0 / 0 / 0 | 0 | 6300 | 326 | 0 / 0 / 0 | 0 | PASS |

- **Scorer edge IDs:** `['ktb_w3', 'ktb_n1']`
- **Our edge IDs:** `['ktb_w3', 'ktb_n1']`
- **Edge IDs Match:** `True`
- **Individual Speed Check:** Vehicles on `ktb_w3` and `ktb_n1` had speeds 15.2-22.4 m/s (free flow); halting count (< 0.1 m/s) was identically 0 for all instances.

## 2. Full 48-Run Reconciliation (Part 2)

Checked all 48 development runs (`inc`, `noi`, `shk`, `det` × `evt`, `conv` × seeds 4401–4406):

- **Total cells checked:** 768
  - 5-minute cells evaluated against truth: 384 (48 per arm/scenario)
  - 15-minute cells evaluated against truth: 336 (42 per arm/scenario)
  - 15-minute cells beyond simulation horizon ($t=7500 > 7200$): 48 (6 per arm/scenario, truth=None)
- **Error formula reconciliation (`err == pred - truth`):** 0 mismatches (PASS)
- **Target time reconciliation (`target_t == issue + 300 / 900`):** 0 mismatches (PASS)
- **Truth value reconciliation (matches Proxy `halting_sum`):** 0 mismatches (PASS)

### Cell Counts by (Arm, Scenario, Horizon)

| Arm | Scenario | 5-min Cells (Expected 48) | 15-min Evaluated Cells (Expected 42) | 15-min Beyond Horizon | Status |
|---|---|---|---|---|---|
| `evt` | `inc` | 48 | 42 | 6 | PASS |
| `evt` | `noi` | 48 | 42 | 6 | PASS |
| `evt` | `shk` | 48 | 42 | 6 | PASS |
| `evt` | `det` | 48 | 42 | 6 | PASS |
| `conv` | `inc` | 48 | 42 | 6 | PASS |
| `conv` | `noi` | 48 | 42 | 6 | PASS |
| `conv` | `shk` | 48 | 42 | 6 | PASS |
| `conv` | `det` | 48 | 42 | 6 | PASS |

## 3. Conclusion & Findings

**Conclusion:** The zero queue predictions across all 48 development runs are a **real property of the Twin simulation state**, not an instrument artefact.

### Supporting Reasons:
1. **Instrument Fidelity:** The instrument inspects the exact corridor edges (`ktb_w3` and `ktb_n1`) where the incident and queue occur in the Proxy. The TraCI/libsumo `edge.getLastStepHaltingNumber` function returns the true number of vehicles with speed < 0.1 m/s, identical to explicit vehicle-by-vehicle speed thresholding.
2. **Absence of Simulated Congestion in the Twin:** In both Conventional (`conv`) and Event-driven (`evt`) runs, the Twin simulated network was completely unqueued on these edges:
   - In `conv`, no incident detection or lane-closing mechanism exists; traffic flows under full nominal 3-lane capacity.
   - In `evt`, the online evidence test failed to adopt the incident hypothesis across all 48 development runs (`replacement_log.jsonl` has 0 adoptions). Consequently, no lanes were ever closed in the Twin.
3. **Replay Persistence:** During frozen replay, traffic continues running on open lanes with nominal demand. Without lane restrictions, vehicles travel at free-flow speeds (~15–22 m/s), resulting in zero halting vehicles at both 300 s and 900 s horizons.
4. **Proxy vs. Twin Discrepancy:** The non-zero truth values (7–148 halting vehicles) recorded in `proxy_halting.parquet` arise because the physical incident (closing lanes 0 and 1 on `ktb_n1`) was active only in the Proxy. Because the Twin never adopted or replicated this restriction, the Twin's queue prediction remained 0.
