MODEL: Gemini 3.8 Flash (High)

# G4 Streak Correction and Missing Interval Diagnosis

Re-evaluation of G4 benchmark runs (`results/blite/synth5/g45/`): `g4_incident`, `g4_control_a`, and `g4_control_b_shock`.

## 1. Summary of G4 Re-evaluation

The streak rule requires $B(t) \ge 3.0$ (or variant $B(t) > 3.0$) at two timestamps exactly 30 s apart ($t_2 - t_1 = 30$ s). Any missing interval resets the consecutive streak counter to 0.

| Run | Condition | Max $B$ | Original Alarm (s) | Corrected Alarm $B \ge 3.0$ (s) | Corrected Alarm $B > 3.0$ (s) | Qualifying Alarms (Old vs New) | Status |
|---|---|---|---|---|---|---|---|
| Incident (`proxy.rou.xml`) | Incident 4,500–5,400 s | 17.16 | 4860.0 | **4890.0** | **4890.0** | 22 vs 19 | **DETECTED (PASS)** |
| Control (a) (`proxy.rou.xml`) | No incident | 2.57 | None | **None** | **None** | 0 vs 0 | **SILENT (PASS)** |
| Control (b) Shock (`proxy_shock.rou.xml`) | No incident (+30% shock) | 2.73 | None | **None** | **None** | 0 vs 0 | **SILENT (PASS)** |

### Key Findings:
1. **Original Alarm Kept**: The original evaluation reported a first alarm at **4,860.0 s**.
2. **Corrected Alarm**: The corrected first alarm is at **4,890.0 s** under both $B \ge 3.0$ and $B > 3.0$. Detection delay after incident start (4,500 s) is **390 s** (compared to the flawed 360 s).
3. **Root Cause of Timing Flaw**: The original `evaluate_crossings` in `run_g45.py` executed `B.dropna().sort_index()` and iterated over sequential index rows without verifying $t_i - t_{i-1} == 30$ s. At $t = 4,800$ s, $B = 4.71 \ge 3.0$. At $t = 4,830$ s, downstream sensor packet loss caused $B(4830)$ to be NaN (omitted). At $t = 4,860$ s, $B = 5.01 \ge 3.0$. The old code chained 4,800 s and 4,860 s (60 s apart) as two consecutive intervals, falsely triggering at 4,860 s. Correctly resetting on the missing 4,830 s interval means 4,860 s starts a new streak of 1, and 4,890 s ($B = 3.76$) completes streak 2.
4. **False Alarm Controls**: Both `g4_control_a` (max $B = 2.57$) and `g4_control_b_shock` (max $B = 2.73$) remain completely silent (0 alarms) under both old and new rules.
5. **Strict vs Weak Inequality Variant**: Exactly identical results for $B > 3.0$ vs $B \ge 3.0$ across all runs. At all crossing timestamps, $B > 3.000$ strictly (the lowest crossing value in `g4_incident` was 3.7618).

## 2. Crossings Timestamps Comparison (`g4_incident`)

- **Original Alarms (22 intervals)**:
  `4860.0, 4890.0, 4920.0, 4950.0, 4980.0, 5040.0, 5070.0, 5160.0, 5190.0, 5220.0, 5250.0, 5280.0, 5310.0, 5340.0, 5370.0, 5400.0, 5430.0, 5460.0, 5490.0, 5520.0, 5850.0, 6420.0`
- **Corrected Alarms (19 intervals)**:
  `4890.0, 4920.0, 4950.0, 4980.0, 5070.0, 5190.0, 5220.0, 5250.0, 5280.0, 5310.0, 5340.0, 5370.0, 5400.0, 5430.0, 5460.0, 5490.0, 5520.0, 5850.0, 6420.0`
- **Spurious Alarms Eliminated by Correction (3 intervals)**:
  - **4,860.0 s**: Previous timestamp 4,830.0 s was missing; interval distance to 4,800.0 s was 60 s.
  - **5,040.0 s**: Previous timestamp 5,010.0 s was missing; interval distance to 4,980.0 s was 60 s.
  - **5,160.0 s**: Previous timestamp 5,130.0 s was missing; interval distance to 5,070.0 s was 90 s.

## 3. Diagnosis of Missing Intervals by Reason

In `run_g45.py`: `compute_bottleneck_index` defines:
$$B(t) = 0.5 (r_{U, o} - r_{D, o}) + 0.5 (r_{D, v}.\text{fillna}(0) - r_{U, v}.\text{fillna}(0))$$
Where $U = \text{AID02109}$ and $D = \text{AID02111}$.

### Diagnostic Findings:
- **Speed nulls do NOT cause missing $B$ intervals**: Although `read_detectors` returns speed `v = None` when a 30-s interval has zero vehicle arrivals ($q = 0$), `compute_bottleneck_index` explicitly applies `.fillna(0)` to both $r_{U, v}$ and $r_{D, v}$. Thus speed nulls are safely imputed and never result in NaN.
- **Sensor packet loss on occupancy IS the sole cause**: The sensor emulator (`SensorEmulator` in `citypulse/proxy/sensors.py`) applies a random communication packet loss with rate `loss = 0.05` per detector:
  ```python
  if self.rng.random() < self.loss:
      obs.append({'detector': d, 'q': None, 'v': None, 'o': None, 'valid': False})
  ```
  Whenever packet loss occurs on either AID02109 or AID02111, `obs_valid = False` and `obs_o = None`. Consequently, $r_{U, o}$ or $r_{D, o}$ is NaN, rendering $B(t)$ NaN.
