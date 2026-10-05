"""Unit tests for the missing-queue runner: classification order and Delta_D (plan rev 2)."""
from pathlib import Path

import pandas as pd

from citypulse.experiments.missing_queue import (
    ARMS,
    classify_outcome,
    compute_plan_metrics,
)

SEEDS = [4301, 4302, 4303, 4304]


def queue_td(values, seeds=SEEDS):
    """values: {seed: (Q_proxy, Q_C, Q_H)} -> long queue table (seed, world, Q)."""
    rows = [{"seed": s, "world": w, "Q": float(v)}
            for s in seeds if s in values for w, v in zip(("proxy", "C", "H"), values[s])]
    return pd.DataFrame(rows)


def metrics(deltas, gates_ok=True, incomplete=None, seeds=SEEDS):
    return {"gates_ok": gates_ok, "incomplete_arms": incomplete or [], "seeds": list(seeds),
            "per_seed": [{"seed": s, "delta_D": d} for s, d in deltas.items()]}


def make_arm_metrics(seed, g_t, g_p, **extra):
    """Synthetic per-arm metrics bundle as returned by compute_variant_decision_metrics."""
    row = {"seed": seed, "a_star": "A3", "BEE_signed": 0.0, "Regret": 0.0, "top1_agree": 1.0,
           "spearman_rho": 1.0, "J_T_r2": {"A0": 100.0, "A3": 100.0 - g_t},
           "J_P_m2": {"A0": 100.0, "A3": 100.0 - g_p}}
    row.update(extra)
    return {"variant": "test", "per_seed": [row], "pooled": {}, "exclusions": {}}


# ---------------------------------------------------------------- classification order (step 1..6)
def test_step1_technical_gate_failure_or_incomplete_grid():
    q = queue_td({4301: (10, 2, 9), 4302: (10, 2, 9), 4303: (10, 2, 9), 4304: (10, 2, 9)})
    d = {s: -3.0 for s in SEEDS}

    res = classify_outcome(q, metrics(d, gates_ok=False))
    assert (res["label"], res["step"]) == ("inconclusive_technical", 1)
    assert res["inputs"]["step1"]["gates_ok"] is False

    # gates unknown (missing gates.json) is not a pass
    res = classify_outcome(q, metrics(d, gates_ok=None))
    assert res["step"] == 1

    res = classify_outcome(q, metrics(d, incomplete=["seed 4301 H-D: 29/30 ok rows"]))
    assert res["label"] == "inconclusive_technical"
    assert res["inputs"]["step1"]["incomplete_arms"] == ["seed 4301 H-D: 29/30 ok rows"]


def test_step1_missing_queue_or_delta_d_is_technical():
    q = queue_td({4301: (10, 2, 9), 4302: (10, 2, 9), 4303: (10, 2, 9)})   # 4304 missing
    res = classify_outcome(q, metrics({s: -3.0 for s in SEEDS}))
    assert res["step"] == 1 and res["inputs"]["step1"]["seeds_missing_queue"] == [4304]

    q_full = queue_td({s: (10, 2, 9) for s in SEEDS})
    res = classify_outcome(q_full, metrics({4301: -3.0, 4302: -3.0, 4303: -3.0, 4304: None}))
    assert res["step"] == 1 and res["inputs"]["step1"]["seeds_missing_delta_D"] == [4304]
    assert classify_outcome(None, metrics({s: -3.0 for s in SEEDS}))["step"] == 1


def test_step2_no_initial_deficit_and_precedence_over_support():
    # 3 of 4 seeds with Q_P - Q_C <= 5 (seed 4304 has a deficit); Delta_D would say "support"
    q = queue_td({4301: (10, 8, 20), 4302: (9, 8, 20), 4303: (8, 8, 20), 4304: (30, 8, 20)})
    res = classify_outcome(q, metrics({s: -3.0 for s in SEEDS}))
    assert (res["label"], res["step"]) == ("no_initial_deficit", 2)
    assert res["inputs"]["step2"]["n_no_deficit"] == 3
    assert res["inputs"]["step2"]["per_seed"][4304]["diff"] == 22.0
    # the later steps are not evaluated: the order stops at the first applicable step
    assert "step3" not in res["inputs"]


def test_step3_inconclusive_restoration():
    # All four seeds show a Proxy deficit, but only one restores material queue (>= 6)
    q = queue_td({4301: (30, 8, 20), 4302: (30, 8, 12), 4303: (30, 8, 11), 4304: (30, 8, 10)})
    res = classify_outcome(q, metrics({s: -3.0 for s in SEEDS}))
    assert (res["label"], res["step"]) == ("inconclusive_restoration", 3)
    assert res["inputs"]["step3"]["n_restored"] == 1
    assert res["inputs"]["step3"]["per_seed"][4301]["restored"] is True
    assert res["inputs"]["step3"]["per_seed"][4304]["proxy_deficit"] is True


