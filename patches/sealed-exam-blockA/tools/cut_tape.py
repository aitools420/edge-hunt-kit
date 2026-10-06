#!/usr/bin/env python3
"""cut_tape.py <out.ndjson> <cut_unix> <in-file> [in-file ...] — NEW CODE (sealed-exam-blockA). The V2/V3 tape day file that holds
the last hour of the block (R-0109: tape-YYYY-MM-DD runs from the previous day's ~23:00Z) is copied with ONLY its rows of ts < cut,
reading only each row's "ts" field (regex, no JSON parse). The parts are read in the reader's order (v4tape.js v23Paths: archive
part(s) first, then the live file). The tape is written in time order (open day 09-24: 596,397 rows, 0 inversions), so the copy stops
at the first row with ts >= cut + 3600; rows below the cut met after a row at/after the cut are kept and counted.
Exit 3 (NOT READY) if the input ends before a row with ts >= cut + 3600 (the writer has not passed the margin yet).
Prints {read, kept, inversions, lateKept, sha256, bytes}."""
import sys, re, gzip, hashlib, json
OUT, CUT, INS = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
STOP = CUT + 3600
rx = re.compile(rb'"ts":(\d+)')
h = hashlib.sha256(); read = kept = byt = inv = late = 0; mx = 0; saw = False; stopped = False
with open(OUT, 'wb') as o:
    for p in INS:
        f = gzip.open(p, 'rb') if p.endswith('.gz') else open(p, 'rb')
        with f:
            for ln in f:
                m = rx.search(ln[:400])
                if not m: continue
                t = int(m.group(1)); read += 1
                if t >= STOP: stopped = True; break
                if t < mx: inv += 1
                else: mx = t
                if t >= CUT: saw = True; continue
                if saw: late += 1
                o.write(ln); h.update(ln); kept += 1; byt += len(ln)
        if stopped: break
print(json.dumps(dict(inputs=INS, read=read, kept=kept, bytes=byt, inversions=inv, lateKept=late, sha256=h.hexdigest(), stopped=stopped)))
sys.exit(0 if stopped else 3)
