# 《城脉·涟控》 final evidence report (laboratory prototype)

**Status: complete.** The design was frozen on 2026-10-06 (`docs/freeze-2026-10-06.md`, frozen code `ed03254`, freeze record `7a6a5ed`, Amendment A plus the pre-collection tooling fixes in `972a50f`, `e3e8083` and `dcec083`). The frozen test audit was collected once at `dcec083`, after Codex gave a GO, on test seeds 4501–4508 that no previous step had touched. Results commit: `aa7de30`.

Contents of this package:
- `METHOD.md`: the method summary;
- `CLAIMS.md`: the exact claims allowed, in English and Chinese;
- `figures/`: five figures plus `figure_data.csv`;
- `tables/`: six tables as CSV and Markdown;
- `demo/`: per-seed decision cards and the commands to reproduce and visualise the results.

## 1. What was built

An event-aware traffic digital twin and an offline decision-fidelity audit on a synthetic Kwun Tong corridor. A hidden **Proxy** world (IDM drivers, a real incident) emits only noisy, sparse sensor messages. The **Twin** (Krauss drivers, its own demand model, normal assimilation) must decide among five infrastructure actions at t_d = 5,100 s. Its predictions are audited against the Proxy's realised outcomes under common random numbers, with the selection replications kept separate from the evaluation replications. Details: `METHOD.md`.

## 2. Frozen test audit: verified facts

Sources: `results/frozen_audit/metrics.json`, `raw.parquet` and `report.md`; tables `t1`, `t2` and `t6`; figures 1, 2, 3 and 5. Intervals are 95 % t-intervals over 8 seeds, in veh·h.

| Quantity | Frozen test (4501–4508) | Development (4201–4208) |
|---|---|---|
| Twin choice a\* (belief B) | A3 8/8 | A3 8/8 |
| Proxy oracle (M₁) | A3 7/8 (A4 on 4508) | A3 7/8 (A4 on 4208) |
| Top-1 agreement | 7/8 | 7/8 |
| BEE, signed (predicted − realised gain) | **+2.162 [1.738, 2.586]** | +1.632 [1.041, 2.222] |
| BEE relative to the A0 total time spent | 1.9 % | 1.4 % |
| Split regret | −0.034 [−0.113, 0.046] | 0.029 [−0.040, 0.098] |
| Spearman / Kendall | 0.825 [0.738, 0.912] / 0.675 | 0.850 / 0.750 |
| Calibration discrepancy (Proxy as Twin) | 0.316 [0.134, 0.499] | 0.181 [0.080, 0.281] |
| Fixed-A3 gain, Twin vs Proxy | 7.066 vs 4.904 | 6.757 vs 5.126 |
| **D300 control** (true clearance given): BEE | −2.870 [−4.914, −0.826] | −3.187 [−5.474, −0.899] |
| D300 a\* / Spearman | A3 5, A0 2, A1 1 / −0.350 | A3 5, A1 2, A0 1 / −0.237 |

- **Integrity:** 960/960 branches succeeded, with no reruns, duplicates or exclusions. The seed-freshness check scanned 11,406 files with no match. The RNG isolation check passed (both worlds: the SUMO seed alone changes the trajectory, the demand seed alone changes it, and identical inputs reproduce it). Code hashes were identical before and after collection, and each branch ran in its own freshly spawned process. Blockers stopped at 755.26–755.30 m on lanes 0 and 1 at 5,103–5,124 s. All 480 D300 release records show resume at 5,400 s, verified at 5,401 s.
- **State at the decision time** (descriptive): the Proxy held 7–24 halted vehicles on the corridor and 161–194 vehicles on `ktb_n1`; the Twin held 0 halted and 26–43 on `ktb_n1` (figure 5).
- **Alarm-to-decision lead time** was 90–210 s. It was below the 120-s allowance on seed 4503 (90 s); t_d stayed at 5,100 s as preregistered.
- **Comparison:** the frozen audit **replicated the scenario-specific pattern** of the development audit: A3 selection, 7/8 oracle agreement, positive benefit overestimation, strong positive ranking agreement and near-zero split regret. The larger point estimates in the frozen set (BEE +2.16 vs +1.63, calibration discrepancy 0.32 vs 0.18) establish neither exact magnitudes nor a between-set difference or equivalence. The two sets are never pooled.

### Verification of every reported metric

1. **Project analyzer** (`citypulse/experiments/frozen_audit_analyze.py`), run by dsh. Before computing anything it enforces the RNG binding to provenance, code, environment and snapshots.
2. **Claude's independent script** (`results/frozen_audit/crosscheck_claude/indep_audit.py`, no project code imported). It first reproduced the development audit exactly. All 160 per-seed values equal the analyzer's within 3 × 10⁻¹⁴ (`compare_output.txt`).
3. **An independent cross-family implementation** (agy-pro, Gemini; `results/frozen_audit/crosscheck_agypro/`), written without reading the analyzer. Every mean agrees exactly; CI half-widths differ in the 4th decimal only, because it used a rounded t value (2.365 vs 2.3646).
4. Codex (OpenAI, read-only) reviewed the freeze record, the procedure (four rounds, ending in a GO) and the final results. It found no defect that invalidates a reported number.

