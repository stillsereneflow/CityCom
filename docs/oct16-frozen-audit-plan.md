# Frozen offline decision audit on fresh test seeds: preregistered before any run (2026-10-06, revision 1, Codex ACCEPT with non-blocking notes folded in)

Roadmap: `docs/decision-2026-10-05-roadmap.md` (Oct 16–18). Requirements: `docs/decision-2026-10-06-missing-queue.md` ("Freeze"), from the Codex ruling `~/.claude/runs/D--CityCom/20261006-0000-codex-sol-mqresult/out.md`, question 3. Base protocol: `docs/oct6-audit-and-pilot2-plan.md` part A, with the RNG and CRN corrections of `results/audit/v2/report.md`.

## Purpose and claim boundary

Measure, on test seeds no development step has touched, the decision fidelity of the **conventional Twin as frozen on 2026-10-16**. This is a confirmation of a laboratory, scenario-specific result: one corridor, one incident type, one decision time, the H_G5 hypothesis world. The submission may report these numbers as such. It may not present them as reliable incident inference, accurate benefit prediction in general, real-world effectiveness, or event-assimilation superiority (`decision-2026-10-05-roadmap.md`, submission scope). The development audit's numbers (seeds 4201–4208) stay reported unchanged beside these, never pooled with them.

## Audited object, frozen

- Code: the commit at the design freeze. `results/frozen_audit/provenance.json` records `git rev-parse HEAD`, a clean `git status --porcelain` for `citypulse/` and the driver, and the sha256 of `citypulse/branching/audit_engine.py`, `citypulse/experiments/decision_audit.py`, `citypulse/twin/service.py`, `citypulse/twin/demand_stream.py`, `citypulse/proxy/service.py`, the driver, both sigma JSONs and every network, detector, demand, vehicle-type and signal file the commands load, plus the effective command lines. No source file under `citypulse/` changes during collection.
- Scenario: net5/synth5, 7,200 s. Proxy incident `ktb_n1` lanes 0–1 at 900 m, 4,500–5,400 s.
- Twin: CONV (NA-300, unqualified), factor 0.85, Twin seed 2, demand seed 202, no event engine.
- Decision time t_d = 5,100 s; horizon 900 s; actions A0–A4; KPI J = total time spent.
- Twin belief **B** (primary): H_G5 point blockage at 755.3 m, lanes 0–1, persistent through the horizon, inserted at t_d (as the development audit).
- Replications: Twin R₁ = 1–3 (select) and R₂ = 4–6 (evaluate) with D_T(r) and SUMO seed r; Proxy M₁ = 1–3, M₂ = 4–6 with D_P(m); calibration (Proxy-as-Twin) 7–12. Snapshots without RNG state, a new process per branch. All rules of part A "Future-replication rules" apply unchanged.

## Seeds

Fresh Proxy test seeds **4501–4508** (N = 8, the development audit's N). Before launch, check that no run directory, JSON `seed` field or Parquet `seed` column under `results/` uses them; write `results/frozen_audit/seed_check.json`. 6001–6008 stay reserved and untouched.

## Estimands (per seed, then over the 8 seeds; definitions exactly as part A and audit v2)

Primary, belief B:
1. a\* on R₁ and the Proxy oracle on M₁; Top-1 agreement.
2. **BEE** = Ĝ_T(a\*) on R₂ − G_P(a\*) on M₂: signed, absolute, relative to J̄_P(A0).
3. **Split regret** J̄_P(a\*) − J̄_P(oracle) on M₂, and Regret_rel with the part A denominator rule.
4. Spearman ρ and Kendall τ between the Twin (R₂) and Proxy (M₂) rankings of A0–A4.
5. The Monte Carlo calibration floor from the calibration branches, reported beside BEE.
6. Paired CRN: corr(a) and VR(a) as in audit v2, per world.

Summaries: paired t 95 % CI over the 8 seeds (primary) and a percentile bootstrap as a check, as part A. Unsplit versions beside. No acceptance threshold: this is a measurement, reported as it comes out.

Secondary, labelled **truth-assisted offline positive control**: belief **D300** (the same blockage, cleared at 5,400 s, by resume after the 5,400-s step as in `audit_engine`; release verified, and a missing blocker or failed resume is a technical failure). Estimands 1–4 for D300, plus the fixed-A3 gain Ĝ_T(A3) on R₂ under B and D300 against G_P(A3) on M₂. No method, parameter or reporting choice is selected or tuned using D300; its action is selected on R₁ and evaluated on R₂.

## Descriptive state-history check (no gating)

From the saved t_d snapshots, per seed, for the Proxy and the Twin:
- incident-history status (Proxy: incident active since 4,500 s; Twin: none, by construction of CONV);
- Q components as defined in `docs/oct11-missing-queue-plan.md` (halted ordinary vehicles on `ktb_w1`, `ktb_w2`, `ktb_w3`, `ktb_n1`, blockers and `incident_*` excluded; pending vehicles from the saved state or meta, routes through those edges), the upstream spillback edges of `results/missing_queue/upstream_edges.json`, and all vehicles on `ktb_n1` regardless of speed;
- per branch: actual blocker placement (lane, position, stop time) and, under D300, clearance evidence.

This check is descriptive. It must not select seeds, tune anything, or gate publication.

## Order, failures, budget

1. Seed check and provenance (clean tree).
2. Two-world runs for 4501–4508; alarm time per seed recorded (t_d stays 5,100 s whatever the alarm).
3. RNG isolation check (audit v2 protocol) on seed 4501, before any metric.
4. Branches: Twin B and D300 (2 × 8 × 6 × 5 = 480), Proxy 240, calibration 240; at most 8 in parallel.
5. Raw J, digests, blocker evidence and queue rows go to `results/frozen_audit/raw.parquet` before any summary.
6. A seed's metric needs the complete 5 × 6 grid for that world and belief; failures are counted by reason and never averaged. An infrastructure failure may be rerun once with identical inputs, recorded.
7. Every metric is computed before anyone looks at a summary. Negative or unflattering results are reported as they are.

Implementation requirements (Codex review `~/.claude/runs/D--CityCom/20261006-0310-codex-sol-frozenprereg/out.md`, accepted with these notes):
- **A new process per branch, literally:** the existing helpers (`audit_engine.run_twin_branch_jobs`, `run_proxy_branch_jobs`) reuse spawn-pool workers across branches. Use `maxtasksperchild=1` with `chunksize=1` (or one spawned process per job), including the serial path. (For the earlier audits this was a deviation from "new process per branch". Evidence that it did not change outputs: branches re-run one per fresh process reproduced the stored J and digests exactly. That covers 3 development-audit rows and 1 missing-queue row re-run by Claude, plus dsh's 25-row compat check.)
- The seed check inspects JSON and Parquet seed fields, not only names, and does not skip audit paths.
- Every required world has unique action–replication keys, finite J and `status == "ok"`. Actual N and exclusions are reported per metric; paired comparisons use common complete seeds; intervals are omitted when N < 2.
- Pending counts that are unavailable are reported as unknown, never as zero. The calibration floor stays beside BEE, with no subtraction and no causal-gap interpretation.

Budget: implementation half a day (existing runners: `decision_audit.py`, `audit_engine.py`, `missing_queue.py`'s queue reader); collection under 2 hours; analysis half a day.
