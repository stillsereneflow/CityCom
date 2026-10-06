# Anonymity scan - `submission/source/citypulse_source.zip`

- Built from the committed tree at `HEAD` = `4fe70e01f66955ef087e25986da78f99aa23ca49` with `git archive` (never from the working directory).
- Package: `citypulse_source.zip`, 1249.1 KiB, 140 files, `zipfile.testzip()` clean.
- Scan time: 2026-10-06 18:12:45.

## Patterns searched

Identifying (tier A, must end at zero): `Windows user path`, `Unix user path`, `profile variable`, `user name`, `e-mail address`, `school / institution`, `git author line`, `author trailer`.

Contextual (tier B, machine-specific but carrying no personal identifier): `home-directory tool path`, `machine-specific repo path`, `machine-specific temp path`.

Every file in the archive was scanned - text files line by line, binary files (the two parquet tables) as UTF-8-decoded byte streams.

The scan is exhaustive over the archive: all 140 entries were read back from the finished zip. The git author identity recorded by `git log` (`%an` / `%ae`) was searched for verbatim, as were user names (any suffix of the recorded name), e-mail addresses, Windows and Unix user-profile paths, the profile environment variable, Chinese and English school names, comment author lines (`Author:`, `Co-authored-by:`, `Signed-off-by:`, the at-sign author trailer) and git author lines. Every pattern is assembled from fragments at run time, so neither this report nor the packaging script contains any of the strings they search for.

The anonymity reports use these placeholders for the identifying strings they describe: 〈用户名样例〉 〈邮箱样例〉 〈姓名样例〉 〈院校样例〉 〈本地用户路径样例〉 (user name, e-mail, personal name, institution, local user path).

A file is rewritten in the packaged copy only when it carries a tier A (personal-identifier) hit; had such a hit sat in a file whose sha256 the freeze manifest records, the packager would still redact it and flag the resulting hash change, because identity outranks integrity. `--selftest` exercises exactly that path on a planted file.

## Redactions applied to the packaged copy

None needed: the included files contain no identifying hit. The redaction pass is still exercised by `--selftest`.

## Remaining identifying hits (must be zero)

**Tier A hits remaining in the archive: 0**


## Contextual matches (reported, not identifying)

11479 matches. These are absolute paths of the build machine (`D:\CityCom-astra`, the frozen interpreter under `D:\CityCom\.venv`), the local agent-run directory `~/.claude/runs/...`, and the machine paths recorded inside the frozen-audit records (`provenance.json`, `seed_check.json`). They contain no user name, no e-mail address and no institution, so they were left byte-identical: most of them live in files whose sha256 is recorded in `results/freeze/freeze_manifest.json`, and altering those bytes would break the integrity check the package is meant to preserve.

Every match was found by the exhaustive scan of the finished archive; the table only groups the listing by file and category, with the exact count and up to four examples per group, because the audit records legitimately contain thousands of machine paths.

