# Step 1 (network capacity): progress, paused 2026-10-02

Goal: the Proxy carries the observed 2026-09-29 08–09h HK demand at scale 1.0. Acceptance: entry backlog ≤ 2% of loaded vehicles after 3,600 s, no growth in running vehicles over the last 15 min, GEH < 5 on ≥ 80% of counted edges in simulation, teleporting disabled.

**Status: FAILED so far. Paused** until GPT-6 Astra's quota resets (2026-10-04 12:28) for a joint review before continuing.

## Measurements (`citypulse.experiments.net_diag`, raw JSON in `results/net_diag_<tag>.json`)

| Tag | Network / demand | Backlog % of loaded | Running at end | GEH < 5 share |
|---|---|---:|---:|---:|
| s100 | trunk corridor (D1–D4 network), 1.0× | 33.6 (7,705 / 22,959) | 3,435 | 0.17* |
| s100_patch1 | + 1-hop side-street stubs + TD lane counts on detector edges, 1.0× | 39.1 | 5,092 | 0.10* |
| s80 / s60 / s40 | same, routes subsampled to 0.8 / 0.6 / 0.4 | 30.1 / 18.2 / 8.1 | 4,079 / 3,023 / 1,763 | — |
| s100_imp30 | + `--time-to-impatience 30` | 39.1 | 4,782 | 0.15* |
| w100b | + 6 OSM-grounded signals restored + Webster timings (10 of 15 signals; 3 joined clusters skipped by the SUMO tool) | 38.2 | 4,583 (still +0.64 veh/s) | **0.02** |
| g100 | + same-road lane gap-fill between TD-verified detector edges (25 edges) | 38.5 | 4,526 (+0.72 veh/s) | 0.03 |

\* Measured with the old diagnostic, which had three bugs Astra found: arrivals counted only in the last step, detector counts summed every step (over-counting slow vehicles), GEH target scaled twice. Rows w100b and g100 use the corrected diagnostic and are the reliable ones.

## What was changed (`citypulse/network/patch_network.py`, committed)

1. Kept edges = motorway/trunk + named corridor roads + 1-hop side-street stubs, so side-street traffic enters through a junction instead of spawning mid-arterial.
2. Lane counts raised to the TD detector's lane count where TD reports more lanes. 9 detector edges had the wrong count; worst cases: Tseung Kwan O Road 1 → 3 and Kwun Tong Road eastbound 1 → 3. Propagated along same-name chains and gap-filled between same-road detector pairs (33 edges patched in total).
3. Junctions with an OSM `traffic_signals` node within 30 m set to traffic_light (9 → 15 signals). Webster timings via `tools/tlsCycleAdaptation.py` as program "0".

## What the measurements say

- **The lane, signal and stub fixes did not reduce the backlog.** It stays at about 38% at 1.0×, and is still 8% at 0.4×. So the cause is not one or two capacity bugs.
- **Largest queues at 1.0×** (`results/step1_jams_w100b.txt`):
  - Tseung Kwan O Road westbound at the Kai Tin Road split (103 halting vehicles).
  - A chain along Kwun Tong Road eastbound (83–99).
  - The Kai Fuk Road 3 → 2 lane drop (60).
  - Lei Yue Mun Road approaches.
- **Leading hypothesis, untested:** the demand construction. routeSampler fits only the 41 counted edges, using random fringe-to-fringe candidate routes averaging about 3.5 km. Unobserved edges, weaving sections and minor-road entries may be loaded far beyond reality. Also, some of the HK counts may be congested discharge flows rather than demand.

## Open questions for the consultation with Astra

1. Demand: restrict OD pairs to plausible boundary entries/exits, constrain turns (routeSampler turn files), or fit an OD matrix to counts with path constraints?
2. Do the observed peak counts include congestion? TD speeds at 08–09h could separate free-flow demand from discharge.
3. Is a narrower study area (KTB + Kai Fuk + KTR spine with bounded entries) more defensible than repairing the wider network junction by junction?
4. Should the acceptance criteria be scale 1.0 at the observed counts, or the observed flows *and speeds* (allowing realistic congestion where TD shows it)?

## State on disk

- **Current files:** `scenarios/kwuntong/net.net.xml` is the g100 network. `proxy.rou.xml` and `twin_cand.rou.xml` are scale 1.0 (the D1–D4 runs used 0.6). The D1–D4 results and figures were produced on the earlier network and are not regenerated.
- **Astra's worktree:** `D:/CityCom-astra` (branch `astra/step1`) holds its partial edit to `net_diag.py`, already adopted in main.
- **HK data:** the recorder is still running as the scheduled task. Weekday mornings 2026-09-21 to 2026-09-30 are backfilled (07–11h archive window).
