# 《城脉·涟控》 — method summary (as frozen 2026-10-06)

A laboratory prototype of an **event-aware traffic digital twin** with an **offline decision-fidelity audit**, on a synthetic corridor shaped like Kwun Tong Road / Kwun Tong Bypass (Hong Kong). Frozen record: `docs/freeze-2026-10-06.md` (+ Amendment A), manifest `results/freeze/freeze_manifest.json`.

## Two worlds, one firewall

| | Proxy ("real world", hidden) | Twin (the system under test) |
|---|---|---|
| Simulator | SUMO 1.27.1, net5 corridor | SUMO 1.27.1, same network |
| Drivers | IDM, `pdist` | Krauss, `tdist` (deliberate structural mismatch) |
| Demand | synth5 route file | Poisson-thinning candidate stream, TKO factor 0.85, normal assimilation NA-300 |
| Incident | `ktb_n1`, lanes 0–1 blocked at 900 m, 4,500–5,400 s | unknown; must be inferred or assumed |
| What it sees | everything | **only sensor messages**: 14 of 21 detectors (`drop_every_3rd`), 30-s q/v/o with noise (CV 0.10, 3 km/h, 1.5 pt) and 5 % loss |

The Twin never reads Proxy state; the firewall is checked by test (event-pilot check 1).

## Online layer: event-aware assimilation (frozen, reported as a mechanics prototype)

1. **Trigger:** a bottleneck index B on the detector pair (AID02109, AID02111) ≥ 3 at two consecutive 30-s ticks.
2. **Hypothesis library (20):** 10 incident (3 locations × lanes × speed factor), 4 demand step, 6 detector fault; family priors 1/3.
3. **Replay scoring:** each hypothesis is replayed from a pinned Twin snapshot (onset = alarm − 600 s) in its own SUMO process; residuals on identical 120-s block support; tempered posterior (β = 0.25).
4. **State machine:** NORMAL → SUSPECTED_EVENT → (adoption if incident MAP with gap > ln 10) EVENT_ASSIMILATION → clearance test → RECOVERY; DEGRADED for unresolved anomalies (exit at +900 s); detector-fault and demand paths return to NORMAL.
5. **Adoption** replaces the live Twin state with the hypothesis replay; clearance lifts it.

## Decision layer: counterfactual branching

At decision time t_d = 5,100 s the Twin forks 5 infrastructure actions — A0 none; A1 incident signal plan; A2 VMS diversion (assumed compliance 0.30); A3 = A1 + A2; A4 = A2 with stronger message — and predicts each action's KPI J = total time spent (veh·h) over the next 15 min. Actions have identical semantics in both worlds (signal programs, VMS + per-vehicle hashed compliance), so no Twin vehicle IDs or routes cross the firewall.

## Offline decision-fidelity audit (the main evidence)

For each Proxy seed, the same 5 actions are executed **in the Proxy** from its own t_d state (true compliance 0.35, true incident) to obtain the oracle. Common random numbers within a replication, independent future-demand draws per replication, selection/evaluation split (Twin R₁ select, R₂ evaluate; Proxy M₁ oracle, M₂ evaluate), every branch in a fresh process from an RNG-stripped snapshot.

- **BEE** (benefit-estimation error) = Ĝ_T(a\*) − G_P(a\*), predicted minus realised gain of the chosen action.
- **Regret** = J̄_P(a\*) − J̄_P(oracle) on M₂.
- **Ranking agreement** Spearman/Kendall, Top-1.
- **Calibration floor**: the same procedure with the Proxy standing in for the Twin — the Monte-Carlo noise level of the instrument.
- Twin belief B: a point blockage at the detector-segment midpoint persisting through the horizon; D300 (truth-assisted control): the same, cleared at the true time.

## Diagnostics that shaped the claims

- **Replay diagnosis** (pilot streams): incident adoption is limited by the incident representation (whole-edge closure), the onset estimate and competition from demand/fault hypotheses.
- **Missing-queue test** (preregistered, 4 seeds): the conventional Twin carries no incident history at t_d; restoring it cut the truth-duration gain error from 4.16 to 0.90 veh·h — the baseline's good decisions are consistent with compensating errors.
- **Development runs** (48 runs, 4 scenarios): no natural incident adoption; demand-shock (as realised, +5–8 %) and stuck-at-normal sensor faults never trigger.

## Process

Every experiment was preregistered and reviewed before it ran (decision-maker: an independent model, read-only); negative results recorded as negative; results recomputed from raw outputs before quoting; development and test seeds disjoint; the test (frozen) audit run once, after the freeze.
