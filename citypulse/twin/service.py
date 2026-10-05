"""Twin process. Receives ONLY SensorMsg (validated) and replies with ReplyMsg.

Normal-mode assimilation (report2 §G.3 / docs/oct5-normal-assim-plan.md): every 60 s the boundary
detector chosen by --boundary-detector (default AID07105, entry edge `tko_insert`) updates the Twin
demand multiplier m_s from the last two 30-s intervals; the rows are logged to assim_log.parquet.
NA-300 (docs/na300-qualification-plan.md, --assim normal300) is the same update on a 300-s tick over
the preceding non-overlapping ten 30-s intervals, with m clipped to the candidate-pool scale 1.5.
--twin-base-factor scales the TKO entry's candidate acceptance only. With --assim off (default)
nothing is read from the sensor message beyond today's logging, so the run is unchanged.

Event-aware assimilation (docs/oct6-event-pilot-plan.md, --event on) adds, on top of that loop:
a 15-min snapshot ring under <out>/ring/ (every 30 s), the corrected G4 trigger every 30 s, the
state machine every 60 s, hypothesis scoring by parallel subprocess replays (<= --event-workers,
default 8) from S(t_on - 60), live state replacement on adoption and on clearance, and the regional
freeze of the frozen entries' m (NA-300 ticks log `frozen`, or `degraded_slow` in DEGRADED). All
decisions are pure and live in citypulse.twin.event; the replays are citypulse.branching.engine
.score_replays. With --event off (default) none of this exists and the loop is unchanged.

Pilot 2 (docs/oct6-audit-and-pilot2-plan.md part B, --event-grid pilot2) changes the incident grid to
10 hypotheses (20 in the library) and moves the DEGRADED bound onto the 30-s tick at entry + 900 s.
--event-force-hstar <incident id> is the labelled forced-adoption integration test: at the first
evaluation of the run (its first episode) that hypothesis is treated as h* with the threshold met.
With --event-grid pilot1 (default) and no --event-force-hstar the behaviour is the pilot-1 one.

Snapshots (--snapshot-times) are written *after* that timestamp's assimilation tick, so the meta's
`m` is the multiplier the online Twin has actually been running with since that instant (F2).
"""
import argparse
import json
import shutil
import time
from collections import deque
from pathlib import Path

import pandas as pd
import traci
import zmq

from citypulse.bus.messages import validate_reply, validate_sensor
from citypulse.branching.engine import (
    _apply_spec_at,
    _lift_spec_at,
    restriction_present,
    score_replays,
    veh_digest,
)
from citypulse.sim import (
    ControlState,
    init_signals,
    detector_loops,
    read_detectors,
    twin_cmd,
    get_control,
    get_twin_compliance,
)
from citypulse.control.actions import ActionExecutor
from citypulse.twin import event as evmod
from citypulse.twin.assim import NormalAssimilator
from citypulse.twin.demand_stream import TwinDemandStream

BOUNDARY_DETECTOR = "AID07105"   # default boundary detector (plan §NA as predeclared);
                                 # --boundary-detector overrides it for the amended arm
BOUNDARY_ENTRY = "tko_insert"    # its entry edge in the Twin candidate routes
ASSIM_PERIOD = 60.0              # s between assimilation ticks (--assim normal)
ASSIM_PERIODS = {"normal": 60.0, "normal300": 300.0}
ASSIM_INTERVALS = {"normal": 2, "normal300": 10}      # 30-s intervals averaged per tick
ASSIM_M_MAX = {"normal": 1.8, "normal300": 1.5}       # m clip; 1.5 = the candidate-pool scale
ASSIM_SENSOR_PERIOD = 30.0       # s between SensorMsg readings (one interval per message)
EVENT_RING_PERIOD = 30.0         # s between ring snapshots (--event on)
EVENT_SENSOR_PERIOD = 30.0       # s between trigger ticks


def load_sigma(assim, sigma_json, boundary_detector):
    """Read sigma for the selected boundary detector, or fail hard at startup (F5).

    With assimilation on, a missing/absent/non-positive sigma would leave every tick `invalid` and
    the run bit-for-bit open loop while still reporting the assimilation mode, so it is an error.
    """
    if assim == "off":
        return {}
    sigma = {}
    if sigma_json:
        with open(sigma_json) as fh:
            sigma = json.load(fh)
    val = sigma.get(boundary_detector)
    try:
        ok = float(val) > 0.0
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise ValueError(
            f"--assim {assim}: sigma_q for boundary detector {boundary_detector!r} is missing or "
            f"non-positive (got {val!r} from {sigma_json!r}); assimilation would silently be a no-op")
    return sigma


