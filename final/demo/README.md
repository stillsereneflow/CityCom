# Offline Decision Audit Demo and Verification Guide

This directory contains the decision card CLI tool, generated decision cards across the frozen test seeds, and instructions to reproduce metrics and inspect simulation state snapshots.

---

## 1. Decision Card CLI (`decision_card.py`)

The decision card CLI reads exclusively from `results/frozen_audit/raw.parquet` (no simulation executed) and prints the offline decision comparison between the Twin model and the hidden Proxy environment.

### Basic Usage
To run the decision card for any frozen seed (4501–4508):
```bash
python final/demo/decision_card.py --seed 4501
```

Optional arguments:
- `--belief`: Twin belief variant, default is `B` (e.g. `--belief B` or `--belief D300`).
- `--raw-path`: Path to `raw.parquet` if running from outside the repository root.

### Running All 8 Frozen Test Seeds
To regenerate `decision_cards.txt` for all frozen seeds:
```powershell
4501..4508 | ForEach-Object { python final/demo/decision_card.py --seed $_ } | Out-File -Encoding utf8 final/demo/decision_cards.txt
```
Pre-generated outputs for all 8 seeds are saved in `final/demo/decision_cards.txt`.

---

## 2. Reproducing Frozen Audit Metrics

To reproduce the frozen audit metrics and validation checks directly from the collected results:
```bash
python -m citypulse.experiments.frozen_audit_analyze analyze --dir results/frozen_audit
```

This verifies the RNG binding against `results/frozen_audit/rng_check.json`, executes the preregistered estimands across seeds 4501–4508, and reports pooled benefit estimation error (BEE), regret, Top-1 agreement, and CRN correlation.

---

## 3. Opening Decision-Time Snapshots in SUMO GUI

The decision-time snapshot at $t_d = 5,100\text{ s}$ captures the corridor state (traffic queues and vehicle placements) right before mitigation actions are applied.

### Finding the SUMO Binaries
The SUMO binaries are packaged inside the environment's `eclipse-sumo` package (`sumo_home`):
- GUI binary: `D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo-gui.exe`
- Headless binary: `D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo.exe`

### Configuration and Network Arguments
In accordance with `citypulse/sim.py` (`proxy_cmd` and `base_cmd`) under `CITYPULSE_NET=blite` and `CITYPULSE_BLITE_REV=5`:
- **Network (`-n`)**: `scenarios/kwuntong/blite/net5.net.xml`
- **Additional files (`-a`)**:
  - Vehicle types: `scenarios/kwuntong/vtypes_proxy.add.xml`
  - Detectors: `scenarios/kwuntong/blite/detectors5.add.xml`
  - Signal plans: `scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml,scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml`
- **Snapshot (`--load-state`)**: `results/frozen_audit/runs/seed_<SEED>/proxy/proxy_state_5100.xml.gz`

### Exact Command to Open in `sumo-gui`
Run the following command from the repository root (`D:\CityCom-astra`):
```cmd
"D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo-gui.exe" -n scenarios/kwuntong/blite/net5.net.xml -a scenarios/kwuntong/vtypes_proxy.add.xml,scenarios/kwuntong/blite/detectors5.add.xml,scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml,scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml --load-state results/frozen_audit/runs/seed_4501/proxy/proxy_state_5100.xml.gz
```

### Verification Command (1 Step Headless SUMO)
To verify that the arguments and state file are completely valid without launching the GUI window, run 1 simulation step ($5,100\text{ s} \to 5,101\text{ s}$):
```cmd
"D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo.exe" -n scenarios/kwuntong/blite/net5.net.xml -a scenarios/kwuntong/vtypes_proxy.add.xml,scenarios/kwuntong/blite/detectors5.add.xml,scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml,scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml --load-state results/frozen_audit/runs/seed_4501/proxy/proxy_state_5100.xml.gz --begin 5100 --end 5101 --no-step-log true --no-warnings true
```
This headless step executes cleanly and exits with status code 0.
