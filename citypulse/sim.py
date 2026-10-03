"""Shared SUMO helpers: command lines, detector read-out, control-state record."""
import json
from collections import defaultdict

import os
from pathlib import Path

from citypulse.config import NET_FILE, RESULTS, SCEN, SENSOR_PERIOD, sumo_bin


def get_net_setting():
    return os.environ.get("CITYPULSE_NET", "").strip().lower()


def get_scen_dir():
    net = get_net_setting()
    if net == "blite":
        return SCEN / "blite"
    if net == "v4":
        return SCEN / "v4"
    return SCEN


def get_net_file():
    net = get_net_setting()
    if net == "blite":
        return SCEN / "blite" / "net3.net.xml"
    if net == "v4":
        return SCEN / "net_bounded_v4.net.xml"
    return NET_FILE


def get_det_file():
    net = get_net_setting()
    if net == "blite":
        return SCEN / "blite" / "detectors3.add.xml"
    if net == "v4":
        return SCEN / "v4" / "detectors.add.xml"
    return SCEN / "detectors.add.xml"


def get_tls_file():
    net = get_net_setting()
    if net == "blite":
        grid_webster = RESULTS / "blite" / "grid" / "tls_webster3.add.xml"
        inc = SCEN / "blite" / "tls_incident3.add.xml"
        if grid_webster.exists() and inc.exists():
            return f"{grid_webster},{inc}"
        return inc
    if net == "v4":
        return SCEN / "v4" / "tls_incident.add.xml"
    return SCEN / "tls_incident.add.xml"


def get_detector_map():
    net = get_net_setting()
    if net == "blite":
        m3 = SCEN / "blite" / "detector_map3.json"
        if m3.exists():
            return m3
        return SCEN / "blite" / "detector_map.json"
    if net == "v4":
        return SCEN / "v4" / "detector_map.json"
    return SCEN / "detector_map.json"


def get_vtypes_file(world):
    scen_dir = get_scen_dir()
    f = scen_dir / f"vtypes_{world}.add.xml"
    if f.exists():
        return f
    return SCEN / f"vtypes_{world}.add.xml"


def get_control():
    if get_net_setting() == "blite":
        from citypulse.scenario_blite import CONTROL
        c = dict(CONTROL)
        cb = list(c["corridor_b"])
        if "tko_a1" in cb and "ktr_w1" in cb:
            idx = cb.index("tko_a1")
            if cb[idx + 1] == "ktr_w1":
                cb.insert(idx + 1, "ms_on_ktr_w1")
        c["corridor_b"] = cb
        return c
    from citypulse.scenario import CONTROL
    return CONTROL


def get_twin_compliance():
    if get_net_setting() == "blite":
        from citypulse.scenario_blite import TWIN_ASSUMED_COMPLIANCE
        return TWIN_ASSUMED_COMPLIANCE
    from citypulse.scenario import TWIN_ASSUMED_COMPLIANCE
    return TWIN_ASSUMED_COMPLIANCE


def __getattr__(name):
    if name == "DET_FILE":
        return get_det_file()
    if name == "TLS_FILE":
        return get_tls_file()
    if name == "NET_FILE":
        return get_net_file()
    if name == "CONTROL":
        return get_control()
    if name == "TWIN_ASSUMED_COMPLIANCE":
        return get_twin_compliance()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def base_cmd(binary="sumo"):
    return [sumo_bin(binary), "-n", str(get_net_file()), "--step-length", "1", "--no-step-log", "true",
            "--no-warnings", "true", "--time-to-teleport", "-1", "--collision.action", "warn"]


def proxy_cmd(seed, routes=None, extra=()):
    scen_dir = get_scen_dir()
    if (scen_dir / "proxy.rou.xml").exists():
        default_routes = scen_dir / "proxy.rou.xml"
    elif (scen_dir / "demand" / "proxy.rou.xml").exists():
        default_routes = scen_dir / "demand" / "proxy.rou.xml"
    else:
        default_routes = SCEN / "proxy.rou.xml"
    c = base_cmd() + ["-a", f"{get_vtypes_file('proxy')},{get_det_file()},{get_tls_file()}",
                      "-r", str(routes or default_routes), "--seed", str(seed),
                      "--device.rerouting.probability", "0.3", "--device.rerouting.period", "60"]
    return c + list(extra)


def twin_cmd(seed, extra=()):
    """Twin has NO route file: its demand is inserted from Python (twin/demand_stream.py)."""
    c = base_cmd() + ["-a", f"{get_vtypes_file('twin')},{get_det_file()},{get_tls_file()}", "--seed", str(seed)]
    return c + list(extra)


def detector_loops():
    """AID -> list of E1 loop ids (one per lane)."""
    m = json.load(open(get_detector_map(), encoding="utf-8"))["mapped"]
    return {d["id"]: [f"{d['id']}_{i}" for i in range(d["n_lanes"])] for d in m}


def read_detectors(tc, loops):
    """Previous completed 30 s interval, aggregated over lanes.
    q: vehicles in interval; v: count-weighted mean speed (km/h, None if no vehicle); o: mean lane occupancy (%)."""
    out = {}
    for aid, ids in loops.items():
        q, sv, occ = 0, 0.0, []
        for lid in ids:
            n = tc.inductionloop.getLastIntervalVehicleNumber(lid)
            s = tc.inductionloop.getLastIntervalMeanSpeed(lid)
            q += n
            if n > 0 and s >= 0:
                sv += s * n
            occ.append(tc.inductionloop.getLastIntervalOccupancy(lid))
        out[aid] = {"q": q, "v": (sv / q * 3.6) if q > 0 else None, "o": sum(occ) / len(occ)}
    return out


class ControlState:
    """Everything set at runtime that a state file may not preserve; re-applied after every loadState."""

    def __init__(self):
        self.tls_program = {}      # tls id -> program id
        self.lane_disallow = {}    # lane id -> list of vClasses
        self.lane_maxspeed = {}    # lane id -> m/s
        self.vms = None            # dict(policy) or None

    def to_dict(self):
        return {"tls_program": self.tls_program, "lane_disallow": self.lane_disallow,
                "lane_maxspeed": self.lane_maxspeed, "vms": self.vms}

    @classmethod
    def from_dict(cls, d):
        cs = cls()
        cs.tls_program, cs.lane_disallow = dict(d["tls_program"]), dict(d["lane_disallow"])
        cs.lane_maxspeed, cs.vms = dict(d["lane_maxspeed"]), d["vms"]
        return cs

    def apply(self, tc):
        for tls, prog in self.tls_program.items():
            tc.trafficlight.setProgram(tls, prog)
        for lane, cls in self.lane_disallow.items():
            tc.lane.setDisallowed(lane, cls)
        for lane, v in self.lane_maxspeed.items():
            tc.lane.setMaxSpeed(lane, v)


def init_signals(tc):
    """SUMO activates the LAST loaded program of a signal, so loading tls_incident.add.xml would silently
    make "P_inc" the default. Force Webster if present, else netconvert program "0" at start (never after a loadState)."""
    for tls in tc.trafficlight.getIDList():
        progs = [l.programID for l in tc.trafficlight.getAllProgramLogics(tls)]
        if "webster" in progs:
            if tc.trafficlight.getProgram(tls) != "webster":
                tc.trafficlight.setProgram(tls, "webster")
        elif "0" in progs and tc.trafficlight.getProgram(tls) != "0":
            tc.trafficlight.setProgram(tls, "0")


def is_sensor_step(t):
    return int(round(t)) % SENSOR_PERIOD == 0 and t > 0
