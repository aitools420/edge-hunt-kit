#!/bin/bash
# make_pins.sh — writes, in this order:
#   pins/block_days.tsv : the registered rows of the 20 block days (BLOCK_DAYS of run_exam.sh x {v2v3-tape, v4-wide}) copied verbatim from
#                         SEALED-HOLDOUT/tape-hashes.tsv; exactly ONE row per (day, feed) or it stops. run_exam.sh verifies the block days
#                         against THIS pinned file, never against the appendable registry (pond #330 H1).
#   pins/code.sha256    : every code file the exam runs, incl. the two frozen analyzers. run_exam.sh is NOT in it (no circularity: the
#                         runner holds the pin files' hashes, the pin files never hold the runner's).
#   pins/inputs.sha256  : every OPEN input the exam reads as it is: the 09-27 tables, the 09-27 join's decimals / unknown keys / warm-up V4
#                         days (V4_OPEN_DAYS of run_exam.sh), the hole and backfill tapes, the open-day raw-file pins, the orientation pin
#                         and pins/block_days.tsv.
#   run_exam.sh         : PIN_CODE_SHA / PIN_INPUTS_SHA / PIN_BLOCK_SHA := the sha256 of the three files above (the runner refuses at step 1
#                         unless the pin files hash to them, pond #330 H1).
# Run once the code is final; then the sha256 of run_exam.sh and of the three pin files go into the register entry.
set -eu
R=/home/green/projects/patches/sealed-exam-blockA; cd $R
REG=/home/green/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv
BLOCK_DAYS=$(sed -n 's/^BLOCK_DAYS="\([^"]*\)".*/\1/p' run_exam.sh); V4_OPEN_DAYS=$(sed -n 's/^V4_OPEN_DAYS="\([^"]*\)".*/\1/p' run_exam.sh)
[ -n "$BLOCK_DAYS" ] && [ -n "$V4_OPEN_DAYS" ] || { echo "make_pins: BLOCK_DAYS / V4_OPEN_DAYS not found in run_exam.sh"; exit 2; }
python3 - "$REG" pins/block_days.tsv $BLOCK_DAYS <<'PY'
import sys
reg, out, days = sys.argv[1], sys.argv[2], sys.argv[3:]
L = open(reg).read().split('\n'); hdr = L[0]
assert hdr.split('\t')[:5] == ['computed_utc', 'day', 'feed', 'sha256_of_uncompressed_content', 'bytes_uncompressed'], 'unexpected registry header'
rows = {}
for ln in L[1:]:
    a = ln.split('\t')
    if len(a) >= 5 and a[1] in days and a[2] in ('v2v3-tape', 'v4-wide'): rows.setdefault((a[1], a[2]), []).append(ln)
bad = [(d, f, len(rows.get((d, f), []))) for d in days for f in ('v2v3-tape', 'v4-wide') if len(rows.get((d, f), [])) != 1]
if bad: sys.exit(f'make_pins: each block day needs exactly ONE registered row per feed: {bad}')
open(out, 'w').write(hdr + '\n' + ''.join(rows[(d, f)][0] + '\n' for d in days for f in ('v2v3-tape', 'v4-wide')))
print('pins/block_days.tsv:', 2 * len(days), 'rows,', days[0], '..', days[-1])
PY
CODE="engines/engine_st_exam.js engines/engine_grid_exam.js engines/engine_st_exam_h.js engines/engine_grid_exam_h.js engines/v4tape_exam.js engines/guard.js engines/guard_test.js
 tools/exam_guard.js tools/run_engine.sh tools/gate.sh tools/stats_rule.py tools/tables.py tools/cut_tape.py tools/days.py tools/report.py tools/exam_checks.py
 builders/tokmeta.py builders/mkmeta.py builders/mkpoolfee.py
 join/meta.js join/unknown_pools.js join/resolve_unknown.py join/anchors.py join/decimals.js join/pools.js join/pass1.js join/finalize.js join/cut_v4.js join/fetch_ethusd.py join/glue.py join/addr_lists.js"
: > pins/code.sha256
for f in $CODE; do sha256sum $R/$f >> pins/code.sha256; done
sha256sum /home/green/projects/patches/blood-stress-2026-09-27/analyze_st.py /home/green/projects/patches/blood-grid-depth-history-2026-09-27/analyze_grid.py >> pins/code.sha256
I=/home/green/projects/patches/twinfix-2026-10-05/inputs; J=/home/green/projects/patches/v4-join-2026-09-27
V4F=""; for d in $V4_OPEN_DAYS; do V4F="$V4F $J/out/v4-swaps-$d.ndjson.gz"; done
sha256sum $I/meta.tsv $I/scam.tsv $I/poolfee.tsv $J/decimals.json $J/unknown_keys.json $V4F \
  /home/green/noxabot/logs/uniswap-v4-tape-hole.ndjson /home/green/noxabot/logs/uniswap-v4-tape-backfill.ndjson $R/pins/open_days.tsv $R/join/orient_0927.json $R/pins/block_days.tsv > pins/inputs.sha256
for kv in PIN_CODE_SHA:pins/code.sha256 PIN_INPUTS_SHA:pins/inputs.sha256 PIN_BLOCK_SHA:pins/block_days.tsv; do
  k=${kv%%:*}; h=$(sha256sum ${kv#*:} | cut -c1-64)
  [ "$(grep -c "^$k=[0-9a-f]\{64\} " run_exam.sh)" = 1 ] || { echo "make_pins: $k not found exactly once in run_exam.sh"; exit 2; }
  sed -i "s/^$k=[0-9a-f]\{64\} /$k=$h /" run_exam.sh
  grep -q "^$k=$h " run_exam.sh || { echo "make_pins: $k was not written"; exit 2; }
  echo "$k=$h (${kv#*:})"
done
wc -l pins/code.sha256 pins/inputs.sha256 pins/block_days.tsv
echo "run_exam.sh sha256 $(sha256sum run_exam.sh | cut -c1-64)"
