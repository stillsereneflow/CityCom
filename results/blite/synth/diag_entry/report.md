MODEL: deepseek-v4-flash
# `tko_in` insertion-backlog diagnosis, synthetic B-lite net4 (seed 1001)

Evidence for a decision; **no frozen file was changed**. Everything below lives under
`results/blite/synth/diag_entry/` and was produced by copies made there.

* Network: `scenarios/kwuntong/blite/net4.net.xml` (baseline) and
  `diag_entry/variants/net4_D.net.xml` (variant D copy).
* Routes: `scenarios/kwuntong/blite/synth/proxy.rou.xml` and the `diag_entry/variants/`
  copies (`departLane="free"` / `"random"`).
* Signals: `scenarios/kwuntong/blite/synth/tls_webster_synth.add.xml` (Webster, unchanged).
* Environment: `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`, `CITYPULSE_NET=blite`,
  `CITYPULSE_BLITE_REV=4`, `CITYPULSE_REROUTE=0`, `--seed 1001`, `--end 7200`, incident-free,
  `--time-to-teleport -1`. Evaluation identical to `results/blite/synth/run_g123.py`
  (G1 teleports/collisions; G2 `scheduled = pending + running + arrived`; G3
  pending ≤ 2 % and every 15-min slope of running and of each source backlog ≤ +0.05 veh/s
  after a 900 s warm-up). Variant A reuses the existing frozen run and was **not** rerun.

Demand context (route file): 8,887 vehicles, of which 5,668 depart at `tko_in`
(4,254 bypass via `ktb_w1` = 2,100 veh/h, 1,414 arterial via `tko_a1` = 700 veh/h) and
3,219 depart on the four cross-street stubs (≈1,600 veh/h). `tko_in` is 2 lanes and, in net4,
lane 0 reaches only `tko_1` lane 0 (which can never reach the bypass), while lane 1 reaches
`tko_1` lanes 1 and 2 (both of which reach `tko_vms` lanes 1–2 and then `ktb_w1`).

## 1. Variant results

Built inputs (SHA-256):

| File | SHA-256 |
|---|---|
| `results/blite/synth/diag_entry/variants/proxy_free.rou.xml` | `16c5b29ab0c1c74b26917069625aca9c7699f188f923f3f657794d908e1d191f` |
| `results/blite/synth/diag_entry/variants/proxy_random.rou.xml` | `548444eaa4b62e750f790da271fa356f9e6aac01d2e7f29494a2264c755c3281` |
| `results/blite/synth/diag_entry/variants/extra.con.xml` | `de8ba76fefcba87f9edf3b0d42883831c33871a559bab587ff71c27a09257846` |
| `results/blite/synth/diag_entry/variants/net4_D.net.xml` | `90863e7d0c4c278d2927138af53863d357c2859afd38d60ef38db6d4d89cfc34` |

Variant D was produced with netconvert from net4 plus a connection patch; the only change to
`tko_in -> tko_1` is the added `fromLane="0" toLane="1"` connection (net4 has `0->0`, `1->1`,
`1->2`; D has `0->0`, `0->1`, `1->1`, `1->2`). All real edge ids and lane ids are unchanged, and
the signalised junctions S1–S4 are untouched (only the internal junction-`j1` lanes were
renumbered by netconvert), so the Webster state strings stay valid.

| Variant | Change | Pending end | Scheduled | Running end | Arrived end | Scheduled−(P+R+A) | Teleports | Collisions | Pending share | G1 | G2 | G3 | Discharge at `out` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| A | baseline (`departLane="best"`, net4) | 2,711 | 8,887 | 183 | 5,993 | 0 | 0 | 0 | 30.51 % | PASS | PASS | **FAIL** | 1,402 veh/h |
| B | `departLane="free"` | 1,588 | 8,887 | 363 | 6,936 | 0 | 0 | 0 | 17.87 % | PASS | PASS | **FAIL** | 1,874 veh/h |
| C | `departLane="random"` | 1,602 | 8,887 | 369 | 6,916 | 0 | 0 | 0 | 18.03 % | PASS | PASS | **FAIL** | 1,864 veh/h |
| D | extra connection `tko_in_0 -> tko_1_1`, `departLane="best"` | 2,721 | 8,887 | 184 | 5,982 | 0 | 0 | 0 | 30.62 % | PASS | PASS | **FAIL** | 1,396 veh/h |

