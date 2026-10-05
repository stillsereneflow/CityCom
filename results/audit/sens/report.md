MODEL: Gemini 3.8 Flash (High)

# Preregistered Offline Decision Audit Sensitivity Report

This report documents the preregistered one-factor offline sensitivity analysis for the decision audit, as specified in `docs/oct8-audit-sensitivity-plan.md` (0401a9c) and `prompt.md`.
The objective is to measure how decision fidelity metrics ($a^*$, BEE, regret, and ranking agreement) move when exactly **one** element of the Twin's belief is varied from the baseline $B$, holding the Proxy and calibration worlds identical.

Per preregistration, this is an observational measurement with no acceptance criteria. Contrasts with the baseline are reported **without multiplicity correction**; they are strictly uncorrected, and no significance claims are made. Variants **D300** and **P900** are designated as **truth-assisted offline positive controls**.

## 1. Baseline Compatibility Replay Check (Blocking Rule 2)

Before collecting sensitivity contrasts, the modified worker with explicit per-job overrides was tested against frozen inputs using default baseline overrides (`hyp_pos=755.3`, `hyp_clear_time=None`, `branch_factor=None`).
Tested grid: Seed 4201 across all 6 replications $\times$ 5 actions (30 runs), plus replication 1 $\times$ 5 actions for seeds 4202–4208 (35 runs). Total: **65 runs**.

- **Overall Status**: **PASSED**
- **Total Checked**: 65
- **Total Matched (J and vehicle digest)**: 65 / 65 (100.0%)
- **Mismatches**: 0
- **Wall Time**: 31.8 s
- **Data File**: `results/audit/sens/baseline_check.json`

### Baseline Check Verification Summary (Sample)
| Seed | Rep | Action | Stored $J$ | Replayed $J$ | $J$ Match | Stored Digest (Prefix) | Replayed Digest (Prefix) | Digest Match |
|---|---|---|---|---|---|---|---|---|
| 4201 | 1 | A0 | 97.9372 | 97.9372 | YES | `c0eeacf585...` | `c0eeacf585...` | YES |
| 4201 | 1 | A1 | 98.2203 | 98.2203 | YES | `a410bb4345...` | `a410bb4345...` | YES |
| 4201 | 1 | A2 | 93.6369 | 93.6369 | YES | `03745fad27...` | `03745fad27...` | YES |
| 4201 | 1 | A3 | 91.5706 | 91.5706 | YES | `034b792f90...` | `034b792f90...` | YES |
| 4201 | 1 | A4 | 92.8067 | 92.8067 | YES | `f9e4d06647...` | `f9e4d06647...` | YES |
| 4201 | 2 | A0 | 97.7100 | 97.7100 | YES | `aaefe2f784...` | `aaefe2f784...` | YES |
| 4201 | 2 | A1 | 96.8397 | 96.8397 | YES | `9c75cdfdfd...` | `9c75cdfdfd...` | YES |
| 4201 | 2 | A2 | 93.1756 | 93.1756 | YES | `aff7f1efaf...` | `aff7f1efaf...` | YES |
| 4201 | 2 | A3 | 91.2642 | 91.2642 | YES | `d06a654404...` | `d06a654404...` | YES |
| 4201 | 2 | A4 | 92.1625 | 92.1625 | YES | `cf9c91cb05...` | `cf9c91cb05...` | YES |
| ... | ... | ... | ... | ... | ... | (55 more rows verified) | ... | ... |

## 2. Actual Blocker Placement and Clearance Verification

Blocking rule 1 requires recording actual blocker placement (edge, lane, pos, time stopped) and actual clearance time in each branch. Both lanes (0 and 1) of `ktb_n1` were blocked at the target position, and D300/D600 cleared via explicit TraCI resume at absolute simulation times 5,400 s and 5,700 s respectively.

