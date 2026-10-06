/**
 * build_deck.js — 《城脉·涟控》competition deck builder.
 *
 * Content source : submission/03_PPT大纲.md  (slide-by-slide, Chinese)
 * Numbers        : final/CLAIMS.md (results) + final/demo/decision_cards.txt (slide 7 only)
 * Figures        : submission/figures/fig1_bee_dev_vs_frozen.png, fig3_action_gains.png,
 *                  fig4_missing_queue.png, fig5_queue_at_decision_time.png (print-resolution copies
 *                  of the final/figures set)
 * Output         : submission/03_答辩PPT.pptx
 *
 * Re-runnable: running it again rebuilds the file from scratch. Speaker notes are
 * taken from submission/04_演讲稿.md when that file exists (### 第N页 headings);
 * otherwise every slide is written with empty notes.
 *
 * Usage: npm ci          (restores pptxgenjs from package-lock.json; node_modules/ is not shipped)
 *        node build_deck.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const PptxGenJS = require('pptxgenjs');

const DECK_DIR = __dirname;
const SUBMISSION_DIR = path.resolve(DECK_DIR, '..');
const ROOT_DIR = path.resolve(SUBMISSION_DIR, '..');
const OUT_FILE = path.join(SUBMISSION_DIR, '03_答辩PPT.pptx');
// The five figures are produced by final/figures/generate_figures.py. The submitted copies live in
// submission/figures/ at print resolution (160 dpi, the resolution the earlier deck used); the
// working-tree copies under final/figures/ are the same pictures at the generator's default 72 dpi,
// so the deck embeds the print-resolution set to stay legible when projected.
const FIG_DIR = path.join(SUBMISSION_DIR, 'figures');
const NOTES_FILE = path.join(SUBMISSION_DIR, '04_演讲稿.md');

/* ------------------------------------------------------------------ theme */

// Colours are 6-digit hex WITHOUT '#'. Blue = Twin, green = Proxy: same meaning
// as in final/figures/*.
const THEME = {
  fontHead: 'Microsoft YaHei',
  fontBody: 'Microsoft YaHei',
  navy: '1B2A41', // dominant dark navy (dark slides, headings)
  light: 'FFFFFF', // light background
  ink: '1B2A41', // body text on light
  muted: '5A6475', // muted text on light
  amber: 'F2A541', // accent
  twin: '2A78D6', // data blue  — Twin
  proxy: '1BAF7A', // data green — Proxy
  surface: 'F4F6F9', // card fill on light
  surfaceDark: '22334C', // card fill on navy
  line: 'D8DEE7', // hairline borders on light
  onDark: 'EAF0F8', // primary text on navy
  onDarkMuted: '9FB0C7', // secondary text on navy
};

const FOOTER_TEXT = '《城脉·涟控》· 实验室原型 · 合成场景';

// Geometry (LAYOUT_WIDE = 13.33" x 7.5")
const PAGE_W = 13.33;
const PAGE_H = 7.5;
const M = 0.5; // 0.5" margins
const CW = PAGE_W - 2 * M; // 12.33
const BODY_TOP = 1.45;
const BODY_BOTTOM = 6.85;
const FOOTER_Y = 6.95;

const NOTES = loadNotes();

/* ---------------------------------------------------------------- helpers */

/** Load per-slide speaker notes from 04_演讲稿.md (### 第N页 …) when present. */
function loadNotes() {
  const map = {};
  if (!fs.existsSync(NOTES_FILE)) return map;
  const md = fs.readFileSync(NOTES_FILE, 'utf8').replace(/\r\n/g, '\n');
  // Split at every Markdown heading, so a page's notes end at the next heading of *any* level.
  // Splitting only on "### 第N页" made the last page swallow the "## 答辩预案" appendix that
  // follows it (Q&A text and its ** markers ended up in slide 14's notes).
  const parts = md.split(/^(#{1,6})\s*(.*)$/m);
  // parts = [preamble, hashes, title, body, hashes, title, body, ...]
  for (let i = 1; i + 2 < parts.length; i += 3) {
    const m = /^第(\d+)页/.exec(parts[i + 1].trim());
    if (m) map[parseInt(m[1], 10)] = parts[i + 2].trim();
  }
  return map;
}

/** Fresh text options every call (never share option objects between calls). */
function tOpts(o) {
  const base = {
    fontFace: THEME.fontBody,
    color: THEME.ink,
    fontSize: 16,
    margin: 0,
    valign: 'middle',
    align: 'left',
    isTextBox: true,
    shadow: { type: 'none' },
  };
  return Object.assign(base, o || {});
}

/** addText wrapper: always a text box (never a placeholder). */
function txt(slide, text, o) {
  slide.addText(text, tOpts(o));
}

/** Rounded card. */
function card(slide, x, y, w, h, o) {
  const opt = o || {};
  slide.addShape(pres.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: opt.radius === undefined ? 0.06 : opt.radius,
    fill: { color: opt.fill || THEME.surface },
    line: { color: opt.line || THEME.line, width: opt.lineWidth === undefined ? 1 : opt.lineWidth },
    shadow: { type: 'none' },
  });
}

/** Flow box (rounded rect + centred text). */
function flowBox(slide, x, y, w, h, text, o) {
  const opt = o || {};
  slide.addShape(pres.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: opt.fill || THEME.surface },
    line: { color: opt.line || THEME.line, width: 1 },
    shadow: { type: 'none' },
  });
  txt(slide, text, {
    x: x + 0.12,
    y: y + 0.05,
    w: w - 0.24,
    h: h - 0.1,
    fontSize: opt.fontSize || 16,
    bold: !!opt.bold,
    color: opt.color || THEME.ink,
    align: opt.align || 'center',
    valign: 'middle',
    lineSpacingMultiple: 1.1,
  });
}

