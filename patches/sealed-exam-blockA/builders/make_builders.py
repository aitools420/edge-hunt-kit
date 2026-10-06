#!/usr/bin/env python3
"""make_builders.py — the exam copies of the 09-27 table builders (sealed-exam-blockA): PATHS ONLY, each anchor asserted to match
exactly once; a unified diff of each copy against its original is written next to it (<name>.diff).
  ALL: the ledgers are read from WORK/ledgers, the SNAPSHOT run_exam.sh takes (and hashes) just before, so the recorded hashes are
  exactly what was read (the live ledgers grow every minute).
  tokmeta.py   (hold-study-2026-09-27, 8eedaed4…)  -> writes WORK/tables/tokmeta.tsv; launchpad LABELS read from
                the file the runner extracts with `git -C ~/noxabot show e5c559ec:lib/launchpads.js` (the last commit before the seal,
                2026-09-26T02:21Z, sha256 1b939aea…), not from the live working tree.
  mkmeta.py    (edge-round3-2026-09-27, 77ffd34f…) -> reads WORK/tables/tokmeta.tsv.
  mkpoolfee.py (blood-selection2-2026-09-27, 5359a037…) -> reads WORK/v4join/meta.json (built by join/meta.js), never the hunter's
                pinned v4-join-2026-09-27/meta.json."""
import os, difflib
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = '/home/green/projects/patches/sealed-exam-blockA/work'
S = {'tokmeta.py': '/home/green/projects/patches/hold-study-2026-09-27/tokmeta.py',
     'mkmeta.py': '/home/green/projects/patches/edge-round3-2026-09-27/mkmeta.py',
     'mkpoolfee.py': '/home/green/projects/patches/blood-selection2-2026-09-27/mkpoolfee.py'}
P = {'tokmeta.py': [("HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = '{WORK}/tables'"),
                    ("L = '/home/green/.openclaw/workspace/wick-engine/logs'", f"L = '{WORK}/ledgers'"),
                    ("src = open('/home/green/noxabot/lib/launchpads.js').read().split('\\n')[13:421]",
                     f"src = open('{WORK}/tables/launchpads_e5c559ec.js').read().split('\\n')[13:421]")],
     'mkmeta.py': [("L = '/home/green/.openclaw/workspace/wick-engine/logs'", f"L = '{WORK}/ledgers'"),
                   ("    for ln in open('/home/green/projects/patches/hold-study-2026-09-27/tokmeta.tsv'):", f"    for ln in open('{WORK}/tables/tokmeta.tsv'):")],
     'mkpoolfee.py': [("with open('/home/green/projects/patches/v4-join-2026-09-27/meta.json', 'rb') as fh, open(sys.argv[1], 'w') as o:",
                       f"with open('{WORK}/v4join/meta.json', 'rb') as fh, open(sys.argv[1], 'w') as o:")]}
TAG = '# sealed-exam-blockA exam copy (paths only): see builders/make_builders.py and the .diff beside this file'
for name, pairs in P.items():
    s0 = open(S[name]).read(); s = s0
    for a, b in pairs:
        n = s.count(a); assert n == 1, f'{name}: anchor found {n} times: {a[:80]!r}'
        s = s.replace(a, b)
    lines = s.split('\n'); lines.insert(1 if lines[0].startswith('#!') else 0, TAG); s = '\n'.join(lines)
    out = os.path.join(HERE, name); open(out, 'w').write(s)
    d = ''.join(difflib.unified_diff(s0.splitlines(True), s.splitlines(True), S[name].replace('/home/green/projects/patches/', ''), f'sealed-exam-blockA/builders/{name}'))
    open(out + '.diff', 'w').write(d)
    print(f'{name}: {len(pairs)} replacements')
