#!/usr/bin/env python
"""Check every number in a submission file against the project's own number whitelist.

The whitelist is built automatically from the documents that define what the project may claim:

    final/CLAIMS.md            final/FINAL_REPORT.md      final/METHOD.md
    final/tables/*.md          final/demo/decision_cards.txt
    docs/freeze-2026-10-06.md  docs/decision-2026-10-03b-synthetic.md
    docs/blite-spec.md
    submission/tools/allowed_extra.txt   (small explicit list of structural numbers)

Every numeric token is extracted from the target files (Markdown, ``.docx``, ``.pptx`` - text and
speaker notes - and ``.srt``) and matched against that whitelist with format normalisation:
``2.16`` matches the recorded ``2.162`` - a value quoted at fewer decimals matches the recorded
value rounded half-up to that many decimals, sign included, so ``[-4.91, -0.83]`` matches
``[-4.914, -0.826]`` - ``+2.16`` matches ``2.16``, ``-`` matches U+2212 ``-``, thousands
separators and a trailing ``%`` are ignored, and a number that is part of an identifier (``A3``,
``net5``, ``AID07106``, ``ktb_n1``) is checked as that identifier.

Two token shapes get special treatment.  A ``k/n`` fraction is whitelisted when a source records
the same pair, as ``k/n``, as ``k of n`` or as a ``k/n`` table cell.  A composite such as
``7.07 / 4.90`` is not a fraction at all and is split into its two numbers.

Structural numbers are not claims: section numbering (``1.1``, ``3.6``, ``第 3 页``) and every
number in a ``参考文献`` / ``References`` section (years, volumes, page ranges, URLs) are reported
as structural instead of being checked against the whitelist.

Usage:
    python submission/tools/check_numbers.py FILE...
    python submission/tools/check_numbers.py --selftest
    python submission/tools/check_numbers.py --out report.md FILE...

Exit status: 0 when every number is whitelisted, 1 when at least one is not (2 on a usage error).
"""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
ALLOWED_EXTRA = Path(__file__).resolve().parent / "allowed_extra.txt"

WHITELIST_SOURCES = [
    "final/CLAIMS.md",
    "final/FINAL_REPORT.md",
    "final/METHOD.md",
    "final/tables/*.md",
    "final/demo/decision_cards.txt",
    "docs/freeze-2026-10-06.md",
    "docs/decision-2026-10-03b-synthetic.md",
    "docs/blite-spec.md",
]

# --------------------------------------------------------------------------------------
# tokenizer
# --------------------------------------------------------------------------------------

# A fraction (``7/8``, ``960/960``, ``5/2/1``) is one token; so is a number with optional sign,
# thousands separators and decimals.  A fraction is made of integers only: ``7.07 / 4.90`` is a
# composite of two numbers, not a fraction, and is split into them.  The sign only binds when it
# does not follow a digit or a letter, so the hyphens of ``2026-10-06`` and ``NA-300`` are
# separators, not minus signs.
TOKEN_RE = re.compile(
    r"(?P<frac>\d+(?:\s*/\s*\d+)+)"
    r"|(?P<sign>(?<![\w.])[+\-\u2212](?=\d))?(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
)

WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
#: a pair of counts written out in prose: ``14 of 21 detectors``
OF_RE = re.compile(r"(?<![\w.])(\d+)\s+of\s+(\d+)(?![\w.])")
#: characters that may surround an identifier without being part of it
WORD_TRIM = ".,;:()[]{}<>\"'`*_|"


class Token:
    """One numeric token found in a document."""

    __slots__ = ("raw", "value", "precision", "where", "ident", "kind", "lineno", "col")

    def __init__(self, raw: str, value: Optional[Decimal], precision: int, where: str,
                 ident: Optional[str], kind: str, lineno: int = 1, col: int = 0) -> None:
        self.raw = raw
        self.value = value
        self.precision = precision
        self.where = where
        self.ident = ident
        self.kind = kind          # "number" | "fraction" | "identifier"
        self.lineno = lineno      # 1-based line of the text this token came from
        self.col = col            # 0-based column of ``raw`` on that line

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.raw!r}, {self.value}, {self.where})"


