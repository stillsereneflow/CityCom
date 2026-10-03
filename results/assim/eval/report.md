MODEL: Gemini 3.8 Flash (High)

# Normal-Mode Assimilation (NA) vs Open Loop (OL) Evaluation Report

Predeclared benchmark evaluation per `docs/oct5-normal-assim-plan.md` on synthetic B-lite net5 / synth5.

## 1. Executive Summary & Acceptance Verdicts

**Overall Benchmark Status: REJECTED (Reported as Negative Result)**

| Acceptance Criterion | Target Rule | Observed Result | 95% CI / Bounds | Verdict |
|---|---|---|---|---|
| **NA Beats OL (Flow RMSE)** | Paired $\Delta$ (NA − OL) 95% CI < 0 | $\Delta = +25.18$ veh/h | [-32.82, +83.19] veh/h | **FAIL** |
| **Forecast Metric (Flow RMSE)** | Companion forecast check | $\Delta = +29.98$ veh/h | [-72.04, +131.99] veh/h | NEUTRAL/WORSE |
| **No Multiplier Oscillation** | On all eval seeds: rev/h $\le 6$, range $\le 0.20$, $\pm 5\%$ med $\ge 80\%$ | Max rev/h: 2.00, Max range: 0.143 | Min fraction: 80.0% | **PASS** |

**Calibrated Boundary Noise Scale (sigma_AID07105)**: `533.736` veh/h (computed as 1.4826 * MAD of OL flow residuals on dev seeds 1001, 1002, 1003 pooled, t >= 900 s).

## 2. Evaluation Seeds: Paired Comparisons (1,800–7,200 s)

### Metric 1: Interior Fit (Flow and Speed RMSE)

| Eval Seed | OL Flow RMSE (veh/h) | NA Flow RMSE (veh/h) | Paired $\Delta$ Flow | OL Speed RMSE (km/h) | NA Speed RMSE (km/h) | Paired $\Delta$ Speed |
|---|---|---|---|---|---|---|
| Seed 3001 | 583.71 | 634.19 | **+50.49** | 6.10 | 6.34 | **+0.25** |
| Seed 3002 | 597.21 | 658.39 | **+61.17** | 5.87 | 5.97 | **+0.11** |
| Seed 3003 | 610.54 | 614.36 | **+3.81** | 6.12 | 6.41 | **+0.29** |
| Seed 3004 | 597.86 | 583.12 | **-14.74** | 5.95 | 5.98 | **+0.03** |
| **Mean** | **597.33** | **622.51** | **+25.18** | **6.01** | **6.18** | **+0.17** |
| **95% CI (t-dist)** | — | — | **[-32.82, +83.19]** | — | — | **[-0.02, +0.36]** |

### Metric 2: 15-Minute Forecast Interior Flow RMSE (t ∈ {3600, 4800, 6000})

| Eval Seed | OL 3600 | NA 3600 | OL 4800 | NA 4800 | OL 6000 | NA 6000 | OL Pooled | NA Pooled | Paired $\Delta$ Pooled |
|---|---|---|---|---|---|---|---|---|---|
| Seed 3001 | 574.34 | 651.41 | 513.98 | 656.79 | 613.96 | 644.66 | 569.48 | 650.90 | **+81.42** |
| Seed 3002 | 563.17 | 650.90 | 565.42 | 654.70 | 532.33 | 607.10 | 553.70 | 637.72 | **+84.02** |
| Seed 3003 | 582.22 | 590.22 | 607.00 | 646.75 | 644.41 | 602.77 | 612.01 | 613.72 | **+1.71** |
| Seed 3004 | 570.04 | 603.68 | 605.10 | 527.34 | 622.11 | 521.98 | 599.50 | 552.25 | **-47.25** |
| **Mean** | — | — | — | — | — | — | **583.67** | **613.65** | **+29.98** |
| **95% CI (t-dist)** | — | — | — | — | — | — | — | — | **[-72.04, +131.99]** |

### Metric 3: Multiplier Stability (NA Arm, Eval Seeds, t > 1,800 s)

| Eval Seed | $m_{\text{TKO}}$ Range ($\le 0.20$) | Reversals | Reversals / h ($\le 6.0$) | Median $m$ | Time within $\pm 5\%$ ($\ge 80\%$) | Status | Ticks by Reason (upd / db / cong / inv) |
|---|---|---|---|---|---|---|---|
| Seed 3001 | 0.143 | 2 | 1.33 | 0.898 | 80.0% | **PASS** | 6 / 9 / 64 / 11 |
| Seed 3002 | 0.143 | 1 | 0.67 | 0.945 | 80.0% | **PASS** | 5 / 3 / 72 / 10 |
| Seed 3003 | 0.097 | 1 | 0.67 | 1.024 | 92.2% | **PASS** | 3 / 7 / 69 / 11 |
| Seed 3004 | 0.097 | 3 | 2.00 | 0.995 | 100.0% | **PASS** | 5 / 12 / 65 / 8 |

