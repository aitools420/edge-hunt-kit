#!/usr/bin/env python3
"""days.py — NEW CODE (sealed-exam-blockA): find, verify and link the raw day files the exam reads.

  days.py verify <tape|wide> <out_manifest.json> <registered.tsv> <day> [<day> ...]
      For each day: locate its ONE file the way the consumer finds it (tape: the patterns of v4tape.js v23Paths and of
      SEALED-HOLDOUT/hash_tape_days.py; wide: ~/noxabot/logs/v4-wide/uniswap-v4-wide-DAY.ndjson[.gz]). Refuse (exit 2) if a day has
      no file or more than one part. sha256 of the UNCOMPRESSED content (as hash_tape_days.py) must equal EVERY registered row for
      (day, feed) in registered.tsv (the tape-hashes.tsv format; feed v2v3-tape or v4-wide); a day with no registered row, or a
      mismatch, is refused. Writes {day: {path, gz, sha256, bytes}}.
  days.py link <tape|wide> <manifest.json> <dest_root>
      tape: dest_root/archive/0000/tape-DAY.ndjson.gz -> a gz file, dest_root/robinhood-tape/tape-DAY.ndjson -> a plain file
            (the two patterns v23Paths reads; a symlink to the verified file). wide: dest_root/uniswap-v4-wide-DAY.ndjson -> the plain
            file (pass1 reads only plain .ndjson; a gz day is decompressed into a plain copy whose sha256 is re-checked).
  days.py hash <file> ... : sha256 + bytes of the uncompressed content (for open days and for registering pins)."""
import sys, os, glob, gzip, hashlib, json
HOME = '/home/green'
WE = HOME + '/.openclaw/workspace/wick-engine/logs'
PAT = {'tape': [WE + '/robinhood-tape/tape-{d}.ndjson', WE + '/robinhood-tape/tape-{d}.ndjson.gz', WE + '/archive/*/tape-{d}.ndjson.gz', WE + '/archive/*/tape-{d}.ndjson'],
       'wide': [HOME + '/noxabot/logs/v4-wide/uniswap-v4-wide-{d}.ndjson', HOME + '/noxabot/logs/v4-wide/uniswap-v4-wide-{d}.ndjson.gz']}
FEED = {'tape': 'v2v3-tape', 'wide': 'v4-wide'}
def refuse(msg): print('REFUSE:', msg); sys.exit(2)
def digest(p):
    h, n = hashlib.sha256(), 0
    with (gzip.open(p, 'rb') if p.endswith('.gz') else open(p, 'rb')) as f:
        while True:
            b = f.read(1 << 20)
            if not b: break
            h.update(b); n += len(b)
    return h.hexdigest(), n
def registered(tsv):
    R = {}
    for ln in open(tsv):
        a = ln.rstrip('\n').split('\t')
        if len(a) < 5 or a[0] == 'computed_utc': continue
        R.setdefault((a[1], a[2]), []).append((a[3], a[4]))
    return R
cmd = sys.argv[1]
if cmd == 'hash':
    for p in sys.argv[2:]: h, n = digest(p); print(f'{h}\t{n}\t{p}')
    sys.exit(0)
kind = sys.argv[2]
if cmd == 'verify':
    out, tsv, days = sys.argv[3], sys.argv[4], sys.argv[5:]
    R = registered(tsv); M = {}
    for d in days:
        hits = sorted(set(p for pat in PAT[kind] for p in glob.glob(pat.format(d=d))))
        if len(hits) != 1: refuse(f'{kind} {d}: {len(hits)} files found {hits}')
        rows = R.get((d, FEED[kind]))
        if not rows: refuse(f'{kind} {d}: no registered row in {tsv}')
        h, n = digest(hits[0])
        bad = [r for r in rows if r[0] != h or (r[1] and int(r[1]) != n)]
        if bad: refuse(f'{kind} {d}: content sha256 {h} ({n} B) of {hits[0]} differs from the registered {bad}')
        M[d] = dict(path=hits[0], gz=hits[0].endswith('.gz'), sha256=h, bytes=n)
        print(f'OK {kind} {d} {h[:16]} {n} {hits[0]}', flush=True)
    json.dump(M, open(out, 'w'), indent=1)
elif cmd == 'link':
    M, dest = json.load(open(sys.argv[3])), sys.argv[4]
    for d, m in sorted(M.items()):
        if kind == 'tape':
            q = os.path.join(dest, 'archive', '0000', f'tape-{d}.ndjson.gz') if m['gz'] else os.path.join(dest, 'robinhood-tape', f'tape-{d}.ndjson')
            os.makedirs(os.path.dirname(q), exist_ok=True)
            if os.path.lexists(q): os.remove(q)
            os.symlink(m['path'], q)
        else:
            q = os.path.join(dest, f'uniswap-v4-wide-{d}.ndjson'); os.makedirs(dest, exist_ok=True)
            if os.path.lexists(q): os.remove(q)
            if not m['gz']: os.symlink(m['path'], q)
            else:
                with gzip.open(m['path'], 'rb') as f, open(q, 'wb') as o:
                    while True:
                        b = f.read(1 << 20)
                        if not b: break
                        o.write(b)
                if digest(q)[0] != m['sha256']: refuse(f'decompressed copy of {m["path"]} does not hash to {m["sha256"]}')
        print(f'linked {kind} {d} -> {q}')
    if kind == 'tape': os.makedirs(os.path.join(dest, 'archive'), exist_ok=True); os.makedirs(os.path.join(dest, 'robinhood-tape'), exist_ok=True)
