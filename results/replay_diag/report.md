MODEL: deepseek-v4.1-flash (DeepSeek Harness)

# Matched-observation replay diagnosis of event inference

Binding spec: `docs/oct10-replay-diagnosis-plan.md` (revision 2, committed at `1774408`). Offline diagnostic only: nothing here is tuned and the online method is unchanged. Truth-assisted variants are offline positive controls; no inferential statistics.

Working tree at report time: `a61e2bc Audit sensitivities (agy-flash; preregistered): baseline replay 65/65 exact; D300 (truth duration) flips BEE to -3.19 and degrades ranking/regret; D600, P456, P900, F100 within ~0.15 of baseline BEE. Recomputed by Claude from raw.`. The spec's preregistration commit is `1774408`; the branch head moved during this run because a parallel agent committed unrelated audit work. No preregistered choice was changed and nothing under `results/replay_diag/` depends on the later commit.

## 1. Gates

| Gate | Verdict | Evidence |
|---|---|---|
| R_P qualification (spec, blocking) | **PASS** | blocker placement exact at 755 m and 900 m; two identical runs bit-identical; the two replays differ (`qualify_rp.json`) |
| Exact reproduction of V0 (spec, blocking) | **PASS** | 13 logged INC evaluations; MAP identical, max |ΔlogL| = 0.000e+00 ≤ 1e-6 |
| NOI re-run stream identity (spec, caution b) | **PASS** | evt_noi_4101: identical (matched stream); evt_noi_4102: identical (matched stream); evt_noi_4103: identical (matched stream) |
| Default identity, before vs after (prompt) | **PASS** | 3 replays from `event_snapshot_4350.xml.gz`: replay-result sha256, vehicle digest, interval count and logL all identical |

Failures by reason: none.

### R_P qualification detail

Run `evt_inc_4101`, evaluation `inc_4101_t5010`, snapshot `event_snapshot_4350.xml.gz`, t_on = 4410 s, t_eval = 5010 s, hypothesis `inc_ktb_n1_k2_s1`.

| Replay | Requested pos (m) | Requested lanes | Recorded placement | Exact |
|---|---|---|---|---|
| rp_755 | 755.0 | [0, 1] | hyp_blocker_1: edge=ktb_n1 lane=1 pos=754.970 t_stopped=4414 (onset+4s), stopped_at_end=True, hyp_blocker_0: edge=ktb_n1 lane=0 pos=754.995 t_stopped=4428 (onset+18s), stopped_at_end=True | True |
| rp_900 | 900.0 | [0, 1] | hyp_blocker_1: edge=ktb_n1 lane=1 pos=899.970 t_stopped=4414 (onset+4s), stopped_at_end=True, hyp_blocker_0: edge=ktb_n1 lane=0 pos=900.000 t_stopped=4415 (onset+5s), stopped_at_end=True | True |

The blocker is recorded on the requested lane at the requested position, still stopped there at t_eval; the recorded stop time is the first step SUMO reports it stopped at that position and can lag the onset by the insertion delay (reported above).


Determinism (twice-repeated identical inputs): rp_755: digest_equal=True, intervals_equal=True, logL_equal=True; rp_900: digest_equal=True, intervals_equal=True, logL_equal=True.

The two replays differ: digest 755 m=3ec769e4ddc4… vs 900 m=c175c4bc99f2…, intervals differ=True, logL -36.483 vs -23.449.

### Default identity (prompt: one replay from a pilot-2 pinned snapshot, before vs after)

| Probe job | sha256 before | sha256 after | identical | logL before | logL after |
|---|---|---|---|---|---|
| asrun | 5ae84965b702cc72… | 5ae84965b702cc72… | True | -71.242849 | -71.242849 |
| collect_eq_on | 5ae84965b702cc72… | 5ae84965b702cc72… | True | -71.242849 | -71.242849 |
| noevent | ab780e8b246f7fab… | ab780e8b246f7fab… | True | - | - |

### Exact reproduction of V0

