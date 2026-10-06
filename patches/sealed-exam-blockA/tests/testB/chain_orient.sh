#!/bin/bash
# chain_orient.sh (2026-10-06): Test B again after the join orientation pin (pond #322 §6 e), then the 20-seed driver resumes.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; T=$F/tests/testB; L=$T/testB.log
while pgrep -f "run_engine.sh st_A_alone_s20260928" > /dev/null; do sleep 30; done
O=$F/seeds20/out/st_A_alone_s20260928.ndjson.gz
[ -s $O ] && nice -n 19 python3 $F/tools/stats_rule.py 1 $O $F/seeds20/stats/st_A_alone_s20260928.json > /dev/null 2>> $F/seeds20/driver.log && echo "$(date -u +%FT%TZ) OK st_A_alone_s20260928 (stats by chain_orient)" >> $F/seeds20/driver.log
echo "$(date -u +%FT%TZ) === Test B RERUN after the 09-27 orientation pin (join/orient_0927.json) ===" >> $L
python3 $T/make_testB.py >> $L 2>&1
bash $T/run_testB.sh
bash $F/seeds20/drive_seeds.sh
