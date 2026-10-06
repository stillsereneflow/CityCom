"""Verify that every slide's speaker notes equal the body of the matching page in 04_演讲稿.md.

Usage: python submission/deck/verify_notes.py [deck.pptx] [04_演讲稿.md]

The deck builder loads notes from 04_演讲稿.md with the same heading rule used here, so this is an
exact check of the delivered .pptx against the corrected script (no re-formatting tolerance).
Prints one ASCII line per slide plus a final verdict; exit status 0 when all 14 match.
"""
import re
import sys
from pathlib import Path

from pptx import Presentation

REPO = Path(__file__).resolve().parents[2]
PPTX = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "submission" / "03_答辩PPT.pptx"
SCRIPT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "submission" / "04_演讲稿.md"


def script_pages(path: Path) -> dict:
    md = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    parts = re.split(r"^(#{1,6})\s*(.*)$", md, flags=re.M)
    pages = {}
    for i in range(1, len(parts) - 1, 3):
        m = re.match(r"^第(\d+)页", parts[i + 1].strip())
        if m:
            pages[int(m.group(1))] = parts[i + 2].strip()
    return pages


def main() -> int:
    pages = script_pages(SCRIPT)
    prs = Presentation(str(PPTX))
    ok = True
    n = 0
    for i, slide in enumerate(prs.slides, 1):
        n = i
        notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
        want = pages.get(i, "")
        same = notes == want
        ok = ok and same and bool(notes)
        print(f"slide {i:2d}: notes {len(notes):4d} chars, script page {len(want):4d} chars, "
              f"{'MATCH' if same else 'MISMATCH'}")
    print(f"slides: {n}; pages in script: {sorted(pages)}")
    print("notes:", "PASS" if ok and len(pages) == n else "FAIL")
    return 0 if ok and len(pages) == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
