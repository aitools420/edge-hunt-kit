#!/usr/bin/env python3
"""seeds20/summarize.py — pond #322 §3 e: the exam cell ALONE on the OPEN JUDGE days (09-17..09-25 entries) over SEEDS 20260927..20260946,
Option A engines. Per rule: d, its lower bound and p at min / 5th / 50th / 95th / max, and the share of seeds clearing each part of the
bar and the whole bar. The bar per seed is report.py's: Holm k = 2 across the two rules' alone runs OF THE SAME SEED (smaller p < 0.0125,
then the other < 0.025), d > 0, lower bound > 0, n >= 300 paired on >= 60 coins, drop-5 > 0, gates PASS. Writes SEEDS20.json / SEEDS20.md."""
import json, os, statistics
F = '/home/green/projects/patches/sealed-exam-blockA'; D = F + '/seeds20'
SEEDS = list(range(20260927, 20260947))
def path(k, s): return f'{F}/proof/out/stats_{k}_A_alone.json' if s == 20260927 else f'{D}/stats/{k}_A_alone_s{s}.json'
def holm(p1, p2):
    ps = sorted([(p if p is not None else 1.0, r) for r, p in ((1, p1), (2, p2))]); first = ps[0][0] < 0.0125
    return {ps[0][1]: first, ps[1][1]: first and ps[1][0] < 0.025}
rows, missing = {1: [], 2: []}, []
for s in SEEDS:
    st = {}
    for r, k in ((1, 'st'), (2, 'grid')):
        p = path(k, s)
        if not os.path.exists(p): missing.append(os.path.basename(p)); continue
        st[r] = json.load(open(p))
    if len(st) < 2: continue
    H = holm(st[1]['bar']['p_one_sided'], st[2]['bar']['p_one_sided'])
    for r in (1, 2):
        b = st[r]['bar']; g = all(v == 'PASS' for v in st[r]['gate']['status'].values())
        parts = dict(holm=H[r], d_pos=b['d_mean'] > 0, lb_pos=b['ci95'][0] > 0, n_ok=b['n'] >= 300 and b['coins'] >= 60, drop5_pos=b['drop5'] > 0, gates=g)
        rows[r].append(dict(seed=s, d=b['d_mean'], lb=b['ci95'][0], p=b['p_one_sided'], n=b['n'], coins=b['coins'], drop5=b['drop5'], **parts, passed=all(parts.values())))
def q(xs, f):
    xs = sorted(xs); i = (len(xs) - 1) * f; lo = int(i); hi = min(lo + 1, len(xs) - 1); return round(xs[lo] + (xs[hi] - xs[lo]) * (i - lo), 6)
out = dict(seeds_done=len(rows[1]), missing=missing, rules={})
md = ['# Exam cell alone on the open JUDGE days, 20 seeds (pond #322 §3 e)', '', f'Seeds with both rules done: {len(rows[1])} of 20.', '']
for r, cell in ((1, 'C2P'), (2, 'D25L48')):
    R = rows[r]
    if not R: continue
    dist = {k: {lab: q([x[k] for x in R], f) for lab, f in (('min', 0), ('p5', 0.05), ('p50', 0.5), ('p95', 0.95), ('max', 1))} for k in ('d', 'lb', 'p')}
    share = {k: round(sum(x[k] for x in R) / len(R), 3) for k in ('holm', 'd_pos', 'lb_pos', 'n_ok', 'drop5_pos', 'gates', 'passed')}
    out['rules'][r] = dict(cell=cell, dist=dist, share=share, per_seed=R)
    md += [f'## rule #{r} ({cell})', '', '| | min | 5th | median | 95th | max |', '|---|---|---|---|---|---|']
    for k, lab in (('d', 'd vs activity twin'), ('lb', 'lower bound'), ('p', 'one-sided p')):
        md.append(f'| {lab} | ' + ' | '.join(str(dist[k][x]) for x in ('min', 'p5', 'p50', 'p95', 'max')) + ' |')
    md += ['', 'Share of seeds clearing: ' + ', '.join(f'{k} {v:.0%}' for k, v in share.items()), '']
json.dump(out, open(D + '/SEEDS20.json', 'w'), indent=1)
open(D + '/SEEDS20.md', 'w').write('\n'.join(md) + '\n'); print('\n'.join(md))
