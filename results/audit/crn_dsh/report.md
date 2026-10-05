MODEL: deepseek-v4.1-flash

# Independent Recompute of the Paired-Action CRN Statistic

Read-only recompute from `results/audit/raw.parquet` (no simulation). Script: `results/audit/crn_dsh/crn_recompute.py`.

- Rows read: **720**; worlds: twin, proxy, calibration; seeds: 4201-4208 (N = 8); actions: A0, A1, A2, A3, A4; replications per world/seed/action: 6-6.
- Status counts overall: `ok` = 720.
- Non-ok rows: twin = 0, proxy = 0, calibration = 0. All rows are `ok`, so a status filter is a no-op and every replication present is used.

## 1. Definitions

For each world and seed, over the replications `m` present (pairs aligned on the same replication index, i.e. genuinely paired CRN draws):

- `rho(a) = Pearson corr_m( J(A0, m), J(a, m) )` for a in {A1, A2, A3, A4}.
- `VR(a) = 1 - Var_m[J(a,m) - J(A0,m)] / ( Var_m[J(a,m)] + Var_m[J(A0,m)] )`, **sample** variances (ddof = 1).

Old statistic, exactly as implemented in `citypulse/experiments/decision_audit.py` (lines 526-535): `pivot(index=replication, columns=action, values=J).T.corr()`. The pivot is 6 (replications) x 5 (actions); `.T` makes it 5 x 6, and `.corr()` correlates its **columns**, so the result is a **6 x 6 matrix indexed by replication**: entry `(m, m')` is the correlation across the 5 actions between replication `m`'s and replication `m'`'s J profile. The audit reduced it to the mean of its 15 upper-triangle pairs (`m < m'`), built from the **proxy** world only, per seed, then averaged over seeds. It is evaluated per world here for comparison.

## 2. Per-seed tables

### 2.1 World `twin`

`rho(a)` per seed (Pearson corr over replications of J(A0, m) vs J(a, m)), with the per-seed old statistic alongside:

| Seed | A1 | A2 | A3 | A4 | mean rho | old-stat mean (15 rep pairs) | n reps |
|---|---|---|---|---|---|---|---|
| 4201 | 0.9323 | 0.9707 | 0.9647 | 0.9574 | 0.9563 | 0.9811 | 6 |
| 4202 | 0.9484 | 0.9183 | 0.9534 | 0.9028 | 0.9307 | 0.9699 | 6 |
| 4203 | 0.5732 | 0.6885 | 0.7287 | 0.6702 | 0.6652 | 0.9657 | 6 |
| 4204 | 0.8850 | 0.9754 | 0.9026 | 0.8562 | 0.9048 | 0.9603 | 6 |
| 4205 | 0.8820 | 0.7726 | 0.9064 | 0.6108 | 0.7929 | 0.9661 | 6 |
| 4206 | 0.8723 | 0.8793 | 0.9549 | 0.9466 | 0.9133 | 0.9739 | 6 |
| 4207 | 0.9756 | 0.9983 | 0.9574 | 0.8822 | 0.9534 | 0.9507 | 6 |
| 4208 | 0.8658 | 0.8982 | 0.7323 | 0.9812 | 0.8694 | 0.9462 | 6 |

`VR(a)` per seed (1 - Var(diff) / (Var(a) + Var(A0)), sample variances):

| Seed | A1 | A2 | A3 | A4 |
|---|---|---|---|---|
| 4201 | 0.9095 | 0.9648 | 0.9610 | 0.9555 |
| 4202 | 0.9384 | 0.9175 | 0.9287 | 0.8996 |
| 4203 | 0.5731 | 0.6658 | 0.7078 | 0.6685 |
| 4204 | 0.8837 | 0.9689 | 0.9026 | 0.8526 |
| 4205 | 0.8682 | 0.7331 | 0.8799 | 0.5848 |
| 4206 | 0.8365 | 0.8064 | 0.9450 | 0.9456 |
| 4207 | 0.9676 | 0.9928 | 0.9239 | 0.8791 |
| 4208 | 0.7818 | 0.8968 | 0.6251 | 0.9796 |

### 2.2 World `proxy`

`rho(a)` per seed (Pearson corr over replications of J(A0, m) vs J(a, m)), with the per-seed old statistic alongside:

| Seed | A1 | A2 | A3 | A4 | mean rho | old-stat mean (15 rep pairs) | n reps |
|---|---|---|---|---|---|---|---|
| 4201 | 0.9936 | 0.9976 | 0.9947 | 0.9871 | 0.9932 | 0.9878 | 6 |
| 4202 | 0.9984 | 0.9997 | 0.9988 | 0.9963 | 0.9983 | 0.9972 | 6 |
| 4203 | 0.9945 | 0.9925 | 0.9947 | 0.9905 | 0.9930 | 0.9888 | 6 |
| 4204 | 0.9910 | 0.9784 | 0.9636 | 0.9665 | 0.9749 | 0.9923 | 6 |
| 4205 | 0.9915 | 0.9648 | 0.9562 | 0.9588 | 0.9678 | 0.9952 | 6 |
| 4206 | 0.9913 | 0.9848 | 0.9895 | 0.9654 | 0.9828 | 0.9858 | 6 |
| 4207 | 0.9998 | 0.9954 | 0.9948 | 0.9996 | 0.9974 | 0.9970 | 6 |
| 4208 | 0.9984 | 0.9869 | 0.9930 | 0.9959 | 0.9935 | 0.9878 | 6 |

`VR(a)` per seed (1 - Var(diff) / (Var(a) + Var(A0)), sample variances):

| Seed | A1 | A2 | A3 | A4 |
|---|---|---|---|---|
| 4201 | 0.9936 | 0.9969 | 0.9947 | 0.9871 |
| 4202 | 0.9984 | 0.9996 | 0.9988 | 0.9963 |
| 4203 | 0.9944 | 0.9925 | 0.9947 | 0.9905 |
| 4204 | 0.9798 | 0.9764 | 0.9626 | 0.9644 |
| 4205 | 0.9905 | 0.9640 | 0.9526 | 0.9562 |
| 4206 | 0.9908 | 0.9773 | 0.9861 | 0.9427 |
| 4207 | 0.9998 | 0.9954 | 0.9945 | 0.9969 |
| 4208 | 0.9969 | 0.9862 | 0.9929 | 0.9856 |

### 2.3 World `calibration`

`rho(a)` per seed (Pearson corr over replications of J(A0, m) vs J(a, m)), with the per-seed old statistic alongside:

| Seed | A1 | A2 | A3 | A4 | mean rho | old-stat mean (15 rep pairs) | n reps |
|---|---|---|---|---|---|---|---|
| 4201 | 0.9948 | 0.9903 | 0.9909 | 0.9503 | 0.9816 | 0.9812 | 6 |
| 4202 | 0.9956 | 0.9934 | 0.9950 | 0.9922 | 0.9941 | 0.9891 | 6 |
| 4203 | 0.9970 | 0.9805 | 0.9656 | 0.9859 | 0.9823 | 0.9964 | 6 |
| 4204 | 0.9939 | 0.9939 | 0.9965 | 0.9861 | 0.9926 | 0.9917 | 6 |
| 4205 | 0.9979 | 0.9999 | 0.9953 | 0.9935 | 0.9966 | 0.9954 | 6 |
| 4206 | 0.9978 | 0.9981 | 0.9968 | 0.9921 | 0.9962 | 0.9848 | 6 |
| 4207 | 0.9978 | 0.9900 | 0.9948 | 0.9795 | 0.9905 | 0.9956 | 6 |
| 4208 | 0.9997 | 0.9928 | 0.9964 | 0.9899 | 0.9947 | 0.9937 | 6 |

`VR(a)` per seed (1 - Var(diff) / (Var(a) + Var(A0)), sample variances):

| Seed | A1 | A2 | A3 | A4 |
|---|---|---|---|---|
| 4201 | 0.9916 | 0.9848 | 0.9908 | 0.9491 |
| 4202 | 0.9937 | 0.9922 | 0.9950 | 0.9914 |
| 4203 | 0.9961 | 0.9794 | 0.9654 | 0.9852 |
| 4204 | 0.9938 | 0.9917 | 0.9964 | 0.9813 |
| 4205 | 0.9978 | 0.9977 | 0.9934 | 0.9922 |
| 4206 | 0.9978 | 0.9981 | 0.9957 | 0.9919 |
| 4207 | 0.9968 | 0.9900 | 0.9938 | 0.9790 |
| 4208 | 0.9995 | 0.9928 | 0.9961 | 0.9899 |

## 3. Per-world summary

Median `rho` and median `VR` are taken over all seed x action cells for that world (8 seeds x 4 actions = 32 values). The old-statistic mean averages the per-seed means of the 15 replication-pair correlations.

| World | Seeds | Reps/cell | Median rho | Median VR | Mean rho | rho range | Old-stat mean | Old-stat per-pair min | Old-stat per-pair max | Non-ok rows |
|---|---|---|---|---|---|---|---|---|---|---|
| twin | 8 | 6-6 | 0.9027 | 0.8982 | 0.8732 | 0.5732-0.9983 | 0.9642 | 0.8435 | 0.9992 | 0 |
| proxy | 8 | 6-6 | 0.9927 | 0.9917 | 0.9876 | 0.9562-0.9998 | 0.9915 | 0.9638 | 0.9998 | 0 |
| calibration | 8 | 6-6 | 0.9939 | 0.9925 | 0.9911 | 0.9503-0.9999 | 0.9910 | 0.9365 | 0.9999 | 0 |

Per-action medians over seeds (same data, split by action):