### Metric 4: Boundary Fit Sanity Check (AID07105 Flow RMSE)

| Eval Seed | OL Boundary RMSE (veh/h) | NA Boundary RMSE (veh/h) | $\Delta$ (NA − OL) |
|---|---|---|---|
| Seed 3001 | 608.06 | 674.19 | +66.13 |
| Seed 3002 | 566.50 | 675.46 | +108.96 |
| Seed 3003 | 608.25 | 616.60 | +8.35 |
| Seed 3004 | 575.57 | 596.92 | +21.35 |

## 3. Development Seeds Reference (1001, 1002, 1003)

| Dev Seed | Arm | Interior Flow RMSE | Interior Speed RMSE | Forecast Pooled RMSE | Boundary RMSE | $m$ Range | Ticks by Reason (upd / db / cong / inv) |
|---|---|---|---|---|---|---|---|
| Seed 1001 | OL | 609.41 | 5.97 | 619.39 | 571.65 | 1.000 (fixed) | — |
| Seed 1001 | NA | 647.34 | 6.26 | 663.22 | 639.49 | 0.185 | 6 / 8 / 68 / 8 |
| Seed 1002 | OL | 610.52 | 5.97 | 599.05 | 569.36 | 1.000 (fixed) | — |
| Seed 1002 | NA | 619.16 | 6.06 | 596.91 | 647.05 | 0.052 | 4 / 10 / 70 / 6 |
| Seed 1003 | OL | 607.15 | 6.11 | 594.05 | 621.26 | 1.000 (fixed) | — |
| Seed 1003 | NA | 619.95 | 5.99 | 598.93 | 621.47 | 0.142 | 6 / 3 / 73 / 8 |

## 4. Multiplier $m_{\text{TKO}}$ Trajectories (One Row per 5 min per Evaluation Seed)

Sampled at 300-s (5-min) window ends across the simulation horizon [0, 7200 s]:

| Time $t$ (s) | Seed 3001 $m$ | Seed 3002 $m$ | Seed 3003 $m$ | Seed 3004 $m$ |
|---|---|---|---|---|
| 300 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 600 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 900 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 1200 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 1500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 1800 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 2100 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 2400 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 2700 | 0.9025 | 0.9025 | 0.9500 | 1.0000 |
| 3000 | 0.8574 | 0.8574 | 0.9975 | 0.9500 |
| 3300 | 0.8574 | 0.9002 | 0.9975 | 0.9975 |
| 3600 | 0.9002 | 0.9002 | 0.9975 | 0.9975 |
| 3900 | 0.9002 | 0.9002 | 0.9975 | 0.9975 |
| 4200 | 0.9002 | 0.9002 | 0.9975 | 0.9476 |
| 4500 | 0.9002 | 0.9453 | 0.9975 | 0.9950 |
| 4800 | 0.9453 | 0.9453 | 1.0474 | 0.9950 |
| 5100 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 5400 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 5700 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 6000 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 6300 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 6600 | 0.8980 | 0.9453 | 1.0474 | 0.9950 |
| 6900 | 0.8980 | 0.9453 | 1.0474 | 1.0448 |
| 7200 | 0.8980 | 0.9453 | 1.0474 | 1.0448 |

## 5. Methodological & Diagnostic Notes

1. **Boundary Detector Sensor Coverage**:
   - In the synthetic B-lite net5 network, 21 induction loops are mapped. Under the index-based `drop_every_3rd` coverage rule (`k % 3 != 2` on sorted IDs), detector `AID07105` is located at sorted index 11 (`11 % 3 == 2`).
   - Under an unpatched run, `AID07105` would never be emitted in `SensorMsg`, leaving the boundary unobserved and the Twin assimilator permanently receiving missing inputs ($m \equiv 1.0$).
   - In accordance with the binding plan (`docs/oct5-normal-assim-plan.md`), which predeclares AID07105 as the boundary sensor providing causal readings for assimilation and σ estimation, the proxy launcher wrapper ensures `AID07105` is observed (`self.observed = sorted(set(self.observed) | {'AID07105'})`), leaving all 14 interior detectors untouched.
2. **Congestion and Deadband Gates**:
   - The high flow on `tko_in` leads to mean occupancy near or exceeding the `o_crit = 15%` threshold across many intervals, triggering the `congested` safety gate.
   - Furthermore, flow residuals between Twin and Proxy at the 30-s scale have a substantial standard deviation, giving a noise scale $\sigma \approx 600$ veh/h. With deadband $\delta = 1.0 \sigma$, smaller demand adjustments remain within the deadband.
3. **Zero Tuning Compliance**:
   - As mandated by the protocol, all parameters ($\kappa = 0.3$, $\delta = 1.0 \sigma$, step clip $0.05$, $m \in [0.5, 1.8]$, $o_{\text{crit}} = 15\%$) were evaluated with zero tuning budget. The results are reported faithfully as found.

REPORT DONE