#!/usr/bin/env python3
"""make_tree.py — TEST C helper (pond #330): a THROWAWAY copy of the CURRENT exam kit in which NOTHING real can be read.

  make_tree.py tree <case_dir> [--cut-future]
      <case_dir>/tree = the kit's runner and tools, with (1) the kit prefix replaced by the tree, (2) EVERY real data root replaced by a
      synthetic fake home <case_dir>/fh (raw tapes, V4-wide files, the locked tape, ledgers, noxabot state, the 09-27 tables and join,
      SEALED-HOLDOUT, the hunter's status file), (3) the window constants of Test B's shifted, OPEN calendar (CUT 2026-09-26, block days
      09-22..09-25, join first day 09-20, CONSIST_DAYS 09-20 09-21, 2 seeds), and (4) every heavy or networked step replaced by a STUB that
      refuses to run (engines are never started: tools/run_engine.sh is a stub whose mode is read from tree/STUB_ENGINE).
      The fake home holds one-line synthetic files only. Then the tree's OWN tools/make_pins.sh writes its pins and the PIN_* anchors.
      --cut-future: CUT = now + 1 day (for the clock refusal; the real runner can no longer be tested before its instant).
      The script asserts that no tree file names a real path under /home/green except the two frozen analyzers (read-only hashing).
  make_tree.py state <case_dir> <days_verified|net|cuts|tables|join> [--consist '<json {day: {field: value}}>']
      Writes the work state of every step up to the given one, exactly as the runner's mark() does: the step's output files (synthetic),
      <step>.sha256 (sha256sum format, absolute paths) and <step>.done. --consist overrides fields of the consist_<day>.json files.
  make_tree.py post <case_dir> [--wrong]      : work/state/MANIFEST_POSTED := the manifest's sha256 (or a wrong one)
  make_tree.py runrow <case_dir> <label> <engine relpath> [--engine-sha HEX] [--tamper]
      a synthetic engine output out/<label>.ndjson.gz and its runs.tsv row (exit 0, full hashes); --tamper changes the output afterwards.
  make_tree.py cap <case_dir> <engine relpath> [--extra-line|--lower]
      a cap change: the original copied to work/state/cap_orig/, the RSS guard 3.2e9 raised to 3.6e9 (--lower: 2.0e9; --extra-line: another
      line changed too), and its CAP_CHANGE record."""
import sys, os, json, gzip, hashlib, shutil, subprocess, time, re, calendar
KIT = '/home/green/projects/patches/sealed-exam-blockA'
SRC = os.environ.get('TESTC_KIT', KIT)      # tests/mutation_check.sh points this at a MUTATED copy of the kit; the replaced prefix stays KIT
FILES = ['run_exam.sh'] + [f'engines/{x}' for x in ('engine_st_exam.js', 'engine_grid_exam.js', 'engine_st_exam_h.js', 'engine_grid_exam_h.js', 'v4tape_exam.js', 'guard.js', 'guard_test.js')] \
    + [f'tools/{x}' for x in ('exam_guard.js', 'seal_guard.js', 'run_engine.sh', 'gate.sh', 'stats_rule.py', 'tables.py', 'cut_tape.py', 'days.py', 'report.py', 'exam_checks.py', 'make_pins.sh')] \
    + [f'builders/{x}' for x in ('tokmeta.py', 'mkmeta.py', 'mkpoolfee.py')] \
    + [f'join/{x}' for x in ('meta.js', 'unknown_pools.js', 'resolve_unknown.py', 'anchors.py', 'decimals.js', 'pools.js', 'pass1.js', 'finalize.js', 'cut_v4.js', 'fetch_ethusd.py', 'glue.py', 'addr_lists.js')]
STUBS = {'tools/gate.sh', 'tools/stats_rule.py', 'tools/tables.py', 'tools/cut_tape.py', 'builders/tokmeta.py', 'builders/mkmeta.py', 'builders/mkpoolfee.py',
         'join/meta.js', 'join/unknown_pools.js', 'join/resolve_unknown.py', 'join/anchors.py', 'join/decimals.js', 'join/pools.js', 'join/pass1.js', 'join/finalize.js',
         'join/cut_v4.js', 'join/fetch_ethusd.py', 'join/glue.py', 'join/addr_lists.js'}
