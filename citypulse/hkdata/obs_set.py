"""Observation dataset module for traffic-twin calibration."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd


def time_to_sec(t_str: str) -> int:
    parts = [int(p) for p in t_str.strip().split(":")]
    return parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)


def sec_to_hhmm(sec: int) -> str:
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}"


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_detector_map(path: Path | str) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        return {item["id"]: item["edge"] for item in json.load(f)["mapped"]}


def process_period_records(df: pd.DataFrame, detector_map: dict[str, str], start_sec: int, end_sec: int):
    """Filter raw records to mapped detectors, drop invalid/out-of-window, and aggregate lanes."""
    m_df = df[df["detector_id"].isin(detector_map)].copy()
    sec = m_df["period_from"].apply(time_to_sec)
    m_df["sec"] = sec

    out_mask = (sec < start_sec) | (sec >= end_sec)
    outside_periods = m_df[out_mask][["detector_id", "period_from"]].drop_duplicates()
    outside_count = len(outside_periods)

    in_df = m_df[~out_mask].copy()
    has_invalid = in_df.groupby(["detector_id", "period_from"])["valid"].transform(lambda s: (s != "Y").any())
    inv_periods = in_df[has_invalid][["detector_id", "period_from"]].drop_duplicates()
    inv_count = len(inv_periods)
    inv_by_det = inv_periods["detector_id"].value_counts().to_dict()

    valid_df = in_df[~has_invalid].copy()
    if valid_df.empty:
        agg = pd.DataFrame(columns=["date", "detector", "edge", "period_from", "sec", "flow", "vol_speed", "occ", "speed"])
    else:
        valid_df["vol_speed"] = valid_df["speed"] * valid_df["volume"]
        g = valid_df.groupby(["date", "detector_id", "period_from", "sec"], as_index=False)
        agg = g.agg(flow=("volume", "sum"), vol_speed=("vol_speed", "sum"), occ=("occupancy", "mean"))
        agg.rename(columns={"detector_id": "detector"}, inplace=True)
        agg["edge"] = agg["detector"].map(detector_map)
        agg["speed"] = np.where(agg["flow"] > 0, agg["vol_speed"] / agg["flow"], np.nan)

    return agg, {"invalid_lane": inv_count, "outside_window": outside_count, "invalid_by_det": inv_by_det}


def aggregate_to_bins(periods_df: pd.DataFrame, bin_sec: int, start_sec: int, calib_dates: set[str]) -> pd.DataFrame:
    """Bin 30s aggregated periods into fixed duration bins."""
    cols = ["date", "detector", "edge", "bin_start", "flow_vph", "speed_kmh", "occ", "n_periods", "coverage", "split"]
    if periods_df.empty:
        return pd.DataFrame(columns=cols)

    periods_df = periods_df.copy()
    periods_df["bin_start"] = (start_sec + ((periods_df["sec"] - start_sec) // bin_sec) * bin_sec).apply(sec_to_hhmm)
    max_p = bin_sec / 30.0
    records = []
    for (dt, det, edge, b_start), sub in periods_df.groupby(["date", "detector", "edge", "bin_start"]):
        n_p, tot_vol = len(sub), sub["flow"].sum()
        records.append({
            "date": dt, "detector": det, "edge": edge, "bin_start": b_start,
            "flow_vph": round(sub["flow"].mean() * 120.0, 2),
            "speed_kmh": round(sub["vol_speed"].sum() / tot_vol, 2) if tot_vol > 0 else np.nan,
            "occ": round(sub["occ"].mean(), 2), "n_periods": int(n_p),
            "coverage": round(n_p / max_p, 4), "split": "calib" if dt in calib_dates else "holdout"
        })
    return pd.DataFrame(records, columns=cols)


def build_profile(df_bins: pd.DataFrame, meta: dict) -> dict:
    """Compute calibration profile stats for bins with coverage >= 0.3."""
    profile = {"meta": meta}
    calib = df_bins[(df_bins["split"] == "calib") & (df_bins["coverage"] >= 0.3)]
    for (det, b_start), sub in calib.groupby(["detector", "bin_start"]):
        profile.setdefault(det, {})[b_start] = {
            "n_days": int(len(sub)),
            "flow_vph": _stats(sub["flow_vph"]),
            "speed_kmh": _stats(sub["speed_kmh"].dropna()) if len(sub["speed_kmh"].dropna()) else None,
            "occ": _stats(sub["occ"])
        }
    return profile


def _stats(series: pd.Series) -> dict:
    p25, p75 = float(series.quantile(0.25)), float(series.quantile(0.75))
    return {"median": round(float(series.median()), 2), "p25": round(p25, 2),
            "p75": round(p75, 2), "iqr": round(p75 - p25, 2)}


def run(calib: list[str], holdout: list[str], start: str = "07:00", end: str = "09:00", bin_size: int = 300,
        raw_dir: str | Path = "data/hk/raw/archive", det_map_path: str | Path = "scenarios/kwuntong/detector_map.json",
        out_dir: str | Path = "results/obs"):
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    det_map = load_detector_map(det_map_path)
    start_sec, end_sec = time_to_sec(start), time_to_sec(end)
    calib_set = set(calib)

    all_periods, files_sha = [], {}
    tot_inv, tot_out, inv_by_det = 0, 0, {}
    for d in list(dict.fromkeys(calib + holdout)):
        fpath = raw_dir / f"{d}.csv"
        files_sha[fpath.name] = sha256_file(fpath)
        p_df, counts = process_period_records(pd.read_csv(fpath), det_map, start_sec, end_sec)
        all_periods.append(p_df)
        tot_inv += counts["invalid_lane"]
        tot_out += counts["outside_window"]
        for k, v in counts["invalid_by_det"].items():
            inv_by_det[k] = inv_by_det.get(k, 0) + v

    combined = pd.concat(all_periods, ignore_index=True) if all_periods else pd.DataFrame()
    df_bins = aggregate_to_bins(combined, bin_size, start_sec, calib_set)
    df_bins.to_parquet(out_dir / "obs_bins.parquet", index=False)

    cov_share = float((df_bins["coverage"] >= 0.3).mean()) if len(df_bins) else 0.0
    meta = {
        "args": {"calib": calib, "holdout": holdout, "start": start, "end": end, "bin": bin_size},
        "files": files_sha,
        "dropped_periods": {"invalid_lane": tot_inv, "outside_window": tot_out},
        "dropped_periods_by_detector": inv_by_det,
        "coverage_ge_0_3_share": round(cov_share, 4)
    }
    with open(out_dir / "obs_profile.json", "w", encoding="utf-8") as f:
        json.dump(build_profile(df_bins, meta), f, indent=2)

    print(f"{len(df_bins)} cells written, {cov_share:.1%} with coverage >= 0.3")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--calib", nargs="+", required=True)
    p.add_argument("--holdout", nargs="+", default=[])
    p.add_argument("--start", default="07:00")
    p.add_argument("--end", default="09:00")
    p.add_argument("--bin", type=int, default=300)
    p.add_argument("--raw-dir", default="data/hk/raw/archive")
    p.add_argument("--detector-map", default="scenarios/kwuntong/detector_map.json")
    p.add_argument("--out-dir", default="results/obs")
    args = p.parse_args()
    run(args.calib, args.holdout, args.start, args.end, args.bin,
        raw_dir=args.raw_dir, det_map_path=args.detector_map, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
