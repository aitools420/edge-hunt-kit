#!/bin/bash
# gate.sh <label> <logdir> — the box gate of tools/run_engine.sh (verbatim), on its own: WAITS (never forces) until no other agent engine
# is running, the edge hunter's step is not run_batch, MemAvailable > 4000 MB, swap-used rises < 64 MB over 60 s, vmstat si+so mean
# < 20000 KB/s, load < 8 and no bigdog. Used by run_exam.sh before each heavy join step (pass1, finalize, the table builders).
set -u
L=$1; LD=$2; mkdir -p "$LD"; GL=$LD/gate.log; HS=/home/green/projects/patches/edge-machine-2026-09-30/machine/status.json
while true; do
  s0=$(free -m | awk '/^Swap:/{print $3}')
  sio=$(vmstat 5 13 | tail -12 | awk '{s+=$7+$8; o+=$8} END{printf "%d %d", s/12, o/12}'); s1=$(free -m | awk '/^Swap:/{print $3}'); bd=$(pgrep -fc 'node.*rh-hypothesis-[b]igdog')
  set -- $sio; io=$1; so=$2; av=$(free -m | awk '/^Mem:/{print $7}'); ld=$(cut -d' ' -f1 /proc/loadavg)
  hs=$(python3 -c "import json; print(json.load(open('$HS')).get('step'))" 2>/dev/null || echo unreadable)
  oe=$(ps -C node -o stat=,args= | awk '$1 !~ /^T/ && /engine_v1.js|engine_st|engine_grid|seal_guard|exam_guard/' | wc -l); pe=$(ps -C node -o stat=,args= | awk '$1 ~ /^T/ && /engine_v1.js|engine_st|engine_grid|seal_guard|exam_guard/' | wc -l)
  echo "$(date -u +%FT%TZ) GATE[$L]: other engines running $oe (stopped $pe) · hunter step $hs · avail ${av}MB · load $ld · swap-used ${s0}->${s1}MB · si+so-mean ${io}KB/s (so ${so}) · bigdog $bd" >> $GL
  if [ "$oe" -eq 0 ] && [ "$hs" != run_batch ] && [ "$hs" != unreadable ] && [ "$av" -gt 4000 ] && awk "BEGIN{exit !($ld < 8)}" && [ "$bd" -eq 0 ] && [ $((s1 - s0)) -lt 64 ] && [ "$io" -lt 20000 ]; then echo "  -> GO" >> $GL; exit 0; fi
  echo "  -> wait 180 s" >> $GL; sleep 180
done
