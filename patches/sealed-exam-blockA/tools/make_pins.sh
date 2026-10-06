#!/bin/bash
# make_pins.sh — writes pins/code.sha256 (every code file the exam runs, incl. the two frozen analyzers) and pins/inputs.sha256 (every
# OPEN input the exam reads as it is: the 09-27 tables, the 09-27 join's decimals / unknown keys / warm-up V4 days, the hole and backfill
# tapes, and the open-day raw-file pins). run_exam.sh refuses if any of these hashes differs. Run once the code is final; then the
# sha256 of the two pin files and of run_exam.sh go into the register entry.
set -eu
R=/home/green/projects/patches/sealed-exam-blockA; cd $R
CODE="engines/engine_st_exam.js engines/engine_grid_exam.js engines/engine_st_exam_h.js engines/engine_grid_exam_h.js engines/v4tape_exam.js engines/guard.js engines/guard_test.js
 tools/exam_guard.js tools/run_engine.sh tools/gate.sh tools/stats_rule.py tools/tables.py tools/cut_tape.py tools/days.py tools/report.py
 builders/tokmeta.py builders/mkmeta.py builders/mkpoolfee.py
 join/meta.js join/unknown_pools.js join/resolve_unknown.py join/anchors.py join/decimals.js join/pools.js join/pass1.js join/finalize.js join/cut_v4.js join/fetch_ethusd.py join/glue.py join/addr_lists.js"
: > pins/code.sha256
for f in $CODE; do sha256sum $R/$f >> pins/code.sha256; done
sha256sum /home/green/projects/patches/blood-stress-2026-09-27/analyze_st.py /home/green/projects/patches/blood-grid-depth-history-2026-09-27/analyze_grid.py >> pins/code.sha256
I=/home/green/projects/patches/twinfix-2026-10-05/inputs; J=/home/green/projects/patches/v4-join-2026-09-27
sha256sum $I/meta.tsv $I/scam.tsv $I/poolfee.tsv $J/decimals.json $J/unknown_keys.json $J/out/v4-swaps-2026-09-24.ndjson.gz $J/out/v4-swaps-2026-09-25.ndjson.gz \
  $J/out/v4-swaps-2026-09-26.ndjson.gz /home/green/noxabot/logs/uniswap-v4-tape-hole.ndjson /home/green/noxabot/logs/uniswap-v4-tape-backfill.ndjson $R/pins/open_days.tsv $R/join/orient_0927.json > pins/inputs.sha256
wc -l pins/code.sha256 pins/inputs.sha256
