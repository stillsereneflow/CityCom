# B-lite: curated two-route corridor (simplified research model)

Status: specification, 2026-10-03. It is triggered by `docs/calibration-status.md`: on the OSM-derived crop `net_bounded_v4`, no demand scale from 0.25× to 1.0× passes the baseline gates. That is the decision rule in `D:/CityCom/docs/decision-2026-10-03.md` §4.

**Label everywhere:** "simplified research model, geometry and detectors grounded in Hong Kong data; not a calibrated replica." Real detector ids, real lane counts (TD) and real distances; hand-built junctions; one travel direction.

## Scope: one direction, two routes

Westbound/northbound only. That is the direction of the incident on Kwun Tong Bypass northbound (old edge `312049503`), of the VMS diversion, and of the arterial alternative. Kai Fuk Road and the opposite carriageways are out of scope; this is stated as a simplification.

```
            ktb_w1 - ktb_w2 - ktb_w3 - ktb_n1 (incident section) - ktb_n2 --\
tko_in - tko_1 - tko_vms  [D: diverge at the VMS]                             M - rejoin - out
            tko_a1 - ktr_w1 -S1- ktr_w2 -S2- ktr_w3 -S3- ktr_w4 -S4- ktr_w5 - ktr_w6 --/
```

## Edges

Lane counts from TD detectors (distinct `lane_id` values in `data/hk/raw/archive/2026-09-29.csv`). Lengths are real chainage: the shortest-path distance on `net_bounded_v4` between the detectors' edges and positions. Where an edge carries detectors, keep each detector's real offset from the edge start, as on the real edge.

| Edge | Detectors (real) | Lanes | Speed (km/h) | Length |
|---|---|---|---|---|
| `tko_in` | AID07105 | 2 | 70 | ≥ 300 m; boundary entry, keep it long so insertion is not limited |
| `tko_1` | AID07106 | 3 | 70 | real distance AID07105 → AID07106 |
| `tko_vms` | — | 3 | 70 | ≥ 200 m, up to the diverge D. **This is the VMS edge** |
| `ktb_w1` | AID02105 | 2 | 70 | real |
| `ktb_w2` | AID02106, AID02107 | 3 | 70 | real |
| `ktb_w3` | AID02108 | 3 | 70 | real |
| `ktb_n1` | AID02109 @ 455.7, AID02110 @ 705.0, AID02111 @ 1054.9 | 3 | 80 | 1,206 m, same as old `312049503`. **Incident section**; incident position 900 m, lanes 0 and 1 blocked |
| `ktb_n2` | AID02112 … AID02115 (real offsets) | 2 | 80 | real (≈ 1,880 m) |
| `tko_a1` | AID07107 | 3 | 70 | real |
| `ktr_w1` | AID07108 | 4 | 50 | real, ends at signal S1 |
| `ktr_w2` | AID07109 | 4 | 50 | real, ends at S2 |
| `ktr_w3` | AID07110 | 2 | 50 | real, ends at S3 |
| `ktr_w4` | AID07111, AID07112 | 3 | 50 | real, ends at S4 |
| `ktr_w5` | AID07113 | 4 | 50 | real |
| `ktr_w6` | AID07114 | 4 (TD may say more; use TD) | 50 | real, to merge M |
| `rejoin` | — | 3 | 70 | 300 m, after merge M. **This is the rejoin edge** |
| `out` | — | 3 | 70 | 200 m, sink |

**Ramps.** Between every pair of consecutive main edges on both routes, add an on-ramp `on_<downstream edge>` (1 lane, 300 m, 50 km/h) and an off-ramp `off_<upstream edge>` (1 lane, 200 m). Unused ramps carry 0 demand; the demand builder decides. Merges are zipper or priority, with a lane-add/drop that respects the lane counts.

**Signals S1–S4.** Real cross streets are not modelled. Each signal has a cross-street stub pair `x<i>_in` / `x<i>_out` (2 lanes, 200 m). Cross-street volume is *scenario-assumed*: a declared range, default 400 veh/h per stub. Each signal has two phases with a fixed cycle; timings are Webster-fitted on the demand, and the TD/HK signal plans are unknown, so say so. Signal ids are `S1`…`S4`.

**Junction rules:**
- No edge shorter than 20 m.
- No dead lanes.
- Every lane change needed for a route has at least 150 m to happen.

Left-hand traffic.

## Control mapping (replaces `CONTROL` for B-lite; new file `citypulse/scenario_blite.py`)

- `vms_edge` = `tko_vms`
- `rejoin_edge` = `rejoin`
- `vms_target_edge` = `ktb_n1`
- `corridor_b` = `[tko_vms, tko_a1, ktr_w1, ktr_w2, ktr_w3, ktr_w4, ktr_w5, ktr_w6, rejoin]`
- `tls_plan` = `[S1, S2, S3, S4]`
- Proxy incident: edge `ktb_n1`, lanes `[0, 1]`, pos 900, t_start 4,500 s (08:15 in a 07:00-start run), duration 900 s. It goes in a B-lite Proxy truth config, never in shared code.

## Demand (1-D flow balance, 07:00–09:00, 15-min slices)

From `results/obs/obs_profile.json` (calibration-day medians):
- Entry `tko_in`: AID07105. It is congested, so it measures discharge; use the median, bounded by p75.
- Diverge split at D: the TKO stream divides between `ktb_w1` and `tko_a1`. Fit it per slice by least squares to AID02105 and AID07107, plus the ramp volumes.
- Along each route: for consecutive detectors, a positive balance (downstream − upstream) feeds the on-ramp between them; a negative balance feeds the off-ramp. A missing or congested detector means the ramp is *assumed* [0, 1,800 × lanes]; list it.
- Merge M: no constraint beyond conservation.
- Proxy and Twin: same network, independent demand realisations. The Twin stream uses a different seed and 1.5× candidates with thinning, as in `citypulse/twin/demand_stream.py`.

## Acceptance

1. **Network checks:** 0 dead lanes, no edge < 20 m, all 4 signals valid, all listed detectors placed within their lanes.
2. **Gates G1–G3** (decision §3) at **scale 1.0** of the observed demand:
   - zero teleports;
   - vehicle accounting reconciles;
   - pending ≤ 2% and no growing queue.
3. **G4:** the Proxy incident is visible in the Twin's sparse detectors (bottleneck index crosses threshold).
4. **G5:** A2 (VMS) diverts a meaningful number of vehicles (≥ 5% of the TKO stream), and at least one action's corridor-delay effect exceeds paired seed variability.
5. **Report the calibration gap honestly** (GEH, speed MAE) as information.