| Evaluation | t_on | t_eval | down-weights | MAP logged | MAP reproduced | max |ΔlogL| | |O| logged | |O| reproduced | PASS |
|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | 4410 | 5010 | {} | flt_AID02111_zero | flt_AID02111_zero | 0.000e+00 | [165] | 165 | True |
| inc_4101_t5040 | 4440 | 5040 | {"AID02111": 5.0} | dem_f1.15 | dem_f1.15 | 0.000e+00 | [135] | 135 | True |
| inc_4101_t5100 | 4440 | 5100 | {"AID02111": 5.0} | dem_f1.15 | dem_f1.15 | 0.000e+00 | [135] | 135 | True |
| inc_4101_t5160 | 4440 | 5160 | {"AID02111": 5.0} | flt_AID02109_noise | flt_AID02109_noise | 0.000e+00 | [174] | 174 | True |
| inc_4102_t4890 | 4290 | 4890 | {} | flt_AID02111_zero | flt_AID02111_zero | 0.000e+00 | [177] | 177 | True |
| inc_4102_t4920 | 4320 | 4920 | {"AID02111": 5.0} | dem_f1.15 | dem_f1.15 | 0.000e+00 | [141] | 141 | True |
| inc_4102_t4980 | 4320 | 4980 | {"AID02111": 5.0} | dem_f1.15 | dem_f1.15 | 0.000e+00 | [141] | 141 | True |
| inc_4102_t5040 | 4320 | 5040 | {"AID02111": 5.0} | flt_AID02109_noise | flt_AID02109_noise | 0.000e+00 | [177] | 177 | True |
| inc_4103_t4860 | 4260 | 4860 | {} | flt_AID02111_stuck | flt_AID02111_stuck | 0.000e+00 | [144] | 144 | True |
| inc_4103_t4890 | 4290 | 4890 | {"AID02111": 5.0} | flt_AID02111_stuck | flt_AID02111_stuck | 0.000e+00 | [177] | 177 | True |
| inc_4103_t4920 | 4320 | 4920 | {"AID02111": 5.0} | dem_f1.3 | dem_f1.3 | 0.000e+00 | [141] | 141 | True |
| inc_4103_t4980 | 4320 | 4980 | {"AID02111": 5.0} | dem_f1.3 | dem_f1.3 | 0.000e+00 | [141] | 141 | True |
| inc_4103_t5040 | 4320 | 5040 | {"AID02111": 5.0} | flt_AID02109_noise | flt_AID02109_noise | 0.000e+00 | [177] | 177 | True |

Every logL of all 20 hypotheses of every logged evaluation is within 1e-6 of the log; the logL difference table is in `reproduce_v0.json`.

## 2. NOI re-run

| Run | stored rows | re-run rows | twin_log identical | label |
|---|---|---|---|---|
| evt_noi_4101 | 3360 | 3360 | True | matched stream |
| evt_noi_4102 | 3360 | 3360 | True | matched stream |
| evt_noi_4103 | 3360 | 3360 | True | matched stream |

Extra Twin snapshots at 4,230 s and 4,350 s (spec); the synthetic episode starts from the 4,230 s snapshot, the 4,350 s one is recorded but not scored (one episode only). All three re-runs reproduce the stored stream row for row, so no NOI result carries the 'rerun control' label of caution (b); the synthetic episodes use the re-run's snapshots and the re-run's observations, which are the stored ones.

## 3. Per-evaluation tables by variant

### V0 — base

representation **R_E**, incident onset logged t_on, locations asrun, fault family True, 20 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | flt_AID02111_zero | fault | 0.027 | -1.252 | False | 0.263 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.004 | -4.623 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.004 | -4.623 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | flt_AID02109_noise | fault | 0.000 | -0.909 | False | -0.039 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_zero | fault | 0.025 | -0.982 | False | 0.198 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.016 | -2.752 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.016 | -2.752 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.000 | -0.835 | False | -0.071 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | flt_AID02111_stuck | fault | 0.024 | -2.737 | False | 0.081 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_stuck | fault | 0.059 | -1.248 | False | 0.070 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.3 | demand | 0.054 | -2.052 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.3 | demand | 0.054 | -2.052 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.227 | 0.593 | False | -0.104 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -10.065 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.000 | -11.776 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.000 | -12.856 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.003 | -5.137 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -7.642 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -9.917 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -7.371 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -10.609 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -11.594 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VP — representation diagnostic

representation **R_P**, incident onset logged t_on, locations asrun, fault family True, 20 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | flt_AID02111_zero | fault | 0.512 | 1.609 | False | 0.263 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.433 | -0.670 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.433 | -0.670 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | flt_AID02109_noise | fault | 0.094 | 5.161 | False | -0.039 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_zero | fault | 0.494 | 2.026 | False | 0.198 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.530 | 0.155 | False | 0.126 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.530 | 0.155 | False | 0.126 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.024 | 4.263 | False | -0.071 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | flt_AID02111_stuck | fault | 0.428 | -0.061 | False | 0.081 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_stuck | fault | 0.265 | 0.024 | False | 0.070 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.464 | 0.368 | False | 0.172 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.464 | 0.368 | False | 0.172 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.360 | 1.212 | False | -0.104 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.218 | -1.210 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.315 | -0.400 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.337 | 0.028 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.092 | -2.150 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.097 | -2.218 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.069 | -2.660 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.162 | -1.333 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.134 | -1.612 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.141 | -1.452 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VT — truth-assisted control (onset)

