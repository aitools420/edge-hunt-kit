#!/bin/bash
# run_exam.sh — the ONE-SHOT sealed exam of Block A (rules #1 C2P and #2 D25L48), end to end, writing report.md.
# Register: patches/SEALED-HOLDOUT/README.md (frozen rules, Holm k = 2, BLOCK EDGES, ENGINE FIX, and this runner's own entry).
# Usage, after 2026-10-07T00:00:00Z — TWO starts (commit-reveal, pond #330 H3):
#   1. bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh
#      PHASE 1 = steps 0-7. It ends by writing work/state/manifest.sha256 (every run-time input the engines read) and STOPS (exit 0),
#      printing the manifest's sha256. Nothing statistical exists yet.
#   2. The coordinator posts that sha256 publicly, then:  echo <sha256> > .../work/state/MANIFEST_POSTED
#   3. bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh
#      PHASE 2 = steps 8-9. It first re-checks the posted hash and every manifest hash, then runs the engines, the statistics and
#      report.md (and publishes runs.tsv, exam.log, REFUSED and the manifest beside it, in report_files/).
# It REFUSES (exit 2) before the instant; on any pin file that is not the registered one (sha256 hard-coded below, pond #330 H1); on any
# code or input hash that differs from those pins; on a closed block day whose content differs from pins/block_days.tsv; on any table
# row known on 09-27 that a rebuild would change; on the 09-25/09-26 seam (B1); on any finished step's output that changed (H2).
# EVERY REFUSAL HAS A CLASS, written to work/state/REFUSED (pond #330 H2, registered):
#   RESUMABLE — only failures that happen BEFORE any statistic exists: network, not ready, and an exam engine that DIES WITHOUT
#               COMPLETING — killed or stopped from outside (SIGKILL 137, e.g. the kernel's OOM killer; SIGTERM 143, e.g. a reboot or
#               shutdown; SIGHUP 129; SIGINT 130), or a death that leaves no runs.tsv row: start again unchanged. A dead engine is
#               re-run unchanged; its death and its re-run are disclosed (work/state/ENGINE_DEATHS, published in report_files/);
#               nothing else may change; a partial output is moved aside and never read. Once step 9 has started
#               (work/state/stats.started: statistics may exist) any RESUMABLE is raised to END.
#   THE RUNNER ITSELF KILLED (a reboot stops the whole tree; no refusal is written): every step is marked done only when it has
#               finished, so the next start re-does the unfinished step from scratch (its leftovers cleared) and re-verifies every
#               finished one; an interrupted step 9 is resumed and disclosed (statistics are written atomically and reused only if
#               computed from exactly the recorded outputs; nothing is printed before report.md is complete).
#   CAP       — an exam engine stopped by its RSS guard or by the heap cap (pond #330 L22, registered): resumable ONLY after that cap
#               alone is raised, the new file hash posted publicly, and the change recorded in work/state/CAP_CHANGE (checked here).
#   END       — everything else (hash mismatch, afterCut, a guard abort, the B1 seam gate, a failed builder / join / engine / stats /
#               report step): this runner never starts again on this work folder. Going on is only possible as a LABELLED
#               DEVIATION, disclosed: see the register (a code fix after step 2 changes a pin, so this runner's hard-coded pin hashes
#               must change, so the runner's own sha256 changes; report.md lists every runner sha256 that ever started).
# A finished exam (work/state/FINAL) is never run again: a CAN'T TELL (data) is final for Block A (no re-run, no re-draw; L4).
set -u -o pipefail
# ======================= constants (the exam) =======================
ROOT=/home/green/projects/patches/sealed-exam-blockA
WORK=$ROOT/work
BLOCK_PIN=$ROOT/pins/block_days.tsv    # the 20 registered block-day rows (09-27..10-06, both feeds), copied once from SEALED-HOLDOUT/tape-hashes.tsv
PIN_CODE_SHA=7eb1505029b86772dce56e42780d5b939f7ecd32ad06a4933dea1cd685a3aab1     # sha256 of pins/code.sha256   (written by tools/make_pins.sh)
PIN_INPUTS_SHA=3f1d868f6fb716945c3b6e7d9a636b06ef1bdb4446a4418b6adf81b710dc2e9e   # sha256 of pins/inputs.sha256 (written by tools/make_pins.sh)
PIN_BLOCK_SHA=02064db211905a3d8052facb764961fd59c3233db1849fd83db32f8612407452    # sha256 of pins/block_days.tsv (written by tools/make_pins.sh)
CUT=1791331200                 # 2026-10-07T00:00:00Z: Block A's data end and the earliest start (Block B begins here; nothing at/after it is read)
READY_AT=1791342000            # CUT + 3 h: by then the raw files holding the last hour have passed the cut + margin (checked again by the cut tools)
CUT_DAY=2026-10-07             # day files that hold the block's last hour: V2/V3 tape from ~23:00Z (R-0109), V4-wide from ~23:42Z; read CUT at CUT
TAPE_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"                     # V2/V3 warm-up days (open; pinned in pins/open_days.tsv)
BLOCK_DAYS="2026-09-27 2026-09-28 2026-09-29 2026-09-30 2026-10-01 2026-10-02 2026-10-03 2026-10-04 2026-10-05 2026-10-06"   # sealed; pins/block_days.tsv
WIDE_OPEN_DAYS="2026-09-25 2026-09-26"                               # V4-wide days the join reads before the block (open; pinned)
V4_OPEN_DAYS="2026-09-24 2026-09-25 2026-09-26"                      # warm-up V4 days the engines read from the 09-27 join (pinned files)
JOIN0_TS=1790294400            # 2026-09-25T00:00:00Z: the join's first day (= join/pass1.js JOIN0)
ETH_FROM=1790208000            # 2026-09-24T00:00:00Z: first ETH/USD point fetched (hourly, CoinGecko, cut at CUT)
TABLE_CUTOFF=1791244800        # 2026-10-06T00:00:00Z: meta / poolfee hold coins and pools born before it (unknown birth kept, as on 09-27)
CONSIST_DAYS="2026-09-25 2026-09-26"                                 # joined days compared with the 09-27 join's own files; the FIRST is the join's first day (B1 gate)
SEEDS="20260927 20260928 20260929 20260930 20260931 20260932 20260933 20260934 20260935 20260936 20260937 20260938 20260939 20260940 20260941 20260942 20260943 20260944 20260945 20260946"
LABEL_COMMIT=e5c559ec53baf0ee12eef6fb84587e277ea588f6                # noxabot lib/launchpads.js: last commit before 2026-09-27T00:00Z
LABEL_SHA=1b939aea01899089285dfbb47963eed740aeda58353fc60e5824e9adffcff592
OLD=/home/green/projects/patches/twinfix-2026-10-05/inputs          # the 09-27 tables (meta 45af2cf8…, scam 9988ebfa…, poolfee 5328cf75…)
OLDJOIN=/home/green/projects/patches/v4-join-2026-09-27             # the 09-27 join (decimals.json, unknown_keys.json, out/ warm-up days)
SCAM_SRC="/home/green/noxabot/state/safety-cache.json /home/green/noxabot/state/tokengate-cache.json /home/green/noxabot/state/redteam-scores.json"
SEAL_A=1790467200              # 2026-09-27T00:00:00Z: the scam table's three sources must be older than this
# ====================================================================
RUNNER=$(readlink -f "$0")
# ---- 0. the clock: nothing is created, read or hashed before the instant ----
NOW=$(date -u +%s); [ "$NOW" -ge "$CUT" ] || { echo "$(date -u +%FT%TZ) REFUSED [RESUMABLE]: it is $(date -u +%FT%TZ): the exam may not start before $(date -u -d @$CUT +%FT%TZ)"; exit 2; }
export EXAM_SCRATCH=$WORK/scratch
V4J=$WORK/v4join; TBL=$WORK/tables; ST=$WORK/state; OUT=$WORK/out; RL=$WORK/runlogs; STATS=$WORK/stats
mkdir -p $WORK $V4J/in/v4-wide $TBL $ST $OUT $RL $STATS $EXAM_SCRATCH $WORK/tape/robinhood-tape $WORK/tape/archive
LOG=$RL/exam.log
CAPF=$ST/CAP_CHANGE
exec > >(tee -a $LOG) 2>&1
say() { echo "$(date -u +%FT%TZ) $*"; }
refuse() {  # refuse <END|RESUMABLE|CAP> <message>   (pond #330 H2: the class decides whether any later start may go on)
  local c=$1; shift
  [ "$c" = RESUMABLE ] && [ -f $ST/stats.started ] && c=END        # once statistics may exist (step 9), nothing is resumable
  say "REFUSED [$c]: $*"; echo "REFUSED $c $(date -u +%FT%TZ): $*" >> $ST/REFUSED; exit 2; }
