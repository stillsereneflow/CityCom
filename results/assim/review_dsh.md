MODEL: deepseek-v4.1-flash

# Review: normal-mode assimilation (commit 721c043) — correctness and test quality

Read-only pass over `citypulse/twin/assim.py`, `citypulse/twin/service.py` (`--assim`/`--sigma-json`/
`--boundary-detector`), `citypulse/twin/demand_stream.py` (`base_rate`, acceptance), `citypulse/branching/engine.py`
(`m` restore), `tests/test_assim.py`, against `docs/oct5-normal-assim-plan.md` (incl. the 20:15 amendment) and
`D:/CityCom/deep-research-report2.md` §G.3 (238–260). No file was modified; every claim below was checked by
reading the code and by running the frozen artifacts (`scenarios/kwuntong/blite/synth5/twin_cand.rou.xml`,
`results/assim/eval/na_*/twin/assim_log.parquet`, `results/assim/eval/na_*/twin/twin_state_*.json`) with the
project venv (`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`). `pytest tests/test_assim.py -q` → 10 passed.

**Baseline for "Oct 5 results"**: eval NA arm = AID07105 forced observable + `sigma_dev.json`
(`{"AID07105": 533.736}`), 4 eval seeds; reported Δ(NA−OL) interior flow RMSE = **+25.18 veh/h**,
CI [−32.82, +83.19] (FAIL), forecast Δ = +29.98 (CI [−72.04, +131.99]), stability PASS (range ≤ 0.143,
≤ 2 rev/h, ≥ 80% within ±5%).

## Findings, ranked

### F1 — HIGH (meaning of the result, not the numbers). κ and `base_s(t)` are inert: every update is a fixed ±5% step

`citypulse/twin/assim.py:115` (deadband), `:118-119` (step clip, m clip); `citypulse/twin/service.py:94-97`.

The deadband opens only when |r| > 1, i.e. |q_b − q̂_b| > σ = 533.736 veh/h, so at every updating tick
|e_s| > σ/base_s ≈ 533.736/2572…2936 ≈ 0.18–0.21, hence κ·|e_s| > 0.3 × 0.18 = 0.054 > `step_clip` = 0.05.
The step clip therefore binds at *every* update, and the whole m trajectory is a sign-only (bang-bang) ±5%
controller: κ and the magnitude of e_s are discarded.

Demonstrating input (all seven Oct 5 NA runs): every one of the **37 rows with `reason == "updated"` in
`results/assim/eval/na_*/twin/assim_log.parquet` has |delta| = 0.050000 exactly** (checked `abs(abs(delta)-0.05) < 1e-12` → 37/37).
Example row: `na_1001` t=120, `e_s = −0.4225`, `r = −1.574`, `delta = −0.0500` (κ·e_s = −0.1268, clipped 2.5×).
Equivalently, per-tick clip threshold `0.05·base/σ ∈ [0.186, 0.275]`; any κ ≥ 0.275 reproduces this trajectory
bit-for-bit, and the plan's predeclared κ = 0.3 sits just above the threshold that makes it unidentifiable.
A synthetic input in the production regime shows it directly: base = 2812, σ = 533.736, resid = +534 veh/h →
|r| = 1.001 (deadband opens), e_s = 0.19, κ·e_s = 0.057 → delta = +0.05.

**Would it change the Oct 5 results?** No — the code matches the predeclared rule, so the numbers stand. It
changes what they mean: metric 3's PASS is a property of a fixed-step controller, the plan's κ (`[开发集调参]`,
report2:256) cannot be tuned or falsified on these runs, and "NA not better than OL" cannot be attributed to the
proportional gain. The `tests/test_assim.py` regime hides this (see T2).

### F2 — HIGH for branching/event mode, NONE for the Oct 5 metrics. The snapshot's `m` is one tick stale

`citypulse/twin/service.py:69-75` (state + meta written **inside** the stepping loop) vs `:82-98` (the
assimilation tick runs **after** the loop, once `read_detectors` has been read).

Every `SNAPSHOT_TIMES` entry (`citypulse/experiments/normal_assim_eval.py:35`) is a multiple of 60 s, so every
snapshot coincides with an assimilation tick; the meta records the pre-tick `m`.

