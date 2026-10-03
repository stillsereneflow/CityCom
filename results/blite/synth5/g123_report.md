MODEL: deepseek-v4.1-flash
# G1-G3 on the synthetic demand, B-lite net5 (repaired entry + diverge + tko_insert)

Binding spec: the Astra decision of 2026-10-03 (`20261003-1823-codex-astra-entry/out.md`).
Demand unchanged and scenario-assumed: constant 2,800 veh/h at `tko_in` (75% bypass /
25% arterial, all to `out`), intermediate ramps 0, 400 veh/h on each cross-street stub,
0-7,200 s.  net5 files, `CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`, incident-free,
synthetic Webster plan from `synth5/tls_webster_synth.add.xml`, seeds 1001/1002/1003,
900 s warm-up.  Teleports are impossible by construction (`--time-to-teleport -1`).

## 1. Per-seed gate table

| Seed | Scheduled | Pending | Running | Arrived | Scheduled-(P+R+A) | Teleports | Collisions | Pending share | G1 | G2 | G3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 1001 | 8886 | 0 | 391 | 8495 | 0 | 0 | 0 | 0.000% | **PASS** | **PASS** | **PASS** |
| 1002 | 8886 | 0 | 405 | 8481 | 0 | 0 | 0 | 0.000% | **PASS** | **PASS** | **FAIL** |
| 1003 | 8886 | 0 | 392 | 8494 | 0 | 0 | 0 | 0.000% | **PASS** | **PASS** | **FAIL** |

### G2 terms, all read at the same step (7,200th step)

`scheduled` = the departures the simulation has reached at that step (SUMO fires
a vehicle's insertion event at the start of the step after its depart time, so
after step 7,200 every vehicle with `depart <= 7,199` is loaded).  The raw count
of `depart < 7,200` is given too: the difference is the final second's
departures, which are still unloaded at that step and are loaded by the flush
step used for the cross-check below.

- seed 1001: step 7200: `8886 = 0 + 391 + 8495` -> gap 0 (raw `depart < 7,200` = 8887); flush cross-check at step 7201: `8887 = 0 + 391 + 8496` -> gap 0
- seed 1002: step 7200: `8886 = 0 + 405 + 8481` -> gap 0 (raw `depart < 7,200` = 8887); flush cross-check at step 7201: `8887 = 0 + 406 + 8481` -> gap 0
- seed 1003: step 7200: `8886 = 0 + 392 + 8494` -> gap 0 (raw `depart < 7,200` = 8887); flush cross-check at step 7201: `8887 = 0 + 391 + 8496` -> gap 0

### G3 15-min window slopes (limit +0.05 veh/s, after the 900 s warm-up)

**seed 1001** (pending share 0.000%)

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.05051 | yes |
| running | 1800-2700 | +0.00400 | yes |
| running | 2700-3600 | +0.03998 | yes |
| running | 3600-4500 | -0.02674 | yes |
| running | 4500-5400 | +0.04184 | yes |
| running | 5400-6300 | -0.01240 | yes |
| running | 6300-7200 | +0.03103 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 900-1800 | -0.02701 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 1800-2700 | -0.01017 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 2700-3600 | +0.01167 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 3600-4500 | -0.02287 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 4500-5400 | +0.02037 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 5400-6300 | +0.00946 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 6300-7200 | +0.00314 | yes |
| backlog `tko_insert` | 900-1800 | +0.00000 | yes |
| backlog `tko_insert` | 1800-2700 | +0.00000 | yes |
| backlog `tko_insert` | 2700-3600 | +0.00000 | yes |
| backlog `tko_insert` | 3600-4500 | +0.00000 | yes |
| backlog `tko_insert` | 4500-5400 | +0.00037 | yes |
| backlog `tko_insert` | 5400-6300 | -0.00037 | yes |
| backlog `tko_insert` | 6300-7200 | +0.00000 | yes |
| backlog `x1_in` | 900-1800 | +0.00000 | yes |
| backlog `x1_in` | 1800-2700 | +0.00000 | yes |
| backlog `x1_in` | 2700-3600 | +0.00000 | yes |
| backlog `x1_in` | 3600-4500 | +0.00000 | yes |
| backlog `x1_in` | 4500-5400 | +0.00000 | yes |
| backlog `x1_in` | 5400-6300 | +0.00000 | yes |
| backlog `x1_in` | 6300-7200 | +0.00000 | yes |
| backlog `x2_in` | 900-1800 | +0.00000 | yes |
| backlog `x2_in` | 1800-2700 | +0.00000 | yes |
| backlog `x2_in` | 2700-3600 | +0.00000 | yes |
| backlog `x2_in` | 3600-4500 | +0.00000 | yes |
| backlog `x2_in` | 4500-5400 | +0.00000 | yes |
| backlog `x2_in` | 5400-6300 | +0.00000 | yes |
| backlog `x2_in` | 6300-7200 | +0.00000 | yes |
| backlog `x3_in` | 900-1800 | +0.00000 | yes |
| backlog `x3_in` | 1800-2700 | +0.00000 | yes |
| backlog `x3_in` | 2700-3600 | +0.00000 | yes |
| backlog `x3_in` | 3600-4500 | +0.00000 | yes |
| backlog `x3_in` | 4500-5400 | +0.00000 | yes |
| backlog `x3_in` | 5400-6300 | +0.00000 | yes |
| backlog `x3_in` | 6300-7200 | +0.00000 | yes |
| backlog `x4_in` | 900-1800 | +0.00000 | yes |
| backlog `x4_in` | 1800-2700 | +0.00000 | yes |
| backlog `x4_in` | 2700-3600 | +0.00000 | yes |
| backlog `x4_in` | 3600-4500 | +0.00000 | yes |
| backlog `x4_in` | 4500-5400 | +0.00000 | yes |
| backlog `x4_in` | 5400-6300 | +0.00000 | yes |
| backlog `x4_in` | 6300-7200 | +0.00000 | yes |