/** Horizontal arrow between flow boxes. */
function hArrow(slide, x, y, w, h, color) {
  const c = color || THEME.amber;
  slide.addShape(pres.ShapeType.rightArrow, {
    x,
    y,
    w,
    h,
    fill: { color: c },
    line: { color: c, width: 0.75 },
    shadow: { type: 'none' },
  });
}

/** Vertical (down) arrow between flow boxes. */
function vArrow(slide, x, y, w, h, color) {
  const c = color || THEME.amber;
  slide.addShape(pres.ShapeType.downArrow, {
    x,
    y,
    w,
    h,
    fill: { color: c },
    line: { color: c, width: 0.75 },
    shadow: { type: 'none' },
  });
}

/** Stat card: big value over a caption (or value left / caption right). */
function statCard(slide, x, y, w, h, value, label, o) {
  const opt = o || {};
  card(slide, x, y, w, h, { fill: opt.fill || THEME.surface, line: opt.line || THEME.line });
  const side = opt.side === true;
  if (side) {
    txt(slide, value, {
      x: x + 0.16,
      y: y + 0.06,
      w: w * 0.4,
      h: h - 0.12,
      fontSize: opt.valueSize || 26,
      bold: true,
      color: opt.accent || THEME.ink,
      align: 'left',
      valign: 'middle',
    });
    txt(slide, label, {
      x: x + w * 0.44,
      y: y + 0.06,
      w: w * 0.54,
      h: h - 0.12,
      fontSize: opt.labelSize || 13,
      color: THEME.muted,
      align: 'left',
      valign: 'middle',
      lineSpacingMultiple: 1.05,
    });
  } else {
    txt(slide, value, {
      x: x + 0.14,
      y: y + 0.1,
      w: w - 0.28,
      h: h * 0.55,
      fontSize: opt.valueSize || 34,
      bold: true,
      color: opt.accent || THEME.ink,
      align: 'center',
      valign: 'middle',
    });
    txt(slide, label, {
      x: x + 0.14,
      y: y + h * 0.56,
      w: w - 0.28,
      h: h * 0.38,
      fontSize: opt.labelSize || 14,
      color: THEME.muted,
      align: 'center',
      valign: 'middle',
      lineSpacingMultiple: 1.05,
    });
  }
}

/** Small chip (rounded rect + one line). */
function chip(slide, x, y, w, h, text, o) {
  const opt = o || {};
  card(slide, x, y, w, h, { fill: opt.fill || THEME.surface, line: opt.line || THEME.line, radius: 0.5 });
  txt(slide, text, {
    x: x + 0.1,
    y: y + 0.04,
    w: w - 0.2,
    h: h - 0.08,
    fontSize: opt.fontSize || 14,
    bold: !!opt.bold,
    color: opt.color || THEME.ink,
    align: 'center',
    valign: 'middle',
  });
}

/** Bulleted body list (bullet + breakLine, one paragraph per item). */
function bullets(slide, items, o) {
  const opt = o || {};
  const runs = items.map((t) => ({ text: t, options: { bullet: true, breakLine: true } }));
  slide.addText(runs, tOpts({
    x: opt.x,
    y: opt.y,
    w: opt.w,
    h: opt.h,
    fontSize: opt.fontSize || 16,
    color: opt.color || THEME.ink,
    valign: 'top',
    align: 'left',
    lineSpacingMultiple: opt.lineSpacingMultiple || 1.25,
    paraSpaceAfter: opt.paraSpaceAfter === undefined ? 10 : opt.paraSpaceAfter,
  }));
}

/** Table helper: rows = [[{text,options}...]], opts = {x,y,w,colW,rowH,...}. */
function table(slide, rows, o) {
  const opt = o || {};
  slide.addTable(rows, {
    x: opt.x,
    y: opt.y,
    w: opt.w,
    colW: opt.colW,
    rowH: opt.rowH,
    fontFace: THEME.fontBody,
    fontSize: opt.fontSize || 14,
    color: THEME.ink,
    valign: 'middle',
    align: 'left',
    margin: 0.06,
    border: { type: 'solid', pt: 1, color: THEME.line },
    fill: { color: THEME.light },
    autoPage: false,
  });
}

/** Figure + caption. The caption doubles as the picture alt-text, so no absolute path is
 *  stored in `descr` (anonymity: the deck must not carry build-machine paths). */
function figure(slide, file, x, y, w, caption) {
  const h = w / file.ratio;
  slide.addImage({ path: file.path, x, y, w, h, altText: caption || path.basename(file.path) });
  if (caption) {
    txt(slide, caption, {
      x,
      y: y + h + 0.05,
      w,
      h: 0.3,
      fontSize: 11,
      color: THEME.muted,
      align: 'center',
      valign: 'top',
    });
  }
  return h;
}

/** True pixel size of a PNG, read from the IHDR chunk (no hard-coded aspect ratios: a
 *  regenerated figure keeps its own proportions instead of being stretched). */
