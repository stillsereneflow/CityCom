"""Unit tests: TD XML parsing, Twin demand stream (CRN thinning), action hashing, sensor emulator."""
import numpy as np

from citypulse.control.actions import u_hash
from citypulse.hkdata.parse import aggregate_detector, parse_raw
from citypulse.proxy.sensors import SensorEmulator
from citypulse.twin.demand_stream import TwinDemandStream

XML = b"""<?xml version="1.0" encoding="utf-8"?><raw_speed_volume_list><date>2026-10-02</date><periods>
<period><period_from>08:00:00</period_from><period_to>08:00:30</period_to><detectors>
<detector><detector_id>AID02109</detector_id><direction>North West</direction><lanes>
<lane><lane_id>Fast Lane</lane_id><speed>80</speed><occupancy>4</occupancy><volume>6</volume><s.d.>3</s.d.><valid>Y</valid></lane>
<lane><lane_id>Slow Lane</lane_id><speed>60</speed><occupancy>6</occupancy><volume>2</volume><s.d.>3</s.d.><valid>Y</valid></lane>
</lanes></detector>
<detector><detector_id>AID01101</detector_id><direction>South</direction><lanes>
<lane><lane_id>Fast Lane</lane_id><speed>70</speed><occupancy>1</occupancy><volume>1</volume><s.d.>1</s.d><valid>N</valid></lane>
</lanes></detector></detectors></period></periods></raw_speed_volume_list>""".replace(b"</s.d><", b"</s.d.><")


def test_parse_filters_corridor_and_aggregates():
    rows = parse_raw(XML)
    assert {r["detector_id"] for r in rows} == {"AID02109"}
    agg = aggregate_detector(rows)[0]
    assert agg["volume"] == 8 and abs(agg["speed"] - 75.0) < 1e-9 and agg["occupancy"] == 5.0


def test_stream_crn_and_seek():
    a, b = TwinDemandStream(seed=5), TwinDemandStream(seed=5)
    ids_a = [v for v, _ in a.due(900)]
    ids_b = [v for v, _ in b.due(900)]
    assert ids_a == ids_b and len(ids_a) > 0
    c = TwinDemandStream(seed=5)
    c.seek(600)
    tail = [v for v, _ in c.due(900)]
    d = TwinDemandStream(seed=5)
    full = [v for v, _ in d.due(900)]
    head = [v for v, _ in TwinDemandStream(seed=5).due(600)]
    assert full == head + tail          # rewind/seek never duplicates or skips


def test_stream_thinning_rate():
    s = TwinDemandStream(seed=1)
    n_cand = sum(1 for c in s.cands if c[0] <= 3600)
    n_acc = len(list(s.due(3600)))
    assert abs(n_acc / n_cand - 1 / s.scale) < 0.02


def test_vms_hash_is_stable_and_uniform():
    assert u_hash("p123") == u_hash("p123")
    u = np.array([u_hash(f"v{i}") for i in range(5000)])
    assert abs(u.mean() - 0.5) < 0.02


def test_sensor_emulator_sparse_noisy_lossy():
    dets = [f"D{i:02d}" for i in range(30)]
    emu = SensorEmulator(dets, seed=1, loss=0.2)
    truth = {d: {"q": 10, "v": 60.0, "o": 5.0} for d in dets}
    msg = emu.emit(30.0, truth)
    assert len(msg["obs"]) == 20                       # every 3rd detector dropped
    assert any(not o["valid"] for o in msg["obs"])      # packet loss
    assert any(o["valid"] and o["q"] != 10 for o in msg["obs"])  # noise
