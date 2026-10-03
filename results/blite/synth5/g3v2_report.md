MODEL: deepseek-v4.1-flash
# G3-v2: post-hoc amended running-count criterion, synthetic demand, B-lite net5

## Amendment statement

This document records an **explicitly post-hoc amendment** of the G3 running-count
criterion (decision 2026-10-03d), made after the original protocol had already been
run and read.  It is not a pre-registered gate and it does not revise the original
result: the original protocol result is **FAIL**, on the running-count 15-min windows
of seeds 1002 and 1003 (seed 1002 running 4500-5400 s +0.05439 veh/s, seed 1003
running 2700-3600 s +0.06142 veh/s, limit +0.05 veh/s).  That verdict is preserved
unchanged in `results/blite/synth5/g123_report.md`; nothing in it was edited, and
`g123_report.md` remains the binding protocol record.

Every other gate of the original protocol is retained unchanged and is *recomputed*
here from the recorded per-seed outputs (`g123_seed<seed>/run.json`, `history.csv`,
`pending_by_source.csv`): G1, G2, the pending share, every per-source insertion
backlog 15-min window slope and every `pending(TKO) + occupancy(tko_insert)` 15-min
window slope.  Only the running-count 15-min window gate is replaced: G3-v2 fits an
OLS line **with an intercept** to every recorded running-count sample with time in
the closed interval `[a, 7200]` for each `a` in `{900, 1800, 2700, 3600, 4500, 5400,
6300}`, per seed separately, on the actual timestamps and the unchanged 60-s
sampling - no smoothing, no exclusions, no pooling of seeds, no boundary adjustment.
Every slope must be <= +0.05 veh/s; a missing expected sample makes the gate
**unevaluated**, never passed.  **No simulation was run for this document.**

## 1. Per-seed retained gates and G3-v2 verdict

| Seed | Samples (60 s) | Teleports | Collisions | G1 | G2 gap | G2 | Pending share | Backlog slopes | Stub slopes | Retained gates | G3-v2 |
|---|---:|---:|---:|---|---:|---|---:|---|---|---|---|
| 1001 | 120 | 0 | 0 | **PASS** | 0 | **PASS** | 0.000% (**PASS**) | max +0.00037 (**PASS**) | max +0.02037 (**PASS**) | **PASS** | **PASS** |
| 1002 | 120 | 0 | 0 | **PASS** | 0 | **PASS** | 0.000% (**PASS**) | max +0.00037 (**PASS**) | max +0.03380 (**PASS**) | **PASS** | **PASS** |
| 1003 | 120 | 0 | 0 | **PASS** | 0 | **PASS** | 0.000% (**PASS**) | max +0.00037 (**PASS**) | max +0.02623 (**PASS**) | **PASS** | **PASS** |

## 2. G3-v2 suffix fits (running count, closed interval [a, 7200])

**seed 1001** (recorded samples 60-7200 s, 120 at 60 s)

| Interval (s) | Samples | Expected | Slope (veh/s) | <= +0.05 |
|---|---:|---:|---:|---|
| 900-7200 | 106 | 106 | +0.00511 | yes |
| 1800-7200 | 91 | 91 | +0.00931 | yes |
| 2700-7200 | 76 | 76 | +0.01267 | yes |
| 3600-7200 | 61 | 61 | +0.01237 | yes |
| 4500-7200 | 46 | 46 | +0.02201 | yes |
| 5400-7200 | 31 | 31 | +0.02705 | yes |
| 6300-7200 | 16 | 16 | +0.03103 | yes |

G3-v2 verdict for seed 1001: **PASS** (worst suffix slope +0.03103 veh/s, limit +0.05 veh/s; all 7 intervals evaluated: yes).

**seed 1002** (recorded samples 60-7200 s, 120 at 60 s)

| Interval (s) | Samples | Expected | Slope (veh/s) | <= +0.05 |
|---|---:|---:|---:|---|
| 900-7200 | 106 | 106 | +0.00600 | yes |
| 1800-7200 | 91 | 91 | +0.01063 | yes |
| 2700-7200 | 76 | 76 | +0.01433 | yes |
| 3600-7200 | 61 | 61 | +0.01460 | yes |
| 4500-7200 | 46 | 46 | +0.02093 | yes |
| 5400-7200 | 31 | 31 | +0.02075 | yes |
| 6300-7200 | 16 | 16 | +0.04069 | yes |

