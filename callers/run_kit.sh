#!/bin/bash
# run_kit.sh — run the callers engine (engine/engine_fast.py) from this kit.
#   EDGE_KIT_ROOT=/path/to/edge-hunt-kit bash run_kit.sh [LAST_DAY]
#   LAST_DAY omitted = "full" run to 2026-09-26 (the engine's own name for it); LAST_DAY < 2026-09-26 = smoke (outputs *_smoke*).
#   FAST_TPS (default 1.5,1.25,2.0), FAST_TAG (default r1), FAST_DELAYS (default 5,15,30,60) pass through to engine_fast.py.
# Every CALLERS_* path can be overridden; the defaults point at the edge-hunt-kit layout after its kit/setup.sh.
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd); E=$K/engine
: "${EDGE_KIT_ROOT:?set EDGE_KIT_ROOT to the edge-hunt-kit folder (after its kit/setup.sh)}"
export CALLERS_TAPE_ROOT=${CALLERS_TAPE_ROOT:-$EDGE_KIT_ROOT/tape/v23}                    # holds archive/<month>/tape-*.ndjson.gz
export CALLERS_TAPE_LIVE=${CALLERS_TAPE_LIVE:-$E/empty_dir}                             # uncompressed live tape-*.ndjson (none in the kit)
export CALLERS_V4_OUT=${CALLERS_V4_OUT:-$EDGE_KIT_ROOT/patches/v4-join-2026-09-27/out}  # v4-swaps-<day>.ndjson.gz
export CALLERS_BF_DIR=${CALLERS_BF_DIR:-$E/empty_dir}                                   # V4 backfill join 07-20..09-11 (NOT released)
export CALLERS_BIRTHS=${CALLERS_BIRTHS:-$E/inputs/births_min.ndjson}
export CALLERS_TOK_BIRTHS=${CALLERS_TOK_BIRTHS:-$E/inputs/token_births_empty.json}
export CALLERS_EDGE_PATCHES=${CALLERS_EDGE_PATCHES:-$EDGE_KIT_ROOT/patches}             # used by costs.py (analysis step) only
mkdir -p "$E/empty_dir"
[ -f "$E/poolfee.tsv" ] || gzip -dc "$E/inputs/poolfee.tsv.gz" > "$E/poolfee.tsv"
[ -f "$CALLERS_BIRTHS" ] || gzip -dc "$E/inputs/births_min.ndjson.gz" > "$CALLERS_BIRTHS"
command -v pigz >/dev/null || { echo "pigz is required (the engine reads .gz tape through it)"; exit 2; }
cd "$E"
export FAST_TPS=${FAST_TPS:-1.5,1.25,2.0} FAST_TAG=${FAST_TAG:-r1}
exec nice -n 10 python3 engine_fast.py "$@"
