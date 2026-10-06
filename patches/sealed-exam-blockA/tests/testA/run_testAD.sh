#!/bin/bash
# run_testAD.sh — Test A (exam engines, window constants set back, runner-built tape links) and Test D (one window constant broken).
# Queued after the proof driver (one engine at a time); seal_guard (Block A) preloaded; SEAL_TEST_ROOT adds the link folder to its roots.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; T=$F/tests/testA; IN=/home/green/projects/patches/twinfix-2026-10-05/inputs
G=$F/tools/seal_guard.js; R=$F/tools/run_engine.sh; LOG=$T/testAD.log
until grep -q 'check_testB exit' $F/tests/testB/testB.log 2>/dev/null; do sleep 60; done
echo "$(date -u +%FT%TZ) Test A/D start" >> $LOG
run() { local L=$1 E=$2; bash $R $L $E $IN/meta.tsv $IN/scam.tsv $IN/poolfee.tsv $T/out $T/runlogs $G SEAL_TEST_ROOT=$T/work/tape/ && echo "$(date -u +%FT%TZ) OK $L" >> $LOG || echo "$(date -u +%FT%TZ) FAIL $L" >> $LOG; }
run testA_st $T/tree/engine_st_testA.js
echo "TEST A rule #1 engine: $(bash $T/compare_bytes.sh $T/out/testA_st.ndjson.gz $F/proof/out/st_A_batch.ndjson.gz)" >> $LOG
run testA_grid $T/tree/engine_grid_testA.js
echo "TEST A rule #2 engine: $(bash $T/compare_bytes.sh $T/out/testA_grid.ndjson.gz $F/proof/out/grid_A_batch.ndjson.gz)" >> $LOG
run testD_st $T/tree/engine_st_testD.js
echo "TEST D (mutated FIT0): $(bash $T/compare_bytes.sh $T/out/testD_st.ndjson.gz $F/proof/out/st_A_batch.ndjson.gz)" >> $LOG
echo "$(date -u +%FT%TZ) Test A/D done" >> $LOG
