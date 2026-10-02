# Five-model review of `deep-research-report1.md` (revised 《城脉·涟控》)

Date: 2026-10-02. Same five reviewers and the same method as round 1 (`fleet-review-of-deep-research-report.md`). Each reviewer worked independently and could see the round-1 review.

| Reviewer | Family | Score for the revised plan | Original plan (round 1) |
|---|---|---:|---:|
| Claude (me) | Anthropic | 8 | 7.5 |
| codex | OpenAI | 6.5 (about 4.5 for a solo team) | 6.5 |
| dsh | DeepSeek | 7.5 | 7 |
| agy-flash | Gemini | 8 | 7 |
| agy-pro | Gemini | 8.5 | 8.5 |

## 1. Verdict

**Everyone agrees the revision is a real improvement, not a renaming.** Most of round 1's blocking items are now fixed:
- the six first-round criteria are quoted correctly
- the unofficial track text is disowned
- Aimsun and PTV are acknowledged, and the report positions against them correctly
- there is an information firewall table
- proxy and twin are deliberately mismatched
- the forecaster has its own job (spillback warning)
- rerouting assumes limited driver compliance
- the experiment matrix is down to 120 runs
- the precomputed fallback is labelled as such
- it says to ask the organisers in writing

**The new headline, "Decision Regret", is now the weakest part,** and the revision has made it the centre of the story. Five issues follow, and every reviewer raised the first four on their own.

## 2. Problems with Decision Regret

1. **The concept is not new.** Measuring regret against an oracle is the standard loss in predict-then-optimize (SPO, Elmachtoub & Grigas), decision-focused learning, online learning and simulation optimisation. Delete "首次" everywhere: the 摘要 leads with it, and the later caveat isn't enough. Suggested wording: "将决策遗憾作为稀疏感知、模型失配条件下交通数字孪生的**离线决策质量审计协议**" (codex, dsh), with citations.
2. **As specified, the measurement is statistically meaningless.** Running each action once in a stochastic proxy gives noise. Needed:
   - the same random seed and the same pre-generated demand and compliance draws across every action (common random numbers)
   - 5–20 replications per action
   - a paired mean with a 95% CI, and the minimum detectable effect, before quoting any figure
   
   The oracle must minimise the *expected* cost, not pick the best single run. Settled direction of the bias (dsh had it backwards): the minimum over noisy runs is biased low, so a naive regret estimate is **inflated**. The twin's predicted gain for the action it picked is biased **upward** (winner's curse), so the gain-calibration error comes out positive even for an unbiased twin. dsh adds: normalise regret by the *achievable* gain, `(J(a*)−min J)/(J(a0)−min J)`, otherwise it is always tiny and flatters the system. The 120-run budget cannot hold oracle × replications. Re-budget.
3. **"Realized gain" only exists in the lab.** A real deployment never sees the no-action world. State plainly that regret is an offline benchmark that the proxy makes possible. dsh's best idea: also offer a *deployable* surrogate, estimating gain-calibration error with difference-in-differences or interrupted time series (treated vs control intersections, before and after). That turns the weakness into a second contribution.
4. **The diagram leaks ground truth.** C5 (Regret/Confidence) receives proxy truth (`P2 -.-> C5`) and feeds the online twin (`C5 --> T2`). That breaches the report's own firewall, and no mechanism is defined anyway. Split the diagram into an **online loop** (sensors → assimilation → control) and an **offline audit loop** (oracle, shadow worlds). Give online confidence a real job using sensor residuals and perturbed-twin rollout spread only. dsh's suggestions: an execution gate ("act only if the predicted-gain CI excludes zero", measured as harmful interventions avoided), and a modulator on assimilation gain.
5. **Units are inconsistent:** "0.9 pp" in §H, "0.9%" in §M.

## 3. Pipeline problems

- **Assimilation will fight the incident (all 5 reviewers).** A lane block lowers downstream flow, and EWMA/RLS reads that as falling demand, so it explains the incident away. Interior calibrators insert or remove vehicles and can erase the very spillback you want to track. Fix:
  - put calibrators only at entry/boundary detectors
  - when the anomaly detector fires, **freeze demand updates and switch to incident hypotheses** (which edge, how much capacity was lost)
  - bound and rate-limit the multiplier, add a dead-band, and keep the update interval at or above the corridor travel time
  - watch for RLS losing excitation under constant demand
  - plot the multiplier trace, and report fidelity on **held-out detectors**
  
  Written up, this gating logic *is* the technical core.
- **The mismatch is still a single number (dsh, an important catch).** The YAML has proxy `demand_scale: 1.12` and twin `initial_demand_scale: 0.95` over the *same* base demand. The twin knows the full spatio-temporal pattern and only has to estimate one scalar, so high fidelity is guaranteed by construction. A different car-following model appears only as "进阶版本" (§G). Fix: independent proxy demand realisations, per-entry time-varying multipliers, different route choice, and the different car-following model **from Day 3**. Also state that the twin is never warm-started from the proxy's full state.
- **The ripple predictor's ablation can't show a KPI effect** with 3–4 fixed actions. Either make the action set depend on the predictor (it chooses which upstream intersections to retime), or evaluate it only on its own metrics: F1, time-to-spillback MAE, warning lead time, branches avoided (codex, dsh). Use a CTM/queue-storage predictor in the MVP; GCN-GRU is optional.
- **Rerouting still isn't transferable** (dsh). "覆盖率/服从率" doesn't solve the missing vehicle-ID correspondence. State an edge-level divert-fraction policy.
- **Save/load pitfalls are still open:** lane-change and car-following internal state; flow vehicles missing on quick-load (define demand as `<vehicle>`/`<trip>` via additional-files); subscriptions must be re-registered; check whether runtime signal-program changes leak across branches. **The first experiment should be a conformance test:** two no-action branches from one snapshot must produce identical outputs.

