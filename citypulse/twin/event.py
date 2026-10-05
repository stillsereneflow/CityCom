"""Event-aware assimilation, pure logic (docs/oct6-event-pilot-plan.md, "Event-aware assimilation").

Pilot 2 (part B of docs/oct6-audit-and-pilot2-plan.md) adds three things here, each behind an explicit
switch so pilot-1 behaviour is unchanged: ``build_hypotheses(grid="pilot2")`` (k in {1, ...,
min(2, n_lanes - 1)} x s in {0.6, 1.0} -- 10 incident hypotheses and a 20-hypothesis library, family
mass still 1/3), ``EventStateMachine(degraded_exit="scheduled")`` (DEGRADED leaves at entry + 900 s
exactly, on the tick, not at the next evaluation) and ``forced_adoption`` (the labelled integration
test that treats a fixed incident hypothesis as h* at the first evaluation).

No SUMO, no traci, no Proxy import (tests/test_firewall.py). The service owns the snapshot ring, the
subprocess replays (``citypulse.branching.engine.score_replays``), the live state replacement and the
logs; this module owns:

* the corrected G4 trigger (B on AID02109/AID02111, two timestamps exactly 30 s apart, a missing
  interval resets the streak);
* the hypothesis library (6 incident in the pilot-1 grid, 10 in the pilot-2 grid, 4 demand, 6 detector
  fault; family priors 1/3, uniform inside a family);
* the identical-support set O (120-s blocks whose four intervals are valid in the observations and
  non-null under every hypothesis) and the exclusions by reason;
* the block-mean standardised residuals of the observation against the hypothesis's prediction (the
  fault model on a faulting detector, the no-event replay elsewhere), logL (c = 1, or c = 5 on the
  noise-fault detector), the beta = 0.25 posterior, adoption (MAP in the incident family and a
  demand-family log gap > ln 10) and EVR;
* the clearance posterior H_clear(tau_c) against the active hypothesis;
* the NORMAL / SUSPECTED_EVENT / DEGRADED / EVENT_ASSIMILATION / RECOVERY state machine.

Units are the ones the Twin reads: q is vehicles per 30-s interval, v is km/h, o is per cent. sigma
comes from ``sigma_event.json`` (1.4826 * MAD of the biased-OL residuals, t >= 900 s), so every
residual is dimensionless.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------- constants (the spec)
PAIR_U = "AID02109"
PAIR_D = "AID02111"
CANDIDATE_SEGMENTS = ("ktb_n1", "ktb_w3", "ktb_n2")
CHANNELS = ("q", "v", "o")

TRIGGER_THRESHOLD = 3.0
TRIGGER_CONSECUTIVE = 2
INTERVAL_S = 30.0
BLOCK_S = 120.0
BLOCK_INTERVALS = 4

BETA = 0.25                      # explicitly uncalibrated (spec, "Posterior")
TAU_LR = math.log(10.0)          # adoption log-posterior gap
O_CRIT = 15.0                    # per cent; congestion gate and RECOVERY exit
PROVISIONAL_ONSET = 600.0        # t_on = alarm - 600
DELTA_S = 60.0                   # replays start from S(t_on - DELTA)
RING_KEEP = 900.0                # 15 min snapshot ring
SUSPECTED_PERIOD = 60.0
DEGRADED_PERIOD = 120.0
EVENT_PERIOD = 60.0
DEGRADED_MAX = 900.0             # > 15 min in DEGRADED -> NORMAL ("unexplained anomaly")
# How the DEGRADED bound is enforced. "eval": at the next evaluation past 15 min (pilot 1, unchanged).
# "scheduled": on the 30-s tick at entry + 900 s exactly, independent of evaluations (part B of
# docs/oct6-audit-and-pilot2-plan.md resolves the pilot-1 conflict: DEGRADED <= 15 min).
DEGRADED_EXIT_EVAL = "eval"
DEGRADED_EXIT_SCHEDULED = "scheduled"
DEGRADED_EXITS = (DEGRADED_EXIT_EVAL, DEGRADED_EXIT_SCHEDULED)
RECOVERY_MIN = 180.0             # >= 180 s in RECOVERY, and >= 3 min of B < 1.5
RECOVERY_RAMP = 300.0            # kappa ramps 0 -> kappa over 5 min
DEGRADED_KAPPA = 0.25            # kappa/4
DEGRADED_DELTA = 2.0             # deadband 2 sigma
B_EXIT = 1.5
CLEAR_TAUS = (60.0, 120.0, 180.0, 240.0, 300.0)
P_CLEAR_THRESHOLD = 0.7
P_DEMAND_THRESHOLD = 0.6
NOISE_C = 5.0
DEFAULT_DOWNWEIGHT = 5.0         # sigma multiplier applied to a faulting detector

NORMAL = "NORMAL"
SUSPECTED = "SUSPECTED_EVENT"
DEGRADED = "DEGRADED"
EVENT = "EVENT_ASSIMILATION"
RECOVERY = "RECOVERY"

FAMILIES = ("incident", "demand", "fault")
FAMILY_PRIOR = {f: 1.0 / 3.0 for f in FAMILIES}
DEMAND_FACTORS = (0.7, 0.85, 1.15, 1.3)
FAULT_DETECTORS = (PAIR_U, PAIR_D)
FAULT_TYPES = ("stuck", "zero", "noise")
BASE_FACTOR_ENTRY = "tko_insert"

# net5 geometry (scenarios/kwuntong/blite/net5.net.xml, detector_map.json): the trigger segment at
# the observed-detector midpoint (755 m = (455.7 + 1054.9) / 2), the neighbours at their midpoints.
INCIDENT_LOCATIONS = (("ktb_n1", 755.0), ("ktb_w3", None), ("ktb_n2", None))
INCIDENT_LANE_COUNTS = {"ktb_n1": 3, "ktb_w3": 3, "ktb_n2": 2}
SEVERITIES_3LANE = ((1, 1.0), (2, 0.6))   # (lanes closed from lane 0, remaining-lane speed factor)
SEVERITIES_2LANE = ((1, 1.0), (1, 0.6))   # no edge is ever fully closed
VCLASSES = ("passenger", "bus", "truck", "trailer", "delivery")

# Incident grids. "pilot1" is docs/oct6-event-pilot-plan.md: 2 severities per 3-lane edge and 2 per
# 2-lane edge, 6 incident hypotheses. "pilot2" is part B of docs/oct6-audit-and-pilot2-plan.md:
# k in {1, ..., min(2, n_lanes - 1)} x s in {0.6, 1.0}, i.e. 4 + 4 + 2 = 10 incident hypotheses and a
# 20-hypothesis library (family mass still 1/3, uniform inside the family).
EVENT_GRIDS = ("pilot1", "pilot2")
GRID_PILOT1 = "pilot1"
GRID_PILOT2 = "pilot2"


# ---------------------------------------------------------------------------------------- helpers
def _num(x):
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _field(row, key):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def load_sigma(path):
    """sigma_event.json -> {detector: {"q": s, "v": s, "o": s}}.

    Accepts either the wrapped file written by ``results/event_pilot/impl/compute_sigma_event.py``
    (``{"sigma": {...}}``) or a bare ``{detector: {...}}`` mapping. A scalar value is read as sigma_q.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    table = raw.get("sigma", raw) if isinstance(raw, dict) else raw
    out = {}
    for det, val in dict(table).items():
        if isinstance(val, dict):
            out[det] = {x: _num(val.get(x)) for x in CHANNELS}
        else:
            out[det] = {"q": _num(val), "v": None, "o": None}
    return out


