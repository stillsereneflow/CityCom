"""Video rendering engine for 《城脉·涟控》 competition demo video.
Renders all 7 segments to 1080p 30 fps H.264 MP4 with burned-in Chinese captions.
"""
import os
import sys
import math
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import imageio
import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_all_data

# Base directories
ROOT = Path(r"D:\CityCom-astra")
VIDEO_DIR = ROOT / "submission" / "video"
SRC_DIR = VIDEO_DIR / "src"
CHECK_DIR = VIDEO_DIR / "frames_check"
SIM_PANELS_DIR = SRC_DIR / "sim_panels"

CHECK_DIR.mkdir(parents=True, exist_ok=True)

# Font configurations
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
SUB_FONT_PATH = r"C:\Windows\Fonts\segoeui.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 54)
    font_large = ImageFont.truetype(FONT_PATH, 40)
    font_title = ImageFont.truetype(FONT_PATH, 32)
    font_body = ImageFont.truetype(FONT_PATH, 24)
    font_small = ImageFont.truetype(FONT_PATH, 20)
    font_caption = ImageFont.truetype(FONT_PATH, 26)
    font_mono = ImageFont.truetype(FONT_PATH, 22)
    font_sub_body = ImageFont.truetype(SUB_FONT_PATH, 24)
    font_sub_small = ImageFont.truetype(SUB_FONT_PATH, 20)
    font_sub_caption = ImageFont.truetype(SUB_FONT_PATH, 26)
    font_sub_title = ImageFont.truetype(SUB_FONT_PATH, 32)
except Exception as e:
    print(f"Font loading failed: {e}")
    font_huge = font_large = font_title = font_body = font_small = font_caption = font_mono = font_sub_body = font_sub_small = font_sub_caption = font_sub_title = ImageFont.load_default()

# Segment time boundaries (at 30 fps)
# 1. Title: 8 s -> 240 frames [0, 240)
# 2. Two Worlds: 40 s -> 1200 frames [240, 1440)
# 3. Event Engine Log: 35 s -> 1050 frames [1440, 2490)
# 4. Decision Branching: 40 s -> 1200 frames [2490, 3690)
# 5. Frozen Audit Summary: 40 s -> 1200 frames [3690, 4890)
# 6. Limitations: 20 s -> 600 frames [4890, 5490)
# 7. End: 5 s -> 150 frames [5490, 5640)
TOTAL_FRAMES = 5640
FPS = 30
W, H = 1920, 1080

# Load programmatic data
DATA = load_all_data()

# Load simulation trace data
sim_trace_file = SRC_DIR / "sim_trace_4501.json"
import json
with open(sim_trace_file, "r", encoding="utf-8") as f:
    SIM_TRACE = json.load(f)

# Pre-cache rendered simulation panels
proxy_panels = {}
for p in sorted(SIM_PANELS_DIR.glob("proxy_*.png")):
    try:
        t_val = int(p.stem.split("_")[1])
        proxy_panels[t_val] = Image.open(p).convert("RGB")
    except Exception:
        pass

twin_panels = {}
for p in sorted(SIM_PANELS_DIR.glob("twin_*.png")):
    try:
        t_val = int(p.stem.split("_")[1])
        twin_panels[t_val] = Image.open(p).convert("RGB")
    except Exception:
        pass

# Fallback images if needed
default_shot = Image.new("RGB", (960, 570), (15, 20, 30))
fig1_img = Image.open(DATA["figures"]["fig1"]).convert("RGB") if Path(DATA["figures"]["fig1"]).exists() else default_shot
fig3_img = Image.open(DATA["figures"]["fig3"]).convert("RGB") if Path(DATA["figures"]["fig3"]).exists() else default_shot


def draw_dark_background(im, draw):
    # Deep slate tech gradient
    draw.rectangle([(0, 0), (W, H)], fill=(13, 17, 23))
    # Subtle grid lines
    grid_color = (22, 27, 34)
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)


def draw_corner_badge(draw, text="实验室原型 · 合成场景"):
    # Semi-transparent pill badge in top-right corner
    bbox = font_small.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px, py = W - tw - 50, 20
    draw.rounded_rectangle([(px - 14, py - 6), (px + tw + 14, py + th + 6)], radius=6, fill=(26, 35, 50), outline=(56, 139, 253), width=1)
    draw.text((px, py), text, fill=(88, 166, 255), font=font_small)


