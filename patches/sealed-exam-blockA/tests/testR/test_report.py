#!/usr/bin/env python3
"""test_report.py — TEST R (pond #330 H1, H2, M5, M6, L4): tools/report.py on SYNTHETIC work folders only (made-up stats files, fake
outputs, fake pins; nothing real is read). Usage: test_report.py [<report.py>] (default: the kit's tools/report.py; a mutated copy is
passed by tests/mutation_check.sh to prove the cases go RED). Writes tests/testR/testR.log unless TESTR_LOG is set.
  R1  M5: primary PASS, the exam cell alone at seed 20260927 NOT SHOWN, 10 of 20 alone seeds PASS  -> qualifies (READING PASS)
  R2  M5: the same with 9 of 20 alone seeds PASS                                                -> does NOT qualify (PASS, draw-dependent)
  R3  M6: rule #1 data gate FAILS at p 0.001, rule #2 p 0.02                                        -> rule #2 must NOT pass
  R4  M6 control: rule #1 gate PASSES at p 0.001, rule #2 p 0.02                                   -> rule #2 PASSES (Holm step 2)
  R5  H2: in R3, none of rule #1's numbers (primary or alone) is in report.md or report.json; they are in withheld_stats.json, whose
          sha256 report.md prints
  R6  H1: report.md's first lines carry the runner's and the three pin files' sha256 (64-hex) and the manifest's
  R7  H1: a failure in sections 6-9 (state/ledgers.sha256 missing) refuses: exit 2, NO report.md, NO report.json, no verdict printed
  R8  H2: a stats file computed from different bytes than the output runs.tsv records refuses (exit 2, nothing written)
  R9  L4: a CAN'T TELL (data) rule reads "final for Block A ... waits for Block B"; qualifies false
  R10 M5 labels: primary NOT SHOWN with 10 of 20 alone seeds PASS reads "NOT SHOWN, draw-dependent"; qualifies false
  R11 an engine death (kernel kill) and its re-run are disclosed in report.md section 10"""
import sys, os, json, gzip, hashlib, shutil, subprocess, tempfile
KIT = '/home/green/projects/patches/sealed-exam-blockA'
REPORT = sys.argv[1] if len(sys.argv) > 1 else KIT + '/tools/report.py'
LOG = os.environ.get('TESTR_LOG', KIT + '/tests/testR/testR.log')
CUT = 1791331200
SEEDS = [str(20260927 + i) for i in range(20)]
sha = lambda b: hashlib.sha256(b).hexdigest()
PASS = dict(d=5.0, ci=[1.0, 9.0], p=0.001, n=400, coins=100, drop5=4.0, gate='PASS')
NOTS = dict(d=2.0, ci=[-1.0, 6.0], p=0.03, n=400, coins=100, drop5=1.0, gate='PASS')


def stats(label, cell, spec, outbytes):
    return dict(rule=1 if 'rule1' in label else 2, cell=cell, src_sha256=sha(outbytes),
                bar=dict(d_mean=spec['d'], ci95=spec['ci'], p_one_sided=spec['p'], n=spec['n'], coins=spec['coins'], drop5=spec['drop5'], se_cons=1.5, n_rows=spec['n']),
                money_test=dict(raw_heavy_mean=spec['d'] - 1, raw_heavy_ci95=[spec['ci'][0] - 1, spec['ci'][1] - 1], n=spec['n'], note='synthetic'),
                reported=dict(synthetic_d=spec['d'], synthetic_p=spec['p']), prefilter=dict(rows_kept=10, skipDepth_dropped={}),
                gate=dict(status=dict(G1=spec['gate'], G4='PASS', G5='PASS', G10='PASS'),
                          components=dict(S=dict(priced_share=0.9 if spec['gate'] == 'PASS' else 0.4, g4_small_share=0.05, g5_fail=0), WR=dict(priced_share=0.9), WA=dict(priced_share=0.9))),
                meta=dict(endTs=CUT - 10, v23Files={'2026-10-06': dict(n=5, first=1, last=2)}, v4Files={'2026-10-06': dict(n=5, first=1, last=2)}, twinDistinct={}))