def load_event_sigma(path):
    """Read sigma_event.json, or fail hard: the trigger needs sigma for both pair detectors."""
    if not path:
        raise ValueError("--event on requires --event-sigma <sigma_event.json>")
    sigma = evmod.load_sigma(path)
    for det in (evmod.PAIR_U, evmod.PAIR_D):
        for x in ("o", "v"):
            if evmod.sigma_of(sigma, det, x) is None:
                raise ValueError(f"--event on: sigma_{det}^{x} is missing or non-positive in {path!r}")
    return sigma


def consecutive_window(hist, n_intervals, sensor_period=ASSIM_SENSOR_PERIOD):
    """True if `hist` holds n_intervals consecutive sensor readings (t, obs, twin), oldest first."""
    h = list(hist)
    return len(h) == n_intervals and all(
        h[i + 1][0] - h[i][0] == sensor_period for i in range(len(h) - 1))


def scaled_assimilator(base, kappa_scale=1.0, delta_scale=1.0):
    """A copy of `base` with kappa and the deadband scaled (DEGRADED's kappa/4, 2 sigma; the RECOVERY
    ramp). assim.py is frozen, so the scaling is done by constructing the equivalent assimilator."""
    if kappa_scale == 1.0 and delta_scale == 1.0:
        return base
    return NormalAssimilator(kappa=base.kappa * kappa_scale, delta=base.delta * delta_scale,
                             step_clip=base.step_clip, m_min=base.m_min, m_max=base.m_max,
                             o_crit=base.o_crit, n_intervals=base.n_intervals)


