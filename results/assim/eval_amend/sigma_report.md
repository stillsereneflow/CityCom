# sigma for the amended boundary detector AID07106

Frozen rule (`docs/oct5-normal-assim-plan.md`, Amendment 2026-10-03 20:15): pool the valid
paired 30-s flow residuals in veh/h, `r = (obs_q - twin_q) * 120`, for detector AID07106,
t in [900, 7200] s, from the OL development runs seeds 1001-1003 only; no occupancy
selection; `sigma = 1.4826 * median(|r - median(r)|)`.

**sigma(AID07106) = 533.736000 veh/h**  (median = 0.0 veh/h, MAD = 360.0 veh/h,
pooled n = 603 residuals)

## Counts per seed

| Seed | window timestamps | AID07106 rows present | valid residuals | excluded: missing row | obs invalid | obs q null | twin q null | median (veh/h) | MAD (veh/h) |
|---|---|---|---|---|---|---|---|---|---|
| 1001 | 211 | 211 | 197 | 0 | 14 | 0 | 0 | 0.0 | 360.0 |
| 1002 | 211 | 211 | 204 | 0 | 7 | 0 | 0 | 0.0 | 360.0 |
| 1003 | 211 | 211 | 202 | 0 | 9 | 0 | 0 | -60.0 | 420.0 |
| **all** | **633** | **633** | **603** | **0** | **30** | **0** | **0** | **0.0** | **360.0** |

Exclusion reasons, in the order they are applied:

- **missing row**: the timestamp is in the window but `twin_log.parquet` has no AID07106 row at
  all, i.e. the detector was not in that `SensorMsg` (outside the fixed observed set, or the
  message never arrived).
- **obs invalid**: the row exists but `obs_valid` is false (the sensor emulator's 5% loss).
- **obs q null** / **twin q null**: the row is flagged valid (or is the Twin's own reading) but the
  flow value is absent, so no residual can be formed.

No occupancy-based selection was applied: occupancy plays no part in this estimate.

## Inputs

| Run | twin_log.parquet sha256 |
|---|---|
| `results/assim/eval/ol_1001` | `024f990cffe1f6997b9821738a88a7861258cb521f0d2ab51d47ba3d951f3500` |
| `results/assim/eval/ol_1002` | `9d2fd94341de89f151ef46a99ea722d250b71870f331ddd0884ade5eff1318a2` |
| `results/assim/eval/ol_1003` | `c0e3aad1e0c401eadb4908a291369e8b2991c6ab537b477ef291eb7eb398b5d7` |

Only these three development runs were read; no evaluation-seed (3001-3004) output was opened.

Note: these OL development runs were produced by `citypulse/experiments/normal_assim_eval.py`,
whose as-predeclared launcher adds AID07105 to the Proxy's observed set. That patch changes the
sensor RNG stream, but AID07106's own `twin_q` comes from the Twin's simulation (m = 1, no
observation is consumed), so the paired residuals used here are the residuals of the runs the
amendment names.

SIGMA DONE
