"""Tests for citypulse.twin.event (event-aware assimilation, docs/oct6-event-pilot-plan.md).

Pure: no SUMO, no Proxy, no service process. Every clause the plan names is pinned here: the trigger
streak and its reset on a missing interval, the 16-hypothesis library and its priors, the identical
support rule, logL with the c = 5 noise normalisation, the adoption threshold, the demand-family
twice rule, DEGRADED's bounds, the clearance two-in-a-row rule, and the RECOVERY minimum time/exit.
"""
import math

import pytest

from citypulse.twin import event as ev

U, D = ev.PAIR_U, ev.PAIR_D
DETS = (U, D)
SIGMA = {U: {"q": 1.0, "v": 1.0, "o": 1.0}, D: {"q": 1.0, "v": 1.0, "o": 1.0}}


def obs_row(q=10, v=50.0, o=5.0, valid=True):
    return {"detector": U, "q": q, "v": v, "o": o, "valid": valid}


def twin_row(q=10, v=50.0, o=5.0):
    return {"q": q, "v": v, "o": o}


def obs_hist(times, dets=DETS, **kw):
    return {d: {float(t): obs_row(**kw) for t in times} for d in dets}


def replays_for(hyps, times, dets=DETS, **kw):
    return {h.id: {d: {float(t): twin_row(**kw) for t in times} for d in dets} for h in hyps}


# ------------------------------------------------------------------------------- trigger
def test_trigger_streak_needs_two_exactly_30s_apart():
    tr = ev.TriggerRule()
    twin = twin_row()
    # r_U^o = 6 -> B = 0.5*6 = 3.0
    hot = obs_row(o=11.0)
    cold = obs_row(o=5.0)
    r1 = tr.step(30.0, hot, twin, cold, twin, SIGMA)
    assert (r1["B"], r1["streak"], r1["alarm"]) == (3.0, 1, False)
    r2 = tr.step(60.0, hot, twin, cold, twin, SIGMA)
    assert (r2["streak"], r2["alarm"]) == (2, True)
    r3 = tr.step(90.0, cold, twin, cold, twin, SIGMA)
    assert (r3["B"], r3["streak"], r3["alarm"]) == (0.0, 0, False)


def test_trigger_missing_interval_resets_the_streak():
    tr = ev.TriggerRule()
    twin, hot, cold = twin_row(), obs_row(o=11.0), obs_row(o=5.0)
    tr.step(30.0, hot, twin, cold, twin, SIGMA)
    bad = tr.step(60.0, obs_row(valid=False), twin, cold, twin, SIGMA)
    assert bad["B"] is None and bad["streak"] == 0
    # 60 s gap: 90 s is a new streak of one, not the second consecutive interval
    gap = tr.step(90.0, hot, twin, cold, twin, SIGMA)
    assert (gap["streak"], gap["alarm"]) == (1, False)
    assert tr.step(120.0, hot, twin, cold, twin, SIGMA)["alarm"] is True


def test_trigger_masked_and_speed_null_imputation():
    tr = ev.TriggerRule()
    hot, cold = obs_row(o=11.0), obs_row(o=5.0)
    # q = 0 -> v is None on both sides: the speed residual is imputed 0, not missing
    twin0 = twin_row(q=0, v=None)
    r = tr.step(30.0, hot, twin0, cold, twin0, SIGMA)
    assert r["B"] == 3.0
    m = tr.step(60.0, hot, twin0, cold, twin0, SIGMA, masked=True)
    assert (m["streak"], m["alarm"], m["masked"], m["B"]) == (0, False, True, 3.0)


def test_trigger_needs_sigma():
    tr = ev.TriggerRule()
    r = tr.step(30.0, obs_row(o=11.0), twin_row(), obs_row(), twin_row(), {})
    assert r["B"] is None and r["streak"] == 0


# ------------------------------------------------------------------------------- hypotheses
def test_hypothesis_library_count_and_priors():
    hyps = ev.build_hypotheses()
    assert len(hyps) == 16
    fams = {f: [h for h in hyps if h.family == f] for f in ev.FAMILIES}
    assert [len(fams[f]) for f in ev.FAMILIES] == [6, 4, 6]
    for f, hs in fams.items():
        assert sum(h.prior for h in hs) == pytest.approx(1.0 / 3.0)
        assert all(h.prior == pytest.approx(1.0 / 3.0 / len(hs)) for h in hs)
    assert len({h.id for h in hyps}) == 16


# ------------------------------------------------- pilot 2: the widened incident grid (part B)
def test_pilot2_grid_has_ten_incident_hypotheses_and_twenty_in_the_library():
    hyps = ev.build_hypotheses(grid=ev.GRID_PILOT2)
    assert len(hyps) == 20
    fams = {f: [h for h in hyps if h.family == f] for f in ev.FAMILIES}
    assert [len(fams[f]) for f in ev.FAMILIES] == [10, 4, 6]
    for f, hs in fams.items():
        assert sum(h.prior for h in hs) == pytest.approx(1.0 / 3.0)
        assert all(h.prior == pytest.approx(1.0 / 3.0 / len(hs)) for h in hs)
    assert len({h.id for h in hyps}) == 20


