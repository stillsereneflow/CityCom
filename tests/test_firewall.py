"""Information firewall: static import rules, message schema, runtime module isolation, logged fields."""
import ast
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from citypulse.bus.messages import FirewallViolation, validate_reply, validate_sensor

ROOT = Path(__file__).resolve().parents[1]
ONLINE_PKGS = ["twin", "branching"]          # Twin-side code
FORBIDDEN = ("citypulse.proxy", "citypulse.experiments")


def imported_modules(py):
    tree = ast.parse(py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


@pytest.mark.parametrize("pkg", ONLINE_PKGS)
def test_twin_side_never_imports_proxy(pkg):
    bad = []
    for py in (ROOT / "citypulse" / pkg).rglob("*.py"):
        for m in imported_modules(py):
            if m.startswith(FORBIDDEN):
                bad.append(f"{py.name}: {m}")
    assert not bad, bad


def test_shared_scenario_has_no_incident_truth():
    import citypulse.scenario as sc
    text = (ROOT / "citypulse" / "scenario.py").read_text(encoding="utf-8")
    assert "PROXY_ONLY" not in dir(sc) and "t_start" not in text and "lanes" not in text
    import citypulse.scenario_blite as sc_b
    text_b = (ROOT / "citypulse" / "scenario_blite.py").read_text(encoding="utf-8")
    assert "PROXY_ONLY" not in dir(sc_b) and "t_start" not in text_b and "lanes" not in text_b


@pytest.mark.parametrize("net_setting", ["", "v4", "blite"])
def test_twin_process_does_not_load_proxy_modules(net_setting):
    import os
    env = dict(os.environ)
    if net_setting:
        env["CITYPULSE_NET"] = net_setting
    else:
        env.pop("CITYPULSE_NET", None)
    code = ("import sys, citypulse.twin.service, citypulse.branching.engine;"
            "print([m for m in sys.modules if m.startswith('citypulse.proxy')])")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env=env, check=True)
    assert out.stdout.strip() == "[]"


def good_sensor():
    return {"type": "sensor", "t": 30.0, "period": 30,
            "obs": [{"detector": "AID02109", "q": 12, "v": 70.5, "o": 4.0, "valid": True}]}


def test_valid_sensor_passes():
    validate_sensor(good_sensor())


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(incident=True),                              # extra top-level key
    lambda m: m["obs"][0].update(true_occupancy=50.0),              # extra per-detector field
    lambda m: m["obs"][0].update(vehicle_ids=["p1"]),               # vehicle state
    lambda m: m.update(future_demand=[1, 2]),                       # future information
    lambda m: m["obs"][0].pop("valid"),                             # missing field
    lambda m: m["obs"][0].update(q="12"),                           # wrong type
])
def test_sensor_violations_rejected(mutate):
    m = good_sensor()
    mutate(m)
    with pytest.raises(FirewallViolation):
        validate_sensor(m)


def test_reply_only_infrastructure_actions():
    validate_reply({"type": "reply", "t": 30.0, "actions": [{"action": "A2", "params": {}}]})
    with pytest.raises(FirewallViolation):
        validate_reply({"type": "reply", "t": 30.0, "actions": [{"action": "reroute_vehicle",
                                                                    "params": {"vid": "p1"}}]})
    with pytest.raises(FirewallViolation):
        validate_reply({"type": "reply", "t": 30.0, "actions": [{"action": "A2", "params": {"route": ["e1"]}}]})


def _twin_log_path():
    import os
    net = os.environ.get("CITYPULSE_NET", "").strip().lower()
    if net == "blite":
        p = ROOT / "results" / "twoworld_blite" / "incident" / "twin" / "twin_log.parquet"
        if p.exists():
            return p
        p_grid = ROOT / "results" / "blite" / "grid" / "two_worlds" / "twin" / "twin_log.parquet"
        if p_grid.exists():
            return p_grid
    elif net == "v4":
        p = ROOT / "results" / "twoworld_v4" / "incident" / "twin" / "twin_log.parquet"
        if p.exists():
            return p
    return ROOT / "results" / "incident" / "twin" / "twin_log.parquet"


def test_twin_log_contains_only_observations_and_twin_values():
    f = _twin_log_path()
    if not f.exists():
        pytest.skip("run citypulse.experiments.run_two_worlds first")
    cols = set(pd.read_parquet(f).columns)
    assert cols == {"t", "detector", "obs_valid", "obs_q", "obs_v", "obs_o", "twin_q", "twin_v", "twin_o"}


def test_twin_sees_sparse_subset():
    f = _twin_log_path()
    if not f.exists():
        pytest.skip("run citypulse.experiments.run_two_worlds first")
    import json
    import os
    seen = set(pd.read_parquet(f).detector)
    net = os.environ.get("CITYPULSE_NET", "").strip().lower()
    if net == "blite":
        scen_map = ROOT / "scenarios" / "kwuntong" / "blite" / "detector_map.json"
    elif net == "v4":
        scen_map = ROOT / "scenarios" / "kwuntong" / "v4" / "detector_map.json"
    else:
        scen_map = ROOT / "scenarios" / "kwuntong" / "detector_map.json"
    all_dets = {d["id"] for d in json.load(open(scen_map, encoding="utf-8"))["mapped"]}
    assert seen < all_dets and len(seen) <= 0.7 * len(all_dets)
