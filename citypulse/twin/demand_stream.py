"""Twin demand: Poisson-thinning candidate stream (report2 §G.1).

Candidates come from twin_cand.rou.xml (sampled at TWIN_CAND_SCALE x counts, independent of the Proxy's
latent demand). Each candidate n has a fixed uniform u_n (seeded); it is inserted iff
u_n < factor(entry) * m_s / scale, where ``factor`` is the Twin base factor of that entry (1.0 for
every entry except the TKO entry, whose factor is set by --twin-base-factor). The stream is a pure
function of (seed, factor, m path), so every branch replaying from a snapshot sees the same
vehicles (common random numbers) and a rewind never duplicates or skips vehicles.
"""
import xml.etree.ElementTree as ET

import bisect
import os
import numpy as np

from citypulse.config import SCEN
from citypulse.demand.make_demand import TWIN_CAND_SCALE

BASE_FACTOR_ENTRY = "tko_insert"   # the only entry --twin-base-factor scales


class TwinDemandStream:
    def __init__(self, seed=0, path=None, scale=TWIN_CAND_SCALE, base_factor=1.0,
                 factor_entries=(BASE_FACTOR_ENTRY,)):
        if path is None:
            net = os.environ.get("CITYPULSE_NET", "").strip().lower()
            if net == "blite":
                p = SCEN / "blite" / "demand" / "twin_cand.rou.xml"
                path = p if p.exists() else (SCEN / "blite" / "twin_cand.rou.xml")
            elif net == "v4":
                path = SCEN / "v4" / "twin_cand.rou.xml"
            else:
                path = SCEN / "twin_cand.rou.xml"
        root = ET.parse(path).getroot()
        cands = []
        is_blite = os.environ.get("CITYPULSE_NET", "").strip().lower() == "blite"
        for v in root.iter("vehicle"):
            r = v.find("route")
            if r is None:
                continue
            edges = r.get("edges").split()
            if is_blite:
                adapted = []
                for i, e in enumerate(edges):
                    adapted.append(e)
                    if i < len(edges) - 1:
                        nxt = edges[i + 1]
                        if (e in ('ktb_w1', 'on_ktb_w2')) and nxt == 'ktb_w2':
                            adapted.append('ms_on_ktb_w2')
                        elif (e in ('tko_a1', 'on_ktr_w1')) and nxt == 'ktr_w1':
                            adapted.append('ms_on_ktr_w1')
                        elif e == 'ktb_n1' and (nxt in ('ktb_n2', 'off_ktb_n1')):
                            adapted.append('dv_off_ktb_n1')
                edges = adapted
            cands.append((float(v.get("depart")), v.get("id"), edges))
        cands.sort()
        self.cands = cands
        self.u = np.random.default_rng(seed).random(len(cands))
        self.scale = scale
        self.base_factor = float(base_factor)
        self.factor_entries = tuple(factor_entries)
        self.m = {}   # entry edge -> multiplier (1.0 = base demand)
        self.ptr = 0

    def multiplier(self, entry):
        return self.m.get(entry, 1.0)

    def factor(self, entry):
        """Twin base factor of `entry`: 1.0 for every entry it is not configured for."""
        return self.base_factor if entry in self.factor_entries else 1.0

    def acceptance(self, entry):
        """Thinning threshold: candidate n of `entry` is inserted iff u_n < this value."""
        return self.factor(entry) * self.multiplier(entry) / self.scale

    def base_rate(self, entry, t, window=300.0):
        """base_s(t): candidate-pool insertion rate of `entry` in veh/h, over [t-window, t+window).

        Reads only the candidate list (a pure function of the pool, so identical in every branch),
        divided by the pool scale: with m_s = 1.0 the expected insertion rate is exactly this value.
        Candidates are counted by their first edge, the same key ``due`` uses for the multiplier.
        The window is clamped to the candidate pool's span and the count divided by that actual
        in-pool length, so the rate is not scaled down where the window overruns the pool (F3).
        """
        lo = bisect.bisect_left(self.cands, (t - window,))
        hi = bisect.bisect_left(self.cands, (t + window,))
        n = sum(1 for i in range(lo, hi) if self.cands[i][2][0] == entry)
        if not self.cands:
            return 0.0
        w_lo = max(t - window, self.cands[0][0])
        w_hi = min(t + window, self.cands[-1][0])
        span = w_hi - w_lo
        if span <= 0:
            return 0.0
        return n * 3600.0 / span / self.scale

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
            if u < self.acceptance(edges[0]):
                yield vid, edges

    def insert_due(self, tc, t, vtype="tdist"):
        n = 0
        for vid, edges in self.due(t):
            rid = "r_" + vid
            tc.route.add(rid, edges)
            tc.vehicle.add(vid, rid, typeID=vtype, departLane="best", departSpeed="max")
            n += 1
        return n
