#!/usr/bin/env python3
"""make_testB.py — TEST B (windowing, plumbing): a dry-run "block" on OPEN days through the WHOLE runner. The test tree is a copy of
every registered exam file with (1) one path prefix replaced (the tree root -> tests/testB/tree/) and (2) the listed window constants
replaced, each anchor asserted to match exactly once. Nothing else differs; the substitutions are written to testB_substitutions.json.
Test window (open data only, every row < 2026-09-27T00:00Z):
  warm-up 09-19..09-21 · block days 09-22..09-25 (their raw files registered in a TEST tape-hashes copy, from pins/open_days.tsv) ·
  rule #1 last assessment 09-23T23:00Z (= cut - 49 h) · rule #2 / C1 last assessment 09-24T23:00Z (signals < 09-25T00:00Z) ·
  CUT 2026-09-26T00:00:00Z: the 09-26 tape file and the 09-26 V4-wide file (each holding the last hour / 18 min) are read CUT at the cut ·
  join from 09-20 · tables: coins / pools born before 09-25T00:00Z · consistency: every joined day 09-20..09-25 against the 09-27 join ·
  2 seeds (20260927, 20260928) instead of 20, to save box time (the loop is the same code).
The test guard = the exam guard with test constants AND the Block A seal guard (09-27) loaded together."""
import os, json, shutil, hashlib, subprocess
R = '/home/green/projects/patches/sealed-exam-blockA'
T = R + '/tests/testB'
TREE = T + '/tree'
PREF_OLD, PREF_NEW = R + '/', TREE + '/'
FILES = ['run_exam.sh'] + [f'engines/{x}' for x in ('engine_st_exam.js', 'engine_grid_exam.js', 'engine_st_exam_h.js', 'engine_grid_exam_h.js', 'v4tape_exam.js', 'guard.js', 'guard_test.js')] \
    + [f'tools/{x}' for x in ('exam_guard.js', 'seal_guard.js', 'run_engine.sh', 'gate.sh', 'stats_rule.py', 'tables.py', 'cut_tape.py', 'days.py', 'report.py')] \
    + [f'builders/{x}' for x in ('tokmeta.py', 'mkmeta.py', 'mkpoolfee.py')] \
    + [f'join/{x}' for x in ('meta.js', 'unknown_pools.js', 'resolve_unknown.py', 'anchors.py', 'decimals.js', 'pools.js', 'pass1.js', 'finalize.js', 'cut_v4.js', 'fetch_ethusd.py', 'glue.py', 'addr_lists.js')] \
    + ['join/orient_0927.json'] + ['pins/open_days.tsv']
ENG_ST = [["CUT = 1791331200;", "CUT = 1790380800;"],
          ["const DATA0 = Date.parse('2026-09-24T00:00:00Z') / 1000;", "const DATA0 = Date.parse('2026-09-19T00:00:00Z') / 1000;"],
          ["const FIT0 = Date.parse('2026-09-27T00:00:00Z') / 1000, JUDGE0 = Date.parse('2026-09-27T00:00:00Z') / 1000;", "const FIT0 = Date.parse('2026-09-22T00:00:00Z') / 1000, JUDGE0 = Date.parse('2026-09-22T00:00:00Z') / 1000;"],
          ["last: Date.parse('2026-10-05T23:00:00Z') / 1000 },", "last: Date.parse('2026-09-24T23:00:00Z') / 1000 },"],
          ["last: Date.parse('2026-10-04T23:00:00Z') / 1000 }];", "last: Date.parse('2026-09-23T23:00:00Z') / 1000 }];"],
          ["const RUN = V4.days('2026-09-24', process.env.STOP_DAY || '2026-10-07');", "const RUN = V4.days('2026-09-19', process.env.STOP_DAY || '2026-09-26');"]]
