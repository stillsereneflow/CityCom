"""Claude's independent recomputation of the audit estimands from raw rows (no project code imported).

usage: python indep_audit.py <raw.parquet> [twin_filter_col=value]
"""
import sys, math
import numpy as np, pandas as pd

raw = pd.read_parquet(sys.argv[1])
flt = sys.argv[2] if len(sys.argv) > 2 else None
A = ["A0", "A1", "A2", "A3", "A4"]
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}


def means(df, reps):
    x = df[df.replication.isin(reps)]
    p = x.pivot_table(index="replication", columns="action", values="J", aggfunc="count")
    assert (p.reindex(columns=A).fillna(0) == 1).all().all(), "grid not unique/complete"
    return x.groupby("action").J.mean().reindex(A)


def rank(v):
    return pd.Series(v).rank().values


def spearman(a, b):
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def kendall(a, b):
    a, b = np.asarray(a), np.asarray(b); n = len(a); s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
    return s / (n * (n - 1) / 2)


def ci(v):
    v = np.asarray(v, float); n = len(v); m = v.mean()
    if n < 2:
        return m, None, None
    h = T95[n - 1] * v.std(ddof=1) / math.sqrt(n)
    return m, m - h, m + h


twin = raw[raw.world == "twin"]
if flt:
    k, v = flt.split("=")
    twin = twin[twin[k].astype(str) == v]
rows = []
for s in sorted(raw.seed.unique()):
    T = twin[twin.seed == s]; P = raw[(raw.world == "proxy") & (raw.seed == s)]
    C = raw[(raw.world == "calibration") & (raw.seed == s)]
    if T.empty or P.empty:
        continue
    for d in (T, P, C):
        if len(d):
            assert (d.status == "ok").all() and np.isfinite(d.J).all()
    t1, t2 = means(T, [1, 2, 3]), means(T, [4, 5, 6])
    p1, p2 = means(P, [1, 2, 3]), means(P, [4, 5, 6])
    a = t1.idxmin(); o = p1.idxmin()
    gT = t2["A0"] - t2[a]; gP = p2["A0"] - p2[a]
    reg = p2[a] - p2[o]; den = p2["A0"] - p2[o]
    r = dict(seed=s, a_star=a, oracle=o, top1=int(a == o), G_T=gT, G_P=gP, BEE=gT - gP,
             BEE_rel=(gT - gP) / p2["A0"], regret=reg, regret_rel=(reg / den if den >= 0.5 else np.nan),
             spearman=spearman(t2.values, p2.values), kendall=kendall(t2.values, p2.values),
             G_T_A3=t2["A0"] - t2["A3"], G_P_A3=p2["A0"] - p2["A3"])
    if len(C):
        c1, c2 = means(C, [7, 8, 9]), means(C, [10, 11, 12])
        ac = c1.idxmin()
        r["floor_signed"] = (c2["A0"] - c2[ac]) - (p2["A0"] - p2[ac])
    rows.append(r)
R = pd.DataFrame(rows).set_index("seed")
pd.set_option("display.width", 250)
print(R.round(3).to_string())
print("N", len(R), "a* counts", R.a_star.value_counts().to_dict(), "oracle", R.oracle.value_counts().to_dict(),
      "top1", R.top1.sum())
for c in ["BEE", "regret", "spearman", "kendall", "BEE_rel", "regret_rel", "floor_signed", "G_T_A3", "G_P_A3"]:
    if c in R:
        v = R[c].dropna()
        m, lo, hi = ci(v)
        print(f"{c:13s} mean {m:+.3f}  CI [{lo if lo is None else round(lo,3)}, {hi if hi is None else round(hi,3)}]  n={len(v)}")
if "floor_signed" in R:
    m, lo, hi = ci(R.floor_signed.abs()); print(f"floor_abs     mean {m:.3f} CI [{lo:.3f}, {hi:.3f}]")
m, lo, hi = ci(R.BEE.abs()); print(f"BEE_abs       mean {m:.3f} CI [{lo:.3f}, {hi:.3f}]")
