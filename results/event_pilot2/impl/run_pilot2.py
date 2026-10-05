"""Pilot-2 driver: runs, forecasts, forced-adoption integration runs, evidence, report.

docs/oct6-audit-and-pilot2-plan.md part B. Steps (each idempotent: completed work is skipped):

1. the 9 pilot-2 runs (INC EVT + INC CONV + NOI EVT on seeds 4101-4103) and their queue forecasts;
2. if no INC EVT run adopted naturally, the 3 labelled forced-adoption runs;
3. the replay-based checks 2/4/7 (``check_replays.py``);
4. the artefact-based checks and the adoption summary (``make_evidence.py``);
5. the report (``make_report.py``).

Usage: python results/event_pilot2/impl/run_pilot2.py [--parallel 3] [--skip-runs] [--skip-forced]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.experiments import event_pilot as ep  # noqa: E402

IMPL = REPO / "results/event_pilot2/impl"
INC_EVT = ("evt_inc_4101", "evt_inc_4102", "evt_inc_4103")
FORCED = ("evtforce_inc_4101", "evtforce_inc_4102", "evtforce_inc_4103")


def run(cmd):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=str(REPO)).returncode


def adopted(run_name):
    p = ep.PILOT2_RUNS_DIR / run_name / "twin/twin_stats.json"
    if not p.exists():
        return None
    ev = (json.loads(p.read_text(encoding="utf-8")).get("event") or {})
    return bool(ev.get("n_replacements"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--skip-runs", action="store_true")
    ap.add_argument("--skip-forced", action="store_true")
    a = ap.parse_args()

    if not a.skip_runs:
        ep.main_pilot2(parallel=a.parallel)
    natural = {n: adopted(n) for n in INC_EVT}
    print(f"natural adoption in the INC EVT runs: {natural}")
    if not a.skip_forced and not any(natural.values()):
        print("no natural adoption -> running the labelled forced-adoption integration runs")
        ep.main_pilot2(parallel=a.parallel, force_only=True)
    elif not any(natural.values()):
        print("no natural adoption; forced runs skipped by request")
    else:
        print("natural adoption occurred -> the forced-adoption test is not required")

    py = sys.executable
    run([py, IMPL / "check_replays.py", "--run", "results/event_pilot2/runs/evt_inc_4101",
         "--forced-run", "results/event_pilot2/runs/evtforce_inc_4101"])
    run([py, IMPL / "make_evidence.py"])
    run([py, IMPL / "make_report.py"])
    print("\nPILOT2 DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
