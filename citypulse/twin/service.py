"""Twin process. Receives ONLY SensorMsg (validated) and replies with ReplyMsg.

No assimilation yet (D1–D4): the Twin runs its own independent demand and logs, per sensor interval,
the observation it received next to its own detector readings (the residual input for D6–D8).
"""
import argparse
import json
import time
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
from citypulse.twin.demand_stream import TwinDemandStream


def run(endpoint, out: Path, seed, demand_seed, snapshot_times=(), demand_path=None):
    out.mkdir(parents=True, exist_ok=True)
    loops = detector_loops()
    stream = TwinDemandStream(seed=demand_seed, path=demand_path)
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
                           "sumo_seed": seed, "demand_path": str(demand_path) if demand_path else None},
                          open(out / f"twin_state_{int(t)}.json", "w"))
        own = read_detectors(tc, loops)
        for o in msg["obs"]:
            tw = own.get(o["detector"], {})
            rows.append({"t": msg["t"], "detector": o["detector"], "obs_valid": o["valid"], "obs_q": o["q"],
                         "obs_v": o["v"], "obs_o": o["o"], "twin_q": tw.get("q"), "twin_v": tw.get("v"),
                         "twin_o": tw.get("o")})
        sock.send_json(validate_reply({"type": "reply", "t": msg["t"], "actions": []}))
    stats = {"messages": n_msgs, "wall_s": time.time() - wall, "arrived": tc.simulation.getArrivedNumber(),
             "running": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles())}
    traci.switch("twin")
    traci.close()
    pd.DataFrame(rows).to_parquet(out / "twin_log.parquet")
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
    a = ap.parse_args()
    print(json.dumps(run(a.endpoint, Path(a.out), a.seed, a.demand_seed, set(a.snapshot_times), demand_path=a.demand_path)))


if __name__ == "__main__":
    main()
