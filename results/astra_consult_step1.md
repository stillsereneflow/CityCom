# Step 1 consultation — 2026-10-03

**Recommendation: rebuild the observation/demand contract before further capacity tuning. The hypothesis that demand construction is the *main* cause is not established.** Two demand-only interventions failed on the unchanged network. Real congestion also exists in TD observations, so uncongested operation at observed counts is the wrong universal target. None of these runs passes step 1.

## Experiments and evidence

All full runs: 3,600 s, SUMO seed 1, original vehicle mix, signal programs and rerouting settings; teleporting disabled. The control exactly reproduces g100 totals, trajectories, detector intervals, source backlogs and fit. Stored input-hash differences are line-ending-only, verified by LF-to-CRLF conversion. Slope uses 16 one-minute observations over the closed interval [2700,3600].

| Tag / intervention | Loaded | Pending (%) | Running end | Final-15-min slope, veh/s | Simulation GEH<5 |
|---|---:|---:|---:|---:|---:|
| `astra_base`: original demand | 26,020 | 10,011 (38.47%) | 4,526 | +0.724 | 1/40 (2.5%) |
| `astra_boundary`: strict topological boundary, fastest paths | 23,178 | 12,429 (53.62%) | 3,818 | +0.611 | 0/40 |
| `astra_optimized`: original candidates, `--optimize full` | 25,131 | 11,782 (46.88%) | 2,376 | +0.334 | 4/40 (10%) |

All have zero teleports. Smaller running populations/slopes partly reflect worse insertion, not successful stabilization. The 6/5/9 vehicles outside inserted+pending have departures in the final second; they are not silently discarded.

Boundary generation considered all 54 entry × 53 exit edges with no incoming/outgoing passenger connection: 1,876 pairs unreachable, 84 without counted edges, 902 retained. Three targets (`1128468449`, `1134206869`, `39596703`) have no candidate coverage. This is a topology-based falsification probe, not a validated OD model. It also shifts demand onto artificial cut stubs: 71.9% of starts are outside the defined trunk/corridor core. Its worse outcome does not disprove every boundary-based model.

Optimization fits **97.6% of the 41 perturbed target counts** at GEH<5 in route space, but concentrates traffic onto only 39 distinct routes. It is a count-fit control, not a plausible OD estimate. Simulation still fails badly. The two experiments cannot partition causality between demand, junction capacity, and their interaction.

Original routes average **2.64 km**, median 2.00, p95 6.12, max 7.92 km; 45.1% start internally, only 15.7% have both endpoints at the topological boundary, and 68.6% touch a noncore edge. Uncounted edges receive **38,484/68,607 planned vehicle-km (56.1%)**. No direct SUMO U-turn connections or repeated edges were found; this does not exclude circuitous paths. These facts warrant OD scrutiny, but do not themselves establish overload relative to reality.

## Q1 — Demand construction

**Use a bounded, path-constrained OD model with measured gates; add turn constraints only where observed.** First identify actual external crossings and legitimate local access, rather than treating every pruning stub as an OD source. Retain physically feasible arterial and bypass alternatives; one fastest route per OD misses counted movements. Fit boundary arrivals and internal observations jointly, with explicit accumulation and uncertainty. Do not invent turning counts or treat internal discharge as new inflow.

Use routeSampler as an initialization/check, not as evidence of dynamic feasibility. Optimization alone improved route-space fit without rescuing simulation. Preserve OD/path diversity with defensible priors, and evaluate alternative feasible solutions to expose under-identification. Do not select a vehicle-minimization weight merely because it reduces backlog.

## Q2 — Do counts include congestion?

**Yes: several sites show congestion-compatible states; their counts cannot identify unconstrained demand.** On September 29, complete-lane, volume-weighted speeds and mean occupancies are:

| Detector | Location | km/h | Occupancy | Valid periods /120 |
|---|---|---:|---:|---:|
| AID07105 | Tseung Kwan O Road WB | 15.7 | 28.8% | 30 |
| AID07106 | Tseung Kwan O Road WB | 19.3 | 32.1% | 46 |
| AID02109 | Bypass NB | 20.3 | 25.1% | 46 |
| AID02110 | Bypass NB | 22.9 | 24.9% | 46 |

The two Tseung Kwan O sites remain slow/high-occupancy across all eight examined weekdays. Bypass severity varies by day. Conversely, AID07226's 26.8 km/h accompanies only 2.3% occupancy and 156.5 veh/h: low speed alone is insufficient evidence of a congested discharge bottleneck.

The table's four sites meet speed<30/occupancy>20 in respectively 23/30, 42/46, 35/46 and 33/46 periods; at the stricter 20/30 cutoffs, these become 13/30, 18/46, 8/46 and 6/46. Congestion duration is threshold-dependent; all nine threshold combinations are retained in `astra_step1/td_summary.json`.

Day-29 quality: 188/7,130 mapped lane rows invalid (2.64%); no duplicates, missing numeric fields or partial valid-lane periods. Only 28–46/120 periods per detector survive, so **61.7–76.7% of expected time periods are absent/invalid**. These are sampled states, not continuous hour-long queue measurements. Pandas independently reproduces all 54 detector aggregates.

