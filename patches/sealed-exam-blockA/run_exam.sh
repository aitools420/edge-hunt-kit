#!/bin/bash
# run_exam.sh — the ONE-SHOT sealed exam of Block A (rules #1 C2P and #2 D25L48), end to end, writing report.md.
# Register: patches/SEALED-HOLDOUT/README.md (frozen rules, Holm k = 2, BLOCK EDGES, ENGINE FIX, and this runner's own entry).
# Usage (once, after 2026-10-07T00:00:00Z):   bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh
# It REFUSES (exit 2) before the instant, on any code or input hash that differs from what is registered, on a closed block day whose
# content differs from tape-hashes.tsv, and on any table row known on 09-27 that a rebuild would change. It WAITS (logged) until the
# raw files that hold the block's last hour have passed the cut by a safe margin. It can be re-run after an interruption: finished
# steps are skipped (their outputs re-verified), an engine run with a good output is not run again; NO setting can change.
set -u -o pipefail
# ======================= constants (the exam) =======================
ROOT=/home/green/projects/patches/sealed-exam-blockA
WORK=$ROOT/work
REG_TSV=/home/green/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv     # sealed-day commitments (coordinator); the runner appends the two cut rows
CUT=1791331200                 # 2026-10-07T00:00:00Z: Block A's data end and the earliest start (Block B begins here; nothing at/after it is read)
READY_AT=1791342000            # CUT + 3 h: by then the raw files holding the last hour have passed the cut + margin (checked again by the cut tools)
CUT_DAY=2026-10-07             # day files that hold the block's last hour: V2/V3 tape from ~23:00Z (R-0109), V4-wide from ~23:42Z; read CUT at CUT
TAPE_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"                     # V2/V3 warm-up days (open; pinned in pins/open_days.tsv)
BLOCK_DAYS="2026-09-27 2026-09-28 2026-09-29 2026-09-30 2026-10-01 2026-10-02 2026-10-03 2026-10-04 2026-10-05 2026-10-06"   # sealed; tape-hashes.tsv
WIDE_OPEN_DAYS="2026-09-25 2026-09-26"                               # V4-wide days the join reads before the block (open; pinned)
V4_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"                      # warm-up V4 days the engines read from the 09-27 join (pinned files)
JOIN0_TS=1790294400            # 2026-09-25T00:00:00Z: the join's first day (= join/pass1.js JOIN0)
ETH_FROM=1790208000            # 2026-09-24T00:00:00Z: first ETH/USD point fetched (hourly, CoinGecko, cut at CUT)
TABLE_CUTOFF=1791244800        # 2026-10-06T00:00:00Z: meta / poolfee hold coins and pools born before it (unknown birth kept, as on 09-27)
CONSIST_DAYS="2026-09-25 2026-09-26"                                 # joined days compared with the 09-27 join's own files (plumbing check)
SEEDS="20260927 20260928 20260929 20260930 20260931 20260932 20260933 20260934 20260935 20260936 20260937 20260938 20260939 20260940 20260941 20260942 20260943 20260944 20260945 20260946"
LABEL_COMMIT=e5c559ec53baf0ee12eef6fb84587e277ea588f6                # noxabot lib/launchpads.js: last commit before 2026-09-27T00:00Z
LABEL_SHA=1b939aea01899089285dfbb47963eed740aeda58353fc60e5824e9adffcff592
OLD=/home/green/projects/patches/twinfix-2026-10-05/inputs          # the 09-27 tables (meta 45af2cf8…, scam 9988ebfa…, poolfee 5328cf75…)
OLDJOIN=/home/green/projects/patches/v4-join-2026-09-27             # the 09-27 join (decimals.json, unknown_keys.json, out/ warm-up days)
SCAM_SRC="/home/green/noxabot/state/safety-cache.json /home/green/noxabot/state/tokengate-cache.json /home/green/noxabot/state/redteam-scores.json"
SEAL_A=1790467200              # 2026-09-27T00:00:00Z: the scam table's three sources must be older than this
# ====================================================================
# ---- 0. the clock: nothing is created, read or hashed before the instant ----
NOW=$(date -u +%s); [ "$NOW" -ge "$CUT" ] || { echo "$(date -u +%FT%TZ) REFUSED: it is $(date -u +%FT%TZ): the exam may not start before $(date -u -d @$CUT +%FT%TZ)"; exit 2; }
export EXAM_SCRATCH=$WORK/scratch
V4J=$WORK/v4join; TBL=$WORK/tables; ST=$WORK/state; OUT=$WORK/out; RL=$WORK/runlogs; STATS=$WORK/stats
mkdir -p $WORK $V4J/in/v4-wide $TBL $ST $OUT $RL $STATS $EXAM_SCRATCH $WORK/tape/robinhood-tape $WORK/tape/archive
LOG=$RL/exam.log
exec > >(tee -a $LOG) 2>&1
say() { echo "$(date -u +%FT%TZ) $*"; }
refuse() { say "REFUSED: $*"; echo "REFUSED $(date -u +%FT%TZ): $*" >> $ST/REFUSED; exit 2; }
done_() { [ -f $ST/$1.done ]; }
mark() { date -u +%FT%TZ > $ST/$1.done; }
exec 9> $WORK/.lock; flock -n 9 || refuse "another run_exam.sh is already running on $WORK"
say "run_exam.sh start; sha256 $(sha256sum $0 | cut -c1-64)"
# ---- 1. code and open inputs: every file hashed, against pins/ (registered) ----
sha256sum --quiet -c $ROOT/pins/code.sha256 > $RL/pins_code.check 2>&1 || refuse "code hash mismatch: $(grep -v ': OK' $RL/pins_code.check | head -5 | tr '\n' ' ')"
sha256sum --quiet -c $ROOT/pins/inputs.sha256 > $RL/pins_inputs.check 2>&1 || refuse "input hash mismatch: $(grep -v ': OK' $RL/pins_inputs.check | head -5 | tr '\n' ' ')"
say "1 code and open inputs: $(wc -l < $ROOT/pins/code.sha256) code files and $(wc -l < $ROOT/pins/inputs.sha256) inputs match pins/"
(cd $ROOT/engines && node guard_test.js > $RL/guard_test.log 2>&1); echo $? > $ST/G3.rc
[ "$(cat $ST/G3.rc)" = 0 ] || refuse "guard_test.js failed (G3)"
for f in $SCAM_SRC; do m=$(stat -c %Y $f); [ "$m" -lt "$SEAL_A" ] || refuse "scam source $f changed after 2026-09-27T00:00Z (mtime $(date -u -d @$m +%FT%TZ)): stop and report"; done
say "1 G3 guard test PASS; the scam table's three sources predate the seal"
# ---- 1b. wait until READY_AT (cut + 3 h): the raw files holding the last hour must be past the cut + margin; this also leaves time to
#      register the last closed days (10-05, 10-06) in tape-hashes.tsv before step 2 checks them ----
while [ "$(date -u +%s)" -lt "$READY_AT" ]; do say "1b waiting until $(date -u -d @$READY_AT +%FT%TZ) (raw files must pass the cut + margin; last days registered)"; sleep 600; done
# ---- 2. closed days against their registered hashes (sealed: tape-hashes.tsv; open: pins/open_days.tsv) ----
if ! done_ days_verified; then
  python3 $ROOT/tools/days.py verify tape $ST/tape_block.json $REG_TSV $BLOCK_DAYS || refuse "a sealed V2/V3 tape day is missing, ambiguous or differs from tape-hashes.tsv"
  python3 $ROOT/tools/days.py verify wide $ST/wide_block.json $REG_TSV $BLOCK_DAYS || refuse "a sealed V4-wide day is missing, ambiguous or differs from tape-hashes.tsv"
  python3 $ROOT/tools/days.py verify tape $ST/tape_open.json $ROOT/pins/open_days.tsv $TAPE_OPEN_DAYS || refuse "an open V2/V3 warm-up day differs from its pin"
  python3 $ROOT/tools/days.py verify wide $ST/wide_open.json $ROOT/pins/open_days.tsv $WIDE_OPEN_DAYS || refuse "an open V4-wide day differs from its pin"
  mark days_verified