def sigma_of(sigma, det, x, weights=None):
    """sigma_det^x, optionally inflated by a detector down-weight factor."""
    row = (sigma or {}).get(det)
    s = _num(row.get(x)) if isinstance(row, dict) else _num(row)
    if s is None or s <= 0:
        return None
    if weights and det in weights:
        s = s * float(weights[det])
    return s


# ---------------------------------------------------------------------------------------- trigger
def bottleneck_index(obs_u, twin_u, obs_d, twin_d, sigma, weights=None):
    """B = 0.5*(r_U^o - r_D^o) + 0.5*(r_D^v - r_U^v); (None, reason) when the interval is missing.

    r = (obs - twin) / sigma. Speed nulls (a detector with q = 0) are imputed as a zero residual, the
    corrected G4 rule: only a lost occupancy packet makes the interval missing.
    """
    if obs_u is None or obs_d is None or twin_u is None or twin_d is None:
        return None, "reading_missing"
    if not bool(_field(obs_u, "valid")) or not bool(_field(obs_d, "valid")):
        return None, "obs_invalid"
    for row in (obs_u, obs_d):
        if _field(row, "q") is None or _field(row, "o") is None:
            return None, "obs_null"
    for det in (PAIR_U, PAIR_D):
        if _field(twin_u if det == PAIR_U else twin_d, "q") is None:
            return None, "twin_null"
    r = {}
    for det, obs_row, twin_row in ((PAIR_U, obs_u, twin_u), (PAIR_D, obs_d, twin_d)):
        for x in ("o", "v"):
            s = sigma_of(sigma, det, x, weights)
            if s is None:
                return None, "no_sigma"
            o, w = _num(_field(obs_row, x)), _num(_field(twin_row, x))
            r[(det, x)] = 0.0 if (o is None or w is None) else (o - w) / s
    return 0.5 * (r[(PAIR_U, "o")] - r[(PAIR_D, "o")]) + 0.5 * (r[(PAIR_D, "v")] - r[(PAIR_U, "v")]), None


