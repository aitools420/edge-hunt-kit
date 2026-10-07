#!/usr/bin/env python3
"""exam_checks.py — NEW CODE (sealed-exam-blockA, pond #330 B1, H1, H2 and L22): the runner's refusal checks, one subcommand each.
Each prints one JSON line and exits 0 (pass) or 2 (refuse); `capfail`, `statsrc`, `capresume` and `killed` use exit 1 as described.

  seam <consist_FIRST.json> [<consist_DAY.json> ...]
      B1. The 09-25/09-26 seam gate, run in step 6 BEFORE any engine (and again on every start). The FIRST file is the join's first
      day (the exam: 2026-09-25): its only allowed differences from the 09-27 join are the other-quote price fields SEAM_FIELDS, on
      at most SEAM_BOUND rows, with no row in one file only. Every LATER day (the exam: 2026-09-26) must be identical row for row:
      differ = 0, only_mine = 0, only_orig = 0. Both files of each comparison must be that day's file and share at least one row.
      The bound and the field list were fixed on open data before the read (REGISTER_DRAFT.md, tests/testB/seam_bound_evidence.json):
        - Test B's first joined day (09-20, the same position in its shifted calendar) differed on exactly 5,878 of 2,010,998 rows,
          in price_eth / price_usd / depth1_eth / depth5_eth (5,878 each) and usd (5,060); eth_usd on 0 rows;
        - an open-data replay of finalize.js's causal other-quote rule (cold start vs the 09-27 join's warm state) reproduces
          those 5,878 rows exactly and predicts 4,824 rows for the exam's first day, 09-25 (of 1,853,640);
        - eth_usd is NOT allowed: it comes from the CoinGecko series alone (finalize.js ethUsd), not from the warm-up, and the hourly
          points are on the hour and identical whatever the query start; it differed only on Test B's last day before ITS cut
          (clarification 10), an edge the exam never compares.
  codecheck <code.sha256> <ROOT> <CAP_CHANGE|-> <REFUSED|->
      H1 + L22. Every pinned code file against its pin. A file that differs passes ONLY through valid registered cap-change records
      (L22): the file is an exam engine (RSS guard) or tools/run_engine.sh (heap cap); each record's original copy hashes to the
      pin (or to the previous record's new hash); the new version differs from it in exactly ONE line, the cap line, whose number
      is larger and nothing else; the current file hashes to the last record's new hash; and no file has more cap changes than
      CAP refusals of that cap in REFUSED (a cap may be raised only after it fired).
      CAP_CHANGE: one tab-separated line per change: utc, path relative to ROOT, old sha256, new sha256, original copy (absolute
      path), where the new hash was posted (non-empty).
  capfail <engine.log> <engine.js> <ROOT>
      L22. Prints the cap that stopped an engine ("rss:engines/<engine>.js" for the engine's RSS guard, "heap:tools/run_engine.sh"
      for V8's heap limit) and exits 0; exits 1 if the log shows neither (any other failure ends the exam).
  capresume <REFUSED> <CAP_CHANGE|->
      L22. Exit 0 if every CAP refusal in REFUSED is matched by a cap-change record for that file (resume allowed), else 1.
  runs <runs.tsv|-> <code.sha256> <ROOT> <CAP_CHANGE|-> <outdir> [--require] <label> [<label> ...]
      H2. Every runs.tsv row of the labels: the engine's sha256 must be its pin (or a registered cap change of it). An output file
      must have exactly one exit=0 row whose content_sha256 equals the sha256 of its uncompressed content; an exit=0 row without
      its output refuses. A file left by a run that did not complete is never read: "partial" (no exit=0 row, the label's last row
      failed) or "unrecorded" (no runs.tsv row at all: the run died with its run_engine.sh); the runner moves it aside unread and
      re-runs. --require: every label must be done.
  killed <runs.tsv> <label> <rows_before> <engine.log> <rc>
      The engine-death rule (coordinator 2026-10-07, after pond #330): exit 0 (RESUMABLE) iff the engine run DIED WITHOUT COMPLETING,
      killed or stopped from outside: either run_engine.sh recorded it with exit 137 (SIGKILL, e.g. the kernel's OOM killer), 143
      (SIGTERM, e.g. a reboot or shutdown), 129 (SIGHUP) or 130 (SIGINT) AND the log holds GNU time's matching "Command terminated by
      signal N" (N = exit - 128); or the run left NO new runs.tsv row at all and run_engine.sh itself ended non-zero (it died too).
      Any other failure exits 1: END (an engine that exits non-zero by itself, even after writing a complete output; SIGABRT 134,
      unless it is V8's heap cap, which `capfail` reports first as CAP).
  statsrc <stats.json> <output.ndjson.gz>
      H2. Exit 0 if the stats file exists and its src_sha256 is the sha256 of exactly this output file (reuse), 1 if it does not
      exist (compute), 2 if it was computed from different bytes (refuse)."""
