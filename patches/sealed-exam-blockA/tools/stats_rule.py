#!/usr/bin/env python3
"""stats_rule.py <1|2> <run.ndjson.gz> <out.json> — one rule's registered statistics on one engine output.

(1) PRE-FILTER — NEW CODE (sealed-exam-blockA, Option A): keep only the exam cell's rows, and DROP every `skipDepth` row (the V4
    depth floor, FIX 2), counting the drops by kind / twin type. The frozen analyzers predate skipDepth rows and would fail on them
    (no 'on' field). Dropping them is the registered rule: a skipped strategy entry drops its pair, a skipped twin leaves the pair
    with fewer twins, and skips are not pricing failures (engine_wh.js / its PREREG §4).
(2) The FROZEN analyzer's own code (sha256 checked below), exec'd up to '# ---- evaluate ----', exactly as
    twinfix-2026-10-05/tools/d_rule1.py and d_rule2.py do. Its only window constant is JUDGE0 = 2026-09-17; every exam assessment
    hour is >= 2026-09-27, so every exam row falls in its 'JUDGE' half and the analyzer runs unchanged.
(3) Rule #1 (C2P, analyze_st.py): THE BAR = cell_sum('C2P','JUDGE','A', view='heavy', seed=501) (= diag_heavyA.py, the registered
    statistic). Rule #2 (D25L48, analyze_grid.py): THE BAR = cell_block('D25L48','JUDGE', SEED+100*14)['d_heavy_vs_A'].
(4) Data gate: the frozen gate() components; statuses G1/G4/G5/G10 with the DATA_GATE.md thresholds (rule #2's own analyzer
    computes them; rule #1's analyzer predates the status line, so the same thresholds are applied here); _meta for G2.
"""
import sys, json, gzip, os, hashlib, collections
RULE, SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FROZEN = {'1': ('/home/green/projects/patches/blood-stress-2026-09-27/analyze_st.py', '2744c11c835036e03df5692a806557e7b6eac537571fd4d1b0853a44514075ca', 'C2P'),
          '2': ('/home/green/projects/patches/blood-grid-depth-history-2026-09-27/analyze_grid.py', '08aaf46db86f7f6324b0def2f1f8a13d90ea9514539f9a040fe8c219155dd04d', 'D25L48')}
APATH, ASHA, CELL = FROZEN[RULE]
SCR = os.environ.get('EXAM_SCRATCH', '/tmp/claude-1000/-home-green-projects/38d725a6-2ce7-42bb-8559-15f1aac1d852/scratchpad')
os.makedirs(SCR, exist_ok=True)
src_bytes = open(APATH, 'rb').read()
assert hashlib.sha256(src_bytes).hexdigest() == ASHA, f'frozen analyzer {APATH} sha256 mismatch — refused'
# ---- (1) pre-filter ----
tmp = f'{SCR}/stats{RULE}_{os.getpid()}.ndjson' + ('.gz' if RULE == '2' else '')
kept, skipped, meta, needle = 0, collections.Counter(), None, f'"cell":"{CELL}"'.encode()
with gzip.open(SRC, 'rb') as f, (gzip.open(tmp, 'wb') if RULE == '2' else open(tmp, 'wb')) as o:
    for ln in f:
        if ln.startswith(b'{"_meta"'): meta = json.loads(ln)['_meta']; continue
        if needle not in ln: continue
        j = json.loads(ln)
        if j.get('cell') != CELL: continue
        if j.get('skipDepth'):
            skipped[f"{j['kind']}{j.get('tw') or ''}|clip{j.get('clip', 50)}"] += 1; continue
        o.write(ln); kept += 1
# ---- (2) the frozen analyzer's own code ----
os.environ.pop('SMOKE_AS_JUDGE', None)
sys.argv = ['frozen', tmp, '/dev/null']
code = src_bytes.decode()
code = code[:code.index('# ---- evaluate ----')]
G = {'__name__': 'frozen_analyzer'}
exec(compile(code, APATH, 'exec'), G)
os.remove(tmp)
o = dict(rule=int(RULE), cell=CELL, src=SRC, src_sha256=hashlib.sha256(open(SRC, 'rb').read()).hexdigest(), analyzer=APATH, analyzer_sha256=ASHA,
         prefilter=dict(rows_kept=kept, skipDepth_dropped=dict(skipped)))
def thr_status(g, twins):
    S = g['S']
    st = dict(G1='PASS' if (S['priced_share'] or 0) >= 0.60 else 'FAIL',
              G4='PASS' if (S['g4_small_share'] or 0) < 0.20 else 'FAIL',
              G5='PASS' if all(g[k]['g5_fail'] == 0 for k in ['S'] + twins) else 'FAIL',
              G10='PASS' if all((g[k]['priced_share'] or 0) >= 0.60 and (g[k]['g4_small_share'] or 0) < 0.20 for k in twins if g[k]['draws']) else 'FAIL')
    return st
