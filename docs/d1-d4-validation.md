# D1–D4 technical de-risking: validation record

Date: 2026-10-02. Machine: Windows 11, 20 logical cores, 16 GB RAM. Python 3.12.13 (project venv `.venv`), Eclipse SUMO 1.27.1 (pip wheel `eclipse-sumo`), TraCI/libsumo 1.27.1.
Source of truth for the design: `deep-research-report2.md`. This file records only what was actually run. Labels: **PASS**, **FAILED** (ran, did not meet the criterion), **NOT TESTED**. All numbers come from the files cited next to them under `results/`.

## 0. Success criterion: status

| Criterion | Status | Evidence |
|---|---|---|
| Two structurally different SUMO worlds run independently | **PASS** | §4. Separate OS processes. Different demand realizations, car-following models (IDM vs Krauss), vehicle mix and route choice. The Twin's own detector series are bit-identical between the incident and no-incident runs, so the Proxy cannot influence the Twin except through observations |
| Proxy receives an incident unknown to the Twin | **PASS** | Incident defined only in `citypulse/proxy/truth_config.py`. Static and runtime import tests (§5) |
| Twin sees only sparse, noisy observations | **PASS** | 36 of 54 mapped detectors, noise, 4.9% packet loss. Schema-validated messages (§5) |
| The anomaly is observable | **PASS** (with caveats, §6) | Bottleneck index from observed detectors crosses 3σ for 2 consecutive intervals 570 s after onset. Single spikes reach 4.08 in the no-incident run |
| Twin can snapshot, branch several interventions, and return measured KPIs | **PASS** (mechanics) / **FAILED** (decision usefulness) | §8. 5 actions × 5/10/15 min run in 15.0 s wall. The action effects are not distinguishable from seed noise |

## 1. Repository and toolchain

- `git init` in `D:\CityCom` (nothing committed). The reports `deep-research-report*.md` and `fleet-review-*.md` are untouched.
- Venv: `uv venv --python 3.12 .venv`, packages pinned in `requirements.txt`.
- `pyarrow` was pinned to 23.0.1, because libsumo 1.27.1 warns it is built against libarrow 23. Side effect: `pd.read_parquet` prints a non-fatal "Windows fatal exception: code 0xc0000139" via faulthandler. The read still succeeds and the tests pass. **Known issue, not fixed.**
- Importing `libsumo` rewrites `SUMO_HOME` to the `sumo_data` package, which has no `bin/` or `tools/`. `citypulse/config.py` now reads `SUMO_HOME` from the `sumo` package instead. Three integration tests failed until this was fixed.
- Tests: `python -m pytest`, **23 passed, 0 failed** (§9).

## 2. Hong Kong TD detector data

| Item | Status | Detail |
|---|---|---|
| Live raw feed URL | **PASS** | `https://resource.data.one.gov.hk/td/traffic-detectors/rawSpeedVol-all.xml`, taken from the data.gov.hk CKAN package metadata. The URL in report2 (`resource.data.gov.hk`) does not exist (NXDOMAIN) and must be corrected there |
| Feed content | **PASS** | Per-lane speed, occupancy, volume, s.d., valid; two 30 s periods per file. Feed timestamps lag wall-clock time by about 1 h (12:47 poll returned period 11:40) |
| Historical archive | **PASS** (correction to report2 §N.3) | `api.data.gov.hk/v1/historical-archive` lists minute-level versions for the correct URL: 1,885 versions for 2026-09-25/26. Some versions return 404: 50 of 149 in the 07–11 h window of 2026-09-29 |
| Live recorder | **PASS**, running | `python -m citypulse.hkdata.recorder live`, started 12:47. At 15:18: 153 polls, 0 errors, 186 distinct 30 s periods (11:39–14:10 feed time), 166 corridor detectors, 84,156 of 84,188 lane rows valid. Only corridor detectors (`AID02*`, `AID05*`, `AID07*`) are stored. **It is a foreground process of this session's shell. It stops on logout or reboot** (see blockers) |
| Backfill | **PASS** (partial) | 2026-09-29: hours 00–02 and 06–10 pulled (152,078 lane rows). The 08–09 h window has 28–46 of 120 possible periods per detector |
| Data used for demand | 2026-09-29 08:00–09:00, 165 detectors with data, 41 counted edges | `scenarios/kwuntong/demand_info.json` |

