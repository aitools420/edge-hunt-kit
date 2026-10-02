#!/usr/bin/env python3
"""hop.py - BLOOD HUNT 2 (PREREG §2): the cost of the EXTRA HOP (ETH -> quote token on entry, quote token -> ETH on exit) for a coin whose
entry pool is quoted in something other than ETH/WETH (the 2,713 stock-token-quoted Pons pools, USDG-quoted pools, any other quote).
Data we hold only: the V4 join rows of the quote token ITSELF (09-08 -> 09-26, never the sealed folder), the join's own pool table
(pools.js: fee key, hook, quote class) and pons_fee_terms.json. No RPC.

A quote token Q's candidate pool for one leg, at moment t (causal: its LAST row at or before t is its state):
  * the pool's token is Q, its quote is ETH or WETH (DIRECT route) - or, for the secondary route, USDG (then an ETH -> USDG leg is added,
    costed the same way on USDG's own direct pools);
  * that last row is <= 24 h old (the join's own staleness rule for pricing a quote), has liquidity > 0, depth1_eth > 0, price_eth > 0;
  * its per-side take is KNOWN EXACTLY: hookless -> fee key + 0.04 % (realism.py's nohook protocol residual); Pons hook -> launch terms
    (pons_fee_terms.json: hook + creator tax). Any other hook (static or dynamic fee) is NOT a candidate: its take is unmeasured, and a
    router minimum over estimated fees would systematically pick the pools whose fee is under-measured (seen in the structure smoke:
    a hooked ETH/USDG pool whose own-swap estimate reads 0). Hooked pools DO count for the reference price below (as in the join);
  * its price agrees with Q's reference price within +/- 10 % (reference = the price of Q's DEEPEST pool, by depth1_eth, among its
    ETH/WETH/USDG pools with a valid row <= 24 h old - the join's own qPrice() rule, i.e. the price the tape used to put Q in ETH).
One leg's multiplier (the engine's composition, buyCost / sellAt): buy (1 + f) x (1 + u), sell (1 - f) / (1 + u), u = size_eth x S1 / depth1_eth.
The route taken = the candidate with the best multiplier (a router picks the cheapest). No candidate -> no route."""
import json, gzip, os, bisect, math, collections, pickle
import numpy as np
P = os.environ['KIT_ROOT'] + '/patches'
S1 = math.sqrt(1.01) - 1; STALE = 86400; PX_TOL = 0.10; NOHOOK_RESID = 0.0004; DYN = 8388608
ETHQ = ('ETH', 'WETH'); USDG = '0x5fc5360d0400a0fd4f2af552add042d716f1d168'; PONS = '0xe5e702641ea86f4ae6cc3cdaed2b886f976be044'
SEAL = 1790467200


def build(rows_files, qpools, out_pkl):
    """rows_files: gz ndjson of join rows whose tok is a quote token; qpools: {pool: {tok, q, fee, hook}} for those tokens' pools."""
    PT = json.load(open(P + '/pons-feeterms-2026-09-27/pons_fee_terms.json'))['pools']
    per = collections.defaultdict(list)
    for f in rows_files:
        with gzip.open(f, 'rt') as fh:
            for ln in fh:
                r = json.loads(ln)
                if r['ts'] >= SEAL: raise RuntimeError('sealed row')
                if r['pool'] not in qpools: continue
                per[r['pool']].append((r['ts'], r.get('blk') or 0, r.get('li') or 0, r.get('price_eth'), r.get('depth1_eth'), r.get('liquidity'),
                                       r.get('price_quote'), r.get('amount_token'), r.get('amount_quote'), r.get('side')))
    T = collections.defaultdict(dict); stat = collections.Counter()
    for pool, rs in per.items():
        m = qpools[pool]; rs.sort(key=lambda x: (x[0], x[1], x[2]))
        hook = m.get('hook'); fee = m.get('fee')
        if hook in (None, 'null'):
            if fee is None or fee >= 1e6: stat['nohook_badfee'] += 1; continue
            kind, static = 'nohook', fee / 1e6 + NOHOOK_RESID
        elif hook == PONS:
            t = PT.get(pool)
            if not t or t.get('status') != 'measured': stat['pons_noterms'] += 1; continue
            kind, static = 'pons', (t['hookFeeBps'] + t['creatorTaxBps']) / 1e4
        else: kind, static = 'hook_unmeasured', None           # take not measured exactly -> never carries the hop; kept for the reference price
        n = len(rs); ts = np.array([x[0] for x in rs], dtype=np.int64)
        px = np.array([x[3] if x[3] is not None else np.nan for x in rs], dtype=float)
        dep = np.array([x[4] if x[4] is not None else np.nan for x in rs], dtype=float)
        ok = np.array([(x[5] not in ('0', None)) and (x[3] or 0) > 0 and (x[4] or 0) > 0 for x in rs])
        fe = np.full(n, np.nan if static is None else static)
        T[m['tok']][pool] = dict(q=m['q'], kind=kind, ts=ts, px=px, dep=dep, ok=ok, fee=fe)
        stat[kind] += 1
    pickle.dump(dict(tables=dict(T), stat=dict(stat)), open(out_pkl, 'wb'))
    return stat


