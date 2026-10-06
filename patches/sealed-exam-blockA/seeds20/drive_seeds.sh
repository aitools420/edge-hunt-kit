#!/bin/bash
# drive_seeds.sh — pond #322 §3 e (promised in forum #324): the Option A engines, exam cell ALONE, on the OPEN days 09-08..09-26 (seal_guard
# preloaded, the 09-27 tables) for SEEDS 20260928..20260946 (20260927 is proof/out/{st,grid}_A_alone). One engine at a time behind the
# box gate (tools/run_engine.sh). Then tools/stats_rule.py per run and summarize.py. Waits for the Test A/D driver first.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; D=$F/seeds20; P=$F/proof; IN=/home/green/projects/patches/twinfix-2026-10-05/inputs
G=$F/tools/seal_guard.js; R=$F/tools/run_engine.sh; LOG=$D/driver.log; mkdir -p $D/out $D/runlogs $D/stats
while pgrep -f "sealed-exam-blockA/tests/testA/run_testAD.sh" > /dev/null; do sleep 120; done
echo "$(date -u +%FT%TZ) seeds driver start" >> $LOG
for s in $(seq 20260928 20260946); do
  for k in st grid; do
    L=${k}_A_alone_s$s; C=$([ $k = st ] && echo C2P || echo D25L48); RULE=$([ $k = st ] && echo 1 || echo 2)
    if [ -s $D/stats/$L.json ]; then continue; fi
    echo "$(date -u +%FT%TZ) start $L" >> $LOG
    if bash $R $L $P/engine_${k}_A_h.js $IN/meta.tsv $IN/scam.tsv $IN/poolfee.tsv $D/out $D/runlogs $G ONLY_CELLS=$C EXAM_SEED=$s; then
      O=$D/out/$L.ndjson.gz; [ -s $O ] || O=$(ls $D/out/$L.ndjson* 2>/dev/null | head -1)
      nice -n 19 python3 $F/tools/stats_rule.py $RULE $O $D/stats/$L.json > /dev/null 2>> $LOG && echo "$(date -u +%FT%TZ) OK $L" >> $LOG || echo "$(date -u +%FT%TZ) STATS FAIL $L" >> $LOG
    else echo "$(date -u +%FT%TZ) FAIL $L" >> $LOG; fi
  done
done
echo "$(date -u +%FT%TZ) seeds driver done" >> $LOG