representation **R_E**, incident onset 4500 s, locations asrun, fault family True, 20 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | flt_AID02111_zero | fault | 0.080 | -0.126 | False | 0.263 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.006 | -4.272 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.006 | -4.272 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | flt_AID02109_noise | fault | 0.000 | -3.174 | False | -0.039 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_zero | fault | 0.143 | 0.463 | False | 0.198 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.045 | -1.785 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.045 | -1.785 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.004 | 2.996 | False | -0.071 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | flt_AID02111_stuck | fault | 0.354 | -0.205 | False | 0.081 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | flt_AID02111_stuck | fault | 0.246 | 0.116 | False | 0.070 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s1 | incident | 0.411 | 0.277 | False | 0.160 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s1 | incident | 0.411 | 0.277 | False | 0.160 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.764 | 2.372 | True | 0.213 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.003 | -5.334 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.001 | -6.223 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.000 | -7.248 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.015 | -3.540 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.001 | -6.190 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -8.452 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.008 | -4.608 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.001 | -6.926 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -8.067 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VPT — truth-assisted control

representation **R_P**, incident onset 4500 s, locations asrun, fault family True, 20 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.821 | 3.305 | True | 0.439 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.455 | -0.956 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.455 | -0.956 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.990 | 12.064 | True | 0.639 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_k2_s0.6 | incident | 0.888 | 4.153 | True | 0.380 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s0.6 | incident | 0.665 | 1.064 | False | 0.233 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s0.6 | incident | 0.665 | 1.064 | False | 0.233 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.981 | 12.354 | True | 0.593 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.548 | 0.119 | False | 0.161 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.833 | 2.370 | True | 0.354 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.851 | 2.042 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.851 | 2.042 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.996 | 7.491 | True | 0.543 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.295 | -1.036 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.334 | -0.505 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.390 | 0.129 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.161 | -1.612 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.125 | -2.076 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.073 | -2.610 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.209 | -1.519 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.158 | -1.737 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.158 | -1.622 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VPL — truth-assisted control (location)

representation **R_P**, incident onset logged t_on, locations asrun900, fault family True, 24 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.727 | 2.509 | True | 0.391 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.500 | -0.180 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.500 | -0.180 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.991 | 11.862 | True | 0.645 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.688 | 2.470 | True | 0.279 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.578 | -0.182 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.578 | -0.182 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | flt_AID02109_noise | fault | 0.056 | 4.905 | False | -0.071 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | flt_AID02111_stuck | fault | 0.478 | -0.397 | False | 0.081 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.548 | 0.515 | False | 0.191 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.633 | 0.031 | False | 0.172 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s0.6 | incident | 0.633 | 0.031 | False | 0.172 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.697 | 2.282 | False | 0.228 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.199 | -1.547 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.281 | -0.736 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.305 | -0.309 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.072 | -2.486 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.075 | -2.554 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.052 | -2.996 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.147 | -1.669 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.115 | -1.949 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.119 | -1.789 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VPTL — truth-assisted control

representation **R_P**, incident onset 4500 s, locations asrun900, fault family True, 24 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.876 | 2.998 | True | 0.442 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.510 | -0.377 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.510 | -0.377 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.987 | 11.727 | True | 0.639 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.917 | 3.998 | True | 0.394 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.727 | 1.050 | False | 0.271 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.727 | 1.050 | False | 0.271 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.973 | 12.017 | True | 0.593 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | flt_AID02111_stuck | fault | 0.618 | -0.136 | False | 0.081 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.829 | 2.034 | False | 0.354 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.862 | 1.705 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.862 | 1.705 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.995 | 7.154 | True | 0.543 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.258 | -1.373 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.293 | -0.841 | False | 0.053 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | flt_AID02109_stuck | fault | 0.343 | -0.207 | False | 0.087 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.132 | -1.948 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.097 | -2.412 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.055 | -2.946 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.217 | -1.855 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.150 | -2.074 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.143 | -1.959 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VNF — competition diagnostic

representation **R_E**, incident onset logged t_on, locations asrun, fault family False, 14 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | dem_f1.15 | demand | 0.183 | -1.252 | False | 0.000 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.008 | -4.623 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.008 | -4.623 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.280 | -0.909 | False | 0.000 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | dem_f1.15 | demand | 0.168 | -0.982 | False | 0.000 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.034 | -2.752 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.034 | -2.752 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | dem_f1.15 | demand | 0.276 | -0.835 | False | 0.000 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | dem_f1.3 | demand | 0.063 | -2.737 | False | 0.000 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | dem_f1.15 | demand | 0.136 | -1.248 | False | 0.000 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | dem_f1.3 | demand | 0.090 | -2.052 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | dem_f1.3 | demand | 0.090 | -2.052 | False | 0.000 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k1_s1 | incident | 0.582 | 0.593 | False | 0.098 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -10.065 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -11.776 | False | 0.000 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -12.856 | False | 0.000 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.004 | -5.137 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -7.642 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -9.917 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -7.371 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -10.609 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.000 | -11.594 | False | 0.000 | 249 | {"obs_invalid": 45} |

