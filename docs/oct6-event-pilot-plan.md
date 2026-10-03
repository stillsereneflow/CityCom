# Oct 6: event-assimilation mechanics pilot. Not E\*. Fixed before any pilot run (2026-10-03 21:10)

Decision-maker: Astra, read-only. The ruling is quoted in full in `~/.claude/runs/D--CityCom/20261003-2058-codex-astra-na300/out.md`.

## NA-300 record (as ruled)

- NA-300 is **NOT QUALIFIED** under `docs/na300-qualification-plan.md`.
- **Criterion 1 passes:** the matched-block estimate is **−115 veh/h [−126, −103]**. agy-flash's −129 [−142, −116] comes from a differently blocked analysis and is retained as such.
- **Criterion 2 fails** on 5 of 8 seeds. Describe it as upward drift with occasional reversals, consistent with slow convergence, not oscillatory instability.
- Acceptance is not relaxed retrospectively.

Evidence: `results/assim/na300/report.md` (4a1f2c1).

## Scope

This is a reduced event-assimilation mechanics pilot. No comparative efficacy claim is made.

### Scenario

- net5/synth5, 7,200 s.
- Proxy-only incident: `ktb_n1`, lanes 0–1 blocked at 900 m, 4,500–5,400 s.
- Twin TKO base factor 0.85 in both arms.
- Actions are held at A0 (no control action).

### Arms

| Arm | Twin |
|---|---|
| **CONV** | NA-300, explicitly unqualified, with `--assim normal300 --boundary-detector AID07106 --sigma-json results/assim/na300/sigma300_dev.json` |
| **EVT** | The same NA-300 beneath event-aware assimilation (below) |

### Seeds

- Proxy development seeds 4001–4003; Twin 2/202.
- **6001–6008 stay untouched.**

### Scenarios per seed

All are paired across both arms:

| Scenario | Description |
|---|---|
| **INC** | The incident above |
| **NOI** | No incident |
| **SHK** | +30% demand shock, 4,500–5,400 s (`synth5/proxy_shock.rou.xml`) |
| **DET** | Proxy sensor fault: AID02109 reports a stuck constant (its last valid reading before 4,500 s) from 4,500 to 5,400 s. Applied to emitted observations only, never to truth. |

That is 2 arms × 4 scenarios × 3 seeds = 24 two-world runs.

## Event-aware assimilation (mandatory components; report2 §G.4–G.5, §H)

### Trigger

The corrected G4 rule: the bottleneck index B on the pair (U, D) = (AID02109, AID02111) is ≥ 3 at two timestamps exactly 30 s apart, and a missing interval resets the streak.

- B = 0.5·(r_U^o − r_D^o) + 0.5·(r_D^v − r_U^v), with r = (obs − twin)/σ_i^x.
- σ_i^x = 1.4826·MAD of the residuals from the biased-OL development runs `results/assim/na300/ol_4001..4003` (t ≥ 900 s).
- CUSUM is deferred.

### Regional freeze

On entering SUSPECTED_EVENT, freeze m of every entry whose routes pass the candidate segments (here `tko_insert`). Unfreeze only as specified below.

### Hypothesis library: 16 hypotheses, family priors 1/3 each, uniform within a family

| Family | Members | Count |
|---|---|---|
| Incident | 3 locations (the trigger segment `ktb_n1` at pos 755; the upstream neighbour `ktb_w3` at its midpoint; the downstream neighbour `ktb_n2` at its midpoint) × 2 severities (k, s) ∈ {(1, 1.0), (2, 0.6)}. For 2-lane `ktb_n2`, use (1, 1.0) and (1, 0.6), so no edge is fully closed. Lanes are closed from lane 0 upward; s scales the remaining lanes' max speed. | 6 |
| Demand | TKO step at t_on, f ∈ {0.7, 0.85, 1.15, 1.3}, no capacity loss | 4 |
| Detector fault | i ∈ {AID02109, AID02111} × type ∈ {stuck (the last pre-t_on reading held), zero (q = o = 0, v missing), noise (c = 5 on that detector)}. The Twin replay has no event; the likelihood uses the fault model on detector i. No channel is dropped. | 6 |

### Onset and snapshots

- One provisional onset: t_on = alarm − 600 s. Truth is never used.
- Snapshot ring every 30 s, keeping 15 min; Δ = 60 s.
- Replays start from S(t_on − Δ).

### Scoring

Each hypothesis is scored in an independent SUMO process:
- load the snapshot;
- restore the control state, stream pointer, m and the base factor (CRN);
- apply the hypothesis from t_on;
- replay to the current t;
- read the Twin detector intervals for [t_on, t].

