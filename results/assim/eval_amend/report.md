MODEL: deepseek-v4.1-flash

# Oct 5 plan amendment: boundary detector AID07106 and its σ

Worktree `D:/CityCom-astra`, `PYTHONDONTWRITEBYTECODE=1`, `CITYPULSE_NET=blite`, `CITYPULSE_BLITE_REV=5`,
`CITYPULSE_REROUTE=0`. Spec: `docs/oct5-normal-assim-plan.md` §"Amendment 2026-10-03 20:15".
Nothing committed. `citypulse/experiments/normal_assim_eval.py` and `results/assim/eval/` were **not**
written to (only `ol_1001`, `ol_1002`, `ol_1003`'s `twin_log.parquet` were read, for σ).

## 1. The change: `--boundary-detector` in `citypulse/twin/service.py`

| File:line (new revision) | Before → after |
|---|---|
| `citypulse/twin/service.py:4-5` | docstring: "the boundary detector AID07105 (entry edge `tko_insert`) updates …" → "the boundary detector chosen by `--boundary-detector` (default AID07105, entry edge `tko_insert`) updates …" |
| `:33-34` | `BOUNDARY_DETECTOR = "AID07105"   # the only entry with a boundary detector` → same constant, comment now marks it as the **default** that `--boundary-detector` overrides |
| `:39-40` | `def run(..., assim="off", sigma_json=None)` → `..., sigma_json=None, boundary_detector=BOUNDARY_DETECTOR)` |
| `:84-85` | `next((o for o in msg["obs"] if o["detector"] == BOUNDARY_DETECTOR), None)` and `own.get(BOUNDARY_DETECTOR)` → both use `boundary_detector` |
| `:96` | `sigma_q=sigma.get(BOUNDARY_DETECTOR)` → `sigma_q=sigma.get(boundary_detector)` |
| `:123-124` | new `ap.add_argument("--boundary-detector", default=BOUNDARY_DETECTOR, help="detector whose obs/Twin readings feed the TKO assimilator (default AID07105)")` |
| `:126-128` | the `run(...)` call passes `boundary_detector=a.boundary_detector` |

Nothing else changes: `BOUNDARY_ENTRY` (`tko_insert`) still keys `stream.base_rate`/`stream.m`, the
60-s tick, the two-interval pairing, the `--assim off` short-circuit, the assimilator parameters, the
`assim_log.parquet` schema and `twin_stats.json` are all untouched.

**Atomic write.** `results/assim/eval_amend/apply_boundary_detector_flag.py` performs six anchored
string replacements (each asserted to occur exactly once), writes the result to
`citypulse/twin/.service.py.tmp-<pid>` next to the target, `flush()` + `os.fsync()`, then `os.replace()`.
No process can import a half-written file, and a failing anchor aborts before anything is written.

* sha256 **before** `976dd317088e06c3765d8e4af9db782fef502b930f1084891cb15e200da488ff` — identical to the
  revision recorded in `results/assim/impl/ASSIM_READY`, so the baseline really was the pre-change code.
* sha256 **after** `38125d713c9bc43b22297a70fe0138b9c43f30eb66e93857c6327824cafdbf79`.

Also touched (dev helper, additive only): `results/assim/impl/run_assim_smoke.py` gained a
`--boundary-detector` pass-through that is omitted unless given, so its previous invocations behave
exactly as before.

## 2. Tests

`python -m pytest tests/test_assim.py -q` → **10 passed in 0.29 s** (unchanged from the previous report).

## 3. Identity checks (`results/assim/eval_amend/identity_check.py`)

Four 900-s two-world runs, Proxy seed 1001, synth5, no incident, no Proxy patch, `pandas.testing.assert_frame_equal(..., check_dtype=True)`:

| Arm | Before (pre-change code) | After (post-change code) | Result |
|---|---|---|---|
| `--assim off` | `amend_before_off` (port 5701, no flag) | `amend_after_off` (port 5703, no flag) | `twin_log.parquet` **420 × 9, identical**, and **byte-identical**: sha256 `ba03eea1b73c5a4c4eefc9a48d114613b859ce323a66d92b80b2c1f12485eba4` |
| `--assim normal` (default flag) | `amend_before_na` (port 5702, `--sigma-json results/assim/impl/sigma_prov.json`) | `amend_after_na` (port 5704, same args) | `assim_log.parquet` **15 × 6, identical**, and **byte-identical**: sha256 `6f874d236ef53dc84e17ca4d47fe0db33636defe4006949044b9e7539dd61697`; `twin_log.parquet` identical too |

* The `off` hash is the very same `ba03eea1…` the previous report recorded for its own before/after pair —
  three independent 900-s off runs now agree byte for byte.
* The NA pair ran the **default** detector: AID07105 is dropped by the frozen coverage rule
  (`drop_every_3rd`, sorted index 11 of 21), so all 15 ticks are `invalid` and m ≡ 1.0 — exactly the
  pre-change outcome. The default is therefore AID07105 in behaviour, not just in the signature.
* `python -m citypulse.twin.service --help` lists `--boundary-detector BOUNDARY_DETECTOR  detector whose
  obs/Twin readings feed the TKO assimilator (default AID07105)`.

**Flag smoke (evidence the selector actually selects).** `results/assim/eval_amend/runs/flag_1001_aid07106`,
900 s, Proxy seed 1001, `--assim normal --boundary-detector AID07106 --sigma-json
results/assim/eval_amend/sigma_dev_AID07106.json`, no Proxy patch: 15 ticks → **5 `updated`, 9 `deadband`,
1 `invalid`**; m 1.0000 → 1.0448 (min 0.9476, max 1.0448). Its `twin_log.parquet` holds exactly the frozen
14-detector observed set, with AID07106 present and AID07105 absent — i.e. AID07106 needs no coverage patch.

## 4. σ for AID07106 (`results/assim/eval_amend/compute_sigma_amend.py`)

**Wait step.** Checked at the start of the task (20:16): `results/assim/eval/ol_1001`, `ol_1002`, `ol_1003`
each already had a finished `twin_log.parquet` (240 messages, `assim: off`) and `twin_stats.json`, so no
polling was needed. **No evaluation-seed output was opened**; the three dev paths are hard-coded in the script.

Frozen rule applied: pool `r = (obs_q − twin_q) × 120` veh/h for detector AID07106, t ∈ [900, 7200] s, from
those three runs only, no occupancy selection; σ = 1.4826 × median(|r − median(r)|).

| Seed | window timestamps | AID07106 rows | valid residuals | excluded: missing row | obs invalid | obs q null | twin q null | median (veh/h) | MAD (veh/h) |
|---|---|---|---|---|---|---|---|---|---|
| 1001 | 211 | 211 | 197 | 0 | 14 | 0 | 0 | 0.0 | 360.0 |
| 1002 | 211 | 211 | 204 | 0 | 7 | 0 | 0 | 0.0 | 360.0 |
| 1003 | 211 | 211 | 202 | 0 | 9 | 0 | 0 | −60.0 | 420.0 |
| **pooled** | **633** | **633** | **603** | **0** | **30** | **0** | **0** | **0.0** | **360.0** |

* Exclusions: 30 of 633 rows (4.7%, matching the sensor emulator's 5% loss) are `obs_valid == False`;
  **no** missing rows (AID07106 is in the fixed observed set at every timestamp), no null flows.
* **σ(AID07106) = 1.4826 × 360.0 = 533.736 veh/h.** Recomputed independently by a second one-liner: same
  n = 603, median 0.0, MAD 360.0, σ = 533.736.
* Per-seed σ: 1001 = 533.736, 1002 = 533.736, 1003 = 622.692. The provisional AID07105 σ (622.692) is not reused.
* Written `results/assim/eval_amend/sigma_dev_AID07106.json` = `{"AID07106": 533.736}`, sha256
  `9b436a1288132ec9cc2857071fd324be5105529f1753d3f03219af84b3099b10`; counts, exclusions, median and MAD in
  `results/assim/eval_amend/sigma_report.md` (which also lists the sha256 of each input log).
* Caveat recorded in `sigma_report.md`: these OL dev runs come from the as-predeclared harness, whose launcher
  adds AID07105 to the Proxy's observed set. That shifts the sensor RNG stream, but in the OL arm the Twin
  consumes no observation, so AID07106's `twin_q` — and hence the residual definition — is that of the runs the
  amendment names. Any later amendment re-run should use `--boundary-detector AID07106` with the frozen
  coverage rule (no Proxy patch), which is now possible.

## 5. Artifacts

`results/assim/eval_amend/`: `AMEND_READY` (sha256 of `service.py` and of the σ json),
`report.md` (this file), `sigma_report.md`, `sigma_dev_AID07106.json`,
`apply_boundary_detector_flag.py`, `compute_sigma_amend.py`, `identity_check.py`,
`runs/flag_1001_aid07106/` (flag smoke). Run outputs for the identity checks:
`results/assim/impl/amend_before_off|amend_before_na|amend_after_off|amend_after_na/`.
`citypulse/experiments/normal_assim_eval.py` and `results/assim/eval/` untouched; nothing committed.

REPORT DONE