- **Theoretical vs Observed Loss Rate**:
  For two independent detectors each with loss probability $p = 0.05$, the probability of at least one detector loss per 30-s interval is:
  $$P(\text{missing}) = 1 - (1 - 0.05)^2 = 0.0975 \quad (9.75\%)$$
  Over 240 intervals (7,200 s), the expected number of missing intervals is $240 \times 0.0975 = 23.4$.
  The observed missing interval counts match theoretical expectation precisely:
  - `g4_incident`: **24** / 240 (10.0%)
  - `g4_control_a`: **27** / 240 (11.25%)
  - `g4_control_b_shock`: **25** / 240 (10.42%)

### Breakdown by Reason per Run

| Run | Total Missing | Upstream AID02109 Loss | Downstream AID02111 Loss | Both Detectors Lost | Zero-Vehicle Speed Nulls (`v=None`) |
|---|---|---|---|---|---|
| `g4_incident` | 24 / 240 | 14 | 10 | 0 | 0 (imputed via fillna) |
| `g4_control_a` | 27 / 240 | 20 | 6 | 1 | 0 (imputed via fillna) |
| `g4_control_b_shock` | 25 / 240 | 16 | 9 | 0 | 0 (imputed via fillna) |

### Complete Inventory of Missing Timestamps

#### `g4_incident` (24 missing intervals)
| Timestamp $t$ (s) | Cause | Upstream AID02109 | Downstream AID02111 |
|---|---|---|---|
| 300.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=2.0 |
| 390.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 960.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1200.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=19.0 | obs_valid=False, packet dropped (None) |
| 1230.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1320.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 1410.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1470.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=8.0 | obs_valid=False, packet dropped (None) |
| 2010.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=3.0 |
| 2250.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 2490.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=13.0 | obs_valid=False, packet dropped (None) |
| 2670.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=20.0 | obs_valid=False, packet dropped (None) |
| 2700.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 3510.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 4020.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4710.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=13.0 | obs_valid=False, packet dropped (None) |
| 4830.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=23.0 | obs_valid=False, packet dropped (None) |
| 5010.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=13.0 | obs_valid=False, packet dropped (None) |
| 5100.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=11.0 | obs_valid=False, packet dropped (None) |
| 5130.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=0.0 |
| 6150.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=19.0 | obs_valid=False, packet dropped (None) |
| 6180.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=13.0 |
| 6450.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 7080.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=21.0 | obs_valid=False, packet dropped (None) |

#### `g4_control_a` (27 missing intervals)
| Timestamp $t$ (s) | Cause | Upstream AID02109 | Downstream AID02111 |
|---|---|---|---|
| 300.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=2.0 |
| 390.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 960.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1200.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=19.0 | obs_valid=False, packet dropped (None) |
| 1230.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1320.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 1410.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1470.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=8.0 | obs_valid=False, packet dropped (None) |
| 2010.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=3.0 |
| 2250.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 2490.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=13.0 | obs_valid=False, packet dropped (None) |
| 2670.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=20.0 | obs_valid=False, packet dropped (None) |
| 2700.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 3510.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 4020.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4650.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4710.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 5100.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=17.0 | obs_valid=False, packet dropped (None) |
| 5160.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 5220.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=18.0 | obs_valid=False, packet dropped (None) |
| 5280.0 | Both U and D lost/invalid | obs_valid=False, packet dropped (None) | obs_valid=False, packet dropped (None) |
| 5490.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 5550.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 5640.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 5880.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 6300.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 6990.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |

#### `g4_control_b_shock` (25 missing intervals)
| Timestamp $t$ (s) | Cause | Upstream AID02109 | Downstream AID02111 |
|---|---|---|---|
| 300.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=2.0 |
| 390.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 960.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1200.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=19.0 | obs_valid=False, packet dropped (None) |
| 1230.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1320.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 1410.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=6.0 |
| 1470.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=8.0 | obs_valid=False, packet dropped (None) |
| 2010.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=3.0 |
| 2250.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 2490.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=13.0 | obs_valid=False, packet dropped (None) |
| 2670.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=20.0 | obs_valid=False, packet dropped (None) |
| 2700.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 3510.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 4020.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4650.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4710.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |
| 4890.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=8.0 |
| 5160.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=22.0 | obs_valid=False, packet dropped (None) |
| 5280.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=19.0 | obs_valid=False, packet dropped (None) |
| 5670.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=4.0 |
| 5940.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=22.0 | obs_valid=False, packet dropped (None) |
| 6510.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=25.0 | obs_valid=False, packet dropped (None) |
| 7050.0 | Downstream AID02111 sensor loss (obs_valid=False) | obs_valid=True, q=20.0 | obs_valid=False, packet dropped (None) |
| 7080.0 | Upstream AID02109 sensor loss (obs_valid=False) | obs_valid=False, packet dropped (None) | obs_valid=True, q=7.0 |

REPORT DONE