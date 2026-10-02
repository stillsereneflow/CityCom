"""Generate D1–D4 evidence figures from results/ (no simulation here)."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sumolib

from citypulse.config import FIGS, NET_FILE, RESULTS, SCEN
from citypulse.proxy.truth_config import EVAL_PAIR, PROXY_ONLY
from citypulse.scenario import CONTROL

DPI = 130


def fig_network():
    net = sumolib.net.readNet(str(NET_FILE))
    m = json.load(open(SCEN / "detector_map.json", encoding="utf-8"))["mapped"]
    observed = set(json.load(open(RESULTS / "incident" / "proxy" / "proxy_stats.json"))["observed_detectors"])
    fig, ax = plt.subplots(figsize=(8, 8))
    for e in net.getEdges():
        xs, ys = zip(*e.getShape())
        name = e.getName() or ""
        if "Kwun Tong Bypass" in name:
            c, w = "tab:blue", 2.0
        elif "Kwun Tong Road" in name:
            c, w = "tab:green", 2.0
        else:
            c, w = "0.75", 0.8
        ax.plot(xs, ys, color=c, lw=w, zorder=1)
    b = set(CONTROL["corridor_b"])
    for e in net.getEdges():
        if e.getID() in b:
            xs, ys = zip(*e.getShape())
            ax.plot(xs, ys, color="tab:orange", lw=4, alpha=0.35, zorder=0)
    for d in m:
        x, y = net.convertLonLat2XY(d["lon"], d["lat"])
        ax.scatter(x, y, s=28, marker="o", zorder=3,
                   facecolor="black" if d["id"] in observed else "white", edgecolor="black")
    inc = net.getEdge(PROXY_ONLY["incident"]["edge"])
    ix, iy = sumolib.geomhelper.positionAtShapeOffset(inc.getShape(), PROXY_ONLY["incident"]["pos"])
    ax.scatter(ix, iy, s=220, marker="X", color="red", zorder=4)
    vx, vy = net.getEdge(CONTROL["vms_edge"]).getShape()[0]
    ax.scatter(vx, vy, s=160, marker="s", color="tab:purple", zorder=4)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color="tab:blue", lw=2, label="Kwun Tong Bypass"),
         Line2D([], [], color="tab:green", lw=2, label="Kwun Tong Road"),
         Line2D([], [], color="tab:orange", lw=4, alpha=0.4, label="VMS diversion corridor B"),
         Line2D([], [], marker="o", ls="", color="black", label="TD detector, observed by Twin"),
         Line2D([], [], marker="o", ls="", mfc="white", mec="black", label="TD detector, hidden from Twin"),
         Line2D([], [], marker="X", ls="", color="red", ms=12, label="Proxy-only incident (unknown to Twin)"),
         Line2D([], [], marker="s", ls="", color="tab:purple", ms=10, label="VMS")]
    ax.legend(handles=h, loc="lower left", fontsize=8)
    ax.set_aspect("equal")
    ax.set_title(f"Kwun Tong corridor SUMO network ({len(net.getEdges())} edges, left-hand), "
                 f"{len(m)} TD detectors mapped")
    ax.set_xticks([]), ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(FIGS / "network.png", dpi=DPI)
    plt.close(fig)


def load(run):
    p = pd.read_parquet(RESULTS / run / "proxy" / "proxy_truth.parquet")
    t = pd.read_parquet(RESULTS / run / "twin" / "twin_log.parquet")
    return p, t


def fig_grounding_and_mismatch():
    info = json.load(open(SCEN / "demand_info.json"))
    p, t = load("baseline")
    m = json.load(open(SCEN / "detector_map.json", encoding="utf-8"))["mapped"]
    edge_of = {d["id"]: d["edge"] for d in m}
    win = (p.t >= 600)
    pm = p[win].groupby("detector")["q"].mean() * 120  # veh/h (30 s intervals)
    tw = t[t.t >= 600].groupby("detector")["twin_q"].mean() * 120
    hk = {d: info["edge_counts_vph"].get(edge_of[d]) for d in pm.index if edge_of.get(d) in info["edge_counts_vph"]}
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    xs = [hk[d] for d in hk]
    axs[0].scatter(xs, [pm[d] for d in hk], s=14, label="Proxy")
    axs[0].scatter([hk[d] for d in hk if d in tw.index], [tw[d] for d in hk if d in tw.index], s=14, marker="^",
                   label="Twin (observed detectors only)")
    lim = max(xs + list(pm.values)) * 1.05
    axs[0].plot([0, lim], [0, lim], "k--", lw=0.8)
    axs[0].set_xlabel(f"HK TD flow x{info['scale']} (veh/h, {info['day']} {info['window'][0]}-{info['window'][1]}h)")
    axs[0].set_ylabel("simulated flow (veh/h, t>=600 s)")
    axs[0].set_title("Grounding: per-detector flow vs HK target", fontsize=10)
    axs[0].legend(fontsize=8)
    # mismatch time series at two observed detectors
    obs_dets = [d for d in ["AID02109", "AID07111"] if d in set(t.detector)]
    for k, d in enumerate(obs_dets[:1]):
        x = t[t.detector == d].sort_values("t")
        pr = p[p.detector == d].sort_values("t")
        axs[1].plot(pr.t, pr.q * 120, label=f"Proxy truth {d}", lw=1)
        axs[1].plot(x.t, x.obs_q * 120, ".", ms=3, label="observation sent to Twin (noisy, lossy)")
        axs[1].plot(x.t, x.twin_q * 120, label="Twin own detector", lw=1)
        axs[1].set_ylabel("flow (veh/h)")
        axs[1].set_xlabel("sim time (s)")
        axs[1].set_title(f"No-incident run, {d}\nProxy vs Twin, no assimilation", fontsize=10)
        axs[1].legend(fontsize=7)
    tt = t[(t.t >= 600) & t.obs_valid]
    g = tt.groupby("detector").agg(obs_v=("obs_v", "mean"), twin_v=("twin_v", "mean"))
    axs[2].scatter(g.obs_v, g.twin_v, s=14)
    axs[2].plot([0, 100], [0, 100], "k--", lw=0.8)
    axs[2].set_xlabel("observed mean speed (km/h)")
    axs[2].set_ylabel("Twin mean speed (km/h)")
    mae_q = (tt.obs_q - tt.twin_q).abs().mean() * 120
    mae_v = (tt.obs_v - tt.twin_v).abs().mean()
    axs[2].set_title(f"Per-detector mean speed, {tt.detector.nunique()} observed detectors\n"
                     f"30 s flow MAE {mae_q:.0f} veh/h, speed MAE {mae_v:.1f} km/h", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGS / "proxy_vs_twin_mismatch.png", dpi=DPI)
    plt.close(fig)
    return {"flow_MAE_vph_obs_vs_twin": float(mae_q), "speed_MAE_kmh_obs_vs_twin": float(mae_v),
            "n_obs_rows": int(len(tt))}


def bottleneck_index(t, u, d, t_cal=(300, 1200)):
    """Report2 §G.2 divergence statistic on observed data only (residual = observation - Twin)."""
    a = t[t.detector == u].set_index("t")
    b = t[t.detector == d].set_index("t")
    out = {}
    for name, x in (("U", a), ("D", b)):
        for k in ("o", "v"):
            r = x[f"obs_{k}"] - x[f"twin_{k}"]
            cal = r.loc[t_cal[0]:t_cal[1]].dropna()
            mad = 1.4826 * np.median(np.abs(cal - cal.median())) or 1.0
            out[f"r_{name}_{k}"] = (r - cal.median()) / mad
    B = 0.5 * (out["r_U_o"] - out["r_D_o"]) + 0.5 * (out["r_D_v"].fillna(0) - out["r_U_v"].fillna(0))
    return B, out


def fig_incident():
    pi, ti = load("incident")
    pb, tb = load("baseline")
    u2, u, d = EVAL_PAIR["U2"], EVAL_PAIR["U"], EVAL_PAIR["D"]
    inc = PROXY_ONLY["incident"]
    fig, axs = plt.subplots(2, 3, figsize=(15, 7.5), sharex=True)
    for j, (k, lab) in enumerate((("o", "occupancy (%)"), ("v", "speed (km/h)"), ("q", "flow (veh/30 s)"))):
        ax = axs[0, j]
        for det, c in ((u2, "tab:orange"), (u, "tab:red"), (d, "tab:blue")):
            x = pi[pi.detector == det].sort_values("t")
            y = pb[pb.detector == det].sort_values("t")
            ax.plot(x.t, x[k], color=c, lw=1.2, label=f"{det} incident")
            ax.plot(y.t, y[k], color=c, lw=0.8, ls=":", label=f"{det} no incident")
        ax.axvspan(inc["t_start"], inc["t_start"] + inc["duration"], color="red", alpha=0.08)
        ax.set_ylabel(lab)
        ax.set_title(f"Proxy truth (hidden): {lab}")
    axs[0, 0].legend(fontsize=7)
    # what the Twin actually receives
    for j, (k, lab) in enumerate((("o", "occupancy (%)"), ("v", "speed (km/h)"))):
        ax = axs[1, j]
        for det, c in ((u2, "tab:orange"), (d, "tab:blue")):
            x = ti[ti.detector == det].sort_values("t")
            ax.plot(x.t, x[f"obs_{k}"], ".", color=c, ms=4, label=f"{det} observed")
            ax.plot(x.t, x[f"twin_{k}"], color=c, lw=0.8, ls="--", label=f"{det} Twin")
        ax.axvspan(inc["t_start"], inc["t_start"] + inc["duration"], color="red", alpha=0.08)
        ax.set_ylabel(lab)
        ax.set_title(f"Twin side (sparse, noisy; {u} not observed)")
        ax.set_xlabel("sim time (s)")
    axs[1, 0].legend(fontsize=7)
    Bi, _ = bottleneck_index(ti, u2, d)
    Bb, _ = bottleneck_index(tb, u2, d)
    ax = axs[1, 2]
    ax.plot(Bi.index, Bi.values, label="incident run")
    ax.plot(Bb.index, Bb.values, label="no-incident run", alpha=0.7)
    ax.axhline(3, color="k", ls="--", lw=0.8)
    ax.axvspan(inc["t_start"], inc["t_start"] + inc["duration"], color="red", alpha=0.08)
    ax.set_title(f"Bottleneck index B({u2}, {d})\nresiduals = observation - Twin", fontsize=10)
    ax.set_xlabel("sim time (s)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "incident_signature.png", dpi=DPI)
    plt.close(fig)

    def first_cross(B, thr=3.0, k=2):
        s = (B > thr).astype(int)
        run = s.groupby((s != s.shift()).cumsum()).cumsum() * s
        hit = run[run >= k]
        return None if hit.empty else float(hit.index[0])

    ex = pi[pi.detector == u].set_index("t")
    return {"B_first_cross_incident_s": first_cross(Bi), "B_first_cross_baseline_s": first_cross(Bb),
            "B_max_baseline": float(Bb.max()), "B_max_incident": float(Bi.max()),
            "proxy_U_occ_pre_mean": float(ex.loc[900:1200, "o"].mean()),
            "proxy_U_occ_incident_mean": float(ex.loc[1500:2100, "o"].mean()),
            "proxy_U_speed_pre_mean": float(ex.loc[900:1200, "v"].mean()),
            "proxy_U_speed_incident_mean": float(ex.loc[1500:2100, "v"].mean()),
            "proxy_D_flow_pre_mean": float(pi[pi.detector == d].set_index("t").loc[900:1200, "q"].mean()),
            "proxy_D_flow_incident_mean": float(pi[pi.detector == d].set_index("t").loc[1500:2100, "q"].mean()),
            "incident": inc}


def fig_branching():
    bb = json.load(open(RESULTS / "branch_benchmark.json"))
    acts = [r["action"] for r in bb["parallel"]["branches"]]
    dis = [bb["parallel"]["branches"]] + list(bb["replications"].values())
    blk = list(bb["blocker"].values())
    nh = bb["no_hypothesis"]["branches"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
    x = np.arange(len(acts))
    for j, h in enumerate(["300", "600", "900"]):
        vals = np.array([[r[i]["kpis"][h]["corridor_delay_vh"] for i in range(len(acts))] for r in blk])
        axs[0].bar(x + (j - 1) * 0.25, vals.mean(0), 0.25, yerr=vals.std(0, ddof=1), capsize=3,
                   label=f"{int(h) // 60} min")
    axs[0].set_xticks(x, acts)
    axs[0].set_ylabel("corridor delay since snapshot (veh*h)")
    axs[0].set_title(f"Same Twin snapshot (t=1500 s) -> 5 actions x 5/10/15 min\n"
                     f"point-blockage hypothesis, mean +- sd over {len(blk)} seeds", fontsize=10)
    axs[0].legend(fontsize=8)
    for k, (key, lab) in enumerate((("corridor_delay_vh", "15-min corridor delay (veh*h)"),
                                    ("halt_inc", "mean halting vehicles on KTB-N edge"))):
        ax = axs[k + 1]
        for off, reps, name in ((-0.27, dis, "whole-edge lane closure"), (0.0, blk, "point blockage"),
                                (0.27, [nh], "no hypothesis (Twin unaware)")):
            v = np.array([[r[i]["kpis"]["900"][key] for i in range(len(acts))] for r in reps])
            ax.bar(x + off, v.mean(0), 0.27, yerr=v.std(0, ddof=1) if len(reps) > 1 else None, capsize=3,
                   label=name)
        ax.set_xticks(x, acts)
        ax.set_ylabel(lab)
        ax.set_title(f"{lab}: by hypothesis representation", fontsize=10)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "branching_comparison.png", dpi=DPI)
    plt.close(fig)
    seq = bb["sequential"]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(["5 branches\nparallel", "5 branches\nsequential", "mean single\nbranch"],
           [bb["parallel"]["wall_s"], seq["wall_s"], float(np.mean(seq["per_branch_wall_s"]))])
    ax.set_ylabel("wall-clock seconds (15-min horizon)")
    ax.set_title("Rollout runtime, 20-core laptop, libsumo")
    fig.tight_layout()
    fig.savefig(FIGS / "rollout_runtime.png", dpi=DPI)
    plt.close(fig)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    fig_network()
    s1 = fig_grounding_and_mismatch()
    s2 = fig_incident()
    fig_branching()
    json.dump({"mismatch": s1, "incident": s2}, open(RESULTS / "figure_stats.json", "w"), indent=1)
    print(json.dumps({"mismatch": s1, "incident": s2}, indent=1))


if __name__ == "__main__":
    main()
