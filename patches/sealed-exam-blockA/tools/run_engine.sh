#!/bin/bash
# run_engine.sh <label> <engine.js> <meta.tsv> <scam.tsv> <poolfee.tsv> <outdir> <logdir> <guard.js> [VAR=value ...]
# ONE engine pass, the twinfix way (twinfix-2026-10-05/tools/run_engine.sh, generalised to take the inputs, the output folder
# and the preloaded guard as arguments):
#  1 GATE (waits, never forces): no other agent engine RUNNING (node processes matching engine_v1.js|engine_st|engine_grid|
#    seal_guard|exam_guard; a STOPPED one is logged, not counted), the edge hunter's machine/status.json step is NOT "run_batch",
#    MemAvailable > 4000 MB, swap-used rising < 64 MB over 60 s, vmstat 5 13 mean si+so < 20000 KB/s, load < 8, no bigdog.
#    A failed check is logged and re-checked after 180 s.
#  2 nice -n 19 ionice -c3, node --max-old-space-size=3000, the guard PRELOADED with `node -r`, STOP_DAY unset unless passed.
#  3 monitor only: logs MemAvailable < 1200 MB and a STOPPED engine; it never kills anything.
#  4 output -> <outdir>/<label>.ndjson.gz ; tape files opened -> <logdir>/<label>.opened ; one summary line -> <logdir>/runs.tsv
set -u
L=$1; E=$2; META=$3; SCAM=$4; POOLF=$5; OD=$6; LD=$7; G=$8; shift 8
ENVV=("$@"); mkdir -p "$OD" "$LD"
GL=$LD/gate.log; HS=/home/green/projects/patches/edge-machine-2026-09-30/machine/status.json
SCR=${EXAM_SCRATCH:-/tmp/claude-1000/-home-green-projects/38d725a6-2ce7-42bb-8559-15f1aac1d852/scratchpad}
mkdir -p "$SCR"
gate() {
  while true; do
    s0=$(free -m | awk '/^Swap:/{print $3}')
    sio=$(vmstat 5 13 | tail -12 | awk '{s+=$7+$8; o+=$8} END{printf "%d %d", s/12, o/12}'); s1=$(free -m | awk '/^Swap:/{print $3}'); bd=$(pgrep -fc 'node.*rh-hypothesis-[b]igdog')
    set -- $sio; io=$1; so=$2; av=$(free -m | awk '/^Mem:/{print $7}'); ld=$(cut -d' ' -f1 /proc/loadavg)
    hs=$(python3 -c "import json; print(json.load(open('$HS')).get('step'))" 2>/dev/null || echo unreadable)
    oe=$(ps -C node -o stat=,args= | awk '$1 !~ /^T/ && /engine_v1.js|engine_st|engine_grid|seal_guard|exam_guard/' | wc -l); pe=$(ps -C node -o stat=,args= | awk '$1 ~ /^T/ && /engine_v1.js|engine_st|engine_grid|seal_guard|exam_guard/' | wc -l)
    echo "$(date -u +%FT%TZ) GATE[$L]: other engines running $oe (stopped $pe) · hunter step $hs · avail ${av}MB · load $ld · swap-used ${s0}->${s1}MB · si+so-mean ${io}KB/s (so ${so}) · bigdog $bd" >> $GL
    if [ "$oe" -eq 0 ] && [ "$hs" != run_batch ] && [ "$hs" != unreadable ] && [ "$av" -gt 4000 ] && awk "BEGIN{exit !($ld < 8)}" && [ "$bd" -eq 0 ] && [ $((s1 - s0)) -lt 64 ] && [ "$io" -lt 20000 ]; then echo "  -> GO" >> $GL; return 0; fi
    echo "  -> wait 180 s" >> $GL; sleep 180
  done
}
case "$E" in *grid*) OUTA=$OD/$L.ndjson.gz; GZ=0;; *) OUTA=$SCR/$L.ndjson; GZ=1;; esac
rm -f $LD/$L.opened.raw
gate
T0=$(date -u +%FT%TZ)
env -u STOP_DAY "${ENVV[@]}" SEAL_LOG=$LD/$L.opened.raw /usr/bin/time -v nice -n 19 ionice -c3 node -r "$G" --max-old-space-size=3000 \
  "$E" "$OUTA" "$META" "$SCAM" "$POOLF" > $LD/$L.log 2>&1 &
TP=$!; sleep 2; EP=$(pgrep -P $TP | head -1); low=0
echo "$(date -u +%FT%TZ) START $L engine=$E guard=$G env=[${ENVV[*]:-}] time_pid=$TP engine_pid=$EP" >> $GL
while kill -0 $TP 2>/dev/null; do
  sleep 15; av=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
  stt=$(ps -o stat= -p $EP 2>/dev/null | cut -c1); [ "$stt" = T ] && [ "$low" != T ] && echo "$(date -u +%FT%TZ) PAUSED $L engine $EP is stopped (SIGSTOP) - waiting, never killed" >> $GL; [ -n "$stt" ] && low=$stt
  [ "$av" -lt 1200 ] && echo "$(date -u +%FT%TZ) LOWMEM $L: MemAvailable ${av}MB (monitor only, no kill)" >> $GL
done
wait $TP; rc=$?; T1=$(date -u +%FT%TZ)
if [ $rc = 0 ] && [ $GZ = 1 ]; then gzip -n -c $OUTA > $OD/$L.ndjson.gz && rm -f $OUTA; OUTA=$OD/$L.ndjson.gz; fi
[ $rc != 0 ] && rm -f $SCR/$L.ndjson
sort -u $LD/$L.opened.raw > $LD/$L.opened 2>/dev/null; rm -f $LD/$L.opened.raw
el=$(grep -m1 'Elapsed (wall' $LD/$L.log | awk '{print $NF}'); us=$(grep -m1 'User time' $LD/$L.log | awk '{print $NF}'); mx=$(grep -m1 'Maximum resident' $LD/$L.log | awk '{print $NF}')
sha=$( [ $rc = 0 ] && zcat $OUTA | sha256sum | cut -c1-64 || echo - )
printf '%s\t%s\t%s\t%s\t%s\texit=%s\telapsed=%s\tuser_s=%s\tmaxrss_kb=%s\topened=%s\tcontent_sha256=%s\tguard=%s\tenv=%s\n' "$L" "$(sha256sum $E | cut -c1-64)" "$E" "$T0" "$T1" "$rc" "$el" "$us" "$mx" \
  "$(wc -l < $LD/$L.opened 2>/dev/null || echo 0)" "$sha" "$(sha256sum $G | cut -c1-16)" "${ENVV[*]:-}" >> $LD/runs.tsv
echo "$(date -u +%FT%TZ) END $L exit $rc elapsed $el" >> $GL
exit $rc
