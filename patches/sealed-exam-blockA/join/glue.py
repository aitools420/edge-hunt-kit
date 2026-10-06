#!/usr/bin/env python3
"""glue.py — NEW CODE (sealed-exam-blockA): the small steps between the v4-join tools that the 09-27 run did by hand (not kept).
  glue.py unknown_split <work> <old_unknown_keys.json>  : unknown_pools.json (every wide pool id the exam meta does not name) ->
        unknown_pools_all.json; unknown_pools.json := only the ids the 09-27 unknown_keys.json does not already resolve (so the
        RPC step resolves only NEW pre-ledger pools).
  glue.py unknown_merge <work> <old_unknown_keys.json>  : unknown_keys.json (new) -> unknown_keys_new.json; unknown_keys.json :=
        09-27 keys + new keys. Prints how many of the new ids (and their swaps) stayed unresolved.
  glue.py poolcounts <work>                              : pools with at least one swap in the shards (column 5) -> poolcounts.tsv
        (finalize.js keeps only these pools in RAM; the 09-27 run's file of the same name).
  glue.py compare <mine.ndjson.gz> <orig.ndjson.gz>      : row-by-row comparison of a joined day with the original join's file
        (both sorted by (blk, li)): identical rows, rows in one only, which fields differ, and how many rows differ in a field the
        engines read (the label fields pad / pad_key / hook / launcher / birth_ts are never read by engine_st / engine_grid)."""
import sys, os, json, glob, gzip, collections
cmd = sys.argv[1]
if cmd in ('unknown_split', 'unknown_merge'):
    W, OLD = sys.argv[2], sys.argv[3]
    old = json.load(open(OLD))
    if cmd == 'unknown_split':
        U = json.load(open(f'{W}/unknown_pools.json'))
        os.replace(f'{W}/unknown_pools.json', f'{W}/unknown_pools_all.json')
        new = {k: v for k, v in U.items() if k not in old}
        json.dump(new, open(f'{W}/unknown_pools.json', 'w'))
        print(json.dumps(dict(unknown_all=len(U), already_resolved_0927=len(U) - len(new), to_resolve=len(new), to_resolve_swaps=sum(v['n'] for v in new.values()))))
    else:
        newk = json.load(open(f'{W}/unknown_keys.json')) if os.path.exists(f'{W}/unknown_keys.json') else {}
        if os.path.exists(f'{W}/unknown_keys.json'): os.replace(f'{W}/unknown_keys.json', f'{W}/unknown_keys_new.json')
        U = json.load(open(f'{W}/unknown_pools.json'))
        un = [k for k in U if k not in newk]
        merged = dict(old); merged.update(newk)
        json.dump(merged, open(f'{W}/unknown_keys.json', 'w'))
        print(json.dumps(dict(old_keys=len(old), new_keys=len(newk), merged=len(merged), new_unresolved=len(un), new_unresolved_swaps=sum(U[k]['n'] for k in un))))
elif cmd == 'poolcounts':
    W = sys.argv[2]; C = collections.Counter()
    for fn in sorted(glob.glob(f'{W}/shards/*.tsv')):
        with open(fn) as f:
            for ln in f:
                a = ln.split('\t', 5)
                if len(a) > 4: C[a[4]] += 1
    with open(f'{W}/poolcounts.tsv', 'w') as o:
        for k in sorted(C): o.write(f'{k}\t{C[k]}\n')
    print(json.dumps(dict(pools=len(C), swaps=sum(C.values()))))
elif cmd == 'compare':
    A, B = sys.argv[2], sys.argv[3]
    def it(fn):
        with gzip.open(fn, 'rt') as f:
            for ln in f:
                if ln.strip(): j = json.loads(ln); yield (j['blk'], j['li']), j
    ENG = {'ts', 'blk', 'li', 'tx', 'tok', 'pool', 'quote', 'price_quote', 'price_eth', 'price_usd', 'side', 'amount_token', 'amount_quote', 'usd', 'liquidity', 'depth1_eth', 'src'}   # what engine_st / engine_grid read (via v4tape toEngine)
    t = collections.Counter(); fields = collections.Counter(); ex = []
    ia, ib = it(A), it(B); a, b = next(ia, None), next(ib, None)
    while a or b:
        if b is None or (a and a[0] < b[0]): t['only_mine'] += 1; a = next(ia, None); continue
        if a is None or b[0] < a[0]: t['only_orig'] += 1; b = next(ib, None); continue
        if a[1] == b[1]: t['identical'] += 1
        else:
            t['differ'] += 1; de = False
            for k in set(a[1]) | set(b[1]):
                if a[1].get(k) != b[1].get(k): fields[k] += 1; de = de or k in ENG
            if de: t['differ_in_engine_fields'] += 1
            if len(ex) < 5: ex.append(dict(mine=a[1], orig=b[1]))
        a, b = next(ia, None), next(ib, None)
    print(json.dumps(dict(mine=A, orig=B, **t, fields=dict(fields), examples=ex)))
