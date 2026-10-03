"""Re-run the three EVT INC pilot runs with the fixed fault-model likelihood.

Uses the harness unchanged (``citypulse.experiments.event_pilot.run_two_world``) with exactly the
arguments recorded in ``results/event_pilot/runs/evt_inc_<seed>/run_info.json``; only ``RUNS_DIR`` is
redirected so the new artefacts land in ``results/event_pilot/fix/evt_inc_<seed>/`` instead of over
the old runs. Seeds 4001, 4002, 4003 run in parallel on ports 5801-5803.

Usage: python results/event_pilot/fix/run_evt_inc.py
"""
import json
import multiprocessing as mp
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.experiments import event_pilot as ep   # noqa: E402

FIX_DIR = REPO / "results/event_pilot/fix"
SEEDS = [4001, 4002, 4003]
PORTS = {4001: 5801, 4002: 5802, 4003: 5803}


def one(seed):
    ep.RUNS_DIR = FIX_DIR          # evt_inc_<seed> -> results/event_pilot/fix/evt_inc_<seed>/
    return ep.run_two_world(f"evt_inc_{seed}", "INC", seed, "evt", PORTS[seed],
                            str(ep.IMPL_DIR / "sigma_event.json"))


def main():
    with mp.Pool(processes=len(SEEDS)) as pool:
        infos = pool.map(one, SEEDS)
    for info in infos:
        print(json.dumps(info))
    print("ALL DONE")


if __name__ == "__main__":
    main()
