# NA-300 qualification test: preregistered before any run (2026-10-03 20:40)

Decision-maker: Astra, read-only. The ruling is quoted in full in `~/.claude/runs/D--CityCom/20261003-2033-codex-astra-oct5result/out.md`.

## Oct 5 record (as ruled)

> Amended NA did not demonstrate improvement over OL and failed the preregistered stability criterion on every evaluation seed. OL's measured boundary **mean flow residual** was approximately 0–2%; its 30-s interior RMSE was consistent with the approximate independent-Poisson noise floor.

- Boundary flow agreement is not proven demand agreement.
- The noise floor limits the achievable RMSE, not statistical detectability.
- Four seeds establish neither equivalence nor general ineffectiveness.
- The stability PASS of the forced-AID07105 variant is kept separate from the amended FAIL.

Evidence:
- `results/assim/eval_amend/eval_report.md` (a98267b);
- `results/assim/eval/report.md` (variant forced07105);
- `results/assim/review_dsh.md`.

## Qualification test of a labelled revision, NA-300 (no subsequent tuning)

### Scenario

- 7,200 s, no incident.
- Proxy, coverage rule (`drop_every_3rd`) and boundary mapping (AID07106) unchanged.
- **Twin TKO base = 0.85 × the frozen Twin base**, identically in OL and NA-300. Other entries are unchanged.
- This is an imposed input reduction, not a guaranteed 15% observed mismatch.

### Controller NA-300

- Every 300 s, use the preceding non-overlapping ten 30-s intervals at the boundary detector; all ten must be valid.
- Gate: the mean observed occupancy of the ten intervals must be < 15%.
- e = (mean q_obs − mean q_twin) / base_s(t) in veh/h; deadband |mean residual| > 1σ_300.
- Δ = clip(κ·e, −0.05, +0.05) with κ = 0.3; m ← clip(m·(1 + Δ), 0.5, 1.5), starting from m = 1.
- The bounds are [0.5, 1.5] because the candidate pool scale is 1.5.

### σ_300

- 1.4826 · MAD of the **300-s mean residuals** (veh/h) at AID07106.
- Taken from the biased-OL development runs only: complete 300-s blocks within 900–7,200 s, no occupancy selection.

### Seeds

- Proxy development: 4001, 4002, 4003.
- Proxy evaluation: 5001–5008.
- Twin SUMO seed 2 and demand-stream seed 202 throughout.
- The arms are paired.
- Before launch, verify that these seeds appear in no existing result directory.
- Inference is conditional on that Twin realisation.

### Acceptance (all required)

1. Over 1,800–7,200 s, the paired seed-level difference NA-300 − OL in **interior 5-min flow RMSE** has a t-95% CI entirely below zero.
   - Interior excludes AID07105 and AID07106.
   - Score identical complete 5-min blocks across arms.
2. **All original stability limits pass on every evaluation seed**, after 1,800 s:
   - ≤ 6 reversals per hour;
   - range of m ≤ 0.20;
   - ≥ 80% of the time within ±5% of the median.

### Also reported (not acceptance)

- block exclusions by reason;
- the signed bias;
- the original 30-s metrics;
- 15-min forecasts from the 3,600 / 4,800 / 6,000 s snapshots.

### Before collecting evidence

- Fix dsh review items F2 (stale snapshot `m`), F3 (base-rate edge truncation) and F5 (missing σ must be a hard error).
- Verify replay: the snapshot's `m` equals the online `m` after that timestamp's tick, and a branch from a snapshot continues the online trajectory.

## Consequence for E\* (Oct 6)

- **If NA-300 qualifies:** NA-300 is M2-conv, with the identical normal controller beneath event-aware assimilation. The same 0.85 factor applies in every Twin arm. Paired Proxy seeds are 6001–6008, with Twin 2/202.
- **If it fails:** Oct 6 is a mechanics pilot only, and comparative efficacy claims are deferred.
