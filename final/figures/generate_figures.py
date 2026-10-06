import sys
sys.path.insert(0, "D:/CityCom-astra")
import argparse
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path

# Color constants (applying exact categorical color scheme)
CLR_TWIN_B = "#2a78d6"       # Twin belief B
CLR_TWIN_D = "#eb6834"       # Twin D300 (truth-assisted control)
CLR_PROXY = "#1baf7a"        # Proxy (realised)
CLR_FLOOR = "#4a3aa7"        # calibration floor
CLR_SURFACE = "#fcfcfb"      # background surface
CLR_TEXT_DARK = "#0b0b0b"    # titles
CLR_TEXT_MUTED = "#52514e"   # labels, ticks
CLR_GRID = "#e6e5e0"         # recessive gridlines (0.6 px)

def setup_style():
    plt.rcParams.update({
        "figure.facecolor": CLR_SURFACE,
        "axes.facecolor": CLR_SURFACE,
        "savefig.facecolor": CLR_SURFACE,
        "text.color": CLR_TEXT_DARK,
        "axes.labelcolor": CLR_TEXT_MUTED,
        "xtick.color": CLR_TEXT_MUTED,
        "ytick.color": CLR_TEXT_MUTED,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
        "axes.edgecolor": CLR_GRID,
        "axes.linewidth": 1.0,
        "grid.color": CLR_GRID,
        "grid.linewidth": 0.6,
    })

def t_crit_95(n):
    from citypulse.experiments.decision_audit import t_critical_95
    return t_critical_95(n - 1)

