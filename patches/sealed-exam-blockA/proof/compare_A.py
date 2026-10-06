#!/usr/bin/env python3
"""compare_A.py <fix1|fix2|draws> <runA.ndjson.gz> <runB.ndjson.gz> <out.json> — the Option A attribution proof, row by row.
  fix1   A = twin-cache engine (_rk), B = Option A with FIX 2 off (no-skip): ONLY the draw rule differs.
         Strategy rows (every kind 'S' row, every field) must be IDENTICAL. Twin rows: B draws min(3, pool) DISTINCT coins per signal and
         twin type; every (signal, twin type, coin) present in both runs must have the IDENTICAL row except `rep` (its draw index).
  fix2   A = no-skip, B = Option A with the SAME random numbers per signal (H2 replay of A's draws): ONLY the depth floor differs.
         Rows keyed without the pair id (cell, sigTs, coin): every strategy-row difference must be (i) a thin entry (V4, depth1 < 0.001)
         skipped, (ii) the same cell+coin AFTER a skipped thin entry (it is free again: re-entry chain), or (iii) only the twin-pool
         descriptors eligN/nA/nD/mlA. Every (signal, twin, coin) in both runs must be identical except thin twin fills; a signal whose
         drawn coin set differs must sit in a cell with an earlier skip (its pool changed).
  draws  A = Option A with replayed draws, B = Option A natural: every strategy row must be IDENTICAL (draws touch twins only).
Prints a summary; writes the full tallies and every unexplained case to out.json. Exit 1 if anything is unexplained."""
import sys, json, gzip, collections
MODE, FA, FB, OUT = sys.argv[1:5]
DESC = {'eligN', 'nA', 'nD', 'mlA'}

def load(fn):
    S, W, meta = {}, collections.defaultdict(list), None
    with gzip.open(fn, 'rt') as f:
        for ln in f:
            j = json.loads(ln)
            if '_meta' in j: meta = j['_meta']; continue
            if j['kind'] == 'S': S.setdefault((j['pair'], j.get('clip', 50)), []).append(j)
            else: W[(j['pair'], j.get('tw'), j.get('clip', 50))].append(j)
    return S, W, meta

def strip(j, drop):
    return {k: v for k, v in j.items() if k not in drop}

def thin(j): return j.get('eK') == 'v4' and j.get('eDepth1') is not None and j['eDepth1'] < 0.001
res = dict(mode=MODE, A=FA, B=FB); bad = []
SA, WA, mA = load(FA); SB, WB, mB = load(FB)

if MODE in ('fix1', 'draws'):
    ka, kb = set(SA), set(SB); same = diff = 0; fields = collections.Counter()
    for k in ka & kb:
        if SA[k] == SB[k]: same += 1
        else:
            diff += 1
            for x, y in zip(SA[k], SB[k]):
                for f in set(x) | set(y):
                    if x.get(f) != y.get(f): fields[f] += 1
            if len(bad) < 50: bad.append(dict(why='strategy row differs', key=list(k), A=SA[k], B=SB[k]))
    res['strategy'] = dict(keysA=len(ka), keysB=len(kb), identical=same, differ=diff, onlyA=len(ka - kb), onlyB=len(kb - ka), fields=dict(fields))
    if ka != kb:
        for k in list(ka ^ kb)[:20]: bad.append(dict(why='strategy key in one run only', key=list(k)))
if MODE == 'fix1':
    pool = {}
    for (p, clip), rows in SA.items():
        if clip == 50: s = rows[0]; pool[p] = dict(R=s.get('eligN'), A=s.get('nA'), D=s.get('nD'))
    t = collections.Counter(); sizebad = []
    for key in set(WA) | set(WB):
        p, tw, clip = key; a, b = WA.get(key, []), WB.get(key, [])
        tb = [w['tok'] for w in b]
        if len(set(tb)) != len(tb): t['B_duplicate_coin'] += 1; bad.append(dict(why='B drew a coin twice', key=list(key), toks=tb))
        if clip == 50:
            n = pool.get(p, {}).get(tw)
            if n is not None and len(b) != min(3, n): t['B_size_not_min3pool'] += 1; sizebad.append(dict(key=list(key), n=n, got=len(b)))
            t[f'B_size_{len(b)}'] += 1
        ia = collections.defaultdict(list)
        for w in a: ia[w['tok']].append(w)
        for w in b:
            m = ia.get(w['tok'])
            if not m: t['B_coin_not_drawn_in_A'] += 1; continue
            if strip(w, {'rep'}) == strip(m[0], {'rep'}): t['same_signal_coin_identical'] += 1
            else:
                t['same_signal_coin_DIFFERENT'] += 1
                if len(bad) < 80: bad.append(dict(why='same signal+coin, different twin row', key=list(key), A=m[0], B=w))
        tbs = set(tb)
        for w in a:
            if w['tok'] not in tbs: t['A_row_coin_not_drawn_in_B'] += 1
    res['twins'] = dict(t); res['size_mismatch_examples'] = sizebad[:20]
    if sizebad: bad.append(dict(why='B twin count != min(3, pool)', n=len(sizebad)))
