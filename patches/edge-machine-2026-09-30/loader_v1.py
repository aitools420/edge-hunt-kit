#!/usr/bin/env python3
"""loader_v1.py - EDGE MACHINE: engine-v1 batch results -> (a) explorer-ready measured Blood records, (b) rows in the per-trade store.
Also owns the ONE mapping between the explorer's Blood dial levels and engine-v1 cell params (both directions).

  python3 loader_v1.py map                         print every Blood dial level -> engine params (or why it cannot be expressed)
  python3 loader_v1.py add <batch dir> [--round N] register a finished run_batch.sh output dir, then rebuild
  python3 loader_v1.py rebuild                     regenerate every output below from the ledger (idempotent)
  python3 loader_v1.py screen                      rebuild, build the merged explorer view, run ./screen.py on it (screen.py is NOT edited)

Outputs (all regenerated from the ledger every time, so a rerun never duplicates anything):
  explorer_points_v1.json        records in build.py's b2_point shape + coords_labels (the stable key; see SEARCH.md "build.py hook")
  trades/v1.ndjson.gz            store rows (store.py's row format, pk = '<lv>|<test>'), JUDGE half, primary view real60h
  trades/index.json              the family 'v1' entries are replaced (store.py's entry format); every other entry is left untouched
  machine/v1_ledger.json         the registered batches      machine/v1_unplaced.json   cells that have no explorer coordinate (+ why)
  machine/data_merged.json       (screen only) data.json + the v1 records not yet in it, with lv at data.json's level numbering
Refuses: a results.json from another engine / cost version than engine/MANIFEST.json; any trade row with a timestamp >= 2026-09-27T00:00Z."""
import json, gzip, os, sys, re, math, collections, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'
DJ_PATH = P + '/edge-explorer/data.json'
MACHINE = os.environ.get('EM_MACHINE_DIR', HERE + '/machine')
STORE = os.environ.get('EM_STORE_DIR', HERE + '/trades')
EXPL_OUT = os.environ.get('EM_EXPLORER_OUT', HERE + '/explorer_points_v1.json')
TEST = 'edge machine v1 (frozen engine, real60h)'
SEAL = 1790467200; TOL = 0.05; SIDE_ROWS = ('tok', 'pair', 'T', 'day', 'sigTs', 'entryTs', 'exitTs', 'reason', 'ret', 'ePk', 'v4e', 'fb', 'pad', 'stock')
MAN = json.load(open(HERE + '/engine/MANIFEST.json'))
# V1.1 (2026-10-02, patches/engine-v1p1-2026-10-02): engine v1.1 = v1 + th 96/120/168 (every hour of the prior th hours), proved byte-identical
# to v1 for th <= 72 (its parity/PARITY.md). Its results are accepted when they carry v1.1's pinned engine sha AND v1's cost version.
_M11 = P + '/engine-v1p1-2026-10-02/engine/MANIFEST.json'                                   # V1.1
MAN11 = json.load(open(_M11)) if os.path.exists(_M11) else None                            # V1.1
ENGINES = {MAN['engine_sha256']: 'v1', **({MAN11['engine_sha256']: 'v1.1'} if MAN11 and MAN11['cost_version'] == MAN['cost_version'] else {})}   # V1.1
TH_OK = lambda th: (0 <= th <= 72) or th in (96, 120, 168)                                  # V1.1: the th values engine v1.1 can express

# ---- engine defaults and dial set: read from prepare_v1.py itself (one source of truth, never copied)
_prep = open(HERE + '/engine/prepare_v1.py').read()
BASE = eval(re.search(r'^BASE = (dict\(.*?\))', _prep, re.M).group(1), {'dict': dict})
DIALS = eval(re.search(r'^DIALS = (\{.*?\})', _prep, re.M | re.S).group(1))

class NotExpressible(Exception):
    pass

# ============================================================== the MAPPING (explorer Blood dial level <-> engine-v1 params)
def _secs(label):
    m = re.fullmatch(r'([\d.]+) (s|min|h|d)', label.strip())
    if not m: raise NotExpressible(f'label {label!r} is not a duration')
    return round(float(m.group(1)) * {'s': 1, 'min': 60, 'h': 3600, 'd': 86400}[m.group(2)])
def _num(L, what):
    v = L.get('v')
    if not isinstance(v, (int, float)): raise NotExpressible(f'{what}: level has no number')
    return v
