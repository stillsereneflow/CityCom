# Number whitelist check

- whitelist: 581 distinct values, 650 literals, 1651 identifiers from `final/CLAIMS.md`, `final/FINAL_REPORT.md`, `final/METHOD.md`, `final/tables/*.md`, `final/demo/decision_cards.txt`, `docs/freeze-2026-10-06.md`, `docs/decision-2026-10-03b-synthetic.md`, `docs/blite-spec.md`, `submission/tools/allowed_extra.txt`.

## `submission\01_项目简表.docx`

28 numeric tokens, 0 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `1` | para 6 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | para 7 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | para 8 | yes | literal `3` in final/CLAIMS.md:9 |
| `1` | para 13 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `15` | para 13 | yes | literal `15` in final/CLAIMS.md:3 |
| `21` | para 14 | yes | literal `21` in final/METHOD.md:13 |
| `14` | para 14 | yes | literal `14` in final/FINAL_REPORT.md:52 |
| `30` | para 14 | yes | literal `30` in final/CLAIMS.md:57 |
| `5` | para 14 | yes | literal `5` in final/CLAIMS.md:27 |
| `10` | para 17 | yes | literal `10` in final/CLAIMS.md:7 |
| `4` | para 17 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | para 17 | yes | literal `6` in final/CLAIMS.md:27 |
| `20` | para 17 | yes | literal `20` in final/CLAIMS.md:23 |
| `5` | para 19 | yes | literal `5` in final/CLAIMS.md:27 |
| `15` | para 19 | yes | literal `15` in final/CLAIMS.md:3 |
| `0/6` | para 33 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `8` | para 36 | yes | literal `8` in final/CLAIMS.md:27 |
| `8/8` | table 1 row 2 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | table 1 row 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | table 1 row 3 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | table 1 row 4 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `95` | table 1 row 4 | yes | literal `95` in final/CLAIMS.md:3 |
| `1.74` | table 1 row 4 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | table 1 row 4 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `-0.03` | table 1 row 5 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | table 1 row 5 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | table 1 row 5 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.825` | table 1 row 6 | yes | literal `0.825` in final/CLAIMS.md:11 |

## `submission\02_作品说明书.docx`

210 numeric tokens, 4 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `1.1` | para 5 | yes | `1.1` is 1.051 in final/tables/t1_frozen_per_seed.md:18 rounded to 1 dp |
| `1.2` | para 13 | yes | `1.2` is 1.171 in final/tables/README.md:38 rounded to 1 dp |
| `1980` | para 14 | **NO** | - |
| `2005` | para 15 | **NO** | - |
| `2006` | para 17 | **NO** | - |
| `1.3` | para 23 | yes | literal `1.3` in docs/freeze-2026-10-06.md:22 |
| `30` | para 25 | yes | literal `30` in final/CLAIMS.md:57 |
| `1` | para 31 | yes | literal `1` in final/CLAIMS.md:9 |
| `3/3` | para 36 | yes | literal `3/3` in final/CLAIMS.md:23 |
| `4` | para 36 | yes | literal `4` in final/CLAIMS.md:9 |
| `1` | para 36 | yes | literal `1` in final/CLAIMS.md:9 |
| `6` | para 37 | yes | literal `6` in final/CLAIMS.md:27 |
| `13` | para 37 | yes | literal `13` in final/CLAIMS.md:27 |
| `25` | para 37 | yes | literal `25` in final/CLAIMS.md:27 |
| `0/6` | para 37 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `5` | para 37 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | para 37 | yes | literal `8` in final/CLAIMS.md:27 |
| `0/13` | para 38 | yes | literal `0/13` in final/CLAIMS.md:25 |
| `6/13` | para 38 | yes | literal `6/13` in final/CLAIMS.md:25 |
| `9` | para 38 | yes | literal `9` in final/tables/README.md:13 |
| `1` | para 40 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | para 41 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `5` | para 42 | yes | literal `5` in final/CLAIMS.md:27 |
| `15` | para 42 | yes | literal `15` in final/CLAIMS.md:3 |
| `8` | para 45 | yes | literal `8` in final/CLAIMS.md:27 |
| `8/8` | para 46 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | para 46 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | para 46 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `-0.03` | para 47 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | para 47 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | para 47 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.825` | para 48 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.738` | para 48 | yes | literal `0.738` in final/CLAIMS.md:11 |
| `0.912` | para 48 | yes | literal `0.912` in final/CLAIMS.md:11 |
| `+2.16` | para 49 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | para 49 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | para 49 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `3` | para 50 | yes | literal `3` in final/CLAIMS.md:9 |
| `5` | para 51 | yes | literal `5` in final/CLAIMS.md:27 |
| `1.27` | para 62 | yes | literal `1.27` in final/METHOD.md:9 |
| `.1` | para 62 | yes | literal `.1` in final/METHOD.md:9 |
| `222` | para 63 | yes | literal `222` in final/FINAL_REPORT.md:103 |
| `3.6` | para 65 | yes | structural: section number |
| `3.1` | para 67 | yes | `3.1` is 3.076 in final/tables/t1_frozen_per_seed.md:5 rounded to 1 dp |
| `3.2` | para 70 | yes | `3.2` is 3.177 in final/demo/decision_cards.txt:33 rounded to 1 dp |
| `3.3` | para 72 | yes | `3.3` is 3.291 in final/tables/t2_dev_vs_frozen_pooled.md:24 rounded to 1 dp |
| `30` | para 73 | yes | literal `30` in final/CLAIMS.md:57 |
| `3` | para 73 | yes | literal `3` in final/CLAIMS.md:9 |
| `600` | para 75 | yes | literal `600` in final/METHOD.md:21 |
| `60` | para 76 | yes | literal `60` in docs/freeze-2026-10-06.md:25 |
| `0.25` | para 77 | yes | literal `0.25` in final/CLAIMS.md:33 |
| `10` | para 79 | yes | literal `10` in final/CLAIMS.md:7 |
| `0.6` | para 80 | yes | literal `0.6` in docs/freeze-2026-10-06.md:21 |
| `900` | para 82 | yes | literal `900` in final/METHOD.md:12 |
| `0.7` | para 83 | yes | literal `0.7` in docs/freeze-2026-10-06.md:22 |
| `3.4` | para 84 | **NO** | - |
| `5,100` | para 85 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `900` | para 85 | yes | literal `900` in final/METHOD.md:12 |
| `755.3` | para 86 | yes | literal `755.3` in final/tables/t6_frozen_validation.md:9 |
| `5,400` | para 87 | yes | literal `5,400` in final/FINAL_REPORT.md:34 |
| `300` | para 87 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `6` | para 88 | yes | literal `6` in final/CLAIMS.md:27 |
| `1` | para 88 | yes | literal `1` in final/CLAIMS.md:9 |
| `3` | para 88 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | para 88 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | para 88 | yes | literal `6` in final/CLAIMS.md:27 |
| `6` | para 88 | yes | literal `6` in final/CLAIMS.md:27 |
| `1` | para 88 | yes | literal `1` in final/CLAIMS.md:9 |
| `3` | para 88 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | para 88 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | para 88 | yes | literal `6` in final/CLAIMS.md:27 |
| `6` | para 88 | yes | literal `6` in final/CLAIMS.md:27 |
| `95` | para 89 | yes | literal `95` in final/CLAIMS.md:3 |
| `3.5` | para 90 | yes | `3.5` is 3.521 in final/demo/decision_cards.txt:153 rounded to 1 dp |
| `2026` | para 91 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `10` | para 91 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `06` | para 91 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `8` | para 91 | yes | literal `8` in final/CLAIMS.md:27 |
| `4501` | para 91 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4508` | para 91 | yes | literal `4508` in final/CLAIMS.md:7 |
| `960/960` | para 92 | yes | literal `960/960` in final/CLAIMS.md:8 |
| `1` | para 96 | yes | literal `1` in final/CLAIMS.md:9 |
| `8` | para 96 | yes | literal `8` in final/CLAIMS.md:27 |
| `3` | para 98 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | para 98 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | para 98 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `+1.63` | para 98 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `0.32` | para 98 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `0.18` | para 98 | yes | literal `0.18` in final/CLAIMS.md:17 |
| `2` | para 100 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3.6` | para 101 | yes | `3.6` is 3.573 in final/tables/t4_missing_queue.md:8 rounded to 1 dp |
| `7` | para 102 | yes | literal `7` in final/CLAIMS.md:15 |
| `24` | para 102 | yes | literal `24` in final/CLAIMS.md:15 |
| `1` | para 102 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `161` | para 102 | yes | literal `161` in final/CLAIMS.md:15 |
| `194` | para 102 | yes | literal `194` in final/CLAIMS.md:15 |
| `0` | para 102 | yes | literal `0` in final/CLAIMS.md:14 |
| `26` | para 102 | yes | literal `26` in final/CLAIMS.md:15 |
| `43` | para 102 | yes | literal `43` in final/CLAIMS.md:15 |
| `4` | para 103 | yes | literal `4` in final/CLAIMS.md:9 |
| `720/720` | para 103 | yes | literal `720/720` in final/CLAIMS.md:21 |
| `3` | para 104 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.16` | para 104 | yes | literal `4.16` in final/CLAIMS.md:21 |
| `0.90` | para 104 | yes | literal `0.90` in final/CLAIMS.md:21 |
| `4` | para 104 | yes | literal `4` in final/CLAIMS.md:9 |
| `6.0` | para 105 | yes | literal `6.0` in final/CLAIMS.md:21 |
| `7.7` | para 105 | yes | literal `7.7` in final/CLAIMS.md:21 |
| `1.4` | para 105 | yes | literal `1.4` in final/CLAIMS.md:21 |
| `3.0` | para 105 | yes | literal `3.0` in final/CLAIMS.md:21 |
| `3` | para 110 | yes | literal `3` in final/CLAIMS.md:9 |
| `3` | para 110 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3.7` | para 111 | yes | `3.7` is 3.729 in final/demo/decision_cards.txt:107 rounded to 1 dp |
| `8` | para 112 | yes | literal `8` in final/CLAIMS.md:27 |
| `4` | para 116 | yes | literal `4` in final/CLAIMS.md:9 |
| `4503` | para 119 | yes | literal `4503` in final/CLAIMS.md:38 |
| `90` | para 119 | yes | literal `90` in final/CLAIMS.md:38 |
| `120` | para 119 | yes | literal `120` in final/CLAIMS.md:38 |
| `5,100` | para 119 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `1` | para 123 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | para 124 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | para 125 | yes | literal `3` in final/CLAIMS.md:9 |
| `1` | para 128 | yes | structural: references section |
| `1980` | para 128 | yes | structural: references section |
| `25` | para 128 | yes | structural: references section |
| `3` | para 128 | yes | structural: references section |
| `347` | para 128 | yes | structural: references section |
| `360` | para 128 | yes | structural: references section |
| `2` | para 129 | yes | structural: references section |
| `2005` | para 129 | yes | structural: references section |
| `39` | para 129 | yes | structural: references section |
| `141` | para 129 | yes | structural: references section |
| `167` | para 129 | yes | structural: references section |
| `3` | para 130 | yes | structural: references section |
| `2017/12/6398` | para 130 | yes | structural: references section |
| `4` | para 131 | yes | structural: references section |
| `2006` | para 131 | yes | structural: references section |
| `52` | para 131 | yes | structural: references section |
| `3` | para 131 | yes | structural: references section |
| `311` | para 131 | yes | structural: references section |
| `322` | para 131 | yes | structural: references section |
| `5` | para 132 | yes | structural: references section |
| `6` | para 133 | yes | structural: references section |
| `4` | para 133 | yes | structural: references section |
| `7` | para 134 | yes | structural: references section |
| `8` | para 135 | yes | structural: references section |
| `2015` | para 135 | yes | structural: references section |
| `15` | para 135 | yes | structural: references section |
| `186` | para 135 | yes | structural: references section |
| `20` | table 1 row 5 | yes | literal `20` in final/CLAIMS.md:23 |
| `10` | table 1 row 5 | yes | literal `10` in final/CLAIMS.md:7 |
| `3` | table 1 row 5 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | table 1 row 5 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | table 1 row 5 | yes | literal `6` in final/CLAIMS.md:27 |
| `2` | table 1 row 6 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `0` | table 3 row 2 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `1` | table 3 row 3 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `2` | table 3 row 4 | yes | identifier `A2` in final/METHOD.md:27 |
| `3` | table 3 row 5 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | table 3 row 6 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `30` | table 4 row 2 | yes | literal `30` in final/CLAIMS.md:57 |
| `0.85` | table 5 row 3 | yes | literal `0.85` in final/METHOD.md:11 |
| `1` | table 5 row 4 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `900` | table 5 row 4 | yes | literal `900` in final/METHOD.md:12 |
| `15` | table 5 row 4 | yes | literal `15` in final/CLAIMS.md:3 |
| `0.35` | table 5 row 5 | yes | literal `0.35` in final/METHOD.md:31 |
| `0.30` | table 5 row 5 | yes | literal `0.30` in final/METHOD.md:27 |
| `14/21` | table 5 row 6 | yes | fraction `14/21` in final/METHOD.md:13 |
| `5` | table 5 row 6 | yes | literal `5` in final/CLAIMS.md:27 |
| `4501` | table 6 row 1 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4508` | table 6 row 1 | yes | literal `4508` in final/CLAIMS.md:7 |
| `4201` | table 6 row 1 | yes | literal `4201` in final/CLAIMS.md:17 |
| `4208` | table 6 row 1 | yes | literal `4208` in final/CLAIMS.md:17 |
| `3` | table 6 row 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | table 6 row 2 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | table 6 row 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | table 6 row 2 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `7/8` | table 6 row 3 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `7/8` | table 6 row 3 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | table 6 row 4 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | table 6 row 4 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | table 6 row 4 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `+1.63` | table 6 row 4 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `1.04` | table 6 row 4 | yes | literal `1.04` in final/CLAIMS.md:17 |
| `2.22` | table 6 row 4 | yes | literal `2.22` in final/CLAIMS.md:17 |
| `-0.03` | table 6 row 5 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | table 6 row 5 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | table 6 row 5 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.03` | table 6 row 5 | yes | literal `0.03` in final/CLAIMS.md:17 |
| `-0.04` | table 6 row 5 | yes | literal `-0.04` in final/CLAIMS.md:17 |
| `0.10` | table 6 row 5 | yes | literal `0.10` in final/CLAIMS.md:17 |
| `0.825` | table 6 row 6 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.850` | table 6 row 6 | yes | literal `0.850` in final/CLAIMS.md:17 |
| `0.32` | table 6 row 7 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `0.13` | table 6 row 7 | yes | value 0.13 in docs/freeze-2026-10-06.md:8 |
| `0.50` | table 6 row 7 | yes | value 0.5 in final/tables/README.md:37 |
| `0.18` | table 6 row 7 | yes | literal `0.18` in final/CLAIMS.md:17 |
| `0.08` | table 6 row 7 | yes | literal `0.08` in final/CLAIMS.md:17 |
| `0.28` | table 6 row 7 | yes | literal `0.28` in final/CLAIMS.md:17 |
| `3` | table 6 row 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.07` | table 6 row 8 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | table 6 row 8 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `6.76` | table 6 row 8 | yes | `6.76` is 6.757 in final/FINAL_REPORT.md:30 rounded to 2 dp |
| `5.13` | table 6 row 8 | yes | `5.13` is 5.126 in final/FINAL_REPORT.md:30 rounded to 2 dp |
| `300` | table 6 row 9 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `-2.87` | table 6 row 9 | yes | value -2.870 in final/CLAIMS.md:14 |
| `-4.91` | table 6 row 9 | yes | `-4.91` is -4.914 in final/CLAIMS.md:14 rounded to 2 dp |
| `-0.83` | table 6 row 9 | yes | `-0.83` is -0.826 in final/CLAIMS.md:14 rounded to 2 dp |
| `-3.19` | table 6 row 9 | yes | literal `-3.19` in final/CLAIMS.md:17 |
| `-5.47` | table 6 row 9 | yes | `-5.47` is -5.474 in final/FINAL_REPORT.md:31 rounded to 2 dp |
| `-0.90` | table 6 row 9 | yes | `-0.90` is -0.899 in final/FINAL_REPORT.md:31 rounded to 2 dp |

## `submission\03_答辩PPT.pptx`

255 numeric tokens, 7 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `1` | slide 1 para 10 | yes | literal `1` in final/CLAIMS.md:9 |
| `20` | slide 1 notes para 1 | yes | literal `20` in final/CLAIMS.md:23 |
| `1` | slide 2 para 6 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | slide 2 para 10 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | slide 2 para 14 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | slide 2 para 18 | yes | literal `4` in final/CLAIMS.md:9 |
| `2` | slide 2 para 20 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `45` | slide 2 notes para 1 | **NO** | - |
| `1` | slide 3 para 7 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `900` | slide 3 para 7 | yes | literal `900` in final/METHOD.md:12 |
| `15` | slide 3 para 8 | yes | literal `15` in final/CLAIMS.md:3 |
| `0.35` | slide 3 para 9 | yes | literal `0.35` in final/METHOD.md:31 |
| `0.30` | slide 3 para 15 | yes | literal `0.30` in final/METHOD.md:27 |
| `14/21` | slide 3 para 19 | yes | fraction `14/21` in final/METHOD.md:13 |
| `30` | slide 3 para 20 | yes | literal `30` in final/CLAIMS.md:57 |
| `5` | slide 3 para 22 | yes | literal `5` in final/CLAIMS.md:27 |
| `3` | slide 3 para 25 | yes | literal `3` in final/CLAIMS.md:9 |
| `45` | slide 3 notes para 1 | **NO** | - |
| `20` | slide 4 para 6 | yes | literal `20` in final/CLAIMS.md:23 |
| `5` | slide 4 para 13 | yes | literal `5` in final/CLAIMS.md:27 |
| `4` | slide 4 para 23 | yes | literal `4` in final/CLAIMS.md:9 |
| `40` | slide 4 notes para 1 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `20` | slide 4 notes para 3 | yes | literal `20` in final/CLAIMS.md:23 |
| `1` | slide 5 para 3 | yes | literal `1` in final/CLAIMS.md:9 |
| `3` | slide 5 para 3 | yes | literal `3` in final/CLAIMS.md:9 |
| `2` | slide 5 para 3 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `2` | slide 5 para 6 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | slide 5 para 9 | yes | literal `3` in final/CLAIMS.md:9 |
| `20` | slide 5 para 9 | yes | literal `20` in final/CLAIMS.md:23 |
| `4` | slide 5 para 12 | yes | literal `4` in final/CLAIMS.md:9 |
| `5` | slide 5 para 15 | yes | literal `5` in final/CLAIMS.md:27 |
| `6` | slide 5 para 18 | yes | literal `6` in final/CLAIMS.md:27 |
| `7` | slide 5 para 21 | yes | literal `7` in final/CLAIMS.md:15 |
| `20` | slide 5 para 22 | yes | literal `20` in final/CLAIMS.md:23 |
| `10` | slide 5 para 24 | yes | literal `10` in final/CLAIMS.md:7 |
| `1/3` | slide 5 para 24 | yes | literal `1/3` in final/METHOD.md:20 |
| `4` | slide 5 para 25 | yes | literal `4` in final/CLAIMS.md:9 |
| `1/3` | slide 5 para 25 | yes | literal `1/3` in final/METHOD.md:20 |
| `6` | slide 5 para 26 | yes | literal `6` in final/CLAIMS.md:27 |
| `1/3` | slide 5 para 26 | yes | literal `1/3` in final/METHOD.md:20 |
| `1/3` | slide 5 para 27 | yes | literal `1/3` in final/METHOD.md:20 |
| `20` | slide 5 para 29 | yes | literal `20` in final/CLAIMS.md:23 |
| `5` | slide 5 para 31 | yes | literal `5` in final/CLAIMS.md:27 |
| `40` | slide 5 notes para 1 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `20` | slide 5 notes para 2 | yes | literal `20` in final/CLAIMS.md:23 |
| `13` | slide 6 para 3 | yes | literal `13` in final/CLAIMS.md:27 |
| `25` | slide 6 para 6 | yes | literal `25` in final/CLAIMS.md:27 |
| `0/6` | slide 6 para 9 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `6` | slide 6 para 10 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | slide 6 para 10 | yes | literal `0` in final/CLAIMS.md:14 |
| `3/3` | slide 6 para 11 | yes | literal `3/3` in final/CLAIMS.md:23 |
| `1/4` | slide 6 para 11 | yes | literal `1/4` in final/CLAIMS.md:23 |
| `5` | slide 6 para 12 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | slide 6 para 12 | yes | literal `8` in final/CLAIMS.md:27 |
| `0/13` | slide 6 para 13 | yes | literal `0/13` in final/CLAIMS.md:25 |
| `6/13` | slide 6 para 13 | yes | literal `6/13` in final/CLAIMS.md:25 |
| `6` | slide 6 para 14 | yes | literal `6` in final/CLAIMS.md:27 |
| `45` | slide 6 notes para 1 | **NO** | - |
| `6` | slide 6 notes para 2 | yes | literal `6` in final/CLAIMS.md:27 |
| `13` | slide 6 notes para 2 | yes | literal `13` in final/CLAIMS.md:27 |
| `25` | slide 6 notes para 2 | yes | literal `25` in final/CLAIMS.md:27 |
| `0/6` | slide 6 notes para 2 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `5` | slide 6 notes para 2 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | slide 6 notes para 2 | yes | literal `8` in final/CLAIMS.md:27 |
| `3/3` | slide 6 notes para 3 | yes | literal `3/3` in final/CLAIMS.md:23 |
| `1/4` | slide 6 notes para 3 | yes | literal `1/4` in final/CLAIMS.md:23 |
| `0/13` | slide 6 notes para 3 | yes | literal `0/13` in final/CLAIMS.md:25 |
| `6/13` | slide 6 notes para 3 | yes | literal `6/13` in final/CLAIMS.md:25 |
| `0` | slide 7 para 3 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `0.00` | slide 7 para 3 | yes | value 0 in final/CLAIMS.md:14 |
| `0.00` | slide 7 para 3 | yes | value 0 in final/CLAIMS.md:14 |
| `1` | slide 7 para 4 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `-0.09` | slide 7 para 4 | yes | `-0.09` is -0.093 in final/demo/decision_cards.txt:8 rounded to 2 dp |
| `0.11` | slide 7 para 4 | yes | `0.11` is 0.105 in final/demo/decision_cards.txt:8 rounded to 2 dp |
| `2` | slide 7 para 5 | yes | identifier `A2` in final/METHOD.md:27 |
| `4.74` | slide 7 para 5 | yes | `4.74` is 4.739 in final/tables/t4_missing_queue.md:5 rounded to 2 dp |
| `3.62` | slide 7 para 5 | yes | value 3.620 in final/demo/decision_cards.txt:9 |
| `3` | slide 7 para 6 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.53` | slide 7 para 6 | yes | `7.53` is 7.526 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4.45` | slide 7 para 6 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4` | slide 7 para 7 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `4.34` | slide 7 para 7 | yes | `4.34` is 4.343 in final/demo/decision_cards.txt:11 rounded to 2 dp |
| `4.64` | slide 7 para 7 | yes | `4.64` is 4.635 in final/tables/t2_dev_vs_frozen_pooled.md:9 rounded to 2 dp |
| `4501` | slide 7 para 8 | yes | literal `4501` in final/CLAIMS.md:7 |
| `3` | slide 7 para 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | slide 7 para 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | slide 7 para 8 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `4.64` | slide 7 para 8 | yes | `4.64` is 4.635 in final/tables/t2_dev_vs_frozen_pooled.md:9 rounded to 2 dp |
| `3` | slide 7 para 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.45` | slide 7 para 8 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `0` | slide 7 para 8 | yes | literal `0` in final/CLAIMS.md:14 |
| `3` | slide 7 para 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.53` | slide 7 para 8 | yes | `7.53` is 7.526 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4.45` | slide 7 para 8 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `3` | slide 7 para 10 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | slide 7 para 10 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4501` | slide 7 para 11 | yes | literal `4501` in final/CLAIMS.md:7 |
| `7.53` | slide 7 para 13 | yes | `7.53` is 7.526 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4.45` | slide 7 para 13 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `5,100` | slide 7 para 15 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `15` | slide 7 para 15 | yes | literal `15` in final/CLAIMS.md:3 |
| `7` | slide 7 para 16 | yes | literal `7` in final/CLAIMS.md:15 |
| `45` | slide 7 notes para 1 | **NO** | - |
| `5` | slide 7 notes para 2 | yes | literal `5` in final/CLAIMS.md:27 |
| `0` | slide 7 notes para 2 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `1` | slide 7 notes para 2 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `2` | slide 7 notes para 2 | yes | identifier `A2` in final/METHOD.md:27 |
| `3` | slide 7 notes para 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | slide 7 notes para 2 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `5,100` | slide 7 notes para 3 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `15` | slide 7 notes para 3 | yes | literal `15` in final/CLAIMS.md:3 |
| `4501` | slide 7 notes para 3 | yes | literal `4501` in final/CLAIMS.md:7 |
| `3` | slide 7 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | slide 7 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | slide 7 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.53` | slide 7 notes para 3 | yes | `7.53` is 7.526 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4.45` | slide 7 notes para 3 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4` | slide 7 notes para 3 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `4.64` | slide 7 notes para 3 | yes | `4.64` is 4.635 in final/tables/t2_dev_vs_frozen_pooled.md:9 rounded to 2 dp |
| `3` | slide 7 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0` | slide 7 notes para 3 | yes | literal `0` in final/CLAIMS.md:14 |
| `1` | slide 8 para 4 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | slide 8 para 9 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `5` | slide 8 para 10 | yes | literal `5` in final/CLAIMS.md:27 |
| `3` | slide 8 para 14 | yes | literal `3` in final/CLAIMS.md:9 |
| `1` | slide 8 para 17 | yes | identifier `R1` in final/demo/decision_cards.txt:14 |
| `2` | slide 8 para 17 | yes | identifier `R2` in final/demo/decision_cards.txt:4 |
| `2026` | slide 8 para 22 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `10` | slide 8 para 22 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `06` | slide 8 para 22 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `8` | slide 8 para 27 | yes | literal `8` in final/CLAIMS.md:27 |
| `35` | slide 8 notes para 1 | **NO** | - |
| `2026` | slide 8 notes para 3 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `10` | slide 8 notes para 3 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `06` | slide 8 notes para 3 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `8/8` | slide 9 para 3 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | slide 9 para 4 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | slide 9 para 6 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | slide 9 para 9 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `95` | slide 9 para 10 | yes | literal `95` in final/CLAIMS.md:3 |
| `1.74` | slide 9 para 10 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | slide 9 para 10 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `-0.03` | slide 9 para 12 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `0.825` | slide 9 para 15 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `1` | slide 9 para 17 | yes | literal `1` in final/CLAIMS.md:9 |
| `960/960` | slide 9 para 18 | yes | literal `960/960` in final/CLAIMS.md:8 |
| `9` | slide 9 para 19 | yes | literal `9` in final/tables/README.md:13 |
| `50` | slide 9 notes para 1 | yes | literal `50` in final/FINAL_REPORT.md:3 |
| `8` | slide 9 notes para 2 | yes | literal `8` in final/CLAIMS.md:27 |
| `960/960` | slide 9 notes para 2 | yes | literal `960/960` in final/CLAIMS.md:8 |
| `8/8` | slide 9 notes para 3 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | slide 9 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | slide 9 notes para 3 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `0.825` | slide 9 notes para 3 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.03` | slide 9 notes para 3 | yes | literal `0.03` in final/CLAIMS.md:17 |
| `2.16` | slide 9 notes para 4 | yes | literal `2.16` in final/CLAIMS.md:19 |
| `95` | slide 9 notes para 4 | yes | literal `95` in final/CLAIMS.md:3 |
| `1.74` | slide 9 notes para 4 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | slide 9 notes para 4 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `2` | slide 10 para 2 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | slide 10 para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | slide 10 para 3 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `3` | slide 10 para 4 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.07` | slide 10 para 4 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | slide 10 para 4 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `0.32` | slide 10 para 5 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `7.07` | slide 10 para 7 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | slide 10 para 7 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `3` | slide 10 para 8 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0.32` | slide 10 para 10 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `10` | slide 10 para 12 | yes | literal `10` in final/CLAIMS.md:7 |
| `40` | slide 10 notes para 1 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `3` | slide 10 notes para 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | slide 10 notes para 2 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `3` | slide 10 notes para 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.07` | slide 10 notes para 2 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | slide 10 notes para 2 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `0.32` | slide 10 notes para 3 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `3` | slide 11 para 2 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | slide 11 para 3 | yes | literal `4` in final/CLAIMS.md:9 |
| `3` | slide 11 para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7` | slide 11 para 4 | yes | literal `7` in final/CLAIMS.md:15 |
| `24` | slide 11 para 4 | yes | literal `24` in final/CLAIMS.md:15 |
| `0` | slide 11 para 4 | yes | literal `0` in final/CLAIMS.md:14 |
| `4` | slide 11 para 5 | yes | literal `4` in final/CLAIMS.md:9 |
| `3` | slide 11 para 5 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.16` | slide 11 para 5 | yes | literal `4.16` in final/CLAIMS.md:21 |
| `0.90` | slide 11 para 5 | yes | literal `0.90` in final/CLAIMS.md:21 |
| `300` | slide 11 para 6 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `3` | slide 11 para 6 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0.21` | slide 11 para 6 | yes | `0.21` is 0.212 in final/CLAIMS.md:14 rounded to 2 dp |
| `4.90` | slide 11 para 6 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `300` | slide 11 para 6 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `11` | slide 11 para 9 | yes | literal `11` in final/tables/t4_missing_queue.md:1 |
| `55` | slide 11 notes para 1 | yes | value 55.000 in final/tables/t4_missing_queue.md:5 |
| `7` | slide 11 notes para 2 | yes | literal `7` in final/CLAIMS.md:15 |
| `24` | slide 11 notes para 2 | yes | literal `24` in final/CLAIMS.md:15 |
| `161` | slide 11 notes para 2 | yes | literal `161` in final/CLAIMS.md:15 |
| `194` | slide 11 notes para 2 | yes | literal `194` in final/CLAIMS.md:15 |
| `0` | slide 11 notes para 2 | yes | literal `0` in final/CLAIMS.md:14 |
| `26` | slide 11 notes para 2 | yes | literal `26` in final/CLAIMS.md:15 |
| `43` | slide 11 notes para 2 | yes | literal `43` in final/CLAIMS.md:15 |
| `4` | slide 11 notes para 3 | yes | literal `4` in final/CLAIMS.md:9 |
| `3` | slide 11 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.16` | slide 11 notes para 3 | yes | literal `4.16` in final/CLAIMS.md:21 |
| `0.90` | slide 11 notes para 3 | yes | literal `0.90` in final/CLAIMS.md:21 |
| `4` | slide 11 notes para 3 | yes | literal `4` in final/CLAIMS.md:9 |
| `300` | slide 11 notes para 3 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `3` | slide 11 notes para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0.21` | slide 11 notes para 3 | yes | `0.21` is 0.212 in final/CLAIMS.md:14 rounded to 2 dp |
| `4.90` | slide 11 notes para 3 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `300` | slide 11 notes para 3 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `4201` | slide 12 para 2 | yes | literal `4201` in final/CLAIMS.md:17 |
| `4208` | slide 12 para 2 | yes | literal `4208` in final/CLAIMS.md:17 |
| `4501` | slide 12 para 2 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4508` | slide 12 para 2 | yes | literal `4508` in final/CLAIMS.md:7 |
| `3` | slide 12 para 3 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | slide 12 para 3 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `8/8` | slide 12 para 3 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `7/8` | slide 12 para 4 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `7/8` | slide 12 para 4 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+1.63` | slide 12 para 5 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `1.04` | slide 12 para 5 | yes | literal `1.04` in final/CLAIMS.md:17 |
| `2.22` | slide 12 para 5 | yes | literal `2.22` in final/CLAIMS.md:17 |
| `+2.16` | slide 12 para 5 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | slide 12 para 5 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | slide 12 para 5 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `0.03` | slide 12 para 6 | yes | literal `0.03` in final/CLAIMS.md:17 |
| `-0.04` | slide 12 para 6 | yes | literal `-0.04` in final/CLAIMS.md:17 |
| `0.10` | slide 12 para 6 | yes | literal `0.10` in final/CLAIMS.md:17 |
| `-0.03` | slide 12 para 6 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | slide 12 para 6 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | slide 12 para 6 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.850` | slide 12 para 7 | yes | literal `0.850` in final/CLAIMS.md:17 |
| `0.825` | slide 12 para 7 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.18` | slide 12 para 8 | yes | literal `0.18` in final/CLAIMS.md:17 |
| `0.08` | slide 12 para 8 | yes | literal `0.08` in final/CLAIMS.md:17 |
| `0.28` | slide 12 para 8 | yes | literal `0.28` in final/CLAIMS.md:17 |
| `0.32` | slide 12 para 8 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `0.13` | slide 12 para 8 | yes | value 0.13 in docs/freeze-2026-10-06.md:8 |
| `0.50` | slide 12 para 8 | yes | value 0.5 in final/tables/README.md:37 |
| `+2.16` | slide 12 para 10 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `+1.63` | slide 12 para 10 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `12` | slide 12 para 11 | yes | literal `12` in final/tables/t3_event_engine_coverage.md:14 |
| `35` | slide 12 notes para 1 | **NO** | - |
| `3` | slide 12 notes para 2 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | slide 12 notes para 2 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `2.16` | slide 12 notes para 2 | yes | literal `2.16` in final/CLAIMS.md:19 |
| `1.63` | slide 12 notes para 2 | yes | literal `1.63` in final/CLAIMS.md:17 |
| `8` | slide 13 para 5 | yes | literal `8` in final/CLAIMS.md:27 |
| `13` | slide 13 para 20 | yes | literal `13` in final/CLAIMS.md:27 |
| `50` | slide 13 notes para 1 | yes | literal `50` in final/FINAL_REPORT.md:3 |
| `8` | slide 13 notes para 3 | yes | literal `8` in final/CLAIMS.md:27 |
| `14` | slide 14 para 12 | yes | literal `14` in final/FINAL_REPORT.md:52 |
| `45` | slide 14 notes para 1 | **NO** | - |