| World | Statistic | A1 | A2 | A3 | A4 |
|---|---|---|---|---|---|
| twin | median rho | 0.8835 | 0.9082 | 0.9299 | 0.8925 |
| twin | median VR | 0.8759 | 0.9071 | 0.9133 | 0.8894 |
| proxy | median rho | 0.9940 | 0.9897 | 0.9938 | 0.9888 |
| proxy | median VR | 0.9940 | 0.9893 | 0.9937 | 0.9863 |
| calibration | median rho | 0.9974 | 0.9931 | 0.9951 | 0.9880 |
| calibration | median VR | 0.9965 | 0.9920 | 0.9944 | 0.9875 |

## 4. What the old statistic actually computed

`pivot(index=replication, columns=action).T.corr()` correlates **replications**, not actions: for each pair of replications it correlates their 5-element vector of action costs. It therefore answers *"do the five-action cost profiles look alike across replications?"* - which is high for any world where all actions move together with the shared demand realisation, whether or not the paired A0-vs-a difference cancels. It is the transpose of the intended pairing measure: the new statistic fixes two **actions** and correlates over **replications**, while the old one fixes two **replications** and correlates over **actions**.

Concretely, for one world/seed the pivot is 6 x 5. The old matrix is 6 x 6 (15 pairs, 5 observations per correlation); `rho(a)` lives in the 5 x 5 matrix `pivot.corr()`, which correlates actions over the 6 replications. Per-world means of both objects:

| World | Old: 6x6 over replications (15 pairs) | Related: 5x5 over actions (10 pairs) | of which A0 pairs (= mean rho) | of which non-A0 pairs |
|---|---|---|---|---|
| twin | 0.9642 | 0.8863 | 0.8732 | 0.8950 |
| proxy | 0.9915 | 0.9859 | 0.9876 | 0.9847 |
| calibration | 0.9910 | 0.9887 | 0.9911 | 0.9872 |

The last two columns are **not** the old statistic - they are the correctly-oriented action-vs-action correlations shown for contrast. The identity `mean_a rho(a) == mean of the A0 pairs of pivot.corr()` holds cell-by-cell; the maximum absolute deviation over all world/seed cells is **0.0000** (numerical noise).

Provenance check: the original audit computed the old statistic on the **proxy** world only (`px` in `decision_audit.py`), giving a mean here of **0.9915**; the audit report lists `Mean CRN Correlation Across Actions = 0.991`, which this reproduces.

## 5. Comparison and reading

| World | New: median rho | New: median VR | Old: mean replication-pair corr | Gap (old - median rho) |
|---|---|---|---|---|
| twin | 0.9027 | 0.8982 | 0.9642 | 0.0615 |
| proxy | 0.9927 | 0.9917 | 0.9915 | -0.0012 |
| calibration | 0.9939 | 0.9925 | 0.9910 | -0.0029 |

- The two statistics are not two estimates of the same quantity. The new `rho(a)` measures how tightly an action's cost tracks the A0 baseline replication-by-replication; the old statistic measures how similar whole action-profiles are between replications.
- The old statistic is compressed and therefore weakly discriminative: its world means span only 0.9642-0.9915 (range 0.027), while the new median rho spans 0.9027-0.9939 (range 0.091). It stays near 1 in every world because all five actions respond to the same demand realisation, so a high value carries little information about baseline pairing.
- Where the two disagree most is the twin world, the one that drives the audit's decisions: there the old statistic reads 0.9642 while the new median rho is 0.9027, and it stays at 0.9657 for seed 4203 even though that seed's per-action rho falls to 0.5732-0.7287. The old statistic would report that seed as near-perfect pairing; the new one exposes it as the weakest seed in the audit.
- `VR(a)` is the variance-reduction reading of the same pairing: `VR = 1` means the action-minus-A0 difference is noiseless (perfect CRN), `VR = 0` means the difference is as noisy as independent runs. It tracks `rho(a)` closely here, as expected for near-linear pairing.
- A mean over 15 replication pairs hides heterogeneity: the per-pair minimum is 0.8435 (twin), 0.9638 (proxy) and 0.9365 (calibration), far below the corresponding means, i.e. some replication pairs disagree strongly while the reported average stays above 0.96.

## 6. Cross-checks

- Pair alignment: every world/seed/action cell uses the same replication set, so `J(A0, m)` and `J(a, m)` are matched on `m`; paired counts per cell observed = [6].
- Replication coverage: 6-6 replications for every world/seed; no missing (world, seed, action, replication) cell.
- Old statistic pair count per seed: [15] upper-triangle pairs of the 6 x 6 matrix, as expected.
- Non-ok rows: twin = 0, proxy = 0, calibration = 0; recomputing with non-ok rows dropped changes nothing.
- Correlations are undefined only for zero-variance inputs; no such cell occurred (all reported values are finite).

REPORT DONE
