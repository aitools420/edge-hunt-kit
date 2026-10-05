#!/usr/bin/env python3
"""selftest.py - tests of the kit's own checking code (pond #296 / #298). No tape, no engine pass, no network; ~30 MB of temp files, deleted at the end.
  KIT_ROOT=/path/to/edge-hunt-kit python3 kit/selftest.py [--validator PATH] [--build-hop PATH] [--parity-check PATH]
HOP  engine/build_hop_v1.py's per-day pipe (zcat | grep | gzip), exec'd from the file itself on ~8 MB of synthetic rows: the success path
     keeps exactly the matching rows; a failing zcat, grep or gzip must RAISE within 30 s (a hang is a FAIL).
VAL  kit/validate_return.py on returns built from our published outputs, with a stand-in for run_batch.sh that hands back the same records
     and rows (no engine runs), optionally changed:
     stage 1      no problem on any published batch; a made-up real60h d_vs_A / d_vs_R (n or d_mean) is rejected; so is a return whose
                  batch.log records another engine_v1.js sha256 or none, that has no batch.log, or whose pass is labelled other than 'v1';
     stage 2      what twin draws change (gate WR / WA, status G5 / G10, d_vs_*, twinA / twinR / pair, row order) is accepted; a change in
                  the cell's own result (gate.S incl. its g5_fail, status G1, the raw mean, a row field) is rejected;
     --full-pass  re-runs exactly the sampled cells' original passes (checked against prepare_v1.py's own split) and rejects any twin
                  difference.
PAR  kit/parity_check.py on our published parity outputs: PARITY only when runlogs/batch.log names the frozen engine_v1.js for every pass.
To watch a test fail, point it at older code:  git show 8c4b2e4:kit/validate_return.py > /tmp/v.py; python3 kit/selftest.py --validator /tmp/v.py
Exit 0 = every test passed."""
import sys, os, json, gzip, shutil, signal, subprocess, tempfile
KR = os.environ.get('KIT_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
E = os.path.join(KR, 'patches/edge-machine-2026-09-30/engine'); PUB = os.path.join(KR, 'patches/edge-machine-2026-09-30/machine/v1_batches')
a = sys.argv[1:]; opt = lambda k, d: os.path.abspath(a[a.index(k) + 1]) if k in a else d
VAL = opt('--validator', os.path.join(KR, 'kit/validate_return.py')); HOP = opt('--build-hop', os.path.join(E, 'build_hop_v1.py'))
PAR = opt('--parity-check', os.path.join(KR, 'kit/parity_check.py'))
ENGINE_SHA = json.load(open(os.path.join(E, 'MANIFEST.json')))['engine_sha256']
T = tempfile.mkdtemp(prefix='kit-selftest-'); fails = []
def check(name, ok, why=''):
    print(('PASS  ' if ok else 'FAIL  ') + name + ('' if ok else f'   <- {why}'), flush=True)
    if not ok: fails.append(name)

# ------------------------------------------------------------------ HOP: the per-day pipe of build_hop_v1.py, exec'd from the file under test
HARNESS = r'''
import sys, types, subprocess as sp
src, D, case = sys.argv[1:4]
L = open(src).read().split('\n'); i = next(k for k, l in enumerate(L) if l.strip() == 'for d in range(8, 27):'); body = []
for l in L[i + 1:]:
    if l.strip() and not l.startswith(' ' * 8): break
    body.append(l[8:])
def Popen(args, **kw):               # the failures under test: a grep that cannot start its search; a gzip that dies after 1 kB
    if case == 'grep' and args[0] == 'grep': args = ['grep', '-F', '-f', D + '/no-such-pattern-file']
    if case == 'gzip' and args[0] == 'gzip': args = ['sh', '-c', 'head -c 1000 > /dev/null; exit 1']
    return sp.Popen(args, **kw)
with open(D + '/rows.gz', 'wb') as fo:
    g = dict(J=D + '/out', d=8, pat=D + '/tok.pat', fo=fo, subprocess=types.SimpleNamespace(Popen=Popen, PIPE=sp.PIPE))
    try: exec('\n'.join(body), g)
    except SystemExit as e: print('RAISED', e); sys.exit(3)
print('NO RAISE')
'''
syn = os.path.join(T, 'v4-day.ndjson.gz'); want = []
with gzip.open(syn, 'wt', compresslevel=1) as f:                    # ~8 MB of rows, 2 in 3 for the token in the pattern
    for k in range(120000):
        ln = '{"ts":%d,"pool":"0x%06x","tok":"%s","amt":%d}' % (1789000000 + k, k, '0xbb' if k % 3 == 0 else '0xaa', k * 7919 % 100000)
        f.write(ln + '\n')
        if k % 3: want.append(ln)
def hop(case):
    D = os.path.join(T, 'hop-' + case); os.makedirs(D + '/out'); open(D + '/tok.pat', 'w').write('"tok":"0xaa"\n')
    if case != 'zcat': shutil.copy(syn, D + '/out/v4-swaps-2026-09-08.ndjson.gz')          # zcat: the day file is missing
    p = subprocess.Popen([sys.executable, '-c', HARNESS, HOP, D, case], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    try: return p.communicate(timeout=30)[0], p.returncode, D
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); p.communicate(); return '', 'HANG', D       # kills the harness AND its zcat / grep / gzip
out, rc, D = hop('ok')
got = gzip.open(D + '/rows.gz', 'rt').read().split('\n')[:-1] if rc == 0 else []
check('HOP success path: exactly the matching rows, nothing raised', rc == 0 and got == want, f'exit {rc}, {len(got)} rows vs {len(want)} {out.strip()[-160:]}')
for case in ('zcat', 'grep', 'gzip'):
    out, rc, D = hop(case)
    check(f'HOP a failing {case} raises instead of hanging', rc == 3 and 'hop rows: child failed' in out,
          'HUNG for 30 s (killed)' if rc == 'HANG' else f'exit {rc}: {out.strip()[-160:]}')

# ------------------------------------------------------------------ VAL: validate_return.py, with a stand-in for run_batch.sh
STANDIN = r'''
import sys, os, json, gzip, random
cells, O = sys.argv[1:3]; SRC, MODE = os.environ['STANDIN_SRC'], os.environ['STANDIN_MODE']; os.makedirs(O, exist_ok=True)
ids = [c['id'] for c in json.load(open(cells))['cells']]
res = json.load(open(SRC + '/results.json')); rec = {c: res['cells'][c] for c in ids}
pairs = [(l.rstrip('\n'), json.loads(l)) for l in gzip.open(SRC + '/trades.ndjson.gz', 'rt')]
pairs = [(l, x) for l, x in pairs if x['cell'] in rec]; rows = [x for _, x in pairs]
flip = lambda s: 'FAIL' if s == 'PASS' else 'PASS'
if MODE != 'same':                      # what another composition of the pass changes: the twin draws, and nothing else
    for r in rec.values():
        for half in ('JUDGE', 'FIT'):
            H = r.get(half)
            if not H: continue
            G = H['gate']
            for w, dd in (('WR', 11), ('WA', -1)):
                for k in ('draws', 'booked'): G[w][k] += dd
                G[w]['hop_exit_fallback'] += 1; G[w]['skip_depth_floor'] += 2; G[w]['g5_fail'] += 1; G[w]['priced_share'] = 0.5
            for s in ('G5', 'G10'): G['status'][s] = flip(G['status'][s])
            for view in ('real60h', 'real60'):
                for k in ('d_vs_A', 'd_vs_R'):
                    if k in H.get(view, {}): H[view][k]['n'] += 1; H[view][k]['d_mean'] = (H[view][k].get('d_mean') or 0) + 0.37
    for x in rows:
        x['pair'] += 1000; x['twinR'] = None
        if x['twinA'] is not None: x['twinA'] = round(x['twinA'] + 0.5, 6)
    random.Random(7).shuffle(rows)
c0 = sorted(rec)[0]; J = rec[c0]['JUDGE']; r0 = next(x for x in rows if x['cell'] == c0)   # an OWN change, in a cell that is compared
if MODE == 'own_S': J['gate']['S']['booked'] += 1
if MODE == 'own_g5': J['gate']['S']['g5_fail'] += 1
if MODE == 'own_G1': J['gate']['status']['G1'] = flip(J['gate']['status']['G1'])
if MODE == 'own_mean': J['real60h']['raw']['mean'] += 0.01
if MODE == 'own_row': r0['exitTs'] += 60
json.dump(dict(res, cells=rec), open(O + '/results.json', 'w'), indent=1)
with gzip.open(O + '/trades.ndjson.gz', 'wt') as f:
    for ln in ([l for l, _ in pairs] if MODE == 'same' else [json.dumps(x, separators=(',', ':')) for x in rows]): f.write(ln + '\n')
'''
open(os.path.join(T, 'standin.py'), 'w').write(STANDIN)
RUNB = os.path.join(T, 'run_batch_standin.sh'); open(RUNB, 'w').write('#!/bin/bash\nexec python3 "$(dirname "$0")/standin.py" "$@"\n')
BASE = dict(dip=0.20, W=3600, L=0, age=86400, lat=60, tp=1.30, hold=86400, cool=21600, mode='P')    # prepare_v1.py BASE
def cells_of(res):                     # a cells.input.json for a published results.json
    out = []
    for cid, r in res['cells'].items():
        c = dict(id=cid, stat_seed=r['stat_seed'])
        if r.get('filter'): c.update(base=r['engine_cell'], filter=r['filter'])
        else: c['params'] = {k: v for k, v in r['dials'].items() if BASE.get(k, '-') != v}
        out.append(c)
    return out
def ret_dir(name, src, cells=None, pass_size=None, edit=None, log='ok'):
    """a returned batch folder: results.json (optionally edited), trades.ndjson.gz, cells.input.json, MANIFEST.used.json, runlogs/batch.log"""
    D = os.path.join(T, name); os.makedirs(D + '/runlogs')
    res = json.load(open(src[0]))
    if edit: edit(res)
    json.dump(res, open(D + '/results.json', 'w'), indent=1); shutil.copy(src[1], D + '/trades.ndjson.gz')
    cj = dict(cells=cells if cells is not None else cells_of(res), **({'pass_size': pass_size} if pass_size else {}))
    json.dump(cj, open(D + '/cells.input.json', 'w'), indent=1); shutil.copy(os.path.join(E, 'MANIFEST.json'), D + '/MANIFEST.used.json')
    if log != 'none':
        h = {'ok': ENGINE_SHA, 'other': 'e1d32ecf' + '0' * 56}.get(log)                   # 'old': the line a kit before 2026-10-05 wrote
        with open(D + '/runlogs/batch.log', 'w') as f:
            for p in res['passes']: f.write(f"2026-10-05T00:00:00Z engine pass {p['pass_']} (20 cells)" + (f' engine_v1.js sha256 {h}' if h else '') + '\n')
    return D
nrun = [0]
def validate(D, *extra, mode='same'):
    nrun[0] += 1; RD = os.path.join(D, f'rerun{nrun[0]}')
    p = subprocess.run([sys.executable, VAL, D, '--run-batch', RUNB, '--rerun', RD, *extra], capture_output=True, text=True,
                       env=dict(os.environ, STANDIN_SRC=D, STANDIN_MODE=mode))
    try: v = json.load(open(D + '/VALIDATION.json')); os.remove(D + '/VALIDATION.json')
    except Exception: v = {}
    return p.returncode, v, (p.stdout + p.stderr).strip()[-300:], RD
SRC = {'parity': (E + '/parity/results_v1_parity.json', E + '/parity/trades_v1_parity.ndjson.gz')}
for b in ('machine-round_1', 'blood-next-2026-10-02', 'blood-fill-2026-10-01', 'blood-cross-2026-10-01'): SRC[b] = (f'{PUB}/{b}/results.json', f'{PUB}/{b}/trades.ndjson.gz')
PAR_CELLS = json.load(open(E + '/parity/cells_parity.json'))['cells']

# stage 1: honest outputs (every published batch), made-up twin deltas, and which engine ran
for b in SRC:
    rc, v, out, _ = validate(ret_dir('s1-' + b, SRC[b], cells=PAR_CELLS if b == 'parity' else None), '--no-rerun')
    check(f'VAL stage 1 accepts our published {b} ({(v.get("stage1") or {}).get("cells")} cells)', rc == 0 and v.get('verdict') == 'ACCEPTED', out)
def bump(blk, k, by):
    def f(res): r = res['cells'][sorted(res['cells'])[0]]['JUDGE']['real60h'][blk]; r[k] = r[k] + by
    return f
for name, edit in (('d_vs_R d_mean (+0.05)', bump('d_vs_R', 'd_mean', 0.05)), ('d_vs_A d_mean (-1.5)', bump('d_vs_A', 'd_mean', -1.5)),
                   ('d_vs_A n (+1)', bump('d_vs_A', 'n', 1))):
    rc, v, out, _ = validate(ret_dir('s1-made-up-' + name.split()[0] + name.split()[1], SRC['machine-round_1'], edit=edit), '--no-rerun')
    probs = (v.get('stage1') or {}).get('problems', [])
    check(f'VAL stage 1 rejects a made-up {name}', rc == 1 and any('d_vs_' in p for p in probs), out)
for name, kw in (('a batch.log that records another engine_v1.js sha256', dict(log='other')),
                 ('a batch.log with no engine sha256 (a kit before 2026-10-05)', dict(log='old')),
                 ('a return without runlogs/batch.log', dict(log='none')),
                 ("an engine pass labelled 'v1-rowkey' (a marked variant)", dict(edit=lambda r: r['passes'][0].update(engine='v1-rowkey')))):
    rc, v, out, _ = validate(ret_dir('s1-engine-' + kw.get('log', 'label'), SRC['machine-round_1'], **kw), '--no-rerun')
    check(f'VAL stage 1 rejects {name}', rc == 1, out)

# stage 2, default: a re-run of the sampled cells alone compares each cell's OWN result
R1 = ret_dir('s2', SRC['machine-round_1'])
for mode, expect, name in (('same', 0, 'accepts an identical re-run'),
                           ('twins', 0, 'accepts a re-run whose twin draws differ (gate WR/WA, G5/G10, d_vs_*, twinA/twinR, pair, row order)'),
                           ('own_S', 1, 'rejects a changed gate.S booked'), ('own_g5', 1, 'rejects a changed gate.S g5_fail'),
                           ('own_G1', 1, 'rejects a changed status G1'), ('own_mean', 1, 'rejects a changed JUDGE real60h raw mean'),
                           ('own_row', 1, "rejects a changed trade row (exitTs)")):
    rc, v, out, _ = validate(R1, mode=mode); cmp = (v.get('stage2') or {}).get('compare') or {}
    differs = any(not (x['record_identical'] and x['rows_identical']) for x in cmp.values())
    check(f'VAL stage 2 {name}', rc == expect and bool(cmp) and differs == bool(expect), out)

# stage 2, --full-pass: the sampled cells' whole ORIGINAL passes (parity cells cut into passes of 2 engine cells; filtered cells follow their base)
def split(cells_file):
    o = tempfile.mkdtemp(dir=T); subprocess.run([sys.executable, E + '/prepare_v1.py', cells_file, o], check=True, capture_output=True)
    return [open(f'{o}/passes/{f}').read().split() for f in sorted(os.listdir(o + '/passes'))], json.load(open(o + '/cellmap.json'))
FP = ret_dir('full', SRC['parity'], cells=PAR_CELLS, pass_size=2); orig, cmap = split(FP + '/cells.input.json')
for mode, expect, name in (('same', 0, 'accepts an identical re-run'), ('twins', 1, 'rejects twin-draw differences (same composition)')):
    rc, v, out, RD = validate(FP, '--full-pass', '--sample', '2', mode=mode); s2 = v.get('stage2') or {}
    need = [ch for ch in orig if any(cmap[c]['engine_cell'] in ch for c in s2.get('sampled', []))]
    cells = sorted(c for c in cmap if any(cmap[c]['engine_cell'] in ch for ch in need))
    got = split(RD + '/cells.sample.json')[0] if os.path.exists(RD + '/cells.sample.json') else None
    check(f'VAL --full-pass ({mode}) re-runs exactly the original passes of {s2.get("sampled")}: {need}', bool(need) and got == need
          and sorted(s2.get('rerun_cells', [])) == cells and sorted(s2.get('compare') or {}) == cells, f're-ran {got}, {s2.get("rerun_cells")}')
    check(f'VAL --full-pass {name}', rc == expect and bool(s2.get('compare')), out)

# ------------------------------------------------------------------ PAR: parity_check.py, our parity outputs as the run, with each kind of batch.log
for log, expect, name in (('ok', 0, 'PARITY when batch.log names the frozen engine file'), ('other', 1, 'NO PARITY when batch.log names another engine file'),
                          ('old', 1, 'NO PARITY when batch.log records no engine sha256'), ('none', 1, 'NO PARITY without runlogs/batch.log')):
    p = subprocess.run([sys.executable, PAR, ret_dir('par-' + log, SRC['parity'], cells=PAR_CELLS, log=log)], capture_output=True, text=True,
                       env=dict(os.environ, KIT_ROOT=KR))
    check(f'PAR parity_check.py: {name}', p.returncode == expect, (p.stdout + p.stderr).strip()[-200:])

shutil.rmtree(T, ignore_errors=True)
print(f'selftest: {len(fails)} FAILED' if fails else 'selftest: ALL PASS'); sys.exit(1 if fails else 0)
