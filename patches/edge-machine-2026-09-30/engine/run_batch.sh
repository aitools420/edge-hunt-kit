#!/bin/bash
# run_batch.sh <cells.json> <outdir> — EDGE MACHINE v1: the WHOLE pipeline for one batch, frozen engine + one cost model.
#   0 verify MANIFEST.json (REFUSES on any code / input / external / data mismatch)  1 prepare (validate cells, split passes)
#   2 decompress + verify the frozen input tables   3 guard test (DATA GATE G3)   4 engine passes, ONE at a time, each behind the A4 gate
#   5 hop tables (A4)   6 batch cost table = frozen v1 table + touched pools (A4)   7 reduce every pass (A4)   8 analyze -> results.json + trades
# Env: PASS_NEED (MB, default 2800) · KEEP_INPUTS=1 keeps <outdir>/in · STOP_DAY=YYYY-MM-DD (smoke only; results then cover fewer days).
# Research only: reads the tape, writes only <outdir>. Never kills another process; the watchdog stops only its own engine by exact PID.
set -u; : "${KIT_ROOT:?set KIT_ROOT to the kit folder (README)}"; export KIT_ROOT NODE_OPTIONS="--require $KIT_ROOT/kit/kitpath.js${NODE_OPTIONS:+ $NODE_OPTIONS}"   # KIT
E=$(dirname "$(readlink -f "$0")"); CELLS=$(readlink -f "$1"); O=$(readlink -m "$2"); NEED=${PASS_NEED:-2800}
mkdir -p $O/runlogs $O/in; export A4_LOG=$O/runlogs/a4.log; export PYTHONDONTWRITEBYTECODE=1
log() { echo "$(date -u +%FT%TZ) $*" | tee -a $O/runlogs/batch.log; }
fail() { log "FAILED: $*"; exit 1; }
[ -n "${STOP_DAY:-}" ] && export STOP_DAY && log "SMOKE: STOP_DAY=$STOP_DAY"
log "batch start: cells $CELLS -> $O"
python3 $E/verify_manifest.py --quiet >> $O/runlogs/batch.log 2>&1 || { log "REFUSED: MANIFEST mismatch (see batch.log)"; exit 2; }
cp $CELLS $O/cells.input.json; cp $E/MANIFEST.json $O/MANIFEST.used.json
python3 $E/prepare_v1.py $CELLS $O >> $O/runlogs/batch.log 2>&1 || fail "cells.json refused (see batch.log)"
for f in meta scam poolfee_lf creators poolquote; do zcat $E/inputs/$f.tsv.gz > $O/in/$f.tsv || fail "decompress $f"; done
python3 $E/verify_manifest.py --quiet --inputs $O/in >> $O/runlogs/batch.log 2>&1 || { log "REFUSED: decompressed inputs mismatch"; exit 2; }
( cd $E && node guard_test.js ) > $O/runlogs/guard_test.log 2>&1; grep -q "NEW GUARD: ALL REQUIRED TESTS PASS" $O/runlogs/guard_test.log || fail "guard test (G3)"
for pf in $O/passes/p*.txt; do
  N=$(basename $pf .txt); log "engine pass $N ($(wc -l < $pf) cells)"
  bash $E/run_pass_v1.sh $O $N $NEED || fail "engine pass $N"
done
PASSES=$(ls $O/p[0-9][0-9].ndjson.gz)
bash $E/a4.sh hop 1500; log "hop tables"
nice -n 19 ionice -c3 python3 $E/build_hop_v1.py $O/hop $O/in/poolquote.tsv $PASSES > $O/runlogs/build_hop.log 2>&1 || fail "hop tables"
bash $E/a4.sh costs 1000; log "cost table"
nice -n 19 ionice -c3 python3 $E/pool_costs_v1.py $O/pool_costs.json $O/in/poolfee_lf.tsv $PASSES > $O/runlogs/pool_costs.log 2>&1 || fail "cost table"
for p in $PASSES; do
  N=$(basename $p .ndjson.gz); bash $E/a4.sh "reduce $N" 1500; log "reduce $N"
  POOL_COSTS=$O/pool_costs.json HOP_DIR=$O/hop /usr/bin/time -v nice -n 19 ionice -c3 python3 $E/reduce_v1.py $p $O/$N.pkl > $O/runlogs/reduce_$N.log 2>&1 || fail "reduce $N"
done
bash $E/a4.sh analyze 1000; log "analyze"
nice -n 19 python3 $E/analyze_v1.py $O > $O/runlogs/analyze.log 2>&1 || fail "analyze"
[ "${KEEP_INPUTS:-0}" = 1 ] || rm -f $O/in/meta.tsv $O/in/scam.tsv $O/in/poolfee_lf.tsv $O/in/creators.tsv
log "DONE: $O/results.json + $O/trades.ndjson.gz ($(grep -c . $O/runlogs/analyze.log) lines of summary in runlogs/analyze.log)"