ENG_GRID = [ENG_ST[0], ENG_ST[1], ENG_ST[2], ["const LAST = Date.parse('2026-10-05T23:00:00Z') / 1000;", "const LAST = Date.parse('2026-09-24T23:00:00Z') / 1000;"], ENG_ST[5]]
P = {
 'engines/engine_st_exam.js': ENG_ST, 'engines/engine_st_exam_h.js': ENG_ST,
 'engines/engine_grid_exam.js': ENG_GRID, 'engines/engine_grid_exam_h.js': ENG_GRID,
 'engines/v4tape_exam.js': [["BLOCK0_DAY = '2026-09-27';", "BLOCK0_DAY = '2026-09-22';"], ["const SEAL = 1791331200;", "const SEAL = 1790380800;"], ["const SEAL_DAY = '2026-10-08';", "const SEAL_DAY = '2026-09-27';"]],
 'tools/exam_guard.js': [["const SEAL = 1791331200, REAL_DAY = '2026-10-07', WORK_DAY = '2026-10-08';", "const SEAL = 1790380800, REAL_DAY = '2026-09-26', WORK_DAY = '2026-09-27';"],
                         ["'use strict';\n", f"'use strict';\nrequire('{TREE}/tools/seal_guard.js');   // TEST B: the Block A seal guard (09-27) is loaded as well\n"]],
 'join/pass1.js': [["const CUT = 1791331200, JOIN0 = '2026-09-25';", "const CUT = 1790380800, JOIN0 = '2026-09-20';"]],
 'join/finalize.js': [["const SEAL = 1791331200; ", "const SEAL = 1790380800; "]],
 'run_exam.sh': [
   ["ROOT=/home/green/projects/patches/sealed-exam-blockA\n", f"ROOT={TREE}\n"],
   ["REG_TSV=/home/green/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv", f"REG_TSV={T}/tape-hashes-testB.tsv"],
   ["CUT=1791331200 ", "CUT=1790380800 "], ["READY_AT=1791342000 ", "READY_AT=1790391600 "], ["CUT_DAY=2026-10-07 ", "CUT_DAY=2026-09-26 "],
   ['TAPE_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"', 'TAPE_OPEN_DAYS="2026-09-19 2026-09-20 2026-09-21"'],
   ['BLOCK_DAYS="2026-09-27 2026-09-28 2026-09-29 2026-09-30 2026-10-01 2026-10-02 2026-10-03 2026-10-04 2026-10-05 2026-10-06"', 'BLOCK_DAYS="2026-09-22 2026-09-23 2026-09-24 2026-09-25"'],
   ['WIDE_OPEN_DAYS="2026-09-25 2026-09-26"', 'WIDE_OPEN_DAYS="2026-09-20 2026-09-21"'],
   ['V4_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"', 'V4_OPEN_DAYS="2026-09-19 2026-09-20 2026-09-21"'],
   ["JOIN0_TS=1790294400 ", "JOIN0_TS=1789862400 "], ["ETH_FROM=1790208000 ", "ETH_FROM=1789776000 "], ["TABLE_CUTOFF=1791244800 ", "TABLE_CUTOFF=1790294400 "],
   ['CONSIST_DAYS="2026-09-25 2026-09-26"', 'CONSIST_DAYS="2026-09-20 2026-09-21 2026-09-22 2026-09-23 2026-09-24 2026-09-25"'],
   ['SEEDS="20260927 20260928 20260929 20260930 20260931 20260932 20260933 20260934 20260935 20260936 20260937 20260938 20260939 20260940 20260941 20260942 20260943 20260944 20260945 20260946"', 'SEEDS="20260927 20260928"']],
}
if os.path.exists(TREE): shutil.rmtree(TREE)
log = {}
for f in FILES:
    s = open(os.path.join(R, f)).read()
    n0 = s.count(PREF_OLD)
    s = s.replace(PREF_OLD, PREF_NEW)
    subs = []
    for a, b in P.get(f, []):
        n = s.count(a); assert n == 1, f'{f}: anchor found {n} times: {a[:80]!r}'
        s = s.replace(a, b); subs.append([a, b])
    os.makedirs(os.path.dirname(os.path.join(TREE, f)), exist_ok=True)
    open(os.path.join(TREE, f), 'w').write(s)
    if f.endswith('.sh') or f.endswith('.py'): os.chmod(os.path.join(TREE, f), 0o755)
    log[f] = dict(prefix_replacements=n0, constant_pairs=subs)
# the TEST registry: the four test block days' raw files, from the open-day pins
reg = [l for l in open(R + '/pins/open_days.tsv')]
hdr, rows = reg[0], [l for l in reg[1:] if l.split('\t')[1] in ('2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25')]
open(T + '/tape-hashes-testB.tsv', 'w').write(hdr + ''.join(rows))
# the test tree's own pins (the same lists as the exam's, for the test files)
code = [f for f in FILES if not f.startswith('pins/') and f != 'run_exam.sh']
ext = ['/home/green/projects/patches/blood-stress-2026-09-27/analyze_st.py', '/home/green/projects/patches/blood-grid-depth-history-2026-09-27/analyze_grid.py']
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
open(TREE + '/pins/code.sha256', 'w').write(''.join(f'{sha(os.path.join(TREE, f))}  {os.path.join(TREE, f)}\n' for f in code) + ''.join(f'{sha(p)}  {p}\n' for p in ext))
inp = []
for ln in open(R + '/pins/inputs.sha256'):
    h, f = ln.rstrip('\n').split('  ', 1)
    if f == R + '/pins/open_days.tsv': f = TREE + '/pins/open_days.tsv'
    inp.append(f'{sha(f)}  {f}\n')
for d in ('2026-09-19', '2026-09-20', '2026-09-21', '2026-09-22', '2026-09-23'):   # Test B's extra warm-up / consistency V4 days of the 09-27 join
    f = f'/home/green/projects/patches/v4-join-2026-09-27/out/v4-swaps-{d}.ndjson.gz'; inp.append(f'{sha(f)}  {f}\n')
open(TREE + '/pins/inputs.sha256', 'w').write(''.join(inp))
json.dump(log, open(T + '/testB_substitutions.json', 'w'), indent=1)
print('test tree written:', len(FILES), 'files;', sum(len(v['constant_pairs']) for v in log.values()), 'constant pairs;', len(rows), 'test registry rows')
