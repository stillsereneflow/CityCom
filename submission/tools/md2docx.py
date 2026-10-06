#!/usr/bin/env python
"""Convert the project's Chinese Markdown into a clean A4 Word document.

Supported: headings ``#``-``####``, paragraphs, bullet and numbered lists, pipe tables,
bold / italic / inline code, images ``![](path)`` with a caption line, block quotes, fenced
code blocks and horizontal rules.

Typography: A4, body 宋体 (SimSun) 12 pt with Latin text in Times New Roman, headings 黑体
(SimHei), 1.5 line spacing, light-grid tables with a shaded header row, images scaled to the
text column (15 cm cap), page numbers in the footer, empty author metadata.

Usage:
    python submission/tools/md2docx.py in.md out.docx [--base DIR] [--selftest]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY_LATIN = "Times New Roman"
BODY_EA = "宋体"
HEAD_EA = "黑体"
MONO_LATIN = "Consolas"
MAX_IMAGE_CM = 15.0
BODY_PT = 12
#: hanging indent of a list item, in cm - the same 0.25" Word gives "List Bullet"
LIST_HANG_CM = 0.635

INLINE_RE = re.compile(
    r"(\*\*.+?\*\*|__.+?__|\*[^*\n]+?\*|_[^_\n]+?_|`[^`\n]+?`|\[[^\]\n]*\]\([^)\n]*\))"
)


# --------------------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------------------


def _strip_theme_fonts(rfonts) -> None:
    """Remove theme font references, which Word prefers over explicit w:ascii/w:eastAsia."""
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        if rfonts.get(qn(f"w:{attr}")) is not None:
            del rfonts.attrib[qn(f"w:{attr}")]


def set_fonts(run, latin: str = BODY_LATIN, east_asian: str = BODY_EA, size: Optional[Pt] = None,
              bold: Optional[bool] = None, italic: Optional[bool] = None,
              color: Optional[RGBColor] = None, mono: bool = False) -> None:
    """Set Latin and East-Asian fonts on a run (python-docx only sets ascii/hAnsi)."""
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    _strip_theme_fonts(rfonts)
    if mono:
        rfonts.set(qn("w:ascii"), MONO_LATIN)
        rfonts.set(qn("w:hAnsi"), MONO_LATIN)
    else:
        rfonts.set(qn("w:ascii"), latin)
        rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), east_asian)
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def style_fonts(style, latin: str, east_asian: str, size: Optional[Pt] = None,
                bold: Optional[bool] = None, color: Optional[RGBColor] = None) -> None:
    style.font.name = latin
    if size is not None:
        style.font.size = size
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    _strip_theme_fonts(rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), east_asian)


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def add_page_number_footer(doc) -> None:
    for section in doc.sections:
        paragraph = section.footer.paragraphs[0] if section.footer.paragraphs else \
            section.footer.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in list(paragraph.runs):
            run._element.getparent().remove(run._element)
        run = paragraph.add_run()
        set_fonts(run, size=Pt(10.5))
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._element.append(begin)
        run._element.append(instr)
        run._element.append(end)


def setup_document() -> "docx.Document":
    doc = docx.Document()
    normal = doc.styles["Normal"]
    style_fonts(normal, BODY_LATIN, BODY_EA, Pt(BODY_PT))
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    sizes = {1: 18, 2: 15, 3: 13, 4: 12}
    for level, size in sizes.items():
        style = doc.styles[f"Heading {level}"]
        style_fonts(style, HEAD_EA, HEAD_EA, Pt(size), bold=True, color=RGBColor(0, 0, 0))
        style.paragraph_format.space_before = Pt(12 if level <= 2 else 8)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number", "List Bullet 2", "List Number 2"):
        try:
            style = doc.styles[name]
        except KeyError:  # pragma: no cover - style set depends on the template
            continue
        style_fonts(style, BODY_LATIN, BODY_EA, Pt(BODY_PT))
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_after = Pt(2)

    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.54)
    section.left_margin = section.right_margin = Cm(3.17)

    add_page_number_footer(doc)
    cp = doc.core_properties
    cp.author = ""
    cp.last_modified_by = ""
    cp.comments = ""
    cp.title = ""
    cp.subject = ""
    cp.category = ""
    cp.keywords = ""
    return doc


# --------------------------------------------------------------------------------------
# inline markup
# --------------------------------------------------------------------------------------


def add_inline(paragraph, text: str, size: Optional[Pt] = None, base_bold: bool = False) -> None:
    """Render ``**bold**``, ``*italic*``, ``` `code` ``` and links into a paragraph."""
    for part in INLINE_RE.split(text):
        if not part:
            continue
        bold, italic, mono = base_bold, False, False
        body = part
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            bold, body = True, part[2:-2]
        elif part.startswith("__") and part.endswith("__") and len(part) > 4:
            bold, body = True, part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            italic, body = True, part[1:-1]
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            italic, body = True, part[1:-1]
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            mono, body = True, part[1:-1]
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            label, url = part[1:].split("](", 1)
            body = f"{label} ({url[:-1]})"
        run = paragraph.add_run(body)
        set_fonts(run, size=size or Pt(BODY_PT), bold=bold, italic=italic, mono=mono)


# --------------------------------------------------------------------------------------
# block parsing
# --------------------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBER_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
RULE_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
CAPTION_RE = re.compile(r"^\s*(?:\*{1,2}|_{1,2})?\s*(?:Figure|Fig\.?|图|表|Table|图表)\s*\d*[:：.]?\s*",
                        re.IGNORECASE)


def is_block_start(line: str) -> bool:
    return bool(HEADING_RE.match(line) or BULLET_RE.match(line) or NUMBER_RE.match(line)
                or IMAGE_RE.match(line) or QUOTE_RE.match(line) or RULE_RE.match(line)
                or line.strip().startswith("|") or line.strip().startswith("```"))


def split_row(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def usable_width_cm(doc) -> float:
    """Width of the text column in cm: the A4 page minus its left and right margins."""
    section = doc.sections[0]
    return (section.page_width - section.left_margin - section.right_margin) / 360000.0


def add_image(doc, base: Path, md_path: Path, path_text: str, caption: Optional[str]) -> None:
    target = (base / path_text).resolve() if not Path(path_text).is_absolute() else Path(path_text)
    if not target.exists():
        target = (md_path.parent / path_text).resolve()
    if not target.exists():
        paragraph = doc.add_paragraph()
        add_inline(paragraph, f"[missing image: {path_text}]")
        return
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(2 if caption else 6)
    run = paragraph.add_run()
    # never wider than the text column, or the centred figure overflows the right margin
    cap_cm = min(MAX_IMAGE_CM, usable_width_cm(doc))
    try:
        from PIL import Image as PILImage

        with PILImage.open(target) as im:
            width_cm = im.width / 96.0 * 2.54
    except Exception:  # pragma: no cover - fall back to the declared cap
        width_cm = cap_cm
    if width_cm > cap_cm:
        run.add_picture(str(target), width=Cm(cap_cm))
    else:
        run.add_picture(str(target), width=Cm(width_cm))
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        add_inline(cap, caption, size=Pt(10.5))
        for r in cap.runs:
            r.font.italic = True
            r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)


def add_table(doc, rows: List[List[str]]) -> None:
    if not rows:
        return
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, row in enumerate(rows):
        for j in range(width):
            cell = table.cell(i, j)
            text = row[j] if j < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.line_spacing = 1.15
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, text, size=Pt(10.5), base_bold=(i == 0))
            if i == 0:
                shade(cell, "D9D9D9")
    # a table that breaks across pages repeats its header row on the following page
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def convert(md_text: str, out_path: Path, md_path: Path, base: Path) -> "docx.Document":
    doc = setup_document()
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # fenced code block
        if stripped.startswith("```"):
            i += 1
            block: List[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.left_indent = Cm(0.5)
            paragraph.paragraph_format.space_after = Pt(8)
            run = paragraph.add_run("\n".join(block))
            set_fonts(run, size=Pt(9.5), mono=True)
            continue

        # table
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1]):
            rows = [split_row(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            add_table(doc, rows)
            continue

        # image (+ optional caption on the immediately following non-empty line)
        m = IMAGE_RE.match(stripped)
        if m:
            caption = None
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and j <= i + 2 and not is_block_start(lines[j]):
                candidate = lines[j].strip()
                if len(candidate) <= 300 and (CAPTION_RE.match(candidate) or j == i + 1):
                    caption = candidate
                    i = j
            add_image(doc, base, md_path, m.group("path"), caption)
            i += 1
            continue

        # heading
        m = HEADING_RE.match(stripped)
        if m:
            level = min(len(m.group(1)), 4)
            paragraph = doc.add_heading(level=level)
            add_inline(paragraph, m.group(2))
            for run in paragraph.runs:
                set_fonts(run, latin=HEAD_EA, east_asian=HEAD_EA,
                          size=Pt({1: 18, 2: 15, 3: 13, 4: 12}[level]), bold=True,
                          color=RGBColor(0, 0, 0))
            i += 1
            continue

        # horizontal rule
        if RULE_RE.match(stripped):
            i += 1
            continue

        # block quote
        m = QUOTE_RE.match(stripped)
        if m:
            quote: List[str] = [m.group(1)]
            i += 1
            while i < len(lines) and QUOTE_RE.match(lines[i].strip()):
                quote.append(QUOTE_RE.match(lines[i].strip()).group(1))
                i += 1
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.6)
            paragraph.paragraph_format.line_spacing = 1.5
            add_inline(paragraph, " ".join(q for q in quote if q))
            for run in paragraph.runs:
                run.font.italic = True
                run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
            continue

        # lists
        m = BULLET_RE.match(line)
        if m:
            level = 2 if len(m.group(1)) >= 2 else 1
            style = "List Bullet" if level == 1 else "List Bullet 2"
            paragraph = doc.add_paragraph(style=style)
            add_inline(paragraph, m.group(2))
            i += 1
            continue
        m = NUMBER_RE.match(line)
        if m:
            level = 2 if len(m.group(1)) >= 2 else 1
            # The number is written literally instead of using Word's "List Number" styles.
            # Those styles share one continuous counter across the whole document, so a second
            # list continues where the first stopped (a bibliography started at "4.") and the
            # literal number was printed a second time on top of the automatic one ("1. 1. …").
            # A hanging indent reproduces the geometry of the bullet lists exactly.
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(LIST_HANG_CM * level)
            paragraph.paragraph_format.first_line_indent = Cm(-LIST_HANG_CM)
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, f"{m.group(2)}. {m.group(3)}")
            i += 1
            continue

        # blank line
        if not stripped:
            i += 1
            continue

        # paragraph: join the following plain lines
        block = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
            block.append(lines[i].strip())
            i += 1
        paragraph = doc.add_paragraph()
        add_inline(paragraph, " ".join(block))
    return doc


def md_to_docx(md_path: Path, out_path: Path, base: Optional[Path] = None) -> "docx.Document":
    text = md_path.read_text(encoding="utf-8")
    doc = convert(text, out_path, md_path, base or md_path.parent)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return doc


# --------------------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------------------

SELFTEST_MD = """# 自检文档 Self-test

