"""Shared SUMO helpers: command lines, detector read-out, control-state record."""
import json
from collections import defaultdict

from citypulse.config import NET_FILE, SCEN, SENSOR_PERIOD, sumo_bin

DET_FILE = SCEN / "detectors.add.xml"
TLS_FILE = SCEN / "tls_incident.add.xml"   # predefined A1 plans (runtime-created programs break loadState)


def base_cmd(binary="sumo"):
    return [sumo_bin(binary), "-n", str(NET_FILE), "--step-length", "1", "--no-step-log", "true",
            "--no-warnings", "true", "--time-to-teleport", "-1", "--collision.action", "warn"]


def proxy_cmd(seed, routes=None, extra=()):
    c = base_cmd() + ["-a", f"{SCEN / 'vtypes_proxy.add.xml'},{DET_FILE},{TLS_FILE}",
                      "-r", str(routes or SCEN / "proxy.rou.xml"), "--seed", str(seed),
                      "--device.rerouting.probability", "0.3", "--device.rerouting.period", "60"]
    return c + list(extra)


def twin_cmd(seed, extra=()):
    """Twin has NO route file: its demand is inserted from Python (twin/demand_stream.py)."""
    c = base_cmd() + ["-a", f"{SCEN / 'vtypes_twin.add.xml'},{DET_FILE},{TLS_FILE}", "--seed", str(seed)]
    return c + list(extra)


def detector_loops():
    """AID -> list of E1 loop ids (one per lane)."""
    m = json.load(open(SCEN / "detector_map.json", encoding="utf-8"))["mapped"]
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
    make "P_inc" the default. Force the netconvert program "0" at start (never after a loadState)."""
    for tls in tc.trafficlight.getIDList():
        progs = [l.programID for l in tc.trafficlight.getAllProgramLogics(tls)]
        if "0" in progs and tc.trafficlight.getProgram(tls) != "0":
            tc.trafficlight.setProgram(tls, "0")


def is_sensor_step(t):
    return int(round(t)) % SENSOR_PERIOD == 0 and t > 0
