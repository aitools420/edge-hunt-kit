#!/usr/bin/env python3
"""analyze_v1.py - EDGE MACHINE v1, stage B: reduced pickles -> <outdir>/results.json (ONE schema) + <outdir>/trades.ndjson.gz (per trade).
Statistics are the hunts' own, exec'd VERBATIM (never re-implemented): inference() / drop5() from ../../blood-realcost-2026-09-27/recost.py
(-> ../../blood-exitgrid-2026-09-27/analyze_xg.py): mean, SE_cons = max(iid, coin-cluster, T-day-cluster, 2-day block bootstrap B 10,000),
95 % range = the more conservative of the bootstrap and mean +/- 1.96 SE_cons. raw_block / d_block / drop_coins = analyze_h2.py's.
Seeds as analyze_h2.py: cell seed (+50 for FIT) + 10 x view index + 1 (raw) / 2 (d vs activity twin) / 3 (d vs random twin); the cell seed is
cells.json `stat_seed` or, by default, derived from the cell id (batch-independent).
PRIMARY view = real60h (the v1 cost model). The no-hop view real60 is reported beside it (every trade kept; hunt 3 published that view).
A filtered cell (cells.json `filter`) = its base's trades whose signal passes the filter, twins following their signal.
Usage: analyze_v1.py <outdir>"""
import json, sys, os, gzip, glob, pickle, collections, math, datetime
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'
O = sys.argv[1]
src = open(P + '/blood-realcost-2026-09-27/recost.py').read()
head = src[:src.index('# ------------------------------------------------------------------ loaders')]
head = head.replace("open('pool_costs.json')", f"open('{O}/pool_costs.json')").replace("IDENT = json.load(open('identity.json'))", "IDENT = {}")
g = {'__name__': 'rc'}; exec(head, g)
inference, drop5, R2 = g['inference'], g['drop5'], g['R2']
VIEWS = ('meas', 'meas_trig', 'heavy', 'real60', 'realtrig', 'lat', 'lat90', 'real60h', 'realtrigh', 'lath', 'lat90h', 'real60u'); VI = {v: i for i, v in enumerate(VIEWS)}
PRIMARY, NOHOP = 'real60h', 'real60'
MAN = json.load(open(HERE + '/MANIFEST.json'))
ENGINE_SHA, COST_V = MAN['engine_sha256'], MAN['cost_version']
CM = json.load(open(O + '/cellmap.json'))
S, GATE, META = {}, collections.defaultdict(collections.Counter), []
for pk in sorted(glob.glob(O + '/p[0-9][0-9].pkl')):
    d = pickle.load(open(pk, 'rb')); assert tuple(d['views']) == VIEWS
    for c, col in d['S'].items():
        assert c not in S, 'engine cell in two passes: ' + c
        S[c] = col
    for k, v in d['gate'].items(): GATE[k].update(v)
    META.append(dict(pass_=os.path.basename(pk)[:-4], missing_pools=len(d['missing_pools']),
                     **{k: (d['meta'] or {}).get(k) for k in ('engine', 'rows', 'rowsV4', 'exits', 'trunc', 'holes', 'sec', 'peakRssMB', 'endTs', 'peakHeld', 'capSkip', 'quoteSkip')}))
# ---- analyze_h2.py blocks (COPY) ----
def summ(vals, toks, days, seed):
    if len(vals) < 3: return {'n': len(vals)}
    I = inference(list(vals), list(toks), list(days), seed)
    return dict(n=len(vals), coins=len(set(toks)), mean=R2(I['mean']), median=R2(np.median(vals)), ci95=[R2(x) for x in I['ci95']], se_cons=R2(I['se_cons']),
                se_iid=R2(I['se_iid']), p_one_sided=None if I['p'] is None else float(f"{I['p']:.3g}"), mde80=R2(I['mde80']), upper95=R2(I['mean'] + 1.645 * I['se_cons']),
                drop5_trades=R2(drop5(list(vals))), days=I['days'])
def drop_coins(vals, toks, k=5):
    by = collections.defaultdict(float)
    for x, t in zip(vals, toks): by[t] += x
    top = set(sorted(by, key=lambda t: -by[t])[:k]); keep = [x for x, t in zip(vals, toks) if t not in top]
    return R2(np.mean(keep)) if keep else None