ALLOWED_REAL = ('/home/green/projects/patches/blood-stress-2026-09-27/analyze_st.py', '/home/green/projects/patches/blood-grid-depth-history-2026-09-27/analyze_grid.py')
T = dict(CUT=1790380800, READY_AT=1790391600, CUT_DAY='2026-09-26', TAPE_OPEN=['2026-09-19', '2026-09-20', '2026-09-21'], BLOCK=['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25'],
         WIDE_OPEN=['2026-09-20', '2026-09-21'], V4_OPEN=['2026-09-19', '2026-09-20', '2026-09-21'], JOIN0=1789862400, ETH_FROM=1789776000, CUTOFF=1790294400,
         CONSIST=['2026-09-20', '2026-09-21'], SEEDS=['20260927', '20260928'])
CONST = [('CUT=1791331200 ', 'CUT={CUT} '), ('READY_AT=1791342000 ', 'READY_AT={READY_AT} '), ('CUT_DAY=2026-10-07 ', f"CUT_DAY={T['CUT_DAY']} "),
         ('TAPE_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"', f'TAPE_OPEN_DAYS="{" ".join(T["TAPE_OPEN"])}"'),
         ('BLOCK_DAYS="2026-09-27 2026-09-28 2026-09-29 2026-09-30 2026-10-01 2026-10-02 2026-10-03 2026-10-04 2026-10-05 2026-10-06"', f'BLOCK_DAYS="{" ".join(T["BLOCK"])}"'),
         ('WIDE_OPEN_DAYS="2026-09-25 2026-09-26"', f'WIDE_OPEN_DAYS="{" ".join(T["WIDE_OPEN"])}"'), ('V4_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"', f'V4_OPEN_DAYS="{" ".join(T["V4_OPEN"])}"'),
         ('JOIN0_TS=1790294400 ', f"JOIN0_TS={T['JOIN0']} "), ('ETH_FROM=1790208000 ', f"ETH_FROM={T['ETH_FROM']} "), ('TABLE_CUTOFF=1791244800 ', f"TABLE_CUTOFF={T['CUTOFF']} "),
         ('CONSIST_DAYS="2026-09-25 2026-09-26"', f'CONSIST_DAYS="{" ".join(T["CONSIST"])}"'),
         ('SEEDS="20260927 20260928 20260929 20260930 20260931 20260932 20260933 20260934 20260935 20260936 20260937 20260938 20260939 20260940 20260941 20260942 20260943 20260944 20260945 20260946"', f'SEEDS="{" ".join(T["SEEDS"])}"')]
sha = lambda b: hashlib.sha256(b).hexdigest()
shaf = lambda p: sha(open(p, 'rb').read())


def W(p, data, mode=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data if isinstance(data, bytes) else data.encode())
    if mode: os.chmod(p, mode)


def stub(rel, tree):
    if rel.endswith('.sh'): return f'#!/bin/bash\necho "TESTC STUB {rel} called: $*" >&2\nexit 3\n'
    if rel.endswith('.py'): return f'import sys\nprint("TESTC STUB {rel} called", file=sys.stderr)\nsys.exit(3)\n'
    return f'console.error("TESTC STUB {rel} called"); process.exit(3);\n'


