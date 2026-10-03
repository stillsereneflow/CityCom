"""Dev-only two-world launcher for the NA-300 implementation work (results/assim/na300_impl/).

Mirrors ``results/assim/impl/run_assim_smoke.py`` (itself a copy of
``citypulse.experiments.run_two_worlds``, which cannot pass a Proxy seed or the assimilation flags)
and adds:
  --assim {off,normal,normal300}   forwarded to the Twin only when given (omitted = pre-change CLI)
  --twin-base-factor F             forwarded to the Twin only when given (pre-change CLI rejects it)
  --boundary-detector D            forwarded to the Twin
  --sigma-json PATH                forwarded to the Twin
  --twin-snapshot T ...            forwarded to the Twin
  --twin-script PATH               launch this file instead of ``-m citypulse.twin.service``
                                   (online_logged.py = the same service + an insertion recorder)

Omitting --assim/--twin-base-factor makes this script able to drive the pre-change revision, which
is what the 900-s off-mode identity check needs.
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
    ap.add_argument("--t-end", type=float, default=900)
    ap.add_argument("--port", type=int, default=5571)
    ap.add_argument("--proxy-seed", type=int, default=1001)
    ap.add_argument("--assim", default=None, choices=[None, "off", "normal", "normal300"])
    ap.add_argument("--sigma-json", default=None)
    ap.add_argument("--boundary-detector", default=None)
    ap.add_argument("--twin-base-factor", type=float, default=None)
    ap.add_argument("--twin-snapshot", type=float, nargs="*", default=[])
    ap.add_argument("--twin-script", default=None, help="launch this file as the Twin process")
    a = ap.parse_args()

    env = dict(os.environ, CITYPULSE_NET="blite", CITYPULSE_BLITE_REV="5", CITYPULSE_REROUTE="0",
               PYTHONDONTWRITEBYTECODE="1")
    run = REPO / "results" / a.run
    (run / "twin").mkdir(parents=True, exist_ok=True)
    (run / "proxy").mkdir(parents=True, exist_ok=True)
    ep = f"tcp://127.0.0.1:{a.port}"

    targs = ([sys.executable, str(a.twin_script)] if a.twin_script
             else [sys.executable, "-m", "citypulse.twin.service"])
    targs += ["--endpoint", ep, "--out", str(run / "twin"),
              "--demand-path", str(SCEN / "twin_cand.rou.xml")]
    if a.assim:
        targs += ["--assim", a.assim]
    if a.sigma_json:
        targs += ["--sigma-json", a.sigma_json]
    if a.boundary_detector:
        targs += ["--boundary-detector", a.boundary_detector]
    if a.twin_base_factor is not None:
        targs += ["--twin-base-factor", str(a.twin_base_factor)]
    if a.twin_snapshot:
        targs += ["--snapshot-times", *map(str, a.twin_snapshot)]

    pargs = [sys.executable, "-c", PLAIN,
             "--endpoint", ep, "--out", str(run / "proxy"), "--t-end", str(a.t_end),
             "--no-incident", "--routes", str(SCEN / "proxy.rou.xml"), "--seed", str(a.proxy_seed)]

    t0 = time.time()
    twin = subprocess.Popen(targs, env=env, cwd=str(REPO))
    time.sleep(2)
    proxy = subprocess.Popen(pargs, env=env, cwd=str(REPO))
    rc_p, rc_t = proxy.wait(), twin.wait()
    info = {"proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": round(time.time() - t0, 1), "t_end": a.t_end,
            "proxy_seed": a.proxy_seed, "assim": a.assim, "sigma_json": a.sigma_json,
            "boundary_detector": a.boundary_detector, "twin_base_factor": a.twin_base_factor,
            "twin_script": a.twin_script, "snapshot_times": list(a.twin_snapshot),
            "twin_argv": targs[1:]}
    json.dump(info, open(run / "run_info.json", "w"), indent=1)
    print(json.dumps(info))
    sys.exit(rc_p or rc_t)


if __name__ == "__main__":
    main()
