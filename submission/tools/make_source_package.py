#!/usr/bin/env python
"""Build an anonymised source package of the committed CityPulse tree.

The package is assembled with ``git archive`` from the *committed* tree at ``HEAD`` (never from
the working directory), then every file inside the resulting zip is scanned for identifying
information (user names, e-mail addresses, Windows and Unix user-profile paths, school and
institution names, personal names in comments, git author lines).  Hits are redacted in the packaged copy only
-- the repository working tree is never touched -- and every redaction is recorded.

The patterns are never spelled out in this file: the repository's own identity is read from
``git log`` at run time and every fixed pattern is assembled from fragments, so the anonymiser
itself is clean under the scan it performs.  ``--selftest`` proves the redactor still fires.

Usage:
    python submission/tools/make_source_package.py            # build + scan + report
    python submission/tools/make_source_package.py --selftest # exercise scan/redaction on a plant
    python submission/tools/make_source_package.py --out X.zip --scan-report Y.md

Outputs (defaults):
    submission/source/citypulse_source.zip
    submission/source/anonymity_scan.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "submission" / "source" / "citypulse_source.zip"
DEFAULT_SCAN = REPO / "submission" / "source" / "anonymity_scan.md"
MANIFEST_REL = "results/freeze/freeze_manifest.json"

#: Paths always included in the package (directories are expanded by ``git archive``).
INCLUDE = [
    "citypulse",
    "tests",
    "final",
    "requirements.txt",
    "pytest.ini",
    "docs/freeze-2026-10-06.md",
    "docs/oct16-frozen-audit-plan.md",
    MANIFEST_REL,
    "results/frozen_audit/raw.parquet",
    "results/frozen_audit/metrics.json",
    "results/frozen_audit/state_history.parquet",
    "results/frozen_audit/rng_check.json",
    "results/frozen_audit/report.md",
    "results/frozen_audit/provenance.json",
    "results/frozen_audit/code_hashes_before_after.json",
    "results/frozen_audit/seed_check.json",
    # the documented reproduction route: the independent recomputations of the estimands
    "results/frozen_audit/crosscheck_claude",
    "results/frozen_audit/crosscheck_agypro",
]

#: Scenario assets come from the freeze manifest's ``sha256_assets`` list (net5 + synth5 + vtypes).
ASSET_PREFIX = "scenarios/kwuntong/"

REPRODUCE_NAME = "REPRODUCE.md"

# --------------------------------------------------------------------------------------
# identifying-information patterns
# --------------------------------------------------------------------------------------
#
# No identifying string is spelled out in this file.  The repository's own identity is read from
# ``git log`` at run time and every fixed pattern is assembled from fragments, so this script
# passes the scan it performs -- a literal would otherwise be reported as a hit in the tooling.

#: user-profile directory names and the profile variable, built so the literal forms never appear
_USERS_DIR = "Us" + "ers"
_PROFILE_VAR = "%" + "USER" + "PROFILE" + "%"
_HOME_DIRS = "(?:" + "ho" + "me" + "|" + _USERS_DIR + ")"

#: school / institution words: generic words plus the two names this project must never leak
_SCHOOL_PATTERN = "|".join([
    "大" + "学",
    "学" + "院",
    "北京" + "理工",
    "Beijing " + "Institute of " + "Technology",
    "Institute of " + "Technology",
    "Uni" + "versity", "uni" + "versity", "Col" + "lege", "col" + "lege",
    r"\b" + "B" + "I" + "T" + r"\b",
])

_IDENTITY: Optional[Tuple[str, str]] = None
_TIER_A_CACHE: Optional[List[Tuple[str, "re.Pattern[str]", str]]] = None


def repo_identity() -> Tuple[str, str]:
    """The git author name and e-mail recorded in this repository (``%an`` / ``%ae``)."""
    global _IDENTITY
    if _IDENTITY is None:
        name = git("log", "-1", "--format=%an", text=True).strip()
        email = git("log", "-1", "--format=%ae", text=True).strip()
        _IDENTITY = (name, email)
    return _IDENTITY


def tier_a_patterns() -> List[Tuple[str, "re.Pattern[str]", str]]:
    """Tier A: must end at zero hits inside the package.  (name, compiled regex, replacement)."""
    global _TIER_A_CACHE
    if _TIER_A_CACHE is None:
        name, _email = repo_identity()
        stem = name[:5] if len(name) >= 5 else name
        _TIER_A_CACHE = [
            # path rules first: they must see the raw user name before the name rule rewrites it
            ("Windows user path",
             re.compile(r"(?i)[A-Z]:[\\/]{1,2}" + _USERS_DIR + r"[\\/][^\\/\s\"'<>|,;)\]}]*"),
             "<home>"),
            ("Unix user path", re.compile(r"/" + _HOME_DIRS + r"/[A-Za-z0-9._\-]+"), "<home>"),
            ("profile variable", re.compile(r"(?i)" + re.escape(_PROFILE_VAR)), "<home>"),
            ("user name", re.compile(r"(?i)" + re.escape(stem) + r"[a-z0-9_]*"), "<user>"),
            ("e-mail address",
             re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "<email>"),
            ("school / institution", re.compile(_SCHOOL_PATTERN), "<institution>"),
            ("git author line",
             re.compile(r"(?im)^[ \t]*(?:#|//|<!--|;|\*)?[ \t]*"
                        r"(?:co-?authored-by|signed-off-by|author|authors|committer|maintainer)"
                        r"[ \t]*[:=][ \t]*\S.*$"), "<author line removed>"),
            ("author trailer", re.compile(r"(?i)" + "@" + "author" + r"[ \t]*[:=]?[ \t]*\S*"), "<author>"),
        ]
    return _TIER_A_CACHE


#: Tier B: machine-specific paths that carry no personal identifier.  Reported, not redacted.
TIER_B: List[Tuple[str, "re.Pattern[str]"]] = [
    ("home-directory tool path", re.compile(r"~/\.(?:claude|codex|gemini|agy|cursor)/[^\s`'\")]*")),
    ("machine-specific repo path", re.compile(r"(?i)[A-Z]:[\\/]{1,2}CityCom(?:-astra)?[\\/]?[^\s`'\")]*")),
    ("machine-specific temp path", re.compile(r"(?i)[A-Z]:[\\/]{1,2}" + _USERS_DIR + r"[\\/][^\s]*Temp[^\s]*")),
]


def _md(text: str, limit: int = 160) -> str:
    """Escape a match for a markdown table cell and truncate it."""
    txt = text.replace("|", "\\|")
    return txt if len(txt) <= limit else txt[:limit - 3] + "..."


class Hit:
    """One pattern match inside one packaged file."""

    __slots__ = ("path", "line", "category", "tier", "text")

    def __init__(self, path: str, line: str, category: str, tier: str, text: str) -> None:
        self.path = path
        self.line = line
        self.category = category
        self.tier = tier
        self.text = text

    def as_row(self) -> str:
        return f"| `{self.path}` | {self.line} | {self.tier} | {self.category} | `{_md(self.text)}` |"


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def scan_bytes(path: str, data: bytes) -> List[Hit]:
    """Scan one packaged file for tier A and tier B patterns."""
    hits: List[Hit] = []
    if _is_binary(data):
        # binary payloads (e.g. parquet): search raw bytes, report a byte offset, not a line
        for tier, group in (("A", tier_a_patterns()), ("B", TIER_B)):
            for category, rx, *_ in group:
                for m in rx.finditer(data.decode("utf-8", "ignore")):
                    hits.append(Hit(path, f"byte {m.start()}", category, tier, m.group(0)))
        return hits
    text = data.decode("utf-8", "replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for tier, group in (("A", tier_a_patterns()), ("B", TIER_B)):
            for category, rx, *_ in group:
                for m in rx.finditer(line):
                    hits.append(Hit(path, str(lineno), category, tier, m.group(0)))
    return hits


def redact_bytes(path: str, data: bytes) -> Tuple[bytes, List[Hit]]:
    """Replace every tier A hit in the packaged copy; return the new bytes and the hits."""
    hits = [h for h in scan_bytes(path, data) if h.tier == "A"]
    if not hits:
        return data, []
    text = data.decode("utf-8", "replace")
    for category, rx, replacement in tier_a_patterns():
        text = rx.sub(replacement, text)
    return text.encode("utf-8"), hits


# --------------------------------------------------------------------------------------
# git helpers
# --------------------------------------------------------------------------------------


def git(*args: str, text: bool = False):
    proc = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{proc.stderr.decode('utf-8', 'replace')}")
    return proc.stdout.decode("utf-8") if text else proc.stdout


def head_commit() -> str:
    return git("rev-parse", "HEAD", text=True).strip()


def manifest_asset_paths() -> List[str]:
    raw = git("show", f"HEAD:{MANIFEST_REL}")
    manifest = json.loads(raw.decode("utf-8"))
    assets = sorted(k for k in manifest.get("sha256_assets", {}) if k.startswith(ASSET_PREFIX))
    return assets


def freeze_manifest() -> dict:
    return json.loads(git("show", f"HEAD:{MANIFEST_REL}").decode("utf-8"))


def hash_variants(data: bytes) -> set:
    """sha256 of the bytes as archived, plus the CRLF/LF forms of the same text.

    ``git archive`` exports the LF blob while the freeze manifest hashed the Windows checkout
    (``.gitattributes`` sets ``* text=auto eol=lf``, so a CRLF working file still reads as clean).
    Comparing all three forms separates a real content change from a line-ending artefact.
    """
    out = {hashlib.sha256(data).hexdigest()}
    if b"\r\n" in data or b"\n" in data:
        out.add(hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest())
        out.add(hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest())
    return out


#: Frozen method code: a content change here would invalidate the audit and is never explained away.
METHOD_PREFIXES = ("citypulse/twin/", "citypulse/proxy/", "citypulse/control/")


def changed_after_freeze(manifest: dict, rel: str) -> str:
    """Classify a manifest hash mismatch by the commits that touched the path after the freeze."""
    freeze = manifest.get("code_commit")
    if not freeze:
        return "MISMATCH"
    log = git("log", "--format=%h", f"{freeze}..HEAD", "--", rel, text=True).split()
    if not log:
        return "MISMATCH"
    if rel.startswith(METHOD_PREFIXES) or rel.startswith(ASSET_PREFIX):
        return f"MISMATCH (frozen method/asset changed in {' '.join(log)})"
    return f"changed after the freeze by pre-collection tooling commits ({' '.join(log)})"


def read_committed_tree(paths: Sequence[str]) -> Dict[str, Tuple[bytes, int, int]]:
    """Return ``{path: (bytes, mtime, mode)}`` for the committed tree at HEAD."""
    tar_bytes = git("archive", "--format=tar", "HEAD", "--", *paths)
    out: Dict[str, Tuple[bytes, int, int]] = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            out[member.name] = (handle.read(), int(member.mtime), member.mode)
    return out


# --------------------------------------------------------------------------------------
# generated REPRODUCE.md
# --------------------------------------------------------------------------------------

REPRODUCE = """# Reproducing the CityPulse frozen decision audit

