MODEL: Gemini 3.8 Flash (High)

# NA-300 Qualification Test Report

Preregistered qualification test per `docs/na300-qualification-plan.md` on synthetic B-lite net5 / synth5.
Protocol uses frozen coverage rule `drop_every_3rd` (AID07105 unobserved, AID07106 boundary) and Twin base factor 0.85.

## 1. Executive Summary & Preregistered Acceptance Verdicts

**Overall Benchmark Status: NOT QUALIFIED (Negative Result: Oct 6 is mechanics pilot only)**

| Acceptance Criterion | Preregistered Rule | Observed Result | 95% CI / Thresholds | Verdict |
|---|---|---|---|---|
| **Criterion 1: Interior 5-min Flow RMSE** | Paired $\Delta$ (NA-300 − OL) 95% CI entirely below 0 | $\Delta = -129.28$ veh/h | [-142.15, -116.42] veh/h | **PASS** |
| **Criterion 2: Multiplier Stability** | All 8 seeds: rev/h $\le 6.0$, range $\le 0.20$, $\pm 5\%$ med $\ge 80\%$ | Max rev/h: 4.00, Max range: 0.177 | Min fraction: 33.3% | **FAIL** |

## 2. Seed-Reservation Check

- **Preregistered Seeds**: Dev seeds 4001–4003, Eval seeds 5001–5008, Reserved E* seeds 6001–6008.
- **Verification**: Prior to test launch, all directories, `run_info.json`, and experiment configurations under `results/` were searched.
- **Findings**: No prior run, configuration file, or result artifact used seeds 4001–4003, 5001–5008, or 6001–6008. All 19 seeds were confirmed strictly reserved.

## 3. Calibrated Boundary Noise Scale (σ_300)

- **Detector**: `AID07106`
- **σ_300 Value**: `177.912` veh/h
- **Formula**: $1.4826 \times \text{MAD}$ of 300-s mean residuals $(q_{\text{obs}} - q_{\text{twin}})\times 120$ from Biased-OL dev runs (seeds 4001, 4002, 4003) over [900, 7200 s].
- **Median Residual**: `+480.000` veh/h, **MAD**: `120.000` veh/h, **Mean Residual**: `+462.146` veh/h.
- **Block Counts**: Total candidate blocks considered: `63` (21 per seed), Complete blocks: `41`, Excluded blocks: `22`.
- **Exclusions by Seed & Reason**:
  - `ol_4001`: 6 excluded (invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10)
  - `ol_4002`: 9 excluded (invalid_readings_valid_8_of_10, invalid_readings_valid_8_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_8_of_10, invalid_readings_valid_7_of_10)
  - `ol_4003`: 7 excluded (invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10, invalid_readings_valid_9_of_10)

## 4. Evaluation Seeds Detailed Results (5001–5008)

### Table 1: Primary Metric — Interior 5-min Flow RMSE (1,800–7,200 s)

| Eval Seed | OL 5-min RMSE (veh/h) | NA-300 5-min RMSE (veh/h) | Paired $\Delta$ (veh/h) | OL 5-min Bias (veh/h) | NA-300 5-min Bias (veh/h) | Scored Blocks | Excluded Blocks |
|---|---|---|---|---|---|---|---|
| Seed 5001 | 346.02 | 221.23 | **-124.79** | +223.65 | +69.00 | 124 | 506 |
| Seed 5002 | 338.22 | 199.98 | **-138.24** | +218.46 | +42.79 | 122 | 508 |
| Seed 5003 | 327.76 | 210.38 | **-117.39** | +210.61 | +49.04 | 127 | 503 |
| Seed 5004 | 318.80 | 209.75 | **-109.04** | +189.25 | +39.66 | 118 | 512 |
| Seed 5005 | 328.98 | 192.83 | **-136.15** | +213.17 | +14.05 | 123 | 507 |
| Seed 5006 | 346.00 | 187.13 | **-158.86** | +232.93 | +33.02 | 129 | 501 |
| Seed 5007 | 344.10 | 224.00 | **-120.10** | +223.28 | +52.72 | 122 | 508 |
| Seed 5008 | 345.14 | 215.44 | **-129.70** | +243.67 | +94.51 | 121 | 509 |
| **Mean** | **336.88** | **207.59** | **-129.28** | **+219.38** | **+49.35** | **986** | **4054** |
| **95% CI (df=7)** | — | — | **[-142.15, -116.42]** | — | — | — | — |

