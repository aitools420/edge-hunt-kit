#!/bin/bash
# run_testC.sh — TEST C (refusals), each on a THROWAWAY copy in the scratchpad; no guard is ever fired on a real file:
#  C1 the runner refuses before the instant: a byte-identical copy of run_exam.sh, run now (before 2026-10-07T00:00Z).
#  C2 the runner refuses on a changed CODE hash: a copy of the Test B tree (open days) with one code file changed by one byte.
#  C3 the runner refuses on a changed INPUT hash: the same copy with one input's registered hash changed.
#  C4 the runner refuses on a block day whose content differs from its registered tape-hashes row: the same copy with one row changed.
#  C5 the exam guard (synthetic files in a throwaway root): refuses STOP_DAY >= 10-08, a raw file of day 10-07, a work file of day 10-08,
#     a work link that resolves to a raw 10-07 file, any /sealed/ path; aborts on a parsed row with ts >= the cut; lets the 10-07 CUT copy,
#     a raw 10-06 file and a table through.
#  C6 the exam reader refuses a day >= 2026-10-08 before opening anything.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; SCR=/tmp/claude-1000/-home-green-projects/38d725a6-2ce7-42bb-8559-15f1aac1d852/scratchpad/testC
LOG=$F/tests/testC/testC.log; : > $LOG; rm -rf $SCR; mkdir -p $SCR
pass=0; fail=0
t() { local name=$1 want=$2; shift 2; out=$("$@" 2>&1); got=$?
  if [ "$got" = "$want" ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi
  echo "$r  $name  (exit $got, want $want) :: $(echo "$out" | grep -E 'REFUSED|GUARD|refused|v4tape|ok|OK' | tail -2 | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG; }
# C1
cp $F/run_exam.sh $SCR/run_exam_copy.sh; [ "$(sha256sum < $F/run_exam.sh)" = "$(sha256sum < $SCR/run_exam_copy.sh)" ] && echo "C1 copy is byte-identical to run_exam.sh" >> $LOG
t "C1 refuses before 2026-10-07T00:00:00Z (byte-identical copy, $(date -u +%FT%TZ))" 2 bash $SCR/run_exam_copy.sh
[ -e $F/work ] && echo "C1 NOTE: $F/work exists" >> $LOG || echo "C1 nothing created: $F/work does not exist" >> $LOG
# a throwaway copy of the Test B tree, with its own root (prefix replaced) and its own pins
mk() { python3 - "$1" <<'PY'
import os, sys, hashlib, shutil
src = '/home/green/projects/patches/sealed-exam-blockA/tests/testB/tree'; dst = sys.argv[1] + '/tree'
if os.path.exists(dst): shutil.rmtree(dst)
for dp, dn, fn in os.walk(src):
    if '/work' in dp: continue
    for f in fn:
        p = os.path.join(dp, f); q = p.replace(src, dst); os.makedirs(os.path.dirname(q), exist_ok=True)
        s = open(p, 'rb').read().replace(src.encode(), dst.encode()); open(q, 'wb').write(s); os.chmod(q, os.stat(p).st_mode)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
for pin in ('code.sha256', 'inputs.sha256'):
    L = []
    for ln in open(os.path.join(dst, 'pins', pin)):
        h, f = ln.rstrip('\n').split('  ', 1); L.append(f'{sha(f)}  {f}\n')
    open(os.path.join(dst, 'pins', pin), 'w').write(''.join(L))
print('copy', dst)
PY
}
# C2 (every copy's ROOT must be the copy itself)
mk $SCR/c2 > /dev/null; echo "// one byte" >> $SCR/c2/tree/tools/report.py
grep -q "^ROOT=$SCR/c2/tree$" $SCR/c2/tree/run_exam.sh && echo "C2 copy ROOT is the copy" >> $LOG || { echo "C2 copy ROOT WRONG" | tee -a $LOG; exit 1; }
t "C2 refuses on a changed code file (tools/report.py + 1 line)" 2 bash $SCR/c2/tree/run_exam.sh
# C3
mk $SCR/c3 > /dev/null; sed -i '1s/^./0/' $SCR/c3/tree/pins/inputs.sha256; [ "$(head -c1 $SCR/c3/tree/pins/inputs.sha256)" = 0 ] || sed -i '1s/^./1/' $SCR/c3/tree/pins/inputs.sha256
t "C3 refuses on a changed input hash (first registered input hash altered)" 2 bash $SCR/c3/tree/run_exam.sh
# C4
mk $SCR/c4 > /dev/null; cp $F/tests/testB/tape-hashes-testB.tsv $SCR/c4/reg.tsv
python3 - $SCR/c4/reg.tsv <<'PY'
import sys; p = sys.argv[1]; L = open(p).read().split('\n'); a = L[3].split('\t'); a[3] = ('f' if a[3][0] != 'f' else 'e') + a[3][1:]; L[3] = '\t'.join(a); open(p, 'w').write('\n'.join(L)); print('altered', a[1], a[2])
PY
sed -i "s|^REG_TSV=.*|REG_TSV=$SCR/c4/reg.tsv|" $SCR/c4/tree/run_exam.sh
t "C4 refuses on a block day whose content differs from its registered row" 2 bash $SCR/c4/tree/run_exam.sh
# C5 exam guard, synthetic
R=$SCR/guardroot/; mkdir -p $R/sealed $SCR/c5work
G=$F/tools/exam_guard.js
python3 - <<PY
import os
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
# the work-folder rules: a THROWAWAY COPY of the guard whose work folder is a scratch folder (one constant replaced), so nothing is
# created under the real exam work folder
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
# C6 the exam reader
t "C6a the exam reader refuses day 2026-10-08 (V2/V3)" 1 node -e "const V=require('$F/engines/v4tape_exam.js');(async()=>{for await (const r of V.readV23Day('2026-10-08')){}})().catch(e=>{console.log(e.message);process.exit(1)})"
t "C6b the exam reader refuses day 2026-10-08 (V4)" 1 node -e "const V=require('$F/engines/v4tape_exam.js');(async()=>{for await (const r of V.readDay('2026-10-08')){}})().catch(e=>{console.log(e.message);process.exit(1)})"
t "C6c the exam engines refuse a RUN day >= the reader's SEAL_DAY (STOP_DAY=2026-10-08)" 1 env STOP_DAY=2026-10-08 node $F/engines/engine_grid_exam.js /dev/null /dev/null /dev/null /dev/null
echo "RESULT pass $pass fail $fail" | tee -a $LOG
rm -rf $SCR
[ $fail = 0 ]
