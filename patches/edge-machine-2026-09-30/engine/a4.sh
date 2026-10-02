#!/bin/bash
# a4.sh <label> [need MB] — A4 resource gate (AUTHORITY A4/G23), checked before EVERY heavy step. WAITS in 3-min polls, never forces,
# never kills anything. = ../../blood-hunt3-2026-09-29/a4.sh (the strictest of the hunts' copies) with only the log path as a variable.
# All must hold: avail > 3 GB + need · load < 8 · swap-used not rising (< 64 MB over the 60 s) · vmstat si+so mean < 20,000 KB/s ·
# no bigdog job (a node process with "bigdog" in its command line; V1: shells that merely mention the word no longer block) · NO other backtest engine (any node process running engine_*.js — one engine pass at a time on this box) ·
# minute of the hour in [06, 48] and no RH heater (rh-wallet-labels.js / rh-smart-money.js, heap up to 3.5 GB at :00) · the Blood rule #3
# live feed's status.json phase == "live" (if the file exists).   Log: $A4_LOG (default /dev/stderr).
NEED=${2:-0}; LOG=${A4_LOG:-/dev/stderr}; ST=${A4_STATUS_FILE:-/nonexistent}   # KIT: the origin box's live-feed status file; unset = no such feed
while true; do
  av=$(free -m | awk '/^Mem:/{print $7}'); ld=$(cut -d' ' -f1 /proc/loadavg); s0=$(free -m | awk '/^Swap:/{print $3}')
  sio=$(vmstat 5 13 | tail -12 | awk '{s+=$7+$8} END{printf "%d", s/12}'); s1=$(free -m | awk '/^Swap:/{print $3}')
  bd=0; for q in $(pgrep -f "[b]igdog"); do [ "$(cat /proc/$q/comm 2>/dev/null)" = node ] && bd=$((bd + 1)); done   # V1: a NODE process (rh-hypothesis-bigdog.js); a shell whose text mentions it is not it
  oe=$(pgrep -f "^(/usr/bin/)?node .*engine_[A-Za-z0-9]*\.js" | wc -l)
  ph=$( [ -f $ST ] && python3 -c "import json;print(json.load(open('$ST')).get('phase'))" 2>/dev/null || echo nofile )
  mn=$((10#$(date -u +%M))); ht=$(pgrep -f "^(/usr/bin/)?node .*rh-(wallet-labels|smart-money)\.js" | wc -l)
  av2=$(free -m | awk '/^Mem:/{print $7}'); oe2=$(pgrep -f "^(/usr/bin/)?node .*engine_[A-Za-z0-9]*\.js" | wc -l)
  echo "$(date -u +%FT%TZ) A4[$1]: avail ${av}->${av2}MB (need > $((3000 + NEED))) · load $ld · swap-used $s0->$s1 MB · si+so mean ${sio} KB/s · bigdog $bd · other engines $oe/$oe2 · min $mn · heater $ht · blood3 $ph" >> $LOG
  if [ "$av2" -gt $((3000 + NEED)) ] && awk "BEGIN{exit !($ld < 8)}" && [ "$bd" -eq 0 ] && [ $((s1 - s0)) -lt 64 ] && [ "$sio" -lt 20000 ] \
     && [ "$oe" -eq 0 ] && [ "$oe2" -eq 0 ] && [ "$mn" -ge 6 ] && [ "$mn" -le 48 ] && [ "$ht" -eq 0 ] && { [ "$ph" = live ] || [ "$ph" = nofile ]; }; then echo "  -> GO" >> $LOG; exit 0; fi
  echo "  -> wait 180 s" >> $LOG; sleep 180
done
