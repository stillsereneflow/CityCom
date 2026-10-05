# Matched-observation replay diagnosis of event inference: preregistered before any run (2026-10-05, revision 2)

Roadmap: `docs/decision-2026-10-05-roadmap.md`, Oct 10–12. This replaces E\* for now.

Revision 2 answers the blocking review `~/.claude/runs/D--CityCom/20261005-1557-codex-sol-diagprereg/out.md`.

## Question

On the **identical** recorded observation streams of the pilot-2 runs, which element of the declared hypothesis library and its replay physics prevents a natural incident adoption? The candidates are the incident **representation**, the onset estimate, the location grid, and competition from the fault family.

This is an offline diagnostic: nothing is tuned and the online method is unchanged. Truth-assisted variants are **offline positive controls**. None of their settings, and neither representation, may enter the online method without a new preregistration.

## Two incident representations

**R_E (as run).** `citypulse/branching/engine.py:146` `_apply_spec_at`: lanes 0..k−1 of the edge are disallowed **along the whole edge** from t_on, and the remaining lanes' max speed is scaled by s. The `pos` field has no physical effect.

**R_P (point blockage, position-sensitive).** From t_on, one stopped blocker vehicle is placed on each closed lane at `pos`, exactly as the audit's H_G5 does (`citypulse/branching/audit_engine.py:258-276`: a vehicle inserted at pos − 1 and stopped at pos). No lane is disallowed. The remaining lanes' max speed is scaled by s along the edge, as in R_E. This matches how the Proxy incident is represented.

**Qualification of R_P (blocking).** On `evt_inc_4101`, at its first logged evaluation:
1. Replay `inc_ktb_n1_k2_s1.0` under R_P at 755 m and at 900 m. The blocker placement (lane, pos, stop time) must be recorded and equal the requested values.
2. The replays must differ (different vehicle digest at t_eval and different observed-detector intervals).
3. Twice-repeated identical inputs must give identical outputs.

Record all of this in `results/replay_diag/qualify_rp.json`. If any part fails, stop.

## Inputs (frozen)

**INC runs:** `results/event_pilot2/runs/evt_inc_4101`, `evt_inc_4102`, `evt_inc_4103` (pilot-2 grid, 20 hypotheses):
- observations from `twin/twin_log.parquet`;
- logged evaluations from `twin/event_log.jsonl`;
- the **pinned episode snapshots** `twin/event_snapshot_<t>.xml.gz` with their JSON. These are the snapshots the online run replayed from, at t_on − 60 s.

**NOI controls:** seeds 4101–4103 are re-run with the identical EVT command (`results/event_pilot2/runs/evt_noi_410x/run_info.json`), adding Twin snapshots at 4,230 and 4,350 s. The re-run's `twin_log.parquet` must equal the stored one, which verifies identical observation streams. If it does not, report the difference and use the re-run's stream for both its snapshots and its observations.

## Per-evaluation fixed elements (held fixed across all variants of one evaluation)

| Element | INC | NOI synthetic episode |
|---|---|---|
| Start snapshot and restored metadata | the evaluation's pinned episode snapshot | snapshot 4,230 s |
| Scoring window | [logged t_on, t_eval] | [4,290, t_eval] |
| Evaluation times | as logged | 4,890 / 5,010 / 5,130 s, one episode |
| Provisional onset | logged t_on | 4,290 s (= imposed alarm 4,890 − 600) |
| σ | `results/event_pilot/impl/sigma_event.json` | same |
| Detector down-weights | those in force before that evaluation, reconstructed from the run's logged state transitions by the code's rule | none |
| Fault anchors | as the code builds them: the last valid pre-t_on reading | same rule, at t_on = 4,290 s |

The scoring window is independent of each hypothesis's onset, which only sets when the hypothesis is applied.

**Support:** O = the intersection, over **all variants and all their hypotheses**, of the valid, complete 120-s blocks within the scoring window. Reject an evaluation if O is empty. Report |O| and the exclusions by reason.

## Exact reproduction (blocking, before any comparison)

For every logged INC evaluation, V0 re-scored with the original pinned snapshot, σ, down-weights, anchors and **the original support rule** (the library-internal support, as run) must reproduce the logged MAP and every logL within 1e-6. If any differ, stop and report. The common-support comparisons below are a separate step.

## Variants (all scored on the common O and the fixed elements above)

| ID | Representation | Onset of incident hypotheses | Locations | Fault family | Label |
|---|---|---|---|---|---|
| V0 | R_E | logged t_on | as run (755, mid `ktb_w3`, mid `ktb_n2`) | yes | base |
| VP | R_P | logged t_on | as run | yes | representation diagnostic |
| VT | R_E | 4,500 s | as run | yes | truth-assisted control (onset) |
| VPT | R_P | 4,500 s | as run | yes | truth-assisted control |
| VPL | R_P | logged t_on | as run + `ktb_n1` 900 m (same (k, s) grid; incident mass 1/3 spread over 14 members) | yes | truth-assisted control (location) |
| VPTL | R_P | 4,500 s | as run + 900 m | yes | truth-assisted control |
| VNF | R_E | logged t_on | as run | **no** (mass 1/2 incident, 1/2 demand) | competition diagnostic |
| VPTLNF | R_P | 4,500 s | as run + 900 m | no | truth-assisted control |

Notes:
- **Demand hypotheses** keep their onset at the provisional onset in every variant; only incident hypotheses take the variant onset.
- **NOI:** 4,500 s is an **imposed control onset**, because NOI has no true incident.

## Outputs per evaluation and variant

- MAP hypothesis and family;
- the incident family's total posterior;
- gap = log P(best incident) − log max over the demand family;
- **would-adopt**: whether the MAP is an incident and the gap > ln 10;
- EVR, |O|, the snapshot used.

## Summary

Per variant, the would-adopt counts over INC evaluations and over NOI synthetic evaluations, the MAP-family distribution, and the median gap. **No inferential statistics:** this is a 3-run diagnostic. Report what moves the outcome, conditional on these streams.

## Order and storage

- The qualification and reproduction JSONs come first.
- Raw per-hypothesis logL rows go to `results/replay_diag/raw.parquet` before any summary.
- Replays run in new processes, at most 8 parallel.
- Failures are counted by reason.
