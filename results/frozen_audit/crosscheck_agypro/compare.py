import json
import numpy as np

with open('D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.json') as f:
    mine = json.load(f)
    
with open('D:/CityCom-astra/results/frozen_audit/metrics.json') as f:
    theirs = json.load(f)
    
map_keys = {
    'BEE': 'BEE_signed',
    'BEE_abs': 'BEE_abs',
    'BEE_rel': 'BEE_signed_rel',
    'Regret': 'Regret',
    'Regret_rel': 'Regret_rel',
    'Top1': 'top1_agree',
    'Spearman': 'spearman_rho',
    'Kendall': 'kendall_tau',
    'G_hat_T_A3': 'G_T_A3',
    'G_P_A3': 'G_P_A3'
}

diffs = []

def check(name, my_val, their_val):
    if np.isnan(my_val) and np.isnan(their_val):
        return
    if np.isnan(my_val) or np.isnan(their_val):
        diffs.append(f"{name}: mine={my_val}, theirs={their_val}")
        return
    if abs(my_val - their_val) > 1e-6:
        diffs.append(f"{name}: mine={my_val}, theirs={their_val}")

# floor_abs
my_floor = mine['floor_abs']['mean']
their_floor = theirs['primary']['pooled']['BEE_floor_abs']['mean']
check("Calibration floor_abs mean", my_floor, their_floor)

my_floor_ci = mine['floor_abs']['ci95']
their_floor_ci = theirs['primary']['pooled']['BEE_floor_abs']['ci95_t'][1] - their_floor
check("Calibration floor_abs ci95", my_floor_ci, their_floor_ci)

for b, b_key in [('B', 'primary'), ('D300', 'secondary')]:
    for my_k, their_k in map_keys.items():
        my_m = mine[b][my_k]['mean']
        their_m = theirs[b_key]['pooled'][their_k]['mean']
        check(f"{b} {my_k} mean", my_m, their_m)
        
        my_ci = mine[b][my_k]['ci95']
        if my_k != 'Top1':
            their_ci = theirs[b_key]['pooled'][their_k]['ci95_t'][1] - their_m
            check(f"{b} {my_k} ci95", my_ci, their_ci)

if not diffs:
    print("No differences > 1e-6!")
else:
    for d in diffs:
        print(d)
        
with open('D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.md', 'a') as f:
    f.write("\n## Comparison with metrics.json\n")
    if not diffs:
        f.write("All checked values match within 1e-6.\n")
    else:
        for d in diffs:
            f.write(f"- {d}\n")
