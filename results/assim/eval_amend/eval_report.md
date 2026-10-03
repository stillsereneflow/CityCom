MODEL: Gemini 3.8 Flash (High)

# Amended Normal-Mode Assimilation (NA) vs Open Loop (OL) Evaluation Report

Amended benchmark evaluation per `docs/oct5-normal-assim-plan.md` §'Amendment 2026-10-03 20:15' on synthetic B-lite net5 / synth5.
Protocol uses frozen coverage rule `drop_every_3rd` (AID07105 unobserved) and boundary detector AID07106.

## 1. Executive Summary & Acceptance Verdicts

**Overall Benchmark Status: REJECTED (Reported as Negative Result)**

| Acceptance Criterion | Target Rule | Observed Result | 95% CI / Bounds | Verdict |
|---|---|---|---|---|
| **NA Beats OL (Flow RMSE)** | Paired $\Delta$ (NA − OL) 95% CI < 0 | $\Delta = +18.42$ veh/h | [-23.99, +60.83] veh/h | **FAIL** |
| **Forecast Metric (Flow RMSE)** | Companion forecast check | $\Delta = +49.92$ veh/h | [-27.04, +126.87] veh/h | NEUTRAL/WORSE |
| **No Multiplier Oscillation** | On all eval seeds: rev/h $\le 6$, range $\le 0.20$, $\pm 5\%$ med $\ge 80\%$ | Max rev/h: 6.67, Max range: 0.378 | Min fraction: 42.2% | **FAIL** |

**Calibrated Boundary Noise Scale (sigma_AID07106)**: `533.736` veh/h (computed as 1.4826 * MAD of OL flow residuals on dev seeds 1001, 1002, 1003 pooled, t >= 900 s).

## 2. Evaluation Seeds: Paired Comparisons (1,800–7,200 s)

### Metric 1: Interior Fit (Flow and Speed RMSE)

| Eval Seed | OL Flow RMSE (veh/h) | NA Flow RMSE (veh/h) | Paired $\Delta$ Flow | OL Speed RMSE (km/h) | NA Speed RMSE (km/h) | Paired $\Delta$ Speed |
|---|---|---|---|---|---|---|
| Seed 3001 | 590.51 | 630.58 | **+40.07** | 6.24 | 6.42 | **+0.18** |
| Seed 3002 | 587.79 | 628.79 | **+41.00** | 5.99 | 6.18 | **+0.19** |
| Seed 3003 | 601.34 | 588.32 | **-13.02** | 6.31 | 6.33 | **+0.02** |
| Seed 3004 | 600.04 | 605.67 | **+5.63** | 6.26 | 6.36 | **+0.10** |
| **Mean** | **594.92** | **613.34** | **+18.42** | **6.20** | **6.32** | **+0.12** |
| **95% CI (t-dist)** | — | — | **[-23.99, +60.83]** | — | — | **[+0.00, +0.24]** |

### Metric 2: 15-Minute Forecast Interior Flow RMSE (t ∈ {3600, 4800, 6000})

| Eval Seed | OL 3600 | NA 3600 | OL 4800 | NA 4800 | OL 6000 | NA 6000 | OL Pooled | NA Pooled | Paired $\Delta$ Pooled |
|---|---|---|---|---|---|---|---|---|---|
| Seed 3001 | 559.24 | 647.86 | 532.31 | 683.59 | 629.59 | 719.25 | 575.25 | 684.28 | **+109.03** |
| Seed 3002 | 552.84 | 588.70 | 562.71 | 567.68 | 527.50 | 631.30 | 547.75 | 596.73 | **+48.99** |
| Seed 3003 | 561.33 | 590.98 | 597.67 | 624.87 | 649.22 | 566.50 | 603.98 | 594.56 | **-9.42** |
| Seed 3004 | 596.86 | 655.65 | 584.19 | 573.64 | 622.95 | 719.89 | 601.60 | 652.67 | **+51.07** |
| **Mean** | — | — | — | — | — | — | **582.14** | **632.06** | **+49.92** |
| **95% CI (t-dist)** | — | — | — | — | — | — | — | — | **[-27.04, +126.87]** |

### Metric 3: Multiplier Stability (NA Arm, Eval Seeds, t > 1,800 s)