function pngSize(file) {
  const buf = fs.readFileSync(file);
  if (buf.length < 24 || buf.readUInt32BE(0) !== 0x89504e47) {
    throw new Error('not a PNG: ' + file);
  }
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

function fig(file) {
  const p = path.join(FIG_DIR, file);
  const size = pngSize(p);
  return { path: p, ratio: size.w / size.h };
}

/* --------------------------------------------------------------- document */

const pres = new PptxGenJS();
pres.layout = 'LAYOUT_WIDE'; // 13.33" x 7.5"
pres.author = ''; // no personal / school information anywhere
pres.company = '';
pres.subject = '';
pres.title = '《城脉·涟控》';
pres.revision = '1';
pres.theme = { headFontFace: THEME.fontHead, bodyFontFace: THEME.fontBody, lang: 'zh-CN' };

// --- layouts: one per frame kind -------------------------------------------
// TITLE   : dark hero cover (slide 1)
// CONTENT : light frame, title-only placeholder (slides 2-13)
// SECTION : dark frame, title-only placeholder (slide 14)
pres.defineSlideMaster({
  title: 'TITLE',
  background: { color: THEME.navy },
  objects: [
    {
      placeholder: {
        options: { name: 'title', type: 'title', x: 0.9, y: 2.2, w: 11.53, h: 1.1 },
        text: '',
      },
    },
    {
      placeholder: {
        options: { name: 'subtitle', type: 'body', x: 0.9, y: 3.5, w: 11.53, h: 0.8 },
        text: '',
      },
    },
    {
      text: {
        text: FOOTER_TEXT,
        options: {
          x: M,
          y: FOOTER_Y,
          w: 9.5,
          h: 0.34,
          fontFace: THEME.fontBody,
          fontSize: 11,
          color: THEME.onDarkMuted,
          align: 'left',
          valign: 'middle',
          isTextBox: true,
        },
      },
    },
  ],
  slideNumber: {
    x: 11.83,
    y: FOOTER_Y,
    w: 1.0,
    h: 0.34,
    fontFace: THEME.fontBody,
    fontSize: 11,
    color: THEME.onDarkMuted,
    align: 'right',
    valign: 'middle',
  },
});

pres.defineSlideMaster({
  title: 'CONTENT',
  background: { color: pres.SchemeColor.background1 }, // theme bg1 = FFFFFF
  objects: [
    {
      placeholder: {
        options: { name: 'title', type: 'title', x: M, y: 0.38, w: CW, h: 0.85 },
        text: '',
      },
    },
    {
      text: {
        text: FOOTER_TEXT,
        options: {
          x: M,
          y: FOOTER_Y,
          w: 9.5,
          h: 0.34,
          fontFace: THEME.fontBody,
          fontSize: 11,
          color: THEME.muted,
          align: 'left',
          valign: 'middle',
          isTextBox: true,
        },
      },
    },
  ],
  slideNumber: {
    x: 11.83,
    y: FOOTER_Y,
    w: 1.0,
    h: 0.34,
    fontFace: THEME.fontBody,
    fontSize: 11,
    color: THEME.muted,
    align: 'right',
    valign: 'middle',
  },
});

pres.defineSlideMaster({
  title: 'SECTION',
  background: { color: THEME.navy },
  objects: [
    {
      placeholder: {
        options: { name: 'title', type: 'title', x: M, y: 0.38, w: CW, h: 0.85 },
        text: '',
      },
    },
    {
      text: {
        text: FOOTER_TEXT,
        options: {
          x: M,
          y: FOOTER_Y,
          w: 9.5,
          h: 0.34,
          fontFace: THEME.fontBody,
          fontSize: 11,
          color: THEME.onDarkMuted,
          align: 'left',
          valign: 'middle',
          isTextBox: true,
        },
      },
    },
  ],
  slideNumber: {
    x: 11.83,
    y: FOOTER_Y,
    w: 1.0,
    h: 0.34,
    fontFace: THEME.fontBody,
    fontSize: 11,
    color: THEME.onDarkMuted,
    align: 'right',
    valign: 'middle',
  },
});

// --- slide factory ---------------------------------------------------------
// pptxgenjs only files a slide under a *named* section when addSlide() is given
// that section's title, so every slide is created through addSlideIn().
const slides = [];
let CURRENT_SECTION = '';
function useSection(title) {
  pres.addSection({ title });
  CURRENT_SECTION = title;
}
function addSlideIn(masterName) {
  return pres.addSlide({ masterName, sectionTitle: CURRENT_SECTION });
}
function lightSlide(title, section) {
  if (section) useSection(section);
  const s = addSlideIn('CONTENT');
  s.addText(title, {
    placeholder: 'title',
    fontFace: THEME.fontHead,
    fontSize: 34,
    bold: true,
    color: THEME.ink,
    align: 'left',
    valign: 'middle',
    margin: 0,
  });
  slides.push(s);
  return s;
}

// Aspect ratios are read from each PNG's IHDR, so a regenerated figure is never stretched.
const FIG1 = fig('fig1_bee_dev_vs_frozen.png');
const FIG3 = fig('fig3_action_gains.png');
const FIG4 = fig('fig4_missing_queue.png');
const FIG5 = fig('fig5_queue_at_decision_time.png');

/* =========================================================== 1 · cover === */
useSection('开篇');
{
  const s = addSlideIn('TITLE');
  s.addText('《城脉·涟控》', {
    placeholder: 'title',
    fontFace: THEME.fontHead,
    fontSize: 40,
    bold: true,
    color: THEME.light,
    align: 'center',
    valign: 'middle',
    margin: 0,
  });
  s.addText('面向突发事件与模型失配的事件感知交通数字孪生', {
    placeholder: 'subtitle',
    fontFace: THEME.fontHead,
    fontSize: 22,
    color: THEME.onDark,
    align: 'center',
    valign: 'middle',
    margin: 0,
  });
  txt(s, '实验室验证级原型 · 第十二届中国研究生智慧城市技术与创意设计大赛', {
    x: 0.9,
    y: 4.42,
    w: 11.53,
    h: 0.45,
    fontSize: 15,
    color: THEME.onDarkMuted,
    align: 'center',
    valign: 'middle',
  });
  const chips = ['事件感知双模同化', '结构失配下的反事实管控', '决策保真度审计'];
  const chipW = 3.6;
  const chipGap = 0.36;
  chips.forEach((t, i) => {
    const x = 0.9 + i * (chipW + chipGap);
    s.addShape(pres.ShapeType.roundRect, {
      x,
      y: 5.25,
      w: chipW,
      h: 0.85,
      rectRadius: 0.12,
      fill: { color: THEME.surfaceDark },
      line: { color: [THEME.twin, THEME.proxy, THEME.amber][i], width: 1.25 },
      shadow: { type: 'none' },
    });
    txt(s, t, {
      x: x + 0.12,
      y: 5.3,
      w: chipW - 0.24,
      h: 0.75,
      fontSize: 16,
      bold: true,
      color: THEME.onDark,
      align: 'center',
      valign: 'middle',
    });
  });
  slides.push(s);
}

/* ======================================================= 2 · problem ===== */
{
  const s = lightSlide('问题：需求同化可能掩盖事故失配');
  card(s, M, 1.5, CW, 0.95, { fill: THEME.surface });
  txt(s, '稀疏观测下，需求变化与通行能力损失可能混淆', {
    x: M + 0.2,
    y: 1.55,
    w: CW - 0.4,
    h: 0.85,
    fontSize: 21,
    bold: true,
    color: THEME.ink,
    align: 'center',
    valign: 'middle',
  });

  const steps = ['通行能力骤降', '下游流量下降', '孪生可能压低需求', '可能遗漏事故排队历史'];
  const bw = 2.75;
  const aw = 0.4;
  const x0 = M + (CW - (4 * bw + 3 * aw)) / 2;
  const by = 2.85;
  const bh = 1.75;
  steps.forEach((t, i) => {
    const x = x0 + i * (bw + aw);
    flowBox(s, x, by, bw, bh, t, { fontSize: 17, fill: THEME.light, line: THEME.line });
    txt(s, String(i + 1), {
      x: x + 0.1,
      y: by + 0.08,
      w: 0.5,
      h: 0.34,
      fontSize: 14,
      bold: true,
      color: THEME.amber,
      align: 'left',
      valign: 'middle',
    });
    if (i < 3) hArrow(s, x + bw + 0.02, by + bh / 2 - 0.18, aw - 0.04, 0.36);
  });

  txt(s, '因此动作选择与收益预测是否可信，需要分别审计', {
    x: M,
    y: 5.05,
    w: CW,
    h: 0.7,
    fontSize: 19,
    color: THEME.muted,
    align: 'center',
    valign: 'middle',
  });
}

/* ============================================ 3 · two deliberately worlds = */
{
  const s = lightSlide('我们的思路：两个刻意不同的世界', '方法与系统');
  const colY = 1.5;
  const colH = 4.35;

  // left: hidden real world (Proxy)
  card(s, M, colY, 4.25, colH, { fill: THEME.light });
  s.addShape(pres.ShapeType.roundRect, {
    x: M,
    y: colY,
    w: 4.25,
    h: 0.68,
    rectRadius: 0.06,
    fill: { color: THEME.proxy },
    line: { color: THEME.proxy, width: 0.75 },
    shadow: { type: 'none' },
  });
  txt(s, '隐藏的现实世界（Proxy）', {
    x: M + 0.12,
    y: colY + 0.04,
    w: 4.01,
    h: 0.6,
    fontSize: 17,
    bold: true,
    color: THEME.light,
    align: 'center',
    valign: 'middle',
  });
  bullets(s, ['IDM 驾驶模型', '路径文件需求', '内含一起事故：ktb_n1 900 米处\n两条车道封闭 15 分钟', 'VMS 服从率真值 0.35'], {
    x: M + 0.2,
    y: colY + 0.85,
    w: 3.85,
    h: colH - 1.0,
    fontSize: 14,
  });

  // right: digital twin
  card(s, 8.58, colY, 4.25, colH, { fill: THEME.light });
  s.addShape(pres.ShapeType.roundRect, {
    x: 8.58,
    y: colY,
    w: 4.25,
    h: 0.68,
    rectRadius: 0.06,
    fill: { color: THEME.twin },
    line: { color: THEME.twin, width: 0.75 },
    shadow: { type: 'none' },
  });
  txt(s, '数字孪生（Twin）', {
    x: 8.7,
    y: colY + 0.04,
    w: 4.01,
    h: 0.6,
    fontSize: 17,
    bold: true,
    color: THEME.light,
    align: 'center',
    valign: 'middle',
  });
  bullets(s, ['Krauss 驾驶模型', '泊松稀疏化需求与常规同化', 'VMS 服从率假设 0.30'], {
    x: 8.78,
    y: colY + 0.85,
    w: 3.85,
    h: colH - 1.0,
    fontSize: 14,
  });

  // middle: only detector messages
  card(s, 5.0, colY, 3.33, colH, { fill: THEME.surface });
  txt(s, '只有检测器消息', {
    x: 5.1,
    y: colY + 0.06,
    w: 3.13,
    h: 0.55,
    fontSize: 15,
    bold: true,
    color: THEME.ink,
    align: 'center',
    valign: 'middle',
  });
  hArrow(s, 5.3, colY + 0.72, 2.73, 0.36);
  bullets(s, ['14/21 个检测器', '30 秒流量、速度、占有率', '带噪声', '5% 丢包'], {
    x: 5.12,
    y: colY + 1.25,
    w: 3.09,
    h: colH - 1.45,
    fontSize: 14,
    paraSpaceAfter: 8,
  });

  card(s, M, 6.05, CW, 0.75, { fill: THEME.surface });
  txt(s, '路网几何与检测器取自香港运输署公开数据；需求为情景设定，不是标定复制品', {
    x: M + 0.2,
    y: 6.1,
    w: CW - 0.4,
    h: 0.65,
    fontSize: 14,
    color: THEME.muted,
    align: 'center',
    valign: 'middle',
  });
}

/* ================================================= 4 · three innovations == */
{
  const s = lightSlide('三项创新与它们的检验');
  const cards = [
    {
      n: '①',
      head: '事件感知双模同化',
      what: '20 个候选假设的回溯重放推断',
      res: '机制已验证，推断能力未达成',
      color: THEME.twin,
    },
    {
      n: '②',
      head: '结构失配下的反事实管控',
      what: '5 个动作在两个世界语义一致',
      res: '本场景中决策一致性得到复现',
      color: THEME.proxy,
    },
    {
      n: '③',
      head: '决策保真度审计',
      what: '预注册、冻结后只运行一次、三套独立实现复核',
      res: '本作品的主要证据',
      color: THEME.amber,
    },
  ];
  const cw = 3.91;
  const gap = 0.3;
  const cy = 1.5;
  const ch = 4.9;
  cards.forEach((c, i) => {
    const x = M + i * (cw + gap);
    card(s, x, cy, cw, ch, { fill: THEME.light });
    s.addShape(pres.ShapeType.roundRect, {
      x,
      y: cy,
      w: cw,
      h: 0.85,
      rectRadius: 0.06,
      fill: { color: c.color },
      line: { color: c.color, width: 0.75 },
      shadow: { type: 'none' },
    });
    txt(s, c.n + ' ' + c.head, {
      x: x + 0.12,
      y: cy + 0.06,
      w: cw - 0.24,
      h: 0.73,
      fontSize: 16,
      bold: true,
      color: THEME.light,
      align: 'center',
      valign: 'middle',
      lineSpacingMultiple: 1.05,
    });
    txt(s, '做了什么', {
      x: x + 0.22,
      y: cy + 1.0,
      w: cw - 0.44,
      h: 0.32,
      fontSize: 13,
      bold: true,
      color: c.color,
      align: 'left',
      valign: 'middle',
    });
    txt(s, c.what, {
      x: x + 0.22,
      y: cy + 1.32,
      w: cw - 0.44,
      h: 1.35,
      fontSize: 15,
      color: THEME.ink,
      align: 'left',
      valign: 'top',
      lineSpacingMultiple: 1.2,
    });
    txt(s, '结果如何', {
      x: x + 0.22,
      y: cy + 2.85,
      w: cw - 0.44,
      h: 0.32,
      fontSize: 13,
      bold: true,
      color: c.color,
      align: 'left',
      valign: 'middle',
    });
    txt(s, c.res, {
      x: x + 0.22,
      y: cy + 3.17,
      w: cw - 0.44,
      h: 1.5,
      fontSize: 15,
      color: THEME.ink,
      align: 'left',
      valign: 'top',
      lineSpacingMultiple: 1.2,
    });
  });
}

/* ================================================ 5 · how the engine works */
{
  const s = lightSlide('事件感知引擎怎样工作');
  const steps = [
    '触发：背离指数 ≥ 3，连续 2 次',
    '疑似事件：冻结需求',
    '20 个假设回溯重放评分',
    '采纳 / 误报 / 故障 / 降级',
    '事件同化',
    '解除',
    '恢复',
  ];
  const bx = M;
  const bw = 5.4;
  const bh = 0.58;
  const bgap = 0.2;
  steps.forEach((t, i) => {
    const y = BODY_TOP + i * (bh + bgap);
    card(s, bx, y, bw, bh, { fill: THEME.surface });
    s.addText(
      [
        { text: String(i + 1) + '  ', options: { bold: true, color: THEME.amber, fontSize: 14 } },
        { text: t, options: { color: THEME.ink, fontSize: 14 } },
      ],
      tOpts({ x: bx + 0.16, y: y + 0.04, w: bw - 0.32, h: bh - 0.08, align: 'left', valign: 'middle' })
    );
    if (i < steps.length - 1) vArrow(s, bx + bw / 2 - 0.14, y + bh + 0.01, 0.28, bgap - 0.02);
  });

  // right column: hypothesis library
  const rx = 6.2;
  const rw = 6.63;
  txt(s, '假设库：20 个候选', {
    x: rx,
    y: BODY_TOP,
    w: rw,
    h: 0.5,
    fontSize: 18,
    bold: true,
    color: THEME.ink,
    align: 'left',
    valign: 'middle',
  });
  const head = (t, al) => ({
    text: t,
    options: { bold: true, color: THEME.light, fill: { color: THEME.navy }, align: al, fontSize: 14 },
  });
  const cell = (t, al, o) => ({
    text: t,
    options: Object.assign({ align: al, fontSize: 14, color: THEME.ink, fill: { color: THEME.light } }, o || {}),
  });
  table(
    s,
    [
      [head('假设族', 'left'), head('数量', 'center'), head('先验', 'center')],
      [cell('事故', 'left'), cell('10', 'center'), cell('1/3', 'center')],
      [cell('需求', 'left'), cell('4', 'center'), cell('1/3', 'center')],
      [cell('检测器故障', 'left'), cell('6', 'center'), cell('1/3', 'center')],
    ],
    { x: rx, y: BODY_TOP + 0.6, w: rw, colW: [3.23, 1.7, 1.7], rowH: 0.62, fontSize: 14 }
  );
  txt(s, '三类假设族，先验均为 1/3', {
    x: rx,
    y: BODY_TOP + 3.15,
    w: rw,
    h: 0.4,
    fontSize: 12,
    color: THEME.muted,
    align: 'left',
    valign: 'middle',
  });
  statCard(s, rx, 5.05, rw, 1.5, '20', '候选假设，逐一回溯重放评分', { valueSize: 40, labelSize: 14 });
}

/* ================================================== 6 · engine reporting = */
{
  const s = lightSlide('事件引擎：如实报告');
  const cw = 3.91;
  const gap = 0.3;
  const cards = [
    { v: '13', l: '次疑似事件', c: THEME.twin },
    { v: '25', l: '次假设评估', c: THEME.amber },
    { v: '0/6', l: '6 个事故运行中 0 个自然采纳', c: THEME.proxy },
  ];
  cards.forEach((c, i) => {
    statCard(s, M + i * (cw + gap), 1.5, cw, 1.6, c.v, c.l, { valueSize: 40, labelSize: 15, accent: c.c });
  });
  bullets(
    s,
    [
      '强制采纳时，替换、解除、恢复流程完整运行；解除 3/3 过早，恢复 1/4 正常完成',
      '需求冲击（实际流量只增加 5–8%）与传感器卡死在正常读数都未触发报警；EVT 与 CONV 的排队预测相同',
      '离线回放诊断：改用点封堵并给出真实起始时刻后，会采纳的评估从 0/13 升到 6/13',
    ],
    { x: M + 0.1, y: 3.45, w: CW - 0.2, h: 3.0, fontSize: 17, paraSpaceAfter: 16 }
  );
}

/* ================================================= 7 · decision loop ===== */
{
  const s = lightSlide('决策环：五个动作的反事实推演');
  const head = (t, al) => ({
    text: t,
    options: { bold: true, color: THEME.light, fill: { color: THEME.navy }, align: al, fontSize: 14 },
  });
  const cell = (t, al, o) => ({
    text: t,
    options: Object.assign({ align: al, fontSize: 14, color: THEME.ink, fill: { color: THEME.light } }, o || {}),
  });
  const hl = { fill: { color: 'EAF1FB' }, bold: true, color: THEME.twin };
  table(
    s,
    [
      [head('动作', 'left'), head('含义', 'left'), head('孪生预测收益（车·时）', 'center'), head('代理世界实现收益（车·时）', 'center')],
      [cell('A0', 'left'), cell('无动作', 'left'), cell('0.00', 'center'), cell('0.00', 'center')],
      [cell('A1', 'left'), cell('事故信号预案', 'left'), cell('−0.09', 'center'), cell('0.11', 'center')],
      [cell('A2', 'left'), cell('VMS 诱导绕行', 'left'), cell('4.74', 'center'), cell('3.62', 'center')],
      [cell('A3', 'left', hl), cell('信号预案 + VMS', 'left', hl), cell('7.53', 'center', hl), cell('4.45', 'center', hl)],
      [cell('A4', 'left'), cell('加强 VMS', 'left'), cell('4.34', 'center'), cell('4.64', 'center')],
    ],
    { x: M, y: 1.5, w: CW, colW: [1.5, 5.0, 2.9, 2.93], rowH: 0.52, fontSize: 14 }
  );
  txt(s, '种子 4501：孪生在 R₁ 选 A3，代理世界在 M₁ 选 A3 作为审计参照；表中收益在 R₂/M₂ 评估。'
    + 'M₂ 中 A4 的实现收益（4.64）略高于 A3（4.45），遗憾为 0 仅因两边选中的动作相同；'
    + 'A3 预测收益 7.53，代理世界实现收益 4.45（车·时）', {
    x: M,
    y: 4.66,
    w: CW,
    h: 0.62,
    fontSize: 12,
    color: THEME.muted,
    align: 'left',
    valign: 'middle',
    lineSpacingMultiple: 1.15,
  });
  const cw = 6.0;
  const gap = 0.33;
  statCard(s, M, 5.35, cw, 1.0, 'R₁ 选 A3 · M₁ 参照 A3', '种子 4501：选择组与审计参照', {
    valueSize: 17,
    labelSize: 12,
    accent: THEME.twin,
  });
  statCard(s, M + cw + gap, 5.35, cw, 1.0, '7.53 / 4.45', '孪生预测收益 / 代理世界实现收益（车·时）', {
    valueSize: 19,
    labelSize: 12,
    accent: THEME.amber,
  });
  txt(s, '注：决策时刻 5,100 秒，评估时域 15 分钟，指标为总通行时间', {
    x: M,
    y: 6.4,
    w: CW,
    h: 0.4,
    fontSize: 12,
    color: THEME.muted,
    align: 'left',
    valign: 'middle',
  });
}

/* =================================================== 8 · audit protocol == */
{
  const s = lightSlide('审计协议：怎样检验孪生的建议', '审计协议与冻结结果');
  const steps = [
    '两个世界在同一决策时刻保存状态',
    '各自执行 5 个动作，使用公共随机数，选择用重复与评估用重复分开',
    '计算收益估计误差、决策遗憾、排序一致性、校准差异',
  ];
  const bw = 3.7;
  const aw = 0.6;
  steps.forEach((t, i) => {
    const x = M + i * (bw + aw);
    card(s, x, 1.6, bw, 2.0, { fill: THEME.surface });
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.18,
      y: 1.76,
      w: 0.5,
      h: 0.5,
      fill: { color: [THEME.twin, THEME.proxy, THEME.amber][i] },
      line: { color: [THEME.twin, THEME.proxy, THEME.amber][i], width: 0.75 },
      shadow: { type: 'none' },
    });
    txt(s, String(i + 1), {
      x: x + 0.18,
      y: 1.76,
      w: 0.5,
      h: 0.5,
      fontSize: 16,
      bold: true,
      color: THEME.light,
      align: 'center',
      valign: 'middle',
    });
    txt(s, t, {
      x: x + 0.2,
      y: 2.35,
      w: bw - 0.4,
      h: 1.1,
      fontSize: 15,
      color: THEME.ink,
      align: 'left',
      valign: 'top',
      lineSpacingMultiple: 1.2,
    });
    if (i < 2) hArrow(s, x + bw + 0.03, 1.6 + 1.0 - 0.18, aw - 0.06, 0.36);
  });
  card(s, M, 3.95, CW, 1.0, { fill: THEME.surface });
  txt(s, '公共随机数：选择用重复（R1）与评估用重复（R2）分开', {
    x: M + 0.2,
    y: 4.0,
    w: CW - 0.4,
    h: 0.9,
    fontSize: 16,
    color: THEME.ink,
    align: 'center',
    valign: 'middle',
  });
  txt(s, '流程保证', {
    x: M,
    y: 5.15,
    w: CW,
    h: 0.35,
    fontSize: 13,
    bold: true,
    color: THEME.muted,
    align: 'left',
    valign: 'middle',
  });
  const g = ['预注册', '设计冻结（2026-10-06）', '测试种子从未使用过', '只运行一次'];
  const gw = 2.9;
  const ggap = 0.24;
  g.forEach((t, i) => {
    chip(s, M + i * (gw + ggap), 5.6, gw, 0.8, t, { fontSize: 15, bold: true });
  });
}

