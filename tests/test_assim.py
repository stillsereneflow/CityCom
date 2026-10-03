"""Pure unit tests for normal-mode assimilation (report2 §G.3) and NA-300.

Each case fixes one clause of the spec: deadband, step clip, m clip, congested gate, invalid or
missing data, the sign of the update and the counts-per-30-s -> veh/h conversion; then the NA-300
window/gate/deadband/clip/bounds, the Twin base factor's acceptance rule, the base-rate pool-edge
clamp and the startup sigma guard. No SUMO, no run files (the two-world identity and replay checks
live in results/assim/na300_impl/report.md).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from citypulse.twin.assim import NormalAssimilator, PER_HOUR, Interval  # noqa: E402
from citypulse.twin.demand_stream import TwinDemandStream  # noqa: E402
from citypulse.twin.service import (  # noqa: E402
    ASSIM_INTERVALS,
    ASSIM_M_MAX,
    ASSIM_PERIODS,
    consecutive_window,
    load_sigma,
)

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


def test_base_rate_pool_edge_is_not_truncated(tmp_path):
    """F3: at the pool edges the count is divided by the actual in-pool window length."""
    xml = tmp_path / "cand.rou.xml"
    rows = [f'<vehicle id="t{i}" depart="{i * 30.0}" type="tdist">'
            f'<route edges="tko_insert tko_in out"/></vehicle>' for i in range(30)]
    xml.write_text("<routes>\n" + "\n".join(rows) + "\n</routes>\n", encoding="utf-8")
    stream = TwinDemandStream(seed=202, path=xml, scale=1.5)
    # t=0: the +/-300 s window overruns the pool at 0, so only [0, 300) is in-pool:
    # 10 candidates / 300 s * 3600 / 1.5 = 80 veh/h (the fixed 2*window denominator gave 40)
    assert stream.base_rate("tko_insert", 0.0) == pytest.approx(80.0)
    assert stream.base_rate("tko_insert", 450.0) == pytest.approx(80.0)   # interior: unchanged
    # t=870 (the last candidate): [570, 870] -> 11 candidates / 300 s * 3600 / 1.5 = 88
    assert stream.base_rate("tko_insert", 870.0) == pytest.approx(88.0)
    # a window entirely beyond the pool has no in-pool length
    assert stream.base_rate("tko_insert", 2000.0) == 0.0


def test_base_rate_on_the_frozen_pool_has_no_edge_bias():
    """F3 on the real synth5 pool: the edge ticks report the interior pool rate, not a truncated one."""
    pool = (Path(__file__).resolve().parents[1] / "scenarios" / "kwuntong" / "blite" / "synth5"
            / "twin_cand.rou.xml")
    if not pool.exists():
        pytest.skip(f"frozen pool not present: {pool}")
    stream = TwinDemandStream(seed=202, path=pool)
    assert stream.base_rate("tko_insert", 3600.0) == pytest.approx(2756.0)   # interior: unchanged
    # the ticks the fixed denominator biased low by up to 2x (old: 1432..2592 veh/h)
    for t in (60.0, 120.0, 180.0, 240.0, 300.0, 6900.0, 6960.0, 7080.0, 7200.0):
        assert stream.base_rate("tko_insert", t) > 2600.0


# ------------------------------------------------------------------- Twin base factor (--twin-base-factor)

def _cand_xml(tmp_path, n_tko=60, n_x=20):
    rows = [f'<vehicle id="t{i}" depart="{i * 10.0}" type="tdist">'
            f'<route edges="tko_insert tko_in out"/></vehicle>' for i in range(n_tko)]
    rows += [f'<vehicle id="x{i}" depart="{i * 30.0}" type="tdist">'
             f'<route edges="x2_in x2_out"/></vehicle>' for i in range(n_x)]
    xml = tmp_path / "cand.rou.xml"
    xml.write_text("<routes>\n" + "\n".join(rows) + "\n</routes>\n", encoding="utf-8")
    return xml


def _due(stream, t=1e9):
    return [(vid, edges[0]) for vid, edges in stream.due(t)]


def test_twin_base_factor_acceptance(tmp_path):
    """Acceptance is u < factor*m/scale, applied to tko_insert only, and is a pure function of
    (seed, factor, m path)."""
    xml = _cand_xml(tmp_path)
    base = TwinDemandStream(seed=202, path=xml, scale=1.5)                   # default factor 1.0
    thin = TwinDemandStream(seed=202, path=xml, scale=1.5, base_factor=0.85)
    # factor 1.0 reproduces the pre-change expression exactly
    assert base.acceptance("tko_insert") == base.multiplier("tko_insert") / base.scale
    assert thin.acceptance("tko_insert") == pytest.approx(0.85 / 1.5)
    assert thin.factor("tko_insert") == 0.85 and thin.factor("x2_in") == 1.0
    assert thin.acceptance("x2_in") == base.acceptance("x2_in") == pytest.approx(1.0 / 1.5)

    d_base, d_thin = _due(base), _due(thin)
    tko_base = {v for v, e in d_base if e == "tko_insert"}
    tko_thin = {v for v, e in d_thin if e == "tko_insert"}
    assert tko_thin and tko_thin < tko_base
    assert {v for v, e in d_base if e == "x2_in"} == {v for v, e in d_thin if e == "x2_in"}
    # exact thinning rule, from the stream's own u
    u = {vid: ui for (_dep, vid, _e), ui in zip(base.cands, base.u)}
    assert tko_thin == {v for v in tko_base if u[v] < 0.85 / 1.5}

    # pure function of (seed, factor, m path): same inputs -> same ids; factor*m is one knob
    assert _due(TwinDemandStream(seed=202, path=xml, scale=1.5, base_factor=0.85)) == d_thin
    eq = TwinDemandStream(seed=202, path=xml, scale=1.5)     # factor 1.0 with m = 0.85
    eq.m["tko_insert"] = 0.85
    assert _due(eq) == d_thin
    # 0.85 * m <= 0.85 * 1.5 = 1.275 < scale, so acceptance stays < 1 at the NA-300 upper bound
    hi = TwinDemandStream(seed=202, path=xml, scale=1.5, base_factor=0.85)
    hi.m["tko_insert"] = 1.5
    assert hi.acceptance("tko_insert") == pytest.approx(0.85)
    assert hi.acceptance("tko_insert") < 1.0
    # the factor never changes base_s(t)
    assert thin.base_rate("tko_insert", 300.0) == base.base_rate("tko_insert", 300.0)


# ----------------------------------------------------------------------------- NA-300 (300-s tick)

NA300_BASE = 2800.0    # veh/h, the frozen TKO base rate
NA300_SIGMA = 200.0    # veh/h, provisional sigma_300 (mechanics only, not the qualification value)


def win(qs, o=5.0, valid=True, v=50.0):
    """Ten 30-s intervals, one q per interval (a scalar is repeated ten times)."""
    if isinstance(qs, (int, float)):
        qs = [qs] * 10
    return [iv(q, o, v=v, valid=valid) for q in qs]


def tick300(obs, twin, m=1.0, base=NA300_BASE, sigma=NA300_SIGMA, t=300.0, **kw):
    kw.setdefault("n_intervals", 10)
    kw.setdefault("m_max", 1.5)
    return NormalAssimilator(**kw).update(t, obs, twin, base, m, sigma_q=sigma)


def test_na300_window_is_ten_intervals():
    """Exactly the preceding ten 30-s intervals; nine, eleven or a two-interval window -> invalid."""
    m_new, row = tick300(win(10), win(8))
    assert row["reason"] == "updated" and m_new > 1.0
    assert tick300(win(10)[:9], win(8))[1]["reason"] == "invalid"
    assert tick300(win(10) + [iv(10)], win(8))[1]["reason"] == "invalid"
    assert tick300(win(10), win(8)[:9])[1]["reason"] == "invalid"
    # the 60-s NA still wants exactly two
    assert NormalAssimilator().update(60.0, win(10), win(8), NA300_BASE, 1.0,
                                      sigma_q=NA300_SIGMA)[1]["reason"] == "invalid"


def test_na300_gate_mean_observed_occupancy_below_15pct():
    """The mean observed occupancy of the ten intervals must be < 15%; the Twin's is ignored."""
    assert tick300(win(10, o=15.0), win(8))[1]["reason"] == "congested"
    assert tick300(win(10, o=14.9), win(8))[1]["reason"] == "updated"
    mixed = [iv(10, o=10.0)] * 5 + [iv(10, o=20.0)] * 5      # mean occupancy exactly 15.0
    assert tick300(mixed, win(8))[1]["reason"] == "congested"
    assert tick300(win(10, o=5.0), win(0, o=40.0))[1]["reason"] == "updated"


