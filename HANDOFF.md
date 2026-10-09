# CityCom handoff: where the work stands and what comes next

Last updated: 2026-10-08, second session (v1.0 RELEASED and untouched: tag `competition-submission-v1.0` at 36d039b. **New: redesigned v2 package in `D:/CityCom-astra/competition_v2/`**, see "Competition v2" below).

**When the user says "resume" (or anything like "continue", "pick up where we left off"), read this file, then do "On resume" below, then carry on with the queue.**

## Project in one paragraph

This is the 12th China Postgraduate Smart City competition entry 《城脉·涟控》. It is an event-aware traffic digital twin on a synthetic corridor shaped like Kwun Tong Road / Kwun Tong Bypass.
- **Deadlines:** submission 2026-10-25 12:00. The design freeze was moved forward to **2026-10-06** on the user's instruction; results are final.
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
- Tests: `python -m pytest -q tests` gives 222 passed / 3 skipped at 4fe70e0.

## FINAL STATE (read this first)

- **Evidence package:** `D:/CityCom-astra/final/` (`README.md`, `FINAL_REPORT.md`, `CLAIMS.md` en+zh, `METHOD.md`, `figures/`, `tables/`, `demo/`); commit 4fe70e0.
- **Freeze:** `docs/freeze-2026-10-06.md` (+ Amendment A) and manifest `results/freeze/freeze_manifest.json`. Frozen code ed03254; collection at dcec083 after a Codex GO (4 rounds of pre-collection tooling fixes, none to the method).
- **Frozen test audit** (`results/frozen_audit/`, aa7de30; seeds 4501–4508, now consumed):
  - 960/960 branches ok;
  - belief B: a\* A3 8/8, oracle 7/8, BEE +2.162 [1.738, 2.586], regret −0.034, Spearman 0.825, calibration discrepancy 0.316;
  - D300 control: BEE −2.870.
  - It replicates the development audit's scenario-specific pattern.
  - Verified by three independent implementations (analyzer, Claude, agy-pro); Codex final ruling: no defect, no core work missing.
- **Allowed claims:** `final/CLAIMS.md` only. No post-freeze defects.
- **Submission package (done):** `D:/CityCom-astra/submission/` (`README.md` index):
  - 项目简表 and 作品说明书 (md/docx/pdf);
  - 14-slide deck with speaker notes (pptx/pdf);
  - 演讲稿 with 答辩预案;
  - 3-min demo video (mp4 + srt + storyboard);
  - anonymised source zip;
  - checks: number whitelist and anonymity, both PASS.

  Codex reviewed two rounds; the remaining blocker was fixed. agy-pro cross-checked every number: no number errors. Unredacted scan originals are kept outside the deliverables in `D:/CityCom/submission-internal/`.
- **Release (immutable):** tag `competition-submission-v1.0` (annotated, local, not pushed) at commit 36d039b in D:/CityCom-astra.
  - `release/competition-submission-v1.0.zip`, sha256 `c583b6b041331546876f35f604ea38bebfe112da504c4c2504edb36b114d3e5e` (also in `.zip.sha256`).
  - The unpacked copy is in `release/competition-submission-v1.0/`, with per-file `SHA256SUMS.txt`. Files are set read-only; `release/.gitattributes` = `* -text`, so a checkout is byte-identical to the checksums.
  - Final read-only Codex review returned READY; anonymity scan 0 identifying hits; number check only flags timing markers, citation years and one section number.
  - Do not edit the release. Any change means a new version (v1.1) with new checksums and tag.
- **Remaining:** only the upload itself (by 2026-10-25 12:00) and live rehearsal. Any wording change must stay within `final/CLAIMS.md`; rebuild with `submission/tools/` and re-run `check_numbers.py` and `scan_anonymity.py`.

## Decision documents, in order (all in `D:/CityCom-astra/docs/`)

1. `decision-2026-10-03b-synthetic.md`: the synthetic benchmark, net5, G3-v2.
2. `oct5-normal-assim-plan.md` and `na300-qualification-plan.md`: normal-mode assimilation. NA failed; NA-300 is NOT QUALIFIED.
3. `oct6-event-pilot-plan.md`, then `oct6-audit-and-pilot2-plan.md`: the event-engine pilots, and the preregistered offline decision audit.
4. **`decision-2026-10-05-roadmap.md`**: the current scope and the day-by-day plan to the freeze. **Read this one.**
5. `oct8-audit-sensitivity-plan.md` (done) and `oct10-replay-diagnosis-plan.md` (done, verified, 3b5e575; corrections in `results/replay_diag/corrections.md`).
6. **`oct11-missing-queue-plan.md`** (rev 2, Codex accepted, 302152e): 2 × 2 test, Twin state (C = restart without blockers, H = restart with R_P blockers from 4,500 s) × future duration (persistent, clears 5,400), fresh seeds 4301–4304. Classification order is fixed in the plan. Roadmap revision appended to `decision-2026-10-05-roadmap.md` (9c8cf08).

Findings log, chronological and terse: `C:/Users/chenq/.claude/runs/D--CityCom/step1-notes/notes.md`. (`step1-notes/` is this log, not a dispatch; it has no `merged` marker on purpose.)

