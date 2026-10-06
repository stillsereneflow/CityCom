Sources: `results/frozen_audit/raw.parquet`, `results/frozen_audit/metrics.json`, `results/frozen_audit/reruns.json`, `results/frozen_audit/code_hashes_before_after.json`, `results/frozen_audit/seed_check.json` and `results/frozen_audit/runs/seed_*/two_world_info.json`; N = 15 checks (7 integrity items + 8 per-seed alarm rows).

| check | value | source |
|---|---|---|
| Rows per world / belief / status | twin/B/ok 240; twin/D300/ok 240; proxy/n/a/ok 240; calibration/n/a/ok 240; total 960 rows (8 seeds x 6 replications x 5 actions per world/belief) | results/frozen_audit/raw.parquet (groupby world, belief, status) |
| Reruns (infrastructure failures rerun once) | 0 reruns recorded (`reruns.json` = []); every branch row has a unique world/seed/replication/action key | results/frozen_audit/reruns.json; results/frozen_audit/raw.parquet |
| RNG isolation check | passed = true (seed 4501); Twin: SUMO-seed-only differs = true (dJ 0.679), demand-only differs = true (dJ -1.657), identical inputs identical = true; Proxy: SUMO-seed-only differs = true, demand-only differs = true, identical inputs identical = true | results/frozen_audit/metrics.json (`rng_check`), results/frozen_audit/rng_check.json |
| Code hashes before/after equal | equal = true; 61 files hashed, 0 differing | results/frozen_audit/code_hashes_before_after.json |
| Blocker placement range (lane, position, stop time) | edge ktb_n1, requested 755.3 m, inserted at t_d = 5,100 s; 480 twin branch rows (B 240, D300 240) x 2 blockers; lane 0 position 755.2577-755.2998 m, lane 1 position 755.2614-755.3000 m; lane 0 stop time 5103-5124 s, lane 1 stop time 5103-5105 s; reuse_blockers = false in every twin row (blockers inserted by the branch) | results/frozen_audit/raw.parquet (blocker_lane_*, blocker_pos_*, blocker_t_stop_*) |
| D300 release checks | 240 D300 twin rows x 2 lanes = 480 release records, all identical: present = true, stopped_at_clear = true, resumed = true, resumed_at = 5400.0 s, stopped_after = false, checked_at = 5401.0 s, released = true; actual_clear_time = 5400.0 s in 240/240 D300 rows | results/frozen_audit/raw.parquet (blocker_release_0/1, actual_clear_time) |
| Seed-check result | passed = true, clean = true; 8 seeds checked (4501-4508), 11406 files scanned, 0 matches, 0 scan failures | results/frozen_audit/seed_check.json |
| Alarm time seed 4501 (t_d = 5,100 s) | first alarm 4920 s; latency 180 s; latency >= 120 s: yes; 20 alarm intervals | results/frozen_audit/runs/seed_4501/two_world_info.json |
| Alarm time seed 4502 (t_d = 5,100 s) | first alarm 4950 s; latency 150 s; latency >= 120 s: yes; 26 alarm intervals | results/frozen_audit/runs/seed_4502/two_world_info.json |
| Alarm time seed 4503 (t_d = 5,100 s) | first alarm 5010 s; latency 90 s; latency >= 120 s: no; 18 alarm intervals | results/frozen_audit/runs/seed_4503/two_world_info.json |
| Alarm time seed 4504 (t_d = 5,100 s) | first alarm 4920 s; latency 180 s; latency >= 120 s: yes; 28 alarm intervals | results/frozen_audit/runs/seed_4504/two_world_info.json |
| Alarm time seed 4505 (t_d = 5,100 s) | first alarm 4890 s; latency 210 s; latency >= 120 s: yes; 22 alarm intervals | results/frozen_audit/runs/seed_4505/two_world_info.json |
| Alarm time seed 4506 (t_d = 5,100 s) | first alarm 4890 s; latency 210 s; latency >= 120 s: yes; 23 alarm intervals | results/frozen_audit/runs/seed_4506/two_world_info.json |
| Alarm time seed 4507 (t_d = 5,100 s) | first alarm 4890 s; latency 210 s; latency >= 120 s: yes; 20 alarm intervals | results/frozen_audit/runs/seed_4507/two_world_info.json |
| Alarm time seed 4508 (t_d = 5,100 s) | first alarm 4980 s; latency 120 s; latency >= 120 s: yes; 17 alarm intervals | results/frozen_audit/runs/seed_4508/two_world_info.json |
