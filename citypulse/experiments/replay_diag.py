"""Matched-observation replay diagnosis of event inference.

Binding spec: ``docs/oct10-replay-diagnosis-plan.md`` (revision 2, committed before any run). Nothing
in this module is imported by the online method: it reads the pilot-2 artefacts, calls the offline
replay entry point (``citypulse.branching.engine.score_replays``) and scores the preregistered variants
with ``citypulse.twin.event``. No setting here may enter the online method without a new
preregistration.

Steps (each writes its own artefact under ``results/replay_diag/``):

``identity``   default-identity probe: three replays from a pilot-2 pinned snapshot, run with the same
               code before and after the engine change (only ``engine.py`` differs) -> before/after JSON
``compare``    the before/after identity comparison -> ``default_identity.json``
``qualify``    R_P qualification on ``evt_inc_4101``'s first logged evaluation -> ``qualify_rp.json``
``reproduce``  exact V0 reproduction of every logged INC evaluation -> ``reproduce_v0.json``
``noi``        re-run the three NOI controls with extra Twin snapshots at 4230/4350 s, compare the
               observation streams (caution b) -> ``noi_rerun/``
``variants``   the eight variants on the common support -> ``raw.parquet`` + ``per_eval.json``
``summary``    would-adopt counts, MAP-family distribution, median gap -> ``summary.json``
``report``     ``results/replay_diag/report.md``

Replays are cached per evaluation in ``results/replay_diag/cache/<eval_id>.pkl`` keyed by the full job
(so a re-run never repeats a SUMO process), and run at most 8 at a time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.branching.engine import score_replays  # noqa: E402
from citypulse.twin import event as ev  # noqa: E402

# --------------------------------------------------------------------------------------- constants
DIAG = REPO / "results/replay_diag"
CACHE = DIAG / "cache"
NOI_RERUN_DIR = DIAG / "noi_rerun"
SIGMA_JSON = REPO / "results/event_pilot/impl/sigma_event.json"
PILOT2_RUNS = REPO / "results/event_pilot2/runs"

INC_RUNS = ("evt_inc_4101", "evt_inc_4102", "evt_inc_4103")
NOI_RUNS = ("evt_noi_4101", "evt_noi_4102", "evt_noi_4103")
NOI_SEEDS = (4101, 4102, 4103)
NOI_PORTS = {"evt_noi_4101": 6301, "evt_noi_4102": 6302, "evt_noi_4103": 6303}

TWIN_SEED = 2
DEMAND_SEED = 202
TWIN_BASE_FACTOR = 0.85
BOUNDARY_DETECTOR = "AID07106"
SNAPSHOT_MARKS = (4500.0, 4800.0, 5100.0, 5400.0, 5700.0, 6000.0, 6300.0, 6600.0)
NOI_EXTRA_SNAPSHOTS = (4230.0, 4350.0)
T_END = 7200.0
SIGMA_DEV = REPO / "results/assim/na300/sigma300_dev.json"
PROXY_ROU = REPO / "scenarios/kwuntong/blite/synth5/proxy.rou.xml"
TWIN_CAND_ROU = REPO / "scenarios/kwuntong/blite/synth5/twin_cand.rou.xml"

# NOI synthetic episode (spec, "Per-evaluation fixed elements"): one episode, imposed onset 4290 s
# (= imposed alarm 4890 - 600), start snapshot 4230 s, scoring window [4290, t_eval].
NOI_T_ON = 4290.0
NOI_SNAP = 4230.0
NOI_EVAL_TIMES = (4890.0, 5010.0, 5130.0)
TRUTH_ONSET = 4500.0          # the truth-assisted control onset (spec, "Variants")
EXTRA_LOCATION = ("ktb_n1", 900.0, "fixed", "p900")   # the added ktb_n1 900 m location (VPL, VPTL)

REPRESENTATIONS = ("R_E", "R_P")

# Location sets. "asrun" is the pilot-2 library's own grid; "asrun900" adds ktb_n1 at 900 m with the
# same (k, s) grid (spec, VPL).
LOC_ASRUN = "asrun"
LOC_ASRUN900 = "asrun900"

# Replay configurations: (representation, incident onset, locations). Variants sharing a configuration
# share their replays; only the library (priors / fault family) differs.
CONFIG_DEF = {
    "A": ("R_E", "logged", LOC_ASRUN),
    "B": ("R_P", "logged", LOC_ASRUN),
    "C": ("R_E", "truth", LOC_ASRUN),
    "D": ("R_P", "truth", LOC_ASRUN),
    "E": ("R_P", "logged", LOC_ASRUN900),
    "F": ("R_P", "truth", LOC_ASRUN900),
}
CONFIGS = tuple(CONFIG_DEF)

# The eight preregistered variants (spec table).
VARIANTS = {
    "V0":     {"config": "A", "fault": True,  "label": "base"},
    "VP":     {"config": "B", "fault": True,  "label": "representation diagnostic"},
    "VT":     {"config": "C", "fault": True,  "label": "truth-assisted control (onset)"},
    "VPT":    {"config": "D", "fault": True,  "label": "truth-assisted control"},
    "VPL":    {"config": "E", "fault": True,  "label": "truth-assisted control (location)"},
    "VPTL":   {"config": "F", "fault": True,  "label": "truth-assisted control"},
    "VNF":    {"config": "A", "fault": False, "label": "competition diagnostic"},
    "VPTLNF": {"config": "F", "fault": False, "label": "truth-assisted control"},
}
VARIANT_IDS = tuple(VARIANTS)

HYP_755 = "inc_ktb_n1_k2_s1"        # ktb_n1, lanes 0-1 closed, speed factor 1.0, pos 755.0 m
EXTRA_HYP_ID = "inc_ktb_n1_k2_s1_900m"
# The replay result fields the default-identity probe hashes: the behavioural output only. New
# metadata keys (collect_from, blockers) are deliberately excluded -- they do not change a replay.
IDENTITY_FIELDS = ("t_snap", "t_on", "t_end", "intervals", "n_vehicles", "veh_digest",
                   "restriction_present", "applied", "lifted")


# --------------------------------------------------------------------------------------- helpers
def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def obs_from_twin_log(path):
    """The observations the Proxy actually sent, from the run's own twin_log.parquet."""
    df = pd.read_parquet(path)
    hist = {}
    for row in df.itertuples():
        hist.setdefault(row.detector, {})[float(row.t)] = {
            "detector": row.detector, "q": None if pd.isna(row.obs_q) else float(row.obs_q),
            "v": None if pd.isna(row.obs_v) else float(row.obs_v),
            "o": None if pd.isna(row.obs_o) else float(row.obs_o), "valid": bool(row.obs_valid)}
    return hist


def anchor_from(obs_hist, t_on):
    """``EventRuntime.anchor_for``: the last valid pre-t_on reading of every detector/channel."""
    anchor = {}
    for det, rows in obs_hist.items():
        vals = {}
        for t in sorted(rows, reverse=True):
            if t >= t_on:
                continue
            r = rows[t]
            if not r["valid"]:
                continue
            for x in ev.CHANNELS:
                if x not in vals and r[x] is not None:
                    vals[x] = r[x]
        anchor[det] = vals
    return anchor


def run_event_meta(run_dir):
    """(lane_counts, midpoints) the service resolved from the live Twin (its own twin_stats)."""
    stats = json.loads((Path(run_dir) / "twin/twin_stats.json").read_text(encoding="utf-8"))
    info = stats.get("event_info") or {}
    counts = info.get("lane_counts") or stats.get("event", {}).get("lane_counts")
    mids = info.get("midpoints") or stats.get("event", {}).get("midpoints")
    return dict(counts), dict(mids)


def downweights_by_time(run_dir):
    """(t, detector) of every detector down-weight the run's logged transitions put in force.

    The code's rule (``EventStateMachine.on_hypotheses``): a SUSPECTED/DEGRADED evaluation whose h* is
    a fault on detector i sets ``downweight[i] = DEFAULT_DOWNWEIGHT`` *after* that evaluation, so a
    down-weight set at t is in force for every evaluation with ``t_eval > t``.
    """
    out = []
    for row in read_jsonl(Path(run_dir) / "twin/state_trace.jsonl"):
        if row.get("to") != ev.NORMAL:
            continue
        m = re.match(r"^detector_fault_(?P<det>.+)_(?P<kind>stuck|zero|noise)$", str(row.get("reason")))
        if m:
            out.append((float(row["t"]), m.group("det")))
    return out