def _hold(L):
    h = _num(L, 'hold'); s = round(h * 3600)
    if h > 72: raise NotExpressible('hold > 72 h: the latest assessment cut-off engine v1 has (last72 = 09-23 20:00) only lets a 72 h hold finish before the seal')
    return {'hold': s, **({'last72': 1} if h == 72 else {})}      # 72 h: assessments end 09-23 20:00 (as skeleton batch 2's 72 h cells)
def _win(L):
    s = _secs(L['label'])
    if s not in (300, 3600, 86400): raise NotExpressible('engine v1 windows are 5 min, 1 h, 24 h only (15 min has no activity-twin window; others were never built)')
    return {'W': s}
def _th(L):                                                                                   # V1.1
    v = _num(L, 'th')
    if not v: return {}
    th = int(round(v))
    if not TH_OK(th): raise NotExpressible(f'th {v}: engine v1.1 expresses 0-72 (at least th of the prior 72 h) or 96 / 120 / 168 (every one of the prior th hours) only')
    return {'th': th}
NEWDIALS = 'a new-dials (literature review) dial: engine v1 has no such filter (it lives only in the new-dials engine)'
MAP = {
    'pad': {'All labelled launchpads': {}, 'The largest launchpad only': {'padMode': 'L'}, 'All except the largest': {'padMode': 'X'}},
    'age': lambda L: {'age': round(_num(L, 'age') * 3600)},
    'vol': lambda L: {'volMin': float(_num(L, 'vol'))} if _num(L, 'vol') else {},
    'volat': lambda L: {'sdMin': round(_num(L, 'volat') / 100, 6)} if _num(L, 'volat') else {},
    'range': {'All': {}, 'Sideways or up': {'range': 'up'}, 'Trends away': {'range': 'away'},
              'Snaps back': 'engine v1 has no snap-back rule (rangeOk knows only up / away)', 'Up only (24 h change ≥ +5%)': 'proposed level; engine v1 has no +5% rule'},
    'dh': lambda L: {'dh': int(_num(L, 'dh'))} if _num(L, 'dh') else {},
    'th': lambda L: _th(L),                                                                   # V1.1: was the inline lambda, now refuses what v1.1 cannot express
    'buyers': {'All': {}, 'Buyers in the last hour': {'buyMin': 4}, '10+ buyers in the last hour': 'engine v1 forces buyMin to its fixed pre-pass median (4); 10+ cannot be set'},
    'creator': {'All': {}, 'Creator has not sold': {'creator': 'notsold'}},
    'holders': {'All': {}, 'Top 10 hold under half': 'restricted by data: no point-in-time holder source (R-0049)'},
    'dip': lambda L: {'dip': round(_num(L, 'dip') / 100, 6)},
    'win': _win,
    'dipon': {'All pools, merged': {'mode': 'M'}, 'The main pool only': {}},
    'delay': lambda L: {'lat': _secs(L['label'])},
    'tp': lambda L: {'tp': round(1 + _num(L, 'tp') / 100, 6)},
    'hold': _hold,
    'fee': {'All pools': {}, 'Low take (≤1% a side)': {'band': 'LOW'}, 'High take (>1% a side)': {'band': 'HIGH'}, 'V2/V3 pools': {'band': 'V23'},
            'Low, after-the-fact split (LP fee left out, R-0113)': 'POST-HOC split (R-0113): never searched',
            'Hook pools at exactly 1% (after-the-fact split only)': 'POST-HOC split (R-0113): never searched'},
    'hq': {'All': {}}, 'mkt': {'All': {}}, 'wash': {'All': {}}, 'snip': {'All': {}, 'Unknown': {}}, 'tod': {'All': {}},
    'mpq': {'any': {}, 'WETH only': {'quote': 'WETH'}},
    'cap': {'none': {}, '20 positions': {'cap': 20}},
}
VAR_KEYS = {'pad': ('padMode',), 'age': ('age',), 'vol': ('volMin',), 'volat': ('sdMin',), 'range': ('range',), 'dh': ('dh',), 'th': ('th',),
            'buyers': ('buyMin',), 'creator': ('creator',), 'holders': (), 'dip': ('dip',), 'win': ('W',), 'dipon': ('mode',), 'delay': ('lat',),
            'tp': ('tp',), 'hold': ('hold', 'last72'), 'fee': ('band',), 'hq': (), 'mkt': (), 'wash': (), 'snip': (), 'tod': (), 'mpq': ('quote',), 'cap': ('cap',)}