/* ============================================== 9 · frozen test results == */
{
  const s = lightSlide('冻结测试结果（核心页）');
  const rows = [
    ['8/8', 'A3 选择'],
    ['7/8', '与事后最优一致'],
    ['+2.16', '收益估计误差 车·时 · 95% CI [1.74, 2.59]'],
    ['−0.03', '遗憾'],
    ['0.825', 'Spearman 排序一致性'],
  ];
  const cx = M;
  const cwid = 5.5;
  const chh = 0.84;
  const cgap = 0.14;
  rows.forEach((r, i) => {
    statCard(s, cx, 1.5 + i * (chh + cgap), cwid, chh, r[0], r[1], {
      side: true,
      valueSize: 24,
      labelSize: 14,
      accent: i === 2 ? THEME.amber : THEME.twin,
    });
  });

  const fh = figure(s, FIG1, 6.3, 1.5, 6.53, '图 1　开发审计与冻结测试的收益估计误差（BEE，车·时）');
  txt(s, '960/960 个分支成功；随机数隔离检验通过；三套独立实现复核，均值一致', {
    x: M,
    y: 6.45,
    w: CW,
    h: 0.4,
    fontSize: 12,
    color: THEME.muted,
    align: 'left',
    valign: 'middle',
  });
  void fh;
}

