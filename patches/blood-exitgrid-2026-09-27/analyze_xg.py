#!/usr/bin/env python3
"""analyze_xg.py — BLOOD C2P EXIT GRID, per PREREG.md (sha256 in PREREG.sha256).
SE / block bootstrap / CI rule / Reality Check copied VERBATIM from ../blood-stress-2026-09-27/analyze_st.py.
Usage: python3 analyze_xg.py <full.ndjson> <results.json>"""
import json, sys, math, collections, datetime
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
JUDGE0 = 1789603200; DAY = 86400; SEED = 20260927
TPS = [8, 10, 15, 20, 30, 50]; HOLDS = [6, 12, 24, 48]; STOPX = 'tp15_h48_s30'; BASEX = 'tp15_h48'
CELLS = [f'tp{t}_h{h}' for t in TPS for h in HOLDS] + [STOPX]
FITCUT = (0.0615136, 0.252308); JCUT = (0.0241398, 0.0508785)
K_PRIMARY, K_SENS = 494, 367

def Phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
def dstr(ts): return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
def heavy(r):
    eP, basis = r['eP'], (r['g5px'] if r.get('g5px') is not None else r['xP'])
    cb = r['entryPx'] / eP - 1; cs = 1 - r['sellPx'] / basis if basis > 0 else 0
    cb2 = max(cb, 0.014) + (0.01 if r.get('ePons') else 0); cs2 = max(cs, 0.014) + (0.01 if r.get('xPons') else 0)
    v = 100 * (basis * (1 - cs2) / (eP * (1 + cb2)) - 1) - 0.2
    return min(v, 0.0) if r['fb'] else v
def unsell_a(r): s = r.get('sell'); return (not s) or (not s['s10h']) or (s['sbr'] is not None and s['sbr'] < 0.5)
R2 = lambda x: None if x is None else round(float(x), 2)
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
def drop5(v): v = sorted(v); return float(np.mean(v[:-5])) if len(v) > 5 else None
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

