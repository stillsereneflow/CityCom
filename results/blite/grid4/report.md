MODEL: Gemini 3.8 Flash

# B-lite Predeclared Scale Grid Report on Network net4

## 1. Overview

This report documents the baseline evaluation of the B-lite simplified research model on corridor network net4 (`scenarios/kwuntong/blite/net4.net.xml`), evaluating baseline acceptance gates G1–G5 across the predeclared scale grid (**1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4**) per the decision rule in `docs/decision-2026-10-03.md`.

In network net4, merge junction M is lane-preserving: arterial incoming approach `ktr_w6` (6 lanes) and bypass incoming approach `ktb_n2` (2 lanes) merge into `rejoin` without sharing target lanes or yielding right-of-way. Downstream edge `out` maintains 9 lanes to the sink.

Signal timings were generated via SUMO's `tlsCycleAdaptation.py` using `tls_base4.add.xml` (program "0" with yellows) as the base and scale-1.0 demand, written scenarios-free to `results/blite/grid4/tls_webster4.add.xml`. All simulation runs use 7,200 s duration, teleport disabled (`--time-to-teleport -1`), collision action warn, and dynamic rerouting (prob=0.3, period=60s).

---

## 2. Predeclared Scale Grid Evaluation (Gates G1–G3)

| Scale | Tag | Loaded | Inserted | Arrived | Running (end) | Pending (end) | Pending Share | Teleports | Accounting Reconciled | Running Slope (vps) | Pending Slope (vps) | G1 | G2 | G3 | Overall G1–G3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1.0** | `s100` | 21,643 | 11,274 | 10,700 | 574 | 10,366 | **47.9%** | 0 | **PASS** | +0.0392 | +1.4075 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.9** | `s090` | 19,597 | 10,779 | 10,228 | 551 | 8,815 | **45.0%** | 0 | **PASS** | +0.0351 | +1.1436 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.8** | `s080` | 17,265 | 10,097 | 9,571 | 526 | 7,167 | **41.5%** | 0 | **PASS** | -0.0007 | +0.9596 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.7** | `s070` | 15,082 | 9,728 | 9,214 | 514 | 5,352 | **35.5%** | 0 | **PASS** | -0.0176 | +0.7258 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.6** | `s060` | 12,857 | 9,183 | 8,674 | 509 | 3,672 | **28.6%** | 0 | **PASS** | +0.0313 | +0.5851 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.5** | `s050` | 10,921 | 8,646 | 8,139 | 507 | 2,272 | **20.8%** | 0 | **PASS** | +0.0041 | +0.3207 | **PASS** | **PASS** | **FAIL** | **FAIL** |
| **0.4** | `s040` | 8,799 | 8,070 | 7,665 | 405 | 728 | **8.3%** | 0 | **PASS** | +0.0014 | +0.0552 | **PASS** | **PASS** | **FAIL** | **FAIL** |

### Evaluation Notes:
- **G1 (Zero teleports):** **PASS** across all runs (0 teleports recorded).
- **G2 (Vehicle accounting reconciliation):** **PASS** across all runs (`inserted == arrived + running_end`, and `loaded == inserted + pending_end` within 1 vehicle latency).
- **G3 (Pending <= 2% and non-growing queue):** **FAIL** across all scales in the predeclared grid (1.0 down to 0.4). While net4 dramatically improves insertion throughput compared to net3 (pending backlog drops from 19.6% to 8.3% at scale 0.4, and arrived vehicles increase by +1,765), scale 0.4 still ends with 728 pending vehicles (8.3% > 2.0% threshold) and a marginal positive queue growth slope ($+0.0552$ vps $> 0.05$ threshold).

---

## 3. Calibration Gap (08:00–09:00, Informational Only)

Evaluated across the 21 mapped TD detectors over twelve 5-minute intervals (252 cells):