**Competition FINAL (2026-10-09, current; supersedes v2 below):** `D:/CityCom-astra/competition_final/` (untracked, not committed).
- **Upload set:** `upload/` holds 01 简表, 02 说明书 and 03 商业计划书 (each .docx + .pdf, filled into the official 2026 templates) and `04_城脉涟控_补充材料.zip` (PPT, re-rendered video, prototype evidence, source code). `archive/` holds one all-in-one zip.
- **Team identity:** 川序 / 陈齐 / phone, given by the user 2026-10-09. It appears **only** in the 简表 identity cells. 团队成员 was not provided and is highlighted 待填写.
- **Constant-A3 baseline:** always-A3 also scores 7/8. This is disclosed everywhere 7/8 appears.
- **Deck:** 14 main + 8 backup slides.
- **Checks:** `validation_report.md` is 9 PASS / 1 WARN (团队成员) / 0 FAIL. codex's final verification says submission-ready apart from the open items.
- **Open items for the user:**
  - names for 团队成员;
  - Chang'an University internal deadline/process (no 2026 notice online; 2022 contact pyk@chd.edu.cn);
  - organizer confirmation of whether the 简表 identity fields go to reviewers;
  - re-export PDFs on a machine with 方正小标宋简体.
- **Rebuild:** run the scripts in `competition_final/_build/`: `fill_jianbiao.py`, `fill_doc_template.py <md> <template> <out>`, `build_deck_final.py`, `to_pdf.ps1`, `make_upload.py`, `validate_package.py upload`.
- **Report:** `final_revision_report.md`.

**Competition v2 (2026-10-08, second session, on the user's redesign request):** `D:/CityCom-astra/competition_v2/` holds a repositioned, competition-oriented package. It is **untracked and not committed** (the user did not ask for a commit).
- **Positioning:** a decision-fidelity audit system supported by counterfactual simulation; the event engine is an experimental component.
- **Files:**
  - `01_项目简表_v2` (filled on the official 附件1 template), `02_作品说明书_v2`, `03_答辩PPT_v2` (15 main + 6 backup slides, built by `_build/build_deck_v2.py`), `04_商业计划书_v2`;
  - `competition_compliance_checklist.md`, `claim_evidence_matrix.md` (the single source of truth), `cross_document_consistency_report.md`, `jury_questions_and_answers.md` (17 questions), `demo_storyboard.md`, `prototype_evidence/`, `revision_report.md`;
  - official templates in `official_templates/` (do not upload them).
- **Review:** codex ran 3 rounds; the last found no factual error left. agy-pro, agy-flash and dsh also reviewed. All of those dispatches are merged.
- **To rebuild after an edit:** run the scripts in `competition_v2/_build/` (`fill_jianbiao.py`, `build_docx_v2.py`, `build_deck_v2.py`, `to_pdf.ps1`, `figs_v2.py`, `fig_network.py`). Then rerun `submission/tools/check_numbers.py` and `scan_anonymity.py`.
- **Open for the user:**
  - identity fields in the 简表;
  - the school's internal deadline;
  - whether to tag v2 as a release, and whether to cut the 90-s v2 video (the v1 video's title card still shows the v1 subtitle).

**Session handoff 2026-10-08 (first session):** every dispatch directory is merged, the worktree is clean, and nothing is running. The next session's first message can simply be "resume". Then confirm the release state (`git -C D:/CityCom-astra describe --tags` → `competition-submission-v1.0`) and wait for the user's next instruction (upload or rehearsal help). Do not reopen experiments.

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

1. **List the run directory** `C:/Users/chenq/.claude/runs/D--CityCom/` and handle every dispatch *directory* without a `merged` marker (loose files there are old prompts, not dispatches). At the final handoff every dispatch was merged.
2. **The method is frozen and the test seeds are consumed.** Do not change the method, do not rerun the frozen audit, and do not pool development and test results. Any new experiment would need fresh seeds, a new preregistration and the user's go.
3. Remaining work, if asked, is submission writing from `final/`: every number and claim must come from `final/CLAIMS.md`.

## Queue (from `decision-2026-10-05-roadmap.md`)

| When | What | Status |
|---|---|---|
| Oct 6–7 | RNG isolation and paired CRN | done (d9d078b) |
| Oct 8–9 | One-factor audit sensitivities | done (a61e2bc) |
| Oct 10–12 | Matched-observation replay diagnosis | done (3b5e575, 302152e) |
| Oct 5–6 | Missing-queue test (`oct11-missing-queue-plan.md`) | done: **Support** (816829c); ruling and claim wording in `docs/decision-2026-10-06-missing-queue.md` (2e333b0) |
| Oct 6 | Fresh INC/NOI/SHK/DET development runs (`oct13-dev-runs-plan.md`, rev 2, 382db30; seeds 4401–4406) | done (b06513a), checks 3d60548, decision 53e4730 |
| Oct 6 | Frozen-audit preregistration + implementation (`oct16-frozen-audit-plan.md`, seeds 4501–4508) | prereg d7d5935 (Codex ACCEPT); code ed03254 |
| Oct 6 | **Design freeze** (moved forward) | 7a6a5ed + Amendment A; collection commit dcec083 |
| Oct 6 | Frozen audit on fresh test seeds | done, aa7de30 |
| Oct 6 | **Results final**; evidence package | done, 4fe70e0 |
| Oct 6 | Submission documents from `final/` | done (c031a19, 6e427b4) |

Seeds already used:
- 1001–1003, 3001–3004: development / evaluation;
- 4001–4003, 4101–4103: pilots;
- 4201–4208: audit;
- 5001–5008: NA-300;
- 4301–4304: missing-queue test;
- 4401–4406: development runs;
- 4501–4508: frozen test audit (consumed 2026-10-06).

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