## 3. SUMO corridor network and detector mapping

| Step | Result |
|---|---|
| OSM extract | Overpass, bbox 22.300–22.338 N, 114.196–114.240 E, motorway…tertiary (+links): 2,830 ways (`data/osm/kwuntong.osm.xml`) |
| Full network | netconvert `--lefthand` …: 1,710 edges, 85 signals (`net_full.net.xml`). **FAILED as a usable baseline**: at 1.0× and 0.5× of the observed demand it gridlocks (e.g. 0.5×: 12,555 vehicles still running and 3,369 arrived after 1 h; with a 300 s teleport timeout, 1,324 teleports). The jams start at peripheral priority junctions |
| Used network (`net.net.xml`) | motorway/trunk (+links) plus every edge named Kwun Tong Road / Kai Fuk / Kwun Tong Bypass: **383 edges, 363 nodes, 6 signals, 53.6 km** of edges |
| Detector mapping | 54 of 58 corridor detectors mapped (≤ 40 m, road-name match, bearing within 50° of the TD `Rotation`). Unmapped: AID02104, AID02116, AID02202, AID02203. One E1 loop per lane, period 30 s |
| Figure | `docs/figures/network.png` |

**Demand (provisional).** `routeSampler.py` fit to the HK edge counts × **0.6**. Proxy: 13,789 vehicles/h, 90.6% of the target count, GEH < 5 at 82.9% of locations. The 0.6 scale is a workaround for the network capacity problem above. It is not a calibration result. Even at 0.6, about 2,100 Proxy vehicles are still waiting for insertion at t = 3000 s: entry capacity is below demand at some sources. The grounding scatter (`proxy_vs_twin_mismatch.png`, left) shows many detectors well below target.

## 4. Proxy and Twin: structural mismatch

| Dimension | Proxy | Twin |
|---|---|---|
| Latent demand | `routeSampler` seed 1001 on candidate routes from `randomTrips` seed 11. Per-edge counts × lognormal(0, 0.10) | Independent candidate routes (`randomTrips` seed 22), `routeSampler` seed 2002 at 1.5× counts. Poisson thinning (accept iff u < 1/1.5), stream seed 202. **No vehicle, route or departure is shared** |
| Insertion | Route file | Python `traci.vehicle.add` from the Twin's own stream |
| Car following | IDM, 12 car types with sampled τ, minGap, accel, decel; lcAssertive 1.5 | Krauss σ = 0.5, τ = 1.0, single parameter set |
| Vehicle mix | 85% cars, 7% buses, 8% trucks | 90% cars, 10% trucks |
| Route choice | 30% of vehicles carry the rerouting device (period 60 s) | Fixed routes |
| SUMO seed | 1 | 2 |
| Observation | — | 36 of 54 detectors (every 3rd by id dropped). Flow × N(1, 0.10), speed + N(0, 3 km/h), occupancy + N(0, 1.5 pp), 5% loss (measured valid share 95.1%) |

Mismatch without assimilation, no-incident run, t ≥ 600 s, 2,778 valid observation rows (`results/figure_stats.json`): **30 s flow MAE 373 veh/h, speed MAE 8.1 km/h**. Several detectors have mean-speed errors above 20 km/h (`proxy_vs_twin_mismatch.png`, right). So high Twin fidelity is not guaranteed by construction (report2 §F.3). Assimilation is **NOT TESTED** (not built, as instructed).

**Not yet implemented** from the report2 mismatch matrix: per-entry time-varying (OU) demand perturbation, independent-date calibration (needs more recorded days), lane-change-parameter sweep, and VMS compliance mismatch as an experimental factor (fixed at 0.35 Proxy / 0.30 Twin).

## 5. Information firewall

