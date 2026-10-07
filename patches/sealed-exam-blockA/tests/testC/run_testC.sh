#!/bin/bash
# run_testC.sh — TEST C (refusals), rebuilt for pond #330 (B1, H1, H2, H3, L22, L4). Every runner case runs on a THROWAWAY tree made by
# tests/testC/make_tree.py from the CURRENT kit: every real data root is redirected to a synthetic fake home, every heavy or networked step
# is a stub (no engine is ever started), the window constants are Test B's shifted OPEN calendar, and the tree has its own pins and PIN_*
# anchors written by its own tools/make_pins.sh. Since 2026-10-07T00:00Z the real runner can no longer be tested by running it (a
# byte-identical copy would START THE EXAM), so C1 now runs a tree whose CUT is one day ahead. A case PASSES only if the runner exits as
# expected, prints the expected refusal CLASS (END / RESUMABLE / CAP) and the expected reason text.
#  C1-C4   the original refusals (clock, code hash, input hash, block-day content) on the new runner.
#  H1a-f   pin anchors: edited pin files refuse; regenerated pins after an edited code file refuse; days.py refuses a pinned file of the
#          wrong hash; the appendable registry is not read at all.
#  B1a-f   the 09-25/09-26 seam gate (tree calendar: 09-20 = the join's first day, 09-21 = the next day), plus the control that passes.
#  H2a-f   engine hash in runs.tsv != pin; a finished step's output changed; a prior END refusal; a prior RESUMABLE does not block; a
#          tampered engine output; a finished exam (FINAL) is never re-run (L4).
#  H3a-e   phase 2 without MANIFEST_POSTED; a wrong posted hash; the manifest altered after posting; a manifest-listed input altered;
#          the control that reaches step 8.
#  L22a-g  the memory caps: RSS guard and heap cap refuse as CAP; no resume without a cap change; a cap change with any other edit, a
#          lowered cap, or a cap raised before it fired refuse END; a valid cap change resumes.
#  K1-K5   an engine that DIES without completing (SIGKILL, exit 137, or no runs.tsv row) is RESUMABLE: re-run unchanged, disclosed,
#          its partial output never read; the control (complete output, then exit 1) stays END; after step 9 starts nothing resumes.
#  K6-K7   external stops are deaths too: SIGTERM 143 (a reboot), SIGHUP 129, SIGINT 130; SIGABRT 134 stays END (unless the heap cap).
#  KR1-KR3 the RUNNER ITSELF SIGTERMed with its whole tree (as a reboot does) during an engine run, during step 2 and during step 9:
#          no END refusal is left behind and the next start resumes (re-run disclosed; the unfinished step redone; step 9 resumed, disclosed).
#  C5, C6  the exam guard and the exam reader on synthetic files (unchanged).
set -u
F=/home/green/projects/patches/sealed-exam-blockA; MT="python3 $F/tests/testC/make_tree.py"
SCR=$(mktemp -d /tmp/claude-1000/testC.XXXXXX)
LOG=${TESTC_LOG:-$F/tests/testC/testC.log}; : > $LOG          # TESTC_LOG / TESTC_KIT: used by tests/mutation_check.sh only
pass=0; fail=0
note() { echo "$*" | tee -a $LOG; }
res() { if [ "$1" = 1 ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi; note "$r  $2  (exit $3, want $4) :: $5"; }
# rc <name> <want_exit> <want_class|-> <want_text> <case_dir>: run the case tree's runner and check exit code, class and reason
rc() { local name=$1 want=$2 cls=$3 txt=$4 c=$SCR/$5 out got ok=1 show
  out=$(bash $c/tree/run_exam.sh 2>&1); got=$?
  [ "$got" = "$want" ] || ok=0
  if [ "$cls" != - ]; then echo "$out" | grep -q "REFUSED \[$cls\]" || ok=0; fi
  echo "$out" | grep -qF -- "$txt" || ok=0
  show=$(echo "$out" | grep -E 'REFUSED \[|PHASE 1 COMPLETE' | tail -1 | sed "s|$SCR|<scr>|g" | cut -c1-330)
  res $ok "$name" "$got" "$want" "$show"; }
mk() { $MT tree $SCR/$1 "${@:2}" > /dev/null || { note "FAIL  could not build tree $1"; fail=$((fail+1)); }; }
st() { $MT state $SCR/$1 "${@:2}" > /dev/null || { note "FAIL  could not write state $1"; fail=$((fail+1)); }; }
p1() { mk $1 && st $1 join && bash $SCR/$1/tree/run_exam.sh > /dev/null 2>&1; [ -f $SCR/$1/tree/work/state/manifest.sha256 ] || { note "FAIL  phase 1 did not complete for $1"; fail=$((fail+1)); }; }
flip() { python3 - "$1" "$2" <<'PY'
import sys, re; p, n = sys.argv[1], int(sys.argv[2]); L = open(p).read().split('\n')
m = re.search(r'[0-9a-f]{64}', L[n]); h = m.group(0); h2 = ('0' if h[0] != '0' else '1') + h[1:]; L[n] = L[n].replace(h, h2, 1); open(p, 'w').write('\n'.join(L))
PY
}
note "Test C started $(date -u +%FT%TZ); throwaway trees under <scr> = $SCR"
# ---------------- C1-C4 ----------------
mk c1 --cut-future
rc "C1 refuses before the instant (tree copy with CUT = now + 1 day)" 2 RESUMABLE "may not start before" c1
[ -e $SCR/c1/tree/work ] && note "C1 NOTE: work/ was created" || note "C1 nothing created: the tree's work/ does not exist"
mk c2; echo '# one byte' >> $SCR/c2/tree/tools/report.py
rc "C2 refuses on a changed code file (tools/report.py + 1 line)" 2 END "code hash mismatch" c2
mk c3; echo 'x' >> $SCR/c3/fh/projects/patches/twinfix-2026-10-05/inputs/meta.tsv
rc "C3 refuses on a changed input file (the 09-27 meta.tsv + 1 line)" 2 END "input hash mismatch" c3
mk c4; echo '{"ts":1,"tok":"EXTRA"}' >> $SCR/c4/fh/.openclaw/workspace/wick-engine/logs/robinhood-tape/tape-2026-09-23.ndjson
rc "C4 refuses on a block day whose content differs from pins/block_days.tsv" 2 END "differs from pins/block_days.tsv" c4
# ---------------- H1: anchored pins ----------------
mk h1a; flip $SCR/h1a/tree/pins/code.sha256 0
rc "H1a refuses an edited pins/code.sha256 (one hash altered)" 2 END "pins/code.sha256 is not the registered pin file" h1a
mk h1b; echo '# edited' >> $SCR/h1b/tree/tools/report.py
python3 - $SCR/h1b/tree <<'PY'
import sys, hashlib; t = sys.argv[1]; p = t + '/pins/code.sha256'; L = []
for ln in open(p):
    h, f = ln.rstrip('\n').split('  ', 1); L.append(f'{hashlib.sha256(open(f, "rb").read()).hexdigest()}  {f}\n')
open(p, 'w').write(''.join(L))
PY
rc "H1b refuses regenerated code pins after an edited code file (the attack H1 names)" 2 END "pins/code.sha256 is not the registered pin file" h1b
mk h1c; flip $SCR/h1c/tree/pins/inputs.sha256 0
rc "H1c refuses an edited pins/inputs.sha256" 2 END "pins/inputs.sha256 is not the registered pin file" h1c
mk h1d; flip $SCR/h1d/tree/pins/block_days.tsv 2
rc "H1d refuses an edited pins/block_days.tsv (one block-day hash altered)" 2 END "pins/block_days.tsv is not the registered pin file" h1d
mk h1e; out=$(python3 $SCR/h1e/tree/tools/days.py verify tape $SCR/h1e/x.json $SCR/h1e/tree/pins/block_days.tsv --sha256 $(printf '0%.0s' $(seq 64)) 2026-09-22 2>&1); g=$?
[ $g = 2 ] && echo "$out" | grep -q "not the pinned" && ok=1 || ok=0
res $ok "H1e days.py refuses a block-day file that is not the pinned one (--sha256)" $g 2 "$(echo "$out" | sed "s|$SCR|<scr>|g" | cut -c1-250)"
mk h1f; python3 - $SCR/h1f/fh/projects/patches/SEALED-HOLDOUT/tape-hashes.tsv <<'PY'
import sys, re; p = sys.argv[1]; s = open(p).read(); open(p, 'w').write(re.sub(r'\t([0-9a-f])([0-9a-f]{63})\t', lambda m: '\t' + ('0' if m.group(1) != '0' else '1') + m.group(2) + '\t', s))
PY
rc "H1f the appendable registry is NOT read (every block-day row corrupted there): step 2 passes, the run stops at step 3's network stub" 2 RESUMABLE "anchors fetch failed" h1f
grep -q "2 every closed day verified" $SCR/h1f/tree/work/runlogs/exam.log && ok=1 || ok=0
res $ok "H1f exam.log shows step 2 verified the block days against pins/block_days.tsv" 0 0 "$(grep '2 every closed day verified' $SCR/h1f/tree/work/runlogs/exam.log | cut -c1-200)"
# ---------------- B1: the seam gate (tree calendar: 2026-09-20 = the join's first day; 2026-09-21 = the next day) ----------------
mk b1a; st b1a join --consist '{"2026-09-21": {"differ": 1, "fields": {"price_eth": 1}}}'
rc "B1a refuses: the day after the first (exam 09-26) differs on 1 row" 2 END "B1 seam gate" b1a
mk b1b; st b1b join --consist '{"2026-09-20": {"differ": 5878, "fields": {"price_eth": 5878, "side": 10}}}'
rc "B1b refuses: the first day (exam 09-25) differs in a field outside the other-quote price fields (side)" 2 END "outside the other-quote price fields" b1b
mk b1c; st b1c join --consist '{"2026-09-20": {"differ": 5879, "fields": {"price_eth": 5879}}}'
rc "B1c refuses: the first day differs on 5,879 rows, over the registered bound 5,878" 2 END "above the registered bound 5878" b1c
mk b1d; st b1d join --consist '{"2026-09-20": {"only_mine": 1}}'
rc "B1d refuses: the first day has a row in the exam's join only" 2 END "rows in one join only" b1d
mk b1e; st b1e join --consist '{"2026-09-20": {"differ": 5878, "fields": {"price_eth": 5878, "eth_usd": 3}}}'
rc "B1e refuses: the first day differs in eth_usd (not on the allowed list)" 2 END "eth_usd" b1e
mk b1f; st b1f join
rc "B1f control: the registered seam (5,878 rows in the five price fields, then 0) passes; phase 1 completes and STOPS" 0 - "PHASE 1 COMPLETE" b1f
[ -s $SCR/b1f/tree/work/state/manifest.sha256 ] && ok=1 || ok=0
res $ok "B1f the manifest is written ($(wc -l < $SCR/b1f/tree/work/state/manifest.sha256 2>/dev/null) files) and no engine ran" 0 0 "runs.tsv present: $([ -e $SCR/b1f/tree/work/runlogs/runs.tsv ] && echo yes || echo no)"
# ---------------- H3: commit-reveal ----------------
p1 h3a; rc "H3a phase 2 refuses without MANIFEST_POSTED (resumable: nothing statistical exists)" 2 RESUMABLE "posted first" h3a
p1 h3b; $MT post $SCR/h3b --wrong > /dev/null
rc "H3b phase 2 refuses a MANIFEST_POSTED that is not the manifest's sha256" 2 END "MANIFEST_POSTED holds" h3b
p1 h3c; $MT post $SCR/h3c > /dev/null; flip $SCR/h3c/tree/work/state/manifest.sha256 3
rc "H3c phase 2 refuses: a manifest entry altered after the hash was posted" 2 END "the manifest changed after it was posted" h3c
p1 h3d; $MT post $SCR/h3d > /dev/null; echo ' ' >> $SCR/h3d/tree/work/v4join/ethusd_coingecko.json
rc "H3d phase 2 refuses: a manifest-listed input (the ETH/USD JSON) changed after posting" 2 END "manifest check failed" h3d
p1 h3e; $MT post $SCR/h3e > /dev/null
rc "H3e control: with the right posted hash phase 2 re-checks and reaches step 8 (the stub engine then fails)" 2 END "engine run primary_rule1 failed" h3e
grep -q "PHASE 2: manifest .* posted and re-checked" $SCR/h3e/tree/work/runlogs/exam.log && ok=1 || ok=0
res $ok "H3e exam.log records the phase-2 re-check before step 8" 0 0 "$(grep 'PHASE 2: manifest' $SCR/h3e/tree/work/runlogs/exam.log | cut -c1-200)"
# ---------------- H2: resume protocol ----------------
p1 h2a; $MT post $SCR/h2a > /dev/null; $MT runrow $SCR/h2a primary_rule1 engines/engine_st_exam.js --engine-sha $(printf 'e%.0s' $(seq 64)) > /dev/null
rc "H2a refuses: an engine sha256 in runs.tsv differs from its pin" 2 END "differs from its pin" h2a
mk h2b; st h2b join; echo ' ' >> $SCR/h2b/tree/work/state/table_meta.json
rc "H2b refuses on resume: a finished step's output (state/table_meta.json) changed" 2 END "output changed since it was marked" h2b
mk h2c; st h2c join; echo "REFUSED END 2026-10-07T03:00:00Z: synthetic prior refusal (hash mismatch)" > $SCR/h2c/tree/work/state/REFUSED
rc "H2c refuses: a prior exam-ending refusal stops every later start" 2 END "a prior refusal ended the exam" h2c
mk h2d; st h2d join; echo "REFUSED RESUMABLE 2026-10-07T03:00:00Z: synthetic network failure" > $SCR/h2d/tree/work/state/REFUSED
rc "H2d control: a prior RESUMABLE refusal does not block (phase 1 completes)" 0 - "PHASE 1 COMPLETE" h2d
p1 h2e; $MT post $SCR/h2e > /dev/null; $MT runrow $SCR/h2e primary_rule1 engines/engine_st_exam.js --tamper > /dev/null
rc "H2e refuses: an engine output whose content differs from runs.tsv" 2 END "output content sha256" h2e
mk h2f; st h2f join; echo "report.md sha256 $(printf 'f%.0s' $(seq 64)) at 2026-10-07T20:00:00Z" > $SCR/h2f/tree/work/state/FINAL
rc "H2f refuses: a finished exam is never re-run (L4: CAN'T TELL (data) is final)" 2 END "the exam is finished" h2f
# ---------------- L22: memory caps ----------------
p1 l22a; $MT post $SCR/l22a > /dev/null; echo rss > $SCR/l22a/tree/STUB_ENGINE
rc "L22a an engine stopped by its RSS guard refuses as CAP, naming the cap" 2 CAP "[cap=rss:engines/engine_st_exam.js]" l22a
rc "L22b no resume without a cap change (still CAP)" 2 CAP "resume refused" l22a
$MT cap $SCR/l22a engines/engine_st_exam.js --extra-line > /dev/null
rc "L22c a 'cap change' that also edits another line refuses END" 2 END "not a registered cap change" l22a
p1 l22d; $MT post $SCR/l22d > /dev/null; echo rss > $SCR/l22d/tree/STUB_ENGINE; bash $SCR/l22d/tree/run_exam.sh > /dev/null 2>&1
$MT cap $SCR/l22d engines/engine_st_exam.js > /dev/null; echo fail > $SCR/l22d/tree/STUB_ENGINE
rc "L22d a valid cap change (RSS guard 3.2e9 -> 3.6e9, recorded) resumes: step 1 and the CAP check pass, step 8 runs again" 2 END "engine run primary_rule1 failed" l22d
grep -q "L22 cap change(s) recorded and verified" $SCR/l22d/tree/work/runlogs/exam.log && ok=1 || ok=0
res $ok "L22d exam.log records the verified cap change" 0 0 "$(grep 'L22 cap change' $SCR/l22d/tree/work/runlogs/exam.log | sed "s|$SCR|<scr>|g" | cut -c1-260)"
p1 l22e; $MT post $SCR/l22e > /dev/null; $MT cap $SCR/l22e engines/engine_st_exam.js > /dev/null
rc "L22e refuses a cap raised before that cap fired" 2 END "may be raised only after it fired" l22e
p1 l22f; $MT post $SCR/l22f > /dev/null; echo heap > $SCR/l22f/tree/STUB_ENGINE
rc "L22f an engine stopped by the heap cap refuses as CAP, naming run_engine.sh" 2 CAP "[cap=heap:tools/run_engine.sh]" l22f
p1 l22g; $MT post $SCR/l22g > /dev/null; echo rss > $SCR/l22g/tree/STUB_ENGINE; bash $SCR/l22g/tree/run_exam.sh > /dev/null 2>&1
$MT cap $SCR/l22g engines/engine_st_exam.js --lower > /dev/null
rc "L22g refuses a cap change that LOWERS the cap" 2 END "the cap was not raised" l22g
# ---------------- K: an engine that dies without completing (kernel kill) is RESUMABLE (coordinator 2026-10-07) ----------------
p1 k1; $MT post $SCR/k1 > /dev/null; echo kill > $SCR/k1/tree/STUB_ENGINE
rc "K1 an engine SIGKILLed (exit 137, 'Command terminated by signal 9', partial output) refuses RESUMABLE in phase 2" 2 RESUMABLE "died without completing" k1
echo ok > $SCR/k1/tree/STUB_ENGINE
rc "K2 resume: the dead engine is re-run unchanged and the run reaches step 9 (there the stub statistics stop it)" 2 END "stats failed for primary_rule1" k1
W=$SCR/k1/tree/work
grep -q "8 all engine runs done" $W/runlogs/exam.log && grep -q "primary_rule1: RE-RUN unchanged (previous attempt: exit=137" $W/state/ENGINE_DEATHS && grep -q "primary_rule1: the output file of a run that did not complete (partial" $W/state/ENGINE_DEATHS && ls $W/failed_outputs/primary_rule1.*.ndjson.gz > /dev/null 2>&1 && ls $W/runlogs/primary_rule1.log.died-* > /dev/null 2>&1 && ok=1 || ok=0
res $ok "K2 the death and the re-run are disclosed (ENGINE_DEATHS), the partial output and the old log kept aside unread, all engine runs done" 0 0 "$(tr '\n' ' ' < $W/state/ENGINE_DEATHS 2>/dev/null | sed "s|$SCR|<scr>|g" | cut -c1-300)"
p1 k3; $MT post $SCR/k3 > /dev/null; echo complete-fail > $SCR/k3/tree/STUB_ENGINE
rc "K3 control: an engine that exits 1 by itself after writing a COMPLETE output stays END" 2 END "engine run primary_rule1 failed (exit 1" k3
p1 k4; $MT post $SCR/k4 > /dev/null; W=$SCR/k4/tree/work
printf '\x1f\x8b\x08\x00\x00\x00\x00\x00' > $W/out/primary_rule2.ndjson.gz; echo "engine output, then nothing (run_engine.sh died too)" > $W/runlogs/primary_rule2.log
echo ok > $SCR/k4/tree/STUB_ENGINE
rc "K4 a run that died with its run_engine.sh (partial output, NO runs.tsv row): moved aside unread, re-run, reaches step 9" 2 END "stats failed for primary_rule1" k4
grep -q "primary_rule2: the output file of a run that did not complete (unrecorded" $W/state/ENGINE_DEATHS && grep -q "primary_rule2: RE-RUN unchanged (previous attempt: no runs.tsv row" $W/state/ENGINE_DEATHS && ok=1 || ok=0
res $ok "K4 the unrecorded death and its re-run are disclosed" 0 0 "$(tr '\n' ' ' < $W/state/ENGINE_DEATHS 2>/dev/null | cut -c1-300)"
p1 k5; $MT post $SCR/k5 > /dev/null; echo kill > $SCR/k5/tree/STUB_ENGINE; date -u +%FT%TZ > $SCR/k5/tree/work/state/stats.started
rc "K5 once step 9 has started (work/state/stats.started: statistics may exist), the same kernel kill is raised to END" 2 END "died without completing" k5
# ---------------- K6-K7: external stops (SIGTERM 143 e.g. a reboot, SIGHUP 129, SIGINT 130) are deaths too (coordinator 2026-10-07) --------
p1 k6; $MT post $SCR/k6 > /dev/null; echo term > $SCR/k6/tree/STUB_ENGINE
rc "K6 an engine SIGTERMed (exit 143, 'Command terminated by signal 15', e.g. a reboot) refuses RESUMABLE" 2 RESUMABLE "died without completing" k6
echo ok > $SCR/k6/tree/STUB_ENGINE
rc "K6 resume: re-run unchanged, the run reaches step 9" 2 END "stats failed for primary_rule1" k6
grep -q "primary_rule1: RE-RUN unchanged (previous attempt: exit=143" $SCR/k6/tree/work/state/ENGINE_DEATHS && ok=1 || ok=0
res $ok "K6 the SIGTERM death and the re-run are disclosed" 0 0 "$(grep 'RE-RUN' $SCR/k6/tree/work/state/ENGINE_DEATHS | cut -c1-200)"
KT=${TESTC_KIT:-$F}; mkdir -p $SCR/k7; k7ok=1; k7s=""
for c in "143|Command terminated by signal 15|0" "129|Command terminated by signal 1|0" "130|Command terminated by signal 2|0" "137|Command terminated by signal 9|0" \
         "134|Command terminated by signal 6|1" "143||1" "137|Command terminated by signal 15|1" "143|Command terminated by signal 1|1" "1|Error: thrown|1"; do
  IFS='|' read ex line want <<< "$c"
  printf 'L\tx\tE\tT0\tT1\texit=%s\n' $ex > $SCR/k7/runs.tsv; printf 'engine output\n%s\n' "$line" > $SCR/k7/L.log
  python3 $KT/tools/exam_checks.py killed $SCR/k7/runs.tsv L 0 $SCR/k7/L.log $ex > /dev/null; g=$?
  [ $g = $want ] || k7ok=0; k7s="$k7s $ex:$([ $g = 0 ] && echo RESUMABLE || echo END)"
done
res $k7ok "K7 the death rule: 143/129/130/137 with GNU time's matching line -> RESUMABLE; 134 (SIGABRT), no line, a mismatched signal, exit 1 -> END" 0 0 "$k7s"
# ---------------- KR: the RUNNER ITSELF killed mid-step, as a reboot does (SIGTERM to its whole session): the next start resumes ----------------
killtree() {  # killtree <case> <file to wait for>: start the case's runner in its own session, wait (<= 30 s) for <file>, SIGTERM the session
  local c=$SCR/$1 w=$2 g i
  setsid bash -c 'echo $$ > "$0/pgid"; exec bash "$0/tree/run_exam.sh"' $c > $c/killtree.out 2>&1 < /dev/null &
  for i in $(seq 1 60); do [ -e "$w" ] && break; sleep 0.5; done; sleep 1
  g=$(cat $c/pgid); kill -TERM -- -$g 2>/dev/null
  for i in $(seq 1 20); do pgrep -g $g > /dev/null || break; sleep 0.5; done; pkill -KILL -g $g 2>/dev/null; wait 2>/dev/null; }
p1 kr1; $MT post $SCR/kr1 > /dev/null; echo hang > $SCR/kr1/tree/STUB_ENGINE; W=$SCR/kr1/tree/work
killtree kr1 $W/runlogs/primary_rule1.log
! grep -q '^REFUSED END' $W/state/REFUSED 2>/dev/null && [ -e $W/out/primary_rule1.ndjson.gz ] && ok=1 || ok=0
res $ok "KR1 the runner SIGTERMed with its whole tree while an engine runs (phase 2): no END refusal is left behind" 0 0 "REFUSED: $(cat $W/state/REFUSED 2>/dev/null | tr '\n' ' ' | cut -c1-120)"
echo ok > $SCR/kr1/tree/STUB_ENGINE
rc "KR1 next start: the killed engine is re-run (its partial output moved aside unread) and the run reaches step 9" 2 END "stats failed for primary_rule1" kr1
grep -q "primary_rule1: RE-RUN unchanged (previous attempt: no runs.tsv row" $W/state/ENGINE_DEATHS && ok=1 || ok=0
res $ok "KR1 disclosed in ENGINE_DEATHS" 0 0 "$(tr '\n' ' ' < $W/state/ENGINE_DEATHS 2>/dev/null | cut -c1-260)"
mk kr2; st kr2 join; W=$SCR/kr2/tree/work; rm -f $W/state/days_verified.done $W/state/days_verified.sha256 $W/state/tape_block.json $W/state/wide_block.json $W/state/tape_open.json $W/state/wide_open.json
RAW=$SCR/kr2/fh/.openclaw/workspace/wick-engine/logs/robinhood-tape/tape-2026-09-22.ndjson; mv $RAW $RAW.orig; mkfifo $RAW
killtree kr2 $W/state/G3.rc
rm -f $RAW; mv $RAW.orig $RAW
! grep -q '^REFUSED' $W/state/REFUSED 2>/dev/null && ! [ -e $W/state/days_verified.done ] && grep -q "1 G3 guard test PASS" $W/runlogs/exam.log && ok=1 || ok=0
res $ok "KR2 the runner SIGTERMed mid-step 2 in phase 1 (reading a block day): no refusal, the step is not marked done" 0 0 "$(tail -1 $W/runlogs/exam.log | cut -c1-120)"
rc "KR2 next start: step 2 is redone from scratch and phase 1 completes" 0 - "PHASE 1 COMPLETE" kr2
p1 kr3; $MT post $SCR/kr3 > /dev/null; echo ok > $SCR/kr3/tree/STUB_ENGINE; echo hang > $SCR/kr3/tree/STUB_STATS; W=$SCR/kr3/tree/work
killtree kr3 $W/state/stats.started
rm -f $SCR/kr3/tree/STUB_STATS
rc "KR3 the runner SIGTERMed in step 9: the next start resumes step 9 (there the stub statistics stop it)" 2 END "stats failed for primary_rule1" kr3
grep -q "step 9 RESUMED after an interrupted start" $W/state/ENGINE_DEATHS && ok=1 || ok=0
res $ok "KR3 the resumed step 9 is disclosed in ENGINE_DEATHS" 0 0 "$(grep 'step 9' $W/state/ENGINE_DEATHS | cut -c1-200)"
# ---------------- C5, C6: the exam guard and the exam reader (synthetic files; unchanged) ----------------
t() { local name=$1 want=$2; shift 2; out=$("$@" 2>&1); got=$?
  if [ "$got" = "$want" ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi
  echo "$r  $name  (exit $got, want $want) :: $(echo "$out" | grep -E 'REFUSED|GUARD|refused|v4tape|ok|OK' | tail -2 | tr '\n' ' ' | sed "s|$SCR|<scr>|g" | cut -c1-300)" | tee -a $LOG; }
R=$SCR/guardroot/; mkdir -p $R/sealed $SCR/c5work
G=$F/tools/exam_guard.js
python3 - <<PY
R='$R'
open(R + 'tape-2026-10-07.ndjson', 'w').write('{"ts":1791331100,"tok":"FAKE-RAW-1007"}\n')
open(R + 'tape-2026-10-06.ndjson', 'w').write('{"ts":1791244900,"tok":"FAKE-RAW-1006"}\n')
open(R + 'sealed/v4-swaps-2026-09-30.ndjson', 'w').write('{"ts":1,"tok":"FAKE"}\n')
open(R + 'rows.ndjson', 'w').write('{"ts":1791331199,"tok":"OPEN-ROW"}\n{"ts":1791331200,"tok":"BLOCK-B-ROW"}\n')
open(R + 'meta.tsv', 'w').write('tok\t-\t-\tPad\n')
PY
READ='const rl=require("readline").createInterface({input:require("fs").createReadStream(process.argv[1]),crlfDelay:Infinity});(async()=>{for await(const ln of rl){let r;try{r=JSON.parse(ln);}catch{continue;}console.log("ok read",r.ts);}})();'
t "C5a STOP_DAY=2026-10-08 refused before load" 97 env STOP_DAY=2026-10-08 node -r $G -e 'console.log("BODY RAN")'
t "C5b a raw (real-root) file of day 10-07 refused before open" 97 env EXAM_GUARD_TEST_ROOT=$R node -r $G -e "$READ" $R/tape-2026-10-07.ndjson
t "C5c a raw file of day 10-06 is read" 0 env EXAM_GUARD_TEST_ROOT=$R node -r $G -e "$READ" $R/tape-2026-10-06.ndjson
t "C5d any /sealed/ path refused" 97 env EXAM_GUARD_TEST_ROOT=$R node -r $G -e "$READ" $R/sealed/v4-swaps-2026-09-30.ndjson
t "C5e a parsed row with ts >= 1791331200 aborts the run (exit 98)" 98 env EXAM_GUARD_TEST_ROOT=$R node -r $G -e "$READ" $R/rows.ndjson
t "C5f a table without a day in its name is read" 0 env EXAM_GUARD_TEST_ROOT=$R node -r $G -e "require('fs').readFileSync(process.argv[1],'utf8');console.log('ok table')" $R/meta.tsv
WC=$SCR/c5work/; mkdir -p $WC
python3 - "$G" "$SCR/exam_guard_c5.js" "$WC" <<'PY'
import sys; s = open(sys.argv[1]).read(); a = "const WORK = ['/home/green/projects/patches/sealed-exam-blockA/work/'];"
assert s.count(a) == 1; open(sys.argv[2], 'w').write(s.replace(a, f"const WORK = ['{sys.argv[3]}'];")); print('guard copy')
PY
cp $R/tape-2026-10-07.ndjson $WC/tape-2026-10-07.ndjson && cp $R/tape-2026-10-07.ndjson $WC/tape-2026-10-08.ndjson && ln -sfn $R/tape-2026-10-07.ndjson $WC/link-tape-2026-10-07.ndjson
G5=$SCR/exam_guard_c5.js
t "C5g the work-folder CUT copy of day 10-07 is read" 0 env EXAM_GUARD_TEST_ROOT=$R node -r $G5 -e "$READ" $WC/tape-2026-10-07.ndjson
t "C5h a work-folder file of day 10-08 refused" 97 env EXAM_GUARD_TEST_ROOT=$R node -r $G5 -e "$READ" $WC/tape-2026-10-08.ndjson
t "C5i a work-folder LINK that resolves to a raw 10-07 file refused" 97 env EXAM_GUARD_TEST_ROOT=$R node -r $G5 -e "$READ" $WC/link-tape-2026-10-07.ndjson
t "C6a the exam reader refuses day 2026-10-08 (V2/V3)" 1 node -e "const V=require('$F/engines/v4tape_exam.js');(async()=>{for await (const r of V.readV23Day('2026-10-08')){}})().catch(e=>{console.log(e.message);process.exit(1)})"
t "C6b the exam reader refuses day 2026-10-08 (V4)" 1 node -e "const V=require('$F/engines/v4tape_exam.js');(async()=>{for await (const r of V.readDay('2026-10-08')){}})().catch(e=>{console.log(e.message);process.exit(1)})"
t "C6c the exam engines refuse a RUN day >= the reader's SEAL_DAY (STOP_DAY=2026-10-08)" 1 env STOP_DAY=2026-10-08 node $F/engines/engine_grid_exam.js /dev/null /dev/null /dev/null /dev/null
note "RESULT pass $pass fail $fail"
rm -rf $SCR
[ $fail = 0 ]