def test_pilot2_severity_grid_is_k_x_s_with_no_edge_fully_closed():
    # k in {1, ..., min(2, n_lanes - 1)} x s in {0.6, 1.0}
    assert ev.incident_severities(3, ev.GRID_PILOT2) == ((1, 0.6), (1, 1.0), (2, 0.6), (2, 1.0))
    assert ev.incident_severities(2, ev.GRID_PILOT2) == ((1, 0.6), (1, 1.0))
    hyps = [h for h in ev.build_hypotheses(grid=ev.GRID_PILOT2,
                                           midpoints={"ktb_w3": 100.0, "ktb_n2": 200.0})
            if h.family == "incident"]
    by_edge = {}
    for h in hyps:
        by_edge.setdefault(h.params["edge"], []).append(h.params)
    assert {e: len(v) for e, v in by_edge.items()} == {"ktb_n1": 4, "ktb_w3": 4, "ktb_n2": 2}
    # the pilot hypothesis location is the observed-detector midpoint, 755 m on ktb_n1
    assert {p["pos"] for p in by_edge["ktb_n1"]} == {755.0}
    assert all(p["pos_kind"] == "fixed" for p in by_edge["ktb_n1"])
    assert sorted((len(p["lanes_closed"]), p["speed_factor"]) for p in by_edge["ktb_n1"]) == [
        (1, 0.6), (1, 1.0), (2, 0.6), (2, 1.0)]
    # 2-lane ktb_n2: only k = 1, so no edge is ever fully closed
    assert sorted((len(p["lanes_closed"]), p["speed_factor"]) for p in by_edge["ktb_n2"]) == [
        (1, 0.6), (1, 1.0)]
    assert by_edge["ktb_w3"][0]["pos"] == 100.0 and by_edge["ktb_n2"][0]["pos"] == 200.0


def test_pilot1_grid_is_reproducible_under_the_new_builder():
    ids = [h.id for h in ev.build_hypotheses() if h.family == "incident"]
    assert ids == ["inc_ktb_n1_k1_s1", "inc_ktb_n1_k2_s0.6", "inc_ktb_w3_k1_s1",
                   "inc_ktb_w3_k2_s0.6", "inc_ktb_n2_k1_s1", "inc_ktb_n2_k1_s0.6"]
    assert all(h.prior == pytest.approx(1.0 / 18.0)
               for h in ev.build_hypotheses() if h.family == "incident")
    with pytest.raises(ValueError):
        ev.build_hypotheses(grid="pilot3")


def test_find_hypothesis_tolerates_the_s1_0_spelling():
    hyps = ev.build_hypotheses(grid=ev.GRID_PILOT2)
    assert ev.normalise_hyp_id("inc_ktb_n1_k2_s1.0") == "inc_ktb_n1_k2_s1"
    assert ev.normalise_hyp_id("inc_ktb_n1_k1_s0.60") == "inc_ktb_n1_k1_s0.6"
    assert ev.normalise_hyp_id("dem_f1.15") == "dem_f1.15"
    assert ev.find_hypothesis(hyps, "inc_ktb_n1_k2_s1.0").id == "inc_ktb_n1_k2_s1"
    assert ev.find_hypothesis(hyps, "inc_ktb_n2_k1_s0.6").params["n_lanes"] == 2
    with pytest.raises(KeyError):
        ev.find_hypothesis(hyps, "inc_ktb_n1_k3_s1")


def test_incident_library_geometry():
    hyps = [h for h in ev.build_hypotheses(midpoints={"ktb_w3": 100.0, "ktb_n2": 200.0})
            if h.family == "incident"]
    by_edge = {}
    for h in hyps:
        by_edge.setdefault(h.params["edge"], []).append(h.params)
    assert set(by_edge) == {"ktb_n1", "ktb_w3", "ktb_n2"}
    assert by_edge["ktb_n1"][0]["pos"] == 755.0
    assert by_edge["ktb_w3"][0]["pos"] == 100.0 and by_edge["ktb_n2"][0]["pos"] == 200.0
    # no edge is fully closed: ktb_n2 (2 lanes) uses k = 1 for both severities
    assert sorted(p["lanes_closed"] for p in by_edge["ktb_n1"]) == [[0], [0, 1]]
    assert sorted(p["lanes_closed"] for p in by_edge["ktb_n2"]) == [[0], [0]]
    assert sorted(p["speed_factor"] for p in by_edge["ktb_n2"]) == [0.6, 1.0]
    assert all(p["speed_factor"] == 1.0 for p in by_edge["ktb_n1"] if len(p["lanes_closed"]) == 1)


def test_demand_and_fault_library():
    hyps = ev.build_hypotheses()
    assert sorted(h.params["factor"] for h in hyps if h.family == "demand") == [0.7, 0.85, 1.15, 1.3]
    faults = [(h.params["detector"], h.params["type"]) for h in hyps if h.family == "fault"]
    assert sorted(faults) == sorted([(d, t) for d in (U, D) for t in ("stuck", "zero", "noise")])
    noise = next(h for h in hyps if h.family == "fault" and h.params["type"] == "noise")
    assert noise.params["c"] == ev.NOISE_C


def test_freeze_entries_follow_the_candidate_routes():
    cands = [(0.0, "a", ["tko_insert", "ktb_w1", "ktb_n1", "ktb_n2"]),
             (1.0, "b", ["tko_insert", "ktb_w1", "ktr_w1"]),
             (2.0, "c", ["on_ktb_w2", "ktb_w2", "ktb_w3"])]
    assert ev.entries_through(cands) == ["on_ktb_w2", "tko_insert"]


