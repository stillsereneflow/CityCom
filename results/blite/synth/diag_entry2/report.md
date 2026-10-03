MODEL: deepseek-v4.1-flash
# Entry capacity of `tko_in` under insertion settings, synthetic B-lite net4 (seed 1001)

Evidence for a decision; **no frozen file was changed**. Everything below lives under
`results/blite/synth/diag_entry2/` and was produced by copies made there
(`run_diag2.py`, `analyze2.py` are copies of the `diag_entry/` scripts, extended).

* Network: `scenarios/kwuntong/blite/net4.net.xml` (unchanged, no netconvert step this time).
* Routes: `scenarios/kwuntong/blite/synth/proxy.rou.xml` (baseline) and the
  `diag_entry2/variants/` copies built here.
* Signals: `scenarios/kwuntong/blite/synth/tls_webster_synth.add.xml` (Webster, unchanged).
* Environment: `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`, `CITYPULSE_NET=blite`,
  `CITYPULSE_BLITE_REV=4`, `CITYPULSE_REROUTE=0`, `--seed 1001`, `--end 7200`,
  `--step-length 1`, `--time-to-teleport -1`, incident-free, `--collision.action warn`.
  G1-G3 evaluated exactly as in `results/blite/synth/run_g123.py`.
* Five runs, one pass, 7,200 s each, 0-900 s warm-up excluded from every rate. Wall time
  16-22 s per run, five in parallel.

Built inputs (SHA-256):

| File | SHA-256 |
|---|---|
| `results/blite/synth/diag_entry2/variants/proxy_E.rou.xml` | `5977a749c2259af408c4bf264d42af17fb5c42f8e598d6343c87d9dfd4419e73` |
| `results/blite/synth/diag_entry2/variants/proxy_F.rou.xml` | `7a5187a63244860d18957c9bac6934c332ef6597650ab7e45ae9b391de2bf564` |
| `results/blite/synth/diag_entry2/variants/proxy_G.rou.xml` | `82ab3042dfb2ada8f4dc7891f6712ac8465908594e647e0ff90a2b1a9899e2a9` |
| `results/blite/synth/diag_entry2/variants/ramp_H.rou.xml` | `36fba334c1abafa4b6950cf1284a5239cc2cd3b419ff4b50c4632b2e19f28f06` |
| `results/blite/synth/diag_entry2/variants/ramp_I.rou.xml` | `db5999296f50a48ea7c36242b5d32b883b719c1652401408e366fdcb0342ccaf` |

E/F/G are the baseline route file with the two departure attributes rewritten (8,887
vehicles each). H/I are the baseline `tko_in` stream rescaled to the linear ramp
lambda(t) = 1,000 + 3,000·t/7,200 veh/h by inverse-CDF sampling of a non-homogeneous Poisson
process conditioned on the exact vehicle count (5,000 instead of 5,668, seed 1001, vehicle
classes kept in baseline depart order), so the 75/25 bypass/arterial split is preserved in
every slice (72.9-77.5 % bypass per 900 s) and the four cross-street stubs keep their exact
baseline departures (782/818/792/827 vehicles, 400 veh/h each); H/I have 8,219 vehicles and
a 2.2-7,199.2 s departure window.

## 0. Instrument note: the per-lane flows here come from the E1 interval file

`diag_entry/run_diag.py` accumulated `inductionloop.getLastStepVehicleNumber(det)` once per
simulation step and reported that as per-lane flow. That call is **not** a per-step crossing
count: SUMO reports a vehicle on the loop on two consecutive steps (once on entering, once on
leaving the loop area). Probe `probe_det.py` (1,200 s of variant E, loop at `tko_in_0`
pos 150 m): per-step sum 378 vs the detector's own `nVehContrib` 272; micro-probe with a
single vehicle: `n=1` at t=19 and t=20 for one crossing. So the accumulated values roughly
double-count, and `diag_entry/{B,C,D}/run.json → per_lane.last_hour` is inflated (e.g. B
`tko_in_0` 1,255 accumulated vs 783 in `e1diag.xml`). The **published** `diag_entry/report.md`
§1 table used the `e1diag.xml` values and is unaffected; this report uses the E1 file
everywhere (detector period 300 s) and never the per-step call.

