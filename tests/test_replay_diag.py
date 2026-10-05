"""Tests for the matched-observation replay diagnosis (docs/oct10-replay-diagnosis-plan.md rev 2).

Pure: no SUMO process, no service. The preregistered pieces that can be pinned without a replay are:
the R_P spec and its engine application (a fake libsumo connection records the calls), the variant
table and the libraries it builds, the separation of a hypothesis's intervention onset from the
interval-collection start and from the scoring bounds, the common-support intersection, the explicit
support argument of ``event.evaluate`` (and its default path), and the down-weight reconstruction from
a run's logged state transitions.
"""
import json
import math
from pathlib import Path

import pytest

from citypulse.branching import engine as eng
from citypulse.experiments import replay_diag as rd
from citypulse.twin import event as ev

DET = "AID02109"
TIMES = (120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0)
SIGMA = {DET: {"q": 1.0, "v": 1.0, "o": 1.0}}


# --------------------------------------------------------------------------------- fake libsumo
class FakeLane:
    def __init__(self):
        self.disallowed, self.speed = {}, {}

    def setDisallowed(self, lane, vclasses):
        self.disallowed[lane] = list(vclasses)

    def getMaxSpeed(self, lane):
        return self.speed.get(lane, 13.9)

    def setMaxSpeed(self, lane, v):
        self.speed[lane] = v


class FakeRoute:
    def __init__(self):
        self.routes = {}

    def getIDList(self):
        return list(self.routes)

    def add(self, rid, edges):
        self.routes[rid] = list(edges)


class FakeVehicle:
    def __init__(self):
        self.added, self.stops, self.lcm = [], [], []

    def getIDList(self):
        return [a["vid"] for a in self.added]

    def add(self, vid, route, **kw):
        self.added.append(dict(kw, vid=vid, route=route))

    def setStop(self, vid, edge, **kw):
        self.stops.append(dict(kw, vid=vid, edge=edge))

    def setLaneChangeMode(self, vid, mode):
        self.lcm.append((vid, mode))


class FakeTC:
    def __init__(self):
        self.lane, self.route, self.vehicle = FakeLane(), FakeRoute(), FakeVehicle()


class FakeCS:
    def __init__(self):
        self.lane_disallow, self.lane_maxspeed = {}, {}


class FakeStream:
    def __init__(self):
        self.m = {}


def incident_spec(representation=None, pos=755.0, k=2, s=1.0, n=3):
    spec = {"kind": "incident", "edge": "ktb_n1", "lanes_closed": list(range(k)), "n_lanes": n,
            "speed_factor": s, "pos": pos}
    if representation is not None:
        spec["representation"] = representation
    return spec


# ------------------------------------------------------------------------- R_E vs R_P application
def test_default_spec_is_R_E_and_disallows_the_closed_lanes():
    tc, cs = FakeTC(), FakeCS()
    eng._apply_spec_at(tc, cs, FakeStream(), incident_spec())
    assert tc.lane.disallowed == {"ktb_n1_0": list(eng.SCORE_VCLASSES),
                                  "ktb_n1_1": list(eng.SCORE_VCLASSES)}
    assert cs.lane_disallow == tc.lane.disallowed
    assert tc.vehicle.added == [] and tc.route.routes == {}


def test_explicit_R_E_is_identical_to_the_default():
    a, b = FakeTC(), FakeTC()
    eng._apply_spec_at(a, FakeCS(), FakeStream(), incident_spec())
    eng._apply_spec_at(b, FakeCS(), FakeStream(), incident_spec("R_E"))
    assert a.lane.disallowed == b.lane.disallowed
    assert a.vehicle.added == b.vehicle.added


def test_R_P_places_one_stopped_blocker_per_closed_lane_and_closes_nothing():
    tc, cs = FakeTC(), FakeCS()
    eng._apply_spec_at(tc, cs, FakeStream(), incident_spec("R_P", pos=900.0))
    assert tc.lane.disallowed == {} and cs.lane_disallow == {}
    assert [a["vid"] for a in tc.vehicle.added] == ["hyp_blocker_0", "hyp_blocker_1"]
    for a in tc.vehicle.added:
        assert a["departPos"] == "899.0" and a["departSpeed"] == "0" and a["typeID"] == "t_car"
    assert [(s["vid"], s["edge"], s["pos"], s["laneIndex"], s["duration"]) for s in tc.vehicle.stops] \
        == [("hyp_blocker_0", "ktb_n1", 900.0, 0, 3600.0),
            ("hyp_blocker_1", "ktb_n1", 900.0, 1, 3600.0)]
    assert tc.vehicle.lcm == [("hyp_blocker_0", 0), ("hyp_blocker_1", 0)]
    assert tc.route.routes == {"hyp_route": ["ktb_n1"]}