class TriggerRule:
    """The corrected G4 streak: B >= 3 at two timestamps exactly 30 s apart; a missing interval resets.

    ``step`` is called once per 30-s SensorMsg. While ``masked`` (after clearance, until both ends
    have o < 15%) B is still computed and logged but no streak is accumulated.
    """

    def __init__(self, threshold=TRIGGER_THRESHOLD, consecutive=TRIGGER_CONSECUTIVE,
                 interval=INTERVAL_S):
        self.threshold = float(threshold)
        self.consecutive = int(consecutive)
        self.interval = float(interval)
        self.last_t = None
        self.streak = 0
        self.alarms = []

    def step(self, t, obs_u, twin_u, obs_d, twin_d, sigma, masked=False, weights=None):
        t = float(t)
        B, why = bottleneck_index(obs_u, twin_u, obs_d, twin_d, sigma, weights)
        if masked or B is None:
            self.streak = 0
        elif B >= self.threshold and self.last_t is not None and abs(t - self.last_t - self.interval) < 1e-6:
            self.streak += 1
        elif B >= self.threshold:
            self.streak = 1      # a gap (missing interval) restarts the streak at this timestamp
        else:
            self.streak = 0
        self.last_t = t
        alarm = bool((not masked) and B is not None and self.streak >= self.consecutive)
        if alarm:
            self.alarms.append(t)
        return {"t": t, "B": None if B is None else float(B), "streak": int(self.streak),
                "masked": bool(masked), "alarm": alarm, "why": why}


# ----------------------------------------------------------------------------------- hypotheses
@dataclass(frozen=True)
class Hypothesis:
    id: str
    family: str
    params: dict
    prior: float

    def to_dict(self):
        return {"id": self.id, "family": self.family, "params": dict(self.params), "prior": self.prior}


def build_hypotheses(midpoints=None, lane_counts=None, t_on=None, grid=GRID_PILOT1):
    """The hypothesis library (spec table), family priors 1/3, uniform within a family.

    ``grid`` selects the incident grid only: ``"pilot1"`` is the 16-hypothesis library of
    docs/oct6-event-pilot-plan.md (6 incident), ``"pilot2"`` the 20-hypothesis library of part B of
    docs/oct6-audit-and-pilot2-plan.md (10 incident). Demand and detector-fault families are identical.
    """
    if grid not in EVENT_GRIDS:
        raise ValueError(f"unknown event grid {grid!r}; expected one of {EVENT_GRIDS}")
    midpoints = dict(midpoints or {})
    lanes = dict(INCIDENT_LANE_COUNTS)
    lanes.update(lane_counts or {})
    incident = []
    for edge, pos in INCIDENT_LOCATIONS:
        n = int(lanes[edge])
        for k, s in incident_severities(n, grid):
            p = midpoints.get(edge) if pos is None else pos
            incident.append((f"inc_{edge}_k{k}_s{s:g}",
                             {"edge": edge, "lanes_closed": list(range(k)), "n_lanes": n,
                              "pos": None if p is None else round(float(p), 1),
                              "pos_kind": "mid" if pos is None else "fixed",
                              "speed_factor": float(s)}))
    hyps = [Hypothesis(hid, "incident", params, FAMILY_PRIOR["incident"] / len(incident))
            for hid, params in incident]
    for f in DEMAND_FACTORS:
        hyps.append(Hypothesis(f"dem_f{f:g}", "demand",
                               {"entry": BASE_FACTOR_ENTRY, "factor": float(f), "t_on": t_on},
                               FAMILY_PRIOR["demand"] / 4.0))
    for det in FAULT_DETECTORS:
        for kind in FAULT_TYPES:
            hyps.append(Hypothesis(f"flt_{det}_{kind}", "fault",
                                   {"detector": det, "type": kind,
                                    "c": NOISE_C if kind == "noise" else 1.0},
                                   FAMILY_PRIOR["fault"] / 6.0))
    return hyps


def incident_severities(n_lanes, grid=GRID_PILOT1):
    """The (lanes closed from lane 0, remaining-lane speed factor) grid of one edge.

    pilot1: the plan's two severities per location ((1, 1.0) and (2, 0.6) on a 3-lane edge; the two
    2-lane variants so no edge is fully closed). pilot2: k in {1, ..., min(2, n_lanes - 1)} crossed
    with s in {0.6, 1.0} -- 4 combinations on a 3-lane edge, 2 on a 2-lane edge, no edge fully closed.
    """
    n = int(n_lanes)
    if grid == GRID_PILOT2:
        return tuple((k, s) for k in range(1, min(2, n - 1) + 1) for s in (0.6, 1.0))
    return SEVERITIES_3LANE if n >= 3 else SEVERITIES_2LANE


_SEV_RE = re.compile(r"^(?P<head>.*_s)(?P<val>[0-9]*\.?[0-9]+)$")


