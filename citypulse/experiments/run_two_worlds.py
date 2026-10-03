"""Launch Twin and Proxy as two separate OS processes connected only by the ZeroMQ firewall.

Output layout: <run>/proxy/ (ground truth, Proxy-only) and <run>/twin/ (what the Twin saw and computed).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from citypulse.config import RESULTS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="two_worlds")
    ap.add_argument("--t-end", type=float, default=3000)
    ap.add_argument("--port", type=int, default=5557)
    ap.add_argument("--no-incident", action="store_true")
    ap.add_argument("--twin-snapshot", type=float, nargs="*", default=[])
    ap.add_argument("--proxy-snapshot", type=float, nargs="*", default=[])
    ap.add_argument("--routes", default=None, help="Proxy routes XML file")
    a = ap.parse_args()
    run = RESULTS / a.run
    ep = f"tcp://127.0.0.1:{a.port}"
    t0 = time.time()
    twin = subprocess.Popen([sys.executable, "-m", "citypulse.twin.service", "--endpoint", ep,
                             "--out", str(run / "twin"), "--snapshot-times", *map(str, a.twin_snapshot)])
    time.sleep(2)
    pargs = [sys.executable, "-m", "citypulse.proxy.service", "--endpoint", ep, "--out", str(run / "proxy"),
             "--t-end", str(a.t_end), "--snapshot-times", *map(str, a.proxy_snapshot)]
    if a.no_incident:
        pargs.append("--no-incident")
    if a.routes:
        pargs.extend(["--routes", str(a.routes)])
    proxy = subprocess.Popen(pargs)
    rc_p, rc_t = proxy.wait(), twin.wait()
    info = {"proxy_rc": rc_p, "twin_rc": rc_t, "wall_s": round(time.time() - t0, 1), "t_end": a.t_end,
            "incident": not a.no_incident}
    json.dump(info, open(run / "run_info.json", "w"), indent=1)
    print(json.dumps(info))
    sys.exit(rc_p or rc_t)


if __name__ == "__main__":
    main()
