import os
import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# Load fonts
font_prop = fm.FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")

# Test extracting simulation data for t=5100, 5400, 5700
# First extract lane shapes
sys.path.insert(0, r"D:\CityCom-astra")
import sumolib

net = sumolib.net.readNet(r"D:\CityCom-astra\scenarios\kwuntong\blite\net5.net.xml")
corridor_edges = ["ktb_w2", "ktb_w3", "ktb_n1", "dv_off_ktb_n1", "ktb_n2"]
lane_shapes = {}
for eid in corridor_edges:
    edge = net.getEdge(eid)
    lane_shapes[eid] = [lane.getShape() for lane in edge.getLanes()]

# Let's run a quick 1-step extraction or inspect vehicles
print("Lane shapes extracted.")

def draw_test_panel(world_name, t, veh_data, blocker_pos, halted_count, out_png):
    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=100)
    fig.patch.set_facecolor('#121823')
    ax.set_facecolor('#0d1117')

    # Draw lane shapes
    for eid, shapes in lane_shapes.items():
        for shape in shapes:
            xs = [p[0] for p in shape]
            ys = [p[1] for p in shape]
            ax.plot(xs, ys, color='#2d3748', linewidth=2.5, zorder=1)

    # Plot vehicles
    # Halted (< 0.1 m/s): strong red #e63946
    # Slow (0.1 to 8 m/s): orange #ff9f1c
    # Free-flow (>= 8 m/s): grey #94a3b8
    xs_halted, ys_halted = [], []
    xs_slow, ys_slow = [], []
    xs_free, ys_free = [], []

    for v in veh_data:
        x, y = v['pos']
        spd = v['speed']
        if v.get('is_blocker'):
            continue
        if spd < 0.1:
            xs_halted.append(x)
            ys_halted.append(y)
        elif spd < 8.0:
            xs_slow.append(x)
            ys_slow.append(y)
        else:
            xs_free.append(x)
            ys_free.append(y)

    if xs_free:
        ax.scatter(xs_free, ys_free, c='#94a3b8', s=16, label='自由流 (≥8 m/s)', zorder=2, alpha=0.85)
    if xs_slow:
        ax.scatter(xs_slow, ys_slow, c='#ff9f1c', s=22, label='缓行 (<8 m/s)', zorder=3, alpha=0.95)
    if xs_halted:
        ax.scatter(xs_halted, ys_halted, c='#e63946', s=28, label='停顿 (<0.1 m/s)', zorder=4, edgecolors='#ffffff', linewidths=0.5)

    # Blocker marker
    bx, by = blocker_pos['pos']
    b_label = blocker_pos['label']
    ax.scatter([bx], [by], c='black', marker='X', s=140, edgecolors='#f87171', linewidths=1.5, zorder=5)
    ax.annotate(b_label, xy=(bx, by), xytext=(bx - 120, by + 40),
                arrowprops=dict(facecolor='#f87171', edgecolor='#f87171', arrowstyle='->', lw=1.5),
                fontsize=11, fontproperties=font_prop, color='#ffffff',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#1e293b', edgecolor='#f87171', alpha=0.9),
                zorder=6)

    # Fixed zoom centered on ktb_n1
    # Center of ktb_n1: (2753.6, 1483.6)
    cx, cy = 2753.6, 1483.6
    span_y = 600.0
    span_x = span_y * (8.8 / 5.2)
    ax.set_xlim(cx - span_x, cx + span_x)
    ax.set_ylim(cy - span_y, cy + span_y)
    ax.set_aspect('equal')
    ax.axis('off')

    # Legend
    leg = ax.legend(loc='lower left', prop=font_prop, facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0', framealpha=0.9)

    plt.tight_layout(pad=0.2)
    plt.savefig(out_png, facecolor=fig.get_facecolor(), edgecolor='none', dpi=100)
    plt.close()
    print(f"Saved {out_png}")

if __name__ == "__main__":
    # Test dummy plot
    test_veh = [
        {'pos': (2700, 1400), 'speed': 0.05, 'is_blocker': False},
        {'pos': (2750, 1450), 'speed': 3.5, 'is_blocker': False},
        {'pos': (2850, 1350), 'speed': 15.0, 'is_blocker': False},
    ]
    draw_test_panel("Proxy", 5100, test_veh, {'pos': (2510, 1784), 'label': '事故 (Proxy 900m)'}, 21, r"D:\CityCom-astra\submission\video\src\scratch\test_panel_proxy.png")