G1 passes everywhere (no teleports are possible by construction and no collisions were
reported). G2 passes everywhere on a consistent snapshot (§3). G3 fails everywhere: every
`tko_in` backlog window is above +0.05 veh/s, and all pending vehicles belong to `tko_in`
(the four `x*_in` backlogs are 0 for the whole run in every variant).

### `tko_in` backlog slope per complete 15-min window (veh/s, limit +0.05)

| Window (s) | A | B | C | D |
|---|---:|---:|---:|---:|
| 900–1800 | +0.34973 | +0.10426 | +0.09542 | +0.35069 |
| 1800–2700 | +0.33848 | +0.12610 | +0.15953 | +0.33973 |
| 2700–3600 | +0.37157 | +0.26912 | +0.23468 | +0.37488 |
| 3600–4500 | +0.34926 | +0.27047 | +0.24517 | +0.35272 |
| 4500–5400 | +0.41324 | +0.27691 | +0.26792 | +0.41377 |
| 5400–6300 | +0.37208 | +0.29735 | +0.29446 | +0.37407 |
| 6300–7200 | +0.41395 | +0.29868 | +0.29777 | +0.41355 |

Every value fails the +0.05 limit. A and D are indistinguishable (both oscillate in the
+0.34…+0.41 band); B and C reduce the slope to ≈+0.10 at the start but it climbs back to
≈+0.30 — the backlog is still growing at the horizon, it is only smaller.

### Per-lane flow, last hour (3,600–7,200 s), E1 `nVehContrib` in veh/h

| Variant | `tko_in_0` | `tko_in_1` | `tko_in` Σ | `tko_vms_0` | `tko_vms_1` | `tko_vms_2` | `tko_vms` Σ | `ktb_w1_0` | `ktb_w1_1` | `ktb_w1` Σ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 432 | 1,044 | 1,476 | n/a | n/a | n/a | (1,477 edge) | 455 | 523 | 978 |
| B | 783 | 1,081 | 1,864 | 313 | 371 | 1,150 | 1,834 | 544 | 836 | 1,380 |
| C | 786 | 1,079 | 1,865 | 262 | 320 | 1,282 | 1,864 | 544 | 888 | 1,432 |
| D | 267 | 1,204 | 1,471 | 19 | 468 | 981 | 1,468 | 431 | 544 | 975 |

Notes. (a) A's numbers come from the frozen `g123_seed1001/e1.xml`, whose loops sit at
`tko_in` pos 41.9 and `tko_1`/`ktb_w1` pos 77.6 / 341.6; B/C/D use the diag loops at
`tko_in` 150 / `tko_1` 130 / `tko_vms` 180 / `ktb_w1` 300, so A's split is measured a little
further upstream but the same lanes. (b) **A's `tko_vms` per-lane flow is not recoverable from
the frozen run**: `detectors4.add.xml` has no `tko_vms` loop, and I did not rerun A. Its
`tko_vms` edge throughput is 1,477 veh/h (all `tko_1` traffic continues onto `tko_vms`),
splitting downstream into `ktb_w1` (978) and `tko_a1` (495, from the frozen
`AID07107_0/1/2` = 18/164/313). The `tko_1` lane split (150/678/649) is *not* a valid proxy
for `tko_vms`: in B/C/D, lane changes on the 3-lane `tko_1` clearly rebalance lanes
(e.g. B `tko_1` 673/338/824 vs `tko_vms` 313/371/1,150). (c) The arterial discharge is the
residual `tko_vms` Σ − `ktb_w1` Σ: A 499 (the frozen `tko_a1` loops measure 495), B 454,
C 432, D 493 veh/h.

