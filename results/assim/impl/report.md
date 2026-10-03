MODEL: deepseek-v4.1-flash

# Normal-mode assimilation (report2 §G.3) in the Twin: implementation, tests, smoke run

Binding spec: `docs/oct5-normal-assim-plan.md` §"NA, as specified" (algorithm: report2 §G.3, lines 238–260).
Worktree `D:/CityCom-astra`, `CITYPULSE_NET=blite`, `CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`,
Twin SUMO seed 2 / demand seed 202, synth5 routes, no incident. Nothing committed.

## 1. Changes (file:line)

| File | Lines | What |
|---|---|---|
| `citypulse/twin/assim.py` (new, 137 lines) | 67–137 | `NormalAssimilator`: constructor `kappa=0.3, delta=1.0, step_clip=0.05, m_min=0.5, m_max=1.8, o_crit=15.0, sigma_q=None`; `update(t, obs, twin, base_vehph, m, sigma_q)` returns `(m_new, row)` with `row = {t, e_s, r, delta, m, reason}` (Δ is the `delta` column), `reason ∈ {updated, deadband, congested, invalid}`. `Interval` dataclass accepts either mappings (SensorMsg `ObsItem` / `read_detectors` row) or objects. `PER_HOUR = 120` (counts per 30 s → veh/h), two intervals averaged. |
| `citypulse/twin/demand_stream.py` | 10 (`import bisect`), 61–72 | `base_rate(entry, t, window=300.0)`: candidates whose first edge is `entry` with `depart ∈ [t−300, t+300)`, `×3600/(2·window)/scale` → veh/h. Reads only `self.cands`/`self.scale` (bisect on the already-sorted candidate list), so it is a pure property of the pool: unchanged by `m` and identical in every branch. Acceptance in `due()` is untouched, so all multipliers at 1.0 accept exactly the same candidates as before. |
| `citypulse/twin/service.py` | 32–34 (`BOUNDARY_DETECTOR="AID07105"`, `BOUNDARY_ENTRY="tko_insert"`, `ASSIM_PERIOD=60.0`), 36 (`run(..., assim="off", sigma_json=None)`), 72 (`"m": dict(stream.m)` in the snapshot meta), 80–96 (assimilation block), 104–106 (`assim_log.parquet`), 119–120 (CLI `--assim {off,normal}`, `--sigma-json`) | Every 60 s of sim time: the last two 30-s intervals of the boundary detector's observation and of the Twin's own reading (`valid = q and o present`), `base_s(t)` from the stream, `sigma[AID07105]` from the JSON; result written to `stream.m["tko_insert"]`. Rows are logged every tick (including no-update ticks). A missing detector, a non-consecutive interval pair, a missing/non-positive σ or a non-positive base rate all fall through to `invalid` and no update. `--assim off` never enters the block. |
| `citypulse/branching/engine.py` | 63 | `stream.m = dict(meta.get("m") or {})` after the branch's `TwinDemandStream` is built (backward compatible with pre-`m` snapshots). |
| `tests/test_assim.py` (new) | all | 10 pure unit tests, no SUMO (see §2). |
| `results/assim/impl/` | — | Run outputs + two dev helpers: `run_assim_smoke.py` (two-world launcher, adds `--proxy-seed/--assim/--sigma-json/--twin-snapshot/--cover-boundary`) and `sigma_from_ol.py` (σ = 1.4826·MAD of OL residuals). |

## 2. Tests

`python -m pytest tests/test_assim.py -q` → **10 passed in 0.29 s**. Each test pins one clause:

| Test | Pins |
|---|---|
| `test_sign_observation_above_twin_raises_m` | obs > twin → `e_s > 0` → m up; obs < twin → m down; `m = m·(1+κ·e_s)` inside the clip |
| `test_deadband_no_update` | `|r| = 1.0σ` exactly → `deadband`, m unchanged (δ is a strict `>`); `r = 0` → deadband; `r = 1.008σ` → update |
| `test_step_clip_at_five_percent` | huge residual → `delta = ±0.05` exactly, m = 1.05 / 0.95 |
| `test_m_clip` | m = 1.79 → 1.80; m = 0.51 → 0.50 |
| `test_congested_gate_no_update` | `o ≥ 15%` (one interval at 20% is enough, the two are averaged) → `congested`, no update; `o = 14.9%` → update |
| `test_invalid_or_missing_data_no_update` | `valid=False` (either side), `q`/`o` None, a `None` interval (detector absent from the SensorMsg), a single interval, σ None/0, base 0 → `invalid`, m unchanged |
| `test_unit_conversion_counts_per_30s_to_vehph` | `PER_HOUR == 120`; (10, 8) counts → 240 veh/h residual; (10,14) vs 8 → mean 12 → 1440 veh/h; 1 vehicle per 30 s = 120 veh/h |
| `test_row_fields_and_reasons` | row keys exactly `{t, e_s, r, delta, m, reason}` |
| `test_interval_dataclass_accepted` | `Interval` objects accepted as well as mappings |
| `test_base_rate_from_candidate_list` | `base_rate` over ±5 min / scale on a synthetic pool, window argument, invariance to `m` |

