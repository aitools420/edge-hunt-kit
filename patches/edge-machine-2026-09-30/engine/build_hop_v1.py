#!/usr/bin/env python3
"""build_hop_v1.py - EDGE MACHINE v1: hop-cost tables for every quote token the batch's V4 entries touch (+ USDG always).
= ../../blood-hunt2-2026-09-29/build_hop.py with ONLY the paths as arguments (poolquote.tsv, qpools.js from this folder) and the
intermediate row file deleted after the tables are built. A token's table depends only on that token's own rows, so a batch-local
table gives the same hop cost as hunt 2's for every token both contain.
1. quote tokens needed = the quote of every V4 entry pool (strategy AND twins) whose quote is not ETH/WETH (poolquote.tsv).
2. rows: the V4 join day files 09-08 -> 09-26 (never the sealed folder), rows whose tok is one of those tokens (grep, then exact filter).
3. qpools.js -> the tokens' pools (fee key, hook, quote class); hop.build() -> hop_tables.pkl. No RPC, no outcome read.
Usage: build_hop_v1.py <hop dir> <poolquote.tsv> <pass.ndjson.gz> [...]"""
import sys, os, json, gzip, subprocess, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import hop
J = os.environ['KIT_ROOT'] + '/patches/v4-join-2026-09-27/out'
OUT, PQ = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
QT = {}
for ln in open(PQ):
    a = ln.rstrip('\n').split('\t'); QT[a[0]] = a[2]
need = {hop.USDG}; seen = collections.Counter()
for f in sys.argv[3:]:
    with gzip.open(f, 'rt') as fh:
        for ln in fh:
            if ln.startswith('{"pr"') or '"ePk"' not in ln: continue
            j = json.loads(ln); pk = j.get('ePk') or ''
            if pk.startswith('v4:') and pk[3:] in QT: need.add(QT[pk[3:]]); seen[QT[pk[3:]]] += 1
open(OUT + '/hop_tokens.txt', 'w').write('\n'.join(sorted(need)) + '\n')
print('quote tokens needed', len(need), flush=True)
subprocess.run(['node', '--max-old-space-size=3000', HERE + '/qpools.js', OUT + '/hop_tokens.txt', OUT + '/hop_qpools.json'], check=True)
pat = OUT + '/hop_tok.pat'; open(pat, 'w').write(''.join('"tok":"%s"\n' % t for t in sorted(need)))
rows = OUT + '/hop_rows.ndjson.gz'
with open(rows, 'wb') as fo:
    for d in range(8, 27):
        f = f'{J}/v4-swaps-2026-09-{d:02d}.ndjson.gz'; assert '/sealed/' not in f
        p1 = subprocess.Popen(['zcat', f], stdout=subprocess.PIPE); p2 = subprocess.Popen(['grep', '-F', '-f', pat], stdin=p1.stdout, stdout=subprocess.PIPE); p1.stdout.close()
        p3 = subprocess.Popen(['gzip', '-1'], stdin=p2.stdout, stdout=fo); p2.stdout.close(); p3.wait(); p2.wait(); p1.wait()   # parent's pipe copies closed: a dying grep/gzip breaks the pipe upstream instead of hanging it (pond #298)
        if p1.returncode != 0 or p2.returncode not in (0, 1) or p3.returncode != 0:   # grep exits 1 on no match; anything else is a broken pipe (pond #284)
            raise SystemExit(f'hop rows: child failed on {f} (zcat {p1.returncode}, grep {p2.returncode}, gzip {p3.returncode})')
qp = json.load(open(OUT + '/hop_qpools.json')); qp = {k: v for k, v in qp.items() if v['tok'] in need}
st = hop.build([rows], qp, OUT + '/hop_tables.pkl')
os.remove(rows)                                                                     # V1: intermediate (rebuildable), 100s of MB
json.dump(dict(tokens=len(need), entries_by_quote=dict(seen.most_common()), table_stat=dict(st)), open(OUT + '/hop_build.json', 'w'), indent=1)
os.symlink(os.path.abspath(PQ), OUT + '/poolquote.tsv') if not os.path.exists(OUT + '/poolquote.tsv') else None
print('tables', dict(st))