Then:
- **Residuals** are aggregated to 120-s block means per (i, b, x), x ∈ {q, v, o}, over the observed detectors.
- **Identical support:** the set O includes only blocks with all four intervals valid in the observations *and* non-null under **every** hypothesis. Report the exclusions by reason.
- **Likelihood:** logL_h = Σ_O [−½ (r̃/c)² − ln c], with c = 1, or c = 5 for the noise-fault detector.
- **Posterior:** P(h) ∝ π(h) · exp(β · logL_h), with **β = 0.25, explicitly uncalibrated.**

### Adoption

- If h\* (the MAP) is in the incident family **and** log P(h\*) − log max over the demand family > ln 10:
  - replace the live Twin state, i.e. load S(t_on − Δ) in the live Twin, apply h\*, and replay to t with the same stream;
  - go to EVENT_ASSIMILATION.
- **EVR** = 1 − SSE_{h\*} / min over the demand family of SSE, on O.

### State machine (report2 §H, CUSUM parts deferred)

**SUSPECTED_EVENT:**
- Evaluate every 60 s.
- If the demand family's total posterior is > 0.6 twice in a row: write the MAP f into m, unfreeze, log a false alarm, go to NORMAL.
- If the MAP is a detector fault: down-weight that detector, unfreeze, go to NORMAL.
- If n_eval ≥ 3: go to DEGRADED.

**DEGRADED:**
- Frozen entries update slowly (κ/4, deadband 2σ).
- Re-evaluate every 2 min; meeting τ_LR leads to EVENT_ASSIMILATION.
- After more than 15 min: go to NORMAL and log an "unexplained anomaly".

**EVENT_ASSIMILATION:**
- Every 60 s, evaluate H_clear(τ_c) for τ_c ∈ {t−60, …, t−300} (5 hypotheses) against the active h\*. Priors: 0.5 active, 0.5 spread over the clear hypotheses.
- After two consecutive evaluations with P_clear > 0.7: remove the restriction, replay from S(τ_c − Δ) with the restriction lifted at τ_c, reset the trigger streak, mask the pair's trigger until both ends have o < 15%, and go to RECOVERY.

**RECOVERY:**
- κ ramps from 0 to κ over 5 min.
- Stay at least 180 s.
- Exit to NORMAL when both ends have o < 15%, the unmasked B < 1.5 for 3 min, and at least 3 min have passed.
- A new trigger after unmasking leads to SUSPECTED_EVENT.

### Deferred

- CUSUM and onset search;
- larger grids and neighbourhood hill-climbing;
- learned localisation and a calibrated severity mapping;
- posterior calibration (β);
- the §G.6 decision-confidence machinery.

Severity is reported as a Twin configuration, not as a real-world severity.

## Artefacts (each run)

- m trajectories with freeze reasons;
- the state-machine trace;
- per evaluation: every hypothesis's logL, posterior, |O| and exclusions; the location and severity of h\*; EVR;
- timestamped 5-min and 15-min **queue forecasts**: halting vehicles on `ktb_w3` + `ktb_n1`, from Twin branches at every 5-min mark in 4,500–6,600 s, frozen, scored offline against Proxy truth;
- alarm counts and exposure per scenario;
- the recovery trace;
- raw logs.

## Mechanics PASS checks (each must hold; accuracy failures are reported as accuracy failures)

1. **Firewall integrity:** no truth field reaches the Twin.
2. **Deterministic replay:** the same hypothesis scored twice at the same t gives identical logL.
3. **Identical scoring support** across hypotheses: asserted.
4. **Effective capacity restriction:** under an incident hypothesis, the lanes are disallowed and the downstream flow drops relative to the no-event replay.
5. **Exact regional freeze:** m is constant while SUSPECTED, EVENT or DEGRADED, except for DEGRADED's slow rule.
6. **Threshold-respecting adoption:** adopted only if the log-posterior gap is > ln 10.
7. **Successful state replacement:** after adoption, the live Twin has the restriction, and its vehicle state equals the replay endpoint.
8. **Clearance rules:** two consecutive P_clear > 0.7, reset, masking, at least 180 s in RECOVERY, and the exit conditions.
9. **Non-incident rejection:** report adoption counts in NOI, SHK and DET.
10. **Bounded unresolved handling:** DEGRADED ≤ 15 min, no deadlock.

## Offline decision audit

This is **separate**. It shares the frozen snapshots only, with independent Twin selection/evaluation replications and Proxy oracle-selection/evaluation replications, and nothing feeds back into tuning. It is specified later.
