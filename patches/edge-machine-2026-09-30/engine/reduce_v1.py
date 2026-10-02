#!/usr/bin/env python3
"""reduce_v1.py - EDGE MACHINE v1, stage A: one engine_v1.js pass file -> compact per-engine-cell arrays (pickle), with the ONE v1 cost
model computed on every trade. = ../../blood-hunt2-2026-09-29/reduce_h2.py (the hop-costed reducer) with ONLY (tagged V1):
  * a trade (or twin draw) whose non-ETH-quoted entry pool has NO direct ETH route is KEPT and flagged (hopX) with the five hop views = NaN,
    instead of being dropped (reduce_h2 `continue`d). Every statistic of a hop view skips NaN, so the hop views are EXACTLY reduce_h2's;
    the no-hop views keep every trade, so they are EXACTLY reduce_lf / reduce_h3's (hunt 3 published real60 = the no-hop view).
  * twin means are per view with NaN skipped (nanmean): hop views average the routable twins (= reduce_h2), no-hop views all (= reduce_h3).
  * kept columns: eQ (H3), the TOKF signal features tfDip (sigTs - hiTs, s), tfSell (nSell), tfMatch (hiMatch); the batch's cost table
    and hop tables come from env POOL_COSTS / HOP_DIR (built per batch by pool_costs_v1.py / build_hop_v1.py). The 'H' identity list dropped.
VIEWS and their meaning (pts per $50 trade; fallback rows 'fb'/'end' capped at 0 in every view) - v1 PRIMARY = real60h:
  meas, meas_trig, heavy   the real-cost batch's basis (recost.py), for reference only
  real60, realtrig         realism costs (realism-2026-09-27: per-pool take/LP, V2/V3 fee+impact, token tax, gas), ETH booking, TP booked
                           60 s after the trigger (real60) or at the trigger print (realtrig) - NO ETH->quote hop
  lat, lat90               realtrig + our bot's measured latency from the engine's probes
  real60h, realtrigh, lath, lat90h   the same four WITH the ETH <-> quote-token hop costed on both legs (R-0115) - real60h = THE v1 cost model
  real60u                  real60h, route may go ETH -> USDG -> quote
Usage: reduce_v1.py <pass.ndjson.gz> <out.pkl>   env POOL_COSTS=<batch pool_costs.json> HOP_DIR=<batch hop dir> [JUDGE0]"""
import json, sys, gzip, os, collections, pickle, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'
SRC, OUT = sys.argv[1], sys.argv[2]
POOLC = os.environ['POOL_COSTS']                                                                        # V1
src = open(P + '/blood-realcost-2026-09-27/recost.py').read()
head = src[:src.index('# ------------------------------------------------------------------ loaders')]
head = head.replace("open('pool_costs.json')", f"open('{POOLC}')").replace("IDENT = json.load(open('identity.json'))", "IDENT = {}")
g = {'__name__': 'rc'}; exec(head, g)
views_rc, POOLS = g['views'], g['POOLS']
sys.path.insert(0, P + '/realism-2026-09-27'); import realism as R
_add = {k: v for k, v in POOLS.items() if k not in R.POOLS}; R.POOLS.update(_add)
JUDGE0 = int(os.environ.get('JUDGE0', 1789603200)); DAY = 86400; SEAL = 1790467200; CLIP = 50.0
VIEWS = ('meas', 'meas_trig', 'heavy', 'real60', 'realtrig', 'lat', 'lat90', 'real60h', 'realtrigh', 'lath', 'lat90h', 'real60u')
HOPV = ('real60h', 'realtrigh', 'lath', 'lat90h', 'real60u')
sys.path.insert(0, HERE); import hop as HOPM
HOPD = os.environ['HOP_DIR']; H = HOPM.Hop(HOPD + '/hop_tables.pkl', HOPD + '/poolquote.tsv')
HOP_GAS = 0.5 * R.LAT['defaults']['gas_eth_per_swap']
NAN = float('nan')
def hop_apply(net, clip_eth, Bh, Sh):
    g = R.gas_pts(clip_eth); X = net + g + 100.0
    return X * Sh / Bh - 100.0 - g - 100.0 * 2 * HOP_GAS / clip_eth
def hop_exit(q, t, size, eleg, allow_usdg=False):
    x = H.route(q, t, size, 'sell', allow_usdg)
    if x: return x['mult'], False
    return (1 - eleg['fee']) / (1 + eleg['impact'] * size / max(eleg.get('size', size), 1e-12)), True
