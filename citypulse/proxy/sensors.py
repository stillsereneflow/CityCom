"""Sensor emulator: Proxy truth -> sparse, noisy, lossy SensorMsg (the only data the Twin may see)."""
import numpy as np

from citypulse.config import SENSOR_PERIOD


class SensorEmulator:
    def __init__(self, all_detectors, seed, coverage_rule="drop_every_3rd", q_cv=0.10, v_sd=3.0, o_sd=1.5,
                 loss=0.05, sensor_fault=None):
        ids = sorted(all_detectors)
        if coverage_rule == "drop_every_3rd":
            self.observed = [d for k, d in enumerate(ids) if k % 3 != 2]
        else:
            self.observed = ids
        self.rng = np.random.default_rng(seed)
        self.q_cv, self.v_sd, self.o_sd, self.loss = q_cv, v_sd, o_sd, loss
        self.sensor_fault = self._parse_fault(sensor_fault)
        self._last_valid = {}

    @staticmethod
    def _parse_fault(fault):
        if not fault:
            return []
        if isinstance(fault, str):
            faults = [f.strip() for f in fault.split(",") if f.strip()]
        elif isinstance(fault, (list, tuple)):
            faults = fault
        else:
            faults = [fault]
        res = []
        for f in faults:
            if isinstance(f, str):
                parts = f.split(":")
                if len(parts) == 4:
                    res.append({
                        "detector": parts[0],
                        "mode": parts[1],
                        "t_start": float(parts[2]),
                        "t_end": float(parts[3])
                    })
            elif isinstance(f, dict):
                res.append(f)
        return res

    def _get_active_fault(self, detector, t):
        for f in self.sensor_fault:
            if f["detector"] == detector and f["t_start"] <= t <= f["t_end"]:
                return f
        return None

    def emit(self, t, truth):
        obs = []
        for d in self.observed:
            fault = self._get_active_fault(d, t)
            if fault and fault["mode"] == "stuck":
                if d in self._last_valid:
                    last = self._last_valid[d]
                    obs.append({"detector": d, "q": last["q"], "v": last["v"], "o": last["o"], "valid": True})
                else:
                    tr = truth[d]
                    obs.append({"detector": d, "q": tr["q"], "v": tr["v"], "o": tr["o"], "valid": True})
                continue
            elif fault and fault["mode"] == "zero":
                obs.append({"detector": d, "q": 0, "v": None, "o": 0.0, "valid": True})
                continue

            tr = truth[d]
            if self.rng.random() < self.loss:
                obs.append({"detector": d, "q": None, "v": None, "o": None, "valid": False})
                continue
            q = int(max(0, round(tr["q"] * self.rng.normal(1.0, self.q_cv))))
            v = None if tr["v"] is None else float(max(0.0, tr["v"] + self.rng.normal(0, self.v_sd)))
            o = float(min(100.0, max(0.0, tr["o"] + self.rng.normal(0, self.o_sd))))
            obs.append({"detector": d, "q": q, "v": v, "o": o, "valid": True})
            self._last_valid[d] = {"q": q, "v": v, "o": o}
        return {"type": "sensor", "t": float(t), "period": SENSOR_PERIOD, "obs": obs}