/* =========================================== 10 · right action, wrong gain */
{
  const s = lightSlide('动作排序一致，但收益被高估');
  figure(s, FIG3, M, 1.5, 6.2, '图 2　各动作收益：孪生预测与代理世界实现（车·时）');
  bullets(
    s,
    [
      '冻结集的平均动作收益在两个世界均以 A3 最高；逐种子选择一致 7/8',
      'A3 收益孪生预测 7.07，代理世界实现 4.90（车·时）',
      '校准差异 0.32 车·时，作为工具自身的噪声水平并列报告，不从误差中扣除',
    ],
    { x: 7.0, y: 1.55, w: 5.83, h: 2.1, fontSize: 16, paraSpaceAfter: 12 }
  );
  statCard(s, 7.0, 3.75, 5.83, 1.25, '7.07 → 4.90', 'A3 收益（车·时）：孪生预测 / 代理世界实现', {
    side: true,
    valueSize: 21,
    labelSize: 12,
    accent: THEME.twin,
  });
  statCard(s, 7.0, 5.15, 5.83, 1.25, '0.32 车·时', '校准差异：工具自身噪声水平，不从误差中扣除', {
    side: true,
    valueSize: 21,
    labelSize: 12,
    accent: THEME.proxy,
  });
}

/* ================================================= 11 · missing queue ==== */
{
  const s = lightSlide('为什么：缺失的排队历史');
  const fh = 2.7;
  const w5 = fh * FIG5.ratio;
  const w4 = fh * FIG4.ratio;
  const gap = 0.6;
  const x0 = M + (CW - (w5 + w4 + gap)) / 2;
  figure(s, FIG5, x0, 1.45, w5, '图 3　决策时刻状态（Proxy 有排队，Twin 为空）');
  figure(s, FIG4, x0 + w5 + gap, 1.45, w4, '图 4　缺失排队诊断：回放事故历史后的 A3 收益误差');
  bullets(
    s,
    [
      '决策时刻，代理世界走廊上有 7–24 辆停驶车辆，孪生为 0',
      '缺失排队诊断（4 个种子，真值辅助解除）：回放事故历史后，固定 A3 的绝对收益误差由 4.16 降至 0.90；完整动作排序未改善',
      '冻结 D300 对照：固定 A3 的孪生预测/代理收益为 0.21/4.90（不是 D300 所选动作的平均收益）',
    ],
    { x: M + 0.1, y: 4.55, w: CW - 0.2, h: 1.35, fontSize: 14, paraSpaceAfter: 8 }
  );
  card(s, M, 5.95, CW, 0.85, { fill: THEME.surface });
  txt(s, '解释：结果与“误差相互抵消”一致——孪生假设封堵持续，这部分抵消了它缺失的事故历史；尚未证明因果机制', {
    x: M + 0.2,
    y: 6.0,
    w: CW - 0.4,
    h: 0.75,
    fontSize: 15,
    color: THEME.ink,
    align: 'center',
    valign: 'middle',
  });
}

