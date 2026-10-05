#!/usr/bin/env python3
"""validate_return.py - check a batch returned by a partner BEFORE anything from it is published (kit/RETURN_SPEC.md).

  python3 kit/validate_return.py <returned batch dir> [--sample K] [--seed S] [--full-pass] [--rerun DIR] [--run-batch PATH] [--no-rerun]

STAGE 1 (cheap, every cell): the returned folder must hold results.json, trades.ndjson.gz, cells.input.json, MANIFEST.used.json and
  runlogs/batch.log.
  * results.json: schema 'edge-machine results v1', engine_sha256 = frozen engine v1, cost_version = v1-real60h-bc18611a45a4, the seal in
    data_window; MANIFEST.used.json carries the same engine/cost labels.
  * which engine RAN (pond #298): those engine_sha256 fields are labels that analyze_v1.py copies from MANIFEST.json, whatever engine ran.
    So every engine pass in results.json must carry the engine's own label 'v1', and runlogs/batch.log must record, for every pass, the
    sha256 of the engine_v1.js file run_batch.sh ran it with (logged since 2026-10-05), equal to the frozen engine's. Like every field of a
    return, the log can be edited: this catches an honest mix-up (a variant run, an older kit), not a forgery; stage 2 is the real check.
  * every cell of cells.input.json is in results.json and vice versa; every trade row belongs to a known cell; NO trade row has T / sigTs /
    entryTs / exitTs >= 1790467200 (2026-09-27T00:00Z); every row carries the frozen engine/cost labels.
  * per cell and half: n = trade rows with a non-null ret, coins, and the mean of ret recomputed from trades.ndjson.gz must equal results.json
    (mean to 1e-6 relative); likewise the real60h twin deltas d_vs_A and d_vs_R (n, coins, d_mean, twin_mean recomputed from ret - twinA and
    ret - twinR; pond #298). That is consistency only: nothing here shows the twins were drawn honestly, and real60 d_vs_A is not checked
    (the rows carry no real60 twin value).
STAGE 2 (the real check, a SAMPLE of cells): K cells are drawn with a fixed seed (a filtered cell brings its base along), written to a fresh
  cells.json with their returned params / filter / base / stat_seed, and re-run here with run_batch.sh. Twin draws depend on which cells
  share the engine pass (pond #284, #298), so this re-run of a subset compares each sampled cell's OWN result: trade rows without pair /
  twinA / twinR, and the results.json record without the d_vs_* blocks, the gate's WR and WA entries and its G5 and G10 statuses (computed
  from the twins). gate.S, its g5_fail included, is still compared. Required: identical for every sampled cell. Anything else = REJECTED.
  The twin draws themselves are therefore not re-verified in this mode.
  --full-pass (stronger, slower: one engine pass for each distinct pass sampled; pond #298 option a): re-run each sampled cell's WHOLE
  original pass instead - the same cells in the same composition, rebuilt the way prepare_v1.py splits cells.input.json - and require every
  cell of those passes to be identical in full, twins, gate and pair included.
Exit 0 = ACCEPTED, 1 = REJECTED, 2 = usage. Writes <returned dir>/VALIDATION.json."""
import sys, os, json, gzip, random, subprocess, collections, math, datetime, re
ENGINE_SHA = 'd1f23fed4ba60bc02eb27d5b2114a63b04015cb9c0ce252ee3efd9005de9db1c'
COST_V = 'v1-real60h-bc18611a45a4'
SEAL = 1790467200
a = sys.argv[1:]
if not a: print(__doc__); sys.exit(2)
B = os.path.abspath(a[0]); opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
K = int(opt('--sample', 3)); SEED = int(opt('--seed', 20261002)); FULL = '--full-pass' in a
KR = os.environ.get('KIT_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RUNB = opt('--run-batch', os.path.join(KR, 'patches/edge-machine-2026-09-30/engine/run_batch.sh'))
problems = []; rep = dict(dir=B, at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
def need(p):
    if not os.path.exists(os.path.join(B, p)): problems.append(f'missing {p}'); return False
    return True
ok = all([need('results.json'), need('trades.ndjson.gz'), need('cells.input.json'), need('MANIFEST.used.json'), need('runlogs/batch.log')])
if not ok: print('REJECTED:', problems); sys.exit(1)
res = json.load(open(os.path.join(B, 'results.json'))); cin = json.load(open(os.path.join(B, 'cells.input.json')))
man = json.load(open(os.path.join(B, 'MANIFEST.used.json')))
if res.get('schema') != 'edge-machine results v1': problems.append('results.json schema')
if res.get('engine_sha256') != ENGINE_SHA or man.get('engine_sha256') != ENGINE_SHA: problems.append('engine is not frozen engine v1')
if res.get('cost_version') != COST_V or man.get('cost_version') != COST_V: problems.append('cost model is not v1-real60h')
if '1790467200' not in json.dumps(res.get('data_window', {})): problems.append('no seal in data_window')
logged = collections.defaultdict(list)            # pond #298: the engine file each pass ran with, as run_batch.sh logged it
for ln in open(os.path.join(B, 'runlogs/batch.log'), errors='replace'):
    m = re.search(r' engine pass (p\d+) \(\s*\d+ cells\)(?: engine_v1\.js sha256 ([0-9a-f]{64}))?', ln)
    if m: logged[m.group(1)].append(m.group(2))
if not res.get('passes'): problems.append('results.json lists no engine pass')
for p in res.get('passes') or []:
    if p.get('engine') != 'v1': problems.append(f"pass {p.get('pass_')}: engine label {p.get('engine')!r} - not the frozen engine's 'v1'")
    hs = logged.get(p.get('pass_'), []); bad = [h for h in hs if h != ENGINE_SHA]
    if not hs: problems.append(f"pass {p.get('pass_')}: no 'engine pass' line in runlogs/batch.log")
    elif bad: problems.append(f"pass {p.get('pass_')}: batch.log records engine_v1.js sha256 {(bad[0] or 'NONE (a kit before 2026-10-05)')[:16]}, not the frozen engine")
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
        for tw in ('A', 'R') if 'real60h' in H else ():   # pond #298 (b): the twin deltas must follow from the rows (analyze_v1.py d_block)
            D = H['real60h'].get('d_vs_' + tw); w = [x for x in v if x.get('twin' + tw) is not None]
            if not isinstance(D, dict): problems.append(f'{cid} {half}: real60h d_vs_{tw} missing'); continue
            if len(w) != D.get('n'): problems.append(f'{cid} {half}: real60h d_vs_{tw} n {D.get("n")} in results, {len(w)} rows with a twin{tw}'); continue
            if len(w) < 3: continue
            if len({x['tok'] for x in w}) != D.get('coins'): problems.append(f'{cid} {half}: real60h d_vs_{tw} coins differ')
            for k, val in (('d_mean', sum(x['ret'] - x['twin' + tw] for x in w) / len(w)), ('twin_mean', sum(x['twin' + tw] for x in w) / len(w))):
                if not (isinstance(D.get(k), (int, float)) and math.isclose(val, D[k], rel_tol=1e-6, abs_tol=0.006)):
                    problems.append(f'{cid} {half}: real60h d_vs_{tw} {k} {D.get(k)} vs rows {val:.4f}')
rep['stage1'] = dict(cells=len(res['cells']), trade_rows=nrows, problems=list(problems))
print(f"stage 1: {len(res['cells'])} cells, {nrows} trade rows, {len(problems)} problem(s)")
if '--no-rerun' not in a and not problems:
    rng = random.Random(SEED); pick = sorted(rng.sample(sorted(res['cells']), min(K, len(res['cells']))))
    by = {c['id']: c for c in cin['cells']}; want = set(pick); ps = cin.get('pass_size', 20)
    for c in pick:
        if by[c].get('base'): want.add(by[c]['base'])
    if FULL:                                        # the sampled cells' WHOLE original passes, cut exactly as prepare_v1.py cuts them
        ps = int(cin.get('pass_size', 40))                                       # prepare_v1.py's default
        eng = sorted(c['id'] for c in cin['cells'] if not c.get('filter'))       # its engine cells (the unfiltered ones), sorted
        chunk = {e: i // ps for i, e in enumerate(eng)}; ecell = lambda c: by[c]['base'] if by[c].get('filter') else c
        keep = {chunk[ecell(c)] for c in pick}; want = {c for c in ids_in if chunk[ecell(c)] in keep}
    sub = dict(cells=[by[c] for c in ids_in if c in want], pass_size=ps)        # input order kept: the passes come out as they did
    RD = os.path.abspath(opt('--rerun', os.path.join(B, '_validate_rerun')))
    os.makedirs(RD, exist_ok=True); json.dump(sub, open(os.path.join(RD, 'cells.sample.json'), 'w'), indent=1)
    print(f"stage 2{' (--full-pass)' if FULL else ''}: re-running {len(want)} cell(s) {sorted(want)} -> {RD}", flush=True)
    rc = subprocess.run(['bash', RUNB, os.path.join(RD, 'cells.sample.json'), os.path.join(RD, 'out')]).returncode
    if rc != 0: problems.append(f'rerun failed (exit {rc}) - see {RD}/out/runlogs/batch.log')
    else:
        r2 = json.load(open(os.path.join(RD, 'out/results.json'))); rows2 = collections.defaultdict(list)
        with gzip.open(os.path.join(RD, 'out/trades.ndjson.gz'), 'rt') as fh:
            for ln in fh: rows2[json.loads(ln)['cell']].append(ln.rstrip('\n'))
        TWIN_ROW = ('pair', 'twinR', 'twinA')
        TWIN_GATE, TWIN_STATUS = ('WR', 'WA'), ('G5', 'G10')   # analyze_v1.py gate(): G5 reads S+WR+WA, G10 reads WR+WA only (pond #298)
        def nopair(lines): return [json.dumps({k: v for k, v in json.loads(x).items() if k not in TWIN_ROW}, sort_keys=True) for x in lines]
        def own(rec):                                   # a cell's own result: no d_vs_* block at any depth, no twin gate entries / statuses
            if isinstance(rec, dict):
                out = {}
                for k, v in rec.items():
                    if k.startswith('d_vs_'): continue
                    if k == 'gate' and isinstance(v, dict):
                        v = {g: x for g, x in v.items() if g not in TWIN_GATE}
                        if isinstance(v.get('status'), dict): v['status'] = {s: x for s, x in v['status'].items() if s not in TWIN_STATUS}
                    out[k] = own(v)
                return out
            if isinstance(rec, list): return [own(v) for v in rec]
            return rec
        cmp = {}
        for c in sorted(want):
            if FULL:    # same cells, same composition: every field must match, twins and pair included (rows sorted: pond #298 item 5)
                same_rec = json.dumps(r2['cells'].get(c), sort_keys=True) == json.dumps(res['cells'][c], sort_keys=True)
                same_rows = sorted(rows2[c]) == sorted(rows[c])
            else:       # pond #284 / #298: twin draws depend on which cells share the pass, so a SUBSET re-run compares the cell's own result
                same_rec = json.dumps(own(r2['cells'].get(c)), sort_keys=True) == json.dumps(own(res['cells'][c]), sort_keys=True)
                same_rows = sorted(nopair(rows2[c])) == sorted(nopair(rows[c]))
            cmp[c] = dict(record_identical=same_rec, rows_identical=same_rows, rows=len(rows[c]))
            if not (same_rec and same_rows): problems.append(f'{c}: rerun differs (record {same_rec}, rows {same_rows})')
        rep['stage2'] = dict(seed=SEED, mode='full-pass' if FULL else 'own-result', sampled=pick, rerun_cells=sorted(want), compare=cmp)
        for c, v in cmp.items(): print(f"  {c}: record {'IDENTICAL' if v['record_identical'] else 'DIFFERS'}, {v['rows']} rows {'IDENTICAL' if v['rows_identical'] else 'DIFFER'}")
rep['problems'] = problems; rep['verdict'] = 'ACCEPTED' if not problems else 'REJECTED'
json.dump(rep, open(os.path.join(B, 'VALIDATION.json'), 'w'), indent=1)
print(rep['verdict'] + ('' if not problems else ': ' + '; '.join(problems[:10])))
sys.exit(0 if not problems else 1)
