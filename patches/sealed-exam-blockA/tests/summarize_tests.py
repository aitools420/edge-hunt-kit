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
    S.append('Test B join vs the 09-27 join, row by row (after the orientation pin): ' + '; '.join(f"{d} identical {v.get('identical', 0)} differ {v.get('differ', 0)} only-new {v.get('only_mine', 0)} only-09-27 {v.get('only_orig', 0)}" + (f" fields {v.get('fields')}" if v.get('differ') else '') for d, v in c['join_consistency'].items()) + '.')
    if c.get('seam_gate'):
        g = c['seam_gate']
        S.append(f"Test B under the exam's B1 seam gate (pond #330; tools/exam_checks.py seam, the code run_exam.sh calls in step 6, ENFORCED by check_testB.py since 2026-10-07): {'PASS' if g.get('ok') else 'FAIL'} — "
                 + '; '.join(f"{d['day']} rule ({d['rule']}) differ {d['differ']} only-new {d['only_mine']} only-09-27 {d['only_orig']}" for d in g.get('days', []))
                 + f"; bound {g.get('bound')} rows in {g.get('allowed_fields_first_day')}. Cut-edge day {c['cut_edge_day']['day']} (not compared by the exam): {'ok' if c['cut_edge_day']['ok'] else 'FAIL'}, fields {c['cut_edge_day']['fields']}.")
    if os.path.exists(f'{T}/testB/check_testB_mutation.log'):
        ml = [l for l in open(f'{T}/testB/check_testB_mutation.log').read().splitlines() if l.startswith('mutation')]
        S.append(f"check_testB.py goes RED on mutated COPIES of the consist files: {sum(1 for l in ml if '-> exit 1;' in l)} of {len(ml)} RED — " + '; '.join(re.sub(r' -> exit.*', '', l[9:]) for l in ml) + '.')
    if os.path.exists(f'{T}/testB/seam_bound_evidence.json'):
        ev = json.load(open(f'{T}/testB/seam_bound_evidence.json'))
        sims = [e for e in ev['evidence'] if 'result' in e]
        S.append(f"B1 bound from open data (tests/testB/seam_bound_evidence.json): the replay of finalize.js's causal rule (tests/testB/seam_sim.py) gives {sims[0]['result']['counts']['differ']} rows on Test B's first day "
                 f"(observed {ev['evidence'][0]['differ']}) and predicts {sims[1]['result']['counts']['differ']} of {sims[1]['result']['counts']['first_day_rows_total']} rows for the exam's 09-25; registered bound {ev['rule']['bound_rows']}.")
    S.append(f"Test B report.md first line (written by the 4884d01 runner and report.py, BEFORE pond #330: its AGREE rule is the old one; Test B's engines and join were not re-run after #330 — the #330 changes are covered by Tests C and R and by check_testB.py's seam gate on Test B's own outputs): {c['report_first_line']}")
if os.path.exists(f'{T}/testB2/testB2.log'):
    b2 = open(f'{T}/testB2/testB2.log').read().splitlines()
    S.append('Test B2 (the join\'s network steps on known items): ' + ' '.join(l for l in b2 if l.startswith('{') or l.startswith('TEST')))
if os.path.exists(f'{T}/testC/testC.log'):
    lines = open(f'{T}/testC/testC.log').read().splitlines()
    res = [l for l in lines if l.startswith('RESULT')]
    S.append(f"Test C (refusals on THROWAWAY trees of the current kit with a synthetic fake home, every heavy step a stub; tests/testC/make_tree.py): {res[-1] if res else 'no result'} — " + '; '.join(re.sub(r'\s+\(exit.*', '', l[6:]) for l in lines if l.startswith('PASS') or l.startswith('FAIL')))
if os.path.exists(f'{T}/testR/testR.log'):
    lines = open(f'{T}/testR/testR.log').read().splitlines()
    S.append('Test R (tools/report.py on synthetic work folders: H1, H2, M5, M6, L4): ' + ' '.join(l for l in lines if l.startswith('RESULT')) + ' — ' + '; '.join(re.sub(r' :: .*', '', l[6:]) for l in lines if l.startswith(('PASS', 'FAIL'))))
if os.path.exists(f'{T}/mutation_check.log'):
    lines = open(f'{T}/mutation_check.log').read().splitlines()
    S.append('Mutation check (each new guard broken in a scratch copy of the kit; the cases testing it must go RED): ' + ' '.join(l for l in lines if l.startswith('RESULT')) + ' — ' + '; '.join(re.sub(r': RED as required (\[[^]]*\]).*', r' -> \1 RED', l[6:]) for l in lines if l.startswith(('PASS', 'FAIL'))))
if os.path.exists(f'{T}/seal_guard/seal_guard_test.log'):
    g = open(f'{T}/seal_guard/seal_guard_test.log').read().splitlines()
    S.append('Seal guard self-test (twinfix seal_guard_test.sh against this folder\'s byte-identical copy, synthetic files): ' + ' '.join(l for l in g if l.startswith('RESULT')))
md += [f'- {s}' for s in S]
json.dump(dict(summary=S), open(f'{T}/TESTS.json', 'w'), indent=1)
open(f'{T}/TESTS.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(S))