def test_step3_ignores_restoration_without_a_proxy_deficit():
    # Restoration is large everywhere, but no seed has Q_P - Q_C > 5 -> step 2 already applies
    q = queue_td({s: (9, 8, 20) for s in SEEDS})
    res = classify_outcome(q, metrics({s: -3.0 for s in SEEDS}))
    assert res["step"] == 2


def test_step4_support():
    q = queue_td({s: (30, 8, 20) for s in SEEDS})
    res = classify_outcome(q, metrics({4301: -1.2, 4302: -2.0, 4303: -1.5, 4304: -0.9}))
    assert (res["label"], res["step"]) == ("support", 4)
    assert res["inputs"]["step4"]["n_negative"] == 4
    assert abs(res["inputs"]["step4"]["mean_delta_D"] - (-1.4)) < 1e-9


def test_step4_needs_both_the_seed_count_and_the_mean():
    q = queue_td({s: (30, 8, 20) for s in SEEDS})
    # 3 of 4 negative but mean -0.8 > -1.0 -> not support; refutation needs mean > -0.5 -> partial
    res = classify_outcome(q, metrics({4301: -2.0, 4302: -0.4, 4303: -0.3, 4304: -0.5}))
    assert res["step"] == 6 and res["label"] == "partial"


def test_step5_refutation_by_seed_count_or_by_mean():
    q = queue_td({s: (30, 8, 20) for s in SEEDS})
    res = classify_outcome(q, metrics({4301: 0.5, 4302: 0.0, 4303: 1.2, 4304: -3.0}))
    assert (res["label"], res["step"]) == ("refutation", 5)
    assert res["inputs"]["step5"]["n_non_negative"] == 3
    # mean-only branch: one non-negative seed but mean Delta_D > -0.5
    res = classify_outcome(q, metrics({4301: -0.4, 4302: -0.3, 4303: -0.2, 4304: -0.1}))
    assert res["step"] == 5 and res["inputs"]["step5"]["n_non_negative"] == 0


def test_step6_partial():
    q = queue_td({s: (30, 8, 20) for s in SEEDS})
    res = classify_outcome(q, metrics({4301: -2.0, 4302: -0.6, 4303: -0.6, 4304: -0.6}))
    assert (res["label"], res["step"]) == ("partial", 6)
    assert res["inputs"]["step6"]["applies"] is True


# ------------------------------------------------------------------------------- Delta_D and plan
def test_delta_d_and_duration_contrast():
    arm_metrics = {
        "C-P": make_arm_metrics(4301, g_t=1.0, g_p=5.0),
        "C-D": make_arm_metrics(4301, g_t=0.5, g_p=5.0),
        "H-P": make_arm_metrics(4301, g_t=4.0, g_p=5.0),
        "H-D": make_arm_metrics(4301, g_t=5.0, g_p=5.0),
    }
    row = compute_plan_metrics(arm_metrics, [4301])[0]
    assert abs(row["G_P_A3"] - 5.0) < 1e-9
    assert abs(row["e_C-D"] - 4.5) < 1e-9          # |0.5 - 5.0|
    assert abs(row["e_H-D"] - 0.0) < 1e-9          # |5.0 - 5.0|
    assert abs(row["delta_D"] - (-4.5)) < 1e-9     # e(H-D) - e(C-D)
    assert abs(row["duration_contrast_C"] - 0.5) < 1e-9   # G_T(C-P) - G_T(C-D)
    assert abs(row["duration_contrast_H"] - (-1.0)) < 1e-9
    assert row["a_star_C-P"] == "A3" and row["top1_agree_H-D"] == 1.0


def test_delta_d_none_when_an_arm_is_incomplete():
    arm_metrics = {"C-P": make_arm_metrics(4301, 1.0, 5.0), "C-D": make_arm_metrics(4301, 0.5, 5.0),
                   "H-P": make_arm_metrics(4301, 4.0, 5.0), "H-D": {"per_seed": [], "pooled": {}}}
    row = compute_plan_metrics(arm_metrics, [4301])[0]
    assert row["G_T_A3_H-D"] is None and row["e_H-D"] is None
    assert row["delta_D"] is None and row["duration_contrast_H"] is None


def test_arm_spec_covers_all_four_arms():
    assert set(ARMS) == {"C-P", "C-D", "H-P", "H-D"}
    assert (Path(__file__).resolve().parents[1] / "citypulse" / "experiments"
            / "missing_queue.py").exists()