**seed 1002** (pending share 0.000%)

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.05299 | yes |
| running | 1800-2700 | -0.00020 | yes |
| running | 2700-3600 | +0.03662 | yes |
| running | 3600-4500 | -0.01534 | yes |
| running | 4500-5400 | +0.05439 | **NO** |
| running | 5400-6300 | -0.01988 | yes |
| running | 6300-7200 | +0.04069 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 900-1800 | -0.02248 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 1800-2700 | -0.00784 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 2700-3600 | +0.01407 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 3600-4500 | -0.02012 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 4500-5400 | +0.03380 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 5400-6300 | -0.00174 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 6300-7200 | +0.01495 | yes |
| backlog `tko_insert` | 900-1800 | +0.00000 | yes |
| backlog `tko_insert` | 1800-2700 | +0.00000 | yes |
| backlog `tko_insert` | 2700-3600 | +0.00000 | yes |
| backlog `tko_insert` | 3600-4500 | +0.00000 | yes |
| backlog `tko_insert` | 4500-5400 | +0.00037 | yes |
| backlog `tko_insert` | 5400-6300 | -0.00037 | yes |
| backlog `tko_insert` | 6300-7200 | +0.00000 | yes |
| backlog `x1_in` | 900-1800 | +0.00000 | yes |
| backlog `x1_in` | 1800-2700 | +0.00000 | yes |
| backlog `x1_in` | 2700-3600 | +0.00000 | yes |
| backlog `x1_in` | 3600-4500 | +0.00000 | yes |
| backlog `x1_in` | 4500-5400 | +0.00000 | yes |
| backlog `x1_in` | 5400-6300 | +0.00000 | yes |
| backlog `x1_in` | 6300-7200 | +0.00000 | yes |
| backlog `x2_in` | 900-1800 | +0.00000 | yes |
| backlog `x2_in` | 1800-2700 | +0.00000 | yes |
| backlog `x2_in` | 2700-3600 | +0.00000 | yes |
| backlog `x2_in` | 3600-4500 | +0.00000 | yes |
| backlog `x2_in` | 4500-5400 | +0.00000 | yes |
| backlog `x2_in` | 5400-6300 | +0.00000 | yes |
| backlog `x2_in` | 6300-7200 | +0.00000 | yes |
| backlog `x3_in` | 900-1800 | +0.00000 | yes |
| backlog `x3_in` | 1800-2700 | +0.00000 | yes |
| backlog `x3_in` | 2700-3600 | +0.00000 | yes |
| backlog `x3_in` | 3600-4500 | +0.00000 | yes |
| backlog `x3_in` | 4500-5400 | +0.00000 | yes |
| backlog `x3_in` | 5400-6300 | +0.00000 | yes |
| backlog `x3_in` | 6300-7200 | +0.00000 | yes |
| backlog `x4_in` | 900-1800 | +0.00000 | yes |
| backlog `x4_in` | 1800-2700 | +0.00000 | yes |
| backlog `x4_in` | 2700-3600 | +0.00000 | yes |
| backlog `x4_in` | 3600-4500 | +0.00000 | yes |
| backlog `x4_in` | 4500-5400 | +0.00000 | yes |
| backlog `x4_in` | 5400-6300 | +0.00000 | yes |
| backlog `x4_in` | 6300-7200 | +0.00000 | yes |

