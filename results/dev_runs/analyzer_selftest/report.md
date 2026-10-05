# Development-runs outcomes (docs/oct13-dev-runs-plan.md revision 2, outcomes 1-9)

Runs analysed: 12. Descriptive counts and means only: no inference, no acceptance criteria, no tuning. Every rate carries its denominator.

## Accounting

| slot | status | attempt | run_dir | in_statistics | note |
|---|---|---|---|---|---|
| conv_inc_4101 | not_declared | n/a | results\event_pilot2\runs\conv_inc_4101 | yes | no --slots: every run directory enters statistics |
| conv_inc_4102 | not_declared | n/a | results\event_pilot2\runs\conv_inc_4102 | yes | no --slots: every run directory enters statistics |
| conv_inc_4103 | not_declared | n/a | results\event_pilot2\runs\conv_inc_4103 | yes | no --slots: every run directory enters statistics |
| evt_inc_4101 | not_declared | n/a | results\event_pilot2\runs\evt_inc_4101 | yes | no --slots: every run directory enters statistics |
| evt_inc_4102 | not_declared | n/a | results\event_pilot2\runs\evt_inc_4102 | yes | no --slots: every run directory enters statistics |
| evt_inc_4103 | not_declared | n/a | results\event_pilot2\runs\evt_inc_4103 | yes | no --slots: every run directory enters statistics |
| evt_noi_4101 | not_declared | n/a | results\event_pilot2\runs\evt_noi_4101 | yes | no --slots: every run directory enters statistics |
| evt_noi_4102 | not_declared | n/a | results\event_pilot2\runs\evt_noi_4102 | yes | no --slots: every run directory enters statistics |
| evt_noi_4103 | not_declared | n/a | results\event_pilot2\runs\evt_noi_4103 | yes | no --slots: every run directory enters statistics |
| evtforce_inc_4101 | not_declared | n/a | results\event_pilot2\runs\evtforce_inc_4101 | yes | no --slots: every run directory enters statistics |
| evtforce_inc_4102 | not_declared | n/a | results\event_pilot2\runs\evtforce_inc_4102 | yes | no --slots: every run directory enters statistics |
| evtforce_inc_4103 | not_declared | n/a | results\event_pilot2\runs\evtforce_inc_4103 | yes | no --slots: every run directory enters statistics |


## Outcome 1: exposure

| run | scenario | arm | seed | alarm_events | alarm_ticks | min_SUSPECTED | min_DEGRADED | min_EVENT | min_RECOVERY | lib_attempted | lib_successful | lib_failed | clr_attempted | clr_successful | clr_failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| conv_inc_4101 | INC | conv | 4101 | n/a | n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 |
| conv_inc_4102 | INC | conv | 4102 | n/a | n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 |
| conv_inc_4103 | INC | conv | 4103 | n/a | n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 |
| evt_inc_4101 | INC | evt | 4101 | 2 | 6 | 2 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 |
| evt_inc_4102 | INC | evt | 4102 | 2 | 6 | 2 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 |
| evt_inc_4103 | INC | evt | 4103 | 3 | 6 | 2 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 0 |
| evt_noi_4101 | NOI | evt | 4101 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| evt_noi_4102 | NOI | evt | 4102 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| evt_noi_4103 | NOI | evt | 4103 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| evtforce_inc_4101 | INC | evt | 4101 | 3 | 7 | 0 | 0 | 4 | 29 | 3 | 3 | 0 | 4 | 4 | 0 |
| evtforce_inc_4102 | INC | evt | 4102 | 2 | 8 | 0 | 0 | 5 | 11.5 | 2 | 2 | 0 | 5 | 5 | 0 |
| evtforce_inc_4103 | INC | evt | 4103 | 1 | 15 | 0 | 0 | 8 | 31 | 1 | 1 | 0 | 8 | 8 | 0 |


Pooled per scenario (EVT runs):

| scenario | n_runs | n_evt_runs | alarm_events | min_SUSPECTED | min_DEGRADED | min_EVENT | min_RECOVERY | lib_a/s/f | clr_a/s/f |
|---|---|---|---|---|---|---|---|---|---|
| INC | 9 | 6 | 13 | 6 | 0 | 17 | 71.5 | 19/19/0 | 17/17/0 |
| NOI | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0/0/0 | 0/0/0 |


## Outcome 2: natural adoption (INC, EVT)

