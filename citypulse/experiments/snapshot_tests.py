"""Empirical saveState/loadState persistence tests (SUMO 1.27.1).

Part 1 (Proxy-style world, route file + vTypeDistribution + rerouting devices): at T0 apply runtime
modifications, save, then compare what survives in
  (N) a NEW sumo process started with --load-state, and
  (I) the SAME process after traci.simulation.loadState.
Part 2 (Twin-style world, NO route file, Python insertion stream): determinism of a new-process
continuation vs. the uninterrupted reference.

Determinism metric: md5 of (vehicle id, lane, position) over all vehicles every 10 s for 300 s.
Writes results/snapshot_tests.json.
"""
import hashlib
import json
from pathlib import Path

import traci

from citypulse.config import RESULTS
from citypulse.sim import init_signals, proxy_cmd, twin_cmd

T0, HORIZON = 600, 300
TLS_MODE = "predefined"
TLS_ADD = str(Path(__file__).resolve().parents[2] / "scenarios" / "kwuntong" / "tls_test.add.xml")
OUT = RESULTS / "snapshot"
TLS = "GS_474385689"                                  # switched to P_test at T0
TLS2 = "cluster_1023011761_491588483_991762813"       # left on default "0" (has P_inc loaded last)
LOOP = "AID02110_0"


def sig_step(tc):
    ids = sorted(tc.vehicle.getIDList())
    s = ";".join(f"{v}:{tc.vehicle.getLanePosition(v):.2f}:{tc.vehicle.getLaneID(v)}" for v in ids)
    return hashlib.md5(s.encode()).hexdigest(), len(ids)


def run_signature(tc, steps, stream=None):
    """Returns (signature list, metrics after the first step)."""
    out, first = [], None
    for k in range(steps):
        if stream is not None:
            stream.insert_due(tc, tc.simulation.getTime() + 1)
        tc.simulationStep()
        if k == 0:
            first = {"pending_after_1_step": len(tc.simulation.getPendingVehicles()),
                     "loop_last_interval_n_after_1_step": tc.inductionloop.getLastIntervalVehicleNumber(LOOP)}
        if k % 10 == 9:
            out.append(sig_step(tc))
    return out, first


def pick_vehicles(tc):
    ids = sorted(tc.vehicle.getIDList())
    good = [v for v in ids if not tc.vehicle.getRoadID(v).startswith(":")
            and len(tc.vehicle.getRoute(v)) - tc.vehicle.getRouteIndex(v) >= 3]
    return good[0], good[1], good[2]


def modify(tc, with_stop=True):
    """Apply every runtime modification under test; return the expected values."""
    exp = {"with_stop": with_stop}
    logic = tc.trafficlight.getAllProgramLogics(TLS)[0]
    phases = [tc.trafficlight.Phase(p.duration * 2, p.state, p.duration * 2, p.duration * 2) for p in logic.phases]
    if TLS_MODE == "runtime":   # program created at runtime via setProgramLogic
        tc.trafficlight.setProgramLogic(TLS, tc.trafficlight.Logic("P_test", 0, 0, phases))
    tc.trafficlight.setProgram(TLS, "P_test")   # "predefined": P_test comes from tls_test.add.xml
    tc.trafficlight.setPhase(TLS, 1)
    exp["tls_program"] = "P_test"
    exp["tls_default_program_kept"] = tc.trafficlight.getProgram(TLS2)   # "0"
    lane_a, lane_b = "312049503_0", "312049503_1"
    tc.lane.setDisallowed(lane_a, ["passenger", "bus", "truck"])
    tc.lane.setMaxSpeed(lane_b, 5.0)
    exp["lane_disallowed"] = sorted(tc.lane.getDisallowed(lane_a))
    exp["lane_maxspeed"] = tc.lane.getMaxSpeed(lane_b)
    v_stop, v_route, v_sub = pick_vehicles(tc)
    r = tc.vehicle.getRoute(v_stop)
    e_stop = r[tc.vehicle.getRouteIndex(v_stop) + 2]
    if with_stop:
        tc.vehicle.setStop(v_stop, e_stop, pos=min(20.0, tc.lane.getLength(e_stop + "_0") - 1), laneIndex=0,
                           duration=500)
    exp["stop_vehicle"], exp["stop_edge"] = v_stop, e_stop
    r2 = list(tc.vehicle.getRoute(v_route))
    i2 = tc.vehicle.getRouteIndex(v_route)
    tc.vehicle.changeTarget(v_route, r2[i2 + 1])
    exp["route_vehicle"], exp["route_after"] = v_route, list(tc.vehicle.getRoute(v_route))
    tc.route.add("r_test_added", [r2[i2 + 1], r2[i2 + 2]] if i2 + 2 < len(r2) else [r2[i2 + 1]])
    tc.vehicle.add("py_added", "r_test_added", typeID="p_car0", departLane="best", departSpeed="0")
    tc.vehicle.setSpeedFactor(v_sub, 0.55)
    exp["speedfactor_vehicle"], exp["speedfactor"] = v_sub, 0.55
    tc.vehicle.subscribe(v_sub, [traci.constants.VAR_SPEED])
    exp["sub_vehicle"] = v_sub
    return exp