Whole suite (`pytest tests/ -q`, all env vars set): **55 passed, 3 skipped, 1 failed**.
The one failure is pre-existing and unrelated: `test_sumo_integration.py::test_init_signals_resets_last_loaded_program`
asserts the re-initialised program id is `"0"` but rev5 loads `"webster"`; that test imports only
`citypulse.sim`/`citypulse.scenario`, none of the files changed here. With `tests/test_sumo_integration.py`
ignored: 53 passed, 2 skipped.

## 3. Off-mode identity check (`--assim off` ≡ today)

Two 900-s two-world runs, Proxy seed 1001, port 5561/5562, synth5 routes, no incident, identical seeds:

```
python results/assim/impl/run_assim_smoke.py --run assim/impl/off_before --t-end 900 --port 5561 --proxy-seed 1001        # pre-change code, no --assim flag
python results/assim/impl/run_assim_smoke.py --run assim/impl/off_after  --t-end 900 --port 5562 --proxy-seed 1001 --assim off
```

* `off_before/twin/twin_stats.json` has no `assim` key (pre-change code); `off_after`'s has `"assim": "off"` — the two runs really did execute different revisions.
* Both `twin_log.parquet`: **420 × 9**, same columns, same dtypes; `pandas.testing.assert_frame_equal` → **identical**.
* The two parquet files are even **byte-identical**: sha256 `ba03eea1b73c5a4c4eefc9a48d114613b859ce323a66d92b80b2c1f12485eba4` for both.

## 4. Smoke run — 3,600 s, Proxy seed 1001, `--assim normal`

### 4a. The requested run on the frozen protocol: blocked by sensor coverage

`results/assim/impl/na_frozen` (60 assimilation ticks, `--sigma-json results/assim/impl/sigma_prov.json`):
**60/60 ticks `invalid`, m ≡ 1.0000, 0 updated / 0 deadband / 0 congested.**

Reason, verified directly: the Proxy's `SensorEmulator` coverage rule `drop_every_3rd` drops every third
detector id in sorted order, and **AID07105 is index 11 of 21** (`scenarios/kwuntong/blite/detector_map.json`),
so it is never emitted — the existing `results/blite/synth5/g45/g4_control_a` twin log also contains no
AID07105 row. The plan's "only TKO has a boundary detector, AID07105" therefore cannot work under the frozen
coverage rule: the NA arm as predeclared is `m ≡ 1` for every tick, i.e. NA ≡ OL. This is outside the files I
was allowed to edit (`proxy/sensors.py`, `proxy/service.py`); the eval harness must either exempt the boundary
detector from the coverage rule or pick a different (observed) boundary detector. The plumbing itself is fine:
`assim_log.parquet` is written with all 60 rows, and the snapshot meta carries `m`.

### 4b. Labelled diagnostic run with AID07105 observed (dev-only patch, not a protocol change)

`results/assim/impl/na_smoke`: same 3,600 s / seed 1001, but the Proxy's observed set is extended by
AID07105 only (patch inside `run_assim_smoke.py --cover-boundary`; interior coverage unchanged, and the
patched run has 15 observed detectors = the frozen 14 + AID07105). σ_prov = **622.692 veh/h**
(1.4826·MAD of the AID07105 OL residuals from the same protocol's OL run `results/assim/impl/ol_smoke`,
t ∈ [900, 1800], n = 28, median −60 veh/h, MAD 420 veh/h). `base_s(t)` for `tko_insert` is 2,736–2,972 veh/h
across the run.