普通段落，包含**粗体**、*斜体*、`inline code` 与中文标点。The report quotes 2.16 [1.74, 2.59] veh·h.

## 二级标题

- 项目一 bullet item
- 项目二 with **bold** text

1. 第一项 numbered
2. 第二项 numbered

另一张编号列表必须从 1 重新开始：

1. 另一表第一项
2. 另一表第二项

> 引用块 block quote line.

| 指标 | 数值 |
| --- | --- |
| BEE | +2.162 |
| Spearman | 0.825 |

![figure](final/figures/fig1_bee_dev_vs_frozen.png)
图 1 自检图片 caption.

```python
print("code block")
```
"""


def selftest(repo: Path) -> int:
    tmp_md = repo / "submission/tools/selftest_md2docx.md"
    tmp_docx = repo / "submission/tools/selftest_md2docx.docx"
    tmp_md.write_text(SELFTEST_MD, encoding="utf-8")
    doc = md_to_docx(tmp_md, tmp_docx, base=repo)
    text = "\n".join(p.text for p in doc.paragraphs)
    # A numbered list must be written literally (never by Word's shared "List Number" counter,
    # which both continues across lists and prints the literal number a second time).
    numbered = [p.text for p in doc.paragraphs if re.match(r"^\d+\.\s", p.text)]
    doubled = [t for t in numbered if re.match(r"^\d+\.\s*\d+\.", t)]
    checks = {
        "heading": "自检文档" in text,
        "bold/italic/code": "粗体" in text and "斜体" in text and "inline code" in text,
        "bullets": any(p.style.name == "List Bullet" for p in doc.paragraphs),
        "numbers literal": numbered[:2] == ["1. 第一项 numbered", "2. 第二项 numbered"],
        "numbers restart": "1. 另一表第一项" in numbered and "2. 另一表第二项" in numbered,
        "numbers not doubled": not doubled,
        "quote": "引用块" in text,
        "table": len(doc.tables) == 1 and doc.tables[0].cell(1, 1).text == "+2.162",
        "table header repeats": doc.tables[0].rows[0]._tr.find(qn("w:trPr")) is not None
                                and doc.tables[0].rows[0]._tr.find(qn("w:trPr")).find(
                                    qn("w:tblHeader")) is not None,
        "image": any("graphic" in p._p.xml for p in doc.paragraphs),
        "image fits column": bool(doc.inline_shapes)
                             and doc.inline_shapes[0].width.pt <= usable_width_cm(doc) / 2.54 * 72,
        "caption": "自检图片" in text,
        "code block": "code block" in text,
        "author empty": doc.core_properties.author == "" and doc.core_properties.last_modified_by == "",
    }
    for name, ok in checks.items():
        print(f"  {name:>14}: {'ok' if ok else 'FAIL'}")
    ok = all(checks.values())
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", nargs="?", help="input Markdown file")
    ap.add_argument("output", nargs="?", help="output .docx file")
    ap.add_argument("--base", default=None,
                    help="directory that relative image paths resolve against (default: the input file's directory)")
    ap.add_argument("--selftest", action="store_true",
                    help="build a document from an inline sample and check the features")
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    if args.selftest:
        return selftest(repo)
    if not args.input or not args.output:
        ap.error("give an input .md and an output .docx, or --selftest")
    doc = md_to_docx(Path(args.input), Path(args.output),
                     base=Path(args.base) if args.base else None)
    print(f"wrote {args.output}: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, "
          f"{len(doc.inline_shapes)} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