### Table 2: Multiplier Stability (NA-300 Arm, t > 1,800 s)

| Eval Seed | $m_{\text{TKO}}$ Range ($\le 0.20$) | Reversals | Reversals / h ($\le 6.0$) | Median $m$ | Time within $\pm 5\%$ ($\ge 80\%$) | Verdict | Ticks by Reason (upd / db / cong / inv) |
|---|---|---|---|---|---|---|---|
| Seed 5001 | 0.109 | 2 | 1.33 | 1.132 | 100.0% | **PASS** | 5 / 7 / 0 / 6 |
| Seed 5002 | 0.147 | 3 | 2.00 | 1.156 | 83.3% | **PASS** | 7 / 3 / 0 / 8 |
| Seed 5003 | 0.147 | 2 | 1.33 | 1.112 | 66.7% | **FAIL** | 7 / 5 / 0 / 6 |
| Seed 5004 | 0.165 | 2 | 1.33 | 1.117 | 66.7% | **FAIL** | 7 / 6 / 0 / 5 |
| Seed 5005 | 0.177 | 6 | 4.00 | 1.178 | 55.6% | **FAIL** | 9 / 6 / 0 / 3 |
| Seed 5006 | 0.171 | 0 | 0.00 | 1.155 | 33.3% | **FAIL** | 4 / 6 / 0 / 8 |
| Seed 5007 | 0.084 | 1 | 0.67 | 1.144 | 100.0% | **PASS** | 3 / 6 / 0 / 9 |
| Seed 5008 | 0.143 | 1 | 0.67 | 1.103 | 66.7% | **FAIL** | 5 / 7 / 0 / 6 |

### Table 3: Signed Bias and 30-s Scale Metrics (1,800–7,200 s)

| Eval Seed | OL Int Bias (30s) | NA-300 Int Bias (30s) | OL AID07106 Bias | NA-300 AID07106 Bias | OL 30s Flow RMSE | NA-300 30s Flow RMSE | Paired $\Delta$ 30s Flow | OL Speed RMSE | NA-300 Speed RMSE |
|---|---|---|---|---|---|---|---|---|---|
| Seed 5001 | +192.99 | +53.74 | +450.70 | +161.86 | 665.94 | 623.83 | **-42.11** | 6.16 | 6.27 |
| Seed 5002 | +189.09 | +31.34 | +463.95 | +138.14 | 671.60 | 606.36 | **-65.24** | 6.23 | 6.23 |
| Seed 5003 | +187.57 | +41.25 | +437.93 | +117.93 | 648.06 | 598.11 | **-49.95** | 6.33 | 6.24 |
| Seed 5004 | +184.45 | +53.68 | +434.74 | +143.31 | 675.80 | 638.35 | **-37.45** | 6.43 | 6.26 |
| Seed 5005 | +185.41 | +8.36 | +432.81 | +51.24 | 690.29 | 640.49 | **-49.80** | 6.40 | 6.38 |
| Seed 5006 | +194.08 | +22.29 | +473.72 | +122.09 | 673.18 | 588.53 | **-84.64** | 6.31 | 6.17 |
| Seed 5007 | +186.15 | +35.87 | +471.53 | +143.29 | 644.20 | 600.06 | **-44.14** | 6.40 | 6.39 |
| Seed 5008 | +194.30 | +59.06 | +442.07 | +158.62 | 659.88 | 600.42 | **-59.47** | 6.35 | 6.47 |
| **Mean** | **+189.25** | **+38.20** | **+450.93** | **+129.56** | **666.12** | **612.02** | **-54.10** | **6.33** | **6.30** |
| **95% CI (df=7)** | — | — | — | — | — | — | **[-66.90, -41.29]** | — | — |

