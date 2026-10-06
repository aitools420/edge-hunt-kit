#!/usr/bin/env python3
"""post/rule2_late_split.py [work_dir] — DESCRIPTIVE, outside the pinned runner, run only AFTER report.md exists (register clarification 4,
answering pond #322 §4 b). Rule #2 (D25L48) primary pass: strategy rows with a signal (T = assessment hour) from 2026-10-05T20:00Z on,
and rows that booked 'end', each counted with their mean return, beside the rest. Never part of the verdict."""
import gzip, json, sys, os, statistics
W = sys.argv[1] if len(sys.argv) > 1 else '/home/green/projects/patches/sealed-exam-blockA/work'
f = os.path.join(W, 'out', 'primary_rule2.ndjson.gz')
assert os.path.exists(os.path.join(os.path.dirname(W.rstrip('/')), 'report.md')), 'report.md first: this split is read only after the verdict'
LATE = 1791230400   # 2026-10-05T20:00:00Z
rows = []
with gzip.open(f, 'rt') as fh:
    for ln in fh:
        if '"cell":"D25L48"' not in ln or '"kind":"S"' not in ln: continue
        j = json.loads(ln)
        if j.get('skipDepth') or j.get('on') is None: continue
        rows.append(j)
def summ(xs): return dict(n=len(xs), coins=len({x['tok'] for x in xs}), mean_on=round(statistics.mean(x['on'] for x in xs), 2) if xs else None)
late = [r for r in rows if r['T'] >= LATE]; early = [r for r in rows if r['T'] < LATE]; end = [r for r in rows if r.get('reason') == 'end']
out = dict(file=f, all=summ(rows), signals_before_1005_2000Z=summ(early), signals_from_1005_2000Z=summ(late), booked_end=summ(end),
           note="strategy rows only, return 'on' as the engine booked it (before the analyzer's cost view); descriptive, not the bar")
print(json.dumps(out, indent=1))