RUN_ENGINE_STUB = r'''#!/bin/bash
# TEST C STUB of tools/run_engine.sh: NEVER starts an engine. Mode from TREE/STUB_ENGINE:
#   rss | heap      : the engine's RSS guard / V8's heap cap fired (L22)
#   kill            : the engine was SIGKILLed (GNU time: "Command terminated by signal 9", exit 137), leaving a PARTIAL output
#   term            : the engine was SIGTERMed, e.g. by a reboot ("Command terminated by signal 15", exit 143), leaving a PARTIAL output
#   hang            : a PARTIAL output and the log are written, then the engine "runs" until the test kills the whole tree
#   complete-fail   : the engine wrote a COMPLETE output, then exited 1 by itself
#   ok              : a complete synthetic output and its exit=0 row (full hashes), exit 0
#   fail (default)  : exit 3, no output
L=$1; E=$2; OD=$6; LD=$7; mkdir -p "$LD" "$OD"
MODE=$(cat __TREE__/STUB_ENGINE 2>/dev/null || echo fail); C=-
case $MODE in
  rss)  echo "Error: RSS guard 3300000000 (TESTC STUB)" > $LD/$L.log; rc=1;;
  heap) echo "FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory (TESTC STUB)" > $LD/$L.log; rc=134;;
  kill) printf '\x1f\x8b\x08\x00\x00\x00\x00\x00' > $OD/$L.ndjson.gz; printf 'TESTC STUB engine output...\nCommand terminated by signal 9\n' > $LD/$L.log; rc=137;;
  term) printf '\x1f\x8b\x08\x00\x00\x00\x00\x00' > $OD/$L.ndjson.gz; printf 'TESTC STUB engine output...\nCommand terminated by signal 15\n' > $LD/$L.log; rc=143;;
  hang) printf '\x1f\x8b\x08\x00\x00\x00\x00\x00' > $OD/$L.ndjson.gz; echo "TESTC STUB engine running" > $LD/$L.log; sleep 120; rc=99;;
  complete-fail) printf '{"stub":"%s"}\n' "$L" | gzip -n > $OD/$L.ndjson.gz; echo "Error: thrown after the output was complete (TESTC STUB)" > $LD/$L.log; rc=1;;
  ok)   printf '{"stub":"%s"}\n' "$L" | gzip -n > $OD/$L.ndjson.gz; C=$(printf '{"stub":"%s"}\n' "$L" | sha256sum | cut -c1-64); echo "TESTC STUB ok" > $LD/$L.log; : > $LD/$L.opened; rc=0;;
  *)    echo "TESTC STUB run_engine.sh: engine not run" > $LD/$L.log; rc=3;;
esac
printf '%s\t%s\t%s\t%s\t%s\texit=%s\telapsed=0\tuser_s=0\tmaxrss_kb=0\topened=0\tcontent_sha256=%s\tguard=-\tenv=-\n' "$L" "$(sha256sum $E | cut -c1-64)" "$E" "$(date -u +%FT%TZ)" "$(date -u +%FT%TZ)" "$rc" "$C" >> $LD/runs.tsv
echo "TESTC STUB run_engine.sh $L mode $MODE rc $rc" >&2
exit $rc
'''


STATS_STUB = '''import sys, os, time
# TEST C STUB of tools/stats_rule.py: never computes anything. TREE/STUB_STATS = hang: "runs" until the test kills the whole tree.
if open('__TREE__/STUB_STATS').read().strip() == 'hang' if os.path.exists('__TREE__/STUB_STATS') else False: time.sleep(120)
print("TESTC STUB tools/stats_rule.py called", file=sys.stderr)
sys.exit(3)
'''


def paths(case):
    case = os.path.abspath(case); return case, os.path.join(case, 'tree'), os.path.join(case, 'fh')


