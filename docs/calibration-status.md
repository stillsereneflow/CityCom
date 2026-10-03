# Calibration status: net_bounded_v4 demand baseline (2026-10-04)

## 1. Chosen scale and the rule used

**No scale passes. There is no frozen baseline; the B-lite fallback is triggered.**

The rule (decision-2026-10-03 §2, operationalised by the Oct 4 task): run the Proxy demand on
`scenarios/kwuntong/net_bounded_v4.net.xml` with the v4 crop metadata
(`results/bounded/netv4/bounded/network.json`) for 7,200 s, at gate scale 0.5…1.0
(tags `d050 d060 d070 d080 d090 d100`), and pick the **largest scale that passes gates G1–G3**.
No scale in that set passes. G1 (zero teleports) and G2 (vehicle accounting reconciles) pass at
every scale; G3 fails at every scale because the insertion backlog at 7,200 s is 24.0 % of loaded
at the smallest swept scale and rises monotonically to 51.1 % at 1.0 (threshold 2 %), and the
15-minute running slope is positive beyond noise.

Because no passing scale exists, `results/bounded/base/proxy_base.rou.xml` is deliberately **not**
written: freezing a demand that fails all three gates would misrepresent the baseline. The closest
candidate, `results/bounded/d050/demand.rou.xml` (scale 0.5, sha256
`46cd471cbdfeb0cab0cd16a434013e2388bdae0a64260811b7d12d1ebaf8724d`), is reported here only as the
input to the d050 numbers; it is not a baseline.

Network pinned for every run: `net_bounded_v4.net.xml` sha256
`be49be10f9992e264c3fa1f8600ed7656e57f320ab1747e74aef8e02d196fd03` (matches the v4 crop metadata);
metadata `results/bounded/netv4/bounded/network.json` sha256
`82f0dc8aaad7b36b976d9f9cd9a4a6ddccdcabcfb0fa24d70471d85a00d26915`.

## 2. Sweep table (one row per run tag; raw table `results/bounded/base/sweep_gates.csv`)

Each row is generated → `obs_score` → `obs_metrics`, separate processes, on v4 with `--net`/`--net-meta`.

| tag | scale | loaded | inserted | pending@7200 | arrived | running@7200 | teleports | pending share | 15-min slope (veh/s) | slope SE | slope limit | G1 | G2 | G3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d050 | 0.5 | 15,414 | 11,712 | 3,702 | 10,497 | 1,215 | 0 | 24.02 % | +0.0507 | 0.0120 | 0.0240 | pass | pass | **fail** |
| d060 | 0.6 | 18,395 | 12,978 | 5,414 | 11,444 | 1,534 | 0 | 29.43 % | +0.1062 | 0.0133 | 0.0266 | pass | pass | **fail** |
| d070 | 0.7 | 21,482 | 13,349 | 8,129 | 11,560 | 1,789 | 0 | 37.84 % | +0.1284 | 0.0086 | 0.0200 | pass | pass | **fail** |
| d080 | 0.8 | 24,381 | 14,203 | 10,175 | 11,951 | 2,252 | 0 | 41.73 % | +0.1990 | 0.0141 | 0.0283 | pass | pass | **fail** |
| d090 | 0.9 | 27,650 | 14,425 | 13,221 | 12,225 | 2,200 | 0 | 47.82 % | −0.1332 | 0.0157 | 0.0314 | pass | pass | **fail** |
| d100 | 1.0 | 30,796 | 15,068 | 15,724 | 11,607 | 3,461 | 0 | 51.06 % | +0.1633 | 0.0145 | 0.0290 | pass | pass | **fail** |

Gate evaluation (`results/bounded/base/eval_gates.py`):

- **G1** zero teleports: `teleports = 0` in all six `dNNN/run.json`.
- **G2** loaded = inserted + pending (+ departing in the last second): `loaded_residual` is 0 (d050),
  3 (d060), 4 (d070), 3 (d080), 4 (d090), 4 (d100) vehicles, and equals the count of vehicles with
  depart in the last simulated second in every run; inserted − arrived − running = 0 in every run.
  All six reconcile.
- **G3** pending@7200 ≤ 2 % of loaded **and** 15-min running slope ≤ 0 or within noise
  (`|slope| ≤ max(2 × standard error, 0.02 veh/s)`): pending fails in all six; the slope passes only
  in d090 (−0.1332 ± 0.0157) and that run still fails pending. G3 fails at every scale for the
  pending term.

Informational points below the prescribed floor (clearly **outside** the rule; they do not change the
outcome and were not used to pick a scale; `results/bounded/base/sweep_gates_extra.csv`):

| tag | scale | loaded | pending@7200 | pending share | G1 | G2 | G3 |
|---|---|---|---|---|---|---|---|
| d025 | 0.25 | 7,787 | 500 | 6.42 % | pass | pass | **fail** (pending) |
| d035 | 0.35 | 10,682 | 1,408 | 13.18 % | pass | pass | **fail** (pending) |