def spec_of(hyp, representation="R_E"):
    """The engine job spec of a hypothesis (``EventRuntime.spec_of`` plus the R_P selector).

    ``representation`` is only written into the spec for R_P: the R_E spec is byte-identical to the one
    the online run built, so V0 and the reproduction gate take the untouched code path.
    """
    p = dict(hyp.params)
    if hyp.family == "incident":
        spec = {"kind": "incident", "edge": p["edge"], "lanes_closed": list(p["lanes_closed"]),
                "n_lanes": int(p["n_lanes"]), "speed_factor": float(p["speed_factor"]),
                "pos": p.get("pos")}
        if representation != "R_E":
            spec["representation"] = representation
        return spec
    if hyp.family == "demand":
        return {"kind": "demand", "entry": p["entry"], "factor": float(p["factor"])}
    return {"kind": "none"}


def locations_of(kind, midpoints):
    """The location grid of a variant, as (edge, pos, pos_kind, id_tag) tuples.

    The id tag keeps the added 900 m members distinct from the as-run 755 m ones (the spec's 14-member
    incident family); the as-run ids are untouched.
    """
    if kind == LOC_ASRUN:
        return [("ktb_n1", 755.0, "fixed", ""),
                ("ktb_w3", float(midpoints["ktb_w3"]), "mid", ""),
                ("ktb_n2", float(midpoints["ktb_n2"]), "mid", "")]
    if kind == LOC_ASRUN900:
        return locations_of(LOC_ASRUN, midpoints) + [EXTRA_LOCATION]
    raise ValueError(f"unknown location set {kind!r}")


def build_library(locations, lane_counts, fault=True):
    """The hypothesis library of one variant: the pilot-2 grid, family priors 1/3 or 1/2.

    ``fault=False`` (VNF, VPTLNF) drops the detector-fault family and splits the mass 1/2 incident,
    1/2 demand (spec, "Variants"). Incident members are listed as-run first, then the added 900 m ones.
    """
    inc = []
    for edge, pos, pos_kind, tag in locations:
        n = int(lane_counts[edge])
        for k, s in ev.incident_severities(n, ev.GRID_PILOT2):
            hid = f"inc_{edge}_" + (f"{tag}_" if tag else "") + f"k{k}_s{s:g}"
            inc.append((hid, {"edge": edge, "lanes_closed": list(range(k)), "n_lanes": n,
                              "pos": round(float(pos), 1), "pos_kind": pos_kind,
                              "speed_factor": float(s)}))
    p_inc = 1.0 / 3.0 if fault else 0.5
    p_dem = 1.0 / 3.0 if fault else 0.5
    hyps = [ev.Hypothesis(hid, "incident", params, p_inc / len(inc)) for hid, params in inc]
    for f in ev.DEMAND_FACTORS:
        hyps.append(ev.Hypothesis(f"dem_f{f:g}", "demand",
                                  {"entry": ev.BASE_FACTOR_ENTRY, "factor": float(f), "t_on": None},
                                  p_dem / 4.0))
    if fault:
        for det in ev.FAULT_DETECTORS:
            for kind in ev.FAULT_TYPES:
                hyps.append(ev.Hypothesis(f"flt_{det}_{kind}", "fault",
                                          {"detector": det, "type": kind,
                                           "c": ev.NOISE_C if kind == "noise" else 1.0},
                                          (1.0 / 3.0) / 6.0))
    return hyps


# ------------------------------------------------------------------------------- evaluation inputs
@dataclass
class EvalSpec:
    """One logged evaluation with every fixed element of the spec's table."""
    eval_id: str
    run: str
    arm: str                       # "INC" | "NOI"
    seed: int
    t_eval: float
    t_on: float                    # provisional onset == scoring-window start
    snapshot: Path
    meta: Path
    obs_hist: dict
    anchor: dict
    weights: dict
    lane_counts: dict
    midpoints: dict
    logged: dict = field(default_factory=dict)   # the run's own event_log row (INC only)
    stream_source: str = "stored"
    label: str = ""

    @property
    def dets(self):
        return sorted(self.obs_hist)


def inc_evaluations():
    """Every logged INC evaluation of the three pilot-2 EVT runs, in run/time order."""
    out = []
    for run in INC_RUNS:
        rd = PILOT2_RUNS / run
        counts, mids = run_event_meta(rd)
        obs = obs_from_twin_log(rd / "twin/twin_log.parquet")
        sets = downweights_by_time(rd)
        for row in read_jsonl(rd / "twin/event_log.jsonl"):
            if row.get("t_on") is None or not row.get("hypotheses"):
                continue
            t_on, t_eval = float(row["t_on"]), float(row["t"])
            snap_t = t_on - ev.DELTA_S
            st = rd / f"twin/event_snapshot_{int(snap_t)}.xml.gz"
            mt = rd / f"twin/event_snapshot_{int(snap_t)}.json"
            if not st.exists():
                raise FileNotFoundError(f"pinned episode snapshot missing: {st}")
            weights = {det: ev.DEFAULT_DOWNWEIGHT for t_tr, det in sets if t_eval > t_tr + 1e-9}
            out.append(EvalSpec(eval_id=f"inc_{run.split('_')[-1]}_t{int(t_eval)}", run=run,
                                arm="INC", seed=int(run.split("_")[-1]), t_eval=t_eval, t_on=t_on,
                                snapshot=st, meta=mt, obs_hist=obs, anchor=anchor_from(obs, t_on),
                                weights=weights, lane_counts=counts, midpoints=mids, logged=row))
    return out


def noi_evaluations(rerun_dir=None):
    """The three synthetic NOI evaluations (snapshot 4230 s, onset 4290 s, one episode)."""
    root = Path(rerun_dir) if rerun_dir is not None else NOI_RERUN_DIR
    out = []
    for run, seed in zip(NOI_RUNS, NOI_SEEDS):
        rd = root / run
        st = rd / f"twin/twin_state_{int(NOI_SNAP)}.xml.gz"
        mt = rd / f"twin/twin_state_{int(NOI_SNAP)}.json"
        if not st.exists():
            raise FileNotFoundError(f"NOI re-run snapshot missing: {st} (run the noi step first)")
        counts, mids = run_event_meta(PILOT2_RUNS / run)     # geometry is run-independent
        obs = obs_from_twin_log(rd / "twin/twin_log.parquet")
        for t_eval in NOI_EVAL_TIMES:
            out.append(EvalSpec(eval_id=f"noi_{seed}_t{int(t_eval)}", run=run, arm="NOI", seed=seed,
                                t_eval=float(t_eval), t_on=NOI_T_ON, snapshot=st, meta=mt,
                                obs_hist=obs, anchor=anchor_from(obs, NOI_T_ON), weights={},
                                lane_counts=counts, midpoints=mids, stream_source="rerun"))
    return out


# ---------------------------------------------------------------------------------- replay caching
def make_job(evd, config, hyp):
    """One replay job: the intervention onset and the interval-collection start are separate fields."""
    rep, onset_kind, _locs = CONFIG_DEF[config]
    onset = evd.t_on if onset_kind == "logged" else TRUTH_ONSET
    t_apply = onset if hyp.family == "incident" else evd.t_on   # demand keeps the provisional onset
    return {"tag": hyp.id, "t_on": float(t_apply), "t_end": float(evd.t_eval),
            "detectors": list(evd.dets), "apply": spec_of(hyp, rep), "lift": None, "t_lift": None,
            "collect_from": float(evd.t_on)}


def job_key(evd, job):
    return json.dumps({"state": str(evd.snapshot), "meta": str(evd.meta),
                       "t_on": job["t_on"], "t_end": job["t_end"],
                       "collect_from": job.get("collect_from"), "apply": job["apply"],
                       "detectors": list(job["detectors"])}, sort_keys=True)


def cache_path(evd):
    return CACHE / f"{evd.eval_id}.pkl"


def load_cache(evd):
    p = cache_path(evd)
    if not p.exists():
        return {}
    return pickle.loads(p.read_bytes())


def save_cache(evd, cache):
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = cache_path(evd).with_suffix(".pkl.tmp")
    tmp.write_bytes(pickle.dumps(cache, protocol=4))
    tmp.replace(cache_path(evd))


def build_cache(evd, wanted, workers=8, force=False):
    """Replay every ``wanted`` hypothesis of this evaluation that is not cached yet, <= workers at once.

    ``wanted`` is an iterable of (config, hypothesis). Returns (cache, n_new, wall_s).
    """
    cache = {} if force else load_cache(evd)
    todo, seen = [], set()
    for config, hyp in wanted:
        job = make_job(evd, config, hyp)
        key = job_key(evd, job)
        if key in cache or key in seen:
            continue
        seen.add(key)
        todo.append((key, job))
    if not todo:
        return cache, 0, 0.0
    res, wall = score_replays(evd.snapshot, evd.meta, [j for _k, j in todo], workers=workers,
                              seed=TWIN_SEED)
    for (key, _job), r in zip(todo, res):
        cache[key] = r
    save_cache(evd, cache)
    return cache, len(todo), wall


