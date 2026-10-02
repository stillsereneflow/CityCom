"""Branching evidence + runtime benchmark.

1. Conformance: A0 twice from the same snapshot -> KPIs must be identical (CRN within the engine).
2. 5 candidate actions (A0..A4) x horizons 5/10/15 min, parallel; also sequential for timing.
The capacity hypothesis (2 of 3 lanes closed on KTB-N 312049503) is SUPPLIED MANUALLY here: event-mode
inference is not implemented yet (D9–D10). It is not read from the Proxy.
"""
import json
import time

from citypulse.branching.engine import run_branches
from citypulse.config import RESULTS

# Position = midpoint of the observed detector segment AID02109 (455.7 m) .. AID02111 (1054.9 m), i.e. where an
# inference from observed detectors could localise it; NOT the Proxy's true position (900 m).
HYP = {"edge": "312049503", "lanes_closed": [0, 1], "mode": "disallow", "source": "manual (inference not implemented)"}
HYP_BLOCK = {"edge": "312049503", "lanes_closed": [0, 1], "mode": "blocker", "pos": 755.0, "duration": 3600,
             "source": "manual (inference not implemented)"}
ACTIONS = ["A0", "A1", "A2", "A3", "A4"]


def main():
    snap = RESULTS / "incident" / "twin"
    state, meta = snap / "twin_state_1500.xml.gz", snap / "twin_state_1500.json"
    out = {"hypothesis": HYP}
    r1, w1 = run_branches(state, meta, ["A0", "A0"], hypothesis=HYP, workers=2)
    out["conformance"] = {"kpis_run1": r1[0]["kpis"], "kpis_run2": r1[1]["kpis"],
                          "identical": r1[0]["kpis"] == r1[1]["kpis"]}
    res_par, wall_par = run_branches(state, meta, ACTIONS, hypothesis=HYP)
    res_seq, wall_seq = run_branches(state, meta, ACTIONS, hypothesis=HYP, workers=1)
    out["parallel"] = {"wall_s": wall_par, "branches": res_par}
    out["sequential"] = {"wall_s": wall_seq, "per_branch_wall_s": [r["wall_s"] for r in res_seq],
                         "setup_s": [r["setup_s"] for r in res_seq]}
    out["parallel_equals_sequential"] = [a["kpis"] == b["kpis"] for a, b in zip(res_par, res_seq)]
    # replications: different SUMO seeds (same snapshot), all 5 actions -> spread of each KPI
    reps = {}
    for seed in (3, 4, 5):
        rr, _ = run_branches(state, meta, ACTIONS, hypothesis=HYP, seed=seed)
        reps[seed] = rr
    out["replications"] = {str(k): v for k, v in reps.items()}
    # point-blockage hypothesis representation, 4 seeds
    blk = {}
    for seed in (2, 3, 4, 5):
        rr, _ = run_branches(state, meta, ACTIONS, hypothesis=HYP_BLOCK, seed=seed)
        blk[seed] = rr
    out["blocker"] = {str(k): v for k, v in blk.items()}
    # no-hypothesis variant (what a Twin that has NOT inferred the incident would predict)
    res_nh, wall_nh = run_branches(state, meta, ACTIONS, hypothesis=None)
    out["no_hypothesis"] = {"wall_s": wall_nh, "branches": res_nh}
    out["hypotheses"] = {"disallow": HYP, "blocker": HYP_BLOCK}
    json.dump(out, open(RESULTS / "branch_benchmark.json", "w"), indent=1)
    print("conformance identical:", out["conformance"]["identical"])
    print(f"parallel wall {wall_par:.1f}s, sequential wall {wall_seq:.1f}s, par==seq {out['parallel_equals_sequential']}")
    for r in res_par:
        k = r["kpis"]
        print(r["action"], {h: round(k[h]["delay_vh"], 1) for h in k}, "arrived15", k[900]["arrived"],
              "halt", round(k[900]["halt_inc"], 1), "diverted", r["n_diverted"], "pending1", r["pending_after_first_step"],
              "/", r["n_pending_meta"], f"wall {r['wall_s']:.1f}s")
    import statistics as st
    for i, a in enumerate(ACTIONS):
        for key in ("delay_vh", "corridor_delay_vh", "halt_inc"):
            dis = [res_par[i]["kpis"][900][key]] + [reps[s][i]["kpis"][900][key] for s in reps]
            bl = [blk[s][i]["kpis"][900][key] for s in blk]
            print(a, key, "disallow mean/sd", round(st.mean(dis), 1), round(st.stdev(dis), 1),
                  "| blocker mean/sd", round(st.mean(bl), 1), round(st.stdev(bl), 1),
                  "| no-hyp", round(res_nh[i]["kpis"][900][key], 1))


if __name__ == "__main__":
    main()
