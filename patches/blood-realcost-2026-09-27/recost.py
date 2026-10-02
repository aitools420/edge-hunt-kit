#!/usr/bin/env python3
"""recost.py - re-cost every trade of the four Blood tests at the REAL per-pool cost (PREREG.md, sha256 in PREREG.sha256).
Inference (inference / cl_se / block_boot / drop5) is exec'd VERBATIM from ../blood-exitgrid-2026-09-27/analyze_xg.py.
Usage: recost.py <out.json>   (reads the re-run rows in the scratchpad rcost/ folder; see identity.json for the row check)"""
import json, sys, math, gzip, collections
import numpy as np
P = __import__('os').environ['KIT_ROOT'] + '/patches'; SP = '<scratchpad of the original 2026-09-27 run: read only below the loaders marker, never by the kit>'
OUT = sys.argv[1]
src = open(P + '/blood-exitgrid-2026-09-27/analyze_xg.py').read(); head = src[:src.index('# ---- load:')]
g = {'__name__': 'axg'}; _a = sys.argv; sys.argv = ['x', '/dev/null', '/dev/null']; exec(head, g); sys.argv = _a
inference, drop5, heavy_src, R2, JUDGE0, DAY, SEED = g['inference'], g['drop5'], g['heavy'], g['R2'], g['JUDGE0'], g['DAY'], g['SEED']
FITCUT, JCUT = g['FITCUT'], g['JCUT']
PC = json.load(open('pool_costs.json')); C = PC['constants']; POOLS = PC['pools']
IDENT = json.load(open('identity.json'))
SLIP = 0.004

# ------------------------------------------------------------------ per-side cost (PREREG §1)
def v4_fees(pool, f_eng):
    """-> (f_real, take, mev, fallback-kind or None)"""
    q = POOLS.get(pool) or {'type': 'unknown'}
    t = q['type']
    if t == 'pons':
        if q.get('take') is None: return 0.0, C['pons_take_fallback'], C['mev_pons'], 'pons_no_terms'
        return 0.0, q['take'], C['mev_pons'], None
    mev = C['mev_other']
    if t == 'nohook':
        if q.get('lp_receipt') is not None: return q['lp_receipt'], 0.0, mev, None
        if q.get('fee_key') is not None and q['fee_key'] < 1: return q['fee_key'] + C['nohook_protocol_resid'], 0.0, mev, None
        return f_eng + C['nohook_protocol_resid'], 0.0, mev, 'nohook_no_key'
    if t == 'dynfee':
        if q.get('lp_receipt') is not None: return q['lp_receipt'], 0.0, mev, None
        if f_eng is not None and abs(f_eng - 0.01) > 1e-12: return f_eng, 0.0, mev, None          # the engine's own per-pool tape measure
        return C['dynfee_fallback_lp'], 0.0, mev, 'dynfee_default'
    if t == 'otherhook':
        f = q['lp_receipt'] if q.get('lp_receipt') is not None else (q['fee_key'] + C['nohook_protocol_resid'] if q.get('fee_key') is not None else f_eng + C['nohook_protocol_resid'])
        return f, 0.0, mev, 'otherhook_take_unmeasured'
    return (f_eng or 0.01) + C['nohook_protocol_resid'], 0.0, mev, 'unknown_pool'

