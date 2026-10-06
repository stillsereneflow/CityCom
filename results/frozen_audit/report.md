# Frozen offline decision audit: analysis

Input: `results\frozen_audit`

Seeds: [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508] (N = 8; seed source: frozen manifest 4501-4508). Decision time t_d = 5,100 s; horizon 900 s; J = total time spent (veh.h).

RNG binding: enforced on the prepared provenance, code/assets/environment fingerprint and snapshot hashes before any metric was computed.

## Claim boundary

> This is a confirmation of a laboratory, scenario-specific result: one corridor, one incident type, one decision time, the H_G5 hypothesis world. The submission may report these numbers as such. It may not present them as reliable incident inference, accurate benefit prediction in general, real-world effectiveness, or event-assimilation superiority

- The development audit's numbers (seeds 4201-4208) stay reported unchanged beside these, never pooled.
- The calibration floor is reported beside BEE; it is never subtracted from BEE and no causal-gap interpretation is made.

## 1. Validation

### Belief B

- **twin**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none
- **proxy**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none
- **calibration**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none

### Belief D300

- **twin**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none
- **proxy**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none
- **calibration**: 8/8 complete seeds [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508]; exclusions: none

## 2. Primary, belief B

Complete seeds: 8 [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508] (common complete seeds for paired comparisons).

