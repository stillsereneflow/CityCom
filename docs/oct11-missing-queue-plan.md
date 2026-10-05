# Missing-queue test: incident history × future duration in the Twin's decision branches (preregistered before any run, 2026-10-05, revision 2)

Revision 2 answers the blocking review `~/.claude/runs/D--CityCom/20261005-2045-codex-sol-mqprereg/out.md`: both Twin states come through the same restart; blocker reuse and clearance are qualified; the queue aggregate Q and the classification order are fixed.

Roadmap: `docs/decision-2026-10-05-roadmap.md` (revised order below). Base audit: `docs/oct6-audit-and-pilot2-plan.md` part A. Sensitivities: `docs/oct8-audit-sensitivity-plan.md`, results `results/audit/sens/report.md` (a61e2bc). Design ruling: `~/.claude/runs/D--CityCom/20261005-2000-codex-sol-diagreview/out.md`, question 3.

## Hypothesis under test

The conventional Twin at t_d = 5,100 s has no incident history: nothing in it has been blocked since the Proxy incident began at 4,500 s. Under the truth-assisted duration D300 (blockage clears at 5,400 s) the Twin's fixed-A3 gain is about 0 (R₂ mean 0.18 veh·h) against the Proxy's 5.13. Under the persistent blockage of the baseline belief it is 6.76. The hypothesis: the missing pre-t_d incident state, and the queue in it, explains the D300 collapse; the persistent-blockage belief compensates for it, so the baseline ranking may be right for the wrong reason.

Already known (descriptive, used seeds 4201–4208, from `proxy_halting.parquet`): Proxy halting on `ktb_n1` at 5,100 s is 8–30 vehicles; `ktb_w3` stays at 0 in [4,500, 5,100]. This is stated now so that it cannot be selected later.

## Design: 2 × 2, all Twin-side, Proxy unchanged

| Arm | Twin state at t_d | Future blockage in branches | Label |
|---|---|---|---|
| C-P | conventional (null replay through the restart below) | persistent through the horizon | baseline belief |
| C-D | conventional | clears at 5,400 s | truth-assisted duration |
| H-P | historical replay (below) | persistent | truth-assisted onset |
| H-D | historical replay | clears at 5,400 s | truth-assisted onset and duration |

Everything else is the base audit, unchanged: A0–A4, KPI J = total time spent over [5,100, 6,000], R₁ = 1–3 select, R₂ = 4–6 evaluate, D_T(r) future-demand draws, SUMO seed r, factor 0.85, H_G5 position 755.3 m, lanes 0–1, new process per branch from a snapshot with the RNG state stripped. Proxy branches M = 1–6 and calibration branches 7–12 as in the base audit.

### Twin states C and H: one restart protocol for both

A snapshot restart does not continue an uninterrupted trajectory exactly (`docs/d1-d4-validation.md`, section 7: divergence at the first 10-s checkpoint in every configuration, with or without saved RNG). So C is **not** the live `twin_state_5100`: both states come out of the same restart, and they differ only in the blockers.

- The live Twin run additionally saves a snapshot at **4,440 s** (pre-incident; with RNG state, as the live Twin saves it) and its meta.
- From it, two replays 4,440 → 5,100, each in a new process:
  - restore the original SUMO seed and demand seed, the stream pointer, the base factor 0.85 and m from the meta, and re-apply the control state; **never** call `init_signals` after loading;
  - the Twin's own demand stream continues from the saved pointer, so the demand submissions are the live run's;
  - the m schedule is replayed from the run's `assim_log.parquet`: at each logged tick, m is set **after** that tick's simulation step, as in `citypulse/twin/service.py:579-622`, including the 5,100-s tick;
  - no control actions (none were active before t_d in CONV);
  - **C:** no blockers. **H:** R_P point blockers `hyp_blocker_0/1` on `ktb_n1` lanes 0–1 at 755.3 m, added immediately after the 4,500-s step, by the same calls as `audit_engine._twin_audit_worker` (insert at pos − 1, stop at pos, lane changes off, stop duration ≥ 3,600 s).
- At 5,100 s (after the m tick) save the state and a meta with the same fields as `twin_state_5100.json`, plus the pending list and each pending vehicle's route, read in-process at that step. Then strip RNG as the base audit does.

**Blocking gates, per seed, before any branch:**
1. Running the C replay twice gives identical vehicle digest (`audit_engine.veh_digest`), pending list, stream pointer and m.
2. Both replays' demand submissions over [4,440, 5,100] equal the live run's (vehicle IDs and depart times from the stream), and the final pointer and m equal the live meta.
3. In H at 5,100 s, both blockers exist, sit on their requested lanes within 1 m of 755.3 m, and are stopped. Their stop times are recorded; the physical delay after 4,500 s is reported separately.