# ------------------------------------------------------------------- support, logL, posterior
def _small_library():
    return [ev.Hypothesis("inc", "incident", {"edge": "ktb_n1"}, 1 / 3),
            ev.Hypothesis("dem", "demand", {"entry": "tko_insert", "factor": 0.7}, 1 / 3),
            ev.Hypothesis(f"flt_{U}_noise", "fault", {"detector": U, "type": "noise", "c": 5.0}, 1 / 3),
            ev.Hypothesis(f"flt_{U}_stuck", "fault", {"detector": U, "type": "stuck", "c": 1.0}, 1 / 3)]


def test_logl_includes_the_c5_noise_normalisation():
    hyps = _small_library()
    times = [10.0, 20.0, 30.0, 40.0]          # one complete 120-s block (block 0)
    oh = obs_hist(times, q=10)
    # every twin reading is 2 sigma above the observation -> r = -2 for every (det, channel)
    rp = replays_for(hyps, times, q=12)
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    evl = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)
    assert len(evl.support) == 2 * 3 * 1            # 2 detectors x 3 channels x 1 block
    assert evl.logL["inc"] == pytest.approx(-4.0)   # 2 q triples x -0.5*(-2)^2 (v and o fit)
    # the noise fault keeps the actual observation but inflates c to 5 on U only: U's q keeps the
    # -0.5*(r/5)^2 term, and every U triple pays -ln 5
    expect_u = (-0.5 * (-2 / 5) ** 2 - math.log(5)) + 2 * (-math.log(5))
    assert evl.logL[f"flt_{U}_noise"] == pytest.approx(expect_u + (-2.0))
    assert evl.logL["dem"] == pytest.approx(-4.0)


def test_identical_support_is_the_intersection_over_every_hypothesis():
    hyps = _small_library()
    times = [10.0, 20.0, 30.0, 40.0]
    oh = obs_hist(times)
    rp = replays_for(hyps, times)
    # no pre-t_on anchor for U -> the stuck hypothesis cannot score U's q and o anywhere
    evl = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor={U: {}, D: {}})
    assert evl.excluded["no_anchor"] == 2           # U's q and o (v is imputed, never null)
    assert len(evl.support) == 4
    assert all(h["n_O"] == 4 for h in evl.rows())
    # with an anchor the whole block is scored
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    evl2 = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)
    assert len(evl2.support) == 6


def test_identical_support_excludes_invalid_observations_and_partial_blocks():
    hyps = _small_library()
    times = [120.0, 150.0, 180.0, 210.0, 240.0, 270.0]   # block 1 complete, block 2 partial
    oh = obs_hist(times)
    oh[U][150.0]["valid"] = False
    rp = replays_for(hyps, times)
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    evl = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 100.0, 270.0, anchor=anchor)
    assert evl.excluded["obs_invalid"] == 3         # U's three channels in block 1
    assert evl.excluded["partial_block"] == 6       # block 2: 2 dets x 3 channels
    assert len(evl.support) == 3                    # D's three channels in block 1
    # identical n_O for every hypothesis (check 3)
    assert len({h["n_O"] for h in evl.rows()}) == 1


# ------------------------------------------------- fault-model likelihood (report2 G.4)
# A fault hypothesis on detector i predicts what i would report, and the likelihood scores the ACTUAL
# observation of i against that prediction: stuck -> the anchor, zero -> 0 for q and o (v keeps the
# no-event replay), noise -> the replay with c = 5. Other detectors keep (obs - twin)/sigma.
# The pre-onset anchor is a quiet reading (q = o = 2), the no-event replay sits between it and the
# congested observation (q = o = 12), and congestion is (q = 25, v = 20, o = 25): so the observation
# is closer to the no-event replay than to the anchor, while the anchor is closer to the zero model.
ANCHOR = {d: {"q": 2.0, "v": 50.0, "o": 2.0} for d in DETS}
TIMES = [10.0, 20.0, 30.0, 40.0]                       # one complete 120-s block
CONGESTED = {"q": 25, "v": 20.0, "o": 25.0}            # what the Proxy really saw (queue)
AT_ANCHOR = {"q": 2, "v": 50.0, "o": 2.0}              # what a stuck detector keeps reporting
REPLAY = {"q": 12, "v": 45.0, "o": 12.0}               # the no-event Twin replay


def _fault_library():
    """A no-event (demand) baseline plus the three fault types on U, so logL can be compared."""
    return [ev.Hypothesis("base", "demand", {"entry": "tko_insert", "factor": 1.0}, 1 / 3),
            ev.Hypothesis(f"flt_{U}_stuck", "fault", {"detector": U, "type": "stuck", "c": 1.0}, 1 / 3),
            ev.Hypothesis(f"flt_{U}_zero", "fault", {"detector": U, "type": "zero", "c": 1.0}, 1 / 3),
            ev.Hypothesis(f"flt_{U}_noise", "fault", {"detector": U, "type": "noise", "c": 5.0}, 1 / 3)]


def _no_event_replays(hyps):
    """The no-event Twin replay every fault hypothesis is scored against."""
    return replays_for(hyps, TIMES, **REPLAY)


def _logl(hyps, obs, rp):
    return ev.evaluate(hyps, list(DETS), TIMES, obs, rp, SIGMA, 0.0, 40.0, anchor=ANCHOR)


