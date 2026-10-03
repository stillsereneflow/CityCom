"""Run the whole event-pilot implementation sequence in order, logging everything.

  1. sigma   : results/event_pilot/impl/compute_sigma_event.py  -> sigma_event.json
  2. tests   : pytest tests/test_event.py
  3. smoke   : results/event_pilot/impl/run_event_smoke.py      -> results/event_pilot/impl/smoke_inc/
  4. checks  : results/event_pilot/impl/check_replay.py         -> check_replay.json (checks 2 and 4)
  5. summary : results/event_pilot/impl/summarise_smoke.py      -> smoke_inc/summary.json
  6. ready   : results/event_pilot/impl/make_ready.py           -> EVENT_READY

Usage: python results/event_pilot/impl/run_all.py [--only sigma,tests,smoke,checks,summary,ready]
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PY = sys.executable
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1",
           CITYPULSE_NET="blite", CITYPULSE_BLITE_REV="5", CITYPULSE_REROUTE="0")

STEPS = {
    "sigma": [PY, "results/event_pilot/impl/compute_sigma_event.py"],
    "tests": [PY, "-m", "pytest", "tests/test_event.py", "-q", "-p", "no:cacheprovider"],
    "smoke": [PY, "results/event_pilot/impl/run_event_smoke.py", "--run",
              "event_pilot/impl/smoke_inc"],
    "checks": [PY, "results/event_pilot/impl/check_replay.py"],
    "summary": [PY, "results/event_pilot/impl/summarise_smoke.py"],
    "ready": [PY, "results/event_pilot/impl/make_ready.py"],
}
ORDER = ["sigma", "tests", "smoke", "checks", "summary", "ready"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(ORDER))
    ap.add_argument("--keep-going", action="store_true",
                    help="continue after a failing step (default: stop, so a missing sigma cannot "
                         "leave the two-world run hanging on the REQ/REP socket)")
    a = ap.parse_args()
    only = [s.strip() for s in a.only.split(",") if s.strip()]
    log = OUT / "run_all.log"
    rcs = {}
    with open(log, "w", encoding="utf-8") as fh:
        for name in ORDER:
            if name not in only:
                continue
            cmd = STEPS[name]
            fh.write(f"\n===== {name}: {' '.join(cmd)} =====\n")
            fh.flush()
            t0 = time.time()
            p = subprocess.run(cmd, cwd=str(REPO), env=ENV, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
            wall = time.time() - t0
            fh.write(p.stdout or "")
            fh.write(f"\n----- {name}: rc={p.returncode} wall={wall:.1f}s -----\n")
            fh.flush()
            print(f"[{name}] rc={p.returncode} wall={wall:.1f}s")
            print((p.stdout or "")[-4000:])
            rcs[name] = p.returncode
            if p.returncode != 0 and not a.keep_going:
                print(f"stopping after {name} (rc={p.returncode}); use --keep-going to continue")
                break
    print(f"rcs={rcs}; full log: {log}")
    return 0 if all(v == 0 for v in rcs.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