| Scale | Evaluated Cells | GEH < 5 Share | Speed MAE (km/h) | Congestion State Agreement |
|---|---|---|---|---|
| **1.0** | 252 | 3.17% | 19.49 km/h | 82.14% |
| **0.9** | 252 | 2.38% | 19.23 km/h | 81.75% |
| **0.8** | 252 | 1.98% | 19.53 km/h | 82.54% |
| **0.7** | 252 | 1.59% | 19.25 km/h | 82.94% |
| **0.6** | 252 | 2.78% | 19.16 km/h | 83.33% |
| **0.5** | 252 | 3.17% | 20.18 km/h | 82.94% |
| **0.4** | 252 | 5.56% | 20.89 km/h | 82.94% |

*Note: In net4, free flow along the Kwun Tong Bypass greatly reduces mainline travel time errors, dropping Speed MAE from ~31.6 km/h (in net3) to ~19.5 km/h, while Congestion State Agreement increases from ~62.3% to ~82.5%.*

---

## 4. Pending Backlog and Bottleneck Analysis

### 4.1 Pending Backlog by Source Gate

Distribution of pending vehicles at $t = 7,200$ s across evaluated grid scales:

| Source Gate | Location | Scale 1.0 (`s100`) | Scale 0.8 (`s080`) | Scale 0.6 (`s060`) | Scale 0.4 (`s040`) |
|---|---|---:|---:|---:|---:|
| `on_ktb_w2` | Bypass entry ramp (Kai Tin Road) | 2,932 | 2,125 | 1,197 | 0 |
| `on_ktr_w6` | Arterial heavy downstream on-ramp | 2,441 | 1,783 | 992 | 276 |
| `tko_in` | Trunk entry gate (Tseung Kwan O Road WB) | 1,691 | 905 | 82 | 0 |
| `on_ktr_w1` | Arterial entry ramp (Kwun Tong Road) | 1,484 | 1,081 | 671 | 44 |
| `on_ktb_w3` | Bypass mid-corridor on-ramp | 1,278 | 984 | 684 | 408 |
| `on_ktr_w5` | Arterial ramp approaching S4 | 540 | 289 | 46 | 0 |
| **Total Pending** | | **10,366** | **7,167** | **3,672** | **728** |

### 4.2 Top Halting Edges in Last 15 Minutes (Scale 0.4, $t = 6,301–7,200$ s)

| Rank | Edge ID | Description | Mean Halting (veh) | Peak Halting (veh) | Step Sum (900 s) |
|---|---|---|---:|---:|---:|
| 1 | `on_ktr_w6` | Arterial heavy downstream on-ramp | 36.53 | 62 | 32,878 |
| 2 | `on_ktr_w1` | Arterial entry ramp (Kwun Tong Road) | 33.08 | 69 | 29,774 |
| 3 | `on_ktb_w3` | Bypass mid-corridor on-ramp | 32.21 | 39 | 28,988 |
| 4 | `x3_in` | S3 cross-street entry stub | 0.60 | 5 | 539 |
| 5 | `x1_in` | S1 cross-street entry stub | 0.49 | 5 | 438 |
| 6 | `x2_in` | S2 cross-street entry stub | 0.44 | 3 | 400 |
| 7 | `ktr_w4` | Arterial link between S3 and S4 | 0.43 | 7 | 387 |
| 8 | `x4_in` | S4 cross-street entry stub | 0.43 | 4 | 383 |
| 9 | `ktr_w2` | Arterial link between S1 and S2 | 0.42 | 6 | 382 |
| 10 | `on_ktb_w2` | Bypass entry ramp (Kai Tin Road) | 0.38 | 7 | 343 |

