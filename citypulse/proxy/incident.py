"""Proxy-only incident: stopped vehicles physically blocking lanes (report2 §F.1 D9).

The Twin never receives this object; it is only in the Proxy config and the Proxy truth log.
"""


class Incident:
    def __init__(self, edge, lanes, pos, t_start, duration, vtype="p_car0"):
        self.edge, self.lanes, self.pos = edge, list(lanes), float(pos)
        self.t_start, self.duration, self.vtype = float(t_start), float(duration), vtype
        self.active = False
        self.ids = []

    def step(self, tc, t):
        if not self.active and t >= self.t_start and not self.ids:
            rid = "inc_route"
            if rid not in tc.route.getIDList():
                tc.route.add(rid, [self.edge])
            for ln in self.lanes:
                vid = f"incident_{ln}"
                tc.vehicle.add(vid, rid, typeID=self.vtype, departLane=str(ln), departPos=str(self.pos - 1),
                               departSpeed="0")
                tc.vehicle.setStop(vid, self.edge, pos=self.pos, laneIndex=ln, duration=self.duration)
                tc.vehicle.setLaneChangeMode(vid, 0)
                self.ids.append(vid)
            self.active = True
        if self.active and t >= self.t_start + self.duration + 5:
            self.active = False

    def to_dict(self):
        return {"edge": self.edge, "lanes": self.lanes, "pos": self.pos, "t_start": self.t_start,
                "duration": self.duration}