The `tko_in` entry throughput last hour is 1,476 / 1,864 / 1,865 / 1,471 veh/h against the
assumed 2,800 veh/h — a shortfall of ≈1,324 / 936 / 935 / 1,329 veh/h, i.e. 0.37 / 0.26 /
0.26 / 0.37 veh/s, matching the measured slopes at the horizon.

### Halting, last 30 min (1,800 steps), mean / max vehicles

| Variant | `tko_in` | `tko_1` | `tko_vms` | `ktb_w1` |
|---|---|---|---|---|
| A | 0.007 / 1 | 0 / 0 | 0.331 / 6 | 0 / 0 |
| B | 3.392 / 32 | 12.085 / 47 | 33.650 / 80 | 0 / 0 |
| C | 2.403 / 35 | 18.980 / 52 | 48.926 / 95 | 0 / 0 |
| D | 0.014 / 1 | 0 / 0 | 0.974 / 5 | 0 / 0 |

(`ktb_w1` never queues in any variant; A's `tko_1`/`ktb_w1` loops recorded no halting at all,
which is why they are absent from the frozen `halting_last30.json`.)

## 2. What the variants show

1. **The failure is entirely on the insertion side.** In A and D `tko_in` itself has ~0.01
   mean halting, `tko_1` has none and `ktb_w1` has none: the corridor downstream of the entry
   is free-flowing while 2,711 (A) / 2,721 (D) vehicles never enter the network at all. Only
   the `tko_in` source backs up; all four cross-street sources insert 100 % of their demand.
2. **`departLane` is first-order but not sufficient.** `free`/`random` use both entry lanes
   (`tko_in_0` 432 → 783/786 veh/h), which cuts the backlog by ≈41 % (2,711 → 1,588/1,602)
   and raises discharge ≈33 % (1,402 → 1,874/1,864 veh/h). But the weaving that this creates
   on `tko_1`/`tko_vms` shows up as new halting (mean 12/34 and 19/49, max 47/80 and 52/95)
   and the backlog still grows at +0.10…+0.30 veh/s. So the lane *choice* rule alone does not
   close the 2,800 veh/h gap.
3. **Fixing only the physical connection is ineffective.** With `departLane="best"` kept, the
   extra `tko_in_0 -> tko_1_1` connection leaves D identical to A (pending 2,721 vs 2,711,
   discharge 1,396 vs 1,402, slopes within noise) and even starves lane 0 further
   (432 → 267 veh/h): the added edge apparently makes lane 1 the best continuation for the
   arterial stream too, so `best` still funnels everything onto lane 1.
4. **Root cause (as configured).** The 2,800 veh/h `tko_in` demand — 75 % of it bypass — is
   offered to a single usable insertion lane in the baseline, and one lane delivers only
   ≈1,470 veh/h here, so the deficit (≈0.35 veh/s) accumulates without bound while the
   corridor stays empty. Neither re-labelling the departure lane nor adding the missing
   physical connection removes the constraint; only using both entry lanes (B/C) helps, and
   even then the entry/diverge pair saturates near ≈1,870 veh/h once the downstream weave
   loads up.

## 3. The G2 "−2" gap: a snapshot-epoch counting bug, not a conservation break

**The baseline as frozen is exact: 8,887 = 2,711 + 183 + 5,993, gap 0**
(`g123_seed1001/run.json`, `"conservation_gap": 0`, and `g123_report.md` §2).

The −2 is reproduced by mixing two read epochs in `run_g123.py`:

* `scheduled_end` (line 238) is `np.searchsorted(departures, END, side='left')`, i.e. departures
  strictly before 7,200 s → 8,887. This is also the loaded count; the largest `depart` in the
  file is 7,199.913, so "loaded vs scheduled" is **not** the cause.
