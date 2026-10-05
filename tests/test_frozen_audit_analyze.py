"""Unit tests for the frozen audit analyzer (docs/oct16-frozen-audit-plan.md)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from citypulse.experiments.frozen_audit_analyze import (
    CLAIM_BOUNDARY,
    PRIMARY_BELIEF,
    SECONDARY_BELIEF,
    analyze,
    clearance_ok,
    compute_belief,
    main,
    normalize_raw,
    seed_metrics,
    state_history_summary,
    summarize,
    validate_world,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ("A0", "A1", "A2", "A3", "A4")
REPS = {"twin": (1, 2, 3, 4, 5, 6), "proxy": (1, 2, 3, 4, 5, 6), "calibration": (7, 8, 9, 10, 11, 12)}
TWIN_J = {"A0": 100.0, "A1": 99.0, "A2": 98.0, "A3": 90.0, "A4": 95.0}
PROXY_J = {"A0": 100.0, "A1": 102.0, "A2": 97.0, "A3": 99.0, "A4": 104.0}
CAL_J = {"A0": 100.0, "A1": 101.0, "A2": 96.0, "A3": 98.0, "A4": 103.0}


def make_rows(world, seed, j_map=TWIN_J, belief=PRIMARY_BELIEF, status="ok", extra=None):
    rows = []
    for r in REPS[world]:
        for a in ACTIONS:
            row = {"world": world, "belief": belief, "seed": seed, "replication": r, "action": a,
                   "J": float(j_map[a]), "veh_digest": f"{world}-{seed}-{r}-{a}", "status": status}
            row.update(extra or {})
            rows.append(row)
    return rows


def make_dataset(seeds=(4501, 4502), belief=PRIMARY_BELIEF, extra=None):
    rows = []
    for s in seeds:
        rows += make_rows("twin", s, belief=belief, extra=extra)
        rows += make_rows("proxy", s, j_map=PROXY_J)
        rows += make_rows("calibration", s, j_map=CAL_J)
    return normalize_raw(pd.DataFrame(rows))


def make_pivot(j_map, reps=(1, 2, 3, 4, 5, 6)):
    n = len(reps)
    return pd.DataFrame({a: ([v] * n if not isinstance(v, list) else v) for a, v in j_map.items()},
                        index=list(reps))


def test_claim_boundary_is_verbatim_from_the_plan():
    plan = (REPO_ROOT / "docs" / "oct16-frozen-audit-plan.md").read_text(encoding="utf-8")
    assert CLAIM_BOUNDARY in plan


def test_validate_world_complete_grid():
    df = make_dataset()
    records, complete = validate_world(df, PRIMARY_BELIEF, "twin", [4501, 4502])
    assert complete == [4501, 4502]
    assert records[4501]["complete"] and records[4501]["n_ok"] == 30
    assert records[4501]["reason"] is None


@pytest.mark.parametrize("mutate,needle", [
    (lambda df: df.drop(df[(df["world"] == "twin") & (df["seed"] == 4501) & (df["action"] == "A2")
                           & (df["replication"] == 4)].index), "incomplete twin grid"),
    (lambda df: df.assign(status=np.where((df["world"] == "twin") & (df["action"] == "A0"), "error", "ok")),
     "incomplete twin grid"),
    (lambda df: df.assign(J=np.where((df["world"] == "twin") & (df["action"] == "A1"), np.nan, df["J"])),
     "incomplete twin grid"),
])
def test_validate_world_excludes_incomplete_grids(mutate, needle):
    df = normalize_raw(mutate(make_dataset()))
    records, complete = validate_world(df, PRIMARY_BELIEF, "twin", [4501, 4502])
    assert 4501 not in complete
    assert needle in records[4501]["reason"]


def test_validate_world_duplicate_keys():
    df = make_dataset(seeds=(4501,))
    exact = pd.concat([df, df[df["world"] == "twin"].head(1)], ignore_index=True)
    records, complete = validate_world(normalize_raw(exact), PRIMARY_BELIEF, "twin", [4501])
    assert complete == [] and records[4501]["reason"] == "duplicate (action, replication) keys"

    conflicting = pd.concat([df, df[df["world"] == "twin"].head(1).assign(J=123.0)], ignore_index=True)
    records, complete = validate_world(normalize_raw(conflicting), PRIMARY_BELIEF, "twin", [4501])
    assert complete == [] and "conflicting J" in records[4501]["reason"]


def test_d300_clearance_evidence_is_a_technical_failure_when_missing():
    ok_extra = {"actual_clear_time": 5400.0, "blocker_pos_0": 755.3, "blocker_pos_1": 755.3,
                "blocker_edge": "ktb_n1"}
    df = make_dataset(seeds=(4501,), belief=SECONDARY_BELIEF, extra=ok_extra)
    _, complete = validate_world(df, SECONDARY_BELIEF, "twin", [4501], require_clearance=True)
    assert complete == [4501]

    for bad in ({"actual_clear_time": None}, {"actual_clear_time": 5300.0},
                {"blocker_pos_0": None},
                {"blocker_release_0": '{"released": false}', "blocker_release_1": '{"released": true}'}):
        extra = dict(ok_extra)
        extra.update(bad)
        bad_df = make_dataset(seeds=(4501,), belief=SECONDARY_BELIEF, extra=extra)
        records, complete = validate_world(bad_df, SECONDARY_BELIEF, "twin", [4501], require_clearance=True)
        assert complete == [], bad
        assert "technical failure: clearance evidence" in records[4501]["reason"]

    released = {"actual_clear_time": 5400.0, "blocker_pos_0": 755.3, "blocker_pos_1": 755.3,
                "blocker_release_0": '{"released": true, "checked_at": 5401.0}',
                "blocker_release_1": '{"released": true, "checked_at": 5401.0}'}
    good = make_dataset(seeds=(4501,), belief=SECONDARY_BELIEF, extra=released)
    assert validate_world(good, SECONDARY_BELIEF, "twin", [4501], require_clearance=True)[1] == [4501]
    assert clearance_ok(pd.Series(released))[0] is True
    assert clearance_ok(pd.Series({"actual_clear_time": 5400.0}))[0] is True


def test_regret_rel_denominator_rule():
    tw = make_pivot(TWIN_J)
    # M1 selects A2 (80) as oracle; M2: A2 = 97, a* = A3 = 99 -> Regret 2, denom 3.0 >= 0.5.
    px = make_pivot({"A0": 100.0, "A1": 102.0, "A2": [80.0, 80.0, 80.0, 97.0, 97.0, 97.0],
                     "A3": [99.0] * 6, "A4": 104.0})
    row = seed_metrics(tw, px, None)
    assert row["a_star"] == "A3" and row["oracle"] == "A2"
    assert abs(row["Regret"] - 2.0) < 1e-9 and abs(row["Regret_denom"] - 3.0) < 1e-9
    assert abs(row["Regret_rel"] - 2.0 / 3.0) < 1e-9

    # M2: A2 = 99.8, a* = A3 = 99.9 -> Regret 0.1, denom 0.2 < 0.5 -> not reported.
    px_small = make_pivot({"A0": 100.0, "A1": 102.0, "A2": [80.0, 80.0, 80.0, 99.8, 99.8, 99.8],
                           "A3": [99.9] * 6, "A4": 104.0})
    row_small = seed_metrics(tw, px_small, None)
    assert abs(row_small["Regret_denom"] - 0.2) < 1e-9
    assert row_small["Regret_rel"] is None

    # Unsplit rule: A2 = 99.8 in every replication -> all-replication denominator 0.2 < 0.5.
    px_unsplit = make_pivot({"A0": 100.0, "A1": 102.0, "A2": 99.8, "A3": 99.9, "A4": 104.0})
    row_unsplit = seed_metrics(tw, px_unsplit, None)
    assert abs(row_unsplit["Regret_denom_unsplit"] - 0.2) < 1e-9
    assert row_unsplit["Regret_rel_unsplit"] is None
    assert row_unsplit["Regret_rel"] is None


def test_seed_metrics_unsplit_and_calibration_floor():
    tw = make_pivot(TWIN_J)
    px = make_pivot(PROXY_J)
    cal = make_pivot(CAL_J, reps=(7, 8, 9, 10, 11, 12))
    row = seed_metrics(tw, px, cal)
    assert row["BEE_signed"] == pytest.approx(row["G_T_hat"] - row["G_P"])
    assert row["BEE_abs"] == pytest.approx(abs(row["BEE_signed"]))
    assert row["a_star_floor"] == "A2"
    assert row["BEE_floor_abs"] == pytest.approx(abs(row["BEE_floor_signed"]))
    assert seed_metrics(tw, px, None)["BEE_floor_abs"] is None


def test_summarize_omits_intervals_when_n_lt_2():
    one = summarize([1.5], [4501], {"proxy: incomplete proxy grid": [4502]})
    assert one["n"] == 1 and one["mean"] == 1.5
    assert one["ci95_t"] is None and one["ci95_boot"] is None
    two = summarize([1.0, 3.0], [4501, 4502], {})
    assert two["n"] == 2 and two["ci95_t"] == pytest.approx([-10.7062, 14.7062], abs=1e-3)
    assert two["ci95_boot"] is not None and two["ci95_t"][0] <= two["mean"] <= two["ci95_t"][1]
    empty = summarize([None, float("nan")], [], {})
    assert empty["n"] == 0 and empty["mean"] is None


def test_compute_belief_reports_exclusions_by_reason():
    df = make_dataset()
    block = compute_belief(df, PRIMARY_BELIEF, [4501, 4502])
    assert block["n_complete_seeds"] == 2 and block["complete_seeds"] == [4501, 4502]
    assert block["pooled"]["BEE_signed"]["n"] == 2

    broken = df.drop(df[(df["world"] == "proxy") & (df["seed"] == 4502) & (df["action"] == "A4")
                        & (df["replication"] == 6)].index)
    block = compute_belief(normalize_raw(broken), PRIMARY_BELIEF, [4501, 4502])
    assert block["complete_seeds"] == [4501]
    excl = block["pooled"]["BEE_signed"]["exclusions"]
    assert any("4502" in str(v) and "proxy" in k for k, v in excl.items())
    assert block["pooled"]["BEE_signed"]["n"] == 1
    assert block["pooled"]["BEE_signed"]["ci95_t"] is None


def test_state_history_pending_unknown_never_zero():
    state = pd.DataFrame([{"world": "proxy", "seed": 4501, "t": 5100.0, "halted_q": 3,
                           "pending_total": None, "pending_q": np.nan, "Q": None,
                           "halted_q_by_edge": '{"ktb_w1": 3}'}])
    summary = state_history_summary(state)
    assert summary["available"] is True and summary["n_rows"] == 1
    row = summary["rows"][0]
    assert row["pending_total"] == "unknown" and row["pending_q"] == "unknown" and row["Q"] == "unknown"
    assert row["halted_q"] == 3 and row["halted_q_by_edge"] == {"ktb_w1": 3}
    missing = state_history_summary(None)
    assert missing["available"] is False and "unknown" in missing["note"]


def test_analyze_writes_outputs_and_never_subtracts_the_floor(tmp_path):
    df = make_dataset()
    df.to_parquet(tmp_path / "raw.parquet")
    pd.DataFrame([{"world": "proxy", "seed": 4501, "t": 5100.0, "pending_total": None, "Q": None}]
                 ).to_parquet(tmp_path / "state_history.parquet")
    (tmp_path / "rng_check.json").write_text('{"passed": true}', encoding="utf-8")

    bundle = analyze(tmp_path)
    assert bundle["n_seeds"] == 2 and bundle["primary"]["n_complete_seeds"] == 2
    assert (tmp_path / "metrics.json").exists() and (tmp_path / "report.md").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert CLAIM_BOUNDARY in report
    assert "never subtracted from BEE" in report
    assert not any("gap" in k for k in bundle["primary"]["pooled"])
    assert "BEE_floor_abs" in bundle["primary"]["pooled"]
    assert main(["analyze", "--dir", str(tmp_path)]) == 0