### VPTLNF — truth-assisted control

representation **R_P**, incident onset 4500 s, locations asrun900, fault family False, 18 hypotheses.

| Evaluation | arm | t_eval | snapshot | MAP | family | P(incident) | gap | would-adopt | EVR | |O| | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| inc_4101_t5010 | INC | 5010 | event_snapshot_4350.xml.gz | inc_ktb_n1_p900_k2_s1 | incident | 0.982 | 2.998 | True | 0.442 | 165 | {"obs_invalid": 45} |
| inc_4101_t5040 | INC | 5040 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.672 | -0.377 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | INC | 5100 | event_snapshot_4380.xml.gz | dem_f1.15 | demand | 0.672 | -0.377 | False | 0.000 | 135 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | INC | 5160 | event_snapshot_4380.xml.gz | inc_ktb_n1_k2_s1 | incident | 1.000 | 11.727 | True | 0.639 | 174 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.989 | 3.998 | True | 0.394 | 177 | {"obs_invalid": 33} |
| inc_4102_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.854 | 1.050 | False | 0.271 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_p900_k2_s0.6 | incident | 0.854 | 1.050 | False | 0.271 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 1.000 | 12.017 | True | 0.593 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | INC | 4860 | event_snapshot_4200.xml.gz | dem_f1.3 | demand | 0.812 | -0.136 | False | 0.000 | 144 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | INC | 4890 | event_snapshot_4230.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.924 | 2.034 | False | 0.354 | 177 | {"obs_invalid": 33} |
| inc_4103_t4920 | INC | 4920 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.915 | 1.705 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | INC | 4980 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.915 | 1.705 | False | 0.396 | 141 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | INC | 5040 | event_snapshot_4260.xml.gz | inc_ktb_n1_k2_s1 | incident | 0.999 | 7.154 | True | 0.543 | 177 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.344 | -1.373 | False | 0.000 | 162 | {"obs_invalid": 48} |
| noi_4101_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.460 | -0.841 | False | 0.000 | 204 | {"obs_invalid": 48} |
| noi_4101_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.566 | -0.207 | False | 0.000 | 234 | {"obs_invalid": 60} |
| noi_4102_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.169 | -1.948 | False | 0.000 | 174 | {"obs_invalid": 36} |
| noi_4102_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.111 | -2.412 | False | 0.000 | 210 | {"obs_invalid": 42} |
| noi_4102_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.059 | -2.946 | False | 0.000 | 243 | {"obs_invalid": 51} |
| noi_4103_t4890 | NOI | 4890 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.294 | -1.855 | False | 0.000 | 183 | {"obs_invalid": 27} |
| noi_4103_t5010 | NOI | 5010 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.178 | -2.074 | False | 0.000 | 222 | {"obs_invalid": 30} |
| noi_4103_t5130 | NOI | 5130 | twin_state_4230.xml.gz | dem_f1.3 | demand | 0.165 | -1.959 | False | 0.000 | 249 | {"obs_invalid": 45} |

## 4. Summary

| Variant | representation | onset | locations | fault family | would-adopt INC | would-adopt NOI | MAP-family distribution | median gap | median P(incident) |
|---|---|---|---|---|---|---|---|---|---|
| V0 | R_E | logged | asrun | True | 0/13 | 0/9 | {"fault": 9, "demand": 13} | -3.688 | 0.004 |
| VP | R_P | logged | asrun | True | 0/13 | 0/9 | {"fault": 9, "demand": 9, "incident": 4} | -0.018 | 0.326 |
| VT | R_E | 4500 | asrun | True | 1/13 | 0/9 | {"fault": 8, "demand": 11, "incident": 3} | -3.357 | 0.007 |
| VPT | R_P | 4500 | asrun | True | 6/13 | 0/9 | {"incident": 11, "demand": 9, "fault": 2} | 0.124 | 0.502 |
| VPL | R_P | logged | asrun900 | True | 3/13 | 0/9 | {"incident": 7, "demand": 11, "fault": 4} | -0.182 | 0.489 |
| VPTL | R_P | 4500 | asrun900 | True | 5/13 | 0/9 | {"incident": 10, "demand": 9, "fault": 3} | -0.172 | 0.564 |
| VNF | R_E | logged | asrun | False | 0/13 | 0/9 | {"demand": 21, "incident": 1} | -3.688 | 0.021 |
| VPTLNF | R_P | 4500 | asrun900 | False | 5/13 | 0/9 | {"incident": 10, "demand": 12} | -0.172 | 0.742 |