UNSHOWN = ('L', 'cool')                         # engine dials with no explorer dial: a cell may only place if they sit at BASE

def level_params(var, l):
    """engine params for ONE level of one explorer var (only the keys that differ from the engine BASE). Raises NotExpressible."""
    L = var['levels'][l]; lab = L['label']; m = MAP.get(var['id'])
    if m is None: raise NotExpressible(f"dial {var['id']!r} has no mapping (new dial?)")
    if callable(m): p = m(L)
    else:
        if lab not in m:
            if var['id'] in ('hq', 'mkt', 'wash', 'snip', 'tod'): raise NotExpressible(NEWDIALS)
            raise NotExpressible(f'label {lab!r} has no entry in the mapping table')
        p = m[lab]
        if isinstance(p, str): raise NotExpressible(p)
    return {k: v for k, v in p.items() if not (k in BASE and _eq(BASE[k], v))}
def _eq(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
    return a == b
def cell_params(V, lv):
    """explorer lv -> engine params (non-BASE keys only). Raises NotExpressible listing EVERY dial that cannot be expressed."""
    p, bad = {}, []
    for var, l in zip(V, lv):
        try: p.update(level_params(var, l))
        except NotExpressible as e: bad.append(f"{var['id']}={var['levels'][l]['label']}: {e}")
    if bad: raise NotExpressible('; '.join(bad))
    return dict(sorted(p.items()))
def expressible(V, lv):
    try: cell_params(V, lv); return True
    except NotExpressible: return False
def cell_id(params):
    def f(v): return (f'{v:.6f}'.rstrip('0').rstrip('.')) if isinstance(v, float) else str(v)     # never exponent form ('1e+07' is not a legal id)
    return 'v1_' + ('_'.join(f'{k}{f(v)}' for k, v in sorted(params.items())) or 'held')
def lv_of_dials(V, dials):
    """engine dials (results.json 'dials' = BASE + params) -> explorer lv. Raises NotExpressible when no explorer coordinate matches."""
    full = dict(BASE, **dials); bad = []
    for k in UNSHOWN:
        if not _eq(full.get(k), BASE.get(k)): bad.append(f'{k}={full.get(k)} (no explorer dial; must sit at the engine default {BASE.get(k)})')
    known = set(BASE) | {k for ks in VAR_KEYS.values() for k in ks}
    extra = [k for k in full if k not in known]
    if extra: bad.append(f'unmapped engine dials {extra}')
    lv = []
    for var in V:
        keys = VAR_KEYS[var['id']]; want = {k: full.get(k, BASE.get(k)) for k in keys}; hits = []
        for l in range(len(var['levels'])):
            try: p = dict(BASE, **level_params(var, l))
            except NotExpressible: continue
            if all(_eq(want[k], p.get(k, BASE.get(k))) for k in keys): hits.append(l)
        if not hits: bad.append(f"{var['id']}: no level matches {want}"); lv.append(None)
        else: lv.append(var['held'] if var['held'] in hits else hits[0])
    if bad: raise NotExpressible('; '.join(bad))
    return lv

def blood(dj=None):
    d = json.load(open(dj or DJ_PATH)); return [s for s in d['strategies'] if s['id'] == 'blood'][0], d

# ============================================================== loading batches
def _ledger():
    try: L = json.load(open(MACHINE + '/v1_ledger.json')); [b.update(dir=os.path.join(HERE, b['dir'])) for b in L['batches'] if not os.path.isabs(b['dir'])]; return L   # KIT: relative batch dirs resolve under this folder
    except (OSError, ValueError): return dict(batches=[])
def _atomic_json(path, obj, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True); tmp = path + '.tmp'
    json.dump(obj, open(tmp, 'w'), **kw); os.replace(tmp, path)
def check_results(res, path):
    if res.get('engine_sha256') not in ENGINES or res.get('cost_version') != MAN['cost_version']:   # V1.1: v1 or v1.1 (same cost model)
        raise SystemExit(f'{path}: not engine v1 / v1.1 / cost {MAN["cost_version"]} - REFUSED (another engine is a new loader, never this one)')
    if '2026-09-27' not in json.dumps(res.get('data_window', {})): raise SystemExit(f'{path}: no seal in its data window - REFUSED')
def build_records(V, S_measured_keys=None):
    """-> records (explorer), store rows, index entries, unplaced; from every batch in the ledger"""
    led = _ledger(); cells = {}; ESHA = {}   # V1.1
    for b in led['batches']:
        res = json.load(open(b['dir'] + '/results.json')); check_results(res, b['dir']); ESHA[b['dir']] = res['engine_sha256']   # V1.1: the batch's own engine
        for cid, rec in res['cells'].items(): cells[cid] = (b, rec)            # a later batch wins (engine v1 is deterministic: same cell = same numbers)
    rows_by = collections.defaultdict(list)
    for b in led['batches']:
        with gzip.open(b['dir'] + '/trades.ndjson.gz', 'rt') as fh:
            for ln in fh:
                r = json.loads(ln)
                for k in ('T', 'sigTs', 'entryTs', 'exitTs'):
                    if r.get(k) is not None and r[k] >= SEAL: raise SystemExit('SEALED ROW in a v1 trade file - refused')
                if r['half'] == 'JUDGE' and r.get('ret') is not None and cells.get(r['cell'], (None,))[0] is b: rows_by[r['cell']].append(r)
    recs, rows, index, unplaced = [], [], {}, []
    for cid, (b, rec) in sorted(cells.items()):
        J = rec.get('JUDGE') or {}; R = (J.get('real60h') or {}).get('raw') or {}; D = (J.get('real60h') or {}).get('d_vs_A') or {}
        if rec.get('filter'): unplaced.append(dict(cell=cid, batch=b['dir'], why=f"token filter {rec['filter']}: no explorer dial for it")); continue
        try: lv = lv_of_dials(V, rec['dials'])
        except NotExpressible as e: unplaced.append(dict(cell=cid, batch=b['dir'], why=str(e))); continue
        if R.get('mean') is None: unplaced.append(dict(cell=cid, batch=b['dir'], why=f"JUDGE n {J.get('n')} < 3: no statistics")); continue
        coords = {V[i]['id']: l for i, l in enumerate(lv) if l != V[i]['held']}
        g = (J.get('gate') or {}).get('status', {})
        esha = ESHA.get(b['dir'], MAN['engine_sha256'])                                      # V1.1: = MAN's for every v1 batch (output unchanged)
        extra = (f"EDGE MACHINE {ENGINES.get(esha, 'v1')} · frozen engine {esha[:8]} · one cost model real60h: per-pool real costs (R-0111), booked in ETH, "
                 f"TP sold 60 s after it hits, ETH→quote-token hop costed (R-0115) · cell chosen by search.py round {b.get('round')} BEFORE it was run · "
                 f"JUDGE 09-17→09-25 · {J.get('coins', '?')} coins · data gate " + ' '.join(f'{k} {v}' for k, v in sorted(g.items())) +
                 (f" · {J['hop_no_route_left_out']} trade(s) with no ETH route to their quote token left out" if J.get('hop_no_route_left_out') else ''))
        r = dict(test=TEST, data='merged2', cost='real', coords=coords, coords_labels={k: V[i]['levels'][lv[i]]['label'] for i, k in ((i, V[i]['id']) for i in range(len(V))) if k in coords},
                 coords_values={k: V[i]['levels'][lv[i]].get('v') for i, k in ((i, V[i]['id']) for i in range(len(V))) if k in coords},
                 raw=R['mean'], d=D.get('d_mean'), d_ci=D.get('ci95'), d_ci_label='95% range, vs activity twin from the same fee band',
                 raw_ci=R.get('ci95'), raw_ci_label='95% range', n=R['n'], extra=extra, b2=True, d5=R.get('drop5_coins'), coins=J.get('coins'),
                 lv=lv, v1=dict(cell=cid, round=b.get('round'), batch=b['dir'], engine_sha256=esha,   # V1.1
                                 cost_version=MAN['cost_version'],
                                stat_seed=rec.get('stat_seed'), gate=g, top_coin_share=J.get('top_coin_share')))
        recs.append(r)
        pk = ','.join(map(str, lv)) + '|' + TEST
        tr = rows_by.get(cid, [])
        for t in tr: rows.append(dict(pk=pk, **{k: t.get(k) for k in SIDE_ROWS}))
        n, mean = len(tr), (sum(t['ret'] for t in tr) / len(tr) if tr else None)
        index[pk] = dict(i=None, test=TEST, family='v1', cell=cid, band=None, view='real60h (engine v1 primary view)', src=[b['dir'] + '/trades.ndjson.gz'],
                         n=n, mean=None if mean is None else round(mean, 4), explorer_n=r['n'], explorer_mean=r['raw'],
                         match=bool(n == r['n'] and mean is not None and abs(mean - r['raw']) <= TOL), file='trades/v1.ndjson.gz')
    return recs, rows, index, unplaced

def rebuild(V=None):
    if V is None: V = blood()[0]['vars']
    recs, rows, index, unplaced = build_records(V)
    _atomic_json(EXPL_OUT, dict(generated_by='loader_v1.py', test=TEST, engine_sha256=MAN['engine_sha256'], cost_version=MAN['cost_version'],
                                join='build.py hook: see SEARCH.md — resolve coords_labels to level numbers at hook time; lv is at data.json numbering when written',
                                records=recs), indent=1)
    os.makedirs(STORE, exist_ok=True); tmp = STORE + '/v1.ndjson.gz.tmp'
    with gzip.open(tmp, 'wt') as fo:
        for r in rows: fo.write(json.dumps(r, separators=(',', ':')) + '\n')
    os.replace(tmp, STORE + '/v1.ndjson.gz')
    ip = STORE + '/index.json'
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    idx = {k: v for k, v in idx.items() if v.get('family') != 'v1'}; idx.update(index)
    _atomic_json(ip, idx, indent=0)
    _atomic_json(MACHINE + '/v1_unplaced.json', unplaced, indent=1)
    bad = [k for k, v in index.items() if not v['match']]
    print(f'loader_v1: {len(recs)} explorer record(s), {len(rows)} store row(s), {len(unplaced)} unplaced, store mismatches {len(bad)}')
    if bad: raise SystemExit('store rows do not reproduce n/mean for: ' + ', '.join(bad[:5]))
    return recs

def merged_view(recs=None):
    """data.json + the v1 records it does not already hold (same lv and test) -> machine/data_merged.json"""
    S, d = blood()
    if recs is None: recs = json.load(open(EXPL_OUT))['records'] if os.path.exists(EXPL_OUT) else []
    have = {(tuple(m['lv']), m['test']) for m in S['measured']}; add = 0
    for r in recs:
        if (tuple(r['lv']), r['test']) in have: continue
        S['measured'].append({k: v for k, v in r.items() if k not in ('coords_labels', 'coords_values')}); add += 1
    out = MACHINE + '/data_merged.json'; _atomic_json(out, d)
    print(f'merged view: data.json + {add} v1 record(s) -> {out}')
    return out

def run_screen():
    """screen.py on the merged view: open() of the explorer's data.json path is redirected to machine/data_merged.json for this one run"""
    if not os.path.exists(STORE + '/index.json'):                     # screen.py would rebuild the store itself and drop the v1 entries
        for s in ('srcmap.py', 'store.py'):
            assert subprocess.run([sys.executable, HERE + '/' + s]).returncode == 0, s
    recs = rebuild(); mp = merged_view(recs)
    import builtins, runpy
    real_open = builtins.open
    def _open(f, *a, **k):
        if isinstance(f, str) and os.path.abspath(f) == DJ_PATH: f = mp
        return real_open(f, *a, **k)
    builtins.open = _open; argv = sys.argv; sys.argv = [HERE + '/screen.py']
    try: runpy.run_path(HERE + '/screen.py', run_name='__main__')
    finally: builtins.open = real_open; sys.argv = argv

def print_map():
    V = blood()[0]['vars']
    for var in V:
        for l, L in enumerate(var['levels']):
            try: s = json.dumps(level_params(var, l)) or '{}'
            except NotExpressible as e: s = 'NOT EXPRESSIBLE: ' + str(e)
            print(f"{var['id']:8s} {l:2d} {'*' if l == var['held'] else ' '} {L['label'][:40]:40s} {s}")

if __name__ == '__main__':
    a = sys.argv[1:] or ['map']
    if a[0] == 'map': print_map()
    elif a[0] == 'add':
        d = os.path.abspath(a[1]); rnd = int(a[a.index('--round') + 1]) if '--round' in a else None
        res = json.load(open(d + '/results.json')); check_results(res, d)
        led = _ledger(); led['batches'] = [b for b in led['batches'] if b['dir'] != d] + [dict(dir=d, round=rnd, cells=sorted(res['cells']))]
        _atomic_json(MACHINE + '/v1_ledger.json', led, indent=1); rebuild()
    elif a[0] == 'rebuild': rebuild()
    elif a[0] == 'screen': run_screen()
    else: raise SystemExit(__doc__)
