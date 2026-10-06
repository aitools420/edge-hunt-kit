#!/usr/bin/env python3
"""report.py <work> <report.md> <cut_unix> "<seeds>" — NEW CODE (sealed-exam-blockA): the exam report, from the runner's outputs only.
Line 1 = each rule's verdict and whether the primary and the sensitivity agree. Then the hashes recorded at run time, the bar
conditions, the money test (reported, not the bar), n / coins, drop-5, the data gate, the sensitivity, and every input sha256.

THE VERDICT (registered): a rule PASSES iff ALL of: Holm k = 2 passes its one-sided p (SE_cons; the smaller of the two rules' p must be
< 0.0125, and only then the larger < 0.025); d > 0 and its CI lower bound > 0; n >= 300 paired trades on >= 60 coins; drop-5 d > 0;
DATA GATE G1-G5, G9, G10 PASS. A gate failure reads CAN'T TELL (data); anything else that misses reads NOT SHOWN.
AGREEMENT (registered with this runner): for each rule the sensitivity AGREES with the primary iff (1) the exam cell alone at SEED
20260927 reaches the same verdict, and (2) the verdict reached by at least half of the 20 alone seeds is the same verdict. Each alone
verdict applies the same bar, with Holm k = 2 across the two rules' alone runs of the same seed."""
import sys, json, os, glob, hashlib, statistics, datetime, re
W, OUTMD, CUT, SEEDS = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split()
ST, STATS, RL, V4J, TBL = (os.path.join(W, x) for x in ('state', 'stats', 'runlogs', 'v4join', 'tables'))
J = lambda p: json.load(open(p))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
runs = {}
for ln in open(os.path.join(RL, 'runs.tsv')):
    a = ln.rstrip('\n').split('\t'); kv = dict(x.split('=', 1) for x in a[5:] if '=' in x)
    runs[a[0]] = dict(engine_sha=a[1], engine=a[2], start=a[3], end=a[4], **kv)
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
def bar_parts(st, label):
    b = st['bar']; ci = b.get('ci95') or [None, None]
    gs, gw = gates(st, label)
    return dict(d=b.get('d_mean'), ci=ci, p=b.get('p_one_sided'), n=b.get('n'), coins=b.get('coins'), drop5=b.get('drop5'),
                d_pos=(b.get('d_mean') or 0) > 0, ci_pos=ci[0] is not None and ci[0] > 0, n_ok=(b.get('n') or 0) >= 300, coins_ok=(b.get('coins') or 0) >= 60,
                drop5_pos=b.get('drop5') is not None and b['drop5'] > 0, gates=gs, gate_why=gw, gates_ok=all(v == 'PASS' for v in gs.values()))
def holm(p1, p2):
    ps = sorted([(p if p is not None else 1.0, k) for k, p in (('1', p1), ('2', p2))])
    out = {}; first_ok = ps[0][0] < 0.0125
    out[ps[0][1]] = dict(p=ps[0][0], threshold=0.0125, step=1, ok=first_ok)
    out[ps[1][1]] = dict(p=ps[1][0], threshold=0.025, step=2, ok=first_ok and ps[1][0] < 0.025)
    return out
def verdict(bp, h):
    if not bp['gates_ok']: return "CAN'T TELL (data)"
    ok = h['ok'] and bp['d_pos'] and bp['ci_pos'] and bp['n_ok'] and bp['coins_ok'] and bp['drop5_pos']
    return 'PASS' if ok else 'NOT SHOWN'
def evaluate(l1, l2):
    s1, s2 = J(os.path.join(STATS, l1 + '.json')), J(os.path.join(STATS, l2 + '.json'))
    b1, b2 = bar_parts(s1, l1), bar_parts(s2, l2); H = holm(b1['p'], b2['p'])
    return dict(s={'1': s1, '2': s2}, b={'1': b1, '2': b2}, holm=H, v={'1': verdict(b1, H['1']), '2': verdict(b2, H['2'])})