If any gate fails, stop and report. The live `twin_state_5100` is kept only as a descriptive comparator (its Q against C's).

### Blockers in branches

- **C arms:** the worker inserts the blockers at t_d as now.
- **H arms:** the blockers already exist in the loaded state. The worker must **reuse** them: no insertion, and it must assert that both exist, are on their lanes and are stopped after loading. Missing blockers are a technical failure, not data.
- **-D arms:** the blockers are resumed **after the 5,400-s step, before advancing to 5,401 s**, as the current audit branches do. The worker verifies that both are actually released (no longer stopped at the next step). `actual_clear_time` is written only when a resume actually happened; a failed release is a technical failure.
- Record actual blocker placement and clearance per branch.

### Seeds

Fresh Proxy seeds **4301–4304** (N = 4). Before launch, verify that no run directory, Parquet or JSON under `results/` uses them as a seed (a grep for the bare numbers hit only unrelated numeric values in `results/bounded/*` and `results/blite/probe/analysis.json`; the implementer re-checks by seed fields). Two-world INC runs as in the base audit, Twin snapshots at 4,440 and 5,100, Proxy snapshot at 5,100.

## Measurements

**Queue (state check).** At t_d, in the Proxy state, C, H and (descriptively) the live Twin state:
- **Q** = ordinary halted vehicles (speed < 0.1 m/s, blocker vehicles excluded) on `ktb_w1`, `ktb_w2`, `ktb_w3`, `ktb_n1`, plus pending vehicles whose routes traverse any of those edges. Components are reported separately.
- Pending vehicles come from the saved meta (Twin) or the state file (Proxy), never from `getPendingVehicles()` right after a load, which returns 0 until the first step.
- Queue extent and spillback: halted vehicles on a fixed upstream list, namely the edges upstream of `ktb_w1` on the TKO approach up to the network boundary, listed by the implementer from the network **before** any run and frozen in the results.

Also, in every branch (all worlds), the same counts at 5,100, 5,160, …, 6,000 s (16 timestamps, inclusive). J keeps its 900 one-second increments. Raw rows to Parquet.

**Primary.** Per seed, fixed-action A3 gain on R₂: Ĝ_T(A3) = J̄_T(A0) − J̄_T(A3), and Proxy G_P(A3) on M₂. Error e = |Ĝ_T(A3) − G_P(A3)|. Primary contrast: Δ_D = e(H-D) − e(C-D), per seed.

**Secondary.**
- The duration contrast Ĝ_T(A3; -P) − Ĝ_T(A3; -D) under C and under H (does history shrink the dependence on the duration belief?).
- a\*, signed BEE, split regret, Top-1, Spearman per arm, exactly as the base audit.
- Paired-action CRN on Twin rows.

## Predictions (stated before any run)

The two state conditions use only pre-action state at t_d, so they are independent of the gain error:
- **No initial deficit:** Q_P − Q_C ≤ 5 on at least 3 of 4 seeds (C above the Proxy also counts as no deficit).
- **Material restoration:** Q_H − Q_C ≥ 6 on at least 3 seeds that also have Q_P − Q_C > 5.

Classify in this order and stop at the first that applies:
1. **Inconclusive (technical):** a gate failed, or a required 5 × 6 grid is incomplete.
2. **No initial deficit:** the "missing queue" premise is false as stated; reported as such whatever Δ_D shows.
3. **Inconclusive (restoration):** material restoration fails. The replay did not restore the history; this is not a refutation.
4. **Support:** Δ_D < 0 on at least 3 of 4 seeds and mean Δ_D ≤ −1.0 veh·h.
5. **Refutation** of the material-improvement prediction: Δ_D ≥ 0 on at least 3 of 4 seeds, or mean Δ_D > −0.5 veh·h. The leading alternatives (Twin driver and capacity physics against the Proxy's, the demand factor) are then named as untested.
6. Otherwise **partial**, reported descriptively.

All four seeds are kept; no subset is ever selected using Δ_D. A negative result concerns this restoration at 755.3 m, not every missing-state explanation.

N = 4: descriptive, no inferential statistics; all per-seed values are reported. Full-state improvement supports an inherited-state explanation; it does not isolate the queue count as the only cause.

## Order, failures, budget

1. Two-world runs on 4301–4304 (Twin snapshots 4,440 and 5,100).
2. C and H replays, then the three gates (blocking).
3. Pilot: seed 4301, arm H-D, replication 1, A0 and A3; check blocker reuse, clearance at 5,400, and queue counts. Then the fixed grid.
4. Grid: 4 arms × 4 seeds × 6 replications × 5 actions = 480 Twin branches; Proxy 120 and calibration 120 branches. About 4–5 s each, 8-way parallel.
5. Raw J and queue rows go to `results/missing_queue/raw.parquet` before any summary. A seed–arm metric needs the complete 5 × 6 grid; failures are counted by reason, never averaged.

Budget: implementation one day, collection and analysis one day.

**Labels.** H arms are truth-assisted onset; -D arms are truth-assisted duration. All are offline positive controls; none is deployable, and no setting may enter the online method without a new preregistration.

## Out of scope

Loading the Proxy's state into the Twin (an alternative ceiling arm) is not run: the worlds use different vehicle types and driver models (IDM `pdist` vs Krauss `tdist`), so the loaded state would not be a Twin state.
