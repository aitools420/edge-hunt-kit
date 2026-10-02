#!/usr/bin/env python3
"""screen.py - EDGE MACHINE stage 1 (DESIGN.md build item 1): S1 + A1-A5 over EVERY measured Blood point of the explorer, answered by code.
READ-ONLY outside this folder. Never reads sealed data (>= 2026-09-27T00:00Z): the trade store refuses such rows when it is built, and this
script re-checks every stored row.
  python3 screen.py            screen from the durable store in trades/ (built by store.py; srcmap.py maps points to their records)
  python3 screen.py --rebuild  re-run srcmap.py + store.py first (needs the engine outputs, which live under /tmp and are NOT durable)
Writes points.json, families.json, candidates.json, norep.json, REPORT.md (unrecoverable.json and trades/ come from store.py)."""
import json, gzip, os, sys, subprocess, collections, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'

# ============================================================== CONFIG — defaults, Chef's to change
CONFIG = dict(
    # S1 screen
    S1_COST='real',                 # only points at the real (measured per-pool / realism) cost class
    S1_NO_POSTHOC=True,             # an after-the-fact split (R-0113 class: the post-hoc fee bands, the realism re-score) never passes
    S1_NO_R0115=True,               # a cell whose ETH->stock-token hop is NOT costed (R-0115; hunt 3 'any'-quote cells) never passes
    S1_MIN_N=30,
    S1_LOWER_GT=0.0,                # the explorer's own 95% range: lower end > this
    # A1 concentration — GATE = coin-clustered bootstrap (Chef TG 14912): resample COINS with all their trades
    A1_BOOT_B=5000, A1_SEED=12345, A1_LOWER_GT=0.0,
    A1_TAIL_HIT=50.0,               # info column: distinct coins with at least one trade >= +50%
    # (without-top-coin / without-best-day lower bars and the top-coin share are INFORMATION ONLY since TG 14912)
    # A2 breadth
    A2_MIN_COINS=15, A2_MIN_DAYS=4,
    # A3 neighbours: measured points one level step away on ONE ordered dial, same cost class; same test preferred, any test if none
    A3_ORDERED_DIALS=('age', 'vol', 'volat', 'dh', 'th', 'dip', 'win', 'delay', 'tp', 'hold'),
    A3_MIN_POS_SHARE=0.5, A3_MIN_NEIGHBOURS=1,
    # A4 data (information, not a gate in this pass): audit H1/H2 flags joined per trade where the audit covered it
    A4_DUST_USD=5.0,
    # A5 dedupe: two points are one family when they share >= this share of EACH other's trades (same coin, same assessment hour)
    A5_OVERLAP=0.80,
    A5_NESTED=0.80,                 # candidates are then grouped into independent trade sets when >= this share of the SMALLER one's trades sit in the other
    # NO REPEATS (Chef TG 14917): first trade per coin by entry time; information only
    SEED=12345,
)
SEAL = 1790467200

if '--rebuild' in sys.argv or not os.path.exists(HERE + '/trades/index.json'):
    for s in ('srcmap.py', 'store.py'):
        r = subprocess.run([sys.executable, HERE + '/' + s]); assert r.returncode == 0, s

# ---- inference exactly as every Blood batch (analyze_xg.py head, the same function audit.py and recost.py use)
_src = open(P + '/blood-exitgrid-2026-09-27/analyze_xg.py').read(); _g = {'__name__': 'axg'}; _a = sys.argv; sys.argv = ['x', '/dev/null', '/dev/null']
_cwd = os.getcwd(); os.chdir(P + '/blood-exitgrid-2026-09-27'); exec(_src[:_src.index('# ---- load:')], _g); os.chdir(_cwd); sys.argv = _a
inference = _g['inference']
def stat(vals, toks, days, seed=CONFIG['SEED']):
    """audit.py's stat(): mean, 95% range, lower = mean - half the range (the explorer's lower bar)"""
    if len(vals) < 3: return dict(n=len(vals), mean=round(float(np.mean(vals)), 2) if len(vals) else None, lower=None, ci=None)
    I = inference(list(vals), list(toks), list(days), seed); lo, hi = I['ci95']
    return dict(n=len(vals), mean=round(I['mean'], 2), ci=[round(lo, 2), round(hi, 2)], lower=round(I['mean'] - (hi - lo) / 2, 2))