def normalise_hyp_id(hid):
    """`inc_ktb_n1_k2_s1.0` -> `inc_ktb_n1_k2_s1`: ids format the severity with %g."""
    m = _SEV_RE.match(str(hid))
    if not m:
        return str(hid)
    try:
        return m.group("head") + f"{float(m.group('val')):g}"
    except ValueError:
        return str(hid)


def find_hypothesis(hyps, hid):
    """The hypothesis with this id, tolerating a `_s1.0` / `_s1` spelling difference."""
    want = normalise_hyp_id(hid)
    for h in hyps:
        if h.id == want:
            return h
    raise KeyError(f"unknown hypothesis {hid!r} (normalised {want!r}); known ids: "
                   f"{[h.id for h in hyps]}")


def entries_through(cands, segments=CANDIDATE_SEGMENTS):
    """Entry edges whose candidate routes pass any candidate segment (the regional-freeze set)."""
    segs = set(segments)
    out = set()
    for _dep, _vid, edges in cands:
        if segs.intersection(edges):
            out.add(edges[0])
    return sorted(out)


def restriction_record(hyp, base_speeds=None):
    """The live restriction record of an adopted incident hypothesis: what the clearance replays lift.

    ``base_speeds`` is {lane: max speed} read from the live Twin *before* the restriction is applied;
    only the lanes the spec scales (the open ones, when speed_factor != 1) are kept. Without this
    record ``EventRuntime.lift_spec`` is empty and every H_clear(tau_c) replay is identical to the
    active one, so P_clear can never leave its 0.5 prior and clearance can never fire.
    """
    p = dict(hyp.params)
    lanes_closed = list(p.get("lanes_closed") or [])
    base = {}
    if float(p.get("speed_factor", 1.0)) != 1.0:
        for ln in range(int(p.get("n_lanes") or 0)):
            if ln in lanes_closed:
                continue
            lane = f"{p['edge']}_{ln}"
            if base_speeds and base_speeds.get(lane) is not None:
                base[lane] = float(base_speeds[lane])
    return {"edge": p["edge"], "lanes_closed": lanes_closed, "n_lanes": int(p.get("n_lanes") or 0),
            "speed_factor": float(p.get("speed_factor", 1.0)), "pos": p.get("pos"),
            "hypothesis": hyp.id, "base_speed": base}


# ------------------------------------------------------- residuals, identical support, posterior
def block_of(t, block=BLOCK_S):
    return int(math.floor(float(t) / block))


def candidate_blocks(dets, times, t_on, t_end):
    """Complete 120-s blocks in (t_on, t_end] -> {block: [t, ...]}, plus the incomplete ones."""
    blocks = {}
    for t in sorted(set(float(x) for x in times)):
        if t_on < t <= t_end + 1e-9:
            blocks.setdefault(block_of(t), []).append(t)
    complete = {b: ts for b, ts in blocks.items() if len(ts) == BLOCK_INTERVALS}
    partial = sorted(b for b, ts in blocks.items() if len(ts) < BLOCK_INTERVALS)
    return complete, partial


_REPLAY = object()   # no fault-model value: the hypothesis is scored against the no-event replay


def effective_obs(hyp, det, x, obs_row, anchor):
    """What the hypothesis predicts detector `det` reports on channel `x`, and its c.

    Incident/demand, and a fault on another detector: `_REPLAY`, i.e. the no-event Twin replay, so the
    residual stays (obs - twin)/sigma. A fault on this detector predicts its own value, which the
    actual observation is then scored against (report2 G.4: "the observations of that detector are
    scored under the fault model"):

    * stuck -> the last pre-t_on reading; None when there is no anchor for q/o (that channel leaves
      the identical support, as before);
    * zero  -> 0 for q and o; `_REPLAY` for v (v is undefined at zero flow, so the support and the
      v residual are unchanged);
    * noise -> `_REPLAY` (the actual observation against the replay) with c = 5 on this detector.
    """
    if hyp.family == "fault" and hyp.params.get("detector") == det:
        kind = hyp.params.get("type")
        if kind == "stuck":
            return _num((anchor or {}).get(det, {}).get(x)), 1.0
        if kind == "zero":
            return (0.0 if x in ("q", "o") else _REPLAY), 1.0
        return _REPLAY, NOISE_C
    return _REPLAY, 1.0