## 4. Schedule

- The report says "说明书从 Day 1", but its table only has a 目录 on D1 and "说明书 90%" on D18, with nothing between. The revision contradicts its own rule (me, agy-pro, codex, dsh). Have a complete rough draft by D10–12, record a working-loop video the day the loop first runs (D12–13), and upload by D19–20.
- **Underestimated:**
  - D2 (cleaning the OSM network and signal programs takes 2–3 days)
  - D6–7 (assimilation takes 4–7 days)
  - D11 (multi-process branching)
  - D14 (the full dashboard in one day)
  - D16 (more than 250 runs in one day)
  
  codex: build instrumentation and the batch runner from about D4, not D15.
- **The report never states team size.** This plan needs 3–4 people; codex scores it 4.5 for one person.

## 5. Fact check

| Claim | Status |
|---|---|
| Aimsun Tees Valley: ~600 deployments, 13.7% travel-time reduction (modelled counterfactual, Jul–Sep 2025, playbooks + signal control) | **Verified** (me, codex) |
| PTV Optima York, rolling 15-min model | Verified (codex) |
| CoLLMLight at ICLR 2026 | Verified (codex, dsh) |
| OpenCity (HKUDS) 2024 | Verified (codex, dsh) |
| 2023: 2194 teams / 166 finalists | Verified (codex) |
| 2024: 3378 teams / 200 finalists | **Verified** (me, codex). Also 274 universities, 43/146/414 prizes |
| 2025: 2338 registrations, 49/143/295 | Verified, but 2338 is registrations; 2335 is participating teams |
| 2025 二等奖 "标智眼" | **Verified** (I checked the HPU page). agy-flash said "contradicted"; it was wrong |
| 2025 二等奖 "以盔助行" | Unverified (agy-flash named a university without a source; not accepted) |
| HK Transport Department minute-level data with history; UTD19 40 cities / 23,541 detectors | Verified (codex) |

**A correction to round 1:** dsh's inference that reaching the final guarantees at least 二等奖 (from 2025: 49+143 = 192) **fails for 2024**, where 43+146 = 189 < 200 finalists. Don't rely on it.

**Still unfixed from round 1:** about 66 `citeturn…` tokens that can't be resolved (codex counted). Keep them out of the 说明书.

## 6. Presentation risks: numbers that will leak

These figures in the report have no caveat next to them: "Twin Fidelity 91.8%" (an undefined metric), "MAE 8.3→3.1 km/h", "异常概率 94%", "检测延迟 47 s", "25% 传感器". The −18.7% / 16.1% / 0.9 figures are repeated without caveat in §M and in the example LLM prompt. They will end up in the video script, the PPT and the 简表's 关键指标 field.

Fix: keep a `docs/numbers.md` that maps every number to a run ID or `PLACEHOLDER`, and make packaging fail if a placeholder value remains (codex, dsh).

Also unsafe to copy:
- "首次", "实际/真实收益", "证明现实有效"
- an unsupported "Confidence: High"
- CO₂ that isn't labelled as a SUMO HBEFA estimate
- "消散时间" without a stated threshold
- a business model with no sizing or unit economics; it's a scored criterion, so one page of numbers is cheap insurance (dsh)

## 7. Disagreements and how they were settled

- **标智眼:** agy-flash said contradicted; codex said verified. I checked the HPU news page and it won 全国决赛二等奖. **agy-flash was wrong**, its second invented "contradiction" in two rounds. Discount agy-flash's fact checks from now on.
- **Direction of the oracle bias:** dsh said regret is biased downward; codex and I said the noisy-min oracle inflates it. **Settled: inflated.** E[min of noisy estimates] ≤ the true minimum, so the subtracted term is too small.
- **Score spread (6.5–8.5):** codex is lowest because it assumes the team may be small and penalises scope. That's a real dependency. **Tell us the team size.**
- **dsh's "47 s is physically impossible with 60 s sensors":** the report aggregates every 30 s (round 1 assumed 5 s), so 47 s is possible. The underlying point stands: state the aggregation window next to any detection delay.

## 8. Recommended changes, ranked

1. **Reframe regret** as an offline audit protocol with citations and no "首次". Use common random numbers, replications, CIs and normalisation by achievable gain. Add a deployable difference-in-differences gain estimator. Withdraw every numeric regret figure until it has been measured.
2. **Split the architecture** into an online loop and an offline audit loop (this removes the C5→T2 leak). Give online confidence a concrete job: an execution gate and an assimilation-gain modulator.
3. **Make the mismatch structural from Day 3** and the assimilation **anomaly-gated** (boundary demand, then incident-capacity hypotheses). Report fidelity on held-out detectors. Write it up as the technical core.
4. **Put the submission on the critical path:** writing slots in the table, a full draft by D12, a loop video by D13, a batch and conformance harness by about D4, upload D19–20. Size the scope to the actual team.
5. **Quarantine placeholders and broken citations** (`numbers.md` plus a check at packaging time). Pick the demo network on purpose: a Hong Kong corridor makes the HK data replay real input on the same network; Harbin ties to the organiser. Right now replay of HK data on a different city's network is only an interface demo.