mark() {  # mark <step> <output file>...: the step's outputs are hashed when it finishes (H2) and re-checked on every later start
  local s=$1 f; shift
  for f in "$@"; do [ -f "$f" ] || refuse END "step $s: output $f is missing at the end of the step"; done
  sha256sum "$@" > $ST/$s.sha256.tmp && mv $ST/$s.sha256.tmp $ST/$s.sha256 || refuse END "step $s: could not hash its outputs"
  date -u +%FT%TZ > $ST/$s.done; }
done_() {  # done_ <step>: 1 = not done; 0 = done AND every output still hashes as marked; a changed output is an END refusal
  [ -f $ST/$1.done ] || return 1
  [ -s $ST/$1.sha256 ] || refuse END "step $1 is marked done but has no output hashes"
  sha256sum --quiet --strict -c $ST/$1.sha256 > $RL/recheck_$1.log 2>&1 || refuse END "step $1: a finished step's output changed since it was marked: $(grep -v ': OK' $RL/recheck_$1.log | head -3 | tr '\n' ' ')"
  return 0; }
recheck_all() { local s; for s in days_verified net cuts tables join; do done_ $s || refuse END "$1: step $s is not done"; done; }
exec 9> $WORK/.lock; flock -n 9 || { say "REFUSED [RESUMABLE]: another run_exam.sh is already running on $WORK"; exit 2; }
say "run_exam.sh start; sha256 $(sha256sum $RUNNER | cut -c1-64) ($RUNNER)"
# ---- 0b. a finished exam, or a refusal that ended it, stops every later start (pond #330 H2; L4) ----
[ -f $ST/FINAL ] && refuse END "the exam is finished ($(cat $ST/FINAL)): it is never run again (registered: a CAN'T TELL (data) is final for Block A, no re-run, no re-draw)"
if [ -f $ST/REFUSED ] && grep -q '^REFUSED END ' $ST/REFUSED; then refuse END "a prior refusal ended the exam: $(grep -m1 '^REFUSED END ' $ST/REFUSED)"; fi
# ---- 1. pins (anchored here), code and open inputs ----
for k in code.sha256:$PIN_CODE_SHA inputs.sha256:$PIN_INPUTS_SHA block_days.tsv:$PIN_BLOCK_SHA; do
  f=$ROOT/pins/${k%%:*}; h=$(sha256sum $f 2>/dev/null | cut -c1-64)
  [ "$h" = "${k##*:}" ] || refuse END "pins/${k%%:*} is not the registered pin file: sha256 ${h:-missing}, registered ${k##*:} (pond #330 H1)"
