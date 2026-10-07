#!/usr/bin/env python3
"""mutation_check.py — proof that Test C and Test R can FAIL (pond #330). Each mutation breaks ONE new guard in a scratch COPY of the kit
(the kit itself is never edited), runs the suite against the copy, and PASSES only if every case that tests that guard goes RED.
Nothing real is read: Test C's trees are synthetic (tests/testC/make_tree.py), Test R's work folders are synthetic. Log: tests/mutation_check.log."""
import os, sys, shutil, subprocess, tempfile, re
F = '/home/green/projects/patches/sealed-exam-blockA'
FILES = ['run_exam.sh'] + [f'engines/{x}' for x in ('engine_st_exam.js', 'engine_grid_exam.js', 'engine_st_exam_h.js', 'engine_grid_exam_h.js', 'v4tape_exam.js', 'guard.js', 'guard_test.js')] \
    + [f'tools/{x}' for x in ('exam_guard.js', 'seal_guard.js', 'run_engine.sh', 'gate.sh', 'stats_rule.py', 'tables.py', 'cut_tape.py', 'days.py', 'report.py', 'exam_checks.py', 'make_pins.sh')] \
    + [f'builders/{x}' for x in ('tokmeta.py', 'mkmeta.py', 'mkpoolfee.py')] \
    + [f'join/{x}' for x in ('meta.js', 'unknown_pools.js', 'resolve_unknown.py', 'anchors.py', 'decimals.js', 'pools.js', 'pass1.js', 'finalize.js', 'cut_v4.js', 'fetch_ethusd.py', 'glue.py', 'addr_lists.js')]