import sys, os, re, json, gzip, hashlib, collections

SEAM_FIELDS = ('price_eth', 'price_usd', 'usd', 'depth1_eth', 'depth5_eth')
SEAM_BOUND = 5878
CAP_FILES = [(re.compile(r'^engines/engine_(st|grid)_exam(_h)?\.js$'), 'rss'), (re.compile(r'^tools/run_engine\.sh$'), 'heap')]
CAP_LINE = {'rss': (re.compile(r"if \(rss > ([0-9][0-9.e+]*)\) throw new Error\('RSS guard ' \+ rss\);"), "throw new Error('RSS guard '"),
            'heap': (re.compile(r'--max-old-space-size=([0-9]+)'), 'node -r "$G" --max-old-space-size=')}
HEX64 = re.compile(r'^[0-9a-f]{64}$')
DEATH_EXITS = {'137': 'SIGKILL', '143': 'SIGTERM', '129': 'SIGHUP', '130': 'SIGINT'}   # killed or stopped from outside (a reboot sends SIGTERM)


def out(ok, **kw):
    print(json.dumps(dict(ok=ok, **kw), default=str))
    sys.exit(0 if ok else 2)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def sha_gz_content(p):
    h = hashlib.sha256()
    with gzip.open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def seam(files):
    rows, bad = [], []
    for i, p in enumerate(files):
        m = re.search(r'consist_(\d{4}-\d\d-\d\d)\.json$', p)
        if not m: bad.append(f'{p}: not a consist_<day>.json file'); continue
        d = m.group(1)
        try:
            c = json.load(open(p))
        except Exception as e:
            bad.append(f'{d}: unreadable ({type(e).__name__})'); continue
        for k in ('mine', 'orig'):
            if os.path.basename(str(c.get(k, ''))) != f'v4-swaps-{d}.ndjson.gz': bad.append(f'{d}: the {k} file is {c.get(k)!r}, not that day\'s file')
        n = {k: int(c.get(k) or 0) for k in ('identical', 'differ', 'only_mine', 'only_orig')}
        fields = {k: int(v) for k, v in (c.get('fields') or {}).items()}
        rule = 'b' if i == 0 else 'a'
        if n['identical'] <= 0: bad.append(f'{d}: no identical row (an empty comparison proves nothing)')
        if n['only_mine'] or n['only_orig']: bad.append(f"{d}: rows in one join only (exam {n['only_mine']}, 09-27 {n['only_orig']}); must be 0")
        if (n['differ'] == 0) != (not fields) or any(v > n['differ'] for v in fields.values()):
            bad.append(f"{d}: inconsistent comparison (differ {n['differ']}, fields {fields})")
        if rule == 'b':
            extra = sorted(set(fields) - set(SEAM_FIELDS))
            if extra: bad.append(f"{d} (first joined day): differences outside the other-quote price fields: {({k: fields[k] for k in extra})}")
            if n['differ'] > SEAM_BOUND: bad.append(f"{d} (first joined day): {n['differ']} rows differ, above the registered bound {SEAM_BOUND}")
        elif n['differ']:
            bad.append(f"{d}: {n['differ']} rows differ from the 09-27 join (must be 0): fields {fields}")
        rows.append(dict(day=d, rule=rule, **n, fields=fields))
    if not files: bad.append('no consistency file given')
    out(not bad, check='seam', bound=SEAM_BOUND, allowed_fields_first_day=list(SEAM_FIELDS), days=rows, why=bad)


def load_pins(p):
    P = []
    for ln in open(p):
        if not ln.strip(): continue
        h, f = ln.rstrip('\n').split('  ', 1)
        P.append((h, f))
    return P


def load_caps(capf):
    if capf in ('-', '') or not os.path.exists(capf): return [], []
    R, bad = [], []
    for k, ln in enumerate(open(capf), 1):
        if not ln.strip(): continue
        a = ln.rstrip('\n').split('\t')
        if len(a) != 6 or not HEX64.match(a[2]) or not HEX64.match(a[3]) or not a[5].strip() or not os.path.isabs(a[4]):
            bad.append(f'CAP_CHANGE line {k} is malformed (want: utc, relpath, old sha256, new sha256, original copy path, where posted)'); continue
        R.append(dict(utc=a[0], rel=a[1], old=a[2], new=a[3], orig=a[4], posted=a[5]))
    return R, bad


def cap_refusals(refused):
    C = collections.Counter()
    if refused in ('-', '') or not os.path.exists(refused): return C
    for ln in open(refused):
        if ln.startswith('REFUSED CAP '):
            m = re.search(r'\[cap=(rss|heap):([^\]]+)\]', ln)
            if m: C[m.group(2)] += 1
    return C