### 4.3 Comparison with net3:
- **Resolution of Merge M Defect:** In net3, `ktb_n2` was the severe network bottleneck (holding 371.5 mean halting vehicles at scale 0.4 due to inverted priority yielding at merge M). In net4, `ktb_n2` halting is reduced to **0.00 veh** (free flow at 21.2 m/s).
- **Residual Queuing at Entry Ramps:** With the corridor mainline unblocked, the remaining insertion delays shift entirely upstream to the physical ramp entry gates: `on_ktb_w3` (408 pending), `on_ktr_w6` (276 pending), and `on_ktr_w1` (44 pending). On `on_ktr_w6`, the 2-lane on-ramp merges into `ktr_w6` lanes 4 and 5 while yielding to `ktr_w5` lane-rise traffic. At scale 0.4, overall pending share reaches 8.3%, just above the 2.0% G3 acceptance threshold.

---

## 5. Gates G4 and G5 Details

Per the evaluation protocol, Gates G4 and G5 are evaluated at the largest scale that passes Gates G1–G3. Because no scale in the predeclared grid (**1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4**) passed Gate G3 (scale 0.4 achieved 8.3% pending share and $+0.0552$ vps queue growth), **no scale passed Gates G1–G3**.

Consequently, **Gates G4 and G5 were not reached**.

---

## 6. Decision and Artifacts

**Decision:** **no scale passes** all gates G1–G5 in the predeclared grid (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4).

### Evaluated Files & Hashes (SHA-256):

| Component | File Path | SHA-256 Checksum |
|---|---|---|
| **Network** | `scenarios/kwuntong/blite/net4.net.xml` | `98ad0f780ff1e4d6335e0d6c5d053a902a09b485ca310160e40fab9a3c68d80c` |
| **Signal Plan (Webster)** | `results/blite/grid4/tls_webster4.add.xml` | `0e387da750a5c944af3b28b19bd3647869d73031328dbd38ce8904527dbf6ffa` |
| **Signal Plan (Base 0)** | `scenarios/kwuntong/blite/tls_base4.add.xml` | `cfeed76f57a8f68c0ebfdc9069831de77ee444d64af5513550017c6a264c3836` |
| **Signal Plan (Incident P_inc)** | `scenarios/kwuntong/blite/tls_incident4.add.xml` | `e54fabfce8f1e55a4a56d97382f582913403449fde6edaebf80f758294cb6a95` |
| **Detectors Additional** | `scenarios/kwuntong/blite/detectors4.add.xml` | `2a45506ca311feb1be076afb774914e1c65ca1b66d46a465bcfdfaa3a65d78cf` |
| **Detector Map** | `scenarios/kwuntong/blite/detector_map.json` | `9c712fdaacc304437d27f3689d273b23bba469a5a6555eb6b20fad6470a16590` |
| **Proxy Demand (Scale 1.0)** | `results/blite/grid/demand_s100/proxy.rou.xml` | `bb7c5bdc8d171f54ea2bac27acb5a478ed41e97cd206243cf73c3260b7ec80c9` |
| **Twin Candidates (Scale 1.0)** | `results/blite/grid/demand_s100/twin_cand.rou.xml` | `ab215b750261679b3256d3e14f508e502e9120cae565c63b0d6bfd7041a03670` |
| **Proxy Demand (Scale 0.4)** | `results/blite/grid/demand_s040/proxy.rou.xml` | `0c4274a0e2cd118040f6224460766aef9696d2975dea543bb339e6b74466fda8` |
| **Twin Candidates (Scale 0.4)** | `results/blite/grid/demand_s040/twin_cand.rou.xml` | `ca04a75e25e0847bb6e092ccbc5cc14cf8b2d6d208e126fc300064259d67d160` |

### Predeclared Seeds and Simulation Parameters:
- **Simulation Duration:** `7,200 s`
- **Proxy Simulation Seed:** `1`
- **Twin Simulation Seed:** `2`
- **Twin Demand Seed:** `202`
- **Sensor Seed:** `77`
- **Branching Seeds:** `[2, 3, 4, 5]`
- **Device Rerouting Probability:** `0.3`, **Period:** `60 s`
- **Time to Teleport:** `-1` (disabled)
- **Collision Action:** `warn`

REPORT DONE
