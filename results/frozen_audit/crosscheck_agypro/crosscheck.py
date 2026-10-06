import pandas as pd
import numpy as np
import json
import os
import math

# t critical values for 95% CI (two-tailed), index is df
T_CRIT = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306
}

def kendall_tau_a(x, y):
    n = len(x)
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i+1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx * dy > 0:
                concordant += 1
            elif dx * dy < 0:
                discordant += 1
    return (concordant - discordant) / (n * (n - 1) / 2)

df = pd.read_parquet('D:/CityCom-astra/results/frozen_audit/raw.parquet')
df['seed'] = df['seed'].astype(int)
df['replication'] = df['replication'].astype(int)

seeds = list(range(4501, 4509))
valid_seeds = []
per_seed_results = []

for s in seeds:
    df_s = df[df['seed'] == s]
    
    # Validation
    if not (df_s['status'] == 'ok').all():
        print(f"Seed {s} invalid: status not ok")
        continue
    if not np.isfinite(df_s['J']).all():
        print(f"Seed {s} invalid: J not finite")
        continue
        
    is_valid = True
    for w, b, reps in [
        ('twin', 'B', list(range(1, 7))),
        ('twin', 'D300', list(range(1, 7))),
        ('proxy', None, list(range(1, 7))),
        ('calibration', None, list(range(7, 13)))
    ]:
        if b is None:
            sub = df_s[(df_s['world'] == w) & df_s['belief'].isna()]
        else:
            sub = df_s[(df_s['world'] == w) & (df_s['belief'] == b)]
            
        if len(sub) != len(reps) * 5:
            is_valid = False
            print(f"Seed {s} invalid: wrong count for {w} {b}: {len(sub)}")
            break
            
        counts = sub.groupby(['action', 'replication']).size()
        if not (counts == 1).all() or len(counts) != len(reps) * 5:
            is_valid = False
            print(f"Seed {s} invalid: missing/dup combinations for {w} {b}")
            break
            
    if not is_valid:
        continue
        
    valid_seeds.append(s)
    
    # Proxy means
    sub_p = df_s[(df_s['world'] == 'proxy') & df_s['belief'].isna()]
    p_1_3 = sub_p[sub_p['replication'].isin([1,2,3])].groupby('action')['J'].mean()
    p_4_6 = sub_p[sub_p['replication'].isin([4,5,6])].groupby('action')['J'].mean()
    
    oracle = p_1_3.idxmin()
    def G_P(a):
        return p_4_6['A0'] - p_4_6[a]
        
    mean_J_P_A0 = p_4_6['A0']
    
    # Calibration
    sub_c = df_s[(df_s['world'] == 'calibration') & df_s['belief'].isna()]
    c_7_9 = sub_c[sub_c['replication'].isin([7,8,9])].groupby('action')['J'].mean()
    c_10_12 = sub_c[sub_c['replication'].isin([10,11,12])].groupby('action')['J'].mean()
    
    a_star_c = c_7_9.idxmin()
    floor_signed = (c_10_12['A0'] - c_10_12[a_star_c]) - G_P(a_star_c)
    
    # Twin
    res_s = {'seed': s, 'floor_signed': floor_signed, 'floor_abs': abs(floor_signed)}
    
    for b in ['B', 'D300']:
        sub_t = df_s[(df_s['world'] == 'twin') & (df_s['belief'] == b)]
        t_1_3 = sub_t[sub_t['replication'].isin([1,2,3])].groupby('action')['J'].mean()
        t_4_6 = sub_t[sub_t['replication'].isin([4,5,6])].groupby('action')['J'].mean()
        
        a_star = t_1_3.idxmin()
        G_hat_T_a_star = t_4_6['A0'] - t_4_6[a_star]
        
        bee = G_hat_T_a_star - G_P(a_star)
        bee_rel = bee / mean_J_P_A0
        
        regret = p_4_6[a_star] - p_4_6[oracle]
        denom = p_4_6['A0'] - p_4_6[oracle]
        regret_rel = regret / denom if denom >= 0.5 else np.nan
        
        top1 = 1 if a_star == oracle else 0
        
        spearman = t_4_6.rank().corr(p_4_6.rank())
        kendall = kendall_tau_a(t_4_6.values, p_4_6.values)
        
        G_hat_T_A3 = t_4_6['A0'] - t_4_6['A3']
        G_P_A3 = p_4_6['A0'] - p_4_6['A3']
        
        res_s[f'{b}_a_star'] = a_star
        res_s[f'{b}_oracle'] = oracle
        res_s[f'{b}_BEE'] = bee
        res_s[f'{b}_BEE_abs'] = abs(bee)
        res_s[f'{b}_BEE_rel'] = bee_rel
        res_s[f'{b}_Regret'] = regret
        res_s[f'{b}_Regret_rel'] = regret_rel
        res_s[f'{b}_Top1'] = top1
        res_s[f'{b}_Spearman'] = spearman
        res_s[f'{b}_Kendall'] = kendall
        res_s[f'{b}_G_hat_T_A3'] = G_hat_T_A3
        res_s[f'{b}_G_P_A3'] = G_P_A3
        
    per_seed_results.append(res_s)

df_res = pd.DataFrame(per_seed_results)
df_res.to_csv('D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/per_seed.csv', index=False)

def get_stats(series):
    s_clean = series.dropna()
    n = len(s_clean)
    if n == 0:
        return {'mean': np.nan, 'ci95': np.nan}
    mean = s_clean.mean()
    if n > 1:
        se = s_clean.std(ddof=1) / math.sqrt(n)
        ci = T_CRIT[n-1] * se
    else:
        ci = np.nan
    return {'mean': mean, 'ci95': ci}

summary = {}
# floor
summary['floor_abs'] = get_stats(df_res['floor_abs'])

for b in ['B', 'D300']:
    summary[b] = {
        'BEE': get_stats(df_res[f'{b}_BEE']),
        'BEE_abs': get_stats(df_res[f'{b}_BEE_abs']),
        'BEE_rel': get_stats(df_res[f'{b}_BEE_rel']),
        'Regret': get_stats(df_res[f'{b}_Regret']),
        'Regret_rel': get_stats(df_res[f'{b}_Regret_rel']),
        'Top1': {'mean': df_res[f'{b}_Top1'].mean(), 'ci95': np.nan},
        'Spearman': get_stats(df_res[f'{b}_Spearman']),
        'Kendall': get_stats(df_res[f'{b}_Kendall']),
        'G_hat_T_A3': get_stats(df_res[f'{b}_G_hat_T_A3']),
        'G_P_A3': get_stats(df_res[f'{b}_G_P_A3'])
    }

with open('D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

with open('D:/CityCom-astra/results/frozen_audit/crosscheck_agypro/summary.md', 'w') as f:
    f.write("# Crosscheck Summary\n\n")
    f.write("## Calibration\n")
    f.write(f"- floor_abs: {summary['floor_abs']['mean']:.4f} ± {summary['floor_abs']['ci95']:.4f}\n\n")
    for b in ['B', 'D300']:
        f.write(f"## Belief {b}\n")
        for k, v in summary[b].items():
            if np.isnan(v['ci95']):
                f.write(f"- {k}: {v['mean']:.4f}\n")
            else:
                f.write(f"- {k}: {v['mean']:.4f} ± {v['ci95']:.4f}\n")
        f.write("\n")

print("Done")
