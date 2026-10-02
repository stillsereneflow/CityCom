"""Record TD raw detector data for the corridor.

live:     poll the live feed every `--interval` s, append corridor rows to data/hk/raw/YYYY-MM-DD.csv
backfill: pull minute files from the data.gov.hk historical archive for a date range

Only corridor detectors (CORRIDOR_PREFIXES) are stored, so a day is a few MB instead of ~700 MB.
"""
import argparse
import csv
import os
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import requests

from citypulse.config import HK_ARCHIVE_GET, HK_ARCHIVE_LIST, HK_DIR, HK_RAW_URL
from citypulse.hkdata.parse import parse_raw

FIELDS = ["date", "period_from", "period_to", "detector_id", "direction", "lane_id",
          "speed", "occupancy", "volume", "sd", "valid"]
UA = {"User-Agent": "CityPulse-research/0.1"}


def append_rows(rows, out_dir: Path, seen: set):
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    by_day = {}
    for r in rows:
        key = (r["date"], r["period_from"], r["detector_id"], r["lane_id"])
        if key in seen:
            continue
        seen.add(key)
        by_day.setdefault(r["date"], []).append(r)
    for day, rs in by_day.items():
        f = out_dir / f"{day}.csv"
        new = not f.exists()
        with open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerows(rs)
        n += len(rs)
    return n


def load_seen(out_dir: Path, day: str):
    f = out_dir / f"{day}.csv"
    seen = set()
    if f.exists():
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                seen.add((r["date"], r["period_from"], r["detector_id"], r["lane_id"]))
    return seen


def acquire_single_instance_lock(out_dir: Path):
    """Exclusive lock held for the process lifetime; released automatically when the process dies.
    Returns the open handle, or None if another recorder already holds it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = open(out_dir / "recorder.lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def live(interval: int, out_dir: Path, max_iter: int = 0):
    lock = acquire_single_instance_lock(out_dir)
    if lock is None:
        return  # another recorder is running (e.g. started by the scheduled task)
    seen = set()
    for f in out_dir.glob("*.csv"):
        seen |= load_seen(out_dir, f.stem)
    log = out_dir / "recorder.log"
    i = 0
    while True:
        t0 = time.time()
        try:
            r = requests.get(HK_RAW_URL, headers=UA, timeout=60)
            r.raise_for_status()
            n = append_rows(parse_raw(r.content), out_dir, seen)
            msg = f"{datetime.now().isoformat(timespec='seconds')} ok rows={n}"
        except Exception as e:  # keep recording through transient network errors
            msg = f"{datetime.now().isoformat(timespec='seconds')} ERROR {type(e).__name__}: {e}"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
        i += 1
        if max_iter and i >= max_iter:
            return
        time.sleep(max(1.0, interval - (time.time() - t0)))


def _fetch(ts):
    for attempt in range(3):
        try:
            r = requests.get(HK_ARCHIVE_GET, params={"url": HK_RAW_URL, "time": ts}, headers=UA, timeout=60)
            if r.status_code == 404:
                return ts, None, "404"
            r.raise_for_status()
            return ts, parse_raw(r.content), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
    return ts, None, err


def backfill(start: str, end: str, out_dir: Path, every: int = 1, hours=(0, 24), workers: int = 8):
    """start/end: YYYYMMDD inclusive. `hours`: [h0, h1) filter on the archive timestamp (HHMM)."""
    from concurrent.futures import ThreadPoolExecutor
    q = {"url": HK_RAW_URL, "start": start, "end": end}
    vers = requests.get(HK_ARCHIVE_LIST, params=q, headers=UA, timeout=60).json()
    stamps = [s for s in vers.get("timestamps", []) if hours[0] <= int(s[9:11]) < hours[1]][::every]
    seen = set()
    for f in out_dir.glob("*.csv"):
        seen |= load_seen(out_dir, f.stem)
    total, errs = 0, 0
    with ThreadPoolExecutor(workers) as ex:
        for k, (ts, rows, err) in enumerate(ex.map(_fetch, stamps)):
            if rows is None:
                errs += 1
                print(f"{ts} ERROR {err}", flush=True)
            else:
                total += append_rows(rows, out_dir, seen)
            if k % 50 == 0:
                print(f"{k}/{len(stamps)} versions, rows={total}", flush=True)
    print(f"done: {len(stamps)} versions, rows={total}, failed={errs}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("live")
    a.add_argument("--interval", type=int, default=60)
    a.add_argument("--max-iter", type=int, default=0)
    b = sub.add_parser("backfill")
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    b.add_argument("--every", type=int, default=1)
    b.add_argument("--hours", type=int, nargs=2, default=[0, 24])
    b.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(HK_DIR / "raw"))
    args = ap.parse_args()
    out = Path(args.out)
    if args.cmd == "live":
        live(args.interval, out, args.max_iter)
    else:
        backfill(args.start, args.end, out / "archive", args.every, tuple(args.hours), args.workers)


if __name__ == "__main__":
    main()
