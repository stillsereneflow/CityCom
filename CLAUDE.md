# CityCom project rules

## GPT-6 Astra is the decision-maker, never the implementer

GPT-6 Astra (codex, `codex exec -m gpt-6-astra`) is used **only for decisions and reviews**:
- consultation and design calls;
- adjudicating conflicting results;
- reviewing results that dsh / agy-flash have produced and I have already verified.

**Astra must never be given implementation work.** That includes:
- writing or editing code or scripts;
- building networks or demand;
- running simulations, sweeps or calibration loops;
- iterating until a criterion is met.

All of that goes to **dsh and agy**, and agy-flash takes part in every multi-piece task.

Before every Astra dispatch, check: **is this a decision or a review?** If the task builds, runs or iterates anything, it is not an Astra task.
- Write the spec, dispatch it to dsh / agy-flash, and verify the result myself.
- Then bring the verified results to Astra for the decision.
- Astra prompts stay short and bounded, read-only (`-s read-only`) whenever possible, and never include a "keep iterating" loop.

Why: on 2026-10-02 and 2026-10-03 Astra was given two implementation tasks: step-1 network repair, and the bounded-demand build with scoring and iteration. That spent the user's money on labour the execution tier should have done. The user stopped the second run and set this rule.