def test_R_P_scales_the_open_lanes_only():
    tc = FakeTC()
    tc.lane.speed.update({"ktb_n1_1": 20.0, "ktb_n1_2": 10.0})
    eng._apply_spec_at(tc, FakeCS(), FakeStream(), incident_spec("R_P", k=1, s=0.6))
    assert tc.lane.speed == {"ktb_n1_1": pytest.approx(12.0), "ktb_n1_2": pytest.approx(6.0)}
    assert "ktb_n1_0" not in tc.lane.speed


def test_R_P_demand_spec_is_untouched_by_the_representation_switch():
    stream = FakeStream()
    eng._apply_spec_at(FakeTC(), FakeCS(), stream,
                       {"kind": "demand", "entry": "tko_insert", "factor": 1.15})
    assert stream.m == {"tko_insert": 1.15}


# ------------------------------------------------------------------------------------ spec_of
def test_spec_of_omits_the_representation_for_R_E():
    hyp = ev.Hypothesis("inc_ktb_n1_k2_s1", "incident",
                        {"edge": "ktb_n1", "lanes_closed": [0, 1], "n_lanes": 3, "pos": 755.0,
                         "pos_kind": "fixed", "speed_factor": 1.0}, 0.1)
    assert "representation" not in rd.spec_of(hyp)
    assert rd.spec_of(hyp, "R_P")["representation"] == "R_P"
    dem = ev.Hypothesis("dem_f1.15", "demand", {"entry": "tko_insert", "factor": 1.15}, 0.1)
    assert rd.spec_of(dem, "R_P") == {"kind": "demand", "entry": "tko_insert", "factor": 1.15}
    flt = ev.Hypothesis("flt_AID02109_zero", "fault", {"detector": DET, "type": "zero", "c": 1.0}, 0.1)
    assert rd.spec_of(flt) == {"kind": "none"}


# ------------------------------------------------------------------------------- variant table
def test_variant_table_is_the_preregistered_one():
    assert rd.VARIANT_IDS == ("V0", "VP", "VT", "VPT", "VPL", "VPTL", "VNF", "VPTLNF")
    want = {"V0": ("R_E", "logged", rd.LOC_ASRUN, True),
            "VP": ("R_P", "logged", rd.LOC_ASRUN, True),
            "VT": ("R_E", "truth", rd.LOC_ASRUN, True),
            "VPT": ("R_P", "truth", rd.LOC_ASRUN, True),
            "VPL": ("R_P", "logged", rd.LOC_ASRUN900, True),
            "VPTL": ("R_P", "truth", rd.LOC_ASRUN900, True),
            "VNF": ("R_E", "logged", rd.LOC_ASRUN, False),
            "VPTLNF": ("R_P", "truth", rd.LOC_ASRUN900, False)}
    for vid, (rep, onset, locs, fault) in want.items():
        cfg = rd.VARIANTS[vid]["config"]
        assert rd.CONFIG_DEF[cfg] == (rep, onset, locs)
        assert rd.VARIANTS[vid]["fault"] is fault


def test_as_run_library_is_the_pilot2_library():
    mids, counts = {"ktb_n1": 503.1, "ktb_w3": 145.95, "ktb_n2": 997.45}, \
        {"ktb_n1": 3, "ktb_w3": 3, "ktb_n2": 2}
    built = rd.build_library(rd.locations_of(rd.LOC_ASRUN, mids), counts, fault=True)
    reference = ev.build_hypotheses(midpoints=mids, lane_counts=counts, grid=ev.GRID_PILOT2)
    assert [h.id for h in built] == [h.id for h in reference]
    assert [dict(h.params) for h in built] == [dict(h.params) for h in reference]
    assert [h.prior for h in built] == [h.prior for h in reference]


def test_900m_library_adds_four_distinct_members_with_the_same_grid():
    mids, counts = {"ktb_n1": 503.1, "ktb_w3": 145.95, "ktb_n2": 997.45}, \
        {"ktb_n1": 3, "ktb_w3": 3, "ktb_n2": 2}
    hyps = rd.build_library(rd.locations_of(rd.LOC_ASRUN900, mids), counts, fault=True)
    inc = [h for h in hyps if h.family == "incident"]
    assert len(inc) == 14 and len({h.id for h in inc}) == 14
    added = [h for h in inc if h.params["pos"] == 900.0]
    assert len(added) == 4
    assert {(tuple(h.params["lanes_closed"]), h.params["speed_factor"]) for h in added} \
        == {(tuple(range(k)), s) for k in (1, 2) for s in (0.6, 1.0)}
    assert all(h.prior == pytest.approx((1.0 / 3.0) / 14.0) for h in inc)
    assert sum(h.prior for h in hyps if h.family == "incident") == pytest.approx(1.0 / 3.0)