Even at one quarter of the fitted gate demand the 2 % pending gate is not met, so the network's
carry ceiling for a uniform demand shrink lies below 0.25 — a scale at which the demand would no
longer be grounded in the observed gate flows. This is the quantitative reason the uniform-shrink
family cannot produce a valid baseline in the allowed range.

Where the backlog sits (d050, `results/bounded/base/pending_by_class.py`): it is spread over the
**inferred** gates, not concentrated at the measured one — 1134206886 (860 pending), 113146472 (667),
1460091254 (553), 987703107 (429), 88008416#0 (343). The measured_congested gate 1189103201 has
**0** pending: the B2 fix removed the 3,600 veh/h cap-driven overload that produced 4,802 pending
vehicles at that gate in b01.

## 3. Gate classification (B1 and B2 fixes)

Every gate now carries exactly one class and its demand is confined to that class's bounds; the
bounds are asserted in the code (`citypulse/demand/bounded.py:140-142` after the fit clamp, and
`:269-271` on the gate totals that are actually realised in the route file).

| class | meaning | 29 entry gates (dominant class over 8 slices) | slice-level (29 × 8 = 232) |
|---|---|---|---|
| `measured` | detector on the gate edge, uncongested → observed flow | 0 | 2 |
| `measured_congested` | detector on the gate edge, congested → [observed median, observed p75] | 1 | 6 |
| `inferred` | same-carriageway observation (flow balance, or corridor boundary crossing with a downstream detector) | 18 | 146 |
| `assumed` | no identified inflow measurement → declared range [0, lanes × 1,800 veh/h] | 10 | 78 |

Gate `206049314` is `inferred` in 2 slices and `assumed` in 6, so its dominant class is `assumed`;
the per-slice class is what the code enforces. The 29 exit/unauthorized gates are `assumed` with
range [0, 0] (no entry demand). Full table with value/range, basis and realised fitted demand:
`results/bounded/base/gates.csv` (58 rows; realised values are for the nominal scale-1.0 fit).

- **B1** (`bounded.py:218` in the old code) removed. The corridor exemption is gone; route bounds and
  the per-gate cap come only from the gate's class (`bounded.py:231-239`, `:256`). Assumed gates keep
  a declared range instead of silently receiving demand, and their realised value is listed in
  `gates.csv`.
- **B2** (`bounded_gates.py:101-103` in the old code) removed. Gate `1189103201` / detector `AID07105`
  is now `measured_congested`: lower bound = observed median, upper bound = observed p75, **no lane
  cap** (`bounded_gates.py:118-126`). Realised demand through the gate fell from 6,990 veh/2 h at the
  3,600 veh/h cap (c02) to 4,917.7 veh/2 h (−30 %), and every slice's realised value lies inside
  [median, p75] (e.g. slice 08:30 [2,540, 2,725] → 2,725).

## 4. Calibration gap (stated honestly; information only, not gates)

Scored hour 08:00–09:00 over the 51 retained v4 detectors (12 five-minute bins = 612 cells). Observed
total 119,014 detector crossings. GEH<5 share, speed MAE, occupancy MAE and congestion agreement are
reported for information only — the task explicitly excludes them from G1–G3.

| tag | scale | observed crossings | simulated crossings | sim/obs | GEH<5 share | speed MAE (km/h) | occupancy MAE (%) | congestion agreement | detectors speed-pass | cells with no simulated speed |
|---|---|---|---|---|---|---|---|---|---|---|
| d050 | 0.5 | 119,014 | 39,578 | 0.333 | 0.0016 | 12.58 | 5.54 | 0.886 | 24 / 51 | 24 |
| d060 | 0.6 | 119,014 | 43,045 | 0.362 | 0.0049 | 12.92 | 6.68 | 0.881 | 22 / 51 | 26 |
| d070 | 0.7 | 119,014 | 45,464 | 0.382 | 0.0000 | 14.42 | 7.81 | 0.850 | 20 / 51 | 27 |
| d080 | 0.8 | 119,014 | 49,135 | 0.413 | 0.0163 | 16.14 | 9.68 | 0.812 | 20 / 51 | 24 |
| d090 | 0.9 | 119,014 | 49,559 | 0.416 | 0.0327 | 16.99 | 11.43 | 0.783 | 19 / 51 | 34 |
| d100 | 1.0 | 119,014 | 39,862 | 0.335 | 0.0261 | 26.63 | 19.09 | 0.520 | 6 / 51 | 116 |

The simulation delivers only 33–42 % of the observed crossing volume in the scored hour, and GEH<5
is 0–3 %. Crucially, adding demand does not close the gap: d090 (0.9) delivers more crossings than
d100 (1.0) while d100's speed MAE doubles, because the extra demand queues at the boundary instead
of crossing detectors. This is a network / insertion-capacity limit at the cropped junctions, not a
scorer artefact — the same conclusion as `results/bounded/dsh_report.md` §4, now on v4 with the
B1/B2 defects removed.

