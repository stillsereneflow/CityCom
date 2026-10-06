"""Compare Claude's independent recompute (indep_audit.py logic, re-run here) with the analyzer's metrics.json."""
import json, subprocess, sys, math
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
raw = pd.read_parquet(HERE.parent / "raw.parquet")
m = json.load(open(HERE.parent / "metrics.json"))
A = ["A0", "A1", "A2", "A3", "A4"]


def mean_by(df, reps):
    return df[df.replication.isin(reps)].groupby("action").J.mean().reindex(A)


def spear(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


rows, worst = [], 0.0
for block, belief in (("primary", "B"), ("secondary", "D300")):
    for ps in m[block]["per_seed"]:
        s = ps["seed"]
        T = raw[(raw.world == "twin") & (raw.belief == belief) & (raw.seed == s)]
        P = raw[(raw.world == "proxy") & (raw.seed == s)]
        C = raw[(raw.world == "calibration") & (raw.seed == s)]
        t1, t2, p1, p2 = mean_by(T, [1, 2, 3]), mean_by(T, [4, 5, 6]), mean_by(P, [1, 2, 3]), mean_by(P, [4, 5, 6])
        a, o = t1.idxmin(), p1.idxmin()
        c1, c2 = mean_by(C, [7, 8, 9]), mean_by(C, [10, 11, 12]); ac = c1.idxmin()
        mine = {"G_T_hat": t2.A0 - t2[a], "G_P": p2.A0 - p2[a], "BEE_signed": (t2.A0 - t2[a]) - (p2.A0 - p2[a]),
                "Regret": p2[a] - p2[o], "spearman_rho": spear(t2.values, p2.values),
                "BEE_floor_signed": (c2.A0 - c2[ac]) - (p2.A0 - p2[ac]),
                "G_T_A3": t2.A0 - t2.A3, "G_P_A3": p2.A0 - p2.A3}
        for k, v in mine.items():
            d = abs(v - ps[k]); worst = max(worst, d)
            rows.append(dict(belief=belief, seed=s, metric=k, claude=v, analyzer=ps[k], absdiff=d))
        rows.append(dict(belief=belief, seed=s, metric="a_star", claude=a, analyzer=ps["a_star"],
                         absdiff=0.0 if a == ps["a_star"] else 1.0))
        rows.append(dict(belief=belief, seed=s, metric="oracle", claude=o, analyzer=ps["oracle"],
                         absdiff=0.0 if o == ps["oracle"] else 1.0))
df = pd.DataFrame(rows)
df.to_csv(HERE / "compare_per_seed.csv", index=False)
bad = df[df.absdiff > 1e-9]
print(f"compared {len(df)} per-seed values; max abs diff {df.absdiff.max():.3e}; mismatches {len(bad)}")
print(bad.to_string() if len(bad) else "ALL MATCH")
