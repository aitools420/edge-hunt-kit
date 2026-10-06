#!/usr/bin/env python3
# sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
"""Block -> timestamp anchors for Robinhood Chain (L2 height = log blockNumber, the series the v4 tape's `blk` is in).
Fetches eth_getBlockByNumber on a fixed grid (every STEP blocks) plus a HELD-OUT random set (never used for
interpolation), from the public RPC (research lane, paced, JSON-RPC batches of 50). Read-only.
Out: anchors.tsv (blk \t ts, grid) and heldout.tsv (blk \t ts)."""
import json, subprocess, random, time, sys, os
import os
RPC = os.environ.get('RPC', 'https://robinhood-rpc.publicnode.com')   # keyless plain reads; the official RPC 429s batches
HERE = '/home/green/projects/patches/sealed-exam-blockA/work/v4join'
STEP = int(os.environ.get('STEP', 25000))
LO = 14_775_000

def call(batch):
    body = json.dumps([{'jsonrpc': '2.0', 'id': i, 'method': m, 'params': p} for i, (m, p) in enumerate(batch)])
    for attempt in range(5):
        try:
            out = subprocess.run(['curl', '-4', '-s', '-m', '60', '-H', 'Content-Type: application/json', '-d', body, RPC],
                                 capture_output=True, text=True, timeout=70).stdout
            r = json.loads(out)
            r = sorted(r, key=lambda x: x['id'])
            return [x.get('result') for x in r]
        except Exception as e:
            time.sleep(2 + attempt * 3)
    raise RuntimeError('rpc failed')

def blocks(nums):
    res = {}
    for i in range(0, len(nums), 50):
        chunk = nums[i:i + 50]
        rs = call([('eth_getBlockByNumber', [hex(b), False]) for b in chunk])
        for b, r in zip(chunk, rs):
            if r: res[b] = int(r['timestamp'], 16)
        time.sleep(0.3)
    return res

head = int(call([('eth_blockNumber', [])])[0], 16)
grid = list(range(LO, head, STEP)) + [head]
random.seed(20260927)
held = sorted(set(random.randrange(LO, head) for _ in range(500)) - set(grid))
g = blocks(grid); h = blocks(held)
with open(os.path.join(HERE, 'anchors.tsv'), 'w') as f:
    for b in sorted(g): f.write(f'{b}\t{g[b]}\n')
with open(os.path.join(HERE, 'heldout.tsv'), 'w') as f:
    for b in sorted(h): f.write(f'{b}\t{h[b]}\n')
print(f'head {head} grid {len(g)}/{len(grid)} heldout {len(h)}/{len(held)}')