Median gap by arm:

| Variant | median gap INC | median gap NOI | median gap all |
|---|---|---|---|
| V0 | -2.052 | -10.065 | -3.688 |
| VP | 0.368 | -1.452 | -0.018 |
| VT | -0.126 | -6.223 | -3.357 |
| VPT | 2.042 | -1.612 | 0.124 |
| VPL | 0.031 | -1.789 | -0.182 |
| VPTL | 1.705 | -1.948 | -0.172 |
| VNF | -2.052 | -10.065 | -3.688 |
| VPTLNF | 1.705 | -1.948 | -0.172 |

MAP-family distribution by arm:

| Variant | INC (13 evaluations) | NOI (9 synthetic evaluations) |
|---|---|---|
| V0 | {"fault": 7, "demand": 6} | {"demand": 7, "fault": 2} |
| VP | {"fault": 7, "demand": 2, "incident": 4} | {"demand": 7, "fault": 2} |
| VT | {"fault": 6, "demand": 4, "incident": 3} | {"demand": 7, "fault": 2} |
| VPT | {"incident": 11, "demand": 2} | {"demand": 7, "fault": 2} |
| VPL | {"incident": 7, "demand": 4, "fault": 2} | {"demand": 7, "fault": 2} |
| VPTL | {"incident": 10, "demand": 2, "fault": 1} | {"demand": 7, "fault": 2} |
| VNF | {"demand": 12, "incident": 1} | {"demand": 9} |
| VPTLNF | {"incident": 10, "demand": 3} | {"demand": 9} |

MAP hypothesis counts per variant:

| Variant | h* counts |
|---|---|
| V0 | {"dem_f1.15": 4, "dem_f1.3": 9, "flt_AID02109_noise": 3, "flt_AID02109_stuck": 2, "flt_AID02111_stuck": 2, "flt_AID02111_zero": 2} |
| VP | {"dem_f1.15": 2, "dem_f1.3": 7, "flt_AID02109_noise": 3, "flt_AID02109_stuck": 2, "flt_AID02111_stuck": 2, "flt_AID02111_zero": 2, "inc_ktb_n1_k1_s0.6": 4} |
| VT | {"dem_f1.15": 4, "dem_f1.3": 7, "flt_AID02109_noise": 2, "flt_AID02109_stuck": 2, "flt_AID02111_stuck": 2, "flt_AID02111_zero": 2, "inc_ktb_n1_k1_s0.6": 1, "inc_ktb_n1_k1_s1": 2} |
| VPT | {"dem_f1.15": 2, "dem_f1.3": 7, "flt_AID02109_stuck": 2, "inc_ktb_n1_k2_s0.6": 3, "inc_ktb_n1_k2_s1": 8} |
| VPL | {"dem_f1.15": 4, "dem_f1.3": 7, "flt_AID02109_noise": 1, "flt_AID02109_stuck": 2, "flt_AID02111_stuck": 1, "inc_ktb_n1_k1_s0.6": 2, "inc_ktb_n1_p900_k2_s0.6": 1, "inc_ktb_n1_p900_k2_s1": 4} |
| VPTL | {"dem_f1.15": 2, "dem_f1.3": 7, "flt_AID02109_stuck": 2, "flt_AID02111_stuck": 1, "inc_ktb_n1_k2_s1": 6, "inc_ktb_n1_p900_k2_s0.6": 3, "inc_ktb_n1_p900_k2_s1": 1} |
| VNF | {"dem_f1.15": 9, "dem_f1.3": 12, "inc_ktb_n1_k1_s1": 1} |
| VPTLNF | {"dem_f1.15": 2, "dem_f1.3": 10, "inc_ktb_n1_k2_s1": 6, "inc_ktb_n1_p900_k2_s0.6": 3, "inc_ktb_n1_p900_k2_s1": 1} |

|O| values over all evaluations: [135, 141, 144, 162, 165, 174, 177, 183, 204, 210, 222, 234, 243, 249]. Exclusions by reason:

| Evaluation | exclusions |
|---|---|
| inc_4101_t5010 | {"obs_invalid": 45} |
| inc_4101_t5040 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5100 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4101_t5160 | {"partial_block": 84, "obs_invalid": 36} |
| inc_4102_t4890 | {"obs_invalid": 33} |
| inc_4102_t4920 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t4980 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4102_t5040 | {"partial_block": 84, "obs_invalid": 33} |
| inc_4103_t4860 | {"partial_block": 84, "obs_invalid": 24} |
| inc_4103_t4890 | {"obs_invalid": 33} |
| inc_4103_t4920 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t4980 | {"partial_block": 84, "obs_invalid": 27} |
| inc_4103_t5040 | {"partial_block": 84, "obs_invalid": 33} |
| noi_4101_t4890 | {"obs_invalid": 48} |
| noi_4101_t5010 | {"obs_invalid": 48} |
| noi_4101_t5130 | {"obs_invalid": 60} |
| noi_4102_t4890 | {"obs_invalid": 36} |
| noi_4102_t5010 | {"obs_invalid": 42} |
| noi_4102_t5130 | {"obs_invalid": 51} |
| noi_4103_t4890 | {"obs_invalid": 27} |
| noi_4103_t5010 | {"obs_invalid": 30} |
| noi_4103_t5130 | {"obs_invalid": 45} |

On every INC evaluation |O| equals the library-internal support the as-run V0 evaluation scored on (the common-support intersection removes nothing V0 kept). Excluded triples are `partial_block` (the 120-s block is not complete inside the scoring window) and `obs_invalid` (the recorded observation is marked invalid); no triple is excluded for a missing replay value, so no variant's physics makes a triple unscorable.


No inferential statistics are reported: this is a 3-run diagnostic, and the summary states what moves the outcome conditional on these streams.

### What moves the outcome (descriptive, conditional on these streams)

- **Representation.** Holding the onset at the logged t_on, R_P (VP) raises the median incident-family posterior from 0.004 (V0) to 0.326 and makes an incident the MAP in 4 of 22 evaluations, but the best-incident-vs-best-demand gap still never reaches ln 10 on an INC evaluation: would-adopt stays 0/13.
- **The fault family is not the binding competition.** Removing it and splitting the mass 1/2 incident, 1/2 demand (VNF) leaves would-adopt at 0/13 and the median gap identical to V0's (-3.688): the family prior cancels in a best-incident-minus-best-demand ratio. Without the fault family the MAP is a demand hypothesis in 21 of 22 evaluations, so in V0 it is the demand family, not the fault family, that outranks the incident family.
- **Onset.** Moving the incident onset to 4,500 s under R_E (VT) gives 1/13; under R_P (VPT) it gives 6/13. With R_E the onset alone moves almost nothing; with R_P it is the factor that carries the gap past ln 10 (median INC gap 2.042 against 0.368 for VP).
- **Location.** Adding ktb_n1 at 900 m under R_P at the logged onset (VPL) gives 3/13 against VP's 0/13; at the 4,500 s onset (VPTL) it gives 5/13 against VPT's 6/13. The added location helps most at the logged onset and is not additive with the truth onset on these streams.
- **NOI.** No variant would adopt on any of the 9 synthetic NOI evaluations, including the truth-assisted ones with the imposed 4,500 s control onset (would-adopt 0/9 everywhere); the NOI gaps run from -12.856 to 0.129.

## 5. Failures by reason

| Evaluation | reason | detail |
|---|---|---|
| - | none | - |

## 6. Changes (file:line)