def _decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _precision(text: str) -> int:
    return len(text.split(".", 1)[1]) if "." in text else 0


def tokenize(text: str, where: str = "L") -> List[Token]:
    """Extract every numeric token from ``text``.

    ``where`` is the label prefix: the line number is appended (``L12``, ``slide 4``, ``para 9``).
    """
    tokens: List[Token] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        pos = f"{where}{lineno}"
        dates = [(m.start(), m.end(), m.group(0)) for m in DATE_RE.finditer(line)]
        for m in TOKEN_RE.finditer(line):
            frac = m.group("frac")
            if frac:
                # one token; keep the numeric value when it is a simple a/b fraction
                parts = [p.strip() for p in frac.split("/")]
                value = None
                if len(parts) == 2:
                    a, b = _decimal(parts[0]), _decimal(parts[1])
                    if a is not None and b not in (None, Decimal(0)):
                        value = a / b
                tokens.append(Token(frac, value, 3, pos, None, "fraction", lineno, m.start()))
                continue
            raw_num = m.group("num")
            sign = m.group("sign") or ""
            if sign == "\u2212":
                sign = "-"
            flat = raw_num.replace(",", "")
            value = _decimal(sign + flat)
            raw = sign + raw_num
            # identifier context: A3, net5, AID07106, ktb_n1, 2026-10-06
            start, end = m.start("num"), m.end("num")
            if sign:
                start = m.start("sign")
            left, right = start, end
            while left > 0 and (line[left - 1].isalnum() or line[left - 1] in "_.-"):
                left -= 1
            while right < len(line) and (line[right].isalnum() or line[right] in "_.-"):
                right += 1
            word = line[left:right].strip(WORD_TRIM)
            ident = None
            if any(c.isalpha() for c in word) and re.fullmatch(r"[A-Za-z0-9_.\-]+", word or ""):
                ident = word
            for d_start, d_end, date in dates:
                if d_start <= start and end <= d_end:
                    ident = date          # a date is checked as one literal (2026-10-06)
                    break
            tokens.append(Token(raw, value, _precision(flat), pos, ident,
                                "identifier" if ident else "number", lineno, start))
    return tokens


def fraction_key(raw: str) -> Optional[Tuple[str, str]]:
    """``14/21`` -> ``("14", "21")``; ``None`` unless the token is a plain two-count fraction."""
    parts = [p.strip() for p in raw.split("/")]
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return parts[0], parts[1]


# --------------------------------------------------------------------------------------
# whitelist
# --------------------------------------------------------------------------------------