Cross-check of the instrument (E1 `tko_in` flow over intervals ≤ 7,200 s vs SUMO's own
departed list, per source):

| Variant | inserted `tko_in` | E1 `tko_in` | E1 last hour | inserted last hour |
|---|---:|---:|---:|---:|
| E | 3,915 | 3,910 | 1,840 | 1,839 |
| F | 4,043 | 4,028 | 1,899 | 1,882 |
| G | 3,467 | 3,463 | 1,744 | 1,745 |
| H | 3,637 | 3,626 | 1,884 | 1,887 |
| I | 3,652 | 3,641 | 1,918 | 1,923 |

The two instruments agree to ≤ 0.4 %, so the E/F/G flows below are directly comparable with
`diag_entry/report.md` §1 (same loop positions: `tko_in` 150 m, `tko_1` 130 m, `tko_vms`
180 m, `ktb_w1` 300 m).

## 1. Variants E/F/G (table as in `diag_entry/report.md` §1)

| Variant | Settings | Pending end | Scheduled | Running end | Arrived end | Scheduled−(P+R+A) | Teleports | Collisions | Pending share | G1 | G2 | G3 | Discharge at `out` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| A | reference: `best`/`max`, frozen `g123_seed1001` | 2,711 | 8,887 | 183 | 5,993 | 0 | 0 | 0 | 30.51 % | PASS | PASS | **FAIL** | 1,402 veh/h |
| B | reference: `free`/`max`, `diag_entry/B` | 1,588 | 8,887 | 363 | 6,936 | 0 | 0 | 0 | 17.87 % | PASS | PASS | **FAIL** | 1,874 veh/h |
| **E** | `departLane="free"`, `departSpeed="desired"` | 1,753 | 8,887 | 356 | 6,778 | 0 | 0 | 0 | 19.73 % | PASS | PASS | **FAIL** | 1,795 veh/h |
| **F** | `departLane="free"`, `departSpeed="last"` | 1,623 | 8,887 | 404 | 6,860 | 0 | 0 | 0 | 18.26 % | PASS | PASS | **FAIL** | 1,838 veh/h |
| **G** | `departLane="best"`, `departSpeed="desired"` | 2,199 | 8,887 | 207 | 6,481 | 0 | 0 | 0 | 24.74 % | PASS | PASS | **FAIL** | 1,648 veh/h |

G1/G2 pass everywhere; G3 fails everywhere (pending > 2 %, every `tko_in` backlog window above
+0.05 veh/s; the four stub backlogs are 0 for the whole run in every variant).

**`tko_in` backlog slope per complete 15-min window (veh/s, limit +0.05)** — every value fails:

| Window (s) | E | F | G | (B, reference) |
|---|---:|---:|---:|---:|
| 900-1800 | +0.18250 | +0.18228 | +0.27583 | +0.10426 |
| 1800-2700 | +0.25358 | +0.21223 | +0.26637 | +0.12610 |
| 2700-3600 | +0.24804 | +0.27267 | +0.31267 | +0.26912 |
| 3600-4500 | +0.30199 | +0.25679 | +0.27275 | +0.27047 |
| 4500-5400 | +0.28583 | +0.31998 | +0.33191 | +0.27691 |
| 5400-6300 | +0.23686 | +0.23961 | +0.29907 | +0.29735 |
| 6300-7200 | +0.28760 | +0.23064 | +0.34049 | +0.29868 |

**Per-lane E1 flow, last hour 3,600-7,200 s (veh/h):**

| Variant | `tko_in_0` | `tko_in_1` | `tko_in` Σ | `tko_1_0` | `tko_1_1` | `tko_1_2` | `tko_vms_0` | `tko_vms_1` | `tko_vms_2` | `tko_vms` Σ | `ktb_w1_0` | `ktb_w1_1` | `ktb_w1` Σ | `tko_a1` Σ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E | 575 | 1,265 | **1,840** | 589 | 394 | 894 | 341 | 391 | 1,146 | 1,878 | 532 | 873 | 1,405 | 477 |
| F | 1,064 | 835 | **1,899** | 639 | 383 | 921 | 306 | 381 | 1,218 | 1,905 | 568 | 899 | 1,467 | 452 |
| G | 331 | 1,413 | **1,744** | 68 | 730 | 946 | 22 | 566 | 1,158 | 1,746 | 518 | 694 | 1,212 | 534 |
| B (ref) | 783 | 1,081 | 1,864 | 673 | 338 | 824 | 313 | 371 | 1,150 | 1,834 | 544 | 836 | 1,380 | 454 |

