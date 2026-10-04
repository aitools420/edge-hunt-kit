#!/bin/bash
# kit/setup.sh - put the tape and the big pool table in place, verify every byte, then run the kit's own checks.
#   KIT_ROOT=/path/to/edge-hunt-kit bash kit/setup.sh [--from DIR] [--scan]
#   --from DIR  use tape files you already downloaded into DIR (names as in kit/TAPE_MANIFEST.sha256) instead of downloading them
#   --scan      also run kit/seal_scan.py over every tape row (a few minutes; proves no row is at/after 2026-09-27T00:00Z)
# Downloads (no login needed): https://github.com/aitools420/edge-hunt-tape/releases/tag/tape-2026-09-26
# Every file is checked against kit/TAPE_MANIFEST.sha256 BEFORE it is moved into place; compare that manifest with the one posted on the forum.
set -euo pipefail
: "${KIT_ROOT:?set KIT_ROOT to the folder this kit was cloned into}"; cd "$KIT_ROOT"
FROM=""; SCAN=0
while [ $# -gt 0 ]; do case "$1" in --from) FROM=$2; shift;; --scan) SCAN=1;; *) echo "unknown arg $1"; exit 2;; esac; shift; done
URL=https://github.com/aitools420/edge-hunt-tape/releases/download/tape-2026-09-26
DL=$KIT_ROOT/downloads; mkdir -p "$DL" tape/v23/archive/2026-09 patches/v4-join-2026-09-27/out
for f in $(awk '{print $2}' kit/TAPE_MANIFEST.sha256); do
  [ -f "$DL/$f" ] && continue
  if [ -n "$FROM" ]; then cp "$FROM/$f" "$DL/$f"; else echo "download $f"; curl -fL --retry 3 -o "$DL/$f.part" "$URL/$f" && mv "$DL/$f.part" "$DL/$f"; fi
done
( cd "$DL" && sha256sum -c "$KIT_ROOT/kit/TAPE_MANIFEST.sha256" ) || { echo "SHA256 MISMATCH - nothing moved into place; delete the bad file(s) in $DL and re-run"; exit 1; }
for f in $(awk '{print $2}' kit/TAPE_MANIFEST.sha256); do
  case "$f" in tape-*) mv "$DL/$f" tape/v23/archive/2026-09/;; v4-swaps-*) mv "$DL/$f" patches/v4-join-2026-09-27/out/;; esac
done
rmdir "$DL" 2>/dev/null || true
if [ ! -f patches/v4-join-2026-09-27/meta.json ]; then zstd -d -q --long=27 patches/v4-join-2026-09-27/meta.json.zst -o patches/v4-join-2026-09-27/meta.json; fi
sha256sum -c kit/META_JSON.sha256
if [ "$SCAN" = 1 ]; then   # an if-block, so a failing scan stops setup under set -e (pond #284)
  python3 kit/seal_scan.py tape/v23/archive/2026-09/*.gz patches/v4-join-2026-09-27/out/*.gz > seal_scan.ndjson
  echo "seal scan: every row < 2026-09-27T00:00Z (seal_scan.ndjson)"
fi
python3 kit/unpatch_check.py | tail -1
python3 patches/edge-machine-2026-09-30/engine/verify_manifest.py
( cd patches/edge-machine-2026-09-30/engine && bash test_seal.sh | tail -1 )
echo "SETUP OK - next: bash patches/edge-machine-2026-09-30/engine/run_batch.sh patches/edge-machine-2026-09-30/engine/parity/cells_parity.json runs/parity"
