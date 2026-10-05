# Offline decision audit and second development pilot: preregistered before any run (2026-10-04)

Decision-maker: Astra, read-only. The ruling is quoted in full in `~/.claude/runs/D--CityCom/20261004-1117-codex-astra-pilot/out.md`. The cross-family review is `results/event_pilot/review_dsh.md`.

## Record of the first pilot (as ruled)

- **Mechanics, partial verification.** "All 10 passed" is withdrawn.
  - Checks 1–4 are supported. Check 3 establishes comparable support, not unbiased inference.
  - Check 5 is partial.
  - Checks 6 and 8 are unit-only.
  - Check 7 is a direct mechanics pass, not adoption-path validation. Its fixture used pos 503.1 m, while the pilot hypotheses use 755 m.
  - Check 9 passes as a reporting requirement, but DET is weak fault-rejection evidence.
  - Check 10 was **exercised live**: DEGRADED lasted 5,040–6,000 s = 960 s. That satisfies the prose rule ("after more than 15 min → NORMAL") but fails the checklist bound (≤ 15 min). The conflict is resolved for pilot 2 below.
- **Development accuracy is negative:** no INC adoption and no forecast improvement. The 40–180 values are posterior gaps against the demand family, not raw logL gaps against incidents.
- The observation-substitution fix (e253af5) was a legitimate implementation correction. Items (a)–(c) follow the declared method, so they are not implementation defects.
- **NA-300 remains unqualified.** Pilot success cannot unlock comparative E\* claims. Seeds 6001–6008 stay untouched.

## A. Offline decision audit (report2 §K, §L)

This audit measures decision fidelity, independent of the event pilot. Nothing feeds back into tuning.

### Scenario

- net5/synth5, 7,200 s.
- Proxy incident: `ktb_n1`, lanes 0–1 at 900 m, 4,500–5,400 s.
- Twin: CONV, i.e. NA-300 (unqualified), `--twin-base-factor 0.85`, Twin seed 2/202, no event engine.

### Seeds

Proxy audit seeds 4201–4208 (N = 8), fresh. Verify before launch that no result uses them.

### Decision point

- t_d = 5,100 s. This is the first 5-min mark after the corrected alarm (about 4,890–4,920 s) plus at least 120 s of computation latency.
- Both worlds save a snapshot at t_d: the Proxy with its incident state, which the offline harness may read; the Twin with its control state, stream pointer, m and base factor.
- The incident's scheduled end at 5,400 s is applied inside Proxy branches by the truth schedule. Truth is allowed offline only.

### Twin belief for branching

H_G5: a point blockage of `ktb_n1` lanes 0–1 at the midpoint of the observed detector segment (755.3 m), lasting until the end of the horizon. This is the same hypothesis as the frozen G5. It is labelled a hypothesis world, not inference.

### Actions

A0–A4 as in G5 (`citypulse/scenario_blite.py`, `citypulse/control/actions.py`): A0 none; A1 signal plan P_inc; A2 VMS diversion; A3 A1 + A2; A4 A2 with boosted compliance.

### KPI

**J = total time spent** (veh·h) over the 15-min horizon [t_d, t_d + 900]: Σ over steps of (running vehicles + pending insertions) × 1 s / 3600.

- This accounts for every vehicle, including entry waiting, with no sampling gap.
- It replaces the sampled timeLoss metric for the audit. The historical metric is kept separately.

### Replications (CRN within a replication: same snapshot, same future demand, same `--seed m` for all actions)

- **Twin:** R₁ = 3 selection replications choose a\* = argmin J̄_T over R₁. R₂ = 3 independent replications estimate Ĝ_T(a\*) = J̄_T(A0) − J̄_T(a\*).
- **Proxy:** M = 6 future replications per action from the Proxy t_d snapshot. Each uses a different `--seed` and a different future-demand draw: the Proxy demand stream for t > t_d is re-sampled per m from the same rates.
  - M₁ = {1, 2, 3} selects oracle = argmin J̄_P over M₁.
  - M₂ = {4, 5, 6} evaluates.

### Future-replication rules (blocking items added on review, 2026-10-05)

Review: `~/.claude/runs/D--CityCom/20261005-1034-codex-sol-auditprereg/out.md`.

1. **RNG.** Every audit branch (Twin, Proxy, calibration) is loaded in a **new process** from a snapshot saved **without** RNG state, on this one Windows platform.
   - **Verify before collecting data:**
     - (i) changing only the branch `--seed` changes the future stochastic trajectory;
     - (ii) identical snapshot, seed, demand draw and action reproduce identical outputs.
   - Record both checks in `results/audit/rng_check.json`.
