"""Mechanics checks 2 and 4 on a real smoke-run snapshot (no new two-world run).

Check 2 (deterministic replay): the same hypothesis scored twice at the same t gives identical logL.
A single hypothesis has no demand family, so its logL is accumulated directly (``ev.logl_of_one``)
instead of through ``ev.evaluate``, which needs that family for the posterior gap and the EVR.
Check 4 (effective capacity restriction): under an incident hypothesis the lanes are disallowed and
the downstream flow drops relative to the no-event replay.

Inputs: a persistent Twin snapshot written by ``--snapshot-times`` (default 4800) and the Twin's own
``twin_log.parquet`` from the smoke run -- the ``obs_*`` columns are exactly the values the Proxy
sent, so the likelihood is reproduced offline without touching the Proxy. The incident is applied at
``--t-on`` (default 4860, inside the Proxy-only incident window 4,500-5,400 s) and the replay runs to
``--t-end`` (default 5400).

Usage: python results/event_pilot/impl/check_replay.py [--run results/event_pilot/impl/smoke_inc]
Writes: results/event_pilot/impl/check_replay.json
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.branching.engine import score_replays          # noqa: E402
from citypulse.twin import event as ev                        # noqa: E402

OUT = Path(__file__).resolve().parent
DOWNSTREAM = ev.PAIR_D          # AID02111, downstream of the incident on ktb_n1
INCIDENT_HYP = "inc_ktb_n1_k2_s0.6"


def obs_from_twin_log(path, dets=None):
    df = pd.read_parquet(path)
    hist = {}
    for row in df.itertuples():
        if dets is not None and row.detector not in dets:
            continue
        hist.setdefault(row.detector, {})[float(row.t)] = {
            "detector": row.detector, "q": None if pd.isna(row.obs_q) else row.obs_q,
            "v": None if pd.isna(row.obs_v) else row.obs_v,
            "o": None if pd.isna(row.obs_o) else row.obs_o, "valid": bool(row.obs_valid)}
    return hist


def anchor_from(obs_hist, t_on):
    anchor = {}
    for det, rows in obs_hist.items():
        vals = {}
        for t in sorted(rows, reverse=True):
            if t >= t_on:
                continue
            r = rows[t]
            if not r["valid"]:
                continue
            for x in ev.CHANNELS:
                if x not in vals and r[x] is not None:
                    vals[x] = r[x]
        anchor[det] = vals
    return anchor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="results/event_pilot/impl/smoke_inc")
    ap.add_argument("--snapshot", type=float, default=4800)
    ap.add_argument("--t-on", type=float, default=4860)
    ap.add_argument("--t-end", type=float, default=5400)
    ap.add_argument("--hypothesis", default=INCIDENT_HYP)
    a = ap.parse_args()

    run = REPO / a.run / "twin"
    state = run / f"twin_state_{int(a.snapshot)}.xml.gz"
    meta = run / f"twin_state_{int(a.snapshot)}.json"
    sigma = ev.load_sigma(OUT / "sigma_event.json")
    hyps = ev.build_hypotheses()
    hyp = next(h for h in hyps if h.id == a.hypothesis)
    obs_hist = obs_from_twin_log(run / "twin_log.parquet")
    dets = sorted(obs_hist)
    anchor = anchor_from(obs_hist, a.t_on)
    spec = {"kind": "incident", "edge": hyp.params["edge"],
            "lanes_closed": list(hyp.params["lanes_closed"]), "n_lanes": hyp.params["n_lanes"],
            "speed_factor": hyp.params["speed_factor"]}

    def job(tag, apply_spec):
        return {"tag": tag, "t_on": a.t_on, "t_end": a.t_end, "detectors": dets,
                "apply": apply_spec, "lift": None, "t_lift": None}

    # check 2: the same hypothesis twice, independent processes
    res1, wall1 = score_replays(state, meta, [job("run1", spec)], workers=1, seed=2)
    res2, wall2 = score_replays(state, meta, [job("run2", spec)], workers=1, seed=2)
    logls, digests, tables, n_os = [], [], [], []
    for r in (res1[0], res2[0]):
        times = sorted(r["intervals"][dets[0]].keys())
        # one hypothesis alone has no demand family, so ``ev.evaluate`` (which needs one for the
        # posterior gap and the EVR) does not apply: its logL is accumulated directly instead.
        ll, n_o = ev.logl_of_one(hyp, dets, times, obs_hist, {hyp.id: r["intervals"]}, sigma,
                                 a.t_on, a.t_end, anchor=anchor)
        logls.append(ll)
        n_os.append(n_o)
        digests.append(r["veh_digest"])
        tables.append(r["intervals"])
    identical = (logls[0] == logls[1] and digests[0] == digests[1] and tables[0] == tables[1])

    # check 4: incident vs no-event replay, downstream flow on AID02111
    res0, wall0 = score_replays(state, meta, [job("noevent", {"kind": "none"})], workers=1, seed=2)
    inc, noev = res1[0], res0[0]

    def flow(res, det):
        vals = [row["q"] for row in res["intervals"].get(det, {}).values() if row["q"] is not None]
        return (sum(vals) / len(vals)) if vals else None, len(vals)

    inc_q, n_inc = flow(inc, DOWNSTREAM)
    noev_q, n_noev = flow(noev, DOWNSTREAM)
    lanes = [f"{hyp.params['edge']}_{i}" for i in hyp.params["lanes_closed"]]
    out = {
        "run": a.run, "snapshot": f"twin_state_{int(a.snapshot)}", "t_on": a.t_on, "t_end": a.t_end,
        "hypothesis": hyp.id, "params": dict(hyp.params),
        "check2_deterministic_replay": {
            "logL_run1": logls[0], "logL_run2": logls[1], "logL_identical": logls[0] == logls[1],
            "n_O": n_os[0], "n_O_run2": n_os[1],
            "digest_run1": digests[0], "digest_run2": digests[1], "digest_identical": digests[0] == digests[1],
            "interval_tables_identical": tables[0] == tables[1], "identical": bool(identical),
            "wall_s": [wall1, wall2], "n_vehicles": inc["n_vehicles"]},
        "check4_capacity_restriction": {
            "lanes_closed": lanes, "restriction_present": inc["restriction_present"],
            "downstream_detector": DOWNSTREAM,
            "incident_mean_q": inc_q, "noevent_mean_q": noev_q,
            "incident_intervals": n_inc, "noevent_intervals": n_noev,
            "flow_drops": bool(inc_q is not None and noev_q is not None and inc_q < noev_q),
            "drop_pct": None if not noev_q else round(100.0 * (inc_q - noev_q) / noev_q, 2),
            "n_vehicles_incident": inc["n_vehicles"], "n_vehicles_noevent": noev["n_vehicles"],
            "wall_s": [wall1, wall0]},
    }
    (OUT / "check_replay.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0 if (out["check2_deterministic_replay"]["identical"]
                 and out["check4_capacity_restriction"]["flow_drops"]
                 and out["check4_capacity_restriction"]["restriction_present"]) else 1


if __name__ == "__main__":
    sys.exit(main())
