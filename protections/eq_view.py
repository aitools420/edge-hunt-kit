#!/usr/bin/env python3
"""eq_view.py <batch dir | trades.ndjson.gz> [--half JUDGE|FIT] - the R-0119 'eq' view beside the full view, per cell.
eq = only trades whose ENTRY pool is quoted in ETH, WETH or USDG (field eQ; V2/V3 entries count as their own quote). Trades on pools quoted
in any other token (stock tokens, memecoins) are priced through that token's ETH reference, which can jump and fool the >20x rule (R-0119).
Prints n, coins, mean, median of `ret` (real60h, % per trade; null = no hop route, left out exactly as analyze_v1.py does) for both views."""
import sys, gzip, json, os, statistics, collections
src = sys.argv[1]; half = sys.argv[sys.argv.index('--half') + 1] if '--half' in sys.argv else 'JUDGE'
f = os.path.join(src, 'trades.ndjson.gz') if os.path.isdir(src) else src
BASE = {'ETH', 'WETH', 'USDG'}
cells = collections.defaultdict(lambda: {'all': [], 'eq': []})
with gzip.open(f, 'rt') as fh:
    for ln in fh:
        r = json.loads(ln)
        if r.get('half') != half or r.get('ret') is None: continue
        c = cells[r['cell']]; c['all'].append((r['tok'], r['ret']))
        if r.get('eQ') in BASE or r.get('eQ') is None: c['eq'].append((r['tok'], r['ret']))
def s(v):
    if not v: return 'n 0'
    x = [b for _, b in v]
    return f"n {len(x):4d}  coins {len({a for a, _ in v}):3d}  mean {statistics.fmean(x):+8.2f}  median {statistics.median(x):+8.2f}"
print(f'{half} half, view real60h (ret)        ALL trades                                   |  EQ view (entry quote ETH/WETH/USDG)')
for cid in sorted(cells): print(f"{cid:28s} {s(cells[cid]['all'])}  |  {s(cells[cid]['eq'])}")