G3-v2 verdict for seed 1002: **PASS** (worst suffix slope +0.04069 veh/s, limit +0.05 veh/s; all 7 intervals evaluated: yes).

**seed 1003** (recorded samples 60-7200 s, 120 at 60 s)

| Interval (s) | Samples | Expected | Slope (veh/s) | <= +0.05 |
|---|---:|---:|---:|---|
| 900-7200 | 106 | 106 | +0.00418 | yes |
| 1800-7200 | 91 | 91 | +0.00933 | yes |
| 2700-7200 | 76 | 76 | +0.01225 | yes |
| 3600-7200 | 61 | 61 | +0.00916 | yes |
| 4500-7200 | 46 | 46 | +0.01991 | yes |
| 5400-7200 | 31 | 31 | +0.01976 | yes |
| 6300-7200 | 16 | 16 | +0.03061 | yes |

G3-v2 verdict for seed 1003: **PASS** (worst suffix slope +0.03061 veh/s, limit +0.05 veh/s; all 7 intervals evaluated: yes).

## 3. Retained-gate detail

**seed 1001**

- G1: teleports 0, collisions 0 -> **PASS**
- G2 at step 7200: `8886 = 0 + 391 + 8495` -> gap 0 -> **PASS**
- pending share: 0/8886 = 0.000% <= 2% -> **PASS**
- per-source backlog 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Source | Window (s) | Samples | Slope (veh/s) | Pass |
|---|---|---:|---:|---|
| `tko_insert` | 900-1800 | 16 | +0.00000 | yes |
| `tko_insert` | 1800-2700 | 16 | +0.00000 | yes |
| `tko_insert` | 2700-3600 | 16 | +0.00000 | yes |
| `tko_insert` | 3600-4500 | 16 | +0.00000 | yes |
| `tko_insert` | 4500-5400 | 16 | +0.00037 | yes |
| `tko_insert` | 5400-6300 | 16 | -0.00037 | yes |
| `tko_insert` | 6300-7200 | 16 | +0.00000 | yes |
| `x1_in` | 900-1800 | 16 | +0.00000 | yes |
| `x1_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x1_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x1_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x1_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x1_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x1_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x2_in` | 900-1800 | 16 | +0.00000 | yes |
| `x2_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x2_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x2_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x2_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x2_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x2_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x3_in` | 900-1800 | 16 | +0.00000 | yes |
| `x3_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x3_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x3_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x3_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x3_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x3_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x4_in` | 900-1800 | 16 | +0.00000 | yes |
| `x4_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x4_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x4_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x4_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x4_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x4_in` | 6300-7200 | 16 | +0.00000 | yes |

- `pending(TKO) + occupancy(tko_insert)` 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Window (s) | Samples | Slope (veh/s) | Pass |
|---|---:|---:|---|
| 900-1800 | 16 | -0.02701 | yes |
| 1800-2700 | 16 | -0.01017 | yes |
| 2700-3600 | 16 | +0.01167 | yes |
| 3600-4500 | 16 | -0.02287 | yes |
| 4500-5400 | 16 | +0.02037 | yes |
| 5400-6300 | 16 | +0.00946 | yes |
| 6300-7200 | 16 | +0.00314 | yes |

**seed 1002**

- G1: teleports 0, collisions 0 -> **PASS**
- G2 at step 7200: `8886 = 0 + 405 + 8481` -> gap 0 -> **PASS**
- pending share: 0/8886 = 0.000% <= 2% -> **PASS**
- per-source backlog 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Source | Window (s) | Samples | Slope (veh/s) | Pass |
|---|---|---:|---:|---|
| `tko_insert` | 900-1800 | 16 | +0.00000 | yes |
| `tko_insert` | 1800-2700 | 16 | +0.00000 | yes |
| `tko_insert` | 2700-3600 | 16 | +0.00000 | yes |
| `tko_insert` | 3600-4500 | 16 | +0.00000 | yes |
| `tko_insert` | 4500-5400 | 16 | +0.00037 | yes |
| `tko_insert` | 5400-6300 | 16 | -0.00037 | yes |
| `tko_insert` | 6300-7200 | 16 | +0.00000 | yes |
| `x1_in` | 900-1800 | 16 | +0.00000 | yes |
| `x1_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x1_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x1_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x1_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x1_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x1_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x2_in` | 900-1800 | 16 | +0.00000 | yes |
| `x2_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x2_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x2_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x2_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x2_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x2_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x3_in` | 900-1800 | 16 | +0.00000 | yes |
| `x3_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x3_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x3_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x3_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x3_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x3_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x4_in` | 900-1800 | 16 | +0.00000 | yes |
| `x4_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x4_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x4_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x4_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x4_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x4_in` | 6300-7200 | 16 | +0.00000 | yes |

