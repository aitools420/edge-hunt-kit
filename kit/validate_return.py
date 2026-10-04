#!/usr/bin/env python3
"""validate_return.py - check a batch returned by a partner BEFORE anything from it is published (kit/RETURN_SPEC.md).

  python3 kit/validate_return.py <returned batch dir> [--sample K] [--seed S] [--rerun DIR] [--run-batch PATH] [--no-rerun]

STAGE 1 (cheap, every cell): the returned folder must hold results.json, trades.ndjson.gz, cells.input.json, MANIFEST.used.json.
  * results.json: schema 'edge-machine results v1', engine_sha256 = frozen engine v1, cost_version = v1-real60h-bc18611a45a4, the seal in
    data_window; MANIFEST.used.json carries the same engine/cost labels.
  * every cell of cells.input.json is in results.json and vice versa; every trade row belongs to a known cell; NO trade row has T / sigTs /
    entryTs / exitTs >= 1790467200 (2026-09-27T00:00Z); every row carries the frozen engine/cost labels.
  * per cell and half: n = trade rows with a non-null ret, coins, and the mean of ret recomputed from trades.ndjson.gz must equal results.json
    (mean to 1e-6 relative).
STAGE 2 (the real check, a SAMPLE of cells): K cells are drawn with a fixed seed (a filtered cell brings its base along), written to a fresh
  cells.json with their returned params / filter / base / stat_seed, and re-run here with run_batch.sh. Required: for every sampled cell,
  results.json cell record IDENTICAL (JSON-equal) and the cell's trade rows IDENTICAL (sorted), both without the per-pass pair counter and the twin-relative
  fields, which depend on which cells share the pass (pond #284). Anything else = REJECTED.
Exit 0 = ACCEPTED, 1 = REJECTED, 2 = usage. Writes <returned dir>/VALIDATION.json."""
import sys, os, json, gzip, random, subprocess, collections, math, datetime
ENGINE_SHA = 'd1f23fed4ba60bc02eb27d5b2114a63b04015cb9c0ce252ee3efd9005de9db1c'
COST_V = 'v1-real60h-bc18611a45a4'
SEAL = 1790467200
a = sys.argv[1:]
if not a: print(__doc__); sys.exit(2)
B = os.path.abspath(a[0]); opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
K = int(opt('--sample', 3)); SEED = int(opt('--seed', 20261002))
KR = os.environ.get('KIT_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RUNB = opt('--run-batch', os.path.join(KR, 'patches/edge-machine-2026-09-30/engine/run_batch.sh'))
problems = []; rep = dict(dir=B, at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
def need(p):
    if not os.path.exists(os.path.join(B, p)): problems.append(f'missing {p}'); return False
    return True
ok = all([need('results.json'), need('trades.ndjson.gz'), need('cells.input.json'), need('MANIFEST.used.json')])
if not ok: print('REJECTED:', problems); sys.exit(1)
res = json.load(open(os.path.join(B, 'results.json'))); cin = json.load(open(os.path.join(B, 'cells.input.json')))
man = json.load(open(os.path.join(B, 'MANIFEST.used.json')))
if res.get('schema') != 'edge-machine results v1': problems.append('results.json schema')
if res.get('engine_sha256') != ENGINE_SHA or man.get('engine_sha256') != ENGINE_SHA: problems.append('engine is not frozen engine v1')
if res.get('cost_version') != COST_V or man.get('cost_version') != COST_V: problems.append('cost model is not v1-real60h')
if '1790467200' not in json.dumps(res.get('data_window', {})): problems.append('no seal in data_window')
ids_in = [c['id'] for c in cin['cells']]
if sorted(ids_in) != sorted(res['cells']): problems.append(f'cells differ: input {len(ids_in)} vs results {len(res["cells"])}')
rows = collections.defaultdict(list); nrows = 0
with gzip.open(os.path.join(B, 'trades.ndjson.gz'), 'rt') as fh:
    for ln in fh:
        nrows += 1; r = json.loads(ln)
        if r.get('cell') not in res['cells']: problems.append(f"row for unknown cell {r.get('cell')}"); continue
        if any((r.get(k) or 0) >= SEAL for k in ('T', 'sigTs', 'entryTs', 'exitTs')): problems.append(f"SEALED ROW in {r['cell']}"); continue
        if r.get('engine_sha256') != ENGINE_SHA or r.get('cost_version') != COST_V: problems.append(f"row labels in {r['cell']}"); continue
        rows[r['cell']].append(ln.rstrip('\n'))
if res.get('trades') is not None and res['trades'] != nrows: problems.append(f"results.json says {res['trades']} trade rows, file has {nrows}")
for cid, rec in res['cells'].items():
    for half in ('JUDGE', 'FIT'):
        H = rec.get(half)
        if not H: continue
        v = [json.loads(x) for x in rows[cid]]; v = [x for x in v if x['half'] == half and x['ret'] is not None]
        if len(v) != H.get('n'): problems.append(f'{cid} {half}: n {H.get("n")} in results, {len(v)} rows'); continue
        if len({x['tok'] for x in v}) != H.get('coins'): problems.append(f'{cid} {half}: coins differ')
        raw = (H.get('real60h') or {}).get('raw') or {}
        if v and raw.get('mean') is not None:
            m = sum(x['ret'] for x in v) / len(v)
            if not math.isclose(m, raw['mean'], rel_tol=1e-6, abs_tol=0.006): problems.append(f'{cid} {half}: mean {raw["mean"]} vs rows {m:.4f}')
rep['stage1'] = dict(cells=len(res['cells']), trade_rows=nrows, problems=list(problems))
print(f"stage 1: {len(res['cells'])} cells, {nrows} trade rows, {len(problems)} problem(s)")
if '--no-rerun' not in a and not problems:
    rng = random.Random(SEED); pick = sorted(rng.sample(sorted(res['cells']), min(K, len(res['cells']))))
    by = {c['id']: c for c in cin['cells']}; want = set(pick)
    for c in pick:
        if by[c].get('base'): want.add(by[c]['base'])
    sub = dict(cells=[by[c] for c in ids_in if c in want], pass_size=cin.get('pass_size', 20))
    RD = os.path.abspath(opt('--rerun', os.path.join(B, '_validate_rerun')))
    os.makedirs(RD, exist_ok=True); json.dump(sub, open(os.path.join(RD, 'cells.sample.json'), 'w'), indent=1)
    print(f'stage 2: re-running {len(want)} cell(s) {sorted(want)} -> {RD}', flush=True)
    rc = subprocess.run(['bash', RUNB, os.path.join(RD, 'cells.sample.json'), os.path.join(RD, 'out')]).returncode
    if rc != 0: problems.append(f'rerun failed (exit {rc}) - see {RD}/out/runlogs/batch.log')
    else:
        r2 = json.load(open(os.path.join(RD, 'out/results.json'))); rows2 = collections.defaultdict(list)
        with gzip.open(os.path.join(RD, 'out/trades.ndjson.gz'), 'rt') as fh:
            for ln in fh: rows2[json.loads(ln)['cell']].append(ln.rstrip('\n'))
        TWIN_ROW = ('pair', 'twinR', 'twinA')
        def nopair(lines): return [json.dumps({k: v for k, v in json.loads(x).items() if k not in TWIN_ROW}, sort_keys=True) for x in lines]
        def own(rec):                                   # drop every twin-relative block (d_vs_A, d_vs_R, ...) at any depth
            if isinstance(rec, dict): return {k: own(v) for k, v in rec.items() if not k.startswith('d_vs_')}
            if isinstance(rec, list): return [own(v) for v in rec]
            return rec
        cmp = {}
        for c in sorted(want):
            # pond #284: 'pair' is one counter per engine pass, and twin draws depend on which cells share the pass, so a re-run of a
            # SUBSET compares the cell's own result only: rows without pair / twin fields, records without the twin-relative blocks.
            same_rec = json.dumps(own(r2['cells'][c]), sort_keys=True) == json.dumps(own(res['cells'][c]), sort_keys=True)
            same_rows = sorted(nopair(rows2[c])) == sorted(nopair(rows[c]))
            cmp[c] = dict(record_identical=same_rec, rows_identical=same_rows, rows=len(rows[c]))
            if not (same_rec and same_rows): problems.append(f'{c}: rerun differs (record {same_rec}, rows {same_rows})')
        rep['stage2'] = dict(seed=SEED, sampled=pick, rerun_cells=sorted(want), compare=cmp)
        for c, v in cmp.items(): print(f"  {c}: record {'IDENTICAL' if v['record_identical'] else 'DIFFERS'}, {v['rows']} rows {'IDENTICAL' if v['rows_identical'] else 'DIFFER'}")
rep['problems'] = problems; rep['verdict'] = 'ACCEPTED' if not problems else 'REJECTED'
json.dump(rep, open(os.path.join(B, 'VALIDATION.json'), 'w'), indent=1)
print(rep['verdict'] + ('' if not problems else ': ' + '; '.join(problems[:10])))
sys.exit(0 if not problems else 1)