def test_stuck_fault_scores_the_observation_against_the_anchor():
    """Congestion at U (obs != anchor) must cost the stuck hypothesis; obs == anchor must fit it."""
    hyps = _fault_library()
    stuck = next(h for h in hyps if h.id == f"flt_{U}_stuck")
    base = next(h for h in hyps if h.id == "base")
    rp = _no_event_replays(hyps)

    hot = obs_hist(TIMES, **CONGESTED)
    r_q, why = ev.block_residual(stuck, U, TIMES, "q", hot, rp, SIGMA, anchor=ANCHOR)
    r_v, _ = ev.block_residual(stuck, U, TIMES, "v", hot, rp, SIGMA, anchor=ANCHOR)
    r_o, _ = ev.block_residual(stuck, U, TIMES, "o", hot, rp, SIGMA, anchor=ANCHOR)
    assert why is None
    # (obs - anchor) / sigma, channel by channel: the anomaly is charged, not erased
    assert (r_q, r_v, r_o) == (pytest.approx(23.0), pytest.approx(-30.0), pytest.approx(23.0))
    evl_hot = _logl(hyps, hot, rp)
    assert evl_hot.logL[stuck.id] < evl_hot.logL[base.id]      # worse than the no-event baseline

    flat = obs_hist(TIMES, **AT_ANCHOR)
    r_q, _ = ev.block_residual(stuck, U, TIMES, "q", flat, rp, SIGMA, anchor=ANCHOR)
    r_o, _ = ev.block_residual(stuck, U, TIMES, "o", flat, rp, SIGMA, anchor=ANCHOR)
    assert (r_q, r_o) == (pytest.approx(0.0), pytest.approx(0.0))
    evl_flat = _logl(hyps, flat, rp)
    assert evl_flat.logL[stuck.id] > evl_flat.logL[base.id]    # better than the no-event baseline
    assert evl_flat.logL[stuck.id] > evl_hot.logL[stuck.id]    # and better than under congestion


def test_zero_fault_scores_the_observation_against_zero():
    """Congestion at U must cost the zero hypothesis too; v stays the no-event replay residual."""
    hyps = _fault_library()
    zero = next(h for h in hyps if h.id == f"flt_{U}_zero")
    base = next(h for h in hyps if h.id == "base")
    rp = _no_event_replays(hyps)

    hot = obs_hist(TIMES, **CONGESTED)
    r_q, _ = ev.block_residual(zero, U, TIMES, "q", hot, rp, SIGMA, anchor=ANCHOR)
    r_v, _ = ev.block_residual(zero, U, TIMES, "v", hot, rp, SIGMA, anchor=ANCHOR)
    r_o, _ = ev.block_residual(zero, U, TIMES, "o", hot, rp, SIGMA, anchor=ANCHOR)
    assert (r_q, r_v, r_o) == (pytest.approx(25.0), pytest.approx(-25.0), pytest.approx(25.0))
    # v is undefined at zero flow: the zero model keeps the no-event replay value, so the support and
    # the v residual are exactly the baseline's
    assert r_v == ev.block_residual(base, U, TIMES, "v", hot, rp, SIGMA, anchor=ANCHOR)[0]
    evl_hot = _logl(hyps, hot, rp)
    assert evl_hot.logL[zero.id] < evl_hot.logL[base.id]

    flat = obs_hist(TIMES, **AT_ANCHOR)
    evl_flat = _logl(hyps, flat, rp)
    assert evl_flat.logL[zero.id] > evl_flat.logL[base.id]
    assert evl_flat.logL[zero.id] > evl_hot.logL[zero.id]


def test_noise_fault_residual_is_unchanged():
    """Noise still scores the actual observation against the replay, with c = 5 on U only."""
    hyps = _fault_library()
    noise = next(h for h in hyps if h.id == f"flt_{U}_noise")
    base = next(h for h in hyps if h.id == "base")
    rp = _no_event_replays(hyps)
    hot = obs_hist(TIMES, **CONGESTED)

    for x, expect in (("q", 13.0), ("v", -25.0), ("o", 13.0)):          # (obs - replay) / sigma
        r = ev.block_residual(noise, U, TIMES, x, hot, rp, SIGMA, anchor=ANCHOR)[0]
        assert r == pytest.approx(expect)
        assert r == ev.block_residual(base, U, TIMES, x, hot, rp, SIGMA, anchor=ANCHOR)[0]
    assert ev._c_of(noise, U) == ev.NOISE_C and ev._c_of(noise, D) == 1.0

    evl = _logl(hyps, hot, rp)
    expect = 0.0
    for x in ev.CHANNELS:
        r = ev.block_residual(base, U, TIMES, x, hot, rp, SIGMA, anchor=ANCHOR)[0]
        expect += -0.5 * (r / ev.NOISE_C) ** 2 - math.log(ev.NOISE_C)
        r = ev.block_residual(base, D, TIMES, x, hot, rp, SIGMA, anchor=ANCHOR)[0]
        expect += -0.5 * r ** 2
    assert evl.logL[noise.id] == pytest.approx(expect)


def test_single_hypothesis_logl_needs_no_demand_family():
    """check_replay check 2 rescores one hypothesis alone: no demand family, so logL is direct."""
    hyp = ev.Hypothesis("inc_ktb_n1_k2_s0.6", "incident", {"edge": "ktb_n1"}, 1.0)
    oh = obs_hist(TIMES, q=10)
    rp = replays_for([hyp], TIMES, q=12)                 # every channel is 2 sigma above the obs
    ll, n_o = ev.logl_of_one(hyp, list(DETS), TIMES, oh, rp, SIGMA, 0.0, 40.0, anchor=ANCHOR)
    assert n_o == 6                                      # 2 detectors x 3 channels x 1 block
    assert ll == pytest.approx(-4.0)                     # q: 2 x -0.5 * (-2)^2 (v and o fit)
    assert ev.logl_of_one(hyp, list(DETS), TIMES, oh, rp, SIGMA, 0.0, 40.0,
                          anchor=ANCHOR) == (ll, n_o)