# ---- load: one row per position with 25 exit overlays -> one flat record per (position, exit) ----
S = {x: {} for x in CELLS}; Wt = {x: {'R': collections.defaultdict(list), 'A': collections.defaultdict(list)} for x in CELLS}
nofill, trunc, skipd = collections.Counter(), collections.Counter(), collections.Counter(); meta = None; draws = collections.Counter()
ENTRY_KEYS = None
for ln in open(SRC):
    j = json.loads(ln)
    if '_meta' in j: meta = j['_meta']; continue
    half = 'JUDGE' if j['T'] >= JUDGE0 else 'FIT'; key = (j['kind'], j.get('tw'), half)
    draws[key] += 1
    if j.get('trunc'): trunc[key] += 1; continue
    if j.get('nofill'): nofill[key] += 1; continue
    if j.get('skipDepth'): skipd[key] += 1; continue
    xs = j.pop('x'); j['half'] = half; j['day'] = (j['T'] // DAY) * DAY; j['v4e'] = j['eK'] == 'v4'
    d = j.get('eDepth1')
    j['band_fit'] = 'v23' if d is None else 'low' if d <= FITCUT[0] else 'mid' if d <= FITCUT[1] else 'high'
    j['band_j'] = 'v23' if d is None else 'j_low' if d <= JCUT[0] else 'j_mid' if d <= JCUT[1] else 'j_high'
    for x in CELLS:
        r = dict(j); r.update(xs[x]); r['x'] = x
        r['fb'] = bool(r.get('fb')); r['on_uncapped'] = r['on']
        if r['fb']: r['on'] = min(r['on'], 0.0)
        r['heavy'] = heavy(r); r['all'] = -100.0 if unsell_a(r) else r['heavy']
        if j['kind'] == 'S': S[x][j['pair']] = r
        else: Wt[x][j['tw']][j['pair']].append(r)

def paired(rows, W, view):
    out = []
    for r in rows:
        ws = W.get(r['pair'], [])
        if ws: tv = sum(w[view] for w in ws) / len(ws); out.append((r, r[view] - tv, tv))
    return out
def money(rows, seed, view='heavy'):
    if len(rows) < 3: return {'n': len(rows)}
    v = [r[view] for r in rows]; I = inference(v, [r['tok'] for r in rows], [r['day'] for r in rows], seed)
    return dict(n=len(rows), coins=len({r['tok'] for r in rows}), raw_mean=R2(I['mean']), raw_ci95=[R2(c) for c in I['ci95']], median=R2(np.median(v)),
                raw_p_one_sided=None if I['p'] is None else float('%.3g' % I['p']), se_cons=R2(I['se_cons']), se_iid=R2(I['se_iid']), mde80=R2(I['mde80']),
                drop5=R2(drop5(v)), win_share=R2(np.mean([a > 0 for a in v])), tp_share=R2(np.mean([r['reason'] == 'tp' for r in rows])),
                stop_share=R2(np.mean([r['reason'] == 'stop' for r in rows])), crash_share=R2(np.mean([a <= -50 for a in v])),
                drain_share=R2(np.mean([r['reason'] == 'drain' for r in rows])), days=I['days'])
def dsum(rows, W, seed, view='heavy'):
    pr = paired(rows, W, view)
    if len(pr) < 3: return {'n': len(pr)}
    d = [x[1] for x in pr]; I = inference(d, [x[0]['tok'] for x in pr], [x[0]['day'] for x in pr], seed)
    return dict(n=len(pr), d_mean=R2(I['mean']), ci95=[R2(c) for c in I['ci95']], p_one_sided=None if I['p'] is None else float('%.3g' % I['p']),
                drop5=R2(drop5(d)), twin_mean=R2(np.mean([x[2] for x in pr])), strat_mean_same_pairs=R2(np.mean([x[0][view] for x in pr])),
                twin_crash_share=R2(np.mean([w[view] <= -50 for x in pr for w in W[x[0]['pair']]])), twin_tp_share=R2(np.mean([w['reason'] == 'tp' for x in pr for w in W[x[0]['pair']]])))
def sel(x, half, pred=None): return [r for r in S[x].values() if r['half'] == half and (pred is None or pred(r))]
def score(m):
    if m.get('n', 0) < 30: return 'CANT_TELL_N'
    if m['raw_ci95'][0] > 0: return 'CI_ABOVE_0'
    return 'CI_COVERS_0' if m['raw_ci95'][1] >= 0 else 'LOSES'
BANDS = [('all', None, None), ('low', 'band_fit', 'FIT'), ('mid', 'band_fit', 'FIT'), ('high', 'band_fit', 'FIT'),
         ('j_low', 'band_j', 'JUDGE'), ('j_mid', 'band_j', 'JUDGE'), ('j_high', 'band_j', 'JUDGE'), ('v23', 'band_fit', None)]
HELD = ('C2P frozen final-exam rule (blood-stress report.txt §7): established coins (age >= 48 h, >= $10k 24 h volume, sd48 >= 3 %), trend '
        'flat/up, 15 % dip on the MAIN pool under that pool\'s 1 h high, $50, entry 60 s later on that pool, exit on the entry pool only, '
        'V4 depth1 < 0.001 ETH entries skipped; entry set / held / 6 h cooldown driven by tp15_h48; twins take the SAME exit')
R = dict(test='Blood C2P exit grid', date='2026-09-27', prereg_sha256=open('PREREG.sha256').read().split()[0], records=[], cells={})
seed = 0
for ci, x in enumerate(CELLS):
    tp = 15 if x == STOPX else int(x.split('_')[0][2:]); h = 48 if x == STOPX else int(x.split('_h')[1])
    R['cells'][x] = {}
    for b, fld, cut in BANDS:
        pred = None if fld is None else (lambda r, fld=fld, b=b: r[fld] == b)
        J, F = sel(x, 'JUDGE', pred), sel(x, 'FIT', pred); seed += 10
        judge = money(J, SEED + seed); judge['vs_activity_twin'] = dsum(J, Wt[x]['A'], SEED + seed + 1)
        judge['vs_random_twin'] = dsum(J, Wt[x]['R'], SEED + seed + 2); judge['base_cost'] = money(J, SEED + seed + 3, 'on')
        fit = money(F, SEED + seed + 4); fit['vs_activity_twin'] = dsum(F, Wt[x]['A'], SEED + seed + 5)
        rec = dict(strategy='Blood', variable='exit_grid', value=x, config='C2P', take_profit=tp, max_hold_h=h, stop=(-30 if x == STOPX else None),
                   depth_band=b, depth_cut=cut, side_view=(x == STOPX),
                   definition=f'C2P entries; exit TP +{tp} % / max hold {h} h' + (' / stop -30 %' if x == STOPX else ', no stop') +
                   ('' if b == 'all' else f'; strategy entry-pool depth band {b}' + (f' (cuts from {cut})' if cut else ' (V2/V3 entry, no depth measure)')) +
                   '; HEAVY cost (max(modelled,1.4 %)/side + 1 % Pons, gas 0.2); primary = raw mean per trade',
                   held=dict(config=HELD, clip_usd=50, data='merged V2/V3 + V4, one timestamp-merged stream', guard='fixed guard 6cdd676b',
                             sealed='nothing >= 2026-09-27T00:00Z read'), judge=judge, fit=fit, score=score(judge))
        R['records'].append(rec); R['cells'][x][b] = rec
# ---- G12: Bonferroni + White Reality Check ----
GRID = [x for x in CELLS if x != STOPX]
for rec in R['records']:
    p = rec['judge'].get('raw_p_one_sided'); pd = rec['judge'].get('vs_activity_twin', {}).get('p_one_sided')
    rec['bonferroni'] = dict(K=K_PRIMARY, alpha=0.05 / K_PRIMARY, raw_passes=bool(p is not None and p < 0.05 / K_PRIMARY),
                             raw_passes_K367=bool(p is not None and p < 0.05 / K_SENS), d_activity_passes=bool(pd is not None and pd < 0.05 / K_PRIMARY))
def famrows(view, bands, dview=False):
    fam, dropped = {}, []
    for x in CELLS:
        for b in bands:
            if x == STOPX and b != 'all': continue
            rows = [r for r in S[x].values() if r['half'] == 'JUDGE' and (b == 'all' or r['band_fit'] == b or r['band_j'] == b)]
            if dview: v = [(r['tok'], r['day'], d) for r, d, _ in paired(rows, Wt[x]['A'], view)]
            else: v = [(r['tok'], r['day'], r[view]) for r in rows]
            if len(v) >= 30: fam[f'{x}|{b}'] = v
            else: dropped.append(f'{x}|{b} (n {len(v)})')
    return fam, dropped
def rc(view, bands, dview=False):
    fam, dropped = famrows(view, bands, dview)
    t = {n: np.mean([a[2] for a in v]) / (np.std([a[2] for a in v], ddof=1) / math.sqrt(len(v))) for n, v in fam.items()}
    best = max(t, key=t.get); out = reality_check(fam, best); out['dropped_n_lt_30'] = dropped
    out['cells'] = dict(sorted(out['cells'].items(), key=lambda kv: -kv[1]['t'])[:8])          # top 8 only, to keep the file readable
    return out
R['reality_check'] = dict(
    money_brief_family=rc('heavy', ['all', 'low', 'mid', 'high']),
    d_activity_brief_family=rc('heavy', ['all', 'low', 'mid', 'high'], dview=True),
    money_with_judge_terciles=rc('heavy', ['all', 'low', 'mid', 'high', 'j_low', 'j_mid', 'j_high']))
# ---- G6 smoothness (pooled JUDGE raw heavy) ----
def cellv(x): return {p: r['heavy'] for p, r in S[x].items() if r['half'] == 'JUDGE'}
V = {x: cellv(x) for x in GRID}; flags = []
for ti, t in enumerate(TPS):
    for hi, h in enumerate(HOLDS):
        x = f'tp{t}_h{h}'
        for axis, nb in (('TP', [f'tp{TPS[k]}_h{h}' for k in (ti - 1, ti + 1) if 0 <= k < len(TPS)]), ('hold', [f'tp{t}_h{HOLDS[k]}' for k in (hi - 1, hi + 1) if 0 <= k < len(HOLDS)])):
            ps = [p for p in V[x] if all(p in V[n] for n in nb)]
            dif = np.array([V[x][p] - np.mean([V[n][p] for n in nb]) for p in ps]); m = dif.mean(); se = dif.std(ddof=1) / math.sqrt(len(dif))
            if abs(m) > 3 and abs(m) > 3 * se: flags.append(dict(cell=x, axis=axis, neighbours=nb, diff=R2(m), paired_se=R2(se)))
R['g6_smoothness'] = dict(rule='cell vs mean of its axis neighbours: |diff| > 3 pts AND > 3 paired SE', flags=flags,
                          grid_raw_heavy={x: R['cells'][x]['all']['judge'].get('raw_mean') for x in GRID})
# ---- R-0068 check: TP exits booked at the actual print 60 s after the trigger, vs the line ----
r68 = {}
for x in GRID:
    tp = int(x.split('_')[0][2:]) / 100 + 1; rows = sel(x, 'JUDGE'); t = [r for r in rows if r['reason'] == 'tp']
    if not t: continue
    val = [(r['xP'] / (1 + r['xw']) if r['xK'] == 'v4' and r['xw'] is not None else r['xP']) / r['entryPx'] for r in t]
    gap = [100 * (v - tp) for v in val]; share_tp = len(t) / len(rows)
    r68[x] = dict(tp_exits=len(t), below_line_share=R2(np.mean([v < tp for v in val])), mean_gap_pts=R2(np.mean(gap)), median_gap_pts=R2(np.median(gap)),
                  worst_gap_pts=R2(min(gap)), line_booking_would_shift_cell_mean_by=R2(-np.mean(gap) * share_tp))
R['r0068_check'] = r68
# ---- overlap (fixed entry set) ----
ov = {}
by = collections.defaultdict(list)
for r in S[BASEX].values(): by[r['tok']].append(r['entryTs'])
for x in CELLS:
    n = o = 0
    for r in S[x].values():
        if r['half'] != 'JUDGE': continue
        n += 1; nxt = [e for e in by[r['tok']] if e > r['entryTs']]
        if nxt and r['exitTs'] > min(nxt): o += 1
    ov[x] = R2(o / n) if n else None
R['overlap_share_judge'] = ov
# ---- best 5 pooled cells: depth split, hot/not-hot, Pons split, per day, heavy+S3a ----
best5 = sorted(GRID, key=lambda x: -(R['cells'][x]['all']['judge'].get('raw_mean') or -1e9))[:5]
bx = {}
for i, x in enumerate(best5):
    J = sel(x, 'JUDGE'); s0 = SEED + 90000 + 100 * i
    bx[x] = dict(depth={b: {k: R['cells'][x][b]['judge'].get(k) for k in ('n', 'raw_mean', 'raw_ci95', 'tp_share', 'crash_share')} |
                        {'d_activity': R['cells'][x][b]['judge']['vs_activity_twin'].get('d_mean'), 'd_activity_ci95': R['cells'][x][b]['judge']['vs_activity_twin'].get('ci95')}
                        for b, _, _ in BANDS if b != 'all'},
                 hot=money([r for r in J if r.get('sigHot') == 1], s0 + 1), not_hot=money([r for r in J if r.get('sigHot') == 0], s0 + 2),
                 pons=money([r for r in J if r.get('pad') == 'Pons'], s0 + 3), non_pons=money([r for r in J if r.get('pad') != 'Pons'], s0 + 4),
                 heavy_plus_s3a=money(J, s0 + 5, 'all'),
                 per_day={dstr(d)[:5]: R2(np.mean([r['heavy'] for r in J if r['day'] == d])) for d in sorted({r['day'] for r in J})},
                 top5_trades=[dict(tok=r['tok'][:10], pad=r['pad'], heavy=R2(r['heavy']), reason=r['reason'], entry=dstr(r['entryTs']), eK=r['eK'], eDepth1=r.get('eDepth1'))
                              for r in sorted(J, key=lambda r: -r['heavy'])[:5]])
R['best5'] = dict(cells=best5, detail=bx)
# ---- DATA GATE ----
def gate():
    o = {}
    for nm, kind, tw in (('S', 'S', None), ('WR', 'W', 'R'), ('WA', 'W', 'A')):
        rowsB = sel(BASEX, 'JUDGE') if kind == 'S' else [w for v in Wt[BASEX][tw].values() for w in v if w['half'] == 'JUDGE']
        k = (kind, tw, 'JUDGE'); tot = draws[k]
        ex = {}
        for x in CELLS:
            rows = sel(x, 'JUDGE') if kind == 'S' else [w for v in Wt[x][tw].values() for w in v if w['half'] == 'JUDGE']
            ex[x] = dict(fallback=sum(r['fb'] for r in rows), small_exit_share=R2(np.mean([r['xU'] < 10 and r['xK'] != 'v4' for r in rows])),
                         exit_gt20x=sum(r['xP'] > 20 * r['eP'] for r in rows), max_on=R2(max(r['on'] for r in rows)), drains=sum(r['reason'] == 'drain' for r in rows),
                         g5=dict(collections.Counter(r['g5'] for r in rows if r['g5'])), exit_pool_differs=sum(r['xPk'] != r['ePk'] for r in rows))
        o[nm] = dict(draws=tot, booked=len(rowsB), nofill=nofill[k], trunc=trunc[k], skip_depth=skipd[k],
                     priced_share_base=R2(sum(1 for r in rowsB if not r['fb']) / tot) if tot else None,
                     small_entry_share=R2(np.mean([r['eU'] < 10 and r['eK'] != 'v4' for r in rowsB])) if rowsB else None,
                     v4_entry=R2(np.mean([r['eK'] == 'v4' for r in rowsB])) if rowsB else None,
                     s3a_unsellable=R2(np.mean([unsell_a(r) for r in rowsB])) if rowsB else None,
                     s3c_no_seller_after_fill_base=R2(np.mean([(r.get('nPostSell') or 0) == 0 for r in rowsB])) if rowsB else None,
                     by_exit=ex)
    fitS = sel(BASEX, 'FIT')
    o['G8'] = dict(fit_n=len(fitS), judge_n=len(sel(BASEX, 'JUDGE')), fit_v4_share=R2(np.mean([r['v4e'] for r in fitS])),
                   judge_v4_share=R2(np.mean([r['v4e'] for r in sel(BASEX, 'JUDGE')])),
                   judge_band_counts_fitcut=dict(collections.Counter(r['band_fit'] for r in sel(BASEX, 'JUDGE'))),
                   judge_band_counts_jcut=dict(collections.Counter(r['band_j'] for r in sel(BASEX, 'JUDGE'))))
    return o
R['gate'] = gate()
R['meta'] = {k: meta.get(k) for k in ('rows', 'rowsV4', 'v4skipLiq0', 'univRows', 'bad', 'badV4', 'exits', 'trunc', 'end', 'holes', 'holeAt', 'nofill', 'mergedOutOfOrder',
                                      'v4OutOfOrder', 'reorder', 'trig', 'twinEmpty', 'matchLvl', 'crossPoolDip', 'fixA', 'fixB', 'fixC', 'feeSrc', 'wide0', 'sec', 'peakRssMB', 'skipDepth', 'endTs')}
R['meta']['v23Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v23Files'].items()}
R['meta']['v4Files'] = {d: dict(n=v['n'], first=dstr(v['first']), last=dstr(v['last'])) for d, v in meta['v4Files'].items()}
json.dump(R, open(OUT, 'w'), indent=1, default=float)
# ---- print ----
print('cell         n   raw_heavy  CI            p        TP%  crash%  | dA    CI           nA   | dR    | base  | FIT raw  n')
for x in CELLS:
    j = R['cells'][x]['all']['judge']; a = j['vs_activity_twin']; rr = j['vs_random_twin']; f = R['cells'][x]['all']['fit']
    print(f"{x:13s} {j['n']:4d} {j['raw_mean']:+6.2f} {str(j['raw_ci95']):16s} {j['raw_p_one_sided']:<8} {j['tp_share']:.2f} {j['crash_share']:.2f} | {a['d_mean']:+5.1f} {str(a['ci95']):14s} {a['n']:4d} | {rr['d_mean']:+5.1f} | {j['base_cost']['raw_mean']:+5.1f} | {f['raw_mean']:+5.1f} {f['n']}")
print('BANDS (raw heavy mean, n):')
for x in CELLS:
    print(x, ' '.join(f"{b}:{R['cells'][x][b]['judge'].get('raw_mean')}/{R['cells'][x][b]['judge'].get('n')}" for b, _, _ in BANDS[1:]))
print('best5', best5); print('RC', json.dumps({k: {kk: v[kk] for kk in ('best_cell', 't_target', 'family', 'day_block2', 'coins')} for k, v in R['reality_check'].items()}))
print('G6 flags', flags); print('R0068', json.dumps(r68)); print('overlap', ov)
print('CI>0 cells:', [(r['value'], r['depth_band'], r['judge']['n'], r['judge']['raw_mean'], r['judge']['raw_ci95'], r['bonferroni']['raw_passes']) for r in R['records'] if r['score'] == 'CI_ABOVE_0'])
