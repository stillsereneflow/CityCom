"""Parse the TD raw speed/volume/occupancy XML (two 30 s periods per file, per lane)."""
import xml.etree.ElementTree as ET

from citypulse.config import CORRIDOR_PREFIXES


def parse_raw(xml_bytes: bytes, prefixes=CORRIDOR_PREFIXES):
    """Return list of per-lane rows; keep only detectors whose id starts with one of `prefixes`."""
    root = ET.fromstring(xml_bytes)
    date = root.findtext("date")
    rows = []
    for period in root.iter("period"):
        p_from, p_to = period.findtext("period_from"), period.findtext("period_to")
        for det in period.iter("detector"):
            did = det.findtext("detector_id")
            if prefixes and not did.startswith(prefixes):
                continue
            direction = det.findtext("direction")
            for lane in det.iter("lane"):
                rows.append({
                    "date": date, "period_from": p_from, "period_to": p_to,
                    "detector_id": did, "direction": direction,
                    "lane_id": lane.findtext("lane_id"),
                    "speed": _num(lane.findtext("speed")),
                    "occupancy": _num(lane.findtext("occupancy")),
                    "volume": _num(lane.findtext("volume")),
                    "sd": _num(lane.findtext("s.d.")),
                    "valid": lane.findtext("valid"),
                })
    return rows


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def aggregate_detector(rows):
    """Lane rows -> one row per (date, period, detector): volume sum, volume-weighted speed, mean occupancy."""
    out = {}
    for r in rows:
        key = (r["date"], r["period_from"], r["detector_id"])
        a = out.setdefault(key, {"date": r["date"], "period_from": r["period_from"], "detector_id": r["detector_id"],
                                 "volume": 0.0, "_sv": 0.0, "_occ": [], "n_lanes": 0, "n_valid": 0})
        a["n_lanes"] += 1
        if r["valid"] != "Y" or r["volume"] is None:
            continue
        a["n_valid"] += 1
        a["volume"] += r["volume"]
        if r["speed"] is not None:
            a["_sv"] += r["speed"] * r["volume"]
        if r["occupancy"] is not None:
            a["_occ"].append(r["occupancy"])
    res = []
    for a in out.values():
        a["speed"] = a["_sv"] / a["volume"] if a["volume"] > 0 else None
        a["occupancy"] = sum(a["_occ"]) / len(a["_occ"]) if a["_occ"] else None
        for k in ("_sv", "_occ"):
            a.pop(k)
        res.append(a)
    return res