- **Processes**: `citypulse.proxy.service` (ZeroMQ REQ) and `citypulse.twin.service` (REP) run as separate OS processes started by `citypulse.experiments.run_two_worlds`. The Proxy writes ground truth to `results/<run>/proxy/`; the Twin writes only to `results/<run>/twin/`.
- **Messages**: only `SensorMsg` (Proxy → Twin) and `ReplyMsg` (Twin → Proxy), with exact-key validation on both sides (`citypulse/bus/messages.py`).
- **Code split**: incident truth and the evaluation detector pair live in `citypulse/proxy/truth_config.py`. The shared `citypulse/scenario.py` holds only infrastructure: VMS, diversion corridor, signals.
- **Tests** (all PASS): no `citypulse.proxy` / `citypulse.experiments` import anywhere under `twin/` or `branching/` (AST scan); importing the Twin service and branching engine loads no `citypulse.proxy*` module (subprocess check); six malformed messages are rejected (incident flag, true occupancy, vehicle ids, future demand, missing field, wrong type); replies with per-vehicle routes are rejected; the Twin log contains only observation and Twin columns; the Twin sees a strict subset of at most 70% of the detectors.
- **Independence check**: the Twin's own detector series are identical in the incident and no-incident runs (`twin_q/v/o` equal), and so are its final stats (1,778 running, 1,534 pending in both).
- **NOT TESTED**: OS-level isolation (Docker containers, separate volumes) from report2 §D. Today the separation is by process, code and directory, all on one filesystem.

## 6. Incident in the Proxy and its signature

Incident (Proxy-only): edge 312049503 (Kwun Tong Bypass northbound, 3 lanes, 1,206 m). Lanes 0 and 1 are blocked by stopped vehicles at 900 m, from t = 1200 s for 900 s. Proxy truth, mean over 900–1200 s → 1500–2100 s (`results/incident/proxy/proxy_truth.parquet`):

| Detector (position on edge) | Occupancy % | Speed km/h | Flow veh/30 s | Twin sees it? |
|---|---|---|---|---|
| AID02109 (456 m, upstream) | 4.3 → 26.3 | 77.5 → 38.0 | 13.9 → 12.4 | yes |
| AID02110 (705 m, upstream) | 4.0 → 49.8 | 76.5 → 5.5 | 13.5 → 9.2 | **no** (dropped by the coverage rule) |
| AID02111 (1,055 m, downstream) | 3.8 → 3.3 | 75.6 → 69.6 | 13.7 → 9.3 | yes |

Upstream congestion plus downstream under-load is the bottleneck signature report2 §G.2 assumes.

**From the Twin's observations only**: the bottleneck index B(AID02109, AID02111) on observation-minus-Twin residuals, standardized by the MAD of 300–1200 s, first exceeds 3 for 2 consecutive 30 s intervals at **t = 1770 s, 570 s after onset**. Its maximum is 29.6. In the no-incident run it never exceeds 3 twice in a row, but single spikes reach **4.08**, so a one-interval trigger at 3 would false-alarm. The long delay is because the queue must spill back 444 m to the first observed upstream detector. After the incident clears, the downstream detector congests (discharge wave) and B turns strongly negative. The recovery logic in report2 §G.5 must expect this. Figure: `docs/figures/incident_signature.png`. This is a visibility check, not the report2 CUSUM detector, whose threshold calibration is **NOT TESTED**.

## 7. saveState / loadState persistence (`results/snapshot_tests.json`)

Setup: Proxy-style world (route file, vTypeDistribution, rerouting devices). Modifications at t = 600 s, save, then compare a **new process** (`--load-state`) and **in-process** `traci.simulation.loadState`. Five configurations: runtime-created vs predefined signal program, RNG saved vs not, with vs without a vehicle stop. Plus a Twin-style world (no route file, Python insertion).

