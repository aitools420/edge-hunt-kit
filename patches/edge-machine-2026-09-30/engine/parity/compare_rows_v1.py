#!/usr/bin/env python3
"""compare_rows_v1.py - PARITY, row level: engine_v1.js output vs a parent batch's engine output, for the named cells. = the token-filter
batch's compare_rows.py generalised: every non-probe row, field by field, after removing `u` and `pair` (global counters, replaced by the
signal's own key tok + sigTs so the twin -> signal link is compared too) and the fields the parent does not write (v1 adds `tf` on strategy
rows, absent from lf/h3 parents; `eQ`, absent from lf/tf parents) - a field the parent DOES write is compared. Probes compared with their uid mapped to the position's key. Multiset compare; counts only.
Usage: compare_rows_v1.py <v1.ndjson.gz> <parent.ndjson.gz> <cell> [<cell> ...]"""
import gzip, json, sys, collections, hashlib
A, B, CELLS = sys.argv[1], sys.argv[2], set(sys.argv[3:])
def load(p, drop):
    rows, probes = [], []
    with gzip.open(p, 'rt') as fh:
        for ln in fh:
            if ln.startswith('{"pr":'): probes.append(json.loads(ln)['pr']); continue
            if ln.startswith('{"_meta"'): continue
            j = json.loads(ln)
            if j.get('cell') in CELLS: rows.append(j)
    sk = {(j['cell'], j['pair']): (j['tok'], j['sigTs']) for j in rows if j['kind'] == 'S'}
    uk, out, keys = {}, collections.Counter(), set()
    for j in rows:
        uk.setdefault(j['u'], (j['cell'], j['kind'], j.get('tw'), j.get('rep'), j['tok'], j['sigTs']))
        keys |= set(j)
        d = {k: v for k, v in j.items() if k not in ('u', 'pair') and k not in drop}; d['_signal'] = sk.get((j['cell'], j['pair']))
        out[json.dumps(d, sort_keys=True)] += 1
    pr = collections.Counter(json.dumps([uk[a[0]]] + a[1:]) for a in probes if a[0] in uk)
    return out, pr, len(rows), keys
_, _, _, kb = load(B, set())
drop = {k for k in ('tf', 'eQ') if k not in kb}                        # fields v1 writes that this parent does not
a, pa, na, _ = load(A, drop); b, pb, nb, _ = load(B, drop)
h = lambda c: hashlib.sha256('\n'.join(sorted(k + '\t' + str(v) for k, v in c.items())).encode()).hexdigest()[:16]
per = {}
for c in sorted(CELLS):
    ca = sum(v for k, v in a.items() if json.loads(k)['cell'] == c); cb = sum(v for k, v in b.items() if json.loads(k)['cell'] == c)
    per[c] = dict(rows_v1=ca, rows_parent=cb)
print(json.dumps(dict(cells=sorted(CELLS), dropped_fields=sorted(drop | {'u', 'pair'}), rows_v1=na, rows_parent=nb, rows_identical=(a == b),
                      only_v1=sum((a - b).values()), only_parent=sum((b - a).values()), probes_v1=sum(pa.values()), probes_parent=sum(pb.values()),
                      probes_identical=(pa == pb), hash_v1=h(a), hash_parent=h(b), per_cell=per)))