if MODE == 'fix2':
    def keyed(S, W):
        Sk, sigtok = {}, {}
        for (p, clip), rows in S.items():
            for s in rows:
                Sk[(s['cell'], s['tok'], s['sigTs'], clip)] = s
                if clip == 50: sigtok[p] = s['tok']
        Wk = {}
        for (p, tw, clip), rows in W.items():
            for w in rows: Wk[(w['cell'], w['sigTs'], sigtok.get(p), tw, clip, w['tok'])] = w
        return Sk, Wk
    SkA, WkA = keyed(SA, WA); SkB, WkB = keyed(SB, WB)
    skipB = collections.defaultdict(list)                       # (cell, tok) -> sigTs of B's skipped strategy entries
    for (cell, tok, ts, clip), s in SkB.items():
        if s.get('skipDepth') and clip == 50: skipB[(cell, tok)].append(ts)
    skipCells = collections.defaultdict(list)
    for (cell, tok), tss in skipB.items(): skipCells[cell].extend(tss)
    for c in skipCells: skipCells[c].sort()
    def after_skip(cell, tok, ts): return any(t0 < ts for t0 in skipB.get((cell, tok), []))
    def cell_skip_before(cell, ts): return any(t0 < ts for t0 in skipCells.get(cell, []))
    t = collections.Counter()
    TRADE_DROP = DESC | {'pair'}
    def base_thin_skipped(cell, tok, ts):                       # the clip-50 strategy entry at this signal was thin (A) and skipped (B)
        a0, b0 = SkA.get((cell, tok, ts, 50)), SkB.get((cell, tok, ts, 50))
        return bool(a0 and b0 and b0.get('skipDepth') and thin(a0))
    for k in set(SkA) | set(SkB):
        cell, tok, ts, clip = k; a, b = SkA.get(k), SkB.get(k)
        if clip != 50 and a and not b and base_thin_skipped(cell, tok, ts): t['S_shadow_of_thin_entry_gone'] += 1; continue
        if a and b:
            if strip(a, TRADE_DROP) == strip(b, TRADE_DROP):
                t['S_same' if all(a.get(f) == b.get(f) for f in DESC) else 'S_same_trade_descriptor_differs'] += 1
            elif b.get('skipDepth') and thin(a): t['S_thin_entry_skipped'] += 1
            elif after_skip(cell, tok, ts): t['S_differs_after_same_coin_skip'] += 1
            else:
                t['S_UNEXPLAINED'] += 1
                if len(bad) < 80: bad.append(dict(why='strategy row differs, not thin, no earlier skip', key=list(k), A=a, B=b))
        else:
            if after_skip(cell, tok, ts): t['S_only_' + ('A' if a else 'B') + '_after_same_coin_skip'] += 1
            else:
                t['S_only_' + ('A' if a else 'B') + '_UNEXPLAINED'] += 1
                if len(bad) < 80: bad.append(dict(why='strategy row in one run only, no earlier skip on that coin', key=list(k), row=a or b))
    WDROP = DESC | {'pair', 'rep'}
    thinTwinB = {(k[0], k[1], k[2], k[3], k[5]) for k, w in WkB.items() if k[4] == 50 and w.get('skipDepth')}
    sigsA, sigsB = collections.defaultdict(set), collections.defaultdict(set)
    for k in WkA:
        if k[4] == 50: sigsA[k[:5]].add(k[5])
    for k in WkB:
        if k[4] == 50: sigsB[k[:5]].add(k[5])
    for k in set(WkA) - set(WkB):
        if k[4] != 50 and (k[0], k[1], k[2], k[3], k[5]) in thinTwinB: t['W_shadow_of_thin_twin_gone'] += 1
    for k in set(WkA) & set(WkB):
        a, b = WkA[k], WkB[k]
        if strip(a, WDROP) == strip(b, WDROP): t['W_same_signal_coin_identical'] += 1
        elif b.get('skipDepth') and thin(a): t['W_thin_twin_skipped'] += 1
        else:
            t['W_same_signal_coin_UNEXPLAINED'] += 1
            if len(bad) < 120: bad.append(dict(why='same signal+coin twin differs (not thin)', key=list(k), A=a, B=b))
    for sk in set(sigsA) | set(sigsB):
        if sigsA.get(sk) == sigsB.get(sk): t['W_signal_coinset_same'] += 1
        elif cell_skip_before(sk[0], sk[1]): t['W_signal_coinset_differs_after_cell_skip'] += 1
        else:
            t['W_signal_coinset_UNEXPLAINED'] += 1
            if len(bad) < 160: bad.append(dict(why='twin coin set differs with no earlier skip in the cell', key=list(sk), A=sorted(sigsA.get(sk, [])), B=sorted(sigsB.get(sk, []))))
    res['tallies'] = dict(t)
    res['skips_B'] = dict(collections.Counter((s['cell'], s['kind'] + (s.get('tw') or '')) and f"{s['cell']}|{s['kind']}{s.get('tw') or ''}" for s in list(SkB.values()) + list(WkB.values()) if s.get('skipDepth')))
    res['first_skip_ts_by_cell'] = {c: v[0] for c, v in skipCells.items()}
res['metaA'] = {k: (mA or {}).get(k) for k in ('rows', 'exits', 'trunc', 'end', 'nofill', 'skipDepth')}
res['metaB'] = {k: (mB or {}).get(k) for k in ('rows', 'exits', 'trunc', 'end', 'nofill', 'skipDepth')}
res['unexplained'] = bad
json.dump(res, open(OUT, 'w'), indent=1, default=str)
summary = {k: v for k, v in res.items() if k not in ('unexplained', 'size_mismatch_examples', 'A', 'B')}
print(json.dumps(summary)[:3000])
print('UNEXPLAINED', len(bad))
sys.exit(1 if bad else 0)
