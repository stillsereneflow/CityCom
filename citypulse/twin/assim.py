"""Normal-mode assimilation (report2 §G.3, docs/oct5-normal-assim-plan.md "NA, as specified").

Pure and SUMO-free: the caller supplies, for the last two 30-s intervals, the boundary detector's
observation and the Twin's own reading as ``(q, v, o, valid)``, plus ``base_s(t)`` (the entry's
Twin base insertion rate in veh/h) and ``sigma_b^q`` (veh/h).

Every 60 s:

    if o_b < o_crit and b is valid in both intervals:
        e_s = (q_b - q̂_b) / base_s(t)                       # both q in veh/h
        if |r_b^q| > delta:                                  # r_b^q = (q_b - q̂_b) / sigma_b^q
            m_s <- clip(m_s * (1 + clip(kappa * e_s, -0.05, +0.05)), 0.5, 1.8)
    else:
        m_s unchanged                                        # congested flow is not demand

Units: ``read_detectors``/``SensorMsg`` report counts per 30-s interval, so q is multiplied by 120
to get veh/h; the two intervals are averaged. Missing or invalid data in either interval, a missing
detector, a non-positive base rate or a missing/non-positive sigma all mean no update.
"""
from __future__ import annotations

from dataclasses import dataclass

INTERVAL_S = 30.0
PER_HOUR = 3600.0 / INTERVAL_S  # 120: counts per 30-s interval -> veh/h


@dataclass
class Interval:
    """One 30-s interval of a single detector: q (veh per interval), v (km/h), o (%), valid."""

    q: float | None = None
    v: float | None = None
    o: float | None = None
    valid: bool = True

    @classmethod
    def of(cls, x):
        """Accept a mapping (SensorMsg ObsItem / read_detectors row) or an Interval."""
        if x is None or isinstance(x, cls):
            return x
        return cls(q=x.get("q"), v=x.get("v"), o=x.get("o"), valid=x.get("valid", True))


def _field(x, key):
    if isinstance(x, dict):
        return x.get(key)
    return getattr(x, key, None)


def _usable(iv):
    """A usable interval has valid=True and numeric q and o (v is not needed by the update)."""
    if iv is None or not bool(_field(iv, "valid")):
        return False
    q, o = _field(iv, "q"), _field(iv, "o")
    return q is not None and o is not None


def _mean(values):
    return sum(values) / len(values)


def _clip(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


class NormalAssimilator:
    """report2 §G.3 entry-demand update for one boundary entry.

    Parameters (defaults fixed by the predeclared plan, no tuning): kappa=0.3, delta=1.0 sigma,
    per-tick step clip ±0.05, m in [0.5, 1.8], o_crit=15%.
    """

    def __init__(self, kappa=0.3, delta=1.0, step_clip=0.05, m_min=0.5, m_max=1.8, o_crit=15.0,
                 sigma_q=None):
        self.kappa = float(kappa)
        self.delta = float(delta)
        self.step_clip = float(step_clip)
        self.m_min = float(m_min)
        self.m_max = float(m_max)
        self.o_crit = float(o_crit)
        self.sigma_q = None if sigma_q is None else float(sigma_q)

    def update(self, t, obs, twin, base_vehph, m, sigma_q=None):
        """One 60-s tick.

        obs, twin: the last two 30-s intervals (oldest first) of the boundary detector, each a
        mapping with q/v/o/valid (SensorMsg ObsItem or read_detectors row) or an Interval.
        base_vehph: base_s(t) in veh/h. m: current multiplier.
        Returns (m_new, row) with row = {t, e_s, r, delta, m, reason}, reason in
        {"updated", "deadband", "congested", "invalid"}.
        """
        sigma = self.sigma_q if sigma_q is None else float(sigma_q)
        row = {"t": float(t), "e_s": None, "r": None, "delta": None, "m": float(m),
               "reason": "invalid"}
        if not isinstance(obs, (list, tuple)) or not isinstance(twin, (list, tuple)):
            return float(m), row
        if len(obs) != 2 or len(twin) != 2:
            return float(m), row
        o2 = [Interval.of(x) for x in obs]
        w2 = [Interval.of(x) for x in twin]
        if not all(_usable(x) for x in o2 + w2):
            return float(m), row
        if _mean([_field(x, "o") for x in o2]) >= self.o_crit:
            row["reason"] = "congested"
            return float(m), row
        if base_vehph is None or base_vehph <= 0 or sigma is None or sigma <= 0:
            return float(m), row
        q_obs = _mean([_field(x, "q") for x in o2]) * PER_HOUR
        q_twin = _mean([_field(x, "q") for x in w2]) * PER_HOUR
        resid = q_obs - q_twin
        e_s = resid / base_vehph
        r = resid / sigma
        row["e_s"], row["r"] = e_s, r
        if abs(r) <= self.delta:
            row["reason"] = "deadband"
            return float(m), row
        step = _clip(self.kappa * e_s, -self.step_clip, self.step_clip)
        m_new = _clip(float(m) * (1.0 + step), self.m_min, self.m_max)
        row["delta"], row["m"], row["reason"] = step, m_new, "updated"
        return m_new, row