`tko_a1` per-lane split (lanes 0/1 = minor links at D, lane 2 = major): E 53/177/247,
F 41/179/232, G 17/165/352, B 18/164/313 (B from the frozen E1 file).

**Halting, last 30 min (1,800 steps), mean / max vehicles:**

| Variant | `tko_in` | `tko_1` | `tko_vms` | `ktb_w1` |
|---|---|---|---|---|
| E | 0.043 / 6 | 7.949 / 53 | 25.803 / 69 | 0 / 0 |
| F | 12.390 / 76 | 17.922 / 77 | 25.515 / 69 | 0 / 0 |
| G | 0.000 / 0 | 0.000 / 0 | 2.304 / 11 | 0 / 0 |
| B (ref) | 3.392 / 32 | 12.085 / 47 | 33.650 / 80 | 0 / 0 |
| A (ref) | 0.007 / 1 | 0 / 0 | 0.331 / 6 | 0 / 0 |

`ktb_w1` never queues in any variant; in E and G the entry itself does not queue either
(0.043 and 0.000 mean halting) — the whole failure is downstream of the entry, in the
`tko_1`/`tko_vms` weave, exactly as in `diag_entry` §2.

## 2. H/I entry capacity (demand ramp 1,000 → 4,000 veh/h)

5-min `tko_in` throughput (E1 loops at 150 m; warm-up 0-900 s excluded). "inserted" is SUMO's
departed list for the `tko_in` source; "demand" is the ramp rate at the bin midpoint:

| Bin (s) | demand | H E1 | H inserted | I E1 | I inserted |
|---|---:|---:|---:|---:|---:|
| 900-1200 | 1,438 | 1,440 | 1,440 | 1,440 | 1,440 |
| 1200-1500 | 1,562 | 1,560 | 1,548 | 1,560 | 1,548 |
| 1500-1800 | 1,688 | 1,692 | 1,692 | 1,692 | 1,692 |
| 1800-2100 | 1,812 | 1,788 | 1,812 | 1,788 | 1,812 |
| 2100-2400 | 1,938 | 1,944 | 1,944 | 1,944 | 1,944 |
| 2400-2700 | 2,062 | 2,052 | 2,052 | 2,052 | 2,052 |
| 2700-3000 | 2,188 | 2,184 | 2,196 | 2,184 | 2,196 |
| 3000-3300 | 2,312 | 2,316 | 2,316 | 2,304 | 2,304 |
| 3300-3600 | 2,438 | 2,412 | 2,436 | 2,196 | 2,196 |
| 3600-3900 | 2,562 | **2,544** | **2,556** | 2,088 | 2,136 |
| 3900-4200 | 2,688 | 1,860 | 1,980 | 2,124 | 2,064 |
| 4200-4500 | 2,812 | 2,172 | 2,100 | 1,752 | 1,776 |
| 4500-4800 | 2,938 | 1,320 | 1,656 | 2,148 | 2,160 |
| 4800-5100 | 3,062 | 1,908 | 1,536 | 1,800 | 1,800 |
| 5100-5400 | 3,188 | 1,944 | 2,100 | 1,740 | 1,728 |
| 5400-5700 | 3,312 | 1,584 | 1,704 | 1,980 | 2,004 |
| 5700-6000 | 3,438 | 1,944 | 1,800 | 1,728 | 1,740 |
| 6000-6300 | 3,562 | 2,004 | 1,872 | 2,016 | 1,956 |
| 6300-6600 | 3,688 | 1,344 | 1,536 | 1,944 | 1,980 |
| 6600-6900 | 3,812 | 1,788 | 1,692 | 2,028 | 2,040 |
| 6900-7200 | 3,938 | 2,196 | 2,112 | 1,668 | 1,692 |

