"""Pre-renders all 61 pairs of matplotlib corridor frames (t=5100..5700, step 10s)
for Proxy and Twin worlds.
"""
import os
import json
import time
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

font_prop = fm.FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")

ROOT = Path(r"D:\CityCom-astra\submission\video")
TRACE_FILE = ROOT / "src" / "sim_trace_4501.json"
OUT_DIR = ROOT / "src" / "sim_panels"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(TRACE_FILE, "r", encoding="utf-8") as f:
    TRACE = json.load(f)

GEOM = TRACE["geometry"]
CORRIDOR_ROADS = {'ktb_w1', 'ktb_w2', 'ktb_w3', 'ktb_n1', 'dv_off_ktb_n1', 'ktb_n2', 'ms_on_ktb_w2'}


def render_single_panel(world_type: str, snap_data: dict, out_path: Path):
    # Width 880, Height 500 at 100 dpi
    fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=100)
    fig.patch.set_facecolor('#121823')
    ax.set_facecolor('#0a0e14')

    # Draw lane shapes
    for eid, edata in GEOM.items():
        for ldata in edata["lanes"]:
            pts = ldata["shape"]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax.plot(xs, ys, color='#253041', linewidth=3.2, zorder=1, solid_capstyle='round')

    # Plot vehicles (only those on corridor edges)
    vehs = [v for v in snap_data["vehicles"] if v["road"] in CORRIDOR_ROADS]
    xs_halt, ys_halt = [], []
    xs_slow, ys_slow = [], []
    xs_free, ys_free = [], []

    for v in vehs:
        x, y = v["pos"]
        spd = v["spd"]
        if spd < 0.1:
            xs_halt.append(x)
            ys_halt.append(y)
        elif spd < 8.0:
            xs_slow.append(x)
            ys_slow.append(y)
        else:
            xs_free.append(x)
            ys_free.append(y)

    if xs_free:
        ax.scatter(xs_free, ys_free, c='#94a3b8', s=16, label='自由流 (≥8 m/s)', zorder=2, alpha=0.85)
    if xs_slow:
        ax.scatter(xs_slow, ys_slow, c='#f59e0b', s=24, label='缓行 (<8 m/s)', zorder=3, alpha=0.95)
    if xs_halt:
        ax.scatter(xs_halt, ys_halt, c='#ef4444', s=32, label='停顿排队 (<0.1 m/s)', zorder=4, edgecolors='#ffffff', linewidths=0.6)

    # Blocker marker & label
    t_val = snap_data["t"]
    if world_type == "proxy":
        # Proxy incident at 900 m on ktb_n1
        bx, by = 2510.1, 1784.2
        if t_val < 5400.0:
            ax.scatter([bx], [by], c='black', marker='X', s=190, edgecolors='#f87171', linewidths=2.0, zorder=6)
            ax.annotate("事故 (900m 处)", xy=(bx, by), xytext=(bx - 230, by + 45),
                        arrowprops=dict(facecolor='#f87171', edgecolor='#f87171', arrowstyle='->', lw=1.8),
                        fontsize=12, fontproperties=font_prop, color='#ffffff', weight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e293b', edgecolor='#f87171', alpha=0.92),
                        zorder=7)
        else:
            ax.scatter([bx], [by], c='#10b981', marker='o', s=140, edgecolors='#ffffff', linewidths=1.5, zorder=6)
            ax.annotate("事故已清除 (5400s)", xy=(bx, by), xytext=(bx - 250, by + 45),
                        arrowprops=dict(facecolor='#10b981', edgecolor='#10b981', arrowstyle='->', lw=1.8),
                        fontsize=12, fontproperties=font_prop, color='#ffffff', weight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e293b', edgecolor='#10b981', alpha=0.92),
                        zorder=7)
    else:
        # Twin blockage at 755.3 m on ktb_n1
        bx, by = 2598.4, 1674.2
        ax.scatter([bx], [by], c='black', marker='X', s=190, edgecolors='#60a5fa', linewidths=2.0, zorder=6)
        ax.annotate("孪生假设封堵 (755.3m)", xy=(bx, by), xytext=(bx - 260, by - 65),
                    arrowprops=dict(facecolor='#60a5fa', edgecolor='#60a5fa', arrowstyle='->', lw=1.8),
                    fontsize=12, fontproperties=font_prop, color='#ffffff', weight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e293b', edgecolor='#60a5fa', alpha=0.92),
                    zorder=7)

    # Fixed zoom centered on ktb_n1: center = (2753.6, 1483.6)
    cx, cy = 2753.6, 1483.6
    span_y = 560.0
    span_x = span_y * (8.8 / 5.0)
    ax.set_xlim(cx - span_x, cx + span_x)
    ax.set_ylim(cy - span_y, cy + span_y)
    ax.set_aspect('equal')
    ax.axis('off')

    # Road annotations
    ax.text(3420, 1020, "ktb_w2 (上游)", fontproperties=font_prop, fontsize=10, color='#64748b', zorder=2)
    ax.text(3180, 1060, "ktb_w3", fontproperties=font_prop, fontsize=10, color='#64748b', zorder=2)
    ax.text(2850, 1380, "ktb_n1 (走廊主体)", fontproperties=font_prop, fontsize=11, color='#94a3b8', zorder=2)

    # Frame overlay indicator
    halt_cnt = snap_data["corridor_halted"]
    overlay_txt = f"仿真时刻 t = {t_val:.0f}s  |  走廊停顿车辆: {halt_cnt} 辆"
    ax.text(0.02, 0.94, overlay_txt, transform=ax.transAxes, fontproperties=font_prop, fontsize=11,
            color='#38bdf8' if world_type == 'twin' else '#fb923c', weight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0f172a', edgecolor='#334155', alpha=0.92))

    # Legend
    ax.legend(loc='lower left', prop=font_prop, facecolor='#0f172a', edgecolor='#334155',
              labelcolor='#e2e8f0', framealpha=0.9, fontsize=9.5)

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=100)
    plt.close()


def generate_all_panels():
    t_start = time.time()
    steps = [int(round(t)) for t in sorted([float(k) for k in TRACE["proxy"].keys()])]
    print(f"Generating {len(steps)} pairs of panels...")
    for step in steps:
        s_key = str(step)
        p_path = OUT_DIR / f"proxy_{step}.png"
        t_path = OUT_DIR / f"twin_{step}.png"
        render_single_panel("proxy", TRACE["proxy"][s_key], p_path)
        render_single_panel("twin", TRACE["twin"][s_key], t_path)
    print(f"All {len(steps)*2} panels generated in {time.time() - t_start:.2f}s.")


if __name__ == "__main__":
    generate_all_panels()
