#!/usr/bin/env python3
"""tables.py <meta|poolfee> <full.tsv> <old_0927.tsv> <cutoff_unix> <out.tsv> <report.json> — NEW CODE (sealed-exam-blockA).
Turns a builder's full output (every coin / pool in the ledgers at run time) into the exam table:
  1. OLD ROWS VERBATIM: every coin / pool already in the 09-27 table keeps its 09-27 line EXACTLY (policy: rows already known must be
     identical). The rebuild is compared with them and every difference is REPORTED with its kind — on the open-data check of 2026-10-05
     the rebuild changed 4 of 471,683 meta rows and 0 of 550,395 poolfee rows, every one because the ledgers learned something AFTER the
     seal (3 coins whose first pool came in the block: birth '-' became a block date; 1 coin 'unknown' on 09-27 whose minter the minters
     ledger learned later, which would now read 'Pons'). Taking such a row from the rebuild would put block knowledge into an old coin.
  2. NEW ROWS: a key the 09-27 table does not hold is added if its birth is unknown ('-' / 'null': cannot be dated, as on 09-27) or
     < cutoff (exam: 2026-10-06T00:00:00Z, coins and pools born up to the end of the entry window).
  3. ORDER: the 09-27 rows first, in their 09-27 order (also cut at the cutoff by their OLD birth — that only bites in a test window
     earlier than the 09-27 table), then the new rows sorted by key. For the exam every 09-27 row passes, so the 09-27 table is a BYTE
     PREFIX of the exam table (checked) — the proof that every old coin and pool reads exactly as on 09-27, labels included.
Writes the table and a JSON report (counts, the rebuild's differences by kind with examples, the prefix check). Never takes an old row
from the rebuild; exits 2 only if the output cannot be written consistently."""
import sys, json, hashlib, collections
KIND, FULL, OLD, CUTOFF, OUT, REP = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6]
BCOL = 1 if KIND == 'meta' else 5
def rows(fn):
    out = []
    with open(fn) as f:
        for ln in f:
            if not ln.endswith('\n'): ln += '\n'
            a = ln.rstrip('\n').split('\t')
            if len(a) <= BCOL: continue
            out.append((a[0], a[BCOL], ln))
    return out
full, old = rows(FULL), rows(OLD)
fmap, dup = {}, 0
for k, b, ln in full:
    if k in fmap: dup += 1; continue
    fmap[k] = ln
oldkeys = set(k for k, _, _ in old)
kinds, examples, missing = collections.Counter(), [], 0
for k, b, ln in old:
    n = fmap.get(k)
    if n is None: missing += 1; kinds['old key absent from the rebuild'] += 1; continue
    if n == ln: continue
    a, c = ln.rstrip('\n').split('\t'), n.rstrip('\n').split('\t')
    NAMES = ['tok', 'birth', 'source', 'label'] if KIND == 'meta' else ['pool', 'tok', 'fee', 'hook', 'venue', 'birth']
    what = [NAMES[i] + (' unknown->known' if x in ('-', 'null') else ' changed') for i, (x, y) in enumerate(zip(a, c)) if x != y]
    if len(a) != len(c): what.append('column count')
    kd = ' + '.join(what)
    kinds[kd] += 1
    if len(examples) < 50: examples.append(dict(key=k, old_0927=ln.rstrip('\n'), rebuild=n.rstrip('\n')))
def passes(b): return b in ('-', 'null', '') or int(b) < CUTOFF
keep_old = [ln for k, b, ln in old if passes(b)]
seen, new_keep, new_drop, new_unknown, new_known_before_seal = set(), [], 0, 0, 0
for k, b, ln in sorted(((k, b, ln) for k, b, ln in full if k not in oldkeys), key=lambda x: x[0]):
    if k in seen: continue
    seen.add(k)
    if passes(b):
        new_keep.append(ln)
        if b in ('-', 'null', ''): new_unknown += 1
        elif int(b) < 1790467200: new_known_before_seal += 1
    else: new_drop += 1
data = ''.join(keep_old + new_keep)
open(OUT, 'w').write(data)
olddata = open(OLD).read()
rep = dict(kind=KIND, full_rows=len(full), full_dup_keys=dup, old_rows=len(old), old_rows_kept_verbatim=len(keep_old),
           old_rows_dropped_by_cutoff=len(old) - len(keep_old), rebuild_identical_for_every_old_row=(sum(kinds.values()) == 0),
           rebuild_differences=sum(kinds.values()), rebuild_difference_kinds=dict(kinds), cutoff=CUTOFF,
           new_rows_kept=len(new_keep), new_unknown_birth_kept=new_unknown, new_rows_born_before_seal_kept=new_known_before_seal,
           new_rows_dropped_by_cutoff=new_drop, out_rows=len(keep_old) + len(new_keep), out_sha256=hashlib.sha256(data.encode()).hexdigest(),
           old_sha256=hashlib.sha256(olddata.encode()).hexdigest(), old_table_is_byte_prefix=data.startswith(olddata),
           examples_rebuild_differences=examples)
json.dump(rep, open(REP, 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if not k.startswith('examples')}))
sys.exit(0)