**Entry capacity** (maximum 5-min `tko_in` throughput sustained over 3 consecutive bins):

| Variant | Settings | Plateau window | Capacity (E1) | Capacity (insertions) | Demand at plateau |
|---|---|---|---:|---:|---:|
| H | ramp, `free`/`max` | 3,000-3,900 s | **2,424 veh/h** (606 veh) | 2,436 veh/h | 2,312-2,562 veh/h |
| I | ramp, `free`/`desired` | 2,700-3,600 s | **2,228 veh/h** (557 veh) | 2,232 veh/h | 2,188-2,438 veh/h |

**Demand level at which the backlog first grows past 50 vehicles** (first minute with
`pending_tko_in` > 50):

| Variant | first > 20 veh | first > 50 veh | demand at onset | 5-min throughput at onset | mean 4,500-7,200 s | max pending |
|---|---|---|---|---|---:|---:|
| H | t = 4,140 s (36 veh, 2,725 veh/h) | **t = 4,200 s (59 veh, 2,750 veh/h)** | 2,750 veh/h | 1,860 veh/h | 1,781 veh/h | 1,362 |
| I | t = 3,600 s (21 veh, 2,500 veh/h) | **t = 3,900 s (56 veh, 2,625 veh/h)** | 2,625 veh/h | 2,088 veh/h | 1,895 veh/h | 1,347 |

Reading: both ramps track the offer exactly up to ≈2,550 veh/h (H) / ≈2,400 veh/h (I), then
break down; the backlog crosses 50 vehicles one bin later, at an offered 2,750 / 2,625 veh/h.
After breakdown the entry settles at 1,781 (H) / 1,895 (I) veh/h mean over 4,500-7,200 s —
the same ≈1,800-1,900 veh/h the constant-demand runs E/F/B reach. So the entry capacity is
**state-dependent**: ≈2,400 veh/h while the downstream weave is still unloaded (H, bin
3,000-3,900), and ≈1,800-1,900 veh/h once the `tko_1`/`tko_vms` weave has loaded up. Both
figures are far below the 2,800 veh/h demand, which is why the backlog grows without bound.

## 3. Where vehicles slow in the weave case (`tko_vms` / `tko_1`)

Lane changes counted on the edge (vehicle changes lane while on that edge):

| Variant | `tko_1` | `tko_vms` |
|---|---:|---:|
| E (`free`/`desired`) | 2,144 | 2,304 |
| F (`free`/`last`) | 2,414 | 2,275 |
| G (`best`/`desired`) | 3,018 | 1,288 |
| H (ramp `free`/`max`) | 2,406 | 1,945 |
| I (ramp `free`/`desired`) | 2,312 | 1,971 |

That is ≈0.55-0.6 lane changes per vehicle through `tko_vms` in E/F — present, but modest.

Per-lane mean speed (m/s), vehicle-weighted over 5-min bins; run / last hour:

| Variant | `tko_vms_0` | `tko_vms_1` | `tko_vms_2` |
|---|---|---|---|
| E | 2.08 / 1.95 | 1.63 / 1.13 | 5.94 / 4.91 |
| F | 2.06 / 1.70 | 1.58 / 1.11 | 5.67 / 5.37 |
| G | 5.84 / 3.85 | 12.06 / 10.42 | 16.58 / 16.30 |

**One minute-resolution look at `tko_vms` in variant E** (`speed_per_min.csv`, 1-min samples;
free-flow speed on this edge is 19.44 m/s):