| run | successful_library_evals | natural_adoptions | rate | any | first_t | timing_class | delay_s | delay_censored_at | forced_adoptions |
|---|---|---|---|---|---|---|---|---|---|
| evt_inc_4101 | 4 | 0 | 0 | no | n/a | n/a | n/a | 2700 | 0 |
| evt_inc_4102 | 4 | 0 | 0 | no | n/a | n/a | n/a | 2700 | 0 |
| evt_inc_4103 | 5 | 0 | 0 | no | n/a | n/a | n/a | 2700 | 0 |
| evtforce_inc_4101 | 3 | 1 | 0.333 | yes | 6450 | post_clearance | 1950 | n/a | 1 |
| evtforce_inc_4102 | 2 | 0 | 0 | no | n/a | n/a | n/a | 2700 | 1 |
| evtforce_inc_4103 | 1 | 0 | 0 | no | n/a | n/a | n/a | 2700 | 1 |


Pooled INC: 1/6 runs with an adoption; 5 right-censored at 2700 s. Adoptions 1 / 19 successful library evaluations = 0.053. Timing classes: {'post_clearance': 1}. From forced runs: 1.


Identification over all natural INC adoptions:

| run | t | h_star | edge | k | s | gap_vs_demand | gap_gt_ln10 | location_correct | exact_ks | timing_class | forced |
|---|---|---|---|---|---|---|---|---|---|---|---|
| evtforce_inc_4101 | 6450 | inc_ktb_n2_k1_s1 | ktb_n2 | 1 | 1 | 8.456 | yes | no | no | post_clearance | no |


Location correct (edge ktb_n1): 0/1. Exact (k, s) = (2, 1.0): 0/1. (k, s) values: {'k1_s1.0': 1}.


## Outcome 3: false adoption (NOI / SHK / DET, EVT)

| run | scenario | successful_library_evals | adoptions | rate |
|---|---|---|---|---|
| evt_noi_4101 | NOI | 0 | 0 | n/a |
| evt_noi_4102 | NOI | 0 | 0 | n/a |
| evt_noi_4103 | NOI | 0 | 0 | n/a |


NOI: 0 adoptions / 0 successful library evaluations = n/a; 0/3 runs with an adoption.


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
| evtforce_inc_4101 | INC | 4101 | 5010 | 5010 | inc_ktb_n1_k2_s1 | during_incident | yes | yes | 2 | 5130 | 180 | 4950 | 0.984 | cleared | no | yes | yes | no |
| evtforce_inc_4101 | INC | 4101 | 6450 | 6450 | inc_ktb_n2_k1_s1 | post_clearance | no | yes | 2 | 6570 | 240 | 6330 | 1 | cleared | no | n/a | n/a | n/a |
| evtforce_inc_4102 | INC | 4102 | 4890 | 4890 | inc_ktb_n1_k2_s1 | during_incident | yes | yes | 5 | 5190 | 240 | 4950 | 0.825 | cleared | no | yes | yes | no |
| evtforce_inc_4103 | INC | 4103 | 4860 | 4860 | inc_ktb_n1_k2_s1 | during_incident | yes | yes | 8 | 5340 | 300 | 5040 | 0.983 | cleared | no | yes | yes | no |


Every executed clearance record (t_dec, tau_c, t_clr, p_clear) is in outcomes.json under `clearance_records`; the episode row uses the deciding record.


INC: 4 adoption episodes; timing classes {'during_incident': 3, 'post_clearance': 1}; outcomes {'cleared': 4}; labelled (natural INC during the incident) 0: premature inference 0, premature live release 0, late 0; forced-run episodes with the same numbers: 3/3/0.


## Outcome 6: recovery spells

| run | scenario | enter | exit | duration_s | spell_class | exit_reason |
|---|---|---|---|---|---|---|
| evtforce_inc_4101 | INC | 5130 | 6240 | 1110 | completed | recovery_complete |
| evtforce_inc_4101 | INC | 6570 | n/a | 630 | censored | n/a |
| evtforce_inc_4102 | INC | 5190 | 5880 | 690 | interrupted_by_trigger | trigger_alarm |
| evtforce_inc_4103 | INC | 5340 | n/a | 1860 | censored | n/a |


INC: 4 spells; {'censored': 2, 'completed': 1, 'interrupted_by_trigger': 1}; durations {'censored': ['630', '1860'], 'completed': ['1110'], 'interrupted_by_trigger': ['690']}.


## Outcome 7: DEGRADED spells (live)