P = evaluate('primary_rule1', 'primary_rule2')
A0 = evaluate(f'alone_rule1_s{SEEDS[0]}', f'alone_rule2_s{SEEDS[0]}')
SE = {s: evaluate(f'alone_rule1_s{s}', f'alone_rule2_s{s}') for s in SEEDS}
agree, sens = {}, {}
for r in ('1', '2'):
    vs = [SE[s]['v'][r] for s in SEEDS]; maj = max(set(vs), key=lambda v: (vs.count(v), v == P['v'][r]))
    share_pass = vs.count('PASS') / len(vs)
    majority_same = vs.count(P['v'][r]) * 2 >= len(vs)
    agree[r] = dict(alone_seed0=A0['v'][r], alone_seed0_same=A0['v'][r] == P['v'][r], majority_same=majority_same, agree=(A0['v'][r] == P['v'][r]) and majority_same)
    ds = [SE[s]['b'][r]['d'] for s in SEEDS if SE[s]['b'][r]['d'] is not None]
    sens[r] = dict(median_d=statistics.median(ds) if ds else None, d_min=min(ds) if ds else None, d_max=max(ds) if ds else None, share_PASS=share_pass,
                   share_ci_pos=sum(SE[s]['b'][r]['ci_pos'] for s in SEEDS) / len(SEEDS),
                   share_p_lt_0125=sum((SE[s]['b'][r]['p'] or 1) < 0.0125 for s in SEEDS) / len(SEEDS),
                   share_p_lt_025=sum((SE[s]['b'][r]['p'] or 1) < 0.025 for s in SEEDS) / len(SEEDS),
                   share_drop5_pos=sum(SE[s]['b'][r]['drop5_pos'] for s in SEEDS) / len(SEEDS),
                   verdicts={s: SE[s]['v'][r] for s in SEEDS})
L = []
first = ' · '.join(f"rule #{r} ({'C2P' if r == '1' else 'D25L48'}): {P['v'][r]} — primary and sensitivity {'AGREE' if agree[r]['agree'] else 'DISAGREE'}"
                   + ('' if agree[r]['agree'] else f" (cell alone at SEED {SEEDS[0]}: {agree[r]['alone_seed0']}; {sens[r]['share_PASS']:.0%} of {len(SEEDS)} seeds PASS)") for r in ('1', '2'))
L.append(f'VERDICT · {first}')
L.append('')
cutj = {k: J(os.path.join(ST, f'cut_{k}.json')) for k in ('tape', 'wide', 'lock')}
eth = os.path.join(V4J, 'ethusd_coingecko.json')
L.append('Hashes recorded at run time (sha256 of exactly the content used, rows before the cut ' + iso(CUT) + '):')
L.append(f"- 10-07 V2/V3 tape cut: `{cutj['tape']['sha256']}` ({cutj['tape']['kept']} rows, {cutj['tape']['bytes']} B; appended to tape-hashes.tsv as v2v3-tape-cutA)")
L.append(f"- 10-07 V4-wide cut: `{cutj['wide']['sha256']}` ({cutj['wide']['kept']} rows, {cutj['wide']['bytes']} B; appended as v4-wide-cutA)")
L.append(f"- locked V4 tape portion (join days from 2026-09-25 to the cut): `{cutj['lock']['sha256']}` ({cutj['lock']['kept']} rows; max lateness seen {cutj['lock']['maxLateBlocks']} blocks)")
L.append(f"- ETH/USD series (CoinGecko hourly, cut at the cut): `{sha(eth)}`")
L.append('')
L.append('## 1 · The bar (PRIMARY: the 09-27 pass composition on the fixed Option A engines, SEED 20260927)')
L.append('| rule | d heavy vs ACTIVITY twin (CI) | SE_cons | one-sided p | Holm step / threshold | n paired / coins | drop-5 | gates | verdict |')
L.append('|---|---|---|---|---|---|---|---|---|')
for r in ('1', '2'):
    b, h, s = P['b'][r], P['holm'][r], P['s'][r]
    L.append(f"| #{r} {s['cell']} | {b['d']} ({b['ci'][0]}..{b['ci'][1]}) | {s['bar'].get('se_cons')} | {b['p']} | {h['step']} / {h['threshold']} → {'ok' if h['ok'] else 'no'} | {b['n']} / {b['coins']} | {b['drop5']} | "
             f"{' '.join(k + ('✓' if v == 'PASS' else '✗') for k, v in b['gates'].items())} | **{P['v'][r]}** |")
