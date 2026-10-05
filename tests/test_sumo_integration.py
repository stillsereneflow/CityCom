"""SUMO integration checks (each starts real SUMO processes; ~20 s total)."""
import json

import libsumo
import traci

from citypulse.config import RESULTS, sumo_bin
from citypulse.sim import init_signals, twin_cmd
from citypulse.scenario import CONTROL


def test_sumo_and_traci_available():
    import subprocess
    out = subprocess.run([sumo_bin(), "--version"], capture_output=True, text=True)
    assert "Eclipse SUMO sumo" in out.stdout


def test_init_signals_resets_last_loaded_program(tmp_path):
    from citypulse.sim import get_control
    control = get_control()
    traci.start(twin_cmd(1), label="t_init")
    tc = traci.getConnection("t_init")
    tls = control["tls_plan"][0]
    before = tc.trafficlight.getProgram(tls)
    progs = [l.programID for l in tc.trafficlight.getAllProgramLogics(tls)]
    init_signals(tc)
    after = tc.trafficlight.getProgram(tls)
    tc.close()
    assert before == "P_inc"     # SUMO activates the last loaded program
    assert after == ("webster" if "webster" in progs else "0")


def test_new_process_load_keeps_vehicles_but_not_lane_closures(tmp_path):
    from citypulse.twin.demand_stream import TwinDemandStream
    from citypulse.sim import get_control
    control = get_control()
    target_lane = f"{control.get('vms_target_edge', '312049503')}_0"
    traci.start(twin_cmd(1), label="t_snap")
    tc = traci.getConnection("t_snap")
    init_signals(tc)
    s = TwinDemandStream(seed=3)
    for _ in range(200):
        s.insert_due(tc, tc.simulation.getTime() + 1)
        tc.simulationStep()
    tc.lane.setDisallowed(target_lane, ["passenger"])
    n = tc.vehicle.getIDCount()
    state = str(tmp_path / "s.xml.gz")
    tc.simulation.saveState(state)
    tc.close()
    libsumo.start(twin_cmd(1, ["--load-state", state]))
    n2 = libsumo.vehicle.getIDCount()
    dis = libsumo.lane.getDisallowed(target_lane)
    libsumo.close()
    assert n2 == n
    assert "passenger" not in dis   # lane closures must be re-applied after load (ControlState)


def test_branch_conformance_result_recorded():
    f = RESULTS / "branch_benchmark.json"
    if not f.exists():
        import pytest
        pytest.skip("run citypulse.experiments.branch_benchmark first")
    b = json.load(open(f))
    assert b["conformance"]["identical"] is True
    assert all(b["parallel_equals_sequential"])