| Eval Seed | $m_{\text{TKO}}$ Range ($\le 0.20$) | Reversals | Reversals / h ($\le 6.0$) | Median $m$ | Time within $\pm 5\%$ ($\ge 80\%$) | Status | Ticks by Reason (upd / db / cong / inv) |
|---|---|---|---|---|---|---|---|
| Seed 3001 | 0.239 | 10 | 6.67 | 1.024 | 64.4% | **FAIL** | 18 / 62 / 0 / 10 |
| Seed 3002 | 0.378 | 9 | 6.00 | 1.014 | 42.2% | **FAIL** | 25 / 58 / 0 / 7 |
| Seed 3003 | 0.322 | 9 | 6.00 | 1.021 | 56.7% | **FAIL** | 22 / 59 / 0 / 9 |
| Seed 3004 | 0.339 | 8 | 5.33 | 0.988 | 53.3% | **FAIL** | 21 / 63 / 0 / 6 |

### Metric 4: Boundary Fit Sanity Check (AID07106 Flow RMSE)

| Eval Seed | OL Boundary RMSE (veh/h) | NA Boundary RMSE (veh/h) | $\Delta$ (NA − OL) |
|---|---|---|---|
| Seed 3001 | 621.64 | 580.02 | -41.63 |
| Seed 3002 | 625.99 | 628.36 | +2.38 |
| Seed 3003 | 645.90 | 586.09 | -59.80 |
| Seed 3004 | 629.45 | 640.27 | +10.82 |

## 3. Development Seeds Reference (1001, 1002, 1003)

| Dev Seed | Arm | Interior Flow RMSE | Interior Speed RMSE | Forecast Pooled RMSE | Boundary RMSE | $m$ Range | Ticks by Reason (upd / db / cong / inv) |
|---|---|---|---|---|---|---|---|
| Seed 1001 | OL | 609.73 | 6.18 | 618.85 | 635.18 | 1.000 (fixed) | — |
| Seed 1001 | NA | 624.96 | 6.13 | 664.24 | 597.99 | 0.287 | 18 / 64 / 0 / 8 |
| Seed 1002 | OL | 608.73 | 6.17 | 602.63 | 637.62 | 1.000 (fixed) | — |
| Seed 1002 | NA | 623.37 | 6.15 | 652.29 | 644.83 | 0.293 | 24 / 61 / 0 / 5 |
| Seed 1003 | OL | 604.58 | 6.10 | 597.20 | 597.64 | 1.000 (fixed) | — |
| Seed 1003 | NA | 620.50 | 6.20 | 601.74 | 610.66 | 0.232 | 21 / 61 / 0 / 8 |

## 4. Multiplier $m_{\text{TKO}}$ Trajectories (One Row per 5 min per Evaluation Seed)

Sampled at 300-s (5-min) window ends across the simulation horizon [0, 7200 s]:

| Time $t$ (s) | Seed 3001 $m$ | Seed 3002 $m$ | Seed 3003 $m$ | Seed 3004 $m$ |
|---|---|---|---|---|
| 300 | 0.9500 | 0.9975 | 0.9025 | 0.9500 |
| 600 | 0.9476 | 0.9950 | 0.9025 | 0.9950 |
| 900 | 1.0448 | 1.0448 | 0.9950 | 1.0448 |
| 1200 | 1.0448 | 1.0448 | 1.0448 | 1.0448 |
| 1500 | 0.9900 | 1.0421 | 1.0421 | 1.0421 |
| 1800 | 0.9876 | 1.0421 | 1.0421 | 0.9405 |
| 2100 | 0.9876 | 0.9405 | 0.9405 | 0.9405 |
| 2400 | 1.0369 | 0.9876 | 0.9876 | 0.9876 |
| 2700 | 0.9851 | 0.8913 | 0.8467 | 0.9382 |
| 3000 | 0.8890 | 0.8044 | 0.8044 | 0.8913 |
| 3300 | 0.9335 | 0.8868 | 0.8868 | 0.8467 |
| 3600 | 0.8868 | 0.8868 | 0.9312 | 0.8890 |
| 3900 | 1.0266 | 1.0266 | 1.0266 | 0.9802 |
| 4200 | 1.0779 | 0.9753 | 0.9753 | 1.0292 |
| 4500 | 1.0240 | 0.9753 | 1.0752 | 0.9777 |
| 4800 | 1.0752 | 1.0752 | 1.0752 | 1.0779 |
| 5100 | 1.0215 | 1.0752 | 1.0215 | 1.0240 |
| 5400 | 1.0215 | 1.0215 | 1.0726 | 1.1290 |
| 5700 | 1.1262 | 1.1234 | 1.1262 | 1.1855 |
| 6000 | 1.1262 | 1.0672 | 1.0699 | 1.1262 |
| 6300 | 1.0699 | 1.0138 | 1.0164 | 1.0164 |
| 6600 | 1.0699 | 1.0138 | 1.0164 | 0.9656 |
| 6900 | 1.0164 | 1.0645 | 1.0672 | 1.0138 |
| 7200 | 1.0672 | 1.1736 | 1.1206 | 1.0645 |