## `submission\04_演讲稿.md`

112 numeric tokens, 7 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `10` | L3 | yes | literal `10` in final/CLAIMS.md:7 |
| `1` | L5 | yes | structural: 第N页/章 reference |
| `20` | L6 | yes | literal `20` in final/CLAIMS.md:23 |
| `2` | L9 | yes | structural: 第N页/章 reference |
| `45` | L10 | **NO** | - |
| `3` | L14 | yes | structural: 第N页/章 reference |
| `45` | L15 | **NO** | - |
| `4` | L20 | yes | structural: 第N页/章 reference |
| `40` | L21 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `20` | L23 | yes | literal `20` in final/CLAIMS.md:23 |
| `5` | L27 | yes | structural: 第N页/章 reference |
| `40` | L28 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `20` | L29 | yes | literal `20` in final/CLAIMS.md:23 |
| `6` | L31 | yes | structural: 第N页/章 reference |
| `45` | L32 | **NO** | - |
| `6` | L33 | yes | literal `6` in final/CLAIMS.md:27 |
| `13` | L33 | yes | literal `13` in final/CLAIMS.md:27 |
| `25` | L33 | yes | literal `25` in final/CLAIMS.md:27 |
| `0/6` | L33 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `5` | L33 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | L33 | yes | literal `8` in final/CLAIMS.md:27 |
| `3/3` | L34 | yes | literal `3/3` in final/CLAIMS.md:23 |
| `1/4` | L34 | yes | literal `1/4` in final/CLAIMS.md:23 |
| `0/13` | L34 | yes | literal `0/13` in final/CLAIMS.md:25 |
| `6/13` | L34 | yes | literal `6/13` in final/CLAIMS.md:25 |
| `7` | L37 | yes | structural: 第N页/章 reference |
| `45` | L38 | **NO** | - |
| `5` | L39 | yes | literal `5` in final/CLAIMS.md:27 |
| `0` | L39 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `1` | L39 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `2` | L39 | yes | identifier `A2` in final/METHOD.md:27 |
| `3` | L39 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | L39 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `5,100` | L40 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `15` | L40 | yes | literal `15` in final/CLAIMS.md:3 |
| `4501` | L40 | yes | literal `4501` in final/CLAIMS.md:7 |
| `3` | L40 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | L40 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | L40 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.53` | L40 | yes | `7.53` is 7.526 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4.45` | L40 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `4` | L40 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `4.64` | L40 | yes | `4.64` is 4.635 in final/tables/t2_dev_vs_frozen_pooled.md:9 rounded to 2 dp |
| `3` | L40 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0` | L40 | yes | literal `0` in final/CLAIMS.md:14 |
| `8` | L42 | yes | structural: 第N页/章 reference |
| `35` | L43 | **NO** | - |
| `2026` | L45 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `10` | L45 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `06` | L45 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `9` | L47 | yes | structural: 第N页/章 reference |
| `50` | L48 | yes | literal `50` in final/FINAL_REPORT.md:3 |
| `8` | L49 | yes | literal `8` in final/CLAIMS.md:27 |
| `960/960` | L49 | yes | literal `960/960` in final/CLAIMS.md:8 |
| `8/8` | L50 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | L50 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | L50 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `0.825` | L50 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.03` | L50 | yes | literal `0.03` in final/CLAIMS.md:17 |
| `2.16` | L51 | yes | literal `2.16` in final/CLAIMS.md:19 |
| `95` | L51 | yes | literal `95` in final/CLAIMS.md:3 |
| `1.74` | L51 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | L51 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `10` | L54 | yes | structural: 第N页/章 reference |
| `40` | L55 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `3` | L56 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | L56 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `3` | L56 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.07` | L56 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | L56 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `0.32` | L57 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `11` | L59 | yes | structural: 第N页/章 reference |
| `55` | L60 | yes | value 55.000 in final/tables/t4_missing_queue.md:5 |
| `7` | L61 | yes | literal `7` in final/CLAIMS.md:15 |
| `24` | L61 | yes | literal `24` in final/CLAIMS.md:15 |
| `161` | L61 | yes | literal `161` in final/CLAIMS.md:15 |
| `194` | L61 | yes | literal `194` in final/CLAIMS.md:15 |
| `0` | L61 | yes | literal `0` in final/CLAIMS.md:14 |
| `26` | L61 | yes | literal `26` in final/CLAIMS.md:15 |
| `43` | L61 | yes | literal `43` in final/CLAIMS.md:15 |
| `4` | L62 | yes | literal `4` in final/CLAIMS.md:9 |
| `3` | L62 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.16` | L62 | yes | literal `4.16` in final/CLAIMS.md:21 |
| `0.90` | L62 | yes | literal `0.90` in final/CLAIMS.md:21 |
| `4` | L62 | yes | literal `4` in final/CLAIMS.md:9 |
| `300` | L62 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `3` | L62 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `0.21` | L62 | yes | `0.21` is 0.212 in final/CLAIMS.md:14 rounded to 2 dp |
| `4.90` | L62 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `300` | L62 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `12` | L66 | yes | structural: 第N页/章 reference |
| `35` | L67 | **NO** | - |
| `3` | L68 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | L68 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `2.16` | L68 | yes | literal `2.16` in final/CLAIMS.md:19 |
| `1.63` | L68 | yes | literal `1.63` in final/CLAIMS.md:17 |
| `13` | L70 | yes | structural: 第N页/章 reference |
| `50` | L71 | yes | literal `50` in final/FINAL_REPORT.md:3 |
| `8` | L73 | yes | literal `8` in final/CLAIMS.md:27 |
| `14` | L78 | yes | structural: 第N页/章 reference |
| `45` | L79 | **NO** | - |
| `1` | L86 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | L89 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | L92 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | L95 | yes | literal `4` in final/CLAIMS.md:9 |
| `0.32` | L96 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `5` | L98 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | L98 | yes | literal `8` in final/CLAIMS.md:27 |
| `8` | L99 | yes | literal `8` in final/CLAIMS.md:27 |
| `6` | L101 | yes | literal `6` in final/CLAIMS.md:27 |
| `7` | L104 | yes | literal `7` in final/CLAIMS.md:15 |
| `8` | L107 | yes | literal `8` in final/CLAIMS.md:27 |

