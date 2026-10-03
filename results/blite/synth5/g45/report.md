MODEL: Gemini 3.8 Flash (High)

# G4, G5 and Audit on Synthetic B-lite Benchmark (net5 / synth5)

Binding spec: `docs/decision-2026-10-03b-synthetic.md` (including amendments 03c net5 and 03d G3-v2).
All runs executed with:
- Working directory: `D:/CityCom-astra`
- Python: `D:/CityCom/.venv/Scripts/python.exe` (SUMO 1.27.1)
- Environment: `CITYPULSE_NET=blite`, `CITYPULSE_BLITE_REV=5`, `CITYPULSE_REROUTE=0`, `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`
- Network: `scenarios/kwuntong/blite/net5.net.xml` with 500m stub `tko_insert`
- Autonomous rerouting disabled (`CITYPULSE_REROUTE=0`), teleports disabled (`--time-to-teleport -1`), collision action `warn`.

## 1. Input Verification (Frozen sha256 in `results/blite/synth5/READY`)

| File | Expected sha256 | Match |
|---|---|---|
| `D:/CityCom-astra/scenarios/kwuntong/blite/net5.net.xml` | `8ab6c9e8ef0cc4d03b690d8f8210aad8c7a88c384d782df673079830a6c012d8` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/detectors5.add.xml` | `2a45506ca311feb1be076afb774914e1c65ca1b66d46a465bcfdfaa3a65d78cf` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/proxy.rou.xml` | `86a19d8f7a2a72fff1c864eee17f249e77b952525bcfa487588d1d5efc8bfa93` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/proxy_shock.rou.xml` | `78926be5a23ef2133ca5b8944ef1446a758409d5ab02fafce090107ff61aff3f` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml` | `e7219af2140e3f63a863894d51bb75301ba19826c7efcf83052dc384527547e5` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml` | `e92e4d52fd72dd6657dcb715f89713967e7835544b96070c30c8e142bc2b6bac` | **PASS** |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth5/twin_cand.rou.xml` | `a449427a0cb47e6efe31d16a98365aa115d1f146fd2ad5af40355ed52dd4e212` | **PASS** |
| `D:/CityCom-astra/results/blite/synth5/g3v2.py` | `cba21ab944df0d625ac901972046267e2dc0d9740cb5fe7c75c7345750fcf202` | **PASS** |

## 2. G4: Incident Detection and False-Alarm Controls

Configuration:
- Incident: `ktb_n1`, lanes 0–1, position 900 m, duration 4,500–5,400 s (Proxy truth only).
- Twin: receives only `SensorMsg` over ZeroMQ, takes state snapshot at 4,800 s.
- Bottleneck rule: upstream `AID02109` (@ 455.7 m) vs downstream `AID02111` (@ 1054.9 m), normalized residual divergence $B(t) = 0.5 (r_{U,o} - r_{D,o}) + 0.5 (r_{D,v} - r_{U,v})$ with robust median/MAD calibration over 600–4,200 s.
- Detection criterion: $B(t) \ge 3.0$ for 2 consecutive 30 s intervals.

| Scenario | Routes | Truth Condition | First Crossing (s) | All Crossings (s) | Max $B$ | Status |
|---|---|---|---|---|---|---|
| Incident Run | `proxy.rou.xml` | Incident 4,500–5,400 s | 4860.0 | 4860.0, 4890.0, 4920.0, 4950.0, 4980.0, 5040.0, 5070.0, 5160.0, 5190.0, 5220.0, 5250.0, 5280.0, 5310.0, 5340.0, 5370.0, 5400.0, 5430.0, 5460.0, 5490.0, 5520.0, 5850.0, 6420.0 | 17.16 | **DETECTED** |
| Control (a) | `proxy.rou.xml` | No incident | None | None | 2.57 | **SILENT** (PASS) |
| Control (b) Demand Shock (+30%) | `proxy_shock.rou.xml` | No incident | None | None | 2.73 | **SILENT** (PASS) |

- **G4 Verdict:** **PASS** (Incident detected at 4860.0s after 4,500 s; 0 false alarms on both controls).

## 3. G5: Action Effect and Intervention Authority

Configuration:
- Branching snapshot: Twin snapshot at $t = 4,800$ s.
- Horizon: 15-min horizon (900 s, $t \in [4800, 5700]$ s).
- Point-blockage hypothesis: edge `ktb_n1`, lanes 0–1 closed at position 755.3 m (midpoint of observed detectors AID02109 and AID02111), mode `blocker`, duration 3,600 s.
- TKO Stream during intervention [4,800, 5,700] s: **664 vehicles** (Twin candidate stream accepted).
- Actions: A0 (baseline), A1 (signals $P_{inc}$), A2 (VMS diversion), A3 (A1 + A2), A4 (A2 with boosted compliance).
- Delay definition: includes both network timeLoss and insertion/stub waiting backlog; unfinished vehicles are accounted for.

### Selection Replications (Seeds: [11, 12, 13, 14])

