# Decision 2026-10-03b: B-lite with reconstructed demand is inadequate. Narrow to a synthetic two-route benchmark on net4.

Decision-maker: GPT-6 Astra, read-only consult. The ruling is quoted in full in `~/.claude/runs/D--CityCom/*-codex-astra-blite2/out.md`.

## Why

Predeclared grid 1.0…0.4 on net4 (`results/blite/grid4/report.md`): no scale passes G3. Pending at 0.4 was 8.3%, with a positive slope. G4 and G5 were **never tested**; they did not fail.

Astra's diagnosis is a demand–topology incompatibility, not proven excessive demand:
- Detector differences do not uniquely identify ramp arrivals.
- Concentrating the inferred exchange onto a few connectors adds an assumption.
- Pooled lane-flow percentiles neither establish corridor capacity nor validate 10.8k veh/h.
- The lane-capacity tests (`results/lanecap/`) do **not** justify changing the Proxy drivers to resemble the Twin.

So the fallback rule from decision D applies: narrow the experiment explicitly. Do not manufacture a pass by approaching empty traffic.

## What changes

The network stays as it is: net4, its detectors, the yellow-inclusive signals, the Proxy/Twin vehicle distributions and the branch machinery. No further widening or junction optimisation.

The demand becomes **scenario-assumed boundary conditions, not estimates**:
- 2,800 veh/h constant at `tko_in`;
- 75% bypass / 25% arterial, all to `out`;
- intermediate ramps at zero;
- 400 veh/h per cross-street stub.

The run keeps the 7,200 s horizon and the Proxy-only incident (`ktb_n1`, lanes 0–1, position 900 m, 4,500–5,400 s). Autonomous rerouting is disabled; diversion happens only through the VMS action.

Freeze the configuration before any comparative evaluation. **No further load search if it fails.**

## Gates

| Gate | Requirement |
|---|---|
| G1–G2 | Zero teleports and zero collisions. Exact conservation: scheduled = pending + running + arrived. |
| G3 | Incident-free, 3 predeclared seeds. Pending ≤ 2%. After warm-up, the running-count slope and every source-backlog slope ≤ 0.05 veh/s over every complete 15-min window. Report discharge and per-edge queues. |
| G4 | The existing sparse-sensor bottleneck threshold detects the incident. Matched no-incident and demand-shock controls quantify false alarms. Truth stays unavailable to inference and action selection. |
| G5 | VMS diverts ≥ 5% of the TKO stream. At least one action's paired delay difference vs A0 has a 95% CI excluding 0 across predeclared replications. Method superiority is **not** a gate. |
| Audit | Snapshots carry pending demand and controller state, and reload consistency is verified. Total delay includes entry waiting, and unfinished vehicles are reported. Selection seeds are kept separate from untouched audit seeds. Negative results are kept. |

## What we can claim

All claims are **conditional on exogenous synthetic boundaries**. This is a method benchmark on a Kwun Tong-shaped corridor, not a calibrated twin of Kwun Tong. The reconstructed TD observation profile stays in the report as context and for the congestion-pattern comparison, but it is not used as a fit target.

## Amendment 2026-10-03c: net5

Astra's ruling is quoted in full in `~/.claude/runs/D--CityCom/20261003-1823-codex-astra-entry/out.md`.

On net4 the synthetic G1–G3 failed, with the whole backlog at the `tko_in` source and the interior free-flowing. Two construction defects were demonstrated (`results/blite/synth/diag_entry*/report.md`):
- `tko_in` lane 0 could not reach the bypass;
- at diverge D, the two arterial turns were minor links yielding to the bypass straight movements.

net5 fixes both, and adds a 500 m, 3-lane insertion stub `tko_insert` (zipper merge to the 2-lane `tko_in`):
- **Entry:** exactly `0→0`, `0→1`, `1→2`.
- **Diverge D:** lane-preserving `tko_vms_0→tko_a1`, `1,2→ktb_w1`, with no crossing geometry.
- **Unchanged:** the demand (2,800 veh/h, 75/25).
- **New G3 series:** TKO pending plus stub occupancy.

If net5 had failed, the outcome would have been recorded as a negative result, with no further widening and no demand cut.

**Result** (`results/blite/synth5/g123_report.md`):
- G1 and G2 pass on all 3 seeds.
- Pending is 0%, all source backlogs are 0, and the TKO+stub slope stays within ±0.04.
- `tko_in` delivers about 2,850 veh/h.
- The 15-min running-count slope fails in seed 1002 (+0.054) and seed 1003 (+0.061).

**The original-protocol G3 verdict is FAIL, and that record is preserved.**

## Amendment 2026-10-03d: G3-v2 (post hoc, explicit)

Astra's ruling is quoted in full in `~/.claude/runs/D--CityCom/20261003-1850-codex-astra-g3slope/out.md`.

The running-count short-window slope does not isolate accumulation: all three seeds share one route file, and the positive windows coincide with rises in its scheduled departures. Astra judged the criterion defective as a test of sustained accumulation.

G3-v2 replaces **only** that gate:
- Per seed, fit an OLS slope of the running count over each closed interval [a, 7200], for a ∈ {900, 1800, …, 6300}.
- Every slope must be ≤ +0.05 veh/s.
- No smoothing, exclusions or pooling.

All other G3 gates are retained unchanged. The existing histories are reanalysed with no rerun. This is a finite-horizon operational gate, not proof of stationarity. Both the original FAIL and the amended result are reported.

## Who builds what

- **dsh:** demand and configuration, plus the G1–G3 records.
- **agy-flash:** G4, G5 and the audit, using the existing pipeline.
- **Astra:** reviews the frozen result, read-only.