def test_na300_deadband_on_the_mean_residual():
    """|mean residual| <= 1 sigma_300 -> deadband; strictly above -> update."""
    # (10 - 8) vehicles per 30 s = 240 veh/h; with sigma = 240, r = 1.0 exactly
    m_edge, row_edge = tick300(win(10), win(8), sigma=240.0)
    assert row_edge["r"] == pytest.approx(1.0) and row_edge["reason"] == "deadband"
    assert m_edge == 1.0
    assert tick300(win(10), win(8), sigma=239.0)[1]["reason"] == "updated"
    assert tick300(win(8), win(8))[1]["reason"] == "deadband"
    # the residual is the mean over the ten intervals, in veh/h
    m_new, row = tick300(win([10] * 5 + [12] * 5), win(8))     # mean 11 -> 1320 - 960 = 360 veh/h
    assert row["e_s"] == pytest.approx(360.0 / NA300_BASE)
    assert m_new == pytest.approx(1.0 + 0.3 * 360.0 / NA300_BASE)


def test_na300_step_clip_and_m_bounds():
    """Delta = clip(0.3 e, +-0.05) and m in [0.5, 1.5] (the pool scale), never 1.8."""
    m_up, row_up = tick300(win(20), win(0))            # e = 2400/2800 = 0.857 -> clipped
    assert row_up["e_s"] == pytest.approx(2400.0 / NA300_BASE)
    assert row_up["delta"] == pytest.approx(0.05) and m_up == pytest.approx(1.05)
    m_dn, row_dn = tick300(win(0), win(20))
    assert row_dn["delta"] == pytest.approx(-0.05) and m_dn == pytest.approx(0.95)
    assert tick300(win(20), win(0), m=1.48)[0] == pytest.approx(1.5)
    assert tick300(win(20), win(0), m=1.79)[0] == pytest.approx(1.5)   # not 1.8
    assert tick300(win(0), win(20), m=0.52)[0] == pytest.approx(0.5)