def test_posterior_is_beta_scaled_and_evr_is_relative_to_the_demand_family():
    hyps = _small_library()
    times = [10.0, 20.0, 30.0, 40.0]
    oh = obs_hist(times, q=10)
    rp = replays_for(hyps, times, q=10)
    rp["dem"] = {d: {float(t): twin_row(q=20) for t in times} for d in DETS}   # r = -10 for dem
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    evl = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)
    assert evl.h_star == "inc"
    assert sum(evl.post.values()) == pytest.approx(1.0)
    # beta = 0.25 is explicitly applied: log post = ln prior + 0.25 logL
    for h in hyps:
        assert evl.log_post[h.id] == pytest.approx(math.log(h.prior) + ev.BETA * evl.logL[h.id]
                                                   - math.log(sum(
                                                       math.exp(math.log(g.prior) + ev.BETA * evl.logL[g.id])
                                                       for g in hyps)))
    assert evl.gap_vs_demand == pytest.approx(evl.log_post["inc"] - evl.log_post["dem"])
    assert evl.evr == pytest.approx(1.0 - evl.sse["inc"] / evl.sse["dem"])


def test_adoption_threshold_is_ln10_above_the_demand_family():
    hyps = _small_library()
    times = [10.0, 20.0, 30.0, 40.0]
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    oh = obs_hist(times, q=10)

    def gap_for(demand_off):
        rp = replays_for(hyps, times, q=10)
        rp["dem"] = {d: {float(t): twin_row(q=10 + demand_off) for t in times} for d in DETS}
        return ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)

    wide = gap_for(10)      # dem r = -10 -> 0.25 * 6 * 50 = +75 log units
    assert ev.adoption_decision(wide) is True
    assert wide.hyp(wide.h_star).family == "incident"
    narrow = gap_for(1)     # dem r = -1 -> 0.25 * 6 * 0.5 = +0.75 log units < ln 10
    assert narrow.gap_vs_demand < ev.TAU_LR
    assert ev.adoption_decision(narrow) is False
    # h* must be an incident hypothesis, not just a big gap
    rp = replays_for(hyps, times, q=10)
    rp["inc"] = {d: {float(t): twin_row(q=20) for t in times} for d in DETS}
    odd = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)
    assert odd.h_star == "dem" and ev.adoption_decision(odd) is False


# ------------------------------------------------------------------------------- clearance
def test_clearance_posterior_priors():
    # all equal logL -> the clear family keeps its prior mass 0.5
    res = ev.clearance_posterior(0.0, [0.0] * 5)
    assert res["p_clear"] == pytest.approx(0.5)
    assert res["post_active"] == pytest.approx(0.5)
    # a much better active hypothesis drives the clear mass down
    assert ev.clearance_posterior(100.0, [0.0] * 5)["p_clear"] < 0.01
    assert ev.clearance_posterior(0.0, [100.0] * 5)["p_clear"] > 0.99


def test_clearance_analysis_rows():
    res, row = ev.clearance_analysis(1000.0, 0.0, [10.0, 20.0, 0.0, 0.0, 0.0])
    assert len(row["hypotheses"]) == 6
    assert row["hypotheses"][0]["id"] == "active" and row["hypotheses"][0]["family"] == "active"
    assert row["tau_c_best"] == 120.0
    assert row["p_clear"] == pytest.approx(res["p_clear"])
    assert sum([h["post"] for h in row["hypotheses"]]) == pytest.approx(1.0)


# ------------------------------------------------------------------------------- state machine
def fake_eval(h_star, family_post, log_post=None, hyps=None):
    hyps = list(hyps) if hyps is not None else ev.build_hypotheses()
    if h_star not in {h.id for h in hyps}:
        h_star = next(h.id for h in hyps if h.family == h_star)
    lp = dict(log_post or {h.id: math.log(h.prior) for h in hyps})
    return ev.Evaluation(t=0.0, hyps=hyps, logL={h.id: 0.0 for h in hyps}, log_post=lp,
                         post={h.id: math.exp(lp[h.id]) for h in hyps}, sse={h.id: 1.0 for h in hyps},
                         support=[], excluded={}, h_star=h_star, gap_vs_demand=0.0, evr=None,
                         family_post=dict(family_post))


def test_alarm_enters_suspected_with_t_on_and_freeze():
    sm = ev.EventStateMachine()
    out = sm.trigger(5000.0, alarm=True, o_u=5.0, o_d=5.0)
    assert sm.state == ev.SUSPECTED and sm.frozen is True
    assert sm.t_on == 4400.0                          # t_on = alarm - 600
    assert out["transitions"][0].reason == "trigger_alarm"
    assert sm.assim_mode() == "frozen" and sm.kappa_scale(5000.0) == 1.0


def test_suspected_adopts_and_enters_event():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.9, "demand": 0.05, "fault": 0.05})
    out = sm.on_hypotheses(5060.0, evl, adopted=True)
    assert sm.state == ev.EVENT and out["adopt"] == evl.h_star
    assert sm.assim_mode() == "frozen"


