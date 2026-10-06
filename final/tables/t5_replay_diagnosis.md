Source: `results/replay_diag/raw.parquet` recomputed with beta = 0.25 (posterior proportional to prior x exp(0.25 x logL), normalised over the hypotheses present in each variant/evaluation) by `final/tables/build_tables.py`; would-adopt = MAP in the incident family and gap = log P(best incident) - log max P(demand) > ln 10, as in `docs/oct10-replay-diagnosis-plan.md`; the variant labels are that plan's table. Agreement with the stored columns: max |post - stored post| = 1.67e-15, max |gap - stored gap| = 3.55e-15, would-adopt differences = 0. N = 8 variants x 22 evaluations (13 INC, 9 NOI synthetic).

| variant | label (oct10 plan) | would-adopt INC (of 13) | would-adopt NOI (of 9) | INC-only median gap (log posterior) | INC MAP family (count) |
|---|---|---|---|---|---|
| V0 | base | 0/13 | 0/9 | -2.052 | incident 0/13; demand 6/13; fault 7/13 |
| VP | representation diagnostic | 0/13 | 0/9 | 0.368 | incident 4/13; demand 2/13; fault 7/13 |
| VT | truth-assisted control (onset) | 1/13 | 0/9 | -0.126 | incident 3/13; demand 4/13; fault 6/13 |
| VPT | truth-assisted control | 6/13 | 0/9 | 2.042 | incident 11/13; demand 2/13; fault 0/13 |
| VPL | truth-assisted control (location) | 3/13 | 0/9 | 0.031 | incident 7/13; demand 4/13; fault 2/13 |
| VPTL | truth-assisted control | 5/13 | 0/9 | 1.705 | incident 10/13; demand 2/13; fault 1/13 |
| VNF | competition diagnostic | 0/13 | 0/9 | -2.052 | incident 1/13; demand 12/13; fault 0/13 |
| VPTLNF | truth-assisted control | 5/13 | 0/9 | 1.705 | incident 10/13; demand 3/13; fault 0/13 |
