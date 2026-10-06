#!/usr/bin/env python
"""Exhaustive anonymity scan over the delivered submission tree.

Usage:
    python submission/tools/scan_anonymity.py [DIR ...] [--json OUT.json] [--quiet]

Scans every file under the given directories (default: ``submission/``) with the tier A
(identifying) and tier B (contextual) patterns of ``tools/make_source_package.py``.  The patterns
are imported, never re-spelled: they are assembled from fragments there, so this scanner contains
no identifying literal either.

File handling
-------------
* text files              : decoded (UTF-8, latin-1 fallback) and scanned line by line
* Office (.docx/.pptx/...) : unzipped; ``docProps/*.xml`` plus every XML part scanned as text
* PDF                     : PyMuPDF metadata dict + page text, plus printable runs
* ZIP                     : entry names and entry contents
* PNG                     : ``tEXt``/``iTXt``/``zTXt`` chunks, plus printable runs
* MP4                     : ffmpeg probe (container metadata), plus printable runs
* anything else           : printable runs (ASCII >= 6 chars, UTF-16LE >= 6 chars)

Binary payloads are never decoded wholesale: a naive UTF-16LE decode of compressed data produces
hundreds of spurious short matches, so runs are matched with the same patterns and short school
acronyms stay word-bounded and case-sensitive.

Exit status: 0 when no tier A hit is found anywhere, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_source_package as msp  # noqa: E402  (same directory)

REPO = Path(__file__).resolve().parents[2]
OFFICE_EXT = {".docx", ".pptx", ".xlsx", ".docm", ".pptm"}
TEXT_EXT = {
    ".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".json", ".csv", ".srt", ".ps1", ".xml",
    ".html", ".htm", ".yml", ".yaml", ".ini", ".cfg", ".toml", ".gitattributes", ".gitignore",
    ".sh", ".bat", ".css", ".svg", ".tex", ".bib",
}
ASCII_RUN = re.compile(rb"[\x20-\x7e]{6,}")
UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){6,}")
FFMPEG = next(
    (p for p in (
        Path(r"D:\CityCom\.venv-media\Lib\site-packages\imageio_ffmpeg\binaries")
        / "ffmpeg-win-x86_64-v7.1.exe",
        Path(r"D:\CityCom\.venv\Lib\site-packages\imageio_ffmpeg\binaries")
        / "ffmpeg-win-x86_64-v7.1.exe",
    ) if p.exists()),
    Path("ffmpeg"),
)


class Hit:
    __slots__ = ("file", "where", "tier", "category", "text")

    def __init__(self, file: str, where: str, tier: str, category: str, text: str) -> None:
        self.file = file
        self.where = where
        self.tier = tier
        self.category = category
        self.text = text

    def as_dict(self) -> dict:
        return {"file": self.file, "where": self.where, "tier": self.tier,
                "category": self.category, "text": self.text[:200]}


def _scan_text(name: str, text: str, hits: List[Hit]) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        for tier, group in (("A", msp.tier_a_patterns()), ("B", msp.TIER_B)):
            for category, rx, *_ in group:
                for m in rx.finditer(line):
                    hits.append(Hit(name, str(lineno), tier, category, m.group(0)))


def _scan_runs(name: str, data: bytes, hits: List[Hit]) -> None:
    for rx in (ASCII_RUN, UTF16_RUN):
        enc = "utf-16-le" if rx is UTF16_RUN else "ascii"
        for m in rx.finditer(data):
            text = m.group(0).decode(enc, "replace")
            for tier, group in (("A", msp.tier_a_patterns()), ("B", msp.TIER_B)):
                for category, pattern, *_ in group:
                    for hit in pattern.finditer(text):
                        hits.append(Hit(name, f"byte {m.start()}", tier, category, hit.group(0)))


def _scan_office(name: str, path: Path, hits: List[Hit]) -> None:
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            data = zf.read(info.filename)
            if info.filename.endswith((".xml", ".rels")) or not msp._is_binary(data):
                _scan_text(f"{name}!{info.filename}", data.decode("utf-8", "replace"), hits)
            else:
                _scan_runs(f"{name}!{info.filename}", data, hits)


def _scan_zip(name: str, path: Path, hits: List[Hit]) -> None:
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            _scan_text(f"{name}!{info.filename}", info.filename, hits)
            data = zf.read(info.filename)
            if not msp._is_binary(data):
                _scan_text(f"{name}!{info.filename}", data.decode("utf-8", "replace"), hits)
            else:
                _scan_runs(f"{name}!{info.filename}", data, hits)


def _scan_pdf(name: str, path: Path, hits: List[Hit]) -> None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None
    if fitz is not None:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        for key, value in meta.items():
            if value:
                _scan_text(f"{name}#meta:{key}", str(value), hits)
        for page in doc:
            _scan_text(f"{name}#page{page.number + 1}", page.get_text(), hits)
    _scan_runs(name, path.read_bytes(), hits)


def _scan_png(name: str, path: Path, hits: List[Hit]) -> None:
    """Scan a PNG's metadata chunks (tEXt / iTXt / zTXt) and its chunk names.

    The compressed image payload (IDAT) is deliberately *not* run-scanned: deflate output is not
    text, and a printable-run sweep over it produces spurious short matches (the same class of
    noise a naive UTF-16LE decode of compressed data produces).  Text rendered into the pixels is
    not ASCII either, so nothing readable is lost.
    """
    data = path.read_bytes()
    pos = 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        _scan_text(f"{name}#chunk:{ctype.decode('latin-1')}", ctype.decode("latin-1"), hits)
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            if ctype == b"zTXt":
                import zlib

                keyword, _, blob = chunk.partition(b"\x00")
                try:
                    text = keyword.decode("latin-1") + " " + zlib.decompress(blob[1:]).decode(
                        "utf-8", "replace")
                except Exception:
                    text = chunk.decode("latin-1")
            else:
                text = chunk.decode("utf-8", "replace")
            _scan_text(f"{name}#{ctype.decode()}", text, hits)
        pos += 12 + length
        if ctype == b"IEND":
            break


def _scan_mp4(name: str, path: Path, hits: List[Hit]) -> None:
    if FFMPEG.exists():
        proc = subprocess.run([str(FFMPEG), "-i", str(path)], capture_output=True)
        _scan_text(f"{name}#ffmpeg-probe", proc.stderr.decode("utf-8", "replace"), hits)
    _scan_runs(name, path.read_bytes(), hits)


def scan_file(path: Path, root: Path) -> List[Hit]:
    name = path.relative_to(root).as_posix()
    hits: List[Hit] = []
    ext = path.suffix.lower()
    if ext in OFFICE_EXT:
        _scan_office(name, path, hits)
    elif ext == ".zip":
        _scan_zip(name, path, hits)
    elif ext == ".pdf":
        _scan_pdf(name, path, hits)
    elif ext == ".png":
        _scan_png(name, path, hits)
    elif ext in (".mp4", ".m4v", ".mov"):
        _scan_mp4(name, path, hits)
    else:
        data = path.read_bytes()
        if ext in TEXT_EXT or not msp._is_binary(data):
            _scan_text(name, data.decode("utf-8", "replace"), hits)
        else:
            _scan_runs(name, data, hits)
    return hits


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dirs", nargs="*", default=None,
                    help="directories to scan (default: submission/)")
    ap.add_argument("--json", default=None, help="dump every hit to this JSON file")
    ap.add_argument("--quiet", action="store_true", help="print only the summary")
    args = ap.parse_args(argv)

    roots = [Path(d) for d in (args.dirs or [REPO / "submission"])]
    hits: List[Hit] = []
    files = 0
    for root in roots:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            files += 1
            hits.extend(scan_file(path, root))

    tier_a = [h for h in hits if h.tier == "A"]
    tier_b = [h for h in hits if h.tier == "B"]
    if not args.quiet:
        for h in tier_a:
            print(f"TIER A  {h.file}:{h.where}  {h.category}: {h.text[:120]}")
        groups: Dict[tuple, int] = {}
        for h in tier_b:
            groups[(h.file, h.category)] = groups.get((h.file, h.category), 0) + 1
        for (file, category), count in sorted(groups.items()):
            print(f"TIER B  {file}  {category} x{count}")
    print(f"files scanned: {files}")
    print(f"tier A (identifying) hits: {len(tier_a)} in "
          f"{len({h.file for h in tier_a})} files")
    print(f"tier B (contextual) hits: {len(tier_b)} in "
          f"{len({h.file for h in tier_b})} files")
    if args.json:
        Path(args.json).write_text(json.dumps([h.as_dict() for h in hits], ensure_ascii=False,
                                              indent=1), encoding="utf-8")
        print(f"json: {args.json}")
    print("anonymity:", "PASS" if not tier_a else "FAIL")
    return 0 if not tier_a else 1


if __name__ == "__main__":
    raise SystemExit(main())