K = ('n', 'coins', 'd_mean', 'd_median', 'ci95', 'se_cons', 'p_one_sided', 'drop5', 'raw_mean', 'raw_ci95', 'twin_mean', 'mde80', 'mean', 'median', 'upper95', 'days')
pick = lambda d: {k: v for k, v in (d or {}).items() if k in K}
if RULE == '1':
    cs = G['cell_sum']
    bar = cs(CELL, 'JUDGE', 'A', view='heavy', seed=501)
    o['bar'] = pick(bar)                                      # THE BAR (d, CI, p, n, coins, drop5) + raw_mean/raw_ci95 (money test)
    o['money_test'] = dict(raw_heavy_mean=bar.get('raw_mean'), raw_heavy_ci95=bar.get('raw_ci95'), n=bar.get('n'),
                           note='heavy-cost raw mean over the strategy trades of the primary pairs (diag_heavyA.py / twinfix d_rule1.py)')
    o['reported'] = dict(base_d_vs_A=pick(cs(CELL, 'JUDGE', 'A', seed=23)), heavy_d_vs_R=pick(cs(CELL, 'JUDGE', 'R', view='heavy', seed=15)),
                         heavy_d_vs_A_v4_entries=pick(cs(CELL, 'JUDGE', 'A', view='heavy', pred=lambda r: r['v4e'], seed=31)),
                         heavy_d_vs_A_v23_entries=pick(cs(CELL, 'JUDGE', 'A', view='heavy', pred=lambda r: not r['v4e'], seed=32)),
                         heavy_d_vs_A_pons=pick(cs(CELL, 'JUDGE', 'A', view='heavy', pred=lambda r: r.get('pad') == 'Pons', seed=33)),
                         heavy_d_vs_A_non_pons=pick(cs(CELL, 'JUDGE', 'A', view='heavy', pred=lambda r: r.get('pad') != 'Pons', seed=34)),
                         FIT_heavy_d_vs_A=pick(cs(CELL, 'FIT', 'A', view='heavy', seed=501)))
    g = G['gate'](CELL, 'JUDGE')
    o['gate'] = dict(components=g, status=thr_status(g, ['WR', 'WA', 'WD']), status_source='DATA_GATE.md thresholds applied to analyze_st.py gate() components')
else:
    i = G['CELLS'].index(CELL); SEEDA = G['SEED']
    b = G['cell_block'](CELL, 'JUDGE', SEEDA + 100 * i)
    o['bar'] = pick(b.get('d_heavy_vs_A'))                   # n / coins here = the PAIRED trades the statistic uses (<= the cell's rows)
    o['bar']['n_rows'], o['bar']['coins_rows'] = b.get('n'), b.get('coins')
    rh = b.get('raw_heavy') or {}
    o['money_test'] = dict(raw_heavy_mean=rh.get('mean'), raw_heavy_ci95=rh.get('ci95'), n=rh.get('n'), coins=rh.get('coins'),
                           note='heavy-cost raw mean over ALL booked strategy trades (analyze_grid.py cell_block raw_heavy)')
    o['reported'] = dict(raw_base=pick(b.get('raw_base')), d_base_vs_A=pick(b.get('d_base_vs_A')), d_heavy_vs_R=pick(b.get('d_heavy_vs_R')),
                         venue={k: dict(n=v.get('n'), raw_heavy=v.get('raw_heavy'), d_heavy_vs_A=pick(v.get('d_heavy_vs_A'))) for k, v in (b.get('venue') or {}).items()},
                         non_pons=pick(b.get('non_pons')), view_depth_floor=pick(b.get('view_depth_floor')),
                         FIT_d_heavy_vs_A=pick((G['cell_block'](CELL, 'FIT', SEEDA + 100 * i + 50) or {}).get('d_heavy_vs_A')))
    g = G['gate'](CELL, 'JUDGE')
    o['gate'] = dict(components={k: v for k, v in g.items() if k != 'status'}, status=g['status'], status_source='analyze_grid.py gate() (frozen)')
# _meta-derived data checks (G2) — the engine's own counters
if meta:
    o['meta'] = {k: meta.get(k) for k in ('rows', 'rowsV4', 'v4skipLiq0', 'univRows', 'bad', 'badV4', 'exits', 'trunc', 'end', 'holes', 'holeAt', 'nofill',
                                          'mergedOutOfOrder', 'v4OutOfOrder', 'reorder', 'wide0', 'endTs', 'sec', 'peakRssMB', 'skipDepth', 'twinDistinct', 'feeSrc')}
    o['meta']['v23Files'] = {d: dict(n=v['n'], first=v['first'], last=v['last']) for d, v in (meta.get('v23Files') or {}).items()}
    o['meta']['v4Files'] = {d: dict(n=v['n'], first=v['first'], last=v['last']) for d, v in (meta.get('v4Files') or {}).items()}
json.dump(o, open(OUT, 'w'), indent=1, default=float)
B = o['bar']
print(f"rule {RULE} {CELL}: n {B.get('n')} coins {B.get('coins')} d {B.get('d_mean')} ci {B.get('ci95')} p {B.get('p_one_sided')} drop5 {B.get('drop5')} | "
      f"money {o['money_test']['raw_heavy_mean']} {o['money_test']['raw_heavy_ci95']} | gate {o['gate']['status']} | skips {dict(skipped)}")
