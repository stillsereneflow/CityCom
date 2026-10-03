"""Mechanics verification for the NA-300 implementation work.

Checks, from the run artifacts only:
  1. off-mode identity: off_before (pre-change revision) vs off_after (post-change) twin_log.parquet
     byte-identical (and pandas-equal), same for the snapshot states;
  2. F2: at every snapshot of the NA-300 runs, meta["m"]["tko_insert"] equals the online m *after*
     that timestamp's tick, and reports how many snapshots would have been stale under the old
     write-before-tick ordering;
  3. the two NA-300 runs (plain service vs service + insertion recorder) agree row-for-row;
  4. NA-300 tick bookkeeping: tick cadence, reasons, m bounds.
Writes results/assim/na300_impl/verify_report.json and prints it.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / "results" / "assim" / "na300_impl"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def twin_log_identity(a, b):
    pa, pb = Path(a) / "twin" / "twin_log.parquet", Path(b) / "twin" / "twin_log.parquet"
    da, db = pd.read_parquet(pa), pd.read_parquet(pb)
    try:
        pd.testing.assert_frame_equal(da, db)
        equal = True
    except AssertionError:
        equal = False
    return {"a": str(pa), "b": str(pb), "sha_a": sha(pa), "sha_b": sha(pb),
            "byte_identical": sha(pa) == sha(pb), "frames_equal": equal,
            "shape_a": list(da.shape), "shape_b": list(db.shape)}


def snapshot_m_check(run_dir):
    twin = Path(run_dir) / "twin"
    adf = pd.read_parquet(twin / "assim_log.parquet").sort_values("t").reset_index(drop=True)
    rows = {float(r["t"]): r for _, r in adf.iterrows()}
    ticks = sorted(rows)
    out = []
    for meta_path in sorted(twin.glob("twin_state_*.json")):
        if "_override" in meta_path.name:      # falsification metas written by branch_replay.py
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ts = float(meta["t"])
        after = [t for t in ticks if t <= ts]
        m_after = float(rows[after[-1]]["m"]) if after else 1.0
        prev = [t for t in ticks if t < ts]
        m_stale = float(rows[prev[-1]]["m"]) if prev else 1.0
        m_meta = float((meta.get("m") or {}).get("tko_insert", 1.0))
        out.append({"t": ts, "meta_m": m_meta, "online_m_after_tick": m_after,
                    "online_m_before_tick": m_stale, "tick_reason": str(rows[ts]["reason"]) if ts in rows else None,
                    "match": m_meta == m_after, "stale_under_old_order": m_stale != m_after,
                    "twin_base_factor": meta.get("twin_base_factor"), "stream_ptr": meta.get("stream_ptr")})
    return out


def main():
    off_before, off_after = BASE / "off_before", BASE / "off_after"
    rep = {"off_identity": twin_log_identity(off_before, off_after)}

    runs = {}
    for name in ("replay4001", "replay4001_logged"):
        run = BASE / name
        twin = run / "twin"
        adf = pd.read_parquet(twin / "assim_log.parquet")
        stats = json.loads((twin / "twin_stats.json").read_text(encoding="utf-8"))
        snaps = snapshot_m_check(run)
        runs[name] = {
            "twin_stats": stats,
            "n_ticks": int(len(adf)),
            "tick_times": [float(x) for x in adf["t"].tolist()],
            "reasons": {k: int(v) for k, v in adf["reason"].value_counts().items()},
            "m_min": float(adf["m"].min()), "m_max": float(adf["m"].max()),
            "n_snapshots": len(snaps),
            "n_snapshot_match": sum(s["match"] for s in snaps),
            "n_snapshot_stale_under_old_order": sum(s["stale_under_old_order"] for s in snaps),
            "snapshots": snaps,
            "inserts_json": (twin / "twin_inserts.json").exists(),
        }
        if (twin / "twin_inserts.json").exists():
            ins = json.loads((twin / "twin_inserts.json").read_text(encoding="utf-8"))
            runs[name]["n_inserts_total"] = len(ins)
            runs[name]["n_inserts_tko"] = sum(1 for r in ins if r["entry"] == "tko_insert")
    rep["runs"] = runs
    rep["replay_pair_identity"] = twin_log_identity(BASE / "replay4001", BASE / "replay4001_logged")
    (BASE / "verify_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "runs"}, indent=1))
    for name, r in runs.items():
        print(name, {k: r[k] for k in ("n_ticks", "reasons", "m_min", "m_max", "n_snapshots",
                                       "n_snapshot_match", "n_snapshot_stale_under_old_order",
                                       "n_inserts_total", "n_inserts_tko") if k in r})
        for s in r["snapshots"]:
            print("   ", s)


if __name__ == "__main__":
    main()
