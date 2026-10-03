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

## Who builds what

- **dsh:** demand and configuration, plus the G1–G3 records.
- **agy-flash:** G4, G5 and the audit, using the existing pipeline.
- **Astra:** reviews the frozen result, read-only.