def check(tc, exp):
    res = {}
    res["vehicle_count"] = (tc.vehicle.getIDCount(), exp["vehicle_count"])
    res["pending_immediately_after_load"] = (len(tc.simulation.getPendingVehicles()), exp["pending"])
    res["tls_program"] = (tc.trafficlight.getProgram(TLS), exp["tls_program"])
    res["tls_phase"] = (tc.trafficlight.getPhase(TLS), exp["tls_phase"])
    res["tls_default_program_kept"] = (tc.trafficlight.getProgram(TLS2), exp["tls_default_program_kept"])
    res["lane_disallowed"] = (sorted(tc.lane.getDisallowed("312049503_0")), exp["lane_disallowed"])
    res["lane_maxspeed"] = (round(tc.lane.getMaxSpeed("312049503_1"), 2), round(exp["lane_maxspeed"], 2))
    vs = exp["stop_vehicle"]
    stops = [s.lane.rsplit("_", 1)[0] for s in tc.vehicle.getStops(vs)] if vs in tc.vehicle.getIDList() else None
    res["vehicle_stop"] = (exp["stop_edge"] in (stops or []), True) if exp["with_stop"] else ("not set", "not set")
    vr = exp["route_vehicle"]
    res["route_change"] = (list(tc.vehicle.getRoute(vr)) if vr in tc.vehicle.getIDList() else None, exp["route_after"])
    res["python_added_vehicle"] = ("py_added" in set(tc.vehicle.getIDList()), exp["py_added_in_network"])
    v = exp["speedfactor_vehicle"]
    res["vehicle_speedfactor"] = (round(tc.vehicle.getSpeedFactor(v), 3) if v in tc.vehicle.getIDList() else None,
                                  exp["speedfactor"])
    res["subscription"] = (bool(tc.vehicle.getSubscriptionResults(exp["sub_vehicle"])), True)
    res["loop_last_interval_n_immediately"] = (tc.inductionloop.getLastIntervalVehicleNumber(LOOP),
                                               exp["loop_last_interval_n"])
    return {k: {"got": g, "expected": e, "preserved": g == e} for k, (g, e) in res.items()}


def fresh(label, extra, seed=1, loading=False):
    log = open(OUT / f"{label}.sumo.log", "w")
    cmd = proxy_cmd(seed, extra=list(extra))
    if TLS_MODE == "predefined":
        i = cmd.index("-a")
        cmd[i + 1] += "," + TLS_ADD
    traci.start(cmd, label=label, stdout=log)
    tc = traci.getConnection(label)
    if not loading:
        init_signals(tc)
    return tc


def sumo_err(label):
    try:
        return " | ".join(l.strip() for l in open(OUT / f"{label}.sumo.log") if "Error" in l)[:300]
    except OSError:
        return ""


def agree(a, b):
    if b is None:
        return None
    same = sum(x[0] == y[0] for x, y in zip(a, b))
    first_diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x[0] != y[0]), None)
    return {"identical_checkpoints": same, "of": len(a), "first_divergence_s": None if first_diff is None
            else (first_diff + 1) * 10, "veh_count_ref_end": a[-1][1], "veh_count_end": b[-1][1]}


