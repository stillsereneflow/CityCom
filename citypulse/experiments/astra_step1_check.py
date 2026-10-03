"""Independent aggregation checks and compact consultation evidence; no baseline edits."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

from citypulse.config import HK_DIR, RESULTS, SCEN
from citypulse.experiments.astra_step1 import OUT, save
from citypulse.sim import init_signals, proxy_cmd


def main():
    checks = {}
    td = json.loads((OUT / "td_detectors.json").read_text(encoding="utf-8"))
    # Pandas independently recomputes all published day-29 complete-lane aggregates.
    frame = pd.read_csv(HK_DIR / "raw/archive/2026-09-29.csv")
    frame = frame[(frame.period_from >= "08:00:00") & (frame.period_from < "09:00:00")]
    frame = frame[frame.detector_id.isin({r["id"] for r in td})]
    assert frame.duplicated(["detector_id", "period_from", "lane_id"]).sum() == 0
    valid = frame[frame.valid == "Y"].copy()
    valid["speed_volume"] = valid.speed * valid.volume
    for r in (r for r in td if r["day"] == "2026-09-29"):
        f = valid[valid.detector_id == r["id"]]
        n = f.period_from.nunique()
        assert len(f) == n * r["expected_lanes"]
        assert n == r["complete_periods"]
        np.testing.assert_allclose([f.volume.sum() * 120 / n,
                                   f.speed_volume.sum() / f.volume.sum(), f.occupancy.mean()],
                                  [r["flow_vph"], r["speed_kmh"], r["occupancy_pct"]])
    checks["td_day29_pandas"] = "54 detector aggregates agree; no duplicate keys or partial valid periods"
    checks["td_day29_discard"] = {"rows": len(frame), "invalid": int((frame.valid != "Y").sum())}
    # Baseline trajectory, count, source and fit records must agree, not only the headline.
    g = json.loads((RESULTS / "net_diag_g100.json").read_text())
    b = json.loads((RESULTS / "net_diag_astra_base.json").read_text())
    for k in ("totals", "history", "sources", "fit", "jams", "detector_intervals", "running_last15_slope_vps"):
        assert g[k] == b[k], k
    checks["baseline_g100_exact_payload"] = True
    checks["g100_hash_after_lf_to_crlf"] = {
        Path(p).name: hashlib.sha256((SCEN / Path(p).name).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() == h
        for p, h in g["input_sha256"].items()}
    summary = []
    for tag in ("astra_base", "astra_boundary", "astra_optimized"):
        p = RESULTS / f"net_diag_{tag}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        t = r["totals"]
        assert t["inserted"] == t["arrived_total"] + t["running_end"]
        not_due = sum(float(v.get("depart")) >= 3599 for v in ET.parse(r["command"][r["command"].index("-r") + 1]).iter("vehicle"))
        # Record final-second departures separately instead of calling them missing vehicles.
        residual = t["loaded"] - t["inserted"] - t["pending_end"]
        assert residual == not_due
        last = [h for h in r["history"] if 2700 <= h["time"] <= 3600]
        assert len(last) == 16
        pending = sorted((s["pending_end"] for s in r["sources"]), reverse=True)
        summary.append({"tag": tag, **t, "pending_pct": t["pending_end"] / t["loaded"] * 100,
                        "slope_vps": r["running_last15_slope_vps"], "geh_lt5": sum(f["geh"] < 5 for f in r["fit"]),
                        "fit_denominator": len(r["fit"]), "unaccounted_loaded": residual,
                        "depart_ge_3599": not_due, "pending_top5_share": sum(pending[:5]) / sum(pending),
                        "sources_with_pending": sum(x > 0 for x in pending)})
    checks["runs"] = summary
    manifest = json.loads((OUT / "input_sha256.json").read_text())
    assert all(hashlib.sha256((SCEN.parent.parent / p).read_bytes()).hexdigest() == h for p, h in manifest.items())
    checks["original_worktree_inputs_unchanged"] = len(manifest)
    # Compare completed-interval API values with SUMO's own XML writer, on all 54 detectors.
    import libsumo as tc
    root = ET.parse(SCEN / "detectors.add.xml")
    xml_path = OUT / "check_loop_output.xml"
    for loop in root.getroot().iter("inductionLoop"):
        loop.set("file", str(xml_path))
    det_path = OUT / "check_detectors.add.xml"
    root.write(det_path, encoding="utf-8", xml_declaration=True)
    cmd = proxy_cmd(1)
    cmd[cmd.index("-a") + 1] = ",".join(map(str, [SCEN / "vtypes_proxy.add.xml", det_path, SCEN / "tls_incident.add.xml"]))
    tc.start(cmd)
    init_signals(tc)
    api = {}
    for t in range(1, 301):
        tc.simulationStep()
        if t % 30 == 0:
            for lid in tc.inductionloop.getIDList():
                api[(lid, t)] = tc.inductionloop.getLastIntervalVehicleNumber(lid)
    tc.close()
    xml = {(i.get("id"), int(float(i.get("end")))): int(i.get("nVehContrib"))
           for i in ET.parse(xml_path).iter("interval")}
    entered = {(i.get("id"), int(float(i.get("end")))): int(i.get("nVehEntered"))
               for i in ET.parse(xml_path).iter("interval")}
    differences = [{"loop_end": k, "api": n, "xml": xml.get(k)} for k, n in api.items() if xml.get(k) != n]
    checks["e1_xml_comparison"] = {"cells": len(api), "differences": differences,
                                  "api_total": sum(api.values()), "xml_total": sum(xml.values()),
                                  "entered_total": sum(entered.values()),
                                  "entered_mismatch_cells": sum(entered.get(k) != n for k, n in api.items())}
    save("checks.json", checks)
    assert not differences, "E1 API counts differ from SUMO XML nVehContrib"
    print(json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
