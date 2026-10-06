# 《城脉·涟控》 — the exact claims we may make

Source of authority: the read-only ruling `~/.claude/runs/D--CityCom/20261006-1450-codex-sol-finalresult/out.md` (decision-maker), on results verified by Claude from raw outputs and cross-checked by two further independent implementations (the project analyzer and an independent Gemini script). Every number below is quoted from `results/` files named in `final/FINAL_REPORT.md`. Intervals are 95 % t intervals over eight seeds; costs and gains are in veh·h (vehicle-hours of total time spent over the 15-min decision horizon).

## (a) Verified facts — quote these numbers exactly

**Frozen test audit** (seeds 4501–4508, run once after the 2026-10-06 design freeze; conventional Twin with an imposed incident belief):
- Integrity: 960/960 branches successful; zero reruns, duplicates or exclusions; seed-freshness and RNG-isolation checks passed; code hashes identical before and after collection.
- The Twin chose A3 (incident signal plan + VMS diversion) on **8/8** seeds; the Proxy oracle was A3 on **7/8** (A4 on seed 4508); Top-1 agreement **7/8**.
- Benefit-estimation error (predicted − realised gain of the chosen action) **+2.162 [1.738, 2.586]**; relative to the no-action total time spent **1.9 %** (not relative to the benefit).
- Split regret **−0.034 [−0.113, 0.046]**; ranking agreement Spearman **0.825 [0.738, 0.912]**, Kendall **0.675**.
- Monte-Carlo calibration discrepancy (Proxy standing in for the Twin) **0.316 [0.134, 0.499]**.
- Fixed action A3: Twin-predicted gain **7.066** vs Proxy-realised **4.904**.
- Truth-assisted control D300 (true clearance time given to the Twin): chosen action A3/A0/A1 on 5/2/1 seeds; BEE **−2.870 [−4.914, −0.826]**; regret **1.804 [−0.282, 3.891]**; Spearman **−0.350**; fixed-A3 gains **0.212** vs **4.904**. (BEE is 0 on seeds 4507/4508 only because A0 was chosen.)
- At the decision time the Proxy held **7–24** halted vehicles on the incident corridor and **161–194** vehicles on `ktb_n1`; the conventional Twin held **0** halted and **26–43**.

**Development audit** (seeds 4201–4208, unchanged): A3 **8/8**, oracle agreement **7/8**, BEE **+1.63 [1.04, 2.22]**, split regret **0.03 [−0.04, 0.10]**, Spearman **0.850**, Kendall **0.750**, calibration discrepancy **0.18 [0.08, 0.28]**; D300 BEE **−3.19**.

**Frozen vs development:** the frozen audit **replicated the scenario-specific pattern** — A3 selection, 7/8 oracle agreement, positive benefit overestimation, strong positive ranking agreement and near-zero split regret. BEE +2.16 vs +1.63 and calibration discrepancy 0.32 vs 0.18 are larger point estimates; neither exact magnitudes nor the between-set difference (or equivalence) were established. The two seed sets are never pooled.

**Missing-queue diagnostic** (preregistered, seeds 4301–4304, 720/720 branches): classification **Support**. Replaying the incident history into the Twin cut the fixed-A3 absolute gain error under truth-assisted clearance from **4.16 to 0.90** (paired changes −4.58, −3.25, −3.06, −2.17; mean −3.27). Queue at decision time: Proxy 55/7/40/25, conventional Twin 0/0/0/0, replayed-history Twin 14/15/17/19. Duration sensitivity fell from 6.0–7.7 to 1.4–3.0. Full-action ranking did not improve.

**Event engine** (20-hypothesis laboratory engine: replay scoring and state management): deterministic replay, identical scoring support, capacity restriction and the observation firewall are verified by recorded checks. Forced pilot runs exercised state replacement, clearance and recovery; clearance was premature in **3/3** primary forced episodes and **1/4** recovery spells completed normally. DEGRADED's scheduled exit has unit-test evidence only.

**Replay diagnosis** (three recorded incident streams): point blockage plus truth-assisted onset raised hypothetical would-adopt evaluations from **0/13 to 6/13**; every variant stayed negative on **nine** synthetic no-incident evaluations. These are dependent offline evaluations, not controller trajectories or a false-adoption rate.