/* =========================================== 12 · frozen vs development = */
{
  const s = lightSlide('冻结测试与开发审计对照');
  const head = (t, al) => ({
    text: t,
    options: { bold: true, color: THEME.light, fill: { color: THEME.navy }, align: al, fontSize: 14 },
  });
  const cell = (t, al, o) => ({
    text: t,
    options: Object.assign({ align: al, fontSize: 14, color: THEME.ink, fill: { color: THEME.light } }, o || {}),
  });
  table(
    s,
    [
      [head('指标', 'left'), head('开发审计（种子 4201–4208）', 'center'), head('冻结测试（种子 4501–4508）', 'center')],
      [cell('A3 选择', 'left'), cell('8/8', 'center'), cell('8/8', 'center')],
      [cell('一致性', 'left'), cell('7/8', 'center'), cell('7/8', 'center')],
      [cell('收益估计误差（车·时）', 'left'), cell('+1.63 [1.04, 2.22]', 'center'), cell('+2.16 [1.74, 2.59]', 'center')],
      [cell('遗憾', 'left'), cell('0.03 [−0.04, 0.10]', 'center'), cell('−0.03 [−0.11, 0.05]', 'center')],
      [cell('Spearman', 'left'), cell('0.850', 'center'), cell('0.825', 'center')],
      [cell('校准差异', 'left'), cell('0.18 [0.08, 0.28]', 'center'), cell('0.32 [0.13, 0.50]', 'center')],
    ],
    { x: M, y: 1.5, w: CW, colW: [3.33, 4.5, 4.5], rowH: 0.55, fontSize: 14 }
  );
  card(s, M, 5.55, CW, 1.2, { fill: THEME.surface });
  txt(s, '冻结测试复现了本场景中的规律；+2.16 对 +1.63 等差别不能确定两组不同，两组不合并', {
    x: M + 0.2,
    y: 5.6,
    w: CW - 0.4,
    h: 1.1,
    fontSize: 17,
    bold: true,
    color: THEME.ink,
    align: 'center',
    valign: 'middle',
    lineSpacingMultiple: 1.15,
  });
}

