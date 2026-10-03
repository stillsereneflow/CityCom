MODEL: deepseek-v4.1-flash
# B-lite net5: repaired entry, repaired diverge D, insertion stub `tko_insert`

Binding spec: the Astra decision of 2026-10-03 quoted in
`C:/Users/chenq/.claude/runs/D--CityCom/20261003-1823-codex-astra-entry/out.md`; evidence base
`results/blite/synth/diag_entry2/report.md`.  net4 and every earlier result are untouched: no
net4/`synth/` file was written or edited, and the net5 build is a separate code path
(`--net5`) that leaves the net4 path byte-reproducible.

## 1. Files built (SHA-256)

| File | SHA-256 |
|---|---|
| `scenarios/kwuntong/blite/net5.net.xml` | `8ab6c9e8ef0cc4d03b690d8f8210aad8c7a88c384d782df673079830a6c012d8` |
| `scenarios/kwuntong/blite/detectors5.add.xml` | `2a45506ca311feb1be076afb774914e1c65ca1b66d46a465bcfdfaa3a65d78cf` |
| `scenarios/kwuntong/blite/synth5/proxy.rou.xml` | `86a19d8f7a2a72fff1c864eee17f249e77b952525bcfa487588d1d5efc8bfa93` |
| `scenarios/kwuntong/blite/synth5/proxy_shock.rou.xml` | `78926be5a23ef2133ca5b8944ef1446a758409d5ab02fafce090107ff61aff3f` |
| `scenarios/kwuntong/blite/synth5/twin_cand.rou.xml` | `a449427a0cb47e6efe31d16a98365aa115d1f146fd2ad5af40355ed52dd4e212` |
| `scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml` | `e92e4d52fd72dd6657dcb715f89713967e7835544b96070c30c8e142bc2b6bac` |
| `scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml` | `e7219af2140e3f63a863894d51bb75301ba19826c7efcf83052dc384527547e5` |
| `results/blite/net5/scratch/tls_base5.add.xml` | `cfeed76f57a8f68c0ebfdc9069831de77ee444d64af5513550017c6a264c3836` |
| `results/blite/net5/scratch/tls_incident5.add.xml` | `e54fabfce8f1e55a4a56d97382f582913403449fde6edaebf80f758294cb6a95` |

`detectors5.add.xml` is byte-identical to `detectors4.add.xml`, and both signal files in
`results/blite/net5/scratch/` are byte-identical to `tls_base4.add.xml` / `tls_incident4.add.xml`:
**no signal link index moved at S1-S4, so nothing was remapped**.  The generated programs are
written into the net5 scratch directory (not into the scenario directory) so that the scenario
directory gains only the two allowed new files.  `synth5/tls_webster_synth.add.xml` and
`synth5/tls_incident_synth.add.xml` are byte copies of the `synth/` plans.

## 2. Changes, with file:line

### 2.1 `citypulse/network/blite.py` (net5 build path; net4 path unchanged)

| Line | Change |
|---|---|
| `blite.py:88` | `NET5_ENTRY = ((0,0), (0,1), (1,2))` - the repaired `tko_in -> tko_1` mainline set. |
| `blite.py:91` | `NET5_D = ((0,"tko_a1",0), (1,"ktb_w1",0), (2,"ktb_w1",1))` - exactly the three mainline links at D. |
| `blite.py:100` | `NET5_FAN_OUT, NET5_FAN_BACK, NET5_FAN_LATERAL = 25.0, 75.0, 12.0` - the `tko_a1` fan (section 3). |
| `blite.py:107` | `NET5_INSERT, NET5_INSERT_LANES, NET5_INSERT_SPEED = 500.0, 3, 70`; `NET5_INSERT_CONNS = ((0,0),(1,1),(2,1))`. |
| `blite.py:346` | `build_graph(..., net5=False)` - one switch, default off. |
| `blite.py:422` | `off_tko_vms` is **dropped** (node and edge are not emitted) - see section 4. |
| `blite.py:444` | at node `D`: the three `NET5_D` links plus the unchanged subordinate on-ramp links (`on_tko_a1 -> tko_a1_{1,2}`, `on_ktb_w1 -> ktb_w1_1`); the net4 five-link set is in the `else` branch. |
| `blite.py:461` | at node `j1`: exactly `NET5_ENTRY` plus the unchanged `tko_in_1 -> off_tko_in_0` take-off and the `on_tko_1 -> tko_1_2` merge. |
| `blite.py:494-512` | insertion stub: node `ins_src` 500 m upstream of `src`, edge `tko_insert` (3 lanes, 70 km/h, 500 m), the `NET5_INSERT_CONNS` merge, `src` becomes `type="zipper"`, and the `tko_a1` fan shape. |
| `blite.py:526` | new CLI flag `--net5`. |
| `blite.py:547` | net5 writes the generated signal programs into `--scratch` instead of the scenario directory. |
| `blite.py:556` | optional `shape` attribute in the edge writer (only set for `tko_a1` in net5; net4 emits no shape). |

