"""Pure unit tests for normal-mode assimilation (report2 §G.3). No SUMO, no run files.

Each case fixes one clause of the spec: deadband, step clip, m clip, congested gate, invalid or
missing data, the sign of the update and the counts-per-30-s -> veh/h conversion.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from citypulse.twin.assim import NormalAssimilator, PER_HOUR, Interval  # noqa: E402
from citypulse.twin.demand_stream import TwinDemandStream  # noqa: E402

BASE = 1000.0        # veh/h
SIGMA = 100.0        # veh/h


def iv(q, o=5.0, v=50.0, valid=True):
    return {"q": q, "v": v, "o": o, "valid": valid}


def pair(q, o=5.0, valid=True):
    return [iv(q, o, valid=valid), iv(q, o, valid=valid)]


def tick(obs, twin, m=1.0, base=BASE, sigma=SIGMA, t=60.0, **kw):
    return NormalAssimilator(**kw).update(t, obs, twin, base, m, sigma_q=sigma)


def test_sign_observation_above_twin_raises_m():
    """obs > twin -> e_s > 0 -> m up; obs < twin -> m down (symmetric)."""
    m_up, row_up = tick(pair(10), pair(8), base=10_000.0)
    assert row_up["reason"] == "updated" and row_up["e_s"] > 0 and m_up > 1.0
    m_dn, row_dn = tick(pair(8), pair(10), base=10_000.0)
    assert row_dn["reason"] == "updated" and row_dn["e_s"] < 0 and m_dn < 1.0
    assert m_up == pytest.approx(1.0 + 0.3 * row_up["e_s"])       # inside the step clip
    assert m_dn == pytest.approx(1.0 + 0.3 * row_dn["e_s"])


def test_deadband_no_update():
    """|r| <= delta = 1 sigma -> m unchanged, reason deadband (delta is a strict threshold)."""
    # 9 - 8 = 1 vehicle per 30 s = 120 veh/h; with sigma = 120 veh/h, r = 1.0 exactly
    m_edge, row_edge = tick(pair(9), pair(8), sigma=120.0)
    assert row_edge["r"] == pytest.approx(1.0) and row_edge["reason"] == "deadband"
    assert m_edge == 1.0 and row_edge["m"] == 1.0
    m_tiny, row_tiny = tick(pair(8), pair(8))
    assert row_tiny["reason"] == "deadband" and row_tiny["e_s"] == 0.0 and m_tiny == 1.0
    # just outside the deadband -> update
    _, row_out = tick(pair(9), pair(8), sigma=119.0)
    assert row_out["reason"] == "updated"


def test_step_clip_at_five_percent():
    """|clip(kappa * e_s)| <= 0.05: a large residual still moves m by at most 5% per tick."""
    m_new, row = tick(pair(50), pair(0))          # huge positive residual
    assert row["delta"] == pytest.approx(0.05)
    assert m_new == pytest.approx(1.05)
    m_dn, row_dn = tick(pair(0), pair(50))
    assert row_dn["delta"] == pytest.approx(-0.05)
    assert m_dn == pytest.approx(0.95)


def test_m_clip():
    """m stays inside [0.5, 1.8]."""
    m_hi, row_hi = tick(pair(50), pair(0), m=1.79)
    assert m_hi == 1.8 and row_hi["reason"] == "updated"
    m_lo, row_lo = tick(pair(0), pair(50), m=0.51)
    assert m_lo == 0.5 and row_lo["reason"] == "updated"


def test_congested_gate_no_update():
    """o >= o_crit (15%) -> no update, reason congested (even with a large residual)."""
    m_new, row = tick(pair(50, o=15.0), pair(0))
    assert m_new == 1.0 and row["reason"] == "congested" and row["delta"] is None
    m_new2, row2 = tick(pair(50, o=22.5), pair(0))
    assert m_new2 == 1.0 and row2["reason"] == "congested"
    # one interval above the threshold is enough (the two intervals are averaged)
    m_new3, row3 = tick([iv(50, 10.0), iv(50, 20.0)], pair(0))
    assert m_new3 == 1.0 and row3["reason"] == "congested"
    # just below -> normal update
    m_new4, row4 = tick(pair(50, o=14.9), pair(0))
    assert row4["reason"] == "updated" and m_new4 > 1.0


def test_invalid_or_missing_data_no_update():
    """valid=False, None fields, a missing detector or a missing interval -> no update."""
    assert tick(pair(50, valid=False), pair(0))[1]["reason"] == "invalid"
    assert tick(pair(50), pair(0, valid=False))[1]["reason"] == "invalid"
    assert tick([iv(None), iv(50)], pair(0))[1]["reason"] == "invalid"
    assert tick(pair(50), [iv(50), iv(None)])[1]["reason"] == "invalid"
    assert tick(pair(50), [iv(50), {"q": 0, "v": None, "o": None, "valid": True}])[1]["reason"] == "invalid"
    m_new, row = tick(None, pair(0))
    assert (m_new, row["reason"], row["e_s"]) == (1.0, "invalid", None)
    m_new, row = tick([iv(50)], pair(0))           # only one interval
    assert (m_new, row["reason"]) == (1.0, "invalid")
    m_new, row = tick([iv(50), None], pair(0))     # detector absent from the SensorMsg
    assert (m_new, row["reason"]) == (1.0, "invalid")
    # missing / non-positive sigma or base rate: e_s is undefined, so no update
    assert tick(pair(50), pair(0), sigma=None)[1]["reason"] == "invalid"
    assert tick(pair(50), pair(0), sigma=0.0)[1]["reason"] == "invalid"
    assert tick(pair(50), pair(0), base=0.0)[1]["reason"] == "invalid"


def test_unit_conversion_counts_per_30s_to_vehph():
    """q counts per 30-s interval become veh/h x120 and the two intervals are averaged."""
    assert PER_HOUR == 120.0
    m_new, row = tick(pair(10), pair(8))                 # 1200 - 960 = 240 veh/h
    assert row["e_s"] == pytest.approx(240.0 / BASE)
    assert row["r"] == pytest.approx(240.0 / SIGMA)
    # 10 and 14 vehicles -> mean 12 per 30 s -> 1440 veh/h
    m_new, row = tick([iv(10), iv(14)], pair(8))
    assert row["e_s"] == pytest.approx((1440.0 - 960.0) / BASE)
    # one vehicle per 30 s is 120 veh/h, not 1
    _, row1 = tick(pair(1), pair(0), sigma=1.0)
    assert row1["e_s"] == pytest.approx(120.0 / BASE)


def test_row_fields_and_reasons():
    """Every tick returns the logged row: t, e_s, r, delta, m, reason."""
    _, row = tick(pair(10), pair(8), t=120.0)
    assert set(row) == {"t", "e_s", "r", "delta", "m", "reason"}
    assert row["t"] == 120.0
    assert row["reason"] in ("updated", "deadband", "congested", "invalid")


def test_interval_dataclass_accepted():
    """The assimilator accepts Interval objects as well as mappings."""
    m_new, row = NormalAssimilator().update(
        60.0, [Interval(q=10, o=5), Interval(q=10, o=5)], [Interval(q=8, o=5), Interval(q=8, o=5)],
        BASE, 1.0, sigma_q=SIGMA)
    assert row["reason"] == "updated" and m_new > 1.0


def test_base_rate_from_candidate_list(tmp_path):
    """base_s(t): candidate rate over +/- 5 min / pool scale, reading only the candidate list."""
    xml = tmp_path / "cand.rou.xml"
    rows = []
    for i in range(30):        # 30 TKO candidates, one per 30 s from 0 to 870 s
        rows.append(f'<vehicle id="t{i}" depart="{i * 30.0}" type="tdist">'
                    f'<route edges="tko_insert tko_in out"/></vehicle>')
    for i in range(10):        # 10 cross-street candidates, same span
        rows.append(f'<vehicle id="x{i}" depart="{i * 90.0}" type="tdist">'
                    f'<route edges="x2_in x2_out"/></vehicle>')
    xml.write_text("<routes>\n" + "\n".join(rows) + "\n</routes>\n", encoding="utf-8")
    stream = TwinDemandStream(seed=202, path=xml, scale=1.5)
    # t=450: window [150, 750) holds 20 TKO candidates -> 20 / 600 s * 3600 / 1.5 = 80 veh/h
    assert stream.base_rate("tko_insert", 450.0) == pytest.approx(80.0)
    assert stream.base_rate("x2_in", 450.0) == pytest.approx(7 / 600.0 * 3600 / 1.5)
    assert stream.base_rate("tko_insert", 450.0, window=60.0) == pytest.approx(4 / 120.0 * 3600 / 1.5)
    # the rate is a property of the pool only: m does not change it
    stream.m["tko_insert"] = 1.8
    assert stream.base_rate("tko_insert", 450.0) == pytest.approx(80.0)
    assert stream.base_rate("tko_insert", 450.0) * 600.0 / 3600.0 * stream.scale == pytest.approx(20.0)