def test_na300_invalid_window_no_update():
    """Any invalid interval in the ten, a missing detector, sigma or base -> invalid, m unchanged."""
    bad = win(10)
    bad[4] = iv(10, valid=False)
    assert tick300(bad, win(8))[1]["reason"] == "invalid"
    bad2 = win(10)
    bad2[9] = iv(None)
    assert tick300(bad2, win(8))[1]["reason"] == "invalid"
    assert tick300(win(10), None)[1]["reason"] == "invalid"
    assert tick300(win(10), win(8), sigma=None)[1]["reason"] == "invalid"
    assert tick300(win(10), win(8), sigma=0.0)[1]["reason"] == "invalid"
    assert tick300(win(10), win(8), base=0.0)[1]["reason"] == "invalid"
    # Interval objects are accepted as well as mappings
    assert tick300([Interval(q=10, o=5)] * 10, [Interval(q=8, o=5)] * 10)[1]["reason"] == "updated"


def test_na300_service_constants():
    """The service drives NA-300 with a 300-s tick over ten intervals and m_max = 1.5."""
    assert ASSIM_PERIODS["normal300"] == 300.0 and ASSIM_PERIODS["normal"] == 60.0
    assert ASSIM_INTERVALS["normal300"] == 10 and ASSIM_INTERVALS["normal"] == 2
    assert ASSIM_M_MAX["normal300"] == 1.5 and ASSIM_M_MAX["normal"] == 1.8


def test_consecutive_window():
    """A tick is only fed when the history holds n consecutive 30-s readings (F2/NA-300 window)."""
    def h(times):
        return [(float(t), iv(10), iv(8)) for t in times]

    assert consecutive_window(h(range(30, 301, 30)), 10)              # 30 .. 300
    assert not consecutive_window(h(range(30, 301, 30))[:9], 10)      # only nine
    gap = list(range(30, 301, 30))
    gap[5] = 200                                                      # a missing 30-s message
    assert not consecutive_window(h(gap), 10)
    assert consecutive_window(h([30, 60]), 2)
    assert not consecutive_window(h([30, 90]), 2)
    assert not consecutive_window([], 10)


def test_load_sigma_missing_or_nonpositive_is_a_hard_error(tmp_path):
    """F5: with assimilation on, a missing/absent/non-positive sigma must raise at startup."""
    sigma_json = tmp_path / "sigma.json"
    sigma_json.write_text(json.dumps({"AID07105": 533.736}), encoding="utf-8")
    assert load_sigma("off", None, "AID07106") == {}
    assert load_sigma("normal300", str(sigma_json), "AID07105") == {"AID07105": 533.736}
    with pytest.raises(ValueError):                     # no --sigma-json at all
        load_sigma("normal", None, "AID07105")
    with pytest.raises(ValueError):
        load_sigma("normal300", None, "AID07106")
    with pytest.raises(ValueError):                     # JSON present but the key is absent (F5)
        load_sigma("normal300", str(sigma_json), "AID07106")
    for bad in (0, -1.0, None, "abc"):
        sigma_json.write_text(json.dumps({"AID07106": bad}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_sigma("normal300", str(sigma_json), "AID07106")
    sigma_json.write_text(json.dumps({"AID07106": 200}), encoding="utf-8")
    assert load_sigma("normal300", str(sigma_json), "AID07106") == {"AID07106": 200}


def test_run_rejects_missing_sigma_before_starting_sumo(tmp_path, monkeypatch):
    """F5 is checked at startup: the error fires before any socket or SUMO process exists."""
    from citypulse.twin import service

    monkeypatch.setattr(service, "detector_loops", lambda: {})
    started = []
    monkeypatch.setattr(service.traci, "start", lambda *a, **k: started.append(a))
    with pytest.raises(ValueError):
        service.run("tcp://127.0.0.1:5999", tmp_path / "out", 2, 202,
                    demand_path=str(_cand_xml(tmp_path)), assim="normal300",
                    sigma_json=None, boundary_detector="AID07106")
    assert started == []