L.append('')
L.append('Conditions: ' + ' · '.join(f"#{r}: d>0 {P['b'][r]['d_pos']}, CI>0 {P['b'][r]['ci_pos']}, Holm {P['holm'][r]['ok']}, n≥300 {P['b'][r]['n_ok']}, coins≥60 {P['b'][r]['coins_ok']}, drop-5>0 {P['b'][r]['drop5_pos']}, gates {P['b'][r]['gates_ok']}" for r in ('1', '2')))
L.append('')
L.append('## 2 · The money test (REPORTED, not the bar)')
for r in ('1', '2'):
    m = P['s'][r]['money_test']
    L.append(f"- rule #{r}: heavy-cost raw mean {m['raw_heavy_mean']} (CI {m['raw_heavy_ci95']}), n {m['n']} — {m['note']}. ⚠️ R-0111: the heavy view's Pons take is too low.")
L.append('')
L.append('## 3 · n, coins, drop-5, Option A counts')
for r in ('1', '2'):
    s = P['s'][r]; mt = s.get('meta') or {}
    L.append(f"- rule #{r}: paired n {s['bar'].get('n')} on {s['bar'].get('coins')} coins (cell rows {s['bar'].get('n_rows', s['bar'].get('n'))}); drop-5 d {s['bar'].get('drop5')}; "
             f"depth-floor skips (pre-filter dropped, this cell) {s['prefilter']['skipDepth_dropped']}; twin draw sizes (this cell) {dict((k, v) for k, v in (mt.get('twinDistinct') or {}).items() if '|' + s['cell'] + '|' in k)}")
L.append('')
L.append('## 4 · Data gate (G1-G5, G9, G10)')
for r in ('1', '2'):
    b = P['b'][r]; c = P['s'][r]['gate']['components']
    L.append(f"- rule #{r}: {b['gates']} · strategy priced {c['S']['priced_share']}, small prints {c['S']['g4_small_share']}, g5 fails {c['S']['g5_fail']}; "
             f"twins priced WR {c['WR']['priced_share']} WA {c['WA']['priced_share']}; G2 notes {b['gate_why']['G2']}; G9 notes {b['gate_why']['G9']}")
L.append('')
L.append('## 5 · Sensitivity (registered 2026-10-05: reported beside the verdict, never instead of it)')
for r in ('1', '2'):
    b0 = A0['b'][r]; z = sens[r]
    L.append(f"- rule #{r}: (1) exam cell ALONE, SEED {SEEDS[0]}: d {b0['d']} ({b0['ci'][0]}..{b0['ci'][1]}), p {b0['p']}, n {b0['n']}/{b0['coins']} → {A0['v'][r]}. "
             f"(2) alone over {len(SEEDS)} seeds {SEEDS[0]}..{SEEDS[-1]}: median d {z['median_d']} (range {z['d_min']}..{z['d_max']}); share PASS {z['share_PASS']:.0%}, CI>0 {z['share_ci_pos']:.0%}, "
             f"p<0.0125 {z['share_p_lt_0125']:.0%}, p<0.025 {z['share_p_lt_025']:.0%}, drop-5>0 {z['share_drop5_pos']:.0%}. Agreement: alone-seed-0 same {agree[r]['alone_seed0_same']}, majority same {agree[r]['majority_same']} → {'AGREE' if agree[r]['agree'] else 'DISAGREE'}.")
L.append('')
L.append('| seed | ' + ' | '.join(f'#{r} d (CI) p → verdict' for r in ('1', '2')) + ' |'); L.append('|---|---|---|')
for s in SEEDS:
    L.append(f'| {s} | ' + ' | '.join(f"{SE[s]['b'][r]['d']} ({SE[s]['b'][r]['ci'][0]}..{SE[s]['b'][r]['ci'][1]}) {SE[s]['b'][r]['p']} → {SE[s]['v'][r]}" for r in ('1', '2')) + ' |')