def build(d, prim1, prim2, alone1, alone2, src_mismatch=False):
    """alone1/alone2: {seed: spec}. Writes a complete synthetic work folder and pins; returns (work, report.md, runner)."""
    root = os.path.join(d, 'kit'); W = os.path.join(root, 'work')
    for sub in ('state', 'stats', 'runlogs', 'v4join/out', 'tables', 'out', '../pins'):
        os.makedirs(os.path.join(W, sub), exist_ok=True)
    for f in ('code.sha256', 'inputs.sha256', 'block_days.tsv'): open(os.path.join(root, 'pins', f), 'w').write(f'synthetic {f}\n')
    runner = os.path.join(root, 'run_exam.sh'); open(runner, 'w').write('# synthetic runner\n')
    ST, RL = os.path.join(W, 'state'), os.path.join(W, 'runlogs')
    open(os.path.join(ST, 'G3.rc'), 'w').write('0\n')
    for k in ('tape', 'wide', 'lock'): json.dump(dict(sha256=k[0] * 64, kept=1, bytes=10, maxLateBlocks=0), open(os.path.join(ST, f'cut_{k}.json'), 'w'))
    for k in ('tape_open', 'tape_block', 'wide_open', 'wide_block'): json.dump({'2026-10-01': dict(sha256='d' * 64, bytes=1, path='/synthetic')}, open(os.path.join(ST, f'{k}.json'), 'w'))
    open(os.path.join(ST, 'ledgers.sha256'), 'w').write('e' * 64 + '  robinhood-token-births.json\n')
    open(os.path.join(ST, 'manifest.sha256'), 'w').write('f' * 64 + '  tables/meta.tsv\n')
    open(os.path.join(ST, 'MANIFEST_POSTED'), 'w').write(sha(open(os.path.join(ST, 'manifest.sha256'), 'rb').read()) + '\n')
    json.dump(dict(ok=True, check='seam'), open(os.path.join(ST, 'seam_gate.json'), 'w'))
    open(os.path.join(W, 'v4join', 'ethusd_coingecko.json'), 'w').write('{"prices":[]}')
    open(os.path.join(RL, 'exam.log'), 'w').write(f'2026-10-07T03:00:00Z run_exam.sh start; sha256 {sha(b"# synthetic runner" + bytes([10]))} ({runner})\n')
    runs = []
    labs = [('primary_rule1', 'C2P', prim1), ('primary_rule2', 'D25L48', prim2)] + [(f'alone_rule1_s{s}', 'C2P', alone1[s]) for s in SEEDS] + [(f'alone_rule2_s{s}', 'D25L48', alone2[s]) for s in SEEDS]
    for lab, cell, spec in labs:
        content = f'{{"synthetic":"{lab}"}}\n'.encode(); gz = gzip.compress(content, mtime=0)
        open(os.path.join(W, 'out', lab + '.ndjson.gz'), 'wb').write(gz)
        s = stats(lab, cell, spec, gz)
        if src_mismatch and lab == 'primary_rule2': s['src_sha256'] = '0' * 64
        json.dump(s, open(os.path.join(W, 'stats', lab + '.json'), 'w'))
        open(os.path.join(RL, lab + '.opened'), 'w').write('')
        runs.append('\t'.join([lab, 'a' * 64, '/synthetic/engine.js', '2026-10-07T04:00:00Z', '2026-10-07T04:10:00Z', 'exit=0', 'elapsed=1', 'user_s=1', 'maxrss_kb=2048',
                               'opened=0', f'content_sha256={sha(content)}', 'guard=' + 'b' * 64, 'env=']))
    open(os.path.join(RL, 'runs.tsv'), 'w').write('\n'.join(runs) + '\n')
    return W, os.path.join(root, 'report.md'), runner


def run(W, md, runner):
    r = subprocess.run(['python3', REPORT, W, md, str(CUT), ' '.join(SEEDS), runner], capture_output=True, text=True)
    rep = open(md).read() if os.path.exists(md) else None
    rj = open(os.path.join(W, 'report.json')).read() if os.path.exists(os.path.join(W, 'report.json')) else None
    return r, rep, rj


res, LINES = [], []
def check(name, ok, detail):
    res.append(ok); LINES.append(f"{'PASS' if ok else 'FAIL'}  {name} :: {detail}")