## 5. Comparison with forced07105 Variant (Protocol Difference & Outcomes)

The table below compares the amended protocol against the earlier labelled variant (`forced07105`), which patched the sensor emulator to force `AID07105` observable:

| Aspect | forced07105 Variant (Earlier) | Amended Protocol (This Run) |
|---|---|---|
| **Sensor Coverage Rule** | Patched (`AID07105` added to observed set) | Frozen `drop_every_3rd` (No emulator patch) |
| **Boundary Detector** | `AID07105` (on `tko_in`) | `AID07106` (most upstream observed on `tko_in`) |
| **AID07105 Status** | Observed (patch) | Unobserved (dropped by `drop_every_3rd`) |
| **Evaluated Interior Detectors** | 14 detectors (all except `AID07105`) | 13 detectors (all observed except `AID07105`, `AID07106`) |
| **Boundary Noise Scale $\sigma$** | 533.736 veh/h | 533.736 veh/h |
| **Paired $\Delta$ Flow RMSE** | $\Delta = +25.18$ veh/h [-32.82, +83.19] | $\Delta = +18.42$ veh/h [-23.99, +60.83] |
| **Paired $\Delta$ Forecast RMSE** | $\Delta = +29.98$ veh/h [-72.04, +131.99] | $\Delta = +49.92$ veh/h [-27.04, +126.87] |
| **Eval Ticks (upd / db / cong / inv)** | 19 / 31 / 270 / 40 | 86 / 242 / 0 / 32 |
| **Beats OL Acceptance** | FAIL | FAIL |
| **Overall Benchmark Verdict** | REJECTED | REJECTED (Reported as Negative Result) |

### Protocol Commentary
- **Fidelity to Freeze**: The amended run restores strict adherence to the frozen coverage rule (`drop_every_3rd`), completely eliminating the ad-hoc monkey patch of `SensorEmulator` that was used in the earlier run.
- **Sensor Positioning**: Shifting the boundary detector to `AID07106` (index 12 in the sorted loop array) leverages the most upstream loop that is genuinely transmitted in `SensorMsg` along the entry corridor without intermediate demand injections.

## 6. Methodological & Diagnostic Notes

1. **Boundary Detector Sensor Coverage**:
   - In the synthetic B-lite net5 network, 21 induction loops are mapped. Under the index-based `drop_every_3rd` coverage rule (`k % 3 != 2` on sorted IDs), detector `AID07105` is located at sorted index 11 (`11 % 3 == 2`) and is unobserved.
   - Per Amendment 2026-10-03 20:15, `AID07106` (sorted index 12, `12 % 3 == 0`) is the most upstream observed detector along the TKO entry path and serves as the boundary detector.
   - Interior scoring excludes both `AID07105` (unobserved) and `AID07106` (boundary detector), leaving 13 interior detectors evaluated across both arms and forecasts.
2. **Congestion and Deadband Gates**:
   - At detector `AID07106`, observed occupancy remained consistently below the `o_crit = 15%` threshold across all eval intervals, resulting in 0 congested ticks (in sharp contrast to `AID07105`, which was gated by congestion 270 times).
   - The assimilator performed 86 updates across the 4 eval seeds; 242 ticks were absorbed by the deadband $\delta = 1.0 \sigma$, and 32 ticks were invalid due to causal sensor dropouts.
3. **Zero Tuning Compliance**:
   - As mandated by the protocol, all parameters ($\kappa = 0.3$, $\delta = 1.0 \sigma$, step clip $0.05$, $m \in [0.5, 1.8]$, $o_{\text{crit}} = 15\%$) were evaluated with zero tuning budget. The results are reported faithfully as found.
4. **Counting Methodology**:
   - Strictly evaluated from logged 30-s interval values (`twin_log.parquet` `obs_q` and `twin_q`), never accumulating per-step `getLastStepVehicleNumber`.

REPORT DONE