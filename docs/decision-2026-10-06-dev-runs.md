# Decision 2026-10-06: development-run results, freeze, claim boundary for the event engine

Ruling: `~/.claude/runs/D--CityCom/20261006-0430-codex-sol-devresult/out.md` (Codex, read-only). Plan: `docs/oct13-dev-runs-plan.md` rev 2. Results: `results/dev_runs/` (b06513a). Instrument checks: `results/dev_runs/checks/` (3d60548).

## Results (verified by Claude from the raw logs)

- 48/48 slots complete on the first attempt; the pairing check passed on all 24 EVT/CONV pairs; provenance was taken on a clean tree.
- **INC (EVT):** 13 suspected-event episodes (trigger-induced entries) and 25 successful library evaluations, with **no natural adoption** (0/6 runs). Descriptive only, not preregistered: the MAP was a fault in 13 evaluations, demand in 8 and an incident in 4. All 4 incident MAPs were `inc_ktb_n1_k1_s1`, with gaps 0.08–0.18 < ln 10; these are dependent evaluations, not identifications. Exclusions: `obs_invalid` 726 and `partial_block` 1,470 across the 25 evaluations (retained |O| 135–216).
- **NOI / SHK / DET (EVT):** no alarm and no library evaluation in any of the 18 runs. Identification is N/A without adoption, and non-incident handling is **untested** (no evaluation).
- **No live coverage** of clearance, RECOVERY or DEGRADED in any run.
- **Forecasts:** the Twin predicts 0 halting vehicles on `ktb_w3` + `ktb_n1` at every issue, so EVT and CONV are identical. INC MAE is 20.6 (5-min, 48 cells per arm) and 18.8 (15-min, 42 cells), all underprediction. In NOI/SHK/DET the truth is 0 on these edges, so the 0 MAE there establishes no general forecasting accuracy.

## Instrument checks (Codex blocking items, both done)

- **Forecast instrument (agy-flash, spot-checked by Claude): pass.** Nine independent readouts (3 runs × issues 4,800/5,100/5,400) loaded the snapshots at the right time with 287–350 vehicles; vehicles on `ktb_w3`/`ktb_n1` were at free-flow speed and had 0 halted, matching the saved predictions. All 768 saved cells reconcile: err = pred − truth; target times are right; truth equals the Proxy's `halting_sum` (Claude re-read `evt_inc_4401`, where 5,700 s gives 126). The cell counts are 48 and 42 per arm and scenario. The zero predictions are a property of the Twin state (no restriction, no incident history), not an instrument artefact.
- **SHK/DET exposure (dsh, spot-checked by Claude):**
  - **DET is injected exactly.** AID02109 is constant, valid, and equal to its last pre-4,500 reading over 4,500–5,400 s in all 6 seeds. The stuck value is a normal reading, so B stays below 2.9: a stuck-at-normal fault leaves no bottleneck signature.
  - **SHK is injected only weakly in realised terms.** `proxy_shock.rou.xml` schedules +29 % upper-route departures in the window (724 vs 561). Realised flow at the corridor detectors rises only 5–8 % (AID07105 733 vs 696 on seed 4401; Claude re-read it); the rest is spread later. There was no halting on `ktb_w3`/`ktb_n1`, and B reached ≥ 3 at most at isolated single ticks (never two consecutive ticks).
  - So SHK did not test the trigger against a realised +30 % shock. "SHK did not alarm" is reported with this realised magnitude, not as "+30 %".
  - B, recomputed from `twin_log` and the event sigma, equals the logged B at every tick of the 18 non-INC runs.

## Claim boundary for the event engine (blocking for the submission)

Permissible: "On six fresh incident development seeds, the unchanged engine initiated 13 suspected-event episodes and completed 25 library evaluations, with no natural adoption. EVT and CONV had identical queue forecasts on the prescribed cells."

Across the corrected pilot records, the replay diagnosis and these runs, claim **verified laboratory replay and state-management mechanics and documented inference limitations**. State explicitly:
- SHK and DET produced no G4 alarm under the tested conditions: DET stuck-at-normal, and SHK with a realised corridor flow increase of 5–8 %. Neither handling pathway was exercised. Do not generalise to every shock or detector fault.
- The fresh runs give no live clearance, recovery or DEGRADED coverage.
- The forced pilot-2 runs covered replacement, clearance and recovery mechanics. All three primary forced episodes released prematurely, and only one of four recovery spells completed normally.
- **DEGRADED's scheduled exit was not covered live, even in forced pilot 2;** its evidence is unit-only (`results/event_pilot2/evidence/check10_degraded.json`).

The corrected replay diagnosis is retained as conditional offline evidence. Excluded: reliable inference, event-assimilation superiority, deployment.

## Freeze (2026-10-16)

Freeze the method unchanged: R_E, the alarm − 600 s onset, the library, the thresholds and the controller. Do not promote R_P, lower thresholds, force coverage, or add outcome-driven runs. Before the freeze, only demonstrated instrument corrections, reporting checks and claim wording may change, with the originals preserved. Remaining effort goes to the frozen audit (`docs/oct16-frozen-audit-plan.md`) and the write-up, which gets a coverage-and-claims table. In the write-up, the two-edge forecast halting counts are distinguished from the audit's wider Q, pending and occupancy measures.
