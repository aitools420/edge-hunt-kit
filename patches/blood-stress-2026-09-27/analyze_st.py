#!/usr/bin/env python3
"""analyze_st.py — BLOOD DIP LEAD STRESS TEST, per PREREG.md (sha256 in PREREG.sha256).
Stats (SEs, block bootstrap, CI rule) copied from ../blood-established-2026-09-27/analyze_bes.py.
Usage: python3 analyze_st.py <full.ndjson> <results_raw.json> [bes_full.ndjson s2_full_merged.ndjson]"""
import json, sys, math, collections, datetime
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
RC_SRC = sys.argv[3:5] if len(sys.argv) >= 5 else None
JUDGE0 = 1789603200; DAY = 86400; SEED = 20260927
CFGS = ['C1', 'C2']; KFAM = {'primary': 270, 'low': 133, 'high': 690}

def Phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
def dstr(ts): return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%m-%d %H:%M')

def heavy(r):
    eP, basis = r['eP'], (r['g5px'] if r.get('g5px') is not None else r['xP'])
    cb = r['entryPx'] / eP - 1; cs = 1 - r['sellPx'] / basis if basis > 0 else 0
    cb2 = max(cb, 0.014) + (0.01 if r.get('ePons') else 0); cs2 = max(cs, 0.014) + (0.01 if r.get('xPons') else 0)
    v = 100 * (basis * (1 - cs2) / (eP * (1 + cb2)) - 1) - 0.2
    return min(v, 0.0) if r['fb'] else v
def unsell_a(r): s = r.get('sell'); return (not s) or (not s['s10h']) or (s['sbr'] is not None and s['sbr'] < 0.5)
def unsell_b(r): s = r.get('sell'); return (not s) or (s['ns'] < 2) or (s['sbr'] is not None and s['sbr'] < 0.5)
def unsell_c(r): return (r.get('nPostSell') or 0) == 0