def draw_text_with_subscript(draw, pos, text, font, font_sub, fill):
    if "₁" not in text and "₂" not in text:
        draw.text(pos, text, fill=fill, font=font)
        return
    x, y = pos
    for ch in text:
        f = font_sub if ch in ("₁", "₂") else font
        draw.text((x, y), ch, font=f, fill=fill)
        adv = f.getlength(ch) if hasattr(f, "getlength") else (f.getbbox(ch)[2] - f.getbbox(ch)[0] if f.getbbox(ch) else 12)
        x += adv


def draw_caption(draw, lines):
    # Dark semi-transparent bottom caption band
    band_y0, band_y1 = H - 120, H - 30
    draw.rounded_rectangle([(180, band_y0), (W - 180, band_y1)], radius=12, fill=(10, 14, 20), outline=(48, 54, 61), width=1)
    
    if len(lines) == 1:
        text = lines[0]
        tw = sum(font_sub_caption.getlength(ch) if ch in ("₁", "₂") else font_caption.getlength(ch) for ch in text)
        tx = int((W - tw) // 2)
        ty = band_y0 + (band_y1 - band_y0 - 28) // 2
        draw_text_with_subscript(draw, (tx, ty), text, font_caption, font_sub_caption, (240, 246, 252))
    elif len(lines) >= 2:
        for idx, text in enumerate(lines[:2]):
            tw = sum(font_sub_caption.getlength(ch) if ch in ("₁", "₂") else font_caption.getlength(ch) for ch in text)
            tx = int((W - tw) // 2)
            ty = band_y0 + 12 + idx * 36
            draw_text_with_subscript(draw, (tx, ty), text, font_caption, font_sub_caption, (240, 246, 252))


# ==================== SEGMENT DRAWERS ====================

def draw_segment1(f_idx):
    # Segment 1: Title (0 to 8s, 240 frames)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    # Accent decorative card
    card_x0, card_y0, card_x1, card_y1 = 200, 220, W - 200, 860
    draw.rounded_rectangle([(card_x0, card_y0), (card_x1, card_y1)], radius=16, fill=(18, 24, 35), outline=(48, 54, 61), width=2)
    # Top highlight line
    draw.line([(card_x0 + 20, card_y0), (card_x1 - 20, card_y0)], fill=(56, 139, 253), width=3)

    # Tag pill
    tag = "香港九龙东合成走廊 · 离线决策审计"
    bbox_t = font_small.getbbox(tag)
    tw_t = bbox_t[2] - bbox_t[0]
    draw.rounded_rectangle([(W // 2 - tw_t // 2 - 15, card_y0 + 50), (W // 2 + tw_t // 2 + 15, card_y0 + 85)], radius=6, fill=(33, 45, 65))
    draw.text((W // 2 - tw_t // 2, card_y0 + 55), tag, fill=(88, 166, 255), font=font_small)

    # Main Title
    t1 = "《城脉·涟控》"
    t2 = "事件感知交通数字孪生实验室原型"
    b1 = font_huge.getbbox(t1)
    b2 = font_large.getbbox(t2)
    draw.text(((W - (b1[2] - b1[0])) // 2, card_y0 + 120), t1, fill=(255, 255, 255), font=font_huge)
    draw.text(((W - (b2[2] - b2[0])) // 2, card_y0 + 210), t2, fill=(201, 209, 217), font=font_large)

    # Subtitle
    sub = "合成的观塘道—观塘绕道走廊（香港九龙东） · 实验室验证级 · 冻结测试结果"
    bs = font_body.getbbox(sub)
    draw.text(((W - (bs[2] - bs[0])) // 2, card_y0 + 310), sub, fill=(139, 148, 158), font=font_body)

    # Feature badges
    badges = ["无在线事故自采纳声称", "真实SUMO离线审计回放", "严谨报告局限与误差抵消", "冻结测试完整复现"]
    bx_start = 280
    for idx, b_txt in enumerate(badges):
        bx = bx_start + idx * 350
        by = card_y0 + 430
        draw.rounded_rectangle([(bx, by), (bx + 310, by + 60)], radius=8, fill=(22, 27, 34), outline=(48, 54, 61), width=1)
        draw.text((bx + 20, by + 18), "[√] " + b_txt, fill=(126, 231, 135), font=font_small)

    return im


def draw_segment2(f_idx):
    # Segment 2: Two Worlds (8 to 48s, frames 240 to 1440)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)
    draw_corner_badge(draw)

    # Simulation time calculation: 5100 -> 5700 s
    progress = (f_idx - 240) / 1200.0
    sim_t = 5100.0 + progress * 600.0
    sim_step_10 = int(round(sim_t / 10.0)) * 10
    sim_step_10 = max(5100, min(5700, sim_step_10))

    # Header bar
    draw.rectangle([(0, 0), (W, 75)], fill=(18, 24, 35))
    draw.line([(0, 75), (W, 75)], fill=(48, 54, 61), width=1)
    draw.text((60, 22), "仿真状态逐帧绘制（SUMO 无界面运行，离线审计数据，种子 4501）", fill=(255, 255, 255), font=font_title)

    # Time indicator pill
    t_str = f"仿真时刻 t = {sim_t:.1f} s"
    bbox_time = font_title.getbbox(t_str)
    tw_time = bbox_time[2] - bbox_time[0]
    draw.rounded_rectangle([(W - tw_time - 320, 15), (W - 290, 60)], radius=6, fill=(31, 111, 235))
    draw.text((W - tw_time - 305, 22), t_str, fill=(255, 255, 255), font=font_title)

    # Split-screen boxes: Left (Proxy), Right (Twin)
    view_w, view_h = 880, 500
    view_y = 150

    # Programmatic facts from state_history.parquet (Seed 4501)
    hist_4501 = DATA["state_history_4501"]
    proxy_q = hist_4501["proxy_q"]
    proxy_ktb_veh = hist_4501["proxy_ktb_n1_all_veh"]
    twin_q = hist_4501["twin_q"]
    twin_ktb_veh = hist_4501["twin_ktb_n1_all_veh"]

    p_snap = SIM_TRACE["proxy"][str(sim_step_10)]
    t_snap = SIM_TRACE["twin"][str(sim_step_10)]
    p_halt = p_snap["corridor_halted"]
    t_halt = t_snap["corridor_halted"]

    # Left frame: Proxy
    draw.rounded_rectangle([(45, 90), (935, 920)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
    draw.text((65, 105), "代理世界（Proxy 世界）", fill=(240, 136, 62), font=font_title)
    draw.text((540, 112), "[设定的合成事故位于 900m 处 · 排队持续形成]", fill=(139, 148, 158), font=font_small)

    if sim_step_10 in proxy_panels:
        p_img = proxy_panels[sim_step_10]
        im.paste(p_img, (50, view_y))

    # Overlay stats on Left
    draw.rectangle([(50, view_y + view_h + 10), (50 + view_w, view_y + view_h + 235)], fill=(22, 27, 34))
    draw.text((70, view_y + view_h + 20), "【代理世界状态】(离线数据，种子 4501 · 动作 A0 · 复现 4):", fill=(201, 209, 217), font=font_body)
    draw.text((90, view_y + view_h + 55), f"• 决策时刻走廊排队 Q = {proxy_q} 辆；ktb_n1 积聚车辆 = {proxy_ktb_veh} 辆 (代理世界排队存在)", fill=(240, 136, 62), font=font_small)
    draw.text((90, view_y + view_h + 85), f"• 走廊实时停顿车辆 (ktb_w1–n1): {p_halt} 辆 (排除事故车辆)", fill=(201, 209, 217), font=font_small)
    if sim_t >= 5400.0:
        draw.text((90, view_y + view_h + 120), "• t=5400s 预定清除时刻: 事故车辆恢复通行，排队开始消散", fill=(126, 231, 135), font=font_small)
    else:
        draw.text((90, view_y + view_h + 120), "• t<5400s: 设定的合成事故阻塞车道 0-1 (900.0m 处)，排队沿 ktb_n1 向上游溢流", fill=(248, 81, 73), font=font_small)

    # Right frame: Twin
    draw.rounded_rectangle([(985, 90), (1875, 920)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
    draw.text((1005, 105), "数字孪生（Twin 世界 · 信念 B）", fill=(88, 166, 255), font=font_title)
    draw.text((1500, 112), "[只接收检测器数据 · 缺失排队历史]", fill=(139, 148, 158), font=font_small)

    if sim_step_10 in twin_panels:
        t_img = twin_panels[sim_step_10]
        im.paste(t_img, (990, view_y))

    # Overlay stats on Right
    draw.rectangle([(990, view_y + view_h + 10), (990 + view_w, view_y + view_h + 235)], fill=(22, 27, 34))
    draw.text((1010, view_y + view_h + 20), "【数字孪生状态】(常规同化 + 强加信念 B 封堵):", fill=(201, 209, 217), font=font_body)
    draw.text((1030, view_y + view_h + 55), f"• 决策时刻走廊排队 Q = {twin_q} 辆；ktb_n1 积聚车辆 = {twin_ktb_veh} 辆 (缺失排队历史)", fill=(248, 81, 73), font=font_small)
    draw.text((1030, view_y + view_h + 85), f"• 走廊实时停顿车辆 (ktb_w1–n1): {t_halt} 辆 (排除封堵车辆)", fill=(201, 209, 217), font=font_small)
    draw.text((1030, view_y + view_h + 120), "• 解释：结果与误差相互抵消一致，尚未证明因果机制。", fill=(88, 166, 255), font=font_small)

    # Caption
    if f_idx < 240 + 600:
        draw_caption(draw, [
            "左侧事故已持续10分钟、排队存在；",
            "右侧孪生在决策时刻没有这段排队历史。"
        ])
    else:
        draw_caption(draw, [
            "右侧孪生只能假设封堵持续；",
            "解释：结果与误差相互抵消一致，尚未证明因果机制。"
        ])

    return im


def draw_segment3(f_idx):
    # Segment 3: Event Engine Log (35 s, frames 1440 to 2490)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    # Header bar
    draw.rectangle([(0, 0), (W, 75)], fill=(18, 24, 35))
    draw.line([(0, 75), (W, 75)], fill=(48, 54, 61), width=1)
    draw.text((60, 22), "开发运行日志回放（evt_inc_4401 状态轨迹与假设库评估）", fill=(255, 255, 255), font=font_title)

    # Terminal card
    term_x0, term_y0, term_x1, term_y1 = 80, 110, W - 80, 890
    draw.rounded_rectangle([(term_x0, term_y0), (term_x1, term_y1)], radius=12, fill=(10, 14, 20), outline=(48, 54, 61), width=1)
    # Terminal title bar
    draw.rectangle([(term_x0, term_y0), (term_x1, term_y0 + 40)], fill=(22, 27, 34))
    draw.ellipse([(term_x0 + 15, term_y0 + 14), (term_x0 + 27, term_y0 + 26)], fill=(248, 81, 73))
    draw.ellipse([(term_x0 + 35, term_y0 + 14), (term_x0 + 47, term_y0 + 26)], fill=(210, 153, 34))
    draw.ellipse([(term_x0 + 55, term_y0 + 14), (term_x0 + 67, term_y0 + 26)], fill=(46, 160, 67))
    draw.text((term_x0 + 85, term_y0 + 10), "citypulse/event_engine: state_trace.jsonl & event_log.jsonl", fill=(139, 148, 158), font=font_small)

    # Terminal logs typing progression
    elapsed_seg = (f_idx - 1440) / 30.0 # 0 to 35s
    logs = [
        (0.0, "[t=4890.0s] [ALARM] 检测器触发警报: NORMAL -> SUSPECTED_EVENT (reason: trigger_alarm)", (240, 136, 62)),
        (3.0, "[t=4890.0s] [EVAL]  启动20假设候选库回放评分 (事故:10, 需求:4, 传感器故障:6)", (88, 166, 255)),
        (7.0, "[t=4890.0s] [MAP]   h* = flt_AID02111_stuck (故障类, logL=-40.83, 后验=0.466, gap=1.85)", (126, 231, 135)),
        (11.0, "[t=4890.0s] [EXIT]  未满足事故采纳条件 (adopted: false) -> SUSPECTED_EVENT -> NORMAL", (210, 153, 34)),
        (15.0, "[t=4920.0s] [ALARM] 再次触发警报: NORMAL -> SUSPECTED_EVENT (reason: trigger_alarm)", (240, 136, 62)),
        (18.0, "[t=4920.0s] [MAP]   h* = dem_f1.3 (需求增加类, factor=1.3, 后验=0.322, gap=0.0)", (88, 166, 255)),
        (22.0, "[t=4980.0s] [EVAL]  持续评估: h* = dem_f1.3 (后验=0.322, adopted: false)", (139, 148, 158)),
        (26.0, "[t=5040.0s] [MAP]   h* = flt_AID02109_stuck (故障类, 后验=0.372) -> 退出报警回到 NORMAL", (210, 153, 34)),
        (29.0, "[t=5100.0s] [STAT]  6 个事故运行中 0 个自然采纳事故假设 | 需求冲击场景触发率: 0/6", (248, 81, 73)),
        (31.0, "[CONCLUSION] 引擎机制完整，但开发运行中未自然采纳事故假设——这是如实报告的局限", (255, 255, 255)),
    ]

    ly = term_y0 + 60
    for t_show, log_text, color in logs:
        if elapsed_seg >= t_show:
            draw.text((term_x0 + 30, ly), log_text, fill=color, font=font_mono)
            ly += 38

    # Caption
    if f_idx < 1440 + 510:
        draw_caption(draw, [
            "引擎触发并评估了20个候选假设；",
            "MAP评估判定为传感器故障或需求变化。"
        ])
    else:
        draw_caption(draw, [
            "6 个事故运行中 0 个自然采纳事故假设；",
            "这是实验室原型如实报告的局限性。"
        ])

    return im


def draw_segment4(f_idx):
    # Segment 4: Decision Branching (40 s, frames 2490 to 3690)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    # Header bar
    draw.rectangle([(0, 0), (W, 75)], fill=(18, 24, 35))
    draw.line([(0, 75), (W, 75)], fill=(48, 54, 61), width=1)
    draw.text((60, 22), "决策分支审计卡片（种子 4501，离线数字孪生 vs 现实代理世界）", fill=(255, 255, 255), font=font_title)

    # Table Card
    tbl_x0, tbl_y0, tbl_x1, tbl_y1 = 80, 110, W - 80, 890
    draw.rounded_rectangle([(tbl_x0, tbl_y0), (tbl_x1, tbl_y1)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)

    # Table title and legend
    draw.text((tbl_x0 + 40, tbl_y0 + 25), "动作分支评估结果表（数据来源：final/demo/decision_cards.txt）", fill=(201, 209, 217), font=font_title)

    # Table headers
    headers = [("动作", 140), ("控制策略说明", 380), ("孪生耗时 J_T", 200), ("孪生收益 G_T", 200), ("代理耗时 J_P", 200), ("现实收益 G_P", 200), ("决策状态", 260)]
    hy = tbl_y0 + 80
    draw.rectangle([(tbl_x0 + 30, hy), (tbl_x1 - 30, hy + 45)], fill=(33, 45, 65))
    hx = tbl_x0 + 45
    for h_txt, hw in headers:
        draw.text((hx, hy + 10), h_txt, fill=(88, 166, 255), font=font_small)
        hx += hw

    # Rows from data
    card_data = DATA["decision_card_4501"]["table"]
    act_names = {
        "A0": "无动作 (Do Nothing)",
        "A1": "事故信号预案 (Signal Plan)",
        "A2": "VMS诱导绕行 (VMS Diversion)",
        "A3": "信号预案 + VMS (Plan + VMS)",
        "A4": "加强VMS (Strong VMS)",
    }

    ry = hy + 55
    for row in card_data:
        act = row["action"]
        is_best = (act == "A3")
        row_bg = (30, 41, 59) if is_best else ((22, 27, 34) if act in ("A1", "A3") else (18, 24, 35))
        outline_c = (210, 153, 34) if is_best else None
        
        draw.rounded_rectangle([(tbl_x0 + 30, ry), (tbl_x1 - 30, ry + 60)], radius=6, fill=row_bg, outline=outline_c, width=2 if is_best else 0)
        
        rx = tbl_x0 + 45
        # Col 1: Action
        act_col = (255, 215, 0) if is_best else (255, 255, 255)
        draw.text((rx, ry + 16), act, fill=act_col, font=font_body)
        rx += 140
        # Col 2: Name
        draw.text((rx, ry + 18), act_names.get(act, act), fill=(201, 209, 217), font=font_small)
        rx += 380
        # Col 3: Twin J
        draw.text((rx, ry + 16), f"{row['twin_j']:.2f}", fill=(201, 209, 217), font=font_body)
        rx += 200
        # Col 4: Twin Gain
        tg_col = (126, 231, 135) if row['twin_gain'] > 0 else ((248, 81, 73) if row['twin_gain'] < 0 else (139, 148, 158))
        draw.text((rx, ry + 16), f"{row['twin_gain']:+.3f}", fill=tg_col, font=font_body)
        rx += 200
        # Col 5: Proxy J
        draw.text((rx, ry + 16), f"{row['proxy_j']:.2f}", fill=(201, 209, 217), font=font_body)
        rx += 200
        # Col 6: Proxy Gain
        pg_col = (126, 231, 135) if row['proxy_gain'] > 0 else (139, 148, 158)
        draw.text((rx, ry + 16), f"{row['proxy_gain']:+.3f}", fill=pg_col, font=font_body)
        rx += 200
        # Col 7: Status
        status_txt = "★ 孪生选择 / 代理 M₁ 参照" if is_best else ("基准对比" if act == "A0" else "候选动作")
        st_col = (255, 215, 0) if is_best else (139, 148, 158)
        draw_text_with_subscript(draw, (rx, ry + 18), status_txt, font_small, font_sub_small, st_col)

        ry += 70

    # Note line under table (values read from decision_cards.txt)
    a3_pg = next(r['proxy_gain'] for r in card_data if r['action'] == 'A3')
    a4_pg = next(r['proxy_gain'] for r in card_data if r['action'] == 'A4')
    note_line = f"孪生在 R₁ 选 A3，代理在 M₁ 选 A3 作为审计参照；表中收益在 R₂/M₂ 评估。M₂ 中 A4 实现收益（{a4_pg:.2f}）高于 A3（{a3_pg:.2f}），遗憾为 0 仅因两边选中的动作相同。"
    draw_text_with_subscript(draw, (tbl_x0 + 40, ry + 6), note_line, font_small, font_sub_small, (240, 180, 100))

    # Summary stat pills at bottom
    sy = ry + 42
    stat_items = [
        ("孪生选择 a*", "A3", (88, 166, 255)),
        ("代理 M₁ 参照", "A3", (126, 231, 135)),
        ("预测收益 G_T(a*)", "+7.526 veh·h", (88, 166, 255)),
        ("代理实现收益 G_P(a*)", "+4.451 veh·h", (126, 231, 135)),
        ("种子 4501 BEE", "+3.076 veh·h (高估)", (240, 136, 62)),
        ("种子 4501 遗憾", "0.000 veh·h (两边选同)", (126, 231, 135)),
    ]
    sx = tbl_x0 + 40
    for idx, (label, val, col) in enumerate(stat_items):
        draw.rounded_rectangle([(sx, sy), (sx + 260, sy + 75)], radius=8, fill=(22, 27, 34), outline=(48, 54, 61), width=1)
        draw_text_with_subscript(draw, (sx + 15, sy + 10), label, font_small, font_sub_small, (139, 148, 158))
        draw.text((sx + 15, sy + 38), val, fill=col, font=font_body)
        sx += 285

    # Caption
    if f_idx < 2490 + 600:
        draw_caption(draw, [
            "离线决策审计评估A0至A4共5种交通控制动作；",
            "种子 4501：孪生与代理世界的 M₁ 参照都选择 A3。"
        ])
    else:
        draw_caption(draw, [
            "种子 4501：孪生选出了与参照一致的动作；",
            "但高估了收益（种子 4501：BEE=+3.08车·时，遗憾=0）。"
        ])

    return im


def draw_segment5(f_idx):
    # Segment 5: Frozen Audit Summary (40 s, frames 3690 to 4890)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    # Header bar
    draw.rectangle([(0, 0), (W, 75)], fill=(18, 24, 35))
    draw.line([(0, 75), (W, 75)], fill=(48, 54, 61), width=1)
    draw.text((60, 22), "冻结测试审计汇总（8个全新测试种子，设计冻结后只运行一次）", fill=(255, 255, 255), font=font_title)

    # Sub-phase: 0-20s (figures) vs 20-40s (stat cards)
    in_seg_f = f_idx - 3690
    m = DATA["metrics"]

    if in_seg_f < 600:
        # Show Fig 1 & Fig 3 from final/figures
        card_w, card_h = 860, 680
        # Left card: fig1
        draw.rounded_rectangle([(60, 100), (60 + card_w, 100 + card_h + 90)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
        draw.text((80, 115), "图1：开发审计 vs 冻结测试 BEE 收益估计误差分布", fill=(88, 166, 255), font=font_title)
        draw.text((80, 150), "来源: final/figures/fig1_bee_dev_vs_frozen.png", fill=(139, 148, 158), font=font_small)
        f1_scaled = fig1_img.resize((card_w - 40, card_h - 80), Image.Resampling.LANCZOS)
        im.paste(f1_scaled, (80, 185))

        # Right card: fig3
        draw.rounded_rectangle([(1000, 100), (1000 + card_w, 100 + card_h + 90)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
        draw.text((1020, 115), "图3：各动作相对无动作的收益：孪生预测与实际（A1–A4）", fill=(88, 166, 255), font=font_title)
        draw.text((1020, 150), "来源: final/figures/fig3_action_gains.png", fill=(139, 148, 158), font=font_small)
        f3_scaled = fig3_img.resize((card_w - 40, card_h - 80), Image.Resampling.LANCZOS)
        im.paste(f3_scaled, (1020, 185))

        draw_caption(draw, [
            "冻结测试复现了开发审计在本场景中的规律；",
            "A3获选8/8，与事后最优一致7/8，收益被高估。"
        ])
    else:
        # 4 Stat Cards from metrics.json
        card_w, card_h = 840, 340
        coords = [
            (80, 110),
            (1000, 110),
            (80, 490),
            (1000, 490),
        ]
        
        cards = [
            ("A3 选择次数", m["a_star_ratio"], f"Top-1 一致：{m['oracle_agree_ratio']}", "8 个冻结测试种子全部选择动作 A3", (88, 166, 255)),
            ("收益估计误差 (Benefit Error BEE)", f"{m['bee_val']} 车·时", f"95% 置信区间: {m['bee_ci']} 车·时", f"相对无动作总通行时间：{m['bee_rel']}（不是相对收益）", (240, 136, 62)),
            ("分拆决策遗憾 (Split Regret)", f"{m['regret_val']} 车·时", f"95% 置信区间: {m['regret_ci']} 车·时", "遗憾接近零（相对在 M₁ 上选出的事后最优）", (126, 231, 135)),
            ("动作排序一致性 (Ranking Spearman)", m["spearman_val"], f"95% 置信区间: {m['spearman_ci']}", "Kendall τ = 0.675", (187, 128, 179)),
        ]

        for (cx, cy), (title, val, line1, line2, col) in zip(coords, cards):
            draw.rounded_rectangle([(cx, cy), (cx + card_w, cy + card_h)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
            draw.text((cx + 40, cy + 30), title, fill=(139, 148, 158), font=font_title)
            draw.text((cx + 40, cy + 85), val, fill=col, font=font_huge)
            draw.line([(cx + 40, cy + 175), (cx + card_w - 40, cy + 175)], fill=(33, 45, 65), width=2)
            draw_text_with_subscript(draw, (cx + 40, cy + 200), "• " + line1, font_body, font_sub_body, (201, 209, 217))
            draw_text_with_subscript(draw, (cx + 40, cy + 250), "• " + line2, font_body, font_sub_body, (139, 148, 158))

        draw_caption(draw, [
            "冻结测试收益被高估（BEE=+2.16车·时）；",
            "决策排序强相关（Spearman=0.825），遗憾近零。"
        ])

    return im


def draw_segment6(f_idx):
    # Segment 6: Limitations (20 s, frames 4890 to 5490)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    # Header bar
    draw.rectangle([(0, 0), (W, 75)], fill=(18, 24, 35))
    draw.line([(0, 75), (W, 75)], fill=(48, 54, 61), width=1)
    draw.text((60, 22), "局限性与有效性边界声明（CLAIMS.md §b 严格对照）", fill=(255, 255, 255), font=font_title)

    # 4 Limitation Cards
    cards_data = [
        ("1. 场景与事故类型单一", "本研究仅验证单一合成走廊（观塘绕道走廊）及单一类型事故，测试集仅覆盖 8 个冻结种子。", (240, 136, 62)),
        ("2. 审计事故信念为给定假设", "冻结测试评估的是强加给定信念（Belief B）的常规孪生，而非算法在线自然推断事故所得。", (240, 136, 62)),
        ("3. 运行状态覆盖局限", "新开发运行无自然解除、恢复或降级覆盖（强制试验另列）；6 个事故运行中 0 个自然采纳事故假设。", (248, 81, 73)),
        ("4. 同化标定与部署边界", "常规同化未通过资格检验，温度系数与阈值未标定；不外推至真实道路或声称部署就绪。", (210, 153, 34)),
    ]

    card_y = 120
    for title, desc, col in cards_data:
        draw.rounded_rectangle([(100, card_y), (W - 100, card_y + 150)], radius=12, fill=(18, 24, 35), outline=(48, 54, 61), width=1)
        # Left color bar
        draw.rounded_rectangle([(100, card_y), (115, card_y + 150)], radius=4, fill=col)
        draw.text((140, card_y + 25), title, fill=col, font=font_title)
        draw.text((140, card_y + 80), desc, fill=(201, 209, 217), font=font_body)
        card_y += 180

    draw_caption(draw, [
        "遵循学术严谨性，公开四大方法局限；",
        "本原型仅用于实验室验证，不得外推至真实道路。"
    ])

    return im


def draw_segment7(f_idx):
    # Segment 7: End (5 s, frames 5490 to 5640)
    im = Image.new("RGB", (W, H), (13, 17, 23))
    draw = ImageDraw.Draw(im)
    draw_dark_background(im, draw)

    t1 = "《城脉·涟控》"
    t2 = "交通数字孪生实验室原型"
    t3 = "实验室验证原型 · 完"

    b1 = font_huge.getbbox(t1)
    b2 = font_large.getbbox(t2)
    b3 = font_body.getbbox(t3)

    draw.text(((W - (b1[2] - b1[0])) // 2, 380), t1, fill=(255, 255, 255), font=font_huge)
    draw.text(((W - (b2[2] - b2[0])) // 2, 480), t2, fill=(88, 166, 255), font=font_large)
    draw.text(((W - (b3[2] - b3[0])) // 2, 590), t3, fill=(139, 148, 158), font=font_body)

    return im


def get_frame(f_idx):
    if f_idx < 240:
        im = draw_segment1(f_idx)
    elif f_idx < 1440:
        im = draw_segment2(f_idx)
    elif f_idx < 2490:
        im = draw_segment3(f_idx)
    elif f_idx < 3690:
        im = draw_segment4(f_idx)
    elif f_idx < 4890:
        im = draw_segment5(f_idx)
    elif f_idx < 5490:
        im = draw_segment6(f_idx)
    else:
        im = draw_segment7(f_idx)

    if f_idx >= 240:
        draw = ImageDraw.Draw(im)
        draw_corner_badge(draw)
    return im


def export_check_frames():
    print("Exporting check frames to submission/video/frames_check/...")
    check_specs = [
        ("check_01_title.png", 120),
        ("check_02_twoworlds_5150.png", 340),
        ("check_02_twoworlds_5450.png", 940),
        ("check_03_eventlog.png", 1800),
        ("check_03_eventlog_end.png", 2400),
        ("check_04_decision_early.png", 2800),
        ("check_04_decision_late.png", 3300),
        ("check_05_audit_figures.png", 3900),
        ("check_05_audit_cards.png", 4500),
        ("check_06_limitations.png", 5100),
        ("check_07_end.png", 5550),
    ]
    for filename, frame_num in check_specs:
        img = get_frame(frame_num)
        out_p = CHECK_DIR / filename
        img.save(out_p, "PNG")
        print(f"  Saved {out_p.name} (frame {frame_num})")


def render_preview_video(out_mp4, preview_fps=15, scale=0.5):
    print(f"Rendering low-resolution preview to {out_mp4}...")
    vw, vh = int(W * scale), int(H * scale)
    writer = imageio.get_writer(
        str(out_mp4),
        fps=preview_fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=None,
    )
    # Step every 2 frames for 15 fps
    step = int(FPS / preview_fps)
    t0 = time.time()
    for f in range(0, TOTAL_FRAMES, step):
        img = get_frame(f).resize((vw, vh), Image.Resampling.BILINEAR)
        writer.append_data(np.array(img))
        if f % (FPS * 20) == 0:
            print(f"  Preview rendered {f / TOTAL_FRAMES * 100:.1f}% ({f}/{TOTAL_FRAMES})...")
    writer.close()
    print(f"Preview video completed in {time.time() - t0:.1f} s!")


def render_full_video(out_mp4):
    print(f"Rendering FULL 1080p 30 fps video to {out_mp4}...")
    writer = imageio.get_writer(
        str(out_mp4),
        fps=FPS,
        codec="libx264",
        quality=9,
        pixelformat="yuv420p",
        macro_block_size=None,
    )
    t0 = time.time()
    for f in range(TOTAL_FRAMES):
        img = get_frame(f)
        writer.append_data(np.array(img))
        if f % (FPS * 15) == 0:
            print(f"  1080p rendered {f / TOTAL_FRAMES * 100:.1f}% ({f}/{TOTAL_FRAMES}) in {time.time() - t0:.1f} s...")
    writer.close()
    print(f"Full 1080p video completed in {time.time() - t0:.1f} s!")


if __name__ == "__main__":
    t_start = time.time()
    export_check_frames()
    
    # Render preview
    preview_path = VIDEO_DIR / "citypulse_preview_540p.mp4"
    render_preview_video(preview_path, preview_fps=15, scale=0.5)

    # Render full 1080p video
    final_path = VIDEO_DIR / "citypulse_demo_1080p.mp4"
    render_full_video(final_path)

    print(f"All rendering finished in {time.time() - t_start:.1f} s!")