| t (s) | `tko_vms_0` | `tko_vms_1` | `tko_vms_2` | (`tko_1_0` / `tko_1_1` / `tko_1_2`) |
|---:|---:|---:|---:|---|
| 5,460 | 4.34 | 1.62 | 11.12 | 11.34 / 2.41 / 5.64 |
| 5,520 | 0.29 | 0.48 | 5.37 | 17.02 / 2.85 / 13.53 |
| 5,580 | 1.35 | 1.74 | 2.00 | 19.44 / 2.13 / 1.15 |
| 5,640 | 2.67 | 3.29 | 7.61 | 15.97 / 1.74 / 2.72 |
| 5,700 | 4.21 | 1.25 | 2.58 | 16.20 / 4.33 / 6.27 |
| 5,760 | 1.66 | 0.97 | 2.44 | 16.39 / 1.64 / 3.02 |
| 5,820 | 5.01 | 3.72 | 8.16 | 12.75 / 1.17 / 1.43 |
| 5,880 | 2.67 | 0.90 | 3.88 | 15.71 / 3.82 / 7.56 |
| 5,940 | 0.51 | 0.57 | 3.14 | 15.84 / 0.77 / 3.52 |
| 6,000 | 7.39 | 3.46 | 5.24 | 16.07 / 1.46 / 1.61 |

Lanes 0 and 1 on `tko_vms` are at walking pace (0.3-5 m/s, mostly < 3 m/s) while lane 2 keeps
2-13 m/s; on `tko_1` the queue sits on lanes 1-2 while lane 0 runs free.

**Who occupies the slow lanes** (`probe_weave.py`: variant E re-run with the standing vehicles
on each lane classified by destination stream — bypass = route via `ktb_w1`, arterial = route
via `tko_a1`; last hour, 60 one-minute samples, mean vehicles):

| Lane | vehicles | bypass | arterial | halting | halting bypass | halting arterial |
|---|---:|---:|---:|---:|---:|---:|
| `tko_1_0` | 4.9 | 2.3 | 2.6 | 1.5 | 0.8 | 0.7 |
| `tko_1_1` | 25.8 | 25.1 | 0.7 | 7.9 | 7.6 | 0.3 |
| `tko_1_2` | 23.0 | 20.5 | 2.5 | 1.3 | 1.1 | 0.1 |
| `tko_vms_0` | 18.0 | 2.5 | 15.5 | 11.1 | 1.4 | 9.7 |
| `tko_vms_1` | 34.9 | 31.8 | 3.1 | 18.0 | 16.1 | 1.9 |
| `tko_vms_2` | 26.7 | 22.4 | 4.3 | 1.1 | 1.0 | 0.1 |

`tko_vms_0` is an arterial lane (86 % arterial) and it is standing still: 11.1 halted vehicles
on average, 87 % of them arterial — that is the queue for the **minor** right-turn
`tko_vms_0 → tko_a1_0` (`state="m"` at priority junction D), which discharges only 53 veh/h.
`tko_vms_1` is a bypass lane (91 % bypass) that is also standing (18.0 halted, 89 % bypass)
because it carries the second minor right-turn `tko_vms_1 → tko_a1_1` (177 veh/h) at its head;
the two queues move together (correlation of the per-minute halting counts over the last hour:
`tko_vms_0` vs `tko_vms_1` = **+0.58**, vs `tko_vms_2` = −0.13). `tko_vms_2` — the only lane
whose movements are both **major** (`→ ktb_w1_1` and `→ tko_a1_2`, both `state="M"`) — keeps
flowing (1.1 halted).

Junction D, last hour (veh/h): minor `tko_a1_0` 53 + minor `tko_a1_1` 177 = 230 minor vs 247
major (`tko_a1_2`), with `ktb_w1_0` 532 and `ktb_w1_1` 873 major through movements.

**Where they slow:** on `tko_vms` lanes 0 and 1 approaching junction D, not on `tko_1`
(lane 0 there is free) and not on the bypass exit (`ktb_w1` halting is 0 in every variant).
The mechanism is the **minor links**, not the lane changes: the arterial right turns
`tko_vms_0 → tko_a1_0` and `tko_vms_1 → tko_a1_1` are `state="m"` and must yield to the
`ktb_w1` major stream, so they queue in the two lanes that also have to carry the 75 % bypass
stream; lane 2 (major links only) stays fast. Lane changes are the consequence of the free
insertion rule (bypass vehicles inserted on lane 0 must weave right) and they are not what
caps the corridor: variant G, where `best` avoids the minor links almost entirely (lane 0
22 veh/h, arterial flow 352 of 534 through the major `tko_a1_2`) and `tko_vms` halting drops to
2.3, still delivers only 1,744 veh/h at the entry.

## 4. Interpretation (5 lines)