def net(r, x, v23='heavy'):
    """measured net for one trade. r = entry fields, x = exit fields (xP, xK, xPk, xw, xf, g5px, sellPx). -> (net, set(fallback kinds))"""
    fb = set(); eP = r['eP']
    basis = x['g5px'] if x.get('g5px') is not None else x['xP']
    # buy side
    if r['eK'] == 'v4':
        u = r.get('eu') or 0.0; f_eng = r.get('ef')
        f, t, mev, k = v4_fees(r['ePk'][3:], f_eng)
        if k: fb.add(k)
        B = (1 + u) * (1 + f) * (1 + mev) / (1 - t)
    else:
        cb = r['entryPx'] / eP - 1; B = 1 + (max(cb, 0.014) if v23 == 'heavy' else cb); fb.add('v23_side')
    # sell side
    if x['xK'] == 'v4':
        pool = x['xPk'][3:]
        if x.get('g5px') is not None:
            f, t, mev, k = v4_fees(pool, 0.01); fb.add('g5_override')
            if k: fb.add(k)
            S = (1 - f) * (1 - t) * (1 - mev) * (1 - SLIP)
        else:
            w = x.get('xw') or 0.0
            f_eng = x.get('xf')
            if f_eng is None: f_eng = 1 - x['sellPx'] * (1 + w) / x['xP']
            f, t, mev, k = v4_fees(pool, f_eng)
            if k: fb.add(k)
            S = (1 - f) * (1 - t) * (1 - mev) / (1 + w)
    else:
        cs = 1 - x['sellPx'] / basis if basis > 0 else 0
        S = 1 - (max(cs, 0.014) if v23 == 'heavy' else cs); fb.add('v23_side')
    v = 100 * (basis * S / (eP * B) - 1) - 0.2
    return v, fb

XF = ('xP', 'xK', 'xPk', 'xw', 'xf', 'g5px', 'sellPx', 'reason', 'fb', 'on')
def views(r, x):
    """all views for one (position, exit). r: entry-level row, x: exit fields incl. reason/fb/on/tb."""
    capped = bool(x.get('fb'))
    cap = (lambda v: min(v, 0.0)) if capped else (lambda v: v)
    h = dict(r); h.update({k: x.get(k) for k in XF}); h['fb'] = capped
    h['ePons'] = 1 if r['eK'] == 'v4' and (POOLS.get(r['ePk'][3:]) or {}).get('type') == 'pons' else 0
    h['xPons'] = 1 if x['xK'] == 'v4' and (POOLS.get(x['xPk'][3:]) or {}).get('type') == 'pons' else 0
    model = min(x['on'], 0.0) if capped else x['on']
    hv = heavy_src(h)                                                    # source heavy (uses Pons flags from the pool table)
    m60, fb60 = net(r, x); m60 = cap(m60)
    mv23, _ = net(r, x, 'model'); mv23 = cap(mv23)
    if x.get('reason') == 'tp' and x.get('tb'):
        tb = x['tb']; xt = {k: tb.get(k) for k in ('xP', 'xK', 'xPk', 'xw', 'xf', 'g5px', 'sellPx')}
        mt, fbt = net(r, xt); trig_used = True
    else:
        mt, fbt = m60, fb60; trig_used = False
    mt = cap(mt)
    return dict(model=model, heavy=hv, meas=m60, meas_trig=mt, meas_v23model=mv23, fbk=sorted(fb60 | fbt), trig_used=trig_used,
                tp=(x.get('reason') == 'tp'), crash=None)

