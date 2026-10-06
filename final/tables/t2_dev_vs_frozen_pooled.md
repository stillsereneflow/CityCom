Sources, side by side and never pooled. Development audit (seeds 4201-4208): belief B read from `results/audit/v2/metrics_v2.json` (`pooled`, `per_seed`), which has the pooled values; its G_T_hat/G_P/G_T_A3/G_P_A3 are not in that pooled block and are recomputed from `results/audit/raw.parquet` with the `docs/oct6-audit-and-pilot2-plan.md` part A definitions (the recomputation reproduces every overlapping metrics_v2 pooled value to < 1e-6). Development D300: recomputed from `results/audit/sens/raw_sens.parquet` (variant D300) with the same definitions; it reproduces `results/audit/sens/metrics_sens.json` variants.D300 per-seed values and pooled means exactly (max |mean diff| 7e-15), while the pooled t-CI bounds agree to 2.4e-7 (the sens report's t multiplier differs in the 8th digit). Frozen test audit (seeds 4501-4508): `results/frozen_audit/metrics.json` `primary.pooled` (B) and `secondary.pooled` (D300). The calibration floor uses the shared calibration branches, so its value is identical for B and D300. 'difference (frozen - dev)' is the difference of the two means only, descriptive, no test. G_T_hat(a*) equals the fixed-A3 G_T_hat under belief B because a* = A3 for all 16 B seeds (dev and frozen). Top-1 agreement is a per-seed yes/no indicator, so it is reported as the exact count k/8 with n/a interval and difference cells (a t-CI on a 0/1 proportion is not meaningful and can exceed 1). N = 8 seeds per audit column; 95 % t-CI over seeds (not for Top-1).

| belief | metric | dev mean | dev CI95 low | dev CI95 high | frozen mean | frozen CI95 low | frozen CI95 high | difference (frozen - dev) [descriptive] |
|---|---|---|---|---|---|---|---|---|
| B (primary) | a* distribution (per seed) | A3 8/8 | n/a | n/a | A3 8/8 | n/a | n/a | n/a |
| B (primary) | oracle distribution (per seed) | A3 7/8; A4 1/8 | n/a | n/a | A3 7/8; A4 1/8 | n/a | n/a | n/a |
| B (primary) | oracle agreement Top-1 | 7/8 | n/a | n/a | 7/8 | n/a | n/a | n/a |
| B (primary) | G_T_hat(a*) (veh.h) | 6.757 | 6.420 | 7.095 | 7.066 | 6.647 | 7.484 | 0.308 |
| B (primary) | G_P(a*) (veh.h) | 5.126 | 4.635 | 5.617 | 4.904 | 4.569 | 5.239 | -0.222 |
| B (primary) | BEE signed (veh.h) | 1.632 | 1.041 | 2.222 | 2.162 | 1.738 | 2.586 | 0.530 |
| B (primary) | \|BEE\| (veh.h) | 1.632 | 1.041 | 2.222 | 2.162 | 1.738 | 2.586 | 0.530 |
| B (primary) | BEE_rel (\|BEE\| / J_P(A0)) | 0.014 | 0.009 | 0.020 | 0.019 | 0.015 | 0.023 | 0.005 |
| B (primary) | Regret (veh.h) | 0.029 | -0.040 | 0.098 | -0.034 | -0.113 | 0.046 | -0.063 |
| B (primary) | Regret_rel (split denominator) | 0.006 | -0.008 | 0.020 | -0.007 | -0.024 | 0.010 | -0.013 |
| B (primary) | Spearman rho | 0.850 | 0.761 | 0.939 | 0.825 | 0.738 | 0.912 | -0.025 |
| B (primary) | Kendall tau | 0.750 | 0.632 | 0.868 | 0.675 | 0.551 | 0.799 | -0.075 |
| B (primary) | calibration floor \|BEE\| (veh.h) | 0.181 | 0.080 | 0.281 | 0.316 | 0.134 | 0.499 | 0.135 |
| B (primary) | fixed-A3 G_T_hat (veh.h) | 6.757 | 6.420 | 7.095 | 7.066 | 6.647 | 7.484 | 0.308 |
| B (primary) | fixed-A3 G_P (veh.h) | 5.126 | 4.635 | 5.617 | 4.904 | 4.569 | 5.239 | -0.222 |
| D300 (secondary) | a* distribution (per seed) | A0 1/8; A1 2/8; A3 5/8 | n/a | n/a | A0 2/8; A1 1/8; A3 5/8 | n/a | n/a | n/a |
| D300 (secondary) | oracle distribution (per seed) | A3 7/8; A4 1/8 | n/a | n/a | A3 7/8; A4 1/8 | n/a | n/a | n/a |
| D300 (secondary) | oracle agreement Top-1 | 4/8 | n/a | n/a | 5/8 | n/a | n/a | n/a |
| D300 (secondary) | G_T_hat(a*) (veh.h) | 0.104 | -0.108 | 0.317 | 0.196 | -0.165 | 0.557 | 0.092 |
| D300 (secondary) | G_P(a*) (veh.h) | 3.291 | 0.927 | 5.655 | 3.066 | 0.902 | 5.230 | -0.225 |
| D300 (secondary) | BEE signed (veh.h) | -3.187 | -5.474 | -0.899 | -2.870 | -4.914 | -0.826 | 0.317 |
| D300 (secondary) | \|BEE\| (veh.h) | 3.297 | 1.138 | 5.456 | 2.884 | 0.855 | 4.912 | -0.413 |
| D300 (secondary) | BEE_rel (\|BEE\| / J_P(A0)) | 0.028 | 0.010 | 0.047 | 0.025 | 0.007 | 0.043 | -0.003 |
| D300 (secondary) | Regret (veh.h) | 1.864 | -0.235 | 3.962 | 1.804 | -0.282 | 3.891 | -0.060 |
| D300 (secondary) | Regret_rel (split denominator) | 0.387 | -0.049 | 0.823 | 0.377 | -0.058 | 0.812 | -0.010 |
| D300 (secondary) | Spearman rho | -0.237 | -0.469 | -0.006 | -0.350 | -0.629 | -0.071 | -0.112 |
| D300 (secondary) | Kendall tau | -0.250 | -0.398 | -0.102 | -0.275 | -0.493 | -0.057 | -0.025 |
| D300 (secondary) | calibration floor \|BEE\| (veh.h) | 0.181 | 0.080 | 0.281 | 0.316 | 0.134 | 0.499 | 0.135 |
| D300 (secondary) | fixed-A3 G_T_hat (veh.h) | 0.179 | -0.023 | 0.380 | 0.212 | -0.175 | 0.599 | 0.033 |
| D300 (secondary) | fixed-A3 G_P (veh.h) | 5.126 | 4.635 | 5.617 | 4.904 | 4.569 | 5.239 | -0.222 |