def block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor=None, weights=None):
    """Mean standardised residual of one (hypothesis, detector, block, channel) or (None, reason).

    The residual is (obs - prediction)/sigma: the prediction is the fault model's value on a faulting
    detector and the no-event replay everywhere else. A stuck or zero hypothesis therefore has to
    explain detector i's observed anomaly instead of erasing it.
    """
    s = sigma_of(sigma, det, x, weights)
    if s is None:
        return None, "no_sigma"
    total = 0.0
    for t in ts:
        obs_row = (obs_hist.get(det) or {}).get(t)
        if obs_row is None or not bool(_field(obs_row, "valid")):
            return None, "obs_invalid"
        if _field(obs_row, "q") is None or _field(obs_row, "o") is None:
            return None, "obs_null"
        obs = _num(_field(obs_row, x))
        pred, _c = effective_obs(hyp, det, x, obs_row, anchor)
        twin_row = ((replays.get(hyp.id) or {}).get(det) or {}).get(t)
        if twin_row is None:
            return None, "twin_null"
        w = _num(_field(twin_row, x))
        if pred is _REPLAY:
            pred = w                                   # (obs - twin_baseline) / sigma
        elif pred is None and x != "v":
            return None, "no_anchor"                   # stuck without a pre-t_on anchor
        if obs is None and x != "v":
            return None, ("no_anchor" if hyp.family == "fault" else "obs_null")
        total += 0.0 if (obs is None or pred is None) else (obs - pred) / s
    return total / len(ts), None


def _c_of(hyp, det):
    if hyp.family == "fault" and hyp.params.get("detector") == det:
        return float(hyp.params.get("c", 1.0))
    return 1.0


def logl_of_one(hyp, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=None, weights=None):
    """logL of a single hypothesis over its own support, and the size of that support.

    ``evaluate`` normalises a posterior over a library and needs a demand family for the gap and the
    EVR; scoring one hypothesis alone (check 2's deterministic-replay rescore) has no such family, so
    its log-likelihood is accumulated directly over the (detector, block, channel) triples whose
    residual is defined -- exactly the per-hypothesis sum ``evaluate`` performs.
    """
    complete, _partial = candidate_blocks(dets, times, t_on, t_end)
    ll, n_o = 0.0, 0
    for det in dets:
        c = _c_of(hyp, det)
        for _b, ts in sorted(complete.items()):
            for x in CHANNELS:
                r, _why = block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)
                if r is None:
                    continue
                ll += -0.5 * (r / c) ** 2 - math.log(c)
                n_o += 1
    return ll, n_o


@dataclass
class Evaluation:
    t: float
    hyps: list
    logL: dict
    log_post: dict
    post: dict
    sse: dict
    support: list
    excluded: dict
    h_star: str
    gap_vs_demand: float
    evr: float | None
    family_post: dict
    n_partial_blocks: int = 0
    adopted: bool = False
    forced: bool = False
    wall_s: float | None = None

    def hyp(self, hid):
        return next(h for h in self.hyps if h.id == hid)

    def rows(self):
        """The `hypotheses` list of event_log.jsonl: identical n_O for every hypothesis (check 3)."""
        n_o = len(self.support)
        return [{"id": h.id, "family": h.family, "params": dict(h.params), "prior": h.prior,
                 "logL": self.logL[h.id], "post": self.post[h.id], "n_O": n_o} for h in self.hyps]

    def to_log_row(self, state, t_on, wall_s=None):
        return {"t": float(self.t), "state": state, "t_on": None if t_on is None else float(t_on),
                "hypotheses": self.rows(), "h_star": self.h_star,
                "gap_vs_demand": self.gap_vs_demand, "evr": self.evr, "adopted": bool(self.adopted),
                "forced": bool(self.forced), "excluded": dict(self.excluded), "p_clear": None,
                "wall_s": self.wall_s if wall_s is None else wall_s}


def evaluate(hyps, dets, times, obs_hist, replays, sigma, t_on, t_end, anchor=None, weights=None,
             beta=BETA):
    """Identical-support residuals -> logL -> beta posterior -> h*, gap vs the demand family, EVR."""
    complete, partial = candidate_blocks(dets, times, t_on, t_end)
    excluded = Counter()
    if partial:
        excluded["partial_block"] = len(partial) * len(dets) * len(CHANNELS)
    cand = [(det, b, x, ts) for det in dets for b, ts in sorted(complete.items()) for x in CHANNELS]
    support, table = [], {}
    for det, b, x, ts in cand:
        reason = None
        for hyp in hyps:
            val, why = block_residual(hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)
            if val is None:
                reason = why
                break
        if reason is not None:
            excluded[reason] += 1
        else:
            support.append((det, b, x, ts))
    for det, b, x, ts in support:
        for hyp in hyps:
            table[(hyp.id, det, b, x)] = block_residual(
                hyp, det, ts, x, obs_hist, replays, sigma, anchor, weights)[0]
    logL, sse = {}, {}
    for hyp in hyps:
        ll, ss = 0.0, 0.0
        for det, b, x, _ts in support:
            r = table[(hyp.id, det, b, x)]
            c = _c_of(hyp, det)
            ll += -0.5 * (r / c) ** 2 - math.log(c)
            ss += r * r
        logL[hyp.id], sse[hyp.id] = ll, ss
    raw = {h.id: math.log(h.prior) + beta * logL[h.id] for h in hyps}
    m = max(raw.values())
    norm = m + math.log(sum(math.exp(v - m) for v in raw.values()))
    log_post = {k: v - norm for k, v in raw.items()}
    post = {k: math.exp(v) for k, v in log_post.items()}
    h_star = max(hyps, key=lambda h: (log_post[h.id], -hyps.index(h))).id
    demand = [h.id for h in hyps if h.family == "demand"]
    if demand:
        gap = log_post[h_star] - max(log_post[d] for d in demand)
        best_demand_sse = min(sse[d] for d in demand)
        evr = None if best_demand_sse <= 0 else 1.0 - sse[h_star] / best_demand_sse
    else:
        # the clearance library is active + H_clear(tau_c) only (no demand family): the adoption gap
        # and the EVR are undefined there, and clearance_analysis reads logL and the support only
        gap, evr = None, None
    family_post = {f: sum(post[h.id] for h in hyps if h.family == f) for f in FAMILIES}
    return Evaluation(t=float(t_end), hyps=list(hyps), logL=logL, log_post=log_post, post=post,
                      sse=sse, support=support, excluded=dict(excluded), h_star=h_star, gap_vs_demand=gap,
                      evr=evr, family_post=family_post, n_partial_blocks=len(partial))


