"""Twin process. Receives ONLY SensorMsg (validated) and replies with ReplyMsg.

Normal-mode assimilation (report2 §G.3 / docs/oct5-normal-assim-plan.md): every 60 s the boundary
detector chosen by --boundary-detector (default AID07105, entry edge `tko_insert`) updates the Twin
demand multiplier m_s from the last two 30-s intervals; the rows are logged to assim_log.parquet.
NA-300 (docs/na300-qualification-plan.md, --assim normal300) is the same update on a 300-s tick over
the preceding non-overlapping ten 30-s intervals, with m clipped to the candidate-pool scale 1.5.
--twin-base-factor scales the TKO entry's candidate acceptance only. With --assim off (default)
nothing is read from the sensor message beyond today's logging, so the run is unchanged.

Snapshots (--snapshot-times) are written *after* that timestamp's assimilation tick, so the meta's
`m` is the multiplier the online Twin has actually been running with since that instant (F2).
"""
import argparse
import json
import time
from collections import deque
from pathlib import Path

import pandas as pd
import traci
import zmq

from citypulse.bus.messages import validate_reply, validate_sensor
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


def consecutive_window(hist, n_intervals, sensor_period=ASSIM_SENSOR_PERIOD):
    """True if `hist` holds n_intervals consecutive sensor readings (t, obs, twin), oldest first."""
    h = list(hist)
    return len(h) == n_intervals and all(
        h[i + 1][0] - h[i][0] == sensor_period for i in range(len(h) - 1))


def run(endpoint, out: Path, seed, demand_seed, snapshot_times=(), demand_path=None, assim="off",
        sigma_json=None, boundary_detector=BOUNDARY_DETECTOR, twin_base_factor=1.0):
    out.mkdir(parents=True, exist_ok=True)
    loops = detector_loops()
    stream = TwinDemandStream(seed=demand_seed, path=demand_path, base_factor=twin_base_factor)
    assim_on = assim != "off"
    sigma = load_sigma(assim, sigma_json, boundary_detector)
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
                m_new, row = assimilator.update(
                    t_b, obs_win, twin_win, stream.base_rate(BOUNDARY_ENTRY, t_b),
                    stream.multiplier(BOUNDARY_ENTRY), sigma_q=sigma.get(boundary_detector))
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
        sock.send_json(validate_reply({"type": "reply", "t": msg["t"], "actions": []}))
    stats = {"messages": n_msgs, "wall_s": time.time() - wall, "arrived": tc.simulation.getArrivedNumber(),
             "running": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles()),
             "assim": assim, "twin_base_factor": twin_base_factor}
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
    a = ap.parse_args()
    print(json.dumps(run(a.endpoint, Path(a.out), a.seed, a.demand_seed, set(a.snapshot_times),
                         demand_path=a.demand_path, assim=a.assim, sigma_json=a.sigma_json,
                         boundary_detector=a.boundary_detector, twin_base_factor=a.twin_base_factor)))


if __name__ == "__main__":
    main()