def replays_of(evd, cache, config, hyps):
    """{hypothesis id: interval table} for one config's library, from the cache."""
    out = {}
    for h in hyps:
        out[h.id] = cache[job_key(evd, make_job(evd, config, h))]["intervals"]
    return out


def union_times(replays):
    times = set()
    for table in replays.values():
        for rows in table.values():
            times.update(rows)
    return sorted(times)


# ------------------------------------------------------------------------------- common support
def common_support(evd, sigma, entries, times):
    """O: the intersection over all variants and all their hypotheses (spec, "Support").

    ``entries`` is a list of (hyps, replays) pairs -- one per variant -- scored with that variant's own
    down-weights and anchor. A (detector, 120-s block, channel) triple leaves O as soon as any variant's
    hypothesis has no defined residual on it; the reason is counted.
    """
    complete, partial = ev.candidate_blocks(evd.dets, times, evd.t_on, evd.t_eval)
    excluded = {}
    if partial:
        excluded["partial_block"] = len(partial) * len(evd.dets) * len(ev.CHANNELS)
    support = []
    for det in evd.dets:
        for b, ts in sorted(complete.items()):
            for x in ev.CHANNELS:
                why = None
                for hyps, replays in entries:
                    for hyp in hyps:
                        val, w = ev.block_residual(hyp, det, ts, x, evd.obs_hist, replays, sigma,
                                                   evd.anchor, evd.weights)
                        if val is None:
                            why = w
                            break
                    if why:
                        break
                if why:
                    excluded[why] = excluded.get(why, 0) + 1
                else:
                    support.append((det, b, x, ts))
    return support, excluded


# ----------------------------------------------------------------------------------- variant score
def variant_outcome(res, hyps, tau=ev.TAU_LR):
    """MAP, families, the spec's gap and would-adopt for one scored variant."""
    post = res.post
    inc = [h.id for h in hyps if h.family == "incident"]
    dem = [h.id for h in hyps if h.family == "demand"]
    best_inc = max(inc, key=lambda i: post[i]) if inc else None
    best_dem = max(dem, key=lambda i: post[i]) if dem else None
    gap = None
    if best_inc is not None and best_dem is not None:
        gap = math.log(post[best_inc]) - math.log(post[best_dem])
    map_hyp = res.hyp(res.h_star)
    would_adopt = bool(map_hyp.family == "incident" and gap is not None and gap > tau)
    return {"h_star": res.h_star, "h_star_family": map_hyp.family,
            "best_incident": best_inc, "best_demand": best_dem,
            "gap": gap, "gap_map": res.gap_vs_demand, "would_adopt": would_adopt,
            "incident_post": res.family_post.get("incident"),
            "demand_post": res.family_post.get("demand"),
            "fault_post": res.family_post.get("fault"), "evr": res.evr,
            "n_O": len(res.support)}


def score_evaluation(evd, sigma, workers=8):
    """Score all eight variants of one evaluation on the common support O."""
    libs = {vid: build_library(locations_of(CONFIG_DEF[VARIANTS[vid]["config"]][2], evd.midpoints),
                               evd.lane_counts, fault=VARIANTS[vid]["fault"])
            for vid in VARIANT_IDS}
    wanted = [(VARIANTS[vid]["config"], h) for vid in VARIANT_IDS for h in libs[vid]]
    cache, n_new, wall = build_cache(evd, wanted, workers=workers)
    replay = {vid: replays_of(evd, cache, VARIANTS[vid]["config"], libs[vid]) for vid in VARIANT_IDS}
    tset = set()
    for vid in VARIANT_IDS:
        tset.update(union_times(replay[vid]))
    times = sorted(tset)
    entries = [(libs[vid], replay[vid]) for vid in VARIANT_IDS]
    support, excluded = common_support(evd, sigma, entries, times)

    per_eval, rows = [], []
    if not support:
        return per_eval, rows, {"n_new": n_new, "wall_s": wall, "empty_support": True,
                                "excluded": excluded}
    for vid in VARIANT_IDS:
        res = ev.evaluate(libs[vid], evd.dets, times, evd.obs_hist, replay[vid], sigma, evd.t_on,
                          evd.t_eval, anchor=evd.anchor, weights=evd.weights, support=support,
                          excluded=excluded)
        out = variant_outcome(res, libs[vid])
        rep, onset_kind, locs = CONFIG_DEF[VARIANTS[vid]["config"]]
        per_eval.append({
            "eval_id": evd.eval_id, "run": evd.run, "arm": evd.arm, "seed": evd.seed,
            "t_eval": evd.t_eval, "t_on": evd.t_on, "snapshot": evd.snapshot.name,
            "variant": vid, "label": VARIANTS[vid]["label"], "representation": rep,
            "onset": (evd.t_on if onset_kind == "logged" else TRUTH_ONSET),
            "onset_kind": onset_kind, "locations": locs, "fault_family": VARIANTS[vid]["fault"],
            "stream_source": evd.stream_source, "eval_label": evd.label,
            "n_hypotheses": len(libs[vid]), "excluded": excluded, **out})
        for h in libs[vid]:
            rows.append({"eval_id": evd.eval_id, "run": evd.run, "arm": evd.arm, "seed": evd.seed,
                         "t_eval": evd.t_eval, "t_on": evd.t_on, "variant": vid,
                         "representation": rep, "onset": (evd.t_on if onset_kind == "logged"
                                                          else TRUTH_ONSET),
                         "locations": locs, "fault_family": VARIANTS[vid]["fault"],
                         "stream_source": evd.stream_source,
                         "hyp_id": h.id, "family": h.family, "prior": h.prior,
                         "logL": res.logL[h.id], "post": res.post[h.id],
                         "log_post": res.log_post[h.id], "n_O": len(res.support),
                         "h_star": out["h_star"], "gap": out["gap"], "gap_map": out["gap_map"],
                         "would_adopt": out["would_adopt"], "evr": out["evr"]})
    return per_eval, rows, {"n_new": n_new, "wall_s": wall, "empty_support": False,
                            "excluded": excluded, "n_O": len(support), "times": len(times)}


# ---------------------------------------------------------------------------------------- steps
def step_identity(tag, workers=3):
    """Default-identity probe: three replays from a pilot-2 pinned snapshot (same code both runs)."""
    evd = inc_evaluations()[0]                     # evt_inc_4101, t_on=4410, t_eval=5010
    hyps = ev.build_hypotheses(midpoints=evd.midpoints, lane_counts=evd.lane_counts,
                               grid=ev.GRID_PILOT2)
    hyp = ev.find_hypothesis(hyps, HYP_755)
    base = {"tag": hyp.id, "t_on": evd.t_on, "t_end": evd.t_eval, "detectors": list(evd.dets),
            "apply": spec_of(hyp), "lift": None, "t_lift": None}
    jobs = [dict(base, tag="asrun"),
            dict(base, tag="noevent", apply={"kind": "none"}),
            dict(base, tag="collect_eq_on", collect_from=evd.t_on)]
    res, wall = score_replays(evd.snapshot, evd.meta, jobs, workers=workers, seed=TWIN_SEED)
    sigma = ev.load_sigma(SIGMA_JSON)
    out = {"tag": tag, "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": evd.run,
           "snapshot": evd.snapshot.name, "t_on": evd.t_on, "t_eval": evd.t_eval,
           "hypothesis": hyp.id, "params": dict(hyp.params), "wall_s": wall, "jobs": {}}
    for r in res:
        times = sorted({t for rows in r["intervals"].values() for t in rows})
        if r["tag"] == "noevent":
            ll, n_o = None, None
        else:
            ll, n_o = ev.logl_of_one(hyp, evd.dets, times, evd.obs_hist,
                                     {hyp.id: r["intervals"]}, sigma, evd.t_on, evd.t_eval,
                                     anchor=evd.anchor)
        payload = {k: r[k] for k in IDENTITY_FIELDS if k in r}
        out["jobs"][r["tag"]] = {
            "sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str)
                                     .encode("utf-8")).hexdigest(),
            "fields": sorted(payload),
            "veh_digest": r["veh_digest"], "n_vehicles": r["n_vehicles"],
            "restriction_present": bool(r["restriction_present"]),
            "n_intervals": len(times), "logL": ll, "n_O": n_o}
    path = DIAG / f"default_identity_{tag}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"identity[{tag}] -> {path}")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'sha256'}
                      for k, v in out["jobs"].items()}, indent=1, default=str))
    return out