Demonstrating input (frozen artifacts): `results/assim/eval/na_1003/twin/twin_state_4200.json` has
`m = {"tko_insert": 0.9025}`, while the assim row at t=4200 is `updated` → `m = 0.947625` (= 0.9025 × 1.05);
`na_3003/twin/twin_state_3000.json` has 0.95 vs the tick's 0.9975. A branch/forecast replaying from those
snapshots therefore runs 5% below the online Twin from that instant — a CRN break versus the online continuation
(≈34 vehicles over a 900 s horizon at base ≈ 2700 veh/h), which is exactly the replay fidelity §G.4 depends on.
I checked all 10 snapshot times × 7 NA runs: only these two mismatch, so the *state* itself is consistent.

**Would it change the Oct 5 results?** No. Metric 2 uses only t ∈ {3600, 4800, 6000}, and in all 7 runs the tick
at those three times was `congested`/`deadband`/`invalid` (never `updated`), so `snap_m == m_after` there; the
mismatches fall on 3000/4200, which the metric does not use. It is a latent defect that fires as soon as a
snapshot time lands on an updating tick. Fix: write the meta (and ideally save the state) after the assimilation
block for that timestamp.

### F3 — MEDIUM. `base_s(t)` is a truncated-window rate at the pool edges (up to 2× low)

`citypulse/twin/demand_stream.py:61-71`: the count is over `[t−300, t+300)` but the denominator is the fixed
`2·window = 600` s, so wherever the window overruns the candidate pool the rate is scaled down.

Demonstrating input (frozen pool `scenarios/kwuntong/blite/synth5/twin_cand.rou.xml`, span [0.55, 7199.66],
8436 `tko_insert` candidates, global rate 2812 veh/h ≈ `TKO_IN_VPH` = 2800):

| t (s) | 60 | 120 | 180 | 240 | 300 | 3600 | 6900 | 6960 | 7080 | 7200 |
|---|---|---|---|---|---|---|---|---|---|---|
| `base_rate("tko_insert", t)` | **1700** | **1988** | **2304** | **2592** | 2880 | 2756 | 2748 | 2488 | 1904 | **1432** |

The first four ticks (t ≤ 240) and the last five (t ≥ 6960) are biased low by up to 1.65×/1.96×, so `e_s` is
inflated by the same factor there. The logged value confirms the code path is the biased one: `na_1001` t=120 has
`base = 1988` (table above). Note also that the window is future-inclusive (±5 min) — Twin-internal, so not a
firewall leak, but not a causal estimate either.

**Would it change the Oct 5 results?** No, as run — because of F1 the step is clipped to ±0.05 regardless of
`base_s`, so the magnitude never reaches m (verified: the 37 updating ticks all have base ∈ [2572, 2936], and
even a halved base would still leave κ|e_s| > 0.05). It *does* change the logged `e_s` diagnostics, and it would
change results under the revision the amendment reserves (60-s σ, longer averaging) or any κ < ~0.27. Fix:
divide by the actual in-pool window length, or clamp the window to the pool.

### F4 — MEDIUM. The upper third of the predeclared m range is unrealizable (acceptance saturates at m = scale = 1.5)

`citypulse/twin/demand_stream.py:90` (`u < m/scale`) with `scale = TWIN_CAND_SCALE = 1.5`
(`citypulse/demand/synth_demand.py:50`), against `m_max = 1.8` (`citypulse/twin/assim.py:74`, plan §G.3).

Demonstrating input (frozen pool, same seed): accepted candidates with `depart ≤ 3600 s` —
m = 1.0 → 4443, m = 1.2 → 5006, **m = 1.5 → 5862, m = 1.6 → 5862, m = 1.8 → 5862**. The thinning probability
saturates at 1.0, so any m > 1.5 produces *identical* demand; the assimilator may sit at m = 1.8 while the
realized insertion rate stays at 1.5 × base. `tests/test_assim.py:65-70` asserts m = 1.8 is reachable in the
assimilator, which is true but cannot be realized in the stream.

**Would it change the Oct 5 results?** No — m stayed inside [0.8574, 1.0474] in all seven runs, and the plan's
stability bar is about the lower half of the range. It would matter for any upward adaptation beyond +50%
(e.g. the shock arm) and it means the m clip at 1.8 is untested end-to-end.

