#!/bin/bash
# run_testB.sh — Test B: the test tree's run_exam.sh end to end on open days (queued after Test A/D: one engine at a time), then the checks.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; T=$F/tests/testB
until grep -q 'proof driver done' $F/proof/runlogs/driver.log 2>/dev/null; do sleep 60; done
echo "$(date -u +%FT%TZ) Test B start" >> $T/testB.log
bash $T/tree/run_exam.sh >> $T/testB.log 2>&1; echo "$(date -u +%FT%TZ) run_exam.sh (test tree) exit $?" >> $T/testB.log
nice -n 19 python3 $T/check_testB.py > $T/check_testB.out 2>&1; echo "$(date -u +%FT%TZ) check_testB exit $?" >> $T/testB.log
