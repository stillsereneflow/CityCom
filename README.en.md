# 城脉·涟控 (CityPulse): D1–D4 prototype

**Final evidence package (2026-10-06): `final/README.md`.** It contains the frozen test audit results, the exact allowed claims, figures, tables and demo. The design freeze record is `docs/freeze-2026-10-06.md`.

The design is `deep-research-report2.md`. What has been run and measured is in `docs/d1-d4-validation.md`.

Hidden "Proxy" SUMO world and an independent, structurally different "Twin" SUMO world on the Kwun Tong Road / Kwun Tong Bypass corridor (Hong Kong). The Twin receives only sparse, noisy detector observations over a ZeroMQ firewall. Snapshot branching evaluates candidate interventions in the Twin.

## Setup (Windows, Git Bash)

```bash
uv venv --python 3.12 .venv
```

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

All commands below run from the repository root.

## Hong Kong TD detector data

Record the live feed (corridor detectors only, appends to `data/hk/raw/YYYY-MM-DD.csv`):

```bash
.venv/Scripts/python.exe -m citypulse.hkdata.recorder live --interval 60
```

Backfill from the data.gov.hk historical archive (archive timestamps are about 1 h ahead of the data periods):

```bash
.venv/Scripts/python.exe -m citypulse.hkdata.recorder backfill --start 20260929 --end 20260929 --hours 7 11
```

## Build the scenario

```bash
.venv/Scripts/python.exe -m citypulse.network.build_network
```

This downloads OSM and builds `scenarios/kwuntong/net_full.net.xml` (add `--skip-download` to reuse `data/osm/`). Then prune it to the corridor network actually used (motorway/trunk plus named corridor roads):

```bash
.venv/Scripts/python.exe -c "import sumolib; n=sumolib.net.readNet('scenarios/kwuntong/net_full.net.xml'); open('scenarios/kwuntong/keep_trunk.txt','w').write('\n'.join(e.getID() for e in n.getEdges() if any(k in e.getType() for k in ['motorway','trunk']) or any(k in (e.getName() or '') for k in ['Kwun Tong Road','Kai Fuk','Kwun Tong Bypass'])))"
```

```bash
.venv/Lib/site-packages/sumo/bin/netconvert.exe -s scenarios/kwuntong/net_full.net.xml --keep-edges.input-file scenarios/kwuntong/keep_trunk.txt --keep-edges.components 1 -o scenarios/kwuntong/net.net.xml
```

Download the detector locations, map them to the network, and generate demand and the predefined signal plans:

```bash
curl -s -o data/hk/detector_locations.csv https://static.data.gov.hk/td/traffic-data-strategic-major-roads/info/traffic_speed_volume_occ_info.csv
```

```bash
.venv/Scripts/python.exe -m citypulse.network.map_detectors
```

```bash
.venv/Scripts/python.exe -m citypulse.demand.make_demand --day 2026-09-29 --h0 8 --h1 9 --scale 0.6
```

```bash
.venv/Scripts/python.exe -m citypulse.network.make_tls_plans
```

## Run

Two worlds, incident in the Proxy, snapshots at t = 1500 s (about 75 s wall):

```bash
.venv/Scripts/python.exe -m citypulse.experiments.run_two_worlds --run incident --t-end 3000 --port 5561 --twin-snapshot 1500 --proxy-snapshot 1500
```

```bash
.venv/Scripts/python.exe -m citypulse.experiments.run_two_worlds --run baseline --t-end 3000 --port 5562 --no-incident
```

Snapshot persistence tests (about 2.5 min):

```bash
.venv/Scripts/python.exe -m citypulse.experiments.snapshot_tests
```

Branching and runtime benchmark (needs the incident run; about 3 min):

```bash
.venv/Scripts/python.exe -m citypulse.experiments.branch_benchmark
```

Figures into `docs/figures/`:

```bash
.venv/Scripts/python.exe -m citypulse.experiments.make_figures
```

Tests:

```bash
.venv/Scripts/python.exe -m pytest
```

## Layout

| Path | Role |
|---|---|
| `citypulse/hkdata/` | TD feed parser, live recorder, archive backfill |
| `citypulse/network/` | OSM → SUMO, detector mapping, predefined incident signal plans |
| `citypulse/demand/` | Independent Proxy / Twin demand from HK counts (routeSampler) |
| `citypulse/proxy/` | Proxy service, sensor emulator, incident; `truth_config.py` = Proxy-only truth |
| `citypulse/twin/` | Twin service, Poisson-thinning demand stream |
| `citypulse/bus/messages.py` | The firewall: the only two message types |
| `citypulse/control/actions.py` | Infrastructure-level actions (signal plan, VMS + compliance) |
| `citypulse/branching/engine.py` | Snapshot → parallel branches → KPIs |
| `citypulse/experiments/` | Runners, tests and figure generation |
| `tests/` | pytest suite |

Generated data (`data/`, `results/`, route files) is git-ignored. Network data © OpenStreetMap contributors (ODbL). Traffic data: Transport Department, HKSAR, via DATA.GOV.HK.
