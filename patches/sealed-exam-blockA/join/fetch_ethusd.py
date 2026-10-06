#!/usr/bin/env python3
"""fetch_ethusd.py <out.json> <from_unix> <cut_unix> — NEW CODE (sealed-exam-blockA). The ETH/USD series the V4 join prices with:
CoinGecko hourly (coins/ethereum/market_chart/range, keyless, IPv4), the same source and shape as v4-join-2026-09-27/ethusd_coingecko.json
(tested 2026-10-05 on 09-19..09-26: 169 hourly points, IDENTICAL to the 09-27 file). Only points with t < cut are kept, so no price at or
after the block's end is ever stored or used. Refuses (exit 2) unless the kept points are hourly, start <= from + 1 h and end >= cut - 2 h."""
import json, subprocess, sys, time, hashlib
OUT, FROM, CUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
url = f'https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from={FROM}&to={CUT}'
d = None
for a in range(8):
    r = subprocess.run(['curl', '-4', '-s', '-m', '60', '-H', 'accept: application/json', url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        if d.get('prices'): break
    except Exception:
        pass
    time.sleep(15 + 15 * a)
if not d or not d.get('prices'): print('REFUSE: CoinGecko fetch failed'); sys.exit(2)
keep = lambda arr: [x for x in arr if x[0] < CUT * 1000]
o = {k: keep(d.get(k, [])) for k in ('prices', 'market_caps', 'total_volumes')}
P = o['prices']; gaps = [(P[i + 1][0] - P[i][0]) / 1000 for i in range(len(P) - 1)]
ok = len(P) >= 24 and P[0][0] / 1000 <= FROM + 3600 and P[-1][0] / 1000 >= CUT - 7200 and max(gaps) <= 7200 and sorted(gaps)[len(gaps) // 2] == 3600
s = json.dumps(o)
open(OUT, 'w').write(s)
print(json.dumps(dict(points=len(P), first=P[0][0] // 1000, last=P[-1][0] // 1000, max_gap_s=max(gaps), dropped_at_or_after_cut=len(d['prices']) - len(P),
                      sha256=hashlib.sha256(s.encode()).hexdigest(), ok=ok)))
sys.exit(0 if ok else 2)
