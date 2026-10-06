#!/bin/bash
# agate.sh <label> <logfile> — the memory half of the box gate, for ANALYSIS steps (row comparisons, statistics; not engines): waits until
# MemAvailable > 4000 MB, swap-used rises < 64 MB over 60 s and the edge hunter is not in run_batch. Logs every check; never forces.
set -u
L=$1; GL=$2; HS=/home/green/projects/patches/edge-machine-2026-09-30/machine/status.json
while true; do
  s0=$(free -m | awk '/^Swap:/{print $3}'); sleep 60; s1=$(free -m | awk '/^Swap:/{print $3}'); av=$(free -m | awk '/^Mem:/{print $7}')
  hs=$(python3 -c "import json; print(json.load(open('$HS')).get('step'))" 2>/dev/null || echo unreadable)
  echo "$(date -u +%FT%TZ) AGATE[$L]: hunter step $hs · avail ${av}MB · swap-used ${s0}->${s1}MB" >> $GL
  if [ "$hs" != run_batch ] && [ "$hs" != unreadable ] && [ "$av" -gt 4000 ] && [ $((s1 - s0)) -lt 64 ]; then echo "  -> GO" >> $GL; exit 0; fi
  echo "  -> wait 120 s" >> $GL; sleep 120
done
