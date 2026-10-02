"""Infrastructure-level actions with identical semantics in Proxy and Twin (report2 §J).

Nothing here takes vehicle ids or routes from the other world. Each world:
  - A1: switches listed signals to the predefined incident plan "P_inc" (network/make_tls_plans.py)
  - A2: runs a VMS at `vms_edge`; vehicles first seen there whose route reaches `rejoin_edge` comply
        with probability c (hashed per vehicle id -> CRN across branches) and get prefix + corridor B + suffix
  - A3: A1 + A2;  A4: A2 with a stronger message (higher claimed compliance)
"""
import hashlib


def u_hash(vid: str, salt: str = "vms") -> float:
    h = hashlib.blake2b(f"{salt}:{vid}".encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") / 2 ** 64


class ActionExecutor:
    def __init__(self, scenario, compliance, control_state):
        self.sc = scenario
        self.c = compliance          # this world's TRUE compliance (Proxy hidden, Twin assumed)
        self.cs = control_state
        self.seen = set()
        self.vms_on = False
        self.n_diverted = 0

    def apply(self, tc, action, params=None):
        if action in ("A1", "A3"):
            for tls in self.sc["tls_plan"]:
                tc.trafficlight.setProgram(tls, "P_inc")   # predefined in tls_incident.add.xml
                self.cs.tls_program[tls] = "P_inc"
        if action in ("A2", "A3", "A4"):
            self.vms_on = True
            boost = 1.6 if action == "A4" else 1.0
            self.c_eff = min(1.0, self.c * boost)
            self.cs.vms = {"edge": self.sc["vms_edge"], "action": action}

    def step(self, tc):
        if not self.vms_on:
            return
        b = self.sc["corridor_b"]
        for vid in tc.edge.getLastStepVehicleIDs(self.sc["vms_edge"]):
            if vid in self.seen:
                continue
            self.seen.add(vid)
            route = list(tc.vehicle.getRoute(vid))
            if self.sc["rejoin_edge"] not in route or self.sc["vms_target_edge"] not in route:
                continue
            if u_hash(vid) >= self.c_eff:
                continue
            i0 = tc.vehicle.getRouteIndex(vid)
            j = route.index(self.sc["rejoin_edge"])
            new = route[i0:route.index(b[0])] + b + route[j + 1:] if b[0] in route else [route[i0]] + b + route[j + 1:]
            try:
                tc.vehicle.setRoute(vid, new)
                self.n_diverted += 1
            except Exception:
                pass
