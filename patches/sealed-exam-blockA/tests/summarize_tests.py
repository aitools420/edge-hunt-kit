#!/usr/bin/env python3
"""summarize_tests.py — tests/TESTS.json and tests/TESTS.md from the test logs (no hand-copied result)."""
import json, os, re
T = '/home/green/projects/patches/sealed-exam-blockA/tests'
S, md = [], ['# Tests (open data only)', '']
ad = open(f'{T}/testA/testAD.log').read() if os.path.exists(f'{T}/testA/testAD.log') else ''
for ln in ad.splitlines():
    if ln.startswith('TEST A rule #1'): S.append('Test A (constants only), rule #1: the exam engine with its window constants set back to 09-08..09-26 and the exam reader reading V2/V3 through the runner-built links — ' + ln.split(': ', 1)[1] + ' against the Option A engine\'s own output (proof/out/st_A_batch).')
    if ln.startswith('TEST A rule #2'): S.append('Test A (constants only), rule #2: ' + ln.split(': ', 1)[1] + ' against proof/out/grid_A_batch.')
    if ln.startswith('TEST D'): S.append('Test D (mutation): the rule #1 Test A copy with ONE window constant broken (first assessment 1 h later) — ' + ln.split(': ', 1)[1] + ' (must be RED).')
if os.path.exists(f'{T}/testB/check_testB.json'):
    c = json.load(open(f'{T}/testB/check_testB.json'))
    runs = c['runs']
    S.append(f"Test B (windowing, plumbing; window 09-19 warm-up / 09-22.. entries / CUT 09-26T00:00Z; 2 seeds): {'PASS' if not c['fails'] else 'FAIL ' + '; '.join(c['fails'])}. "
             f"{len(runs)} engine outputs: strategy rows outside their window {sum(v['outside'] for v in runs.values())}; exits at/after the cut {sum(v['exit_after_cut'] for v in runs.values())}; "
             f"booked 'end' {sum(v['end'] for v in runs.values())} (all at the data end: {sum(v['end_not_at_data_end'] for v in runs.values()) == 0}); data end {sorted(set(v['data_end'] for v in runs.values()))}; "
             f"last signals {json.dumps({k: v['sig_max'] for k, v in runs.items() if 'primary' in k})}.")
    st = c['steps']
    S.append(f"Test B tables: meta {st['table_meta']['out_rows']} rows (09-27 rows kept verbatim {st['table_meta']['old_rows_kept_verbatim']}, rebuild differs on {st['table_meta']['rebuild_differences']} old rows: {st['table_meta']['rebuild_difference_kinds']}; new {st['table_meta']['new_rows_kept']}); "
             f"poolfee {st['table_poolfee']['out_rows']} rows (rebuild differs on {st['table_poolfee']['rebuild_differences']}; new {st['table_poolfee']['new_rows_kept']}).")
    S.append(f"Test B cuts: V2/V3 {st['cut_tape']['kept']} rows kept of {st['cut_tape']['read']} read (inversions {st['cut_tape']['inversions']}); V4-wide {st['cut_wide']['kept']} of {st['cut_wide']['read']}; "
             f"locked tape {st['cut_lock']['kept']} of {st['cut_lock']['read']} (max lateness {st['cut_lock']['maxLateBlocks']} blocks, late rows kept after the first at-cut row {st['cut_lock']['lateKeptAfterCutRow']}); two cut rows in the test registry: {len(c['registry_cut_rows']) == 2}.")
    S.append('Test B join vs the 09-27 join, row by row: ' + '; '.join(f"{d} identical {v.get('identical', 0)} differ {v.get('differ', 0)} only-new {v.get('only_mine', 0)} only-09-27 {v.get('only_orig', 0)}" + (f" fields {v.get('fields')}" if v.get('differ') else '') for d, v in c['join_consistency'].items()) + '.')
    S.append(f"Test B report.md first line: {c['report_first_line']}")
if os.path.exists(f'{T}/testB2/testB2.log'):
    b2 = open(f'{T}/testB2/testB2.log').read().splitlines()
    S.append('Test B2 (the join\'s network steps on known items): ' + ' '.join(l for l in b2 if l.startswith('{') or l.startswith('TEST')))
if os.path.exists(f'{T}/testC/testC.log'):
    lines = open(f'{T}/testC/testC.log').read().splitlines()
    res = [l for l in lines if l.startswith('RESULT')]
    S.append(f"Test C (refusals, throwaway copies): {res[-1] if res else 'no result'} — " + '; '.join(re.sub(r'\s+\(exit.*', '', l[6:]) for l in lines if l.startswith('PASS') or l.startswith('FAIL')))
if os.path.exists(f'{T}/seal_guard/seal_guard_test.log'):
    g = open(f'{T}/seal_guard/seal_guard_test.log').read().splitlines()
    S.append('Seal guard self-test (twinfix seal_guard_test.sh against this folder\'s byte-identical copy, synthetic files): ' + ' '.join(l for l in g if l.startswith('RESULT')))
md += [f'- {s}' for s in S]
json.dump(dict(summary=S), open(f'{T}/TESTS.json', 'w'), indent=1)
open(f'{T}/TESTS.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(S))
