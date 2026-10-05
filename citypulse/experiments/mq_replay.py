"""Missing-queue experiment: Part A — two-world runs, restart replays C and H, gates, queue at t_d.
Preregistration: docs/oct11-missing-queue-plan.md (revision 2).
"""
from __future__ import annotations
import argparse, gzip, json, os, subprocess, sys, time
import multiprocessing as mp
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET
import pandas as pd

from citypulse.branching.audit_engine import strip_future_departures_from_proxy_snapshot, strip_rng_state_from_xml, veh_digest
from citypulse.experiments.decision_audit import compute_alarm_for_twin_log
from citypulse.sim import ControlState, proxy_cmd, twin_cmd
from citypulse.twin.demand_stream import TwinDemandStream

REPO_ROOT = Path(__file__).resolve().parents[2]
SCEN5_DIR = REPO_ROOT / "scenarios" / "kwuntong" / "blite" / "synth5"
PROXY_ROU, TWIN_CAND_ROU = SCEN5_DIR / "proxy.rou.xml", SCEN5_DIR / "twin_cand.rou.xml"
SIGMA_DEV = REPO_ROOT / "results" / "assim" / "na300" / "sigma300_dev.json"
RESULTS_MQ = REPO_ROOT / "results" / "missing_queue"
UPSTREAM_JSON = RESULTS_MQ / "upstream_edges.json"

SEEDS, TWIN_SEED, DEMAND_SEED = [4301, 4302, 4303, 4304], 2, 202
TWIN_BASE_FACTOR, BOUNDARY_DETECTOR, BOUNDARY_ENTRY, T_D = 0.85, "AID07106", "tko_insert", 5100.0

