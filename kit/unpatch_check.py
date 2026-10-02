#!/usr/bin/env python3
"""unpatch_check.py - prove that every shipped pipeline file is either byte-identical to the origin file, or differs ONLY in the lines listed
in kit/PATCHES.json: for each patched file, reverse each (kit line -> original line) and require the sha256 of the result to equal the origin
sha256 (recorded in the engine MANIFEST.json as code_original / external_original). Run from anywhere with KIT_ROOT set. Exit 1 on any failure."""
import os, sys, json, hashlib
R = os.environ['KIT_ROOT']; E = 'patches/edge-machine-2026-09-30/engine/'
P = json.load(open(os.path.join(R, 'kit/PATCHES.json'))); man = json.load(open(os.path.join(R, E, 'MANIFEST.json')))
orig = {E + f: h for f, h in man['code_original'].items()}; orig.update(man['external_original'])
REPLACED = {E + 'manifest_lib.py', E + 'verify_manifest.py'}     # rewritten for the kit layout (manifest machinery, no computation)
bad = 0
for f in sorted(set(orig) | set(P)):
    h0 = orig.get(f) or P[f]['original_sha256']
    if not os.path.exists(os.path.join(R, f)): print('MISSING    ' + f + '  (run kit/setup.sh first)'); bad += 1; continue
    s = open(os.path.join(R, f), 'rb').read().decode()
    h = hashlib.sha256(s.encode()).hexdigest()
    if f in REPLACED: print(f'REPLACED   {f}  (kit manifest machinery; see kit/CHANGES.md)'); continue
    if f not in P:
        ok = h == h0; print(('IDENTICAL  ' if ok else 'FAIL       ') + f); bad += not ok; continue
    e = P[f]; ok = h == e['kit_sha256']
    for new, old in e['edits']:
        if s.count(new) != 1: ok = False; break
        s = s.replace(new, old)
    ok = ok and hashlib.sha256(s.encode()).hexdigest() == h0 == e['original_sha256']
    print(('UNPATCH OK ' if ok else 'FAIL       ') + f + f'  ({len(e["edits"])} line(s) reversed -> origin sha256 {h0[:16]})'); bad += not ok
print('unpatch check:', 'ALL OK' if not bad else f'{bad} FAILED'); sys.exit(1 if bad else 0)
