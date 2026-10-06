# Decision 2026-10-05: records, submission scope, and the plan to the design freeze

Decision-maker: Codex (gpt-6.1-sol), read-only. The ruling is quoted in full in `~/.claude/runs/D--CityCom/20261005-1131-codex-sol-auditpilot2/out.md`.

## Records

**Offline decision audit** (`results/audit/report.md`, ab9d9f2). The numbers are **provisional** until the two defects below are fixed.

> Eight-seed offline hypothesis-world audit: A3 selected on 8/8 seeds; M₁ oracle agreement 7/8; ranking ρ = 0.85, τ = 0.75; split regret 0.03 veh·h. Benefits were optimistic: signed BEE +1.63 [1.04, 2.22], versus calibration floor 0.18. Zero execution failures. Three seeds missed the 120-s latency allowance; timestamps remain unchanged.

- This supports scenario-specific decision fidelity, not deployable efficacy.
- Subtracting the floor does not establish a causal "structural gap".

agy-pro's four "blocking" items were adjudicated as **not defects**, and Codex concurred:
- rerouting is disabled in both worlds;
- the duration mismatch is preregistered;
- no prior actions need restoring;
- split regret correctly evaluates the M₁-selected oracle on M₂.

**Two defects qualify the audit** (found by Codex, verified by Claude in the code):
1. **RNG check:** `citypulse/experiments/decision_audit.py:269-300` compares r = 1 against r = 2, which changes the demand draw **and** the SUMO seed together. It therefore does not isolate the seed, as the preregistration requires.
2. **CRN statistic:** `decision_audit.py:528-536` correlates the action-cost profiles *between replications* (`pivot.T.corr()`). The intended statistic is the correlation of action costs *across paired replications*, together with the variance reduction it buys.

**Pilot 2** (`results/event_pilot2/report.md`, 1cf2b14):

> No natural adoption in three primary INC runs; forecasts equal CONV. MAP hypotheses included demand and fault, never incident. NOI produced zero alarms. Forced runs verified replacement and clearance mechanics, but cleared prematurely in 3/3; only 1/4 recovery spells completed normally. One subsequent false adoption depended on forced history. DEGRADED's 900-s exit is unit-verified, not live-verified.

The restriction-recording fix is legitimate. Mechanics success does not establish inference accuracy.

## Submission scope (deadline 2026-10-25)

A laboratory prototype centred on decision auditing and verified replay mechanics.

- **Allowed claims:** laboratory mechanics, and bounded, scenario-specific decision fidelity.
- **Excluded claims:** reliable inference, accurate benefit prediction, real-world effectiveness, and event-assimilation superiority.

## E\*

**E\* does not run in its current gated form.** It is replaced by the paired replay diagnostic below.

Reopening it requires all of:
- a newly preregistered, independently qualified controller successor (not relaxed NA-300 criteria);
- frozen scenarios, metric and meaningful-effect threshold;
- identical observation streams;
- untouched test seeds.

## Plan to the freeze (each item ≤ 1 day of implementation, using existing runners)

| Dates | Work |
|---|---|
| Oct 6–7 | Isolate the SUMO seed with demand fixed (and demand with the SUMO seed fixed). Recompute the paired-action CRN and the variance reduction. |
| Oct 8–9 | Offline one-factor audit sensitivities: incident duration, blockage position, demand factor. Keep the splits and the calibration floor. Neither bias nor robustness may be attributed without these contrasts. |
| Oct 10–12 | Matched-observation replay diagnosis of the onset/location mismatch and of fault competition. Truth-assisted variants are labelled offline positive controls. |
| Oct 13–15 | Fresh INC/NOI/SHK/DET development runs, measuring natural adoption, false adoption, premature clearance, forecasts and exclusions. DEGRADED exercised live. |
| Oct 16 | Design freeze. |
| Oct 16–18 | The frozen audit on fresh test seeds. |
| Oct 18 | Results freeze. |

## Revision 2026-10-05 evening (Codex ruling `~/.claude/runs/D--CityCom/20261005-2000-codex-sol-diagreview/out.md`)

The replay diagnosis is done (3b5e575; corrections in `results/replay_diag/corrections.md`). The online method keeps R_E and the alarm − 600 s onset through the freeze; R_P is reported as a diagnosed alternative. Revised order:

| Dates | Work |
|---|---|
| Oct 5–6 | Missing-queue test preregistered (`docs/oct11-missing-queue-plan.md`, 302152e); implementation, gates, pilot. |
| Oct 13–14 | Complete the missing-queue grid. Alongside: fresh unchanged-method INC/NOI/SHK/DET development runs (needs its own preregistration first). |
| Oct 15 | Natural adoption, clearance, forecast, exclusion and live DEGRADED coverage; reconcile claims, corrected audit records and the duration sensitivity. |
| Oct 16 | Design freeze: R_E and the existing onset rule frozen; R_P successor requirements documented. |
| Oct 16–18 | Frozen audit on untouched test seeds; results freeze Oct 18. |

## Completion 2026-10-06

The design freeze was moved forward to 2026-10-06 on the user's instruction (`docs/freeze-2026-10-06.md`). The frozen test audit ran once on seeds 4501–4508 (results `aa7de30`). It replicated the development audit's scenario-specific pattern: A3 8/8, oracle agreement 7/8, BEE +2.16 [1.74, 2.59], regret −0.03, Spearman 0.825. Final evidence package: `final/` (`FINAL_REPORT.md`, `CLAIMS.md`). No core experiment remains (Codex ruling `~/.claude/runs/D--CityCom/20261006-1450-codex-sol-finalresult/out.md`).