| Where | What |
|---|---|
| citypulse/branching/engine.py:145 | R_P selector: `spec["representation"] == "R_P"` places blockers instead of closing lanes; the R_E path is unchanged and remains the default |
| citypulse/branching/engine.py:187 | one stopped blocker per closed lane at pos, departPos = pos - 1, duration 3600 s, LCM 0 (the audit's H_G5 point blockage); no lane is disallowed |
| citypulse/branching/engine.py:273 | intervention onset (`t_on`) separated from the interval-collection start (`collect_from`, default `t_on`) -- caution (a) |
| citypulse/branching/engine.py:310 | interval collection uses `collect_from`; with the default this is the old `t_on` condition |
| citypulse/branching/engine.py:330 | the recorded blocker placement (edge, lane, pos, first stopped step, state at t_end) travels in the replay result |
| citypulse/twin/event.py:479 | `evaluate` accepts an explicit support set and its exclusions; both default to None, which keeps the library-internal support rule of the online method |

`git diff --stat`:

```
citypulse/branching/engine.py | 81 +++++++++++++++++++++++++++++++++++++------
 citypulse/twin/event.py       | 56 +++++++++++++++++++-----------
 2 files changed, 105 insertions(+), 32 deletions(-)
```

```diff
diff --git a/citypulse/branching/engine.py b/citypulse/branching/engine.py
index 85c9bab..d8799d5 100644
--- a/citypulse/branching/engine.py
+++ b/citypulse/branching/engine.py
@@ -148,2 +148,7 @@ def _apply_spec_at(tc, cs, stream, spec):
-    Incident: lanes 0..k-1 of the edge are disallowed and the remaining lanes' max speed is scaled by
-    ``speed_factor`` (the state file keeps neither, so both are recorded in the control state).
+    Incident, R_E (default): lanes 0..k-1 of the edge are disallowed and the remaining lanes' max speed
+    is scaled by ``speed_factor`` (the state file keeps neither, so both are recorded in the control
+    state).
+    Incident, R_P (``spec["representation"] == "R_P"``, the oct10-replay-diagnosis representation): one
+    stopped blocker vehicle per closed lane at ``pos`` -- the audit's H_G5 point blockage
+    (``citypulse/branching/audit_engine.py`` ``_twin_audit_worker``: a vehicle inserted at pos - 1 and
+    stopped at pos) -- and no lane is disallowed. The remaining lanes' max speed is scaled as in R_E.
@@ -159,4 +164,7 @@ def _apply_spec_at(tc, cs, stream, spec):
-        for ln in closed:
-            lane = f"{edge}_{ln}"
-            tc.lane.setDisallowed(lane, list(SCORE_VCLASSES))
-            cs.lane_disallow[lane] = list(SCORE_VCLASSES)
+        if spec.get("representation", "R_E") == "R_P":
+            _place_blockers(tc, edge, closed, float(spec["pos"]))
+        else:
+            for ln in closed:
+                lane = f"{edge}_{ln}"
+                tc.lane.setDisallowed(lane, list(SCORE_VCLASSES))
+                cs.lane_disallow[lane] = list(SCORE_VCLASSES)
@@ -178,0 +187,18 @@ def _apply_spec_at(tc, cs, stream, spec):
+def _place_blockers(tc, edge, lanes, pos):
+    """R_P: one Twin-owned stopped vehicle per closed lane at ``pos`` (point blockage, no lane closure).
+
+    The blocker is added with ``departPos = pos - 1`` and ``departSpeed = 0`` and stopped at ``pos``,
+    exactly as the audit's H_G5 does; SUMO inserts it at the first step at which that position is free.
+    """
+    if "hyp_route" not in tc.route.getIDList():
+        tc.route.add("hyp_route", [edge])
+    for ln in lanes:
+        vid = f"hyp_blocker_{ln}"
+        if vid in tc.vehicle.getIDList():
+            continue
+        tc.vehicle.add(vid, "hyp_route", typeID="t_car", departLane=str(ln),
+                       departPos=str(pos - 1), departSpeed="0")
+        tc.vehicle.setStop(vid, edge, pos=pos, laneIndex=ln, duration=3600.0)
+        tc.vehicle.setLaneChangeMode(vid, 0)
+
+
@@ -215 +241,6 @@ def _score_worker(job):
-    """One hypothesis in its own SUMO process: load the snapshot, restore, replay [t_on, t_end]."""
+    """One hypothesis in its own SUMO process: load the snapshot, restore, replay [t_on, t_end].
+
+    ``t_on`` is when the hypothesis is applied; ``collect_from`` (default ``t_on``, so the default is
+    unchanged) is the first instant whose detector intervals are kept -- the scoring window start. The
+    two are separate so a hypothesis's intervention onset can differ from interval collection.
+    """
@@ -241,0 +273 @@ def _score_worker(job):
+        collect_from = float(job["collect_from"]) if job.get("collect_from") is not None else t_on
@@ -243,0 +276,2 @@ def _score_worker(job):
+        want_blockers = bool(apply_spec and apply_spec.get("kind") == "incident"
+                             and apply_spec.get("representation", "R_E") == "R_P")
@@ -252,0 +287 @@ def _score_worker(job):
+        blockers = {}
@@ -265 +300,11 @@ def _score_worker(job):
-            if t > t_on + 1e-9 and abs(t - round(t / 30.0) * 30.0) < 1e-6:
+            if want_blockers:
+                # record the actual R_P placement: edge, lane, position and the step it stopped
+                for ln in apply_spec.get("lanes_closed") or []:
+                    vid = f"hyp_blocker_{ln}"
+                    if (vid not in blockers and vid in tc.vehicle.getIDList()
+                            and tc.vehicle.isStopped(vid)):
+                        blockers[vid] = {"edge": tc.vehicle.getRoadID(vid),
+                                         "lane": int(tc.vehicle.getLaneIndex(vid)),
+                                         "pos": float(tc.vehicle.getLanePosition(vid)),
+                                         "t_stopped": float(t)}
+            if t > collect_from + 1e-9 and abs(t - round(t / 30.0) * 30.0) < 1e-6:
@@ -271,0 +317,11 @@ def _score_worker(job):
+        if want_blockers:
+            # the blocker must still be stopped at the requested point at the end of the replay
+            for vid, b in blockers.items():
+                if vid in tc.vehicle.getIDList():
+                    b["pos_at_end"] = float(tc.vehicle.getLanePosition(vid))
+                    b["lane_at_end"] = int(tc.vehicle.getLaneIndex(vid))
+                    b["stopped_at_end"] = bool(tc.vehicle.isStopped(vid))
+                else:
+                    b["pos_at_end"] = None
+                    b["lane_at_end"] = None
+                    b["stopped_at_end"] = False
@@ -273 +329,2 @@ def _score_worker(job):
-                "intervals": intervals, "n_vehicles": n_veh, "veh_digest": digest,
+                "collect_from": collect_from, "intervals": intervals, "n_vehicles": n_veh,
+                "veh_digest": digest, "blockers": blockers,
@@ -288,2 +345,4 @@ def score_replays(state, meta, jobs, workers=8, seed=2, compliance=None):
-    ``t_on`` and ``lift`` at ``t_lift`` (both optional). Returns ``(results, wall_s)`` with one result
-    per job, in job order.
+    ``t_on`` and ``lift`` at ``t_lift`` (both optional). ``collect_from`` (optional, default ``t_on``)
+    is the first instant whose detector intervals are kept, so a hypothesis's intervention onset can
+    differ from the scoring window start. Returns ``(results, wall_s)`` with one result per job, in job
+    order.
diff --git a/citypulse/twin/event.py b/citypulse/twin/event.py
index a87380f..f1783bc 100644
--- a/citypulse/twin/event.py
+++ b/citypulse/twin/event.py
@@ -479,2 +479,8 @@ def evaluate(hyps, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=No
-             beta=BETA):
-    """Identical-support residuals -> logL -> beta posterior -> h*, gap vs the demand family, EVR."""
+             beta=BETA, support=None, excluded=None):
+    """Identical-support residuals -> logL -> beta posterior -> h*, gap vs the demand family, EVR.
+
+    With ``support`` -- an explicit list of (detector, block, channel, times) triples -- the library's
+    own intersection is not recomputed, so a caller can score several libraries on one preregistered
+    set O; ``excluded`` then carries that set's exclusions by reason. Both default to None, which keeps
+    the library-internal support rule of the online method exactly as it was.
+    """
@@ -482,16 +488,20 @@ def evaluate(hyps, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=No
-    excluded = Counter()
-    if partial:
-        excluded["partial_block"] = len(partial) * len(dets) * len(CHANNELS)
-    cand = [(det, b, x, ts) for det in dets for b, ts in sorted(complete.items()) for x in CHANNELS]
-    support, table = [], {}
-    for det, b, x, ts in cand:
-        reason = None
-        for hyp in hyps:
-            val, why = block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)
-            if val is None:
-                reason = why
-                break
-        if reason is not None:
-            excluded[reason] += 1
-        else:
-            support.append((det, b, x, ts))
+    explicit = support is not None
+    if not explicit:
+        excluded = Counter()
+        if partial:
+            excluded["partial_block"] = len(partial) * len(dets) * len(CHANNELS)
+        cand = [(det, b, x, ts) for det in dets for b, ts in sorted(complete.items())
+                for x in CHANNELS]
+        support = []
+        for det, b, x, ts in cand:
+            reason = None
+            for hyp in hyps:
+                val, why = block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)
+                if val is None:
+                    reason = why
+                    break
+            if reason is not None:
+                excluded[reason] += 1
+            else:
+                support.append((det, b, x, ts))
+    table = {}
@@ -500,2 +510,5 @@ def evaluate(hyps, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=No
-            table[(hyp.id, det, b, x)] = block_residual(
-                hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)[0]
+            r = block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)[0]
+            if explicit and r is None:
+                raise ValueError(f"the explicit support has no residual for {hyp.id!r} on "
+                                 f"({det}, block {b}, {x})")
+            table[(hyp.id, det, b, x)] = r
@@ -528 +541,2 @@ def evaluate(hyps, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=No
-                      sse=sse, support=support, excluded=dict(excluded), h_star=h_star, gap_vs_demand=gap,
+                      sse=sse, support=support, excluded=dict(excluded or {}), h_star=h_star,
+                      gap_vs_demand=gap,
```

New files: `citypulse/experiments/replay_diag.py`, `tests/test_replay_diag.py`, outputs under `results/replay_diag/`. Untouched: `citypulse/branching/audit_engine.py`, `citypulse/experiments/decision_audit.py`, `tests/test_audit.py`, `results/audit/`, `citypulse/twin/service.py`.

## 7. Raw rows

`results/replay_diag/raw.parquet`: 3520 rows, 24 columns (eval_id, run, arm, seed, t_eval, t_on, variant, representation, onset, locations, fault_family, stream_source, hyp_id, family, prior, logL, post, log_post, n_O, h_star, gap, gap_map, would_adopt, evr), written before any summary.

REPORT DONE