class EventRuntime:
    """--event on: snapshot ring, trigger, hypothesis scoring, live replacement and the event logs.

    All decisions are made by citypulse.twin.event; this class owns the I/O (ring files, subprocess
    replays, SUMO restarts) and the four event logs. Inert unless --event on.
    """

    def __init__(self, out, sigma, stream, workers=8, seed=2, demand_seed=202, demand_path=None,
                 grid=evmod.GRID_PILOT1, force_hstar=None):
        self.out = Path(out)
        self.ring_dir = self.out / "ring"
        self.ring_dir.mkdir(parents=True, exist_ok=True)
        self.sigma = sigma
        self.stream = stream
        self.workers = int(workers)
        self.seed = int(seed)
        self.demand_seed = int(demand_seed)
        self.demand_path = str(demand_path) if demand_path else None
        self.grid = grid
        self.force_hstar = force_hstar
        self.trigger = evmod.TriggerRule()
        # pilot 2: the DEGRADED bound is scheduled on the tick at entry + 900 s, not at the next
        # evaluation (part B, "Specification conflict resolved"); pilot 1 keeps the eval-driven bound.
        self.sm = evmod.EventStateMachine(
            degraded_exit=(evmod.DEGRADED_EXIT_SCHEDULED if grid == evmod.GRID_PILOT2
                           else evmod.DEGRADED_EXIT_EVAL))
        self.hyps = evmod.build_hypotheses(grid=grid)
        self.lane_counts, self.midpoints, self.freeze_entries = {}, {}, []
        self.obs_hist = {}                 # detector -> t -> ObsItem
        self.msg_times = deque()
        self.ring = {}                     # t -> (state path, meta path)
        self.trigger_rows, self.event_rows, self.state_rows, self.replacement_rows = [], [], [], []
        self.wall_total = 0.0
        self.n_eval = 0
        self.anchor, self.anchor_t_on = None, None
        self.episode_snap = None            # pinned S(t_on - delta) of the current episode
        self.n_forced = 0

    # ------------------------------------------------------------------ startup / geometry
    def init_twin(self, tc):
        """Resolve the incident library geometry and the freeze set from the live Twin."""
        for edge, _pos in evmod.INCIDENT_LOCATIONS:
            ids = [l for l in tc.lane.getIDList()
                   if l.startswith(edge + "_") and l[len(edge) + 1:].isdigit()]
            self.lane_counts[edge] = len(ids)
            if ids:
                self.midpoints[edge] = 0.5 * tc.lane.getLength(sorted(ids)[0])
        self.hyps = evmod.build_hypotheses(midpoints=self.midpoints, lane_counts=self.lane_counts,
                                           grid=self.grid)
        if self.force_hstar is not None:
            # fail at startup, not mid-run: the forced id must exist in the final library
            h = evmod.find_hypothesis(self.hyps, self.force_hstar)
            if h.family != "incident":
                raise ValueError(f"--event-force-hstar {self.force_hstar!r} is not an incident "
                                 f"hypothesis (family {h.family!r})")
            self.force_hstar = h.id
        self.freeze_entries = evmod.entries_through(self.stream.cands)
        return {"lane_counts": self.lane_counts, "midpoints": self.midpoints,
                "freeze_entries": self.freeze_entries, "grid": self.grid,
                "n_hypotheses": len(self.hyps), "force_hstar": self.force_hstar}

    # ------------------------------------------------------------------ observations
    def note(self, t, msg_obs):
        t = float(t)
        for o in msg_obs:
            self.obs_hist.setdefault(o["detector"], {})[t] = dict(o)
        self.msg_times.append(t)
        while len(self.msg_times) > 240:            # 2 h of 30-s messages is far more than enough
            old = self.msg_times.popleft()
            for rows in self.obs_hist.values():
                rows.pop(old, None)

    def anchor_for(self, t_on):
        """Last valid pre-t_on reading of every detector/channel (the stuck-fault anchor)."""
        if self.anchor is not None and self.anchor_t_on == t_on:
            return self.anchor
        anchor = {}
        for det, rows in self.obs_hist.items():
            vals = {}
            for tt in sorted(rows, reverse=True):
                if tt >= t_on:
                    continue
                r = rows[tt]
                if not r.get("valid"):
                    continue
                for x in evmod.CHANNELS:
                    if x not in vals and r.get(x) is not None:
                        vals[x] = r[x]
            anchor[det] = vals
        self.anchor, self.anchor_t_on = anchor, t_on
        return anchor

    # ------------------------------------------------------------------ snapshot ring
    def ring_write(self, tc, t, cs):
        t = float(t)
        st = self.ring_dir / f"twin_state_{int(t)}.xml.gz"
        mt = self.ring_dir / f"twin_state_{int(t)}.json"
        tc.simulation.saveState(str(st))
        meta = {"t": t, "control_state": cs.to_dict(), "stream_ptr": self.stream.ptr,
                "pending": list(tc.simulation.getPendingVehicles()), "demand_seed": self.demand_seed,
                "sumo_seed": self.seed, "demand_path": self.demand_path, "m": dict(self.stream.m),
                "twin_base_factor": self.stream.base_factor, "restriction": self.sm.restriction,
                "event_state": self.sm.state, "t_on": self.sm.t_on, "active_hyp": self.sm.active_hyp}
        mt.write_text(json.dumps(meta), encoding="utf-8")
        self.ring[t] = (st, mt)
        self.ring_prune(t)
        return st, mt

    def ring_prune(self, t_now):
        """Delete ring files older than 15 min -- inside this run's ring dir only."""
        keep = float(t_now) - evmod.RING_KEEP
        for tt in [k for k in self.ring if k < keep]:
            st, mt = self.ring.pop(tt)
            for p in (st, mt):
                try:
                    if p.exists() and self.ring_dir.resolve() in p.resolve().parents:
                        p.unlink()
                except OSError:
                    pass

    def ring_snapshot(self, t):
        """The ring snapshot at t (the ring is written every 30 s); nearest at or before t."""
        if float(t) in self.ring:
            return self.ring[float(t)]
        cands = [k for k in self.ring if k <= float(t) + 1e-9]
        if not cands:
            raise KeyError(f"no ring snapshot at or before t={t}")
        return self.ring[max(cands)]

    def pin_episode(self, t_alarm):
        """Copy S(t_on - Delta) out of the ring so every evaluation of this episode replays the same
        start (the 15-min ring would otherwise prune it while a long episode is still being scored)."""
        snap_t = float(t_alarm) - self.sm.onset_lag - self.sm.delta
        try:
            st, mt = self.ring_snapshot(snap_t)
        except KeyError:
            self.episode_snap = None
            return None
        dst_st = self.out / f"event_snapshot_{int(snap_t)}.xml.gz"
        dst_mt = self.out / f"event_snapshot_{int(snap_t)}.json"
        shutil.copyfile(st, dst_st)
        shutil.copyfile(mt, dst_mt)
        self.episode_snap = (float(snap_t), dst_st, dst_mt)
        return self.episode_snap

    def episode_paths(self, want):
        """(state, meta) for the episode's replay start, pinned when available."""
        if self.episode_snap is not None and abs(self.episode_snap[0] - float(want)) < 1e-9:
            return self.episode_snap[1], self.episode_snap[2]
        return self.ring_snapshot(want)

    # ------------------------------------------------------------------ specs
    def spec_of(self, hyp):
        """The engine job spec of a hypothesis (incident: lanes + speed factor; demand: level f)."""
        if hyp.family == "incident":
            p = dict(hyp.params)
            return {"kind": "incident", "edge": p["edge"], "lanes_closed": list(p["lanes_closed"]),
                    "n_lanes": int(p["n_lanes"]), "speed_factor": float(p["speed_factor"]),
                    "pos": p.get("pos")}
        if hyp.family == "demand":
            return {"kind": "demand", "entry": hyp.params["entry"],
                    "factor": float(hyp.params["factor"])}
        return {"kind": "none"}

    def lift_spec(self):
        r = self.sm.restriction or {}
        return {"edge": r.get("edge"), "lanes_closed": list(r.get("lanes_closed") or []),
                "base_speed": dict(r.get("base_speed") or {})}

    def restriction_of(self, hyp, tc):
        """The live restriction record of an adopted incident hypothesis (event.restriction_record).

        It is what the clearance replays lift: the closed lanes and the pre-restriction max speed of
        every lane the spec scales. The base speeds are read from the live Twin *before* the
        replacement closes it, which is also before any restriction is applied to it. Without this
        record ``lift_spec`` is empty and every H_clear(tau_c) replay is identical to the active one,
        so P_clear could never leave its prior.
        """
        p = dict(hyp.params)
        base = {f"{p['edge']}_{ln}": float(tc.lane.getMaxSpeed(f"{p['edge']}_{ln}"))
                for ln in range(int(p.get("n_lanes") or 0))}
        return evmod.restriction_record(hyp, base)

    # ------------------------------------------------------------------ 30-s tick
    def step(self, t, msg_obs, own, tc, cs, act):
        """One SensorMsg tick: trigger, RECOVERY checks, and the state-machine evaluation when due."""
        t = float(t)
        self.note(t, msg_obs)
        ou = next((o for o in msg_obs if o["detector"] == evmod.PAIR_U), None)
        od = next((o for o in msg_obs if o["detector"] == evmod.PAIR_D), None)
        row = self.trigger.step(t, ou, own.get(evmod.PAIR_U), od, own.get(evmod.PAIR_D), self.sigma,
                                masked=self.sm.masked, weights=self.sm.downweight)
        self.trigger_rows.append({"t": row["t"], "B": row["B"], "streak": row["streak"],
                                  "masked": row["masked"]})
        o_u = float(ou["o"]) if ou and ou.get("valid") and ou.get("o") is not None else None
        o_d = float(od["o"]) if od and od.get("valid") and od.get("o") is not None else None
        out = self.sm.trigger(t, row["alarm"], o_u, o_d)
        self._log_transitions(out["transitions"])
        for tr in out["transitions"]:
            if tr.dst == evmod.SUSPECTED:
                self.pin_episode(tr.t)
        if self.sm.state == evmod.RECOVERY and int(round(t)) % 60 == 0:
            self._log_transitions(self.sm.recovery_tick(t, o_u, o_d, row["B"])["transitions"])
        deg = self.sm.degraded_tick(t)          # pilot 2: DEGRADED bound on the tick, not on an eval
        if deg["transitions"]:
            self._log_transitions(deg["transitions"])
        if self.sm.due(t):
            tc = self.evaluate(t, tc, cs, act)
        return tc

    # ------------------------------------------------------------------ evaluation
    def _fail(self, t, st_before, t_on, err):
        """Log a failed evaluation (missing ring snapshot, crashed replay) and skip the tick."""
        self.event_rows.append({"t": float(t), "state": st_before, "t_on": t_on, "hypotheses": [],
                                "h_star": None, "gap_vs_demand": None, "evr": None, "adopted": False,
                                "excluded": {"error": str(err)[:400]}, "p_clear": None, "wall_s": 0.0})
        self.sm.t_last_eval = float(t)

    def evaluate(self, t, tc, cs, act):
        st_before = self.sm.state
        t_on = self.sm.t_on
        try:
            st_path, mt_path = self.episode_paths(t_on - self.sm.delta)
        except KeyError as err:
            self._fail(t, st_before, t_on, err)
            return tc
        dets = sorted(self.obs_hist)
        if st_before == evmod.EVENT:
            return self.evaluate_clearance(t, tc, cs, act, st_path, mt_path, dets)
        jobs = [{"tag": h.id, "t_on": t_on, "t_end": t, "detectors": dets, "apply": self.spec_of(h),
                 "lift": None, "t_lift": None} for h in self.hyps]
        try:
            res, wall = score_replays(st_path, mt_path, jobs, workers=self.workers, seed=self.seed)
        except Exception as err:                      # a crashed replay must not kill the Twin
            self._fail(t, st_before, t_on, err)
            return tc
        replays = {r["tag"]: r["intervals"] for r in res}
        ev = evmod.evaluate(self.hyps, dets, self._times(res, dets), self.obs_hist, replays,
                            self.sigma, t_on, t, anchor=self.anchor_for(t_on),
                            weights=self.sm.downweight)
        ev.wall_s = wall
        adopted = evmod.adoption_decision(ev)
        if not adopted and self.force_hstar is not None and self.n_forced == 0 \
                and st_before == evmod.SUSPECTED and self.sm.n_eval == 0:
            # labelled forced-adoption integration test: at the FIRST evaluation of the run (the first
            # evaluation of its first episode), treat the fixed hypothesis as h* and the threshold as
            # met (part B); it is an integration test, never inference
            adopted = evmod.forced_adoption(ev, self.force_hstar)
            self.n_forced += 1
        ev.adopted = adopted
        out = self.sm.on_hypotheses(t, ev, adopted=adopted)
        self._log_transitions(out["transitions"])
        self.event_rows.append(ev.to_log_row(st_before, t_on))
        self.wall_total += wall
        self.n_eval += 1
        if out["write_m"] is not None:
            self.stream.m[evmod.BASE_FACTOR_ENTRY] = float(out["write_m"])
        if out["adopt"]:
            h = next(h for h in self.hyps if h.id == out["adopt"])
            r = next(r for r in res if r["tag"] == h.id)
            # record the live restriction BEFORE the replacement restarts SUMO: the clearance
            # replays lift exactly this record (event.py EventStateMachine.restriction)
            if h.family == "incident":
                self.sm.restriction = self.restriction_of(h, tc)
            tc = self.replace_live(tc, cs, act, st_path, mt_path, t_on, t, apply_spec=self.spec_of(h))
            self.log_replacement(t, h, r, tc, "adoption", st_path, forced=bool(ev.forced))
        return tc

    def evaluate_clearance(self, t, tc, cs, act, st_path, mt_path, dets):
        """EVENT_ASSIMILATION: the active h* against H_clear(tau_c), tau_c in {60..300}."""
        t_on = self.sm.t_on
        active = next((h for h in self.hyps if h.id == self.sm.active_hyp), None)
        if active is None:
            self.sm.t_last_eval = float(t)
            return tc
        spec, lift = self.spec_of(active), self.lift_spec()
        jobs = [{"tag": "active", "t_on": t_on, "t_end": t, "detectors": dets, "apply": spec,
                 "lift": None, "t_lift": None}]
        for tau in evmod.CLEAR_TAUS:
            jobs.append({"tag": f"clear_{int(tau)}", "t_on": t_on, "t_end": t, "detectors": dets,
                         "apply": spec, "lift": lift, "t_lift": t - tau})
        try:
            res, wall = score_replays(st_path, mt_path, jobs, workers=self.workers, seed=self.seed)
        except Exception as err:                      # a crashed replay must not kill the Twin
            self._fail(t, evmod.EVENT, t_on, err)
            return tc
        replays = {r["tag"]: r["intervals"] for r in res}
        hyps = [evmod.Hypothesis("active", "incident", dict(active.params), 0.5)]
        hyps += [evmod.Hypothesis(f"clear_{int(tau)}", "incident", dict(active.params), 0.1)
                 for tau in evmod.CLEAR_TAUS]
        ev = evmod.evaluate(hyps, dets, self._times(res, dets), self.obs_hist, replays, self.sigma,
                            t_on, t, anchor=self.anchor_for(t_on), weights=self.sm.downweight)
        cres, row = evmod.clearance_analysis(
            t, ev.logL["active"], [ev.logL[f"clear_{int(tau)}"] for tau in evmod.CLEAR_TAUS])
        row["wall_s"] = wall
        row["t_on"] = t_on
        row["excluded"] = dict(ev.excluded)
        self.wall_total += wall
        self.n_eval += 1
        out = self.sm.on_clearance(t, cres["p_clear"], tau_c=row["tau_c_best"])
        self._log_transitions(out["transitions"])
        self.event_rows.append(row)
        if out["clear"]:
            tau_c = out["clear"]["tau_c"]
            r_clear = next((r for r in res if r["tag"] == f"clear_{int(tau_c)}"), None)
            tc = self.replace_live(tc, cs, act, st_path, mt_path, t_on, t, apply_spec=spec,
                                   lift_spec=lift, t_lift=t - tau_c)
            self.trigger.streak = 0
            self.log_replacement(t, active, r_clear, tc, "clearance", st_path)
        return tc

    @staticmethod
    def _times(res, dets):
        times = set()
        for r in res:
            for d in dets:
                times.update(r["intervals"].get(d, {}).keys())
        return sorted(times)

    # ------------------------------------------------------------------ live state replacement
    def replace_live(self, tc, cs, act, st_path, mt_path, t_on, t_end, apply_spec=None,
                     lift_spec=None, t_lift=None):
        """Load S in the live Twin, restore the control state/stream/m, replay to t_end.

        A fresh SUMO process is started with --load-state (the verified path: engine._score_worker
        and the na300 branch replay); the ControlState object is updated in place because the
        ActionExecutor holds it.
        """
        meta = json.loads(Path(mt_path).read_text(encoding="utf-8"))
        cmd = twin_cmd(self.seed, ["--save-state.rng", "--load-state", str(st_path)])
        try:
            tc.close()
        except Exception:
            pass
        traci.start(cmd, label="twin")
        tc = traci.getConnection("twin")
        src = ControlState.from_dict(meta["control_state"])
        cs.tls_program, cs.lane_disallow = dict(src.tls_program), dict(src.lane_disallow)
        cs.lane_maxspeed, cs.vms = dict(src.lane_maxspeed), src.vms
        cs.apply(tc)
        self.stream.m = dict(meta.get("m") or {})
        if meta.get("stream_ptr") is not None:
            self.stream.ptr = int(meta["stream_ptr"])
        else:
            self.stream.seek(tc.simulation.getTime())
        t0 = tc.simulation.getTime()
        applied = lifted = False
        if apply_spec is not None and t_on <= t0 + 1e-9:
            _apply_spec_at(tc, cs, self.stream, apply_spec)
            applied = True
        if lift_spec is not None and t_lift is not None and t_lift <= t0 + 1e-9:
            _lift_spec_at(tc, cs, lift_spec)
            lifted = True
        while tc.simulation.getTime() < t_end - 1e-9:
            t_next = tc.simulation.getTime() + 1
            if not applied and apply_spec is not None and t_next > t_on:
                _apply_spec_at(tc, cs, self.stream, apply_spec)
                applied = True
            if not lifted and lift_spec is not None and t_lift is not None and t_next > t_lift:
                _lift_spec_at(tc, cs, lift_spec)
                lifted = True
            self.stream.insert_due(tc, t_next)
            tc.simulationStep()
            act.step(tc)
        return tc

    def log_replacement(self, t, hyp, res, tc, kind, st_path, forced=False):
        digest, n_veh = veh_digest(tc)
        present = restriction_present(tc, self.spec_of(hyp)) if hyp.family == "incident" else False
        row = {"t": float(t), "kind": kind, "forced": bool(forced), "snapshot": Path(st_path).name,
               "hypothesis": hyp.id,
               "family": hyp.family, "params": dict(hyp.params),
               "n_vehicles_after_replay": None if res is None else int(res["n_vehicles"]),
               "n_vehicles_live": int(n_veh),
               "veh_digest_replay": None if res is None else res["veh_digest"],
               "veh_digest_live": digest,
               "vehicles_match": bool(res is not None and res["veh_digest"] == digest
                                      and res["n_vehicles"] == n_veh),
               "restriction_present_live": bool(present),
               "restriction_present_replay": None if res is None else bool(res["restriction_present"])}
        self.replacement_rows.append(row)
        return row

    # ------------------------------------------------------------------ logs
    def _log_transitions(self, transitions):
        for tr in transitions:
            self.state_rows.append(tr.to_dict())

    def write_logs(self):
        with open(self.out / "event_log.jsonl", "w", encoding="utf-8") as fh:
            for r in self.event_rows:
                fh.write(json.dumps(r, default=str) + "\n")
        with open(self.out / "state_trace.jsonl", "w", encoding="utf-8") as fh:
            for r in self.state_rows:
                fh.write(json.dumps(r, default=str) + "\n")
        with open(self.out / "replacement_log.jsonl", "w", encoding="utf-8") as fh:
            for r in self.replacement_rows:
                fh.write(json.dumps(r, default=str) + "\n")
        pd.DataFrame(self.trigger_rows, columns=["t", "B", "streak", "masked"]).to_parquet(
            self.out / "trigger_log.parquet")

    def summary(self):
        return {"state": self.sm.state, "t_on": self.sm.t_on, "t_alarm": self.sm.t_alarm,
                "n_eval": self.n_eval, "wall_s": self.wall_total, "masked": self.sm.masked,
                "frozen": self.sm.frozen, "active_hyp": self.sm.active_hyp,
                "restriction": self.sm.restriction, "downweight": dict(self.sm.downweight),
                "n_alarms": len(self.trigger.alarms), "alarms": list(self.trigger.alarms),
                "false_alarms": self.sm.false_alarms, "unexplained": self.sm.unexplained,
                "transitions": list(self.state_rows), "freeze_entries": self.freeze_entries,
                "lane_counts": self.lane_counts, "midpoints": self.midpoints,
                "n_replacements": len(self.replacement_rows),
                "t_adopt": self.sm.t_adopt, "t_recovery": self.sm.t_recovery,
                "grid": self.grid, "n_hypotheses": len(self.hyps),
                "force_hstar": self.force_hstar, "n_forced_adoptions": self.n_forced,
                "degraded_exit": self.sm.degraded_exit}


