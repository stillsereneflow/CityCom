"""Unit tests for citypulse.experiments.mq_replay pure logic."""
from pathlib import Path
import pandas as pd
import pytest

from citypulse.experiments.mq_replay import (
    aggregate_q_counts,
    build_m_schedule,
    regenerate_twin_demand,
    TWIN_CAND_ROU,
)

Q_EDGES = ["ktb_w1", "ktb_w2", "ktb_w3", "ktb_n1"]
UPSTREAM_EDGES = ["tko_vms", "tko_1", "tko_in", "tko_insert", "on_ktb_w1", "on_tko_vms", "on_tko_1"]
EXTRA_EDGES = ["ms_on_ktb_w2", "on_ktb_w3", "on_ktb_n1"]


def test_build_m_schedule():
    data = [
        {"t": 4200.0, "m": 1.0},
        {"t": 4440.0, "m": 1.1},
        {"t": 4500.0, "m": 1.2},
        {"t": 4800.0, "m": 1.3},
        {"t": 5100.0, "m": 1.4},
        {"t": 5400.0, "m": 1.5},
    ]
    df = pd.DataFrame(data)
    sched = build_m_schedule(df)

    assert 4200.0 not in sched
    assert 4440.0 not in sched
    assert 4500.0 in sched and sched[4500.0] == 1.2
    assert 4800.0 in sched and sched[4800.0] == 1.3
    assert 5100.0 in sched and sched[5100.0] == 1.4
    assert 5400.0 not in sched
    assert len(sched) == 3


def test_submission_regeneration():
    sched = {4500.0: 1.15, 4800.0: 1.25, 5100.0: 1.30}
    ins1, ptr1, m1 = regenerate_twin_demand(
        seed=202,
        path=TWIN_CAND_ROU,
        base_factor=0.85,
        t_start=4440.0,
        t_end=5100.0,
        m_schedule=sched,
    )
    ins2, ptr2, m2 = regenerate_twin_demand(
        seed=202,
        path=TWIN_CAND_ROU,
        base_factor=0.85,
        t_start=4440.0,
        t_end=5100.0,
        initial_ptr=None,
        m_schedule=sched,
    )
    assert ins1 == ins2
    assert ptr1 == ptr2
    assert m1 == m2
    assert len(ins1) > 0
    assert m1.get("tko_insert") == 1.30

    for vid, dep, step in ins1:
        assert isinstance(vid, str)
        assert dep <= float(step)
        assert 4441 <= step <= 5100


def test_q_aggregation_excluding_blockers():
    vehicles = [
        # Ordinary halted on Q edges
        ("v1", "ktb_w1", 0.05),
        ("v2", "ktb_w2", 0.00),
        ("v3", "ktb_n1", 0.09),
        # Moving on Q edges (speed >= 0.1, not counted)
        ("v4", "ktb_n1", 0.10),
        ("v5", "ktb_w3", 15.0),
        # Blocker vehicles on Q edge (speed 0.0, must be EXCLUDED by hyp_ prefix)
        ("hyp_blocker_0", "ktb_n1", 0.0),
        ("hyp_blocker_1", "ktb_n1", 0.0),
        ("hyp_extra", "ktb_w2", 0.0),
        # Proxy incident vehicles are blockers too
        ("incident_0", "ktb_n1", 0.0),
        ("incident_1", "ktb_n1", 0.0),
        # Upstream spillback halted (speed < 0.1, not in Q)
        ("v_up1", "tko_vms", 0.0),
        ("v_up2", "tko_1", 0.08),
        # Extra descriptive halted (speed < 0.1, not in Q)
        ("v_ex1", "ms_on_ktb_w2", 0.0),
    ]

    pending_vehicles = ["p1", "p2", "p3"]
    pending_routes = {
        "p1": ["tko_insert", "tko_in", "tko_1", "tko_vms", "ktb_w1", "ktb_w2", "out"],  # traverses ktb_w1, ktb_w2 (Q)
        "p2": ["x1_in", "x1_out"],  # does not traverse Q edges
        "p3": ["tko_insert", "ktb_n1", "out"],  # traverses ktb_n1 (Q)
    }

    counts = aggregate_q_counts(
        vehicles=vehicles,
        q_edges=Q_EDGES,
        upstream_edges=UPSTREAM_EDGES,
        extra_edges=EXTRA_EDGES,
        pending_vehicles=pending_vehicles,
        pending_routes=pending_routes,
    )

    # Q edge halted counts
    assert counts["ktb_w1"] == 1
    assert counts["ktb_w2"] == 1
    assert counts["ktb_w3"] == 0
    assert counts["ktb_n1"] == 1  # only v3; hyp_blocker_0/1 excluded!
    halted_q = 1 + 1 + 0 + 1  # 3

    # Upstream and extra counts
    assert counts["tko_vms"] == 1
    assert counts["tko_1"] == 1
    assert counts["ms_on_ktb_w2"] == 1

    # Pending Q count
    assert counts["pending_q"] == 2  # p1 and p3

    # Total Q
    assert counts["Q"] == halted_q + 2  # 5