| Item | New process | In-process | Consequence for the engine |
|---|---|---|---|
| Vehicles in network | kept (923 = 923) | kept | — |
| Vehicles waiting for insertion | kept, but `getPendingVehicles()` returns 0 until the first step. After 1 step: 174 vs reference 175 (1 vehicle off, **not explained**) | kept (175 = 175) | Don't read the pending list right after loading. No re-insertion needed (re-adding fails: "already exists") |
| Vehicle added via `traci.vehicle.add` | kept | kept | — |
| Route change (`changeTarget`) | kept | kept | — |
| Vehicle stop (`setStop`) | kept | **FAILED** in 1 of 2 configurations: SUMO quit with "no valid route … to stop edge" | Never use in-process reload |
| Per-vehicle speed factor | kept | kept | — |
| Active signal program, **predefined** in an additional file | kept, phase kept; a signal left on "0" stays "0" | kept | — |
| Active signal program **created at runtime** (`setProgramLogic`) | **FAILED**: SUMO quits on load, "Unknown program 'P_test'" | works | All action plans must be predefined (`tls_incident.add.xml`) |
| Lane closure (`lane.setDisallowed`) | **lost** (reverts to the network default) | unchanged (cannot tell "restored" from "never reset") | Re-apply from `ControlState` after every load |
| Lane speed (`lane.setMaxSpeed`) | **lost** (22.22 instead of 5.0) | unchanged | Re-apply |
| TraCI subscriptions | **lost** | kept | Re-subscribe |
| E1 last-interval values | **reset** (0 vs 6), still 0 after 1 step | reset | First Twin interval after a load is invalid |
| Exact trajectory continuation vs uninterrupted run | **FAILED in every configuration**: diverges at the first 10 s checkpoint, with or without `--save-state.rng`, also in the Twin-style world, also with `--save-state.precision 8` | **FAILED**; with RNG, 1,514 vs 1,049 vehicles after 300 s | A snapshot gives a statistically similar but not identical future. Report2 §L.2's "exact replay" consistency test cannot pass as written. Cause **NOT TESTED** (docs list lane-change and car-following internal state as unsaved) |
| Two new-process branches from the same snapshot, same seed | **PASS**: identical KPIs. Parallel = sequential for all 5 actions | — | Common random numbers across branches hold |
| Rerouting-device state, Linux/Windows portability | **NOT TESTED** | | |

**Bug found and fixed while testing.** Loading `tls_incident.add.xml` makes `P_inc` the **active** program of each signal from t = 0, because SUMO activates the last loaded program. Every run before the fix silently used the incident plan as its "do nothing" baseline. Fix: `sim.init_signals()` forces program "0" at start (never after a load). Test: `test_init_signals_resets_last_loaded_program`.

## 8. Snapshot branching engine and runtime

`citypulse/branching/engine.py`:
1. Load the same Twin snapshot (t = 1500 s) in one new libsumo process per action.
2. Re-apply the control state and the capacity hypothesis.
3. Continue the Twin's own demand stream (same seed in every branch).
4. Apply the action and roll out 900 s, reading KPIs at 300, 600 and 900 s.

Actions: A0 do nothing; A1 predefined incident plan on 4 signals along corridor B; A2 VMS diversion (compliance 0.30, hashed per vehicle); A3 = A1 + A2; A4 = stronger VMS (0.48).

The capacity hypothesis is **supplied manually**: 2 of 3 lanes on 312049503. Event-mode inference is not built yet. The point-blockage position is 755 m, the midpoint of the observed detector segment, not the Proxy's true 900 m.

**Runtime** (`results/branch_benchmark.json`; 15-min horizon, about 1,800–2,400 vehicles in the network; the 5- and 10-min KPIs are checkpoints of the same run):

| Measurement | Wall time |
|---|---|
| One branch, sequential (incl. load + setup 0.40–0.51 s) | 8.3–8.6 s |
| 5 branches sequential | 43.1 s |
| 5 branches parallel (5 processes) | **15.0 s** (13.4–13.8 s each under contention) |
| Two-world lockstep run, 3,000 s simulated (Proxy + Twin) | 73.3 s |

**KPIs** (15 min, point-blockage hypothesis, mean ± sd over SUMO seeds 2–5):

| Action | Corridor delay (veh·h) | Network delay incl. entry backlog (veh·h, seed 2) | Vehicles diverted |
|---|---|---|---|
| A0 | 172.2 ± 1.1 | 419.7 | 0 |
| A1 | 171.4 ± 1.0 | 419.7 | 0 |
| A2 | 172.1 ± 2.0 | 423.3 | 4 |
| A3 | 173.8 ± 1.3 | 418.0 | 4 |
| A4 | 171.8 ± 1.8 | 423.2 | 5 |