| File | Category | Matches | Examples (line: match) |
| --- | --- | --- | --- |
| `citypulse/experiments/event_pilot.py` | machine-specific repo path | 1 | 20: `D:/CityCom-astra` |
| `citypulse/experiments/normal_assim_eval.py` | machine-specific repo path | 1 | 19: `D:/CityCom-astra` |
| `docs/freeze-2026-10-06.md` | home-directory tool path | 1 | 65: `~/.claude/runs/D--CityCom/20261006-0700-codex-sol-freeze/out.md` |
| `docs/freeze-2026-10-06.md` | machine-specific repo path | 1 | 8: `D:/CityCom/.venv` |
| `docs/oct16-frozen-audit-plan.md` | home-directory tool path | 2 | 3: `~/.claude/runs/D--CityCom/20261006-0000-codex-sol-mqresult/out.md`; 55: `~/.claude/runs/D--CityCom/20261006-0310-codex-sol-frozenprereg/out.md` |
| `final/CLAIMS.md` | home-directory tool path | 1 | 3: `~/.claude/runs/D--CityCom/20261006-1450-codex-sol-finalresult/out.md` |
| `final/FINAL_REPORT.md` | machine-specific repo path | 1 | 101: `D:/CityCom-astra` |
| `final/demo/README.md` | machine-specific repo path | 5 | 47: `D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo-gui.exe`; 48: `D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo.exe`; 60: `D:\CityCom-astra`; 62: `D:\CityCom\.venv\Lib\site-packages\sumo\bin\sumo-gui.exe`; ... 1 more |
| `final/figures/generate_figures.py` | machine-specific repo path | 1 | 2: `D:/CityCom-astra` |
| `results/frozen_audit/crosscheck_agypro/compare.py` | machine-specific repo path | 3 | 4: `D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.json`; 7: `D:/CityCom-astra/results/frozen_audit/metrics.json`; 60: `D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.md` |
| `results/frozen_audit/crosscheck_agypro/crosscheck.py` | machine-specific repo path | 4 | 33: `D:/CityCom-astra/results/frozen_audit/raw.parquet`; 141: `D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/per_seed.csv`; 174: `D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.json`; 177: `D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.md` |
| `results/frozen_audit/metrics.json` | machine-specific repo path | 1 | 4151: `D:\\CityCom\\.venv\\Scripts\\python.exe` |
| `results/frozen_audit/provenance.json` | machine-specific repo path | 42 | 30: `D:\\CityCom\\.venv\\Scripts\\python.exe`; 38: `D:\\CityCom-astra\\scenarios\\kwuntong\\blite\\synth5\\twin_cand.rou.xml`; 44: `D:\\CityCom-astra\\results\\assim\\na300\\sigma300_dev.json`; 51: `D:\\CityCom\\.venv\\Scripts\\python.exe`; ... 38 more |
| `results/frozen_audit/rng_check.json` | machine-specific repo path | 1 | 205: `D:\\CityCom\\.venv\\Scripts\\python.exe` |
| `results/frozen_audit/seed_check.json` | machine-specific repo path | 11406 | 15: `D:\\CityCom-astra\\results\\.pytest_tmp\\test_backlog_classification_do0\\bac...`; 16: `D:\\CityCom-astra\\results\\.pytest_tmp\\test_backlog_classification_do0\\bac...`; 17: `D:\\CityCom-astra\\results\\.pytest_tmp\\test_backlog_classification_do0\\bac...`; 18: `D:\\CityCom-astra\\results\\.pytest_tmp\\test_backlog_classification_do0\\bac...`; ... 11402 more |
| `scenarios/kwuntong/blite/net5.net.xml` | machine-specific repo path | 5 | 7: `D:\CityCom-astra\results\blite\net5\scratch\blite5.nod.xml`; 8: `D:\CityCom-astra\results\blite\net5\scratch\blite5.edg.xml`; 9: `D:\CityCom-astra\results\blite\net5\scratch\blite5.con.xml`; 10: `D:\CityCom-astra\results\blite\net5\scratch\tls_base5.add.xml`; ... 1 more |
| `scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml` | machine-specific repo path | 3 | 5: `D:\CityCom-astra\scenarios\kwuntong\blite\net4.net.xml`; 6: `D:\CityCom-astra\scenarios\kwuntong\blite\synth\tls_webster_synth.add.xml`; 7: `D:\CityCom-astra\scenarios\kwuntong\blite\synth\proxy.rou.xml` |

## Integrity against the freeze manifest

- 72 included paths are covered by `sha256_code` / `sha256_assets`: 1 changed after the freeze by pre-collection tooling commits (dcec083 e3e8083 972a50f), 60 match, 8 match after LF/CRLF normalisation, 3 match to collection provenance (pre-collection tooling fix).
- changed after the freeze by pre-collection tooling commits (dcec083 e3e8083 972a50f): `citypulse/experiments/frozen_audit_analyze.py`
- match after LF/CRLF normalisation: `scenarios/kwuntong/blite/detector_map.json`, `scenarios/kwuntong/blite/detectors5.add.xml`, `scenarios/kwuntong/blite/net5.net.xml`, `scenarios/kwuntong/blite/synth5/proxy.rou.xml`, `scenarios/kwuntong/blite/synth5/proxy_shock.rou.xml`, `scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml`, `scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml`, `scenarios/kwuntong/blite/synth5/twin_cand.rou.xml`
- match to collection provenance (pre-collection tooling fix): `citypulse/branching/audit_engine.py`, `citypulse/experiments/decision_audit.py`, `citypulse/experiments/frozen_audit.py`
- The freeze manifest was computed on the Windows checkout (CRLF); `git archive` exports the LF blob (`.gitattributes`: `* text=auto eol=lf`). Re-applying CRLF reproduces the manifest sha256 exactly for these assets, so their content is unchanged.
- The audit-tooling files listed above were changed by the pre-collection fixes recorded in `docs/freeze-2026-10-06.md` (Amendment A); their bytes match either `results/frozen_audit/provenance.json` (`file_hashes`) or the commit that last touched them. The frozen method code (`citypulse/twin`, `citypulse/proxy`, `citypulse/control`) and every scenario asset are byte-identical to the manifest.
- 4 manifest-hashed paths are deliberately not in the package (development-scratch and other-seed assets); the frozen audit needs only the net5/synth5 set listed above.