def raw_block(col, ix, vw, seed):
    ix = ix[~np.isnan(col['v'][ix, VI[vw]])]                                       # V1: a hop view skips no-route trades (= reduce_h2's exclusion)
    v = col['v'][ix, VI[vw]]; toks = [col['tok'][i] for i in ix]; days = col['day'][ix]
    s = summ(v, toks, days, seed)
    if len(ix) >= 3:
        s['drop5_coins'] = drop_coins(v, toks); s['crash_share'] = R2(np.mean(v <= -50)); s['win_share'] = R2(np.mean(v > 0))
        s['u_raw'] = R2((s['ci95'][1] - s['ci95'][0]) / 2); s['lower_explorer'] = R2(s['mean'] - (s['ci95'][1] - s['ci95'][0]) / 2)
        s['lower'] = s['ci95'][0]
    return s
def d_block(col, ix, vw, tw, seed):
    ix = ix[~np.isnan(col['v'][ix, VI[vw]])]
    t = col['t' + tw][ix, VI[vw]]; ok = ~np.isnan(t)
    jx = ix[ok]; d = col['v'][jx, VI[vw]] - col['t' + tw][jx, VI[vw]]
    if len(jx) < 3: return {'n': int(len(jx))}
    toks = [col['tok'][i] for i in jx]; s = summ(d, toks, col['day'][jx], seed)
    s['d_mean'] = s.pop('mean'); s['d_median'] = s.pop('median'); s['drop5_coins'] = drop_coins(d, toks)
    s['twin_mean'] = R2(np.mean(col['t' + tw][jx, VI[vw]])); s['twin_tp_share'] = R2(np.nanmean(col['tp' + tw][jx]))
    return s
def gate(ec, half):
    o = {}
    for w in ('S', 'WR', 'WA'):
        G = GATE.get(f'{ec}|{half}|{w}', {}); booked = G.get('booked', 0); tot = booked + G.get('nofill', 0) + G.get('trunc', 0)
        o[w] = dict(draws=tot, booked=booked, nofill=G.get('nofill', 0), trunc=G.get('trunc', 0), skip_depth_floor=G.get('skip_depth_floor', 0),
                    fallback_exit=G.get('fallback_exit', 0), priced_share=R2((booked - G.get('fallback_exit', 0)) / tot) if tot else None,
                    g4_small_share=R2(G.get('small', 0) / (2 * booked)) if booked else None, g5_fail=G.get('g5_fail', 0),
                    hop_no_route=G.get('hop_no_route_excluded', 0), hop_exit_fallback=G.get('hop_exit_fallback', 0))
    g1 = (o['S']['priced_share'] or 0) >= 0.60; g4 = (o['S']['g4_small_share'] or 0) < 0.20
    g5 = all(o[k]['g5_fail'] == 0 for k in ('S', 'WR', 'WA'))
    g10 = all((o[k]['priced_share'] or 0) >= 0.60 and (o[k]['g4_small_share'] or 0) < 0.20 for k in ('WR', 'WA') if o[k]['draws'])
    o['status'] = dict(G1='PASS' if g1 else 'FAIL', G4='PASS' if g4 else 'FAIL', G5='PASS' if g5 else 'FAIL', G10='PASS' if g10 else 'FAIL')
    o['note'] = 'engine-cell counts (a filtered cell shows its base\'s)'
    return o
def fmask(col, f):
    m = np.ones(len(col['T']), dtype=bool)
    if f:
        if 'min_dip_sec' in f: m &= ~np.isnan(col['tfDip']) & (np.nan_to_num(col['tfDip'], nan=-1) >= f['min_dip_sec'])
        if 'min_sells' in f: m &= ~np.isnan(col['tfSell']) & (np.nan_to_num(col['tfSell'], nan=-1) >= f['min_sells'])
    return m
day = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime('%Y-%m-%d')
res = dict(schema='edge-machine results v1', engine='engine_v1.js', engine_sha256=ENGINE_SHA, cost_version=COST_V, manifest_sha256=MAN['manifest_sha256'],
           primary_view=PRIMARY, primary_view_meaning='real per-pool costs (R-0111), ETH booking, TP sold 60 s after the trigger, ETH<->quote-token hop costed on both legs (R-0115); trades with no direct ETH route to their quote token are left out of this view',
           nohop_view=NOHOP, data_window=MAN['data_window'], cells={}, passes=META)