def eth_px(px, pe, ts): return pe if pe else (px / R.eth_usd_at(ts) if px else None)
def rpool(pk): return pk[3:] if pk and pk.startswith('v4:') else pk
def xfee(j):
    if j['xK'] != 'v4': return j.get('ef')
    if j.get('g5px') is not None: return 0.01
    return 1 - j['sellPx'] * (1 + (j.get('xw') or 0)) / j['xP']
def real_net(j, eK, ePool, e_eth, xK, xPool, x_eth, xf, xw, entry_ts, clip_eth):
    gross = x_eth / e_eth
    cb = R.cost_per_side(ePool, j['tok'], 'buy', clip_eth, engine_fee=j.get('ef'), engine_impact=j.get('eu') if eK == 'v4' else None)
    cs = R.cost_per_side(xPool, j['tok'], 'sell', clip_eth * gross, engine_fee=xf, engine_impact=xw if xK == 'v4' else None)
    bi, si = cb['impact'], cs['impact']
    B = (1 + cb['total'] - bi) * (1 + bi); Sx = (1 - (cs['total'] - si)) / (1 + si)
    return 100 * (gross * Sx / B - 1) - R.gas_pts(clip_eth), cb, cs
# ---- pass 1: probes ----
probes = {}; pstat = collections.Counter(); meta = None
with gzip.open(SRC, 'rt') as fh:
    for ln in fh:
        if ln.startswith('{"pr":'):
            a = json.loads(ln)['pr']
            if a[3] is None: pstat['null'] += 1; continue
            if a[3] >= SEAL: raise RuntimeError('sealed print in a probe')
            probes.setdefault(a[0], {})[a[1]] = (a[3], eth_px(a[4], a[5], a[3]), a[6], a[7])
            pstat['ok'] += 1
