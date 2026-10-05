"""Proxy world process: hidden 'reality'. Talks to the Twin ONLY via SensorMsg/ReplyMsg over ZeroMQ (REQ).

Writes Proxy ground truth to <run>/proxy/ (never read by the Twin process).
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
import traci
import zmq

import os
from citypulse.bus.messages import validate_reply, validate_sensor
from citypulse.control.actions import ActionExecutor
from citypulse.proxy.incident import Incident
from citypulse.proxy.sensors import SensorEmulator
from citypulse.sim import ControlState, init_signals, detector_loops, is_sensor_step, proxy_cmd, read_detectors


def get_truth():
    if os.environ.get("CITYPULSE_NET", "").strip().lower() == "blite":
        from citypulse.proxy.truth_blite import PROXY_ONLY
        return PROXY_ONLY
    from citypulse.proxy.truth_config import PROXY_ONLY
    return PROXY_ONLY


def get_control():
    if os.environ.get("CITYPULSE_NET", "").strip().lower() == "blite":
        from citypulse.scenario_blite import CONTROL
        return CONTROL
    from citypulse.scenario import CONTROL
    return CONTROL


def run(endpoint, out: Path, seed, sensor_seed, t_end, incident_on, snapshot_times=(), routes=None,
        sensor_fault=None):
    out.mkdir(parents=True, exist_ok=True)
    truth = get_truth()
    control = get_control()
    loops = detector_loops()
    emu = SensorEmulator(loops.keys(), sensor_seed, sensor_fault=sensor_fault)
    inc = Incident(**truth["incident"]) if incident_on else None
    cs = ControlState()
    act = ActionExecutor(control, truth["vms_true_compliance"], cs)
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect(endpoint)
    traci.start(proxy_cmd(seed, routes), label="proxy")
    tc = traci.getConnection("proxy")
    init_signals(tc)
    truth_rows, halt_rows, wall = [], [], time.time()
    t = 0.0
    while t < t_end:
        tc.simulationStep()
        t = tc.simulation.getTime()
        if inc:
            inc.step(tc, t)
        act.step(tc)
        if t in snapshot_times:
            tc.simulation.saveState(str(out / f"proxy_state_{int(t)}.xml.gz"))
        if is_sensor_step(t):
            truth = read_detectors(tc, loops)
            for d, v in truth.items():
                truth_rows.append({"t": t, "detector": d, **v})
            h_w3 = tc.edge.getLastStepHaltingNumber("ktb_w3")
            h_n1 = tc.edge.getLastStepHaltingNumber("ktb_n1")
            halt_rows.append({"t": t, "ktb_w3": h_w3, "ktb_n1": h_n1, "halting_sum": h_w3 + h_n1})
            msg = validate_sensor(emu.emit(t, truth))
            sock.send_json(msg)
            reply = validate_reply(sock.recv_json())
            for a in reply["actions"]:
                act.apply(tc, a["action"], a["params"])
    stats = {"t_end": t, "wall_s": time.time() - wall, "arrived": tc.simulation.getArrivedNumber(),
             "running": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles()),
             "teleports_total": None, "observed_detectors": emu.observed,
             "incident": inc.to_dict() if inc else None, "n_diverted": act.n_diverted}
    sock.send_json({"type": "sensor", "t": -1.0, "period": 0, "obs": []})  # end-of-run sentinel
    sock.recv_json()
    traci.switch("proxy")
    traci.close()
    pd.DataFrame(truth_rows).to_parquet(out / "proxy_truth.parquet")
    pd.DataFrame(halt_rows).to_parquet(out / "proxy_halting.parquet")
    json.dump(stats, open(out / "proxy_stats.json", "w"), indent=1)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sensor-seed", type=int, default=77)
    ap.add_argument("--t-end", type=float, default=3000)
    ap.add_argument("--no-incident", action="store_true")
    ap.add_argument("--snapshot-times", type=float, nargs="*", default=[])
    ap.add_argument("--proxy-snapshot-times", type=float, nargs="*", default=[], help="Proxy snapshot times")
    ap.add_argument("--routes", default=None, help="Proxy routes XML file")
    ap.add_argument("--sensor-fault", default=None, help="Sensor fault specification, e.g. AID02109:stuck:4500:5400")
    a = ap.parse_args()
    snaps = set(a.snapshot_times) | set(a.proxy_snapshot_times)
    s = run(a.endpoint, Path(a.out), a.seed, a.sensor_seed, a.t_end, not a.no_incident, snaps,
            routes=a.routes, sensor_fault=a.sensor_fault)
    print(json.dumps({k: v for k, v in s.items() if k != "observed_detectors"}))


if __name__ == "__main__":
    main()