def adoption_decision(ev, tau=TAU_LR):
    """h* in the incident family and log P(h*) - log max_demand P > ln 10.

    A library without a demand family (the clearance one) has no defined gap: no adoption.
    """
    if ev.gap_vs_demand is None:
        return False
    return bool(ev.hyp(ev.h_star).family == "incident" and ev.gap_vs_demand > tau)


def forced_adoption(ev, forced_id, tau=TAU_LR):
    """The labelled forced-adoption integration test (part B, "Integration coverage, all required").

    Treat ``forced_id`` as h* and the adoption threshold as met, so the downstream path (live
    replacement, EVENT_ASSIMILATION, clearance evaluation, RECOVERY, exit) is exercised when no
    natural adoption occurs. It is an integration test only and never evidence of inference: the
    evaluation keeps its own logL/posterior rows and is flagged ``forced``.
    """
    hyp = find_hypothesis(ev.hyps, forced_id)
    if hyp.family != "incident":
        raise ValueError(f"--event-force-hstar: {forced_id!r} is not an incident hypothesis")
    ev.h_star = hyp.id
    ev.gap_vs_demand = max(float(ev.gap_vs_demand), float(tau) + 1e-9)
    ev.adopted = True
    ev.forced = True
    return True


def demand_map(ev):
    """Highest-posterior demand member (the f written into m on a demand false alarm)."""
    dem = [h for h in ev.hyps if h.family == "demand"]
    return max(dem, key=lambda h: ev.log_post[h.id])


def clearance_posterior(logL_active, logL_clear, beta=BETA, p_active=0.5):
    """Priors 0.5 active / 0.5 spread over the clear hypotheses; returns the clear-family mass."""
    n = len(logL_clear)
    lp = [math.log(p_active) + beta * float(logL_active)]
    lp += [math.log((1.0 - p_active) / n) + beta * float(v) for v in logL_clear]
    m = max(lp)
    norm = m + math.log(sum(math.exp(v - m) for v in lp))
    posts = [math.exp(v - norm) for v in lp]
    return {"p_clear": float(sum(posts[1:])), "post_active": posts[0],
            "post_clear": posts[1:], "log_post": [v - norm for v in lp]}


def clearance_analysis(t, logL_active, logL_clear, taus=CLEAR_TAUS, beta=BETA):
    """The clearance evaluation row: the active hypothesis plus the five H_clear(tau_c)."""
    res = clearance_posterior(logL_active, logL_clear, beta=beta)
    hyps = [{"id": "active", "family": "active", "params": {}, "logL": float(logL_active),
             "post": res["post_active"]}]
    for tau, ll in zip(taus, logL_clear):
        hyps.append({"id": f"clear_{int(tau)}", "family": "clear", "params": {"tau_c": float(tau)},
                     "logL": float(ll), "post": None})
    for h, p in zip(hyps[1:], res["post_clear"]):
        h["post"] = float(p)
    best = int(max(range(len(logL_clear)), key=lambda i: logL_clear[i]))
    row = {"t": float(t), "state": EVENT, "t_on": None, "hypotheses": hyps, "h_star": "active",
           "gap_vs_demand": None, "evr": None, "adopted": False, "excluded": {}, "p_clear": res["p_clear"],
           "wall_s": None, "tau_c": float(taus[best]), "tau_c_best": float(taus[best])}
    return res, row


# --------------------------------------------------------------------------------- state machine
@dataclass
class Transition:
    t: float
    src: str
    dst: str
    reason: str

    def to_dict(self):
        return {"t": float(self.t), "from": self.src, "to": self.dst, "reason": self.reason}