- `pending(TKO) + occupancy(tko_insert)` 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Window (s) | Samples | Slope (veh/s) | Pass |
|---|---:|---:|---|
| 900-1800 | 16 | -0.02248 | yes |
| 1800-2700 | 16 | -0.00784 | yes |
| 2700-3600 | 16 | +0.01407 | yes |
| 3600-4500 | 16 | -0.02012 | yes |
| 4500-5400 | 16 | +0.03380 | yes |
| 5400-6300 | 16 | -0.00174 | yes |
| 6300-7200 | 16 | +0.01495 | yes |

**seed 1003**

- G1: teleports 0, collisions 0 -> **PASS**
- G2 at step 7200: `8886 = 0 + 392 + 8494` -> gap 0 -> **PASS**
- pending share: 0/8886 = 0.000% <= 2% -> **PASS**
- per-source backlog 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Source | Window (s) | Samples | Slope (veh/s) | Pass |
|---|---|---:|---:|---|
| `tko_insert` | 900-1800 | 16 | +0.00000 | yes |
| `tko_insert` | 1800-2700 | 16 | +0.00000 | yes |
| `tko_insert` | 2700-3600 | 16 | +0.00000 | yes |
| `tko_insert` | 3600-4500 | 16 | +0.00000 | yes |
| `tko_insert` | 4500-5400 | 16 | +0.00037 | yes |
| `tko_insert` | 5400-6300 | 16 | -0.00037 | yes |
| `tko_insert` | 6300-7200 | 16 | -0.00012 | yes |
| `x1_in` | 900-1800 | 16 | +0.00000 | yes |
| `x1_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x1_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x1_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x1_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x1_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x1_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x2_in` | 900-1800 | 16 | +0.00000 | yes |
| `x2_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x2_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x2_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x2_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x2_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x2_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x3_in` | 900-1800 | 16 | +0.00000 | yes |
| `x3_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x3_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x3_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x3_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x3_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x3_in` | 6300-7200 | 16 | +0.00000 | yes |
| `x4_in` | 900-1800 | 16 | +0.00000 | yes |
| `x4_in` | 1800-2700 | 16 | +0.00000 | yes |
| `x4_in` | 2700-3600 | 16 | +0.00000 | yes |
| `x4_in` | 3600-4500 | 16 | +0.00000 | yes |
| `x4_in` | 4500-5400 | 16 | +0.00000 | yes |
| `x4_in` | 5400-6300 | 16 | +0.00000 | yes |
| `x4_in` | 6300-7200 | 16 | +0.00000 | yes |

- `pending(TKO) + occupancy(tko_insert)` 15-min window slopes (limit +0.05 veh/s) -> **PASS**

| Window (s) | Samples | Slope (veh/s) | Pass |
|---|---:|---:|---|
| 900-1800 | 16 | -0.03824 | yes |
| 1800-2700 | 16 | -0.01451 | yes |
| 2700-3600 | 16 | +0.02002 | yes |
| 3600-4500 | 16 | -0.03145 | yes |
| 4500-5400 | 16 | +0.02623 | yes |
| 5400-6300 | 16 | -0.00137 | yes |
| 6300-7200 | 16 | +0.01686 | yes |

## 4. Diagnostics: original 15-min running-count window slopes

Not a gate in this document - the replaced criterion, listed so the amendment
can be read next to what it replaces.  These are the slopes that made the
original protocol FAIL (marked **NO**).

