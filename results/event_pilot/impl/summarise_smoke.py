"""Summarise the event-pilot smoke run from its logs (no simulation).

Reads ``<run>/twin/{event_log.jsonl, state_trace.jsonl, trigger_log.parquet,
replacement_log.jsonl, assim_log.parquet, twin_stats.json}`` and prints/writes the numbers the report
needs: the state trace, per-evaluation rows, adoption and clearance times, wall times, the trigger
alarms, the exclusions, and mechanics checks 5 (exact regional freeze) and 9/10 (adoption counts and
DEGRADED duration).

Usage: python results/event_pilot/impl/summarise_smoke.py --run results/event_pilot/impl/smoke_inc
Writes: <run>/summary.json
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="results/event_pilot/impl/smoke_inc")
    a = ap.parse_args()
    twin = REPO / a.run / "twin"
    stats = json.loads((twin / "twin_stats.json").read_text(encoding="utf-8"))
    ev_rows = read_jsonl(twin / "event_log.jsonl")
    trace = read_jsonl(twin / "state_trace.jsonl")
    repl = read_jsonl(twin / "replacement_log.jsonl")
    trig = pd.read_parquet(twin / "trigger_log.parquet")
    assim = pd.read_parquet(twin / "assim_log.parquet") if (twin / "assim_log.parquet").exists() else None

    evsum = []
    for r in ev_rows:
        hyps = r.get("hypotheses") or []
        star = next((h for h in hyps if h["id"] == r.get("h_star")), None)
        evsum.append({"t": r["t"], "state": r["state"], "h_star": r.get("h_star"),
                      "family": None if star is None else star["family"],
                      "params": None if star is None else star["params"],
                      "gap": r.get("gap_vs_demand"), "evr": r.get("evr"), "adopted": r.get("adopted"),
                      "p_clear": r.get("p_clear"), "n_O": None if not hyps else hyps[0]["n_O"],
                      "excluded": r.get("excluded"), "wall_s": r.get("wall_s")})

    alarms = trig[trig["B"].notna() & (trig["B"] >= 3.0)]["t"].tolist()
    b_ok = trig[trig["B"].notna()]
    max_b = float(b_ok["B"].max()) if len(b_ok) else None
    max_b_t = float(b_ok.loc[b_ok["B"].idxmax(), "t"]) if len(b_ok) else None
    adopt = [t for t in trace if t["to"] == "EVENT_ASSIMILATION"]
    clear = [t for t in trace if t["to"] == "RECOVERY"]
    walls = [r["wall_s"] for r in evsum if r["wall_s"] is not None]

    # check 5: m constant while frozen (assim_log reasons) except DEGRADED's slow rule
    freeze_check = None
    if assim is not None and len(assim):
        rows = assim.to_dict("records")
        frozen_m = {round(r["m"], 12) for r in rows if r["reason"] == "frozen"}
        freeze_check = {"n_ticks": len(rows), "reasons": {},
                        "frozen_m_values": sorted(frozen_m),
                        "m_constant_while_frozen": len(frozen_m) <= 1}
        for r in rows:
            freeze_check["reasons"][r["reason"]] = freeze_check["reasons"].get(r["reason"], 0) + 1

    out = {"stats_event": stats.get("event"), "state_trace": trace, "evaluations": evsum,
           "alarms": alarms, "n_alarm_ticks": len(alarms),
           "max_B": max_b, "max_B_t": max_b_t, "n_ticks_B_ge_3": len(alarms),
           "n_trigger_ticks": int(len(trig)), "n_masked_ticks": int(trig["masked"].sum()),
           "adoption": adopt, "clearance": clear, "replacements": repl,
           "wall_s": {"n": len(walls), "total": float(sum(walls)), "mean": (sum(walls) / len(walls)) if walls else None,
                      "max": max(walls) if walls else None},
           "run_wall_s": stats.get("wall_s"), "freeze_check": freeze_check,
           "assim_log": None if assim is None else assim.to_dict("records")}
    (REPO / a.run / "summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")

    def num(x, nd=3):
        return "None" if x is None else round(float(x), nd)

    print(f"run wall {num(stats.get('wall_s'), 1)}s, twin messages {stats.get('messages')}")
    print("state trace:")
    for tr in trace:
        print(f"  t={tr['t']:8.1f}  {tr['from']:18s} -> {tr['to']:18s}  {tr['reason']}")
    print(f"evaluations: {len(evsum)}")
    for e in evsum:
        print(f"  t={e['t']:8.1f} state={e['state']:18s} h*={str(e['h_star']):22s} "
              f"gap={num(e['gap'])} evr={num(e['evr'])} adopted={e['adopted']} "
              f"p_clear={num(e['p_clear'])} n_O={e['n_O']} wall={num(e['wall_s'], 1)}s "
              f"excluded={e['excluded']}")
    print(f"alarm ticks (B>=3): {len(alarms)} first={alarms[0] if alarms else None}; "
          f"max B={num(max_b)} at t={max_b_t} over {len(trig)} trigger ticks "
          f"({int(trig['masked'].sum())} masked)")
    print(f"evaluation wall: n={len(walls)} total={sum(walls):.1f}s max={max(walls) if walls else None}")
    print(f"freeze check: {freeze_check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
