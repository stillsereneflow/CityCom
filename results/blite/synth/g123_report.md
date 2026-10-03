MODEL: deepseek-v4-flash
# G1-G3 on synthetic boundary demand, B-lite net4

Binding spec: `docs/decision-2026-10-03b-synthetic.md`. The demand is scenario-assumed,
not estimated: constant 2,800 veh/h at `tko_in` (75% bypass / 25% arterial, all to `out`),
all intermediate ramps at 0, 400 veh/h on each cross-street stub, 0-7,200 s,
`CITYPULSE_NET=blite` with net4 files, `CITYPULSE_REROUTE=0`, SUMO seeds 1001/1002/1003,
synthetic Webster signal plan. Non-zero teleports are impossible by construction
(`--time-to-teleport -1`); collisions are counted from `simulation.getCollisions()`.

## 1. Files built

| File | SHA-256 |
|---|---|
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/proxy.rou.xml` | `a057b25d0dfc3f44afef3bddecf684888e65be454ef49f8f5ea93c01dc26954d` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/twin_cand.rou.xml` | `61af4a1867938f8a0feb0f071d7904ea8401b7a1b515f585bc4255c0d6c6246b` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/proxy_shock.rou.xml` | `0f973bacec6c87a3519e47827ecf5e80b5ccf77e83e378cfb40623cbf398d90c` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/demand.json` | `95fa77ef8dba23fcc8fb1e54fa1a1dedf296289b869d4726c3dacb8637a55eb1` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/demand_shock.json` | `bc1ab5fb86affbdf7781a2ab4607f8e478a7f3ee7c6879faf2db181a8be5a610` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/tls_webster_synth.add.xml` | `e92e4d52fd72dd6657dcb715f89713967e7835544b96070c30c8e142bc2b6bac` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/synth/tls_incident_synth.add.xml` | `e7219af2140e3f63a863894d51bb75301ba19826c7efcf83052dc384527547e5` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/net4.net.xml` | `98ad0f780ff1e4d6335e0d6c5d053a902a09b485ca310160e40fab9a3c68d80c` |
| `D:/CityCom-astra/scenarios/kwuntong/blite/detectors4.add.xml` | `2a45506ca311feb1be076afb774914e1c65ca1b66d46a465bcfdfaa3a65d78cf` |

Per-seed output directories: `results/blite/synth/<tag>/` with `history.csv`,
`pending_by_source.csv`, `halting_last30.json`, `collisions.xml`, `run.json`.

## 2. Per-seed gate table

| Seed | Scheduled | Pending | Running | Arrived | Scheduled-(P+R+A) | Teleports | Collisions | Pending share | G1 | G2 | G3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 1001 | 8887 | 2711 | 183 | 5993 | 0 | 0 | 0 | 30.505% | **PASS** | **PASS** | **FAIL** |
| 1002 | 8887 | 2686 | 184 | 6017 | 0 | 0 | 0 | 30.224% | **PASS** | **PASS** | **FAIL** |
| 1003 | 8887 | 2716 | 175 | 5996 | 0 | 0 | 0 | 30.561% | **PASS** | **PASS** | **FAIL** |

### G2 terms (scheduled = pending + running + arrived)

`arrived` counts every route completion in the simulation: the corridor streams end
at `out` and the cross-street stubs end at `xN_out`, so all completions belong in the
identity. Discharge at `out` alone is reported separately in section 3.

- seed 1001: `8887 = 2711 + 183 + 5993` -> gap 0
- seed 1002: `8887 = 2686 + 184 + 6017` -> gap 0
- seed 1003: `8887 = 2716 + 175 + 5996` -> gap 0

### G3 15-min window slopes (limit +0.05 veh/s, after 900 s warm-up)

**seed 1001**

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.01613 | yes |
| running | 1800-2700 | -0.00341 | yes |
| running | 2700-3600 | +0.01341 | yes |
| running | 3600-4500 | +0.00870 | yes |
| running | 4500-5400 | -0.01414 | yes |
| running | 5400-6300 | +0.00775 | yes |
| running | 6300-7200 | -0.00775 | yes |
| backlog `tko_in` | 900-1800 | +0.34973 | **NO** |
| backlog `tko_in` | 1800-2700 | +0.33848 | **NO** |
| backlog `tko_in` | 2700-3600 | +0.37157 | **NO** |
| backlog `tko_in` | 3600-4500 | +0.34926 | **NO** |
| backlog `tko_in` | 4500-5400 | +0.41324 | **NO** |
| backlog `tko_in` | 5400-6300 | +0.37208 | **NO** |
| backlog `tko_in` | 6300-7200 | +0.41395 | **NO** |
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

