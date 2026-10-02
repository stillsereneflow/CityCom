"""Twin demand: Poisson-thinning candidate stream (report2 §G.1).

Candidates come from twin_cand.rou.xml (sampled at TWIN_CAND_SCALE x counts, independent of the Proxy's
latent demand). Each candidate n has a fixed uniform u_n (seeded); it is inserted iff u_n < m_s / scale.
The stream is a pure function of (seed, m), so every branch replaying from a snapshot sees the same
vehicles (common random numbers) and a rewind never duplicates or skips vehicles.
"""
import xml.etree.ElementTree as ET

import numpy as np

from citypulse.config import SCEN
from citypulse.demand.make_demand import TWIN_CAND_SCALE


class TwinDemandStream:
    def __init__(self, seed=0, path=None, scale=TWIN_CAND_SCALE):
        root = ET.parse(path or SCEN / "twin_cand.rou.xml").getroot()
        cands = []
        for v in root.iter("vehicle"):
            r = v.find("route")
            if r is None:
                continue
            cands.append((float(v.get("depart")), v.get("id"), r.get("edges").split()))
        cands.sort()
        self.cands = cands
        self.u = np.random.default_rng(seed).random(len(cands))
        self.scale = scale
        self.m = {}   # entry edge -> multiplier (1.0 = base demand)
        self.ptr = 0

    def multiplier(self, entry):
        return self.m.get(entry, 1.0)

    def seek(self, t):
        """Position the pointer at the first candidate with depart > t (used after loadState)."""
        lo, hi = 0, len(self.cands)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cands[mid][0] <= t:
                lo = mid + 1
            else:
                hi = mid
        self.ptr = lo

    def due(self, t):
        """Yield accepted candidates with depart <= t, advancing the pointer."""
        while self.ptr < len(self.cands) and self.cands[self.ptr][0] <= t:
            dep, vid, edges = self.cands[self.ptr]
            u = self.u[self.ptr]
            self.ptr += 1
            if u < self.multiplier(edges[0]) / self.scale:
                yield vid, edges

    def insert_due(self, tc, t, vtype="tdist"):
        n = 0
        for vid, edges in self.due(t):
            rid = "r_" + vid
            tc.route.add(rid, edges)
            tc.vehicle.add(vid, rid, typeID=vtype, departLane="best", departSpeed="max")
            n += 1
        return n