/* ================================================== 13 · limits ========== */
{
  const s = lightSlide('局限与边界', '局限与展望');
  const items = [
    '单一合成走廊与事故类型，8 个测试种子',
    '审计中的事故信念是给定的，不是在线推断得到的',
    '引擎未自然采纳事故；新开发运行无自然解除、恢复或降级覆盖（强制试验另列）',
    '常规同化未通过资格检验，温度系数与阈值未标定',
  ];
  const rh = 0.95;
  const rgap = 0.15;
  items.forEach((t, i) => {
    const y = 1.5 + i * (rh + rgap);
    card(s, M, y, CW, rh, { fill: THEME.surface });
    s.addShape(pres.ShapeType.ellipse, {
      x: M + 0.25,
      y: y + 0.2,
      w: 0.55,
      h: 0.55,
      fill: { color: THEME.navy },
      line: { color: THEME.navy, width: 0.75 },
      shadow: { type: 'none' },
    });
    txt(s, '!', {
      x: M + 0.25,
      y: y + 0.2,
      w: 0.55,
      h: 0.55,
      fontSize: 18,
      bold: true,
      color: THEME.amber,
      align: 'center',
      valign: 'middle',
    });
    txt(s, t, {
      x: M + 1.05,
      y: y + 0.08,
      w: CW - 1.3,
      h: rh - 0.16,
      fontSize: 16,
      color: THEME.ink,
      align: 'left',
      valign: 'middle',
    });
  });
  card(s, M, 5.95, CW, 0.85, { fill: THEME.navy, line: THEME.navy });
  txt(s, '我们不声称：可靠的事故推断、可部署、真实道路有效、事件同化更优、收益预测普遍准确', {
    x: M + 0.2,
    y: 6.0,
    w: CW - 0.4,
    h: 0.75,
    fontSize: 15,
    bold: true,
    color: THEME.light,
    align: 'center',
    valign: 'middle',
  });
}