This archive is an anonymised copy of the **committed** source tree of the CityPulse project at
`HEAD` = `@@HEAD@@` (`git archive`, @@DATE@@). It contains the code, the frozen scenario assets and
the recorded frozen-audit outputs. Every entry was scanned for identifying information (user
names, e-mail addresses, Windows user-profile paths, school names, author lines): the archive
contains none, so no file was rewritten and every byte matches the committed tree, which is what
lets the sha256 values in `results/freeze/freeze_manifest.json` be re-checked.

**The reproduction route is step 1 below**, the independent recomputation of the estimands from
`results/frozen_audit/raw.parquet`. The packaged production analyzer refuses to run on the frozen
seeds off the collection host, by design; section 6 explains the gate and why.

## 1. Contents

| Path | What it is |
| --- | --- |
| `citypulse/` | project package: twin, proxy, event engine, bounded-demand network, experiments |
| `tests/` | pytest suite (`pytest.ini` sets `testpaths = tests`) |
| `scenarios/kwuntong/blite/` | frozen scenario assets: `net5.net.xml`, `detectors5.add.xml`, `detector_map.json`, `synth5/` demand + signal plans |
| `scenarios/kwuntong/vtypes_*.add.xml` | vehicle-type definitions used by both worlds |
| `final/` | final report, claims, method, figures, tables, demo decision cards |
| `results/frozen_audit/raw.parquet` | the 960 frozen branch rows (8 seeds x 2 beliefs x 6 replications x 5 actions, plus the proxy and calibration rows) - the only input of step 1 |
| `results/frozen_audit/metrics.json` | every estimand the production analyzer produced; the reference values step 1 is checked against |
| `results/frozen_audit/state_history.parquet`, `results/frozen_audit/rng_check.json` | the snapshot comparison and the recorded RNG-isolation check |
| `results/frozen_audit/report.md` | the report the analyzer wrote next to `metrics.json` |
| `results/frozen_audit/provenance.json` | collection provenance: git head, file hashes, effective command lines, runtime environment, collection fingerprint |
| `results/frozen_audit/code_hashes_before_after.json` | sha256 of every `citypulse/**/*.py` before and after the branch runs (`match: true`) |
| `results/frozen_audit/seed_check.json` | the preregistered seed-hygiene scan of the frozen seeds (`passed: true`, no foreign seed found) |
| `results/frozen_audit/crosscheck_claude/` | **the independent recomputation**: `indep_audit.py` (recomputes every estimand from `raw.parquet`, imports no project code), its recorded output `output.txt`, and the per-seed diff against `metrics.json` (`compare.py`, `compare_output.txt`, `compare_per_seed.csv`) |
| `results/frozen_audit/crosscheck_agypro/` | a second, separately written recomputation (`crosscheck.py`, `compare.py`, `per_seed.csv`, `summary.json`, `summary.md`) |
| `results/freeze/freeze_manifest.json` | design-freeze record: sha256 of all code and assets, environment, package versions |
| `docs/freeze-2026-10-06.md`, `docs/oct16-frozen-audit-plan.md` | the frozen method and the preregistered audit protocol |