**seed 1002**

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.01152 | yes |
| running | 1800-2700 | -0.00292 | yes |
| running | 2700-3600 | +0.00512 | yes |
| running | 3600-4500 | +0.01142 | yes |
| running | 4500-5400 | -0.00451 | yes |
| running | 5400-6300 | +0.01282 | yes |
| running | 6300-7200 | -0.00909 | yes |
| backlog `tko_in` | 900-1800 | +0.34081 | **NO** |
| backlog `tko_in` | 1800-2700 | +0.33841 | **NO** |
| backlog `tko_in` | 2700-3600 | +0.38385 | **NO** |
| backlog `tko_in` | 3600-4500 | +0.33527 | **NO** |
| backlog `tko_in` | 4500-5400 | +0.40463 | **NO** |
| backlog `tko_in` | 5400-6300 | +0.37042 | **NO** |
| backlog `tko_in` | 6300-7200 | +0.40306 | **NO** |
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

**seed 1003**

| Series | Window (s) | Slope (veh/s) | Pass |
|---|---|---:|---|
| running | 900-1800 | -0.00110 | yes |
| running | 1800-2700 | +0.00507 | yes |
| running | 2700-3600 | +0.00645 | yes |
| running | 3600-4500 | +0.00735 | yes |
| running | 4500-5400 | -0.02113 | yes |
| running | 5400-6300 | +0.00887 | yes |
| running | 6300-7200 | -0.01836 | yes |
| backlog `tko_in` | 900-1800 | +0.35532 | **NO** |
| backlog `tko_in` | 1800-2700 | +0.35103 | **NO** |
| backlog `tko_in` | 2700-3600 | +0.37488 | **NO** |
| backlog `tko_in` | 3600-4500 | +0.33885 | **NO** |
| backlog `tko_in` | 4500-5400 | +0.40358 | **NO** |
| backlog `tko_in` | 5400-6300 | +0.37843 | **NO** |
| backlog `tko_in` | 6300-7200 | +0.41613 | **NO** |
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

## 3. Discharge and queues

Discharge at `out` is the number of distinct vehicles that reached the `out` edge, as a
mean rate over the run (veh/h). Halting is per-edge mean and max over the last 30 min
(1,800 one-second steps, so the mean denominator is the full window). The queue is the
insertion backlog (pending vehicles), largest value over the run.

| Seed | Discharge at `out` (veh/h) | Largest queue (veh) | Largest queue source | Peak time (s) |
|---|---:|---:|---|---:|
| 1001 | 1,402 | 2711 | `tko_in` (2711) | 7200 |
| 1002 | 1,414 | 2687 | `tko_in` (2687) | 7200 |
| 1003 | 1,404 | 2716 | `tko_in` (2716) | 7200 |

### seed 1001: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `x3_in` | 1.08 | 11 |
| `ktr_w4` | 1.01 | 13 |
| `x4_in` | 0.86 | 7 |
| `ktr_w2` | 0.69 | 5 |
| `ktr_w3` | 0.64 | 8 |
| `x2_in` | 0.54 | 6 |
| `ktr_w1` | 0.48 | 6 |
| `x1_in` | 0.48 | 5 |
| `tko_vms` | 0.33 | 6 |
| `tko_in` | 0.01 | 1 |

### seed 1002: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `ktr_w4` | 1.09 | 11 |
| `x3_in` | 1.07 | 11 |
| `x4_in` | 0.88 | 8 |
| `ktr_w2` | 0.82 | 8 |
| `tko_vms` | 0.58 | 7 |
| `ktr_w3` | 0.52 | 9 |
| `x2_in` | 0.52 | 6 |
| `x1_in` | 0.51 | 4 |
| `ktr_w1` | 0.48 | 7 |
| `tko_in` | 0.02 | 1 |
| `ms_on_ktr_w1` | 0.00 | 1 |

### seed 1003: per-edge halting, last 30 min

| Edge | Mean halting (veh) | Max halting (veh) |
|---|---:|---:|
| `ktr_w4` | 1.08 | 12 |
| `x3_in` | 1.03 | 10 |
| `x4_in` | 0.92 | 8 |
| `ktr_w2` | 0.63 | 6 |
| `x2_in` | 0.55 | 7 |
| `ktr_w3` | 0.54 | 10 |
| `x1_in` | 0.47 | 5 |
| `ktr_w1` | 0.43 | 5 |
| `tko_vms` | 0.23 | 4 |
| `tko_in` | 0.01 | 1 |

## 4. Commands

```
python D:/CityCom-astra/results/blite/synth/run_g123.py --seeds 1001 1002 1003
```

## 5. Verdict: G1-G3 FAIL, no READY written

Seeds failing: 1001, 1002, 1003.

Per the binding spec, **the demand and the network were not changed** (no load search).
The observed failure sign is an insertion backlog at `tko_in` that grows at a constant
rate instead of stabilising while the corridor itself stays free-flowing (per-edge
halting in the last 30 min stays at or below ~1 veh). The assumed 2,800 veh/h cannot be
delivered through this entry/diverge configuration: net4 wires the bypass branch to
`tko_vms` lanes 1-2, which are fed only by `tko_in` lane 1 (`tko_in` lane 0 feeds
`tko_1` lane 0, which feeds `tko_vms` lane 0 and the arterial), so the 75% bypass
stream is effectively limited to a single entry lane. The existing reconstructed
demand shows the same signature (`results/blite/grid4/s100/run.json`: 1,691 pending
at `tko_in`).

No READY file was created: `READY` is only written when every seed passes G1-G3.

REPORT DONE
