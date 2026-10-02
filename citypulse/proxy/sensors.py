"""Sensor emulator: Proxy truth -> sparse, noisy, lossy SensorMsg (the only data the Twin may see)."""
import numpy as np

from citypulse.config import SENSOR_PERIOD


class SensorEmulator:
    def __init__(self, all_detectors, seed, coverage_rule="drop_every_3rd", q_cv=0.10, v_sd=3.0, o_sd=1.5,
                 loss=0.05):
        ids = sorted(all_detectors)
        if coverage_rule == "drop_every_3rd":
            self.observed = [d for k, d in enumerate(ids) if k % 3 != 2]
        else:
            self.observed = ids
        self.rng = np.random.default_rng(seed)
        self.q_cv, self.v_sd, self.o_sd, self.loss = q_cv, v_sd, o_sd, loss

    def emit(self, t, truth):
        obs = []
        for d in self.observed:
            tr = truth[d]
            if self.rng.random() < self.loss:
                obs.append({"detector": d, "q": None, "v": None, "o": None, "valid": False})
                continue
            q = int(max(0, round(tr["q"] * self.rng.normal(1.0, self.q_cv))))
            v = None if tr["v"] is None else float(max(0.0, tr["v"] + self.rng.normal(0, self.v_sd)))
            o = float(min(100.0, max(0.0, tr["o"] + self.rng.normal(0, self.o_sd))))
            obs.append({"detector": d, "q": q, "v": v, "o": o, "valid": True})
        return {"type": "sensor", "t": float(t), "period": SENSOR_PERIOD, "obs": obs}