### F5 — MEDIUM. A missing/absent σ silently degrades NA to OL (the exact failure the amendment was written about)

`citypulse/twin/service.py:45` (`sigma = json.load(...) if (assim_on and sigma_json) else {}`), `:96`
(`sigma_q=sigma.get(boundary_detector)`), `citypulse/twin/assim.py:93,107` (missing σ → `invalid`, no update).
`citypulse/experiments/normal_assim_eval.py:144` only appends `--sigma-json` `if sigma_json and Path(sigma_json).exists()`.

Demonstrating input: `python -m citypulse.twin.service --assim normal --boundary-detector AID07106 …` with no
`--sigma-json`, or with a JSON that lacks the boundary key (`{"AID07105": 533.736}` while the detector is
AID07106) → **120/120 ticks `reason == "invalid"`, m ≡ 1.0** — the run is bit-for-bit OL, but `twin_stats.json`
still says `"assim": "normal"` and an `assim_log.parquet` is written. The harness turns this into a silent
false negative if the σ path is wrong (it checks `Path(...).exists()` but not the key).

**Would it change the Oct 5 results?** No — the eval runs did pass σ (`run_info.json` lists
`results/assim/eval/sigma_dev.json`, value 533.736, and the logs show 37 updates). But the acceptance rule is a
*negative* result, which this failure mode fabricates; the guard should be a hard error when
`assim == "normal"` and σ for the selected detector is missing or ≤ 0.

### F6 — MEDIUM (spec reading, results-relevant). The congestion gate averages the two intervals' occupancy

`citypulse/twin/assim.py:104` (`_mean(o_obs) >= o_crit → congested`). The plan says "if the observed occupancy
o_b < o_crit and b is valid in both intervals" (plan:17; report2:247) without saying whether the gate is on the
two-interval mean or per interval; the amendment freezes "the two-interval mean" among the parameters (plan:80),
so the mean is defensible, but it is an unstated choice that materially moves the result.

Demonstrating input (frozen artifacts): of the 37 updating ticks, **20 (54%) were applied at ticks where one of
the two observed AID07105 intervals had occupancy ≥ 15%** (from `twin_log.parquet.obs_o`); e.g. `na_1001` t=2760
(o = 15.8%, 9.2% → mean 12.5), `na_3002` t=3180 (10.9%, 18.1% → mean 14.5), `na_3003` t=3000 (16.4%, 13.5%).
Under the per-interval reading ("both intervals must be below o_crit") those ticks would be blocked, so **the m
trajectories — and hence Δ = +25.18 with CI [−32.82, +83.19] — would change**. (No `congested` tick had both
intervals below 15%, so the mean gate is never stricter than the per-interval one here.)
`tests/test_assim.py:79-81` pins the mean as intended, so this is a documentation/predeclaration gap rather than
a coding slip; the plan requires all tick reasons to be reported (plan:82), and the reading should be stated there.

**Would it change the Oct 5 results?** Yes, under the per-interval reading — 54% of the updates would disappear.

### F7 — LOW. Update boundary is 1 s, not 0: candidates due at the tick instant use the old m

`citypulse/twin/service.py:63-66` consumes candidates with `depart ≤ getTime()+1` *before* stepping, so a
candidate with `depart == t` is inserted before the tick at t and the update only affects `depart ≥ t+1`.
Demonstrating input: the tick at t=60 (m: 1.0 → 0.95) cannot influence the candidate with `depart = 60`, only
those with `depart ≥ 61`. "Future insertions only" holds (plan:21), but the boundary is one second wide.
**Oct 5 impact:** none (≈1 s of demand; the same convention predates this commit).

### F8 — LOW. `--boundary-detector` selects the detector but the entry stays hard-coded

