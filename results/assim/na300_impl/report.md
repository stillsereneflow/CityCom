MODEL: deepseek-v4.1-flash

# NA-300 + Twin base factor: review items F2/F3/F5, tests, identity and replay verification

Worktree `D:/CityCom-astra` (HEAD `17d4d8d`, nothing committed). Env for every run and test:
`PYTHONDONTWRITEBYTECODE=1`, `CITYPULSE_NET=blite`, `CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`;
Twin SUMO seed 2, demand-stream seed 202, synth5 routes, no incident. Binding spec:
`docs/na300-qualification-plan.md`; findings: `results/assim/review_dsh.md` (F2, F3, F5).
`citypulse/experiments/normal_assim_eval.py` and `results/assim/na300/` were **not** touched (agy-flash
owns them; its harness already expects `--twin-base-factor`, the `twin_base_factor` snapshot key and
`TwinDemandStream(base_factor=...)`, which is exactly the interface implemented here).

## 1. Changes (file:line)

| File | Lines | What |
|---|---|---|
| `citypulse/twin/assim.py` | 1–22 | Docstring: the 300-s NA-300 rule (ten intervals, `sigma_300`, `m ≤ 1.5`) alongside the 60-s NA. |
| | 75–90 | `NormalAssimilator(..., n_intervals=2)`: number of consecutive 30-s intervals averaged per tick. Default 2 = the predeclared NA, bit-for-bit unchanged. |
| | 92–106 | `update()` takes `n_intervals` intervals instead of a hard-coded pair (`len(obs) != self.n_intervals` → `invalid`). Everything else (occupancy gate, `e_s`, `r`, deadband, ±0.05 step clip, m clip) is the same code path for both modes. |
| `citypulse/twin/service.py` | 33–44 | Mode constants: `ASSIM_PERIODS = {normal: 60, normal300: 300}`, `ASSIM_INTERVALS = {2, 10}`, `ASSIM_M_MAX = {1.8, 1.5}` (= pool scale), `ASSIM_SENSOR_PERIOD = 30`. |
| | 48–70 | **F5**: `load_sigma(assim, sigma_json, boundary_detector)` — with assimilation on, a missing JSON, a JSON without the selected detector's key, or a non-positive value raises `ValueError` at startup (before any socket/SUMO). |
| | 72–77 | `consecutive_window(hist, n_intervals)`: the tick is fed only if the history holds n consecutive 30-s readings. |
| | 79–88 | `run(..., twin_base_factor=1.0)`; the stream is built with the factor, the assimilator with `n_intervals`/`m_max` for the mode. |
| | 106–114 | Snapshot detection is deferred (`snap_t`) instead of writing inside the stepping loop. |
| | 121–139 | Assimilation block: `n_intervals`-window, per-mode period, σ for the selected detector; reasons `updated`/`deadband`/`congested`/`invalid` logged to `assim_log.parquet` exactly as before. |
| | 140–147 | **F2**: the state file and meta are written **after** that timestamp's assimilation tick, so `meta["m"]` is the multiplier the online Twin has been running with since that instant; the meta also records `twin_base_factor`. Snapshot times are unchanged. |
| | 149–151, 170–179 | `twin_stats.json` carries `twin_base_factor`; CLI `--assim {off,normal,normal300}` and `--twin-base-factor` (default 1.0). |
| `citypulse/twin/demand_stream.py` | 1–9, 19 | Docstring; `BASE_FACTOR_ENTRY = "tko_insert"` — the only entry the factor scales. |
| | 23–27, 60–61 | `TwinDemandStream(..., base_factor=1.0, factor_entries=(BASE_FACTOR_ENTRY,))`. |
| | 68–74 | `factor(entry)` (1.0 for every other entry) and `acceptance(entry) = factor·m/scale`. |
| | 114 | `due()` accepts iff `u_n < self.acceptance(edges[0])` — the stream stays a pure function of (seed, factor, m path); at factor 1.0 the expression is float-identical to the old `m/scale`. |
| | 76–95 | **F3**: `base_rate` clamps ±window to the candidate-pool span and divides the count by that actual in-pool length (span ≤ 0 → 0.0). |
| `citypulse/branching/engine.py` | 5–9, 62–64 | Branch worker restores the Twin base factor from the snapshot meta (`meta.get("twin_base_factor") or 1.0`, backward compatible with pre-change snapshots) next to the `m` restore. |
| `tests/test_assim.py` | 1–27, 160–390 | 12 new tests (below); 22 total. |
| `results/assim/na300_impl/` | — | Outputs + four dev harness scripts: `run_na300.py` (two-world launcher with the new flags), `online_logged.py` (production service + insertion recorder), `branch_replay.py` (production branch engine + id comparison), `verify_na300.py` (identity/snapshot-m/ticks), `sigma_prov_300.json`. |

