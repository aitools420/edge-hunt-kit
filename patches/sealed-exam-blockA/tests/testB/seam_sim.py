#!/usr/bin/env python3
"""seam_sim.py <warm_day_file> <first_day_file> — open-data dry run of the join's FIRST-DAY effect (finalize.js causal other-quote
prices, Q_STALE 24 h). Streams the 09-27 join's own rows of two consecutive OPEN days and replays finalize's QS reference logic twice:
WARM (state built from the previous day, = the 09-27 join) and COLD (empty at the first day's 00:00Z, = a join whose first day this is).
Counts the first day's rows whose other-quote ETH price would differ (=> price_eth, price_usd, depth1_eth, depth5_eth, usd differ).
Memory: QS = (other-quote currencies) x (their reference pools), < 1e4 entries; rows are streamed one at a time."""
import sys, gzip, json, re, collections
W, F = sys.argv[1], sys.argv[2]
Q_STALE = 86400
rq = re.compile(rb'"quote_addr":"(0x[0-9a-f]+)"')
OTHERQ = set()
for fn in (W, F):
    with gzip.open(fn, 'rb') as f:
        for ln in f:
            m = rq.search(ln)
            if m: OTHERQ.add(m.group(1).decode())
rt = re.compile(rb'"tok":"(0x[0-9a-f]+)"')
def qprice(QS, q, ts):
    m = QS.get(q)
    if not m: return None
    best = None
    for v in m.values():
        if ts - v[1] <= Q_STALE and (best is None or v[2] > best[2]): best = v
    return best[0] if best else None
QSw, QSc = {}, {}
c = collections.Counter(); hours = collections.Counter(); byq = collections.Counter()
for day, fn in (('warm', W), ('first', F)):
    with gzip.open(fn, 'rb') as f:
        for ln in f:
            other = b'"quote_addr"' in ln
            mt = rt.search(ln); tok = mt.group(1).decode() if mt else None
            if not other and tok not in OTHERQ: continue
            j = json.loads(ln); ts = j['ts']
            pq, pe_file, dep_file = j.get('price_quote'), j.get('price_eth'), j.get('depth1_eth')
            if other:
                q = j['quote_addr']
                qw = qprice(QSw, q, ts)
                qc = qprice(QSc, q, ts) if day == 'first' else None
                if day == 'first':
                    c['first_day_other_quote_rows'] += 1
                    if pe_file is not None and qw is not None and pq:
                        c['warm_reproduces_file'] += abs(pq * qw - pe_file) <= 1e-6 * abs(pe_file)
                        c['warm_checked'] += 1
                    if qw != qc:
                        c['differ'] += 1; hours[(ts % 86400) // 3600] += 1; byq[j['quote']] += 1
                        if qc is None: c['differ_cold_null'] += 1
                qfile = (pe_file / pq) if (pe_file is not None and pq) else None
            if tok in OTHERQ and pe_file is not None and pe_file > 0 and float(j.get('liquidity') or 0) > 0:
                for QS, qm in ((QSw, None), (QSc, None)):
                    if QS is QSc and day != 'first': continue
                    pe, dep = pe_file, dep_file
                    if other:                                    # a reference pool that is itself other-quoted: price by this mode's qeth
                        qmode = qw if QS is QSw else qc
                        if qmode is None or not qfile: continue
                        pe, dep = pq * qmode, (dep_file or 0) * qmode / qfile
                    QS.setdefault(tok, {})[j['pool']] = (pe, ts, dep or 0)
            if day == 'first': c['first_day_rows_touched'] += 1
with gzip.open(F, 'rb') as f: c['first_day_rows_total'] = sum(1 for _ in f)
print(json.dumps(dict(first_day_file=F, warm_file=W, otherq_currencies=len(OTHERQ), counts=dict(c),
                      differ_by_utc_hour=dict(sorted(hours.items())), differ_by_quote_top10=dict(byq.most_common(10)))))