/* ================================================== 14 · outlook ========= */
{
  const s = addSlideIn('SECTION');
  s.addText('应用前景与总结', {
    placeholder: 'title',
    fontFace: THEME.fontHead,
    fontSize: 34,
    bold: true,
    color: THEME.light,
    align: 'left',
    valign: 'middle',
    margin: 0,
  });
  const steps = ['离线决策保真度审计', '真实数据验证与可靠事件推断', '人在回路的辅助提示'];
  const bw = 3.7;
  const aw = 0.6;
  steps.forEach((t, i) => {
    const x = M + i * (bw + aw);
    s.addShape(pres.ShapeType.roundRect, {
      x,
      y: 2.25,
      w: bw,
      h: 1.25,
      rectRadius: 0.1,
      fill: { color: THEME.surfaceDark },
      line: { color: [THEME.twin, THEME.proxy, THEME.amber][i], width: 1.25 },
      shadow: { type: 'none' },
    });
    txt(s, t, {
      x: x + 0.15,
      y: 2.3,
      w: bw - 0.3,
      h: 1.15,
      fontSize: 17,
      bold: true,
      color: THEME.onDark,
      align: 'center',
      valign: 'middle',
      lineSpacingMultiple: 1.1,
    });
    if (i < 2) hArrow(s, x + bw + 0.03, 2.25 + 0.625 - 0.18, aw - 0.06, 0.36);
  });
  txt(s, '以下是待验证的应用设想：先开展离线决策保真度审计；真实数据验证与可靠事件推断达成后，'
    + '再研究人在回路的辅助提示。当前不作安全保证或部署承诺。', {
    x: 0.9,
    y: 3.75,
    w: 11.53,
    h: 1.0,
    fontSize: 16,
    color: THEME.onDarkMuted,
    align: 'center',
    valign: 'middle',
    lineSpacingMultiple: 1.2,
  });
  txt(s, '在模型失配与事故未知时，先检验孪生的建议是否可信，再谈使用', {
    x: 0.9,
    y: 4.95,
    w: 11.53,
    h: 1.0,
    fontSize: 24,
    bold: true,
    color: THEME.amber,
    align: 'center',
    valign: 'middle',
  });
  slides.push(s);
}

/* ---------------------------------------------------------------- notes --- */
slides.forEach((s, i) => {
  const n = NOTES[i + 1];
  if (n) s.addNotes(n); // notes stay empty until 04_演讲稿.md exists
});

/* ---------------------------------------------------------------- write --- */
pres.writeFile({ fileName: OUT_FILE }).then((f) => {
  console.log('wrote ' + f);
  console.log('slides: ' + slides.length + '  notes: ' + Object.keys(NOTES).length);
});