def cap_kind(rel):
    for rx, k in CAP_FILES:
        if rx.match(rel): return k
    return None


def cap_diff(a_text, b_text, kind):
    """None if b differs from a ONLY by a larger number on the one cap line, else the reason."""
    A, B = a_text.split('\n'), b_text.split('\n')
    if len(A) != len(B): return 'line count changed'
    diff = [i for i in range(len(A)) if A[i] != B[i]]
    if len(diff) != 1: return f'{len(diff)} lines changed (exactly one, the cap line, may change)'
    i = diff[0]; rx, anchor = CAP_LINE[kind]
    if anchor not in A[i]: return f'line {i + 1} is not the {kind} cap line'
    ms = list(rx.finditer(A[i]))
    if len(ms) != 1: return f'line {i + 1}: the cap pattern occurs {len(ms)} times'
    m = ms[0]
    mb = re.match(re.escape(A[i][:m.start(1)]) + r'([0-9][0-9.e+]*)' + re.escape(A[i][m.end(1):]) + r'$', B[i])
    if not mb: return f'line {i + 1}: more than the cap number changed'
    try:
        x, y = float(m.group(1)), float(mb.group(1))
    except ValueError:
        return 'cap number unreadable'
    if not y > x: return f'the cap was not raised ({m.group(1)} -> {mb.group(1)})'
    return None


def codecheck(pinf, root, capf, refused):
    P = load_pins(pinf); R, bad = load_caps(capf); fired = cap_refusals(refused)
    accepted = []
    by_rel = collections.defaultdict(list)
    for r in R: by_rel[r['rel']].append(r)
    pinned_rel = {os.path.relpath(f, root): (h, f) for h, f in P}
    for rel, recs in by_rel.items():
        if rel not in pinned_rel: bad.append(f'cap change for {rel}: not a pinned code file'); continue
        if not cap_kind(rel): bad.append(f'cap change for {rel}: this file has no registered cap (L22 allows only the engines\' RSS guard and run_engine.sh\'s heap cap)')
        if len(recs) > fired.get(rel, 0): bad.append(f'{len(recs)} cap change(s) for {rel} but that cap fired {fired.get(rel, 0)} time(s): a cap may be raised only after it fired (L22)')
    for h, f in P:
        if not os.path.exists(f): bad.append(f'{f}: missing'); continue
        cur = sha_file(f)
        if cur == h: continue
        rel = os.path.relpath(f, root); recs = by_rel.get(rel)
        if not recs: bad.append(f'{f}: FAILED (code hash mismatch)'); continue
        kind = cap_kind(rel)
        if not kind: continue                                   # already refused above
        expect_old, why = h, None
        for k, r in enumerate(recs):
            if r['old'] != expect_old: why = f'record {k + 1}: old sha256 is not the pin / the previous record\'s new sha256'; break
            if not os.path.exists(r['orig']) or sha_file(r['orig']) != r['old']: why = f'record {k + 1}: the original copy {r["orig"]} is missing or does not hash to {r["old"]}'; break
            nxt = recs[k + 1]['orig'] if k + 1 < len(recs) else f
            if sha_file(nxt) != r['new']: why = f'record {k + 1}: the new version does not hash to the recorded {r["new"]}'; break
            d = cap_diff(open(r['orig']).read(), open(nxt).read(), kind)
            if d: why = f'record {k + 1}: not a registered cap change: {d}'; break
            expect_old = r['new']
        if why is None and cur != recs[-1]['new']: why = 'the current file is not the last recorded version'
        if why: bad.append(f'{f}: FAILED ({why})')
        else: accepted.append(dict(file=rel, kind=kind, changes=len(recs), now=cur, posted=[r['posted'] for r in recs]))
    out(not bad, check='codecheck', files=len(P), cap_changes_accepted=accepted, why=bad[:8])


def capfail(logp, engine, root):
    s = open(logp, errors='replace').read() if os.path.exists(logp) else ''
    rel = os.path.relpath(os.path.realpath(engine), os.path.realpath(root))
    if 'RSS guard ' in s and cap_kind(rel) == 'rss': print(f'rss:{rel}'); sys.exit(0)
    if 'Reached heap limit' in s or 'JavaScript heap out of memory' in s: print('heap:tools/run_engine.sh'); sys.exit(0)
    sys.exit(1)


def capresume(refused, capf):
    fired = cap_refusals(refused); R, bad = load_caps(capf)
    n = collections.Counter(r['rel'] for r in R)
    short = {rel: dict(fired=k, raised=n.get(rel, 0)) for rel, k in fired.items() if n.get(rel, 0) < k}
    print(json.dumps(dict(ok=not short and not bad, check='capresume', fired=dict(fired), raised=dict(n), waiting=short, why=bad)))
    sys.exit(0 if not short and not bad else 1)