## Q3 — Narrower study area?

**Prefer a bounded KTB–Kai Fuk–KTR demonstrator if its gates and diversion paths can be observed.** Keep the wider network as a reference; do not repeatedly widen lanes or repair junctions without physical evidence. Cropping alone failed in the boundary probe. Preserve the VMS approach, both intervention alternatives and their rejoin, with queues contained or explicitly represented outside the boundary.

The baseline has pending vehicles at 164 sources, with only 34.0% at the largest five. This describes widespread symptoms, not 164 independent bottlenecks: a few downstream constraints can propagate widely. Earlier unsuccessful repairs do **not** prove that one or two remaining junction defects are impossible.

## Q4 — Acceptance criteria?

**Accept observed flows plus speeds/occupancies and plausible queue evolution, allowing observed congestion.** Scale 1.0 must mean the audited observation set, not an assertion that discharge counts equal arrivals. Warm up using 07–08h observations before scoring 08–09h. Retain GEH<5 on ≥80% of declared scored locations, with no silently omitted locations. Assess speed and congestion duration on matching observed times, including held-out weekdays.

Apply backlog≤2% and nonpositive running slope only where verified boundary conditions imply uncongested/stationary operation. Else require explained external queues and accumulation consistent with boundary inflow–outflow; unexplained insertion backlog remains a failure. Never omit entry queues from total intervention cost simply because they are inconvenient.

## Priority order and acceptance checks

1. **Repair observation provenance/mapping.** Regenerate targets against current detector positions; expose coverage, invalidity and perturbation. Check all 41 targets map and are scored; exact IDs, timestamps and hashes accompany every run.
2. **Specify gates, OD priors and alternate paths.** Check every target has candidate coverage, every endpoint has a physical access justification, and route-space residuals and unobserved vehicle-km are reported. No silent target deletion.
3. **Run the bounded model with warm-up, then diagnose residual bottlenecks.** Require the declared flow criterion and held-out speed MAE no worse than a calibration-weekday-median predictor; congestion durations must fit observed weekday variability. Attribute residual external queues before proposing individual junction changes.

## Measurement/code concerns

- `demand_info.json`/`counts_proxy.xml` still target `1128468458`, while AID07224 now maps to `1128468457`. `net_diag` silently scores 40/41. Its GEH target is unperturbed TD, unlike routeSampler's perturbed objective.
- `--fringe-factor 20` is a preference, not fringe-only demand. The progress note's ~3.5 km is not the current sampled mean.
- `fill_gaps` treats equal bracketing lane counts as proof an intervening drop is an OSM error; a real merge/drop is also possible.
- Independent 300-s E1 check: 1/1,590 lane-interval cells differs from SUMO XML `nVehContrib` (API 4 versus XML 3; totals 4,133 versus 4,132). Exact-match assertion fails reproducibly; semantics remain unresolved. This is not an interval-wide counting failure and cannot explain insertion backlog. Do not claim perfect flow-instrument validation.

## Reproduction and scope

From the worktree, set `PYTHONDONTWRITEBYTECODE=1`. Let `P=D:/CityCom/.venv/Scripts/python.exe`, `R=results/astra_step1`, and `S=D:/CityCom/.venv/Lib/site-packages/sumo/tools/routeSampler.py`:

```text
P -m citypulse.experiments.astra_step1 --prepare --routes scenarios/kwuntong/proxy.rou.xml
P S -r R/boundary_candidates.rou.xml -d scenarios/kwuntong/counts_proxy.xml -o R/boundary.rou.xml --seed 1001 --prefix p --attributes 'type="pdist" departLane="best" departSpeed="max"'
P S -r scenarios/kwuntong/cand_proxy.rou.xml -d scenarios/kwuntong/counts_proxy.xml -o R/optimized.rou.xml --seed 1001 --prefix p --attributes 'type="pdist" departLane="best" departSpeed="max"' --optimize full
P -m citypulse.experiments.net_diag --tag astra_base --libsumo
P -m citypulse.experiments.net_diag --tag astra_boundary --routes R/boundary.rou.xml --libsumo
P -m citypulse.experiments.net_diag --tag astra_optimized --routes R/optimized.rou.xml --libsumo
P -m citypulse.experiments.astra_step1 --routes R/boundary.rou.xml R/optimized.rou.xml
P -m citypulse.experiments.astra_step1_check
```

Optimization needs `PYTHONPATH=R/packages`: SciPy 1.18.1 was installed there using `uv --no-config --no-cache pip install --python P --target R/packages --no-deps scipy`; temporary files stayed inside R. No other dependencies, workers, remote compute or downloads. Raw diagnostics, summaries, input hashes and the failed E1 check are retained. All 33 original scenario/archive/baseline inputs remain byte-identical; existing tracked files, main checkout and recorder were not changed. Experiments stopped after two negative interventions; no parameter tuning or further network modification.