| Action | Mean Delay (veh·h) | Delay SD | Paired $\Delta$ vs A0 Mean (veh·h) | 95% CI (t-dist) | 95% CI Excludes 0 | Mean Diverted (veh) | Reach Share (%) | Arrived | Running (Unfinished) | Backlog End |
|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | 33.88 | 0.86 | baseline | baseline | — | 0.0 | 0.0% | 907.8 | 438.2 | 0.0 |
| **A1** | 32.33 | 0.19 | -1.55 | [-3.08, -0.02] | **YES** | 0.0 | 0.0% | 914.5 | 431.5 | 0.0 |
| **A2** | 25.11 | 1.17 | -8.76 | [-10.37, -7.16] | **YES** | 153.0 | 23.0% | 963.5 | 382.5 | 0.0 |
| **A3** | 19.82 | 1.01 | -14.05 | [-15.39, -12.72] | **YES** | 153.0 | 23.0% | 1001.2 | 344.8 | 0.0 |
| **A4** | 26.31 | 0.50 | -7.57 | [-8.69, -6.44] | **YES** | 237.5 | 35.8% | 951.0 | 395.0 | 0.0 |

- Actions whose 95% CI excludes 0: **A1, A2, A3, A4**
- Reach requirement (target ≥ 5%): **PASS** (A2 reach: 23.0%, A4 reach: 35.8%)
- Effect requirement (≥ 1 action CI excludes 0): **PASS**
- **G5 Selection Verdict:** **PASS**

### Audit Replications (Untouched) (Seeds: [21, 22, 23, 24])

| Action | Mean Delay (veh·h) | Delay SD | Paired $\Delta$ vs A0 Mean (veh·h) | 95% CI (t-dist) | 95% CI Excludes 0 | Mean Diverted (veh) | Reach Share (%) | Arrived | Running (Unfinished) | Backlog End |
|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | 33.64 | 0.86 | baseline | baseline | — | 0.0 | 0.0% | 905.0 | 441.0 | 0.0 |
| **A1** | 32.85 | 0.44 | -0.80 | [-1.94, +0.35] | No | 0.0 | 0.0% | 912.0 | 434.0 | 0.0 |
| **A2** | 25.19 | 0.59 | -8.45 | [-9.35, -7.55] | **YES** | 152.5 | 23.0% | 962.0 | 384.0 | 0.0 |
| **A3** | 20.50 | 0.58 | -13.15 | [-14.06, -12.23] | **YES** | 152.8 | 23.0% | 999.2 | 346.8 | 0.0 |
| **A4** | 26.35 | 0.47 | -7.30 | [-8.61, -5.98] | **YES** | 237.8 | 35.8% | 952.8 | 393.2 | 0.0 |

- Actions whose 95% CI excludes 0: **A2, A3, A4**
- Audit Note: Audit seeds run after selection and never influenced the choice of action or hypothesis.

## 4. Audit Checks

### (i) Snapshot Completeness and Reload Determinism
- Snapshot file: `results/blite/synth5/g45/g4_incident/twin/twin_state_4800.xml.gz`
- Pending vehicles carried in snapshot: **2**
- Controller state carried in snapshot: TLS program and phase preserved; lane closures / max speed re-applied via `ControlState`.
- Two independent reloads stepped 60 s:
  - Initial TLS state matches: **YES**
  - Initial pending vehicles match: **YES**
  - Vehicle positions / speeds identical over 60 steps (tolerance 1e-6): **YES** (Max position difference: `0.00e+00` m)
- **Audit (i) Verdict:** **PASS**

### (ii) Information Firewall and SensorMsg Schema
- SensorMsg schema strictly enforced: keys `['obs', 'period', 't', 'type']`, ObsItem keys `['detector', 'o', 'q', 'v', 'valid']`.
- Ground truth injection probes:
  - Probe `extra incident truth field`: **Correctly rejected by firewall**
  - Probe `extra lanes_closed truth field`: **Correctly rejected by firewall**
  - Probe `extra truth_pos in obs`: **Correctly rejected by firewall**
  - Probe `valid sensor message`: **Accepted valid schema**
- Logged columns in `twin_log.parquet`: `['detector', 'obs_o', 'obs_q', 'obs_v', 'obs_valid', 't', 'twin_o', 'twin_q', 'twin_v']` (Contains only observation and Twin's own readings; zero ground truth fields present).
- **Audit (ii) Verdict:** **PASS**

## 5. Gate Summary

| Gate | Criterion | Status | Verdict |
|---|---|---|---|
| **G4** | Detection after 4,500s; zero false alarms on controls (a) & (b) | Incident detected at 4860.0s; both controls silent | **PASS** |
| **G5** | Reach ≥ 5%; at least one action paired delay 95% CI excludes 0 | Reach = 23.0%; significant actions: A1, A2, A3, A4 | **PASS** |
| **Audit (i)** | Snapshot state carries pending & TLS; reload 60s identical (tol 1e-6) | Exact match across 60 steps (max diff 0.00e+00m) | **PASS** |
| **Audit (ii)** | No truth fields reach the Twin | Zero truth fields; strict schema rejection verified | **PASS** |

## 6. Execution Commands

```pwsh
# Set environment
$env:CITYPULSE_NET="blite"
$env:CITYPULSE_BLITE_REV="5"
$env:CITYPULSE_REROUTE="0"
$env:PYTHONDONTWRITEBYTECODE="1"
$env:OPENBLAS_NUM_THREADS="1"

# Run entire G4, G5 and audit pipeline
D:/CityCom/.venv/Scripts/python.exe results/blite/synth5/g45/run_g45.py
```

REPORT DONE