| Seed | a* (R1) | Oracle (M1) | Top-1 | G_T(a*) | G_P(a*) | BEE signed | BEE abs | BEE rel | Regret | Regret denom | Regret rel | Spearman | Kendall | Floor (abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4501 | A3 | A3 | 1 | 7.526 | 4.451 | 3.076 | 3.076 | 0.0269 | 0.000 | 4.451 | 0.0000 | 0.600 | 0.400 | 0.417 |
| 4502 | A3 | A3 | 1 | 6.778 | 4.564 | 2.214 | 2.214 | 0.0188 | 0.000 | 4.564 | 0.0000 | 0.800 | 0.600 | 0.066 |
| 4503 | A3 | A3 | 1 | 6.252 | 4.669 | 1.583 | 1.583 | 0.0143 | 0.000 | 4.669 | 0.0000 | 0.900 | 0.800 | 0.198 |
| 4504 | A3 | A3 | 1 | 7.146 | 5.573 | 1.573 | 1.573 | 0.0134 | 0.000 | 5.573 | 0.0000 | 0.900 | 0.800 | 0.050 |
| 4505 | A3 | A3 | 1 | 7.512 | 5.093 | 2.419 | 2.419 | 0.0217 | 0.000 | 5.093 | 0.0000 | 0.900 | 0.800 | 0.601 |
| 4506 | A3 | A3 | 1 | 7.706 | 5.348 | 2.358 | 2.358 | 0.0202 | 0.000 | 5.348 | 0.0000 | 0.800 | 0.600 | 0.612 |
| 4507 | A3 | A3 | 1 | 6.954 | 4.647 | 2.307 | 2.307 | 0.0203 | 0.000 | 4.647 | 0.0000 | 0.800 | 0.600 | 0.235 |
| 4508 | A3 | A4 | 0 | 6.652 | 4.887 | 1.765 | 1.765 | 0.0155 | -0.268 | 4.619 | -0.0581 | 0.900 | 0.800 | 0.349 |

### Pooled over seeds

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| G_T_hat | 8 | 7.066 | [6.647, 7.484] | [6.733, 7.383] | none |
| G_P | 8 | 4.904 | [4.569, 5.239] | [4.659, 5.172] | none |
| BEE_signed | 8 | 2.162 | [1.738, 2.586] | [1.846, 2.507] | none |
| BEE_abs | 8 | 2.162 | [1.738, 2.586] | [1.846, 2.507] | none |
| BEE_rel | 8 | 0.019 | [0.015, 0.023] | [0.016, 0.022] | none |
| BEE_signed_rel | 8 | 0.019 | [0.015, 0.023] | [0.016, 0.022] | none |
| BEE_signed_unsplit | 8 | 2.029 | [1.690, 2.368] | [1.754, 2.276] | none |
| BEE_abs_unsplit | 8 | 2.029 | [1.690, 2.368] | [1.754, 2.276] | none |
| BEE_rel_unsplit | 8 | 0.018 | [0.015, 0.021] | [0.015, 0.020] | none |
| Regret | 8 | -0.034 | [-0.113, 0.046] | [-0.101, 0.000] | none |
| Regret_denom | 8 | 4.870 | [4.525, 5.216] | [4.624, 5.151] | none |
| Regret_rel | 8 | -0.007 | [-0.024, 0.010] | [-0.022, 0.000] | none |
| Regret_unsplit | 8 | 0.007 | [-0.009, 0.023] | [0.000, 0.021] | none |
| Regret_denom_unsplit | 8 | 4.916 | [4.540, 5.292] | [4.650, 5.221] | none |
| Regret_rel_unsplit | 8 | 0.001 | [-0.002, 0.005] | [0.000, 0.004] | none |
| top1_agree | 8 | 0.875 | [0.579, 1.171] | [0.625, 1.000] | none |
| top1_r2_m2_agree | 8 | 0.875 | [0.579, 1.171] | [0.625, 1.000] | none |
| spearman_rho | 8 | 0.825 | [0.738, 0.912] | [0.750, 0.887] | none |
| kendall_tau | 8 | 0.675 | [0.551, 0.799] | [0.575, 0.775] | none |
| BEE_floor_signed | 8 | 0.170 | [-0.130, 0.470] | [-0.066, 0.401] | none |
| BEE_floor_abs | 8 | 0.316 | [0.134, 0.499] | [0.179, 0.459] | none |
| BEE_floor_rel | 8 | 0.003 | [0.001, 0.004] | [0.002, 0.004] | none |
| G_T_A3 | 8 | 7.066 | [6.647, 7.484] | [6.733, 7.383] | none |
| G_P_A3 | 8 | 4.904 | [4.569, 5.239] | [4.659, 5.172] | none |
| BEE_A3 | 8 | 2.162 | [1.738, 2.586] | [1.846, 2.507] | none |

### Unsplit versions (selection bias shown beside)

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| BEE_signed_unsplit | 8 | 2.029 | [1.690, 2.368] | [1.754, 2.276] | none |
| BEE_abs_unsplit | 8 | 2.029 | [1.690, 2.368] | [1.754, 2.276] | none |
| BEE_rel_unsplit | 8 | 0.018 | [0.015, 0.021] | [0.015, 0.020] | none |
| Regret_unsplit | 8 | 0.007 | [-0.009, 0.023] | [0.000, 0.021] | none |
| Regret_denom_unsplit | 8 | 4.916 | [4.540, 5.292] | [4.650, 5.221] | none |
| Regret_rel_unsplit | 8 | 0.001 | [-0.002, 0.005] | [0.000, 0.004] | none |

## 3. Secondary, belief D300 (truth-assisted offline positive control)

Complete seeds: 8 [4501, 4502, 4503, 4504, 4505, 4506, 4507, 4508] (common complete seeds for paired comparisons).

| Seed | a* (R1) | Oracle (M1) | Top-1 | G_T(a*) | G_P(a*) | BEE signed | BEE abs | BEE rel | Regret | Regret denom | Regret rel | Spearman | Kendall | Floor (abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4501 | A3 | A3 | 1 | 0.703 | 4.451 | -3.748 | 3.748 | 0.0328 | 0.000 | 4.451 | 0.0000 | -0.300 | -0.200 | 0.417 |
| 4502 | A3 | A3 | 1 | -0.056 | 4.564 | -4.620 | 4.620 | 0.0393 | 0.000 | 4.564 | 0.0000 | -0.600 | -0.400 | 0.066 |
| 4503 | A3 | A3 | 1 | -0.101 | 4.669 | -4.770 | 4.770 | 0.0432 | 0.000 | 4.669 | 0.0000 | -0.500 | -0.200 | 0.198 |
| 4504 | A3 | A3 | 1 | -0.007 | 5.573 | -5.579 | 5.579 | 0.0476 | 0.000 | 5.573 | 0.0000 | -0.200 | -0.200 | 0.050 |
| 4505 | A1 | A3 | 0 | -0.021 | -0.076 | 0.055 | 0.055 | 0.0005 | 5.169 | 5.093 | 1.0149 | 0.200 | 0.200 | 0.601 |
| 4506 | A3 | A3 | 1 | 1.051 | 5.348 | -4.297 | 4.297 | 0.0369 | 0.000 | 5.348 | 0.0000 | 0.000 | -0.200 | 0.612 |
| 4507 | A0 | A3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0000 | 4.647 | 4.647 | 1.0000 | -0.700 | -0.600 | 0.235 |
| 4508 | A0 | A4 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0000 | 4.619 | 4.619 | 1.0000 | -0.700 | -0.600 | 0.349 |

### Pooled over seeds

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| G_T_hat | 8 | 0.196 | [-0.165, 0.557] | [-0.040, 0.507] | none |
| G_P | 8 | 3.066 | [0.902, 5.230] | [1.239, 4.679] | none |
| BEE_signed | 8 | -2.870 | [-4.914, -0.826] | [-4.399, -1.160] | none |
| BEE_abs | 8 | 2.884 | [0.855, 4.912] | [1.188, 4.399] | none |
| BEE_rel | 8 | 0.025 | [0.007, 0.043] | [0.010, 0.038] | none |
| BEE_signed_rel | 8 | -0.025 | [-0.043, -0.007] | [-0.038, -0.010] | none |
| BEE_signed_unsplit | 8 | -2.253 | [-4.304, -0.202] | [-3.894, -0.572] | none |
| BEE_abs_unsplit | 8 | 2.305 | [0.301, 4.309] | [0.660, 3.908] | none |
| BEE_rel_unsplit | 8 | 0.020 | [0.003, 0.038] | [0.006, 0.034] | none |
| Regret | 8 | 1.804 | [-0.282, 3.891] | [0.000, 3.602] | none |
| Regret_denom | 8 | 4.870 | [4.525, 5.216] | [4.624, 5.151] | none |
| Regret_rel | 8 | 0.377 | [-0.058, 0.812] | [0.000, 0.754] | none |
| Regret_unsplit | 8 | 2.359 | [0.257, 4.461] | [0.599, 4.072] | none |
| Regret_denom_unsplit | 8 | 4.916 | [4.540, 5.292] | [4.650, 5.221] | none |
| Regret_rel_unsplit | 8 | 0.497 | [0.055, 0.939] | [0.127, 0.867] | none |
| top1_agree | 8 | 0.625 | [0.192, 1.058] | [0.250, 1.000] | none |
| top1_r2_m2_agree | 8 | 0.250 | [-0.137, 0.637] | [0.000, 0.625] | none |
| spearman_rho | 8 | -0.350 | [-0.629, -0.071] | [-0.562, -0.125] | none |
| kendall_tau | 8 | -0.275 | [-0.493, -0.057] | [-0.450, -0.100] | none |
| BEE_floor_signed | 8 | 0.170 | [-0.130, 0.470] | [-0.066, 0.401] | none |
| BEE_floor_abs | 8 | 0.316 | [0.134, 0.499] | [0.179, 0.459] | none |
| BEE_floor_rel | 8 | 0.003 | [0.001, 0.004] | [0.002, 0.004] | none |
| G_T_A3 | 8 | 0.212 | [-0.175, 0.599] | [-0.066, 0.535] | none |
| G_P_A3 | 8 | 4.904 | [4.569, 5.239] | [4.659, 5.172] | none |
| BEE_A3 | 8 | -4.692 | [-5.133, -4.251] | [-5.032, -4.340] | none |

### Unsplit versions (selection bias shown beside)

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| BEE_signed_unsplit | 8 | -2.253 | [-4.304, -0.202] | [-3.894, -0.572] | none |
| BEE_abs_unsplit | 8 | 2.305 | [0.301, 4.309] | [0.660, 3.908] | none |
| BEE_rel_unsplit | 8 | 0.020 | [0.003, 0.038] | [0.006, 0.034] | none |
| Regret_unsplit | 8 | 2.359 | [0.257, 4.461] | [0.599, 4.072] | none |
| Regret_denom_unsplit | 8 | 4.916 | [4.540, 5.292] | [4.650, 5.221] | none |
| Regret_rel_unsplit | 8 | 0.497 | [0.055, 0.939] | [0.127, 0.867] | none |

## 4. Fixed-A3 gain (R2 under B and D300 vs G_P(A3) on M2)

- **B**: G_T_A3 = 7.066 [6.647, 7.484]; G_P_A3 = 4.904 [4.569, 5.239]; BEE_A3 = 2.162 [1.738, 2.586]
- **D300**: G_T_A3 = 0.212 [-0.175, 0.599]; G_P_A3 = 4.904 [4.569, 5.239]; BEE_A3 = -4.692 [-5.133, -4.251]

## 5. v2 paired CRN (corr(a), VR(a))

Each world contributes only the seeds whose own grid validated as complete; N and the exclusions are reported per world, and no row is silently deduplicated.

### Belief B

| World | N seeds | Rows | Median corr | Median VR | Pooled median corr | Pooled median VR | Exclusions |
|---|---|---|---|---|---|---|---|
| twin | 8 | 240 | A1 0.9244, A2 0.9240, A3 0.8601, A4 0.9217 | A1 0.9211, A2 0.9235, A3 0.8531, A4 0.8562 | 0.9190 | 0.9024 | none |
| proxy | 8 | 240 | A1 0.9971, A2 0.9968, A3 0.9938, A4 0.9913 | A1 0.9947, A2 0.9964, A3 0.9900, A4 0.9840 | 0.9954 | 0.9937 | none |
| calibration | 8 | 240 | A1 0.9975, A2 0.9965, A3 0.9926, A4 0.9889 | A1 0.9968, A2 0.9959, A3 0.9913, A4 0.9867 | 0.9940 | 0.9924 | none |

### Belief D300

| World | N seeds | Rows | Median corr | Median VR | Pooled median corr | Pooled median VR | Exclusions |
|---|---|---|---|---|---|---|---|
| twin | 8 | 240 | A1 0.9573, A2 0.9299, A3 0.9497, A4 0.9200 | A1 0.9471, A2 0.9284, A3 0.9121, A4 0.8814 | 0.9429 | 0.9285 | none |
| proxy | 8 | 240 | A1 0.9971, A2 0.9968, A3 0.9938, A4 0.9913 | A1 0.9947, A2 0.9964, A3 0.9900, A4 0.9840 | 0.9954 | 0.9937 | none |
| calibration | 8 | 240 | A1 0.9975, A2 0.9965, A3 0.9926, A4 0.9889 | A1 0.9968, A2 0.9959, A3 0.9913, A4 0.9867 | 0.9940 | 0.9924 | none |

## 6. State history (descriptive only, no gating)

- 16 snapshot rows; identical displayed rows collapsed. Pending counts that are unavailable are shown as unknown, never as zero.
- descriptive only; incident history: Proxy active since 4,500 s, Twin none (CONV)

| seed | world | incident_history | ktb_w1 | ktb_w2 | ktb_w3 | ktb_n1 | tko_vms | tko_1 | tko_in | tko_insert | on_ktb_w1 | on_tko_vms | on_tko_1 | ms_on_ktb_w2 | on_ktb_w3 | on_ktb_n1 | pending_q | Q | ktb_n1_all_veh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4501 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 171 |
| 4501 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 43 |
| 4502 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 186 |
| 4502 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 |
| 4503 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 161 |
| 4503 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 38 |
| 4504 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 184 |
| 4504 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 |
| 4505 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 194 |
| 4505 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 33 |
| 4506 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 194 |
| 4506 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30 |
| 4507 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 180 |
| 4507 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 39 |
| 4508 | proxy | incident active since 4,500 s | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 184 |
| 4508 | twin | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27 |

## 7. RNG isolation check (binding enforced before metrics)

- passed: True

No interval is reported for N < 2; no acceptance threshold applies.

