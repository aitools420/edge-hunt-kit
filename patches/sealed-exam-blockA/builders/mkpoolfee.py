#!/usr/bin/env python3
# sealed-exam-blockA exam copy (paths only): see builders/make_builders.py and the .diff beside this file
"""pool -> fee, hook, venue, tok from ../v4-join-2026-09-27/meta.json (streamed regex; READ-ONLY). Out: argv[1] TSV."""
import re, sys
pat = re.compile(rb'"(0x[0-9a-f]{64})":\["(0x[0-9a-f]{40})","0x[0-9a-f]{40}","0x[0-9a-f]{40}",(\d+),(-?\d+),(null|"0x[0-9a-f]{40}"),(null|"[^"]*"),(null|\d+),(null|\d+)')
n = 0
with open('/home/green/projects/patches/sealed-exam-blockA/work/v4join/meta.json', 'rb') as fh, open(sys.argv[1], 'w') as o:
    tail = b''
    while True:
        ch = fh.read(8 << 20)
        if not ch: break
        buf = tail + ch; last = 0
        for m in pat.finditer(buf):
            o.write('\t'.join([m.group(1).decode(), m.group(2).decode(), m.group(3).decode(), m.group(5).decode().strip('"'), m.group(6).decode().strip('"'), m.group(8).decode()]) + '\n'); n += 1; last = m.end()
        tail = buf[max(last, len(buf) - 4096):]
print(n, 'pools')