## `submission\video\captions.srt`

18 numeric tokens, 0 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `10` | L3 | yes | literal `10` in final/CLAIMS.md:7 |
| `20` | L13 | yes | literal `20` in final/CLAIMS.md:23 |
| `6` | L18 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | L18 | yes | literal `0` in final/CLAIMS.md:14 |
| `0` | L23 | yes | literal `0` in final/CLAIMS.md:14 |
| `4` | L23 | yes | literal `4` in final/CLAIMS.md:9 |
| `5` | L23 | yes | literal `5` in final/CLAIMS.md:27 |
| `4501` | L24 | yes | literal `4501` in final/CLAIMS.md:7 |
| `3` | L24 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4501` | L28 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4501` | L29 | yes | literal `4501` in final/CLAIMS.md:7 |
| `+3.08` | L29 | yes | `+3.08` is 3.076 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `0` | L29 | yes | literal `0` in final/CLAIMS.md:14 |
| `3` | L34 | yes | literal `3` in final/CLAIMS.md:9 |
| `8/8` | L34 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `7/8` | L34 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | L38 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `0.825` | L39 | yes | literal `0.825` in final/CLAIMS.md:11 |

## `submission\video\storyboard.md`

216 numeric tokens, 26 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `188` | L3 | **NO** | - |
| `3` | L3 | yes | literal `3` in final/CLAIMS.md:9 |
| `08` | L3 | yes | literal `08` in docs/blite-spec.md:59 |
| `3` | L3 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | L3 | yes | literal `4` in final/CLAIMS.md:9 |
| `1920` | L4 | **NO** | - |
| `1080` | L4 | **NO** | - |
| `1080` | L4 | **NO** | - |
| `16` | L4 | yes | literal `16` in final/FINAL_REPORT.md:83 |
| `9` | L4 | yes | literal `9` in final/tables/README.md:13 |
| `30` | L4 | yes | literal `30` in final/CLAIMS.md:57 |
| `.264` | L5 | **NO** | - |
| `4` | L5 | yes | literal `4` in the whitelist corpus |
| `22` | L6 | yes | literal `22` in final/tables/t5_replay_diagnosis.md:1 |
| `2` | L6 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `1` | L15 | yes | literal `1` in final/CLAIMS.md:9 |
| `00` | L15 | yes | literal `00` in docs/blite-spec.md:59 |
| `00` | L15 | yes | literal `00` in docs/blite-spec.md:59 |
| `00` | L15 | yes | literal `00` in docs/blite-spec.md:59 |
| `08` | L15 | yes | literal `08` in docs/blite-spec.md:59 |
| `8` | L15 | yes | literal `8` in final/CLAIMS.md:27 |
| `2` | L16 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `00` | L16 | yes | literal `00` in docs/blite-spec.md:59 |
| `08` | L16 | yes | literal `08` in docs/blite-spec.md:59 |
| `00` | L16 | yes | literal `00` in docs/blite-spec.md:59 |
| `48` | L16 | yes | literal `48` in final/FINAL_REPORT.md:54 |
| `40` | L16 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `4501` | L16 | yes | literal `4501` in final/CLAIMS.md:7 |
| `0` | L16 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `4` | L16 | yes | literal `4` in final/CLAIMS.md:9 |
| `4501` | L16 | yes | literal `4501` in final/CLAIMS.md:7 |
| `5100` | L16 | **NO** | - |
| `5700` | L16 | **NO** | - |
| `1` | L16 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `2` | L16 | yes | identifier `ktb_w2` in docs/blite-spec.md:12 |
| `3` | L16 | yes | identifier `ktb_w3` in final/tables/t3_event_engine_coverage.md:14 |
| `1` | L16 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `2` | L16 | yes | identifier `ktb_n2` in docs/freeze-2026-10-06.md:21 |
| `0.1` | L16 | yes | value 0.10 in final/CLAIMS.md:17 |
| `8` | L16 | yes | literal `8` in final/CLAIMS.md:27 |
| `8` | L16 | yes | literal `8` in final/CLAIMS.md:27 |
| `900.0` | L16 | **NO** | - |
| `755.3` | L16 | yes | literal `755.3` in the whitelist corpus |
| `5100` | L16 | **NO** | - |
| `21` | L16 | yes | literal `21` in final/METHOD.md:13 |
| `1` | L16 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `171` | L16 | **NO** | - |
| `0` | L16 | yes | literal `0` in final/CLAIMS.md:14 |
| `1` | L16 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `43` | L16 | yes | literal `43` in final/CLAIMS.md:15 |
| `5400` | L16 | yes | literal `5400` in final/FINAL_REPORT.md:34 |
| `10` | L16 | yes | literal `10` in final/CLAIMS.md:7 |
| `5` | L16 | yes | literal `5` in the whitelist corpus |
| `4501` | L16 | yes | identifier `seed_4501` in final/tables/t6_frozen_validation.md:12 |
| `5100` | L16 | **NO** | - |
| `4501` | L16 | yes | literal `4501` in the whitelist corpus |
| `4` | L16 | yes | literal `4` in the whitelist corpus |
| `4` | L16 | yes | literal `4` in final/CLAIMS.md:9 |
| `4501` | L16 | yes | identifier `seed_4501` in final/tables/t6_frozen_validation.md:12 |
| `5100` | L16 | **NO** | - |
| `4501` | L16 | yes | literal `4501` in final/CLAIMS.md:7 |
| `10` | L16 | yes | literal `10` in final/CLAIMS.md:7 |
| `3` | L17 | yes | literal `3` in final/CLAIMS.md:9 |
| `00` | L17 | yes | literal `00` in docs/blite-spec.md:59 |
| `48` | L17 | yes | literal `48` in final/FINAL_REPORT.md:54 |
| `01` | L17 | yes | value 1 in final/CLAIMS.md:8 |
| `23` | L17 | yes | literal `23` in final/tables/t6_frozen_validation.md:17 |
| `35` | L17 | **NO** | - |
| `4890.0` | L17 | **NO** | - |
| `4890.0` | L17 | **NO** | - |
| `20` | L17 | yes | literal `20` in final/CLAIMS.md:23 |
| `02111` | L17 | yes | literal `02111` in the whitelist corpus |
| `0.466` | L17 | **NO** | - |
| `4920.0` | L17 | **NO** | - |
| `4920.0` | L17 | **NO** | - |
| `4980.0` | L17 | **NO** | - |
| `1.3` | L17 | yes | literal `1.3` in the whitelist corpus |
| `0.322` | L17 | **NO** | - |
| `5040.0` | L17 | **NO** | - |
| `02109` | L17 | yes | literal `02109` in the whitelist corpus |
| `0.372` | L17 | **NO** | - |
| `5100.0` | L17 | **NO** | - |
| `6` | L17 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | L17 | yes | literal `0` in final/CLAIMS.md:14 |
| `20` | L17 | yes | literal `20` in final/CLAIMS.md:23 |
| `6` | L17 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | L17 | yes | literal `0` in final/CLAIMS.md:14 |
| `4401` | L17 | yes | literal `4401` in the whitelist corpus |
| `20` | L17 | yes | literal `20` in final/CLAIMS.md:23 |
| `4401` | L17 | yes | literal `4401` in the whitelist corpus |
| `1` | L17 | yes | literal `1` in the whitelist corpus |
| `4401` | L17 | yes | literal `4401` in the whitelist corpus |
| `1` | L17 | yes | literal `1` in the whitelist corpus |
| `6` | L17 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | L17 | yes | literal `0` in final/CLAIMS.md:14 |
| `4` | L18 | yes | literal `4` in final/CLAIMS.md:9 |
| `01` | L18 | yes | value 1 in final/CLAIMS.md:8 |
| `23` | L18 | yes | literal `23` in final/tables/t6_frozen_validation.md:17 |
| `02` | L18 | yes | value 2 in final/FINAL_REPORT.md:16 |
| `03` | L18 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `40` | L18 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `4501` | L18 | yes | literal `4501` in final/CLAIMS.md:7 |
| `0` | L18 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `4` | L18 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `0` | L18 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `1` | L18 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `2` | L18 | yes | identifier `A2` in final/METHOD.md:27 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | L18 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | L18 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `4.64` | L18 | yes | `4.64` is 4.635 in final/tables/t2_dev_vs_frozen_pooled.md:9 rounded to 2 dp |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.45` | L18 | yes | `4.45` is 4.451 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `0` | L18 | yes | literal `0` in final/CLAIMS.md:14 |
| `0` | L18 | yes | literal `0` in final/CLAIMS.md:14 |
| `4` | L18 | yes | literal `4` in final/CLAIMS.md:9 |
| `5` | L18 | yes | literal `5` in final/CLAIMS.md:27 |
| `4501` | L18 | yes | literal `4501` in final/CLAIMS.md:7 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4501` | L18 | yes | literal `4501` in final/CLAIMS.md:7 |
| `+3.08` | L18 | yes | `+3.08` is 3.076 in final/tables/t1_frozen_per_seed.md:5 rounded to 2 dp |
| `0` | L18 | yes | literal `0` in final/CLAIMS.md:14 |
| `0` | L18 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `0.000` | L18 | yes | literal `0.000` in final/tables/t1_frozen_per_seed.md:5 |
| `0.000` | L18 | yes | literal `0.000` in final/tables/t1_frozen_per_seed.md:5 |
| `1` | L18 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `-0.093` | L18 | yes | literal `-0.093` in final/demo/decision_cards.txt:8 |
| `+0.105` | L18 | yes | literal `+0.105` in final/demo/decision_cards.txt:8 |
| `2` | L18 | yes | identifier `A2` in final/METHOD.md:27 |
| `+4.738` | L18 | yes | literal `+4.738` in final/demo/decision_cards.txt:9 |
| `+3.620` | L18 | yes | literal `+3.620` in final/demo/decision_cards.txt:9 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `+7.526` | L18 | yes | literal `+7.526` in final/tables/t1_frozen_per_seed.md:5 |
| `+4.451` | L18 | yes | literal `+4.451` in final/tables/t1_frozen_per_seed.md:5 |
| `4` | L18 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `+4.343` | L18 | yes | literal `+4.343` in final/demo/decision_cards.txt:11 |
| `+4.644` | L18 | yes | literal `+4.644` in final/demo/decision_cards.txt:11 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3` | L18 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `+7.526` | L18 | yes | literal `+7.526` in final/tables/t1_frozen_per_seed.md:5 |
| `+4.451` | L18 | yes | literal `+4.451` in final/tables/t1_frozen_per_seed.md:5 |
| `4501` | L18 | yes | literal `4501` in final/CLAIMS.md:7 |
| `+3.076` | L18 | yes | literal `+3.076` in final/tables/t1_frozen_per_seed.md:5 |
| `4501` | L18 | yes | literal `4501` in final/CLAIMS.md:7 |
| `0.000` | L18 | yes | literal `0.000` in final/tables/t1_frozen_per_seed.md:5 |
| `5` | L19 | yes | literal `5` in final/CLAIMS.md:27 |
| `02` | L19 | yes | value 2 in final/FINAL_REPORT.md:16 |
| `03` | L19 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `02` | L19 | yes | value 2 in final/FINAL_REPORT.md:16 |
| `43` | L19 | yes | literal `43` in final/CLAIMS.md:15 |
| `40` | L19 | yes | value 40.000 in final/tables/t4_missing_queue.md:7 |
| `20` | L19 | yes | literal `20` in final/CLAIMS.md:23 |
| `1` | L19 | yes | literal `1` in final/CLAIMS.md:9 |
| `1` | L19 | yes | literal `1` in the whitelist corpus |
| `2` | L19 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | L19 | yes | literal `3` in the whitelist corpus |
| `1` | L19 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `4` | L19 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `20` | L19 | yes | literal `20` in final/CLAIMS.md:23 |
| `8` | L19 | yes | literal `8` in final/CLAIMS.md:27 |
| `3` | L19 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | L19 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `1` | L19 | yes | identifier `Top-1` in final/CLAIMS.md:9 |
| `7/8` | L19 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | L19 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | L19 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | L19 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `1.9` | L19 | yes | literal `1.9` in final/CLAIMS.md:10 |
| `-0.03` | L19 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | L19 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | L19 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.825` | L19 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.738` | L19 | yes | literal `0.738` in final/CLAIMS.md:11 |
| `0.912` | L19 | yes | literal `0.912` in final/CLAIMS.md:11 |
| `0.675` | L19 | yes | literal `0.675` in final/CLAIMS.md:11 |
| `3` | L19 | yes | literal `3` in final/CLAIMS.md:9 |
| `8/8` | L19 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `7/8` | L19 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `1` | L19 | yes | literal `1` in the whitelist corpus |
| `3` | L19 | yes | literal `3` in the whitelist corpus |
| `95` | L19 | yes | literal `95` in final/CLAIMS.md:3 |
| `6` | L20 | yes | literal `6` in final/CLAIMS.md:27 |
| `02` | L20 | yes | value 2 in final/FINAL_REPORT.md:16 |
| `43` | L20 | yes | literal `43` in final/CLAIMS.md:15 |
| `03` | L20 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `03` | L20 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `20` | L20 | yes | literal `20` in final/CLAIMS.md:23 |
| `4` | L20 | yes | literal `4` in final/CLAIMS.md:9 |
| `1` | L20 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | L20 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | L20 | yes | literal `3` in final/CLAIMS.md:9 |
| `6` | L20 | yes | literal `6` in final/CLAIMS.md:27 |
| `0` | L20 | yes | literal `0` in final/CLAIMS.md:14 |
| `4` | L20 | yes | literal `4` in final/CLAIMS.md:9 |
| `7` | L21 | yes | literal `7` in final/CLAIMS.md:15 |
| `03` | L21 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `03` | L21 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `03` | L21 | yes | literal `03` in docs/decision-2026-10-03b-synthetic.md:1 |
| `08` | L21 | yes | literal `08` in docs/blite-spec.md:59 |
| `5` | L21 | yes | literal `5` in final/CLAIMS.md:27 |
| `2` | L26 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `4501` | L26 | yes | literal `4501` in final/CLAIMS.md:7 |
| `5100` | L26 | **NO** | - |
| `5100` | L26 | **NO** | - |
| `5700` | L26 | **NO** | - |
| `10` | L26 | yes | literal `10` in final/CLAIMS.md:7 |
| `5` | L26 | yes | literal `5` in the whitelist corpus |
| `3` | L27 | yes | literal `3` in final/CLAIMS.md:9 |
| `4401` | L27 | yes | literal `4401` in the whitelist corpus |
| `4` | L28 | yes | literal `4` in final/CLAIMS.md:9 |
| `5` | L29 | yes | literal `5` in final/CLAIMS.md:27 |
| `1` | L29 | yes | literal `1` in the whitelist corpus |
| `3` | L29 | yes | literal `3` in the whitelist corpus |

## Summary

- files checked: 6
- numeric tokens: 839
- **not whitelisted: 44**

### Verdict

Checked on 2026-10-06 with
`python -B submission/tools/check_numbers.py submission/01_项目简表.docx submission/02_作品说明书.docx submission/03_答辩PPT.pptx submission/04_演讲稿.md submission/video/captions.srt submission/video/storyboard.md --out submission/checks/numbers_report.md`
(the deck `.pptx` is read as slide text **and** speaker notes, so the 04 script is checked both as
the source file and as the notes it becomes).

- **No non-whitelisted number is a claim about the project's results.** All 44 fall into four
  groups:
  - **14 个 45/35 计时标记（PPT 与演讲稿各 7 个）** — the `建议时长: 45秒` / `35秒` lines: 7 in
    `04_演讲稿.md` (L10, L15, L32, L38, L43, L67, L79) and the same 7 copied into the deck's speaker
    notes (slides 2, 3, 6, 7, 8, 12, 14). They are speaking-time aids, not claims.
  - **In-text citation years and one section number in `02_作品说明书.docx`** — `1980`, `2005`,
    `2006` are the years cited in 1.2 相关工作 (Willsky et al. 1980; Wang & Papageorgiou 2005;
    Smith & Winkler 2006), and `3.4` is the heading `### 3.4`. The whitelist's structural rule
    (section numbering, numbers inside a 参考文献 section) covers the bibliography itself but not an
    in-text citation, and the `.docx` reader cannot see the Markdown `#` that marks `3.4` as a
    heading — the same `3.4` is correctly read as a section number when `02_作品说明书.md` is
    checked directly (3 flagged there: the three citation years only). Tool limitation, not a
    content problem.
  - **Video metadata in `video/storyboard.md`** — `188` (total clip seconds), `1920`/`1080`
    (frame size), `.264` (the tokenizer splitting the codec name `H.264`) and `35` (the length of
    segment 3 in seconds).
  - **Simulation and event-log trace values in `video/storyboard.md`** — the simulation clock
    (`5100`, `5700`, `4890.0`, `4920.0`, `4980.0`, `5040.0`, `5100.0`), the incident location
    (`900.0` m), a corridor vehicle count read from the frozen snapshot (`171`) and three recorded
    hypothesis posteriors (`0.466`, `0.322`, `0.372`). They describe what the rendered video and
    log replay show, not what the audit claims.
- **Every headline claim matches `final/CLAIMS.md`.** `+2.16 [1.74, 2.59]`, `−0.03 [−0.11, 0.05]`,
  `0.825`, `8/8`, `7/8`, `960/960`, `0/6`, `13`, `25`, `0/13 → 6/13`, `4.16 → 0.90`,
  `7.53 / 4.45`, `7.07 / 4.90`, `0.32`, `0.18`, `+1.63` and the `45/35` timing markers are all
  whitelisted by the recorded sources; the docx, pptx, script, captions and storyboard agree with
  each other and with the frozen records.
- `video/captions.srt` is fully whitelisted (18 tokens, 0 flagged).