class Hop:
    def __init__(self, pkl, poolquote_tsv, need_pools=None):
        d = pickle.load(open(pkl, 'rb')); self.T = d['tables']; self.stat = d['stat']
        self.QOF = {}                                           # coin pool -> (quote addr, class, sym)
        for ln in open(poolquote_tsv):
            a = ln.rstrip('\n').split('\t')
            if need_pools is None or a[0] in need_pools: self.QOF[a[0]] = (a[2], a[3], a[4])
        self._c = {}

    def _state(self, tok, t, quotes):
        """[(pool, fee, dep, px)] valid candidates of tok's pools quoted in `quotes` at t, and the reference price (join's qPrice rule)."""
        t = (int(t) // 60) * 60                                 # state as of the minute floor: deterministic whatever the query order
        key = (tok, t, quotes)
        if key in self._c: return self._c[key]
        cand, best = [], None
        for pool, R in self.T.get(tok, {}).items():
            i = int(np.searchsorted(R['ts'], t, side='right')) - 1
            if i < 0 or t - R['ts'][i] > STALE or not R['ok'][i]: continue
            if R['q'] in ('ETH', 'WETH', 'USDG') and (best is None or R['dep'][i] > best[0]): best = (R['dep'][i], R['px'][i])
            if R['q'] in quotes and R['fee'][i] == R['fee'][i]: cand.append((pool, float(R['fee'][i]), float(R['dep'][i]), float(R['px'][i]), R['kind']))
        ref = best[1] if best else None
        cand = [c for c in cand if ref and abs(c[3] / ref - 1) <= PX_TOL]
        if len(self._c) > 200000: self._c.clear()
        self._c[key] = (cand, ref); return cand, ref

    @staticmethod
    def _mult(fee, dep, size, side):
        u = size * S1 / dep
        return (1 + fee) * (1 + u) if side == 'buy' else (1 - fee) / (1 + u)

    def leg(self, tok, t, size, side, quotes=ETHQ):
        cand, _ = self._state(tok, t, quotes)
        if not cand: return None
        best = None
        for pool, fee, dep, px, kind in cand:
            m = self._mult(fee, dep, size, side)
            better = (best is None) or (m < best['mult'] if side == 'buy' else m > best['mult'])
            if better: best = dict(mult=m, pool=pool, fee=fee, impact=size * S1 / dep, kind=kind)
        return best

    def route(self, tok, t, size, side, allow_usdg=False):
        """best route ETH <-> tok at t: direct (ETH/WETH pool of tok), or (allow_usdg) ETH <-> USDG <-> tok. -> dict or None."""
        d = self.leg(tok, t, size, side)
        if d: d = dict(d, route='direct')
        if allow_usdg and tok != USDG:
            a = self.leg(USDG, t, size, side); b = self.leg(tok, t, size, side, quotes=('USDG',))
            if a and b:
                m = a['mult'] * b['mult']
                if d is None or (m < d['mult'] if side == 'buy' else m > d['mult']):
                    d = dict(mult=m, pool=b['pool'], fee=a['fee'] + b['fee'], impact=a['impact'] + b['impact'], kind=b['kind'], route='via_usdg')
        return d

    def quote_of(self, pool):
        """(quote addr, class, sym) for a V4 coin pool whose quote is NOT ETH/WETH, else None"""
        return self.QOF.get(pool)
