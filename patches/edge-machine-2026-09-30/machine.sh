#!/bin/bash
# machine.sh [--dry] [--round N] — EDGE MACHINE: ONE round of the loop (DESIGN.md "X search"). Research only; not installed in any cron.
#   1 verify engine/MANIFEST.json   2 gate -> screen (loader_v1.py screen: screen.py on data.json + every v1 point) -> snapshot
#   3 search.py -> round_N/{cells.json, why.json, fit.json}   4 budget check (<= 20 cells), sha256 of cells.json BEFORE any run
#   5 A4 gate (engine/a4.sh, capped at 2 h) -> engine/run_batch.sh -> loader_v1.py add -> screen again -> snapshot     (SKIPPED by --dry)
#   6 search.py summarize: compare with the previous round -> round_N/summary.json + ONE plain-English line (line.txt)
#   7 Telegram to Chef ONLY if something changed (a new candidate, a candidate lost, the predicted best moved) and not --dry
# Safety: one round at a time (flock on machine/.lock) · KILL file (machine/KILL) checked before every step, stops cleanly ·
# resource gate before every heavy step (avail > 3 GB, swap-used not rising over 60 s, load < 8); a gate that waits > 2 h stops the round
# cleanly · never kills any process · reads nothing >= 2026-09-27T00:00Z (the engine, the store and loader_v1.py all refuse such rows).
# Env: EM_MACHINE_DIR (default ./machine) · EM_BATCH_ROOT (default $EM_MACHINE_DIR/batches) · EM_GATE_MAX_S (7200) · EM_NO_TG=1 ·
#      EM_TG_STUB=<file> (append the line there instead of sending: tests) · EM_TG_ENV (the .env holding TG_BOT_TOKEN / TG_CHAT_ID)
#      tests only: EM_SKIP_SCREEN=1 (reuse the current points.json, pre and post) · EM_SKIP_GATE=1 · EM_FAKE_BATCH=<finished batch dir>
#      (use it instead of running the engine: no A4 wait, no run_batch; with EM_STORE_DIR / EM_EXPLORER_OUT set to temp paths)
set -u; : "${KIT_ROOT:?set KIT_ROOT to the kit folder (README)}"; export KIT_ROOT   # KIT
H=$(dirname "$(readlink -f "$0")"); M=${EM_MACHINE_DIR:-$H/machine}; mkdir -p "$M"
export EM_MACHINE_DIR=$M PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
DRY=0; RND=""; TGTEST=""
while [ $# -gt 0 ]; do case "$1" in --dry) DRY=1;; --round) RND=$2; shift;; --tg-test) TGTEST=$2; shift;; *) echo "unknown arg $1"; exit 2;; esac; shift; done

tg_send() {   # $1 = the line. Token and chat id come from config (.env), never from this file; nothing secret is echoed.
  if [ -n "${EM_TG_STUB:-}" ]; then printf '%s\n' "$1" >> "$EM_TG_STUB"; return 0; fi
  local envf=${EM_TG_ENV:-} tok chat code   # KIT: no default; set EM_TG_ENV to YOUR .env (TG_BOT_TOKEN / TG_CHAT_ID) to get a line per changed round
  tok=$(grep -m1 '^TG_BOT_TOKEN=' "$envf" 2>/dev/null | cut -d= -f2- | tr -d "\"' ")
  chat=$(grep -m1 '^TG_CHAT_ID=' "$envf" 2>/dev/null | cut -d= -f2- | tr -d "\"' ")
  [ -n "$tok" ] && [ -n "$chat" ] || return 1
  for extra in "" "--doh-url https://1.1.1.1/dns-query"; do     # the box has no v6 egress (-4); router DNS can fail -> DoH retry
    code=$(curl -4 -s -m 20 $extra -o /dev/null -w '%{http_code}' --data-urlencode "chat_id=$chat" --data-urlencode "text=$1" \
           "https://api.telegram.org/bot$tok/sendMessage" 2>/dev/null)
    [ "$code" = 200 ] && return 0
  done
  return 1
}
if [ -n "${EM_FAKE_BATCH:-}" ]; then   # tests only: must not reach the real store, the real explorer file or Telegram
  case "${EM_STORE_DIR:-$H/trades}" in "$H/trades"|"$H/trades/") echo "EM_FAKE_BATCH needs EM_STORE_DIR away from $H/trades - refused"; exit 2;; esac
  [ -n "${EM_EXPLORER_OUT:-}" ] && [ "$(readlink -m "$EM_EXPLORER_OUT")" != "$H/explorer_points_v1.json" ] || { echo "EM_FAKE_BATCH needs a temp EM_EXPLORER_OUT - refused"; exit 2; }
  [ "$(readlink -m "$M")" != "$H/machine" ] || { echo "EM_FAKE_BATCH needs a temp EM_MACHINE_DIR - refused"; exit 2; }
  [ -n "${EM_TG_STUB:-}" ] || [ "${EM_NO_TG:-0}" = 1 ] || { echo "EM_FAKE_BATCH needs EM_TG_STUB or EM_NO_TG=1 - refused"; exit 2; }
