#!/usr/bin/env python3
"""analyze_grid.py — BLOOD 2-D GRID (dip depth x trading history), per PREREG.md (sha256 in PREREG.sha256).
Stats (SEs, block bootstrap, CI rule, Reality Check) copied from ../blood-stress-2026-09-27/analyze_st.py.
Usage: python3 analyze_grid.py <full.ndjson.gz> <results.json> [--quiet]"""
import json, sys, math, collections, datetime, gzip
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
QUIET = '--quiet' in sys.argv
import os
JUDGE0 = 0 if os.environ.get('SMOKE_AS_JUDGE') else 1789603200; DAY = 86400; SEED = 20260927
DIPS = [10, 15, 20, 25, 30, 40]; LEVELS = [0, 24, 48, 72]; LNAME = {0: 'all', 24: '>=24', 48: '>=48', 72: '72'}
CELLS = [f'D{d}L{L}' for d in DIPS for L in LEVELS]
K_FAM = 294; ALPHA = 0.05
GUESS = {'cell': 'D40L72', 'raw': 4.54}

def Phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
def dstr(ts): return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
R2 = lambda x: None if x is None else round(float(x), 2)

def heavy(r):
    eP, basis = r['eP'], (r['g5px'] if r.get('g5px') is not None else r['xP'])
    cb = r['entryPx'] / eP - 1; cs = 1 - r['sellPx'] / basis if basis > 0 else 0
    cb2 = max(cb, 0.014) + (0.01 if r.get('ePons') else 0); cs2 = max(cs, 0.014) + (0.01 if r.get('xPons') else 0)
    v = 100 * (basis * (1 - cs2) / (eP * (1 + cb2)) - 1) - 0.2
    return min(v, 0.0) if r['fb'] else v
def unsell_a(r): s = r.get('sell'); return (not s) or (not s['s10h']) or (s['sbr'] is not None and s['sbr'] < 0.5)
def unsell_c(r): return (r.get('nPostSell') or 0) == 0
def thin(r): return r['eK'] == 'v4' and r.get('eDepth1') is not None and r['eDepth1'] < 0.001