def test_no_fault_family_splits_the_mass_half_incident_half_demand():
    mids, counts = {"ktb_n1": 503.1, "ktb_w3": 145.95, "ktb_n2": 997.45}, \
        {"ktb_n1": 3, "ktb_w3": 3, "ktb_n2": 2}
    hyps = rd.build_library(rd.locations_of(rd.LOC_ASRUN, mids), counts, fault=False)
    assert not [h for h in hyps if h.family == "fault"]
    assert sum(h.prior for h in hyps) == pytest.approx(1.0)
    assert sum(h.prior for h in hyps if h.family == "incident") == pytest.approx(0.5)
    assert sum(h.prior for h in hyps if h.family == "demand") == pytest.approx(0.5)


# ------------------------------------------------------------------ onset vs collection separation
def evalspec(t_on=4410.0, t_eval=5010.0):
    return rd.EvalSpec(eval_id="x", run="evt_inc_4101", arm="INC", seed=4101, t_eval=t_eval, t_on=t_on,
                       snapshot=Path("s.xml.gz"), meta=Path("s.json"), obs_hist=obs_hist(),
                       anchor={}, weights={}, lane_counts={"ktb_n1": 3, "ktb_w3": 3, "ktb_n2": 2},
                       midpoints={"ktb_n1": 503.1, "ktb_w3": 145.95, "ktb_n2": 997.45})


def test_incident_onset_follows_the_variant_and_demand_keeps_the_provisional_onset():
    evd = evalspec()
    inc = ev.Hypothesis("inc_ktb_n1_k2_s1", "incident",
                        {"edge": "ktb_n1", "lanes_closed": [0, 1], "n_lanes": 3, "pos": 755.0,
                         "pos_kind": "fixed", "speed_factor": 1.0}, 0.1)
    dem = ev.Hypothesis("dem_f1.15", "demand", {"entry": "tko_insert", "factor": 1.15}, 0.1)
    v0 = rd.make_job(evd, "A", inc)
    vt = rd.make_job(evd, "C", inc)
    assert (v0["t_on"], vt["t_on"]) == (4410.0, rd.TRUTH_ONSET)
    assert v0["collect_from"] == vt["collect_from"] == 4410.0     # scoring bounds never move
    assert vt["t_end"] == 5010.0
    assert rd.make_job(evd, "C", dem)["t_on"] == 4410.0           # demand keeps the provisional onset
    assert rd.make_job(evd, "C", dem)["collect_from"] == 4410.0


def test_truth_onset_never_moves_the_scoring_window():
    evd = evalspec(t_on=4320.0, t_eval=5040.0)
    inc = ev.Hypothesis("inc_ktb_n2_k1_s1", "incident",
                        {"edge": "ktb_n2", "lanes_closed": [0], "n_lanes": 2, "pos": 997.5,
                         "pos_kind": "mid", "speed_factor": 1.0}, 0.1)
    job = rd.make_job(evd, "D", inc)
    assert job["t_on"] == rd.TRUTH_ONSET and job["collect_from"] == 4320.0 and job["t_end"] == 5040.0


def test_noi_plan_is_the_preregistered_synthetic_episode():
    assert rd.NOI_EVAL_TIMES == (4890.0, 5010.0, 5130.0)
    assert rd.NOI_T_ON == 4290.0 and rd.NOI_SNAP == 4230.0
    assert rd.NOI_EVAL_TIMES[0] - rd.NOI_T_ON == 600.0            # imposed alarm - 600
    assert rd.NOI_SNAP == rd.NOI_T_ON - ev.DELTA_S                # start snapshot = t_on - 60


def test_job_key_ignores_the_tag_and_keeps_the_separated_fields():
    evd = evalspec()
    inc = ev.Hypothesis("inc_ktb_n1_k2_s1", "incident",
                        {"edge": "ktb_n1", "lanes_closed": [0, 1], "n_lanes": 3, "pos": 755.0,
                         "pos_kind": "fixed", "speed_factor": 1.0}, 0.1)
    a, b = rd.make_job(evd, "A", inc), rd.make_job(evd, "A", inc)
    b["tag"] = "other"
    assert rd.job_key(evd, a) == rd.job_key(evd, b)
    assert rd.job_key(evd, a) != rd.job_key(evd, rd.make_job(evd, "B", inc))
    assert rd.job_key(evd, a) != rd.job_key(evd, rd.make_job(evd, "C", inc))