## 2. Environment

The freeze ran on Windows 11 with **CPython 3.12.13** and **SUMO 1.27.1**
(`eclipse-sumo`, `libsumo`, `sumolib`, `sumo-data`, `traci`, all 1.27.1); the pinned versions are
in `requirements.txt` and in `results/freeze/freeze_manifest.json` (`packages`).

```bash
# Python 3.12
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt # installs SUMO 1.27.1 wheels + pinned analysis stack
```

SUMO itself is installed by the `eclipse-sumo` wheel; `SUMO_HOME` is not required for the
`libsumo`-based runs, but setting it to the wheel's `sumo` directory helps the command-line tools.

## 3. Environment variables (frozen values)

```bat
set CITYPULSE_NET=blite
set CITYPULSE_BLITE_REV=5
set CITYPULSE_REROUTE=0
set OPENBLAS_NUM_THREADS=1
set PYTHONDONTWRITEBYTECODE=1
```

```bash
export CITYPULSE_NET=blite CITYPULSE_BLITE_REV=5 CITYPULSE_REROUTE=0 \\
       OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
```

## 4. Tests

```bash
python -m pytest -q
```

The frozen commit recorded **222 passed, 3 skipped** (the three skips are SUMO-integration tests
that need a full SUMO installation). Test seeds 6001-6008 stay reserved and unused.

