#!/usr/bin/env python3
"""make_join.py — the exam copies of the v4-join-2026-09-27 tools the 09-27 runs used (sealed-exam-blockA).
Every copy = the original with listed, exact replacements (each anchor asserted to match exactly once); a unified diff of each
copy against its original is written next to it (<name>.diff). What changes:
  * PATHS: every tool reads and writes the exam work folder WORK/v4join instead of its own folder; meta.js reads the ledger and state
    files from the runner's hashed snapshot (work/ledgers); pass1 / unknown_pools read their
    raw inputs from WORK/v4join/in (links to the hash-checked V4-wide day files and the hole/backfill tapes, plus the runner's CUT
    copies of the locked tape and of the 10-07 wide file).
  * pass1: the block's CUT (1791331200) and the join's first day (JOIN0 2026-09-25: one warm-up day for finalize's causal
    other-quote prices before the 09-26 consistency day and the block days) as constants, with a two-line RANGE FILTER (a row at or
    after CUT is counted and dropped — there must be none, the runner checks; a row before JOIN0 is dropped unsharded).
  * finalize: SEAL = CUT, so every exam day goes to WORK/v4join/out (no day of the exam data is at or after the seal).
  * resolve_unknown: the official RPC now caps eth_getLogs (100,000 blocks with several topic values, 10,000,000 with one; measured
    2026-10-05), so the same Initialize-log query is paged — one pool id per request, 10,000,000-block windows walking back from the
    pool's last swap — with the original's parsing and output (tests/testB2: the answers equal the 09-27 keys).
Nothing else changes: the same anchors interpolation, pool table, decimals, ETH/USD and causal other-quote pricing, dedupe by
(blk, li) with the locked-tape row kept (as on 09-27, R-0114 included)."""
import os, sys, difflib
SRC = '/home/green/projects/patches/v4-join-2026-09-27'
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = '/home/green/projects/patches/sealed-exam-blockA/work/v4join'
TAG = '// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file'
P = {
 'meta.js': [
   ("const HERE = __dirname;", f"const HERE = '{WORK}';"),
   ("const NOX = '/home/green/noxabot/state';", "const NOX = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers/state';   // the runner's hashed snapshot"),
   ("const BIRTHS = '/home/green/.openclaw/workspace/wick-engine/logs/robinhood-v4-births.ndjson';", "const BIRTHS = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers/robinhood-v4-births.ndjson';   // the runner's hashed snapshot")],
 'unknown_pools.js': [
   ("const M = JSON.parse(fs.readFileSync(path.join(__dirname, 'meta.json'), 'utf8'));", f"const M = JSON.parse(fs.readFileSync(path.join('{WORK}', 'meta.json'), 'utf8'));"),
   ("const WD = '/home/green/noxabot/logs/v4-wide';", f"const WD = '{WORK}/in/v4-wide';"),
   ("  fs.writeFileSync(path.join(__dirname, 'unknown_pools.json'), JSON.stringify(U));", f"  fs.writeFileSync(path.join('{WORK}', 'unknown_pools.json'), JSON.stringify(U));")],
 'resolve_unknown.py': [
   ("HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = '{WORK}'"),
   # the official RPC now refuses eth_getLogs over > 100,000 blocks with several values in a topic position, and over > 10,000,000
   # blocks with one value (both measured 2026-10-05); the 09-27 full-range batch query fails today. The SAME query is paged: one
   # pool id per request, windows of 10,000,000 blocks walking back from the pool's last swap; parsing and output are the original's.
   ('''for i in range(0, len(ids), 50):
    chunk = ids[i:i + 50]
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getLogs', 'params': [{'address': PM, 'fromBlock': '0x0', 'toBlock': hex(max(U[k]['last'] for k in chunk)), 'topics': [INIT, chunk]}]})
    for attempt in range(6):
        r = subprocess.run(['curl', '-4', '-s', '-m', '120', '-H', 'Content-Type: application/json', '-d', body, RPC], capture_output=True, text=True).stdout
        try:
            j = json.loads(r)
            if 'result' in j: break
        except Exception: pass
        time.sleep(15 + 15 * attempt)
    else:
        print('FAILED chunk', i); continue
    for l in j['result']:''',
    '''SPAN = 10_000_000   # sealed-exam-blockA: the RPC's getLogs span with ONE value per topic position (measured 2026-10-05)
def getlogs(fb, tb, pid):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getLogs', 'params': [{'address': PM, 'fromBlock': hex(fb), 'toBlock': hex(tb), 'topics': [INIT, pid]}]})
    for attempt in range(6):
        r = subprocess.run(['curl', '-4', '-s', '-m', '120', '-H', 'Content-Type: application/json', '-d', body, RPC], capture_output=True, text=True).stdout
        try:
            j = json.loads(r)
            if 'result' in j: return j['result']
        except Exception: pass
        time.sleep(15 + 15 * attempt)
    return None
for i, pid in enumerate(ids):
    hi, res = U[pid]['last'], []
    while hi >= 0 and not res:
        lo = max(0, hi - SPAN + 1); res = getlogs(lo, hi, pid); hi = lo - 1
        if res is None: break
        time.sleep(0.2)
    if res is None:
        print('FAILED chunk', i); continue
    j = {'result': res}
    for l in j['result']:'''),
   ("    print(i, len(out), flush=True)\n    time.sleep(3)\n", "    if i % 50 == 0: print(i, len(out), flush=True)\n")],
 'anchors.py': [
   ("HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = '{WORK}'")],
 'decimals.js': [
   ("const OUT = path.join(__dirname, 'decimals.json');", f"const OUT = path.join('{WORK}', 'decimals.json');")],
 'pools.js': [
   ("function load(dir = __dirname) {", f"function load(dir = '{WORK}') {{"),
   # ORIENTATION PIN (pond #322 §6 e; found by Test B 2026-10-06: 45 of the 663,994 pools both tables know flipped token/quote, because
   # the rule counts currencies over the WHOLE, larger table): every pool the 09-27 table oriented by RULE or by its Initialize log keeps
   # the 09-27 orientation (join/orient_0927.json, made by join/make_orient.js with the 09-27 pools.js, read-only). New pools: unchanged rule.
   ("  const P = new Map();\n",
    "  const P = new Map();\n  const PIN = JSON.parse(fs.readFileSync('/home/green/projects/patches/sealed-exam-blockA/join/orient_0927.json', 'utf8'));   // sealed-exam-blockA: 09-27 orientation pin\n  const pinned = (id, c0, c1) => (PIN[id] === c0 || PIN[id] === c1) ? [PIN[id], PIN[id] === c0 ? c1 : c0] : null;\n"),
   ("    if (tok0 && (tok0 === c0 || tok0 === c1)) { tok = tok0; quote = tok0 === c0 ? c1 : c0; }",
    "    const pn = pinned(id, c0, c1);\n    if (pn) { [tok, quote] = pn; how = 'pin0927'; }\n    else if (tok0 && (tok0 === c0 || tok0 === c1)) { tok = tok0; quote = tok0 === c0 ? c1 : c0; }"),
   ("    const [c0, c1, fee, tsp, hook, blk] = k; const [tok, quote] = pick(c0, c1);",
    "    const [c0, c1, fee, tsp, hook, blk] = k; const [tok, quote] = pinned(id, c0, c1) || pick(c0, c1);")],
 'pass1.js': [
   ("const HERE = __dirname, SH = process.argv[2];", f"const HERE = '{WORK}', SH = process.argv[2];\nconst CUT = 1791331200, JOIN0 = '2026-09-25';   // sealed-exam-blockA: the block's CUT and the join's first day"),
   ("  const st = stats[src + ':' + path.basename(file)] = { lines: 0, swaps: 0, nopool: 0, bad: 0 };",
    "  const st = stats[src + ':' + path.basename(file)] = { lines: 0, swaps: 0, nopool: 0, bad: 0, afterCut: 0, beforeJoin0: 0 };"),
   ("    const ts = blkTs(r.blk), day = new Date(ts * 1000).toISOString().slice(0, 10);\n",
    "    const ts = blkTs(r.blk), day = new Date(ts * 1000).toISOString().slice(0, 10);\n"
    "    if (ts >= CUT) { st.afterCut++; continue; } if (day < JOIN0) { st.beforeJoin0++; continue; }   // sealed-exam-blockA range filter\n"),
   ("  const L = '/home/green/noxabot/logs';", f"  const L = '{WORK}/in';")],
 'finalize.js': [
   ("const HERE = __dirname, SH = process.argv[2], OUT = path.join(HERE, 'out'), SEALED_DIR = path.join(OUT, 'sealed');",
    f"const HERE = '{WORK}', SH = process.argv[2], OUT = path.join(HERE, 'out'), SEALED_DIR = path.join(OUT, 'sealed');"),
   ("const SEAL = 1790467200;                                 // 2026-09-27T00:00:00Z — SEALED-HOLDOUT/README.md",
    "const SEAL = 1791331200;                                 // sealed-exam-blockA: the Block A exam's CUT 2026-10-07T00:00:00Z — nothing at or after it exists here")],
}
for name, pairs in P.items():
    s0 = open(os.path.join(SRC, name)).read(); s = s0
    for a, b in pairs:
        n = s.count(a); assert n == 1, f'{name}: anchor found {n} times: {a[:80]!r}'
        s = s.replace(a, b)
    lines = s.split('\n')
    if name.endswith('.js'):
        k = 1 if lines[0].startswith('#!') else 0
        lines.insert(k, TAG)
    else:
        k = 1 if lines[0].startswith('#!') else 0
        lines.insert(k, TAG.replace('//', '#', 1))
    s = '\n'.join(lines)
    out = os.path.join(HERE, name)
    open(out, 'w').write(s)
    d = ''.join(difflib.unified_diff(s0.splitlines(True), s.splitlines(True), f'v4-join-2026-09-27/{name}', f'sealed-exam-blockA/join/{name}'))
    open(out + '.diff', 'w').write(d)
    print(f'{name}: {len(pairs)} replacements, diff {sum(1 for l in d.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))} lines')