| run | scenario | enter | exit | duration_s | spell_class | exit_at_entry_plus_900 | exit_reason |
|---|---|---|---|---|---|---|---|


INC: 0 spells; {}; exits at entry + 900 s exactly: 0; exit live-covered: no.


NOI: 0 spells; {}; exits at entry + 900 s exactly: 0; exit live-covered: no.


## Outcome 8: exclusions

| run | kind | t | state | successful | n_O | n_O_source | excluded_total | excluded | error |
|---|---|---|---|---|---|---|---|---|---|
| evt_inc_4101 | library | 5010 | SUSPECTED_EVENT | yes | 165 | logged | 45 | {"obs_invalid": 45} | n/a |
| evt_inc_4101 | library | 5040 | SUSPECTED_EVENT | yes | 135 | logged | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evt_inc_4101 | library | 5100 | SUSPECTED_EVENT | yes | 135 | logged | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evt_inc_4101 | library | 5160 | SUSPECTED_EVENT | yes | 174 | logged | 36 | {"partial_block": 84, "obs_invalid": 36} | n/a |
| evt_inc_4102 | library | 4890 | SUSPECTED_EVENT | yes | 177 | logged | 33 | {"obs_invalid": 33} | n/a |
| evt_inc_4102 | library | 4920 | SUSPECTED_EVENT | yes | 141 | logged | 27 | {"partial_block": 84, "obs_invalid": 27} | n/a |
| evt_inc_4102 | library | 4980 | SUSPECTED_EVENT | yes | 141 | logged | 27 | {"partial_block": 84, "obs_invalid": 27} | n/a |
| evt_inc_4102 | library | 5040 | SUSPECTED_EVENT | yes | 177 | logged | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evt_inc_4103 | library | 4860 | SUSPECTED_EVENT | yes | 144 | logged | 24 | {"partial_block": 84, "obs_invalid": 24} | n/a |
| evt_inc_4103 | library | 4890 | SUSPECTED_EVENT | yes | 177 | logged | 33 | {"obs_invalid": 33} | n/a |
| evt_inc_4103 | library | 4920 | SUSPECTED_EVENT | yes | 141 | logged | 27 | {"partial_block": 84, "obs_invalid": 27} | n/a |
| evt_inc_4103 | library | 4980 | SUSPECTED_EVENT | yes | 141 | logged | 27 | {"partial_block": 84, "obs_invalid": 27} | n/a |
| evt_inc_4103 | library | 5040 | SUSPECTED_EVENT | yes | 177 | logged | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evtforce_inc_4101 | library | 5010 | SUSPECTED_EVENT | yes | 165 | logged | 45 | {"obs_invalid": 45} | n/a |
| evtforce_inc_4101 | clearance | 5070 | EVENT_ASSIMILATION | yes | 165 | derived | 45 | {"partial_block": 42, "obs_invalid": 45} | n/a |
| evtforce_inc_4101 | clearance | 5130 | EVENT_ASSIMILATION | yes | 204 | derived | 48 | {"obs_invalid": 48} | n/a |
| evtforce_inc_4101 | library | 6420 | SUSPECTED_EVENT | yes | 123 | logged | 45 | {"partial_block": 84, "obs_invalid": 45} | n/a |
| evtforce_inc_4101 | library | 6450 | SUSPECTED_EVENT | yes | 153 | logged | 57 | {"obs_invalid": 57} | n/a |
| evtforce_inc_4101 | clearance | 6510 | EVENT_ASSIMILATION | yes | 153 | derived | 57 | {"partial_block": 42, "obs_invalid": 57} | n/a |
| evtforce_inc_4101 | clearance | 6570 | EVENT_ASSIMILATION | yes | 192 | derived | 60 | {"obs_invalid": 60} | n/a |
| evtforce_inc_4102 | library | 4890 | SUSPECTED_EVENT | yes | 177 | logged | 33 | {"obs_invalid": 33} | n/a |
| evtforce_inc_4102 | clearance | 4950 | EVENT_ASSIMILATION | yes | 177 | derived | 33 | {"partial_block": 42, "obs_invalid": 33} | n/a |
| evtforce_inc_4102 | clearance | 5010 | EVENT_ASSIMILATION | yes | 213 | derived | 39 | {"obs_invalid": 39} | n/a |
| evtforce_inc_4102 | clearance | 5070 | EVENT_ASSIMILATION | yes | 213 | derived | 39 | {"partial_block": 42, "obs_invalid": 39} | n/a |
| evtforce_inc_4102 | clearance | 5130 | EVENT_ASSIMILATION | yes | 240 | derived | 54 | {"obs_invalid": 54} | n/a |
| evtforce_inc_4102 | clearance | 5190 | EVENT_ASSIMILATION | yes | 240 | derived | 54 | {"partial_block": 42, "obs_invalid": 54} | n/a |
| evtforce_inc_4102 | library | 5880 | SUSPECTED_EVENT | yes | 141 | logged | 27 | {"partial_block": 84, "obs_invalid": 27} | n/a |
| evtforce_inc_4103 | library | 4860 | SUSPECTED_EVENT | yes | 144 | logged | 24 | {"partial_block": 84, "obs_invalid": 24} | n/a |
| evtforce_inc_4103 | clearance | 4920 | EVENT_ASSIMILATION | yes | 177 | derived | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evtforce_inc_4103 | clearance | 4980 | EVENT_ASSIMILATION | yes | 177 | derived | 33 | {"partial_block": 84, "obs_invalid": 33} | n/a |
| evtforce_inc_4103 | clearance | 5040 | EVENT_ASSIMILATION | yes | 213 | derived | 39 | {"partial_block": 84, "obs_invalid": 39} | n/a |
| evtforce_inc_4103 | clearance | 5100 | EVENT_ASSIMILATION | yes | 213 | derived | 39 | {"partial_block": 84, "obs_invalid": 39} | n/a |
| evtforce_inc_4103 | clearance | 5160 | EVENT_ASSIMILATION | yes | 243 | derived | 51 | {"partial_block": 84, "obs_invalid": 51} | n/a |
| evtforce_inc_4103 | clearance | 5220 | EVENT_ASSIMILATION | yes | 243 | derived | 51 | {"partial_block": 84, "obs_invalid": 51} | n/a |
| evtforce_inc_4103 | clearance | 5280 | EVENT_ASSIMILATION | yes | 276 | derived | 60 | {"partial_block": 84, "obs_invalid": 60} | n/a |
| evtforce_inc_4103 | clearance | 5340 | EVENT_ASSIMILATION | yes | 276 | derived | 60 | {"partial_block": 84, "obs_invalid": 60} | n/a |