**Fresh event development runs** (48/48 slots, 24 matched EVT/CONV pairs): 6 incident runs gave **13** suspected-event episodes, **25** library evaluations and **0/6** natural adoptions. EVT and CONV forecasts were identical (incident MAE **20.6** halting vehicles at 5 min, **18.8** at 15 min; 48/42 cells per arm, none missing). No-incident, demand-shock and sensor-fault runs produced no alarms (18 runs); the shock realised only **5–8 %** extra corridor flow and the fault was stuck at a normal reading.

## (b) Limitations

- One synthetic corridor, one incident type, one decision time, one action menu; eight test seeds.
- The frozen audit evaluates the conventional Twin **with an imposed incident belief**, not successful online incident inference.
- NA-300 normal assimilation is unqualified; posterior tempering (β = 0.25) and thresholds are uncalibrated.
- The fresh runs give no live clearance, recovery or DEGRADED coverage; the engine never adopted an incident naturally.
- Replay-diagnosis conclusions depend on the saved histories and scoring support. Missing-queue evidence (N = 4) is descriptive, and history replay changes the whole inherited state, not only the queue.
- Split regret is measured against an oracle chosen on M₁ and evaluated on M₂; a negative regret does not mean the Twin beat a true oracle.
- The calibration discrepancy is an empirical Monte-Carlo level, not a proven lower bound, and is never subtracted from BEE.
- Seed 4503 had 90 s of alarm-to-decision lead time (below the 120 s allowance); the decision time stayed at 5,100 s as preregistered.

## (c) Interpretations (always worded as interpretations)

- The evidence is **consistent with compensating errors**: the persistent future-blockage belief partly offsets the Twin's missing incident history.
- Restoring historical state **supports an inherited-state explanation** for the Twin's sensitivity to the duration belief.
- Good action agreement alongside optimistic benefit estimates **suggests that decision agreement and benefit accuracy can diverge**.

## (d) Hypotheses that remain unproven

- That the queue deficit alone causes the benefit bias.
- That an observation-only point-blockage successor would infer incidents reliably.
- That history replay would improve online forecasting or general action ranking.
- That any of these findings transfer to real traffic or other scenarios.

## (e) Claims that must not be made

- Reliable incident inference, deployment readiness, real-world effectiveness, event-assimilation superiority, or general benefit-prediction accuracy.
- "Proved right for the wrong reason"; exact state recovery; a causal "BEE minus floor" structural gap; accurate D300 predictions on the grounds that two BEE values are zero.
- Robust handling of a realised +30 % demand shock or of detector faults in general; successful natural clearance or recovery.
- Any pooled development + test statistic.

---

## 可以使用的表述（中文摘要）

- **冻结测试审计**（8 个从未使用的种子，设计冻结后只运行一次）：960/960 分支全部成功，复核全部通过。孪生在 8/8 个种子上选择 A3（事故信号预案 + VMS 诱导），与代理世界最优动作一致 7/8；收益估计误差 +2.16 [1.74, 2.59] 车·时（高估），分拆遗憾 −0.03 [−0.11, 0.05]，排序一致性 Spearman 0.825。
- **开发审计**（另 8 个种子，结果不变）：A3 8/8，一致 7/8，收益估计误差 +1.63 [1.04, 2.22]。冻结测试**复现了同一场景下的规律**（选择 A3、7/8 一致、收益高估、排序强正相关、遗憾接近零）；两组数值不合并。
- **缺失排队诊断**（预注册，4 个种子）：把事故历史回放进孪生后，A3 收益误差从 4.16 降到 0.90 车·时；结论为"支持"。解释：结果**与误差相互抵消一致**（持续封堵的假设部分抵消了孪生缺失的事故历史）。
- **事件感知引擎**：回放评分、状态替换、清除与恢复的机制在实验室条件下得到验证；在新的开发运行中**没有**自然采纳事故假设（0/6），需求冲击与传感器故障场景未触发报警。
- **不得声称**：可靠的事故推断、可部署、真实道路有效、事件同化优于常规同化、收益预测普遍准确、合并开发与测试数据的统计量。
