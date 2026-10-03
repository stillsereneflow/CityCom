"""sigma_i^x for the event trigger: 1.4826 * MAD of the biased-OL residuals (obs - twin).

Source (spec: "sigma_i^x = 1.4826*MAD of the residuals from the biased-OL development runs
results/assim/na300/ol_4001..4003 (t >= 900 s)"): the three open-loop NA-300 development runs
(``--twin-base-factor 0.85``, no incident), rows with t >= 900 s and obs_valid = True, per detector
and channel x in {q, v, o}. Units are the Twin's: q per 30-s interval, v km/h, o per cent.

A zero MAD (a detector/channel whose residual never moves) falls back to a fixed per-channel floor
so the trigger and the likelihood never divide by zero; the fallback is recorded per detector.

Usage:  python results/event_pilot/impl/compute_sigma_event.py
Writes: results/event_pilot/impl/sigma_event.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUNS = ("ol_4001", "ol_4002", "ol_4003")
T_MIN = 900.0
CHANNELS = ("q", "v", "o")
FLOOR = {"q": 1.0, "v": 0.5, "o": 0.1}
PAIR = ("AID02109", "AID02111")


def main():
    frames = []
    for name in RUNS:
        p = REPO / "results" / "assim" / "na300" / name / "twin" / "twin_log.parquet"
        df = pd.read_parquet(p)
        df = df[(df["t"] >= T_MIN) & (df["obs_valid"])]
        df = df.assign(run=name)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    sigma, med, mad, counts, fallback = {}, {}, {}, {}, {}
    for det, g in df.groupby("detector"):
        sigma[det], med[det], mad[det], counts[det], fallback[det] = {}, {}, {}, {}, {}
        for x in CHANNELS:
            r = (g[f"obs_{x}"] - g[f"twin_{x}"]).dropna().to_numpy(dtype=float)
            counts[det][x] = int(r.size)
            if r.size == 0:
                sigma[det][x] = None
                fallback[det][x] = "no_residuals"
                continue
            m = float(np.median(r))
            a = float(1.4826 * np.median(np.abs(r - m)))
            med[det][x], mad[det][x] = m, a
            if a > 0.0:
                sigma[det][x] = a
            else:
                sigma[det][x] = FLOOR[x]
                fallback[det][x] = "mad_zero_floor"

    out = {"sigma": sigma, "pair": list(PAIR), "t_min": T_MIN, "runs": list(RUNS),
           "channel_floor": FLOOR, "median": med, "mad": mad, "n_residuals": counts,
           "fallbacks": {d: {x: v for x, v in f.items() if v} for d, f in fallback.items()},
           "source": "results/assim/na300/ol_4001..4003 twin_log.parquet (biased OL, factor 0.85)",
           "formula": "1.4826 * median(|r - median(r)|), r = obs_x - twin_x, t >= 900 s, obs_valid"}
    (OUT / "sigma_event.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"{'detector':10s} {'n_q':>6s} {'sigma_q':>10s} {'sigma_v':>9s} {'sigma_o':>9s}  fallback")
    for det in sorted(sigma):
        fb = ",".join(f"{x}:{v}" for x, v in fallback[det].items()) or "-"
        def f(x):
            v = sigma[det][x]
            return "None" if v is None else f"{v:.4f}"
        print(f"{det:10s} {counts[det]['q']:6d} {f('q'):>10s} {f('v'):>9s} {f('o'):>9s}  {fb}")
    for det in PAIR:
        assert sigma.get(det) and all(sigma[det][x] for x in ("v", "o")), f"pair detector {det} bad"
    print(f"wrote {OUT / 'sigma_event.json'} ({len(sigma)} detectors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