def tree(case, future=False):
    case, TR, FH = paths(case)
    if os.path.exists(case): shutil.rmtree(case)
    c = dict(CUT=T['CUT'], READY_AT=T['READY_AT'])
    if future: c['CUT'] = int(time.time()) + 86400; c['READY_AT'] = c['CUT'] + 10800
    REPL = [(KIT, TR), ('/home/green/.openclaw', FH + '/.openclaw'), ('/home/green/noxabot', FH + '/noxabot'),
            ('/home/green/projects/patches/twinfix-2026-10-05', FH + '/projects/patches/twinfix-2026-10-05'),
            ('/home/green/projects/patches/v4-join-2026-09-27', FH + '/projects/patches/v4-join-2026-09-27'),
            ('/home/green/projects/patches/SEALED-HOLDOUT', FH + '/projects/patches/SEALED-HOLDOUT'),
            ('/home/green/projects/patches/edge-machine-2026-09-30', FH + '/projects/patches/edge-machine-2026-09-30'),
            ("HOME = '/home/green'", f"HOME = '{FH}'")]
    for rel in FILES:
        src = open(os.path.join(SRC, rel)).read()
        if rel == 'tools/run_engine.sh': s = RUN_ENGINE_STUB.replace('__TREE__', TR)
        elif rel == 'tools/stats_rule.py': s = STATS_STUB.replace('__TREE__', TR)
        elif rel in STUBS: s = stub(rel, TR)
        else:
            s = src
            for a, b in REPL: s = s.replace(a, b)
            if rel == 'run_exam.sh':
                for a, b in CONST:
                    assert s.count(a) == 1, f'run_exam.sh anchor {a[:50]!r} found {s.count(a)} times'
                    s = s.replace(a, b.format(**c))
        W(os.path.join(TR, rel), s, 0o755 if rel.endswith(('.sh', '.py')) else 0o644)
    for dp, dn, fn in os.walk(TR):                                   # nothing in the tree may name a real data path
        for f in fn:
            txt = open(os.path.join(dp, f), errors='replace').read()
            for m in re.finditer(r'/home/green[^\s\'"`)]*', txt):
                assert m.group(0).startswith(ALLOWED_REAL), f'{os.path.join(dp, f)} names a real path {m.group(0)}'
    # ---- the fake home: synthetic one-line files only ----
    WE = FH + '/.openclaw/workspace/wick-engine/logs'; NX = FH + '/noxabot'
    day_ts = lambda d: calendar.timegm(time.strptime(d + ' 12', '%Y-%m-%d %H'))   # noon UTC of the day
    for d in T['TAPE_OPEN'] + T['BLOCK']: W(f'{WE}/robinhood-tape/tape-{d}.ndjson', f'{{"ts":{day_ts(d)},"tok":"FAKE-TAPE-{d}"}}\n')
    for d in T['WIDE_OPEN'] + T['BLOCK']: W(f'{NX}/logs/v4-wide/uniswap-v4-wide-{d}.ndjson', f'{{"blk":{day_ts(d)},"pool":"FAKE-WIDE-{d}"}}\n')
    W(f'{NX}/logs/uniswap-v4-tape-hole.ndjson', '{"blk":1,"fake":"hole"}\n'); W(f'{NX}/logs/uniswap-v4-tape-backfill.ndjson', '{"blk":1,"fake":"backfill"}\n')
    for f in ('safety-cache.json', 'tokengate-cache.json', 'redteam-scores.json'):
        W(f'{NX}/state/{f}', '{}\n'); os.utime(f'{NX}/state/{f}', (1788220800, 1788220800))      # 2026-09-01, before the seal
    TW = FH + '/projects/patches/twinfix-2026-10-05/inputs'
    for f in ('meta.tsv', 'scam.tsv', 'poolfee.tsv'): W(f'{TW}/{f}', f'FAKE\t{f}\n')
    OJ = FH + '/projects/patches/v4-join-2026-09-27'
    W(f'{OJ}/decimals.json', '{"dec":{},"sym":{}}\n'); W(f'{OJ}/unknown_keys.json', '{}\n')
    for d in sorted(set(T['V4_OPEN'] + T['CONSIST'])): W(f'{OJ}/out/v4-swaps-{d}.ndjson.gz', gzip.compress(f'{{"fake":"09-27 join {d}"}}\n'.encode(), mtime=0))
    W(FH + '/projects/patches/edge-machine-2026-09-30/machine/status.json', '{"step":"idle"}\n')
    hdr = 'computed_utc\tday\tfeed\tsha256_of_uncompressed_content\tbytes_uncompressed\tsource_file\n'
    row = lambda d, feed, p: f'2026-10-07T00:00:00Z\t{d}\t{feed}\t{shaf(p)}\t{os.path.getsize(p)}\t{p}\n'
    W(FH + '/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv', hdr + ''.join(row(d, 'v2v3-tape', f'{WE}/robinhood-tape/tape-{d}.ndjson') + row(d, 'v4-wide', f'{NX}/logs/v4-wide/uniswap-v4-wide-{d}.ndjson') for d in T['BLOCK']))
    W(TR + '/pins/open_days.tsv', hdr + ''.join(row(d, 'v2v3-tape', f'{WE}/robinhood-tape/tape-{d}.ndjson') for d in T['TAPE_OPEN']) + ''.join(row(d, 'v4-wide', f'{NX}/logs/v4-wide/uniswap-v4-wide-{d}.ndjson') for d in T['WIDE_OPEN']))
    W(TR + '/join/orient_0927.json', '{}\n')
    r = subprocess.run(['bash', TR + '/tools/make_pins.sh'], capture_output=True, text=True)
    if r.returncode: sys.exit(f'tree make_pins.sh failed: {r.stdout} {r.stderr}')
    print(f'tree {TR} (fake home {FH}); CUT {c["CUT"]}; {r.stdout.strip().splitlines()[-1]}')