def coin_boot(vals, toks, B=CONFIG['A1_BOOT_B'], seed=CONFIG['A1_SEED']):
    """coin-clustered bootstrap: resample coins with replacement (each with ALL its trades); mean = resampled sum / resampled count"""
    coins = sorted(set(toks)); ci = {t: i for i, t in enumerate(coins)}; C = len(coins)
    s = np.zeros(C); c = np.zeros(C)
    for v, t in zip(vals, toks): s[ci[t]] += v; c[ci[t]] += 1
    rng = np.random.default_rng(seed); W = np.zeros((B, C))
    idx = rng.integers(0, C, size=(B, C))
    for b in range(B): W[b] = np.bincount(idx[b], minlength=C)
    bm = (W @ s) / np.maximum(W @ c, 1)
    lo, hi = np.percentile(bm, [2.5, 97.5]); return round(float(lo), 2), round(float(hi), 2)

# ---- the points and the store
S = [s for s in json.load(open(P + '/edge-explorer/data.json'))['strategies'] if s['id'] == 'blood'][0]
DJ, VARS = S['measured'], S['vars']; VIX = {v['id']: i for i, v in enumerate(VARS)}
def pkey(m): return ','.join(map(str, m['lv'])) + '|' + m['test']
IDX = json.load(open(HERE + '/trades/index.json'))
UNREC = {u['pk']: u for u in json.load(open(HERE + '/unrecoverable.json'))}
ROWS = collections.defaultdict(list)
for fam in sorted({v['family'] for v in IDX.values()}):
    with gzip.open(f'{HERE}/trades/{fam}.ndjson.gz', 'rt') as fh:
        for ln in fh:
            r = json.loads(ln)
            for k in ('T', 'sigTs', 'entryTs', 'exitTs'):
                if r.get(k) is not None and r[k] >= SEAL: raise SystemExit('SEALED ROW in the trade store - refused')
            ROWS[r['pk']].append(r)
# ---- A4: the anomaly audit's per-trade flags (H1 dust, H2 winner nobody else sold at), keyed by coin + assessment hour
AUD = {}
for ln in open(P + '/blood-anomaly-audit-2026-09-30/trade_flags.ndjson'):
    f = json.loads(ln)
    AUD[(f['tok'], f['T'])] = dict(H1=bool(f['H1_dust_e'] or f['H1_dust_x'] or f['H1_dust_trig']), H1_thin=bool(f['H1_thin_x']),
                                   H2=bool(f['val'] > 0 and f['sells_at_exit_level'] == 0), H2a=bool(f['H2_flag_a']))

def flags_of(m):
    ex = m.get('extra', '')
    posthoc = bool(m.get('band')) or m['test'] == 'realism re-score' or any(w in ex for w in ('after seeing the data', 'AFTER-THE-FACT', 'AFTER THE FACT', 'POST-HOC'))
    return posthoc, 'R-0115: the ETH→stock-token hop is NOT costed' in ex

C = CONFIG; PTS = []
for i, m in enumerate(DJ):
    pk = pkey(m); posthoc, r0115 = flags_of(m); lower = m['raw_ci'][0] if m.get('raw_ci') else None
    fails = []
    if m.get('cost', 'model') != C['S1_COST']: fails.append(f"cost '{m.get('cost', 'model')}'")
    if C['S1_NO_POSTHOC'] and posthoc: fails.append('post-hoc view (R-0113 class)')
    if C['S1_NO_R0115'] and r0115: fails.append('stock hop not costed (R-0115)')
    if m['n'] < C['S1_MIN_N']: fails.append(f"n {m['n']} < {C['S1_MIN_N']}")
    if lower is None or not lower > C['S1_LOWER_GT']: fails.append(f'lower {lower} <= 0')
    ix = IDX.get(pk)
    p = dict(pk=pk, i=i, test=m['test'], cost=m.get('cost', 'model'), labels={v['id']: v['levels'][m['lv'][VIX[v['id']]]]['label'] for v in VARS if m['lv'][VIX[v['id']]] != v['held']},
             n=m['n'], mean=m['raw'], ci=m.get('raw_ci'), lower=lower, posthoc=posthoc, r0115=r0115,
             recovered=ix is not None, store_match=ix['match'] if ix else None, store_src=ix and dict(family=ix['family'], cell=ix['cell'], band=ix['band'], view=ix['view'], files=ix['src']),
             unrecoverable=(UNREC.get(pk) or {}).get('status'),
             S1=dict(pass_=not fails, fails=fails))
    PTS.append(p)

