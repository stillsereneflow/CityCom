"""Structural validation of submission/03_答辩PPT.pptx: list every slide's text.

Usage: python validate_pptx.py [deck.pptx] [report.txt]
"""
import sys
from pptx import Presentation
from pptx.util import Emu

PATH = sys.argv[1] if len(sys.argv) > 1 else r"D:\CityCom-astra\submission\03_答辩PPT.pptx"
OUT = sys.argv[2] if len(sys.argv) > 2 else None
if OUT:
    sys.stdout = open(OUT, "w", encoding="utf-8")

prs = Presentation(PATH)
print(f"file: {PATH}")
print(f"slide size: {prs.slide_width / 914400:.2f} x {prs.slide_height / 914400:.2f} in")
print(f"slides: {len(prs.slides)}")
print(f"core properties: author={prs.core_properties.author!r} title={prs.core_properties.title!r} "
      f"subject={prs.core_properties.subject!r} last_modified_by={prs.core_properties.last_modified_by!r} "
      f"comments={prs.core_properties.comments!r} category={prs.core_properties.category!r}")

for i, slide in enumerate(prs.slides, 1):
    print(f"\n=== slide {i} (layout: {slide.slide_layout.name}) ===")
    for sh in slide.shapes:
        kind = str(sh.shape_type).split(" ")[0]
        pos = ""
        try:
            pos = (f" @({sh.left / 914400:.2f},{sh.top / 914400:.2f})"
                   f" {sh.width / 914400:.2f}x{sh.height / 914400:.2f}")
        except TypeError:
            pos = " @(inherited)"
        if sh.has_text_frame and sh.text_frame.text.strip():
            body = sh.text_frame.text.replace("\n", " | ")
            print(f"  [{kind}] {sh.name}{pos}: {body}")
        elif sh.shape_type is not None and sh.has_text_frame:
            print(f"  [{kind}] {sh.name}{pos}: <empty>")
        elif sh.shape_type is not None and not sh.has_text_frame:
            print(f"  [{kind}] {sh.name}{pos}")
        if sh.has_table:
            tbl = sh.table
            print(f"      table rows={len(tbl.rows)} cols={len(tbl.columns)} "
                  f"rowH={[round(r.height / 914400, 3) for r in tbl.rows]}")
            for r, row in enumerate(tbl.rows):
                cells = " || ".join(c.text.replace("\n", " ") for c in row.cells)
                print(f"      row{r}: {cells}")
    if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
        notes = slide.notes_slide.notes_text_frame.text
        print(f"  <notes: {len(notes)} chars> {notes[:60]!r}")
    else:
        print("  <notes: empty>")
