# Number whitelist check

- whitelist: 581 distinct values, 650 literals, 1651 identifiers from `final/CLAIMS.md`, `final/FINAL_REPORT.md`, `final/METHOD.md`, `final/tables/*.md`, `final/demo/decision_cards.txt`, `docs/freeze-2026-10-06.md`, `docs/decision-2026-10-03b-synthetic.md`, `docs/blite-spec.md`, `submission/tools/allowed_extra.txt`.

## `submission\02_作品说明书.md`

209 numeric tokens, 3 not whitelisted.

| Number | Where | Whitelisted | Matching source |
| --- | --- | --- | --- |
| `1.1` | L11 | yes | structural: section number |
| `1.2` | L23 | yes | structural: section number |
| `1980` | L25 | **NO** | - |
| `2005` | L26 | **NO** | - |
| `2006` | L28 | **NO** | - |
| `1.3` | L36 | yes | structural: section number |
| `30` | L39 | yes | literal `30` in final/CLAIMS.md:57 |
| `1` | L51 | yes | literal `1` in final/CLAIMS.md:9 |
| `20` | L60 | yes | literal `20` in final/CLAIMS.md:23 |
| `10` | L60 | yes | literal `10` in final/CLAIMS.md:7 |
| `3` | L60 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | L60 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | L60 | yes | literal `6` in final/CLAIMS.md:27 |
| `2` | L61 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3/3` | L66 | yes | literal `3/3` in final/CLAIMS.md:23 |
| `4` | L66 | yes | literal `4` in final/CLAIMS.md:9 |
| `1` | L66 | yes | literal `1` in final/CLAIMS.md:9 |
| `6` | L67 | yes | literal `6` in final/CLAIMS.md:27 |
| `13` | L67 | yes | literal `13` in final/CLAIMS.md:27 |
| `25` | L67 | yes | literal `25` in final/CLAIMS.md:27 |
| `0/6` | L67 | yes | literal `0/6` in final/CLAIMS.md:27 |
| `5` | L67 | yes | literal `5` in final/CLAIMS.md:27 |
| `8` | L67 | yes | literal `8` in final/CLAIMS.md:27 |
| `0/13` | L68 | yes | literal `0/13` in final/CLAIMS.md:25 |
| `6/13` | L68 | yes | literal `6/13` in final/CLAIMS.md:25 |
| `9` | L68 | yes | literal `9` in final/tables/README.md:13 |
| `1` | L70 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | L72 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `5` | L74 | yes | literal `5` in final/CLAIMS.md:27 |
| `15` | L74 | yes | literal `15` in final/CLAIMS.md:3 |
| `0` | L78 | yes | identifier `A0` in final/CLAIMS.md:14 |
| `1` | L79 | yes | identifier `A1` in final/CLAIMS.md:14 |
| `2` | L80 | yes | identifier `A2` in final/METHOD.md:27 |
| `3` | L81 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4` | L82 | yes | identifier `A4` in final/CLAIMS.md:9 |
| `8` | L86 | yes | literal `8` in final/CLAIMS.md:27 |
| `8/8` | L87 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | L87 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | L87 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `-0.03` | L88 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | L88 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | L88 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.825` | L89 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.738` | L89 | yes | literal `0.738` in final/CLAIMS.md:11 |
| `0.912` | L89 | yes | literal `0.912` in final/CLAIMS.md:11 |
| `+2.16` | L90 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | L90 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | L90 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `3` | L92 | yes | literal `3` in final/CLAIMS.md:9 |
| `5` | L94 | yes | literal `5` in final/CLAIMS.md:27 |
| `1.27` | L109 | yes | literal `1.27` in final/METHOD.md:9 |
| `.1` | L109 | yes | literal `.1` in final/METHOD.md:9 |
| `222` | L110 | yes | literal `222` in final/FINAL_REPORT.md:103 |
| `3.6` | L112 | yes | structural: section number |
| `3.1` | L118 | yes | structural: section number |
| `30` | L124 | yes | literal `30` in final/CLAIMS.md:57 |
| `3.2` | L128 | yes | structural: section number |
| `0.85` | L133 | yes | literal `0.85` in final/METHOD.md:11 |
| `1` | L134 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `900` | L134 | yes | literal `900` in final/METHOD.md:12 |
| `15` | L134 | yes | literal `15` in final/CLAIMS.md:3 |
| `0.35` | L135 | yes | literal `0.35` in final/METHOD.md:31 |
| `0.30` | L135 | yes | literal `0.30` in final/METHOD.md:27 |
| `14/21` | L136 | yes | fraction `14/21` in final/METHOD.md:13 |
| `5` | L136 | yes | literal `5` in final/CLAIMS.md:27 |
| `3.3` | L138 | yes | structural: section number |
| `30` | L140 | yes | literal `30` in final/CLAIMS.md:57 |
| `3` | L140 | yes | literal `3` in final/CLAIMS.md:9 |
| `600` | L143 | yes | literal `600` in final/METHOD.md:21 |
| `60` | L144 | yes | literal `60` in docs/freeze-2026-10-06.md:25 |
| `0.25` | L145 | yes | literal `0.25` in final/CLAIMS.md:33 |
| `10` | L148 | yes | literal `10` in final/CLAIMS.md:7 |
| `0.6` | L149 | yes | literal `0.6` in docs/freeze-2026-10-06.md:21 |
| `900` | L151 | yes | literal `900` in final/METHOD.md:12 |
| `0.7` | L152 | yes | literal `0.7` in docs/freeze-2026-10-06.md:22 |
| `3.4` | L154 | yes | structural: section number |
| `5,100` | L156 | yes | literal `5,100` in final/CLAIMS.md:38 |
| `900` | L156 | yes | literal `900` in final/METHOD.md:12 |
| `755.3` | L157 | yes | literal `755.3` in final/tables/t6_frozen_validation.md:9 |
| `5,400` | L158 | yes | literal `5,400` in final/FINAL_REPORT.md:34 |
| `300` | L158 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `6` | L159 | yes | literal `6` in final/CLAIMS.md:27 |
| `1` | L159 | yes | literal `1` in final/CLAIMS.md:9 |
| `3` | L159 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | L159 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | L159 | yes | literal `6` in final/CLAIMS.md:27 |
| `6` | L159 | yes | literal `6` in final/CLAIMS.md:27 |
| `1` | L159 | yes | literal `1` in final/CLAIMS.md:9 |
| `3` | L159 | yes | literal `3` in final/CLAIMS.md:9 |
| `4` | L159 | yes | literal `4` in final/CLAIMS.md:9 |
| `6` | L159 | yes | literal `6` in final/CLAIMS.md:27 |
| `6` | L159 | yes | literal `6` in final/CLAIMS.md:27 |
| `95` | L160 | yes | literal `95` in final/CLAIMS.md:3 |
| `3.5` | L162 | yes | structural: section number |
| `2026` | L164 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `10` | L164 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `06` | L164 | yes | identifier `2026-10-06` in final/CLAIMS.md:7 |
| `8` | L164 | yes | literal `8` in final/CLAIMS.md:27 |
| `4501` | L164 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4508` | L164 | yes | literal `4508` in final/CLAIMS.md:7 |
| `960/960` | L165 | yes | literal `960/960` in final/CLAIMS.md:8 |
| `1` | L169 | yes | literal `1` in the whitelist corpus |
| `1` | L171 | yes | literal `1` in final/CLAIMS.md:9 |
| `8` | L171 | yes | literal `8` in final/CLAIMS.md:27 |
| `4501` | L173 | yes | literal `4501` in final/CLAIMS.md:7 |
| `4508` | L173 | yes | literal `4508` in final/CLAIMS.md:7 |
| `4201` | L173 | yes | literal `4201` in final/CLAIMS.md:17 |
| `4208` | L173 | yes | literal `4208` in final/CLAIMS.md:17 |
| `3` | L175 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | L175 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `3` | L175 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `8/8` | L175 | yes | literal `8/8` in final/CLAIMS.md:9 |
| `7/8` | L176 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `7/8` | L176 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | L177 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `1.74` | L177 | yes | literal `1.74` in final/CLAIMS.md:64 |
| `2.59` | L177 | yes | literal `2.59` in final/CLAIMS.md:64 |
| `+1.63` | L177 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `1.04` | L177 | yes | literal `1.04` in final/CLAIMS.md:17 |
| `2.22` | L177 | yes | literal `2.22` in final/CLAIMS.md:17 |
| `-0.03` | L178 | yes | literal `-0.03` in final/CLAIMS.md:64 |
| `-0.11` | L178 | yes | literal `-0.11` in final/CLAIMS.md:64 |
| `0.05` | L178 | yes | literal `0.05` in final/CLAIMS.md:64 |
| `0.03` | L178 | yes | literal `0.03` in final/CLAIMS.md:17 |
| `-0.04` | L178 | yes | literal `-0.04` in final/CLAIMS.md:17 |
| `0.10` | L178 | yes | literal `0.10` in final/CLAIMS.md:17 |
| `0.825` | L179 | yes | literal `0.825` in final/CLAIMS.md:11 |
| `0.850` | L179 | yes | literal `0.850` in final/CLAIMS.md:17 |
| `0.32` | L180 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `0.13` | L180 | yes | value 0.13 in docs/freeze-2026-10-06.md:8 |
| `0.50` | L180 | yes | value 0.5 in final/tables/README.md:37 |
| `0.18` | L180 | yes | literal `0.18` in final/CLAIMS.md:17 |
| `0.08` | L180 | yes | literal `0.08` in final/CLAIMS.md:17 |
| `0.28` | L180 | yes | literal `0.28` in final/CLAIMS.md:17 |
| `3` | L181 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7.07` | L181 | yes | `7.07` is 7.066 in final/CLAIMS.md:13 rounded to 2 dp |
| `4.90` | L181 | yes | `4.90` is 4.904 in final/CLAIMS.md:13 rounded to 2 dp |
| `6.76` | L181 | yes | `6.76` is 6.757 in final/FINAL_REPORT.md:30 rounded to 2 dp |
| `5.13` | L181 | yes | `5.13` is 5.126 in final/FINAL_REPORT.md:30 rounded to 2 dp |
| `300` | L182 | yes | identifier `D300` in final/CLAIMS.md:14 |
| `-2.87` | L182 | yes | value -2.870 in final/CLAIMS.md:14 |
| `-4.91` | L182 | yes | `-4.91` is -4.914 in final/CLAIMS.md:14 rounded to 2 dp |
| `-0.83` | L182 | yes | `-0.83` is -0.826 in final/CLAIMS.md:14 rounded to 2 dp |
| `-3.19` | L182 | yes | literal `-3.19` in final/CLAIMS.md:17 |
| `-5.47` | L182 | yes | `-5.47` is -5.474 in final/FINAL_REPORT.md:31 rounded to 2 dp |
| `-0.90` | L182 | yes | `-0.90` is -0.899 in final/FINAL_REPORT.md:31 rounded to 2 dp |
| `3` | L184 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `7/8` | L184 | yes | literal `7/8` in final/CLAIMS.md:9 |
| `+2.16` | L184 | yes | literal `+2.16` in final/CLAIMS.md:19 |
| `+1.63` | L184 | yes | literal `+1.63` in final/CLAIMS.md:17 |
| `0.32` | L184 | yes | literal `0.32` in final/CLAIMS.md:19 |
| `0.18` | L184 | yes | literal `0.18` in final/CLAIMS.md:17 |
| `3` | L186 | yes | literal `3` in the whitelist corpus |
| `2` | L188 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3.6` | L190 | yes | structural: section number |
| `7` | L192 | yes | literal `7` in final/CLAIMS.md:15 |
| `24` | L192 | yes | literal `24` in final/CLAIMS.md:15 |
| `1` | L192 | yes | identifier `ktb_n1` in final/CLAIMS.md:15 |
| `161` | L192 | yes | literal `161` in final/CLAIMS.md:15 |
| `194` | L192 | yes | literal `194` in final/CLAIMS.md:15 |
| `0` | L192 | yes | literal `0` in final/CLAIMS.md:14 |
| `26` | L192 | yes | literal `26` in final/CLAIMS.md:15 |
| `43` | L192 | yes | literal `43` in final/CLAIMS.md:15 |
| `4` | L194 | yes | literal `4` in final/CLAIMS.md:9 |
| `720/720` | L194 | yes | literal `720/720` in final/CLAIMS.md:21 |
| `3` | L195 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `4.16` | L195 | yes | literal `4.16` in final/CLAIMS.md:21 |
| `0.90` | L195 | yes | literal `0.90` in final/CLAIMS.md:21 |
| `4` | L195 | yes | literal `4` in final/CLAIMS.md:9 |
| `6.0` | L196 | yes | literal `6.0` in final/CLAIMS.md:21 |
| `7.7` | L196 | yes | literal `7.7` in final/CLAIMS.md:21 |
| `1.4` | L196 | yes | literal `1.4` in final/CLAIMS.md:21 |
| `3.0` | L196 | yes | literal `3.0` in final/CLAIMS.md:21 |
| `4` | L202 | yes | literal `4` in the whitelist corpus |
| `3` | L204 | yes | literal `3` in final/CLAIMS.md:9 |
| `3` | L204 | yes | identifier `A3` in final/CLAIMS.md:9 |
| `3.7` | L206 | yes | structural: section number |
| `8` | L208 | yes | literal `8` in final/CLAIMS.md:27 |
| `4` | L212 | yes | literal `4` in final/CLAIMS.md:9 |
| `1` | L223 | yes | literal `1` in final/CLAIMS.md:9 |
| `2` | L224 | yes | literal `2` in final/FINAL_REPORT.md:16 |
| `3` | L225 | yes | literal `3` in final/CLAIMS.md:9 |
| `1` | L233 | yes | structural: references section |
| `1980` | L233 | yes | structural: references section |
| `25` | L233 | yes | structural: references section |
| `3` | L233 | yes | structural: references section |
| `347` | L233 | yes | structural: references section |
| `360` | L233 | yes | structural: references section |
| `2` | L234 | yes | structural: references section |
| `2005` | L234 | yes | structural: references section |
| `39` | L234 | yes | structural: references section |
| `141` | L234 | yes | structural: references section |
| `167` | L234 | yes | structural: references section |
| `3` | L235 | yes | structural: references section |
| `2017/12/6398` | L235 | yes | structural: references section |
| `4` | L236 | yes | structural: references section |
| `2006` | L236 | yes | structural: references section |
| `52` | L236 | yes | structural: references section |
| `3` | L236 | yes | structural: references section |
| `311` | L236 | yes | structural: references section |
| `322` | L236 | yes | structural: references section |
| `5` | L237 | yes | structural: references section |
| `6` | L238 | yes | structural: references section |
| `4` | L238 | yes | structural: references section |
| `7` | L239 | yes | structural: references section |
| `8` | L240 | yes | structural: references section |
| `2015` | L240 | yes | structural: references section |
| `15` | L240 | yes | structural: references section |
| `186` | L240 | yes | structural: references section |

## Summary

- files checked: 1
- numeric tokens: 209
- **not whitelisted: 3**