def test_suspected_demand_family_twice_writes_m_and_returns_to_normal():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("demand", {"incident": 0.1, "demand": 0.8, "fault": 0.1})
    out1 = sm.on_hypotheses(5060.0, evl, adopted=False)
    assert sm.state == ev.SUSPECTED and out1["write_m"] is None
    out2 = sm.on_hypotheses(5120.0, evl, adopted=False)
    assert sm.state == ev.NORMAL and out2["unfreeze"] is True
    assert out2["write_m"] in ev.DEMAND_FACTORS
    assert out2["log_false_alarm"] is not None and len(sm.false_alarms) == 1
    # one evaluation in a row is not enough (and the third evaluation then degrades)
    sm2 = ev.EventStateMachine()
    sm2.trigger(5000.0, alarm=True)
    mixed = fake_eval("incident", {"incident": 0.6, "demand": 0.3, "fault": 0.1})
    sm2.on_hypotheses(5060.0, evl, adopted=False)
    sm2.on_hypotheses(5120.0, mixed, adopted=False)
    assert sm2.demand_streak == 0 and sm2.state == ev.SUSPECTED
    sm2.on_hypotheses(5180.0, evl, adopted=False)
    assert sm2.demand_streak == 1 and sm2.state == ev.DEGRADED


def test_suspected_detector_fault_downweights_and_returns_to_normal():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("fault", {"incident": 0.1, "demand": 0.1, "fault": 0.8})
    out = sm.on_hypotheses(5060.0, evl, adopted=False)
    assert sm.state == ev.NORMAL and out["downweight"] in (U, D)
    assert sm.downweight[out["downweight"]] == ev.DEFAULT_DOWNWEIGHT
    assert out["unfreeze"] is True


def test_suspected_third_unresolved_evaluation_degrades():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    for k, t in enumerate((5060.0, 5120.0, 5180.0), start=1):
        sm.on_hypotheses(t, evl, adopted=False)
        assert sm.n_eval == k
        assert sm.state == (ev.SUSPECTED if k < 3 else ev.DEGRADED)
    assert sm.assim_mode() == "slow" and sm.kappa_scale(5180.0) == ev.DEGRADED_KAPPA
    assert sm.delta_scale() == ev.DEGRADED_DELTA


def test_degraded_bounds_at_15_minutes_and_can_still_adopt():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    for t in (5060.0, 5120.0, 5180.0):
        sm.on_hypotheses(t, evl, adopted=False)
    assert sm.state == ev.DEGRADED
    t_deg = sm.t_state
    assert sm.due(t_deg + 60.0) is False and sm.due(t_deg + 120.0) is True
    # within 15 min an adoption is still possible
    out = sm.on_hypotheses(t_deg + 120.0, evl, adopted=True)
    assert sm.state == ev.EVENT and out["adopt"] is not None
    # after more than 15 min -> NORMAL with an unexplained anomaly
    sm2 = ev.EventStateMachine()
    sm2.trigger(5000.0, alarm=True)
    for t in (5060.0, 5120.0, 5180.0):
        sm2.on_hypotheses(t, evl, adopted=False)
    t_deg = sm2.t_state
    out = sm2.on_hypotheses(t_deg + 960.0, evl, adopted=False)
    assert sm2.state == ev.NORMAL and out["unfreeze"] is True
    assert out["log_unexplained"] is not None and len(sm2.unexplained) == 1


def test_degraded_exit_is_scheduled_at_exactly_entry_plus_900_and_needs_no_evaluation():
    """Pilot 2 resolves the pilot-1 conflict: DEGRADED <= 15 min, on the tick, not on an eval."""
    sm = ev.EventStateMachine(degraded_exit=ev.DEGRADED_EXIT_SCHEDULED)
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    for t in (5060.0, 5120.0, 5180.0):
        sm.on_hypotheses(t, evl, adopted=False)
    assert sm.state == ev.DEGRADED
    t_deg = sm.t_state
    assert t_deg == 5180.0
    # the eval-driven bound is off in this mode: the next evaluation at +120 s changes nothing
    assert sm.due(t_deg + 120.0) is True
    assert sm.on_hypotheses(t_deg + 120.0, evl, adopted=False)["transitions"] == []
    assert sm.state == ev.DEGRADED
    # one tick before entry + 900 s: still DEGRADED, nothing logged
    out = sm.degraded_tick(t_deg + 870.0)
    assert out["transitions"] == [] and sm.state == ev.DEGRADED and sm.unexplained == []
    # exactly at entry + 900 s -> NORMAL with the unexplained anomaly, on the tick
    out = sm.degraded_tick(t_deg + 900.0)
    assert sm.state == ev.NORMAL and out["unfreeze"] is True
    assert out["transitions"][0].reason == "unexplained_anomaly"
    assert out["log_unexplained"] == {"t": t_deg + 900.0, "seconds": 900.0}
    assert len(sm.unexplained) == 1 and sm.frozen is False
    assert sm.assim_mode() == "normal"
    # a further tick is inert
    assert sm.degraded_tick(t_deg + 930.0)["transitions"] == []


def test_degraded_tick_is_inert_in_the_pilot1_mode():
    sm = ev.EventStateMachine()                       # pilot-1 default: eval-driven bound
    assert sm.degraded_exit == ev.DEGRADED_EXIT_EVAL
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    for t in (5060.0, 5120.0, 5180.0):
        sm.on_hypotheses(t, evl, adopted=False)
    t_deg = sm.t_state
    assert sm.degraded_tick(t_deg + 900.0)["transitions"] == []
    assert sm.state == ev.DEGRADED                       # still the old behaviour: exits at the eval
    out = sm.on_hypotheses(t_deg + 960.0, evl, adopted=False)
    assert sm.state == ev.NORMAL and out["transitions"][0].reason == "unexplained_anomaly"