tmp = tempfile.mkdtemp(prefix='testR.', dir='/tmp/claude-1000')
try:
    def seeds(npass, seed0):
        a = {s: dict(NOTS) for s in SEEDS}; a[SEEDS[0]] = dict(seed0)
        k = 1 if seed0 is PASS else 0
        for s in SEEDS[1:]:
            if k >= npass: break
            a[s] = dict(PASS); k += 1
        return a
    allpass = {s: dict(PASS) for s in SEEDS}
    # R1 / R2
    for name, npass, want_q, want_read in (('R1', 10, True, 'READING: PASS;'), ('R2', 9, False, 'READING: PASS, draw-dependent;')):
        W, md, rn = build(os.path.join(tmp, name), PASS, PASS, seeds(npass, NOTS), allpass)
        r, rep, rj = run(W, md, rn)
        q = json.loads(rj)['qualifies']['1'] if rj else None
        first = rep.split('\n')[0] if rep else r.stderr
        check(f'{name} M5: primary PASS, seed 20260927 alone NOT SHOWN, {npass}/20 alone seeds PASS -> qualifies {want_q}',
              r.returncode == 0 and q is want_q and want_read in first and f'{npass} of 20 alone seeds PASS' in first,
              f"exit {r.returncode}; report.json qualifies['1'] = {q}; line 1: {first[:230]}")
        if name == 'R1':
            rl = [ln for ln in rep.split('\n') if ln.startswith('READING · rule #1')]
            check('R1 the READING line prints seed 20260927 alone as information only', bool(rl) and 'NOT SHOWN — information only' in rl[0], (rl or ['none'])[0][:230])
    # R3 / R4 / R5 / R9
    G1F = dict(d=7.654321, ci=[3.21, 9.87], p=0.00123457, n=345, coins=67, drop5=6.54321, gate='FAIL')
    G1P = dict(G1F, gate='PASS')
    R2P = dict(d=4.0, ci=[0.5, 8.0], p=0.02, n=400, coins=100, drop5=3.0, gate='PASS')
    A1F = {s: dict(d=8.111111, ci=[2.22, 9.99], p=0.000777, n=345, coins=67, drop5=7.1, gate='FAIL') for s in SEEDS}
    W, md, rn = build(os.path.join(tmp, 'R3'), G1F, R2P, A1F, allpass)
    r3, rep3, rj3 = run(W, md, rn)
    j3 = json.loads(rj3) if rj3 else {}
    check('R3 M6: rule #1 data gate FAIL at p 0.001, rule #2 at p 0.02 -> rule #2 NOT SHOWN (rule #1 enters Holm with p = 1)',
          r3.returncode == 0 and j3['primary']['2']['verdict'] == 'NOT SHOWN' and j3['primary']['1']['verdict'] == "CAN'T TELL (data)" and j3['primary']['2']['holm']['threshold'] == 0.0125,
          f"exit {r3.returncode}; verdicts #1 {j3.get('primary', {}).get('1', {}).get('verdict')} #2 {j3.get('primary', {}).get('2', {}).get('verdict')}; rule #2 Holm {j3.get('primary', {}).get('2', {}).get('holm')}")
    W4, md4, rn4 = build(os.path.join(tmp, 'R4'), G1P, R2P, {s: dict(G1P) for s in SEEDS}, allpass)
    r4, rep4, rj4 = run(W4, md4, rn4)
    j4 = json.loads(rj4) if rj4 else {}
    check('R4 M6 control: rule #1 gate PASS at p 0.001, rule #2 at p 0.02 -> rule #2 PASS (Holm step 2, 0.025)',
          r4.returncode == 0 and j4['primary']['2']['verdict'] == 'PASS' and j4['primary']['2']['holm']['threshold'] == 0.025,
          f"exit {r4.returncode}; verdicts #1 {j4.get('primary', {}).get('1', {}).get('verdict')} #2 {j4.get('primary', {}).get('2', {}).get('verdict')}; rule #2 Holm {j4.get('primary', {}).get('2', {}).get('holm')}")
    secret = ['7.654321', '0.00123457', '6.54321', '3.21', '9.87', '345 / 67', '8.111111', '0.000777', '9.99', '6.654321']
    leak = [x for x in secret if x in (rep3 or '') or x in (rj3 or '')]
    wfile = os.path.join(W, 'withheld_stats.json'); wtxt = open(wfile).read() if os.path.exists(wfile) else ''
    check('R5 H2: none of rule #1\'s statistics (primary or alone) is printed in report.md or report.json',
          r3.returncode == 0 and not leak and '7.654321' in wtxt and '8.111111' in wtxt and sha(wtxt.encode()) in rep3,
          f"leaked {leak}; withheld_stats.json holds them: {'7.654321' in wtxt and '8.111111' in wtxt}; its sha256 printed in report.md: {bool(wtxt) and sha(wtxt.encode()) in (rep3 or '')}")
    rd = [ln for ln in (rep3 or '').split('\n') if ln.startswith('READING · rule #1')]
    check("R9 L4: a CAN'T TELL (data) rule reads final for Block A, waits for Block B; qualifies false",
          bool(rd) and 'final for Block A' in rd[0] and 'waits for Block B' in rd[0] and j3['qualifies']['1'] is False, (rd or ['none'])[0][:230])
    # R6 (on R4's report)
    L4 = rep4.split('\n') if rep4 else []
    kit4 = os.path.join(tmp, 'R4', 'kit'); hs = {f: sha(open(os.path.join(kit4, 'pins', f), 'rb').read()) for f in ('code.sha256', 'inputs.sha256', 'block_days.tsv')}
    ok6 = len(L4) > 2 and sha(open(rn4, 'rb').read()) in L4[1] and all(h in L4[1] for h in hs.values()) and sha(open(os.path.join(W4, 'state', 'manifest.sha256'), 'rb').read()) in L4[2]
    check('R6 H1: report.md lines 2-3 carry the runner, the three pin files and the manifest (full sha256)', ok6, (L4[1][:200] if len(L4) > 1 else 'no report'))
    # R7
    W7, md7, rn7 = build(os.path.join(tmp, 'R7'), PASS, PASS, allpass, allpass); os.remove(os.path.join(W7, 'state', 'ledgers.sha256'))
    r7, rep7, rj7 = run(W7, md7, rn7)
    check('R7 H1: a section 6-9 failure refuses: exit 2, no report.md, no report.json, no verdict printed',
          r7.returncode == 2 and rep7 is None and rj7 is None and 'VERDICT' not in r7.stdout, f"exit {r7.returncode}; report.md {'written' if rep7 else 'absent'}; stderr {r7.stderr.strip()[:160]}")
    # R8
    W8, md8, rn8 = build(os.path.join(tmp, 'R8'), PASS, PASS, allpass, allpass, src_mismatch=True)
    r8, rep8, rj8 = run(W8, md8, rn8)
    check('R8 H2: a stats file computed from other bytes than the recorded output refuses', r8.returncode == 2 and rep8 is None and 'src_sha256' in r8.stderr,
          f"exit {r8.returncode}; stderr {r8.stderr.strip()[:200]}")
    # R10
    W10, md10, rn10 = build(os.path.join(tmp, 'R10'), NOTS, PASS, seeds(10, PASS), allpass)
    r10, rep10, rj10 = run(W10, md10, rn10)
    rd10 = [ln for ln in (rep10 or '').split('\n') if ln.startswith('READING · rule #1')]
    check('R10 M5 labels: primary NOT SHOWN with 10/20 alone seeds PASS reads "NOT SHOWN, draw-dependent"; qualifies false',
          r10.returncode == 0 and bool(rd10) and 'NOT SHOWN, draw-dependent' in rd10[0] and json.loads(rj10)['qualifies']['1'] is False, (rd10 or [r10.stderr])[0][:230])
    # R11
    W11, md11, rn11 = build(os.path.join(tmp, 'R11'), PASS, PASS, allpass, allpass)
    open(os.path.join(W11, 'state', 'ENGINE_DEATHS'), 'w').write('2026-10-07T05:00:00Z alone_rule1_s20260930: RE-RUN unchanged (previous attempt: exit=137)\n')
    os.makedirs(os.path.join(W11, 'failed_outputs')); open(os.path.join(W11, 'failed_outputs', 'alone_rule1_s20260930.x.ndjson.gz'), 'wb').write(b'\x1f\x8b')
    r11, rep11, rj11 = run(W11, md11, rn11)
    sec = (rep11 or '').split('## 10')[-1]
    check('R11 a kernel-killed engine\'s death and re-run are disclosed in report.md section 10 (with the moved-aside output\'s sha256)',
          r11.returncode == 0 and 'RE-RUN unchanged (previous attempt: exit=137)' in sec and 'kept unread: work/failed_outputs/alone_rule1_s20260930.x.ndjson.gz' in sec, sec.strip()[:230].replace('\n', ' | '))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
LINES.append(f'RESULT pass {sum(res)} fail {len(res) - sum(res)} (report.py sha256 {sha(open(REPORT, "rb").read())})')
os.makedirs(os.path.dirname(LOG), exist_ok=True); open(LOG, 'w').write('\n'.join(LINES) + '\n'); print('\n'.join(LINES))
sys.exit(0 if all(res) else 1)