M = [  # id, file, anchor (must occur once), replacement, cases that must go RED
 ('M1-pin-anchors', 'run_exam.sh', '|| refuse END "pins/${k%%:*} is not the registered pin file', '|| say "MUTATION unchecked pins/${k%%:*}', ['H1a', 'H1b', 'H1c', 'H1d']),
 ('M2-seam-recheck', 'run_exam.sh', 'seam_gate $RL/seam_gate.recheck.json ', ': MUTATION ', ['B1a', 'B1b', 'B1c', 'B1d', 'B1e']),
 ('M3-seam-bound', 'tools/exam_checks.py', 'SEAM_BOUND = 5878', 'SEAM_BOUND = 5879', ['B1c']),
 ('M4-seam-fields', 'tools/exam_checks.py', "SEAM_FIELDS = ('price_eth', 'price_usd', 'usd', 'depth1_eth', 'depth5_eth')", "SEAM_FIELDS = ('price_eth', 'price_usd', 'usd', 'depth1_eth', 'depth5_eth', 'eth_usd')", ['B1e']),
 ('M5-prior-end', 'run_exam.sh', "grep -q '^REFUSED END ' $ST/REFUSED; then refuse END", "grep -q 'MUTATION' $ST/REFUSED; then refuse END", ['H2c']),
 ('M6-final', 'run_exam.sh', '[ -f $ST/FINAL ] && refuse END', '[ -f $ST/FINAL ] && false && refuse END', ['H2f']),
 ('M7-posted', 'run_exam.sh', '[ -f $ST/MANIFEST_POSTED ] || refuse RESUMABLE', '[ -f $ST/MANIFEST_POSTED ] || true MUTATION', ['H3a']),
 ('M8-posted-hash', 'run_exam.sh', '[ "$P2" = "$MS" ] || refuse END', 'true || refuse END', ['H3b', 'H3c']),
 ('M9-manifest-recheck', 'run_exam.sh', '(cd $WORK && sha256sum --quiet --strict -c state/manifest.sha256) > $RL/manifest.check 2>&1 || refuse END "manifest check failed (a run-time',
  'true || refuse END "MUTATION (a run-time', ['H3d']),
 ('M10-step-recheck', 'run_exam.sh', 'sha256sum --quiet --strict -c $ST/$1.sha256 > $RL/recheck_$1.log 2>&1 ||', 'true ||', ['H2b']),
 ('M11-engine-pin', 'tools/exam_checks.py', "elif r['engine_sha'] not in allowed[r['engine']]:", 'elif False:', ['H2a']),
 ('M12-output-content', 'tools/exam_checks.py', "if c != ok_rows[0].get('content_sha256'):", 'if False:', ['H2e']),
 ('M13-cap-diff', 'tools/exam_checks.py', "            if d: why = f'record {k + 1}: not a registered cap change: {d}'; break", '            pass', ['L22c', 'L22g']),
 ('M14-cap-fired', 'tools/exam_checks.py', '        if len(recs) > fired.get(rel, 0):', '        if False:', ['L22e']),
 ('M15-cap-class', 'run_exam.sh', '&& refuse CAP "engine run $L stopped', '&& refuse END "engine run $L stopped', ['L22a', 'L22f']),
 ('M16-cap-resume', 'run_exam.sh', "if [ -f $ST/REFUSED ] && grep -q '^REFUSED CAP ' $ST/REFUSED; then", 'if false; then', ['L22b']),
 ('M17-block-pin', 'run_exam.sh', 'days.py verify tape $ST/tape_block.json $BLOCK_PIN --sha256 $PIN_BLOCK_SHA', 'days.py verify tape $ST/tape_block.json /home/green/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv', ['H1f']),
 ('M23-kill-class', 'run_exam.sh', '&& refuse RESUMABLE "engine run $L died without completing', '&& refuse END "engine run $L died without completing', ['K1', 'K2']),
 ('M24-kill-any-failure', 'tools/exam_checks.py', "        ok, why = ex in DEATH_EXITS and sig,", "        ok, why = True,", ['K3', 'K7']),
 ('M25-unrecorded-refused', 'tools/exam_checks.py', "            else: status[L] = 'unrecorded'", "            else: bad.append(f'{L}: MUTATION unrecorded')", ['K4']),
 ('M26-escalation', 'run_exam.sh', '[ "$c" = RESUMABLE ] && [ -f $ST/stats.started ] && c=END', '[ "$c" = RESUMABLE ] && false && c=END', ['K5']),
 ('M27-deaths-disclosed', 'tools/report.py', "    if os.path.exists(dp):", "    if False:", ['R11']),
 ('M28-death-exits', 'tools/exam_checks.py', "DEATH_EXITS = {'137': 'SIGKILL', '143': 'SIGTERM', '129': 'SIGHUP', '130': 'SIGINT'}", "DEATH_EXITS = {'137': 'SIGKILL'}", ['K6', 'K7']),
 ('M29-step9-resume-disclosed', 'run_exam.sh', 'then death "step 9 RESUMED after an interrupted start', 'then : "step 9 RESUMED after an interrupted start', ['KR3']),
 ('M30-rerun-disclosed', 'run_exam.sh', 'death "$L: RE-RUN unchanged', ': "$L: RE-RUN unchanged', ['K2', 'K4', 'K6', 'KR1']),
 ('M18-old-agree', 'tools/report.py', "agree[r]['agree'] = agree[r]['majority_same']", "agree[r]['agree'] = agree[r]['majority_same'] and A0['v'][r] == P['v'][r]; half = half and A0['v'][r] == P['v'][r]", ['R1']),
 ('M19-holm-p1', 'tools/report.py', "pv = lambda b: 1.0 if (not b['gates_ok'] or b['p'] is None) else b['p']", "pv = lambda b: 1.0 if b['p'] is None else b['p']", ['R3']),
 ('M20-withhold', 'tools/report.py', "WH = {r: P['v'][r] == CT for r in R}", 'WH = {r: False for r in R}', ['R5']),
 ('M21-swallow', 'tools/report.py', "    for ln in open(os.path.join(ST, 'ledgers.sha256')):", "    for ln in (open(os.path.join(ST, 'ledgers.sha256')) if os.path.exists(os.path.join(ST, 'ledgers.sha256')) else []):", ['R7']),
 ('M22-stats-src', 'tools/report.py', "if s.get('src_sha256') != sha(f):", 'if False:', ['R8']),
]
LOG = F + '/tests/mutation_check.log'; lines = []; ok = bad = 0
scr = tempfile.mkdtemp(prefix='mutation.', dir='/tmp/claude-1000')
try:
    for mid, f, a, b, want in M:
        K = os.path.join(scr, mid, 'kit')
        for x in FILES: os.makedirs(os.path.dirname(os.path.join(K, x)), exist_ok=True); shutil.copy2(os.path.join(F, x), os.path.join(K, x))
        s = open(os.path.join(K, f)).read()
        if s.count(a) != 1: bad += 1; lines.append(f'FAIL  {mid}: anchor found {s.count(a)} times in {f}'); continue
        open(os.path.join(K, f), 'w').write(s.replace(a, b))
        log = os.path.join(scr, mid, 'log')
        if f == 'tools/report.py':
            subprocess.run(['python3', F + '/tests/testR/test_report.py', os.path.join(K, f)], env=dict(os.environ, TESTR_LOG=log), capture_output=True)
        else:
            subprocess.run(['bash', F + '/tests/testC/run_testC.sh'], env=dict(os.environ, TESTC_KIT=K, TESTC_LOG=log), capture_output=True)
        red = sorted(set(m.group(1) for m in re.finditer(r'^FAIL\s+(\S+)', open(log).read(), re.M))) if os.path.exists(log) else []
        miss = [w for w in want if w not in red]
        if miss: bad += 1; lines.append(f'FAIL  {mid} ({f}): expected RED {miss}; RED were {red}')
        else: ok += 1; lines.append(f'PASS  {mid} ({f}): RED as required {want}; all RED cases {red}')
        print(lines[-1], flush=True)
finally:
    shutil.rmtree(scr, ignore_errors=True)
lines.append(f'RESULT mutations caught {ok} of {ok + bad}')
open(LOG, 'w').write('\n'.join(lines) + '\n'); print(lines[-1])
sys.exit(0 if bad == 0 else 1)
