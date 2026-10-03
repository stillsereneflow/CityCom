"""Dev-only two-world launcher for the event-pilot smoke run (results/event_pilot/impl/).

Mirrors ``citypulse.experiments.run_two_worlds`` (Twin process first, 2-s wait, then the Proxy; the
two talk only over the ZeroMQ firewall) and adds the Twin flags that launcher cannot pass:
``--assim normal300 --boundary-detector AID07106 --sigma-json ... --twin-base-factor 0.85 --event on
--event-sigma ... --event-workers 8``. The incident lives in the Proxy only and is ON by default --
the INC arm is the plain Proxy (``--no-incident`` gives the NOI control, not used here).

Twin: seed 2, demand seed 202, synth5 candidate pool. Proxy: seed 4001 (sensor seed 77 = default),
synth5 proxy routes, 7,200 s.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCEN = REPO / "scenarios" / "kwuntong" / "blite" / "synth5"
PLAIN = "from citypulse.proxy.service import main\nmain()\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run dir relative to results/")
    ap.add_argument("--t-end", type=float, default=7200)
    ap.add_argument("--port", type=int, default=5581)
    ap.add_argument("--proxy-seed", type=int, default=4001)
    ap.add_argument("--twin-seed", type=int, default=2)
    ap.add_argument("--demand-seed", type=int, default=202)
    ap.add_argument("--assim", default="normal300")
    ap.add_argument("--boundary-detector", default="AID07106")
    ap.add_argument("--sigma-json", default="results/assim/na300/sigma300_dev.json")
    ap.add_argument("--twin-base-factor", type=float, default=0.85)
    ap.add_argument("--event", default="on", choices=["on", "off"])
    ap.add_argument("--event-sigma", default="results/event_pilot/impl/sigma_event.json")
    ap.add_argument("--event-workers", type=int, default=8)
    ap.add_argument("--twin-snapshot", type=float, nargs="*", default=[4200, 4800, 5400, 6000])
    ap.add_argument("--no-incident", action="store_true")
    a = ap.parse_args()

    env = dict(os.environ, CITYPULSE_NET="blite", CITYPULSE_BLITE_REV="5", CITYPULSE_REROUTE="0",
               PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1")
    run = REPO / "results" / a.run
    (run / "twin").mkdir(parents=True, exist_ok=True)
    (run / "proxy").mkdir(parents=True, exist_ok=True)
    ep = f"tcp://127.0.0.1:{a.port}"

    targs = [sys.executable, "-m", "citypulse.twin.service", "--endpoint", ep,
             "--out", str(run / "twin"), "--seed", str(a.twin_seed),
             "--demand-seed", str(a.demand_seed), "--demand-path", str(SCEN / "twin_cand.rou.xml"),
             "--assim", a.assim, "--boundary-detector", a.boundary_detector,
             "--sigma-json", str(REPO / a.sigma_json), "--twin-base-factor", str(a.twin_base_factor),
             "--event", a.event]
    if a.event == "on":
        targs += ["--event-sigma", str(REPO / a.event_sigma), "--event-workers", str(a.event_workers)]
    if a.twin_snapshot:
        targs += ["--snapshot-times", *map(str, a.twin_snapshot)]

    pargs = [sys.executable, "-c", PLAIN, "--endpoint", ep, "--out", str(run / "proxy"),
             "--t-end", str(a.t_end), "--seed", str(a.proxy_seed),
             "--routes", str(SCEN / "proxy.rou.xml")]
    if a.no_incident:
        pargs.append("--no-incident")

    t0 = time.time()
    twin = subprocess.Popen(targs, env=env, cwd=str(REPO))
    time.sleep(2)
    proxy = subprocess.Popen(pargs, env=env, cwd=str(REPO))
    rc_p, rc_t = proxy.wait(), twin.wait()
    info = {"proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": round(time.time() - t0, 1), "t_end": a.t_end,
            "proxy_seed": a.proxy_seed, "twin_seed": a.twin_seed, "demand_seed": a.demand_seed,
            "incident": not a.no_incident, "assim": a.assim, "boundary_detector": a.boundary_detector,
            "sigma_json": a.sigma_json, "twin_base_factor": a.twin_base_factor, "event": a.event,
            "event_sigma": a.event_sigma, "event_workers": a.event_workers,
            "snapshot_times": list(a.twin_snapshot), "twin_argv": targs[1:], "proxy_argv": pargs[1:]}
    json.dump(info, open(run / "run_info.json", "w"), indent=1)
    print(json.dumps(info))
    sys.exit(rc_p or rc_t)


if __name__ == "__main__":
    main()