Tick counts (60 ticks): **3 `updated`, 6 `deadband`, 44 `congested`, 7 `invalid`**; m: 1.0000 → 0.9500 →
0.9025 → 0.8574 (range 0.1426, all updates negative).

| t (s) | m | updated | deadband | congested | invalid | mean r |
|---|---|---|---|---|---|---|
| 300 | 0.9500 | 1 | 2 | 2 | 0 | -0.450 |
| 600 | 0.9500 | 0 | 0 | 5 | 0 |  |
| 900 | 0.9500 | 0 | 0 | 3 | 2 |  |
| 1200 | 0.9500 | 0 | 0 | 5 | 0 |  |
| 1500 | 0.9500 | 0 | 0 | 3 | 2 |  |
| 1800 | 0.9500 | 0 | 1 | 4 | 0 | 0.193 |
| 2100 | 0.9500 | 0 | 0 | 5 | 0 |  |
| 2400 | 0.9500 | 0 | 0 | 4 | 1 |  |
| 2700 | 0.9500 | 0 | 1 | 4 | 0 | -0.096 |
| 3000 | 0.8574 | 2 | 0 | 3 | 0 | -1.108 |
| 3300 | 0.8574 | 0 | 0 | 3 | 2 |  |
| 3600 | 0.8574 | 0 | 2 | 3 | 0 | -0.385 |

What the smoke shows (diagnostic only, one dev seed, no tuning done):

* The **congested gate dominates**: AID07105's observed occupancy averages 16.3% and is ≥ 15% in 69% of
  intervals, so 44/60 ticks never reach the update rule — the entry loop is congested, exactly the case
  §G.3 excludes ("congested flow is not demand").
* Of the 9 ticks that pass the gate, 6 are inside the deadband: with δ = 1.0σ and σ = 623 veh/h, a residual
  must exceed ~5 vehicles per 30 s, while the median |residual| is 60–120 veh/h. The Twin's TKO entry flow
  happened to sit slightly *above* the Proxy's in the few open ticks, so m drifted **down**, away from the
  designed ~8% demand deficit that only appears downstream.
* Consequently m moves in rare 5%-clipped steps (3 updates in an hour) rather than tracking: the m range of
  0.143 stays inside the plan's ≤ 0.20 stability bar, but with only 3 non-zero updates that bar is not
  evidence of tracking quality.
* Also note the requested σ rule is self-limiting: σ estimated from the same OL residual distribution that
  the deadband tests against makes |r| > 1σ rare by construction.

## 5. Snapshot / branch carry of `m`

* Probe run `results/assim/impl/snap_na` (900 s, σ = 100 veh/h probe, snapshot at 600 s):
  `twin/twin_state_600.json` meta now contains `"m": {"tko_insert": 0.9686274509803923}` alongside
  `control_state`, `stream_ptr`, `pending`, `demand_seed`, `sumo_seed`, `demand_path`.
* Branch replay from that snapshot through `citypulse/branching/engine._worker` (A0, horizon 120 s, one
  process each): meta `m = 1.8` → 382 vehicles running at t+120 s; meta `m = 0.5` → 286. The multiplier is
  restored into the branch's stream, so a branch continues the assimilated demand rather than m = 1.

## 6. Artifacts

`results/assim/impl/ASSIM_READY` lists the sha256 of `citypulse/twin/assim.py`
(`5a971bf1470586d20a8e8f6931d47d9907c307a14a85ec53d1bfa2ff299319b4`) and `citypulse/twin/service.py`
(`976dd317088e06c3765d8e4af9db782fef502b930f1084891cb15e200da488ff`). Other touched files:
`demand_stream.py` `eaa7895385e047d097e371fc242e190af1002ef455672d229781815dec1ebea0`,
`branching/engine.py` `4a9c5b63c36e4e9bd3e7ac74f6a93abea9860f628ee35e41d0f952d3a77567d5`,
`tests/test_assim.py` `249ad2c1435e5e3966583242371306e38e86cabf8b3803a7664c92ec9acd3f0c`.
Runs under `results/assim/impl/`: `off_before`, `off_after`, `ol_smoke`, `na_frozen`, `na_smoke`, `snap_na`
(each `proxy/`, `twin/`, `run_info.json`); `sigma_prov.json`, `sigma_small_probe.json`, `meta_probe_*.json`.
`results/assim/eval/` and `citypulse/experiments/normal_assim_eval.py` were not touched.

REPORT DONE