### 2.2 `citypulse/demand/synth_demand.py` (net5 option)

| Line | Change |
|---|---|
| `synth_demand.py:58` | `SYNTH5_DIR`, `NET5`, `INSERT_EDGE`, `TKO_ENTRY`, `SYNTH5_ROUTE_FILES`, `SYNTH5_TLS_FILES`. |
| `synth_demand.py:349` | `build_synth5()`: copies `proxy.rou.xml`, `proxy_shock.rou.xml`, `twin_cand.rou.xml`, prepends `tko_insert` to every route that starts at `tko_in`, sets `departLane="free"` / `departSpeed="max"` on those vehicles, copies the two signal plans byte-for-byte, and asserts departure time, class, destination, first edge and count against the `synth/` source. |
| `synth_demand.py:414` | `--net5` CLI flag. |

### 2.3 `citypulse/sim.py` (only so that `CITYPULSE_BLITE_REV=5` selects the net5 files)

| Line | Change |
|---|---|
| `sim.py:54` | `get_tls_file()`: `rev == "5"` returns `synth5/tls_webster_synth.add.xml,tls_incident_synth.add.xml` (net5's own plans) instead of the net4 grid plan plus the missing `tls_incident5.add.xml`. |
| `sim.py:90` | `get_detector_map()`: a missing `detector_map<rev>.json` now falls back to the net4 map before the net3 map (net5's map lives in `results/blite/net5/scratch/`, its detector set is net4's).  Revs 2/3/4 keep their existing files, so only rev 5 changes. |

`get_net_file()` and `get_det_file()` already resolved `net5.net.xml` / `detectors5.add.xml`
from `CITYPULSE_BLITE_REV=5`; no change was needed there.

## 3. Diverge D: why `tko_a1` needs a shape

In this lefthand network SUMO numbers lanes from the left: `tko_vms_0` is the **leftmost**
lane (measured lateral offset +3.2 m; `tko_in_0` +1.6 m, `tko_1_0` +3.2 m, `ktb_w1_0` +1.6 m -
`results/blite/net5/probe_geom.py`).  The chainage-based nodes put the bypass on the left of
the corridor (`ktb_w1` leaves D at 241.7 deg) and the arterial on the right (`tko_a1` at
258.1 deg, node `j3` 34 m right of the `tko_vms` axis, `A1` 35 m left of it).  With the
specified lane assignment (`tko_vms_0 -> tko_a1_0`) the three connectors therefore cross if
`tko_a1` keeps net4's straight chord from D to `j3`: that is exactly the crossing net4 has
(`probe_internal.py` on net4 finds `tko_vms_0->tko_a1_0` crossing both bypass links, and
netconvert makes it minor `m` with `response` bits against them).

net5 places `tko_a1` on the side of lane 0 - the arterial's three lanes leave D fanned out on
the left of the `tko_vms` axis (12 m left at 25 m out) and rejoin the net4 chord 75 m
downstream, so `tko_a1` lane 0 starts left of `ktb_w1` lane 0 and the connectors leave the
junction in lane order.  The edge end, the `j3` junction, the downstream geometry, the edge
length (204.8 m) and the detector chainage are unchanged.  This is a deliberate, documented
local geometry change; the alternative (keeping the chord and accepting the crossing) is what
the spec forbids ("do not merely erase foe bits over crossing geometry").

Two consequences, stated plainly:

* The two branch **edges** (`tko_a1` and `ktb_w1`) now cross each other about 50 m past the
  junction exit, because the frozen chainage nodes put `j3` to the right of `A1` while lane 0
  is on the left.  The three **connectors** do not cross, which is what the junction logic is
  built from; the crossing is a local artifact of the coarse detector chords
  (`AID07106 -> AID07107` at 245 deg against the real 200 deg bearing at `AID07107`) and
  cannot be removed without moving `j3`, `A1` or `D`, i.e. without changing the frozen
  downstream geometry.
* `tko_a1` lane 1 has no mainline link any more, so it would be a dead lane.  The
  zero-demand on-ramp `on_tko_a1` therefore feeds **both** inner arterial lanes (1 and 2)
  instead of lane 2 only; both of its links stay minor.  Without that, check (b) fails.

## 4. Dropped `off_tko_vms`

`off_tko_vms` is **dropped** (edge and node).  Keeping it would need a fourth mainline link
out of `tko_vms` (`tko_vms_2 -> off_tko_vms_0`), which the spec forbids ("remove all other
mainline diverge connections from `tko_vms`"), and without that link the stub lane is
unreachable, i.e. a dead lane.  It carries no demand, no detector and no route, so nothing
else changes.

## 5. Insertion stub

`tko_insert`: exactly 500.0 m, 3 lanes, 19.44 m/s (70 km/h), upstream of the unchanged
2-lane `tko_in` (307.4 m), with `0->0`, `1->1`, `2->1`.  **The node `src` is declared
`type="zipper"`**: with a plain priority node netconvert makes the middle lane minor and the
outer lane major (state `m`/`M`, mutual `response` bits), which is a lane drop with a yield;
the zipper node gives both merging links state `Z` (equal priority, alternating merge) and
keeps `tko_insert_0 -> tko_in_0` major.  `netconvert` accepts the 3-lane-to-2-lane zipper
node without a lane-drop warning.  Every TKO route now departs on the 500 m stub with
`departLane="free"`, `departSpeed="max"`; the shortest required lane-change run is
`tko_in` 307.4 m (>= 150 m), and `tko_insert` 500 m, `tko_1` 276.6 m, `tko_vms` 382.7 m.

## 6. Checks (`results/blite/net5/check5.py`, `check_report.json`)

```
PASS  a_routes_connected: 31075 routes, 0 unconnected
PASS  b_no_dead_lanes: 133 lanes, dead: none
PASS  c_D_no_mutual_foes: links [0, 1, 2] states ['M', 'M', 'M'] offending pairs none
PASS  c2_D_connectors_no_crossing: crossing pairs: none
PASS  d_entry_connections: tko_in->tko_1 = [(0,0), (0,1), (1,2)]
PASS  e_detectors_equal_net4: 62 loops, identical to net4: True
PASS  f_signal_state_lengths: S1-S4 mismatches: none
PASS  g_route_equivalence: 31075 vehicles compared, 0 differences
PASS  x_insert_stub_spec: 500.0 m, 3 lanes, 69.98 km/h
PASS  x_insert_connections: 0->0, 1->1, 2->1
PASS  x_insert_zipper_node: node src type = zipper
PASS  x_tko_1_tko_vms_identity: links = [(0,0), (1,1), (2,2)]
PASS  x_lane_change_room: tko_insert 500.0, tko_in 307.4, tko_1 276.6, tko_vms 382.7 m
```

**(c)** is asserted on the `<request>` rows of junction D.  The bit strings are indexed with
the **last** character for request 0 (SUMO writes them highest index first); that decoding was
verified against a hand-built cross junction (`results/blite/net5/scratch/tiny/`), where the
straight-through link's foes come out as exactly its crossing/merging partners and a left
turn's `response` bits come out as exactly the opposing through movement.  At D in net5:

| req | link | state | response | foes |
|---|---|---|---|---|
| 0 | `tko_vms_0 -> tko_a1_0` | `M` | `000000` | `000000` |
| 1 | `tko_vms_1 -> ktb_w1_0` | `M` | `000000` | `111000` = reqs 3, 4, 5 |
| 2 | `tko_vms_2 -> ktb_w1_1` | `M` | `000000` | `111000` = reqs 3, 4, 5 |
| 3 | `on_tko_a1_0 -> tko_a1_1` | `m` | `000110` | `000110` |
| 4 | `on_tko_a1_0 -> tko_a1_2` | `m` | `000110` | `000110` |
| 5 | `:D_5_0` (`on_ktb_w1 -> ktb_w1_1`) | `m` | `000110` | `000110` |

None of the three mainline links (0, 1, 2) has a foe or response bit against another of the
three, all three are major, and the only foes they have are against the two zero-demand
on-ramp links, which are subordinate (`m`, response bits set) exactly as the spec allows.  No
foe bit was hand-edited: the whole junction logic is netconvert's output from the geometry and
the connection file (`results/blite/net5/scratch/blite5.{nod,edg,con}.xml`).

## 7. Net5 build command

```powershell
cd D:\CityCom-astra
$env:PYTHONDONTWRITEBYTECODE='1'; $env:OPENBLAS_NUM_THREADS='1'
D:\CityCom\.venv\Scripts\python.exe -m citypulse.network.blite --tag 5 --net5 `
    --scratch results/blite/net5/scratch
D:\CityCom\.venv\Scripts\python.exe -m citypulse.demand.synth_demand --net5
D:\CityCom\.venv\Scripts\python.exe results\blite\net5\check5.py
```

New under `results/blite/net5/`: `check5.py`, `check_report.json`, `probe_geom.py`,
`probe_branch.py`, `probe_links.py`, `probe_internal.py`, `scratch/` (`blite5.nod/edg/con.xml`,
`tls_base5.add.xml`, `tls_incident5.add.xml`, `detector_map5.json`, the throwaway
`exp_build.py` / `tiny/` decoders) and this report.  G1-G3 on the net5 demand is in
`results/blite/synth5/g123_report.md`; **G3 failed on 2 of 3 seeds, so no `READY` file was
written and the demand and the network were not changed further.**

REPORT DONE