class Whitelist:
    """Values, literals and identifiers taken from the source-of-truth documents."""

    def __init__(self) -> None:
        self.values: Dict[Decimal, Tuple[str, str]] = {}   # value -> (source, line)
        self.literals: Dict[str, Tuple[str, str]] = {}     # normalised literal -> (source, line)
        self.words: Dict[str, Tuple[str, str]] = {}        # identifier (lower) -> (source, line)
        self.fractions: Dict[Tuple[str, str], Tuple[str, str]] = {}   # (k, n) -> (source, line)
        self.raw_numbers: set = set()                      # every literal seen, for exact matches

    def add_text(self, text: str, source: str) -> None:
        for lineno, line in enumerate(text.splitlines(), start=1):
            pos = f"{source}:{lineno}"
            for w in WORD_RE.findall(line):
                self.words.setdefault(w.strip(WORD_TRIM).lower(), (source, str(lineno)))
            for date in DATE_RE.findall(line):
                self.words.setdefault(date.lower(), (source, str(lineno)))
            for k, n in OF_RE.findall(line):
                self.fractions.setdefault((k, n), (source, str(lineno)))
            for tok in tokenize(line, where=""):
                self.raw_numbers.add(tok.raw)
                if tok.value is not None:
                    self.values.setdefault(tok.value, (source, str(lineno)))
                if tok.ident:
                    self.words.setdefault(tok.ident.lower(), (source, str(lineno)))
                flat = tok.raw.replace(",", "").replace("+", "")
                if tok.kind == "fraction":
                    flat = flat.replace(" ", "")
                    key = fraction_key(tok.raw)
                    if key is not None:
                        self.fractions.setdefault(key, (source, str(lineno)))
                self.literals.setdefault(flat, (source, str(lineno)))

    def add_number(self, text: str, source: str) -> None:
        """Add one explicit structural number (from allowed_extra.txt)."""
        tok = _decimal(text.replace(",", ""))
        if tok is not None:
            self.values.setdefault(tok, (source, "explicit"))
        self.literals.setdefault(text.replace(",", ""), (source, "explicit"))

    def add_entry(self, entry: str, source: str) -> None:
        """Add one allowed_extra.txt entry: a number, a date or an inclusive ``a-b`` range."""
        if re.fullmatch(r"\d+-\d+", entry):
            lo, hi = (int(x) for x in entry.split("-"))
            for n in range(lo, hi + 1):
                self.add_number(str(n), source)
            return
        self.add_number(entry, source)

    # -- matching ------------------------------------------------------------------------

    def match(self, tok: Token) -> Optional[str]:
        """Return a human-readable whitelist source, or ``None`` when the token is unknown."""
        if tok.kind == "fraction":
            flat = tok.raw.replace(" ", "")
            if flat in self.literals:
                src = self.literals[flat]
                return f"literal `{tok.raw}` in {src[0]}:{src[1]}"
            key = fraction_key(tok.raw)
            if key is not None and key in self.fractions:
                src = self.fractions[key]
                return f"fraction `{tok.raw}` in {src[0]}:{src[1]}"
            return None
        if tok.ident:
            hit = self.words.get(tok.ident.lower())
            if hit:
                return f"identifier `{tok.ident}` in {hit[0]}:{hit[1]}"
            if tok.value is not None and tok.raw in self.raw_numbers:
                return f"literal `{tok.raw}` in the whitelist corpus"
            return None
        flat = tok.raw.replace(",", "")
        if flat in self.literals:
            src = self.literals[flat]
            return f"literal `{tok.raw}` in {src[0]}:{src[1]}"
        if flat.lstrip("+") in self.literals:
            src = self.literals[flat.lstrip("+")]
            return f"literal `{tok.raw}` in {src[0]}:{src[1]}"
        if tok.value is None:
            return None
        # value match: an exact value, or a recorded value quoted at a coarser precision
        # (2.16 for the recorded 2.162, -4.91 for the recorded -4.914).  A document may never
        # quote *more* precision than any recorded number, and rounding to a coarse recorded
        # integer (3.7 -> 4) is not a match.
        for value, (source, line) in self.values.items():
            if value == tok.value:
                return f"value {value} in {source}:{line}"
        for value, (source, line) in self.values.items():
            places = -value.as_tuple().exponent
            if places <= tok.precision or places > 9:
                continue
            rounded = _round(value, tok.precision)
            if rounded is not None and rounded == tok.value:
                return f"`{tok.raw}` is {value} in {source}:{line} rounded to {tok.precision} dp"
        return None


