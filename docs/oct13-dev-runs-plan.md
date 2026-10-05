# Fresh development runs of the unchanged event method (INC / NOI / SHK / DET): preregistered before any run (2026-10-06, revision 2)

Revision 2 answers the blocking review `~/.claude/runs/D--CityCom/20261006-0100-codex-sol-devprereg/out.md`; its round-2 review (items 1–4 and 6 resolved) prescribed the exact completeness-manifest fix, adopted verbatim below. It adds: clearance in absolute time and per episode; fixed evaluation denominators and censoring; forecast issue sets within the horizon; spell outcomes; completeness and failure accounting; asset and configuration hashes.

Roadmap: `docs/decision-2026-10-05-roadmap.md` (revision of 2026-10-05 evening), Oct 13–15. Required elements: `~/.claude/runs/D--CityCom/20261006-0000-codex-sol-mqresult/out.md`, question 4. Method and scenarios: `docs/oct6-event-pilot-plan.md` as amended by `docs/oct6-audit-and-pilot2-plan.md` part B. Scope: `docs/decision-2026-10-06-missing-queue.md`.

## Purpose

Development evidence for the method as it will be frozen on 2026-10-16: natural adoption, identification, false adoption, clearance and recovery, forecasts, exclusions, and live DEGRADED coverage, on fresh seeds and all four scenarios. This is a measurement. **There are no accuracy acceptance criteria**; nothing here qualifies E\*, and nothing is tuned from it.

## Method, unchanged and pinned

- Provenance, written to `results/dev_runs/provenance.json` before the first run:
  - `git rev-parse HEAD` and `git status --porcelain` for `citypulse/` and the driver (collection must not start with uncommitted execution code);
  - sha256 of `citypulse/twin/event.py`, `citypulse/twin/service.py`, `citypulse/branching/engine.py`, `citypulse/twin/demand_stream.py`, `citypulse/experiments/event_pilot.py` and the development driver;
  - sha256 of both sigma JSONs and of the resolved network, detector, demand (`proxy.rou.xml`, `proxy_shock.rou.xml`, `twin_cand.rou.xml`), vehicle-type and signal/control files that the commands actually load;
  - the effective command line of every Proxy and Twin process (also in each `run_info.json`).
  No source file under `citypulse/` changes during collection.
- Configuration (as pilot 2): event grid `pilot2` (20 hypotheses: 10 incident, 4 demand, 6 fault; family mass 1/3, uniform within), incident representation **R_E**, provisional onset alarm − 600 s, noise c = 5, β = 0.25, τ_LR = ln 10, the corrected G4 trigger, DEGRADED exit at entry + 900 s exactly, `--event-sigma results/event_pilot/impl/sigma_event.json`, `--event-workers 4`.
- Twin (both arms): seed 2, demand seed 202, base factor 0.85, `--assim normal300 --boundary-detector AID07106`, sigma `results/assim/na300/sigma300_dev.json`. Actions held at A0.
- No forced adoption and no forced DEGRADED in this run set.

## Scenarios (as `docs/oct6-event-pilot-plan.md`, Proxy side only)

| Scenario | Proxy | Truth used for scoring only |
|---|---|---|
| INC | `ktb_n1` lanes 0–1 blocked at 900 m, 4,500–5,400 s | onset 4,500, clearance 5,400, edge `ktb_n1`, (k, s) = (2, 1.0) |
| NOI | no event | none |
| SHK | +30 % demand, 4,500–5,400 s (`synth5/proxy_shock.rou.xml`) | demand event, no capacity loss |
| DET | AID02109 stuck at its last valid pre-4,500 reading, 4,500–5,400 s, emitted observations only | detector fault on AID02109, type stuck |

Proxy sensor seed 77; network net5, demand synth5, horizon 7,200 s.

## Seeds and pairing

- Proxy development seeds **4401–4406** (N = 6). Before launch, check that no run directory, JSON `seed` field or Parquet `seed` column under `results/` uses them; write `results/dev_runs/seed_check.json`. Reserved and untouched: 6001–6008 (E\*) and whatever the frozen-audit preregistration names.
- Arms **EVT** and **CONV** for every scenario and seed: 2 × 4 × 6 = **48 two-world runs**.
- Pairing check (blocking): within a (scenario, seed), EVT's and CONV's `twin_log.parquet` must have the same unique (t, detector) keys and identical observation columns, including validity flags and null patterns (the Proxy does not see the Twin; actions are A0). If they differ, stop and report.
- Firewall check (blocking): no truth field reaches the Twin, as check 1 of the pilot plan.

## Outcomes (definitions fixed now)

Per run and pooled per scenario, with denominators.

**Evaluation sets.** A *library evaluation* is an evaluation of the 20-hypothesis library in SUSPECTED_EVENT or DEGRADED. A *clearance evaluation* is an evaluation of the active h\* against H_clear in EVENT_ASSIMILATION; it uses a different library and never enters adoption or non-incident denominators. Library evaluations are reported as attempted, successful and failed (failures by reason). A scenario or run with zero successful library evaluations reports adoption rates as **N/A**, not 0.