# ------------------------------------------------------------------ loaders (row filters exactly as the source analyses)
def rows_of(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt') as fh:
        for ln in fh:
            j = json.loads(ln)
            if '_meta' in j or j.get('trunc') or j.get('nofill') or j.get('noscale') or j.get('skipDepth'): continue
            if j.get('clip', 50) != 50: continue
            yield j
def band_of(t_entry, r):
    if r['eK'] != 'v4': return 'V23'
    q = POOLS.get(r['ePk'][3:]) or {'type': 'unknown'}
    if q['type'] != 'pons': return 'LOW'
    tk = q['take'] if q.get('take') is not None else C['pons_take_fallback']
    return 'LOW' if tk <= 0.01 + 1e-9 else 'HIGH'
def pons1(r):
    if r['eK'] != 'v4': return False
    q = POOLS.get(r['ePk'][3:]) or {}; return q.get('type') == 'pons' and q.get('take') is not None and abs(q['take'] - 0.01) < 1e-9

# unit = dict(key -> strategy view rows), twins key -> list
class Cell:
    def __init__(s): s.S = {}; s.W = collections.defaultdict(list)
def mk(r, x):
    v = views(r, x); v.update(tok=r['tok'], day=(r['T'] // DAY) * DAY, half='JUDGE' if r['T'] >= JUDGE0 else 'FIT', band=band_of(None, r),
                              pons1=pons1(r), v4e=r['eK'] == 'v4', eDepth1=r.get('eDepth1'), kind=r['kind'])
    return v

TESTS = {}
FBCOUNT = collections.defaultdict(collections.Counter)
def count_fb(test, v):
    c = FBCOUNT[test + '|' + v['half']]; c['trades'] += 1
    k = set(v['fbk'])
    if k: c['any_fallback'] += 1
    if k - {'v23_side'}: c['v4_fallback'] += 1
    if k == {'v23_side'} or ('v23_side' in k): c['v23_side'] += 1
    for kk in k: c['kind:' + kk] += 1
    if v['tp']: c['tp_exits'] += 1
    if v['trig_used']: c['tp_trigger_rebooked'] += 1

def load_xg():
    cells = collections.defaultdict(Cell); src = SP + '/rcost/xg.ndjson' if IDENT['xg']['use_rerun'] else SP + '/xg/full.ndjson'
    for j in rows_of(src):
        xs = j.pop('x'); d = j.get('eDepth1')
        bf = 'v23' if d is None else 'low' if d <= FITCUT[0] else 'mid' if d <= FITCUT[1] else 'high'
        bj = 'v23' if d is None else 'j_low' if d <= JCUT[0] else 'j_mid' if d <= JCUT[1] else 'j_high'
        for x, xv in xs.items():
            v = mk(j, xv); v['band_fit'] = bf; v['band_j'] = bj
            if x == 'tp15_h48': count_fb('exit grid (per position, base exit tp15_h48)', v)
            c = cells[x]
            if j['kind'] == 'S': c.S[j['pair']] = v
            elif j.get('tw') == 'A': c.W[j['pair']].append(v)
    return cells
def load_flat(name, path, cellset, tw):
    cells = collections.defaultdict(Cell)
    for j in rows_of(path):
        if j['cell'] not in cellset: continue
        if j['kind'] != 'S' and tw is not None and j.get('tw') != tw: continue
        v = mk(j, j); count_fb(name, v); c = cells[j['cell']]
        if j['kind'] == 'S': c.S[j['pair']] = v
        else: c.W[j['pair']].append(v)
    return cells

# ------------------------------------------------------------------ stats
def money(rows, view, seed):
    if len(rows) < 3: return {'n': len(rows)}
    v = [r[view] for r in rows]; I = inference(v, [r['tok'] for r in rows], [r['day'] for r in rows], seed)
    return dict(n=len(rows), coins=len({r['tok'] for r in rows}), raw_mean=R2(I['mean']), raw_ci95=[R2(c) for c in I['ci95']], median=R2(np.median(v)),
                raw_p_one_sided=None if I['p'] is None else float('%.3g' % I['p']), se_cons=R2(I['se_cons']), drop5=R2(drop5(v)),
                win_share=R2(np.mean([a > 0 for a in v])), tp_share=R2(np.mean([r['tp'] for r in rows])), crash_share=R2(np.mean([a <= -50 for a in v])), days=I['days'])
def dsum(rows, W, view, seed, twin_pred=None):
    pr = []
    for r in rows:
        ws = [w for w in W.get(r['_pair'], []) if twin_pred is None or twin_pred(w)]
        if ws: tv = sum(w[view] for w in ws) / len(ws); pr.append((r, r[view] - tv, tv, ws))
    if len(pr) < 3: return {'n': len(pr)}
    d = [x[1] for x in pr]; I = inference(d, [x[0]['tok'] for x in pr], [x[0]['day'] for x in pr], seed)
    return dict(n=len(pr), d_mean=R2(I['mean']), ci95=[R2(c) for c in I['ci95']], p_one_sided=None if I['p'] is None else float('%.3g' % I['p']),
                drop5=R2(drop5(d)), twin_mean=R2(np.mean([x[2] for x in pr])), twin_tp_share=R2(np.mean([w['tp'] for x in pr for w in x[3]])))
SEEDC = [0]
def summarize(cell, half, pred=None, twin_pred=None):
    rows = []
    for k, r in cell.S.items():
        if r['half'] == half and (pred is None or pred(r)): r['_pair'] = k; rows.append(r)
    out = {}
    for view in ('meas', 'meas_trig'):
        SEEDC[0] += 10; s = SEED + 50000 + SEEDC[0]
        m = money(rows, view, s); m['vs_twin'] = dsum(rows, cell.W, view, s + 1, twin_pred)
        out[view] = m
    SEEDC[0] += 10
    ref = {vw: money(rows, vw, SEED + 50000 + SEEDC[0] + i) for i, vw in enumerate(('heavy', 'model', 'meas_v23model'))}
    ref['heavy']['vs_twin'] = dsum(rows, cell.W, 'heavy', SEED + 50000 + SEEDC[0] + 5, twin_pred)
    fbs = [r for r in rows]; out['fallback_share_strategy'] = R2(np.mean([bool(r['fbk']) for r in fbs])) if fbs else None
    out['v4_fallback_share_strategy'] = R2(np.mean([bool(set(r['fbk']) - {'v23_side'}) for r in fbs])) if fbs else None
    out['ref'] = ref
    return out

def judge_block(sm, view):
    m = sm[view]; d = m.get('vs_twin', {})
    if m.get('n', 0) < 3: return {'n': m.get('n', 0)}
    return dict(n=m['n'], coins=m['coins'], raw_mean=m['raw_mean'], raw_ci95=m['raw_ci95'], median=m['median'], drop5=m['drop5'], se_cons=m['se_cons'],
                raw_p_one_sided=m['raw_p_one_sided'], win_share=m['win_share'], tp_share=m['tp_share'], crash_share=m['crash_share'],
                d_mean=d.get('d_mean'), ci95=d.get('ci95'), d_n=d.get('n'), p_one_sided=d.get('p_one_sided'), d_drop5=d.get('drop5'),
                twin_mean=d.get('twin_mean'), twin_tp_share=d.get('twin_tp_share'), days=m['days'],
                fallback_share=sm['fallback_share_strategy'], v4_fallback_share=sm['v4_fallback_share_strategy'],
                heavy_raw_mean=sm['ref']['heavy'].get('raw_mean'), heavy_d_mean=sm['ref']['heavy'].get('vs_twin', {}).get('d_mean'),
                model_raw_mean=sm['ref']['model'].get('raw_mean'), v23_at_model_raw_mean=sm['ref']['meas_v23model'].get('raw_mean'),
                v23_at_model_raw_ci95=sm['ref']['meas_v23model'].get('raw_ci95'))

# ------------------------------------------------------------------ run
SRC_REC = {n: json.load(open(f'{P}/{d}/results.json'))['records'] for n, d in (('exit grid', 'blood-exitgrid-2026-09-27'), ('grid', 'blood-grid-depth-history-2026-09-27'),
                                                                              ('stress', 'blood-stress-2026-09-27'), ('established', 'blood-established-2026-09-27'))}
DROP = {'judge', 'fit', 'score', 'bonferroni', 'judge_views', 'gate', 'verdict', 'scalability', 'judge_hookfee_1pct', 'judge_trend_armB', 'fit_trend_armB',
        'shares_judge', 'shares_fit', 'crash_decomp_judge', 'crash_decomp_fit', 'modeM_judge', 'reality_check', 'clips', 'pad_hot', 'pad_not_hot', 'raw_passes'}
def base_rec(src):
    return {k: v for k, v in src.items() if k not in DROP}
RECS, POST = [], []
FROZEN = {('stress', 'C2P'): 'FROZEN FINAL-EXAM RULE #1 (C2P) — registered HEAVY cost and bar UNCHANGED; this is an ADDED labelled measured-cost view only',
          ('grid', 'D25L48'): 'FROZEN FINAL-EXAM RULE #2 (25%|>=48) — registered HEAVY cost and bar UNCHANGED; this is an ADDED labelled measured-cost view only'}
def emit(test, cellname, rec0, cell, pred=None, extra=None):
    J, F = summarize(cell, 'JUDGE', pred), summarize(cell, 'FIT', pred)
    for view, tb in (('meas', '60s'), ('meas_trig', 'trigger')):
        r = base_rec(rec0); r.update(extra or {})
        r.update(test=test, cell=cellname, cost_model='measured_per_pool', tp_booking=tb, judge=judge_block(J, view), fit=judge_block(F, view))
        if (test, cellname) in FROZEN: r['frozen_rule_note'] = FROZEN[(test, cellname)]
        RECS.append(r)
def emit_bands(test, cellname, rec0, cell):
    for b, pred, tpred in (('LOW', lambda r: r['band'] == 'LOW', lambda w: w['band'] == 'LOW'), ('LOW_PONS1', lambda r: r['pons1'], lambda w: w['pons1']),
                           ('HIGH', lambda r: r['band'] == 'HIGH', lambda w: w['band'] == 'HIGH'), ('V23', lambda r: r['band'] == 'V23', lambda w: w['band'] == 'V23')):
        J = summarize(cell, 'JUDGE', pred, tpred)
        for view, tb in (('meas', '60s'), ('meas_trig', 'trigger')):
            r = base_rec(rec0); r.update(test=test, cell=cellname, cost_model='measured_per_pool', tp_booking=tb, fee_band=b, POSTHOC='fee band is a NEW variable, chosen after JUDGE was read — not a result',
                                          judge=judge_block(J, view))
            POST.append(r)

# exit grid
xg = load_xg(); print('xg loaded', flush=True)
src = {(r['value'], r['depth_band']): r for r in SRC_REC['exit grid']}
for x, c in xg.items():
    for b in ('all', 'low', 'mid', 'high', 'j_low', 'j_mid', 'j_high', 'v23'):
        if b == 'all': pred = None
        elif b in ('low', 'mid', 'high'): pred = (lambda r, b=b: r['band_fit'] == b)
        elif b == 'v23': pred = (lambda r: r['band_fit'] == 'v23')
        else: pred = (lambda r, b=b: r['band_j'] == b)
        emit('exit grid', x, src[(x, b)], c, pred)
    emit_bands('exit grid', x, src[(x, 'all')], c)
del xg
# grid
gsrc = {r['cell']: r for r in SRC_REC['grid']}
gp = SP + '/rcost/grid.ndjson.gz' if IDENT['grid']['use_rerun'] else SP + '/grid/full.ndjson.gz'
gr = load_flat('grid', gp, set(gsrc), 'A'); print('grid loaded', flush=True)
for cn, c in gr.items(): emit('grid', cn, gsrc[cn], c); emit_bands('grid', cn, gsrc[cn], c)
del gr
# stress
ssrc = {r['config']: r for r in SRC_REC['stress'] if r['value'] == 'S1_one_pool'}
sp = SP + '/rcost/st.ndjson' if IDENT['st']['use_rerun'] else SP + '/st/full.ndjson'
st = load_flat('stress', sp, {'C1P', 'C2P'}, 'A'); print('stress loaded', flush=True)
for cn, c in st.items():
    rec0 = dict(ssrc[cn[:2]]); rec0['value'] = 'S1_one_pool'
    emit('stress', cn, rec0, c, extra=dict(twin='activity (A)')); emit_bands('stress', cn, rec0, c)
del st
# established
bsrc = {r['value']: r for r in SRC_REC['established']}
bp = SP + '/rcost/bes.ndjson' if IDENT['bes']['use_rerun'] else SP + '/bes/full.ndjson'
be = load_flat('established', bp, {'A' + w for w in bsrc}, None); print('bes loaded', flush=True)
for cn, c in be.items():
    emit('established', cn, bsrc[cn[1:]], c, extra=dict(twin='matched twin (the test design)')); emit_bands('established', cn, bsrc[cn[1:]], c)

json.dump(dict(test='Blood re-cost at real per-pool cost', date='2026-09-27', prereg_sha256=open('PREREG.sha256').read().split()[0],
               records=RECS, records_posthoc_fee_band=POST, fallback_counts={k: dict(v) for k, v in FBCOUNT.items()}, identity=IDENT), open(OUT, 'w'))
print('records', len(RECS), 'posthoc', len(POST))
for k, v in FBCOUNT.items(): print(k, dict(v))