The figure and demo scripts recompute per-seed BEE from raw and assert equality with `metrics.json`.

## 3. Supporting results (all preregistered, verified from raw)

| Study | Result | Source |
|---|---|---|
| Missing-queue diagnostic (4301–4304) | **Support.** Replaying incident history cut the fixed-A3 absolute gain error under true clearance from 4.16 to 0.90 (Δ −4.58/−3.25/−3.06/−2.17). Queue at t_d: Proxy 55/7/40/25, Twin 0, replayed Twin 14–19. Duration sensitivity 6.0–7.7 → 1.4–3.0. Full ranking not improved. | `t4`, figure 4, `docs/decision-2026-10-06-missing-queue.md` |
| Replay diagnosis (pilot-2 streams) | Point blockage + true onset: would-adopt 0/13 → 6/13; 0/9 on synthetic no-incident evaluations; dependent offline evaluations. | `t5`, `results/replay_diag/corrections.md` |
| Event development runs (4401–4406, 48 runs) | 13 suspected-event episodes, 25 library evaluations, 0/6 natural adoptions. EVT = CONV forecasts (incident MAE 20.6 / 18.8 halting vehicles). No alarms in the no-incident, shock and fault runs; the shock realised only +5–8 % flow and the fault was stuck at a normal reading. | `t3`, `docs/decision-2026-10-06-dev-runs.md` |
| Event-engine mechanics coverage | Trigger, library evaluation and forecasts: live. Adoption, state replacement, clearance and RECOVERY: forced runs only (clearance premature 3/3; recovery completed 1/4). DEGRADED scheduled exit: unit-tested only. | `t3` |

## 4. Verified facts, limitations, interpretations, unproven hypotheses

The authoritative wording is `CLAIMS.md`. In short:

- **Verified facts:** the numbers in sections 2 and 3 above, each traceable to a file.
- **Limitations:**
  - one synthetic corridor, incident type, decision time and action menu; 8 test seeds;
  - the audit evaluates the conventional Twin **with an imposed incident belief**, not online inference;
  - the event engine never adopted an incident naturally;
  - the assimilation and posterior are uncalibrated;
  - no live clearance, recovery or DEGRADED coverage;
  - the missing-queue evidence is N = 4 and descriptive;
  - the calibration discrepancy is not a lower bound and is never subtracted;
  - split regret is relative to an oracle chosen on M₁.
- **Interpretations:**
  - the results are consistent with compensating errors: the persistent-blockage belief partly offsets the missing incident history;
  - historical state supports an inherited-state explanation of duration sensitivity;
  - decision agreement and benefit accuracy can diverge.
- **Unproven hypotheses:**
  - the queue deficit alone causes the bias;
  - a point-blockage successor would infer incidents reliably;
  - history replay would improve online forecasting or ranking;
  - transfer to real traffic or other scenarios.

## 5. Deviations and process record

- **Design freeze moved forward** from 2026-10-16 to 2026-10-06 on the user's instruction, before any test result existed.
- **Pre-collection tooling fixes** (none to the method), made after Codex NO-GO reviews (rounds 1–3) and before any frozen result was seen:
  - enabling the production seeds;
  - a field-based seed check;
  - one process per job in the RNG check;
  - an RNG record bound to provenance, code fingerprint and snapshots, enforced before branches and before metrics;
  - measured blocker placement and D300 release records required;
  - an analyzer that takes its seed set from the manifest and does not invent status.

  The frozen method files are byte-identical to the freeze manifest.
- **Earlier audits** (development, sensitivities, missing-queue) reused pool processes across branches, a deviation from "a new process per branch". Fresh-process re-runs of sampled rows reproduced the stored J and digests exactly, so no number changes. The frozen audit used one process per branch.
- **Post-freeze defects:** none found. `docs/post-freeze-defects.md` was not needed.
- **One post-collection test update** (not a method change): `test_seed_check_frozen_seeds_clean` asserted that seeds 4501–4508 were unused. That state ended with collection, so the test now asserts the seeds are recorded as consumed. The pre-collection result is preserved in `results/frozen_audit/seed_check.json`.
- **Worker reports:** two reports misprinted numbers while the underlying data were correct (an agy-flash smoke table, and dsh's pooled medians in the replay-diagnosis report). Every quoted number here was recomputed from raw.

## 6. Reproduce

```
cd D:/CityCom-astra
set CITYPULSE_NET=blite & set CITYPULSE_BLITE_REV=5 & set CITYPULSE_REROUTE=0 & set OPENBLAS_NUM_THREADS=1
python -m pytest -q tests                                                  # 222 passed, 3 skipped
python -m citypulse.experiments.frozen_audit_analyze analyze --dir results/frozen_audit
python results/frozen_audit/crosscheck_claude/indep_audit.py results/frozen_audit/raw.parquet belief=B
python final/demo/decision_card.py --seed 4501
python final/figures/generate_figures.py ; python final/tables/build_tables.py
```

A full re-collection would use `python -m citypulse.experiments.frozen_audit prepare|twoworld|rngcheck|branches|statehistory --out <new dir>`. It needs fresh seeds: 4501–4508 are now used.
