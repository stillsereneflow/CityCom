# Five-model review of `deep-research-report.md` (《城脉·涟控》)

Date: 2026-10-02. Reviewers, each working independently from the same prompt:

| Reviewer | Model family | Score for the recommendation | Keep the topic? | Web access |
|---|---|---:|---|---|
| Claude (me) | Anthropic | 7.5 | Yes | Yes: official guide PDF, SUMO docs, school news sites |
| codex | OpenAI (gpt-5.6-sol) | 6.5 | Yes | Yes, with links |
| dsh | DeepSeek | 7 | Yes | Partial (`.cn` and sumo.dlr.de failed) |
| agy-flash | Gemini 3.8 Flash | 7 | Yes | Unclear. One of its "facts" was wrong (see §4) |
| agy-pro | Gemini 3.1 Pro | 8.5 | Yes | Unclear |

The two agy lanes are both Gemini, so together they count as one model family, not two independent opinions.

## 1. Consensus: keep the topic, change the plan

All five reviewers say **the recommendation stands**. None would bet on another candidate over a narrowed 《城脉·涟控》.

Its lead over 生命绿波 is meaningless, though. Four reviewers recomputed the 13-weight model independently, and the published totals reproduce exactly: 9.14 / 9.11 / 8.96 / 8.67 / 8.43 / 8.32 / 8.21 / 8.12. A gap of 0.03 between hand-assigned scores is noise. The real tie-breaker is the one the report half-states: 生命绿波 is easy to reduce to "better ambulance pre-emption", while 涟控 has a better answer to "what does the twin add?". Don't put the weighted table in the PPT.

Every reviewer agrees on the same thing: **the topic is good, and the engineering plan overpromises for 21 days.**

## 2. Findings only I made, from the official guide (most important)

I pulled the official 12th-edition guide (参赛指南, dated 2026-06-23) and checked the report against it:

1. **The report misquotes the first-round criteria.** The guide (§2.3.2) lists six: 主题相关性、创意新颖性、**可行性**、社会与经济效益、**商业模式与市场前景**、**作品展现形式**. The report gives three and calls business logic a "bonus". It is a scored criterion, and the 简表 has a required 商业模式和预期效益 section.
2. **The first round is a document-only online review.** The live demo is judged only at the final on 12-26. Yet the report's plan writes the 说明书/简表 on Day 20. That is backwards: what decides whether you reach December is the 简表 (≤1500 字), the 说明书 (≤8500 字), the video, and the prototype with source code. The guide requires source code for software entries.
3. **There is no official "赛题原文" for the track.** The guide says 定向赛道 "每个赛道不设置具体题目，参赛同学可自行拟定题目". Section M of the report aligns itself sentence by sentence with track text it labels "用户提供的", and the guide doesn't contain that text. Check where it came from. If it isn't official, Section M loses its anchor.
4. **商业计划书 is optional** ("可选"). Teams are 1–4 people. The 简表 asks for a 技术成熟度 level, 国内外对比参照物, and 3–5 关键指标 backed by "试验报告/第三方检测报告". Simulated improvements will be self-reported, so plan for that field.
5. **The report misses the closest prior art: Aimsun Live and PTV Optima.** Real-time simulation-based prediction with parallel evaluation of response plans is what those commercial products do. Judges from industry may know them, and the 简表 asks you to name a comparison product. So position the project as open, lightweight, a learned forecaster combined with simulation, with measured twin fidelity. Don't claim to be the first to do counterfactual rollouts.
6. **Rule caveat:** the guide says 作品内容 "一律不得调整或更改" after the submission deadline, but it also promises finalists mentoring to 完善方案/提升表现形式. Ask the secretariat what may change before the final, because the report assumes CARLA and VLM can be added after October.

## 3. Technical problems raised by several reviewers

| Issue | Raised by | Fix |
|---|---|---|
| **Proxy A and Twin B use the same simulator, demand and parameters**, so the fidelity numbers are trivially good and it reads as "SUMO vs SUMO" | all 5 | Build in deliberate mismatch: a different car-following model (Krauss vs IDM), different sigma/tau, hidden demand multipliers, about 50% detector coverage, noise and latency. A fidelity curve that dips at incident onset and then recovers becomes the best plot you have. |
| **"Correct the twin every 20–30 s" names no actual mechanism**, and it is the real research problem | all 5 | Use calibrators only at entry/boundary detectors. Estimate demand and capacity parameters rather than moving vehicles. Detect the incident with a multi-hypothesis bank: candidate {edge, capacity loss}, roll each out, score against observations (dsh). Fallback: a calibrator-driven twin. Budget 3–7 days, not 1. |
| **The forecaster duplicates the rollouts.** The "do nothing" branch already is a forecast, so the "– forecast" ablation may show zero effect, which hurts you in Q&A | me, dsh, agy-flash | Give the GNN its own job: a millisecond network-wide trigger and pruning of candidate actions. Make it optional on the critical path, with persistence or TCN as fallback. Add a shockwave/CTM physics baseline. |
| **Label leakage**: using true `incident_mask`/`capacity_ratio` after claiming the system detects incidents automatically; rollouts reading the proxy's future departures | codex | Train and run on *estimated* incident features. Branches only see a demand forecast. |
| **Rerouting actions can't be transferred.** The twin has no vehicle-ID correspondence, so a per-vehicle routing plan can't be deployed to the proxy | dsh | Express routing as an edge-level policy (divert fraction f of vehicles using edge e). Report **decision regret**: benefit the twin predicted vs benefit the proxy realised. |
| **Rollout comparisons are noise without paired randomness** | me, dsh, codex | Use `--save-state.rng`, the same seed in every branch, and 3–5 replications per action. |
| **Compute**: 6 branches in sequence take tens of seconds | all | Run headless branches in parallel processes. Use a 300 s horizon and about 4 actions. Measure P50/P95 latency on the actual demo laptop. |
| **The Day-17 experiment matrix is 5×4×3×3×5 = 900 scenario cells**, times 5 baselines and ablations | dsh, codex, agy-flash | Reduce it, automate it, and start it running in the background from about Day 8. Log raw runs. |
| **Save/load caveats**: lane-change and car-following internal state aren't saved; flow vehicles may be missing on quick-load; subscriptions must be re-registered; runtime `setMaxSpeed`/`setDisallowed` changes may not survive | codex, dsh, me | Write a branching conformance test first: two branches with the same action must produce identical outputs. Define demand as `<vehicle>`/`<trip>` loaded via additional-files, not flows. |
| **Schedule**: Day 6 (twin), Days 8–11 (data plus GNN), Days 12–15 (branching plus control) and Day 17 are all underestimated | all | Finish the full narrow loop by Day 9–10 and the automated experiments by Day 13. Materials start in week 1 (my addition). Freeze features by Day 17. |