L.append('')
def tail_sections():
    L.append('## 6 · Reported beside the bar (frozen spec lists)')
    for r in ('1', '2'):
        L.append(f"- rule #{r}: " + json.dumps(P['s'][r]['reported'], default=str)[:2500])
    L.append('')
    L.append('## 7 · Every input sha256')
    L.append('Code and open inputs: verified against pins/code.sha256 and pins/inputs.sha256 before anything ran (lists below).')
    for fn in ('code.sha256', 'inputs.sha256'):
        p = os.path.join(os.path.dirname(OUTMD), 'pins', fn)
        L.append(f'- pins/{fn} sha256 `{sha(p)}`:'); L += ['  - `' + ln.strip() + '`' for ln in open(p)]
    for k in ('tape_open', 'tape_block', 'wide_open', 'wide_block'):
        for d, m in sorted(J(os.path.join(ST, f'{k}.json')).items()): L.append(f"- {k} {d}: `{m['sha256']}` ({m['bytes']} B uncompressed) {m['path']}")
    for p in sorted(glob.glob(os.path.join(TBL, '*.tsv')) + glob.glob(os.path.join(TBL, '*.js')) + [os.path.join(V4J, x) for x in ('anchors.tsv', 'meta.json', 'decimals.json', 'unknown_keys.json', 'ethusd_coingecko.json')]):
        if os.path.exists(p): L.append(f'- {p.replace(W + "/", "work/")}: `{sha(p)}`')
    for p in sorted(glob.glob(os.path.join(V4J, 'out', 'v4-swaps-*.ndjson.gz'))): L.append(f'- {p.replace(W + "/", "work/")}: `{sha(p)}`')
    for ln in open(os.path.join(ST, 'ledgers.sha256')):
        h, f = ln.split(None, 1); L.append(f'- ledger / state snapshot read by the table builders and join/meta.js: work/ledgers/{f.strip()} `{h}`')
    L.append('')
    L.append('## 8 · Engine runs')
    L.append('| run | engine sha256 | start | end | exit | elapsed | max RSS MB | files opened | output content sha256 |'); L.append('|---|---|---|---|---|---|---|---|---|')
    for k, v in runs.items():
        L.append(f"| {k} | `{v['engine_sha'][:16]}` | {v['start']} | {v['end']} | {v.get('exit')} | {v.get('elapsed')} | {int(v.get('maxrss_kb') or 0) // 1024} | {v.get('opened')} | `{v.get('content_sha256', '')[:16]}` |")
    L.append('')
    L.append('## 9 · Steps')
    for k in ('table_meta', 'table_poolfee', 'unknown_split', 'unknown_merge', 'poolcounts', 'addr_lists'):
        p = os.path.join(ST, f'{k}.json')
        if os.path.exists(p): L.append(f'- {k}: ' + json.dumps({a: b for a, b in J(p).items() if not str(a).startswith('examples')})[:600])
    for p in sorted(glob.glob(os.path.join(ST, 'consist_*.json'))):
        c = J(p); L.append(f"- join consistency {os.path.basename(p)[8:-5]} vs the 09-27 join: identical {c.get('identical', 0)}, differ {c.get('differ', 0)}, only mine {c.get('only_mine', 0)}, only 09-27 {c.get('only_orig', 0)}, fields {c.get('fields')}")
try:
    tail_sections()
except Exception as e:                                          # sections 6-9 are context; a failure here must not lose the verdict above
    L.append(f'(sections 6-9 failed: {type(e).__name__}: {e} — the verdict, bar, money test, gates and sensitivity above are complete)')
open(OUTMD, 'w').write('\n'.join(L) + '\n')
json.dump(dict(primary={r: dict(verdict=P['v'][r], bar=P['b'][r], holm=P['holm'][r]) for r in ('1', '2')}, agree=agree, sensitivity=sens), open(os.path.join(W, 'report.json'), 'w'), indent=1, default=str)
print(L[0])
