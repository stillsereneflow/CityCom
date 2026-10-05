# CityCom handoff: where the work stands and what comes next

Last updated: 2026-10-06 06:40 (session 2 end: replay diagnosis, missing-queue test (Support), dev runs + checks, frozen audit preregistered and implemented; awaiting go for the frozen audit).

**When the user says "resume" (or anything like "continue", "pick up where we left off"), read this file, then do "On resume" below, then carry on with the queue.**

## Project in one paragraph

This is the 12th China Postgraduate Smart City competition entry 《城脉·涟控》. It is an event-aware traffic digital twin on a synthetic corridor shaped like Kwun Tong Road / Kwun Tong Bypass.
- **Deadlines:** submission 2026-10-25 12:00; design freeze 2026-10-16; results freeze 2026-10-18.
- **Plan of record:** `D:/CityCom/deep-research-report2.md`.
- **Two worlds:**
  - **Proxy** (hidden "real world"): IDM `pdist` drivers, with incidents injected;
  - **Twin**: Krauss `tdist` drivers, Poisson-thinning demand, sees only sensor messages through a firewall.
- **Submission scope** (decided 2026-10-05): a laboratory prototype covering verified replay mechanics and bounded, scenario-specific decision fidelity.
  - **No claims of:** reliable incident inference, accurate benefit prediction, real-world effectiveness, or event-assimilation superiority.
  - **E\* is not run** in its gated form.

## Where the code is

**All active work is in the git worktree `D:/CityCom-astra`, on branch `astra/step1`.** `D:/CityCom` (`master`) holds only the older decision documents, plus this file. Run everything with cwd `D:/CityCom-astra` and these settings:

- Python: `D:/CityCom/.venv/Scripts/python.exe` (SUMO 1.27.1).
- Env: `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 CITYPULSE_NET=blite CITYPULSE_BLITE_REV=5 CITYPULSE_REROUTE=0`.
- Frozen baseline: net5 / synth5 (`results/blite/synth5/READY`).
- Tests: `python -m pytest -q tests` gave 112 passed / 3 skipped at a61e2bc.

## Decision documents, in order (all in `D:/CityCom-astra/docs/`)

1. `decision-2026-10-03b-synthetic.md`: the synthetic benchmark, net5, G3-v2.
2. `oct5-normal-assim-plan.md` and `na300-qualification-plan.md`: normal-mode assimilation. NA failed; NA-300 is NOT QUALIFIED.
3. `oct6-event-pilot-plan.md`, then `oct6-audit-and-pilot2-plan.md`: the event-engine pilots, and the preregistered offline decision audit.
4. **`decision-2026-10-05-roadmap.md`**: the current scope and the day-by-day plan to the freeze. **Read this one.**
5. `oct8-audit-sensitivity-plan.md` (done) and `oct10-replay-diagnosis-plan.md` (done, verified, 3b5e575; corrections in `results/replay_diag/corrections.md`).
6. **`oct11-missing-queue-plan.md`** (rev 2, Codex accepted, 302152e): 2 × 2 test, Twin state (C = restart without blockers, H = restart with R_P blockers from 4,500 s) × future duration (persistent, clears 5,400), fresh seeds 4301–4304. Classification order is fixed in the plan. Roadmap revision appended to `decision-2026-10-05-roadmap.md` (9c8cf08).

Findings log, chronological and terse: `C:/Users/chenq/.claude/runs/D--CityCom/step1-notes/notes.md`.

## Results so far (all verified by recomputation unless marked otherwise)

**Offline decision audit** (`results/audit/report.md`, v2 corrections in `results/audit/v2/`): 8 seeds.
- The Twin chose A3 on 8/8 seeds; the Proxy oracle agreed on 7/8.
- Signed BEE +1.63 veh·h [1.04, 2.22], against a calibration floor of 0.18.
- Regret 0.03; Spearman 0.85.
- Paired CRN median ρ: Twin 0.90, Proxy 0.99.
- RNG isolation passes.

**Sensitivities** (`results/audit/sens/report.md`, a61e2bc):
- With the true incident duration (D300, a positive control), the Twin's predicted gain is about 0, so BEE −3.19 and the ranking collapses.
- The other one-factor variants stay within about 0.15 veh·h of the baseline.
- **Working hypothesis, not yet tested:** the conventional Twin at t_d lacks the queue the Proxy has built since 4,500 s. The persistent-blockage belief compensates, so the baseline's good ranking may be "right for the wrong reason". This needs a test before any claim.

**Replay diagnosis** (verified from `raw.parquet`, β = 0.25; Codex reviewed, agy-pro second opinion):
- Would-adopt INC/NOI: V0 0/13, VP 0, VT 1, VPT 6, VPL 3, VPTL 5, VNF 0, VPTLNF 5; NOI 0/9 everywhere.
- Ruling: keep R_E and the alarm − 600 s onset through the freeze; R_P is a diagnosed alternative. An R_P successor needs its own preregistration plus `_lift_spec_at` / `restriction_present` changes.
- Fixed-A3 R₂ gains: Twin baseline 6.76, Twin D300 0.18, Proxy 5.13. Proxy `ktb_n1` halting at 5,100 s on 4201–4208: 8–30 vehicles.

