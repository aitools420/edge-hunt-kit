#!/usr/bin/env python3
# sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
"""Resolve pool keys for wide-file pool ids the births ledger does not name (pools initialised before it started),
from the PoolManager's own Initialize logs (topic1 = poolId), official RPC, full range, paced. Read-only; out unknown_keys.json."""
import json, subprocess, time, os
HERE = '/home/green/projects/patches/sealed-exam-blockA/work/v4join'
U = json.load(open(os.path.join(HERE, 'unknown_pools.json')))
INIT = '0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438'
PM = '0x8366a39CC670B4001A1121B8F6A443A643e40951'
RPC = 'https://rpc.mainnet.chain.robinhood.com'
ids = [k for k, v in sorted(U.items(), key=lambda x: -x[1]['n'])]
out = {}
def W(d, n): return d[2 + 64 * n: 2 + 64 * (n + 1)]
def s256(h):
    v = int(h, 16); return v - (1 << 256) if v >> 255 else v
SPAN = 10_000_000   # sealed-exam-blockA: the RPC's getLogs span with ONE value per topic position (measured 2026-10-05)
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
    for l in j['result']:
        d = l['data']; t = l['topics']
        out[t[1].lower()] = ['0x' + t[2][26:].lower(), '0x' + t[3][26:].lower(), int(W(d, 0), 16), s256(W(d, 1)), '0x' + W(d, 2)[24:].lower(), int(l['blockNumber'], 16)]
    if i % 50 == 0: print(i, len(out), flush=True)
json.dump(out, open(os.path.join(HERE, 'unknown_keys.json'), 'w'))
n_res = sum(U[k]['n'] for k in out); n_all = sum(v['n'] for v in U.values())
print(f'resolved {len(out)}/{len(ids)} pools, {n_res}/{n_all} swaps')
