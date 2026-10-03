"""G3-v2 (post-hoc amended running-count criterion) on the synthetic B-lite net5 histories.

**No simulation is run.**  This script re-reads the per-seed outputs of the already
completed G1-G3 protocol (``g123_seed<seed>/run.json``, ``history.csv``,
``pending_by_source.csv``), recomputes every retained gate, and adds the G3-v2
running-count criterion frozen by the decision-maker (decision 2026-10-03d).

Retained unchanged (recomputed here from the recorded series, not copied from the
old verdicts):

* G1 (no teleports, no collisions);
* G2 (``scheduled = pending + running + arrived`` read at the same step);
* pending share <= 2%;
* every per-source insertion-backlog 15-min window slope <= +0.05 veh/s;
* every ``pending(TKO) + occupancy(tko_insert)`` 15-min window slope <= +0.05 veh/s.

Replaced: **only** the running-count 15-min window gate.  G3-v2 fits, for each seed
separately, an OLS line *with an intercept* to every recorded running-count sample
with time in the closed interval ``[a, 7200]`` for each ``a`` in
``{900, 1800, 2700, 3600, 4500, 5400, 6300}``; every slope must be <= +0.05 veh/s.
Actual timestamps and the unchanged 60-s sampling are used: no smoothing, no
exclusions, no pooling of seeds and no boundary adjustment.  If an expected sample
is missing in an interval the gate is **unevaluated**, never passed.

The original 15-min running-count window slopes are reported as diagnostics only
(they are the windows that made the original protocol result FAIL on seeds 1002
and 1003; ``g123_report.md`` is left untouched).

Usage::

    python results/blite/synth5/g3v2.py

Writes ``results/blite/synth5/g3v2_report.md`` and, only on a full pass, the
``results/blite/synth5/READY`` hash list.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent                       # results/blite/synth5
ROOT = HERE.parents[2]                                       # repository root
SCEN_BLITE = ROOT / "scenarios" / "kwuntong" / "blite"
SYNTH5 = SCEN_BLITE / "synth5"
NET5 = SCEN_BLITE / "net5.net.xml"
DET5 = SCEN_BLITE / "detectors5.add.xml"
SELF = HERE / "g3v2.py"

SEEDS = (1001, 1002, 1003)
END = 7200
SAMPLE_DT = 60                       # unchanged sampling of the recorded histories
WARMUP = 900
WINDOW = 900
SLOPE_LIMIT = 0.05                   # veh/s
PENDING_SHARE_LIMIT = 0.02
SUFFIX_STARTS = (900, 1800, 2700, 3600, 4500, 5400, 6300)
RUNNING_WINDOW_STARTS = (900, 1800, 2700, 3600, 4500, 5400, 6300)
MODEL = "deepseek-v4.1-flash"


# --------------------------------------------------------------------------- data


def read_history(path):
    """``history.csv`` -> (sorted times, {time: running}, {time: pending_plus_stub})."""
    times, running, stub = [], {}, {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            t = int(row["time"])
            times.append(t)
            running[t] = float(row["running"])
            stub[t] = float(row["pending_plus_stub"])
    times.sort()
    return times, running, stub


def read_backlog(path):
    """``pending_by_source.csv`` -> {source: {time: pending}}."""
    out = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["source"], {})[int(row["time"])] = float(row["pending"])
    return out


def read_run_meta(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------ maths


def ols_slope(times, values):
    """OLS slope of ``values`` on ``times`` **with an intercept** (veh/s)."""
    x = np.asarray(times, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.size < 2:
        return float("nan")
    xm, ym = x.mean(), y.mean()
    sxx = float(((x - xm) ** 2).sum())
    if sxx == 0.0:
        return float("nan")
    return float(((x - xm) * (y - ym)).sum() / sxx)


def window_slopes(samples, starts=RUNNING_WINDOW_STARTS, window=WINDOW, limit=SLOPE_LIMIT):
    """Slope of every complete 15-min window [start, start+window] (closed, as recorded)."""
    out = []
    for start in starts:
        idx = sorted(t for t in samples if start <= t <= start + window)
        slope = ols_slope(idx, [samples[t] for t in idx])
        out.append({"window": [start, start + window], "n": len(idx), "slope": slope,
                    "pass": bool(np.isfinite(slope) and slope <= limit)})
    return out


def suffix_fit(samples, start, end=END, dt=SAMPLE_DT):
    """G3-v2 fit on the closed interval [start, end] of the 60-s sampling grid.

    Returns ``n`` (samples present), ``n_expected`` (samples the unchanged grid
    requires) and the slope; ``complete`` is False as soon as one expected sample
    is missing, which makes the gate unevaluated rather than passed.
    """
    expected = list(range(start, end + 1, dt))
    present = [t for t in expected if t in samples]
    missing = [t for t in expected if t not in samples]
    slope = ols_slope(present, [samples[t] for t in present]) if len(present) >= 2 else float("nan")
    complete = not missing
    return {"window": [start, end], "n": len(present), "n_expected": len(expected),
            "missing": missing, "slope": slope, "complete": bool(complete),
            "pass": bool(complete and np.isfinite(slope) and slope <= SLOPE_LIMIT)}


# ---------------------------------------------------------------------- per seed


def evaluate_seed(seed, run_dir):
    """Recompute every retained gate and the G3-v2 criterion for one seed."""
    times, running, stub = read_history(run_dir / "history.csv")
    backlog = read_backlog(run_dir / "pending_by_source.csv")
    meta = read_run_meta(run_dir / "run.json")
    g2 = meta["g2_terms"]

    # --- retained: G1 and G2, recomputed from the recorded terms -----------------
    teleports, collisions = int(meta["teleports"]), int(meta["collisions"])
    g1_pass = teleports == 0 and collisions == 0
    gap = int(g2["scheduled"]) - (int(g2["pending"]) + int(g2["running"]) + int(g2["arrived"]))
    g2_pass = gap == 0

    # --- retained: pending share -------------------------------------------------
    pending_share = int(g2["pending"]) / max(int(g2["scheduled"]), 1)
    pending_share_pass = pending_share <= PENDING_SHARE_LIMIT

    # --- retained: per-source backlog 15-min window slopes -----------------------
    backlog_windows = {src: window_slopes(series) for src, series in sorted(backlog.items())}
    backlog_pass = all(w["pass"] for rows in backlog_windows.values() for w in rows)

    # --- retained: pending(TKO) + occupancy(tko_insert) window slopes ------------
    stub_windows = window_slopes(stub)
    stub_pass = all(w["pass"] for w in stub_windows)

    # --- replaced: G3-v2 suffix fits on the running count ------------------------
    suffix = [suffix_fit(running, a) for a in SUFFIX_STARTS]
    suffix_evaluated = all(s["complete"] for s in suffix)
    g3v2_pass = suffix_evaluated and all(s["pass"] for s in suffix)

    # --- diagnostics only: the original 15-min running-count window slopes -------
    running_windows = window_slopes(running)

    retained_pass = bool(g1_pass and g2_pass and pending_share_pass
                         and backlog_pass and stub_pass)
    return {
        "seed": seed,
        "n_samples": len(times), "t_first": times[0] if times else None,
        "t_last": times[-1] if times else None,
        "g1": {"teleports": teleports, "collisions": collisions, "pass": bool(g1_pass)},
        "g2": {"scheduled": int(g2["scheduled"]), "pending": int(g2["pending"]),
               "running": int(g2["running"]), "arrived": int(g2["arrived"]),
               "step": int(g2["step"]), "gap": gap, "pass": bool(g2_pass)},
        "pending_share": pending_share, "pending_share_pass": bool(pending_share_pass),
        "backlog_windows": backlog_windows, "backlog_pass": bool(backlog_pass),
        "stub_windows": stub_windows, "stub_pass": bool(stub_pass),
        "suffix": suffix, "suffix_evaluated": bool(suffix_evaluated),
        "g3v2_pass": bool(g3v2_pass),
        "running_windows": running_windows,
        "retained_pass": retained_pass,
        "all_pass": bool(retained_pass and g3v2_pass),
    }


# ------------------------------------------------------------------------- hashes


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def hash_manifest():
    """sha256 of net5, detectors5, every file under synth5/ and this script."""
    files = [NET5, DET5]
    files += sorted(p for p in SYNTH5.rglob("*") if p.is_file())
    files.append(SELF)
    return [(sha256(f), f) for f in files]


def write_ready(path, manifest):
    path.write_text("".join(f"{h}  {f.as_posix()}\n" for h, f in manifest), encoding="utf-8")


# ------------------------------------------------------------------------- report


def yn(ok):
    return "PASS" if ok else "FAIL"


def write_report(path, results, manifest=None, ready_path=None):
    lines = [
        f"MODEL: {MODEL}",
        "# G3-v2: post-hoc amended running-count criterion, synthetic demand, B-lite net5",
        "",
        "## Amendment statement",
        "",
        "This document records an **explicitly post-hoc amendment** of the G3 running-count",
        "criterion (decision 2026-10-03d), made after the original protocol had already been",
        "run and read.  It is not a pre-registered gate and it does not revise the original",
        "result: the original protocol result is **FAIL**, on the running-count 15-min windows",
        "of seeds 1002 and 1003 (seed 1002 running 4500-5400 s +0.05439 veh/s, seed 1003",
        "running 2700-3600 s +0.06142 veh/s, limit +0.05 veh/s).  That verdict is preserved",
        "unchanged in `results/blite/synth5/g123_report.md`; nothing in it was edited, and",
        "`g123_report.md` remains the binding protocol record.",
        "",
        "Every other gate of the original protocol is retained unchanged and is *recomputed*",
        "here from the recorded per-seed outputs (`g123_seed<seed>/run.json`, `history.csv`,",
        "`pending_by_source.csv`): G1, G2, the pending share, every per-source insertion",
        "backlog 15-min window slope and every `pending(TKO) + occupancy(tko_insert)` 15-min",
        "window slope.  Only the running-count 15-min window gate is replaced: G3-v2 fits an",
        "OLS line **with an intercept** to every recorded running-count sample with time in",
        "the closed interval `[a, 7200]` for each `a` in `{900, 1800, 2700, 3600, 4500, 5400,",
        "6300}`, per seed separately, on the actual timestamps and the unchanged 60-s",
        "sampling - no smoothing, no exclusions, no pooling of seeds, no boundary adjustment.",
        "Every slope must be <= +0.05 veh/s; a missing expected sample makes the gate",
        "**unevaluated**, never passed.  **No simulation was run for this document.**",
        "",
        "## 1. Per-seed retained gates and G3-v2 verdict",
        "",
        "| Seed | Samples (60 s) | Teleports | Collisions | G1 | G2 gap | G2 | Pending share | "
        "Backlog slopes | Stub slopes | Retained gates | G3-v2 |",
        "|---|---:|---:|---:|---|---:|---|---:|---|---|---|---|",
    ]
    for r in results:
        backlog_max = max((w["slope"] for rows in r["backlog_windows"].values() for w in rows),
                          default=float("nan"))
        stub_max = max((w["slope"] for w in r["stub_windows"]), default=float("nan"))
        lines.append(
            f"| {r['seed']} | {r['n_samples']} | {r['g1']['teleports']} | "
            f"{r['g1']['collisions']} | **{yn(r['g1']['pass'])}** | {r['g2']['gap']} | "
            f"**{yn(r['g2']['pass'])}** | {r['pending_share']:.3%} "
            f"(**{yn(r['pending_share_pass'])}**) | max {backlog_max:+.5f} "
            f"(**{yn(r['backlog_pass'])}**) | max {stub_max:+.5f} "
            f"(**{yn(r['stub_pass'])}**) | **{yn(r['retained_pass'])}** | "
            f"**{yn(r['g3v2_pass'])}** |")

    lines += ["", "## 2. G3-v2 suffix fits (running count, closed interval [a, 7200])", ""]
    for r in results:
        lines += [f"**seed {r['seed']}** (recorded samples {r['t_first']}-{r['t_last']} s, "
                  f"{r['n_samples']} at 60 s)", "",
                  "| Interval (s) | Samples | Expected | Slope (veh/s) | <= +0.05 |",
                  "|---|---:|---:|---:|---|"]
        for s in r["suffix"]:
            if not s["complete"]:
                verdict = f"**UNEVALUATED** ({len(s['missing'])} missing)"
            else:
                verdict = "yes" if s["pass"] else "**NO**"
            slope = "n/a" if not np.isfinite(s["slope"]) else f"{s['slope']:+.5f}"
            lines.append(f"| {s['window'][0]}-{s['window'][1]} | {s['n']} | {s['n_expected']} | "
                         f"{slope} | {verdict} |")
        worst = max((s["slope"] for s in r["suffix"] if np.isfinite(s["slope"])),
                    default=float("nan"))
        lines += ["",
                  f"G3-v2 verdict for seed {r['seed']}: **{yn(r['g3v2_pass'])}** "
                  f"(worst suffix slope {worst:+.5f} veh/s, limit +0.05 veh/s; "
                  f"all 7 intervals evaluated: {'yes' if r['suffix_evaluated'] else 'NO'}).",
                  ""]

    lines += ["## 3. Retained-gate detail", ""]
    for r in results:
        lines += [f"**seed {r['seed']}**", "",
                  f"- G1: teleports {r['g1']['teleports']}, collisions {r['g1']['collisions']} "
                  f"-> **{yn(r['g1']['pass'])}**",
                  f"- G2 at step {r['g2']['step']}: "
                  f"`{r['g2']['scheduled']} = {r['g2']['pending']} + {r['g2']['running']} + "
                  f"{r['g2']['arrived']}` -> gap {r['g2']['gap']} -> **{yn(r['g2']['pass'])}**",
                  f"- pending share: {r['g2']['pending']}/{r['g2']['scheduled']} = "
                  f"{r['pending_share']:.3%} <= 2% -> **{yn(r['pending_share_pass'])}**",
                  f"- per-source backlog 15-min window slopes (limit +0.05 veh/s) -> "
                  f"**{yn(r['backlog_pass'])}**", "",
                  "| Source | Window (s) | Samples | Slope (veh/s) | Pass |",
                  "|---|---|---:|---:|---|"]
        for src, rows in r["backlog_windows"].items():
            for w in rows:
                lines.append(f"| `{src}` | {w['window'][0]}-{w['window'][1]} | {w['n']} | "
                             f"{w['slope']:+.5f} | {'yes' if w['pass'] else '**NO**'} |")
        lines += ["",
                  f"- `pending(TKO) + occupancy(tko_insert)` 15-min window slopes "
                  f"(limit +0.05 veh/s) -> **{yn(r['stub_pass'])}**", "",
                  "| Window (s) | Samples | Slope (veh/s) | Pass |",
                  "|---|---:|---:|---|"]
        for w in r["stub_windows"]:
            lines.append(f"| {w['window'][0]}-{w['window'][1]} | {w['n']} | {w['slope']:+.5f} | "
                         f"{'yes' if w['pass'] else '**NO**'} |")
        lines.append("")

    lines += ["## 4. Diagnostics: original 15-min running-count window slopes", "",
              "Not a gate in this document - the replaced criterion, listed so the amendment",
              "can be read next to what it replaces.  These are the slopes that made the",
              "original protocol FAIL (marked **NO**).", "",
              "| Seed | Window (s) | Samples | Slope (veh/s) | Original pass |",
              "|---|---|---:|---:|---|"]
    for r in results:
        for w in r["running_windows"]:
            lines.append(f"| {r['seed']} | {w['window'][0]}-{w['window'][1]} | {w['n']} | "
                         f"{w['slope']:+.5f} | {'yes' if w['pass'] else '**NO**'} |")

    lines += ["", "## 5. Caveat", "",
              "G3-v2 is a **finite-horizon operational gate, not proof of stationarity**.  It",
              "asks only whether the recorded running count, over each suffix of the 2 h",
              "horizon that starts at or after the 900 s warm-up, has an OLS trend no steeper",
              "than +0.05 veh/s.  A pass is consistent with a bounded, oscillating or slowly",
              "settling count on this horizon; it does not establish that the corridor is in",
              "steady state, that the trend would stay flat beyond 7,200 s, or that the same",
              "holds for other seeds, demand levels or incidents.  The amendment was chosen",
              "after seeing the original result and is weaker than the replaced gate by",
              "construction: it cannot overturn the original FAIL, only characterise the",
              "running count over the longer suffixes."]

    lines += ["", "## 6. Verdict", ""]
    if all(r["all_pass"] for r in results):
        lines += ["All three seeds pass every retained gate and G3-v2.",
                  "`results/blite/synth5/READY` lists the SHA-256 of "
                  "`scenarios/kwuntong/blite/net5.net.xml`,",
                  "`scenarios/kwuntong/blite/detectors5.add.xml`, every file under",
                  "`scenarios/kwuntong/blite/synth5/` and `results/blite/synth5/g3v2.py`:",
                  ""]
        for h, f in manifest:
            lines.append(f"- `{f.as_posix()}`  `{h}`")
        lines += ["",
                  "The original protocol verdict **FAIL** (seeds 1002 and 1003 running-count",
                  "windows) remains in `g123_report.md`; this READY is issued under the",
                  "post-hoc amended criterion of decision 2026-10-03d only."]
    else:
        failed = [r["seed"] for r in results if not r["all_pass"]]
        lines += [f"Seeds failing: {', '.join(str(s) for s in failed)}.  "
                  "No READY file was written."]
    lines += ["", "REPORT DONE", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- main


def main():
    results = []
    for seed in SEEDS:
        run_dir = HERE / f"g123_seed{seed}"
        r = evaluate_seed(seed, run_dir)
        results.append(r)
        print(f"seed {seed}: G1={yn(r['g1']['pass'])} G2={yn(r['g2']['pass'])} "
              f"pending_share={r['pending_share']:.3%} "
              f"backlog={yn(r['backlog_pass'])} stub={yn(r['stub_pass'])} "
              f"retained={yn(r['retained_pass'])} g3v2={yn(r['g3v2_pass'])} "
              f"suffix_max={max(s['slope'] for s in r['suffix']):+.5f}")

    manifest = None
    ready_path = None
    if all(r["all_pass"] for r in results):
        manifest = hash_manifest()
        ready_path = HERE / "READY"
        write_ready(ready_path, manifest)

    report = HERE / "g3v2_report.md"
    write_report(report, results, manifest=manifest, ready_path=ready_path)
    print(f"report written to {report}")
    if ready_path is not None:
        print(f"READY written to {ready_path} ({len(manifest)} files)")
    else:
        print("no READY written: not every seed passes the retained gates and G3-v2")
    return results


if __name__ == "__main__":
    main()