`citypulse/twin/service.py:35` (`BOUNDARY_ENTRY = "tko_insert"`), `:95-97`: the update always writes
`stream.m["tko_insert"]`. Demonstrating input: `--boundary-detector AID07106` (amendment) is correct only because
AID07106 still sits on the TKO entry; any future re-mapping (plan:73, "Missing observations do not trigger
dynamic re-selection") would silently assimilate the wrong entry. **Oct 5 impact:** none.

### F9 — LOW (harness, outside the listed files; note the file is being edited concurrently). Amended-arm scoring mask is a caller argument, not the default

**Caveat:** `citypulse/experiments/normal_assim_eval.py` is *uncommitted and was modified by another process
during this review* (211 insertions vs 721c043; mtime 20:30:43, line numbers below are from the working tree as
read). At commit 721c043 `compute_run_metrics` used the module constant `BOUNDARY_DETECTOR = "AID07105"` for both
the interior mask and the boundary sanity metric; the working-tree revision parameterises them
(`interior_exclude`, `boundary_detector`, now at `:284`/`:297`) but both still **default to the as-predeclared
mask** `(BOUNDARY_DETECTOR,)`. The amendment requires the mask to exclude **both** AID07105 and AID07106
(plan:81). Demonstrating input: scoring an amended (AID07106) run through the default call sites (or with
`--boundary-detector AID07106` but no explicit `interior_exclude`) counts the boundary detector as interior.
**Oct 5 impact:** none (no amended eval-seed run exists — `results/assim/eval_amend/` holds only a 900 s flag
smoke), but it would corrupt the amended comparison if the harness is reused without passing the two-detector
mask. The σ-existence guard at `:144` (F5) is still present in the working tree.

## The six questions, answered

1. **Update rule vs spec — matches, with one unstated reading.** Units: `PER_HOUR = 3600/30 = 120`
   (`assim.py:24-25,109-110`) ✔. Two-interval mean of counts ✔. `e_s = (q_b − q̂_b)/base_s(t)` in veh/h ✔
   (fixed point: m → q_b/base_s ✔). Deadband is `abs(r) <= delta → no update` (`:115`), i.e. update iff |r| > δ
   ✔ exactly as report2:249. Both clips ✔ (step ±0.05, then m ∈ [0.5, 1.8]). Gate uses the **observed**
   occupancy only (`:104`, never the Twin's) ✔. Missing/invalid handling ✔ (`valid=False`, null q/o on either
   side, absent detector, non-consecutive pair, non-positive base, missing/non-positive σ → `invalid`, m
   unchanged; `v` correctly not required). The only ambiguity is the mean-vs-per-interval occupancy gate (F6).
2. **Timing — correct.** Proxy emits at t = 30, 60, … (`proxy/service.py:63-68`, `sim.is_sensor_step`) and both
   worlds call the same `read_detectors` at the same sim time, which returns the same completed 30-s interval
   (`sim.py:183-197`); the tick pairs `h[0], h[1]` only when `h[1].t − h[0].t == 30.0` (`service.py:92`), so the
   observed and Twin readings are the same two intervals. Ticks fire every 60 s of sim time (`:89`), and the
   update lands after the stepping loop, so it affects only later insertions ✔ (F7 is the 1-s boundary).
3. **`base_s(t)` — right entry, right units, no `TWIN_CAND_SCALE` off-by-scale in steady state.**
   `base_rate` reads only the pool and divides by `scale = 1.5` (`demand_stream.py:61-71`); measured on the
   frozen pool: 8436 candidates / 7200 s × 3600 / 1.5 = **2812 veh/h ≈ TKO_IN_VPH = 2800** ✔, and
   `due()` accepts with p = m/1.5, so λ = m·base_s ✔. The scale error is *spatial, not global*: the window is
   truncated at the run edges (F3), and `base_s` is ignored anyway once the step clip binds (F1).
4. **CRN — intact except F2.** `u_n = default_rng(seed).random(len(cands))` indexed by `ptr`
   (`demand_stream.py:53,86-91`), so `due()` is a pure function of (seed, m path); `base_rate` never touches the
   pointer. Snapshot meta carries `m` and `stream_ptr` (`service.py:71-75`); the branch restores
   `stream.m = dict(meta.get("m") or {})` **before** `stream.seek(t0)` (`engine.py:62-64`), and `seek(t0)` is
   exactly the saved pointer (the loop consumes `depart ≤ getTime()`, and `seek` advances past `depart ≤ t0`) ✔.
   The one break is the pre-tick `m` in the meta at snapshot times that are ticks (F2: `na_1003` t=4200,
   `na_3003` t=3000 — 5% demand discontinuity vs the online continuation).
5. **`--assim off` — unchanged.** The 721c043 diff touches the off path only by adding `"m": dict(stream.m)`
   (empty → `{}`) to the snapshot meta and `"assim": "off"` to `twin_stats.json`; the whole assimilation block is
   behind `if assim_on` (`service.py:82`), σ is not read, and `engine.py:63` maps a pre-change snapshot's absent
   `m` to `{}` → multiplier 1.0. Independently confirmed by `results/assim/impl/report.md:43-54`: three off runs
   byte-identical (`twin_log.parquet` sha256 `ba03eea1…`). No issue found.
6. **Tests — see below.**

## Tests: what they fail to catch

`tests/test_assim.py` is 10 pure-unit tests; everything at the service/stream seam is untested.

- **T1. No service-level test at all.** The 60-s cadence (`service.py:89`), the 30-s pairing guard (`:92`), the
  `deque(maxlen=2)` window, "future insertions only", and the snapshot-vs-tick ordering (F2) have no test. A
  version with `h[0]`/`h[1]` swapped, or `% 30`, or the snapshot written after the tick, passes the suite.
- **T2. The tests' parameter regime hides F1.** They use `BASE = 1000–10,000` with `SIGMA = 100`
  (`tests/test_assim.py:16-17`), i.e. σ/base ≈ 0.01–0.1, so `test_sign_observation_above_twin_raises_m:34-39`
  exercises a proportional step (κ·e_s = 0.0072) that **cannot occur** in the frozen scenario (σ/base ≈ 0.19).
  No test pins the production regime where the deadband and the step clip interact — add e.g. base = 2812,
  σ = 533.736, resid = 534 → assert `delta == 0.05`.
- **T3. The Twin's occupancy is never the congested one.** `test_congested_gate_no_update:73-84` covers
  obs-congested/twin-free only; `tick(pair(50, o=5.0), pair(0, o=25.0))` (→ `updated` with the current code) is
  untested, so a bug gating on `twin_o` would pass.
- **T4. `base_rate` edge behaviour untested (F3).** `test_base_rate_from_candidate_list:136-155` samples t=450
  with the window [150, 750) fully inside the pool; `base_rate(..., 0.0)` / `(..., 870.0)` (1700 / 1432 veh/h
  vs 2812) are not covered, and the test's synthetic pool has no edge to expose the fixed denominator.
- **T5. Acceptance is never tested against `m` (F4).** The test asserts only that `base_rate` is m-invariant
  (`:152-155`); nothing checks `due()`'s thinning, so the m ≥ 1.5 saturation (m = 1.5/1.6/1.8 → identical 5862
  candidates) and the meaning of `m_max = 1.8` are invisible.