def run(dpi=72, out_dir="final/figures"):
    setup_style()
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    csv_rows = []

    # =========================================================================
    # 1. Figure 1: fig1_bee_dev_vs_frozen.png
    # =========================================================================
    print("Generating Figure 1...")
    raw_dev = pd.read_parquet("results/audit/raw.parquet")
    raw_frozen = pd.read_parquet("results/frozen_audit/raw.parquet")

    # Dev audit calculations
    dev_seeds = sorted(raw_dev["seed"].unique())
    dev_bee, dev_floor = [], []
    for s in dev_seeds:
        tw = raw_dev[(raw_dev["world"] == "twin") & (raw_dev["seed"] == s) & (raw_dev["status"] == "ok")]
        px = raw_dev[(raw_dev["world"] == "proxy") & (raw_dev["seed"] == s) & (raw_dev["status"] == "ok")]
        cal = raw_dev[(raw_dev["world"] == "calibration") & (raw_dev["seed"] == s) & (raw_dev["status"] == "ok")]

        r1 = tw[tw["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
        r2 = tw[tw["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        a_star = r1.idxmin()
        g_t = r2["A0"] - r2[a_star]

        m2 = px[px["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        g_p = m2["A0"] - m2[a_star]
        bee = g_t - g_p
        dev_bee.append(bee)

        cal_sel = cal[cal["replication"].isin([7, 8, 9])].groupby("action")["J"].mean()
        cal_eval = cal[cal["replication"].isin([10, 11, 12])].groupby("action")["J"].mean()
        a_floor = cal_sel.idxmin()
        g_cal = cal_eval["A0"] - cal_eval[a_floor]
        g_p_floor = m2["A0"] - m2[a_floor]
        floor = abs(g_cal - g_p_floor)
        dev_floor.append(floor)

        csv_rows.append({"figure": "fig1", "series": "BEE (belief B)", "seed/group": f"Dev seed {s}", "value": bee})
        csv_rows.append({"figure": "fig1", "series": "|floor_signed|", "seed/group": f"Dev seed {s}", "value": floor})

    # Frozen audit calculations
    froz_seeds = sorted(raw_frozen["seed"].unique())
    froz_bee, froz_floor = [], []
    for s in froz_seeds:
        tw = raw_frozen[(raw_frozen["world"] == "twin") & (raw_frozen["belief"] == "B") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]
        px = raw_frozen[(raw_frozen["world"] == "proxy") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]
        cal = raw_frozen[(raw_frozen["world"] == "calibration") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]

        r1 = tw[tw["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
        r2 = tw[tw["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        a_star = r1.idxmin()
        g_t = r2["A0"] - r2[a_star]

        m2 = px[px["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        g_p = m2["A0"] - m2[a_star]
        bee = g_t - g_p
        froz_bee.append(bee)

        cal_sel = cal[cal["replication"].isin([7, 8, 9])].groupby("action")["J"].mean()
        cal_eval = cal[cal["replication"].isin([10, 11, 12])].groupby("action")["J"].mean()
        a_floor = cal_sel.idxmin()
        g_cal = cal_eval["A0"] - cal_eval[a_floor]
        g_p_floor = m2["A0"] - m2[a_floor]
        floor = abs(g_cal - g_p_floor)
        froz_floor.append(floor)

        csv_rows.append({"figure": "fig1", "series": "BEE (belief B)", "seed/group": f"Frozen seed {s}", "value": bee})
        csv_rows.append({"figure": "fig1", "series": "|floor_signed|", "seed/group": f"Frozen seed {s}", "value": floor})

    # Statistics
    dev_m, dev_se = np.mean(dev_bee), np.std(dev_bee, ddof=1) / np.sqrt(len(dev_bee))
    dev_ci = t_crit_95(len(dev_bee)) * dev_se
    froz_m, froz_se = np.mean(froz_bee), np.std(froz_bee, ddof=1) / np.sqrt(len(froz_bee))
    froz_ci = t_crit_95(len(froz_bee)) * froz_se

    dev_fl_m = np.mean(dev_floor)
    froz_fl_m = np.mean(froz_floor)

    csv_rows.append({"figure": "fig1", "series": "Mean BEE", "seed/group": "Development audit", "value": dev_m})
    csv_rows.append({"figure": "fig1", "series": "95% CI half-width", "seed/group": "Development audit", "value": dev_ci})
    csv_rows.append({"figure": "fig1", "series": "Mean BEE", "seed/group": "Frozen test audit", "value": froz_m})
    csv_rows.append({"figure": "fig1", "series": "95% CI half-width", "seed/group": "Frozen test audit", "value": froz_ci})

    fig, ax = plt.subplots(figsize=(7.6, 5.3), dpi=dpi)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="-", alpha=0.7)
    ax.xaxis.grid(False)

    ax.axhline(0, color=CLR_TEXT_MUTED, linestyle="--", linewidth=1.0, alpha=0.5, zorder=1)

    # Coordinated positions
    x_dev_bar = 0.78
    x_dev_dots = 0.94
    x_dev_fl = 1.25

    x_froz_bar = 2.08
    x_froz_dots = 2.24
    x_froz_fl = 2.55

    # Seed dots
    rng = np.random.default_rng(42)
    dev_j = rng.uniform(-0.025, 0.025, size=len(dev_bee))
    froz_j = rng.uniform(-0.025, 0.025, size=len(froz_bee))

    ax.scatter(x_dev_dots + dev_j, dev_bee, color=CLR_TWIN_B, s=65, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Twin belief B BEE (per seed)")
    ax.scatter(x_dev_fl + dev_j, dev_floor, color=CLR_FLOOR, s=65, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Calibration discrepancy (empirical, not a bound)")

    ax.scatter(x_froz_dots + froz_j, froz_bee, color=CLR_TWIN_B, s=65, edgecolors=CLR_SURFACE, linewidths=2, zorder=4)
    ax.scatter(x_froz_fl + froz_j, froz_floor, color=CLR_FLOOR, s=65, edgecolors=CLR_SURFACE, linewidths=2, zorder=4)

    # Thick bars for Mean and 95% t-CI (width=4.0)
    ax.errorbar(x_dev_bar, dev_m, yerr=dev_ci, fmt="o", color=CLR_TWIN_B, ecolor=CLR_TWIN_B,
                elinewidth=4.0, capsize=6, capthick=2.0, markersize=8, markeredgecolor=CLR_SURFACE,
                markeredgewidth=2, zorder=5)
    ax.errorbar(x_froz_bar, froz_m, yerr=froz_ci, fmt="o", color=CLR_TWIN_B, ecolor=CLR_TWIN_B,
                elinewidth=4.0, capsize=6, capthick=2.0, markersize=8, markeredgecolor=CLR_SURFACE,
                markeredgewidth=2, zorder=5)

    # Calibration floor mean ticks
    ax.plot([x_dev_fl - 0.06, x_dev_fl + 0.06], [dev_fl_m, dev_fl_m], color=CLR_FLOOR, linewidth=2.5, zorder=5)
    ax.plot([x_froz_fl - 0.06, x_froz_fl + 0.06], [froz_fl_m, froz_fl_m], color=CLR_FLOOR, linewidth=2.5, zorder=5)

    # Direct labels on key values
    ax.text(x_dev_bar - 0.04, dev_m + dev_ci + 0.35, f"Mean: {dev_m:.2f} veh·h\n[95% CI: {dev_m-dev_ci:.2f}, {dev_m+dev_ci:.2f}]",
            ha="center", va="bottom", fontsize=8.2, color=CLR_TEXT_DARK, fontweight="semibold")
    ax.text(x_froz_bar - 0.06, froz_m + froz_ci + 0.08, f"Mean: {froz_m:.2f} veh·h\n[95% CI: {froz_m-froz_ci:.2f}, {froz_m+froz_ci:.2f}]",
            ha="center", va="bottom", fontsize=8.2, color=CLR_TEXT_DARK, fontweight="semibold")
    ax.text(x_dev_fl + 0.08, dev_fl_m, f"Calib. discrepancy: {dev_fl_m:.2f}",
            ha="left", va="center", fontsize=8.0, color=CLR_FLOOR, fontweight="semibold")
    ax.text(x_froz_fl + 0.08, froz_fl_m, f"Calib. discrepancy: {froz_fl_m:.2f}",
            ha="left", va="center", fontsize=8.0, color=CLR_FLOOR, fontweight="semibold")

    ax.set_xticks([1.02, 2.32])
    ax.set_xticklabels(["Development audit\n(seeds 4201–4208)", "Frozen test audit\n(seeds 4501–4508)"],
                       fontsize=10.0, fontweight="semibold")
    ax.set_ylabel("Benefit Estimation Error BEE (veh·h)", fontsize=10.5)
    ax.set_ylim(-0.6, 3.8)
    ax.set_xlim(0.35, 3.0)

    ax.set_title("Twin Overestimates Decision Benefit Across Development and Frozen Audits",
                 fontsize=11.5, fontweight="bold", pad=20, loc="left", color=CLR_TEXT_DARK)
    ax.text(0.0, 1.03, "N = 8 seeds per audit; thick bars = group mean with 95% t-CI; units in veh·h",
            transform=ax.transAxes, fontsize=8.8, color=CLR_TEXT_MUTED)

    ax.legend(frameon=False, loc="upper right", fontsize=8.5)
    plt.tight_layout()
    fig1_path = out_path / "fig1_bee_dev_vs_frozen.png"
    plt.savefig(fig1_path, dpi=dpi)
    plt.close()
    print(f"Saved {fig1_path}")

    # =========================================================================
    # 2. Figure 2: fig2_gain_predicted_vs_realised.png
    # =========================================================================
    print("Generating Figure 2...")
    froz_a3_b, froz_a3_d, froz_a3_p = [], [], []
    for s in froz_seeds:
        tw_b = raw_frozen[(raw_frozen["world"] == "twin") & (raw_frozen["belief"] == "B") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]
        tw_d = raw_frozen[(raw_frozen["world"] == "twin") & (raw_frozen["belief"] == "D300") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]
        px = raw_frozen[(raw_frozen["world"] == "proxy") & (raw_frozen["seed"] == s) & (raw_frozen["status"] == "ok")]

        r2_b = tw_b[tw_b["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        r2_d = tw_d[tw_d["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
        m2 = px[px["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()

        g_b = float(r2_b["A0"] - r2_b["A3"])
        g_d = float(r2_d["A0"] - r2_d["A3"])
        g_p = float(m2["A0"] - m2["A3"])

        froz_a3_b.append(g_b)
        froz_a3_d.append(g_d)
        froz_a3_p.append(g_p)

        csv_rows.append({"figure": "fig2", "series": "Twin predicted (belief B)", "seed/group": str(s), "value": g_b})
        csv_rows.append({"figure": "fig2", "series": "Twin predicted (belief D300)", "seed/group": str(s), "value": g_d})
        csv_rows.append({"figure": "fig2", "series": "Proxy realised", "seed/group": str(s), "value": g_p})

    mean_b = float(np.mean(froz_a3_b))
    mean_d = float(np.mean(froz_a3_d))
    mean_p = float(np.mean(froz_a3_p))

    csv_rows.append({"figure": "fig2", "series": "Mean Twin B", "seed/group": "Frozen audit", "value": mean_b})
    csv_rows.append({"figure": "fig2", "series": "Mean Twin D300", "seed/group": "Frozen audit", "value": mean_d})
    csv_rows.append({"figure": "fig2", "series": "Mean Proxy", "seed/group": "Frozen audit", "value": mean_p})

    fig, ax = plt.subplots(figsize=(8.2, 5.3), dpi=dpi)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="-", alpha=0.7)
    ax.xaxis.grid(False)

    x_idx = np.arange(len(froz_seeds))
    w_off = 0.18

    # Plot dots
    ax.scatter(x_idx - w_off, froz_a3_b, color=CLR_TWIN_B, s=65, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Twin predicted (belief B)")
    ax.scatter(x_idx, froz_a3_d, color=CLR_TWIN_D, s=65, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Twin predicted (D300 control)")
    ax.scatter(x_idx + w_off, froz_a3_p, color=CLR_PROXY, s=65, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Proxy realised (ground truth)")

    # Mean lines
    ax.axhline(mean_b, color=CLR_TWIN_B, linestyle="--", linewidth=1.5, zorder=2, alpha=0.85)
    ax.axhline(mean_p, color=CLR_PROXY, linestyle="--", linewidth=1.5, zorder=2, alpha=0.85)
    ax.axhline(mean_d, color=CLR_TWIN_D, linestyle="--", linewidth=1.5, zorder=2, alpha=0.85)

    # Right labels in clear right margin
    x_lbl = 7.7
    ax.text(x_lbl, mean_b + 0.22, f"Twin B mean: {mean_b:.2f} veh·h", color=CLR_TWIN_B,
            ha="left", va="bottom", fontsize=8.5, fontweight="bold")
    ax.text(x_lbl, mean_p + 0.22, f"Proxy mean: {mean_p:.2f} veh·h", color=CLR_PROXY,
            ha="left", va="bottom", fontsize=8.5, fontweight="bold")
    ax.text(x_lbl, mean_d + 0.22, f"Twin D300 mean: {mean_d:.2f} veh·h", color=CLR_TWIN_D,
            ha="left", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_xticks(x_idx)
    ax.set_xticklabels([str(s) for s in froz_seeds], fontsize=9.5)
    ax.set_xlabel("Frozen Test Seed", fontsize=10)
    ax.set_ylabel("Fixed-Action A3 Gain vs A0 (veh·h)", fontsize=10.5)
    ax.set_ylim(-1.0, 9.2)
    ax.set_xlim(-0.5, 9.5)

    ax.set_title("Belief B Overpredicts A3 Gain Whereas D300 Collapses Near Zero",
                 fontsize=11.5, fontweight="bold", pad=20, loc="left", color=CLR_TEXT_DARK)
    ax.text(0.0, 1.03, "Frozen test audit (N = 8 seeds, 4501–4508); horizontal guides = group means (veh·h)",
            transform=ax.transAxes, fontsize=8.8, color=CLR_TEXT_MUTED)

    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.02, 0.98), fontsize=8.5)
    plt.tight_layout()
    fig2_path = out_path / "fig2_gain_predicted_vs_realised.png"
    plt.savefig(fig2_path, dpi=dpi)
    plt.close()
    print(f"Saved {fig2_path}")

    # =========================================================================
    # 3. Figure 3: fig3_action_gains.png
    # =========================================================================
    print("Generating Figure 3...")
    actions = ["A1", "A2", "A3", "A4"]
    tw_means, tw_cis = [], []
    px_means, px_cis = [], []

    for a in actions:
        tw_g, px_g = [], []
        for s in froz_seeds:
            tw = raw_frozen[(raw_frozen["world"] == "twin") & (raw_frozen["belief"] == "B") & (raw_frozen["seed"] == s) & (raw_frozen["replication"].isin([4, 5, 6]))]
            px = raw_frozen[(raw_frozen["world"] == "proxy") & (raw_frozen["seed"] == s) & (raw_frozen["replication"].isin([4, 5, 6]))]
            tw_m = tw.groupby("action")["J"].mean()
            px_m = px.groupby("action")["J"].mean()
            tw_g.append(tw_m["A0"] - tw_m[a])
            px_g.append(px_m["A0"] - px_m[a])

        m_tw = float(np.mean(tw_g))
        ci_tw = float(t_crit_95(len(tw_g)) * (np.std(tw_g, ddof=1) / np.sqrt(len(tw_g))))
        m_px = float(np.mean(px_g))
        ci_px = float(t_crit_95(len(px_g)) * (np.std(px_g, ddof=1) / np.sqrt(len(px_g))))

        tw_means.append(m_tw)
        tw_cis.append(ci_tw)
        px_means.append(m_px)
        px_cis.append(ci_px)

        csv_rows.append({"figure": "fig3", "series": "Twin (B, R2) mean gain", "seed/group": a, "value": m_tw})
        csv_rows.append({"figure": "fig3", "series": "Twin (B, R2) 95% CI half-width", "seed/group": a, "value": ci_tw})
        csv_rows.append({"figure": "fig3", "series": "Proxy (M2) mean gain", "seed/group": a, "value": m_px})
        csv_rows.append({"figure": "fig3", "series": "Proxy (M2) 95% CI half-width", "seed/group": a, "value": ci_px})

    fig, ax = plt.subplots(figsize=(7.8, 5.3), dpi=dpi)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="-", alpha=0.7)
    ax.xaxis.grid(False)

    x_act = np.arange(len(actions))
    bar_w = 0.28
    gap = 0.02

    rects_tw = ax.bar(x_act - bar_w/2 - gap/2, tw_means, width=bar_w, yerr=tw_cis,
                      color=CLR_TWIN_B, ecolor=CLR_TEXT_DARK, capsize=4, error_kw={"elinewidth": 1.5, "capthick": 1.5},
                      label="Twin predicted (belief B, R₂)")
    rects_px = ax.bar(x_act + bar_w/2 + gap/2, px_means, width=bar_w, yerr=px_cis,
                      color=CLR_PROXY, ecolor=CLR_TEXT_DARK, capsize=4, error_kw={"elinewidth": 1.5, "capthick": 1.5},
                      label="Proxy realised (ground truth, M₂)")

    ax.axhline(0, color=CLR_TEXT_MUTED, linestyle="--", linewidth=1.0, alpha=0.5)

    # Direct labels on top of bars
    for i, (rect, val, ci) in enumerate(zip(rects_tw, tw_means, tw_cis)):
        y_pos = max(val + ci + 0.25, 0.4)
        ax.text(rect.get_x() + rect.get_width()/2, y_pos, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8.5, fontweight="semibold", color=CLR_TWIN_B)

    for i, (rect, val, ci) in enumerate(zip(rects_px, px_means, px_cis)):
        y_pos = max(val + ci + 0.25, 0.4)
        ax.text(rect.get_x() + rect.get_width()/2, y_pos, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8.5, fontweight="semibold", color=CLR_PROXY)

    action_labels = [
        "A1 signal plan",
        "A2 VMS diversion",
        "A3 signal plan + VMS",
        "A4 stronger VMS",
    ]
    ax.set_xticks(x_act)
    ax.set_xticklabels(action_labels, fontsize=9.5)
    ax.set_ylabel("Mean Gain vs A0 (veh·h)", fontsize=10.5)
    ax.set_ylim(-0.8, 9.0)

    ax.set_title("Twin and Proxy both rank A3 highest; the Twin overpredicts its gain",
                 fontsize=11.5, fontweight="bold", pad=20, loc="left", color=CLR_TEXT_DARK)
    ax.text(0.0, 1.03, "Frozen test audit (N = 8 seeds, 4501–4508); bars = mean gain vs A0 with 95% t-CI (veh·h)",
            transform=ax.transAxes, fontsize=8.8, color=CLR_TEXT_MUTED)

    ax.legend(frameon=False, loc="upper left", fontsize=8.8)
    plt.tight_layout()
    fig3_path = out_path / "fig3_action_gains.png"
    plt.savefig(fig3_path, dpi=dpi)
    plt.close()
    print(f"Saved {fig3_path}")

    # =========================================================================
    # 4. Figure 4: fig4_missing_queue.png
    # =========================================================================
    print("Generating Figure 4...")
    mq_raw = pd.read_parquet("results/missing_queue/raw.parquet")
    mq_seeds = [4301, 4302, 4303, 4304]
    cd_errors, hd_errors = [], []

    for s in mq_seeds:
        px = mq_raw[(mq_raw["world"] == "proxy") & (mq_raw["seed"] == s) & (mq_raw["replication"].isin([4, 5, 6]))]
        g_p = float(px.groupby("action")["J"].mean()["A0"] - px.groupby("action")["J"].mean()["A3"])

        cd = mq_raw[(mq_raw["arm"] == "C-D") & (mq_raw["seed"] == s) & (mq_raw["replication"].isin([4, 5, 6]))]
        g_cd = float(cd.groupby("action")["J"].mean()["A0"] - cd.groupby("action")["J"].mean()["A3"])
        e_cd = abs(g_cd - g_p)
        cd_errors.append(e_cd)

        hd = mq_raw[(mq_raw["arm"] == "H-D") & (mq_raw["seed"] == s) & (mq_raw["replication"].isin([4, 5, 6]))]
        g_hd = float(hd.groupby("action")["J"].mean()["A0"] - hd.groupby("action")["J"].mean()["A3"])
        e_hd = abs(g_hd - g_p)
        hd_errors.append(e_hd)

        csv_rows.append({"figure": "fig4", "series": "Conventional state (C-D) error", "seed/group": str(s), "value": e_cd})
        csv_rows.append({"figure": "fig4", "series": "Replayed-history state (H-D) error", "seed/group": str(s), "value": e_hd})

    mean_e_cd = float(np.mean(cd_errors))
    mean_e_hd = float(np.mean(hd_errors))
    csv_rows.append({"figure": "fig4", "series": "Mean C-D error", "seed/group": "Missing-queue diagnostic", "value": mean_e_cd})
    csv_rows.append({"figure": "fig4", "series": "Mean H-D error", "seed/group": "Missing-queue diagnostic", "value": mean_e_hd})

    fig, ax = plt.subplots(figsize=(7.8, 5.0), dpi=dpi)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.grid(True, linestyle="-", alpha=0.7)
    ax.yaxis.grid(False)

    y_pos = np.arange(len(mq_seeds))

    # Dumbbell connecting lines
    for y, e_cd, e_hd in zip(y_pos, cd_errors, hd_errors):
        ax.plot([e_hd, e_cd], [y, y], color=CLR_TEXT_MUTED, linewidth=2.0, zorder=2, alpha=0.6)
        reduction = e_hd - e_cd
        ax.text((e_hd + e_cd) / 2, y + 0.16, f"Δ = {reduction:+.2f} veh·h",
                ha="center", va="bottom", fontsize=8.2, color=CLR_TEXT_MUTED, fontstyle="italic")

    # Dumbbell points
    ax.scatter(cd_errors, y_pos, color=CLR_TWIN_D, s=80, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Conventional state (C-D, missing queue)")
    ax.scatter(hd_errors, y_pos, color=CLR_TWIN_B, s=80, edgecolors=CLR_SURFACE, linewidths=2,
               zorder=4, label="Replayed-history state (H-D, restored queue)")

    # Mean guides
    ax.axvline(mean_e_cd, color=CLR_TWIN_D, linestyle="--", linewidth=1.2, alpha=0.7, zorder=1)
    ax.axvline(mean_e_hd, color=CLR_TWIN_B, linestyle="--", linewidth=1.2, alpha=0.7, zorder=1)

    ax.text(mean_e_cd + 0.08, len(mq_seeds) - 0.35, f"C-D mean:\n{mean_e_cd:.2f} veh·h",
            color=CLR_TWIN_D, fontsize=8.5, fontweight="bold", ha="left", va="top")
    ax.text(mean_e_hd + 0.08, len(mq_seeds) - 0.35, f"H-D mean:\n{mean_e_hd:.2f} veh·h",
            color=CLR_TWIN_B, fontsize=8.5, fontweight="bold", ha="left", va="top")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"Seed {s}" for s in mq_seeds], fontsize=9.5)
    ax.set_xlabel("Absolute Fixed-A3 Gain Error |Ĝ_T(A3) − G_P(A3)| (veh·h)", fontsize=10)
    ax.set_xlim(-0.2, 5.4)
    ax.set_ylim(-0.6, len(mq_seeds) - 0.2)

    ax.set_title("Replaying Incident History Substantially Reduces Gain Estimation Error",
                 fontsize=11.5, fontweight="bold", pad=20, loc="left", color=CLR_TEXT_DARK)
    ax.text(0.0, 1.03, "Missing-queue diagnostic (N = 4 seeds, 4301–4304); truth-assisted clearance arm (veh·h)",
            transform=ax.transAxes, fontsize=8.8, color=CLR_TEXT_MUTED)

    ax.legend(frameon=False, loc="lower right", fontsize=8.5)
    plt.tight_layout()
    fig4_path = out_path / "fig4_missing_queue.png"
    plt.savefig(fig4_path, dpi=dpi)
    plt.close()
    print(f"Saved {fig4_path}")

    # =========================================================================
    # 5. Figure 5: fig5_queue_at_decision_time.png
    # =========================================================================
    print("Generating Figure 5...")
    sh_df = pd.read_parquet("results/frozen_audit/state_history.parquet")

    sh_px = sh_df[sh_df["world"] == "proxy"].sort_values("seed")
    sh_tw = sh_df[sh_df["world"] == "twin"].sort_values("seed")

    q_px = sh_px["Q"].values
    q_tw = sh_tw["Q"].values
    ktb_px = sh_px["ktb_n1_all_veh"].values
    ktb_tw = sh_tw["ktb_n1_all_veh"].values
    sh_seeds = sh_px["seed"].values

    for s, qp, qt, kp, kt in zip(sh_seeds, q_px, q_tw, ktb_px, ktb_tw):
        csv_rows.append({"figure": "fig5", "series": "Halted Q (Proxy)", "seed/group": str(s), "value": qp})
        csv_rows.append({"figure": "fig5", "series": "Halted Q (Twin)", "seed/group": str(s), "value": qt})
        csv_rows.append({"figure": "fig5", "series": "Vehicles on ktb_n1 (Proxy)", "seed/group": str(s), "value": kp})
        csv_rows.append({"figure": "fig5", "series": "Vehicles on ktb_n1 (Twin)", "seed/group": str(s), "value": kt})

    csv_rows.append({"figure": "fig5", "series": "Mean Halted Q (Proxy)", "seed/group": "Frozen audit", "value": np.mean(q_px)})
    csv_rows.append({"figure": "fig5", "series": "Mean Halted Q (Twin)", "seed/group": "Frozen audit", "value": np.mean(q_tw)})
    csv_rows.append({"figure": "fig5", "series": "Mean ktb_n1 (Proxy)", "seed/group": "Frozen audit", "value": np.mean(ktb_px)})
    csv_rows.append({"figure": "fig5", "series": "Mean ktb_n1 (Twin)", "seed/group": "Frozen audit", "value": np.mean(ktb_tw)})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 5.0), dpi=dpi)

    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, linestyle="-", alpha=0.7)
        ax.xaxis.grid(False)

    x_sh = np.arange(len(sh_seeds))
    x_lbl = 7.4

    # Panel 1: Halted Q
    for x, qp, qt in zip(x_sh, q_px, q_tw):
        ax1.plot([x, x], [qt, qp], color=CLR_TEXT_MUTED, linewidth=1.5, zorder=2, alpha=0.5)

    ax1.scatter(x_sh, q_tw, color=CLR_TWIN_B, s=65, edgecolors=CLR_SURFACE, linewidths=2,
                zorder=4, label="Twin (empty initial queue)")
    ax1.scatter(x_sh, q_px, color=CLR_PROXY, s=65, edgecolors=CLR_SURFACE, linewidths=2,
                zorder=4, label="Proxy (realised queue)")

    mean_qp = np.mean(q_px)
    mean_qt = np.mean(q_tw)
    ax1.axhline(mean_qp, color=CLR_PROXY, linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.axhline(mean_qt, color=CLR_TWIN_B, linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.text(x_lbl, mean_qp + 0.8, f"Proxy mean: {mean_qp:.1f} veh", color=CLR_PROXY,
             ha="left", va="bottom", fontsize=8.2, fontweight="bold")
    ax1.text(x_lbl, mean_qt + 0.8, f"Twin mean: {mean_qt:.1f} veh", color=CLR_TWIN_B,
             ha="left", va="bottom", fontsize=8.2, fontweight="bold")

    ax1.set_xticks(x_sh)
    ax1.set_xticklabels([str(s) for s in sh_seeds], fontsize=8.5)
    ax1.set_xlabel("Frozen Test Seed", fontsize=9.5)
    ax1.set_ylabel("Halted Vehicles Q (veh)", fontsize=10)
    ax1.set_ylim(-2, 32)
    ax1.set_xlim(-0.5, 12.2)
    ax1.set_title("Halted Queue at Decision Time (t_d)", fontsize=10.5, fontweight="bold", loc="left", color=CLR_TEXT_DARK)
    ax1.legend(frameon=False, loc="upper left", fontsize=8.2)

    # Panel 2: ktb_n1 all veh
    for x, kp, kt in zip(x_sh, ktb_px, ktb_tw):
        ax2.plot([x, x], [kt, kp], color=CLR_TEXT_MUTED, linewidth=1.5, zorder=2, alpha=0.5)

    ax2.scatter(x_sh, ktb_tw, color=CLR_TWIN_B, s=65, edgecolors=CLR_SURFACE, linewidths=2,
                zorder=4, label="Twin (free flow state)")
    ax2.scatter(x_sh, ktb_px, color=CLR_PROXY, s=65, edgecolors=CLR_SURFACE, linewidths=2,
                zorder=4, label="Proxy (congested corridor)")

    mean_kp = np.mean(ktb_px)
    mean_kt = np.mean(ktb_tw)
    ax2.axhline(mean_kp, color=CLR_PROXY, linestyle="--", linewidth=1.2, alpha=0.8)
    ax2.axhline(mean_kt, color=CLR_TWIN_B, linestyle="--", linewidth=1.2, alpha=0.8)
    ax2.text(x_lbl, mean_kp + 4.0, f"Proxy mean: {mean_kp:.1f} veh", color=CLR_PROXY,
             ha="left", va="bottom", fontsize=8.2, fontweight="bold")
    ax2.text(x_lbl, mean_kt + 4.0, f"Twin mean: {mean_kt:.1f} veh", color=CLR_TWIN_B,
             ha="left", va="bottom", fontsize=8.2, fontweight="bold")

    ax2.set_xticks(x_sh)
    ax2.set_xticklabels([str(s) for s in sh_seeds], fontsize=8.5)
    ax2.set_xlabel("Frozen Test Seed", fontsize=9.5)
    ax2.set_ylabel("All Vehicles on ktb_n1 (veh)", fontsize=10)
    ax2.set_ylim(0, 250)
    ax2.set_xlim(-0.5, 12.2)
    ax2.set_title("Corridor Vehicle Count on ktb_n1", fontsize=10.5, fontweight="bold", loc="left", color=CLR_TEXT_DARK)
    ax2.legend(frameon=False, loc="upper left", fontsize=8.2)

    fig.suptitle("Twin Misses Incident Queue and Corridor Congestion at Decision Time",
                 fontsize=12, fontweight="bold", x=0.06, y=0.98, ha="left", color=CLR_TEXT_DARK)
    fig.text(0.06, 0.93, "Frozen test audit snapshot at t_d = 5,100 s (N = 8 seeds, 4501–4508); vehicle counts",
             fontsize=8.8, color=CLR_TEXT_MUTED, ha="left")

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    fig5_path = out_path / "fig5_queue_at_decision_time.png"
    plt.savefig(fig5_path, dpi=dpi)
    plt.close()
    print(f"Saved {fig5_path}")

    # =========================================================================
    # Write CSV
    # =========================================================================
    df_csv = pd.DataFrame(csv_rows)
    # Ensure column naming matches: figure, series, seed/group, value
    csv_file = out_path / "figure_data.csv"
    df_csv.to_csv(csv_file, index=False)
    print(f"Saved {csv_file} with {len(df_csv)} records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpi", type=int, default=72)
    parser.add_argument("--out-dir", type=str, default="final/figures")
    args = parser.parse_args()
    run(dpi=args.dpi, out_dir=args.out_dir)
