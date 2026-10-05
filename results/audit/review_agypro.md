MODEL: Gemini 3.1 Pro (High)

# Code Review: Offline Decision Audit Harness

Here are the findings based on the provided specifications, ranked by severity.

## 1. Twin ignores autonomous rerouting (BEE Inflation)
**Severity:** Critical
**Status:** **blocking**
**File:** `citypulse/sim.py:166` vs `173`
**Issue:** `twin_cmd` does not include the `--device.rerouting.probability` arguments, whereas `proxy_cmd` (via `reroute_enabled()`) applies a 30% rerouting probability. The Twin branch simulates with 0% autonomous rerouting, while the Proxy branch simulates with 30%. This massively inflates the Twin's predicted delay for A0 and the predicted gain `g_t_hat` for interventions, providing a direct explanation for `BEE = +1.63 veh·h`.

## 2. Incident duration mismatch (BEE Inflation)
**Severity:** Critical
**Status:** **blocking**
**File:** `citypulse/branching/audit_engine.py:276` and `372`
**Issue:** The Twin branch explicitly applies the hypothetical blockage (`hyp_blocker_0/1`) with `duration=3600.0`, meaning the Twin assumes the incident will persist for the entire 900s evaluation horizon. In contrast, the Proxy branch clears the incident natively at `t=5400.0` (only 300s into the horizon) by explicitly calling `tc.vehicle.resume()`. This mismatch heavily overestimates the expected delay in the Twin, artificially inflating BEE.

## 3. Proxy silently drops pre-snapshot ControlState
**Severity:** High
**Status:** **blocking**
**File:** `citypulse/branching/audit_engine.py:362`
**Issue:** SUMO's `loadState` is known to drop lane closures and maxspeed. The Twin branch correctly works around this by deserializing and re-applying `meta["control_state"]`. However, `_proxy_audit_worker` initializes a fresh, empty `ControlState()` and does not have a mechanism to re-apply prior actions. Any control actions (e.g. VMS, lane closures) ordered by the Twin before `t=5100` are silently dropped in the Proxy evaluation.

## 4. Split Regret evaluation uses M1 oracle instead of M2 optimum
**Severity:** High
**Status:** **blocking**
**File:** `citypulse/experiments/decision_audit.py:495`
**Issue:** Split Regret is computed as `j_p_m2[a_star] - j_p_m2[oracle]`, and its denominator as `j_p_m2["A0"] - j_p_m2[oracle]`. Because `oracle` is selected on M1, it is not guaranteed to be the best action on M2. This means `j_p_m2[oracle]` can be worse than `a_star` or `A0`, leading to negative regret, negative denominators, and incorrectly discarded metrics (because `denom >= 0.5` becomes False). The true Regret on the evaluation set should be compared against the hindsight optimum on M2: `j_p_m2.min()`.

REPORT DONE