fi
say "2 every closed day verified (block days against tape-hashes.tsv, open days against pins)"
# ---- 3. the block's anchors (block -> time, public RPC) and ETH/USD (CoinGecko hourly, cut at CUT) ----
if ! done_ net; then
  python3 $ROOT/join/anchors.py > $RL/anchors.log 2>&1 || refuse "anchors fetch failed (see $RL/anchors.log)"
  last=$(tail -1 $V4J/anchors.tsv | cut -f2); [ "$last" -ge $((CUT + 7200)) ] || refuse "anchors end at $last, not 2 h past the cut"
  python3 $ROOT/join/fetch_ethusd.py $V4J/ethusd_coingecko.json $ETH_FROM $CUT > $RL/ethusd.log 2>&1 || refuse "ETH/USD fetch failed or incomplete: $(cat $RL/ethusd.log)"
  mark net
fi
say "3 anchors $(wc -l < $V4J/anchors.tsv) (last $(date -u -d @$(tail -1 $V4J/anchors.tsv | cut -f2) +%FT%TZ)); ETH/USD $(cat $RL/ethusd.log)"
# ---- 4. the cuts: the 10-07 V2/V3 file, the 10-07 V4-wide file and the locked V4 tape, rows < CUT only; hashed; two rows appended ----
if ! done_ cuts; then
  for i in $(seq 1 72); do
    T7=$(python3 -c "
import glob; d='$CUT_DAY'; W='/home/green/.openclaw/workspace/wick-engine/logs'
a=sorted(glob.glob(W+'/archive/*/tape-'+d+'.ndjson.gz')); l=W+'/robinhood-tape/tape-'+d+'.ndjson'
import os; print(' '.join(a+([l] if os.path.exists(l) else [])))")
    [ -n "$T7" ] || { say "4 no $CUT_DAY tape file yet; wait 600 s"; sleep 600; continue; }
    [ "$(echo $T7 | wc -w)" = 1 ] || refuse "the $CUT_DAY tape has more than one part: $T7"
    python3 $ROOT/tools/cut_tape.py $WORK/tape/robinhood-tape/tape-$CUT_DAY.ndjson $CUT $T7 > $ST/cut_tape.json; r1=$?
    W7=/home/green/noxabot/logs/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson
    [ -f $W7 ] && { node $ROOT/join/cut_v4.js $V4J/anchors.tsv $W7 $V4J/in/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson $CUT $JOIN0_TS > $ST/cut_wide.json; r2=$?; } || r2=3
    node $ROOT/join/cut_v4.js $V4J/anchors.tsv /home/green/noxabot/logs/uniswap-v4-tape.ndjson $V4J/in/uniswap-v4-tape.ndjson $CUT $JOIN0_TS > $ST/cut_lock.json; r3=$?
    say "4 cut attempt $i: tape rc $r1, wide rc $r2, locked tape rc $r3"
    [ $r1 = 0 ] && [ $r2 = 0 ] && [ $r3 = 0 ] && break
    { [ $r1 != 3 ] && [ $r1 != 0 ]; } || { [ $r2 != 3 ] && [ $r2 != 0 ]; } || { [ $r3 != 3 ] && [ $r3 != 0 ]; } && refuse "a cut tool failed (rc $r1/$r2/$r3)"
    sleep 600
  done
  [ $r1 = 0 ] && [ $r2 = 0 ] && [ $r3 = 0 ] || refuse "the raw files never passed the cut + margin"
  python3 - "$REG_TSV" "$CUT_DAY" "$CUT" "$ST/cut_tape.json" "$ST/cut_wide.json" <<'PY' || refuse "could not append the cut rows to tape-hashes.tsv"
import json, sys, datetime
tsv, day, cut, a, b = sys.argv[1:6]
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
A, B = json.load(open(a)), json.load(open(b))
with open(tsv, 'a') as o:
    o.write(f"{now}\t{day}\tv2v3-tape-cutA\t{A['sha256']}\t{A['bytes']}\t{' + '.join(A['inputs'])} rows ts<{cut} (Block A exam cut, run_exam.sh)\n")
    o.write(f"{now}\t{day}\tv4-wide-cutA\t{B['sha256']}\t{B['bytes']}\t{B['in']} rows t<{cut} by the exam anchors (Block A exam cut, run_exam.sh)\n")
print('appended')
PY
  mark cuts
fi
say "4 cuts: tape $(cut -c1-200 $ST/cut_tape.json); wide $(cut -c1-200 $ST/cut_wide.json); locked $(cut -c1-200 $ST/cut_lock.json)"
# ---- 5. tables: meta.tsv and poolfee.tsv rebuilt (coins / pools born before TABLE_CUTOFF; every 09-27 row kept verbatim), scam.tsv as on 09-27 ----
if ! done_ tables; then
  c=$(git -C /home/green/noxabot log --before=2026-09-27T00:00:00Z -1 --format=%H -- lib/launchpads.js); [ "$c" = "$LABEL_COMMIT" ] || refuse "launchpads.js last pre-seal commit is $c, not $LABEL_COMMIT"
  git -C /home/green/noxabot show $LABEL_COMMIT:lib/launchpads.js > $TBL/launchpads_e5c559ec.js || refuse "git show failed"
  [ "$(sha256sum $TBL/launchpads_e5c559ec.js | cut -c1-64)" = "$LABEL_SHA" ] || refuse "launchpads.js at $LABEL_COMMIT does not hash to $LABEL_SHA"
  # the ledgers and state files the builders and join/meta.js read: a SNAPSHOT, hashed, so the recorded hashes are exactly what was read
  mkdir -p $WORK/ledgers/state
  for f in robinhood-token-births.json robinhood-token-minters.ndjson robinhood-v4-births.ndjson; do cp /home/green/.openclaw/workspace/wick-engine/logs/$f $WORK/ledgers/$f || refuse "snapshot of $f failed"; done
  for f in v4-poolkeys.json uniswap-launches.json hook-pad-map.json; do cp /home/green/noxabot/state/$f $WORK/ledgers/state/$f || refuse "snapshot of $f failed"; done
  (cd $WORK/ledgers && sha256sum robinhood-token-births.json robinhood-token-minters.ndjson robinhood-v4-births.ndjson state/v4-poolkeys.json state/uniswap-launches.json state/hook-pad-map.json) > $ST/ledgers.sha256
  bash $ROOT/tools/gate.sh tables $RL
  nice -n 19 python3 $ROOT/builders/tokmeta.py > $RL/tokmeta.log 2>&1 || refuse "tokmeta.py failed"
  nice -n 19 python3 $ROOT/builders/mkmeta.py $TBL/meta_full.tsv > $RL/mkmeta.log 2>&1 || refuse "mkmeta.py failed"
  python3 $ROOT/tools/tables.py meta $TBL/meta_full.tsv $OLD/meta.tsv $TABLE_CUTOFF $TBL/meta.tsv $ST/table_meta.json > /dev/null || refuse "meta.tsv could not be written"
  python3 -c "import json,sys;d=json.load(open('$ST/table_meta.json'));sys.exit(0 if d['old_table_is_byte_prefix'] or d['old_rows_dropped_by_cutoff'] else 1)" || refuse "meta.tsv: the 09-27 table is not a byte prefix of the exam table"
  nice -n 19 node $ROOT/join/meta.js > $RL/v4meta.log 2>&1 || refuse "join/meta.js failed"
  nice -n 19 python3 $ROOT/builders/mkpoolfee.py $TBL/poolfee_full.tsv > $RL/mkpoolfee.log 2>&1 || refuse "mkpoolfee.py failed"
  python3 $ROOT/tools/tables.py poolfee $TBL/poolfee_full.tsv $OLD/poolfee.tsv $TABLE_CUTOFF $TBL/poolfee.tsv $ST/table_poolfee.json > /dev/null || refuse "poolfee.tsv could not be written"
  python3 -c "import json,sys;d=json.load(open('$ST/table_poolfee.json'));sys.exit(0 if d['old_table_is_byte_prefix'] or d['old_rows_dropped_by_cutoff'] else 1)" || refuse "poolfee.tsv: the 09-27 table is not a byte prefix of the exam table"
  cp $OLD/scam.tsv $TBL/scam.tsv
  mark tables
fi
say "5 tables: meta $(python3 -c "import json;d=json.load(open('$ST/table_meta.json'));print(d['out_rows'],'rows; 09-27 table a byte prefix',d['old_table_is_byte_prefix'],'; rebuild differs on',d['rebuild_differences'],'old rows (kept verbatim)',d['rebuild_difference_kinds'])"); poolfee $(python3 -c "import json;d=json.load(open('$ST/table_poolfee.json'));print(d['out_rows'],'rows; 09-27 table a byte prefix',d['old_table_is_byte_prefix'],'; rebuild differs on',d['rebuild_differences'],'old rows (kept verbatim)',d['rebuild_difference_kinds'])")"
# ---- 6. the V4 join for the block (the 09-27 tools, exam copies), from the verified raw files ----
if ! done_ join; then
  python3 $ROOT/tools/days.py link wide $ST/wide_open.json $V4J/in/v4-wide > /dev/null && python3 $ROOT/tools/days.py link wide $ST/wide_block.json $V4J/in/v4-wide > /dev/null || refuse "wide links failed"
  ln -sfn /home/green/noxabot/logs/uniswap-v4-tape-hole.ndjson $V4J/in/uniswap-v4-tape-hole.ndjson; ln -sfn /home/green/noxabot/logs/uniswap-v4-tape-backfill.ndjson $V4J/in/uniswap-v4-tape-backfill.ndjson
  cp $OLDJOIN/unknown_keys.json $V4J/unknown_keys_0927.json; cp $OLDJOIN/decimals.json $V4J/decimals.json
  bash $ROOT/tools/gate.sh unknown_pools $RL
  nice -n 19 node -r $ROOT/tools/exam_guard.js $ROOT/join/unknown_pools.js > $RL/unknown_pools.log 2>&1 || refuse "unknown_pools.js failed"
  python3 $ROOT/join/glue.py unknown_split $V4J $V4J/unknown_keys_0927.json > $ST/unknown_split.json || refuse "unknown split failed"
  if [ "$(python3 -c "import json;print(json.load(open('$ST/unknown_split.json'))['to_resolve'])")" != 0 ]; then
    python3 $ROOT/join/resolve_unknown.py > $RL/resolve_unknown.log 2>&1 || refuse "resolve_unknown.py failed"
    grep -q 'FAILED chunk' $RL/resolve_unknown.log && refuse "resolve_unknown.py: an RPC chunk failed"
  fi
  python3 $ROOT/join/glue.py unknown_merge $V4J $V4J/unknown_keys_0927.json > $ST/unknown_merge.json || refuse "unknown merge failed"
  rm -rf $V4J/shards
  bash $ROOT/tools/gate.sh pass1 $RL
  nice -n 19 ionice -c3 node --max-old-space-size=4000 -r $ROOT/tools/exam_guard.js $ROOT/join/pass1.js $V4J/shards > $RL/pass1.log 2>&1 || refuse "pass1.js failed"
  python3 -c "import json,sys;s=json.load(open('$V4J/pass1_stats.json'));a=sum(v.get('afterCut',0) for v in s.values());print('afterCut',a);sys.exit(1 if a else 0)" || refuse "pass1 saw rows at/after the cut"
  python3 $ROOT/join/glue.py poolcounts $V4J > $ST/poolcounts.json || refuse "poolcounts failed"
  nice -n 19 node $ROOT/join/addr_lists.js $V4J > $ST/addr_lists.json || refuse "addr_lists failed"
  nice -n 19 node $ROOT/join/decimals.js $V4J/addr_quotes.json $V4J/addr_toks.json > $RL/decimals.log 2>&1 || refuse "decimals.js failed"
  bash $ROOT/tools/gate.sh finalize $RL
  nice -n 19 ionice -c3 node --max-old-space-size=6000 -r $ROOT/tools/exam_guard.js $ROOT/join/finalize.js $V4J/shards > $RL/finalize.log 2>&1 || refuse "finalize.js failed"
  for d in $BLOCK_DAYS; do [ -s $V4J/out/v4-swaps-$d.ndjson.gz ] || refuse "no joined V4 file for $d"; done
  for d in $CONSIST_DAYS; do python3 $ROOT/join/glue.py compare $V4J/out/v4-swaps-$d.ndjson.gz $OLDJOIN/out/v4-swaps-$d.ndjson.gz > $ST/consist_$d.json || refuse "consistency compare failed"; done
  rm -rf $V4J/shards
  mark join
fi
say "6 join: $(cat $ST/unknown_merge.json); $(cat $ST/poolcounts.json); consistency $(for d in $CONSIST_DAYS; do python3 -c "import json;d=json.load(open('$ST/consist_$d.json'));print('$d', 'identical', d.get('identical',0), 'differ', d.get('differ',0), 'only_mine', d.get('only_mine',0), 'only_orig', d.get('only_orig',0), end='; ')"; done)"
# ---- 7. the engines' V2/V3 view: links to the verified day files + the 10-07 CUT copy ----
python3 $ROOT/tools/days.py link tape $ST/tape_open.json $WORK/tape > /dev/null && python3 $ROOT/tools/days.py link tape $ST/tape_block.json $WORK/tape > /dev/null || refuse "tape links failed"
[ -s $WORK/tape/robinhood-tape/tape-$CUT_DAY.ndjson ] || refuse "the $CUT_DAY cut copy is missing"
for d in $V4_OPEN_DAYS; do [ -s $OLDJOIN/out/v4-swaps-$d.ndjson.gz ] || refuse "missing open V4 day $d"; done
# ---- 8. the runs: PRIMARY (the 09-27 pass composition, SEED 20260927) and SENSITIVITY (the exam cell alone x 20 seeds) ----
run1() {  # label engine [env...]
  local L=$1; shift
  if [ -s $OUT/$L.ndjson.gz ] && grep -q "^$L	.*exit=0	" $RL/runs.tsv 2>/dev/null; then say "8 $L already done"; return 0; fi
  bash $ROOT/tools/run_engine.sh $L "$@" || refuse "engine run $L failed (see $RL/$L.log)"
}
M=$TBL/meta.tsv; S=$TBL/scam.tsv; P=$TBL/poolfee.tsv; G=$ROOT/tools/exam_guard.js
run1 primary_rule1 $ROOT/engines/engine_st_exam.js $M $S $P $OUT $RL $G
run1 primary_rule2 $ROOT/engines/engine_grid_exam.js $M $S $P $OUT $RL $G
for s in $SEEDS; do
  run1 alone_rule1_s$s $ROOT/engines/engine_st_exam_h.js $M $S $P $OUT $RL $G ONLY_CELLS=C2P EXAM_SEED=$s
  run1 alone_rule2_s$s $ROOT/engines/engine_grid_exam_h.js $M $S $P $OUT $RL $G ONLY_CELLS=D25L48 EXAM_SEED=$s
done
say "8 all engine runs done"
# ---- 9. statistics (frozen analyzers' own code after the pre-filter) and the report ----
for f in $OUT/*.ndjson.gz; do L=$(basename $f .ndjson.gz); r=$([[ $L == *rule1* ]] && echo 1 || echo 2)
  [ -s $STATS/$L.json ] || nice -n 19 python3 $ROOT/tools/stats_rule.py $r $f $STATS/$L.json > /dev/null || refuse "stats failed for $L"; done
python3 $ROOT/tools/report.py $WORK $ROOT/report.md $CUT "$SEEDS" || refuse "report failed"
say "9 report written: $ROOT/report.md"
head -3 $ROOT/report.md