## Files scanned

| File | Bytes |
| --- | --- |
| `REPRODUCE.md` | 13194 |
| `citypulse/__init__.py` | 52 |
| `citypulse/branching/__init__.py` | 0 |
| `citypulse/branching/audit_engine.py` | 31397 |
| `citypulse/branching/engine.py` | 17966 |
| `citypulse/bus/__init__.py` | 0 |
| `citypulse/bus/messages.py` | 2190 |
| `citypulse/config.py` | 1660 |
| `citypulse/control/__init__.py` | 0 |
| `citypulse/control/actions.py` | 2463 |
| `citypulse/demand/__init__.py` | 0 |
| `citypulse/demand/blite_demand.py` | 15128 |
| `citypulse/demand/bounded.py` | 16302 |
| `citypulse/demand/bounded_gates.py` | 10508 |
| `citypulse/demand/make_demand.py` | 7108 |
| `citypulse/demand/synth_demand.py` | 16865 |
| `citypulse/experiments/__init__.py` | 0 |
| `citypulse/experiments/astra_step1.py` | 9193 |
| `citypulse/experiments/astra_step1_check.py` | 5664 |
| `citypulse/experiments/branch_benchmark.py` | 4003 |
| `citypulse/experiments/decision_audit.py` | 109090 |
| `citypulse/experiments/dev_outcomes.py` | 49907 |
| `citypulse/experiments/dev_runs.py` | 24386 |
| `citypulse/experiments/event_pilot.py` | 44121 |
| `citypulse/experiments/frozen_audit.py` | 32367 |
| `citypulse/experiments/frozen_audit_analyze.py` | 32384 |
| `citypulse/experiments/make_figures.py` | 12457 |
| `citypulse/experiments/missing_queue.py` | 30627 |
| `citypulse/experiments/mq_replay.py` | 24887 |
| `citypulse/experiments/net_diag.py` | 6974 |
| `citypulse/experiments/normal_assim_eval.py` | 73465 |
| `citypulse/experiments/obs_metrics.py` | 10706 |
| `citypulse/experiments/obs_score.py` | 10119 |
| `citypulse/experiments/replay_diag.py` | 68369 |
| `citypulse/experiments/run_two_worlds.py` | 2443 |
| `citypulse/experiments/snapshot_tests.py` | 11845 |
| `citypulse/hkdata/__init__.py` | 0 |
| `citypulse/hkdata/obs_set.py` | 7174 |
| `citypulse/hkdata/parse.py` | 2538 |
| `citypulse/hkdata/recorder.py` | 5899 |
| `citypulse/hkdata/run_recorder.py` | 585 |
| `citypulse/network/__init__.py` | 0 |
| `citypulse/network/blite.py` | 33074 |
| `citypulse/network/bounded.py` | 12186 |
| `citypulse/network/build_network.py` | 1920 |
| `citypulse/network/make_tls_plans.py` | 2296 |
| `citypulse/network/map_detectors.py` | 4586 |
| `citypulse/network/patch_network.py` | 25849 |
| `citypulse/proxy/__init__.py` | 0 |
| `citypulse/proxy/incident.py` | 1428 |
| `citypulse/proxy/sensors.py` | 3174 |
| `citypulse/proxy/service.py` | 4644 |
| `citypulse/proxy/truth_blite.py` | 504 |
| `citypulse/proxy/truth_config.py` | 439 |
| `citypulse/scenario.py` | 1873 |
| `citypulse/scenario_blite.py` | 869 |
| `citypulse/sim.py` | 8980 |
| `citypulse/twin/__init__.py` | 0 |
| `citypulse/twin/assim.py` | 5459 |
| `citypulse/twin/demand_stream.py` | 5441 |
| `citypulse/twin/event.py` | 37814 |
| `citypulse/twin/service.py` | 36743 |
| `docs/freeze-2026-10-06.md` | 7446 |
| `docs/oct16-frozen-audit-plan.md` | 7130 |
| `final/CLAIMS.md` | 8459 |
| `final/FINAL_REPORT.md` | 9995 |
| `final/METHOD.md` | 4407 |
| `final/README.md` | 1269 |
| `final/demo/README.md` | 3986 |
| `final/demo/decision_card.py` | 5153 |
| `final/demo/decision_cards.txt` | 12413 |
| `final/figures/fig1_bee_dev_vs_frozen.png` | 82269 |
| `final/figures/fig2_gain_predicted_vs_realised.png` | 75640 |
| `final/figures/fig3_action_gains.png` | 64865 |
| `final/figures/fig4_missing_queue.png` | 73443 |
| `final/figures/fig5_queue_at_decision_time.png` | 96831 |
| `final/figures/figure_data.csv` | 6218 |
| `final/figures/generate_figures.py` | 28572 |
| `final/tables/README.md` | 4878 |
| `final/tables/build_tables.py` | 42925 |
| `final/tables/t1_frozen_per_seed.csv` | 2744 |
| `final/tables/t1_frozen_per_seed.md` | 2334 |
| `final/tables/t2_dev_vs_frozen_pooled.csv` | 4607 |
| `final/tables/t2_dev_vs_frozen_pooled.md` | 4683 |
| `final/tables/t3_event_engine_coverage.csv` | 3708 |
| `final/tables/t3_event_engine_coverage.md` | 4046 |
| `final/tables/t4_missing_queue.csv` | 916 |
| `final/tables/t4_missing_queue.md` | 1334 |
| `final/tables/t5_replay_diagnosis.csv` | 899 |
| `final/tables/t5_replay_diagnosis.md` | 1554 |
| `final/tables/t6_frozen_validation.csv` | 3323 |
| `final/tables/t6_frozen_validation.md` | 3760 |
| `pytest.ini` | 27 |
| `requirements.txt` | 231 |
| `results/freeze/freeze_manifest.json` | 9324 |
| `results/frozen_audit/code_hashes_before_after.json` | 13108 |
| `results/frozen_audit/crosscheck_agypro/compare.py` | 2108 |
| `results/frozen_audit/crosscheck_agypro/crosscheck.py` | 6247 |
| `results/frozen_audit/crosscheck_agypro/per_seed.csv` | 2717 |
| `results/frozen_audit/crosscheck_agypro/summary.json` | 1856 |
| `results/frozen_audit/crosscheck_agypro/summary.md` | 1971 |
| `results/frozen_audit/crosscheck_claude/compare.py` | 2352 |
| `results/frozen_audit/crosscheck_claude/compare_output.txt` | 77 |
| `results/frozen_audit/crosscheck_claude/compare_per_seed.csv` | 8217 |
| `results/frozen_audit/crosscheck_claude/indep_audit.py` | 3297 |
| `results/frozen_audit/crosscheck_claude/output.txt` | 3723 |
| `results/frozen_audit/metrics.json` | 115394 |
| `results/frozen_audit/provenance.json` | 21866 |
| `results/frozen_audit/raw.parquet` | 172399 |
| `results/frozen_audit/report.md` | 13294 |
| `results/frozen_audit/rng_check.json` | 14081 |
| `results/frozen_audit/seed_check.json` | 1085461 |
| `results/frozen_audit/state_history.parquet` | 12026 |
| `scenarios/kwuntong/blite/detector_map.json` | 4745 |
| `scenarios/kwuntong/blite/detectors5.add.xml` | 5512 |
| `scenarios/kwuntong/blite/net5.net.xml` | 99411 |
| `scenarios/kwuntong/blite/synth5/proxy.rou.xml` | 1745441 |
| `scenarios/kwuntong/blite/synth5/proxy_shock.rou.xml` | 1762093 |
| `scenarios/kwuntong/blite/synth5/tls_incident_synth.add.xml` | 1161 |
| `scenarios/kwuntong/blite/synth5/tls_webster_synth.add.xml` | 1823 |
| `scenarios/kwuntong/blite/synth5/twin_cand.rou.xml` | 2601558 |
| `scenarios/kwuntong/vtypes_proxy.add.xml` | 3126 |
| `scenarios/kwuntong/vtypes_twin.add.xml` | 380 |
| `tests/test_assim.py` | 19649 |
| `tests/test_audit.py` | 13300 |
| `tests/test_blite_demand.py` | 7501 |
| `tests/test_bounded_obs.py` | 22882 |
| `tests/test_dev_outcomes.py` | 20899 |
| `tests/test_dev_runs.py` | 9899 |
| `tests/test_event.py` | 37439 |
| `tests/test_firewall.py` | 5335 |
| `tests/test_frozen_audit.py` | 16135 |
| `tests/test_frozen_audit_analyze.py` | 23577 |
| `tests/test_missing_queue.py` | 7348 |
| `tests/test_mq_replay.py` | 3800 |
| `tests/test_obs_set.py` | 7514 |
| `tests/test_replay_diag.py` | 19162 |
| `tests/test_sumo_integration.py` | 2341 |
| `tests/test_synth_demand.py` | 7335 |
| `tests/test_units.py` | 2865 |

