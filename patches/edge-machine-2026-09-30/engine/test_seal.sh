#!/bin/bash
# test_seal.sh — EDGE MACHINE v1: the SEAL refusals still fire (SEALED-HOLDOUT/README.md: nothing with ts >= 2026-09-27T00:00Z is read).
# Cheap: no engine pass over real data. Each test must REFUSE; the script exits non-zero if any does not.
#  1 engine_v1.js with STOP_DAY=2026-09-27 -> "sealed day in RUN" before any row is read
#  2 v4tape.readDay('2026-09-27') -> refused by the reader
#  3 reduce_v1.py on a synthetic pass file holding one row with exitTs >= seal -> "sealed row"
#  4 analyze-stage per-trade writer guard: grep'd in analyze_v1.py (the output check is code, exercised by every batch)
#  5 hop.build() on a synthetic row with ts >= seal -> "sealed row"
#  6 (not a seal test, same harness) engine_v1.js refuses an unknown cell dial
E=$(dirname "$(readlink -f "$0")"); T=$(mktemp -d); ok=0; bad=0; export PYTHONDONTWRITEBYTECODE=1; : "${KIT_ROOT:?set KIT_ROOT to the kit folder (README)}"; export KIT_ROOT NODE_OPTIONS="--require $KIT_ROOT/kit/kitpath.js${NODE_OPTIONS:+ $NODE_OPTIONS}"   # KIT
pass() { echo "PASS  $1"; ok=$((ok + 1)); }; failt() { echo "FAIL  $1"; bad=$((bad + 1)); }
echo '{"cells":[{"id":"X","params":{"dip":0.25}}]}' > $T/c.json
( cd $E && STOP_DAY=2026-09-27 timeout 120 node engine_v1.js $T/o.gz /dev/null /dev/null /dev/null /dev/null $T/c.json ) > $T/1.log 2>&1
grep -q "sealed day in RUN" $T/1.log && pass "1 engine refuses a sealed RUN day" || { failt "1 engine sealed day"; tail -3 $T/1.log; }
node -e "const V=require(process.env.KIT_ROOT+'/patches/v4-join-2026-09-27/v4tape.js');(async()=>{try{for await (const r of V.readDay('2026-09-27')){};console.log('READ')}catch(e){console.log('REFUSED',e.message)}})()" > $T/2.log 2>&1
grep -q REFUSED $T/2.log && pass "2 v4tape refuses a sealed day" || failt "2 v4tape sealed day"
python3 - $T <<'PYEOF'
import gzip, json, sys
row = dict(u=1, kind='S', cell='X', pair=1, tok='0xabc', T=1790000000, sigTs=1790000000, entryTs=1790000060, exitTs=1790467300, reason='time')
with gzip.open(sys.argv[1] + '/p.ndjson.gz', 'wt') as f: f.write(json.dumps(row) + '\n')
PYEOF
cp $E/pool_costs_v1.json $T/pc.json
mkdir -p $T/hop; python3 -c "
import sys, pickle; sys.path.insert(0, '$E'); import hop
pickle.dump(dict(tables={}, stat={}), open('$T/hop/hop_tables.pkl', 'wb')); open('$T/hop/poolquote.tsv', 'w').write('')"
POOL_COSTS=$T/pc.json HOP_DIR=$T/hop python3 $E/reduce_v1.py $T/p.ndjson.gz $T/p.pkl > $T/3.log 2>&1
grep -q "sealed row" $T/3.log && pass "3 reducer refuses a sealed row" || { failt "3 reducer sealed row"; tail -3 $T/3.log; }
grep -q "SEALED ROW in the per-trade output - refused" $E/analyze_v1.py && pass "4 analyze has the per-trade seal guard" || failt "4 analyze guard"
python3 -c "
import sys, gzip, json; sys.path.insert(0, '$E'); import hop
with gzip.open('$T/h.ndjson.gz', 'wt') as f: f.write(json.dumps(dict(ts=1790467200, pool='0x1', tok='0x2')) + '\n')
try: hop.build(['$T/h.ndjson.gz'], {'0x1': dict(tok='0x2', q='WETH', fee=3000, hook=None)}, '$T/h.pkl'); print('READ')
except RuntimeError as e: print('REFUSED', e)" > $T/5.log 2>&1
grep -q REFUSED $T/5.log && pass "5 hop.build refuses a sealed row" || failt "5 hop sealed row"
echo '{"cells":[{"id":"Y","params":{"dipp":0.25}}]}' > $T/c2.json
( cd $E && timeout 120 node engine_v1.js $T/o2.gz /dev/null /dev/null /dev/null /dev/null $T/c2.json ) > $T/6.log 2>&1
grep -q "unknown cell dial 'dipp'" $T/6.log && pass "6 engine refuses an unknown dial" || failt "6 unknown dial"
rm -rf $T; echo "seal tests: $ok pass, $bad fail"; [ $bad -eq 0 ]