# ---- pass 2: positions ----
S = collections.defaultdict(list)
TW = {'A': collections.defaultdict(list), 'R': collections.defaultdict(list)}
gate = collections.defaultdict(collections.Counter)
gmax = collections.defaultdict(lambda: collections.defaultdict(lambda: -1e9))
missing_pools = collections.Counter(); latfb = collections.Counter(); srcs = collections.Counter()
def who(j): return 'S' if j['kind'] == 'S' else 'W' + j['tw']
with gzip.open(SRC, 'rt') as fh:
    for ln in fh:
        if ln.startswith('{"pr":'): continue
        j = json.loads(ln)
        if '_meta' in j: meta = j['_meta']; continue
        if j['T'] >= SEAL or (j.get('exitTs') or 0) >= SEAL or (j.get('entryTs') or 0) >= SEAL or (j.get('sigTs') or 0) >= SEAL: raise RuntimeError('sealed row')
        half = 'JUDGE' if j['T'] >= JUDGE0 else 'FIT'; c = j['cell']; gk = (c, half, who(j)); G = gate[gk]
        if j.get('trunc'): G['trunc'] += 1; continue
        if j.get('nofill'): G['nofill'] += 1; continue
        if j.get('skipDepth'): G['skip_depth_floor'] += 1; continue
        for pk in (j.get('ePk'), j.get('xPk'), (j.get('tb') or {}).get('xPk')):
            if pk and pk.startswith('v4:') and pk[3:] not in POOLS: missing_pools[pk[3:]] += 1
        v = views_rc(j, j); fb = bool(j.get('fb')); cap = (lambda x: min(x, 0.0)) if fb else (lambda x: x)
        clip_eth = CLIP / R.eth_usd_at(j['entryTs'])
        qv = H.quote_of(rpool(j['ePk'])) if j.get('eK') == 'v4' else None
        hopx = False                                                                                   # V1
        if qv:
            he = H.route(qv[0], j['entryTs'], clip_eth, 'buy')
            if he is None: G['hop_no_route_excluded'] += 1; G['hop_no_route|' + (qv[2] or qv[0][:10])] += 1; hopx = True   # V1: flag, keep
            else:
                he['size'] = clip_eth; heu = H.route(qv[0], j['entryTs'], clip_eth, 'buy', allow_usdg=True); heu['size'] = clip_eth
                G['hop_' + ('usdg_quoted' if qv[1] == 'USDG' else 'other_quoted')] += 1
        basis = j['g5px'] if j.get('g5px') is not None else j['xP']
        e_eth = j['eP'] / R.eth_usd_at(j['entryTs']); x_eth = basis / R.eth_usd_at(j['exitTs'])
        r60, cb, cs = real_net(j, j['eK'], rpool(j['ePk']), e_eth, j['xK'], rpool(j['xPk']), x_eth, xfee(j), j.get('xw'), j['entryTs'], clip_eth)
        tb = j.get('tb') if j.get('reason') == 'tp' else None
        if tb:
            tbasis = tb['g5px'] if tb.get('g5px') is not None else tb['xP']
            rtr, _, cst = real_net(j, j['eK'], rpool(j['ePk']), e_eth, tb['xK'], rpool(tb['xPk']), tbasis / R.eth_usd_at(tb['ts']), tb.get('xf'), tb.get('xw'), j['entryTs'], clip_eth)
        else: rtr, cst = r60, cs
        srcs[cb['src'][:40]] += 1; srcs[cs['src'][:40]] += 1
        lv = {}
        pr = probes.get(j['u'], {})
        for tag, ek, xk in (('lat', 'e', 'x'), ('lat90', 'e90', 'x90')):
            if fb: lv[tag] = min(rtr, 0.0); latfb[tag + '|fallback_row'] += 1; continue
            e = pr.get(ek); x = pr.get(xk)
            if e is None or e[1] is None or not (e[1] > 0): latfb[tag + '|no_entry_probe'] += 1; e = None
            ePool = rpool(e[2]) if e else rpool(j['ePk']); eE = e[1] if e else e_eth
            xs = tb or j
            engine_x = (xs['g5px'] if xs.get('g5px') is not None else xs['xP']) / R.eth_usd_at(xs['ts'] if tb else j['exitTs'])
            if xs.get('g5') in ('c2', 'lastok'): xE = engine_x; latfb[tag + '|g5_engine_exit'] += 1
            elif x is None or x[1] is None or not (x[1] > 0): xE = engine_x; latfb[tag + '|no_exit_probe'] += 1
            else:
                xE = x[1]
                if xE > 20 * eE and xs.get('g5') not in ('depthok', 'corroborated'): xE = engine_x; latfb[tag + '|gt20x_engine_exit'] += 1
            xf = tb.get('xf') if tb else xfee(j); xw = xs.get('xw')
            lv[tag], _, _ = real_net(j, j['eK'] if not e else ('v4' if str(e[2]).startswith('v4:') else 'v23'), ePool, eE, xs['xK'], rpool(xs['xPk']), xE, xf, xw, j['entryTs'], clip_eth)
        if qv and not hopx:
            tx60 = j['exitTs']; txtr = tb['ts'] if tb else j['exitTs']; hv = {}
            for tag, net, tx in (('real60h', r60, tx60), ('realtrigh', rtr, txtr), ('lath', lv['lat'], txtr + R.latency_sec('sell')), ('lat90h', lv['lat90'], txtr + R.latency_sec('sell', 'p90'))):
                sz = clip_eth * max(0.01, (net + 100) / 100); Sh, fbk = hop_exit(qv[0], tx, sz, he); G['hop_exit_fallback'] += fbk
                hv[tag] = hop_apply(net, clip_eth, he['mult'], Sh)
            Shu, _ = hop_exit(qv[0], tx60, clip_eth * max(0.01, (r60 + 100) / 100), heu, allow_usdg=True); hv['real60u'] = hop_apply(r60, clip_eth, heu['mult'], Shu)
            hopE, hopEu, hopRt = he['mult'] - 1, heu['mult'] - 1, heu['route']
        elif qv:                                                                                        # V1: no direct route -> hop views NaN
            hv = {k: NAN for k in HOPV}; hopE = hopEu = NAN; hopRt = 'no_route'
        else:
            hv = dict(real60h=r60, realtrigh=rtr, lath=lv['lat'], lat90h=lv['lat90'], real60u=r60); hopE = hopEu = 0.0; hopRt = 'none'
        vals = dict(meas=v['meas'], meas_trig=v['meas_trig'], heavy=v['heavy'], real60=cap(r60), realtrig=cap(rtr), lat=cap(lv['lat']), lat90=cap(lv['lat90']),
                    **{k: (x if x != x else cap(x)) for k, x in hv.items()})
        vt = tuple(vals[k] for k in VIEWS)
        G['booked'] += 1; G['fallback_exit'] += fb; G['drains'] += j.get('reason') == 'drain'; G['tp'] += bool(v['tp'])
        G['small'] += (j['eU'] < 10 and j['eK'] != 'v4') + ((j.get('xU') or 0) < 10 and j['xK'] != 'v4')
        G['exit_gt20x'] += j['xP'] > 20 * j['eP']
        if j.get('g5'): G['g5|' + j['g5']] += 1
        mx = max(x for x in vt if x == x)
        G['g5_fail'] += mx > 1000 and j.get('g5') not in ('depthok', 'corroborated')
        G['big_uncorroborated'] += mx > 500 and j.get('g5') not in ('depthok', 'corroborated')
        s = j.get('sell'); G['unsell_a'] += (not s) or (not s['s10h']) or (s['sbr'] is not None and s['sbr'] < 0.5)
        G['taxed'] += (cb['tax'] + cst['tax']) > 0.001
        for k, x in zip(VIEWS, vt):
            if x == x: gmax[gk][k] = max(gmax[gk][k], x)
        if j['kind'] == 'S':
            tf = j.get('tf') or {}
            S[c].append(dict(pair=j['pair'], tok=j['tok'], pad=j.get('pad'), T=j['T'], half=half, day=(j['T'] // DAY) * DAY, sigTs=j['sigTs'], entryTs=j['entryTs'],
                             exitTs=j['exitTs'], reason=j['reason'], fb=fb, tp=bool(v['tp']), v4e=j['eK'] == 'v4', ePk=j['ePk'], sigHot=j.get('sigHot'), g5=j.get('g5'),
                             eU=j['eU'], xP=j['xP'], eP=j['eP'], v=vt, taxed=(cb['tax'] + cst['tax']) > 0.001,
                             eBand=j.get('eBand'), eTake=j.get('eTake') if j.get('eTake') is not None else NAN, eTy=j.get('eTy'), eStock=bool(j.get('eStock')), xStock=bool(j.get('xStock')),
                             qcls=('eth' if not qv else 'usdg' if qv[1] == 'USDG' else 'other'), qsym=(qv[2] if qv else ''), hopE=hopE, hopEu=hopEu, hopRt=hopRt,
                             hopX=hopx, eQ=j.get('eQ'), tfDip=(j['sigTs'] - tf['hiTs']) if tf.get('hiTs') is not None else NAN,           # V1
                             tfSell=tf['nSell'] if tf.get('nSell') is not None else NAN, tfMatch=bool(tf.get('hiMatch')), tfHas=bool(tf)))
        else:
            TW[j['tw']][(c, j['pair'])].append(vt + (bool(v['tp']),))
out = {}; NV = len(VIEWS); PI = VIEWS.index('real60h')
for c, rows in S.items():
    col = {k: [r[k] for r in rows] for k in ('pair', 'tok', 'pad', 'T', 'day', 'sigTs', 'entryTs', 'exitTs', 'reason', 'fb', 'tp', 'v4e', 'ePk', 'sigHot', 'g5', 'eU', 'xP', 'eP', 'taxed',
                                            'eBand', 'eTake', 'eTy', 'eStock', 'xStock', 'qcls', 'qsym', 'hopE', 'hopEu', 'hopRt', 'hopX', 'eQ', 'tfDip', 'tfSell', 'tfMatch', 'tfHas')}
    col['judge'] = np.array([r['half'] == 'JUDGE' for r in rows]); col['v'] = np.array([r['v'] for r in rows], dtype=float).reshape(-1, NV)
    for tw in ('A', 'R'):
        tv, nn, nh, tp = [], [], [], []
        for r in rows:
            ws = TW[tw].get((c, r['pair']), [])
            nn.append(len(ws)); nh.append(sum(1 for w in ws if w[PI] == w[PI]))
            if ws:
                a = np.array([w[:NV] for w in ws], dtype=float)
                with np.errstate(all='ignore'): m = [float(np.nanmean(a[:, i])) if np.any(~np.isnan(a[:, i])) else NAN for i in range(NV)]
                tv.append(m); tp.append(float(np.mean([w[-1] for w in ws])))
            else: tv.append([NAN] * NV); tp.append(NAN)
        col['t' + tw] = np.array(tv, dtype=float).reshape(-1, NV); col['n' + tw] = np.array(nn); col['nh' + tw] = np.array(nh); col['tp' + tw] = np.array(tp)
    for k in ('T', 'day', 'sigTs', 'entryTs', 'exitTs'): col[k] = np.array(col[k], dtype=np.int64)
    for k in ('fb', 'tp', 'v4e', 'taxed', 'eStock', 'xStock', 'hopX', 'tfMatch', 'tfHas'): col[k] = np.array(col[k], dtype=bool)
    for k in ('eU', 'xP', 'eP', 'eTake', 'hopE', 'hopEu', 'tfDip', 'tfSell'): col[k] = np.array(col[k], dtype=float)
    out[c] = col
pickle.dump(dict(src=SRC, views=VIEWS, S=out, gate={f'{k[0]}|{k[1]}|{k[2]}': dict(v) for k, v in gate.items()},
                 gmax={f'{k[0]}|{k[1]}|{k[2]}': dict(v) for k, v in gmax.items()}, meta=meta, probes=dict(pstat), latfb=dict(latfb),
                 missing_pools=dict(missing_pools), cost_src=dict(srcs), realism_pools_added=len(_add)), open(OUT, 'wb'))
print('cells', len(out), 'strategy rows', sum(len(v['T']) for v in out.values()), 'probes', dict(pstat), 'missing pools', len(missing_pools), 'latfb', dict(latfb))