Findings (`docs/figures/branching_comparison.png`):
1. **The action effects are within seed noise.** The VMS diverts only 4–5 vehicles in 15 min, because few Twin routes pass both the VMS edge and the rejoin edge. The signal plan changes delay by under 1%. The current action space cannot support a decision. **FAILED for decision usefulness.**
2. **The network delay KPI is dominated by the entry backlog** (about 1,000 vehicles waiting to enter, worth roughly 250 veh·h). That backlog is a network/demand artefact, so "corridor delay" (vehicles whose route uses the VMS target edge or corridor B, about 2,000 vehicles) was added and is the KPI to use.
3. **Both Twin-side hypothesis representations produce much smaller impacts than the Proxy incident.** Whole-edge lane closure strands the vehicles already on the closed lanes (a constant 15.7 halting vehicles, sd 0). The point blockage gives 8.6–9.1 halting vehicles on the edge. Corridor delay with a hypothesis is 172–174 veh·h vs 167–171 veh·h without one. In the Proxy, the same incident reduces upstream speed to 5.5 km/h and spills back past a detector 444 m upstream. Calibrating this severity mapping (report2 §F.2, ρ(k, s)) is a prerequisite for event-mode inference.

## 9. Tests (`python -m pytest`, 23 passed)

- `tests/test_firewall.py` (14): static import rule, runtime module isolation, schema rejection cases, reply rules, Twin log columns, sparse subset.
- `tests/test_units.py` (5): TD XML parse and aggregation; Twin stream CRN, seek without duplicates or gaps, thinning rate within 0.02 of 1/1.5; VMS hash stability and uniformity; sensor emulator sparsity, noise and loss.
- `tests/test_sumo_integration.py` (4): SUMO binary; `init_signals` resets the last-loaded program; new-process load keeps vehicles and drops lane closures; branch conformance and parallel = sequential recorded.

## 10. Evidence files

| Figure | Content |
|---|---|
| `docs/figures/network.png` | Corridor network, observed vs hidden detectors, Proxy-only incident, VMS, corridor B |
| `docs/figures/proxy_vs_twin_mismatch.png` | HK-target grounding scatter; Proxy truth vs observations vs Twin at AID02109; per-detector speed mismatch |
| `docs/figures/incident_signature.png` | Proxy truth at 3 detectors (incident vs no incident); what the Twin receives; bottleneck index |
| `docs/figures/branching_comparison.png` | 5 actions × 5/10/15 min; KPIs by hypothesis representation |
| `docs/figures/rollout_runtime.png` | Parallel vs sequential wall time |
| `results/snapshot_tests.json` | Full persistence table data |

## 11. Blockers and open items

1. **Network capacity and demand.** The OSM-derived network gridlocks at observed demand, so 0.6× is used, and an entry backlog of about 2,000 vehicles persists. Report2's calibration step (D5–D7) needs junction and lane repair on the full network or a better-bounded corridor. Until then, KPIs must exclude the backlog.
2. **Action space has no measurable effect.** The VMS location and eligibility rule reach about 5 vehicles per 15 min. The signal plans are weak.
3. **Twin capacity-loss representation is too mild** compared with the Proxy blockage. The severity mapping must be calibrated before hypothesis inference.
4. **Exact snapshot replay is impossible in SUMO 1.27.1** as tested. Report2's "bit-identical branch vs reference" acceptance test must become "identical between branches + statistically equivalent to the reference".
5. **Recorder persistence.** The live HK recorder dies with this session or a reboot. It needs a Windows scheduled task, which I did not create because it is persistent machine configuration. Backfill from the archive covers gaps, with about 1/3 of versions missing (404).
6. **Report2 corrections needed**: the TD feed URL; the historical archive does exist.
7. **NOT TESTED**: Docker isolation, assimilation, the CUSUM detector and its ARL calibration, rerouting-device state across loads, Linux portability of state files.