S, Wt, SH, meta = {}, collections.defaultdict(lambda: collections.defaultdict(list)), collections.defaultdict(list), None
nofill, trunc, noscale = collections.Counter(), collections.Counter(), collections.Counter()
for ln in open(SRC):
    j = json.loads(ln)
    if '_meta' in j: meta = j['_meta']; continue
    half = 'JUDGE' if j['T'] >= JUDGE0 else 'FIT'; j['half'] = half
    key = (j['kind'], j.get('tw'), j['cell'], half)
    if j.get('noscale'): noscale[key + (j['clip'],)] += 1; continue
    if j.get('trunc'): trunc[key] += 1; continue
    if j.get('nofill'): nofill[key] += 1; continue
    j['fb'] = bool(j.get('fb')); j['on_uncapped'] = j['on']
    if j['fb']: j['on'] = min(j['on'], 0.0)
    j['heavy'] = heavy(j)
    j['s3a'] = -100.0 if unsell_a(j) else j['on']; j['s3b'] = -100.0 if unsell_b(j) else j['on']; j['s3c'] = -100.0 if unsell_c(j) else j['on']
    j['all'] = -100.0 if unsell_a(j) else j['heavy']                   # every stress at once: heavy costs + S3a
    j['day'] = (j['T'] // DAY) * DAY; j['v4e'] = j['eK'] == 'v4'
    if j['clip'] != 50: SH[(j['clip'], j['kind'])].append(j); continue
    if j['kind'] == 'S': S[j['pair']] = j
    else: Wt[j['tw']][j['pair']].append(j)

def paired(rows, W, view='on'):
    out = []
    for r in rows:
        ws = W.get(r['pair'], [])
        if not ws: continue
        tv = sum(w[view] for w in ws) / len(ws); out.append((r, r[view] - tv, tv))
    return out
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
    bb = block_boot(vals, days, 2, seed=seed)
    se = max(x for x in (se_iid, se_coin, se_day, bb['se']) if x is not None)
    cn = [m - 1.96 * se, m + 1.96 * se]; cb = [bb['lo'], bb['hi']]
    return dict(mean=m, se_iid=se_iid, se_coin=se_coin, se_day=se_day, se_block2d=bb['se'], se_cons=se,
                ci95=cn if cn[0] <= cb[0] else cb, p=1 - Phi(m / se) if se > 0 else None, mde80=2.487 * se, days=bb['D'])
R2 = lambda x: None if x is None else round(float(x), 2)
def summarize(pr, seed, view='on'):
    if len(pr) < 3: return {'n': len(pr)}
    d = [x[1] for x in pr]; raw = [x[0][view] for x in pr]; tw = [x[2] for x in pr]
    toks = [x[0]['tok'] for x in pr]; days = [x[0]['day'] for x in pr]
    Id = inference(d, toks, days, seed); Ir = inference(raw, toks, days, seed + 100)
    return dict(n=len(pr), coins=len(set(toks)), d_mean=R2(Id['mean']), d_median=R2(np.median(d)), ci95=[R2(x) for x in Id['ci95']],
                raw_mean=R2(Ir['mean']), median=R2(np.median(raw)), raw_ci95=[R2(x) for x in Ir['ci95']], drop5=R2(drop5(d)), raw_drop5=R2(drop5(raw)),
                twin_mean=R2(np.mean(tw)), win_share=R2(np.mean([v > 0 for v in raw])), tp_share=R2(np.mean([x[0]['reason'] == 'tp' for x in pr])),
                mde80=R2(Id['mde80']), se_iid=R2(Id['se_iid']), se_cons=R2(Id['se_cons']), se_block2d=R2(Id['se_block2d']),
                p_one_sided=None if Id['p'] is None else round(Id['p'], 6), raw_p_one_sided=None if Ir['p'] is None else round(Ir['p'], 4),
                v4_entry_rows=int(sum(x[0]['v4e'] for x in pr)), days=Id['days'])
def srows(cell, half, pred=None): return [r for r in S.values() if r['cell'] == cell and r['half'] == half and (pred is None or pred(r))]
def cell_sum(cell, half, tw='R', view='on', pred=None, seed=0):
    return summarize(paired(srows(cell, half, pred), Wt[tw], view), SEED + seed, view)

def crash_decomp(cell, half, tw):
    pr = paired(srows(cell, half), Wt[tw], 'on'); dc, dr = [], []
    for r, d, tv in pr:
        ws = Wt[tw][r['pair']]; sc = r['on'] if r['on'] <= -50 else 0.0; wc = sum(w['on'] for w in ws if w['on'] <= -50) / len(ws)
        dc.append(sc - wc); dr.append(d - (sc - wc))
    if not pr: return {}
    return dict(n=len(pr), d_mean=R2(np.mean([x[1] for x in pr])), from_crash_rows=R2(np.mean(dc)), from_rest=R2(np.mean(dr)),
                s_crash_share=R2(np.mean([r['on'] <= -50 for r, _, _ in pr])),
                twin_crash_share=R2(np.mean([w['on'] <= -50 for r, _, _ in pr for w in Wt[tw][r['pair']]])))
def shares(cell, half):
    o = {}
    for nm, rows in (('S', srows(cell, half)),) + tuple((f'W{t}', [w for v in Wt[t].values() for w in v if w['cell'] == cell and w['half'] == half]) for t in 'RAD'):
        if not rows: continue
        o[nm] = dict(n=len(rows), s3a_unsellable=R2(np.mean([unsell_a(r) for r in rows])), s3b_unsellable=R2(np.mean([unsell_b(r) for r in rows])),
                     s3c_unsellable=R2(np.mean([unsell_c(r) for r in rows])), sbr_lt_05=R2(np.mean([bool(r.get('sell') and r['sell']['sbr'] is not None and r['sell']['sbr'] < 0.5) for r in rows])),
                     no_sell10_1h=R2(np.mean([not (r.get('sell') and r['sell']['s10h']) for r in rows])),
                     crash_share=R2(np.mean([r['on'] <= -50 for r in rows])), raw_mean=R2(np.mean([r['on'] for r in rows])),
                     n10_median=R2(np.median([r['n10'] for r in rows if r.get('n10') is not None])) if rows else None,
                     v4_entry=R2(np.mean([r['eK'] == 'v4' for r in rows])), hot_share=R2(np.mean([r.get('hot') == 1 for r in rows])))
    return o
def clip_view(cfg, half='JUDGE'):
    cell = cfg + 'P'; out = {}
    for c in (200, 500):
        Ss = {r['pair']: r for r in SH[(c, 'S')] if r['cell'] == cell and r['half'] == half}
        Ws = collections.defaultdict(list)
        for r in SH[(c, 'W')]:
            if r['cell'] == cell and r['half'] == half and r.get('tw') == 'R': Ws[r['pair']].append(r)
        prc = paired(list(Ss.values()), Ws, 'on'); pr50 = paired([S[p] for p in Ss if p in S], {p: [w for w in Wt['R'][p] if w['eK'] == 'v4'] for p in Ss}, 'on')
        pr50 = [x for x in pr50 if x[0]['pair'] in {y[0]['pair'] for y in prc}]
        nos = noscale[('S', None, cell, half, c)]
        out[f'clip{c}'] = dict(**summarize(prc, SEED + c), no_depth_strategy=nos, same_pairs_at_50=summarize(pr50, SEED + c + 1) if len(pr50) >= 3 else {'n': len(pr50)},
                               heavy=summarize(paired(list(Ss.values()), Ws, 'heavy'), SEED + c + 2, 'heavy'))
    v4 = paired([r for r in srows(cell, half) if r['v4e']], Wt['R'], 'on')
    out['clip50_v4_entries'] = summarize(v4, SEED + 50)
    return out

def gate(cell, half='JUDGE'):
    o = {}
    for nm, kind, tw in (('S', 'S', None), ('WR', 'W', 'R'), ('WA', 'W', 'A'), ('WD', 'W', 'D')):
        rows = srows(cell, half) if kind == 'S' else [w for v in Wt[tw].values() for w in v if w['cell'] == cell and w['half'] == half]
        nf, tr = nofill[(kind, tw, cell, half)], trunc[(kind, tw, cell, half)]; tot = len(rows) + nf + tr
        small = sum(r['eU'] < 10 and r['eK'] != 'v4' for r in rows) + sum(r['xU'] < 10 and r['xK'] != 'v4' for r in rows)
        o[nm] = dict(draws=tot, booked=len(rows), nofill=nf, trunc=tr, fallback=sum(r['fb'] for r in rows),
                     priced_share=R2(sum(1 for r in rows if not r['fb']) / tot) if tot else None, g4_small_share=R2(small / (2 * len(rows))) if rows else None,
                     drains=sum(r['reason'] == 'drain' for r in rows), exit_gt20x=sum(r['xP'] > 20 * r['eP'] for r in rows),
                     g5=dict(collections.Counter(r['g5'] for r in rows if r['g5'])), g5_fail=sum(1 for r in rows if r['on'] > 1000 and r['g5'] not in ('depthok', 'corroborated')),
                     max_on=R2(max((r['on'] for r in rows), default=None)), exit_pool_differs=sum(r['xPk'] != r['ePk'] for r in rows),
                     v4_entry=R2(np.mean([r['eK'] == 'v4' for r in rows])) if rows else None)
    return o
def outl(cell, half='JUDGE', k=5):
    def desc(r): return dict(kind=r['kind'], tw=r.get('tw'), tok=r['tok'], pad=r['pad'], on=round(r['on'], 1), reason=r['reason'], entry=dstr(r['entryTs']), exit=dstr(r['exitTs']),
                             eK=r['eK'], ePool=r['ePk'], eU=r['eU'], xU=r['xU'], x_over_e=round(r['xP'] / r['eP'], 3), g5=r['g5'], eDepth1=r.get('eDepth1'), sell=r.get('sell'))
    s = sorted(srows(cell, half), key=lambda r: -r['on']); w = sorted([x for v in Wt['A'].values() for x in v if x['cell'] == cell and x['half'] == half], key=lambda r: -r['on'])
    return dict(strategy_best=[desc(r) for r in s[:k]], strategy_worst=[desc(r) for r in s[-k:]], twinA_best=[desc(r) for r in w[:k]], twinA_worst=[desc(r) for r in w[-k:]])

# ---- S5 Reality Check ----
def load_family():
    fam = {}
    def add(name, S_, W_):
        rows = []
        for p, r in S_.items():
            ws = W_.get(p)
            if ws: rows.append((r['tok'], (r['T'] // DAY) * DAY, r['on'] - sum(w['on'] for w in ws) / len(ws)))
        if len(rows) >= 30: fam[name] = rows
    for cell in ('C1M', 'C1P', 'C2M', 'C2P'):
        add('stress_' + cell, {p: r for p, r in S.items() if r['cell'] == cell and r['half'] == 'JUDGE'}, Wt['R'])
    if not RC_SRC: return fam
    for path, lab in ((RC_SRC[0], 'cell'), (RC_SRC[1], 'L')):
        Sx, Wx = collections.defaultdict(dict), collections.defaultdict(lambda: collections.defaultdict(list))
        for ln in open(path):
            j = json.loads(ln)
            if '_meta' in j or j.get('nofill') or j.get('trunc') or j.get('noscale') or 'on' not in j or j['T'] < JUDGE0: continue
            if j.get('clip', 50) != 50: continue
            on = min(j['on'], 0.0) if j.get('fb') else j['on']; j['on'] = on; c = str(j[lab])
            if j['kind'] == 'S': Sx[c][j['pair']] = j
            else: Wx[c][j['pair']].append(j)
        for c in Sx: add(('bes_' if lab == 'cell' else 's2_L') + c, Sx[c], Wx[c])
    return fam
def reality_check(fam, target, B=5000, seed=SEED):
    names = sorted(fam); tstat = {}
    days = sorted({d for n in names for _, d, _ in fam[n]}); coins = sorted({t for n in names for t, _, _ in fam[n]})
    di = {d: i for i, d in enumerate(days)}; ci = {t: i for i, t in enumerate(coins)}
    agg = {}
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
        res[nm] = dict(p=R2(float(np.mean(mx >= tstat[target]))) if target in tstat else None, max_null_p95=R2(float(np.percentile(mx, 95))))
    return dict(target=target, t_target=R2(tstat.get(target)), family=len(names), cells={n: dict(n=len(fam[n]), t=R2(tstat[n]), mean=R2(agg[n][0])) for n in names},
                best_cell=max(names, key=lambda n: tstat[n]), n_days=D, n_coins=C, **res)

# ---- evaluate ----
R = dict(test='Blood dip lead: stress test S1-S8', date='2026-09-27', prereg_sha256=open('PREREG.sha256').read().split()[0], records=[], by_config={})
fam = load_family()
def cl(s): return s.get('ci95', [None])[0] if isinstance(s, dict) else None
def score(s, kill=True):
    if not s or s.get('n', 0) < 30: return 'CANT_TELL_N'
    return 'PASS' if s['ci95'][0] > 0 else 'FAIL'
HELD = dict(C1='selection #2 "all": labelled launchpad coins, age >= 24 h, dip >= 20 % under the 1 h high, TP +30 %, hold 24 h, no cooldown',
            C2='blood-established 1 h: age >= 48 h, >= $10k 24 h volume, sd48 >= 3 %, trend arm A, dip >= 15 % under the 1 h high, TP +15 %, hold 48 h, 6 h cooldown')
for ci, cfg in enumerate(CFGS):
    P, M = cfg + 'P', cfg + 'M'; B = {}; s = 10 * ci
    def rec(check, definition, judge, fit=None, extra=None):
        r = dict(strategy='Blood', variable='stress_check', value=check, config=cfg, definition=definition,
                 held=dict(config=HELD[cfg], clip_usd=50, data='merged V2/V3 + V4 in ONE timestamp-merged stream (R-0109)', guard='fixed guard 6cdd676b', fixes='FIX a/b/c of blood-established',
                           sealed='nothing >= 2026-09-27T00:00Z read'), judge=judge, fit=fit, score=score(judge) if judge is not None else None)
        if extra: r.update(extra)
        R['records'].append(r); B[check] = r; return r
    rec('S0_replication', 'mode M (merged-series dip, entry any pool), vs random twin, base costs', cell_sum(M, 'JUDGE', seed=s + 1), cell_sum(M, 'FIT', seed=s + 2))
    rec('S1_one_pool', 'mode P: dip on the main pool vs that pool\'s own 1 h high, entry on that pool; vs random twin', cell_sum(P, 'JUDGE', seed=s + 3), cell_sum(P, 'FIT', seed=s + 4))
    rec('S2_heavy_costs', 'mode P; every side max(modelled, 1.4 %) + 1 % on Pons-hook pools; vs random', cell_sum(P, 'JUDGE', view='heavy', seed=s + 5), cell_sum(P, 'FIT', view='heavy', seed=s + 6))
    rec('S3a_sellability', 'mode P; entry with no >= $10 sell on the entry pool in the prior hour, or median sell/buy < 0.5, booked -100 % (strategy and twins)',
        cell_sum(P, 'JUDGE', view='s3a', seed=s + 7), cell_sum(P, 'FIT', view='s3a', seed=s + 8), dict(shares_judge=shares(P, 'JUDGE'), shares_fit=shares(P, 'FIT')))
    rec('S3b_sellability_view', 'view: fewer than 2 sell prints in the prior hour (the dip alone does not count), or sell/buy < 0.5 -> -100 %', cell_sum(P, 'JUDGE', view='s3b', seed=s + 9), cell_sum(P, 'FIT', view='s3b', seed=s + 10))
    rec('S3c_sellability_expost', 'view: nobody sold on the entry pool between our fill and our exit -> -100 %', cell_sum(P, 'JUDGE', view='s3c', seed=s + 11), cell_sum(P, 'FIT', view='s3c', seed=s + 12))
    rec('S4_vs_activity_twin', 'mode P; twin = same $10+-trade-count band and main-pool depth band, no dip', cell_sum(P, 'JUDGE', 'A', seed=s + 13), cell_sum(P, 'FIT', 'A', seed=s + 14),
        dict(crash_decomp_judge={t: crash_decomp(P, 'JUDGE', t) for t in 'RAD'}, crash_decomp_fit={t: crash_decomp(P, 'FIT', t) for t in 'RAD'},
             modeM_judge=cell_sum(M, 'JUDGE', 'A', seed=s + 15)))
    rec('S4_vs_down_twin', 'mode P; twin = fell >= dip over 6 h (> -60 %), no dip now', cell_sum(P, 'JUDGE', 'D', seed=s + 16), cell_sum(P, 'FIT', 'D', seed=s + 17),
        dict(modeM_judge=cell_sum(M, 'JUDGE', 'D', seed=s + 18)))
    def a_vs_r(half, sd):
        rows = [dict(r, on=sum(w['on'] for w in Wt['A'][r['pair']]) / len(Wt['A'][r['pair']])) for r in srows(P, half) if Wt['A'].get(r['pair']) and Wt['R'].get(r['pair'])]
        return summarize(paired(rows, Wt['R'], 'on'), SEED + sd)
    rec('S4_activity_twin_vs_random', 'activity twin minus random twin on the same signals (is activity alone the gap?)', a_vs_r('JUDGE', s + 19), a_vs_r('FIT', s + 26))
    bonf = {k: dict(K=K, alpha=0.05 / K, p=B['S1_one_pool']['judge'].get('p_one_sided'), passes=(B['S1_one_pool']['judge'].get('p_one_sided') or 1) < 0.05 / K) for k, K in KFAM.items()}
    rc = reality_check(fam, 'stress_' + P) if fam else None
    rec('S5_best_of_many', 'Bonferroni (= Holm step 1) over the stated family; White Reality Check over the reconstructable family', B['S1_one_pool']['judge'], None,
        dict(bonferroni=bonf, reality_check=rc, score=('PASS' if bonf['primary']['passes'] and rc and rc['day_block2']['p'] is not None and rc['day_block2']['p'] < 0.05 and rc['coins']['p'] < 0.05 else 'FAIL')))
    rec('S6_hot', 'mode P vs random, signal coin HOT (6 h hourly volume > prior 24 h hourly volume)', cell_sum(P, 'JUDGE', pred=lambda r: r.get('sigHot') == 1, seed=s + 20), cell_sum(P, 'FIT', pred=lambda r: r.get('sigHot') == 1, seed=s + 21))
    rec('S6_not_hot', 'mode P vs random, signal coin NOT hot', cell_sum(P, 'JUDGE', pred=lambda r: r.get('sigHot') == 0, seed=s + 22), cell_sum(P, 'FIT', pred=lambda r: r.get('sigHot') == 0, seed=s + 23),
        dict(pad_hot=cell_sum(P, 'JUDGE', pred=lambda r: r.get('sigPadHot') == 1, seed=s + 24), pad_not_hot=cell_sum(P, 'JUDGE', pred=lambda r: r.get('sigPadHot') == 0, seed=s + 25)))
    cv = clip_view(cfg)
    rec('S7_clip200', 'mode P, V4 entries, $200 clip (same entry print/pool; depth allows u <= 0.10), vs random $200 shadows', cv['clip200'], None, dict(clips=cv))
    rec('S7_clip500', 'as S7 at $500', cv['clip500'], None)
    for half in ('JUDGE', 'FIT'):
        for mode in ('M', 'P'):
            for k, pred in (('v4', lambda r: r['v4e']), ('v23', lambda r: not r['v4e'])):
                rec(f'S8_{mode}_{half}_{k}', f'mode {mode}, {half}, strategy entry venue {k}, vs random', cell_sum(cfg + mode, half, pred=pred, seed=s + 30 + len(B)))
    rec('ALL_stresses', 'mode P, heavy costs + S3a, vs ACTIVITY twin (every stress at once)', cell_sum(P, 'JUDGE', 'A', view='all', seed=s + 90), cell_sum(P, 'FIT', 'A', view='all', seed=s + 91))
    # survival rule (PREREG §6)
    sv = dict(S1=score(B['S1_one_pool']['judge']), S2=score(B['S2_heavy_costs']['judge']), S3=score(B['S3a_sellability']['judge']), S4=score(B['S4_vs_activity_twin']['judge']),
              S5=B['S5_best_of_many']['score'], S6=score(B['S6_not_hot']['judge']), S7=score(B['S7_clip200']['judge']))
    j8 = B['S8_P_JUDGE_v4']['judge']; v23 = B['S8_P_JUDGE_v23']['judge']; fitP = B['S1_one_pool']['fit']
    v4only = bool(j8.get('d_mean') and j8['d_mean'] > 0 and (v23.get('n', 0) < 3 or v23['ci95'][0] <= 0) and (fitP.get('n', 0) < 3 or fitP['ci95'][0] <= 0))
    cdR = B['S4_vs_activity_twin']['crash_decomp_judge'].get('R', {})
    dR, dA = B['S1_one_pool']['judge'].get('d_mean'), B['S4_vs_activity_twin']['judge']
    cls = ('dip effect' if score(dA) == 'PASS' else 'activity / crash-avoidance effect (not the dip)' if dR and dR > 0 else 'no effect')
    crash = bool(cdR and cdR.get('d_mean') and cdR['d_mean'] > 0 and cdR['from_crash_rows'] >= (2 / 3) * cdR['d_mean'])
    R['by_config'][cfg] = dict(survival=sv, survives=all(v == 'PASS' for v in sv.values()), v4_only_flag=v4only, classification=cls, crash_avoidance_specifically=crash,
                               gate_judge_P=gate(P), gate_judge_M=gate(M), outliers_judge_P=outl(P))
R['meta'] = {k: meta[k] for k in ('rows', 'rowsV4', 'v4skipLiq0', 'univRows', 'bad', 'badV4', 'exits', 'trunc', 'end', 'holes', 'holeAt', 'nofill', 'mergedOutOfOrder', 'v4OutOfOrder',
                                  'reorder', 'trig', 'twinEmpty', 'matchLvl', 'crossPoolDip', 'eligSrc', 'fixA', 'fixB', 'fixC', 'shadow', 'feeSrc', 'g5', 'wide0', 'sec', 'peakRssMB', 'drop', 'assess')}
R['meta']['v23Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v23Files'].items()}
R['meta']['v4Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v4Files'].items()}
json.dump(R, open(OUT, 'w'), indent=1, default=float)
for cfg in CFGS:
    print(cfg, json.dumps(R['by_config'][cfg]['survival']), R['by_config'][cfg]['classification'], 'v4only', R['by_config'][cfg]['v4_only_flag'], 'crash', R['by_config'][cfg]['crash_avoidance_specifically'])
for r in R['records']:
    j = r['judge'] or {}; f = r['fit'] or {}
    print(f"{r['config']} {r['value']:<26} J n {j.get('n')} d {j.get('d_mean')} ci {j.get('ci95')} raw {j.get('raw_mean')} tw {j.get('twin_mean')} p {j.get('p_one_sided')} | F n {f.get('n')} d {f.get('d_mean')} ci {f.get('ci95')} raw {f.get('raw_mean')}")