### Table 4: 15-Minute Forecast Interior Flow RMSE (t ∈ {3600, 4800, 6000})

| Eval Seed | OL 3600 | NA 3600 | OL 4800 | NA 4800 | OL 6000 | NA 6000 | OL Pooled | NA Pooled | Paired $\Delta$ Pooled |
|---|---|---|---|---|---|---|---|---|---|
| Seed 5001 | 706.13 | 652.23 | 693.95 | 607.42 | 587.19 | 557.55 | 664.23 | 606.67 | **-57.55** |
| Seed 5002 | 646.70 | 598.84 | 659.80 | 570.64 | 681.14 | 612.45 | 662.75 | 594.37 | **-68.38** |
| Seed 5003 | 678.09 | 644.40 | 596.66 | 602.78 | 602.63 | 559.94 | 627.01 | 603.40 | **-23.62** |
| Seed 5004 | 693.31 | 691.10 | 673.89 | 647.33 | 661.38 | 620.57 | 676.24 | 653.46 | **-22.78** |
| Seed 5005 | 761.61 | 585.34 | 684.49 | 643.79 | 704.85 | 584.03 | 717.86 | 604.74 | **-113.12** |
| Seed 5006 | 692.45 | 632.92 | 683.22 | 572.22 | 686.45 | 544.38 | 687.36 | 584.09 | **-103.27** |
| Seed 5007 | 657.18 | 643.64 | 627.31 | 585.96 | 642.77 | 572.29 | 642.59 | 601.40 | **-41.19** |
| Seed 5008 | 650.44 | 604.32 | 628.88 | 611.31 | 607.40 | 529.80 | 629.15 | 582.82 | **-46.33** |
| **Mean** | — | — | — | — | — | — | **663.40** | **603.87** | **-59.53** |
| **95% CI (df=7)** | — | — | — | — | — | — | — | — | **[-87.83, -31.23]** |

## 5. Paired Statistical Comparison (df = 7, t_crit = 2.3646)

| Metric | Mean OL | Mean NA-300 | Mean Paired $\Delta$ | SD($\Delta$) | SE($\Delta$) | 95% Confidence Interval | Significant? |
|---|---|---|---|---|---|---|---|
| **Primary: 5-min Flow RMSE** | 336.88 | 207.59 | **-129.28** | 15.39 | 5.44 | **[-142.15, -116.42]** | YES (<0) |
| **Forecast Pooled Flow RMSE** | 663.40 | 603.87 | **-59.53** | 33.85 | 11.97 | **[-87.83, -31.23]** | YES (<0) |
| **30-s Interior Flow RMSE** | 666.12 | 612.02 | **-54.10** | 15.32 | 5.41 | **[-66.90, -41.29]** | YES (<0) |
| **Interior Signed Bias** | +189.25 | +38.20 | **-151.06** | 16.80 | 5.94 | **[-165.10, -137.01]** | YES |

## 6. Multiplier $m_{\text{TKO}}$ Trajectories (One Row per 5 min across 8 Evaluation Seeds)