2. **Twin future demand.**
   - Replication r uses a future-demand draw with seed `D_T(r) = 900000 + 1000·seed + r`, where r = 1..3 for R₁ and r = 4..6 for R₂.
   - The candidate stream for departures after t_d is re-sampled from the same rates (the thinning uniforms and route draws are regenerated from D_T(r)).
   - The snapshot's pending vehicles, m and factor 0.85 are preserved.
   - The draw is shared across A0–A4 within a replication; R₁ and R₂ draws are independent.
   - SUMO `--seed` = r.
   - The existing branch worker restores the same demand seed (`citypulse/branching/engine.py:69`), so the audit needs its own entry point.
3. **Proxy future demand.**
   - Preserve every vehicle running or pending at t_d.
   - Remove all departures scheduled after t_d, and insert a re-sampled stream from the same per-route rates, exactly once, with seed `D_P(m) = 800000 + 1000·seed + m`, m = 1..6.
   - Assert that no original future departure remains.
   - The same protocol applies to the Proxy-as-Twin calibration branches, with seeds m = 7..12.
   - Independent draws for selection and evaluation; SUMO `--seed` = m.

Non-blocking notes:
- For split Regret_rel, the denominator is the M₂ gain of the M₁-selected oracle, J̄_P(A0; M₂) − J̄_P(oracle; M₂), not a fresh minimum on M₂.
- Record each seed's alarm time (corrected G4 rule, applied offline to the Twin log) and confirm t_d − alarm ≥ 120 s. If it is not, report it; t_d stays fixed.
- Forced-adoption outcomes in pilot 2 are reported separately from natural adoption and forecasts.

### Metrics (per seed, then pooled over 8 seeds)

- **BEE** = |Ĝ_T(a\*) − G_P(a\*)| on M₂: signed, absolute, and relative to J̄_P(A0).
- **Regret** = J̄_P(a\*) − J̄_P(oracle) on M₂, plus Regret_rel. Do not report Regret_rel when its denominator J̄_P(A0) − min J̄_P < 0.5 veh·h.
- **Ranking:** Top-1 agreement; Spearman ρ and Kendall τ between Twin (on R₂) and Proxy (on M₂) rankings of A0–A4.
- **Unsplit** versions are reported beside, to show the selection bias.
- **CRN effectiveness:** the correlation of paired J across actions within each replication.
- **Summary:** paired t 95% CI (primary) and a percentile-bootstrap interval as a check.
- **Monte Carlo floor** (calibration control, labelled as such): repeat the Twin-side procedure using **Proxy** branches from the Proxy t_d snapshot with seeds 7–12 (R₁ = 7–9, R₂ = 10–12) in place of the Twin. The resulting BEE floor is reported beside BEE.

### Storage and order

All raw J(a; m) go to Parquet (`results/audit/raw.parquet`). Compute every metric before looking at any summary. Failures (locks, errors, missing snapshots) are counted by reason and are not averaged in.

### Acceptance

None. This is a measurement. Results are reported as they are; no efficacy claim is made.

## B. Second development pilot (event engine)

Development only. The original negative result is retained.

### The only change to the method: the incident grid

k ∈ {1, …, min(2, n_lanes − 1)} × s ∈ {0.6, 1.0}, at the same 3 locations:

| Location | Lanes | Hypotheses |
|---|---|---|
| `ktb_n1` | 3 | 4 |
| `ktb_w3` | 3 | 4 |
| `ktb_n2` | 2 | 2 |

That gives **10** incident hypotheses. Family mass stays 1/3, uniform within the family, so the library has 20 hypotheses.

**Unchanged:** locations, onset (alarm − 600 s), noise model (c = 5), β = 0.25, τ_LR, trigger, and all thresholds.

### Specification conflict resolved

DEGRADED exits at **entry + 900 s exactly**, scheduled independently of hypothesis evaluations, so DEGRADED ≤ 15 min.

### Integration coverage, all required

- **Live adoption and clearance:** at least one end-to-end run that enters EVENT_ASSIMILATION, replaces the live state, runs clearance evaluation, and either enters RECOVERY and exits, or reports why not.
  - If no natural adoption occurs, run a **labelled forced-adoption integration test**: the same INC scenario with the adoption threshold applied to a fixed h\* injected at the first evaluation. It exercises the downstream path only and is not evidence of inference.
- Check 7 is repeated on the actual pilot hypothesis location (755 m).

### Runs

- INC × fresh development seeds 4101, 4102, 4103: EVT arm, plus the CONV arm for forecasts.
- NOI × the same seeds, EVT only, as a false-adoption check.

### Artefacts and checks

As in `docs/oct6-event-pilot-plan.md`, with:
- every check labelled live, direct or unit;
- forecasts scored as before.

### Report

Adoption times, h\*, EVR, forecast errors (descriptive), and the checks table with honest labels.
