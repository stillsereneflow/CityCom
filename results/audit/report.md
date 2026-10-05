MODEL: Gemini 3.8 Flash (High)

# Preregistered Offline Decision Audit Report

This report documents the offline decision fidelity audit prescribed in `docs/oct6-audit-and-pilot2-plan.md` (Part A) and report2 §K–§L.
As preregistered, this audit is an observational measurement of decision fidelity; no efficacy claims are made.

## 1. Seed Verification

- **Audit Seeds**: 4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208 (N = 8)
- **Verification**: Checked against all prior runs in `results/`. None of seeds 4201–4208 were previously used.

## 2. Corrected-G4 Alarm Times and Latencies

Decision timestamp: $t_d = 5,100$ s. Alarm detection requires $B \ge 3.0$ at two timestamps exactly 30 s apart on Twin log (using $\sigma$ from `results/event_pilot/impl/sigma_event.json`).

| Seed | First Alarm $t_{\text{alarm}}$ (s) | $t_d - t_{\text{alarm}}$ (s) | $\ge 120$ s Required | Alarm Intervals | Wall Time (s) |
|---|---|---|---|---|---|
| 4201 | 5100.0 | 0.0 | NO | 15 | 68.0 |
| 4202 | 5010.0 | 90.0 | NO | 20 | 68.1 |
| 4203 | 4980.0 | 120.0 | YES | 21 | 68.5 |
| 4204 | 4890.0 | 210.0 | YES | 21 | 68.6 |
| 4205 | 5040.0 | 60.0 | NO | 20 | 80.6 |
| 4206 | 4890.0 | 210.0 | YES | 19 | 80.6 |
| 4207 | 4920.0 | 180.0 | YES | 25 | 80.6 |
| 4208 | 4890.0 | 210.0 | YES | 24 | 80.7 |

## 3. RNG Check on Seed 4201

- **Overall Status**: **PASSED**
- **Twin World**:
  - (i) Different `--seed` (r=1 vs r=2) produces different trajectory: **True** (digest `c0eeacf58597...` vs `aaefe2f78491...`)
  - (ii) Identical inputs (r=1 run 1 vs run 2) reproduce identical J and vehicle digest: **True** (J = 97.937222 veh·h, digest `c0eeacf58597...`)
- **Proxy World**:
  - (i) Different `--seed` (m=1 vs m=2) produces different trajectory: **True** (digest `56dfb081cd4c...` vs `27e6e277fc7b...`)
  - (ii) Identical inputs (m=1 run 1 vs run 2) reproduce identical J and vehicle digest: **True** (J = 108.868611 veh·h, digest `56dfb081cd4c...`)

## 4. Per-Seed Decision Audit Results

| Seed | Twin $a^*$ | Proxy Oracle | $\hat{G}_T(a^*)$ | $G_P(a^*)$ | BEE (abs) | BEE (rel) | Regret | Regret (rel) | BEE Floor |
|---|---|---|---|---|---|---|---|---|---|
| 4201 | A3 | A3 | 7.05 | 5.12 | 1.92 | 1.7% | 0.00 | 0.0% | 0.15 |
| 4202 | A3 | A3 | 6.17 | 4.52 | 1.65 | 1.5% | 0.00 | 0.0% | 0.02 |
| 4203 | A3 | A3 | 6.35 | 5.08 | 1.27 | 1.1% | 0.00 | 0.0% | 0.33 |
| 4204 | A3 | A3 | 6.63 | 6.43 | 0.19 | 0.2% | 0.00 | 0.0% | 0.09 |
| 4205 | A3 | A3 | 7.11 | 4.84 | 2.27 | 2.0% | 0.00 | 0.0% | 0.22 |
| 4206 | A3 | A3 | 7.29 | 5.23 | 2.06 | 1.8% | 0.00 | 0.0% | 0.12 |
| 4207 | A3 | A3 | 6.48 | 5.15 | 1.33 | 1.2% | 0.00 | 0.0% | 0.14 |
| 4208 | A3 | A4 | 6.99 | 4.63 | 2.35 | 2.0% | 0.23 | 4.8% | 0.38 |

### Mean Action Costs $J$ (veh·h)

#### Twin Evaluation $R_2$ (veh·h)
| Seed | A0 | A1 | A2 | A3 | A4 | Selected $a^*$ |
|---|---|---|---|---|---|---|
| 4201 | 95.90 | 95.82 | 90.76 | 88.85 | 90.21 | A3 |
| 4202 | 88.40 | 88.55 | 83.12 | 82.23 | 83.87 | A3 |
| 4203 | 100.46 | 101.01 | 96.16 | 94.11 | 96.92 | A3 |
| 4204 | 102.74 | 101.93 | 98.32 | 96.12 | 98.53 | A3 |
| 4205 | 97.59 | 97.37 | 91.72 | 90.48 | 92.23 | A3 |
| 4206 | 97.68 | 97.09 | 92.56 | 90.40 | 92.02 | A3 |
| 4207 | 89.19 | 89.60 | 84.17 | 82.71 | 84.70 | A3 |
| 4208 | 104.01 | 104.01 | 98.71 | 97.03 | 99.05 | A3 |