| Seed | Window (s) | Samples | Slope (veh/s) | Original pass |
|---|---|---:|---:|---|
| 1001 | 900-1800 | 16 | -0.05051 | yes |
| 1001 | 1800-2700 | 16 | +0.00400 | yes |
| 1001 | 2700-3600 | 16 | +0.03998 | yes |
| 1001 | 3600-4500 | 16 | -0.02674 | yes |
| 1001 | 4500-5400 | 16 | +0.04184 | yes |
| 1001 | 5400-6300 | 16 | -0.01240 | yes |
| 1001 | 6300-7200 | 16 | +0.03103 | yes |
| 1002 | 900-1800 | 16 | -0.05299 | yes |
| 1002 | 1800-2700 | 16 | -0.00020 | yes |
| 1002 | 2700-3600 | 16 | +0.03662 | yes |
| 1002 | 3600-4500 | 16 | -0.01534 | yes |
| 1002 | 4500-5400 | 16 | +0.05439 | **NO** |
| 1002 | 5400-6300 | 16 | -0.01988 | yes |
| 1002 | 6300-7200 | 16 | +0.04069 | yes |
| 1003 | 900-1800 | 16 | -0.03809 | yes |
| 1003 | 1800-2700 | 16 | -0.01208 | yes |
| 1003 | 2700-3600 | 16 | +0.06142 | **NO** |
| 1003 | 3600-4500 | 16 | -0.02772 | yes |
| 1003 | 4500-5400 | 16 | +0.04794 | yes |
| 1003 | 5400-6300 | 16 | -0.01811 | yes |
| 1003 | 6300-7200 | 16 | +0.03061 | yes |

## 5. Caveat

G3-v2 is a **finite-horizon operational gate, not proof of stationarity**.  It
asks only whether the recorded running count, over each suffix of the 2 h
horizon that starts at or after the 900 s warm-up, has an OLS trend no steeper
than +0.05 veh/s.  A pass is consistent with a bounded, oscillating or slowly
settling count on this horizon; it does not establish that the corridor is in
steady state, that the trend would stay flat beyond 7,200 s, or that the same
holds for other seeds, demand levels or incidents.  The amendment was chosen
after seeing the original result and is weaker than the replaced gate by
construction: it cannot overturn the original FAIL, only characterise the
running count over the longer suffixes.

## 6. Verdict

All three seeds pass every retained gate and G3-v2.
`results/blite/synth5/READY` lists the SHA-256 of `scenarios/kwuntong/blite/net5.net.xml`,
`scenarios/kwuntong/blite/detectors5.add.xml`, every file under
`scenarios/kwuntong/blite/synth5/` and `results/blite/synth5/g3v2.py`:

- `D:/CityCom-astra/scenarios/kwuntong/blite/net5.net.xml`  `8ab6c9e8ef0cc4d03b690d8f8210aad8c7a88c384d782df673079830a6c012d8`
- `D:/CityCom-astra/scenarios/kwuntong/blite/detectors5.add.xml`  `2a45506ca311feb1be076afb774914e1c65ca1b66d46a465bcfdfaa3a65d78cf`
- `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/proxy.rou.xml`  `86a19d8f7a2a72fff1c864eee17f249e77b952525bcfa487588d1d5efc8bfa93`
- `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/proxy_shock.rou.xml`  `78926be5a23ef2133ca5b8944ef1446a758409d5ab02fafce090107ff61aff3f`
- `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml`  `e7219af2140e3f63a863894d51bb75301ba19826c7efcf83052dc384527547e5`
- `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml`  `e92e4d52fd72dd6657dcb715f89713967e7835544b96070c30c8e142bc2b6bac`
- `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/twin_cand.rou.xml`  `a449427a0cb47e6efe31d16a98365aa115d1f146fd2ad5af40355ed52dd4e212`
- `D:/CityCom-astra/results/blite/synth5/g3v2.py`  `cba21ab944df0d625ac901972046267e2dc0d9740cb5fe7c75c7345750fcf202`

The original protocol verdict **FAIL** (seeds 1002 and 1003 running-count
windows) remains in `g123_report.md`; this READY is issued under the
post-hoc amended criterion of decision 2026-10-03d only.

REPORT DONE
