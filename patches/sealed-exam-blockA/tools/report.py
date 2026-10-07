#!/usr/bin/env python3
"""report.py <work> <report.md> <cut_unix> "<seeds>" <run_exam.sh> — NEW CODE (sealed-exam-blockA): the exam report, from the runner's
outputs only. Line 1 = each rule's verdict, its registered READING and whether it qualifies. The next lines = the sha256 of the runner,
of the three pin files and of the posted manifest (pond #330 H1). Then the hashes recorded at run time, the bar conditions, the money test
(reported, not the bar), n / coins, drop-5, the data gate, the sensitivity, every input sha256, the engine runs, the steps, and every
refusal / deviation on this work folder.

A FAILURE ANYWHERE IS A REFUSAL (pond #330 H1): the whole report is built in memory first; any error exits 2 and writes NOTHING (no
report.md, no report.json, no verdict printed). Every stats file must have been computed from exactly the output file runs.tsv records.

THE VERDICT (registered): a rule PASSES iff ALL of: Holm k = 2 passes its one-sided p (SE_cons; the smaller of the two rules' p must be
< 0.0125, and only then the larger < 0.025); d > 0 and its CI lower bound > 0; n >= 300 paired trades on >= 60 coins; drop-5 d > 0;
DATA GATE G1-G5, G9, G10 PASS. A gate failure reads CAN'T TELL (data); anything else that misses reads NOT SHOWN.
HOLM AND THE DATA GATE (pond #330 M6, Chef 2026-10-07): a rule whose data gate fails enters Holm with p = 1, so the other rule must
clear 0.0125 (alpha / 2, alpha = 2.5 %) on its own.
CAN'T TELL (data) IS FINAL for Block A (pond #330 L4, Chef 2026-10-07): no re-run, no re-draw; that rule waits for Block B. Its
statistics (primary and all 20 alone seeds) are NEVER printed: they go only to work/withheld_stats.json, whose sha256 report.md prints
(pond #330 H2). An alone seed whose own gate fails has its numbers withheld the same way.
AGREEMENT AND QUALIFYING (pond #330 M5, Chef 2026-10-07): the sensitivity AGREES with the primary iff at least 10 of the 20 alone seeds
reach the primary's verdict (each alone verdict: the same bar, Holm across the two rules' alone runs of that seed). A PASS QUALIFIES
(the real-money gate, any public claim) iff the primary PASSES and at least 10 of the 20 alone seeds PASS. The exam cell alone at SEED
20260927 is printed as information only. READING labels (registered, clarification 1): PASS (qualifies) · PASS, draw-dependent ·
NOT SHOWN · NOT SHOWN, draw-dependent (>= 10 of 20 alone seeds PASS) · CAN'T TELL (data)."""
import sys, json, os, glob, hashlib, statistics, datetime, re, gzip
W, OUTMD, CUT, SEEDS, RUNNER = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split(), sys.argv[5]
ROOT = os.path.dirname(os.path.abspath(OUTMD))
ST, STATS, RL, V4J, TBL, OUTD = (os.path.join(W, x) for x in ('state', 'stats', 'runlogs', 'v4join', 'tables', 'out'))
CT = "CAN'T TELL (data)"
J = lambda p: json.load(open(p))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    runs, run_rows = {}, []
    for ln in open(os.path.join(RL, 'runs.tsv')):
        a = ln.rstrip('\n').split('\t'); kv = dict(x.split('=', 1) for x in a[5:] if '=' in x)
        r = dict(label=a[0], engine_sha=a[1], engine=a[2], start=a[3], end=a[4], **kv); run_rows.append(r)
        if kv.get('exit') == '0': runs[a[0]] = r
    G3 = open(os.path.join(ST, 'G3.rc')).read().strip() == '0'

    def g2(meta):
        if not meta: return False, ['no _meta']
        why = []
        for k in ('holes', 'mergedOutOfOrder', 'v4OutOfOrder'):
            if meta.get(k): why.append(f'{k} {meta[k]}')
        if (meta.get('reorder') or {}).get('lateRows'): why.append(f"lateRows {meta['reorder']['lateRows']}")
        for d, v in (meta.get('v23Files') or {}).items():
            if not v['n']: why.append(f'V2/V3 {d} empty')
        for d, v in (meta.get('v4Files') or {}).items():
            if not v['n'] and d < iso(CUT)[:10]: why.append(f'V4 {d} empty')
        e = meta.get('endTs') or 0
        if not (CUT - 3600 <= e < CUT): why.append(f'data end {e} not in the last hour before the cut')
        return not why, why

    def g9(label):
        """every file the run opened is either a table, a work-folder file of a day < the cut day + 1, or a real file of a day < the cut day"""
        cutday = iso(CUT)[:10]; bad = []
        p = os.path.join(RL, f'{label}.opened')
        if not os.path.exists(p): return False, ['no opened-file list']
        for ln in open(p):
            for q in ln.strip().split(' -> '):
                days = re.findall(r'\d{4}-\d{2}-\d{2}', os.path.basename(q))
                if '/sealed/' in q: bad.append(q)
                elif any(d > cutday for d in days): bad.append(q)
                elif any(d == cutday for d in days) and not q.startswith(W): bad.append(q)
        r = runs.get(label, {})
        if r.get('exit') != '0': bad.append(f"exit {r.get('exit')}")
        return not bad, bad[:5]

    def gates(st, label):
        g = dict(st['gate']['status']); ok2, w2 = g2(st.get('meta')); ok9, w9 = g9(label)
        g['G2'] = 'PASS' if ok2 else 'FAIL'; g['G3'] = 'PASS' if G3 else 'FAIL'; g['G9'] = 'PASS' if ok9 else 'FAIL'
        return {k: g[k] for k in ('G1', 'G2', 'G3', 'G4', 'G5', 'G9', 'G10')}, dict(G2=w2, G9=w9)

    def load_stats(label):
        s = J(os.path.join(STATS, label + '.json'))
        f = os.path.join(OUTD, label + '.ndjson.gz')
        if label not in runs: raise RuntimeError(f'{label}: no successful run in runs.tsv')
        if s.get('src_sha256') != sha(f): raise RuntimeError(f'{label}: stats src_sha256 {s.get("src_sha256")} is not the sha256 of {f}')
        with gzip.open(f, 'rb') as g:
            h = hashlib.sha256()
            for b in iter(lambda: g.read(1 << 20), b''): h.update(b)
        if h.hexdigest() != runs[label].get('content_sha256'): raise RuntimeError(f'{label}: output content differs from runs.tsv')
        return s

    def bar_parts(st, label):
        b = st['bar']; ci = b.get('ci95') or [None, None]
        gs, gw = gates(st, label)
        return dict(d=b.get('d_mean'), ci=ci, p=b.get('p_one_sided'), n=b.get('n'), coins=b.get('coins'), drop5=b.get('drop5'), se_cons=b.get('se_cons'),
                    d_pos=(b.get('d_mean') or 0) > 0, ci_pos=ci[0] is not None and ci[0] > 0, n_ok=(b.get('n') or 0) >= 300, coins_ok=(b.get('coins') or 0) >= 60,
                    drop5_pos=b.get('drop5') is not None and b['drop5'] > 0, gates=gs, gate_why=gw, gates_ok=all(v == 'PASS' for v in gs.values()))

    def holm(b1, b2):
        """Holm k = 2; a rule whose data gate fails enters with p = 1 (M6), a missing p counts as 1."""
        pv = lambda b: 1.0 if (not b['gates_ok'] or b['p'] is None) else b['p']
        ps = sorted([(pv(b1), '1'), (pv(b2), '2')])
        out = {}; first_ok = ps[0][0] < 0.0125
        out[ps[0][1]] = dict(p_holm=ps[0][0], threshold=0.0125, step=1, ok=first_ok)
        out[ps[1][1]] = dict(p_holm=ps[1][0], threshold=0.025, step=2, ok=first_ok and ps[1][0] < 0.025)
        return out

    def verdict(bp, h):
        if not bp['gates_ok']: return CT
        ok = h['ok'] and bp['d_pos'] and bp['ci_pos'] and bp['n_ok'] and bp['coins_ok'] and bp['drop5_pos']
        return 'PASS' if ok else 'NOT SHOWN'

    def evaluate(l1, l2):
        s1, s2 = load_stats(l1), load_stats(l2)
        b1, b2 = bar_parts(s1, l1), bar_parts(s2, l2); H = holm(b1, b2)
        return dict(s={'1': s1, '2': s2}, b={'1': b1, '2': b2}, holm=H, v={'1': verdict(b1, H['1']), '2': verdict(b2, H['2'])})

    P = evaluate('primary_rule1', 'primary_rule2')
    SE = {s: evaluate(f'alone_rule1_s{s}', f'alone_rule2_s{s}') for s in SEEDS}
    A0 = SE[SEEDS[0]]
    R = ('1', '2'); CELL = {'1': 'C2P', '2': 'D25L48'}
    WH = {r: P['v'][r] == CT for r in R}                                 # rule withheld: its primary data gate failed
    WHS = {(s, r): WH[r] or SE[s]['v'][r] == CT for s in SEEDS for r in R}  # (seed, rule) numbers withheld
    withheld = dict(note='statistics withheld from report.md (pond #330 H2): a data-gate failure never prints d / CI / p / n',
                    primary={r: dict(verdict=P['v'][r], bar=P['b'][r], holm=P['holm'][r], money_test=P['s'][r].get('money_test'), reported=P['s'][r].get('reported'))
                             for r in R if WH[r]},
                    alone={f'{s}|{r}': dict(verdict=SE[s]['v'][r], bar=SE[s]['b'][r], holm=SE[s]['holm'][r]) for s in SEEDS for r in R if WHS[(s, r)]})
    wtxt = json.dumps(withheld, indent=1, default=str)
    wsha = hashlib.sha256(wtxt.encode()).hexdigest()

    agree, sens, reading, qual = {}, {}, {}, {}
    for r in R:
        vs = [SE[s]['v'][r] for s in SEEDS]; npass = vs.count('PASS'); half = npass * 2 >= len(vs)
        agree[r] = dict(majority_same=vs.count(P['v'][r]) * 2 >= len(vs), n_same=vs.count(P['v'][r]), n_pass=npass, n_seeds=len(vs),
                        alone_seed0=A0['v'][r], alone_seed0_note='information only (pond #330 M5): not part of AGREE or of qualifying')
        agree[r]['agree'] = agree[r]['majority_same']
        if P['v'][r] == 'PASS': reading[r], qual[r] = ('PASS' if half else 'PASS, draw-dependent'), half
        elif P['v'][r] == 'NOT SHOWN': reading[r], qual[r] = ('NOT SHOWN, draw-dependent' if half else 'NOT SHOWN'), False
        else: reading[r], qual[r] = CT, False
        ok_seeds = [s for s in SEEDS if not WHS[(s, r)]]
        ds = [SE[s]['b'][r]['d'] for s in ok_seeds if SE[s]['b'][r]['d'] is not None]
        sh = lambda f: (sum(1 for s in ok_seeds if f(SE[s]['b'][r])) / len(ok_seeds)) if ok_seeds else None
        sens[r] = dict(seeds_with_numbers=len(ok_seeds), median_d=statistics.median(ds) if ds else None, d_min=min(ds) if ds else None, d_max=max(ds) if ds else None,
                       share_PASS=npass / len(vs), share_ci_pos=sh(lambda b: b['ci_pos']),
                       share_p_lt_0125=sh(lambda b: b['p'] is not None and b['p'] < 0.0125), share_p_lt_025=sh(lambda b: b['p'] is not None and b['p'] < 0.025),
                       share_drop5_pos=sh(lambda b: b['drop5_pos']), verdicts={s: SE[s]['v'][r] for s in SEEDS})
    pct = lambda x: '—' if x is None else f'{x:.0%}'
    L = []

    def first(r):
        if WH[r]: return f"rule #{r} ({CELL[r]}): {CT} — final for Block A: no re-run, no re-draw; this rule waits for Block B (statistics withheld)"
        return (f"rule #{r} ({CELL[r]}): {P['v'][r]} — primary and sensitivity {'AGREE' if agree[r]['agree'] else 'DISAGREE'} "
                f"({agree[r]['n_pass']} of {len(SEEDS)} alone seeds PASS) → READING: {reading[r]}; qualifies: {'true' if qual[r] else 'false'}")
    L.append('VERDICT · ' + ' · '.join(first(r) for r in R))
    pins = {k: sha(os.path.join(ROOT, 'pins', k)) for k in ('code.sha256', 'inputs.sha256', 'block_days.tsv')}
    man = os.path.join(ST, 'manifest.sha256'); posted = os.path.join(ST, 'MANIFEST_POSTED')
    L.append(f"Runner run_exam.sh sha256 `{sha(RUNNER)}` · pins/code.sha256 `{pins['code.sha256']}` · pins/inputs.sha256 `{pins['inputs.sha256']}` · pins/block_days.tsv `{pins['block_days.tsv']}`")
    L.append(f"Phase-1 manifest work/state/manifest.sha256 `{sha(man)}` ({sum(1 for _ in open(man))} files), posted before phase 2 as `{open(posted).read().strip()}`")
    starts = sorted(set(re.findall(r'run_exam\.sh start; sha256 ([0-9a-f]{64})', open(os.path.join(RL, 'exam.log')).read())))
    L.append(f"Runner sha256 at every start on this work folder: {', '.join('`' + x + '`' for x in starts)}"
             + ('' if len(starts) == 1 else ' — ⚠️ DEVIATION: the runner changed between starts (see section 10)'))
    L.append(f"Withheld statistics (data-gate failures, never printed): work/withheld_stats.json sha256 `{wsha}` ({len(withheld['primary'])} primary rules, {len(withheld['alone'])} alone seed-rules)")
    for r in R:
        if WH[r]: L.append(f"READING · rule #{r} ({CELL[r]}): {CT} — final for Block A (no re-run, no re-draw); this rule waits for Block B. Sensitivity not read. qualifies: false")
        else: L.append(f"READING · rule #{r} ({CELL[r]}): {reading[r]} — primary {P['v'][r]}; {agree[r]['n_pass']} of {len(SEEDS)} alone seeds PASS; qualifies: {'true' if qual[r] else 'false'}. "
                       f"(Exam cell alone at SEED {SEEDS[0]}: {A0['v'][r] if not WHS[(SEEDS[0], r)] else CT} — information only.)")
    L.append('')
    cutj = {k: J(os.path.join(ST, f'cut_{k}.json')) for k in ('tape', 'wide', 'lock')}
    eth = os.path.join(V4J, 'ethusd_coingecko.json')
    L.append('Hashes recorded at run time (sha256 of exactly the content used, rows before the cut ' + iso(CUT) + '):')
    L.append(f"- 10-07 V2/V3 tape cut: `{cutj['tape']['sha256']}` ({cutj['tape']['kept']} rows, {cutj['tape']['bytes']} B; row v2v3-tape-cutA in work/state/cut_rows.tsv)")
    L.append(f"- 10-07 V4-wide cut: `{cutj['wide']['sha256']}` ({cutj['wide']['kept']} rows, {cutj['wide']['bytes']} B; row v4-wide-cutA in work/state/cut_rows.tsv)")
    L.append(f"- locked V4 tape portion (join days from 2026-09-25 to the cut): `{cutj['lock']['sha256']}` ({cutj['lock']['kept']} rows; max lateness seen {cutj['lock']['maxLateBlocks']} blocks)")
    L.append(f"- ETH/USD series (CoinGecko hourly, cut at the cut): `{sha(eth)}`")
    L.append('')
    W_ = '(withheld: data gate failed)'
    L.append('## 1 · The bar (PRIMARY: the 09-27 pass composition on the fixed Option A engines, SEED 20260927)')
    L.append('| rule | d heavy vs ACTIVITY twin (CI) | SE_cons | one-sided p | Holm step / threshold | n paired / coins | drop-5 | gates | verdict |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    gtxt = lambda b: ' '.join(k + ('✓' if v == 'PASS' else '✗') for k, v in b['gates'].items())
    for r in R:
        b, h, s = P['b'][r], P['holm'][r], P['s'][r]
        if WH[r]:
            L.append(f"| #{r} {s['cell']} | {W_} | — | — (enters Holm with p = 1) | {h['step']} / {h['threshold']} | — | — | {gtxt(b)} | **{P['v'][r]}** |")
        else:
            L.append(f"| #{r} {s['cell']} | {b['d']} ({b['ci'][0]}..{b['ci'][1]}) | {b['se_cons']} | {b['p']} | {h['step']} / {h['threshold']} → {'ok' if h['ok'] else 'no'} | {b['n']} / {b['coins']} | {b['drop5']} | "
                     f"{gtxt(b)} | **{P['v'][r]}** |")
    L.append('')
    L.append('Conditions: ' + ' · '.join((f"#{r}: gates {P['b'][r]['gates_ok']} (other conditions withheld)" if WH[r] else
                                         f"#{r}: d>0 {P['b'][r]['d_pos']}, CI>0 {P['b'][r]['ci_pos']}, Holm {P['holm'][r]['ok']}, n≥300 {P['b'][r]['n_ok']}, coins≥60 {P['b'][r]['coins_ok']}, drop-5>0 {P['b'][r]['drop5_pos']}, gates {P['b'][r]['gates_ok']}") for r in R))
    L.append("Holm (registered, pond #330 M6): a rule whose data gate fails enters Holm with p = 1, so the other rule must clear 0.0125 on its own.")
    L.append('')
    L.append('## 2 · The money test (REPORTED, not the bar)')
    for r in R:
        if WH[r]: L.append(f'- rule #{r}: {W_}'); continue
        m = P['s'][r]['money_test']
        L.append(f"- rule #{r}: heavy-cost raw mean {m['raw_heavy_mean']} (CI {m['raw_heavy_ci95']}), n {m['n']} — {m['note']}. ⚠️ R-0111: the heavy view's Pons take is too low.")
    L.append('')
    L.append('## 3 · n, coins, drop-5, Option A counts')
    for r in R:
        if WH[r]: L.append(f'- rule #{r}: {W_}'); continue
        s = P['s'][r]; mt = s.get('meta') or {}
        L.append(f"- rule #{r}: paired n {s['bar'].get('n')} on {s['bar'].get('coins')} coins (cell rows {s['bar'].get('n_rows', s['bar'].get('n'))}); drop-5 d {s['bar'].get('drop5')}; "
                 f"depth-floor skips (pre-filter dropped, this cell) {s['prefilter']['skipDepth_dropped']}; twin draw sizes (this cell) {dict((k, v) for k, v in (mt.get('twinDistinct') or {}).items() if '|' + s['cell'] + '|' in k)}")
    L.append('')
    L.append('## 4 · Data gate (G1-G5, G9, G10)')
    for r in R:
        b = P['b'][r]; c = P['s'][r]['gate']['components']
        L.append(f"- rule #{r}: {b['gates']} · strategy priced {c['S']['priced_share']}, small prints {c['S']['g4_small_share']}, g5 fails {c['S']['g5_fail']}; "
                 f"twins priced WR {c['WR']['priced_share']} WA {c['WA']['priced_share']}; G2 notes {b['gate_why']['G2']}; G9 notes {b['gate_why']['G9']}")
    L.append('')
    L.append('## 5 · Sensitivity (registered 2026-10-05: reported beside the verdict, never instead of it; AGREE / qualifying as amended 2026-10-07, pond #330 M5)')
    for r in R:
        if WH[r]: L.append(f'- rule #{r}: not read — the primary is {CT}, final for Block A {W_}'); continue
        z = sens[r]; b0 = A0['b'][r]
        s0 = W_ if WHS[(SEEDS[0], r)] else f"d {b0['d']} ({b0['ci'][0]}..{b0['ci'][1]}), p {b0['p']}, n {b0['n']}/{b0['coins']}"
        L.append(f"- rule #{r}: alone over {len(SEEDS)} seeds {SEEDS[0]}..{SEEDS[-1]}: {agree[r]['n_pass']} PASS, {agree[r]['n_same']} reach the primary's verdict → {'AGREE' if agree[r]['agree'] else 'DISAGREE'}; "
                 f"READING {reading[r]}; qualifies {'true' if qual[r] else 'false'}. Over the {z['seeds_with_numbers']} seeds with numbers: median d {z['median_d']} (range {z['d_min']}..{z['d_max']}); CI>0 {pct(z['share_ci_pos'])}, "
                 f"p<0.0125 {pct(z['share_p_lt_0125'])}, p<0.025 {pct(z['share_p_lt_025'])}, drop-5>0 {pct(z['share_drop5_pos'])}. Information only: the exam cell alone at SEED {SEEDS[0]}: {s0} → {A0['v'][r]}.")
    L.append('')
    L.append('| seed | ' + ' | '.join(f'#{r} d (CI) p → verdict' for r in R) + ' |'); L.append('|---|---|---|')
    for s in SEEDS:
        cells = []
        for r in R:
            if WH[r]: cells.append('not read')
            elif WHS[(s, r)]: cells.append(f'{W_} → {CT}')
            else: b = SE[s]['b'][r]; cells.append(f"{b['d']} ({b['ci'][0]}..{b['ci'][1]}) {b['p']} → {SE[s]['v'][r]}")
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    L.append('')
    L.append('## 6 · Reported beside the bar (frozen spec lists)')
    for r in R:
        L.append(f'- rule #{r}: ' + (W_ if WH[r] else json.dumps(P['s'][r]['reported'], default=str)[:2500]))
    L.append('')
    L.append('## 7 · Every input sha256')
    L.append('Code and open inputs: verified against pins/code.sha256 and pins/inputs.sha256 before anything ran; block days against pins/block_days.tsv (lists below).')
    for fn in ('code.sha256', 'inputs.sha256', 'block_days.tsv'):
        p = os.path.join(ROOT, 'pins', fn)
        L.append(f'- pins/{fn} sha256 `{sha(p)}`:'); L.extend('  - `' + ln.strip() + '`' for ln in open(p))
    for k in ('tape_open', 'tape_block', 'wide_open', 'wide_block'):
        for d, m in sorted(J(os.path.join(ST, f'{k}.json')).items()): L.append(f"- {k} {d}: `{m['sha256']}` ({m['bytes']} B uncompressed) {m['path']}")
    for p in sorted(glob.glob(os.path.join(TBL, '*.tsv')) + glob.glob(os.path.join(TBL, '*.js')) + [os.path.join(V4J, x) for x in ('anchors.tsv', 'heldout.tsv', 'meta.json', 'decimals.json', 'unknown_keys.json', 'ethusd_coingecko.json')]):
        if os.path.exists(p): L.append(f'- {p.replace(W + "/", "work/")}: `{sha(p)}`')
    for p in sorted(glob.glob(os.path.join(V4J, 'out', 'v4-swaps-*.ndjson.gz'))): L.append(f'- {p.replace(W + "/", "work/")}: `{sha(p)}`')
    for ln in open(os.path.join(ST, 'ledgers.sha256')):
        h, f = ln.split(None, 1); L.append(f'- ledger / state snapshot read by the table builders and join/meta.js: work/ledgers/{f.strip()} `{h}`')
    L.append(f'- the phase-1 manifest (every line is re-checked before phase 2 and before step 9): work/state/manifest.sha256 `{sha(man)}`')
    L.append('')
    L.append('## 8 · Engine runs (every runs.tsv row, full 64-hex sha256; runs.tsv itself is published in report_files/)')
    L.append('| run | engine sha256 | start | end | exit | elapsed | max RSS MB | files opened | output content sha256 |'); L.append('|---|---|---|---|---|---|---|---|---|')
    for v in run_rows:
        L.append(f"| {v['label']} | `{v['engine_sha']}` | {v['start']} | {v['end']} | {v.get('exit')} | {v.get('elapsed')} | {int(v.get('maxrss_kb') or 0) // 1024} | {v.get('opened')} | `{v.get('content_sha256', '')}` |")
    L.append('')
    L.append('## 9 · Steps')
    for k in ('table_meta', 'table_poolfee', 'unknown_split', 'unknown_merge', 'poolcounts', 'addr_lists'):
        p = os.path.join(ST, f'{k}.json')
        if os.path.exists(p): L.append(f'- {k}: ' + json.dumps({a: b for a, b in J(p).items() if not str(a).startswith('examples')})[:600])
    for p in sorted(glob.glob(os.path.join(ST, 'consist_*.json'))):
        c = J(p); L.append(f"- join consistency {os.path.basename(p)[8:-5]} vs the 09-27 join: identical {c.get('identical', 0)}, differ {c.get('differ', 0)}, only mine {c.get('only_mine', 0)}, only 09-27 {c.get('only_orig', 0)}, fields {c.get('fields')}")
    L.append(f"- B1 seam gate (pond #330, before any engine ran): {json.dumps(J(os.path.join(ST, 'seam_gate.json')))}")
    L.append('')
    L.append('## 10 · Refusals, cap changes, engine deaths and deviations on this work folder (registered, pond #330 H2 / L22)')
    rf = sorted(glob.glob(os.path.join(ST, 'REFUSED*')))
    if not rf: L.append('- no refusal')
    for p in rf:
        L.append(f'- {os.path.basename(p)} sha256 `{sha(p)}`:'); L.extend(f'  - {ln.rstrip()}' for ln in open(p) if ln.strip())
    cp = os.path.join(ST, 'CAP_CHANGE')
    if os.path.exists(cp):
        L.append(f'- CAP_CHANGE sha256 `{sha(cp)}` (L22: the only allowed change after an engine hit its RSS guard or heap cap):'); L.extend(f'  - {ln.rstrip()}' for ln in open(cp) if ln.strip())
    else: L.append('- no cap change')
    dp = os.path.join(ST, 'ENGINE_DEATHS')                     # engines that died without completing (kernel kill): re-run unchanged, disclosed
    if os.path.exists(dp):
        L.append(f'- ENGINE_DEATHS sha256 `{sha(dp)}` (an engine that died without completing is re-run unchanged; a partial output is never read):'); L.extend(f'  - {ln.rstrip()}' for ln in open(dp) if ln.strip())
    else: L.append('- no engine death')
    fo = sorted(glob.glob(os.path.join(W, 'failed_outputs', '*'))) + sorted(glob.glob(os.path.join(RL, '*.log.died-*')))
    for p in fo: L.append(f'- kept unread: {p.replace(W + "/", "work/")} sha256 `{sha(p)}`')
    L.append(f"- runner sha256 at every start: {', '.join(starts)}" + ('' if len(starts) == 1 else ' — the runner changed between starts: a LABELLED DEVIATION, see the coordinator\'s post'))
    rep = dict(primary={r: dict(verdict=P['v'][r], reading=reading[r], qualifies=qual[r], holm=dict(step=P['holm'][r]['step'], threshold=P['holm'][r]['threshold'], ok=P['holm'][r]['ok']),
                                bar=({'withheld': True} if WH[r] else P['b'][r])) for r in R},
               agree={r: ({'withheld': True} if WH[r] else agree[r]) for r in R},
               sensitivity={r: ({'withheld': True} if WH[r] else sens[r]) for r in R},
               qualifies={r: qual[r] for r in R}, withheld_stats_sha256=wsha, runner_sha256=sha(RUNNER), pins_sha256=pins, manifest_sha256=sha(man))
    rtxt = json.dumps(rep, indent=1, default=str)
    return L, wtxt, rtxt


try:
    L, wtxt, rtxt = main()
except Exception as e:                                     # pond #330 H1: no swallowed failure, nothing written, no verdict printed
    print(f'REPORT REFUSED: {type(e).__name__}: {e} — nothing written', file=sys.stderr)
    sys.exit(2)
def put(path, text):                                      # atomic: a kill (e.g. a reboot) never leaves a half-written file
    open(path + '.tmp', 'w').write(text); os.replace(path + '.tmp', path)
put(os.path.join(W, 'withheld_stats.json'), wtxt)
put(os.path.join(W, 'report.json'), rtxt)
put(OUTMD, '\n'.join(L) + '\n')
print(L[0])
