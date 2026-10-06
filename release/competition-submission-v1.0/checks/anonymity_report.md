# Anonymity report — `submission/`

- Scan time: 2026-10-06 18:28 (final pass; the scan is re-runnable with
  `python -B submission/tools/scan_anonymity.py submission`).
- Scope: **every file under `submission/`** — 319 files, including `deck/`, `tools/`, `video/src/`
  and the packaged `source/citypulse_source.zip`.
- Result: **0 identifying (tier A) hits.** The scan exits 0.

**Placeholders.** The identifying strings this report has to describe are never spelled out here.
They are replaced by 〈用户名样例〉 (user name), 〈邮箱样例〉 (e-mail address), 〈姓名样例〉 (personal
name), 〈院校样例〉 (institution) and 〈本地用户路径样例〉 (local user path). The same convention is
used in `source/anonymity_scan.md`.

## Method

`submission/tools/scan_anonymity.py` imports the tier A (identifying) and tier B (contextual)
patterns from `submission/tools/make_source_package.py` — they are never re-spelled — and applies
them to every file:

| File kind | How it is read |
| --- | --- |
| text (`.md` `.py` `.js` `.json` `.csv` `.srt` `.ps1` `.xml` …) | decoded (UTF-8, latin-1 fallback), scanned line by line |
| Office (`.docx` `.pptx`) | unzipped; `docProps/*.xml` and every XML part scanned as text |
| PDF | PyMuPDF metadata dict + page text, plus printable runs over the raw bytes |
| ZIP | entry names and entry contents |
| PNG | `tEXt` / `iTXt` / `zTXt` metadata chunks; the compressed image payload is not run-scanned |
| MP4 | ffmpeg container probe (metadata tags) plus printable runs |
| anything else | printable runs (ASCII ≥ 6 chars, UTF-16LE ≥ 6 chars) |

The compressed payloads are the one place where a byte sweep would be meaningless: deflate and
H.264 output is not text, and running the patterns over it produces spurious short matches. Text
that is *rendered* into a picture is pixels, not ASCII, so nothing readable is lost by skipping it.

## Verdict

- **Tier A (identifying) hits: 0 in 0 files.** No user name, e-mail address, personal name,
  institution name or local user path is present in any file under `submission/`.
- **The two anonymity reports themselves are redacted.** `checks/anonymity_report.md` (this file)
  and `source/anonymity_scan.md` describe the identifying strings only through the placeholders
  above. The unredacted originals are kept outside the deliverables, in
  `D:/CityCom/submission-internal/`.
- **Document metadata is clean.** No `dc:creator`, `cp:lastModifiedBy` or `Company` in any
  submitted Office file; no `Author` in any submitted PDF; no title/artist/author tag in either
  MP4 (see the tables below).
- **Tier B (contextual) hits: 11660 in 55 files** — machine-specific paths (`D:\CityCom-astra`,
  `D:\CityCom\.venv`, `~/.claude/runs/…`) inside build scripts and the frozen-audit records. They
  carry no user name, e-mail address or institution and were deliberately left byte-identical: most
  live in files whose sha256 the freeze manifest records, and altering them would break the
  integrity check the source package exists to preserve.

## Document metadata

| File | Kind | Metadata found |
| --- | --- | --- |
| `01_项目简表.docx` | office | no creator / last-modified-by / company — parts=18, Application=Microsoft Macintosh Word, AppVersion=14.0000, TotalTime=0 |
| `01_项目简表.pdf` | pdf | no author / title / subject — creator=producer=Microsoft® Word 适用于 Microsoft 365, 3 pages |
| `02_作品说明书.docx` | office | no creator / last-modified-by / company — parts=21, Application=Microsoft Macintosh Word, AppVersion=14.0000, TotalTime=0 |
| `02_作品说明书.pdf` | pdf | no author / title / subject — creator=producer=Microsoft® Word 适用于 Microsoft 365, 11 pages |
| `03_答辩PPT.pptx` | office | no creator / last-modified-by / company — parts=101, dc:title=《城脉·涟控》, Application=Microsoft Office PowerPoint, AppVersion=16.0000, TotalTime=0 |
| `03_答辩PPT.pdf` | pdf | no author — title=《城脉·涟控》, creator=producer=Microsoft® PowerPoint® 适用于 Microsoft 365, 14 pages |
| `tools/selftest_claims.docx` | office | no creator / last-modified-by / company — parts=18 |
| `tools/selftest_claims.pdf` | pdf | no author / title — 4 pages |
| `tools/selftest_md2docx.docx` | office | no creator / last-modified-by / company — parts=19 |
| `tools/selftest_numbers_synthetic.pptx` | office | no creator / last-modified-by / company — parts=43, Application=Microsoft Macintosh PowerPoint, TotalTime=1 |
| `video/citypulse_demo_1080p.mp4` | mp4 | only `encoder=Lavf61.7.100` / `Lavc61.19.100 libx264` and `handler_name=VideoHandler`; no title/artist/author/comment |
| `video/citypulse_preview_540p.mp4` | mp4 | same tags only |