1. **Exposure:** alarm events; minutes in SUSPECTED_EVENT, DEGRADED, EVENT_ASSIMILATION and RECOVERY; library and clearance evaluations (attempted/successful/failed).
2. **Natural adoption (INC, EVT):** an adoption with the gap > ln 10, reported per run (any adoption) and per successful library evaluation. Each adoption is classed by its time: **pre-onset** (< 4,500 s), **during the incident** [4,500, 5,400), or **post-clearance** (≥ 5,400 s). **Identification**, over all natural INC adoptions: h\* edge = `ktb_n1` (location correct); (k, s) reported, exact match to (2, 1.0) reported separately. **Delay:** first adoption time − 4,500 s; INC runs with no adoption are right-censored at 2,700 s (the 7,200-s horizon).
3. **False adoption:** any adoption in NOI, SHK or DET (EVT), per run and per successful library evaluation.
4. **Non-incident handling**, per successful library evaluation: SHK, whether the MAP is in the demand family and the false-alarm path writes m and returns to NORMAL; DET, whether the MAP is a fault on AID02109 and of type stuck.
5. **Clearance, per adoption episode** (every adoption episode in every run is accounted for, not one per run). The runner logs τ_c as a look-back of 60–300 s and lifts the restriction at t_dec − τ_c (`citypulse/twin/service.py:394-436`). For each executed clearance record the **decision time t_dec** and the **inferred clearance time t_clr = t_dec − τ_c**.
   - For natural INC episodes adopted during the incident: **premature inference** if t_clr < 5,400 s; **premature live release**, reported separately, if t_dec < 5,400 s; **late** if t_dec > 6,300 s; **overdue, right-censored** if the episode is still in EVENT_ASSIMILATION at 7,200 s.
   - Pre-onset, post-clearance and false-adoption episodes: t_dec, t_clr and the outcome are reported separately, without the premature/late labels.
   - Not applicable without an adoption.
6. **Recovery spells:** each spell is **completed** (exit conditions met), **interrupted by a new trigger**, or **censored** at 7,200 s; durations kept.
7. **DEGRADED spells, live:** each spell is **resolved by adoption** (EVENT_ASSIMILATION entered), **scheduled timeout** (exit to NORMAL), or **censored** at 7,200 s; durations kept. Only a scheduled timeout is checked for exit at entry + 900 s exactly, and only scheduled timeouts count as live coverage of the exit. If none occurs, the exit is reported as **not live-covered**; it is not forced and no further runs are added for it.
8. **Exclusions:** per library and clearance evaluation, |O| and exclusions by reason.
9. **Forecasts:** halting vehicles on `ktb_w3` + `ktb_n1`, from Twin branches frozen at issue, scored offline against Proxy truth. Issue sets: **5-min** horizon at the 8 marks 4,500, 4,800, …, 6,600 s; **15-min** horizon at the 7 marks 4,500, …, 6,300 s (6,600 + 900 > 7,200). Every (run, horizon, mark) cell in these sets is required; a missing snapshot, prediction or truth value is a failure, never a silently smaller denominator. Per arm and scenario: MAE and mean signed error over (seed, mark). Paired difference EVT − CONV of the absolute error per (seed, mark), over complete EVT/CONV pairs only, summarised by mean and per-seed values. Descriptive only.

## Mechanics coverage (the only success criteria)

Each item is reported as covered **live**, **direct** or **unit**, as in the pilot reports: the 10 mechanics checks of `docs/oct6-event-pilot-plan.md`, with check 10 requiring a live DEGRADED entry and its scheduled exit. An uncovered item is reported as uncovered. No accuracy outcome is a pass/fail criterion.

## Raw data, failures, reruns, budget

- Every run keeps its full logs (`twin_log`, `event_log.jsonl`, state trace, `replacement_log.jsonl`, `queue_forecasts.json`, `run_info.json`, stdout/stderr) under `results/dev_runs/runs/`.
- **Completeness manifest, frozen before collection** in `results/dev_runs/completeness_manifest.json` (round-2 fix, `~/.claude/runs/D--CityCom/20261006-0130-codex-sol-devprereg2/out.md`):
  - the expected detector IDs, taken from the resolved detector configuration (not from collected output); `twin_log.parquet` must hold exactly one row for every (t, detector) in {30, 60, …, 7,200} × those IDs;
  - every required snapshot and every forecast cell of outcome 9, each with an available prediction and truth value;
  - every required log, with its per-arm applicability: `run_info.json` with the effective commands, stdout/stderr, `twin_log.parquet`, `assim_log.parquet` (both arms); `state_trace.jsonl`, `event_log.jsonl`, `replacement_log.jsonl` (EVT only; `event_log.jsonl` and `replacement_log.jsonl` may legitimately be empty when no evaluation or replacement happened; the file must still exist).
- A run is **complete** only if both processes exit 0 and every manifest item is present. Any missing required artefact, missing or duplicate observation key, or missing forecast component makes the run **incomplete**, with the reason recorded; incomplete runs are excluded from complete-run statistics. No evaluation error may be swallowed: every caught replay failure is logged as a failed evaluation and counted, and a run whose only defect is fully logged evaluation failures is **complete but flagged**.
- **Failures and reruns.** Every attempt is preserved, including failed ones. A run that fails for an infrastructure reason (port, process start such as `0xC0000142`, disk) may be rerun **once** with identical arguments, into a new attempt directory; the original artefacts are kept and both attempts are listed in `reruns.json`. No rerun for any outcome-related reason. A slot still incomplete after its one rerun is a permanent failure.
- **Accounting.** Outcome tables and `runs_summary.json` are produced only after all 48 planned slots have been attempted, and list every slot: complete, flagged or permanently failed, with reasons. Per-arm statistics use complete runs; paired statistics (forecasts, pairing check) use complete EVT/CONV pairs only.
- At most 4 runs in parallel (each EVT run uses 4 scoring workers). Budget: about 48 × 2 min ≈ 30–60 min wall; implementation half a day (the pilot-2 runner already exists).
- Report descriptively. Negative results are recorded as negative. Nothing is tuned, and no outcome is relaxed or redefined after the data.
