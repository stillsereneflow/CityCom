# Missing-queue test: metrics and classification (plan rev 2)

Seeds: [4301, 4302, 4303, 4304]. Queue table: `D:\CityCom-astra\results\missing_queue\queue_td.parquet` (available: True). Gates passed: True.

## Per-seed primary and secondary quantities

| Seed | Arm | G_T(A3) R2 | e | a* | BEE signed | Regret | Top-1 | Spearman |
|---|---|---|---|---|---|---|---|---|
| 4301 | C-P | 7.158 | 2.033 | A3 | 2.033 | 0.000 | 1 | 0.800 |
| 4301 | C-D | 0.387 | 4.739 | A3 | -4.739 | 0.000 | 1 | -0.400 |
| 4301 | H-P | 7.363 | 2.237 | A3 | 2.237 | 0.000 | 1 | 0.600 |
| 4301 | H-D | 5.280 | 0.154 | A3 | 0.154 | 0.000 | 1 | 0.200 |
| 4302 | C-P | 7.881 | 3.425 | A3 | 3.425 | 0.065 | 0 | 0.600 |
| 4302 | C-D | 0.136 | 4.320 | A0 | 0.000 | 4.521 | 0 | -0.700 |
| 4302 | H-P | 6.190 | 1.734 | A3 | 1.734 | 0.065 | 0 | 0.600 |
| 4302 | H-D | 3.382 | 1.074 | A3 | -1.074 | 0.065 | 0 | -0.100 |
| 4303 | C-P | 6.196 | 2.010 | A3 | 2.010 | 0.873 | 0 | 0.700 |
| 4303 | C-D | 0.160 | 4.025 | A1 | 0.083 | 5.074 | 0 | -0.400 |
| 4303 | H-P | 6.220 | 2.034 | A3 | 2.034 | 0.873 | 0 | 0.600 |
| 4303 | H-D | 3.221 | 0.965 | A3 | -0.965 | 0.873 | 0 | -0.100 |
| 4304 | C-P | 8.250 | 3.896 | A3 | 3.896 | 0.000 | 1 | 0.900 |
| 4304 | C-D | 0.781 | 3.573 | A3 | -3.573 | 0.000 | 1 | 0.000 |
| 4304 | H-P | 7.118 | 2.765 | A3 | 2.765 | 0.000 | 1 | 1.000 |
| 4304 | H-D | 5.757 | 1.403 | A3 | 1.403 | 0.000 | 1 | 0.800 |

| Seed | G_P(A3) M2 | Delta_D = e(H-D) - e(C-D) | Duration contrast C | Duration contrast H |
|---|---|---|---|---|
| 4301 | 5.126 | -4.584 | 6.771 | 2.083 |
| 4302 | 4.456 | -3.246 | 7.745 | 2.808 |
| 4303 | 4.186 | -3.060 | 6.035 | 2.999 |
| 4304 | 4.353 | -2.169 | 7.469 | 1.362 |

## Queue inputs (queue_td.parquet)

| Seed | Q_proxy | Q_C | Q_H | Q_live | Q_P - Q_C | Q_H - Q_C |
|---|---|---|---|---|---|---|
| 4301 | 55.0 | 0.0 | 14.0 | 0.0 | 55.0 | 14.0 |
| 4302 | 7.0 | 0.0 | 15.0 | 0.0 | 7.0 | 15.0 |
| 4303 | 40.0 | 0.0 | 17.0 | 0.0 | 40.0 | 17.0 |
| 4304 | 25.0 | 0.0 | 19.0 | 0.0 | 25.0 | 19.0 |

## Classification (preregistered order; inputs printed at every step)

1. Inconclusive (technical): gates_ok=True, incomplete seed-arms=[], seeds missing queue=[], seeds missing Delta_D=[] -> applies=False
2. No initial deficit: Q_P - Q_C <= 5: n_required=3 -> applies=False
   inputs: {"applies": false, "n_no_deficit": 0, "n_required": 3, "per_seed": {"4301": {"Q_C": 0.0, "Q_P": 55.0, "diff": 55.0, "no_deficit": false}, "4302": {"Q_C": 0.0, "Q_P": 7.0, "diff": 7.0, "no_deficit": false}, "4303": {"Q_C": 0.0, "Q_P": 40.0, "diff": 40.0, "no_deficit": false}, "4304": {"Q_C": 0.0, "Q_P": 25.0, "diff": 25.0, "no_deficit": false}}}
3. Inconclusive (restoration): Q_H - Q_C >= 6 on seeds with a deficit: n_required=3 -> applies=False
   inputs: {"applies": false, "n_required": 3, "n_restored": 4, "per_seed": {"4301": {"Q_C": 0.0, "Q_H": 14.0, "diff": 14.0, "proxy_deficit": true, "restored": true}, "4302": {"Q_C": 0.0, "Q_H": 15.0, "diff": 15.0, "proxy_deficit": true, "restored": true}, "4303": {"Q_C": 0.0, "Q_H": 17.0, "diff": 17.0, "proxy_deficit": true, "restored": true}, "4304": {"Q_C": 0.0, "Q_H": 19.0, "diff": 19.0, "proxy_deficit": true, "restored": true}}}
4. Support: Delta_D < 0 and mean Delta_D <= -1: n_required=3 -> applies=True
   inputs: {"applies": true, "mean_delta_D": -3.2650462962962976, "n_negative": 4, "n_required": 3, "per_seed_delta_D": {"4301": -4.584351851851849, "4302": -3.2460185185185253, "4303": -3.0603703703703644, "4304": -2.1694444444444514}}

**Label: Support** (first applicable step: 4)

## Completeness and failures

Complete 5 x 6 Twin grid per seed-arm: True
- no branch failures