done
say "1 pin files are the registered ones: pins/code.sha256 $PIN_CODE_SHA · pins/inputs.sha256 $PIN_INPUTS_SHA · pins/block_days.tsv $PIN_BLOCK_SHA"
python3 $ROOT/tools/exam_checks.py codecheck $ROOT/pins/code.sha256 $ROOT $CAPF $ST/REFUSED > $RL/pins_code.check 2>&1 || refuse END "code hash mismatch: $(tail -c 600 $RL/pins_code.check)"
sha256sum --quiet --strict -c $ROOT/pins/inputs.sha256 > $RL/pins_inputs.check 2>&1 || refuse END "input hash mismatch: $(grep -v ': OK' $RL/pins_inputs.check | head -5 | tr '\n' ' ')"
say "1 code and open inputs: $(wc -l < $ROOT/pins/code.sha256) code files and $(wc -l < $ROOT/pins/inputs.sha256) inputs match pins/ ($(cat $RL/pins_code.check))"
[ "${CONSIST_DAYS%% *}" = "$(date -u -d @$JOIN0_TS +%F)" ] || refuse END "CONSIST_DAYS must start at the join's first day $(date -u -d @$JOIN0_TS +%F)"
(cd $ROOT/engines && node guard_test.js > $RL/guard_test.log 2>&1); echo $? > $ST/G3.rc
[ "$(cat $ST/G3.rc)" = 0 ] || refuse END "guard_test.js failed (G3)"
for f in $SCAM_SRC; do m=$(stat -c %Y $f); [ "$m" -lt "$SEAL_A" ] || refuse END "scam source $f changed after 2026-09-27T00:00Z (mtime $(date -u -d @$m +%FT%TZ)): stop and report"; done
say "1 G3 guard test PASS; the scam table's three sources predate the seal"
if [ -f $ST/REFUSED ] && grep -q '^REFUSED CAP ' $ST/REFUSED; then
  python3 $ROOT/tools/exam_checks.py capresume $ST/REFUSED $CAPF > $RL/capresume.check 2>&1 || refuse CAP "resume refused: an exam engine hit its RSS guard or heap cap and that cap has not been raised and recorded (registered L22: the only allowed change is raising that cap; post the new file hash, then add the record to work/state/CAP_CHANGE): $(cat $RL/capresume.check)"
  say "1 L22 cap change(s) recorded and verified: $(cat $RL/capresume.check)"
fi
# ---- 1b. wait until READY_AT (cut + 3 h): the raw files holding the last hour must be past the cut + margin ----
while [ "$(date -u +%s)" -lt "$READY_AT" ]; do say "1b waiting until $(date -u -d @$READY_AT +%FT%TZ) (raw files must pass the cut + margin)"; sleep 600; done
# ---- PHASE 2 entry (H3): a written manifest means phase 1 is over; the posted hash and every manifest hash are checked FIRST ----
PHASE=1
if [ -f $ST/manifest.sha256 ]; then
  PHASE=2
  MS=$(sha256sum $ST/manifest.sha256 | cut -c1-64)
  [ -f $ST/MANIFEST_POSTED ] || refuse RESUMABLE "phase 2 needs the manifest's sha256 posted first: post $MS, then write it to $ST/MANIFEST_POSTED (pond #330 H3)"
  P2=$(grep -oE '[0-9a-f]{64}' $ST/MANIFEST_POSTED | head -1)
  [ "$P2" = "$MS" ] || refuse END "MANIFEST_POSTED holds ${P2:-no sha256}, but the manifest hashes to $MS: the manifest changed after it was posted, or the wrong hash was posted"
  (cd $WORK && sha256sum --quiet --strict -c state/manifest.sha256) > $RL/manifest.check 2>&1 || refuse END "manifest check failed (a run-time input changed after the manifest was posted): $(grep -v ': OK' $RL/manifest.check | head -3 | tr '\n' ' ')"
  recheck_all "phase 2"
  [ -f $ST/phase2.started ] || date -u +%FT%TZ > $ST/phase2.started
  say "PHASE 2: manifest $MS posted and re-checked ($(wc -l < $ST/manifest.sha256) files); every finished step re-verified"
fi
# ---- 2. closed days against their registered hashes (sealed: pins/block_days.tsv; open: pins/open_days.tsv) ----
if ! done_ days_verified; then
  python3 $ROOT/tools/days.py verify tape $ST/tape_block.json $BLOCK_PIN --sha256 $PIN_BLOCK_SHA $BLOCK_DAYS || refuse END "a sealed V2/V3 tape day is missing, ambiguous or differs from pins/block_days.tsv"
  python3 $ROOT/tools/days.py verify wide $ST/wide_block.json $BLOCK_PIN --sha256 $PIN_BLOCK_SHA $BLOCK_DAYS || refuse END "a sealed V4-wide day is missing, ambiguous or differs from pins/block_days.tsv"
  python3 $ROOT/tools/days.py verify tape $ST/tape_open.json $ROOT/pins/open_days.tsv $TAPE_OPEN_DAYS || refuse END "an open V2/V3 warm-up day differs from its pin"
  python3 $ROOT/tools/days.py verify wide $ST/wide_open.json $ROOT/pins/open_days.tsv $WIDE_OPEN_DAYS || refuse END "an open V4-wide day differs from its pin"
  mark days_verified $ST/tape_block.json $ST/wide_block.json $ST/tape_open.json $ST/wide_open.json
