# Frozen offline decision audit: analysis

Input: `results\frozen_audit_smoke\analyzer_selftest`

Seeds: [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208] (N = 8). Decision time t_d = 5,100 s; horizon 900 s; J = total time spent (veh.h).

## Claim boundary

> This is a confirmation of a laboratory, scenario-specific result: one corridor, one incident type, one decision time, the H_G5 hypothesis world. The submission may report these numbers as such. It may not present them as reliable incident inference, accurate benefit prediction in general, real-world effectiveness, or event-assimilation superiority

- The development audit's numbers (seeds 4201-4208) stay reported unchanged beside these, never pooled.
- The calibration floor is reported beside BEE; it is never subtracted from BEE and no causal-gap interpretation is made.

## 1. Validation

### Belief B

- **twin**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none
- **proxy**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none
- **calibration**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none

### Belief D300

- **twin**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none
- **proxy**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none
- **calibration**: 8/8 complete seeds [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208]; exclusions: none

## 2. Primary, belief B

Complete seeds: 8 [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208] (common complete seeds for paired comparisons).

| Seed | a* (R1) | Oracle (M1) | Top-1 | G_T(a*) | G_P(a*) | BEE signed | BEE abs | BEE rel | Regret | Regret denom | Regret rel | Spearman | Kendall | Floor (abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 1 | 7.048 | 5.123 | 1.925 | 1.925 | 0.0170 | 0.000 | 5.123 | 0.0000 | 0.900 | 0.800 | 0.150 |
| 4202 | A3 | A3 | 1 | 6.172 | 4.518 | 1.655 | 1.655 | 0.0147 | 0.000 | 4.518 | 0.0000 | 0.900 | 0.800 | 0.021 |
| 4203 | A3 | A3 | 1 | 6.350 | 5.081 | 1.269 | 1.269 | 0.0109 | 0.000 | 5.081 | 0.0000 | 0.700 | 0.600 | 0.327 |
| 4204 | A3 | A3 | 1 | 6.625 | 6.433 | 0.192 | 0.192 | 0.0016 | 0.000 | 6.433 | 0.0000 | 0.900 | 0.800 | 0.092 |
| 4205 | A3 | A3 | 1 | 7.110 | 4.842 | 2.268 | 2.268 | 0.0200 | 0.000 | 4.842 | 0.0000 | 0.800 | 0.600 | 0.219 |
| 4206 | A3 | A3 | 1 | 7.286 | 5.228 | 2.058 | 2.058 | 0.0184 | 0.000 | 5.228 | 0.0000 | 1.000 | 1.000 | 0.117 |
| 4207 | A3 | A3 | 1 | 6.482 | 5.150 | 1.332 | 1.332 | 0.0117 | 0.000 | 5.150 | 0.0000 | 0.900 | 0.800 | 0.144 |
| 4208 | A3 | A4 | 0 | 6.986 | 4.631 | 2.354 | 2.354 | 0.0201 | 0.232 | 4.863 | 0.0477 | 0.700 | 0.600 | 0.378 |

### Pooled over seeds

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| G_T_hat | 8 | 6.757 | [6.420, 7.095] | [6.498, 7.017] | none |
| G_P | 8 | 5.126 | [4.635, 5.617] | [4.806, 5.549] | none |
| BEE_signed | 8 | 1.632 | [1.041, 2.222] | [1.141, 2.050] | none |
| BEE_abs | 8 | 1.632 | [1.041, 2.222] | [1.141, 2.050] | none |
| BEE_rel | 8 | 0.014 | [0.009, 0.020] | [0.010, 0.018] | none |
| BEE_signed_rel | 8 | 0.014 | [0.009, 0.020] | [0.010, 0.018] | none |
| BEE_signed_unsplit | 8 | 1.739 | [1.176, 2.303] | [1.292, 2.172] | none |
| BEE_abs_unsplit | 8 | 1.739 | [1.176, 2.303] | [1.292, 2.172] | none |
| BEE_rel_unsplit | 8 | 0.015 | [0.010, 0.020] | [0.011, 0.019] | none |
| Regret | 8 | 0.029 | [-0.040, 0.098] | [0.000, 0.087] | none |
| Regret_denom | 8 | 5.155 | [4.682, 5.627] | [4.854, 5.567] | none |
| Regret_rel | 8 | 0.006 | [-0.008, 0.020] | [0.000, 0.018] | none |
| Regret_unsplit | 8 | 0.081 | [-0.110, 0.272] | [0.000, 0.242] | none |
| Regret_denom_unsplit | 8 | 5.150 | [4.731, 5.570] | [4.870, 5.503] | none |
| Regret_rel_unsplit | 8 | 0.015 | [-0.021, 0.052] | [0.000, 0.046] | none |
| top1_agree | 8 | 0.875 | [0.579, 1.171] | [0.625, 1.000] | none |
| top1_r2_m2_agree | 8 | 0.750 | [0.363, 1.137] | [0.375, 1.000] | none |
| spearman_rho | 8 | 0.850 | [0.761, 0.939] | [0.775, 0.912] | none |
| kendall_tau | 8 | 0.750 | [0.632, 0.868] | [0.650, 0.850] | none |
| BEE_floor_signed | 8 | 0.152 | [0.018, 0.285] | [0.048, 0.252] | none |
| BEE_floor_abs | 8 | 0.181 | [0.080, 0.281] | [0.107, 0.261] | none |
| BEE_floor_rel | 8 | 0.002 | [0.001, 0.002] | [0.001, 0.002] | none |
| G_T_A3 | 8 | 6.757 | [6.420, 7.095] | [6.498, 7.017] | none |
| G_P_A3 | 8 | 5.126 | [4.635, 5.617] | [4.806, 5.549] | none |
| BEE_A3 | 8 | 1.632 | [1.041, 2.222] | [1.141, 2.050] | none |

### Unsplit versions (selection bias shown beside)

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| BEE_signed_unsplit | 8 | 1.739 | [1.176, 2.303] | [1.292, 2.172] | none |
| BEE_abs_unsplit | 8 | 1.739 | [1.176, 2.303] | [1.292, 2.172] | none |
| BEE_rel_unsplit | 8 | 0.015 | [0.010, 0.020] | [0.011, 0.019] | none |
| Regret_unsplit | 8 | 0.081 | [-0.110, 0.272] | [0.000, 0.242] | none |
| Regret_denom_unsplit | 8 | 5.150 | [4.731, 5.570] | [4.870, 5.503] | none |
| Regret_rel_unsplit | 8 | 0.015 | [-0.021, 0.052] | [0.000, 0.046] | none |

## 3. Secondary, belief D300 (truth-assisted offline positive control)

Complete seeds: 8 [4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208] (common complete seeds for paired comparisons).

| Seed | a* (R1) | Oracle (M1) | Top-1 | G_T(a*) | G_P(a*) | BEE signed | BEE abs | BEE rel | Regret | Regret denom | Regret rel | Spearman | Kendall | Floor (abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A1 | A3 | 0 | -0.141 | 0.116 | -0.257 | 0.257 | 0.0023 | 5.007 | 5.123 | 0.9773 | 0.100 | 0.000 | 0.150 |
| 4202 | A1 | A3 | 0 | 0.130 | -0.312 | 0.442 | 0.442 | 0.0039 | 4.830 | 4.518 | 1.0691 | -0.400 | -0.400 | 0.021 |
| 4203 | A3 | A3 | 1 | -0.083 | 5.081 | -5.164 | 5.164 | 0.0442 | 0.000 | 5.081 | 0.0000 | -0.500 | -0.400 | 0.327 |
| 4204 | A3 | A3 | 1 | 0.534 | 6.433 | -5.900 | 5.900 | 0.0483 | 0.000 | 6.433 | 0.0000 | 0.100 | 0.000 | 0.092 |
| 4205 | A0 | A3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0000 | 4.842 | 4.842 | 1.0000 | 0.000 | -0.200 | 0.219 |
| 4206 | A3 | A3 | 1 | -0.012 | 5.228 | -5.241 | 5.241 | 0.0470 | 0.000 | 5.228 | 0.0000 | -0.600 | -0.400 | 0.117 |
| 4207 | A3 | A3 | 1 | -0.047 | 5.150 | -5.198 | 5.198 | 0.0456 | 0.000 | 5.150 | 0.0000 | -0.200 | -0.200 | 0.144 |
| 4208 | A3 | A4 | 0 | 0.456 | 4.631 | -4.175 | 4.175 | 0.0356 | 0.232 | 4.863 | 0.0477 | -0.400 | -0.400 | 0.378 |

### Pooled over seeds

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| G_T_hat | 8 | 0.104 | [-0.108, 0.317] | [-0.044, 0.279] | none |
| G_P | 8 | 3.291 | [0.927, 5.655] | [1.330, 5.003] | none |
| BEE_signed | 8 | -3.187 | [-5.474, -0.899] | [-4.832, -1.300] | none |
| BEE_abs | 8 | 3.297 | [1.138, 5.456] | [1.512, 4.845] | none |
| BEE_rel | 8 | 0.028 | [0.010, 0.047] | [0.013, 0.041] | none |
| BEE_signed_rel | 8 | -0.027 | [-0.047, -0.008] | [-0.041, -0.011] | none |
| BEE_signed_unsplit | 8 | -3.522 | [-5.580, -1.464] | [-4.948, -1.734] | none |
| BEE_abs_unsplit | 8 | 3.704 | [1.919, 5.488] | [2.184, 4.948] | none |
| BEE_rel_unsplit | 8 | 0.032 | [0.017, 0.047] | [0.019, 0.043] | none |
| Regret | 8 | 1.864 | [-0.235, 3.962] | [0.604, 3.670] | none |
| Regret_denom | 8 | 5.155 | [4.682, 5.627] | [4.854, 5.567] | none |
| Regret_rel | 8 | 0.387 | [-0.049, 0.823] | [0.122, 0.759] | none |
| Regret_unsplit | 8 | 1.309 | [-0.562, 3.181] | [0.081, 3.003] | none |
| Regret_denom_unsplit | 8 | 5.150 | [4.731, 5.570] | [4.870, 5.503] | none |
| Regret_rel_unsplit | 8 | 0.273 | [-0.120, 0.666] | [0.015, 0.637] | none |
| top1_agree | 8 | 0.500 | [0.053, 0.947] | [0.125, 0.875] | none |
| top1_r2_m2_agree | 8 | 0.375 | [-0.058, 0.808] | [0.125, 0.750] | none |
| spearman_rho | 8 | -0.237 | [-0.469, -0.006] | [-0.412, -0.062] | none |
| kendall_tau | 8 | -0.250 | [-0.398, -0.102] | [-0.350, -0.125] | none |
| BEE_floor_signed | 8 | 0.152 | [0.018, 0.285] | [0.048, 0.252] | none |
| BEE_floor_abs | 8 | 0.181 | [0.080, 0.281] | [0.107, 0.261] | none |
| BEE_floor_rel | 8 | 0.002 | [0.001, 0.002] | [0.001, 0.002] | none |
| G_T_A3 | 8 | 0.179 | [-0.023, 0.380] | [0.028, 0.336] | none |
| G_P_A3 | 8 | 5.126 | [4.635, 5.617] | [4.806, 5.549] | none |
| BEE_A3 | 8 | -4.947 | [-5.403, -4.491] | [-5.298, -4.603] | none |

### Unsplit versions (selection bias shown beside)

| Metric | N | Mean | Paired t 95% CI | Percentile bootstrap 95% CI | Exclusions |
|---|---|---|---|---|---|
| BEE_signed_unsplit | 8 | -3.522 | [-5.580, -1.464] | [-4.948, -1.734] | none |
| BEE_abs_unsplit | 8 | 3.704 | [1.919, 5.488] | [2.184, 4.948] | none |
| BEE_rel_unsplit | 8 | 0.032 | [0.017, 0.047] | [0.019, 0.043] | none |
| Regret_unsplit | 8 | 1.309 | [-0.562, 3.181] | [0.081, 3.003] | none |
| Regret_denom_unsplit | 8 | 5.150 | [4.731, 5.570] | [4.870, 5.503] | none |
| Regret_rel_unsplit | 8 | 0.273 | [-0.120, 0.666] | [0.015, 0.637] | none |

## 4. Fixed-A3 gain (R2 under B and D300 vs G_P(A3) on M2)

- **B**: G_T_A3 = 6.757 [6.420, 7.095]; G_P_A3 = 5.126 [4.635, 5.617]; BEE_A3 = 1.632 [1.041, 2.222]
- **D300**: G_T_A3 = 0.179 [-0.023, 0.380]; G_P_A3 = 5.126 [4.635, 5.617]; BEE_A3 = -4.947 [-5.403, -4.491]

## 5. v2 paired CRN (corr(a), VR(a))

| Belief | World | Median corr | Median VR | Pooled median corr | Pooled median VR |
|---|---|---|---|---|---|
| B | twin | A1 0.8835, A2 0.9082, A3 0.9299, A4 0.8925 | A1 0.8759, A2 0.9071, A3 0.9133, A4 0.8894 | 0.9027 | 0.8982 |
| B | proxy | A1 0.9940, A2 0.9897, A3 0.9938, A4 0.9888 | A1 0.9940, A2 0.9893, A3 0.9937, A4 0.9863 | 0.9927 | 0.9917 |
| B | calibration | A1 0.9974, A2 0.9931, A3 0.9951, A4 0.9880 | A1 0.9965, A2 0.9920, A3 0.9944, A4 0.9875 | 0.9939 | 0.9925 |
| D300 | twin | A1 0.9523, A2 0.9727, A3 0.9795, A4 0.9513 | A1 0.9376, A2 0.9695, A3 0.9657, A4 0.9421 | 0.9631 | 0.9481 |
| D300 | proxy | A1 0.9940, A2 0.9897, A3 0.9938, A4 0.9888 | A1 0.9940, A2 0.9893, A3 0.9937, A4 0.9863 | 0.9927 | 0.9917 |
| D300 | calibration | A1 0.9974, A2 0.9931, A3 0.9951, A4 0.9880 | A1 0.9965, A2 0.9920, A3 0.9944, A4 0.9875 | 0.9939 | 0.9925 |

## 6. State history (descriptive only, no gating)

- 104 snapshot rows; identical displayed rows collapsed. Pending counts that are unavailable are shown as unknown, never as zero.
- descriptive only; incident history: Proxy active since 4,500 s, Twin none (CONV)

| world | belief | seed | replication | t | halted_q | halted_upstream | blocker_halted | pending_total | pending_q | Q | blocker_edge | blocker_pos_0 | blocker_pos_1 | actual_clear_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| twin | B | 4201 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4201 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4201 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4201 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4201 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4201 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4202 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4203 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4204 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4205 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4206 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4207 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | B | 4208 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| twin | D300 | 4201 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4201 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4201 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4201 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4201 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4201 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4202 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.29 | 5400.00 |
| twin | D300 | 4202 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.30 | 5400.00 |
| twin | D300 | 4202 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4202 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4202 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4202 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4203 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4203 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.30 | 5400.00 |
| twin | D300 | 4203 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4203 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.30 | 5400.00 |
| twin | D300 | 4203 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.26 | 5400.00 |
| twin | D300 | 4203 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4204 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4204 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.27 | 5400.00 |
| twin | D300 | 4204 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.28 | 5400.00 |
| twin | D300 | 4204 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.26 | 755.27 | 5400.00 |
| twin | D300 | 4204 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4204 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.28 | 5400.00 |
| twin | D300 | 4205 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.29 | 5400.00 |
| twin | D300 | 4205 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4205 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4205 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.27 | 5400.00 |
| twin | D300 | 4205 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4205 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.27 | 755.29 | 5400.00 |
| twin | D300 | 4206 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4206 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.27 | 755.29 | 5400.00 |
| twin | D300 | 4206 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.29 | 5400.00 |
| twin | D300 | 4206 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4206 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4206 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4207 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.27 | 755.30 | 5400.00 |
| twin | D300 | 4207 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4207 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4207 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.29 | 5400.00 |
| twin | D300 | 4207 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.30 | 5400.00 |
| twin | D300 | 4207 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.30 | 5400.00 |
| twin | D300 | 4208 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4208 | 2 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4208 | 3 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| twin | D300 | 4208 | 4 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.28 | 755.28 | 5400.00 |
| twin | D300 | 4208 | 5 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.30 | 755.29 | 5400.00 |
| twin | D300 | 4208 | 6 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 755.29 | 755.29 | 5400.00 |
| proxy | B | 4201 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4202 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4203 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4204 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4205 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4206 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4207 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |
| proxy | B | 4208 | 1 | 5100.00 | unknown | unknown | 2 | unknown | unknown | unknown | ktb_n1 | 900.00 | 900.00 | 5400.00 |

## 7. RNG isolation check (descriptive)

- passed: True

No interval is reported for N < 2; no acceptance threshold applies.