def test_degraded_still_adopts_just_before_the_scheduled_exit():
    sm = ev.EventStateMachine(degraded_exit=ev.DEGRADED_EXIT_SCHEDULED)
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    for t in (5060.0, 5120.0, 5180.0):
        sm.on_hypotheses(t, evl, adopted=False)
    t_deg = sm.t_state
    assert sm.degraded_tick(t_deg + 899.0)["transitions"] == []
    out = sm.on_hypotheses(t_deg + 900.0, evl, adopted=True)
    assert sm.state == ev.EVENT and out["adopt"] == evl.h_star


def test_forced_adoption_marks_h_star_and_the_threshold():
    """The labelled integration test: a fixed incident hypothesis as h*, threshold treated as met."""
    hyps = ev.build_hypotheses(grid=ev.GRID_PILOT2)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33}, hyps=hyps)
    natural = evl.h_star
    assert ev.forced_adoption(evl, "inc_ktb_n1_k2_s1.0") is True
    assert evl.h_star == "inc_ktb_n1_k2_s1" and evl.h_star != natural
    assert evl.adopted is True and evl.forced is True
    assert evl.gap_vs_demand >= ev.TAU_LR
    assert ev.adoption_decision(evl) is True
    assert evl.to_log_row(ev.SUSPECTED, 4290.0)["forced"] is True
    with pytest.raises(ValueError):
        ev.forced_adoption(evl, "dem_f1.15")           # not an incident hypothesis
    with pytest.raises(KeyError):
        ev.forced_adoption(evl, "inc_ktb_n1_k3_s1")


def test_forced_adoption_drives_the_state_machine_into_event():
    sm = ev.EventStateMachine(degraded_exit=ev.DEGRADED_EXIT_SCHEDULED)
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33},
                    hyps=ev.build_hypotheses(grid=ev.GRID_PILOT2))
    ev.forced_adoption(evl, "inc_ktb_n1_k2_s1.0")
    out = sm.on_hypotheses(5060.0, evl, adopted=evl.adopted)
    assert sm.state == ev.EVENT and sm.active_hyp == "inc_ktb_n1_k2_s1"
    assert out["adopt"] == "inc_ktb_n1_k2_s1" and sm.t_adopt == 5060.0
    assert sm.assim_mode() == "frozen"                 # the live restriction is in force


def test_restriction_record_is_what_clearance_replays_lift():
    """The live restriction must be recorded, or every H_clear replay equals the active one."""
    hyps = ev.build_hypotheses(grid=ev.GRID_PILOT2)
    hyp = ev.find_hypothesis(hyps, "inc_ktb_n1_k2_s0.6")      # 2 lanes closed, speed factor 0.6
    base = {f"ktb_n1_{i}": 50.0 + i for i in range(3)}
    rec = ev.restriction_record(hyp, base)
    assert rec["edge"] == "ktb_n1" and rec["lanes_closed"] == [0, 1]
    # only the open lane is scaled by the spec, so only it needs its base speed restored
    assert rec["base_speed"] == {"ktb_n1_2": 52.0}
    assert rec["hypothesis"] == "inc_ktb_n1_k2_s0.6"
    # speed factor 1.0 scales nothing: the lift only re-allows the closed lanes
    assert ev.restriction_record(ev.find_hypothesis(hyps, "inc_ktb_n1_k2_s1"), base)["base_speed"] == {}
    # a fully specified record must round-trip through the state machine's restriction slot
    sm = ev.EventStateMachine(degraded_exit=ev.DEGRADED_EXIT_SCHEDULED)
    sm.trigger(5000.0, alarm=True)
    evl = fake_eval("incident", {"incident": 0.9}, hyps=hyps)
    ev.forced_adoption(evl, "inc_ktb_n1_k2_s0.6")
    sm.on_hypotheses(5060.0, evl, adopted=True)
    sm.restriction = rec
    assert sm.restriction["lanes_closed"] == [0, 1]
    assert sm.snapshot()["restriction"] == rec
    sm.on_clearance(5120.0, 0.8)
    sm.on_clearance(5180.0, 0.8)
    assert sm.state == ev.RECOVERY and sm.restriction is None       # lifted on clearance


def test_evaluate_without_a_demand_family_is_defined():
    """The clearance library is active + H_clear only: no demand family, so no gap and no EVR."""
    hyps = [ev.Hypothesis("active", "incident", {"edge": "ktb_n1"}, 0.5),
            ev.Hypothesis("clear_60", "incident", {"edge": "ktb_n1"}, 0.1)]
    times = [10.0, 20.0, 30.0, 40.0]
    anchor = {d: {"q": 10, "v": 50.0, "o": 5.0} for d in DETS}
    oh = obs_hist(times, q=10)
    rp = replays_for(hyps, times, q=12)
    evl = ev.evaluate(hyps, list(DETS), times, oh, rp, SIGMA, 0.0, 40.0, anchor=anchor)
    assert evl.gap_vs_demand is None and evl.evr is None
    assert evl.family_post["incident"] == pytest.approx(1.0)
    assert evl.family_post["demand"] == 0.0 and evl.family_post["fault"] == 0.0
    assert evl.h_star in {"active", "clear_60"}
    res, row = ev.clearance_analysis(40.0, evl.logL["active"], [evl.logL["clear_60"]])
    assert row["p_clear"] == pytest.approx(res["p_clear"]) and row["p_clear"] is not None
    assert ev.adoption_decision(evl) is False          # h* is incident but the gap is undefined


