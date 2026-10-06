#!/bin/bash
# drive_proof.sh — Option A proof runs on the OPEN days 09-08..09-26 (seal_guard preloaded on every run; 09-27 tables).
set -u
F=/home/green/projects/patches/sealed-exam-blockA; P=$F/proof; IN=/home/green/projects/patches/twinfix-2026-10-05/inputs
G=$F/tools/seal_guard.js; R=$F/tools/run_engine.sh; LOG=$P/runlogs/driver.log; mkdir -p $P/out $P/runlogs
run() { local L=$1 E=$2; shift 2; echo "$(date -u +%FT%TZ) start $L" >> $LOG
  if bash $R $L $E $IN/meta.tsv $IN/scam.tsv $IN/poolfee.tsv $P/out $P/runlogs $G "$@"; then echo "$(date -u +%FT%TZ) OK $L" >> $LOG; else echo "$(date -u +%FT%TZ) FAIL $L" >> $LOG; fi; }
echo "$(date -u +%FT%TZ) proof driver start" >> $LOG
run st_A_noskip_batch $P/engine_st_A_noskip.js
run st_A_batch $F/engines/engine_st_A.js
nice -n 19 node $P/rng_replay_A.js $P/out/st_A_noskip_batch.ndjson.gz '*' $P/out/st_A_noskip_batch.ALL.replay.json >> $LOG 2>&1
run st_A_replay $P/engine_st_A_h.js RNG_REPLAY=$P/out/st_A_noskip_batch.ALL.replay.json
run st_A_alone $P/engine_st_A_h.js ONLY_CELLS=C2P
run grid_A_noskip_batch $P/engine_grid_A_noskip.js
run grid_A_batch $F/engines/engine_grid_A.js
nice -n 19 node $P/rng_replay_A.js $P/out/grid_A_noskip_batch.ndjson.gz '*' $P/out/grid_A_noskip_batch.ALL.replay.json >> $LOG 2>&1
run grid_A_replay $P/engine_grid_A_h.js RNG_REPLAY=$P/out/grid_A_noskip_batch.ALL.replay.json
run grid_A_alone $P/engine_grid_A_h.js ONLY_CELLS=D25L48
echo "$(date -u +%FT%TZ) proof driver done" >> $LOG
