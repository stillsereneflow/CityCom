Sources: Q_P/Q_C/Q_H read from `results/missing_queue/queue_td.parquet` at t_d (worlds proxy/C/H, column Q) and cross-checked against `results/missing_queue/metrics.json` `queue[]`; e(C-D), e(H-D), delta_D and the duration contrasts from `results/missing_queue/metrics.json` `plan[]`; the classification label from `results/missing_queue/metrics.json` `classification` (rule order in `docs/oct11-missing-queue-plan.md`). N = 4 seeds (4301-4304) + 1 classification row.

| seed | Q_P (proxy) | Q_C (conventional) | Q_H (historical) | e(C-D) | e(H-D) | delta_D = e(H-D) - e(C-D) | duration contrast C (G_T(A3;-P) - G_T(A3;-D)) | duration contrast H (G_T(A3;-P) - G_T(A3;-D)) | classification |
|---|---|---|---|---|---|---|---|---|---|
| 4301 | 55.000 | 0.000 | 14.000 | 4.739 | 0.154 | -4.584 | 6.771 | 2.083 | study-level (see last row) |
| 4302 | 7.000 | 0.000 | 15.000 | 4.320 | 1.074 | -3.246 | 7.745 | 2.808 | study-level (see last row) |
| 4303 | 40.000 | 0.000 | 17.000 | 4.025 | 0.965 | -3.060 | 6.035 | 2.999 | study-level (see last row) |
| 4304 | 25.000 | 0.000 | 19.000 | 3.573 | 1.403 | -2.169 | 7.469 | 1.362 | study-level (see last row) |
| classification (all seeds) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | support (step 4 of the ordered rule): delta_D < 0 on 4/4 seeds, mean delta_D = -3.265 <= -1.0 veh.h |