#### Proxy Evaluation $M_2$ (veh·h)
| Seed | A0 | A1 | A2 | A3 | A4 | Oracle ($M_1$) |
|---|---|---|---|---|---|---|
| 4201 | 112.98 | 112.87 | 109.07 | 107.86 | 109.14 | A3 |
| 4202 | 112.36 | 112.67 | 108.73 | 107.84 | 108.10 | A3 |
| 4203 | 116.91 | 117.04 | 112.26 | 111.83 | 111.76 | A3 |
| 4204 | 122.25 | 122.01 | 117.23 | 115.82 | 117.20 | A3 |
| 4205 | 113.32 | 113.35 | 109.59 | 108.48 | 108.79 | A3 |
| 4206 | 111.60 | 111.55 | 107.39 | 106.37 | 107.17 | A3 |
| 4207 | 113.89 | 113.90 | 109.66 | 108.74 | 109.20 | A3 |
| 4208 | 117.14 | 117.49 | 113.63 | 112.50 | 112.27 | A4 |

## 5. Pooled Metrics Summary (N = 8)

| Metric | Mean | Std | Paired t 95% CI | Percentile Bootstrap 95% CI |
|---|---|---|---|---|
| BEE (signed, veh·h) | 1.63 | 0.71 | [1.04, 2.22] | [1.14, 2.05] |
| BEE (absolute, veh·h) | 1.63 | 0.71 | [1.04, 2.22] | [1.13, 2.05] |
| BEE (relative to $J_P(A0)$) | 1.4% | 0.6% | [0.9%, 2.0%] | [1.0%, 1.8%] |
| BEE (unsplit abs, veh·h) | 1.74 | 0.67 | [1.18, 2.30] | [1.30, 2.17] |
| BEE (unsplit rel) | 1.5% | 0.6% | [1.0%, 2.0%] | [1.1%, 1.9%] |
| Regret (veh·h) | 0.03 | 0.08 | [-0.04, 0.10] | [0.00, 0.09] |
| Regret (rel, when denom $\ge 0.5$) | 0.6% | 1.7% | [-0.8%, 2.0%] | [0.0%, 1.8%] |
| Regret (unsplit, veh·h) | 0.08 | 0.23 | [-0.11, 0.27] | [0.00, 0.24] |
| Monte Carlo BEE Floor (abs, veh·h) | 0.18 | 0.12 | [0.08, 0.28] | [0.11, 0.26] |
| Monte Carlo BEE Floor (rel) | 0.2% | 0.1% | [0.1%, 0.2%] | [0.1%, 0.2%] |
| Top-1 Agreement ($a^* ==$ Oracle) | 87.5% | 35.4% | [57.9%, 117.1%] | [62.5%, 100.0%] |
| Top-1 Ranking Agreement ($R_2$ vs $M_2$) | 75.0% | 46.3% | [36.3%, 113.7%] | [37.5%, 100.0%] |
| Spearman Rank Correlation $\rho$ | 0.850 | 0.107 | [0.761, 0.939] | [0.775, 0.912] |
| Kendall Tau $\tau$ | 0.750 | 0.141 | [0.632, 0.868] | [0.650, 0.850] |
| Mean CRN Correlation Across Actions | 0.991 | 0.005 | [0.988, 0.995] | [0.989, 0.995] |

### BEE vs Calibration Floor Comparison

- **Twin BEE Absolute**: 1.63 veh·h
- **Monte Carlo Floor Absolute**: 0.18 veh·h
- **Structural Gap (Twin BEE - Floor)**: 1.45 veh·h

## 6. Execution Failures by Reason

No failures recorded across all two-world and branch runs (0 failures).

## 7. Artifact and Code Files

- Modified files:
  - `citypulse/proxy/service.py` (added `--proxy-snapshot-times`)
  - `citypulse/experiments/run_two_worlds.py` (added `--proxy-snapshot-times`)
- New implementation files:
  - `citypulse/branching/audit_engine.py` (Twin, Proxy, and Calibration branch workers)
  - `citypulse/experiments/decision_audit.py` (audit runner and pipeline)
  - `tests/test_audit.py` (unit tests for metric calculations, assertion, and thresholds)
- Results and data files:
  - `results/audit/rng_check.json` (RNG check verification on seed 4201)
  - `results/audit/raw.parquet` (raw J values for all 720 branch runs)
  - `results/audit/metrics.json` (per-seed and pooled summary metrics)
  - `results/audit/report.md` (this report)

REPORT DONE