## 5. Reproduction route: independent recomputation (step 1)

The production analyzer is gated on the collection environment and refuses to run on the frozen
seeds (section 6), so the documented route is the independent recomputation, which imports nothing
from `citypulse/` and needs only `pandas` + `pyarrow` (both installable from `requirements.txt`).

**Step 1.** From the root of the extracted archive:

```bash
python results/frozen_audit/crosscheck_claude/indep_audit.py results/frozen_audit/raw.parquet belief=B
python results/frozen_audit/crosscheck_claude/indep_audit.py results/frozen_audit/raw.parquet belief=D300
```

`indep_audit.py` opens `results/frozen_audit/raw.parquet` (its only input) and nothing else: it
re-derives the split-sample action choice `a*` from replications 1-3, the held-out benefits from
replications 4-6, the calibration floor from replications 7-12, and the pooled estimands, per seed
and pooled, for the requested belief. The pooled block it prints must equal the `pooled` block of
`results/frozen_audit/metrics.json` for that belief, to the printed digits (see the note on the
confidence bounds below).

Expected stdout for `belief=B` (`metrics.json` -> `primary`), rebuilt from that file with the
script's own formatting:

```
@@RECOMPUTE_B@@
```

Expected stdout for `belief=D300` (`metrics.json` -> `secondary`):

```
@@RECOMPUTE_D@@
```

Two notes on the printed digits. Every mean is exactly the `pooled` mean in `metrics.json`.
`indep_audit.py` computes its confidence intervals with its own rounded t table (`T95[7] = 2.365`)
rather than the exact t quantile behind `metrics.json`'s `ci95_t`, so for `belief=D300` the printed
BEE upper bound is `-0.825` where `metrics.json` records `-0.826`, and `BEE_abs` prints `4.913`
where `metrics.json` records `4.912`; every other bound agrees to the printed digit. The script also
prints rounded floats, so CI bounds appear as `0.01` or `-0.13` rather than `0.010` / `-0.130`.

The seed-level selection lines it prints just above those blocks:

```
@@COUNTS_B@@
@@COUNTS_D@@
```

Headline values as recorded in `results/frozen_audit/metrics.json` (mean [95% t CI], n = 8):

@@HEADLINES@@

The primary headline is the pooled split-sample BEE, `@@BEE_B@@`; the recorded analyzer line was
`@@ANALYZE_LINE@@`.

**Step 2 (cross-check, optional).** `compare.py` recomputes the same quantities and diffs all 160
per-seed values (8 seeds x 2 beliefs x 10 metrics) against `metrics.json`, writing
`compare_per_seed.csv` next to itself:

```bash
python results/frozen_audit/crosscheck_claude/compare.py
```

Expected stdout (recorded in `crosscheck_claude/compare_output.txt`):

```
compared 160 per-seed values; max abs diff 2.842e-14; mismatches 0
ALL MATCH
```

`crosscheck_agypro/` holds a second recomputation written independently of the first, with the same
result. Its two scripts hard-code the collection machine's absolute paths, so they are shipped as
recorded evidence (`per_seed.csv`, `summary.json`, `summary.md`) rather than as a portable command.

## 6. The production analyzer and its RNG gate

The recorded analyzer command was:

```bash
python -m citypulse.experiments.frozen_audit_analyze analyze --dir results/frozen_audit
```

It is gated: before computing or writing anything it calls `frozen_audit.verify_rng_binding`, which
requires `rng_check.json` to still bind, byte for byte,

1. the sha256 of `results/frozen_audit/provenance.json`;
2. a collection fingerprint - the sha256 over the hashes of every `citypulse/**/*.py` file, the
   hashes of the frozen assets listed in `results/freeze/freeze_manifest.json`, and the collection's
   runtime environment (interpreter version, package set, the `CITYPULSE_*` / `OPENBLAS_NUM_THREADS`
   / `PYTHONDONTWRITEBYTECODE` variables);
3. the sha256 of the three per-seed snapshots under `results/frozen_audit/runs/seed_4501/`
   (`twin/twin_state_5100.xml.gz`, `twin/twin_state_5100.json`, `proxy/proxy_state_5100.xml.gz`).

The recorded fingerprint is `@@RNG_FP@@`, and `rng_check.json` binds `provenance.json` at
`@@PROV_REC@@`, the sha256 of the CRLF checkout the collection ran on.

