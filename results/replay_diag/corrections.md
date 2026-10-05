# Corrections to `report.md` (2026-10-05, after verification and Codex review)

Review: `~/.claude/runs/D--CityCom/20261005-2000-codex-sol-diagreview/out.md`. Cross-family second opinion: `~/.claude/runs/D--CityCom/20261005-2002-agypro-diagreview/out.log`. Counts recomputed by Claude from `raw.parquet` with β = 0.25; they match `summary.json`.

1. **Pooled medians.** The report's "median gap" and "median incident posterior" pool the 13 INC and 9 NOI evaluations. INC-only median gaps: V0 −2.05, VP 0.37, VT −0.13, VPT 2.04, VPL 0.03, VPTL 1.71, VNF −2.05, VPTLNF 1.71.
2. **"R_P never past ln 10 alone" is false.** VP's incident-vs-demand gap exceeds ln 10 on two evaluations (5.16 at `inc_4101_t5160`, 4.26 at `inc_4102_t5040`), but a fault hypothesis holds the MAP there, so neither would adopt.
3. **"The demand family, not the fault family, is the binding competitor" is too broad.** Removing the fault family does not rescue V0 (its gap stays below threshold), but faults bind under VP (item 2). V0 MAP families over INC: 6 demand, 7 fault.
4. **R_P is not strictly necessary and onset correction is not universally necessary:** VT adopts 1/13 under R_E; VPL adopts 3/13 at the logged onset. The location contrast also changes per-member priors, so it is not geometry alone.
5. **Onset is requested, not exact.** R_P blockers stop 4–18 s after the requested onset.

## What may be claimed

On three recorded INC streams, matched-observation replay identified sensitivity of incident adoption to incident representation, onset and location. Combining point blockage with the truth-assisted onset raised would-adopt evaluations from 0/13 to 6/13. All variants stayed negative on nine synthetic NOI evaluations. These are dependent evaluations conditional on the original snapshots, histories, down-weights, library and β = 0.25; they are hypothetical decisions, not controller trajectories, and the NOI result is not a false-adoption rate.

## Decision on the online method (Codex, agreed by agy-pro)

R_E and the existing onset rule (alarm − 600 s) stay through the design freeze. R_P is reported as a diagnosed alternative and R_E as a limitation. An R_P successor needs its own preregistration, including an observation-only onset rule, and two engine changes: `_lift_spec_at` does not remove point blockers, and `restriction_present` checks only lane disallowance.