def _round(value: Decimal, places: int) -> Optional[Decimal]:
    """Round half-up to ``places`` decimals; ``None`` when that is not meaningful/possible."""
    if places < 0 or places > 9:
        return None
    try:
        with localcontext() as ctx:
            ctx.prec = max(28, len(value.as_tuple().digits) + places + 5)
            return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def build_whitelist(repo: Path) -> Whitelist:
    wl = Whitelist()
    for pattern in WHITELIST_SOURCES:
        for path in sorted(repo.glob(pattern)):
            wl.add_text(path.read_text(encoding="utf-8", errors="replace"),
                        path.relative_to(repo).as_posix())
    if ALLOWED_EXTRA.exists():
        for lineno, line in enumerate(ALLOWED_EXTRA.read_text(encoding="utf-8").splitlines(), 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            for part in re.split(r"[\s,]+", line):
                if part:
                    wl.add_entry(part, "submission/tools/allowed_extra.txt")
    return wl


# --------------------------------------------------------------------------------------
# document readers
# --------------------------------------------------------------------------------------


def read_text(path: Path) -> List[Tuple[str, str]]:
    """Return ``[(label, text)]`` for Markdown / text."""
    return [("L", path.read_text(encoding="utf-8", errors="replace"))]


def read_srt(path: Path) -> List[Tuple[str, str]]:
    """Return the spoken text of an ``.srt`` file.

    Cue indices and the ``00:00:01,000 --> 00:00:04,000`` timing lines are structural subtitle
    machinery, not content, so they are dropped (the line numbers of the kept text are preserved
    by padding the dropped lines with blanks); every number in the subtitle text is still checked.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    kept: List[str] = []
    for i, line in enumerate(lines):
        if "-->" in line:
            kept.append("")
            continue
        if re.fullmatch(r"\s*\d+\s*", line) and i + 1 < len(lines) and "-->" in lines[i + 1]:
            kept.append("")
            continue
        kept.append(line)
    return [("L", "\n".join(kept))]


def read_docx(path: Path) -> List[Tuple[str, str]]:
    import docx  # python-docx

    doc = docx.Document(str(path))
    out: List[Tuple[str, str]] = []
    body = "\n".join(p.text for p in doc.paragraphs)
    out.append(("para ", body))
    for i, table in enumerate(doc.tables, 1):
        rows = ["\t".join(cell.text for cell in row.cells) for row in table.rows]
        out.append((f"table {i} row ", "\n".join(rows)))
    for s, section in enumerate(doc.sections, 1):
        for name, part in (("header", section.header), ("footer", section.footer)):
            if part is not None and part.paragraphs:
                out.append((f"{name} {s} para ", "\n".join(p.text for p in part.paragraphs)))
    return out


def read_pptx(path: Path) -> List[Tuple[str, str]]:
    from pptx import Presentation

    prs = Presentation(str(path))
    out: List[Tuple[str, str]] = []
    for i, slide in enumerate(prs.slides, 1):
        chunks: List[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                chunks.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                chunks.extend("\t".join(c.text for c in row.cells) for row in shape.table.rows)
        out.append((f"slide {i} para ", "\n".join(chunks)))
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text
            if notes.strip():
                out.append((f"slide {i} notes para ", notes))
    return out


READERS = {".md": read_text, ".markdown": read_text, ".txt": read_text, ".srt": read_srt,
           ".docx": read_docx, ".pptx": read_pptx}


def read_document(path: Path) -> List[Tuple[str, str]]:
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise SystemExit(f"unsupported file type: {path} (use .md/.txt/.srt/.docx/.pptx)")
    return reader(path)


# --------------------------------------------------------------------------------------
# structural numbers (section numbering, references)
# --------------------------------------------------------------------------------------

#: a heading of the form ``## Title``
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+\S")
#: the heading that opens a bibliography, with or without Markdown hashes
REFS_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})?\s*(?:参考文献|references)\s*[:：]?\s*$",
                             re.IGNORECASE)
#: a section number: ``1.1``, ``3.6``, ``3.6.2`` - short integers joined by dots
SECTION_NUMBER_RE = re.compile(r"\d{1,2}(?:\.\d{1,2})+")
#: words that make a following dotted number a cross-reference to a section, not a claim
SECTION_CUES = ("部分", "章节", "参见", "详见", "见", "section", "chapter", "see", "§")
#: units that make ``第 3 …`` a structural reference rather than a claim
ORDINAL_UNITS = ("页", "章", "节", "部分", "条", "次", "轮", "阶段", "步", "版", "届", "卷", "期")
ORDINAL_RE = re.compile(r"第\s*$")
ORDINAL_UNIT_RE = re.compile(r"\s*(?:" + "|".join(ORDINAL_UNITS) + r")")


def references_lines(text: str) -> set:
    """1-based line numbers covered by a ``参考文献`` / ``References`` section.

    The section runs from its heading to the next heading of the same or higher level, or to the
    end of the document: a bibliography's years, volumes, page ranges and URLs are citations,
    not claims about this project.
    """
    lines = text.splitlines()
    covered: set = set()
    level: Optional[int] = None
    for lineno, line in enumerate(lines, start=1):
        if level is None:
            m = REFS_HEADING_RE.match(line.strip())
            if m:
                level = len(m.group("hashes") or "#")
                covered.add(lineno)
            continue
        h = HEADING_RE.match(line)
        if h and len(h.group("hashes")) <= level:
            level = None                      # a new same-or-higher section starts here
            continue
        covered.add(lineno)
    return covered


def _in_section_context(line: str, col: int) -> bool:
    """Is the dotted number at ``col`` used as section numbering rather than as a value?"""
    before = line[:col]
    if re.fullmatch(r"[\s#>]*", before):
        # numbers the line: ``### 1.1 Problem``.  A bare ``7.07`` that opens a paragraph is a
        # value, not a section number, so a Markdown heading marker must be present.
        return "#" in before
    if re.fullmatch(r"[\s#>]*(?:[-*+]|\d+[.)])\s+[\s#>]*", before):
        return True                                       # after a list marker
    tail = before[-12:]
    return any(cue in tail for cue in SECTION_CUES)


def structural_reason(line: str, tok: Token) -> Optional[str]:
    """Why ``tok`` is document structure rather than a claim, or ``None`` when it is a claim."""
    if tok.kind == "fraction":
        return None
    after = line[tok.col + len(tok.raw):]
    if ORDINAL_RE.search(line[:tok.col]) and ORDINAL_UNIT_RE.match(after):
        return "structural: 第N页/章 reference"
    if (tok.ident is None and SECTION_NUMBER_RE.fullmatch(tok.raw)
            and _in_section_context(line, tok.col)):
        return "structural: section number"
    return None


# --------------------------------------------------------------------------------------
# checking
# --------------------------------------------------------------------------------------


class Result:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: List[Tuple[Token, Optional[str]]] = []

    @property
    def bad(self) -> List[Tuple[Token, Optional[str]]]:
        return [(t, s) for t, s in self.rows if s is None]


def check_file(path: Path, wl: Whitelist) -> Result:
    res = Result(path)
    for label, text in read_document(path):
        refs = references_lines(text)
        lines = text.splitlines()
        for tok in tokenize(text, where=label):
            line = lines[tok.lineno - 1] if tok.lineno <= len(lines) else ""
            if tok.lineno in refs:
                reason: Optional[str] = "structural: references section"
            else:
                reason = structural_reason(line, tok)
            res.rows.append((tok, reason or wl.match(tok)))
    return res


def format_report(results: Sequence[Result], wl: Whitelist, repo: Path) -> str:
    lines: List[str] = []
    total = bad_total = 0
    lines.append("# Number whitelist check")
    lines.append("")
    lines.append(f"- whitelist: {len(wl.values)} distinct values, {len(wl.literals)} literals, "
                 f"{len(wl.words)} identifiers from "
                 + ", ".join(f"`{s}`" for s in WHITELIST_SOURCES)
                 + ", `submission/tools/allowed_extra.txt`.")
    lines.append("")
    for res in results:
        bad = res.bad
        total += len(res.rows)
        bad_total += len(bad)
        try:
            shown = res.path.relative_to(repo).as_posix()
        except ValueError:
            shown = str(res.path)
        lines.append(f"## `{shown}`")
        lines.append("")
        lines.append(f"{len(res.rows)} numeric tokens, {len(bad)} not whitelisted.")
        lines.append("")
        lines.append("| Number | Where | Whitelisted | Matching source |")
        lines.append("| --- | --- | --- | --- |")
        for tok, src in res.rows:
            mark = "yes" if src else "**NO**"
            lines.append(f"| `{tok.raw}` | {tok.where} | {mark} | {src or '-'} |")
        lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- files checked: {len(results)}")
    lines.append(f"- numeric tokens: {total}")
    lines.append(f"- **not whitelisted: {bad_total}**")
    return "\n".join(lines) + "\n"


def print_report(results: Sequence[Result], repo: Path) -> int:
    bad_total = 0
    total = 0
    for res in results:
        bad = res.bad
        bad_total += len(bad)
        total += len(res.rows)
        try:
            shown = res.path.relative_to(repo).as_posix()
        except ValueError:
            shown = str(res.path)
        print(f"\n=== {shown} : {len(res.rows)} numbers, {len(bad)} not whitelisted ===")
        for tok, src in res.rows:
            if src is None:
                print(f"  {tok.where:>14}  {tok.raw:>16}   *** NOT WHITELISTED ***")
            else:
                print(f"  {tok.where:>14}  {tok.raw:>16}   ok   <- {src}")
    print(f"\nTOTAL: {total} numbers in {len(results)} file(s); {bad_total} not whitelisted")
    return bad_total


# --------------------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------------------

SYNTHETIC = """# Synthetic check file (invented numbers must be flagged)

- Claimed benefit-estimation error **+2.16 [1.74, 2.59]** veh·h on seeds 4501-4508 (whitelisted).
- Invented: the queue fell to 47.7 vehicles and the gain reached 12.345 veh·h (must be flagged).
- Also invented: 4321 halted vehicles and an 88.8 % improvement (must be flagged).
- Structural: section 2, year 2026, slide 12 (allowed by allowed_extra.txt).
"""

#: Exercises the structural / composite / fraction / rounding rules added on top of SYNTHETIC.
SYNTHETIC_STRUCTURAL = """# Synthetic structure file

### 1.1 Section numbering is not a claim

- Composite of two numbers: 7.07 / 4.90 (recorded as 7.066 and 4.904).
- Fraction: 14/21 (recorded as "14 of 21").
- Negative interval: [-4.91, -0.83] (recorded as [-4.914, -0.826]).
- Invented: 第 99 页 reports 777777 vehicles (only that count must be flagged).

## 参考文献

1. Invented, A. (1999). *Journal of Nothing*, 12(3), 45-67. https://example.org/1999/12/3456
2. 又一条 888888（参考文献内的数字全部是结构，不是断言）。

# 结语

- Invented again: 555555 vehicles (must be flagged once the references section ends).
"""


def selftest(repo: Path) -> int:
    wl = build_whitelist(repo)
    claims = repo / "final/CLAIMS.md"
    res = check_file(claims, wl)
    bad = res.bad
    print(f"selftest 1: {claims.relative_to(repo).as_posix()} -> {len(res.rows)} numbers, "
          f"{len(bad)} not whitelisted (expected 0)")
    for tok, _ in bad:
        print(f"  unexpected: {tok.where} {tok.raw}")
    synth = Path(__file__).resolve().parent / "selftest_numbers_synthetic.md"
    synth.write_text(SYNTHETIC, encoding="utf-8")
    res2 = check_file(synth, wl)
    flagged = [t.raw for t, s in res2.bad]
    print(f"selftest 2: {synth.name} -> {len(res2.rows)} numbers, {len(flagged)} flagged: {flagged}")
    expect_flagged = {"47.7", "12.345", "4321", "88.8"}
    ok = not bad and expect_flagged.issubset(set(flagged)) and len(flagged) == len(expect_flagged)

    # 3. a synthetic .pptx: the slide text is a recorded number, the speaker notes are invented
    from pptx import Presentation

    pptx_path = Path(__file__).resolve().parent / "selftest_numbers_synthetic.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "BEE +2.162 [1.738, 2.586] on seeds 4501-4508"
    slide.notes_slide.notes_text_frame.text = "invented 98765 vehicles in the speaker notes"
    # python-pptx's default template carries the library author in the core properties; the
    # self-test artefact must not name anybody, so every identity field is cleared before saving.
    props = prs.core_properties
    props.author = ""
    props.last_modified_by = ""
    props.title = ""
    props.subject = ""
    props.comments = ""
    props.category = ""
    props.keywords = ""
    prs.save(str(pptx_path))
    res3 = check_file(pptx_path, wl)
    flagged3 = [t.raw for t, s in res3.bad]
    print(f"selftest 3: {pptx_path.name} -> {len(res3.rows)} numbers, {len(flagged3)} flagged: {flagged3}")
    ok = ok and flagged3 == ["98765"]

    # 4. a synthetic .srt: cue indices and timecodes are structural, the text number is checked
    srt_path = Path(__file__).resolve().parent / "selftest_numbers_synthetic.srt"
    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:04,000\n收益估计误差 +2.16 车·时\n\n"
        "2\n00:00:05,000 --> 00:00:08,000\ninvented 54321 halted vehicles\n", encoding="utf-8")
    res4 = check_file(srt_path, wl)
    flagged4 = [t.raw for t, s in res4.bad]
    print(f"selftest 4: {srt_path.name} -> {len(res4.rows)} numbers, {len(flagged4)} flagged: {flagged4}")
    ok = ok and flagged4 == ["54321"]

    # 5. structural numbers, composites, k/n fractions and rounding (incl. negatives)
    struct_path = Path(__file__).resolve().parent / "selftest_numbers_structural.md"
    struct_path.write_text(SYNTHETIC_STRUCTURAL, encoding="utf-8")
    res5 = check_file(struct_path, wl)
    flagged5 = [t.raw for t, s in res5.bad]
    print(f"selftest 5: {struct_path.name} -> {len(res5.rows)} numbers, "
          f"{len(flagged5)} flagged: {flagged5}")
    reasons = {t.raw: (s or "*** NOT WHITELISTED ***") for t, s in res5.rows}
    want = {"7.07": "rounded", "4.90": "rounded", "14/21": "fraction",
            "-4.91": "rounded", "-0.83": "rounded", "1.1": "section number",
            "99": "第N", "1999": "references section"}
    wrong = {raw: reasons.get(raw) for raw, cue in want.items() if cue not in (reasons.get(raw) or "")}
    for raw, reason in wrong.items():
        print(f"  selftest 5: `{raw}` matched as {reason!r}, expected {want[raw]!r}")
    ok = ok and flagged5 == ["777777", "555555"] and not wrong

    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*", help="files to check (.md/.txt/.srt/.docx/.pptx)")
    ap.add_argument("--repo", default=str(REPO), help="repository root holding the whitelist sources")
    ap.add_argument("--out", default=None, help="also write a Markdown report here")
    ap.add_argument("--selftest", action="store_true",
                    help="check final/CLAIMS.md (expect 0) and a synthetic file (expect flags)")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    if args.selftest:
        return selftest(repo)
    if not args.files:
        ap.error("give at least one file, or --selftest")
    wl = build_whitelist(repo)
    results = [check_file(Path(f), wl) for f in args.files]
    bad_total = print_report(results, repo)
    if args.out:
        Path(args.out).write_text(format_report(results, wl, repo), encoding="utf-8")
        print(f"report written: {args.out}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