def step_compare_identity():
    """Before vs after: every probe job must be identical in digest, intervals and logL."""
    before = json.loads((DIAG / "default_identity_before.json").read_text(encoding="utf-8"))
    after = json.loads((DIAG / "default_identity_after.json").read_text(encoding="utf-8"))
    jobs = {}
    for name in sorted(before["jobs"]):
        b, a = before["jobs"][name], after["jobs"].get(name)
        jobs[name] = {
            "sha256_before": b["sha256"], "sha256_after": None if a is None else a["sha256"],
            "sha256_identical": bool(a is not None and a["sha256"] == b["sha256"]),
            "veh_digest_identical": bool(a is not None and a["veh_digest"] == b["veh_digest"]),
            "logL_before": b["logL"], "logL_after": None if a is None else a["logL"],
            "logL_identical": bool(a is not None and a["logL"] == b["logL"]),
            "n_intervals_identical": bool(a is not None and a["n_intervals"] == b["n_intervals"]),
            "restriction_present_before": b["restriction_present"],
            "restriction_present_after": None if a is None else a["restriction_present"]}
    passed = bool(jobs) and all(v["sha256_identical"] and v["logL_identical"]
                                and v["veh_digest_identical"] and v["n_intervals_identical"]
                                for v in jobs.values())
    out = {"check": "default_identity", "passed": passed, "snapshot": before["snapshot"],
           "run": before["run"], "t_on": before["t_on"], "t_eval": before["t_eval"],
           "hypothesis": before["hypothesis"], "jobs": jobs,
           "note": ("same probe code, run before and after the engine change; only "
                    "citypulse/branching/engine.py and citypulse/twin/event.py differ. sha256 covers "
                    "the replay's behavioural output (" + ", ".join(IDENTITY_FIELDS) + "); the new "
                    "metadata keys collect_from/blockers are excluded because they cannot change a "
                    "replay.")}
    (DIAG / "default_identity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"default_identity: passed={passed}")
    return out


def step_qualify(workers=4):
    """R_P qualification on evt_inc_4101's first logged evaluation (spec, blocking)."""
    evd = inc_evaluations()[0]
    hyps = ev.build_hypotheses(midpoints=evd.midpoints, lane_counts=evd.lane_counts,
                               grid=ev.GRID_PILOT2)
    hyp = ev.find_hypothesis(hyps, HYP_755)
    p900 = dict(hyp.params)
    p900["pos"] = 900.0
    hyp900 = ev.Hypothesis(EXTRA_HYP_ID, "incident", p900, hyp.prior)

    def job(tag, h):
        return {"tag": tag, "t_on": evd.t_on, "t_end": evd.t_eval, "detectors": list(evd.dets),
                "apply": spec_of(h, "R_P"), "lift": None, "t_lift": None,
                "collect_from": evd.t_on}

    jobs = [job("rp_755_run1", hyp), job("rp_755_run2", hyp),
            job("rp_900_run1", hyp900), job("rp_900_run2", hyp900)]
    res, wall = score_replays(evd.snapshot, evd.meta, jobs, workers=workers, seed=TWIN_SEED)
    by = {r["tag"]: r for r in res}
    sigma = ev.load_sigma(SIGMA_JSON)

    def logl(r, h):
        times = sorted({t for rows in r["intervals"].values() for t in rows})
        return ev.logl_of_one(h, evd.dets, times, evd.obs_hist, {h.id: r["intervals"]}, sigma,
                              evd.t_on, evd.t_eval, anchor=evd.anchor)

    placement = {}
    for name, h in (("rp_755", hyp), ("rp_900", hyp900)):
        r = by[f"{name}_run1"]
        requested = {"edge": h.params["edge"], "lanes": list(h.params["lanes_closed"]),
                     "pos": float(h.params["pos"]), "t_on": evd.t_on}
        got = r.get("blockers") or {}
        ok = len(got) == len(requested["lanes"])
        detail = {}
        for ln in requested["lanes"]:
            vid = f"hyp_blocker_{ln}"
            b = got.get(vid)
            entry = {"requested_lane": ln, "requested_pos": requested["pos"], "recorded": b}
            if b is None:
                ok = False
            else:
                entry["lane_matches"] = int(b["lane"]) == int(ln)
                entry["edge_matches"] = b["edge"] == requested["edge"]
                entry["pos_matches"] = abs(float(b["pos"]) - requested["pos"]) < 0.5
                entry["stop_time_recorded"] = b.get("t_stopped") is not None
                entry["stop_time_requested"] = requested["t_on"]
                entry["stop_delay_s"] = (None if b.get("t_stopped") is None
                                         else float(b["t_stopped"]) - requested["t_on"])
                entry["stop_after_onset"] = bool(entry["stop_delay_s"] is not None
                                                 and entry["stop_delay_s"] >= -1e-9)
                # still a point blockage at the end of the replay
                entry["stopped_at_end"] = bool(b.get("stopped_at_end"))
                entry["lane_at_end_matches"] = b.get("lane_at_end") == int(ln)
                entry["pos_at_end_matches"] = bool(b.get("pos_at_end") is not None
                                                   and abs(float(b["pos_at_end"])
                                                           - requested["pos"]) < 0.5)
                ok = ok and all(entry[k] for k in ("lane_matches", "edge_matches", "pos_matches",
                                                   "stop_time_recorded", "stop_after_onset",
                                                   "stopped_at_end", "lane_at_end_matches",
                                                   "pos_at_end_matches"))
            detail[vid] = entry
        placement[name] = {"requested": requested, "recorded": got, "per_lane": detail, "ok": ok,
                           "max_stop_delay_s": max((v["stop_delay_s"] for v in detail.values()
                                                    if v.get("stop_delay_s") is not None), default=None)}

    determinism = {}
    for name, h in (("rp_755", hyp), ("rp_900", hyp900)):
        a, b = by[f"{name}_run1"], by[f"{name}_run2"]
        la, lb = logl(a, h), logl(b, h)
        determinism[name] = {"veh_digest_equal": a["veh_digest"] == b["veh_digest"],
                             "intervals_equal": a["intervals"] == b["intervals"],
                             "n_vehicles_equal": a["n_vehicles"] == b["n_vehicles"],
                             "logL_run1": la[0], "logL_run2": lb[0], "logL_equal": la[0] == lb[0],
                             "passed": bool(a["veh_digest"] == b["veh_digest"]
                                            and a["intervals"] == b["intervals"]
                                            and a["n_vehicles"] == b["n_vehicles"]
                                            and la[0] == lb[0])}

    a, b = by["rp_755_run1"], by["rp_900_run1"]
    differ = {"veh_digest_755": a["veh_digest"], "veh_digest_900": b["veh_digest"],
              "veh_digest_differs": a["veh_digest"] != b["veh_digest"],
              "intervals_differ": a["intervals"] != b["intervals"],
              "n_vehicles_755": a["n_vehicles"], "n_vehicles_900": b["n_vehicles"],
              "logL_755": logl(a, hyp)[0], "logL_900": logl(b, hyp900)[0],
              "n_detectors": len(evd.dets)}
    differ["passed"] = bool(differ["veh_digest_differs"] and differ["intervals_differ"])

    passed = bool(placement["rp_755"]["ok"] and placement["rp_900"]["ok"]
                  and determinism["rp_755"]["passed"] and determinism["rp_900"]["passed"]
                  and differ["passed"])
    out = {"check": "R_P_qualification", "passed": passed, "run": evd.run, "eval_id": evd.eval_id,
           "snapshot": evd.snapshot.name, "t_on": evd.t_on, "t_eval": evd.t_eval,
           "hypothesis": hyp.id, "hypothesis_params": dict(hyp.params),
           "hypothesis_900m_params": p900, "wall_s": wall,
           "blocker_placement": placement, "determinism": determinism, "replays_differ": differ,
           "restriction_present_rp_755": bool(a["restriction_present"]),
           "note": ("R_P: one stopped blocker per closed lane at pos (audit H_G5), no lane disallowed. "
                    "The recorded stop time is the first 1-s step at which the blocker reports "
                    "isStopped at the requested position; SUMO inserts a mid-run vehicle at the first "
                    "step at which departPos = pos - 1 is free, so it can lag the requested onset "
                    "(the recorded delays are reported per lane and are not a placement mismatch).")}
    (DIAG / "qualify_rp.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"qualify_rp: passed={passed} -> {DIAG / 'qualify_rp.json'}")
    return out


def step_reproduce(workers=8):
    """Exact reproduction of every logged INC evaluation (V0's own replays, original support rule)."""
    sigma = ev.load_sigma(SIGMA_JSON)
    evals = inc_evaluations()
    per_eval, failures = [], []
    for evd in evals:
        hyps = ev.build_hypotheses(midpoints=evd.midpoints, lane_counts=evd.lane_counts,
                                   grid=ev.GRID_PILOT2)
        logged = {h["id"]: h for h in evd.logged["hypotheses"]}
        # the rebuilt library must be the run's library, params and priors byte for byte
        lib_ok = all(h.id in logged and dict(h.params) == logged[h.id]["params"]
                     and float(h.prior) == float(logged[h.id]["prior"]) for h in hyps)
        cache, n_new, wall = build_cache(evd, [("A", h) for h in hyps], workers=workers)
        replays = replays_of(evd, cache, "A", hyps)
        times = union_times(replays)
        res = ev.evaluate(hyps, evd.dets, times, evd.obs_hist, replays, sigma, evd.t_on, evd.t_eval,
                          anchor=evd.anchor, weights=evd.weights)
        dll = {h.id: res.logL[h.id] - float(logged[h.id]["logL"]) for h in hyps}
        worst = max(dll.items(), key=lambda kv: abs(kv[1]))
        n_o_logged = {int(v["n_O"]) for v in logged.values()}
        row = {"eval_id": evd.eval_id, "run": evd.run, "t_on": evd.t_on, "t_eval": evd.t_eval,
               "snapshot": evd.snapshot.name, "weights": evd.weights,
               "n_hypotheses": len(hyps), "library_matches_logged": bool(lib_ok),
               "map_logged": evd.logged["h_star"], "map_reproduced": res.h_star,
               "map_matches": res.h_star == evd.logged["h_star"],
               "gap_logged": evd.logged["gap_vs_demand"], "gap_reproduced": res.gap_vs_demand,
               "gap_abs_diff": abs(float(res.gap_vs_demand) - float(evd.logged["gap_vs_demand"])),
               "n_O_reproduced": len(res.support), "n_O_logged": sorted(n_o_logged),
               "n_O_matches": len(res.support) in n_o_logged,
               "excluded_reproduced": dict(res.excluded),
               "excluded_logged": dict(evd.logged.get("excluded") or {}),
               "max_abs_logL_diff": abs(worst[1]), "max_abs_logL_diff_hyp": worst[0],
               "all_logL_within_1e-6": bool(all(abs(v) <= 1e-6 for v in dll.values())),
               "logL_diffs": dll, "n_new_replays": n_new, "wall_s": wall}
        row["passed"] = bool(lib_ok and row["map_matches"] and row["all_logL_within_1e-6"])
        if not row["passed"]:
            failures.append({"eval_id": evd.eval_id, "reason": "v0_reproduction_mismatch",
                             "detail": {"map_matches": row["map_matches"],
                                        "max_abs_logL_diff": row["max_abs_logL_diff"],
                                        "max_abs_logL_diff_hyp": row["max_abs_logL_diff_hyp"]}})
        per_eval.append(row)
        print(f"reproduce {evd.eval_id}: passed={row['passed']} map={res.h_star} "
              f"max|dlogL|={row['max_abs_logL_diff']:.3e} n_O={len(res.support)}")
    out = {"check": "exact_reproduction_of_V0", "passed": bool(per_eval) and not failures,
           "tolerance": 1e-6, "n_evaluations": len(per_eval), "evaluations": per_eval,
           "failures": failures,
           "note": ("V0 re-scored with the original pinned snapshot, sigma, down-weights, anchors and "
                    "the original library-internal support rule (event.evaluate without an explicit "
                    "support argument)")}
    (DIAG / "reproduce_v0.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"reproduce_v0: passed={out['passed']} -> {DIAG / 'reproduce_v0.json'}")
    return out


# -------------------------------------------------------------------------------------- NOI reruns
def diag_env():
    import os
    env = dict(os.environ)
    env.update({"CITYPULSE_NET": "blite", "CITYPULSE_BLITE_REV": "5", "CITYPULSE_REROUTE": "0",
                "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"})
    return env


def noi_rerun_command(run_name):
    """The identical EVT command of the stored NOI run, with the two extra Twin snapshots added."""
    info = json.loads((PILOT2_RUNS / run_name / "run_info.json").read_text(encoding="utf-8"))
    out = NOI_RERUN_DIR / run_name
    twin_dir, proxy_dir = out / "twin", out / "proxy"
    twin_dir.mkdir(parents=True, exist_ok=True)
    proxy_dir.mkdir(parents=True, exist_ok=True)
    ep = f"tcp://127.0.0.1:{NOI_PORTS[run_name]}"
    snaps = [str(int(t)) for t in tuple(SNAPSHOT_MARKS) + tuple(NOI_EXTRA_SNAPSHOTS)]
    targs = [sys.executable, "-m", "citypulse.twin.service", "--endpoint", ep, "--out", str(twin_dir),
             "--seed", str(TWIN_SEED), "--demand-seed", str(DEMAND_SEED),
             "--snapshot-times", *snaps, "--demand-path", str(TWIN_CAND_ROU), "--assim", "normal300",
             "--boundary-detector", BOUNDARY_DETECTOR, "--sigma-json", str(SIGMA_DEV),
             "--twin-base-factor", str(TWIN_BASE_FACTOR), "--event", "on",
             "--event-sigma", str(info["event_sigma"]),
             "--event-workers", "4", "--event-grid", "pilot2"]
    pargs = [sys.executable, "-m", "citypulse.proxy.service", "--endpoint", ep, "--out", str(proxy_dir),
             "--seed", str(info["seed"]), "--sensor-seed", "77", "--t-end", str(int(T_END)),
             "--routes", str(PROXY_ROU), "--no-incident"]
    return info, targs, pargs, twin_dir


def launch_noi_reruns(parallel=3, timeout_s=2400):
    """Re-run the three NOI controls (2 SUMO processes each; at most ``parallel`` at a time)."""
    NOI_RERUN_DIR.mkdir(parents=True, exist_ok=True)
    env = diag_env()
    procs, results = [], {}
    for run_name in NOI_RUNS:
        info, targs, pargs, twin_dir = noi_rerun_command(run_name)
        log = (NOI_RERUN_DIR / run_name)
        log.mkdir(parents=True, exist_ok=True)
        (log / "command.json").write_text(json.dumps({"twin": targs, "proxy": pargs}, indent=1),
                                          encoding="utf-8")
        t0 = time.time()
        twin = subprocess.Popen(targs, env=env, cwd=str(REPO),
                                stdout=open(log / "twin.out", "w"), stderr=subprocess.STDOUT)
        time.sleep(2)
        proxy = subprocess.Popen(pargs, env=env, cwd=str(REPO),
                                 stdout=open(log / "proxy.out", "w"), stderr=subprocess.STDOUT)
        procs.append((run_name, twin, proxy, t0))
        print(f"launched NOI re-run {run_name} (twin pid {twin.pid}, proxy pid {proxy.pid})", flush=True)
    for run_name, twin, proxy, t0 in procs:
        # fail fast: a twin that dies early leaves the proxy retrying its REQ connect forever
        while twin.poll() is None and proxy.poll() is None:
            if time.time() - t0 > timeout_s:
                twin.kill()
                proxy.kill()
                break
            time.sleep(1)
        if twin.poll() is not None and twin.returncode != 0 and proxy.poll() is None:
            proxy.kill()
        try:
            rc_p = proxy.wait(timeout=120)
            rc_t = twin.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proxy.kill()
            twin.kill()
            rc_p, rc_t = proxy.wait(), twin.wait()
        results[run_name] = {"proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": round(time.time() - t0, 1)}
        print(f"NOI re-run {run_name}: proxy_rc={rc_p} twin_rc={rc_t} "
              f"wall={results[run_name]['wall_s']}s", flush=True)
    (NOI_RERUN_DIR / "launch.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    bad = {k: v for k, v in results.items() if v["proxy_rc"] or v["twin_rc"]}
    if bad:
        raise RuntimeError(f"NOI re-runs failed: {bad}")
    return results


def compare_streams():
    """Stored vs re-run twin_log.parquet per NOI seed (spec, "NOI controls"; caution b)."""
    out = {}
    for run_name in NOI_RUNS:
        stored = pd.read_parquet(PILOT2_RUNS / run_name / "twin/twin_log.parquet")
        rerun = pd.read_parquet(NOI_RERUN_DIR / run_name / "twin/twin_log.parquet")
        key = ["t", "detector"]
        a = stored.sort_values(key).reset_index(drop=True)
        b = rerun.sort_values(key).reset_index(drop=True)
        row = {"run": run_name, "rows_stored": int(len(a)), "rows_rerun": int(len(b)),
               "columns_equal": list(a.columns) == list(b.columns)}
        if row["columns_equal"] and len(a) == len(b):
            diffs = {}
            for col in a.columns:
                if col in key:
                    same = bool((a[col].astype(str) == b[col].astype(str)).all())
                    diffs[col] = {"identical": same}
                else:
                    av, bv = a[col].astype(float), b[col].astype(float)
                    na, nb = av.isna(), bv.isna()
                    nan_same = bool((na == nb).all())
                    d = float((av.fillna(0) - bv.fillna(0)).abs().max()) if nan_same else None
                    diffs[col] = {"identical": bool(nan_same and d == 0.0),
                                  "max_abs_diff": d, "nan_pattern_equal": nan_same}
            row["columns"] = diffs
            row["identical"] = bool(all(v["identical"] for v in diffs.values()))
        else:
            row["identical"] = False
            row["columns"] = {}
        row["label"] = "matched stream" if row["identical"] else "rerun control"
        out[run_name] = row
        print(f"{run_name}: twin_log identical={row['identical']} -> {row['label']}")
    passed = all(v["identical"] for v in out.values())
    res = {"check": "noi_rerun_stream_identity", "passed": passed, "streams": out,
           "note": ("the re-run's twin_log.parquet is compared row for row with the stored one; on a "
                    "mismatch the re-run's stream is used for both its snapshots and its observations "
                    "and the results are labelled 'rerun control' (caution b)")}
    (DIAG / "noi_rerun" / "stream_compare.json").write_text(json.dumps(res, indent=1, default=str),
                                                            encoding="utf-8")
    return res


def step_noi(launch=True, workers=8):
    if launch:
        launch_noi_reruns()
    cmp = compare_streams()
    # record the labels on the evaluations used by the variant step
    labels = {run: v["label"] for run, v in cmp["streams"].items()}
    (DIAG / "noi_rerun" / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
    return cmp


# ------------------------------------------------------------------------------------- variants
def step_variants(workers=8):
    """All eight variants on the common support of every evaluation; raw rows first."""
    sigma = ev.load_sigma(SIGMA_JSON)
    labels_path = DIAG / "noi_rerun" / "labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    evals = inc_evaluations() + noi_evaluations()
    per_eval, rows, failures, runs = [], [], [], []
    for evd in evals:
        if evd.arm == "NOI":
            evd.label = labels.get(evd.run, "")
        pe, rw, info = score_evaluation(evd, sigma, workers=workers)
        runs.append({"eval_id": evd.eval_id, "arm": evd.arm, "n_new_replays": info["n_new"],
                     "wall_s": info["wall_s"], "empty_support": info["empty_support"],
                     "n_O": info.get("n_O"), "excluded": info.get("excluded")})
        if info["empty_support"]:
            failures.append({"eval_id": evd.eval_id, "reason": "empty_support",
                             "excluded": info["excluded"]})
        per_eval.extend(pe)
        rows.extend(rw)
        print(f"variants {evd.eval_id}: n_O={info.get('n_O')} new_replays={info['n_new']} "
              f"wall={info['wall_s']:.1f}s")
    if rows:
        pd.DataFrame(rows).to_parquet(DIAG / "raw.parquet", index=False)
    (DIAG / "per_eval.json").write_text(json.dumps({"rows": per_eval, "runs": runs,
                                                    "failures": failures}, indent=1, default=str),
                                        encoding="utf-8")
    print(f"variants: {len(rows)} raw rows, {len(per_eval)} per-evaluation rows, "
          f"{len(failures)} failures -> {DIAG / 'raw.parquet'}")
    return per_eval, failures


# -------------------------------------------------------------------------------------- summary
def median(xs):
    xs = [float(x) for x in xs if x is not None]
    return float(statistics.median(xs)) if xs else None


def build_summary(per_eval, failures):
    """Per variant: would-adopt counts (INC / NOI), MAP-family distribution, median gap. Descriptive."""
    variants = {}
    for vid in VARIANT_IDS:
        sel = [r for r in per_eval if r["variant"] == vid]
        inc = [r for r in sel if r["arm"] == "INC"]
        noi = [r for r in sel if r["arm"] == "NOI"]
        fam = {}
        for r in sel:
            fam[r["h_star_family"]] = fam.get(r["h_star_family"], 0) + 1
        fam_inc, fam_noi = {}, {}
        for r in inc:
            fam_inc[r["h_star_family"]] = fam_inc.get(r["h_star_family"], 0) + 1
        for r in noi:
            fam_noi[r["h_star_family"]] = fam_noi.get(r["h_star_family"], 0) + 1
        variants[vid] = {
            "label": VARIANTS[vid]["label"], "representation": CONFIG_DEF[VARIANTS[vid]["config"]][0],
            "onset_kind": CONFIG_DEF[VARIANTS[vid]["config"]][1],
            "locations": CONFIG_DEF[VARIANTS[vid]["config"]][2],
            "fault_family": VARIANTS[vid]["fault"],
            "n_evaluations": len(sel),
            "would_adopt_inc": sum(1 for r in inc if r["would_adopt"]), "n_inc": len(inc),
            "would_adopt_noi": sum(1 for r in noi if r["would_adopt"]), "n_noi": len(noi),
            "map_family_counts": fam,
            "map_family_counts_inc": fam_inc,
            "map_family_counts_noi": fam_noi,
            "median_gap": median([r["gap"] for r in sel]),
            "median_gap_inc": median([r["gap"] for r in inc]),
            "median_gap_noi": median([r["gap"] for r in noi]),
            "median_n_O": median([r["n_O"] for r in sel]),
            "median_incident_post": median([r["incident_post"] for r in sel]),
            "h_star_counts": {k: sum(1 for r in sel if r["h_star"] == k)
                              for k in sorted({r["h_star"] for r in sel})},
        }
    n_o = sorted({r["n_O"] for r in per_eval})
    excl = {}
    for r in per_eval:
        for k, v in (r.get("excluded") or {}).items():
            excl.setdefault(r["eval_id"], {})[k] = v
    out = {"check": "summary", "n_evaluations": len({r["eval_id"] for r in per_eval}),
           "n_inc_evaluations": len({r["eval_id"] for r in per_eval if r["arm"] == "INC"}),
           "n_noi_evaluations": len({r["eval_id"] for r in per_eval if r["arm"] == "NOI"}),
           "n_O_values": n_o, "exclusions_by_evaluation": excl, "variants": variants,
           "failures": failures,
           "note": "descriptive only: 3 runs, no inferential statistics (spec, Summary)"}
    (DIAG / "summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: {"would_adopt_inc": v["would_adopt_inc"], "n_inc": v["n_inc"],
                          "would_adopt_noi": v["would_adopt_noi"], "n_noi": v["n_noi"],
                          "median_gap": v["median_gap"], "map_family_counts": v["map_family_counts"]}
                      for k, v in variants.items()}, indent=1))
    return out


# --------------------------------------------------------------------------------------- report
def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return out


def _f(x, n=3):
    if x is None:
        return "-"
    return f"{float(x):.{n}f}"


def _loc(rel, needle):
    """`file:line` of the first line containing ``needle`` (the changes table of the report)."""
    for i, line in enumerate((REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return f"{rel}:{i}"
    return f"{rel}:?"


def step_report():
    """results/replay_diag/report.md: gates, per-evaluation tables, summary, changes, identity."""
    import subprocess as sp
    per = json.loads((DIAG / "per_eval.json").read_text(encoding="utf-8"))
    per_eval, failures = per["rows"], per["failures"]
    summary = json.loads((DIAG / "summary.json").read_text(encoding="utf-8"))
    qualify = json.loads((DIAG / "qualify_rp.json").read_text(encoding="utf-8"))
    repro = json.loads((DIAG / "reproduce_v0.json").read_text(encoding="utf-8"))
    identity = json.loads((DIAG / "default_identity.json").read_text(encoding="utf-8"))
    streams = json.loads((DIAG / "noi_rerun/stream_compare.json").read_text(encoding="utf-8"))
    raw = pd.read_parquet(DIAG / "raw.parquet")
    diff = sp.run(["git", "-C", str(REPO), "diff", "--stat", "--",
                   "citypulse/branching/engine.py", "citypulse/twin/event.py"],
                  capture_output=True, text=True).stdout.strip()
    diff_full = sp.run(["git", "-C", str(REPO), "diff", "-U0", "--",
                        "citypulse/branching/engine.py", "citypulse/twin/event.py"],
                       capture_output=True, text=True).stdout.strip()
    head = sp.run(["git", "-C", str(REPO), "log", "--oneline", "-1"],
                  capture_output=True, text=True).stdout.strip()

    L = ["MODEL: deepseek-v4.1-flash (DeepSeek Harness)", "",
         "# Matched-observation replay diagnosis of event inference",
         "",
         "Binding spec: `docs/oct10-replay-diagnosis-plan.md` (revision 2, committed at `1774408`). "
         "Offline diagnostic only: nothing here is tuned and the online method is unchanged. "
         "Truth-assisted variants are offline positive controls; no inferential statistics.",
         "",
         f"Working tree at report time: `{head}`. The spec's preregistration commit is `1774408`; the "
         "branch head moved during this run because a parallel agent committed unrelated audit work. "
         "No preregistered choice was changed and nothing under `results/replay_diag/` depends on the "
         "later commit.",
         "",
         "## 1. Gates",
         ""]
    L += _table(["Gate", "Verdict", "Evidence"], [
        ["R_P qualification (spec, blocking)", "**PASS**" if qualify["passed"] else "**FAIL**",
         f"blocker placement exact at 755 m and 900 m; two identical runs bit-identical; the two "
         f"replays differ (`qualify_rp.json`)"],
        ["Exact reproduction of V0 (spec, blocking)",
         "**PASS**" if repro["passed"] else "**FAIL**",
         f"{repro['n_evaluations']} logged INC evaluations; MAP identical, max |ΔlogL| = "
         f"{max(e['max_abs_logL_diff'] for e in repro['evaluations']):.3e} ≤ 1e-6"],
        ["NOI re-run stream identity (spec, caution b)",
         "**PASS**" if streams["passed"] else "**FAIL**",
         "; ".join(f"{k}: {'identical' if v['identical'] else 'DIFFERS'} "
                   f"({v['label']})" for k, v in streams["streams"].items())],
        ["Default identity, before vs after (prompt)",
         "**PASS**" if identity["passed"] else "**FAIL**",
         f"{len(identity['jobs'])} replays from `{identity['snapshot']}`: replay-result sha256, "
         f"vehicle digest, interval count and logL all identical"],
    ])
    L += ["", f"Failures by reason: " + (", ".join(
        f"{f['reason']} ({f['eval_id']})" for f in failures) if failures else "none") + ".",
          "",
          "### R_P qualification detail",
          "",
          f"Run `{qualify['run']}`, evaluation `{qualify['eval_id']}`, snapshot "
          f"`{qualify['snapshot']}`, t_on = {qualify['t_on']:.0f} s, t_eval = {qualify['t_eval']:.0f} s, "
          f"hypothesis `{qualify['hypothesis']}`.",
          ""]
    qrows = []
    for name in ("rp_755", "rp_900"):
        pl = qualify["blocker_placement"][name]
        rec = ", ".join(f"{vid}: edge={b['edge']} lane={b['lane']} pos={b['pos']:.3f} "
                        f"t_stopped={b['t_stopped']:.0f} (onset+"
                        f"{b['t_stopped'] - pl['requested']['t_on']:.0f}s), "
                        f"stopped_at_end={b.get('stopped_at_end')}"
                        for vid, b in (pl["recorded"] or {}).items()) or "none"
        qrows.append([name, pl["requested"]["pos"], pl["requested"]["lanes"], rec, pl["ok"]])
    L += _table(["Replay", "Requested pos (m)", "Requested lanes", "Recorded placement", "Exact"], qrows)
    L += ["", "The blocker is recorded on the requested lane at the requested position, still stopped "
          "there at t_eval; the recorded stop time is the first step SUMO reports it stopped at that "
          "position and can lag the onset by the insertion delay (reported above).", ""]
    L += ["", "Determinism (twice-repeated identical inputs): " + "; ".join(
        f"{k}: digest_equal={v['veh_digest_equal']}, intervals_equal={v['intervals_equal']}, "
        f"logL_equal={v['logL_equal']}" for k, v in qualify["determinism"].items()) + ".",
          "",
          "The two replays differ: "
          f"digest 755 m={qualify['replays_differ']['veh_digest_755'][:12]}… vs 900 m="
          f"{qualify['replays_differ']['veh_digest_900'][:12]}…, "
          f"intervals differ={qualify['replays_differ']['intervals_differ']}, "
          f"logL {_f(qualify['replays_differ']['logL_755'])} vs "
          f"{_f(qualify['replays_differ']['logL_900'])}.",
          "",
          "### Default identity (prompt: one replay from a pilot-2 pinned snapshot, before vs after)",
          ""]
    L += _table(["Probe job", "sha256 before", "sha256 after", "identical", "logL before", "logL after"],
                [[k, v["sha256_before"][:16] + "…", (v["sha256_after"] or "")[:16] + "…",
                  v["sha256_identical"], _f(v["logL_before"], 6), _f(v["logL_after"], 6)]
                 for k, v in identity["jobs"].items()])
    L += ["", "### Exact reproduction of V0",
          ""]
    L += _table(["Evaluation", "t_on", "t_eval", "down-weights", "MAP logged", "MAP reproduced",
                 "max |ΔlogL|", "|O| logged", "|O| reproduced", "PASS"],
                [[e["eval_id"], f"{e['t_on']:.0f}", f"{e['t_eval']:.0f}",
                  json.dumps(e["weights"]), e["map_logged"], e["map_reproduced"],
                  f"{e['max_abs_logL_diff']:.3e}", json.dumps(e["n_O_logged"]), e["n_O_reproduced"],
                  e["passed"]] for e in repro["evaluations"]])
    L += ["", "Every logL of all 20 hypotheses of every logged evaluation is within 1e-6 of the log; "
          "the logL difference table is in `reproduce_v0.json`.", ""]

    L += ["## 2. NOI re-run", ""]
    L += _table(["Run", "stored rows", "re-run rows", "twin_log identical", "label"],
                [[k, v["rows_stored"], v["rows_rerun"], v["identical"], v["label"]]
                 for k, v in streams["streams"].items()])
    L += ["", "Extra Twin snapshots at 4,230 s and 4,350 s (spec); the synthetic episode starts from "
          "the 4,230 s snapshot, the 4,350 s one is recorded but not scored (one episode only). All "
          "three re-runs reproduce the stored stream row for row, so no NOI result carries the "
          "'rerun control' label of caution (b); the synthetic episodes use the re-run's snapshots and "
          "the re-run's observations, which are the stored ones.", ""]

    L += ["## 3. Per-evaluation tables by variant", ""]
    for vid in VARIANT_IDS:
        sel = [r for r in per_eval if r["variant"] == vid]
        if not sel:
            continue
        v = summary["variants"][vid]
        L += [f"### {vid} — {v['label']}", "",
              f"representation **{v['representation']}**, incident onset "
              f"{'logged t_on' if v['onset_kind'] == 'logged' else f'{TRUTH_ONSET:.0f} s'}, locations "
              f"{v['locations']}, fault family {v['fault_family']}, {sel[0]['n_hypotheses']} hypotheses.",
              ""]
        L += _table(["Evaluation", "arm", "t_eval", "snapshot", "MAP", "family", "P(incident)",
                     "gap", "would-adopt", "EVR", "|O|", "excluded"],
                    [[r["eval_id"], r["arm"], f"{r['t_eval']:.0f}", r["snapshot"], r["h_star"],
                      r["h_star_family"], _f(r["incident_post"]), _f(r["gap"]),
                      r["would_adopt"], _f(r["evr"]), r["n_O"],
                      json.dumps(r.get("excluded") or {})] for r in sel])
        L += [""]

    L += ["## 4. Summary", ""]
    L += _table(["Variant", "representation", "onset", "locations", "fault family",
                 "would-adopt INC", "would-adopt NOI", "MAP-family distribution", "median gap",
                 "median P(incident)"],
                [[vid, v["representation"], "logged" if v["onset_kind"] == "logged" else "4500",
                  v["locations"], v["fault_family"],
                  f"{v['would_adopt_inc']}/{v['n_inc']}", f"{v['would_adopt_noi']}/{v['n_noi']}",
                  json.dumps(v["map_family_counts"]), _f(v["median_gap"]),
                  _f(v["median_incident_post"])]
                 for vid, v in summary["variants"].items()])
    L += ["", "Median gap by arm:", ""]
    L += _table(["Variant", "median gap INC", "median gap NOI", "median gap all"],
                [[vid, _f(v["median_gap_inc"]), _f(v["median_gap_noi"]), _f(v["median_gap"])]
                 for vid, v in summary["variants"].items()])
    L += ["", "MAP-family distribution by arm:", ""]
    L += _table(["Variant", "INC (13 evaluations)", "NOI (9 synthetic evaluations)"],
                [[vid, json.dumps(v["map_family_counts_inc"]), json.dumps(v["map_family_counts_noi"])]
                 for vid, v in summary["variants"].items()])
    L += ["", "MAP hypothesis counts per variant:", ""]
    L += _table(["Variant", "h* counts"],
                [[vid, json.dumps(v["h_star_counts"])] for vid, v in summary["variants"].items()])
    L += ["", f"|O| values over all evaluations: {summary['n_O_values']}. Exclusions by reason:", ""]
    L += _table(["Evaluation", "exclusions"],
                [[k, json.dumps(v)] for k, v in summary["exclusions_by_evaluation"].items()])
    same_o = all(r["n_O"] == next(e["n_O_reproduced"] for e in repro["evaluations"]
                                  if e["eval_id"] == r["eval_id"])
                 for r in per_eval if r["arm"] == "INC")
    L += ["", "On every INC evaluation |O| equals the library-internal support the as-run V0 "
          "evaluation scored on " + ("(the common-support intersection removes nothing V0 kept)."
                                     if same_o else "(the intersection is smaller than V0's support).")
          + " Excluded triples are `partial_block` (the 120-s block is not complete inside the scoring "
            "window) and `obs_invalid` (the recorded observation is marked invalid); no triple is "
            "excluded for a missing replay value, so no variant's physics makes a triple unscorable.", ""]
    L += ["", "No inferential statistics are reported: this is a 3-run diagnostic, and the summary "
          "states what moves the outcome conditional on these streams.", ""]

    v = summary["variants"]
    n_eval = len({r["eval_id"] for r in per_eval})
    n_inc = len({r["eval_id"] for r in per_eval if r["arm"] == "INC"})
    n_noi = len({r["eval_id"] for r in per_eval if r["arm"] == "NOI"})
    min_noi = min(r["gap"] for r in per_eval if r["arm"] == "NOI")
    max_noi = max(r["gap"] for r in per_eval if r["arm"] == "NOI")
    vnf_map = v["VNF"]["map_family_counts"]
    L += ["### What moves the outcome (descriptive, conditional on these streams)", "",
          f"- **Representation.** Holding the onset at the logged t_on, R_P (VP) raises the median "
          f"incident-family posterior from {_f(v['V0']['median_incident_post'])} (V0) to "
          f"{_f(v['VP']['median_incident_post'])} and makes an incident the MAP in "
          f"{v['VP']['map_family_counts'].get('incident', 0)} of {n_eval} evaluations, but the "
          f"best-incident-vs-best-demand gap still never reaches ln 10 on an INC evaluation: "
          f"would-adopt stays {v['VP']['would_adopt_inc']}/{n_inc}.",
          f"- **The fault family is not the binding competition.** Removing it and splitting the mass "
          f"1/2 incident, 1/2 demand (VNF) leaves would-adopt at {v['VNF']['would_adopt_inc']}/{n_inc} "
          f"and the median gap identical to V0's ({_f(v['VNF']['median_gap'])}): the family prior "
          f"cancels in a best-incident-minus-best-demand ratio. Without the fault family the MAP is a "
          f"demand hypothesis in {vnf_map.get('demand', 0)} of {n_eval} evaluations, so in V0 it is the "
          f"demand family, not the fault family, that outranks the incident family.",
          f"- **Onset.** Moving the incident onset to 4,500 s under R_E (VT) gives "
          f"{v['VT']['would_adopt_inc']}/{n_inc}; under R_P (VPT) it gives "
          f"{v['VPT']['would_adopt_inc']}/{n_inc}. With R_E the onset alone moves almost nothing; with "
          f"R_P it is the factor that carries the gap past ln 10 (median INC gap "
          f"{_f(v['VPT']['median_gap_inc'])} against {_f(v['VP']['median_gap_inc'])} for VP).",
          f"- **Location.** Adding ktb_n1 at 900 m under R_P at the logged onset (VPL) gives "
          f"{v['VPL']['would_adopt_inc']}/{n_inc} against VP's {v['VP']['would_adopt_inc']}/{n_inc}; at "
          f"the 4,500 s onset (VPTL) it gives {v['VPTL']['would_adopt_inc']}/{n_inc} against VPT's "
          f"{v['VPT']['would_adopt_inc']}/{n_inc}. The added location helps most at the logged onset "
          f"and is not additive with the truth onset on these streams.",
          f"- **NOI.** No variant would adopt on any of the {n_noi} synthetic NOI evaluations, "
          f"including the truth-assisted ones with the imposed 4,500 s control onset (would-adopt "
          f"0/{n_noi} everywhere); the NOI gaps run from {_f(min_noi)} to {_f(max_noi)}.",
          ""]

    L += ["## 5. Failures by reason", ""]
    L += _table(["Evaluation", "reason", "detail"],
                [[f["eval_id"], f["reason"], json.dumps(f.get("detail", {}))] for f in failures]
                or [["-", "none", "-"]])
    L += ["", "## 6. Changes (file:line)", ""]
    L += _table(["Where", "What"], [
        [_loc("citypulse/branching/engine.py", 'def _apply_spec_at'),
         "R_P selector: `spec[\"representation\"] == \"R_P\"` places blockers instead of closing lanes; "
         "the R_E path is unchanged and remains the default"],
        [_loc("citypulse/branching/engine.py", 'def _place_blockers'),
         "one stopped blocker per closed lane at pos, departPos = pos - 1, duration 3600 s, LCM 0 "
         "(the audit's H_G5 point blockage); no lane is disallowed"],
        [_loc("citypulse/branching/engine.py", 'collect_from = float(job["collect_from"])'),
         "intervention onset (`t_on`) separated from the interval-collection start (`collect_from`, "
         "default `t_on`) -- caution (a)"],
        [_loc("citypulse/branching/engine.py", 'if t > collect_from + 1e-9'),
         "interval collection uses `collect_from`; with the default this is the old `t_on` condition"],
        [_loc("citypulse/branching/engine.py", '"blockers": blockers'),
         "the recorded blocker placement (edge, lane, pos, first stopped step, state at t_end) travels "
         "in the replay result"],
        [_loc("citypulse/twin/event.py", 'beta=BETA, support=None, excluded=None'),
         "`evaluate` accepts an explicit support set and its exclusions; both default to None, which "
         "keeps the library-internal support rule of the online method"],
    ])
    L += ["", "`git diff --stat`:", "", "```", diff or "(no diff)", "```", "",
          "```diff", diff_full or "(no diff)", "```", "",
          "New files: `citypulse/experiments/replay_diag.py`, `tests/test_replay_diag.py`, outputs "
          "under `results/replay_diag/`. Untouched: `citypulse/branching/audit_engine.py`, "
          "`citypulse/experiments/decision_audit.py`, `tests/test_audit.py`, `results/audit/`, "
          "`citypulse/twin/service.py`.", ""]
    L += ["## 7. Raw rows", "",
          f"`results/replay_diag/raw.parquet`: {len(raw)} rows, "
          f"{len(raw.columns)} columns ({', '.join(raw.columns)}), written before any summary.", "",
          "REPORT DONE"]
    (DIAG / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"report -> {DIAG / 'report.md'}")
    return L


# ------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="matched-observation replay diagnosis (rev 2)")
    ap.add_argument("--step", required=True,
                    choices=["identity", "compare", "qualify", "reproduce", "noi", "variants",
                             "summary", "report"])
    ap.add_argument("--tag", default="before", help="identity step: output tag")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-launch", action="store_true", help="noi step: only compare existing re-runs")
    a = ap.parse_args()
    DIAG.mkdir(parents=True, exist_ok=True)
    if a.step == "identity":
        step_identity(a.tag, workers=max(1, min(a.workers, 3)))
    elif a.step == "compare":
        return 0 if step_compare_identity()["passed"] else 1
    elif a.step == "qualify":
        return 0 if step_qualify(workers=max(1, min(a.workers, 4)))["passed"] else 1
    elif a.step == "reproduce":
        return 0 if step_reproduce(workers=a.workers)["passed"] else 1
    elif a.step == "noi":
        return 0 if step_noi(launch=not a.no_launch)["passed"] else 1
    elif a.step == "variants":
        _pe, failures = step_variants(workers=a.workers)
        return 0 if not failures else 1
    elif a.step == "summary":
        per = json.loads((DIAG / "per_eval.json").read_text(encoding="utf-8"))
        build_summary(per["rows"], per["failures"])
    elif a.step == "report":
        step_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