* The last `history.csv` row is taken at `k = 7200` (line 185), **before** the extra flush step.
* `run_g123.py` then performs one extra `simulationStep()` (line 204) and reads `arrived`,
  `end_running` and `end_pending` **after** it (lines 205–209).

Frozen seed-1001 evidence:

```
history.csv, t=7200 row : running=185  pending=2711  arrived=5990
run.json (post-flush)   : running=183  pending=2711  arrived=5993
```

* consistent (post-flush) snapshot: 2,711 + 183 + 5,993 = **8,887** → gap 0.
* mixed epoch (`pending` post-flush + `running` from the 7,200 s row + `arrived` post-flush):
  2,711 + 185 + 5,993 = **8,889** → gap **−2**.

Mechanism: over the single flush second `arrived` rises by 3 (5,990 → 5,993) and `running`
falls by 2 (185 → 183), so the **net insertion during the flush step is Δrunning + Δarrived
= −2 + 3 = 1**. The mixed-epoch sum uses `running` from before that step and `arrived` from
after it, so it counts the flush-step arrivals but not the offsetting flush-step insertion:
it is larger than the consistent sum by exactly `running_pre − running_end = Δarrived −
net insertion = 3 − 1 = 2`. Hence gap = −2. (Equivalently: the flush-second arrivals are
counted as running as well, while the flush-second insertion is not; net overcount
3 − 1 = 2.)

The same artifact is visible in the new runs, which recorded both epochs:

| Variant | `running` at t=7,200 (history) | `running_end` (post-flush) | flush arrivals | mixed-epoch gap |
|---|---:|---:|---:|---:|
| A (frozen) | 185 | 183 | 3 | −2 |
| B | 364 | 363 | 1 | −1 |
| C | 371 | 369 | 3 | −2 |
| D | 184 | 184 | 1 | 0 |

So: **counting bug (inconsistent snapshot epoch / double count), not a real conservation
break.** On any single epoch every variant conserves exactly
(A 6,176 + 2,711, B 7,299 + 1,588, C 7,285 + 1,602, D 6,166 + 2,721 — all 8,887), and the
frozen baseline's own G2 terms are exact. The fix would be to snapshot running/pending/arrived
at one epoch (either all at `k = END` or all after the flush step), not to change the network
or the demand.

## 4. Commands

```powershell
cd D:\CityCom-astra
$env:PYTHONDONTWRITEBYTECODE='1'; $env:OPENBLAS_NUM_THREADS='1'
$env:CITYPULSE_NET='blite'; $env:CITYPULSE_BLITE_REV='4'; $env:CITYPULSE_REROUTE='0'

# build B/C route copies + the D net (netconvert connection patch)
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry\run_diag.py --build

# three runs in parallel (separate pwsh processes), seed 1001, 7200 s
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry\run_diag.py --variant B *> results\blite\synth\diag_entry\logs\B.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry\run_diag.py --variant C *> results\blite\synth\diag_entry\logs\C.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry\run_diag.py --variant D *> results\blite\synth\diag_entry\logs\D.txt

# assemble the table / per-lane flows
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry\analyze.py
```

The netconvert step invoked by `--build` is:

```powershell
D:\CityCom\.venv\Lib\site-packages\sumo\bin\netconvert.exe `
  --sumo-net-file scenarios\kwuntong\blite\net4.net.xml `
  --connection-files results\blite\synth\diag_entry\variants\extra.con.xml `
  --output-file results\blite\synth\diag_entry\variants\net4_D.net.xml --no-warnings true
```

Variant A was not rerun; its numbers are read from
`results/blite/synth/g123_seed1001/{run.json,history.csv,halting_last30.json,e1.xml}`.
Per-variant outputs are `results/blite/synth/diag_entry/{B,C,D}/{run.json,history.csv,
pending_by_source.csv,e1diag.xml,diag_dets.add.xml,collisions.xml,sumo.log}` and the
console logs are under `results/blite/synth/diag_entry/logs/`.

REPORT DONE