class EventStateMachine:
    """NORMAL -> SUSPECTED_EVENT -> (EVENT_ASSIMILATION | DEGRADED | NORMAL) -> RECOVERY -> NORMAL.

    Every method returns the side-effect instructions the service must apply; the state itself is
    only advanced here. ``assim_mode`` and ``kappa_scale`` tell the NA-300 tick what to do with the
    frozen entry (reason `frozen`, DEGRADED's slow rule `degraded_slow`, or the RECOVERY ramp).
    """

    def __init__(self, onset_lag=PROVISIONAL_ONSET, delta=DELTA_S, suspected_period=SUSPECTED_PERIOD,
                 degraded_period=DEGRADED_PERIOD, event_period=EVENT_PERIOD, degraded_max=DEGRADED_MAX,
                 recovery_min=RECOVERY_MIN, recovery_ramp=RECOVERY_RAMP,
                 degraded_exit=DEGRADED_EXIT_EVAL):
        self.state = NORMAL
        self.t_state = None
        self.t_on = None
        self.t_alarm = None
        self.t_last_eval = None
        self.n_eval = 0
        self.demand_streak = 0
        self.clear_streak = 0
        self.masked = False
        self.frozen = False
        self.restriction = None       # dict set by the service when an incident is adopted
        self.active_hyp = None
        self.downweight = {}
        self.t_adopt = None
        self.t_recovery = None
        self.b_ok_since = None
        self.false_alarms = []
        self.unexplained = []
        self.onset_lag = float(onset_lag)
        self.delta = float(delta)
        self.suspected_period = float(suspected_period)
        self.degraded_period = float(degraded_period)
        self.event_period = float(event_period)
        self.degraded_max = float(degraded_max)
        self.recovery_min = float(recovery_min)
        self.recovery_ramp = float(recovery_ramp)
        if degraded_exit not in DEGRADED_EXITS:
            raise ValueError(f"unknown degraded_exit {degraded_exit!r}; expected {DEGRADED_EXITS}")
        self.degraded_exit = degraded_exit
        self.transitions = []

    # -- bookkeeping
    def _go(self, t, dst, reason):
        tr = Transition(float(t), self.state, dst, reason)
        self.transitions.append(tr)
        self.state = dst
        self.t_state = float(t)
        return tr

    def _start_episode(self, t):
        self.t_alarm = float(t)
        self.t_on = float(t) - self.onset_lag
        self.n_eval = 0
        self.demand_streak = 0
        self.clear_streak = 0
        self.frozen = True
        self.restriction = None
        self.active_hyp = None
        self.t_adopt = None
        self.t_recovery = None
        self.b_ok_since = None
        self.t_last_eval = None
        return self._go(t, SUSPECTED, "trigger_alarm")

    # -- trigger tick (30 s)
    def trigger(self, t, alarm, o_u=None, o_d=None):
        out = {"transitions": [], "unmask": False}
        if self.masked and o_u is not None and o_d is not None and o_u < O_CRIT and o_d < O_CRIT:
            self.masked = False
            out["unmask"] = True
        if alarm and not self.masked and self.state in (NORMAL, RECOVERY):
            out["transitions"].append(self._start_episode(t))
        return out

    # -- evaluation cadence
    def period(self):
        return {SUSPECTED: self.suspected_period, DEGRADED: self.degraded_period,
                EVENT: self.event_period}.get(self.state)

    def due(self, t):
        p = self.period()
        if p is None:
            return False
        return self.t_last_eval is None or (float(t) - self.t_last_eval) >= p - 1e-9

    def next_eval_at(self, t):
        p = self.period()
        if p is None:
            return None
        return float(t) if self.t_last_eval is None else self.t_last_eval + p

    # -- hypothesis evaluation (SUSPECTED_EVENT, DEGRADED)
    def on_hypotheses(self, t, ev, adopted=False):
        t = float(t)
        out = {"transitions": [], "freeze": False, "unfreeze": False, "write_m": None, "adopt": None,
               "downweight": None, "log_false_alarm": None, "log_unexplained": None}
        self.t_last_eval = t
        if self.state == SUSPECTED:
            self.n_eval += 1
            if adopted:
                self.active_hyp = ev.h_star
                self.t_adopt = t
                out["adopt"] = ev.h_star
                out["transitions"].append(self._go(t, EVENT, f"adopted_{ev.h_star}"))
                return out
            if ev.family_post.get("demand", 0.0) > P_DEMAND_THRESHOLD:
                self.demand_streak += 1
            else:
                self.demand_streak = 0
            if self.demand_streak >= 2:
                h = demand_map(ev)
                out["write_m"] = float(h.params["factor"])
                out["unfreeze"] = True
                self.frozen = False
                out["log_false_alarm"] = {"t": t, "factor": out["write_m"], "hyp": h.id}
                self.false_alarms.append(out["log_false_alarm"])
                out["transitions"].append(self._go(t, NORMAL, f"false_alarm_demand_f{h.params['factor']:g}"))
                return out
            h = ev.hyp(ev.h_star)
            if h.family == "fault":
                det = h.params["detector"]
                out["downweight"] = det
                self.downweight[det] = DEFAULT_DOWNWEIGHT
                out["unfreeze"] = True
                self.frozen = False
                out["transitions"].append(self._go(t, NORMAL, f"detector_fault_{det}_{h.params['type']}"))
                return out
            if self.n_eval >= 3:
                out["transitions"].append(self._go(t, DEGRADED, "unresolved_3_evals"))
            return out
        if self.state == DEGRADED:
            if adopted:
                self.active_hyp = ev.h_star
                self.t_adopt = t
                out["adopt"] = ev.h_star
                out["transitions"].append(self._go(t, EVENT, f"adopted_{ev.h_star}"))
                return out
            if (self.degraded_exit == DEGRADED_EXIT_EVAL and self.t_state is not None
                    and (t - self.t_state) > self.degraded_max):
                out["unfreeze"] = True
                self.frozen = False
                out["log_unexplained"] = {"t": t, "seconds": t - self.t_state}
                self.unexplained.append(out["log_unexplained"])
                out["transitions"].append(self._go(t, NORMAL, "unexplained_anomaly"))
            return out
        return out

    # -- DEGRADED bound, scheduled independently of evaluations (pilot 2)
    def degraded_tick(self, t):
        """Leave DEGRADED at exactly entry + degraded_max, whether or not an evaluation is due.

        Only active with ``degraded_exit="scheduled"`` (the pilot-2 variant); with the pilot-1 default
        this is inert and the bound is still applied inside ``on_hypotheses``.
        """
        t = float(t)
        out = {"transitions": [], "unfreeze": False, "log_unexplained": None}
        if (self.degraded_exit != DEGRADED_EXIT_SCHEDULED or self.state != DEGRADED
                or self.t_state is None):
            return out
        if t - self.t_state >= self.degraded_max - 1e-9:
            out["unfreeze"] = True
            self.frozen = False
            out["log_unexplained"] = {"t": t, "seconds": t - self.t_state}
            self.unexplained.append(out["log_unexplained"])
            out["transitions"].append(self._go(t, NORMAL, "unexplained_anomaly"))
        return out

    # -- clearance evaluation (EVENT_ASSIMILATION)
    def on_clearance(self, t, p_clear, tau_c=None):
        t = float(t)
        out = {"transitions": [], "clear": None}
        self.t_last_eval = t
        if self.state != EVENT:
            return out
        self.clear_streak = self.clear_streak + 1 if p_clear > P_CLEAR_THRESHOLD else 0
        if self.clear_streak >= 2:
            out["clear"] = {"tau_c": None if tau_c is None else float(tau_c)}
            self.masked = True
            self.frozen = False
            self.restriction = None
            self.t_recovery = t
            self.b_ok_since = None
            out["transitions"].append(self._go(t, RECOVERY, "cleared_two_consecutive"))
        return out

    # -- RECOVERY tick (60 s): exit conditions
    def recovery_tick(self, t, o_u, o_d, b):
        t = float(t)
        out = {"transitions": []}
        if self.state != RECOVERY or self.t_recovery is None:
            return out
        if b is None or float(b) >= B_EXIT:
            self.b_ok_since = None
        elif self.b_ok_since is None:
            self.b_ok_since = t
        if ((t - self.t_recovery) >= self.recovery_min and self.b_ok_since is not None
                and (t - self.b_ok_since) >= self.recovery_min
                and o_u is not None and o_d is not None and o_u < O_CRIT and o_d < O_CRIT):
            out["transitions"].append(self._go(t, NORMAL, "recovery_complete"))
        return out

    # -- what the NA-300 tick does to the frozen entry
    def assim_mode(self):
        if self.state == DEGRADED and self.frozen:
            return "slow"
        if self.frozen:
            return "frozen"
        return "normal"

    def kappa_scale(self, t):
        if self.state == RECOVERY and self.t_recovery is not None:
            return max(0.0, min(1.0, (float(t) - self.t_recovery) / self.recovery_ramp))
        if self.state == DEGRADED:
            return DEGRADED_KAPPA
        return 1.0

    def delta_scale(self):
        return DEGRADED_DELTA if self.state == DEGRADED else 1.0

    def snapshot(self):
        return {"state": self.state, "t_on": self.t_on, "t_alarm": self.t_alarm,
                "n_eval": self.n_eval, "masked": self.masked, "frozen": self.frozen,
                "downweight": dict(self.downweight), "restriction": self.restriction,
                "active_hyp": self.active_hyp, "t_adopt": self.t_adopt, "t_recovery": self.t_recovery,
                "false_alarms": len(self.false_alarms), "unexplained": len(self.unexplained)}