S, Wt, meta = {}, {'R': collections.defaultdict(list), 'A': collections.defaultdict(list)}, None
nofill, trunc = collections.Counter(), collections.Counter()
with gzip.open(SRC, 'rt') as fh:
    for ln in fh:
        j = json.loads(ln)
        if '_meta' in j: meta = j['_meta']; continue
        half = 'JUDGE' if j['T'] >= JUDGE0 else 'FIT'; j['half'] = half
        key = (j['kind'], j.get('tw'), j['cell'], half)
        if j.get('trunc'): trunc[key] += 1; continue
        if j.get('nofill'): nofill[key] += 1; continue
        j['fb'] = bool(j.get('fb')); j['on_uncapped'] = j['on']
        if j['fb']: j['on'] = min(j['on'], 0.0)
        j['heavy'] = heavy(j); j['day'] = (j['T'] // DAY) * DAY; j['v4e'] = j['eK'] == 'v4'
        for k in ('ePk', 'xPk', 'sigK', 'src', 'eu', 'ef', 'xw', 'otherPool', 'drainBlocked', 'eDelay'):
            j.pop(k, None)
        if j['kind'] == 'S': S[j['pair']] = j
        else: Wt[j['tw']][j['pair']].append(j)

def drop5(v): v = sorted(v); return float(np.mean(v[:-5])) if len(v) > 5 else None
def cl_se(vals, keys):
    v = np.asarray(vals); m = v.mean(); g = collections.defaultdict(float)
    for x, k in zip(v, keys): g[k] += x - m
    G = len(g)
    if G < 2: return None
    return math.sqrt(sum(s * s for s in g.values()) * G / (G - 1)) / len(v)
def block_boot(vals, days, L=2, B=10000, seed=SEED):
    ud = sorted(set(days)); D = len(ud); idx = {d: i for i, d in enumerate(ud)}
    s = np.zeros(D); c = np.zeros(D)
    for x, d in zip(vals, days): s[idx[d]] += x; c[idx[d]] += 1
    rng = np.random.default_rng(seed); nb = math.ceil(D / L)
    st = rng.integers(0, D, size=(B, nb)); take = ((st[:, :, None] + np.arange(L)[None, None, :]) % D).reshape(B, -1)[:, :D]
    bm = s[take].sum(1) / np.maximum(c[take].sum(1), 1)
    return dict(se=float(bm.std(ddof=1)), lo=float(np.percentile(bm, 2.5)), hi=float(np.percentile(bm, 97.5)), D=D)
def inference(vals, toks, days, seed):
    n = len(vals); m = float(np.mean(vals))
    se_iid = float(np.std(vals, ddof=1) / math.sqrt(n)); se_coin = cl_se(vals, toks); se_day = cl_se(vals, days)
    bb = block_boot(vals, days, 2, seed=seed) if len(set(days)) >= 2 else dict(se=None, lo=None, hi=None, D=len(set(days)))
    se = max(x for x in (se_iid, se_coin, se_day, bb['se']) if x is not None)
    cn = [m - 1.96 * se, m + 1.96 * se]; cb = [bb['lo'], bb['hi']]
    ci = cn if (cb[0] is None or cn[0] <= cb[0]) else cb
    return dict(mean=m, se_iid=se_iid, se_cons=se, ci95=ci, p=1 - Phi(m / se) if se > 0 else None, mde80=2.487 * se, days=bb['D'])

def summ_vals(vals, toks, days, seed):
    if len(vals) < 3: return {'n': len(vals)}
    I = inference(vals, toks, days, seed)
    return dict(n=len(vals), coins=len(set(toks)), mean=R2(I['mean']), median=R2(np.median(vals)), ci95=[R2(x) for x in I['ci95']],
                se_iid=R2(I['se_iid']), se_cons=R2(I['se_cons']), p_one_sided=None if I['p'] is None else float(f"{I['p']:.3g}"),
                mde80=R2(I['mde80']), upper95=R2(I['mean'] + 1.645 * I['se_cons']), drop5=R2(drop5(vals)), days=I['days'])

def paired(rows, tw, view, twin_pred=None):
    out = []
    for r in rows:
        ws = [w for w in Wt[tw].get(r['pair'], []) if twin_pred is None or twin_pred(w)]
        if not ws: continue
        tv = sum(w[view] for w in ws) / len(ws); out.append((r, r[view] - tv, tv, ws))
    return out
def dsum(rows, tw, view, seed, twin_pred=None):
    pr = paired(rows, tw, view, twin_pred)
    if len(pr) < 3: return {'n': len(pr)}
    d = [x[1] for x in pr]; s = summ_vals(d, [x[0]['tok'] for x in pr], [x[0]['day'] for x in pr], seed)
    s['d_mean'] = s.pop('mean'); s['d_median'] = s.pop('median')
    s['raw_mean'] = R2(np.mean([x[0][view] for x in pr])); s['twin_mean'] = R2(np.mean([x[2] for x in pr]))
    s['twin_tp_share'] = R2(np.mean([w['reason'] == 'tp' for x in pr for w in x[3]]))
    s['twin_crash_share'] = R2(np.mean([w['on'] <= -50 for x in pr for w in x[3]]))
    return s
def srows(cell, half, pred=None): return [r for r in S.values() if r['cell'] == cell and r['half'] == half and (pred is None or pred(r))]
def rawsum(rows, view, seed):
    if len(rows) < 3: return {'n': len(rows)}
    return summ_vals([r[view] for r in rows], [r['tok'] for r in rows], [r['day'] for r in rows], seed)

def cell_block(cell, half, seed):
    rows = srows(cell, half)
    o = dict(n=len(rows), coins=len({r['tok'] for r in rows}))
    if len(rows) < 3: return o
    o['raw_base'] = rawsum(rows, 'on', seed + 1); o['raw_heavy'] = rawsum(rows, 'heavy', seed + 2)
    o['tp_share'] = R2(np.mean([r['reason'] == 'tp' for r in rows])); o['crash_share'] = R2(np.mean([r['on'] <= -50 for r in rows]))
    o['drain_share'] = R2(np.mean([r['reason'] == 'drain' for r in rows]))
    o['v4_entry_share'] = R2(np.mean([r['v4e'] for r in rows])); o['pons_entry_share'] = R2(np.mean([r['pad'] == 'Pons' for r in rows]))
    o['d_base_vs_R'] = dsum(rows, 'R', 'on', seed + 3); o['d_heavy_vs_R'] = dsum(rows, 'R', 'heavy', seed + 4)
    o['d_base_vs_A'] = dsum(rows, 'A', 'on', seed + 5); o['d_heavy_vs_A'] = dsum(rows, 'A', 'heavy', seed + 6)   # PRIMARY
    o['venue'] = {k: dict(n=len(rs), raw_base=R2(np.mean([r['on'] for r in rs])) if rs else None, raw_heavy=R2(np.mean([r['heavy'] for r in rs])) if rs else None,
                          d_heavy_vs_A=dsum(rs, 'A', 'heavy', seed + 7 + i))
                  for i, (k, rs) in enumerate((('v4', [r for r in rows if r['v4e']]), ('v23', [r for r in rows if not r['v4e']])))}
    o['hot'] = dsum([r for r in rows if r.get('sigHot') == 1], 'A', 'heavy', seed + 9)
    o['not_hot'] = dsum([r for r in rows if r.get('sigHot') == 0], 'A', 'heavy', seed + 10)
    o['view_depth_floor'] = dsum([r for r in rows if not thin(r)], 'A', 'heavy', seed + 11, twin_pred=lambda w: not thin(w))
    o['view_depth_floor']['strategy_dropped'] = sum(thin(r) for r in rows)
    o['non_pons'] = dsum([r for r in rows if r['pad'] != 'Pons'], 'A', 'heavy', seed + 12)
    return o

def gate(cell, half='JUDGE'):
    o = {}
    for nm, kind, tw in (('S', 'S', None), ('WR', 'W', 'R'), ('WA', 'W', 'A')):
        rows = srows(cell, half) if kind == 'S' else [w for v in Wt[tw].values() for w in v if w['cell'] == cell and w['half'] == half]
        nf, tr = nofill[(kind, tw, cell, half)], trunc[(kind, tw, cell, half)]; tot = len(rows) + nf + tr
        small = sum(r['eU'] < 10 and r['eK'] != 'v4' for r in rows) + sum(r['xU'] < 10 and r['xK'] != 'v4' for r in rows)
        o[nm] = dict(draws=tot, booked=len(rows), nofill=nf, trunc=tr, fallback=sum(r['fb'] for r in rows),
                     priced_share=R2(sum(1 for r in rows if not r['fb']) / tot) if tot else None, g4_small_share=R2(small / (2 * len(rows))) if rows else None,
                     drains=sum(r['reason'] == 'drain' for r in rows), exit_gt20x=sum(r['xP'] > 20 * r['eP'] for r in rows),
                     g5=dict(collections.Counter(r['g5'] for r in rows if r['g5'])), g5_fail=sum(1 for r in rows if r['on'] > 1000 and r['g5'] not in ('depthok', 'corroborated')),
                     max_on=R2(max((r['on'] for r in rows), default=None)), s3a_unsellable=R2(np.mean([unsell_a(r) for r in rows])) if rows else None,
                     s3c_unsellable=R2(np.mean([unsell_c(r) for r in rows])) if rows else None, thin_entry=sum(thin(r) for r in rows))
    g1 = (o['S']['priced_share'] or 0) >= 0.60; g4 = (o['S']['g4_small_share'] or 0) < 0.20; g5 = o['S']['g5_fail'] == 0 and o['WA']['g5_fail'] == 0 and o['WR']['g5_fail'] == 0
    g10 = all((o[k]['priced_share'] or 0) >= 0.60 and (o[k]['g4_small_share'] or 0) < 0.20 for k in ('WR', 'WA') if o[k]['draws'])
    o['status'] = dict(G1='PASS' if g1 else 'FAIL', G4='PASS' if g4 else 'FAIL', G5='PASS' if g5 else 'FAIL', G10='PASS' if g10 else 'FAIL')
    return o

def outl(cell, half='JUDGE', k=5):
    def desc(r): return dict(kind=r['kind'], tw=r.get('tw'), tok=r['tok'], pad=r['pad'], on=round(r['on'], 1), heavy=round(r['heavy'], 1), reason=r['reason'],
                             entry=dstr(r['entryTs']), exit=dstr(r['exitTs']), eK=r['eK'], eU=r['eU'], xU=r['xU'], x_over_e=round(r['xP'] / r['eP'], 3), g5=r['g5'], eDepth1=r.get('eDepth1'))
    s = sorted(srows(cell, half), key=lambda r: -r['heavy'])
    return dict(strategy_best=[desc(r) for r in s[:k]], strategy_worst=[desc(r) for r in s[-k:]])

# ---- Reality Check over the 24 cells, primary statistic ----
def reality_check(B=5000, seed=SEED):
    fam = {}
    for c in CELLS:
        pr = paired(srows(c, 'JUDGE'), 'A', 'heavy')
        if len(pr) >= 30: fam[c] = [(x[0]['tok'], x[0]['day'], x[1]) for x in pr]
    names = sorted(fam); tstat = {}
    if not names: return dict(family=0, cells_in_rc=[], best_cell=None, day_block2=dict(adj_p={}), coins=dict(adj_p={}))
    days = sorted({d for n in names for _, d, _ in fam[n]}); coins = sorted({t for n in names for t, _, _ in fam[n]})
    di = {d: i for i, d in enumerate(days)}; ci = {t: i for i, t in enumerate(coins)}; agg = {}
    for n in names:
        v = np.array([x[2] for x in fam[n]]); m = v.mean(); se = v.std(ddof=1) / math.sqrt(len(v)); tstat[n] = m / se
        sd, cd = np.zeros(len(days)), np.zeros(len(days)); sc, cc = np.zeros(len(coins)), np.zeros(len(coins))
        for t, d, x in fam[n]: sd[di[d]] += x; cd[di[d]] += 1; sc[ci[t]] += x; cc[ci[t]] += 1
        agg[n] = (m, se, sd, cd, sc, cc)
    rng = np.random.default_rng(seed); D, C = len(days), len(coins); L = 2
    nb = math.ceil(D / L); st = rng.integers(0, D, size=(B, nb)); take = ((st[:, :, None] + np.arange(L)[None, None, :]) % D).reshape(B, -1)[:, :D]
    wD = np.zeros((B, D)); np.add.at(wD, (np.repeat(np.arange(B), D), take.ravel()), 1)
    wC = np.zeros((B, C), dtype=np.float32)
    for b in range(B): wC[b] = np.bincount(rng.integers(0, C, C), minlength=C)
    res = {}
    for nm, w, si, ci_ in (('day_block2', wD, 2, 3), ('coins', wC, 4, 5)):
        mx = np.full(B, -np.inf)
        for n in names:
            m, se, *_ = agg[n]; s_, c_ = agg[n][si], agg[n][ci_]
            bm = (w @ s_) / np.maximum(w @ c_, 1); mx = np.maximum(mx, (bm - m) / se)
        res[nm] = dict(max_null_p95=R2(float(np.percentile(mx, 95))), adj_p={n: round(float(np.mean(mx >= tstat[n])), 4) for n in names})
    best = max(names, key=lambda n: tstat[n])
    return dict(family=len(names), cells_in_rc=names, n_days=D, n_coins=C, t={n: R2(tstat[n]) for n in names}, best_cell=best, t_best=R2(tstat[best]),
                p_best_day_block2=res['day_block2']['adj_p'][best], p_best_coins=res['coins']['adj_p'][best], **res)

# ---- evaluate ----
R = dict(test='Blood 2-D grid: dip depth x 72 h trading history', date='2026-09-27', prereg_sha256=(open('PREREG.sha256').read().split()[0] if os.path.exists('PREREG.sha256') else None), cells={})
for i, c in enumerate(CELLS):
    R['cells'][c] = dict(JUDGE=cell_block(c, 'JUDGE', SEED + 100 * i), FIT=cell_block(c, 'FIT', SEED + 100 * i + 50), gate=gate(c), gate_fit=gate(c, 'FIT'))
rc = reality_check(); R['reality_check'] = rc
# G6 smoothness
def val(c, key, half='JUDGE'):
    J = R['cells'][c][half]
    if key == 'n': return J['n'], 0
    if key == 'd': x = J.get('d_heavy_vs_A', {}); return x.get('d_mean'), x.get('se_cons')
    if key == 'raw': x = J.get('raw_heavy', {}); return x.get('mean'), x.get('se_cons')
    if key == 'twA': x = J.get('d_heavy_vs_A', {}); return x.get('twin_mean'), x.get('se_cons')
def smooth(half):
    out = dict(count_rises=[], kinks=[], twin_jumps=[])
    for axis in ('dip', 'level'):
        lines = [[f'D{d}L{L}' for d in DIPS] for L in LEVELS] if axis == 'dip' else [[f'D{d}L{L}' for L in LEVELS] for d in DIPS]
        for ln in lines:
            for a, b in zip(ln, ln[1:]):
                na, nb_ = val(a, 'n', half)[0], val(b, 'n', half)[0]
                if na and nb_ > 1.05 * na: out['count_rises'].append(dict(axis=axis, from_=a, to=b, n_from=na, n_to=nb_))
                ta, sa = val(a, 'twA', half); tb, sb = val(b, 'twA', half)
                if axis == 'dip' and None not in (ta, tb, sa) and abs(tb - ta) > 2 * max(sa, sb or 0): out['twin_jumps'].append(dict(from_=a, to=b, twinA_from=ta, twinA_to=tb, se=max(sa, sb or 0)))
            for k in range(1, len(ln) - 1):
                for key in ('d', 'raw', 'twA'):
                    x, se = val(ln[k], key, half); x0, _ = val(ln[k - 1], key, half); x1, _ = val(ln[k + 1], key, half)
                    if None in (x, se, x0, x1): continue
                    if abs(x - (x0 + x1) / 2) > 2 * se: out['kinks'].append(dict(axis=axis, cell=ln[k], stat=key, value=x, neighbours=[x0, x1], se_cons=se))
    out['verdict'] = 'PIPELINE SUSPECT' if out['count_rises'] else ('KINKS' if out['kinks'] or out['twin_jumps'] else 'SMOOTH')
    return out
R['G6'] = dict(JUDGE=smooth('JUDGE'), FIT=smooth('FIT'))
# verdicts
for c in CELLS:
    C = R['cells'][c]; J = C['JUDGE']; P = J.get('d_heavy_vs_A', {})
    fails = [g for g, s in C['gate']['status'].items() if s == 'FAIL']
    p = P.get('p_one_sided'); bonf = p is not None and p < ALPHA / K_FAM
    rcp = (rc['day_block2']['adj_p'].get(c), rc['coins']['adj_p'].get(c)); rcpass = None not in rcp and max(rcp) < 0.05
    ci_ok = P.get('n', 0) >= 30 and P['ci95'][0] > 0
    money = J.get('raw_heavy', {}).get('n', 0) >= 30 and J['raw_heavy']['ci95'][0] > 0
    if fails: v = "⚠️ Can't tell (data)"
    elif P.get('n', 0) < 30: v = "Can't tell (n)"
    elif ci_ok and bonf and rcpass: v = '✅ beats the activity twin at heavy cost, survives the family correction'
    elif ci_ok: v = '🟡 beats the activity twin on its own CI, NOT after the family correction'
    else: v = f"❌ not shown (upper 95 % bound {P.get('upper95')})"
    C['verdict'] = v; C['gate_fails'] = fails; C['makes_money_heavy'] = money
    C['makes_money_base'] = J.get('raw_base', {}).get('n', 0) >= 30 and J['raw_base']['ci95'][0] > 0
    C['family'] = dict(K=K_FAM, alpha=ALPHA / K_FAM, p=p, bonferroni_pass=bonf, rc_adj_p_day_block2=rcp[0], rc_adj_p_coins=rcp[1], rc_pass=rcpass)
# Holm over the 24 (context)
ps = sorted([(R['cells'][c]['family']['p'], c) for c in CELLS if R['cells'][c]['family']['p'] is not None])
holm, stop = {}, False
for i, (p, c) in enumerate(ps):
    if stop or p >= ALPHA / (len(ps) - i): stop = True; holm[c] = False
    else: holm[c] = True
for c in CELLS: R['cells'][c]['family']['holm24_pass'] = holm.get(c, False)
R['outliers'] = {c: outl(c) for c in ('D20L0', 'D40L0', 'D40L72', 'D10L0')}
R['meta'] = {k: meta[k] for k in ('rows', 'rowsV4', 'v4skipLiq0', 'univRows', 'bad', 'badV4', 'exits', 'trunc', 'end', 'holes', 'holeAt', 'nofill', 'mergedOutOfOrder', 'v4OutOfOrder',
                                  'reorder', 'trig', 'twinEmpty', 'matchLvl', 'eligL', 'drop', 'assess', 'fixA', 'fixB', 'fixC', 'feeSrc', 'g5', 'wide0', 'sec', 'peakRssMB', 'profCalls')}
R['meta']['v23Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v23Files'].items() if v['first']}
R['meta']['v4Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v4Files'].items() if v['first']}
json.dump(R, open(OUT, 'w'), indent=1, default=float)
if QUIET:
    print('ok', len(S), 'strategy rows', sum(len(v) for t in Wt.values() for v in t.values()), 'twin rows; keys', sorted(R['cells']['D20L0']['JUDGE'].keys()) if R['cells']['D20L0']['JUDGE'].get('n', 0) >= 3 else 'no JUDGE rows (smoke)')
    sys.exit(0)
print('RC best', rc['best_cell'], rc['t_best'], rc['p_best_day_block2'], rc['p_best_coins'])
for c in CELLS:
    C = R['cells'][c]; J = C['JUDGE']; P = J.get('d_heavy_vs_A', {}); Rb = J.get('raw_base', {}); Rh = J.get('raw_heavy', {}); F = C['FIT'].get('d_heavy_vs_A', {})
    print(f"{c:<7} n {J['n']:>5} co {J.get('coins')} rawB {Rb.get('mean')} {Rb.get('ci95')} rawH {Rh.get('mean')} {Rh.get('ci95')} | dA_H {P.get('d_mean')} {P.get('ci95')} p {P.get('p_one_sided')} | "
          f"dR_B {J.get('d_base_vs_R', {}).get('d_mean')} | tp {J.get('tp_share')} cr {J.get('crash_share')} v4 {J.get('v4_entry_share')} | FIT n {C['FIT']['n']} dA_H {F.get('d_mean')} {F.get('ci95')} | {C['verdict']} {C['gate_fails']}")
print('G6', json.dumps(R['G6']['JUDGE'])[:3000])