def one(tag, extra, with_stop):
    state = str(OUT / f"state_{tag}.xml.gz")
    tc = fresh(f"ref_{tag}", extra)
    for _ in range(T0):
        tc.simulationStep()
    exp = modify(tc, with_stop)
    tc.simulationStep()
    exp.update({"vehicle_count": tc.vehicle.getIDCount(), "pending": len(tc.simulation.getPendingVehicles()),
                "tls_phase": tc.trafficlight.getPhase(TLS),
                "py_added_in_network": "py_added" in set(tc.vehicle.getIDList()),
                "loop_last_interval_n": tc.inductionloop.getLastIntervalVehicleNumber(LOOP)})
    tc.simulation.saveState(state)
    ref_sig, ref_first = run_signature(tc, HORIZON)
    out = {"vehicles": {k: exp[k] for k in ("stop_vehicle", "route_vehicle", "speedfactor_vehicle")},
           "reference_after_1_step": ref_first}

    def after_step(first):
        return {k: {"got": first[k], "expected": ref_first[k], "preserved": first[k] == ref_first[k]} for k in first}

    in_sig = None
    try:
        tc.simulation.loadState(state)
        out["in_process"] = check(tc, exp)
        in_sig, first = run_signature(tc, HORIZON)
        out["in_process"].update(after_step(first))
        tc.close()
        out["in_process_status"] = "OK"
    except Exception as e:  # SUMO may quit on load
        out["in_process_status"] = f"FAILED: {sumo_err(f'ref_{tag}') or e}"
        try:
            traci.switch(f"ref_{tag}")
            traci.close()
        except Exception:
            pass
    new_sig = new2_sig = None
    try:
        tn = fresh(f"new_{tag}", extra + ["--load-state", state], loading=True)
        out["new_process"] = check(tn, exp)
        new_sig, first = run_signature(tn, HORIZON)
        out["new_process"].update(after_step(first))
        tn.close()
        out["new_process_status"] = "OK"
        tn2 = fresh(f"new2_{tag}", extra + ["--load-state", state], seed=999, loading=True)
        new2_sig, _ = run_signature(tn2, HORIZON)
        tn2.close()
    except Exception as e:
        out["new_process_status"] = f"FAILED: {sumo_err(f'new_{tag}') or e}"
        out.setdefault("new_process", {})
    out["determinism"] = {"in_process_vs_ref": agree(ref_sig, in_sig), "new_process_vs_ref": agree(ref_sig, new_sig),
                          "new_process_seed999_vs_ref": agree(ref_sig, new2_sig)}
    return out


def twin_style(rng):
    """No route file: demand inserted from the Twin stream. New-process continuation vs. reference."""
    from citypulse.twin.demand_stream import TwinDemandStream
    tag = "twin_" + ("rng" if rng else "norng")
    extra = ["--save-state.rng"] if rng else []
    state = str(OUT / f"state_{tag}.xml.gz")
    traci.start(twin_cmd(2, extra), label=f"ref_{tag}", stdout=open(OUT / f"ref_{tag}.sumo.log", "w"))
    tc = traci.getConnection(f"ref_{tag}")
    init_signals(tc)
    s = TwinDemandStream(seed=202)
    for _ in range(T0):
        s.insert_due(tc, tc.simulation.getTime() + 1)
        tc.simulationStep()
    tc.simulation.saveState(state)
    t_save = tc.simulation.getTime()
    ref_sig, _ = run_signature(tc, HORIZON, s)
    tc.close()
    res = {}
    for seed in (2, 999):
        lab = f"new_{tag}_{seed}"
        traci.start(twin_cmd(seed, extra + ["--load-state", state]), label=lab, stdout=open(OUT / f"{lab}.sumo.log", "w"))
        tn = traci.getConnection(lab)
        s2 = TwinDemandStream(seed=202)
        s2.seek(t_save)
        sig, _ = run_signature(tn, HORIZON, s2)
        tn.close()
        res[f"new_process_seed{seed}_vs_ref"] = agree(ref_sig, sig)
    return tag, res


def main():
    global TLS_MODE
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for mode, rng, with_stop in [("runtime", True, False), ("predefined", True, True), ("predefined", True, False),
                                 ("predefined", False, True), ("predefined", False, False)]:
        TLS_MODE = mode
        tag = f"{mode}_" + ("rng" if rng else "norng") + ("_stop" if with_stop else "_nostop")
        report[tag] = one(tag, ["--save-state.rng"] if rng else [], with_stop)
    TLS_MODE = "none"
    for rng in (True, False):
        tag, r = twin_style(rng)
        report[tag] = {"determinism": r}
    json.dump(report, open(RESULTS / "snapshot_tests.json", "w"), indent=1, default=str)
    for tag, r in report.items():
        print("==", tag, "| in-process:", r.get("in_process_status"), "| new-process:", r.get("new_process_status"))
        for k in list(r.get("new_process") or r.get("in_process") or {}):
            ip = r.get("in_process", {}).get(k, {})
            nw = r.get("new_process", {}).get(k, {})
            print(f"  {k:36s} new={nw.get('preserved', 'n/a')!s:5s} inproc={ip.get('preserved', 'n/a')!s:5s} "
                  f"got={str((nw or ip).get('got'))[:40]} exp={str((nw or ip).get('expected'))[:40]}")
        print("  determinism", json.dumps(r["determinism"]))


if __name__ == "__main__":
    main()
