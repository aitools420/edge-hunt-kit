#!/bin/bash
# seal_guard_test.sh — synthetic self-test of tools/seal_guard.js. Uses ONLY fake files in a throwaway scratch root; no real tape path is touched.
F=/home/green/projects/patches/sealed-exam-blockA; G=$F/tools/seal_guard.js
R=/tmp/claude-1000/-home-green-projects/38d725a6-2ce7-42bb-8559-15f1aac1d852/scratchpad/sealtest_blockA/; rm -rf $R; mkdir -p $R/sealed
echo '{"ts":1790000000,"tok":"FAKE-SEALED-FILE-CONTENT"}' > $R/tape-2026-09-27.ndjson
echo '{"ts":1790000000,"tok":"FAKE-SEALED-DIR-CONTENT"}' > $R/sealed/v4-swaps-2026-09-20.ndjson
printf '%s\n' '{"ts":1790467199,"tok":"FAKE-OPEN-ROW"}' '{"ts":1790467200,"tok":"FAKE-SEALED-ROW"}' '{"ts":1790000001,"tok":"AFTER"}' > $R/tape-2026-09-26.ndjson
pass=0; fail=0
t() { local name=$1 want=$2; shift 2; out=$("$@" 2>&1); got=$?; if [ "$got" = "$want" ]; then pass=$((pass+1)); r=PASS; else fail=$((fail+1)); r=FAIL; fi
      echo "$r  $name  (exit $got, want $want) :: $(echo "$out" | tr '\n' ' ' | cut -c1-160)"; }
READ='const rl=require("readline").createInterface({input:require("fs").createReadStream(process.argv[1]),crlfDelay:Infinity});
(async()=>{for await(const ln of rl){let r;try{r=JSON.parse(ln);}catch{continue;}console.log("yielded",r.ts,r.tok);}})();'
t "T1 STOP_DAY=2026-09-27 refused before load"     97 env STOP_DAY=2026-09-27 node -r $G -e 'console.log("BODY RAN")'
t "T2 STOP_DAY=2026-09-26 allowed"                  0 env STOP_DAY=2026-09-26 node -r $G -e 'console.log("body ran")'
t "T3 sealed-day file name refused before open"    97 env SEAL_TEST_ROOT=$R node -r $G -e "$READ" $R/tape-2026-09-27.ndjson
t "T4 /sealed/ dir refused before open"            97 env SEAL_TEST_ROOT=$R node -r $G -e "$READ" $R/sealed/v4-swaps-2026-09-20.ndjson
t "T5 sealed ROW inside an open-day file aborts (through try/catch)" 98 env SEAL_TEST_ROOT=$R SEAL_LOG=$R/opened.log node -r $G -e "$READ" $R/tape-2026-09-26.ndjson
t "T6 readFileSync of a sealed-day name refused"   97 env SEAL_TEST_ROOT=$R node -r $G -e "require('fs').readFileSync(process.argv[1],'utf8')" $R/tape-2026-09-27.ndjson
echo "opened.log: $(cat $R/opened.log 2>/dev/null)"
echo "RESULT pass $pass fail $fail"
rm -rf $R
[ $fail = 0 ]
