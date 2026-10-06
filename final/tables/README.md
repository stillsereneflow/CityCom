# final/tables - evidence tables from the collected results

Built by `final/tables/build_tables.py` (reads stored artefacts only; no simulation, no tuning).
Each table exists as `.csv` (full precision) and `.md` (pipe table, 3 decimals, one-line caption
with source and N).

| table | content | sources |
|---|---|---|
| `t1_frozen_per_seed` | frozen test audit, per seed and belief (B primary, D300 secondary): a*, oracle, Top-1, G_T_hat(a*), G_P(a*), BEE signed, regret, Spearman, Kendall, floor signed, fixed-A3 G_T and G_P | `results/frozen_audit/metrics.json` `primary.per_seed`, `secondary.per_seed` |
| `t2_dev_vs_frozen_pooled` | development audit (seeds 4201-4208) beside the frozen test audit (seeds 4501-4508), never pooled, with a descriptive frozen-minus-dev difference column; B and D300 blocks | development B: `results/audit/v2/metrics_v2.json` `pooled`/`per_seed`, with G_T_hat/G_P/G_T_A3/G_P_A3 recomputed from `results/audit/raw.parquet` (part A definitions); development D300: recomputed from `results/audit/sens/raw_sens.parquet` (variant D300); frozen: `results/frozen_audit/metrics.json` `primary.pooled`, `secondary.pooled` |
| `t3_event_engine_coverage` | event-engine mechanisms: evidence level (live natural / live forced / unit only / not covered), counts with denominators, source | `results/dev_runs/outcomes/outcomes.json`; `results/event_pilot2/report.md`; `docs/decision-2026-10-06-dev-runs.md` |
| `t4_missing_queue` | per seed Q_P, Q_C, Q_H at t_d, e(C-D), e(H-D), delta_D, duration contrast under C and H, and the study classification label | `results/missing_queue/queue_td.parquet`; `results/missing_queue/metrics.json` (`queue[]`, `plan[]`, `classification`) |
| `t5_replay_diagnosis` | per variant: would-adopt counts over the 13 INC and 9 NOI evaluations, INC-only median gap, MAP-family distribution, variant labels; recomputed at beta = 0.25 | `results/replay_diag/raw.parquet`; labels from `docs/oct10-replay-diagnosis-plan.md` |
| `t6_frozen_validation` | frozen-audit integrity: rows per world/belief/status, reruns, RNG check, code hashes before/after, blocker placement range, D300 release checks, seed check, alarm time and latency per seed | `results/frozen_audit/raw.parquet`, `metrics.json`, `reruns.json`, `code_hashes_before_after.json`, `seed_check.json`, `runs/seed_*/two_world_info.json` |

## Verification performed while building

* The part A / audit v2 recomputation from `results/audit/raw.parquet` reproduces
  `results/audit/v2/metrics_v2.json` `pooled` and `per_seed` for every overlapping metric
  (max abs difference < 1e-6, exact for the rankings); this is what the development-B
  fixed-A3 rows use, since that pooled block does not contain them.
* The same definitions applied to `results/audit/sens/raw_sens.parquet` (variant D300)
  reproduce `results/audit/sens/metrics_sens.json` `variants.D300` per-seed values and pooled
  means exactly (max abs difference 7e-15; per-seed a*, oracle, G_T_hat, G_P, BEE, regret, Top-1,
  Spearman, Kendall). Its pooled t-CI bounds agree to 2.4e-7: the sens report's t multiplier
  differs from the exact t(0.975, 7) in the 8th digit, and the table uses the exact value
  (the same one that reproduces `metrics_v2.json` pooled exactly).
* The same definitions applied to `results/frozen_audit/raw.parquet` reproduce
  `results/frozen_audit/metrics.json` `primary.pooled` and `secondary.pooled` (all metrics,
  including the calibration floor and the fixed-A3 gains).
* The beta = 0.25 replay recomputation reproduces the stored `post`, `gap` and `would_adopt`
  columns of `results/replay_diag/raw.parquet` (agreement figures are printed in the t5 caption).
* Q_P/Q_C/Q_H from `results/missing_queue/queue_td.parquet` equal the `queue[]` aggregates in
  `results/missing_queue/metrics.json` (asserted in the script).
* Top-1 agreement (`a* == oracle`) is a per-seed 0/1 indicator: `t1_frozen_per_seed` shows it as
  yes/no per seed, and `t2_dev_vs_frozen_pooled` shows the exact per-seed count k/8 (B: dev 7/8,
  frozen 7/8; D300: dev 4/8, frozen 5/8) with n/a interval and difference cells, because a 95 %
  t-CI on that proportion is not meaningful and can exceed 1 (it did: 0.579-1.171). The counts
  equal the stored pooled means times 8 (`metrics_v2.json`, `results/frozen_audit/metrics.json`).

## Inferred values

No value in these tables is inferred beyond its source: every cell is either read from the
cited JSON path or recomputed from the cited Parquet with the cited definition. The only
choices made here are (a) the development-B source split described above, (b) the calibration
floor's comparison action (the floor's own R1-selected a*, which is what the stored audit
values use; the plan text is ambiguous, and using the main a* changes the dev pooled floor from
0.1808 to 0.2074), and (c) the ordering/labels of rows, which carry no numeric meaning.