# ---------------------------------------------------------------------------------- down-weights
def test_downweights_are_in_force_only_after_their_transition(tmp_path):
    run = tmp_path / "run"
    (run / "twin").mkdir(parents=True)
    rows = [{"t": 5010.0, "from": "SUSPECTED_EVENT", "to": "NORMAL",
             "reason": "detector_fault_AID02111_zero"},
            {"t": 5160.0, "from": "SUSPECTED_EVENT", "to": "NORMAL",
             "reason": "detector_fault_AID02109_noise"},
            {"t": 5200.0, "from": "SUSPECTED_EVENT", "to": "DEGRADED", "reason": "unresolved_3_evals"}]
    (run / "twin/state_trace.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    sets = rd.downweights_by_time(run)
    assert sets == [(5010.0, "AID02111"), (5160.0, "AID02109")]
    # the evaluation at 5010 s runs before its own transition, so it carries no down-weight
    assert {d for t, d in sets if 5010.0 > t} == set()
    assert {d for t, d in sets if 5160.0 > t} == {"AID02111"}
    assert {d for t, d in sets if 5170.0 > t} == {"AID02111", "AID02109"}


# ------------------------------------------------------------------------------ common support
def obs_hist(times=TIMES):
    return {DET: {t: {"detector": DET, "q": 10.0, "v": 50.0, "o": 5.0, "valid": True} for t in times}}


def twin_table(times=TIMES):
    return {t: {"q": 10.0, "v": 50.0, "o": 5.0} for t in times}


def two_hyps():
    return [ev.Hypothesis("h1", "incident", {}, 0.5), ev.Hypothesis("h2", "incident", {}, 0.5)]


def test_common_support_intersects_every_variant_and_counts_the_reason():
    hyps = two_hyps()
    times = list(TIMES)
    good = {h.id: {DET: twin_table()} for h in hyps}
    short = {h.id: {DET: twin_table([t for t in TIMES if t != 300.0])} for h in hyps}
    entries = [(hyps, good), (hyps, short)]
    support, excluded = rd.common_support(evalspec(t_on=90.0, t_eval=330.0), SIGMA, entries, times)
    assert excluded == {"twin_null": 3}                # one (detector, block, channel) triple
    assert len(support) == 2 * 1 * 3 - 3
    assert all(b != 2 for _d, b, _x, _ts in support)


def test_common_support_is_the_whole_intersection_when_nothing_is_missing():
    hyps = two_hyps()
    good = {h.id: {DET: twin_table()} for h in hyps}
    support, excluded = rd.common_support(evalspec(t_on=90.0, t_eval=330.0), SIGMA,
                                          [(hyps, good), (hyps, good)], list(TIMES))
    assert excluded == {} and len(support) == 2 * 1 * 3
    assert {b for _d, b, _x, _ts in support} == {1, 2}


def test_common_support_excludes_partial_blocks_by_reason():
    hyps = two_hyps()
    good = {h.id: {DET: twin_table()} for h in hyps}
    support, excluded = rd.common_support(evalspec(t_on=90.0, t_eval=300.0), SIGMA,
                                          [(hyps, good)], list(TIMES))
    # block 2 (240..330) is incomplete inside (90, 300]
    assert excluded == {"partial_block": 1 * 1 * 3}
    assert len(support) == 1 * 1 * 3


# ------------------------------------------------------------- evaluate with an explicit support
def test_evaluate_with_an_explicit_support_matches_the_internal_one():
    hyps = two_hyps()
    good = {h.id: {DET: twin_table()} for h in hyps}
    base = ev.evaluate(hyps, [DET], list(TIMES), obs_hist(), good, SIGMA, 90.0, 330.0)
    again = ev.evaluate(hyps, [DET], list(TIMES), obs_hist(), good, SIGMA, 90.0, 330.0,
                        support=list(base.support), excluded=dict(base.excluded))
    assert again.logL == base.logL and again.post == base.post and again.h_star == base.h_star
    assert again.support == base.support and again.excluded == base.excluded


def test_explicit_support_rejects_a_triple_it_cannot_score():
    hyps = two_hyps()
    short = {h.id: {DET: twin_table([t for t in TIMES if t != 330.0])} for h in hyps}
    support = [(DET, 2, "q", [240.0, 270.0, 300.0, 330.0])]   # 330 s missing from the replay
    with pytest.raises(ValueError):
        ev.evaluate(hyps, [DET], list(TIMES), obs_hist(), short, SIGMA, 90.0, 330.0, support=support)


def test_default_evaluate_still_uses_the_library_internal_support():
    hyps = two_hyps()
    short = {h.id: {DET: twin_table([t for t in TIMES if t != 300.0])} for h in hyps}
    res = ev.evaluate(hyps, [DET], list(TIMES), obs_hist(), short, SIGMA, 90.0, 330.0)
    assert res.excluded == {"twin_null": 3}
    assert len(res.support) == 3


# ------------------------------------------------------------------------------ variant outcome
def test_gap_is_best_incident_minus_best_demand_and_drives_would_adopt():
    hyps = [ev.Hypothesis("inc_a", "incident", {}, 1.0 / 3.0),
            ev.Hypothesis("dem_a", "demand", {}, 1.0 / 3.0)]
    res = ev.evaluate(hyps, [DET], list(TIMES), obs_hist(),
                      {h.id: {DET: twin_table()} for h in hyps}, SIGMA, 90.0, 330.0)
    out = rd.variant_outcome(res, hyps)
    assert out["gap"] == pytest.approx(math.log(res.post["inc_a"]) - math.log(res.post["dem_a"]))
    assert out["gap"] == pytest.approx(out["gap_map"])
    assert out["would_adopt"] is (out["h_star_family"] == "incident" and out["gap"] > ev.TAU_LR)


def test_would_adopt_needs_the_map_itself_to_be_an_incident():
    class FakeEval:
        def __init__(self, post, h_star, hyps, gap_map=0.0):
            self.post, self.log_post = post, {k: math.log(v) for k, v in post.items()}
            self.h_star, self.gap_vs_demand, self.evr = h_star, gap_map, 0.0
            self.support, self._hyps = [1, 2, 3], hyps
            self.family_post = {f: sum(v for k, v in post.items()
                                       if next(h for h in hyps if h.id == k).family == f)
                                for f in ev.FAMILIES}

        def hyp(self, hid):
            return next(h for h in self._hyps if h.id == hid)

    hyps = [ev.Hypothesis("inc_a", "incident", {}, 0.2), ev.Hypothesis("dem_a", "demand", {}, 0.3),
            ev.Hypothesis("flt_a", "fault", {}, 0.5)]
    # the best incident beats the best demand by more than ln 10, but the MAP is a fault
    fault_map = FakeEval({"inc_a": 0.499, "dem_a": 0.001, "flt_a": 0.500}, "flt_a", hyps)
    out = rd.variant_outcome(fault_map, hyps)
    assert out["h_star_family"] == "fault"
    assert out["gap"] == pytest.approx(math.log(0.499) - math.log(0.001))
    assert out["gap"] > ev.TAU_LR and out["would_adopt"] is False
    # the MAP is an incident but the gap is under the threshold
    weak = FakeEval({"inc_a": 0.30, "dem_a": 0.60, "flt_a": 0.10}, "inc_a", hyps)
    out = rd.variant_outcome(weak, hyps)
    assert out["h_star_family"] == "incident" and out["would_adopt"] is False


# --------------------------------------------------------------------------------- misc plumbing
def test_identity_fields_cover_behaviour_and_exclude_new_metadata():
    assert "intervals" in rd.IDENTITY_FIELDS and "veh_digest" in rd.IDENTITY_FIELDS
    assert "collect_from" not in rd.IDENTITY_FIELDS and "blockers" not in rd.IDENTITY_FIELDS


def test_obs_and_anchor_come_from_the_runs_own_log():
    hist = {DET: {30.0: {"detector": DET, "q": 1.0, "v": 2.0, "o": 3.0, "valid": True},
                  60.0: {"detector": DET, "q": 4.0, "v": None, "o": 6.0, "valid": True},
                  90.0: {"detector": DET, "q": 9.0, "v": 9.0, "o": 9.0, "valid": False}}}
    anchor = rd.anchor_from(hist, 90.0)
    assert anchor[DET] == {"q": 4.0, "v": 2.0, "o": 6.0}      # last valid pre-t_on reading per channel


def test_variant_labels_are_the_spec_labels():
    assert rd.VARIANTS["V0"]["label"] == "base"
    assert rd.VARIANTS["VP"]["label"] == "representation diagnostic"
    assert rd.VARIANTS["VNF"]["label"] == "competition diagnostic"
    assert rd.VARIANTS["VPTLNF"]["label"] == "truth-assisted control"
