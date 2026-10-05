# Offline audit sensitivities, one factor at a time: preregistered before any run (2026-10-05)

Roadmap: `docs/decision-2026-10-05-roadmap.md`, Oct 8–9. Base audit: `docs/oct6-audit-and-pilot2-plan.md`, part A. Data: `results/audit/raw.parquet`. Corrected metrics: `results/audit/v2/metrics_v2.json` (d9d078b).

## Purpose

Measure how the audit's decision-fidelity metrics (a\*, BEE, regret, ranking) move when **one** element of the Twin's belief changes. This shows which part of the positive BEE (+1.63 veh·h) is sensitive to which belief element.

It is a measurement, with no acceptance criterion. No bias or robustness is attributed except through these contrasts.

## What is held fixed

- **Proxy side:** the same 8 seeds (4201–4208), the same t_d = 5,100 s snapshots, and the same Proxy branches. The **existing Proxy and calibration rows** of `raw.parquet` are reused unchanged, so G_P, the oracle and the floor are identical across variants.
- **Twin side:** the same t_d snapshots, the same future-demand draws D_T(r), the same SUMO seeds r = 1–6 with R₁ = 1–3 and R₂ = 4–6, the same actions A0–A4, the same KPI (total time spent over 900 s), and the same code path (`citypulse/branching/audit_engine.py`). Only the single factor below changes.

## Variants (Twin belief; each changes one factor from the baseline B)

| ID | Factor | Value | Baseline value | Label |
|---|---|---|---|---|
| B | (none) | as run | | baseline; re-used rows, not re-run |
| D300 | blockage duration from t_d | 300 s (ends at 5,400 s) | whole horizon (≥ 900 s) | **truth-assisted, offline positive control** |
| D600 | blockage duration | 600 s | whole horizon | sensitivity |
| P456 | blockage position on `ktb_n1` | 456 m (at the upstream detector AID02109) | 755.3 m | sensitivity |
| P900 | blockage position | 900 m | 755.3 m | **truth-assisted, offline positive control** |
| F100 | Twin TKO base factor in branches | 1.00 | 0.85 | sensitivity (the Twin's demand belief) |

For F100, the factor is changed in the branch stream only. The snapshot's m and pending vehicles are kept.

## Metrics per variant

Per seed, then pooled over 8 seeds, exactly as in the base audit:
- a\*; Ĝ_T(a\*) on R₂;
- **BEE** (signed, absolute, relative), split and unsplit;
- **Regret** and split Regret_rel (M₂ gain of the M₁ oracle);
- Top-1 agreement, Spearman, Kendall;
- paired-action CRN on the Twin rows.

**Contrast with the baseline:** per seed, Δ = metric(variant) − metric(B), with a paired t 95% CI over the 8 seeds, for signed BEE, |BEE| and regret. There are 5 variant contrasts. Report them **without** a multiplicity correction, state that they are uncorrected, and draw no significance claims.

## Blocking rules added on review (2026-10-05)

Review: `~/.claude/runs/D--CityCom/20261005-1554-codex-sol-sensprereg/out.md`.

1. **Explicit per-job overrides** in the Twin branch worker (`citypulse/branching/audit_engine.py:258-276` hard-codes 755.3 m, a 3,600-s stop and the snapshot's factor):
   - `hyp_pos` (default 755.3);
   - `hyp_clear_time`, an absolute simulation time (default: none, i.e. no clearance within the horizon);
   - `branch_factor` (default: the snapshot meta's factor).
   
   D300 and D600 must clear at **simulation times 5,400 s and 5,700 s**, by an explicit resume or removal at that time, independent of when the blockers reach their stops. Record the actual blocker placement (edge, lane, pos, time stopped) and the clearance time in each branch's output.
2. **Baseline compatibility check** before collecting contrasts:
   - With the modified worker and identical frozen inputs (default overrides), replay at least seed 4201, all 6 replications × 5 actions, plus one replication × 5 actions for every other seed.
   - J and the vehicle digest must match the stored baseline rows exactly.
   - If any differ, stop and report.
   - These verification rows are stored separately and do not enter the analysis.
3. **Incomplete-data rule:**
   - A seed–variant metric is computed only if all 5 actions × all 6 Twin replications are present and ok. Never select or evaluate on a reduced grid.
   - Each contrast uses the seeds complete in both B and the variant. Report the actual N and the exclusions by reason.
   - Omit the t interval when fewer than 2 pairs remain.

Non-blocking: these contrasts establish sensitivity conditional on the frozen snapshots. They do not decompose +1.63 veh·h into additive causal contributions.

## Raw data, order, failures

- New Twin rows are appended to `results/audit/sens/raw_sens.parquet`, with a `variant` column. The base `raw.parquet` is not modified.
- Compute every metric before looking at any summary.
- Failures are counted by reason.

## Compute budget

5 variants × 8 seeds × 6 replications × 5 actions = 1,200 Twin branches (about 4–5 s each, 8-way parallel).