def run(endpoint, out: Path, seed, demand_seed, snapshot_times=(), demand_path=None, assim="off",
        sigma_json=None, boundary_detector=BOUNDARY_DETECTOR, twin_base_factor=1.0, event="off",
        event_sigma=None, event_workers=8, event_grid=evmod.GRID_PILOT1, event_force_hstar=None):
    out.mkdir(parents=True, exist_ok=True)
    loops = detector_loops()
    stream = TwinDemandStream(seed=demand_seed, path=demand_path, base_factor=twin_base_factor)
    assim_on = assim != "off"
    sigma = load_sigma(assim, sigma_json, boundary_detector)
    event_on = event == "on"
    ev = None
    if event_on:
        ev = EventRuntime(out, load_event_sigma(event_sigma), stream, workers=event_workers, seed=seed,
                          demand_seed=demand_seed, demand_path=demand_path, grid=event_grid,
                          force_hstar=event_force_hstar)
    n_intervals = ASSIM_INTERVALS.get(assim, 2)
    assim_period = ASSIM_PERIODS.get(assim, ASSIM_PERIOD)
    assimilator = (NormalAssimilator(n_intervals=n_intervals, m_max=ASSIM_M_MAX.get(assim, 1.8))
                   if assim_on else None)
    hist, assim_rows = deque(maxlen=n_intervals), []
    cs = ControlState()
    act = ActionExecutor(get_control(), get_twin_compliance(), cs)
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(endpoint)
    traci.start(twin_cmd(seed, ["--save-state.rng"]), label="twin")
    tc = traci.getConnection("twin")
    init_signals(tc)
    ev_info = ev.init_twin(tc) if ev is not None else None
    rows, wall, n_msgs = [], time.time(), 0
    while True:
        msg = validate_sensor(sock.recv_json())
        if msg["t"] < 0:
            sock.send_json(validate_reply({"type": "reply", "t": -1.0, "actions": []}))
            break
        n_msgs += 1
        snap_t = None
        while tc.simulation.getTime() < msg["t"]:
            t_next = tc.simulation.getTime() + 1
            stream.insert_due(tc, t_next)
            tc.simulationStep()
            act.step(tc)
            t = tc.simulation.getTime()
            if t in snapshot_times:
                snap_t = t
        own = read_detectors(tc, loops)
        for o in msg["obs"]:
            tw = own.get(o["detector"], {})
            rows.append({"t": msg["t"], "detector": o["detector"], "obs_valid": o["valid"], "obs_q": o["q"],
                         "obs_v": o["v"], "obs_o": o["o"], "twin_q": tw.get("q"), "twin_v": tw.get("v"),
                         "twin_o": tw.get("o")})
        if assim_on:
            t_b = float(msg["t"])
            obs_b = next((o for o in msg["obs"] if o["detector"] == boundary_detector), None)
            tw_b = own.get(boundary_detector)
            twin_b = None if tw_b is None else {"q": tw_b.get("q"), "v": tw_b.get("v"), "o": tw_b.get("o"),
                                                "valid": tw_b.get("q") is not None and tw_b.get("o") is not None}
            hist.append((t_b, obs_b, twin_b))
            if int(round(t_b)) % int(assim_period) == 0:
                # n_intervals consecutive 30-s intervals ending at this tick; anything else is
                # fed as missing -> no update
                ok = consecutive_window(hist, n_intervals)
                h = list(hist)
                obs_win = tuple(x[1] for x in h) if ok else None
                twin_win = tuple(x[2] for x in h) if ok else None
                mode = ev.sm.assim_mode() if ev is not None else "normal"
                if mode == "frozen":
                    # regional freeze: the entry's m is held; the tick is still logged
                    assim_rows.append({"t": t_b, "e_s": None, "r": None, "delta": None,
                                       "m": stream.multiplier(BOUNDARY_ENTRY), "reason": "frozen"})
                else:
                    kappa_scale = ev.sm.kappa_scale(t_b) if ev is not None else 1.0
                    delta_scale = ev.sm.delta_scale() if ev is not None else 1.0
                    m_new, row = scaled_assimilator(
                        assimilator, kappa_scale, delta_scale).update(
                        t_b, obs_win, twin_win, stream.base_rate(BOUNDARY_ENTRY, t_b),
                        stream.multiplier(BOUNDARY_ENTRY), sigma_q=sigma.get(boundary_detector))
                    if mode == "slow":
                        row["reason"] = "degraded_slow"
                    stream.m[BOUNDARY_ENTRY] = m_new
                    assim_rows.append(row)
        if snap_t is not None:
            # F2: after this timestamp's assimilation tick, so meta["m"] is the online m from now on
            tc.simulation.saveState(str(out / f"twin_state_{int(snap_t)}.xml.gz"))
            json.dump({"t": snap_t, "control_state": cs.to_dict(), "stream_ptr": stream.ptr,
                       "pending": list(tc.simulation.getPendingVehicles()), "demand_seed": demand_seed,
                       "sumo_seed": seed, "demand_path": str(demand_path) if demand_path else None,
                       "m": dict(stream.m), "twin_base_factor": stream.base_factor},
                      open(out / f"twin_state_{int(snap_t)}.json", "w"))
        if ev is not None and float(msg["t"]) % EVENT_SENSOR_PERIOD == 0:
            ev.ring_write(tc, msg["t"], cs)
            tc = ev.step(float(msg["t"]), msg["obs"], own, tc, cs, act)
        sock.send_json(validate_reply({"type": "reply", "t": msg["t"], "actions": []}))
    stats = {"messages": n_msgs, "wall_s": time.time() - wall, "arrived": tc.simulation.getArrivedNumber(),
             "running": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles()),
             "assim": assim, "twin_base_factor": twin_base_factor}
    if ev is not None:
        ev.write_logs()
        stats["event"] = ev.summary()
        stats["event_info"] = ev_info
    traci.switch("twin")
    traci.close()
    pd.DataFrame(rows).to_parquet(out / "twin_log.parquet")
    if assim_on:
        pd.DataFrame(assim_rows, columns=["t", "e_s", "r", "delta", "m", "reason"]).to_parquet(
            out / "assim_log.parquet")
    json.dump(stats, open(out / "twin_stats.json", "w"), indent=1)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--demand-seed", type=int, default=202)
    ap.add_argument("--snapshot-times", type=float, nargs="*", default=[])
    ap.add_argument("--demand-path", default=None, help="Twin candidate routes XML file")
    ap.add_argument("--assim", default="off", choices=["off", "normal", "normal300"],
                    help="assimilation mode: off (default), normal (60-s NA), normal300 (300-s NA-300)")
    ap.add_argument("--sigma-json", default=None, help='{"<detector>": sigma_q_vehph}')
    ap.add_argument("--boundary-detector", default=BOUNDARY_DETECTOR,
                    help="detector whose obs/Twin readings feed the TKO assimilator (default AID07105)")
    ap.add_argument("--twin-base-factor", type=float, default=1.0,
                    help="scale on the TKO entry's candidate acceptance (default 1.0 = unchanged)")
    ap.add_argument("--event", default="off", choices=["off", "on"],
                    help="event-aware assimilation (default off: byte-identical behaviour)")
    ap.add_argument("--event-sigma", default=None, help="sigma_event.json (per-detector q/v/o MAD)")
    ap.add_argument("--event-workers", type=int, default=8, help="max parallel scoring replays")
    ap.add_argument("--event-grid", default=evmod.GRID_PILOT1, choices=list(evmod.EVENT_GRIDS),
                    help="incident hypothesis grid: pilot1 (16 hypotheses, default) or pilot2 (20)")
    ap.add_argument("--event-force-hstar", default=None,
                    help="pilot-2 labelled integration test: at the first evaluation treat this "
                         "incident hypothesis as h* and the adoption threshold as met")
    a = ap.parse_args()
    print(json.dumps(run(a.endpoint, Path(a.out), a.seed, a.demand_seed, set(a.snapshot_times),
                         demand_path=a.demand_path, assim=a.assim, sigma_json=a.sigma_json,
                         boundary_detector=a.boundary_detector, twin_base_factor=a.twin_base_factor,
                         event=a.event, event_sigma=a.event_sigma, event_workers=a.event_workers,
                         event_grid=a.event_grid, event_force_hstar=a.event_force_hstar)))


if __name__ == "__main__":
    main()