1. **Departure speed does not fix the entry.** With `departLane="free"` the last-hour
   `tko_in` throughput is 1,840 veh/h for `desired` (E) and 1,899 for `last` (F) against 1,864
   for `max` (B, `diag_entry`) — a ±3 % spread — and with `best` it gets *worse*, not better
   (G 1,744 vs B 1,864; both fail G3 with a still-growing backlog), so `desired`/`last` buy
   nothing over the existing `max`.
2. **The ramp gives the entry capacity directly: ≈2,400 veh/h while the downstream weave is
   unloaded, ≈1,800-1,900 veh/h once it is loaded.** H sustains 2,424 veh/h over three
   consecutive 5-min bins (I 2,228), the backlog passes 50 vehicles at an offered 2,750 veh/h
   (I 2,625), and after breakdown the mean falls to 1,781 (I 1,895) veh/h — the same plateau as
   the constant-demand runs.
3. **2,800 veh/h is not deliverable by this entry/diverge pair at any departure setting**, and
   the deficit accumulates: E/F/G lose 1,753 / 1,623 / 2,199 vehicles over 2 h and every 15-min
   backlog slope is +0.18…+0.34 veh/s, i.e. the corridor is *not* congested while the entry is
   starved.
4. **The residual bottleneck is the weave at junction D, driven by the two `state="m"` minor
   right turns** `tko_vms → tko_a1`: `tko_vms_0` (86 % arterial) stands with 11.1 halted
   vehicles, `tko_vms_1` (91 % bypass) with 18.0 (correlation +0.58), while `tko_vms_2` — whose
   movements are both major — flows; removing the weave with `best` (G) empties lane 0 and
   removes the halting but leaves the entry at 1,744 veh/h, so the weave is a *consequence* of
   free insertion, not the only constraint.
5. **For the decision:** the measured per-lane entry rate is ≈920 veh/h (1,840/2) against the
   ≈1,400 veh/h per lane that reality supports on this corridor (and the ≈1,680 veh/h real
   5-min p95), so the model's `tko_in` entry is about a third short of the real corridor; either
   the assumed 2,800 veh/h must be revisited or the network's entry/diverge lane assignment
   (the `tko_in` lane-0 dead end into the arterial, and the minor right turns at D) must be
   fixed before any synthetic demand at that level can be used as evidence.

## 5. Commands

```powershell
cd D:\CityCom-astra
$env:PYTHONDONTWRITEBYTECODE='1'; $env:OPENBLAS_NUM_THREADS='1'
$env:CITYPULSE_NET='blite'; $env:CITYPULSE_BLITE_REV='4'; $env:CITYPULSE_REROUTE='0'

# build E/F/G route copies + the H/I ramp route files (writes only under diag_entry2/variants)
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --build

# five runs in parallel (separate pwsh processes), seed 1001, 7200 s
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --variant E *> results\blite\synth\diag_entry2\logs\E.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --variant F *> results\blite\synth\diag_entry2\logs\F.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --variant G *> results\blite\synth\diag_entry2\logs\G.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --variant H *> results\blite\synth\diag_entry2\logs\H.txt
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\run_diag2.py --variant I *> results\blite\synth\diag_entry2\logs\I.txt

# tables / capacity / weave read-out
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\analyze2.py *> results\blite\synth\diag_entry2\logs\analyze.txt

# E1-semantics probe and the weave-composition probe (diagnostics, one extra E run)
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\probe_det.py
D:\CityCom\.venv\Scripts\python.exe results\blite\synth\diag_entry2\probe_weave.py
```

Per-variant outputs: `results/blite/synth/diag_entry2/{E,F,G,H,I}/{run.json,history.csv,
pending_by_source.csv,e1diag.xml,bins300.csv,insertions300.csv,speed_per_min.csv,
halt_per_min.csv,speed_bins300.csv,diag_dets.add.xml,collisions.xml,sumo.log}`; console logs
under `results/blite/synth/diag_entry2/logs/`. Variants A/B/C were not rerun; their numbers are
read from `results/blite/synth/g123_seed1001/` and `results/blite/synth/diag_entry/{B,C}/`.
Nothing was committed; no frozen file was edited.

REPORT DONE