| Time $t$ (s) | Seed 5001 $m$ | Seed 5002 $m$ | Seed 5003 $m$ | Seed 5004 $m$ | Seed 5005 $m$ | Seed 5006 $m$ | Seed 5007 $m$ | Seed 5008 $m$ |
|---|---|---|---|---|---|---|---|---|
| 300 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 600 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0421 | 1.0000 | 1.0316 | 1.0000 |
| 900 | 1.0334 | 1.0500 | 1.0457 | 1.0000 | 1.0421 | 1.0500 | 1.0832 | 1.0500 |
| 1200 | 1.0334 | 1.1025 | 1.0457 | 1.0000 | 1.0421 | 1.0780 | 1.0832 | 1.0500 |
| 1500 | 1.0780 | 1.1025 | 1.0776 | 1.0394 | 1.0779 | 1.0780 | 1.1231 | 1.0767 |
| 1800 | 1.0780 | 1.1025 | 1.0776 | 1.0394 | 1.0779 | 1.0780 | 1.1231 | 1.0767 |
| 2100 | 1.0780 | 1.1025 | 1.0776 | 1.0675 | 1.0779 | 1.0780 | 1.1231 | 1.0767 |
| 2400 | 1.1077 | 1.1025 | 1.0776 | 1.1109 | 1.1161 | 1.0780 | 1.1231 | 1.0767 |
| 2700 | 1.0783 | 1.1025 | 1.0776 | 1.1109 | 1.0949 | 1.0780 | 1.1231 | 1.0767 |
| 3000 | 1.0783 | 1.0727 | 1.0776 | 1.0850 | 1.0949 | 1.0780 | 1.0899 | 1.0515 |
| 3300 | 1.0783 | 1.0727 | 1.0776 | 1.0850 | 1.0949 | 1.0780 | 1.0899 | 1.0515 |
| 3600 | 1.0783 | 1.1091 | 1.0776 | 1.0850 | 1.1221 | 1.0780 | 1.0899 | 1.0515 |
| 3900 | 1.1323 | 1.1579 | 1.0776 | 1.0850 | 1.1686 | 1.1319 | 1.1444 | 1.0515 |
| 4200 | 1.1323 | 1.1579 | 1.0776 | 1.0850 | 1.1686 | 1.1319 | 1.1444 | 1.0764 |
| 4500 | 1.1323 | 1.1579 | 1.1003 | 1.0850 | 1.1310 | 1.1319 | 1.1444 | 1.0764 |
| 4800 | 1.1323 | 1.1874 | 1.1241 | 1.1223 | 1.1875 | 1.1781 | 1.1444 | 1.1302 |
| 5100 | 1.1323 | 1.1557 | 1.1484 | 1.1223 | 1.1875 | 1.1781 | 1.1444 | 1.1302 |
| 5400 | 1.1323 | 1.1557 | 1.1484 | 1.1223 | 1.1875 | 1.1781 | 1.1444 | 1.1302 |
| 5700 | 1.1323 | 1.1557 | 1.2018 | 1.1784 | 1.2396 | 1.2218 | 1.1444 | 1.1707 |
| 6000 | 1.1323 | 1.1557 | 1.2245 | 1.1784 | 1.2396 | 1.2218 | 1.1444 | 1.1943 |
| 6300 | 1.1537 | 1.1557 | 1.2245 | 1.1784 | 1.2021 | 1.2218 | 1.1444 | 1.1943 |
| 6600 | 1.1870 | 1.1557 | 1.1859 | 1.1784 | 1.2021 | 1.2218 | 1.1444 | 1.1943 |
| 6900 | 1.1870 | 1.1799 | 1.1859 | 1.2078 | 1.2021 | 1.2218 | 1.1744 | 1.1943 |
| 7200 | 1.1870 | 1.2199 | 1.2127 | 1.2320 | 1.2549 | 1.2495 | 1.1744 | 1.1943 |

## 7. Methodological and Protocol Notes

1. **Preregistered Binding Protocol**: Executed strictly against `docs/na300-qualification-plan.md` with zero subsequent tuning.
2. **Twin Base Factor**: Imposed 0.85 reduction (`--twin-base-factor 0.85`) identically applied to Open Loop and NA-300.
3. **Boundary Sensor & Coverage Rule**: Preserved frozen `drop_every_3rd` coverage rule without any emulator monkey-patching; `AID07106` used as the boundary detector.
4. **Scored Blocks**: Primary 5-min flow RMSE scored strictly on identical complete blocks across arms.

REPORT DONE