Not changed (out of scope): F1 (κ inert under the old σ), F4 (`m_max = 1.8` unrealizable — NA-300's 1.5
bound is realizable), F6 (two-interval occupancy gate), F7 (1-s update boundary), F8 (hard-coded entry).

## 2. Tests

```
D:/CityCom/.venv/Scripts/python.exe -m pytest tests/test_assim.py -q -p no:cacheprovider   ->  22 passed
D:/CityCom/.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider                ->  67 passed, 3 skipped, 1 failed
```
The one failure is pre-existing and unrelated: `tests/test_sumo_integration.py::test_init_signals_resets_last_loaded_program`
asserts the re-initialised program id is `"0"` while rev5 loads `"webster"`; that test imports only
`citypulse.config/sim/scenario`, none of the four modules changed here (same failure recorded at 721c043
in `results/assim/impl/report.md`).

New tests (12), each pinning one clause:

| Test | Pins |
|---|---|
| `test_na300_window_is_ten_intervals` | exactly ten intervals; nine, eleven or a two-interval window → `invalid`; the 60-s NA still wants two |
| `test_na300_gate_mean_observed_occupancy_below_15pct` | mean observed occupancy ≥ 15% → `congested` (incl. 10/20 mix = 15.0), 14.9% → update; the Twin's occupancy never gates |
| `test_na300_deadband_on_the_mean_residual` | \|mean residual\| = 1σ_300 exactly → `deadband`; 1.008σ → update; residual is the veh/h mean over the ten intervals |
| `test_na300_step_clip_and_m_bounds` | Δ = clip(0.3·e, ±0.05); m ∈ [0.5, 1.5] — m = 1.79 with a large residual stops at **1.5**, never 1.8 |
| `test_na300_invalid_window_no_update` | one invalid/None interval, a missing detector, σ None/0 or base 0 → `invalid`, m unchanged; `Interval` objects accepted |
| `test_na300_service_constants` | the service runs NA-300 at a 300-s tick over ten intervals with `m_max = 1.5` (and NA unchanged at 60 s / 2 / 1.8) |
| `test_consecutive_window` | a gap in the 30-s history, nine readings or an empty history block the tick |
| `test_twin_base_factor_acceptance` | acceptance = u < factor·m/scale; factor scales `tko_insert` only (other entries' ids identical); factor 1.0 equals the pre-change expression exactly; same (seed, factor, m) → same ids; factor 0.85·m = m′ = 0.85 with factor 1.0 (one knob); 0.85·1.5 = 1.275 < scale so acceptance < 1 at the m bound; factor never changes `base_s` |
| `test_base_rate_pool_edge_is_not_truncated` | synthetic pool: `base_rate(t=0) = 80` veh/h (fixed denominator gave 40), interior unchanged, last-candidate window 88, window beyond the pool 0 |
| `test_base_rate_on_the_frozen_pool_has_no_edge_bias` | frozen synth5 pool: interior 2756 veh/h unchanged; every edge tick (t ≤ 300, t ≥ 6900) > 2600 (old: 1432–2592) |
| `test_load_sigma_missing_or_nonpositive_is_a_hard_error` | F5: off → `{}`; missing JSON, absent key, 0, negative, `None`, non-numeric → `ValueError` |
| `test_run_rejects_missing_sigma_before_starting_sumo` | the F5 error fires in `run()` before `traci.start` (monkeypatched to record calls → never called) |

F3 on the frozen pool, old vs new (veh/h):

| t (s) | 60 | 120 | 180 | 240 | 300 | 1800 | 3600 | 6900 | 6960 | 7080 | 7200 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| old `base_s` | 1700 | 1988 | 2304 | 2592 | 2880 | 2908 | 2756 | 2748 | 2488 | 1904 | 1432 |
| new `base_s` | 2838 | 2844 | 2883 | 2883 | 2883 | 2908 | 2756 | 2750 | 2766 | 2722 | 2867 |

## 3. Default-off identity: 900 s, `--assim off`, factor 1.0

Two two-world runs, Proxy seed 1001, no incident, plain Proxy (no sensor patch), 900 s:
`off_before` = the pre-change revision (`--assim off`, no factor flag — the old CLI), `off_after` =
this revision (`--assim off --twin-base-factor 1.0`). Harness: `run_na300.py`.

* `off_before/twin/twin_stats.json` has no `twin_base_factor` key and `run_info.json` records the old
  argv; `off_after`'s records the new flags — the two runs really did execute different revisions.
* `twin_log.parquet`: **420 × 9 in both, byte-identical**, sha256
  `ba03eea1b73c5a4c4eefc9a48d114613b859ce323a66d92b80b2c1f12485eba4` for both; `assert_frame_equal`
  → equal (`results/assim/na300_impl/verify_report.json`, `off_identity`).
* That hash is also the one recorded for the three earlier off runs in `results/assim/impl/report.md`
  (sha256 `ba03eea1…`), i.e. the post-change code reproduces the frozen off-mode behaviour exactly.

## 4. Replay verification (mechanics only)

Two-world, Proxy seed **4001**, 3,600 s, `--assim normal300 --boundary-detector AID07106
--twin-base-factor 0.85 --sigma-json sigma_prov_300.json`, snapshots at 600…3600 every 300 s.
**σ_300 = 200 veh/h in `sigma_prov_300.json` is provisional and is used only for this mechanics
check** — it is not the qualification σ_300 (that is 1.4826·MAD of biased-OL 300-s residuals), and no
4001 output was used to choose any parameter. `replay4001` = the production service; `replay4001_logged`
= the same service (`online_logged.py` calls `citypulse.twin.service.main()`) with an insertion
recorder that calls `insert_due` unchanged and reconstructs the ids it inserted from the same
acceptance rule. Their `twin_log.parquet` are byte-identical (sha256 `69af3e0b…`), so the recorder is
non-invasive.

### 4a. F2 — the snapshot's `m` equals the online `m` after that timestamp's tick

11 snapshots; **11/11 match** (`meta["m"]["tko_insert"] == assim_log.m` of the tick at that timestamp).
**4/11 would have been stale under the old write-before-tick ordering** (the ticks at 600, 900, 2400,
2700 are `updated`), so the check is not vacuous: e.g. at t = 2400 the meta now reads
`1.1059076262083782` where the old code would have written `1.0776315789473685` (−2.6% demand).
Every snapshot also carries `twin_base_factor: 0.85` and the unchanged `stream_ptr`.

### 4b. Branch from the 1,800-s snapshot, 300 s, assimilation frozen

`branch_replay.py` runs the production `citypulse.branching.engine.run_branches` (workers = 1) on
`twin_state_1800.xml.gz` + meta (m = 1.0776315789473685, factor 0.85, `seek(1800)`); the engine never
assimilates, so m is frozen for the whole window.

* online insertions in (1800, 2100]: **366**; branch insertions: **366**;
* **identical vehicle ids, in the same order** (`ids_equal: true`, `sets_equal: true`, both
  difference lists empty) — `branch_replay_1800.json`;
* end-of-window insertion backlog agrees with the online snapshot meta: `pending` = 0 = `backlog_end`.

Falsification (the same branch with one field perturbed) shows the comparison has teeth:

| Branch | meta m | factor | insertions in (1800, 2100] | ids equal |
|---|---|---|---|---|
| as saved | 1.0776315789473685 | 0.85 | 366 | **yes** |
| stale m from the 2400-s snapshot (2400→2700 window) | 1.0776315789473685 (pre-tick) | 0.85 | 352 vs 355 online | no (3 vehicles missing) |
| factor forced to 1.0 (1800→2100 window) | 1.0776315789473685 | 1.0 | 392 vs 366 online | no (26 extra) |

### 4c. NA-300 tick bookkeeping (provisional σ_300 = 200)

12 ticks (300…3600 s): **4 `updated`, 5 `deadband`, 3 `invalid`**, m ∈ [1.0000, 1.1059] (bounds
[0.5, 1.5] never approached). The 3 `invalid` ticks (300, 1500, 1800 s) are Proxy observation dropouts
inside the ten-interval window (`obs_valid = False` in exactly one of the ten), i.e. the "all ten
valid" rule, not a missing message: all ten intervals were present and consecutive in every tick.
Example rows: t = 900 `e_s = 0.168956`, `r = 2.46`, Δ = +0.05 (clipped) → m 1.0263→1.0776; t = 2400
`e_s = 0.087464`, `r = 1.20`, Δ = +0.0262 → m 1.1059; t = 2700 `e_s = −0.080056`, `r = −1.14`,
Δ = −0.0240 → m 1.0793. With the 0.85 factor the controller drives m towards 1/0.85 ≈ 1.18, as
expected for an imposed input reduction.

### 4d. F5 end-to-end

`python -m citypulse.twin.service --assim normal300 --boundary-detector AID07106` (no `--sigma-json`,
and separately with a σ JSON that lacks the AID07106 key) exits 1 with
`ValueError: --assim normal300: sigma_q for boundary detector 'AID07106' is missing or non-positive …`
before any SUMO process or socket exists — the silent-OL failure mode of F5 is closed.

## 5. Outputs

`results/assim/na300_impl/`: `off_before/`, `off_after/`, `replay4001/`, `replay4001_logged/`
(proxy/ + twin/ + run_info.json), `sigma_prov_300.json`, `run_na300.py`, `online_logged.py`,
`branch_replay.py`, `verify_na300.py`, `verify_report.json`, `branch_replay_1800.json`,
`branch_replay_falsify_stale_m_2400.json`, `branch_replay_falsify_factor1_1800.json`, `NA300_READY`.

Nothing was committed. NA-300's qualification runs are agy-flash's, in `results/assim/na300/`.

REPORT DONE