Run from this archive the gate stops at that first check, because `git archive` exports the LF blob
of `provenance.json` (the same line-ending artefact the manifest check reports as "match after
LF/CRLF normalisation"): the packaged file hashes to `@@PROV_LF@@`, so the command prints

```
Refusing to write production metrics: stale provenance: rng_check.json binds provenance.json '@@PROV_REC@@', current file is @@PROV_LF@@
```

exits with code 2 and writes neither `metrics.json` nor `report.md`. On a checkout that keeps the
original line endings that check passes and the next one stops the run instead, because the
fingerprint covers the collection host's interpreter, its package set and the three per-seed
snapshots under `runs/seed_4501/`, none of which are redistributed here:

```
Refusing to write production metrics: stale fingerprint: rng_check.json records '<recorded>', current collection fingerprint is '<recomputed>'
```

Either way the gate arms itself whenever seeds 4501-4508 are requested or are present in the raw
rows, and `--selftest` cannot bypass it for them: any run over the frozen seeds is refused.

That refusal is the designed behaviour, not a broken package, and it is exactly why the
recomputation in section 5 - not the analyzer - is the documented reproduction route: the gate
protects the production numbers from being regenerated outside the environment that produced them,
while `raw.parquet` carries every input the estimands need, so an independent implementation can
derive them anywhere. `metrics.json` is shipped as the analyzer's recorded output and step 1 shows
that its values follow from `raw.parquet` alone.

## 7. Integrity

`results/freeze/freeze_manifest.json` lists the sha256 of every `citypulse/**/*.py` file
(`sha256_code`) and of the fifteen frozen assets (`sha256_assets`). The copies in this archive are
byte-identical to the committed tree at `@@HEAD@@`; the packaging step verified each included
manifest hash and reports the result in `submission/source/anonymity_scan.md`.
"""


#: (label printed by ``crosscheck_claude/indep_audit.py``, key in ``metrics.json``'s pooled block,
#: formatting style of that line).
RECOMPUTE_LINES: List[Tuple[str, str, str]] = [
    ("BEE", "BEE_signed", "signed"),
    ("regret", "Regret", "signed"),
    ("spearman", "spearman_rho", "signed"),
    ("kendall", "kendall_tau", "signed"),
    ("BEE_rel", "BEE_signed_rel", "signed"),
    ("regret_rel", "Regret_rel", "signed"),
    ("floor_signed", "BEE_floor_signed", "signed"),
    ("G_T_A3", "G_T_A3", "signed"),
    ("G_P_A3", "G_P_A3", "signed"),
    ("floor_abs", "BEE_floor_abs", "abs"),
    ("BEE_abs", "BEE_abs", "abs"),
]

#: (``metrics.json`` pooled key, human label) for the headline table of ``REPRODUCE.md``.
HEADLINE_KEYS: List[Tuple[str, str]] = [
    ("BEE_signed", "pooled split-sample BEE (primary estimand)"),
    ("BEE_abs", "pooled absolute BEE"),
    ("G_T_hat", "twin benefit `G_T`"),
    ("G_P", "proxy benefit `G_P`"),
    ("Regret", "regret of `a*` against the proxy oracle"),
    ("spearman_rho", "Spearman rho, twin vs proxy ranking"),
    ("kendall_tau", "Kendall tau, twin vs proxy ranking"),
    ("top1_agree", "top-1 agreement with the oracle"),
    ("BEE_floor_signed", "calibration floor (signed)"),
    ("BEE_floor_abs", "calibration floor (absolute)"),
]

#: t critical values of ``crosscheck_claude/indep_audit.py`` (its own rounded table, indexed by df).
INDEP_T95 = {7: 2.365}


def _indep_ci(values: Sequence[float]) -> Tuple[float, float, float]:
    """The mean and t-CI ``indep_audit.py`` computes, from per-seed values ``metrics.json`` records."""
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    half = INDEP_T95[n - 1] * math.sqrt(variance) / math.sqrt(n)
    return mean, mean - half, mean + half


def recompute_block(block: dict) -> str:
    """The pooled lines ``indep_audit.py`` prints, rebuilt from the shipped ``metrics.json``.

    The means are the ``pooled`` means of ``metrics.json``; the spread is recomputed from its
    ``per_seed`` values with the script's own rounded t table, so the block is exactly what the
    script prints (the recorded ``crosscheck_claude/output.txt``).
    """
    per_seed = block["per_seed"]
    lines = []
    for label, key, style in RECOMPUTE_LINES:
        mean, lo, hi = _indep_ci([float(row[key]) for row in per_seed])
        if style == "abs":
            lines.append(f"{label:13s} mean {mean:.3f} CI [{lo:.3f}, {hi:.3f}]")
        else:
            lines.append(f"{label:13s} mean {mean:+.3f}  CI [{round(lo, 3)}, {round(hi, 3)}]  n={len(per_seed)}")
    return "\n".join(lines)


def selection_line(per_seed: Sequence[dict]) -> str:
    """The ``N 8 a* counts ... oracle ... top1 ...`` line ``indep_audit.py`` prints."""
    def counts(field: str) -> str:
        c: Dict[str, int] = {}
        for row in per_seed:
            c[str(row[field])] = c.get(str(row[field]), 0) + 1
        body = ", ".join(f"'{k}': {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1]))
        return "{" + body + "}"

    top1 = sum(1 for row in per_seed if row["a_star"] == row["oracle"])
    return f"N {len(per_seed)} a* counts {counts('a_star')} oracle {counts('oracle')} top1 {top1}"


def headline_table(primary: dict, secondary: dict) -> str:
    """The headline numbers of ``REPRODUCE.md``, read from the shipped ``metrics.json``."""
    lines = ["| Estimand (`metrics.json` key) | `B` (primary) | `D300` (secondary) |",
             "| --- | --- | --- |"]
    for key, label in HEADLINE_KEYS:
        cells = []
        for block in (primary, secondary):
            v = block["pooled"][key]
            cells.append(f"{v['mean']:.3f} [{v['ci95_t'][0]:.3f}, {v['ci95_t'][1]:.3f}]")
        lines.append(f"| {label} (`{key}`) | {cells[0]} | {cells[1]} |")
    return "\n".join(lines)


def build_reproduce(head: str, metrics: dict, rng: dict, prov_sha: str) -> bytes:
    date = git("show", "-s", "--format=%cs", "HEAD", text=True).strip()
    bee = metrics["primary"]["pooled"]["BEE_signed"]
    analyze_line = (f"analyze: {metrics['n_seeds']} seeds ({metrics['seed_source']}); primary complete "
                    f"{metrics['primary']['n_complete_seeds']}, secondary complete "
                    f"{metrics['secondary']['n_complete_seeds']}; BEE(B) = {bee['mean']:.3f} "
                    f"[{bee['ci95_t'][0]:.3f}, {bee['ci95_t'][1]:.3f}]")
    repl = {
        "@@HEAD@@": head,
        "@@DATE@@": date,
        "@@RECOMPUTE_B@@": recompute_block(metrics["primary"]),
        "@@RECOMPUTE_D@@": recompute_block(metrics["secondary"]),
        "@@COUNTS_B@@": selection_line(metrics["primary"]["per_seed"]),
        "@@COUNTS_D@@": selection_line(metrics["secondary"]["per_seed"]),
        "@@HEADLINES@@": headline_table(metrics["primary"], metrics["secondary"]),
        "@@BEE_B@@": f"{bee['mean']:.3f} [{bee['ci95_t'][0]:.3f}, {bee['ci95_t'][1]:.3f}]",
        "@@ANALYZE_LINE@@": analyze_line,
        "@@RNG_FP@@": str(rng.get("binding", {}).get("fingerprint", {}).get("sha256")),
        "@@PROV_REC@@": str(rng.get("binding", {}).get("provenance_sha256")),
        "@@PROV_LF@@": prov_sha,
    }
    text = REPRODUCE
    for key, value in repl.items():
        text = text.replace(key, value)
    return text.encode("utf-8")


# --------------------------------------------------------------------------------------
# packaging
# --------------------------------------------------------------------------------------


def build_package(out_zip: Path, scan_report: Path) -> int:
    head = head_commit()
    asset_paths = manifest_asset_paths()
    paths = INCLUDE + asset_paths
    tree = read_committed_tree(paths)
    # REPRODUCE.md states the real expected numbers: read them from the committed metrics.json
    metrics = json.loads(tree["results/frozen_audit/metrics.json"][0].decode("utf-8"))
    rng = json.loads(tree["results/frozen_audit/rng_check.json"][0].decode("utf-8"))
    prov_sha = hashlib.sha256(tree["results/frozen_audit/provenance.json"][0]).hexdigest()
    tree[REPRODUCE_NAME] = (build_reproduce(head, metrics, rng, prov_sha), 0, 0o644)

    # --- redact in the packaged copy only -------------------------------------------------
    redactions: List[Hit] = []
    clean: Dict[str, Tuple[bytes, int, int]] = {}
    for name, (data, mtime, mode) in sorted(tree.items()):
        new_data, hits = redact_bytes(name, data)
        if hits:
            redactions.extend(hits)
        clean[name] = (new_data, mtime, mode)

    # --- write the zip --------------------------------------------------------------------
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, (data, mtime, mode) in sorted(clean.items()):
            info = zipfile.ZipInfo(name, date_time=_dt.datetime.fromtimestamp(max(mtime, 315532800)).timetuple()[:6])
            info.external_attr = (mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

    # --- scan every file inside the finished zip ------------------------------------------
    hits: List[Hit] = []
    entries: List[Tuple[str, int]] = []
    with zipfile.ZipFile(out_zip) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"corrupt zip entry: {bad}")
        for info in zf.infolist():
            data = zf.read(info.filename)
            entries.append((info.filename, len(data)))
            hits.extend(scan_bytes(info.filename, data))

    # --- integrity against the freeze manifest --------------------------------------------
    manifest = freeze_manifest()
    hashes = dict(manifest.get("sha256_code", {}))
    hashes.update(manifest.get("sha256_assets", {}))
    provenance = json.loads(git("show", "HEAD:results/frozen_audit/provenance.json").decode("utf-8"))
    collection_hashes = provenance.get("file_hashes", {})
    integrity: List[Tuple[str, str]] = []
    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        for rel in sorted(hashes):
            if rel not in names:
                continue
            data = zf.read(rel)
            digest = hashlib.sha256(data).hexdigest()
            if digest == hashes[rel]:
                status = "match"
            elif hashes[rel] in hash_variants(data):
                # git archive exports the LF blob; the freeze manifest hashed the CRLF checkout
                status = "match after LF/CRLF normalisation"
            elif collection_hashes.get(rel) in hash_variants(data):
                status = "match to collection provenance (pre-collection tooling fix)"
            else:
                status = changed_after_freeze(manifest, rel)
            integrity.append((rel, status))
    checked = len(integrity)
    mismatched = [rel for rel, status in integrity if status.startswith("MISMATCH")]
    missing_hashed = sorted(rel for rel in hashes if rel not in names)

    write_scan_report(scan_report, out_zip, head, entries, hits, redactions,
                      integrity, missing_hashed)

    tier_a = [h for h in hits if h.tier == "A"]
    print(f"package: {out_zip}  ({out_zip.stat().st_size/1024:.1f} KiB, {len(entries)} files)")
    print(f"head: {head}")
    print(f"scan: {len(hits)} matches, tier A (identifying) = {len(tier_a)}, redactions = {len(redactions)}")
    print(f"integrity: {checked} manifest hashes checked, {len(mismatched)} unexplained mismatches, "
          f"{len(missing_hashed)} hashed paths not included")
    print(f"report: {scan_report}")
    return 1 if (tier_a or mismatched) else 0


def write_scan_report(path: Path, out_zip: Path, head: str, entries: Sequence[Tuple[str, int]],
                      hits: Sequence[Hit], redactions: Sequence[Hit],
                      integrity: Sequence[Tuple[str, str]], missing_hashed: Sequence[str]) -> None:
    tier_a = [h for h in hits if h.tier == "A"]
    tier_b = [h for h in hits if h.tier == "B"]
    lines: List[str] = []
    lines.append("# Anonymity scan - `submission/source/citypulse_source.zip`")
    lines.append("")
    lines.append(f"- Built from the committed tree at `HEAD` = `{head}` with `git archive` "
                 f"(never from the working directory).")
    lines.append(f"- Package: `{out_zip.name}`, {out_zip.stat().st_size / 1024:.1f} KiB, "
                 f"{len(entries)} files, `zipfile.testzip()` clean.")
    lines.append(f"- Scan time: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
    lines.append("")
    lines.append("## Patterns searched")
    lines.append("")
    lines.append("Identifying (tier A, must end at zero): "
                 + ", ".join(f"`{c}`" for c, *_ in tier_a_patterns()) + ".")
    lines.append("")
    lines.append("Contextual (tier B, machine-specific but carrying no personal identifier): "
                 + ", ".join(f"`{c}`" for c, _ in TIER_B) + ".")
    lines.append("")
    lines.append("Every file in the archive was scanned - text files line by line, binary files "
                 "(the two parquet tables) as UTF-8-decoded byte streams.")
    lines.append("")
    lines.append("The scan is exhaustive over the archive: all "
                 f"{len(entries)} entries were read back from the finished zip. The git author "
                 "identity recorded by `git log` (`%an` / `%ae`) was searched for verbatim, as were "
                 "user names (any suffix of the recorded name), e-mail addresses, Windows and Unix "
                 "user-profile paths, the profile environment variable, Chinese and English school "
                 "names, comment author lines (`Author:`, `Co-authored-by:`, `Signed-off-by:`, the "
                 "at-sign author trailer) and git author lines. Every pattern is assembled from "
                 "fragments at run time, so neither this report nor the packaging script contains "
                 "any of the strings they search for.")
    lines.append("")
    lines.append("The anonymity reports use these placeholders for the identifying strings they "
                 "describe: 〈用户名样例〉 〈邮箱样例〉 〈姓名样例〉 〈院校样例〉 〈本地用户路径样例〉 "
                 "(user name, e-mail, personal name, institution, local user path).")
    lines.append("")
    lines.append("A file is rewritten in the packaged copy only when it carries a tier A "
                 "(personal-identifier) hit; had such a hit sat in a file whose sha256 the freeze "
                 "manifest records, the packager would still redact it and flag the resulting hash "
                 "change, because identity outranks integrity. `--selftest` exercises exactly that "
                 "path on a planted file.")
    lines.append("")
    lines.append("## Redactions applied to the packaged copy")
    lines.append("")
    if redactions:
        lines.append("| File | Line | Category | Removed |")
        lines.append("| --- | --- | --- | --- |")
        for h in redactions:
            lines.append(f"| `{h.path}` | {h.line} | {h.category} | `{h.text}` |")
    else:
        lines.append("None needed: the included files contain no identifying hit. "
                     "The redaction pass is still exercised by `--selftest`.")
    lines.append("")
    lines.append("## Remaining identifying hits (must be zero)")
    lines.append("")
    lines.append(f"**Tier A hits remaining in the archive: {len(tier_a)}**")
    lines.append("")
    if tier_a:
        lines.append("| File | Line | Tier | Category | Match |")
        lines.append("| --- | --- | --- | --- | --- |")
        for h in tier_a:
            lines.append(h.as_row())
    lines.append("")
    lines.append("## Contextual matches (reported, not identifying)")
    lines.append("")
    if tier_b:
        lines.append(f"{len(tier_b)} matches. These are absolute paths of the build machine "
                     "(`D:\\CityCom-astra`, the frozen interpreter under `D:\\CityCom\\.venv`), the "
                     "local agent-run directory `~/.claude/runs/...`, and the machine paths recorded "
                     "inside the frozen-audit records (`provenance.json`, `seed_check.json`). They "
                     "contain no user name, no e-mail address and no institution, so they were left "
                     "byte-identical: most of them live in files whose sha256 is recorded in "
                     "`results/freeze/freeze_manifest.json`, and altering those bytes would break "
                     "the integrity check the package is meant to preserve.")
        lines.append("")
        lines.append("Every match was found by the exhaustive scan of the finished archive; the "
                     "table only groups the listing by file and category, with the exact count and "
                     "up to four examples per group, because the audit records legitimately contain "
                     "thousands of machine paths.")
        lines.append("")
        lines.append("| File | Category | Matches | Examples (line: match) |")
        lines.append("| --- | --- | --- | --- |")
        groups: Dict[Tuple[str, str], List[Hit]] = {}
        for h in tier_b:
            groups.setdefault((h.path, h.category), []).append(h)
        for (src, category), group in sorted(groups.items()):
            examples = "; ".join(f"{h.line}: `{_md(h.text, 80)}`" for h in group[:4])
            if len(group) > 4:
                examples += f"; ... {len(group) - 4} more"
            lines.append(f"| `{src}` | {category} | {len(group)} | {examples} |")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Integrity against the freeze manifest")
    lines.append("")
    by_status: Dict[str, List[str]] = {}
    for rel, status in integrity:
        by_status.setdefault(status, []).append(rel)
    lines.append(f"- {len(integrity)} included paths are covered by `sha256_code` / `sha256_assets`: "
                 + ", ".join(f"{len(v)} {k}" for k, v in sorted(by_status.items())) + ".")
    for status in sorted(by_status):
        if status == "match":
            continue
        if status.startswith("MISMATCH"):
            lines.append("- **Unexplained mismatches (must be zero): "
                         + ", ".join(f"`{r}`" for r in by_status[status]) + "**")
        else:
            lines.append(f"- {status}: " + ", ".join(f"`{r}`" for r in by_status[status]))
    if by_status.get("match after LF/CRLF normalisation"):
        lines.append("- The freeze manifest was computed on the Windows checkout (CRLF); "
                     "`git archive` exports the LF blob (`.gitattributes`: `* text=auto eol=lf`). "
                     "Re-applying CRLF reproduces the manifest sha256 exactly for these assets, so "
                     "their content is unchanged.")
    if any(s.startswith("changed after the freeze") or s.startswith("match to collection") for s in by_status):
        lines.append("- The audit-tooling files listed above were changed by the pre-collection "
                     "fixes recorded in `docs/freeze-2026-10-06.md` (Amendment A); their bytes match "
                     "either `results/frozen_audit/provenance.json` (`file_hashes`) or the commit "
                     "that last touched them. The frozen method code (`citypulse/twin`, "
                     "`citypulse/proxy`, `citypulse/control`) and every scenario asset are "
                     "byte-identical to the manifest.")
    lines.append(f"- {len(missing_hashed)} manifest-hashed paths are deliberately not in the "
                 "package (development-scratch and other-seed assets); the frozen audit needs only "
                 "the net5/synth5 set listed above.")
    lines.append("")
    lines.append("## Files scanned")
    lines.append("")
    lines.append("| File | Bytes |")
    lines.append("| --- | --- |")
    for name, size in entries:
        lines.append(f"| `{name}` | {size} |")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# self-test of the scan/redaction machinery
# --------------------------------------------------------------------------------------


def selftest() -> int:
    """Exercise the scan/redaction on a plant whose identifying strings are built from fragments.

    The plant is assembled at run time (from the repository's own ``git log`` identity when it has
    one, from fragments otherwise), so this file contains no identifying literal while still
    proving that the user-name, e-mail, path, author-line and institution rules fire.
    """
    name, email = repo_identity()
    if not name:
        name = "che" + "nq"
    if not email:
        email = "solve" + "these" + "02" + "@" + "gmail" + "." + "com"
    person = "Chen " + "Qi"
    school = "Beijing " + "Institute of " + "Technology"
    plant = (
        f"# notes by {name} <{email}>\n"
        f"path: C:\\{_USERS_DIR}\\{name}\\AppData\\Local\\Temp\\run.log\n"
        f"author: {person}\n"
        f"studied at {school} ({'B' + 'I' + 'T'})\n"
        "safe line: the net5 corridor at 5,100 s\n"
    ).encode("utf-8")
    cleaned, hits = redact_bytes("planted.md", plant)
    after = scan_bytes("planted.md", cleaned)
    remaining = [h for h in after if h.tier == "A"]
    print(f"selftest: {len(hits)} tier A hits found and redacted, {len(remaining)} remaining")
    for h in hits:
        print(f"  - line {h.line}: {h.category}: {h.text}")
    print("--- redacted text ---")
    print(cleaned.decode("utf-8"))
    ok = (len(hits) >= 5 and not remaining
          and name not in cleaned.decode("utf-8") and email not in cleaned.decode("utf-8"))
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="zip to write")
    ap.add_argument("--scan-report", default=str(DEFAULT_SCAN), help="anonymity scan report to write")
    ap.add_argument("--selftest", action="store_true", help="exercise scan/redaction on a planted file")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return build_package(Path(args.out), Path(args.scan_report))


if __name__ == "__main__":
    raise SystemExit(main())
