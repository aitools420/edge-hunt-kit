#!/usr/bin/env python3
"""verify_manifest.py - EDGE MACHINE v1, KIT LAYOUT: REFUSE (exit 2) unless every pinned file matches MANIFEST.json.
code / inputs / external: sha256 must match. data: for every day, the files the engine would read must be EXACTLY the manifest's parts (no
extra or missing part), each with the pinned size and sha256 (file sha256 cached in $KIT_ROOT/.kit_verified.json by size + mtime, so only a
new or changed file is re-hashed). --content additionally re-hashes every day's DECOMPRESSED content against the origin content hash
(slow, ~4.6 GB). --inputs DIR also checks the decompressed tables in DIR. Usage: verify_manifest.py [--inputs DIR] [--content] [--quiet]"""
import json, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import manifest_lib as M
man = json.load(open(HERE + '/MANIFEST.json')); bad = []; q = '--quiet' in sys.argv
chk = hashlib.sha256(json.dumps({k: v for k, v in man.items() if k not in ('created', 'manifest_sha256')}, sort_keys=True).encode()).hexdigest()
if chk != man['manifest_sha256']: bad.append('MANIFEST.json itself was edited (manifest_sha256 mismatch)')
if sorted(man['code']) != sorted(M.CODE): bad.append('the code file list differs from manifest_lib.CODE')
for f, h in man['code'].items():
    if not os.path.exists(HERE + '/' + f) or M.sha(HERE + '/' + f) != h: bad.append('code ' + f)
for f, h in man['inputs'].items():
    if not os.path.exists(HERE + '/' + f) or M.sha(HERE + '/' + f) != h: bad.append('input ' + f)
for f, h in man['external'].items():
    p = os.path.join(M.ROOT, f)
    if not os.path.exists(p) or M.sha(p) != h: bad.append('external ' + f)
CF = os.path.join(M.ROOT, '.kit_verified.json')
try: cache = json.load(open(CF))
except Exception: cache = {}
for d, rec in man['data'].items():
    cur = [M.rel(p) for p in M.day_parts(d)]; want = [x['path'] for x in rec['parts']]
    if cur != want: bad.append(f'data {d}: the engine would read {cur}, manifest pins {want}'); continue
    for x in rec['parts']:
        p = os.path.join(M.ROOT, x['path']); st = os.stat(p); key = [st.st_size, st.st_mtime_ns]
        c = cache.get(x['path'])
        if not (c and c[:2] == key and c[2] == x['sha256']):
            h = M.sha(p) if st.st_size == x['size'] else None
            if h != x['sha256']: bad.append(f"data {d}: {x['path']} size/sha256 mismatch"); continue
            cache[x['path']] = key + [h]
    if '--content' in sys.argv and M.day_content(d) != rec['content']: bad.append(f'data {d}: DECOMPRESSED CONTENT differs from the origin')
try: json.dump(cache, open(CF, 'w'))
except Exception: pass
if '--inputs' in sys.argv:
    D = sys.argv[sys.argv.index('--inputs') + 1]
    for f, h in man['inputs_plain'].items():
        p = D + '/' + os.path.basename(f)
        if not os.path.exists(p) or M.sha(p) != h: bad.append('decompressed input ' + p)
if bad:
    print('MANIFEST MISMATCH - REFUSED. A changed engine/pipeline is a NEW VERSION (v2 + a new manifest), never a silent edit:'); [print('  ' + b) for b in bad]
    sys.exit(2)
if not q: print(f"MANIFEST OK: {man['version']} engine {man['engine_sha256'][:16]} cost {man['cost_version']}" + (' (content re-hashed)' if '--content' in sys.argv else ''))