PNG `tEXt` chunks: the matplotlib figures carry `Software\0Matplotlib version…, https://matplotlib.org/`
and nothing else — no author, no path.

## What was fixed in this round

1. **Both reports redacted.** The previous `checks/anonymity_report.md` reproduced the user names,
   the e-mail address, the personal name and the institution verbatim, and its conclusion claimed no
   identifier reached any delivered file. Every identifying literal is now a placeholder and the
   conclusion states what is actually true: 报告中的识别字符串已替换为占位符；交付物中未发现识别信息。
   The unredacted originals live in `D:/CityCom/submission-internal/`
   (`anonymity_report.unredacted.md`, `anonymity_scan.unredacted.md`).
2. **The tooling no longer spells out what it looks for.** `tools/make_source_package.py` now reads
   the repository's own identity from `git log` at run time and assembles every fixed pattern
   (user-profile directory, profile variable, school/institution words, author trailer) from
   fragments, and its self-test plant is built the same way. Its `--selftest` still fires: 7 tier A
   hits found and redacted, 0 remaining.
3. **The throw-away `tools/selftest_numbers_synthetic.pptx` no longer carries the python-pptx
   template default.** `tools/check_numbers.py` clears `author`, `last_modified_by`, `title`,
   `subject`, `comments`, `category` and `keywords` before saving the self-test artefact, and the
   file was regenerated: `cp:lastModifiedBy` and `dc:creator` are now empty.
4. **The deck no longer stores build-machine paths in picture alt-text.** `deck/build_deck.js` passes
   each figure's caption as the picture `altText`, so `descr` holds the Chinese caption instead of
   `D:\CityCom-astra\final\figures\…` on slides 9, 10 and 11.
5. **`deck/node_modules/` was removed from the deliverable.** It is a third-party npm install tree
   (353 files, 6.6 MB) and produced 52 tier A matches in 30 files — upstream library e-mail
   addresses and example user paths (`…@example.com`, `/Users/…`, `/home/…`) plus two TypeScript
   `author:` declarations. None of it has anything to do with this submission, but any e-mail sweep
   would report it. `deck/package.json` and `deck/package-lock.json` remain, so the deck rebuilds
   after `npm ci`.
6. **`__pycache__` directories were deleted** (`tools/`, `video/src/`); bytecode caches can embed
   paths from the machine that produced them.

## Tier A — identifying hits

**0.** For the record, the round before this one reported 21 hits confined to the anonymity
machinery itself (the two reports, the packaging script's own detectors and plant, and one
illustrative path example in `video/storyboard.md`); all of them are gone now.

## Tier B — contextual machine paths (reported, not identifying)

11660 matches in 55 files, none carrying a user name, e-mail address or institution:

| File | Category | Matches |
| --- | --- | --- |
| `source/citypulse_source.zip` (11406 of them in `results/frozen_audit/seed_check.json`, 42 in `provenance.json`) | machine-specific repo path / home-directory tool path | 11479 |
| `source/anonymity_scan.md` | machine-specific repo path / home-directory tool path | 40 |
| `video/src/scratch/*.py` (28 scripts) | machine-specific repo path | 121 |
| `checks/anonymity_report.md` (this file) | machine-specific repo path / home-directory tool path | 6 |
| `video/src/*.py` (`data_loader`, `generate_panels`, `render_engine`, `sim_extractor`) | machine-specific repo path | 5 |
| `tools/make_source_package.py`, `tools/scan_anonymity.py`, `tools/selftest_claims.*` | machine-specific repo path / home-directory tool path | 7 |
| `deck/check_package.py`, `deck/validate_pptx.py` | machine-specific repo path | 2 |

The 11479 inside the source zip are the same matches `source/anonymity_scan.md` reports for the
archive; they sit in the frozen-audit records (`seed_check.json`, `provenance.json`) and in the two
documents that quote the agent-run paths, and they are left byte-identical because those files are
hash-checked against `results/freeze/freeze_manifest.json`.

## Conclusion

**报告中的识别字符串已替换为占位符；交付物中未发现识别信息。** Every file under `submission/` was
scanned for user names (any suffix of the repository's recorded git identity), e-mail addresses,
personal names, institution names and local user paths: **0 identifying hits**. The only remaining
matches are machine-specific build paths that carry no personal identifier, reported above and left
byte-identical because the frozen-audit records they live in are hash-checked.
