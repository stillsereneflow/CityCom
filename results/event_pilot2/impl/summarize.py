"""Compact console summary of the pilot-2 artefacts (for inspection; the report is make_report.py)."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "results/event_pilot2/runs"


def main():
    s = json.loads((REPO / "results/event_pilot2/runs_summary.json").read_text(encoding="utf-8"))
    for n, v in sorted(s.items()):
        q = v.get("queue_forecasts", {})
        a = v.get("alarms", {})
        e = v.get("event", {})
        s5, s15 = q.get("summary_5min", {}), q.get("summary_15min", {})
        print(f"{n:18s} alarms={a.get('alarm_events')} exp_min={a.get('exposure_min')} "
              f"first={a.get('first_alarm_t')} last={a.get('last_alarm_t')} "
              f"5min(mae={s5.get('mae')},rmse={s5.get('rmse')},bias={s5.get('bias')},n={s5.get('n')}) "
              f"15min(mae={s15.get('mae')},rmse={s15.get('rmse')},bias={s15.get('bias')},n={s15.get('n')})")
        if e:
            print(f"{'':18s} n_eval={e.get('n_eval')} n_repl={e.get('n_replacements')} "
                  f"transitions={[(t['t'], t['to'], t['reason']) for t in (e.get('transitions') or [])]}")
            for r in e.get("event_rows", []):
                hs = next((h for h in r["hypotheses"] if h["id"] == r["h_star"]), None)
                print(f"{'':18s}   t={r['t']} {r['state']} h*={r['h_star']} "
                      f"({hs['family'] if hs else None}) gap={r['gap_vs_demand']} evr={r['evr']} "
                      f"adopted={r['adopted']} p_clear={r['p_clear']} wall={r['wall_s']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
