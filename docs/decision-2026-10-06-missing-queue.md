# Decision 2026-10-06: missing-queue result, claim wording, freeze

Ruling: `~/.claude/runs/D--CityCom/20261006-0000-codex-sol-mqresult/out.md` (Codex, read-only). Cross-family opinion: `~/.claude/runs/D--CityCom/20261006-0001-agypro-mqresult/out.log` (agy-pro). Results: `results/missing_queue/` (816829c), plan `docs/oct11-missing-queue-plan.md` rev 2.

## Result (verified by Claude from raw rows and saved states)

- Classification under the preregistered order: **Support** (step 4). Gates G1–G3 pass on all four seeds; 720/720 branches ok.
- Q at t_d: Proxy 55/7/40/25, conventional Twin C 0 on all seeds, historical replay H 14/15/17/19.
- Δ_D = e(H-D) − e(C-D) per seed: −4.58/−3.25/−3.06/−2.17, mean −3.27 veh·h. Mean fixed-A3 absolute gain error under truth-assisted clearance: 4.16 (C-D) → 0.90 (H-D).
- Duration contrast Ĝ(A3; persistent) − Ĝ(A3; clears 5,400): under C 6.0–7.7, under H 1.4–3.0.
- H-D Spearman 0.2/−0.1/−0.1/0.8. The full-action ranking did not improve.

## Claim wording (blocking for the submission)

> In a preregistered four-seed offline diagnostic, replaying incident history reduced fixed-A3 absolute gain error under truth-assisted clearance from a mean 4.16 to 0.90 veh·h. All four paired contrasts improved. History also reduced the dependence on the persistent-duration belief, supporting an inherited-state explanation for the conventional Twin's duration sensitivity.

- Report all per-seed values. N = 4 is descriptive: no inferential significance.
- H changes the whole inherited state (vehicle distribution, positions, speeds), not only Q. Blocker stopping lagged the requested onset by 3–25 s.
- **Not claimed:** queue count as the sole cause; exact state recovery (on seed 4302, Q_H 15 > Q_P 7, and H holds fewer vehicles on `ktb_n1` than the Proxy); deployability; reliable inference; accurate online benefits; general superiority; improved full-action ranking.
- Interpretation, phrased as such: "The good baseline decision agreement is consistent with compensating errors: the persistent future-blockage belief partly offsets the missing incident history." Not "proved right for the wrong reason".
- **BEE +1.63 veh·h [1.04, 2.22] is retained unchanged** (blocking), labelled as the eight-seed, as-run conventional hypothesis-world audit, beside its good ranking and low regret. No correction factor: do not subtract the 0.18 floor or Δ_D, and do not pool experiments.

## Freeze

- The conventional Twin stays the audited object. R_E, the onset rule and the thresholds are frozen on 2026-10-16. H is not promoted into the method, and no H grid is added before the results freeze.
- The frozen-audit preregistration (before Oct 16–18 collection) must fix the configuration, fresh seeds, estimands and claim boundary. It adds a **descriptive** state-history check from saved snapshots: incident-history status, Q components and pending counts, vehicle occupancy at t_d, and actual branch placement and clearance. This check must not select seeds, tune the method or gate publication.
- Done 2026-10-06 (Codex's blocking item for any future -D reuse): `audit_engine._twin_audit_worker` now fails a branch with `clear_failed` when a blocker is missing at clearance or `resume()` raises. Previously only a resumed blocker that stayed stopped failed. A stored C-D row re-ran identically.

## Peer disagreement

agy-pro read the -P/-D arms as immediate vs delayed *actions*; they are persistent vs clearing *duration beliefs*. Its claim wording and its development-run checklist rest on that misreading and were not adopted. Codex's ruling stands.