## 5. What this baseline is NOT

- **Not calibrated to 1.0× peak counts.** Demand is grounded in observed detector flow but is not
  fitted to reproduce 08:00–09:00 counts; at the largest swept scale it still delivers only ~34 % of
  observed crossings, and the demand that cannot be inserted is 51 % of all loaded vehicles.
- **Signal timings are unknown.** v4 carries Webster-fitted programs (`tls_webster_v4.add.xml`) but
  Hong Kong TD does not publish the real signal plans; no green split, cycle or offset here is a
  measured HK value.
- **Gate demand is partly inferred and partly assumed.** Only 1 of 29 entry gates has a detector of
  its own; 18 gates are inferred from observed flow and 10 are assumed ranges [0, lanes × 1,800]
  with no measurement of inflow.
- **Cropped geometry.** The network is a corridor crop; junction capacity is a crop artefact, not the
  real junction. The pending backlog is dominated by boundary insertion, not by link capacity.
- **No real-world benefit claim.** This is a synthetic proxy used to ground the method, and it
  currently fails its own acceptance gates.

## 6. Exact commands (reproduce the reported runs)

No frozen demand file exists (section 1), so the commands below reproduce the sweep itself. Run from
`D:/CityCom-astra` with `PYTHONDONTWRITEBYTECODE=1` and `OPENBLAS_NUM_THREADS=1`; the six prescribed
tags are `d050 d060 d070 d080 d090 d100` with `--scale 0.5 … 1.0`.

```powershell
$py   = 'D:/CityCom/.venv/Scripts/python.exe'
$net  = 'scenarios/kwuntong/net_bounded_v4.net.xml'
$meta = 'results/bounded/netv4/bounded/network.json'
foreach ($scale in 0.5, 0.6, 0.7, 0.8, 0.9, 1.0) {
  $tag = 'd{0:d3}' -f [int]($scale * 100)
  & $py -m citypulse.demand.bounded --tag $tag --scale $scale --net $net --net-meta $meta
  & $py -m citypulse.experiments.obs_score --tag $tag --net $net --net-meta $meta
  & $py -m citypulse.experiments.obs_metrics --tag $tag --net $net --net-meta $meta
}
```

Gate evaluation and the gate table:

```powershell
& $py results/bounded/base/eval_gates.py --tags d050 d060 d070 d080 d090 d100 --scales 0.5 0.6 0.7 0.8 0.9 1.0
& $py results/bounded/base/make_gates_csv.py --demand results/bounded/d100
```

## 7. Files changed for this task

| file:line | change |
|---|---|
| `citypulse/demand/bounded_gates.py:82-204` | every gate gets a class, `lower_vph`/`upper_vph` and a declared range basis; lane-count split now scales the bounds too (B1) |
| `citypulse/demand/bounded_gates.py:113-133` | direct-detector gate is `measured` (uncongested) or `measured_congested` median..p75 (B2) |
| `citypulse/demand/bounded_gates.py:143-183` | diverging/missing/congested non-direct gates are `assumed` with range [0, lanes × 1,800]; corridor boundary crossing with an uncongested downstream detector is `inferred` |
| `citypulse/demand/bounded.py:123-142` | per-gate class-bound clamp after the fit, with the no-demand-outside-class-bounds assertions |
| `citypulse/demand/bounded.py:188-189` | new `--scale` option (multiplies every gate demand before Poisson sampling) |
| `citypulse/demand/bounded.py:231-239`, `:256` | route priors/bounds from the gate class only (no corridor exemption) |
| `citypulse/demand/bounded.py:263-271` | gate demand × `--scale`; assertion on the realised per-gate totals |
| `citypulse/demand/bounded.py:284`, `:294-295` | `gate_scale` and the class-bound contract recorded in `demand.json` |
| `results/bounded/base/gates.csv` | all 58 gates: class, value/range, basis, realised demand |
| `results/bounded/base/sweep_gates.csv`, `sweep_gates_extra.csv` | gate evaluation per run (prescribed sweep; informational extra) |
| `results/bounded/base/{eval_gates,make_gates_csv,pending_by_class,gap_numbers,probe_gates}.py` | helper scripts |
| `docs/calibration-status.md` | this document |

`citypulse/experiments/obs_score.py` and `obs_metrics.py` were not modified: the G1–G3 evidence is
already written by the existing pipeline (`run.json`, `history.csv`, `pending.csv`, `cells.csv`).

**Process note.** These code and document changes could not be committed from this session: the DSH
file sandbox is `workspace-write`, the worktree's git metadata lives at
`D:/CityCom/.git/worktrees/CityCom-astra/` (outside the workspace), and the wider-access escalation
was refused because no approval channel was available. The changes are complete on disk and are meant
to be committed as one commit on `astra/step1`; `results/` (including `results/bounded/base/`) stays
gitignored as before.

CALIBRATION STATUS DONE
