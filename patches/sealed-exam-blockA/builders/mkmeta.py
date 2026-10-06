#!/usr/bin/env python3
# sealed-exam-blockA exam copy (paths only): see builders/make_builders.py and the .diff beside this file
"""meta.tsv (session scratchpad): tok \t birthTs|- \t source|- \t pad. READ-ONLY on the estate.
pad from ../hold-study-2026-09-27/tokmeta.tsv (R-0053 join: minter -> launchpads.js LABELS); source from robinhood-token-births.json
(same streamed regex as tokmeta.py, plus the "source" field). 'labelled' in this study = pad not in {unknown, unlabelled}."""
import re, sys
L = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers'
pat = re.compile(rb'"(0x[0-9a-f]{40})":\{"sym":"(?:[^"\\]|\\.)*","decimals":\d+,"firstBlock":\d+,"firstTs":(\d+)(?:,"source":"([^"]*)")?')
src = {}
with open(f'{L}/robinhood-token-births.json', 'rb') as fh:
    tail = b''
    while True:
        ch = fh.read(16 << 20)
        if not ch: break
        buf = tail + ch
        for m in pat.finditer(buf): src[m.group(1).decode()] = (m.group(2).decode(), (m.group(3) or b'-').decode())
        tail = buf[-4096:]
n = 0
with open(sys.argv[1], 'w') as o:
    for ln in open('/home/green/projects/patches/sealed-exam-blockA/work/tables/tokmeta.tsv'):
        a = ln.rstrip('\n').split('\t'); b = src.get(a[0], (a[1], '-'))
        o.write(f"{a[0]}\t{b[0]}\t{b[1]}\t{a[4]}\n"); n += 1
    for t, b in src.items():
        pass
print(n, 'tokens;', len(src), 'births with source')