fi
if [ -n "$TGTEST" ]; then [ -n "${EM_TG_STUB:-}" ] || { echo "--tg-test needs EM_TG_STUB (never sends for real)"; exit 2; }; tg_send "$TGTEST"; exit $?; fi

exec 9>"$M/.lock"; flock -n 9 || { echo "$(date -u +%FT%TZ) another round holds $M/.lock - not starting"; exit 0; }
if [ -z "$RND" ]; then last=$(ls -d "$M"/round_* 2>/dev/null | sed 's/.*round_//' | sort -n | tail -1); RND=$(( ${last:--1} + 1 )); fi
R=$M/round_$RND; mkdir -p "$R"; LOG=$R/machine.log; export A4_LOG=$R/a4.log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
stop() {   # clean stop with a summary.json that says why
  log "STOP: $1"
  python3 -c "import json,sys;json.dump(dict(round=int(sys.argv[1]),status=sys.argv[2],dry=bool(int(sys.argv[3])),changed=False),open(sys.argv[4],'w'),indent=1)" "$RND" "$1" "$DRY" "$R/summary.json"
  exit 0
}
killchk() { [ -e "$M/KILL" ] && stop "killed: $M/KILL present (before: $1)"; return 0; }
gate() {   # $1 label. avail > 3 GB, load < 8, swap-used rising < 64 MB over 60 s. Polls every 3 min; > EM_GATE_MAX_S -> stop cleanly.
  local t0=$(date +%s) av ld s0 s1
  [ "${EM_SKIP_GATE:-0}" = 1 ] && { echo "$(date -u +%FT%TZ) GATE[$1]: skipped (EM_SKIP_GATE=1, tests)" >> "$LOG"; return 0; }
  while true; do
    killchk "gate $1"
    av=$(free -m | awk '/^Mem:/{print $7}'); ld=$(cut -d' ' -f1 /proc/loadavg); s0=$(free -m | awk '/^Swap:/{print $3}')
    vmstat 5 12 > /dev/null; s1=$(free -m | awk '/^Swap:/{print $3}')
    echo "$(date -u +%FT%TZ) GATE[$1]: avail ${av} MB · load $ld · swap-used $s0->$s1 MB" >> "$LOG"
    # hunter v0: screen / search are light (seconds, small memory) — they need avail > 3 GB and load < 8; the swap-not-rising leg stays on the
    # heavy step (engine run, engine/a4.sh, unchanged). A box that swaps a little all day otherwise held a 6 s fit for hours.
    if [ "$av" -gt 3000 ] && awk "BEGIN{exit !($ld < 8)}" && { [ "${EM_LIGHT_SWAPCHECK:-0}" = 0 ] || [ $((s1 - s0)) -lt 64 ]; }; then return 0; fi
    [ $(( $(date +%s) - t0 )) -gt "${EM_GATE_MAX_S:-7200}" ] && stop "resource gate waited > ${EM_GATE_MAX_S:-7200} s at $1"
    sleep 180
  done
}
# HUNTER v0 (Chef TG 15778): status.json for the live view — round, arm, step, the cells of the current pass (labels), times
ARM=${EM_ARM:-hunter}
status() { python3 - "$M/status.json" "$RND" "$ARM" "$1" "$R/cells.json" <<'PYEOF'
import json, os, sys, datetime
f, rnd, arm, step, cj = sys.argv[1:6]
cells = [c.get('labels', {}) for c in json.load(open(cj))['cells']] if os.path.exists(cj) and step in ('picked', 'run_batch', 'loaded') else []
old = json.load(open(f)) if os.path.exists(f) else {}
st = dict(round=int(rnd), arm=arm, step=step, at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), cells=cells,
          round_started=old.get('round_started') if old.get('round') == int(rnd) else datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
json.dump(st, open(f + '.tmp', 'w'), indent=1, ensure_ascii=False); os.replace(f + '.tmp', f)
PYEOF
}
log "round $RND start (dry=$DRY, arm=$ARM) -> $R"; status start
killchk manifest
python3 "$H/engine/verify_manifest.py" --quiet >> "$LOG" 2>&1 || stop "engine MANIFEST mismatch (engine v1 changed?) - refused"
killchk screen
if [ "${EM_SKIP_SCREEN:-0}" = 1 ]; then log "screen skipped (EM_SKIP_SCREEN=1, tests)"; else
  gate screen; log "screen (pre)"; nice -n 19 python3 "$H/loader_v1.py" screen > "$R/screen_pre.log" 2>&1 || stop "screen failed (see screen_pre.log)"; fi