- **T6. No test of the branch restore or of the snapshot meta.** `engine.py:63` and `service.py:71-75` were
  verified by hand in `results/assim/impl/report.md:114-121`, not by a test; F2 was found only by comparing the
  frozen meta with the assim log.
- **T7. Small gaps in the invalid-path test (`:87-103`).** `base=None` is not covered (only `0.0`), nor is a σ
  JSON whose key is absent for the selected detector (F5), nor a pair straddling a gap (`h[1].t − h[0].t == 60`).
- **T8. `test_m_clip:65-70` asserts m = 1.8 is reachable** while the stream cannot realize m > 1.5 (F4) — the
  test gives confidence in a bound that is inert end-to-end.

## Bottom line

The update rule itself is a faithful transcription of report2 §G.3 / the plan, and `--assim off`, the interval
pairing, the 60-s cadence, and the CRN plumbing (seed-indexed `u`, `m` + pointer in the snapshot, branch restore)
are all correct. The substantive problems are behavioural and interpretive, not formula errors: **the predeclared
κ is inert because the deadband and the step clip make every update a fixed ±5% step (F1)**, `base_s(t)` is
mis-scaled at the run edges (F3), the snapshot `m` is one tick stale at tick-aligned snapshots (F2), a missing σ
silently turns NA into OL (F5), and the occupancy gate's two-interval mean — an unstated reading — is what let
54% of the Oct 5 updates through (F6). Of these, only **F6 would change the Oct 5 numbers** under the alternative
per-interval reading; F1 changes what those numbers mean; F2/F3/F4/F5 are latent and would bite the reserved
revision, the shock arm, or the §G.4 replay rather than the reported evaluation.

REPORT DONE