fi
say "2 every closed day verified (block days against pins/block_days.tsv, open days against pins/open_days.tsv)"
# ---- 3. the block's anchors (block -> time, public RPC) and ETH/USD (CoinGecko hourly, cut at CUT) ----
if ! done_ net; then
  python3 $ROOT/join/anchors.py > $RL/anchors.log 2>&1 || refuse RESUMABLE "anchors fetch failed (network; see $RL/anchors.log)"
  last=$(tail -1 $V4J/anchors.tsv | cut -f2); [ "$last" -ge $((CUT + 7200)) ] || refuse RESUMABLE "anchors end at $last, not 2 h past the cut (not ready)"
  python3 $ROOT/join/fetch_ethusd.py $V4J/ethusd_coingecko.json $ETH_FROM $CUT > $RL/ethusd.log 2>&1 || refuse RESUMABLE "ETH/USD fetch failed or incomplete (network): $(cat $RL/ethusd.log)"
  mark net $V4J/anchors.tsv $V4J/heldout.tsv $V4J/ethusd_coingecko.json
fi
say "3 anchors $(wc -l < $V4J/anchors.tsv) (last $(date -u -d @$(tail -1 $V4J/anchors.tsv | cut -f2) +%FT%TZ)); ETH/USD $(cat $RL/ethusd.log)"
# ---- 4. the cuts: the 10-07 V2/V3 file, the 10-07 V4-wide file and the locked V4 tape, rows < CUT only; hashed; the two cut rows go to
#      work/state/cut_rows.tsv (the runner never writes SEALED-HOLDOUT/tape-hashes.tsv; the coordinator registers the rows from there) ----
if ! done_ cuts; then
  for i in $(seq 1 72); do
    T7=$(python3 -c "
import glob; d='$CUT_DAY'; W='/home/green/.openclaw/workspace/wick-engine/logs'
a=sorted(glob.glob(W+'/archive/*/tape-'+d+'.ndjson.gz')); l=W+'/robinhood-tape/tape-'+d+'.ndjson'
import os; print(' '.join(a+([l] if os.path.exists(l) else [])))")
    [ -n "$T7" ] || { say "4 no $CUT_DAY tape file yet; wait 600 s"; sleep 600; continue; }
    [ "$(echo $T7 | wc -w)" = 1 ] || refuse END "the $CUT_DAY tape has more than one part: $T7"
    python3 $ROOT/tools/cut_tape.py $WORK/tape/robinhood-tape/tape-$CUT_DAY.ndjson $CUT $T7 > $ST/cut_tape.json; r1=$?
    W7=/home/green/noxabot/logs/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson
    [ -f $W7 ] && { node $ROOT/join/cut_v4.js $V4J/anchors.tsv $W7 $V4J/in/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson $CUT $JOIN0_TS > $ST/cut_wide.json; r2=$?; } || r2=3
    node $ROOT/join/cut_v4.js $V4J/anchors.tsv /home/green/noxabot/logs/uniswap-v4-tape.ndjson $V4J/in/uniswap-v4-tape.ndjson $CUT $JOIN0_TS > $ST/cut_lock.json; r3=$?
    say "4 cut attempt $i: tape rc $r1, wide rc $r2, locked tape rc $r3"
    [ $r1 = 0 ] && [ $r2 = 0 ] && [ $r3 = 0 ] && break
    { [ $r1 != 3 ] && [ $r1 != 0 ]; } || { [ $r2 != 3 ] && [ $r2 != 0 ]; } || { [ $r3 != 3 ] && [ $r3 != 0 ]; } && refuse END "a cut tool failed (rc $r1/$r2/$r3)"
    sleep 600
  done
  [ $r1 = 0 ] && [ $r2 = 0 ] && [ $r3 = 0 ] || refuse RESUMABLE "the raw files never passed the cut + margin (not ready)"
  python3 - "$ST/cut_rows.tsv" "$CUT_DAY" "$CUT" "$ST/cut_tape.json" "$ST/cut_wide.json" <<'PY' || refuse END "could not write the cut rows to work/state/cut_rows.tsv"
import json, sys, datetime
tsv, day, cut, a, b = sys.argv[1:6]
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
A, B = json.load(open(a)), json.load(open(b))
with open(tsv, 'w') as o:                     # written whole (idempotent), in tape-hashes.tsv's format
    o.write(f"{now}\t{day}\tv2v3-tape-cutA\t{A['sha256']}\t{A['bytes']}\t{' + '.join(A['inputs'])} rows ts<{cut} (Block A exam cut, run_exam.sh)\n")
    o.write(f"{now}\t{day}\tv4-wide-cutA\t{B['sha256']}\t{B['bytes']}\t{B['in']} rows t<{cut} by the exam anchors (Block A exam cut, run_exam.sh)\n")
print('written')
PY
  mark cuts $WORK/tape/robinhood-tape/tape-$CUT_DAY.ndjson $V4J/in/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson $V4J/in/uniswap-v4-tape.ndjson $ST/cut_tape.json $ST/cut_wide.json $ST/cut_lock.json $ST/cut_rows.tsv
fi
say "4 cuts: tape $(cat $ST/cut_tape.json); wide $(cat $ST/cut_wide.json); locked $(cat $ST/cut_lock.json)"
# ---- 5. tables: meta.tsv and poolfee.tsv rebuilt (coins / pools born before TABLE_CUTOFF; every 09-27 row kept verbatim), scam.tsv as on 09-27 ----
if ! done_ tables; then
  c=$(git -C /home/green/noxabot log --before=2026-09-27T00:00:00Z -1 --format=%H -- lib/launchpads.js); [ "$c" = "$LABEL_COMMIT" ] || refuse END "launchpads.js last pre-seal commit is $c, not $LABEL_COMMIT"
  git -C /home/green/noxabot show $LABEL_COMMIT:lib/launchpads.js > $TBL/launchpads_e5c559ec.js || refuse END "git show failed"
  [ "$(sha256sum $TBL/launchpads_e5c559ec.js | cut -c1-64)" = "$LABEL_SHA" ] || refuse END "launchpads.js at $LABEL_COMMIT does not hash to $LABEL_SHA"
  # the ledgers and state files the builders and join/meta.js read: a SNAPSHOT, hashed, so the recorded hashes are exactly what was read
  mkdir -p $WORK/ledgers/state
  for f in robinhood-token-births.json robinhood-token-minters.ndjson robinhood-v4-births.ndjson; do cp /home/green/.openclaw/workspace/wick-engine/logs/$f $WORK/ledgers/$f || refuse END "snapshot of $f failed"; done
  for f in v4-poolkeys.json uniswap-launches.json hook-pad-map.json; do cp /home/green/noxabot/state/$f $WORK/ledgers/state/$f || refuse END "snapshot of $f failed"; done
  (cd $WORK/ledgers && sha256sum robinhood-token-births.json robinhood-token-minters.ndjson robinhood-v4-births.ndjson state/v4-poolkeys.json state/uniswap-launches.json state/hook-pad-map.json) > $ST/ledgers.sha256
  bash $ROOT/tools/gate.sh tables $RL
  nice -n 19 python3 $ROOT/builders/tokmeta.py > $RL/tokmeta.log 2>&1 || refuse END "tokmeta.py failed"
  nice -n 19 python3 $ROOT/builders/mkmeta.py $TBL/meta_full.tsv > $RL/mkmeta.log 2>&1 || refuse END "mkmeta.py failed"
  python3 $ROOT/tools/tables.py meta $TBL/meta_full.tsv $OLD/meta.tsv $TABLE_CUTOFF $TBL/meta.tsv $ST/table_meta.json > /dev/null || refuse END "meta.tsv could not be written"
  python3 -c "import json,sys;d=json.load(open('$ST/table_meta.json'));sys.exit(0 if d['old_table_is_byte_prefix'] or d['old_rows_dropped_by_cutoff'] else 1)" || refuse END "meta.tsv: the 09-27 table is not a byte prefix of the exam table"
  nice -n 19 node $ROOT/join/meta.js > $RL/v4meta.log 2>&1 || refuse END "join/meta.js failed"
  nice -n 19 python3 $ROOT/builders/mkpoolfee.py $TBL/poolfee_full.tsv > $RL/mkpoolfee.log 2>&1 || refuse END "mkpoolfee.py failed"
  python3 $ROOT/tools/tables.py poolfee $TBL/poolfee_full.tsv $OLD/poolfee.tsv $TABLE_CUTOFF $TBL/poolfee.tsv $ST/table_poolfee.json > /dev/null || refuse END "poolfee.tsv could not be written"
  python3 -c "import json,sys;d=json.load(open('$ST/table_poolfee.json'));sys.exit(0 if d['old_table_is_byte_prefix'] or d['old_rows_dropped_by_cutoff'] else 1)" || refuse END "poolfee.tsv: the 09-27 table is not a byte prefix of the exam table"
  cp $OLD/scam.tsv $TBL/scam.tsv
  mark tables $TBL/launchpads_e5c559ec.js $TBL/tokmeta.tsv $TBL/meta_full.tsv $TBL/meta.tsv $TBL/poolfee_full.tsv $TBL/poolfee.tsv $TBL/scam.tsv $ST/table_meta.json $ST/table_poolfee.json \
    $ST/ledgers.sha256 $WORK/ledgers/robinhood-token-births.json $WORK/ledgers/robinhood-token-minters.ndjson $WORK/ledgers/robinhood-v4-births.ndjson \
    $WORK/ledgers/state/v4-poolkeys.json $WORK/ledgers/state/uniswap-launches.json $WORK/ledgers/state/hook-pad-map.json $V4J/meta.json
fi
say "5 tables: meta $(python3 -c "import json;d=json.load(open('$ST/table_meta.json'));print(d['out_rows'],'rows; 09-27 table a byte prefix',d['old_table_is_byte_prefix'],'; rebuild differs on',d['rebuild_differences'],'old rows (kept verbatim)',d['rebuild_difference_kinds'])"); poolfee $(python3 -c "import json;d=json.load(open('$ST/table_poolfee.json'));print(d['out_rows'],'rows; 09-27 table a byte prefix',d['old_table_is_byte_prefix'],'; rebuild differs on',d['rebuild_differences'],'old rows (kept verbatim)',d['rebuild_difference_kinds'])")"
# ---- 6. the V4 join for the block (the 09-27 tools, exam copies), from the verified raw files ----
seam_gate() {  # seam_gate <out.json> — B1 (pond #330): the join's first day may differ from the 09-27 join only in other-quote price fields
  local a=() d; for d in $CONSIST_DAYS; do a+=($ST/consist_$d.json); done      # (bounded); every later day not at all
  python3 $ROOT/tools/exam_checks.py seam "${a[@]}" > $1.tmp 2>&1 || refuse END "B1 seam gate: the exam's join differs from the 09-27 join at the 09-25/09-26 seam beyond what was registered: $(cat $1.tmp)"
  mv $1.tmp $1; }
if ! done_ join; then
  rm -rf $V4J/shards $V4J/out; rm -f $V4J/unknown_keys.json $V4J/unknown_keys_new.json $V4J/unknown_pools.json $V4J/unknown_pools_all.json $ST/consist_*.json   # leftovers of an interrupted attempt
  python3 $ROOT/tools/days.py link wide $ST/wide_open.json $V4J/in/v4-wide > /dev/null && python3 $ROOT/tools/days.py link wide $ST/wide_block.json $V4J/in/v4-wide > /dev/null || refuse END "wide links failed"
  ln -sfn /home/green/noxabot/logs/uniswap-v4-tape-hole.ndjson $V4J/in/uniswap-v4-tape-hole.ndjson; ln -sfn /home/green/noxabot/logs/uniswap-v4-tape-backfill.ndjson $V4J/in/uniswap-v4-tape-backfill.ndjson
  cp $OLDJOIN/unknown_keys.json $V4J/unknown_keys_0927.json; cp $OLDJOIN/decimals.json $V4J/decimals.json
  bash $ROOT/tools/gate.sh unknown_pools $RL
  nice -n 19 node -r $ROOT/tools/exam_guard.js $ROOT/join/unknown_pools.js > $RL/unknown_pools.log 2>&1 || refuse END "unknown_pools.js failed"
  python3 $ROOT/join/glue.py unknown_split $V4J $V4J/unknown_keys_0927.json > $ST/unknown_split.json || refuse END "unknown split failed"
  if [ "$(python3 -c "import json;print(json.load(open('$ST/unknown_split.json'))['to_resolve'])")" != 0 ]; then
    python3 $ROOT/join/resolve_unknown.py > $RL/resolve_unknown.log 2>&1 || refuse RESUMABLE "resolve_unknown.py failed (network)"
    grep -q 'FAILED chunk' $RL/resolve_unknown.log && refuse RESUMABLE "resolve_unknown.py: an RPC chunk failed (network)"
  fi
  python3 $ROOT/join/glue.py unknown_merge $V4J $V4J/unknown_keys_0927.json > $ST/unknown_merge.json || refuse END "unknown merge failed"
  rm -rf $V4J/shards
  bash $ROOT/tools/gate.sh pass1 $RL
  nice -n 19 ionice -c3 node --max-old-space-size=4000 -r $ROOT/tools/exam_guard.js $ROOT/join/pass1.js $V4J/shards > $RL/pass1.log 2>&1 || refuse END "pass1.js failed"
  python3 -c "import json,sys;s=json.load(open('$V4J/pass1_stats.json'));a=sum(v.get('afterCut',0) for v in s.values());print('afterCut',a);sys.exit(1 if a else 0)" || refuse END "pass1 saw rows at/after the cut"
  python3 $ROOT/join/glue.py poolcounts $V4J > $ST/poolcounts.json || refuse END "poolcounts failed"
  nice -n 19 node $ROOT/join/addr_lists.js $V4J > $ST/addr_lists.json || refuse END "addr_lists failed"
  nice -n 19 node $ROOT/join/decimals.js $V4J/addr_quotes.json $V4J/addr_toks.json > $RL/decimals.log 2>&1 || refuse RESUMABLE "decimals.js failed (network)"
  bash $ROOT/tools/gate.sh finalize $RL
  nice -n 19 ionice -c3 node --max-old-space-size=6000 -r $ROOT/tools/exam_guard.js $ROOT/join/finalize.js $V4J/shards > $RL/finalize.log 2>&1 || refuse END "finalize.js failed"
  for d in $BLOCK_DAYS; do [ -s $V4J/out/v4-swaps-$d.ndjson.gz ] || refuse END "no joined V4 file for $d"; done
  for d in $CONSIST_DAYS; do python3 $ROOT/join/glue.py compare $V4J/out/v4-swaps-$d.ndjson.gz $OLDJOIN/out/v4-swaps-$d.ndjson.gz > $ST/consist_$d.json || refuse END "consistency compare failed"; done
  seam_gate $ST/seam_gate.json                               # B1: refuses BEFORE the join is marked done, so before any engine runs
  rm -rf $V4J/shards
  cs=(); for d in $CONSIST_DAYS; do cs+=($ST/consist_$d.json); done
  mark join $V4J/unknown_keys_0927.json $V4J/decimals.json $V4J/unknown_keys.json $V4J/pass1_stats.json $V4J/poolcounts.tsv $V4J/addr_quotes.json $V4J/addr_toks.json \
    $V4J/finalize_stats.json $V4J/out/*.ndjson.gz $ST/unknown_split.json $ST/unknown_merge.json $ST/poolcounts.json $ST/addr_lists.json "${cs[@]}" $ST/seam_gate.json
fi
seam_gate $RL/seam_gate.recheck.json                         # B1 again on every start (the consist files are re-verified by their hashes above)
say "6 join: $(cat $ST/unknown_merge.json); $(cat $ST/poolcounts.json); B1 seam gate PASS: $(cat $RL/seam_gate.recheck.json)"
# ---- 7. the engines' V2/V3 view: links to the verified day files + the 10-07 CUT copy ----
python3 $ROOT/tools/days.py link tape $ST/tape_open.json $WORK/tape > /dev/null && python3 $ROOT/tools/days.py link tape $ST/tape_block.json $WORK/tape > /dev/null || refuse END "tape links failed"
[ -s $WORK/tape/robinhood-tape/tape-$CUT_DAY.ndjson ] || refuse END "the $CUT_DAY cut copy is missing"
for d in $V4_OPEN_DAYS; do [ -s $OLDJOIN/out/v4-swaps-$d.ndjson.gz ] || refuse END "missing open V4 day $d"; done
# ---- END OF PHASE 1 (H3): the manifest of every run-time input the engines and the report read, then STOP ----
if [ $PHASE = 1 ]; then
  M=(tape/robinhood-tape/tape-$CUT_DAY.ndjson v4join/in/v4-wide/uniswap-v4-wide-$CUT_DAY.ndjson v4join/in/uniswap-v4-tape.ndjson
     ledgers/robinhood-token-births.json ledgers/robinhood-token-minters.ndjson ledgers/robinhood-v4-births.ndjson
     ledgers/state/v4-poolkeys.json ledgers/state/uniswap-launches.json ledgers/state/hook-pad-map.json
     tables/meta.tsv tables/poolfee.tsv tables/scam.tsv tables/launchpads_e5c559ec.js tables/tokmeta.tsv tables/meta_full.tsv tables/poolfee_full.tsv
     v4join/anchors.tsv v4join/heldout.tsv v4join/ethusd_coingecko.json v4join/decimals.json v4join/unknown_keys.json v4join/meta.json
     state/cut_tape.json state/cut_wide.json state/cut_lock.json state/cut_rows.tsv state/tape_block.json state/wide_block.json
     state/tape_open.json state/wide_open.json state/ledgers.sha256 state/seam_gate.json)
  for d in $CONSIST_DAYS; do M+=(state/consist_$d.json); done
  for d in $CONSIST_DAYS $BLOCK_DAYS; do M+=(v4join/out/v4-swaps-$d.ndjson.gz); done
  (cd $WORK && sha256sum "${M[@]}") > $ST/manifest.sha256.tmp || refuse END "the manifest could not be written"
  mv $ST/manifest.sha256.tmp $ST/manifest.sha256
  MS=$(sha256sum $ST/manifest.sha256 | cut -c1-64)
  say "PHASE 1 COMPLETE. Manifest work/state/manifest.sha256 ($(wc -l < $ST/manifest.sha256) files) sha256 $MS"
  say "NEXT: post that sha256 publicly, then: echo $MS > $ST/MANIFEST_POSTED ; then start run_exam.sh again for phase 2 (engines, statistics, report)."
  cat $ST/manifest.sha256
  exit 0
fi
# ---- 8. the runs: PRIMARY (the 09-27 pass composition, SEED 20260927) and SENSITIVITY (the exam cell alone x 20 seeds) ----
LABELS="primary_rule1 primary_rule2"; for s in $SEEDS; do LABELS="$LABELS alone_rule1_s$s alone_rule2_s$s"; done
death() { echo "$(date -u +%FT%TZ) $*" >> $ST/ENGINE_DEATHS; say "8 DISCLOSED: $*"; }
run1() {  # label engine [args...]: a finished run is reused only if runs.tsv's engine hash is its pin and the output content matches runs.tsv (H2)
  local L=$1 E=$2 cap n0 rc ts=$(date -u +%Y%m%dT%H%M%SZ) prev
  python3 $ROOT/tools/exam_checks.py runs $RL/runs.tsv $ROOT/pins/code.sha256 $ROOT $CAPF $OUT $L > $RL/runs_check.json 2>&1 || refuse END "engine run $L: $(cat $RL/runs_check.json)"
  if grep -qE '"(partial|unrecorded)"' $RL/runs_check.json; then        # the output of a run that never completed: moved aside, NEVER read
    mkdir -p $WORK/failed_outputs; mv $OUT/$L.ndjson.gz $WORK/failed_outputs/$L.$ts.ndjson.gz
    death "$L: the output file of a run that did not complete ($(grep -oE '"(partial|unrecorded)"' $RL/runs_check.json | tr -d '"'); sha256 $(sha256sum $WORK/failed_outputs/$L.$ts.ndjson.gz | cut -c1-64)) moved to work/failed_outputs/ unread"; fi
  if [ -s $OUT/$L.ndjson.gz ]; then say "8 $L already done (output content and engine sha256 re-verified against runs.tsv and the pins)"; return 0; fi
  if [ -e $RL/$L.log ] || awk -F'\t' -v l=$L '$1==l{f=1} END{exit !f}' $RL/runs.tsv 2>/dev/null; then    # a RE-RUN: disclosed, evidence kept
    prev=$(awk -F'\t' -v l=$L '$1==l{x=$6} END{print x}' $RL/runs.tsv 2>/dev/null)
    [ -e $RL/$L.log ] && mv $RL/$L.log $RL/$L.log.died-$ts
    [ -e $EXAM_SCRATCH/$L.ndjson ] && { mkdir -p $WORK/failed_outputs; mv $EXAM_SCRATCH/$L.ndjson $WORK/failed_outputs/$L.$ts.scratch.ndjson; }
    death "$L: RE-RUN unchanged (previous attempt: ${prev:-no runs.tsv row}; its log kept as runlogs/$L.log.died-$ts)"; fi
  shift
  n0=$(awk -F'\t' -v l=$L '$1==l' $RL/runs.tsv 2>/dev/null | wc -l)
  bash $ROOT/tools/run_engine.sh $L "$@"; rc=$?
  [ $rc = 0 ] && return 0
  cap=$(python3 $ROOT/tools/exam_checks.py capfail $RL/$L.log $E $ROOT) && refuse CAP "engine run $L stopped by its memory cap [cap=$cap]. Registered (pond #330 L22): the only allowed change is raising that cap; post the new file hash publicly, record it in work/state/CAP_CHANGE, then start again"
  python3 $ROOT/tools/exam_checks.py killed $RL/runs.tsv $L $n0 $RL/$L.log $rc > $RL/killed_check.json 2>&1 && refuse RESUMABLE "engine run $L died without completing ($(cat $RL/killed_check.json)). Registered: an engine that dies without completing (kernel kill or an external stop such as a reboot; no complete output) is re-run unchanged; the death and the re-run are disclosed in report_files; nothing else may change; a partial output is never read. Start again unchanged"
  refuse END "engine run $L failed (exit $rc; see $RL/$L.log)"
}
M=$TBL/meta.tsv; S=$TBL/scam.tsv; P=$TBL/poolfee.tsv; G=$ROOT/tools/exam_guard.js
run1 primary_rule1 $ROOT/engines/engine_st_exam.js $M $S $P $OUT $RL $G
run1 primary_rule2 $ROOT/engines/engine_grid_exam.js $M $S $P $OUT $RL $G
for s in $SEEDS; do
  run1 alone_rule1_s$s $ROOT/engines/engine_st_exam_h.js $M $S $P $OUT $RL $G ONLY_CELLS=C2P EXAM_SEED=$s
  run1 alone_rule2_s$s $ROOT/engines/engine_grid_exam_h.js $M $S $P $OUT $RL $G ONLY_CELLS=D25L48 EXAM_SEED=$s
done
say "8 all engine runs done"
# ---- 9. statistics (frozen analyzers' own code after the pre-filter) and the report; everything re-checked first (H2, H3) ----
(cd $WORK && sha256sum --quiet --strict -c state/manifest.sha256) > $RL/manifest.check 2>&1 || refuse END "manifest check failed before step 9: $(grep -v ': OK' $RL/manifest.check | head -3 | tr '\n' ' ')"
recheck_all "before step 9"
python3 $ROOT/tools/exam_checks.py runs $RL/runs.tsv $ROOT/pins/code.sha256 $ROOT $CAPF $OUT --require $LABELS > $RL/runs_check.json 2>&1 || refuse END "runs check before step 9: $(cat $RL/runs_check.json)"
if [ -f $ST/stats.started ]; then death "step 9 RESUMED after an interrupted start (step 9 first began $(cat $ST/stats.started)); nothing had been printed; a statistics file is reused only if computed from exactly the recorded output"
else date -u +%FT%TZ > $ST/stats.started; fi                  # from here statistics may exist: no refusal is resumable any more
for L in $LABELS; do r=$([[ $L == *rule1* ]] && echo 1 || echo 2)
  python3 $ROOT/tools/exam_checks.py statsrc $STATS/$L.json $OUT/$L.ndjson.gz > /dev/null; rc=$?
  [ $rc = 0 ] && continue; [ $rc = 1 ] || refuse END "stats for $L were computed from a different output"
  nice -n 19 python3 $ROOT/tools/stats_rule.py $r $OUT/$L.ndjson.gz $STATS/$L.json.tmp > /dev/null && mv $STATS/$L.json.tmp $STATS/$L.json || refuse END "stats failed for $L"; done
python3 $ROOT/tools/report.py $WORK $ROOT/report.md $CUT "$SEEDS" $RUNNER || refuse END "report failed (nothing written; registered: a report failure is a refusal, pond #330 H1)"
echo "report.md sha256 $(sha256sum $ROOT/report.md | cut -c1-64) at $(date -u +%FT%TZ)" > $ST/FINAL
grep -q "CAN'T TELL (data)" $ROOT/report.md && say "9 a rule read CAN'T TELL (data): final for Block A, no re-run, no re-draw; it waits for Block B (registered L4)"
say "9 report written: $ROOT/report.md ($(cat $ST/FINAL)); publishing runs.tsv, exam.log, REFUSED and the manifest beside it in report_files/"
PF=$ROOT/report_files; mkdir -p $PF
cp $RL/runs.tsv $PF/runs.tsv; cp $ST/manifest.sha256 $PF/manifest.sha256; cp $ST/MANIFEST_POSTED $PF/MANIFEST_POSTED
if [ -f $ST/REFUSED ]; then cp $ST/REFUSED $PF/REFUSED.txt; else echo "no refusal" > $PF/REFUSED.txt; fi
[ -f $CAPF ] && cp $CAPF $PF/CAP_CHANGE.tsv
if [ -f $ST/ENGINE_DEATHS ]; then cp $ST/ENGINE_DEATHS $PF/ENGINE_DEATHS.txt; else echo "no engine death" > $PF/ENGINE_DEATHS.txt; fi
head -6 $ROOT/report.md
cp $LOG $PF/exam.log