# ---- A3 neighbours (needs only data.json)
ORD = [VIX[d] for d in C['A3_ORDERED_DIALS']]
bycost = collections.defaultdict(list)
for i, m in enumerate(DJ): bycost[m.get('cost', 'model')].append(i)
for p, m in zip(PTS, DJ):
    near_same, near_any = [], []
    for j in bycost[m.get('cost', 'model')]:
        o = DJ[j]
        if j == p['i'] or DJ[j]['raw'] is None: continue
        diff = [k for k in range(len(m['lv'])) if m['lv'][k] != o['lv'][k]]
        if len(diff) == 1 and diff[0] in ORD and abs(m['lv'][diff[0]] - o['lv'][diff[0]]) == 1:
            (near_same if o['test'] == m['test'] else near_any).append(j)
    use, scope = (near_same, 'same test') if near_same else (near_any, 'any test (none in the same test)')
    pos = sum(1 for j in use if DJ[j]['raw'] > 0)
    share = pos / len(use) if use else None
    p['A3'] = dict(neighbours=len(use), positive=pos, share=None if share is None else round(share, 2), scope=scope if use else None,
                   which=[dict(test=DJ[j]['test'], dial=VARS[[k for k in range(len(DJ[j]['lv'])) if DJ[j]['lv'][k] != m['lv'][k]][0]]['id'], mean=DJ[j]['raw'], n=DJ[j]['n']) for j in use],
                   pass_=bool(use and len(use) >= C['A3_MIN_NEIGHBOURS'] and share >= C['A3_MIN_POS_SHARE']))

