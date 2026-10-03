# Oct 5: normal-mode assimilation (report2 §G.3) on the frozen synthetic baseline. Predeclared before any assimilated run.

Baseline: net5 / synth5, frozen (`results/blite/synth5/READY`; Astra freeze review `~/.claude/runs/D--CityCom/20261003-1958-codex-astra-freeze/out.md`). The designed Proxy/Twin mismatch is retained: driver models, independent demand draws, and Twin TKO demand about 8% below the Proxy's.

## What is compared

| Arm | Twin | Role |
|---|---|---|
| **OL** | Open loop, m_s ≡ 1 (current `citypulse/twin/service.py`) | "No assimilation" reference |
| **NA** | Normal-mode assimilation per report2 §G.3 | The "conventional assimilation" arm that E\* later compares event-aware assimilation against (M2-conv) |

Both arms get identical causal sensor access: the same `SensorMsg` stream, 30-s intervals, no truth.

## NA, as specified, with initial values and **zero tuning budget**

- Every 60 s, use the last two 30-s intervals. For each boundary entry s that has a boundary detector b(s):
  - if the observed occupancy o_b < o_crit and b is valid in both intervals:
    - e_s = (q_b − q̂_b) / base_s(t);
    - if |r_b^q| > δ: m_s ← clip(m_s · (1 + clip(κ · e_s, −0.05, +0.05)), 0.5, 1.8);
  - otherwise m_s is unchanged.
- Parameters, fixed with no tuning: κ = 0.3, δ = 1.0 σ, o_crit = 15%.
- r_b^q = (q_b − q̂_b) / σ_b^q, where σ_b^q = 1.4826 · MAD of the OL residuals on the **development** runs only (t ≥ 900 s, no incident).
- base_s(t) is the Twin base insertion rate of entry s, i.e. the candidate-pool rate divided by the pool scale, in veh/h. q values are converted to veh/h.
- **Entries:** only TKO has a boundary detector, AID07105 on `tko_in`; its entry edge in the routes is `tko_insert`. The cross-street stubs have no detector, so their m stays 1. No split-ratio update (optional in §G.3, not used).
- Twin snapshots, rewinds and branches carry m_s and the stream pointer in their JSON meta.

## Runs

All runs are two-world, no incident, synth5 demand, 7,200 s, Proxy `CITYPULSE_REROUTE=0`.

| Set | Proxy seeds | Twin seed / demand seed | Use |
|---|---|---|---|
| Development | 1001, 1002, 1003 | 2 / 202 | σ estimation; implementation debugging; **no parameter selection** |
| Evaluation (fresh) | 3001, 3002, 3003, 3004 | 2 / 202 | All reported comparisons; frozen before they are run |

Each evaluation seed is run in both arms (paired).

## Metrics (evaluation seeds; window 1,800–7,200 s)

Interior detectors are all detectors **except** AID07105, which is used for assimilation.

1. **Interior fit:** per run, the RMSE of the 30-s flow residual q − q̂ (veh/h), pooled over interior detectors and intervals where both values are valid. Also the speed RMSE (km/h) where both are non-null.
2. **Forecast:** at t ∈ {3,600, 4,800, 6,000}, take the Twin snapshot, freeze m, run the Twin 15 min ahead with no further assimilation, and compute the interior flow RMSE against the Proxy observations of the same 15 min.
3. **Multiplier stability (NA only)**, after t = 1,800 s:
   - the range of m_TKO;
   - reversals: sign changes between consecutive non-zero updates;
   - the time fraction within ±5% of the median of m_TKO.
4. **Boundary fit:** the AID07105 flow RMSE. Reported as a sanity check, not as evidence.

## Acceptance (Oct 5 row of `docs/decision-2026-10-03.md`)

- **"NA beats OL":** the paired NA − OL difference of metric 1 (interior flow RMSE) has a t-based 95% CI entirely below 0 over the 4 evaluation seeds. Metric 2 is reported beside it with its CI.
- **"Without multiplier oscillation":** on every evaluation seed, after 1,800 s:
  - at most 6 reversals per hour;
  - range of m_TKO ≤ 0.20;
  - ≥ 80% of the time within ±5% of the median.
- **A negative result is reported as such.** No retuning after the evaluation runs.

## Amendment 2026-10-03 20:15 (before any NA evaluation result existed)

Astra's ruling is quoted in full in `~/.claude/runs/D--CityCom/20261003-2013-codex-astra-assim/out.md`.

**What exposed the problem.** dsh's implementation smoke run (`results/assim/impl/report.md`) found that the firewall coverage rule `drop_every_3rd` (`citypulse/proxy/sensors.py:11-12`) drops AID07105, which is sorted index 11. The as-predeclared NA arm is therefore NA ≡ OL by construction. That establishes unobservability, not ineffectiveness.

A labelled dev-seed diagnostic, with AID07105 forced observable on seed 1001 only, also showed:
- the congestion gate blocked 44 of 60 ticks;
- σ ≈ 623 veh/h;
- m moved down to 0.86.

**No evaluation-seed result had been produced or seen.** At 20:14 only the OL run directories existed.

**Amended (for the amended NA arm only):**
- **Boundary rule:** b(s) is the most upstream detector in the fixed observed set along the entry path, with no demand-carrying entry or exit between the entry boundary and that detector. This is frozen as **b(TKO) = AID07106**. Missing observations do not trigger dynamic re-selection.
- **Coverage rule unchanged.**
- **σ for AID07106:**
  - pool the valid paired **30-s** flow residuals in veh/h from the OL development runs, seeds 1001–1003, t ∈ [900, 7200] s, no incident, without occupancy selection;
  - σ = 1.4826 × median(|r − median(r)|);
  - report the counts and exclusions;
  - do not reuse the provisional σ from AID07105.
- **Parameters unchanged:** κ = 0.3, δ = 1σ, o_crit = 15%, the two-interval mean, 60-s ticks, step and m bounds.
- **Scoring mask:** interior excludes **both AID07105 and AID07106**, identically for OL and amended NA, including forecasts. The boundary sanity metric moves to AID07106.
- **Unchanged:** seeds, windows, acceptance criteria and stability limits. All tick reasons are reported.
- **Reserved for a separately preregistered revision:** a 60-s σ, longer averaging, and fitting o_crit from occupancy.

**Records.** Any NA runs made under the original mapping are kept as the as-predeclared record, labelled with their start times.

## Also on Oct 5: G4 detector correction (from the freeze review)

- Reset the 2-interval streak across missing intervals: two crossings must be at timestamps exactly 30 s apart.
- Re-evaluate the existing `results/blite/synth5/g45/g4_*/bottleneck_index.csv`.
- Diagnose and count the missing B intervals by reason (24–27 of 240 per run). A likely cause: `read_detectors` returns `v = None` when a 30-s interval has no vehicle.
- The historical 4,860 s value stays recorded. The corrected alarm (expected 4,890 s, a 390 s delay) is reported beside it.
