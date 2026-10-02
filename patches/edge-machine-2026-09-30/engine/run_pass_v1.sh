#!/bin/bash
# run_pass_v1.sh <outdir> <pass name> [need MB] — A4 gate, then ONE engine_v1.js pass on <outdir>/passes/<name>.txt, with a watchdog that
# stops THIS engine (its exact PID, never anything else) if avail < 2.5 GB; the pass is then retried whole after A4 passes again.
# = the hunts' run_pass.sh with the paths as arguments. Writes <outdir>/<name>.ndjson.gz and <outdir>/runlogs/<name>.log.
E=$(dirname "$(readlink -f "$0")"); O=$1; N=$2; NEED=${3:-2800}; export A4_LOG=$O/runlogs/a4.log
for try in 1 2 3 4 5 6; do
  bash $E/a4.sh "$N try $try" $NEED
  ( cd $E && CELL_IDS=$O/passes/$N.txt exec nice -n 19 ionice -c3 /usr/bin/time -v node --max-old-space-size=2400 engine_v1.js \
      $O/$N.ndjson.gz $O/in/meta.tsv $O/in/scam.tsv $O/in/poolfee_lf.tsv $O/in/creators.tsv $O/engine_cells.json ) > $O/runlogs/$N.log 2>&1 &
  TP=$!; sleep 2; EP=$(pgrep -P $TP -f 'engine_v1.js' | head -1)
  echo "$(date -u +%FT%TZ) PASS $N try $try started (time pid $TP, engine pid $EP)" >> $A4_LOG
  killed=0
  while kill -0 $TP 2>/dev/null; do
    av=$(free -m | awk '/^Mem:/{print $7}')
    if [ "$av" -lt 2500 ]; then
      echo "$(date -u +%FT%TZ) WATCHDOG stop PASS $N (avail $av MB): kill engine pid $EP" >> $A4_LOG
      [ -n "$EP" ] && kill $EP; killed=1; wait $TP; break
    fi
    sleep 10
  done
  wait $TP 2>/dev/null; rc=$?
  if [ $killed -eq 0 ] && grep -q '"peakRssMB"' $O/runlogs/$N.log; then echo "$(date -u +%FT%TZ) PASS $N DONE exit $rc" >> $A4_LOG; exit 0; fi
  if [ $killed -eq 0 ] && grep -qE "sealed|unknown cell dial|RSS guard" $O/runlogs/$N.log; then echo "$(date -u +%FT%TZ) PASS $N REFUSED/FAILED (see log) - not retried" >> $A4_LOG; exit 3; fi
  echo "$(date -u +%FT%TZ) PASS $N try $try FAILED (exit $rc, killed $killed) - retry after A4" >> $A4_LOG; sleep 300
done
echo "$(date -u +%FT%TZ) PASS $N GAVE UP" >> $A4_LOG; exit 1