**Event engine:**
- **Pilots 1 and 2:** no natural incident adoption, since the MAP is always a fault or demand hypothesis.
- **Forced adoption** verified the replacement, clearance and RECOVERY mechanics, but clearance came early in 3/3 runs.
- **A modelling gap found by Codex:** incident hypotheses close lanes along the whole edge (`_apply_spec_at` ignores `pos`), while the Proxy incident is a point blockage. That gap is the replay diagnosis's main question.

## On resume (do these first, in order)

1. **List the run directory** `C:/Users/chenq/.claude/runs/D--CityCom/` and handle every dispatch *directory* without a `merged` marker (loose files there are old prompts, not dispatches). At handoff (2026-10-06 ~06:40), every dispatch was merged.
2. **State:** development runs done and checked (`docs/decision-2026-10-06-dev-runs.md`, 53e4730). Frozen-audit code is implemented and smoke-tested on dev seed 4201 (ed03254): `citypulse/experiments/frozen_audit.py` (prepare / twoworld / rngcheck / branches / statehistory) and `frozen_audit_analyze.py` (analyze). **Seeds 4501–4508 are untouched.**
3. **Open decision for the user:** run the frozen audit now (declaring the design freeze early, since Codex ruled "freeze unchanged") or wait for Oct 16. Once the user says go: `frozen_audit.py prepare` (clean tree) → `twoworld` → `rngcheck --seed 4501` → `branches` (detached, ~1–2 h) → `statehistory` → `frozen_audit_analyze.py analyze --dir results/frozen_audit`. Then verify from raw, Codex review, and start the write-up with the coverage-and-claims table.

## Queue (from `decision-2026-10-05-roadmap.md`)

| When | What | Status |
|---|---|---|
| Oct 6–7 | RNG isolation and paired CRN | done (d9d078b) |
| Oct 8–9 | One-factor audit sensitivities | done (a61e2bc) |
| Oct 10–12 | Matched-observation replay diagnosis | done (3b5e575, 302152e) |
| Oct 5–6 | Missing-queue test (`oct11-missing-queue-plan.md`) | done: **Support** (816829c); ruling and claim wording in `docs/decision-2026-10-06-missing-queue.md` (2e333b0) |
| Oct 6 | Fresh INC/NOI/SHK/DET development runs (`oct13-dev-runs-plan.md`, rev 2, 382db30; seeds 4401–4406) | done (b06513a), checks 3d60548, decision 53e4730 |
| Oct 6 | Frozen-audit preregistration + implementation (`oct16-frozen-audit-plan.md`, seeds 4501–4508) | prereg d7d5935 (Codex ACCEPT); code ed03254, smoke-tested; collection awaits go |
| Oct 16 | **Design freeze** | |
| Oct 16–18 | Frozen audit on fresh test seeds | |
| Oct 18 | **Results freeze**, then writing the submission | |

Seeds already used:
- 1001–1003, 3001–3004: development / evaluation;
- 4001–4003, 4101–4103: pilots;
- 4201–4208: audit;
- 5001–5008: NA-300;
- 4301–4304: missing-queue test;
- 4401–4406: development runs;
- 4501–4508: frozen audit (preregistered, untouched).

**6001–6008 are reserved for E\* and untouched.** Pick fresh ranges for anything new, and check that no result uses them.

## Working rules that must carry over

**Codex (`gpt-6.1-sol`) is the decision-maker and reviewer.** It does not implement (see `D:/CityCom/CLAUDE.md`).
- Invoke it read-only:
  ```
  codex exec --skip-git-repo-check -s read-only -c openai_base_url="https://chatgpt.com/backend-api/codex" -m gpt-6.1-sol -c model_reasoning_effort=high -C "D:/CityCom-astra" -o "$R/out.md" - < "$R/prompt.md" > "$R/out.log" 2>&1; echo $? > "$R/exit"
  ```
- **Launch it detached** (`nohup sh -c "…" &`). Session ends killed two foreground reviews.

**Implementation goes to dsh and agy.** agy-flash must take part in every multi-piece task; agy-pro is the long-reasoning reviewer. Long jobs are launched **detached with `nohup sh -c "…; echo \$? > exit" &`**, because background tool calls are capped at 2 hours. agy-flash and agy-pro share one quota: a 429 means wait for the stated reset time.

**Every experiment is preregistered before it runs.**
- Write the plan in `docs/`, get Codex's review (at most two rounds), and commit it before any run.
- Truth-assisted variants are labelled offline positive controls.
- Negative results are recorded as negative; acceptance is never relaxed retrospectively.

**Verify every worker result yourself**, by recomputing from the raw data before quoting it. Worker reports have overclaimed (for example "all 10 checks passed") and have had real defects that only showed up on checking.

**Keep the user's messages short.** Report results concisely, and don't dump command output.