def check_fresh_seeds(seeds: List[int] = SEEDS, results_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    rdir, found, seed_strs = results_dir or (REPO_ROOT / "results"), [], {str(s) for s in seeds}
    for p in rdir.glob("**/*"):
        if p.is_dir() and any(s in p.name for s in seed_strs):
            found.append(f"Directory: {p}")
        elif p.is_file() and p.suffix == ".json" and p.name != "seed_check.json":
            try:
                def _scan(obj: Any) -> None:
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k == "seed" and (v in seeds or str(v) in seed_strs):
                                found.append(f"JSON seed={v} in {p}")
                            _scan(v)
                    elif isinstance(obj, list):
                        for it in obj: _scan(it)
                _scan(json.loads(p.read_text(encoding="utf-8")))
            except Exception: pass
        elif p.is_file() and p.suffix == ".parquet":
            try:
                df = pd.read_parquet(p)
                if "seed" in df.columns and (m := set(df["seed"].unique()) & set(seeds)):
                    found.append(f"Parquet column seed contains {m} in {p}")
            except Exception: pass
    return len(found) == 0, found

def load_upstream_edge_specs(path: Path = UPSTREAM_JSON) -> Tuple[List[str], List[str], List[str]]:
    d = json.load(open(path, "r", encoding="utf-8"))
    return d["Q_edges"], d["upstream_spillback_edges"], d["descriptive_extra_edges"]

def build_m_schedule(df_assim: pd.DataFrame) -> Dict[float, float]:
    return {float(r["t"]): float(r["m"]) for _, r in df_assim.iterrows() if 4440.0 < float(r["t"]) <= 5100.0}

def regenerate_twin_demand(
    seed: int, path: Optional[Path | str], base_factor: float, t_start: float = 4440.0,
    t_end: float = 5100.0, initial_ptr: Optional[int] = None, initial_m: Optional[Dict[str, float]] = None,
    m_schedule: Optional[Dict[float, float]] = None,
) -> Tuple[List[Tuple[str, float, int]], int, Dict[str, float]]:
    stream = TwinDemandStream(seed=seed, path=path, base_factor=base_factor)
    if initial_m: stream.m = dict(initial_m)
    stream.seek(t_start)
    if initial_ptr is not None:
        assert stream.ptr == initial_ptr, f"Pointer mismatch: {stream.ptr} vs {initial_ptr}"
    cand_dep, sched, inserted = {v: d for d, v, _ in stream.cands}, m_schedule or {}, []
    for step_t in range(int(t_start) + 1, int(t_end) + 1):
        t_curr = float(step_t)
        for vid, _ in stream.due(t_curr):
            inserted.append((vid, cand_dep[vid], step_t))
        if t_curr in sched:
            stream.m[BOUNDARY_ENTRY] = sched[t_curr]
    return inserted, stream.ptr, dict(stream.m)

def aggregate_q_counts(
    vehicles: List[Tuple[str, str, float]], q_edges: List[str], upstream_edges: List[str],
    extra_edges: List[str], pending_vehicles: List[str], pending_routes: Dict[str, List[str]],
) -> Dict[str, Any]:
    all_edges = q_edges + upstream_edges + extra_edges
    counts = {e: 0 for e in all_edges}
    for vid, road, sp in vehicles:
        # blockers are excluded in both worlds: the Twin's hyp_* and the Proxy's incident_* vehicles
        if not vid.startswith(("hyp_", "incident_")) and sp < 0.1 and road in counts:
            counts[road] += 1
    q_set = set(q_edges)
    pending_q = sum(1 for vid in pending_vehicles if any(e in q_set for e in pending_routes.get(vid, [])))
    counts["pending_q"] = pending_q
    counts["Q"] = sum(counts[e] for e in q_edges) + pending_q
    return counts

def parse_proxy_pending(xml_path: Path) -> Tuple[List[str], Dict[str, List[str]]]:
    with gzip.open(xml_path, "rb") as f:
        root = ET.parse(f).getroot()
    lane_vids = {v for l in root.findall(".//lane/vehicles") for v in l.get("value", "").split()}
    routes = {r.get("id"): r.get("edges", "").split() for r in root.findall(".//route")}
    pending_vids, pending_dict = [], {}
    for v in root.findall(".//vehicle"):
        vid = v.get("id")
        if vid and vid not in lane_vids:
            pending_vids.append(vid)
            pending_dict[vid] = routes.get(v.get("route", ""), [])
    return pending_vids, pending_dict

def run_twoworld_batch(seeds: List[int], runs_dir: Path, base_port: int = 5600, t_end: float = 7200.0) -> Dict[int, Any]:
    env = dict(os.environ, CITYPULSE_NET="blite", CITYPULSE_BLITE_REV="5", CITYPULSE_REROUTE="0",
               PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1")
    procs, t0 = [], time.time()
    for i, s in enumerate(seeds):
        s_dir = runs_dir / f"seed_{s}"
        twin_dir, proxy_dir = s_dir / "twin", s_dir / "proxy"
        twin_dir.mkdir(parents=True, exist_ok=True)
        proxy_dir.mkdir(parents=True, exist_ok=True)
        ep = f"tcp://127.0.0.1:{base_port + i * 2}"
        targs = [sys.executable, "-m", "citypulse.twin.service", "--endpoint", ep, "--out", str(twin_dir),
                 "--seed", str(TWIN_SEED), "--demand-seed", str(DEMAND_SEED), "--demand-path", str(TWIN_CAND_ROU),
                 "--assim", "normal300", "--boundary-detector", BOUNDARY_DETECTOR, "--sigma-json", str(SIGMA_DEV),
                 "--twin-base-factor", str(TWIN_BASE_FACTOR), "--snapshot-times", "4440", "5100"]
        pargs = [sys.executable, "-m", "citypulse.proxy.service", "--endpoint", ep, "--out", str(proxy_dir),
                 "--seed", str(s), "--sensor-seed", "77", "--t-end", str(int(t_end)), "--routes", str(PROXY_ROU),
                 "--proxy-snapshot-times", "5100"]
        procs.append((s, s_dir, subprocess.Popen(targs, env=env, cwd=str(REPO_ROOT)), pargs))

    time.sleep(2)
    proxy_procs = [(s, s_dir, tp, subprocess.Popen(pargs, env=env, cwd=str(REPO_ROOT))) for s, s_dir, tp, pargs in procs]
    results = {}
    for s, s_dir, twin_p, proxy_p in proxy_procs:
        rc_p, rc_t = proxy_p.wait(), twin_p.wait()
        wall = round(time.time() - t0, 1)
        if rc_p != 0 or rc_t != 0:
            raise RuntimeError(f"Two-world run failed for seed {s}: proxy_rc={rc_p}, twin_rc={rc_t}")
        twin_state, proxy_state = s_dir / "twin" / "twin_state_5100.xml.gz", s_dir / "proxy" / "proxy_state_5100.xml.gz"
        strip_rng_state_from_xml(twin_state)
        strip_rng_state_from_xml(proxy_state)
        strip_future_departures_from_proxy_snapshot(proxy_state, T_D)
        alarm_info = compute_alarm_for_twin_log(s_dir / "twin" / "twin_log.parquet")
        info = {"seed": s, "wall_s": wall, "proxy_rc": rc_p, "twin_rc": rc_t, "alarm": alarm_info,
                "twin_state_4440": str(s_dir / "twin" / "twin_state_4440.xml.gz"),
                "twin_meta_4440": str(s_dir / "twin" / "twin_state_4440.json"),
                "twin_state": str(twin_state), "twin_meta": str(s_dir / "twin" / "twin_state_5100.json"),
                "proxy_state": str(proxy_state)}
        json.dump(info, open(s_dir / "two_world_info.json", "w", encoding="utf-8"), indent=2)
        results[s] = info
    return results

def _replay_worker(job: Dict[str, Any]) -> Dict[str, Any]:
    import libsumo as tc
    t_wall0, seed, world = time.time(), int(job["seed"]), str(job["world"])
    twin_state_4440, twin_meta_4440 = str(job["twin_state_4440"]), str(job["twin_meta_4440"])
    assim_log_path, out_state_path = str(job["assim_log_path"]), Path(job["out_state_path"])
    out_meta_path, save_state = Path(job["out_meta_path"]), bool(job.get("save_state", True))
    meta_4440 = json.load(open(twin_meta_4440, "r", encoding="utf-8"))

    cmd = twin_cmd(TWIN_SEED, ["--load-state", twin_state_4440, "--save-state.rng"])
    try:
        tc.start(cmd)
        assert tc.simulation.getTime() == 4440.0, f"Expected t0=4440.0"
        ControlState.from_dict(meta_4440["control_state"]).apply(tc)

        cand_path, base_factor = meta_4440.get("demand_path"), meta_4440.get("twin_base_factor") or TWIN_BASE_FACTOR
        stream = TwinDemandStream(seed=meta_4440.get("demand_seed", DEMAND_SEED), path=cand_path, base_factor=base_factor)
        stream.m = dict(meta_4440.get("m") or {})
        stream.seek(4440)
        assert stream.ptr == meta_4440["stream_ptr"], f"Pointer mismatch: {stream.ptr} vs {meta_4440["stream_ptr"]}"

        cand_dep = {vid: dep for dep, vid, _ in stream.cands}
        cand_routes = {vid: edges for _, vid, edges in stream.cands}
        m_schedule = build_m_schedule(pd.read_parquet(assim_log_path))
        inserted_vehicles: List[Tuple[str, float, int]] = []
        blocker_stops = {"hyp_blocker_0": {"lane": 0, "pos": None, "time_stopped": None},
                         "hyp_blocker_1": {"lane": 1, "pos": None, "time_stopped": None}}

        for step_t in range(4441, 5101):
            t_curr = float(step_t)
            for vid, edges in stream.due(t_curr):
                rid = "r_" + vid
                tc.route.add(rid, edges)
                tc.vehicle.add(vid, rid, typeID="tdist", departLane="best", departSpeed="max")
                inserted_vehicles.append((vid, cand_dep[vid], step_t))
            tc.simulationStep()

            if world == "H":
                if step_t == 4500:
                    if "hyp_route" not in tc.route.getIDList(): tc.route.add("hyp_route", ["ktb_n1"])
                    for ln in (0, 1):
                        vid = f"hyp_blocker_{ln}"
                        tc.vehicle.add(vid, "hyp_route", typeID="t_car", departLane=str(ln), departPos="754.3", departSpeed="0")
                        tc.vehicle.setStop(vid, "ktb_n1", pos=755.3, laneIndex=ln, duration=3600.0)
                        tc.vehicle.setLaneChangeMode(vid, 0)
                elif step_t > 4500:
                    for ln in (0, 1):
                        vid, b_info = f"hyp_blocker_{ln}", blocker_stops[f"hyp_blocker_{ln}"]
                        if b_info["time_stopped"] is None and vid in tc.vehicle.getIDList() and tc.vehicle.isStopped(vid):
                            b_info["time_stopped"], b_info["pos"] = t_curr, tc.vehicle.getLanePosition(vid)
            if t_curr in m_schedule:
                stream.m[BOUNDARY_ENTRY] = m_schedule[t_curr]

        digest, n_veh = veh_digest(tc)
        pending_ids = list(tc.simulation.getPendingVehicles())
        blocker_status = {}
        if world == "H":
            for ln in (0, 1):
                vid = f"hyp_blocker_{ln}"
                ex = vid in tc.vehicle.getIDList()
                stopped = tc.vehicle.isStopped(vid) if ex else False
                b_info = blocker_stops[vid]
                if b_info["time_stopped"] is None and stopped:
                    b_info["time_stopped"], b_info["pos"] = 5100.0, tc.vehicle.getLanePosition(vid)
                blocker_status[vid] = {
                    "exists": ex, "road": tc.vehicle.getRoadID(vid) if ex else None,
                    "lane": tc.vehicle.getLaneIndex(vid) if ex else None,
                    "pos": tc.vehicle.getLanePosition(vid) if ex else None, "stopped": stopped,
                    "stop_time": b_info["time_stopped"], "stop_pos": b_info["pos"],
                    "delay_s": (b_info["time_stopped"] - 4500.0) if b_info["time_stopped"] else None,
                }

        if save_state:
            out_state_path.parent.mkdir(parents=True, exist_ok=True)
            tc.simulation.saveState(str(out_state_path))
            meta_out = {
                "t": 5100.0, "control_state": ControlState.from_dict(meta_4440["control_state"]).to_dict(),
                "stream_ptr": stream.ptr, "pending": pending_ids,
                "pending_routes": {vid: cand_routes.get(vid, []) for vid in pending_ids},
                "demand_seed": meta_4440.get("demand_seed", DEMAND_SEED), "sumo_seed": TWIN_SEED,
                "demand_path": str(cand_path) if cand_path else None, "m": dict(stream.m),
                "twin_base_factor": base_factor, "veh_digest": digest, "n_veh": n_veh,
            }
            if world == "H": meta_out["blockers"] = blocker_status
            json.dump(meta_out, open(out_meta_path, "w", encoding="utf-8"), indent=2)

        tc.close()
        if save_state: strip_rng_state_from_xml(out_state_path)
        return {"status": "ok", "seed": seed, "world": world, "veh_digest": digest, "n_veh": n_veh,
                "pending": pending_ids, "stream_ptr": stream.ptr, "m": dict(stream.m),
                "inserted": inserted_vehicles, "blockers": blocker_status if world == "H" else None,
                "wall_s": round(time.time() - t_wall0, 2)}
    except Exception as e:
        try: tc.close()
        except Exception: pass
        return {"status": "error", "seed": seed, "world": world, "error": str(e),
                "reason": type(e).__name__, "wall_s": round(time.time() - t_wall0, 2)}

def _read_halted_worker(job: Dict[str, Any]) -> Dict[str, Any]:
    import libsumo as tc
    try:
        tc.start(job["cmd"])
        vehs = [(v, tc.vehicle.getRoadID(v), float(tc.vehicle.getSpeed(v))) for v in tc.vehicle.getIDList()]
        tc.close()
        return {"status": "ok", "vehicles": vehs}
    except Exception as e:
        try: tc.close()
        except Exception: pass
        return {"status": "error", "error": str(e), "reason": type(e).__name__}

def run_replays_and_gates(
    seeds: List[int], runs_dir: Path, states_dir: Path, gates_file: Path, workers: int = 4
) -> Dict[str, Any]:
    ctx = mp.get_context("spawn")
    jobs = []
    for s in seeds:
        s_run, s_state = runs_dir / f"seed_{s}", states_dir / f"seed_{s}"
        t_4440, m_4440 = s_run / "twin" / "twin_state_4440.xml.gz", s_run / "twin" / "twin_state_4440.json"
        assim_p = s_run / "twin" / "assim_log.parquet"
        for w, tag, save in [("C", "C_run1", True), ("C", "C_run2", False), ("H", "H", True)]:
            jobs.append({"seed": s, "world": w, "tag": tag, "twin_state_4440": str(t_4440),
                         "twin_meta_4440": str(m_4440), "assim_log_path": str(assim_p),
                         "out_state_path": str(s_state / f"{w}_5100.xml.gz"),
                         "out_meta_path": str(s_state / f"{w}_5100.json"), "save_state": save})

    with ctx.Pool(min(workers, len(jobs))) as pool:
        raw_res = pool.map(_replay_worker, jobs)

    by_seed_tag: Dict[int, Dict[str, Any]] = {s: {} for s in seeds}
    for j, res in zip(jobs, raw_res): by_seed_tag[j["seed"]][j["tag"]] = res

    gates_data: Dict[str, Any] = {"all_passed": True, "seeds": {}}
    for s in seeds:
        rc1, rc2, rh = by_seed_tag[s]["C_run1"], by_seed_tag[s]["C_run2"], by_seed_tag[s]["H"]
        if rc1["status"] != "ok" or rc2["status"] != "ok" or rh["status"] != "ok":
            gates_data["all_passed"] = False
            gates_data["seeds"][str(s)] = {"passed": False, "error": "Replay execution failed"}
            continue

        live_meta = json.load(open(runs_dir / f"seed_{s}" / "twin" / "twin_state_5100.json", "r", encoding="utf-8"))
        m_4440 = json.load(open(runs_dir / f"seed_{s}" / "twin" / "twin_state_4440.json", "r", encoding="utf-8"))
        m_sched = build_m_schedule(pd.read_parquet(runs_dir / f"seed_{s}" / "twin" / "assim_log.parquet"))

        regen_ins, regen_ptr, regen_m = regenerate_twin_demand(
            seed=m_4440["demand_seed"], path=m_4440.get("demand_path"),
            base_factor=m_4440.get("twin_base_factor") or TWIN_BASE_FACTOR,
            initial_ptr=m_4440["stream_ptr"], initial_m=m_4440.get("m"), m_schedule=m_sched)

        g1_pass = (rc1["veh_digest"] == rc2["veh_digest"] and rc1["pending"] == rc2["pending"]
                   and rc1["stream_ptr"] == rc2["stream_ptr"] and rc1["m"] == rc2["m"])
        g1_info = {"passed": bool(g1_pass), "veh_digest_c1": rc1["veh_digest"], "veh_digest_c2": rc2["veh_digest"],
                   "pending_c1": rc1["pending"], "pending_c2": rc2["pending"],
                   "stream_ptr_c1": rc1["stream_ptr"], "stream_ptr_c2": rc2["stream_ptr"],
                   "m_c1": rc1["m"], "m_c2": rc2["m"]}

        ins_c = [(v, round(d, 3), step) for v, d, step in rc1["inserted"]]
        ins_h = [(v, round(d, 3), step) for v, d, step in rh["inserted"]]
        ins_rg = [(v, round(d, 3), step) for v, d, step in regen_ins]
        c_eq_h, c_eq_rg = (ins_c == ins_h), (ins_c == ins_rg)
        ptr_eq = (rc1["stream_ptr"] == live_meta["stream_ptr"] == rh["stream_ptr"] == regen_ptr)
        m_eq = (rc1["m"] == live_meta["m"] == rh["m"] == regen_m)
        g2_pass = c_eq_h and c_eq_rg and ptr_eq and m_eq
        g2_info = {"passed": bool(g2_pass), "n_inserted_c": len(ins_c), "n_inserted_h": len(ins_h),
                   "n_inserted_regen": len(ins_rg), "inserted_c_equals_h": c_eq_h,
                   "inserted_c_equals_regen": c_eq_rg, "final_ptr_replay": rc1["stream_ptr"],
                   "final_ptr_live": live_meta["stream_ptr"], "final_m_replay": rc1["m"], "final_m_live": live_meta["m"]}

        b_res = rh["blockers"] or {}
        b0, b1 = b_res.get("hyp_blocker_0", {}), b_res.get("hyp_blocker_1", {})
        g3_pass = (b0.get("exists") and b0.get("road") == "ktb_n1" and b0.get("lane") == 0
                   and abs(float(b0.get("pos") or 0) - 755.3) <= 1.0 and b0.get("stopped")
                   and b1.get("exists") and b1.get("road") == "ktb_n1" and b1.get("lane") == 1
                   and abs(float(b1.get("pos") or 0) - 755.3) <= 1.0 and b1.get("stopped"))
        g3_info = {"passed": bool(g3_pass), "hyp_blocker_0": b0, "hyp_blocker_1": b1}

        seed_pass = bool(g1_pass and g2_pass and g3_pass)
        if not seed_pass: gates_data["all_passed"] = False
        gates_data["seeds"][str(s)] = {"passed": seed_pass, "G1": g1_info, "G2": g2_info, "G3": g3_info}

    json.dump(gates_data, open(gates_file, "w", encoding="utf-8"), indent=2)
    return gates_data

def compute_queue_td(
    seeds: List[int], runs_dir: Path, states_dir: Path, out_parquet: Path, out_md: Path, workers: int = 4
) -> pd.DataFrame:
    q_edges, upstream_edges, extra_edges = load_upstream_edge_specs()
    stream_temp = TwinDemandStream(seed=DEMAND_SEED, path=TWIN_CAND_ROU, base_factor=TWIN_BASE_FACTOR)
    cand_routes = {vid: edges for _, vid, edges in stream_temp.cands}

    read_jobs, meta_info = [], []
    for s in seeds:
        p_state = runs_dir / f"seed_{s}" / "proxy" / "proxy_state_5100.xml.gz"
        read_jobs.append({"cmd": proxy_cmd(s, routes=str(PROXY_ROU), extra=["--load-state", str(p_state)])})
        meta_info.append({"seed": s, "world": "proxy", "state_path": p_state})

        c_state, c_meta = states_dir / f"seed_{s}" / "C_5100.xml.gz", states_dir / f"seed_{s}" / "C_5100.json"
        read_jobs.append({"cmd": twin_cmd(TWIN_SEED, ["--load-state", str(c_state)])})
        meta_info.append({"seed": s, "world": "C", "meta_path": c_meta})

        h_state, h_meta = states_dir / f"seed_{s}" / "H_5100.xml.gz", states_dir / f"seed_{s}" / "H_5100.json"
        read_jobs.append({"cmd": twin_cmd(TWIN_SEED, ["--load-state", str(h_state)])})
        meta_info.append({"seed": s, "world": "H", "meta_path": h_meta})

        l_state, l_meta = runs_dir / f"seed_{s}" / "twin" / "twin_state_5100.xml.gz", runs_dir / f"seed_{s}" / "twin" / "twin_state_5100.json"
        read_jobs.append({"cmd": twin_cmd(TWIN_SEED, ["--load-state", str(l_state)])})
        meta_info.append({"seed": s, "world": "live", "meta_path": l_meta})

    ctx = mp.get_context("spawn")
    with ctx.Pool(min(workers, len(read_jobs))) as pool:
        read_res = pool.map(_read_halted_worker, read_jobs)

    rows = []
    for info, res in zip(meta_info, read_res):
        s, world = info["seed"], info["world"]
        err = res.get('error')
        assert res["status"] == "ok", f"Halted read failed for seed {s} world {world}: {err}"
        if world == "proxy":
            pend_vids, pend_routes = parse_proxy_pending(info["state_path"])
        else:
            meta = json.load(open(info["meta_path"], "r", encoding="utf-8"))
            pend_vids = meta.get("pending", [])
            pend_routes = meta.get("pending_routes") or {v: cand_routes.get(v, []) for v in pend_vids}

        q_agg = aggregate_q_counts(res["vehicles"], q_edges, upstream_edges, extra_edges, pend_vids, pend_routes)
        rows.append({"seed": s, "world": world, **q_agg})

    df = pd.DataFrame(rows)
    df.to_parquet(out_parquet, index=False)

    md_lines = ["# Queue at t_d (5,100 s)", "",
                "| Seed | World | " + " | ".join(q_edges) + " | pending_q | Q | " + " | ".join(upstream_edges + extra_edges) + " |",
                "|---|" + ":---:|" * (len(q_edges) + 3 + len(upstream_edges + extra_edges))]
    for _, r in df.iterrows():
        s_val, w_val, pq_val, q_val = r['seed'], r['world'], r['pending_q'], r['Q']
        md_lines.append(f"| {s_val} | {w_val} | " + " | ".join(str(r[e]) for e in q_edges)
                        + f" | {pq_val} | **{q_val}** | " + " | ".join(str(r[e]) for e in upstream_edges + extra_edges) + " |")

    md_lines.extend(["", "## Contrasts", "", "| Seed | Q(Proxy) | Q(C) | Q(H) | Q(Live) | Q_P − Q_C | Q_H − Q_C |",
                     "|---|:---:|:---:|:---:|:---:|:---:|:---:|"])
    for s in seeds:
        s_df = df[df["seed"] == s].set_index("world")
        qp, qc, qh, ql = int(s_df.loc["proxy", "Q"]), int(s_df.loc["C", "Q"]), int(s_df.loc["H", "Q"]), int(s_df.loc["live", "Q"])
        md_lines.append(f"| {s} | {qp} | {qc} | {qh} | {ql} | {qp - qc} | {qh - qc} |")

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return df

def main() -> None:
    ap = argparse.ArgumentParser(description="Missing-queue experiment Part A")
    ap.add_argument("--check-seeds", action="store_true")
    ap.add_argument("--two-world", action="store_true")
    ap.add_argument("--replays", action="store_true")
    ap.add_argument("--queue-td", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="*", default=SEEDS)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--base-port", type=int, default=5600)
    args = ap.parse_args()

    run_all = args.all or not (args.check_seeds or args.two_world or args.replays or args.queue_td)
    RESULTS_MQ.mkdir(parents=True, exist_ok=True)
    runs_dir, states_dir = RESULTS_MQ / "runs", RESULTS_MQ / "states"

    if args.check_seeds or run_all:
        ok, violations = check_fresh_seeds(args.seeds)
        json.dump({"seeds": args.seeds, "clean": ok, "violations": violations},
                  open(RESULTS_MQ / "seed_check.json", "w", encoding="utf-8"), indent=2)
        if not ok:
            print(f"Seeds check failed: {violations}")
            sys.exit(1)
        print("Step 1: Seeds check PASSED.")

    if args.two_world or run_all:
        print("Step 2: Launching two-world INC runs...")
        run_twoworld_batch(args.seeds, runs_dir, base_port=args.base_port)
        print("Step 2: Two-world INC runs completed.")

    if args.replays or run_all:
        print("Step 3 & 4: Running C and H replays & evaluating gates...")
        gates = run_replays_and_gates(args.seeds, runs_dir, states_dir, RESULTS_MQ / "gates.json", workers=args.workers)
        if not gates.get("all_passed"):
            print("GATES FAILED! Stopping execution.")
            sys.exit(1)
        print("Step 3 & 4: Replays and gates PASSED.")

    if args.queue_td or run_all:
        print("Step 5: Measuring queue at t_d...")
        compute_queue_td(args.seeds, runs_dir, states_dir, RESULTS_MQ / "queue_td.parquet", RESULTS_MQ / "queue_td.md", workers=args.workers)
        print("Step 5: Queue measurement completed.")

if __name__ == "__main__":
    main()