def test_clearance_needs_two_consecutive_evaluations_above_threshold():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    sm.on_hypotheses(5060.0, fake_eval("incident", {"incident": 0.9}), adopted=True)
    assert sm.state == ev.EVENT
    out = sm.on_clearance(5120.0, 0.75)
    assert sm.state == ev.EVENT and out["clear"] is None and sm.clear_streak == 1
    out = sm.on_clearance(5180.0, 0.5)                 # below the threshold resets the streak
    assert sm.state == ev.EVENT and sm.clear_streak == 0
    sm.on_clearance(5240.0, 0.71)
    out = sm.on_clearance(5300.0, 0.9)
    assert sm.state == ev.RECOVERY and out["clear"] is not None
    assert sm.masked is True and sm.frozen is False
    assert sm.assim_mode() == "normal"


def test_recovery_minimum_time_and_exit_conditions():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    sm.on_hypotheses(5060.0, fake_eval("incident", {"incident": 0.9}), adopted=True)
    sm.on_clearance(5120.0, 0.8)
    sm.on_clearance(5180.0, 0.8)
    assert sm.state == ev.RECOVERY
    t_r = sm.t_recovery
    assert sm.kappa_scale(t_r) == pytest.approx(0.0)
    assert sm.kappa_scale(t_r + 150.0) == pytest.approx(0.5)
    assert sm.kappa_scale(t_r + 300.0) == pytest.approx(1.0)
    # still inside the minimum stay
    assert sm.recovery_tick(t_r + 60.0, 5.0, 5.0, 0.4)["transitions"] == []
    assert sm.state == ev.RECOVERY
    # B < 1.5 has to hold for 3 min: the clock starts at the first tick below 1.5 (t_r + 60)
    assert sm.recovery_tick(t_r + 120.0, 5.0, 5.0, 0.4)["transitions"] == []
    assert sm.recovery_tick(t_r + 180.0, 5.0, 5.0, 0.4)["transitions"] == []
    out = sm.recovery_tick(t_r + 240.0, 5.0, 5.0, 0.4)
    assert sm.state == ev.NORMAL and out["transitions"][0].reason == "recovery_complete"
    # a B spike resets the 3-min clock, and o >= 15% blocks the exit
    sm2 = ev.EventStateMachine()
    sm2.trigger(5000.0, alarm=True)
    sm2.on_hypotheses(5060.0, fake_eval("incident", {"incident": 0.9}), adopted=True)
    sm2.on_clearance(5120.0, 0.8)
    sm2.on_clearance(5180.0, 0.8)
    t_r = sm2.t_recovery
    sm2.recovery_tick(t_r + 120.0, 5.0, 5.0, 0.4)
    sm2.recovery_tick(t_r + 180.0, 5.0, 5.0, 2.0)      # spike -> reset
    sm2.recovery_tick(t_r + 240.0, 5.0, 5.0, 0.4)      # clock restarts here
    assert sm2.recovery_tick(t_r + 300.0, 5.0, 5.0, 0.4)["transitions"] == []
    assert sm2.recovery_tick(t_r + 420.0, 20.0, 5.0, 0.4)["transitions"] == []   # o >= 15%
    assert sm2.recovery_tick(t_r + 480.0, 5.0, 5.0, 0.4)["transitions"] != []
    assert sm2.state == ev.NORMAL


def test_masking_unmasks_when_both_ends_are_below_15pct_and_a_new_trigger_restarts():
    sm = ev.EventStateMachine()
    sm.trigger(5000.0, alarm=True)
    sm.on_hypotheses(5060.0, fake_eval("incident", {"incident": 0.9}), adopted=True)
    sm.on_clearance(5120.0, 0.8)
    sm.on_clearance(5180.0, 0.8)
    assert sm.masked is True
    # masked: the trigger rule never accumulates a streak, so no alarm is raised at this tick
    assert sm.trigger(5200.0, alarm=False, o_u=5.0, o_d=5.0)["transitions"] == []
    assert sm.masked is False                                   # ... and both ends are clear now
    # a new trigger after unmasking leads back to SUSPECTED_EVENT
    out = sm.trigger(5300.0, alarm=True, o_u=5.0, o_d=5.0)
    assert sm.state == ev.SUSPECTED and out["transitions"][0].reason == "trigger_alarm"
    assert sm.t_on == 4700.0
    # while masked and congested, no unmasking
    sm2 = ev.EventStateMachine()
    sm2.trigger(5000.0, alarm=True)
    sm2.on_hypotheses(5060.0, fake_eval("incident", {"incident": 0.9}), adopted=True)
    sm2.on_clearance(5120.0, 0.8)
    sm2.on_clearance(5180.0, 0.8)
    sm2.trigger(5210.0, alarm=False, o_u=20.0, o_d=5.0)
    assert sm2.masked is True


def test_evaluation_periods():
    sm = ev.EventStateMachine()
    assert sm.due(100.0) is False                        # NORMAL never evaluates
    sm.trigger(5000.0, alarm=True)
    assert sm.due(5000.0) is True                        # first evaluation right after the alarm
    evl = fake_eval("incident", {"incident": 0.34, "demand": 0.33, "fault": 0.33})
    sm.on_hypotheses(5000.0, evl, adopted=False)
    assert sm.due(5030.0) is False and sm.due(5060.0) is True     # SUSPECTED: every 60 s
    for t in (5060.0, 5120.0):
        sm.on_hypotheses(t, evl, adopted=False)
    assert sm.state == ev.DEGRADED
    sm.on_hypotheses(5180.0, evl, adopted=False)
    assert sm.due(5240.0) is False and sm.due(5300.0) is True     # DEGRADED: every 2 min
    assert sm.next_eval_at(5240.0) == 5300.0
