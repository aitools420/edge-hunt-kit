#!/bin/bash
# run_testB2.sh — the two network steps of the exam join that Test B may not reach (it may find no NEW pre-ledger pool or NEW token):
# the exam copies of resolve_unknown.py (official RPC, PoolManager Initialize logs) and decimals.js (public RPC, Multicall3), each pointed
# at a throwaway folder (one path replaced) and fed 12 pools (6 by id, 6 with the earliest Initialize blocks) and 6 tokens the 09-27 join
# already resolved; their answers must equal the 09-27 ones.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; J=/home/green/projects/patches/v4-join-2026-09-27
S=/tmp/claude-1000/-home-green-projects/38d725a6-2ce7-42bb-8559-15f1aac1d852/scratchpad/testB2; rm -rf $S; mkdir -p $S
sed "s|/home/green/projects/patches/sealed-exam-blockA/work/v4join|$S|g" $F/join/resolve_unknown.py > $S/resolve_unknown.py
sed "s|/home/green/projects/patches/sealed-exam-blockA/work/v4join|$S|g" $F/join/decimals.js > $S/decimals.js
python3 - $S $J <<'PY'
import json, sys
S, J = sys.argv[1:3]
U = json.load(open(f'{J}/unknown_pools.json')); K = json.load(open(f'{J}/unknown_keys.json'))
pick = sorted(K)[:6] + [k for k, _ in sorted(K.items(), key=lambda x: x[1][5])[:6]]   # 6 by id + the 6 earliest Initialize blocks (a long walk back)
json.dump({k: U[k] for k in pick}, open(f'{S}/unknown_pools.json', 'w'))
D = json.load(open(f'{J}/decimals.json'))
toks = [a for a in sorted(D['dec']) if D['dec'][a] is not None][:6]
json.dump([[a, 1] for a in toks], open(f'{S}/addr_toks.json', 'w')); json.dump([], open(f'{S}/addr_quotes.json', 'w'))
json.dump(dict(pick=pick, toks=toks), open(f'{S}/inputs.json', 'w'))
PY
(cd $S && python3 resolve_unknown.py) > $S/resolve.log 2>&1; echo "resolve exit $?"
(cd $S && node decimals.js $S/addr_quotes.json $S/addr_toks.json) > $S/decimals.log 2>&1; echo "decimals exit $?"
python3 - $S $J <<'PY'
import json, sys
S, J = sys.argv[1:3]
I = json.load(open(f'{S}/inputs.json')); K0 = json.load(open(f'{J}/unknown_keys.json')); K1 = json.load(open(f'{S}/unknown_keys.json'))
D0 = json.load(open(f'{J}/decimals.json')); D1 = json.load(open(f'{S}/decimals.json'))
ok_k = all(K1.get(p) == K0[p] for p in I['pick']); ok_d = all(D1['dec'].get(a) == D0['dec'][a] for a in I['toks'])
print(json.dumps(dict(resolve_pools=len(I['pick']), resolve_identical_to_0927=ok_k, decimals_tokens=len(I['toks']), decimals_identical_to_0927=ok_d)))
print('TEST B2', 'PASS' if ok_k and ok_d else 'FAIL')
PY
rm -rf $S