**seed 1003** (pending share 0.000%)

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.03809 | yes |
| running | 1800-2700 | -0.01208 | yes |
| running | 2700-3600 | +0.06142 | **NO** |
| running | 3600-4500 | -0.02772 | yes |
| running | 4500-5400 | +0.04794 | yes |
| running | 5400-6300 | -0.01811 | yes |
| running | 6300-7200 | +0.03061 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 900-1800 | -0.03824 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 1800-2700 | -0.01451 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 2700-3600 | +0.02002 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 3600-4500 | -0.03145 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 4500-5400 | +0.02623 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 5400-6300 | -0.00137 | yes |
| pending(TKO) + occupancy(`tko_insert`) | 6300-7200 | +0.01686 | yes |
| backlog `tko_insert` | 900-1800 | +0.00000 | yes |
| backlog `tko_insert` | 1800-2700 | +0.00000 | yes |
| backlog `tko_insert` | 2700-3600 | +0.00000 | yes |
| backlog `tko_insert` | 3600-4500 | +0.00000 | yes |
| backlog `tko_insert` | 4500-5400 | +0.00037 | yes |
| backlog `tko_insert` | 5400-6300 | -0.00037 | yes |
| backlog `tko_insert` | 6300-7200 | -0.00012 | yes |
| backlog `x1_in` | 900-1800 | +0.00000 | yes |
| backlog `x1_in` | 1800-2700 | +0.00000 | yes |
| backlog `x1_in` | 2700-3600 | +0.00000 | yes |
| backlog `x1_in` | 3600-4500 | +0.00000 | yes |
| backlog `x1_in` | 4500-5400 | +0.00000 | yes |
| backlog `x1_in` | 5400-6300 | +0.00000 | yes |
| backlog `x1_in` | 6300-7200 | +0.00000 | yes |
| backlog `x2_in` | 900-1800 | +0.00000 | yes |
| backlog `x2_in` | 1800-2700 | +0.00000 | yes |
| backlog `x2_in` | 2700-3600 | +0.00000 | yes |
| backlog `x2_in` | 3600-4500 | +0.00000 | yes |
| backlog `x2_in` | 4500-5400 | +0.00000 | yes |
| backlog `x2_in` | 5400-6300 | +0.00000 | yes |
| backlog `x2_in` | 6300-7200 | +0.00000 | yes |
| backlog `x3_in` | 900-1800 | +0.00000 | yes |
| backlog `x3_in` | 1800-2700 | +0.00000 | yes |
| backlog `x3_in` | 2700-3600 | +0.00000 | yes |
| backlog `x3_in` | 3600-4500 | +0.00000 | yes |
| backlog `x3_in` | 4500-5400 | +0.00000 | yes |
| backlog `x3_in` | 5400-6300 | +0.00000 | yes |
| backlog `x3_in` | 6300-7200 | +0.00000 | yes |
| backlog `x4_in` | 900-1800 | +0.00000 | yes |
| backlog `x4_in` | 1800-2700 | +0.00000 | yes |
| backlog `x4_in` | 2700-3600 | +0.00000 | yes |
| backlog `x4_in` | 3600-4500 | +0.00000 | yes |
| backlog `x4_in` | 4500-5400 | +0.00000 | yes |
| backlog `x4_in` | 5400-6300 | +0.00000 | yes |
| backlog `x4_in` | 6300-7200 | +0.00000 | yes |

## 2. Actual crossings into `tko_in` per 15 min (E1 `nVehContrib`)

Sum of the `tko_in_0` + `tko_in_1` loop contributions in each complete 15-min
window after the warm-up (the per-step `getLastStepVehicleNumber` call
double-counts and is not used anywhere).  The last row is the partial interval
after the horizon, kept only so the file is complete.

| Window (s) | seed 1001 | seed 1002 | seed 1003 |
|---|---:|---:|---:|
| 900-1800 | 703 | 707 | 714 |
| 1800-2700 | 689 | 688 | 690 |
| 2700-3600 | 683 | 684 | 673 |
| 3600-4500 | 698 | 698 | 702 |
| 4500-5400 | 706 | 698 | 704 |
| 5400-6300 | 706 | 717 | 713 |
| 6300-7200 | 741 | 733 | 733 |
| 7200-8100 | 1 | 2 | 1 |

## 3. Lane discharge (E1 crossings, last hour 3,600-7,200 s)

| Edge | seed 1001 | seed 1002 | seed 1003 |
|---|---:|---:|---:|
| `tko_in` | 2,851 | 2,846 | 2,852 |
| `tko_vms` | 2,847 | 2,844 | 2,851 |
| `ktb_w1` | 2,142 | 2,143 | 2,152 |
| `tko_a1` | 702 | 700 | 701 |

Per lane:

| Lane | seed 1001 | seed 1002 | seed 1003 |
|---|---:|---:|---:|
| `AID02105_0` | 930 | 916 | 915 |
| `AID02105_1` | 1,212 | 1,227 | 1,237 |
| `AID07105_0` | 1,606 | 1,600 | 1,601 |
| `AID07105_1` | 1,245 | 1,246 | 1,251 |
| `AID07107_0` | 338 | 325 | 350 |
| `AID07107_1` | 240 | 249 | 224 |
| `AID07107_2` | 124 | 126 | 127 |
| `diag_tko_vms_0` | 704 | 698 | 702 |
| `diag_tko_vms_1` | 929 | 913 | 933 |
| `diag_tko_vms_2` | 1,214 | 1,233 | 1,216 |

## 4. Queues and delay

Stub waiting is the halting time on `tko_insert` accumulated per second (veh-s)
and is part of the delay read-out, not hidden outside it.

| Seed | Discharge at `out` (veh/h) | Largest queue (veh) | Peak time (s) | Stub waiting (veh-s) | Stub waiting mean (veh) |
|---|---:|---:|---:|---:|---:|
| 1001 | 2,654 | 4 | 420 | 180 | 0.025 |
| 1002 | 2,649 | 1 | 5400 | 145 | 0.020 |
| 1003 | 2,656 | 1 | 5400 | 190 | 0.026 |

### seed 1001: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `ktr_w4` | 1.45 | 14 |
| `ktr_w2` | 1.31 | 8 |
| `ktr_w1` | 1.14 | 10 |
| `x3_in` | 1.08 | 11 |
| `x4_in` | 0.86 | 7 |
| `ktr_w3` | 0.69 | 11 |
| `x2_in` | 0.54 | 6 |
| `x1_in` | 0.48 | 5 |
| `tko_insert` | 0.03 | 2 |

### seed 1002: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `ktr_w2` | 1.49 | 11 |
| `ktr_w4` | 1.34 | 11 |
| `ktr_w1` | 1.12 | 9 |
| `x3_in` | 1.07 | 11 |
| `x4_in` | 0.88 | 8 |
| `ktr_w3` | 0.73 | 10 |
| `x2_in` | 0.52 | 6 |
| `x1_in` | 0.51 | 4 |
| `tko_insert` | 0.02 | 2 |

### seed 1003: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `ktr_w4` | 1.39 | 12 |
| `ktr_w2` | 1.38 | 8 |
| `ktr_w1` | 1.28 | 8 |
| `x3_in` | 1.03 | 10 |
| `x4_in` | 0.92 | 8 |
| `ktr_w3` | 0.69 | 11 |
| `x2_in` | 0.55 | 7 |
| `x1_in` | 0.47 | 5 |
| `tko_insert` | 0.03 | 2 |

## 5. Commands

```
python results/blite/synth5/run_g123.py --seeds 1001 1002 1003   # one process per seed, in parallel
```

## 6. Verdict: G1-G3 FAIL, no READY written

Seeds failing: 1002, 1003.  Per the binding spec the
demand and the network were **not** changed further and no READY file exists.

What fails, and only that:

* seed 1002 running 4500-5400 s +0.05439 veh/s, seed 1003 running 2700-3600 s +0.06142 veh/s - the running count, limit +0.05 veh/s.
* Every other G3 series passes on every seed: the pending share is 0.000%,
  every source insertion backlog is 0 for the whole run (slope 0), and the new
  `pending(TKO) + occupancy(tko_insert)` series stays within +/-0.04 veh/s.

Diagnosis: the repaired entry and diverge do deliver the assumed demand - the
  `tko_in` crossings are 673-741 veh per 15 min (2,690-2,960 veh/h) against a
  drawn demand of 2,834 veh/h, the last-hour discharge is 2,846-2,852 veh/h at
  `tko_in` and 2,844-2,851 veh/h at `tko_vms`, split 2,142-2,152 on `ktb_w1`
  (bypass) and 700-702 on `tko_a1` (arterial), pending is 0 at the horizon and
  there are no collisions, no teleports and no queues (worst last-30-min mean
  halting 1.5 veh).  The running count is not trending away: it oscillates with
  a period of roughly 30 min and an amplitude of about +/-30 vehicles around
  ~355 (slopes alternate in sign, e.g. seed 1001 -0.051, +0.004, +0.040,
  -0.027, +0.042, -0.012, +0.031), and the two failing windows are single
  upswings of that oscillation, one per seed and at different windows.  The
  corridor is loaded at ~2,850 veh/h for the first time (net4 never delivered
  the demand), so the 2 h horizon still contains the slow settling of that
  oscillation; the strict per-window slope gate catches it in 2 of 3 seeds.

REPORT DONE