def runs(args):
    runsf, pinf, root, capf, outdir = args[:5]; rest = args[5:]
    require = '--require' in rest; labels = [x for x in rest if x != '--require']
    pins = {f: h for h, f in load_pins(pinf)}; R, badc = load_caps(capf)
    allowed = collections.defaultdict(set)
    for f, h in pins.items(): allowed[f].add(h)
    for r in R:
        f = os.path.join(root, r['rel']); allowed[f].add(r['old']); allowed[f].add(r['new'])
    rows = collections.defaultdict(list)
    if runsf != '-' and os.path.exists(runsf):
        for ln in open(runsf):
            a = ln.rstrip('\n').split('\t')
            if len(a) < 6: continue
            kv = dict(x.split('=', 1) for x in a[5:] if '=' in x)
            rows[a[0]].append(dict(engine_sha=a[1], engine=a[2], **kv))
    bad, status = list(badc), {}
    for L in labels:
        for r in rows.get(L, []):
            if r['engine'] not in pins: bad.append(f'{L}: engine {r["engine"]} is not a pinned file')
            elif r['engine_sha'] not in allowed[r['engine']]: bad.append(f'{L}: engine sha256 {r["engine_sha"]} in runs.tsv differs from its pin {pins[r["engine"]]}')
            if r.get('content_sha256') not in (None, '-') and not HEX64.match(r['content_sha256']): bad.append(f'{L}: runs.tsv content_sha256 is not 64-hex')
        ok_rows = [r for r in rows.get(L, []) if r.get('exit') == '0']
        f = os.path.join(outdir, f'{L}.ndjson.gz')
        if os.path.exists(f):
            if len(ok_rows) == 1:
                c = sha_gz_content(f)
                if c != ok_rows[0].get('content_sha256'): bad.append(f'{L}: output content sha256 {c} differs from runs.tsv {ok_rows[0].get("content_sha256")}')
                else: status[L] = 'done'
            elif len(ok_rows) > 1: bad.append(f'{L}: {len(ok_rows)} successful runs in runs.tsv (a finished run is never repeated)')
            elif rows.get(L) and rows[L][-1].get('exit') != '0': status[L] = 'partial'
            else: status[L] = 'unrecorded'
        else:
            if ok_rows: bad.append(f'{L}: runs.tsv records a successful run but its output is missing')
            else: status[L] = 'absent'
        if require and status.get(L) != 'done': bad.append(f'{L}: not done ({status.get(L, "refused")})')
    out(not bad, check='runs', status=status, why=bad[:8])


def killed(runsf, label, n0, logp, rc):
    rows = [ln.rstrip('\n').split('\t') for ln in (open(runsf) if os.path.exists(runsf) else [])]
    mine = [a for a in rows if a and a[0] == label]
    log = open(logp, errors='replace').read() if os.path.exists(logp) else ''
    new = mine[int(n0):]
    if not new:
        ok, why = int(rc) != 0, f'no runs.tsv row was written for this attempt (run_engine.sh ended with {rc}): the run died with it'
    else:
        ex = dict(x.split('=', 1) for x in new[-1][5:] if '=' in x).get('exit')
        n = int(ex) - 128 if ex and ex.isdigit() else None
        sig = n is not None and f'Command terminated by signal {n}\n' in log + '\n'
        ok, why = ex in DEATH_EXITS and sig, f'runs.tsv exit={ex}; "Command terminated by signal {n}" in the log: {sig}'
    print(json.dumps(dict(check='killed', label=label, died_without_completing=ok, why=why)))
    sys.exit(0 if ok else 1)


def statsrc(sp, op):
    if not os.path.exists(sp): print(json.dumps(dict(check='statsrc', stats=sp, exists=False))); sys.exit(1)
    try:
        s = json.load(open(sp)).get('src_sha256')
    except Exception:
        s = None
    h = sha_file(op) if os.path.exists(op) else None
    ok = s is not None and s == h
    print(json.dumps(dict(check='statsrc', stats=sp, src_sha256=s, output_sha256=h, ok=ok)))
    sys.exit(0 if ok else 2)


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'seam': seam(a)
    elif cmd == 'codecheck': codecheck(*a[:4])
    elif cmd == 'capfail': capfail(*a[:3])
    elif cmd == 'capresume': capresume(*a[:2])
    elif cmd == 'runs': runs(a)
    elif cmd == 'statsrc': statsrc(*a[:2])
    elif cmd == 'killed': killed(*a[:5])
    else: print(f'unknown command {cmd}'); sys.exit(2)
