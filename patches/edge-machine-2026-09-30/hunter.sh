#!/bin/bash
# hunter.sh — EDGE HUNTER v0 (Chef Y TG 15778, voice TG 15763/15766; built by the coordinator, Chef TG 15797). A plain script, no AI in the loop.
# Runs machine.sh rounds back to back until a wall-clock budget or machine/KILL. Arms alternate: hunter (GP/UCB picks, search.py) and
# random (the same number of cells, uniformly from the SAME legal pool, seeded) — so the 24 h trial can be judged hunter vs random at
# EQUAL passes. Every round keeps machine.sh's own rules: one round at a time (flock), KILL file, resource gates, engine v1 A4 gate,
# pre-registered cells.json hash, nothing read >= 2026-09-27T00:00Z, Telegram only when something changed.
# After a round that loaded cells it rebuilds the explorer (patches/edge-explorer/build.py) unless build.py was edited in the last 2 min;
# it does NOT ship the page — it writes machine/ship_pending and the coordinator ships.
# Env: HUNT_HOURS (24) · EM_MAX_CELLS (20) · EM_PASS_SIZE (20) · HUNT_FIRST_ARM (hunter) · HUNT_DRY=1 (every round --dry) · HUNT_MAX_ROUNDS
set -u
H=$(dirname "$(readlink -f "$0")"); M=${EM_MACHINE_DIR:-$H/machine}; mkdir -p "$M"
END=$(( $(date +%s) + ${HUNT_HOURS:-24} * 3600 )); ARM=${HUNT_FIRST_ARM:-hunter}; N=0
export EM_MAX_CELLS=${EM_MAX_CELLS:-20} EM_PASS_SIZE=${EM_PASS_SIZE:-20}
hl() { echo "$(date -u +%FT%TZ) $*" >> "$M/hunter.log"; }
exec 8>"$M/.hunter.lock"; flock -n 8 || { echo "another hunter.sh is running - not starting"; exit 0; }
hl "HUNTER start: budget ${HUNT_HOURS:-24} h, cells/round $EM_MAX_CELLS, pass size $EM_PASS_SIZE, first arm $ARM, dry ${HUNT_DRY:-0}"
while [ "$(date +%s)" -lt "$END" ]; do
  [ -e "$M/KILL" ] && { hl "KILL present - hunter stops"; break; }
  [ -n "${HUNT_MAX_ROUNDS:-}" ] && [ "$N" -ge "$HUNT_MAX_ROUNDS" ] && { hl "max rounds $N reached"; break; }
  SEED=$(( $(date +%s) % 1000000 ))
  hl "round with arm=$ARM seed=$SEED"
  EM_ARM=$ARM EM_SEED=$SEED bash "$H/machine.sh" $([ "${HUNT_DRY:-0}" = 1 ] && echo --dry) >> "$M/hunter.log" 2>&1
  last=$(ls -d "$M"/round_* 2>/dev/null | sed 's/.*round_//' | sort -n | tail -1); S="$M/round_$last/summary.json"
  st=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('status') or ('ran %s' % d.get('cells_run')))" "$S" 2>/dev/null)
  hl "round $last ($ARM): $st"
  ran=$(python3 -c "import json,sys;print(int(json.load(open(sys.argv[1])).get('cells_run') or 0))" "$S" 2>/dev/null || echo 0)
  case "$st" in *"killed"*|*"gate waited"*|*"MANIFEST"*) hl "round stopped ($st) - hunter pauses 10 min"; sleep 600; continue;; esac
  if [ "${ran:-0}" -gt 0 ] && [ -n "${EM_EXPLORER_DIR:-}" ]; then   # KIT: no explorer ships; set EM_EXPLORER_DIR to a folder with your own build.py
    BP=$EM_EXPLORER_DIR/build.py
    if [ $(( $(date +%s) - $(stat -c %Y "$BP") )) -lt 120 ]; then hl "build.py edited < 2 min ago - explorer rebuild skipped this round"
    else ( cd "$EM_EXPLORER_DIR" && nice -n 19 timeout 1200 python3 build.py > "$M/round_$last/explorer_build.log" 2>&1 ) \
           && { date -u +%FT%TZ > "$M/ship_pending"; hl "explorer rebuilt (ship pending)"; } || hl "explorer rebuild FAILED (see round_$last/explorer_build.log)"; fi
  fi
  N=$((N + 1)); [ "$ARM" = hunter ] && ARM=random || ARM=hunter
done
hl "HUNTER end after $N rounds"
