# Development-runs outcomes (docs/oct13-dev-runs-plan.md revision 2, outcomes 1-9)

Runs analysed: 2. Descriptive counts and means only: no inference, no acceptance criteria, no tuning. Every rate carries its denominator.

## Accounting

| slot | status | attempt | run_dir | in_statistics | note |
|---|---|---|---|---|---|
| conv_noi_4401 | complete | 1 | results\dev_runs\smoke\conv_noi_4401\attempt_1 | yes |  |
| evt_noi_4401 | complete | 1 | results\dev_runs\smoke\evt_noi_4401\attempt_1 | yes |  |


## Outcome 1: exposure

| run | scenario | arm | seed | alarm_events | alarm_ticks | min_SUSPECTED | min_DEGRADED | min_EVENT | min_RECOVERY | lib_attempted | lib_successful | lib_failed | clr_attempted | clr_successful | clr_failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| conv_noi_4401 | NOI | conv | 4401 | n/a | n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 |
| evt_noi_4401 | NOI | evt | 4401 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


Pooled per scenario (EVT runs):

| scenario | n_runs | n_evt_runs | alarm_events | min_SUSPECTED | min_DEGRADED | min_EVENT | min_RECOVERY | lib_a/s/f | clr_a/s/f |
|---|---|---|---|---|---|---|---|---|---|
| NOI | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0/0/0 | 0/0/0 |


## Outcome 2: natural adoption (INC, EVT)

| run | successful_library_evals | natural_adoptions | rate | any | first_t | timing_class | delay_s | delay_censored_at | forced_adoptions |
|---|---|---|---|---|---|---|---|---|---|


Pooled INC: None/None runs with an adoption; None right-censored at 2700 s. Adoptions None / None successful library evaluations = n/a. Timing classes: None. From forced runs: None.


Identification over all natural INC adoptions:

| run | t | h_star | edge | k | s | gap_vs_demand | gap_gt_ln10 | location_correct | exact_ks | timing_class | forced |
|---|---|---|---|---|---|---|---|---|---|---|---|


Location correct (edge ktb_n1): None/None. Exact (k, s) = (2, 1.0): None/None. (k, s) values: None.


## Outcome 3: false adoption (NOI / SHK / DET, EVT)

| run | scenario | successful_library_evals | adoptions | rate |
|---|---|---|---|---|
| evt_noi_4401 | NOI | 0 | 0 | n/a |


NOI: 0 adoptions / 0 successful library evaluations = n/a; 0/1 runs with an adoption.


SHK: no runs analysed.


DET: no runs analysed.


## Outcome 4: non-incident handling, per successful library evaluation

| run | scenario | t | h_star | family | map_is_demand | false_alarm_path | m_written | returned_to_normal | detector | fault_type | map_is_aid02109 | map_is_stuck | fault_path |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|


SHK: no runs analysed.


DET: no runs analysed.


## Outcome 5: clearance per adoption episode

| run | scenario | seed | episode_start | t_adopt | h_star | timing_class | forced_adoption | run_forced | n_clearance_records | t_dec | tau_c | t_clr | p_clear | outcome | labels_apply | premature_inference | premature_live_release | late |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|


Every executed clearance record (t_dec, tau_c, t_clr, p_clear) is in outcomes.json under `clearance_records`; the episode row uses the deciding record.


## Outcome 6: recovery spells

| run | scenario | enter | exit | duration_s | spell_class | exit_reason |
|---|---|---|---|---|---|---|


## Outcome 7: DEGRADED spells (live)

| run | scenario | enter | exit | duration_s | spell_class | exit_at_entry_plus_900 | exit_reason |
|---|---|---|---|---|---|---|---|


## Outcome 8: exclusions

| run | kind | t | state | successful | n_O | n_O_source | excluded_total | excluded | error |
|---|---|---|---|---|---|---|---|---|---|


## Outcome 9: forecasts (halting on ktb_w3 + ktb_n1, scored offline)

| arm | scenario | horizon | required_cells | complete_cells | failed_cells | denominator_cells | mae | mean_signed_error |
|---|---|---|---|---|---|---|---|---|
| conv | NOI | 15min | 7 | 7 | 0 | 7 | 0 | 0 |
| conv | NOI | 5min | 8 | 8 | 0 | 8 | 0 | 0 |
| evt | NOI | 15min | 7 | 7 | 0 | 7 | 0 | 0 |
| evt | NOI | 5min | 8 | 8 | 0 | 8 | 0 | 0 |


Paired EVT - CONV absolute-error differences, per seed (complete pairs only):

| scenario | horizon | seed | n_pairs | mean_evt_minus_conv_abs_error |
|---|---|---|---|---|
| NOI | 15min | 4401 | 7 | 0 |
| NOI | 5min | 4401 | 8 | 0 |


Paired, pooled over seeds (complete pairs only):

| scenario | horizon | n_pairs | mean_evt_minus_conv_abs_error |
|---|---|---|---|
| NOI | 15min | 7 | 0 |
| NOI | 5min | 8 | 0 |


## Failures

No required forecast cell is missing or failed.


Defects: none recorded