python3 "$H/search.py" snapshot --out "$R/screen_pre.json" >> "$LOG" 2>&1 || stop "snapshot failed"
killchk search; gate search; log "search"
status search; nice -n 19 python3 "$H/search.py" --round "$RND" --out "$R" --arm "$ARM" ${EM_SEED:+--seed $EM_SEED} ${EM_MAX_CELLS:+--cells $EM_MAX_CELLS} ${EM_PASS_SIZE:+--pass-size $EM_PASS_SIZE} >> "$LOG" 2>&1 || stop "search failed (see machine.log)"
NC=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['cells']))" "$R/cells.json")
[ "$NC" -ge 1 ] && [ "$NC" -le "${EM_MAX_CELLS:-20}" ] || stop "budget: $NC cells picked (must be 1..${EM_MAX_CELLS:-20}) - refused"
sha256sum "$R/cells.json" > "$R/cells.json.sha256"; log "picked $NC cells; pre-registered $(cut -c1-16 "$R/cells.json.sha256")"; status picked
RAN=0
if [ $DRY = 1 ]; then
  log "DRY: run_batch, loader add and the post-run screen skipped (nothing new to screen)"
else
  killchk run_batch
  B=${EM_BATCH_ROOT:-$M/batches}/round_$RND
  if [ -n "${EM_FAKE_BATCH:-}" ]; then B=$EM_FAKE_BATCH; log "TEST: EM_FAKE_BATCH=$B stands in for run_batch (no engine run)"; else
    timeout "${EM_GATE_MAX_S:-7200}" bash "$H/engine/a4.sh" "machine round $RND" "${PASS_NEED:-2800}"
    [ $? = 124 ] && stop "A4 gate waited > ${EM_GATE_MAX_S:-7200} s before run_batch"
    killchk run_batch; log "run_batch -> $B"; status run_batch
    bash "$H/engine/run_batch.sh" "$R/cells.json" "$B" >> "$LOG" 2>&1 || stop "run_batch failed or refused (see $B/runlogs/batch.log)"
  fi
  killchk loader; python3 "$H/loader_v1.py" add "$B" --round "$RND" >> "$LOG" 2>&1 || stop "loader_v1.py add failed"; status loaded
  RAN=$NC; killchk "screen (post)"
  if [ "${EM_SKIP_SCREEN:-0}" = 1 ]; then log "post-run screen skipped (EM_SKIP_SCREEN=1, tests)"; else
    gate "screen post"; log "screen (post)"
    nice -n 19 python3 "$H/loader_v1.py" screen > "$R/screen_post.log" 2>&1 || stop "post-run screen failed"; fi
  python3 "$H/search.py" snapshot --out "$R/screen_post.json" >> "$LOG" 2>&1 || stop "snapshot failed"
fi
PREV=""; for d in $(ls -d "$M"/round_* 2>/dev/null | sed 's/.*round_//' | sort -n); do
  [ "$d" -lt "$RND" ] && [ -f "$M/round_$d/fit.json" ] && [ -f "$M/round_$d/screen_pre.json" ] && PREV=$M/round_$d; done
python3 "$H/search.py" summarize --round-dir "$R" ${PREV:+--prev-dir "$PREV"} --ran "$RAN" $([ $DRY = 1 ] && echo --dry) $([ $RAN -gt 0 ] && echo --batch-dir "$B") >> "$LOG" 2>&1 || stop "summarize failed"
LINE=$(cat "$R/line.txt"); CH=$(python3 -c "import json,sys;print(int(bool(json.load(open(sys.argv[1])).get('changed'))))" "$R/summary.json")
if [ $DRY = 1 ]; then echo "NOT SENT (dry run): $LINE" > "$R/tg.txt"
elif [ "$CH" != 1 ]; then echo "NOT SENT (nothing changed): $LINE" > "$R/tg.txt"
elif [ "${EM_NO_TG:-0}" = 1 ]; then echo "NOT SENT (EM_NO_TG=1): $LINE" > "$R/tg.txt"
elif tg_send "$LINE"; then echo "SENT $(date -u +%FT%TZ): $LINE" > "$R/tg.txt"
else echo "SEND FAILED $(date -u +%FT%TZ): $LINE" > "$R/tg.txt"; fi
status done; log "done: $(head -c 60 "$R/tg.txt")…"; log "$LINE"