| Variant | Factor / Description | Target Pos (m) | Lane 0 Stopped Pos / Time | Lane 1 Stopped Pos / Time | Target Clear $t$ (s) | Actual Clearance Time(s) |
|---|---|---|---|---|---|---|
| **D300** | truth-assisted offline positive control | 755.3 | 755.29 m @ 5105.8 s | 755.29 m @ 5104.1 s | 5400.0 s | 5400.0 s |
| **D600** | sensitivity | 755.3 | 755.29 m @ 5105.8 s | 755.29 m @ 5104.1 s | 5700.0 s | 5700.0 s |
| **P456** | sensitivity | 456.0 | 455.99 m @ 5110.9 s | 455.99 m @ 5105.0 s | None (persistent) | None (persistent) |
| **P900** | truth-assisted offline positive control | 900.0 | 899.99 m @ 5106.7 s | 899.99 m @ 5104.1 s | None (persistent) | None (persistent) |
| **F100** | sensitivity (the Twin's demand belief) | 755.3 | 755.29 m @ 5105.8 s | 755.29 m @ 5104.1 s | None (persistent) | None (persistent) |

## 3. Decision Audit Results by Variant

Audit metrics are computed per seed over complete grids (5 actions $\times$ 6 replications), then pooled over 8 seeds.

### Variant **Baseline B** (as run)
- **Factor**: none
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 7.05 | 5.12 | +1.92 | 1.92 | 1.7% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4202 | A3 | A3 | 6.17 | 4.52 | +1.65 | 1.65 | 1.5% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4203 | A3 | A3 | 6.35 | 5.08 | +1.27 | 1.27 | 1.1% | 0.00 | 0.0% | 1 | 0.700 | 0.600 |
| 4204 | A3 | A3 | 6.63 | 6.43 | +0.19 | 0.19 | 0.2% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4205 | A3 | A3 | 7.11 | 4.84 | +2.27 | 2.27 | 2.0% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4206 | A3 | A3 | 7.29 | 5.23 | +2.06 | 2.06 | 1.8% | 0.00 | 0.0% | 1 | 1.000 | 1.000 |
| 4207 | A3 | A3 | 6.48 | 5.15 | +1.33 | 1.33 | 1.2% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4208 | A3 | A4 | 6.99 | 4.63 | +2.35 | 2.35 | 2.0% | 0.23 | 4.8% | 0 | 0.700 | 0.600 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | 1.63 | 0.71 | 0.25 | [1.04, 2.22] | [1.14, 2.05] |
| BEE (absolute, veh·h) | 1.63 | 0.71 | 0.25 | [1.04, 2.22] | [1.13, 2.05] |
| BEE (relative) | 1.4% | 0.6% | 0.2% | [0.9%, 2.0%] | [1.0%, 1.8%] |
| Regret (veh·h) | 0.03 | 0.08 | 0.03 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (relative) | 0.6% | 1.7% | 0.6% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | 12.5% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | 16.4% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.850 | 0.107 | 0.038 | [0.761, 0.939] | [0.775, 0.912] |
| Kendall Tau Correlation $\tau$ | 0.750 | 0.141 | 0.050 | [0.632, 0.868] | [0.650, 0.850] |

### Variant **D300** (truth-assisted offline positive control)
- **Factor**: blockage duration from t_d = 300 s (ends at 5,400 s)
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A1 | A3 | -0.14 | 0.12 | -0.26 | 0.26 | 0.2% | 5.01 | 97.7% | 0 | 0.100 | 0.000 |
| 4202 | A1 | A3 | 0.13 | -0.31 | +0.44 | 0.44 | 0.4% | 4.83 | 106.9% | 0 | -0.400 | -0.400 |
| 4203 | A3 | A3 | -0.08 | 5.08 | -5.16 | 5.16 | 4.4% | 0.00 | 0.0% | 1 | -0.500 | -0.400 |
| 4204 | A3 | A3 | 0.53 | 6.43 | -5.90 | 5.90 | 4.8% | 0.00 | 0.0% | 1 | 0.100 | 0.000 |
| 4205 | A0 | A3 | 0.00 | 0.00 | +0.00 | 0.00 | 0.0% | 4.84 | 100.0% | 0 | 0.000 | -0.200 |
| 4206 | A3 | A3 | -0.01 | 5.23 | -5.24 | 5.24 | 4.7% | 0.00 | 0.0% | 1 | -0.600 | -0.400 |
| 4207 | A3 | A3 | -0.05 | 5.15 | -5.20 | 5.20 | 4.6% | 0.00 | 0.0% | 1 | -0.200 | -0.200 |
| 4208 | A3 | A4 | 0.46 | 4.63 | -4.18 | 4.18 | 3.6% | 0.23 | 4.8% | 0 | -0.400 | -0.400 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | -3.19 | 2.74 | 0.97 | [-5.47, -0.90] | [-4.83, -1.30] |
| BEE (absolute, veh·h) | 3.30 | 2.58 | 0.91 | [1.14, 5.46] | [1.51, 4.89] |
| BEE (relative) | 2.8% | 2.2% | 0.8% | [1.0%, 4.7%] | [1.3%, 4.1%] |
| Regret (veh·h) | 1.86 | 2.51 | 0.89 | [-0.23, 3.96] | [0.60, 3.67] |
| Regret (relative) | 38.7% | 52.2% | 18.4% | [-4.9%, 82.3%] | [12.2%, 75.9%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 50.0% | 53.5% | 18.9% | [5.3%, 94.7%] | [12.5%, 87.5%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 37.5% | 51.8% | 18.3% | [-5.8%, 80.8%] | [12.5%, 75.0%] |
| Spearman Rank Correlation $\rho$ | -0.237 | 0.277 | 0.098 | [-0.469, -0.006] | [-0.412, -0.062] |
| Kendall Tau Correlation $\tau$ | -0.250 | 0.177 | 0.063 | [-0.398, -0.102] | [-0.350, -0.125] |

### Variant **D600** (sensitivity)
- **Factor**: blockage duration from t_d = 600 s (ends at 5,700 s)
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 6.77 | 5.12 | +1.65 | 1.65 | 1.5% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4202 | A3 | A3 | 5.77 | 4.52 | +1.25 | 1.25 | 1.1% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4203 | A3 | A3 | 6.34 | 5.08 | +1.26 | 1.26 | 1.1% | 0.00 | 0.0% | 1 | 0.700 | 0.600 |
| 4204 | A3 | A3 | 6.67 | 6.43 | +0.24 | 0.24 | 0.2% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4205 | A3 | A3 | 7.16 | 4.84 | +2.32 | 2.32 | 2.1% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4206 | A3 | A3 | 7.17 | 5.23 | +1.95 | 1.95 | 1.7% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4207 | A3 | A3 | 6.03 | 5.15 | +0.88 | 0.88 | 0.8% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4208 | A3 | A4 | 7.17 | 4.63 | +2.54 | 2.54 | 2.2% | 0.23 | 4.8% | 0 | 0.600 | 0.400 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | 1.51 | 0.76 | 0.27 | [0.87, 2.15] | [1.01, 2.01] |
| BEE (absolute, veh·h) | 1.51 | 0.76 | 0.27 | [0.87, 2.15] | [1.00, 2.00] |
| BEE (relative) | 1.3% | 0.7% | 0.2% | [0.8%, 1.9%] | [0.9%, 1.8%] |
| Regret (veh·h) | 0.03 | 0.08 | 0.03 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (relative) | 0.6% | 1.7% | 0.6% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | 12.5% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | 16.4% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.825 | 0.116 | 0.041 | [0.728, 0.922] | [0.750, 0.887] |
| Kendall Tau Correlation $\tau$ | 0.700 | 0.151 | 0.053 | [0.574, 0.826] | [0.600, 0.775] |

### Variant **P456** (sensitivity)
- **Factor**: blockage position on ktb_n1 = 456 m (upstream detector AID02109)
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 6.56 | 5.12 | +1.44 | 1.44 | 1.3% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4202 | A3 | A3 | 7.54 | 4.52 | +3.02 | 3.02 | 2.7% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4203 | A3 | A3 | 7.07 | 5.08 | +1.99 | 1.99 | 1.7% | 0.00 | 0.0% | 1 | 0.600 | 0.400 |
| 4204 | A3 | A3 | 6.27 | 6.43 | -0.16 | 0.16 | 0.1% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4205 | A3 | A3 | 6.02 | 4.84 | +1.18 | 1.18 | 1.0% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4206 | A3 | A3 | 7.03 | 5.23 | +1.80 | 1.80 | 1.6% | 0.00 | 0.0% | 1 | 1.000 | 1.000 |
| 4207 | A3 | A3 | 6.30 | 5.15 | +1.15 | 1.15 | 1.0% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4208 | A3 | A4 | 7.80 | 4.63 | +3.17 | 3.17 | 2.7% | 0.23 | 4.8% | 0 | 0.800 | 0.600 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | 1.70 | 1.08 | 0.38 | [0.80, 2.60] | [1.00, 2.37] |
| BEE (absolute, veh·h) | 1.74 | 1.00 | 0.35 | [0.90, 2.57] | [1.10, 2.39] |
| BEE (relative) | 1.5% | 0.9% | 0.3% | [0.8%, 2.2%] | [1.0%, 2.1%] |
| Regret (veh·h) | 0.03 | 0.08 | 0.03 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (relative) | 0.6% | 1.7% | 0.6% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | 12.5% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | 16.4% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.825 | 0.116 | 0.041 | [0.728, 0.922] | [0.750, 0.900] |
| Kendall Tau Correlation $\tau$ | 0.675 | 0.183 | 0.065 | [0.522, 0.828] | [0.550, 0.800] |

### Variant **P900** (truth-assisted offline positive control)
- **Factor**: blockage position on ktb_n1 = 900 m
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 7.67 | 5.12 | +2.55 | 2.55 | 2.3% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4202 | A3 | A3 | 8.62 | 4.52 | +4.10 | 4.10 | 3.7% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4203 | A3 | A3 | 5.72 | 5.08 | +0.64 | 0.64 | 0.5% | 0.00 | 0.0% | 1 | 0.700 | 0.600 |
| 4204 | A3 | A3 | 4.17 | 6.43 | -2.26 | 2.26 | 1.8% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4205 | A3 | A3 | 7.12 | 4.84 | +2.28 | 2.28 | 2.0% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4206 | A3 | A3 | 7.21 | 5.23 | +1.99 | 1.99 | 1.8% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4207 | A3 | A3 | 5.82 | 5.15 | +0.67 | 0.67 | 0.6% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4208 | A3 | A4 | 6.92 | 4.63 | +2.28 | 2.28 | 1.9% | 0.23 | 4.8% | 0 | 0.700 | 0.600 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | 1.53 | 1.89 | 0.67 | [-0.04, 3.11] | [0.20, 2.62] |
| BEE (absolute, veh·h) | 2.10 | 1.10 | 0.39 | [1.18, 3.02] | [1.43, 2.80] |
| BEE (relative) | 1.8% | 1.0% | 0.3% | [1.0%, 2.7%] | [1.2%, 2.5%] |
| Regret (veh·h) | 0.03 | 0.08 | 0.03 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (relative) | 0.6% | 1.7% | 0.6% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | 12.5% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | 16.4% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.812 | 0.083 | 0.030 | [0.743, 0.882] | [0.762, 0.862] |
| Kendall Tau Correlation $\tau$ | 0.675 | 0.104 | 0.037 | [0.588, 0.762] | [0.625, 0.750] |

### Variant **F100** (sensitivity (the Twin's demand belief))
- **Factor**: Twin TKO base factor in branches = 1.00
- **Complete Seeds**: 8 / 8
- **Exclusions**: None (complete 8/8 seeds)

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE signed | BEE abs | BEE rel | Regret | Regret rel | Top-1 | Spearman $\rho$ | Kendall $\tau$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 7.01 | 5.12 | +1.88 | 1.88 | 1.7% | 0.00 | 0.0% | 1 | 1.000 | 1.000 |
| 4202 | A3 | A3 | 7.04 | 4.52 | +2.53 | 2.53 | 2.2% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4203 | A3 | A3 | 6.76 | 5.08 | +1.68 | 1.68 | 1.4% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4204 | A3 | A3 | 6.95 | 6.43 | +0.51 | 0.51 | 0.4% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4205 | A3 | A3 | 7.34 | 4.84 | +2.49 | 2.49 | 2.2% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4206 | A3 | A3 | 6.67 | 5.23 | +1.44 | 1.44 | 1.3% | 0.00 | 0.0% | 1 | 0.800 | 0.600 |
| 4207 | A3 | A3 | 7.22 | 5.15 | +2.07 | 2.07 | 1.8% | 0.00 | 0.0% | 1 | 0.900 | 0.800 |
| 4208 | A3 | A4 | 6.18 | 4.63 | +1.55 | 1.55 | 1.3% | 0.23 | 4.8% | 0 | 0.900 | 0.800 |

#### Pooled Metrics Summary
| Metric | Mean | Std | SE | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|---|
| BEE (signed, veh·h) | 1.77 | 0.65 | 0.23 | [1.23, 2.31] | [1.33, 2.16] |
| BEE (absolute, veh·h) | 1.77 | 0.65 | 0.23 | [1.23, 2.31] | [1.32, 2.16] |
| BEE (relative) | 1.6% | 0.6% | 0.2% | [1.1%, 2.0%] | [1.2%, 1.9%] |
| Regret (veh·h) | 0.03 | 0.08 | 0.03 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (relative) | 0.6% | 1.7% | 0.6% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | 12.5% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | 16.4% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.887 | 0.064 | 0.023 | [0.834, 0.941] | [0.850, 0.925] |
| Kendall Tau Correlation $\tau$ | 0.775 | 0.128 | 0.045 | [0.668, 0.882] | [0.700, 0.850] |

## 4. Sensitivity Contrasts with Baseline B

Per preregistration (`docs/oct8-audit-sensitivity-plan.md`), paired differences $\Delta = \text{metric}(\text{variant}) - \text{metric}(B)$ are evaluated per seed over complete seeds.
Blocking rule 3 requires reporting actual $N$, exclusions by reason, and the uncorrected paired $t$ 95% CI. Contrasts are **uncorrected for multiplicity**, and no claims of statistical significance are made.

| Contrast Variant | Factor Changed | Preregistered Label | Complete $N$ | Exclusions | $\Delta \text{BEE}_{\text{signed}}$ (veh·h) [95% CI] | $\Delta |\text{BEE}|$ (veh·h) [95% CI] | $\Delta \text{Regret}$ (veh·h) [95% CI] |
|---|---|---|---|---|---|---|---|
| **D300** | blockage duration from t_d = 300 s (ends at 5,400 s) | **truth-assisted offline positive control** | 8 | None | -4.82 [-6.88, -2.75] | +1.67 [-0.85, +4.18] | +1.83 [-0.28, +3.95] |
| **D600** | blockage duration from t_d = 600 s (ends at 5,700 s) | **sensitivity** | 8 | None | -0.12 [-0.32, +0.07] | -0.12 [-0.32, +0.07] | +0.00 [+0.00, +0.00] |
| **P456** | blockage position on ktb_n1 = 456 m (upstream detector AID02109) | **sensitivity** | 8 | None | +0.07 [-0.62, +0.75] | +0.11 [-0.56, +0.78] | +0.00 [+0.00, +0.00] |
| **P900** | blockage position on ktb_n1 = 900 m | **truth-assisted offline positive control** | 8 | None | -0.10 [-1.25, +1.05] | +0.47 [-0.52, +1.45] | +0.00 [+0.00, +0.00] |
| **F100** | Twin TKO base factor in branches = 1.00 | **sensitivity (the Twin's demand belief)** | 8 | None | +0.14 [-0.36, +0.64] | +0.14 [-0.36, +0.64] | +0.00 [+0.00, +0.00] |

### Detailed Per-Seed Contrast Values ($\Delta = \text{Variant} - B$)

#### Paired Difference $\Delta \text{BEE}_{\text{signed}}$ (veh·h)
| Seed | D300 (positive control) | D600 | P456 | P900 (positive control) | F100 |
|---|---|---|---|---|---|
| 4201 | -2.18 | -0.28 | -0.49 | +0.63 | -0.04 |
| 4202 | -1.21 | -0.41 | +1.37 | +2.45 | +0.87 |
| 4203 | -6.43 | -0.01 | +0.72 | -0.63 | +0.41 |
| 4204 | -6.09 | +0.05 | -0.35 | -2.45 | +0.32 |
| 4205 | -2.27 | +0.05 | -1.09 | +0.01 | +0.23 |
| 4206 | -7.30 | -0.11 | -0.26 | -0.07 | -0.62 |
| 4207 | -6.53 | -0.45 | -0.18 | -0.66 | +0.74 |
| 4208 | -6.53 | +0.19 | +0.82 | -0.07 | -0.81 |

#### Paired Difference $\Delta |\text{BEE}|$ (veh·h)
| Seed | D300 (positive control) | D600 | P456 | P900 (positive control) | F100 |
|---|---|---|---|---|---|
| 4201 | -1.67 | -0.28 | -0.49 | +0.63 | -0.04 |
| 4202 | -1.21 | -0.41 | +1.37 | +2.45 | +0.87 |
| 4203 | +3.90 | -0.01 | +0.72 | -0.63 | +0.41 |
| 4204 | +5.71 | +0.05 | -0.03 | +2.07 | +0.32 |
| 4205 | -2.27 | +0.05 | -1.09 | +0.01 | +0.23 |
| 4206 | +3.18 | -0.11 | -0.26 | -0.07 | -0.62 |
| 4207 | +3.87 | -0.45 | -0.18 | -0.66 | +0.74 |
| 4208 | +1.82 | +0.19 | +0.82 | -0.07 | -0.81 |

#### Paired Difference $\Delta \text{Regret}$ (veh·h)
| Seed | D300 (positive control) | D600 | P456 | P900 (positive control) | F100 |
|---|---|---|---|---|---|
| 4201 | +5.01 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4202 | +4.83 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4203 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4204 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4205 | +4.84 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4206 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4207 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 4208 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |

## 5. Twin Common Random Numbers (CRN) Diagnostic Across Variants

Paired action correlation $\text{corr}(a) = \text{Corr}_{r}(J(A0, r), J(a, r))$ and variance reduction $\text{VR}(a)$ across the 6 Twin replications.

| Variant | A1 Median Corr | A1 Median VR | A2 Median Corr | A2 Median VR | A3 Median Corr | A3 Median VR | A4 Median Corr | A4 Median VR | Pooled Median Corr | Pooled Median VR |
|---|---|---|---|---|---|---|---|---|---|---|
| **B** | 0.8835 | 0.8759 | 0.9082 | 0.9071 | 0.9299 | 0.9133 | 0.8925 | 0.8894 | **0.9027** | **0.8982** |
| **D300** | 0.9523 | 0.9376 | 0.9727 | 0.9695 | 0.9795 | 0.9657 | 0.9513 | 0.9421 | **0.9631** | **0.9481** |
| **D600** | 0.8831 | 0.8788 | 0.9206 | 0.9171 | 0.9437 | 0.9206 | 0.9177 | 0.9116 | **0.9177** | **0.9061** |
| **P456** | 0.9006 | 0.8882 | 0.9446 | 0.8692 | 0.9202 | 0.9080 | 0.7585 | 0.7093 | **0.9006** | **0.8309** |
| **P900** | 0.8703 | 0.8429 | 0.9037 | 0.8497 | 0.8856 | 0.8168 | 0.7774 | 0.7335 | **0.8620** | **0.8030** |
| **F100** | 0.9293 | 0.8819 | 0.8830 | 0.8604 | 0.8957 | 0.8547 | 0.8679 | 0.8616 | **0.8847** | **0.8642** |

## 6. Execution Failures by Reason

No simulation errors or worker exceptions occurred across all 1,200 sensitivity Twin branches (0 failures).

## 7. Artifact and Code Files

- Implementation code files:
  - `citypulse/branching/audit_engine.py` (added `resolve_twin_job_overrides`, `hyp_pos`, `hyp_clear_time`, `branch_factor` overrides, blocker placement and clearance tracking)
  - `citypulse/experiments/decision_audit.py` (added sensitivity runner `--sens`, baseline compatibility check, metrics & contrasts calculation, blocker summarizer, and report generator)
  - `tests/test_audit.py` (unit tests verifying baseline defaults preservation and sensitivity variant override parsing)
- Results and data files:
  - `results/audit/sens/baseline_check.json` (65/65 exact matches against stored baseline)
  - `results/audit/sens/raw_sens.parquet` (1,200 sensitivity Twin branch simulation records)
  - `results/audit/sens/blocker_summary.json` (actual blocker placement and clearance verification)
  - `results/audit/sens/metrics_sens.json` (per-variant metrics, pooled statistics, and paired contrasts)
  - `results/audit/sens/report.md` (this report)

REPORT DONE