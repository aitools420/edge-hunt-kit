#!/bin/bash
# cleanup_intermediates.sh — deletes the tests' BIG intermediates (joined V4 days, cut copies, full tables, meta.json, engine outputs,
# scratch), keeping the engine outputs, every log, state file, statistic, check result and report. Only paths under tests/ are touched.
set -u
W=/home/green/projects/patches/sealed-exam-blockA/tests/testB/tree/work
du -sh $W 2>/dev/null
rm -rf $W/v4join/out $W/v4join/shards $W/v4join/in $W/scratch $W/tape
rm -f $W/v4join/meta.json $W/v4join/decimals.json $W/v4join/unknown_keys*.json $W/v4join/unknown_pools*.json $W/v4join/addr_*.json
rm -f $W/tables/*_full.tsv $W/tables/tokmeta.tsv
du -sh $W 2>/dev/null