## 4. Disagreements and how they were settled

- **Was the 2024 华南理工 绿波 project a national first prize?** agy-flash said CONTRADICTED ("校内二等奖"). codex and dsh said verified. **I checked the SCUT news page:** "'人车智行'团队荣获全国一等奖". **agy-flash was wrong**, apparently an invented "fact".
- **Does TraCI have `loadState`?** dsh doubted it. codex said yes. **I checked the TraCI docs:** `load state (0x96)` exists ("faster than simulation.load since the network and additional objects are retained"). **dsh was wrong.** Its broader point still holds: parallel futures need separate processes.
- **Should you drop the dual-SUMO design?** agy-flash: replace it with one SUMO plus a macroscopic twin. agy-pro: sync only OD and the incident flag. codex, dsh and I: keep A/B but make it an honest model-mismatch benchmark, with a calibrator-driven fallback. **Position: keep A/B with mismatch.** Dropping it removes the project's answer to "how is this different from a SUMO simulation?".
- **agy-pro: "fake" the live rollouts by precomputing them.** Caching is fine as a stability backup *only if it is disclosed*. If a judge asks "is this live?" and the answer is no, the project loses credibility. **Rejected as stated.**
- **agy-pro: "the UI is 80% of the judging score."** Nothing supports this, and the first round is document-only. **Rejected.**
- dsh noticed that the 2025 figures give 49 + 143 = 192 = the number of finalists, so reaching the final may already guarantee at least 二等奖. codex found an earlier notice saying 203 projects advanced. This is plausible but unconfirmed, so don't rely on it.

## 5. Fact-check summary

| Claim | Status |
|---|---|
| Registration/eligibility deadline 10-23 12:00, submission 10-25 12:00, first round 10-26 to 11-23, final 12-26/27 | **Verified** (official guide; codex too) |
| First-round criteria (3 listed) | **Wrong**: the guide lists 6 (§2 above) |
| 商业计划书 status "unclear" | **Optional** per the guide |
| 2023 北航 I-BMS champion; 《纵横》 first prize, built on LibCity | Verified by codex (BUAA news) |
| 2024 华南理工 绿波 national first prize; Sameway second prize | **Verified** (I checked SCUT news) |
| 2025: 255 universities, 2335 teams, 2130 entries, 192 finalists, 49/143/295 prizes | Verified by codex (official summary). Earlier notice: 2338 registrations, 203 advancing |
| 2025 multimodal-LLM highway incident project, national first prize | Verified by codex (HIT) |
| 2026 intelligent-transport competition: 128 universities / 1026 entries; non-stop intersection and DRL-signal awards | Unverified |
| Official track text "高精度交通数字孪生模型 / 车流实时复刻…" | **Not in the official guide**. Source unknown |
| Weighted scores 9.14 / 9.11 | Reproduce exactly. The 0.03 gap is noise |
| SUMO saveState/loadState usable for branching | True, with the caveats in §3 |

Separately: the report's ~30 `citeturnNNviewMM` tokens can't be resolved. Replace them with real links before anything from the report goes into submission materials.

## 6. Recommended changes, merged and ranked

1. **Plan around the first round.** Start the 简表 and 说明书 in week 1, and write a real 商业模式与市场前景 section: customers are 交警 and traffic operations centres; offer it as a plugin or SaaS for existing signal platforms; compare against Aimsun Live / PTV Optima. By 10-25 have the video, prototype and source code. The full closed-loop polish continues toward the final, subject to the rule caveat in §2.6. Confirm registration and school eligibility now, because they close 10-23.
2. **Narrow the MVP:** 9 intersections, one incident type, 4 actions, a 300 s horizon, no VLM or CARLA. The Graph-TCN is optional.
3. **Turn A/B into an honest mismatch benchmark** using estimated (never true) incident and queue inputs and no future-demand access. Report fidelity, decision regret, and detection delay.
4. **Make incident and capacity estimation an explicit module.** Give the forecaster a distinct job (trigger and pruning). Route with edge-level policies. Use paired seeds and replications.
5. **Redesign the evaluation:** hold out locations, demand levels and ideally a second network; give baselines the same information; add a shockwave/CTM baseline; log raw runs; report mean ± CI and failure counts. A cheap local touch, since the organiser is 哈工大 / 哈尔滨: use a Harbin OSM network and add snow/ice capacity loss as one scenario axis.