# ---- A1, A2, A4, NO REPEATS (need the trades)
for p in PTS:
    R = ROWS.get(p['pk'])
    if not p['recovered'] or not R:
        p['A1'] = p['A2'] = p['A4'] = p['norep'] = None; continue
    v = [r['ret'] for r in R]; tk = [r['tok'] for r in R]
    dy = [(r['T'] // 86400) * 86400 if r.get('T') is not None else r['day'] for r in R]
    eday = {(r['entryTs'] // 86400) if r.get('entryTs') else (r['day'] // 86400) for r in R}
    only_s1 = p['S1']['pass_']
    lo, hi = coin_boot(v, tk)
    by = collections.defaultdict(float); bd = collections.defaultdict(float)
    for x, t, d in zip(v, tk, dy): by[t] += x; bd[d] += x
    tot = sum(v); top = max(by, key=lambda t: by[t]); best = max(bd, key=lambda d: bd[d])
    keep1 = [k for k in range(len(v)) if tk[k] != top]; keepd = [k for k in range(len(v)) if dy[k] != best]
    w1 = stat([v[k] for k in keep1], [tk[k] for k in keep1], [dy[k] for k in keep1])
    wd = stat([v[k] for k in keepd], [tk[k] for k in keepd], [dy[k] for k in keepd])
    tail = len({t for x, t in zip(v, tk) if x >= C['A1_TAIL_HIT']})
    p['A1'] = dict(coin_boot_ci=[lo, hi], coin_boot_lower=lo, pass_=lo > C['A1_LOWER_GT'],
                   info=dict(lower_without_top_coin=w1['lower'], lower_without_best_day=wd['lower'], top_coin=top, top_coin_trades=tk.count(top),
                             top_coin_share=round(by[top] / tot, 3) if tot > 0 else None, best_day=int(best), best_day_share=round(bd[best] / tot, 3) if tot > 0 else None,
                             tail_hit_coins=tail))
    p['A2'] = dict(coins=len(by), entry_days=len(eday), pass_=len(by) >= C['A2_MIN_COINS'] and len(eday) >= C['A2_MIN_DAYS'])
    au = [AUD.get((r['tok'], r.get('T'))) for r in R]; cov = [a for a in au if a]
    h2 = [k for k, a in enumerate(au) if a and a['H2']]
    keep2 = [k for k in range(len(v)) if k not in set(h2)]
    p['A4'] = dict(audit_covered=len(cov), H1_dust=sum(a['H1'] for a in cov), H1_thin_exit=sum(a['H1_thin'] for a in cov), H2_no_seller_at_exit=len(h2),
                   mean_without_H2=round(float(np.mean([v[k] for k in keep2])), 2) if h2 and keep2 else None,
                   entry_print_under_5usd=sum(1 for r in R if r.get('eU') is not None and r['eU'] < C['A4_DUST_USD']),
                   exit_print_under_5usd=sum(1 for r in R if r.get('xU') is not None and r['xU'] < C['A4_DUST_USD']),
                   exit_print_known=sum(1 for r in R if r.get('xU') is not None), note='information only in this pass (no A4 gate set)')
    # NO REPEATS: the first trade on each coin (by entry time; by assessment hour where entry time is missing)
    first = {}
    for k, r in enumerate(R):
        key = r.get('entryTs') if r.get('entryTs') is not None else (r.get('T') if r.get('T') is not None else r['day'])
        if r['tok'] not in first or key < first[r['tok']][0]: first[r['tok']] = (key, k)
    ks = sorted(k for _, k in first.values())
    nr = stat([v[k] for k in ks], [tk[k] for k in ks], [dy[k] for k in ks])
    p['norep'] = dict(norep_mean=nr['mean'], norep_n=nr['n'], norep_ci=nr['ci'], ordered_by='entryTs' if all(R[k].get('entryTs') for k in ks) else 'partial (day only)')
    p['recomputed'] = dict(n=len(v), mean=round(float(np.mean(v)), 2))

# ---- A5 families: union points sharing >= A5_OVERLAP of EACH other's trades (coin + assessment hour)
def tkey(r): return (r['tok'], r['T']) if r.get('T') is not None else ('day', r['tok'], r['day'], r['ret'])
SETS = {p['pk']: {tkey(r) for r in ROWS[p['pk']]} for p in PTS if p['recovered'] and ROWS.get(p['pk'])}
inv = collections.defaultdict(set)
for k, s in SETS.items():
    for t in s: inv[t].add(k)
par = {k: k for k in SETS}
def find(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
pairs = 0
for a, sa in SETS.items():
    cnt = collections.Counter()
    for t in sa: cnt.update(inv[t])
    for b, c in cnt.items():
        if b <= a: continue
        if c / max(len(sa), len(SETS[b])) >= C['A5_OVERLAP']:
            pairs += 1; ra, rb = find(a), find(b)
            if ra != rb: par[ra] = rb
FAMS = collections.defaultdict(list)
for k in SETS: FAMS[find(k)].append(k)
PBY = {p['pk']: p for p in PTS}
def checks(p): return dict(S1=p['S1']['pass_'], A1=bool(p['A1'] and p['A1']['pass_']), A2=bool(p['A2'] and p['A2']['pass_']), A3=p['A3']['pass_'])
def rank(p):
    ck = checks(p); return (sum(ck.values()), ck['S1'], (p['A1'] or {}).get('coin_boot_lower') or -1e9)
fam_out = []
for fid, (root, mem) in enumerate(sorted(FAMS.items(), key=lambda kv: max(rank(PBY[k]) for k in kv[1]), reverse=True)):
    mem.sort(key=lambda k: rank(PBY[k]), reverse=True); rep = PBY[mem[0]]
    for k in mem: PBY[k]['A5'] = dict(family=fid, size=len(mem), representative=(k == mem[0]))
    ck = checks(rep)
    fam_out.append(dict(family=fid, size=len(mem), representative=rep['pk'], rep_checks=ck, rep_all_pass=all(ck.values()),
                        rep_failed=[c for c, ok in ck.items() if not ok], rep_mean=rep['mean'], rep_n=rep['n'], rep_lower=rep['lower'],
                        rep_coin_boot_lower=(rep['A1'] or {}).get('coin_boot_lower'), members=mem))
for p in PTS:
    p.setdefault('A5', None)
    ck = checks(p); p['all_pass'] = all(ck.values()) and p['recovered'] and bool(p['store_match'])
    p['checks'] = ck
cands = [dict(pk=f['representative'], family=f['family'], family_size=f['size'], **{k: PBY[f['representative']][k] for k in ('test', 'labels', 'n', 'mean', 'lower', 'A1', 'A2', 'A3', 'A4', 'norep')})
         for f in fam_out if f['rep_all_pass'] and PBY[f['representative']]['all_pass']]
# candidate trade sets: nested cells (a subset inside a superset) are the same evidence even when the family rule keeps them apart
cpar = {c['pk']: c['pk'] for c in cands}
def cfind(x):
    while cpar[x] != x: x = cpar[x]
    return x
for a in cpar:
    for b in cpar:
        if a < b and len(SETS[a] & SETS[b]) / min(len(SETS[a]), len(SETS[b])) >= C['A5_NESTED']: cpar[cfind(a)] = cfind(b)
roots = sorted({cfind(k) for k in cpar}); 
for c in cands:
    c['trade_set'] = roots.index(cfind(c['pk']))
    c['overlap_with_other_candidates'] = {o['pk']: round(len(SETS[c['pk']] & SETS[o['pk']]) / len(SETS[c['pk']]), 2) for o in cands if o['pk'] != c['pk']}
json.dump(dict(config=CONFIG, points=PTS), open(HERE + '/points.json', 'w'), indent=0, default=str)
json.dump(dict(config=dict(A5_OVERLAP=C['A5_OVERLAP'], trade_key='coin + assessment hour (T)'), overlap_pairs=pairs, families=fam_out), open(HERE + '/families.json', 'w'), indent=0)
json.dump(cands, open(HERE + '/candidates.json', 'w'), indent=1, default=str)
json.dump({p['pk']: p['norep'] for p in PTS if p.get('norep')}, open(HERE + '/norep.json', 'w'), indent=0)

# ---- REPORT.md (<= 40 lines)
rec = [p for p in PTS if p['recovered']]; real = [p for p in PTS if p['cost'] == 'real']
s1 = [p for p in PTS if p['S1']['pass_']]
def cnt(key, pool): return sum(1 for p in pool if p.get(key) and p[key]['pass_'])
near = [f for f in fam_out if not (f['rep_all_pass'] and PBY[f['representative']]['all_pass']) and f['rep_checks']['S1']]
near.sort(key=lambda f: (len(f['rep_failed']), -(f['rep_coin_boot_lower'] or -1e9)))
mism = [p for p in rec if not p['store_match']]
L = ['# EDGE MACHINE stage 1 — screen.py result', '',
     f"Points: {len(PTS)} measured Blood points ({len(real)} at real cost). Trades recovered from existing outputs for {len(rec)} "
     f"(n and mean re-derived and matched to data.json for {len(rec) - len(mism)}; mismatches {len(mism)}); {len(UNREC)} not recovered (unrecoverable.json).",
     f"S1 (real cost · pre-registered · not R-0115 · n ≥ {C['S1_MIN_N']} · lower > 0): **{len(s1)}** pass "
     f"(of {sum(1 for p in PTS if p['n'] >= 30 and p['lower'] is not None and p['lower'] > 0)} with n ≥ 30 and lower > 0; the rest fail on cost class, post-hoc view or R-0115).",
     f"Of the S1 passers — A1 coin-clustered lower > 0: **{cnt('A1', s1)}** · A2 ≥ {C['A2_MIN_COINS']} coins and ≥ {C['A2_MIN_DAYS']} entry days: **{cnt('A2', s1)}** · "
     f"A3 ≥ {C['A3_MIN_POS_SHARE']:.0%} of one-step neighbours positive: **{cnt('A3', s1)}** · all four: **{sum(1 for p in s1 if p['all_pass'])}**.",
     f"⚠️ A1's coin-clustered gate is LOOSER than the explorer's own bar (that takes the widest of iid / coin / day / 2-day-block errors, and with ~9 JUDGE days the day error "
     f"dominates), so A1 removes almost nothing S1 kept. Without the top coin {sum(1 for p in s1 if ((((p['A1'] or {}).get('info') or {}).get('lower_without_top_coin')) or -1) > 0)} of {len(s1)} S1 passers keep "
     f"lower > 0; without the best day {sum(1 for p in s1 if ((((p['A1'] or {}).get('info') or {}).get('lower_without_best_day')) or -1) > 0)} (info only since TG 14912).",
     f"Over all {len(rec)} recovered points: A1 {cnt('A1', rec)} · A2 {cnt('A2', rec)} · A3 {cnt('A3', rec)} (A3 over all {len(PTS)}: {cnt('A3', PTS)}).",
     f"A5: {len(fam_out)} trade families among the recovered points (≥ {C['A5_OVERLAP']:.0%} shared trades both ways; {pairs} linked pairs); "
     f"{len({PBY[p['pk']]['A5']['family'] for p in s1 if PBY[p['pk']].get('A5')})} families hold the {len(s1)} S1 passers.",
     '', f"**Candidates (one per family, passing S1 + A1 + A2 + A3): {len(cands) if cands else 'NONE'}** — but nested (≥ {C['A5_NESTED']:.0%} of the smaller "
     f"cell's trades inside another) they are only **{len({c['trade_set'] for c in cands})} independent trade sets** (set = first number below)."]
for c in cands:
    inf = (c['A1'] or {}).get('info') or {}   # hunter v0: a point with no A1 detail no longer crashes the report
    L.append(f"- [{c['trade_set']}] {c['test'][:24]} · {', '.join(f'{k}={v}' for k, v in c['labels'].items() if k != 'fee')} · n {c['n']} · mean {c['mean']:+.2f} · lower {c['lower']:+.2f} · coin-boot lower {c['A1']['coin_boot_lower']:+.2f} · "
             f"{c['A2']['coins']} coins / {c['A2']['entry_days']} d · w/o top coin {inf['lower_without_top_coin']:+.2f} · w/o best day {inf['lower_without_best_day']:+.2f} · "
             f"top coin {inf['top_coin_share']:.0%} · no-repeats {c['norep']['norep_mean']:+.2f} (n {c['norep']['norep_n']})")
both = [c for c in cands if ((((c['A1'] or {}).get('info') or {}).get('lower_without_top_coin')) or -1) > 0 and ((((c['A1'] or {}).get('info') or {}).get('lower_without_best_day')) or -1) > 0]
L.append(f"Only {len(both)} of {len(cands)} keep lower > 0 both without their top coin AND without their best day. Stage 1 applies NO family-wide correction: every "
         "point read the same spent JUDGE days (K ≈ 3,500 tests; per the explorer notes none passed its own batch's family correction) — a candidate here is a queue entry for V (one fresh read), not an edge.")
L += ['', 'Top 5 "nearly passed" families (representative passes S1; fewest failed checks, then best coin-clustered lower):']
for f in near[:5]:
    p = PBY[f['representative']]; a1 = p['A1'] or {}; inf = a1.get('info', {})
    L.append(f"- fam {f['family']} ({f['size']} pts) {p['test'][:28]} · {', '.join(f'{k}={v}' for k, v in p['labels'].items() if k not in ('dipon',))} · n {p['n']} mean {p['mean']:+.2f} "
             f"lower {p['lower']:+.2f} · FAILS {'+'.join(f['rep_failed'])} · coin-boot lower {a1.get('coin_boot_lower')} · {p['A2']['coins']} coins/{p['A2']['entry_days']} d · "
             f"nbrs {p['A3']['positive']}/{p['A3']['neighbours']} + · top coin {inf.get('top_coin_share')} · tail-hit coins {inf.get('tail_hit_coins')} · no-repeats {p['norep']['norep_mean']} (n {p['norep']['norep_n']})")
L += ['', 'Information columns (not gates): lower without the top coin / best day, top-coin share, tail-hit coins (≥ +50), A4 audit flags, NO REPEATS '
      '(first trade per coin) — all in points.json; norep.json is keyed `lv|test` for the explorer builder.',
      'Limits: model/heavy-cost points were not recovered (they fail S1 on cost); A4 flags exist only for the 48 coins the anomaly audit taped; '
      'the realism re-score rows have no timestamps (day-level identity). Trade families use coin + assessment hour, so the same signal at a '
      'different entry delay or exit counts as the same trade.',
      '', 'Reproduce every count: `cd ' + HERE + ' && python3 screen.py` (uses trades/; `--rebuild` re-derives it from /tmp engine outputs), then',
      "`python3 -c \"import json;d=json.load(open('points.json'))['points'];s=[p for p in d if p['S1']['pass_']];"
      "print(len(d),sum(p['recovered'] for p in d),len(s),*[sum(1 for p in s if p['checks'][k]) for k in ('A1','A2','A3')],sum(p['all_pass'] for p in d))\"`",
      "`python3 -c \"import json;print(len(json.load(open('families.json'))['families']),len(json.load(open('candidates.json'))),len(json.load(open('unrecoverable.json'))))\"`"]
assert len(L) <= 40, len(L)
open(HERE + '/REPORT.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