INC library: 19 evaluations (19 successful); |O| [165, 135, 135, 174, 177, 141, 141, 177, 144, 177, 141, 141, 177, 165, 123, 153, 177, 141, 144]; exclusions by reason {'obs_invalid': 642, 'partial_block': 1092}.


INC clearance: 17 evaluations (17 successful); |O| [165, 204, 153, 192, 177, 213, 213, 240, 240, 177, 177, 213, 213, 243, 243, 276, 276]; exclusions by reason {'obs_invalid': 795, 'partial_block': 882}.


## Outcome 9: forecasts (halting on ktb_w3 + ktb_n1, scored offline)

| arm | scenario | horizon | required_cells | complete_cells | failed_cells | denominator_cells | mae | mean_signed_error |
|---|---|---|---|---|---|---|---|---|
| conv | INC | 15min | 21 | 21 | 0 | 21 | 18.381 | -18.381 |
| conv | INC | 5min | 24 | 24 | 0 | 24 | 19.25 | -19.25 |
| evt | INC | 15min | 42 | 42 | 0 | 42 | 18.5 | -17.452 |
| evt | INC | 5min | 48 | 48 | 0 | 48 | 18.479 | -18.438 |
| evt | NOI | 15min | 21 | 21 | 0 | 21 | 0 | 0 |
| evt | NOI | 5min | 24 | 24 | 0 | 24 | 0 | 0 |


Paired EVT - CONV absolute-error differences, per seed (complete pairs only):

| scenario | horizon | seed | n_pairs | mean_evt_minus_conv_abs_error |
|---|---|---|---|---|
| INC | 15min | 4101 | 7 | 1.571 |
| INC | 15min | 4102 | 7 | 1.286 |
| INC | 15min | 4103 | 7 | -2.143 |
| INC | 5min | 4101 | 8 | -1.375 |
| INC | 5min | 4102 | 8 | -1.625 |
| INC | 5min | 4103 | 8 | -1.625 |


Paired, pooled over seeds (complete pairs only):

| scenario | horizon | n_pairs | mean_evt_minus_conv_abs_error |
|---|---|---|---|
| INC | 15min | 21 | 0.238 |
| INC | 5min | 24 | -1.542 |


## Failures

No required forecast cell is missing or failed.


Defects: none recorded
