"""Twin process. Receives ONLY SensorMsg (validated) and replies with ReplyMsg.

Normal-mode assimilation (--assim normal, report2 §G.3 / docs/oct5-normal-assim-plan.md): every 60 s
the boundary detector chosen by --boundary-detector (default AID07105, entry edge `tko_insert`)
updates the Twin demand multiplier m_s from the last two 30-s intervals; the rows are logged to
assim_log.parquet. With --assim off (default) nothing is read from the sensor message beyond today's
logging, so the run is unchanged.
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
ASSIM_PERIOD = 60.0              # s between assimilation ticks


def run(endpoint, out: Path, seed, demand_seed, snapshot_times=(), demand_path=None, assim="off",
        sigma_json=None, boundary_detector=BOUNDARY_DETECTOR):
    out.mkdir(parents=True, exist_ok=True)
    loops = detector_loops()
    stream = TwinDemandStream(seed=demand_seed, path=demand_path)
    assim_on = assim == "normal"
    sigma = json.load(open(sigma_json)) if (assim_on and sigma_json) else {}
    assimilator = NormalAssimilator() if assim_on else None
    hist, assim_rows = deque(maxlen=2), []
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
        while tc.simulation.getTime() < msg["t"]:
            t_next = tc.simulation.getTime() + 1
            stream.insert_due(tc, t_next)
            tc.simulationStep()
            act.step(tc)
            t = tc.simulation.getTime()
            if t in snapshot_times:
                tc.simulation.saveState(str(out / f"twin_state_{int(t)}.xml.gz"))
                json.dump({"t": t, "control_state": cs.to_dict(), "stream_ptr": stream.ptr,
                           "pending": list(tc.simulation.getPendingVehicles()), "demand_seed": demand_seed,
                           "sumo_seed": seed, "demand_path": str(demand_path) if demand_path else None,
                           "m": dict(stream.m)},
                          open(out / f"twin_state_{int(t)}.json", "w"))
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
            if int(round(t_b)) % int(ASSIM_PERIOD) == 0:
                h = list(hist)
                # two consecutive 30-s intervals; anything else is fed as missing -> no update
                pair = (h[0][1], h[1][1]) if len(h) == 2 and h[1][0] - h[0][0] == 30.0 else None
                pair_t = (h[0][2], h[1][2]) if pair is not None else None
                m_new, row = assimilator.update(
                    t_b, pair, pair_t, stream.base_rate(BOUNDARY_ENTRY, t_b),
                    stream.multiplier(BOUNDARY_ENTRY), sigma_q=sigma.get(boundary_detector))
                stream.m[BOUNDARY_ENTRY] = m_new
                assim_rows.append(row)
        sock.send_json(validate_reply({"type": "reply", "t": msg["t"], "actions": []}))
    stats = {"messages": n_msgs, "wall_s": time.time() - wall, "arrived": tc.simulation.getArrivedNumber(),
             "running": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles()),
             "assim": assim}
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
    ap.add_argument("--assim", default="off", choices=["off", "normal"], help="normal-mode assimilation")
    ap.add_argument("--sigma-json", default=None, help='{"<detector>": sigma_q_vehph}')
    ap.add_argument("--boundary-detector", default=BOUNDARY_DETECTOR,
                    help="detector whose obs/Twin readings feed the TKO assimilator (default AID07105)")
    a = ap.parse_args()
    print(json.dumps(run(a.endpoint, Path(a.out), a.seed, a.demand_seed, set(a.snapshot_times),
                         demand_path=a.demand_path, assim=a.assim, sigma_json=a.sigma_json,
                         boundary_detector=a.boundary_detector)))


if __name__ == "__main__":
    main()
