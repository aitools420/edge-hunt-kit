#!/usr/bin/env python3
# sealed-exam-blockA exam copy (paths only): see builders/make_builders.py and the .diff beside this file
"""Token metadata join (READ-ONLY on the estate) -> tokmeta.tsv in this folder:
tok \t birthTs(or -) \t creator(or -) \t minter(or -) \t pad
pad = LABELS[minter] brand (lib/launchpads.js lines 14-421, the LABELS map) per R-0053's join, else
'unlabelled' (minter known, no label) else 'unknown' (token absent from the minters ledger).
Births parsing reuses theory-batch-2 births_tsv.py's regex, streamed in 16 MB chunks."""
import re, os, json
HERE = '/home/green/projects/patches/sealed-exam-blockA/work/tables'
L = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers'
pat = re.compile(rb'"(0x[0-9a-f]{40})":\{"sym":"(?:[^"\\]|\\.)*","decimals":\d+,"firstBlock":\d+,"firstTs":(\d+)(?:,"source":"[^"]*")?(?:,"creator":(?:"(0x[0-9a-f]{40})"|null))?')
births = {}
with open(f'{L}/robinhood-token-births.json', 'rb') as fh:
    tail = b''
    while True:
        ch = fh.read(16 << 20)
        if not ch: break
        buf = tail + ch
        for m in pat.finditer(buf): births[m.group(1).decode()] = (int(m.group(2)), (m.group(3) or b'-').decode())
        tail = buf[-4096:]
labels = {}
src = open('/home/green/projects/patches/sealed-exam-blockA/work/tables/launchpads_e5c559ec.js').read().split('\n')[13:421]
for ln in src:
    m = re.match(r"\s*'(0x[0-9a-fA-F]{40})':\s*'([^']*)'", ln)
    if m: labels[m.group(1).lower()] = m.group(2).split(' (')[0].strip()
minter = {}
with open(f'{L}/robinhood-token-minters.ndjson') as fh:
    for ln in fh:
        try: j = json.loads(ln)
        except Exception: continue
        if j.get('tok') and j.get('minter'): minter.setdefault(j['tok'].lower(), j['minter'].lower())
toks = set(births) | set(minter)
with open(os.path.join(HERE, 'tokmeta.tsv'), 'w') as o:
    for t in toks:
        b = births.get(t); mi = minter.get(t)
        pad = labels.get(mi, 'unlabelled') if mi else 'unknown'
        o.write(f"{t}\t{b[0] if b else '-'}\t{b[1] if b else '-'}\t{mi or '-'}\t{pad}\n")
print(len(toks), 'tokens', len(births), 'births', len(minter), 'minters', len(labels), 'labels', len(set(labels.values())), 'brands')