def mark(ST, step, files):
    for f in files: assert os.path.isfile(f), f'{step}: {f} missing'
    W(f'{ST}/{step}.sha256', ''.join(f'{shaf(f)}  {f}\n' for f in files)); W(f'{ST}/{step}.done', '2026-10-07T00:00:00Z\n')


def state(case, upto, consist=None):
    case, TR, FH = paths(case); WK = TR + '/work'; ST, RL, V4J, TBL = WK + '/state', WK + '/runlogs', WK + '/v4join', WK + '/tables'
    order = ['days_verified', 'net', 'cuts', 'tables', 'join']; n = order.index(upto) + 1
    for d in (ST, RL, V4J + '/in/v4-wide', V4J + '/out', TBL, WK + '/ledgers/state', WK + '/tape/robinhood-tape', WK + '/tape/archive'): os.makedirs(d, exist_ok=True)
    blk = open(TR + '/pins/block_days.tsv', 'rb').read()
    if n >= 1:
        for kind, out, reg, days, extra in (('tape', 'tape_block', TR + '/pins/block_days.tsv', T['BLOCK'], ['--sha256', sha(blk)]), ('wide', 'wide_block', TR + '/pins/block_days.tsv', T['BLOCK'], ['--sha256', sha(blk)]),
                                            ('tape', 'tape_open', TR + '/pins/open_days.tsv', T['TAPE_OPEN'], []), ('wide', 'wide_open', TR + '/pins/open_days.tsv', T['WIDE_OPEN'], [])):
            r = subprocess.run(['python3', TR + '/tools/days.py', 'verify', kind, f'{ST}/{out}.json', reg] + extra + days, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
        mark(ST, 'days_verified', [f'{ST}/{x}.json' for x in ('tape_block', 'wide_block', 'tape_open', 'wide_open')])
    if n >= 2:
        W(V4J + '/anchors.tsv', f'14775000\t1780000000\n99999999\t{T["CUT"] + 9000}\n'); W(V4J + '/heldout.tsv', '15000000\t1780100000\n')
        W(V4J + '/ethusd_coingecko.json', '{"prices":[[1789776000000,2600.0]],"market_caps":[],"total_volumes":[]}')
        W(RL + '/ethusd.log', '{"points": 1, "ok": true, "fake": "TESTC"}\n'); W(RL + '/anchors.log', 'TESTC fake anchors\n')
        mark(ST, 'net', [V4J + '/anchors.tsv', V4J + '/heldout.tsv', V4J + '/ethusd_coingecko.json'])
    if n >= 3:
        cd = T['CUT_DAY']
        W(f'{WK}/tape/robinhood-tape/tape-{cd}.ndjson', f'{{"ts":{T["CUT"] - 5},"tok":"FAKE-CUT"}}\n'); W(f'{V4J}/in/v4-wide/uniswap-v4-wide-{cd}.ndjson', '{"blk":1,"fake":"wide cut"}\n')
        W(f'{V4J}/in/uniswap-v4-tape.ndjson', '{"blk":1,"fake":"lock cut"}\n')
        W(ST + '/cut_tape.json', json.dumps(dict(inputs=['FAKE'], read=1, kept=1, bytes=40, inversions=0, lateKept=0, sha256='a' * 64, stopped=True)) + '\n')
        W(ST + '/cut_wide.json', json.dumps({'in': 'FAKE', 'read': 1, 'kept': 1, 'bytes': 30, 'inversions': 0, 'maxLateBlocks': 0, 'lateKeptAfterCutRow': 0, 'sha256': 'b' * 64, 'stopped': True}) + '\n')
        W(ST + '/cut_lock.json', json.dumps({'in': 'FAKE', 'read': 1, 'kept': 1, 'bytes': 30, 'inversions': 0, 'maxLateBlocks': 0, 'lateKeptAfterCutRow': 0, 'sha256': 'c' * 64, 'stopped': True}) + '\n')
        W(ST + '/cut_rows.tsv', f'2026-10-07T00:00:00Z\t{cd}\tv2v3-tape-cutA\t{"a" * 64}\t40\tFAKE\n2026-10-07T00:00:00Z\t{cd}\tv4-wide-cutA\t{"b" * 64}\t30\tFAKE\n')
        mark(ST, 'cuts', [f'{WK}/tape/robinhood-tape/tape-{cd}.ndjson', f'{V4J}/in/v4-wide/uniswap-v4-wide-{cd}.ndjson', f'{V4J}/in/uniswap-v4-tape.ndjson'] + [f'{ST}/{x}' for x in ('cut_tape.json', 'cut_wide.json', 'cut_lock.json', 'cut_rows.tsv')])
    if n >= 4:
        for f in ('launchpads_e5c559ec.js', 'tokmeta.tsv', 'meta_full.tsv', 'meta.tsv', 'poolfee_full.tsv', 'poolfee.tsv', 'scam.tsv'): W(f'{TBL}/{f}', f'FAKE {f}\n')
        tj = dict(out_rows=1, old_table_is_byte_prefix=True, rebuild_differences=0, rebuild_difference_kinds={}, old_rows=1, old_rows_kept_verbatim=1, old_rows_dropped_by_cutoff=0)
        W(ST + '/table_meta.json', json.dumps(tj)); W(ST + '/table_poolfee.json', json.dumps(tj))
        led = ['robinhood-token-births.json', 'robinhood-token-minters.ndjson', 'robinhood-v4-births.ndjson', 'state/v4-poolkeys.json', 'state/uniswap-launches.json', 'state/hook-pad-map.json']
        for f in led: W(f'{WK}/ledgers/{f}', f'FAKE {f}\n')
        W(ST + '/ledgers.sha256', ''.join(f'{shaf(WK + "/ledgers/" + f)}  {f}\n' for f in led)); W(V4J + '/meta.json', '{"fake":"meta"}\n')
        mark(ST, 'tables', [f'{TBL}/{f}' for f in ('launchpads_e5c559ec.js', 'tokmeta.tsv', 'meta_full.tsv', 'meta.tsv', 'poolfee_full.tsv', 'poolfee.tsv', 'scam.tsv')]
             + [ST + '/table_meta.json', ST + '/table_poolfee.json', ST + '/ledgers.sha256'] + [f'{WK}/ledgers/{f}' for f in led] + [V4J + '/meta.json'])
    if n >= 5:
        for f in ('unknown_keys_0927.json', 'decimals.json', 'unknown_keys.json', 'pass1_stats.json', 'addr_quotes.json', 'addr_toks.json', 'finalize_stats.json'): W(f'{V4J}/{f}', '{"fake":"%s"}\n' % f)
        W(V4J + '/poolcounts.tsv', 'FAKEPOOL\t1\n')
        for d in T['CONSIST'] + T['BLOCK']: W(f'{V4J}/out/v4-swaps-{d}.ndjson.gz', gzip.compress(f'{{"fake":"exam join {d}"}}\n'.encode(), mtime=0))
        for k in ('unknown_split', 'unknown_merge', 'poolcounts', 'addr_lists'): W(f'{ST}/{k}.json', '{"fake":"%s"}\n' % k)
        OJ = FH + '/projects/patches/v4-join-2026-09-27/out'
        base = {T['CONSIST'][0]: dict(identical=2005120, differ=5878, differ_in_engine_fields=5878, fields=dict(price_eth=5878, price_usd=5878, usd=5060, depth5_eth=5878, depth1_eth=5878)),
                T['CONSIST'][1]: dict(identical=3119960, fields={})}
        for d in T['CONSIST']:
            c = dict(mine=f'{V4J}/out/v4-swaps-{d}.ndjson.gz', orig=f'{OJ}/v4-swaps-{d}.ndjson.gz', **base[d]); c.update((consist or {}).get(d, {}))
            W(f'{ST}/consist_{d}.json', json.dumps(c) + '\n')
        r = subprocess.run(['python3', TR + '/tools/exam_checks.py', 'seam'] + [f'{ST}/consist_{d}.json' for d in T['CONSIST']], capture_output=True, text=True)
        W(ST + '/seam_gate.json', r.stdout)                         # what the runner writes when the gate passes (a failing gate never reaches mark)
        outs = sorted(os.path.join(V4J, 'out', f) for f in os.listdir(V4J + '/out') if f.endswith('.ndjson.gz'))
        mark(ST, 'join', [f'{V4J}/{f}' for f in ('unknown_keys_0927.json', 'decimals.json', 'unknown_keys.json', 'pass1_stats.json', 'poolcounts.tsv', 'addr_quotes.json', 'addr_toks.json', 'finalize_stats.json')]
             + outs + [f'{ST}/{k}.json' for k in ('unknown_split', 'unknown_merge', 'poolcounts', 'addr_lists')] + [f'{ST}/consist_{d}.json' for d in T['CONSIST']] + [ST + '/seam_gate.json'])
    print(f'state written up to {upto}')


def post(case, wrong=False):
    case, TR, FH = paths(case); ST = TR + '/work/state'
    h = shaf(ST + '/manifest.sha256')
    if wrong: h = ('0' if h[0] != '0' else '1') + h[1:]
    W(ST + '/MANIFEST_POSTED', h + '\n'); print('posted', h)


def runrow(case, label, rel, engine_sha=None, tamper=False):
    case, TR, FH = paths(case); WK = TR + '/work'; E = f'{TR}/{rel}'
    content = f'{{"fake":"engine output {label}"}}\n'.encode()
    W(f'{WK}/out/{label}.ndjson.gz', gzip.compress(content, mtime=0))
    row = [label, engine_sha or shaf(E), E, '2026-10-07T05:00:00Z', '2026-10-07T05:10:00Z', 'exit=0', 'elapsed=1', 'user_s=1', 'maxrss_kb=1', 'opened=0',
           f'content_sha256={sha(content)}', f'guard={shaf(TR + "/tools/exam_guard.js")}', 'env=']
    with open(f'{WK}/runlogs/runs.tsv', 'a') as o: o.write('\t'.join(row) + '\n')
    if tamper: W(f'{WK}/out/{label}.ndjson.gz', gzip.compress(content + b'{"tampered":true}\n', mtime=0))
    print('run row', label, 'tampered' if tamper else '')


def cap(case, rel, extra=False, lower=False):
    case, TR, FH = paths(case); ST = TR + '/work/state'; f = f'{TR}/{rel}'
    os.makedirs(ST + '/cap_orig', exist_ok=True)
    orig = f'{ST}/cap_orig/{int(time.time() * 1000)}_{os.path.basename(f)}'; shutil.copy2(f, orig)
    s = open(f).read(); a = "if (rss > 3.2e9) throw new Error('RSS guard ' + rss);"
    assert s.count(a) == 1
    s = s.replace(a, a.replace('3.2e9', '2.0e9' if lower else '3.6e9'))
    if extra: s = s.replace("'use strict';", "'use strict'; // TESTC: a second, unregistered change", 1)
    open(f, 'w').write(s)
    with open(ST + '/CAP_CHANGE', 'a') as o: o.write('\t'.join(['2026-10-07T06:00:00Z', rel, shaf(orig), shaf(f), orig, 'TESTC: posted in a synthetic forum post']) + '\n')
    print('cap change', rel, 'extra' if extra else '', 'lower' if lower else '')


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'tree': tree(a[0], '--cut-future' in a)
    elif cmd == 'state': state(a[0], a[1], json.loads(a[a.index('--consist') + 1]) if '--consist' in a else None)
    elif cmd == 'post': post(a[0], '--wrong' in a)
    elif cmd == 'runrow': runrow(a[0], a[1], a[2], a[a.index('--engine-sha') + 1] if '--engine-sha' in a else None, '--tamper' in a)
    elif cmd == 'cap': cap(a[0], a[1], '--extra-line' in a, '--lower' in a)
    else: sys.exit(f'unknown command {cmd}')