trows = []
for cid, cm in CM.items():
    ec = cm['engine_cell']; col = S.get(ec)
    rec = dict(cell=cid, engine_cell=ec, filter=cm['filter'], dials=cm['dials'], labels=cm['labels'], stat_seed=cm['stat_seed'],
               engine_sha256=ENGINE_SHA, cost_version=COST_V, data_window=MAN['data_window'])
    if col is None: rec['missing'] = True; res['cells'][cid] = rec; continue
    fm = fmask(col, cm['filter'])
    for half, off in (('JUDGE', 0), ('FIT', 50)):
        seed = cm['stat_seed'] + off
        ix = np.nonzero((col['judge'] == (half == 'JUDGE')) & fm)[0]
        prim = ix[~np.isnan(col['v'][ix, VI[PRIMARY]])]
        dl = sorted({day(x) for x in col['day'][prim]})
        H = dict(n=int(len(prim)), coins=len({col['tok'][i] for i in prim}), n_days=len(dl), days=dl,
                 hop_no_route_left_out=int(col['hopX'][ix].sum()), base_rows_before_filter=int((col['judge'] == (half == 'JUDGE')).sum()) if cm['filter'] else None)
        if len(ix) >= 3:
            vp, vn = VI[PRIMARY], VI[NOHOP]
            H[PRIMARY] = dict(raw=raw_block(col, ix, PRIMARY, seed + 10 * vp + 1), d_vs_A=d_block(col, ix, PRIMARY, 'A', seed + 10 * vp + 2),
                              d_vs_R=d_block(col, ix, PRIMARY, 'R', seed + 10 * vp + 3))
            H[NOHOP] = dict(raw=raw_block(col, ix, NOHOP, seed + 10 * vn + 1), d_vs_A=d_block(col, ix, NOHOP, 'A', seed + 10 * vn + 2))
            H['exit_reasons'] = dict(collections.Counter(col['reason'][i] for i in prim))
            H['tp_share'] = R2(np.mean(col['tp'][prim])) if len(prim) else None
            H['stock_entry_share'] = R2(np.mean(col['eStock'][prim])) if len(prim) else None
            H['quote_class'] = dict(collections.Counter(str(col['qcls'][i]) for i in ix))
            H['top_coin_share'] = None
            if len(prim):
                by = collections.defaultdict(float)
                for i in prim: by[col['tok'][i]] += col['v'][i, vp]
                tot = sum(by.values()); top = max(by, key=lambda t: by[t]); H['top_coin'] = top
                H['top_coin_share'] = R2(by[top] / tot) if tot > 0 else None
        H['gate'] = gate(ec, half)
        rec[half] = H
        for i in ix:
            vpv = col['v'][i, VI[PRIMARY]]; ta = col['tA'][i, VI[PRIMARY]]; tr = col['tR'][i, VI[PRIMARY]]
            f = lambda x: None if x != x else round(float(x), 6)
            trows.append(dict(cell=cid, tok=col['tok'][i], pair=int(col['pair'][i]), T=int(col['T'][i]), day=int(col['day'][i]), half=half, sigTs=int(col['sigTs'][i]),
                              entryTs=int(col['entryTs'][i]), exitTs=int(col['exitTs'][i]), reason=col['reason'][i], ret=f(vpv), ret_real60=f(col['v'][i, VI[NOHOP]]),
                              twinA=f(ta), twinR=f(tr), ePk=col['ePk'][i], v4e=bool(col['v4e'][i]), fb=bool(col['fb'][i]), stock=bool(col['eStock'][i]), pad=col['pad'][i],
                              eQ=col['eQ'][i], hopX=bool(col['hopX'][i]), tfDip=f(col['tfDip'][i]), tfSell=f(col['tfSell'][i]), cost_version=COST_V, engine_sha256=ENGINE_SHA))
    res['cells'][cid] = rec
for r in trows:
    for k in ('T', 'sigTs', 'entryTs', 'exitTs'):
        if r[k] >= 1790467200: raise SystemExit('SEALED ROW in the per-trade output - refused')
with gzip.open(O + '/trades.ndjson.gz', 'wt', compresslevel=6) as fo:
    for r in trows: fo.write(json.dumps(r, separators=(',', ':')) + '\n')
res['trades_file'] = 'trades.ndjson.gz'; res['trades'] = len(trows)
json.dump(res, open(O + '/results.json', 'w'), indent=1, default=float)
print('cells', len(res['cells']), 'trades', len(trows))
for cid, r in res['cells'].items():
    J = r.get('JUDGE', {}); a = J.get(PRIMARY, {}).get('raw', {}); b = J.get(NOHOP, {}).get('raw', {})
    print(f"{cid:28s} JUDGE {PRIMARY} n {a.get('n')} mean {a.get('mean')} lower {a.get('lower')} | {NOHOP} n {b.get('n')} mean {b.get('mean')} lower {b.get('lower')}")
