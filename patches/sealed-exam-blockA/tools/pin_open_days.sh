#!/bin/bash
# pin_open_days.sh — sha256 of the uncompressed content of every OPEN raw day file the exam and the tests read (tape 09-08..09-26,
# V4-wide 09-18..09-26; all rows < 2026-09-27T00:00Z), in the tape-hashes.tsv format, so the runner verifies open days the same way.
set -u
F=/home/green/projects/patches/sealed-exam-blockA; O=$F/pins/open_days.tsv
echo -e 'computed_utc\tday\tfeed\tsha256_of_uncompressed_content\tbytes_uncompressed\tsource_file' > $O.tmp
for d in $(python3 -c "import datetime as D;s=D.date(2026,9,8);print(' '.join(str(s+D.timedelta(i)) for i in range(19)))"); do
  for k in tape wide; do
    [ $k = wide ] && [[ "$d" < "2026-09-18" ]] && continue
    p=$(python3 -c "
import glob,sys
P={'tape':['/home/green/.openclaw/workspace/wick-engine/logs/robinhood-tape/tape-{d}.ndjson','/home/green/.openclaw/workspace/wick-engine/logs/robinhood-tape/tape-{d}.ndjson.gz','/home/green/.openclaw/workspace/wick-engine/logs/archive/*/tape-{d}.ndjson.gz','/home/green/.openclaw/workspace/wick-engine/logs/archive/*/tape-{d}.ndjson'],'wide':['/home/green/noxabot/logs/v4-wide/uniswap-v4-wide-{d}.ndjson','/home/green/noxabot/logs/v4-wide/uniswap-v4-wide-{d}.ndjson.gz']}
h=sorted(set(x for p in P['$k'] for x in glob.glob(p.format(d='$d'))))
print(h[0] if len(h)==1 else 'AMBIG:'+','.join(h))")
    case "$p" in AMBIG*) echo "AMBIGUOUS $k $d $p"; exit 2;; esac
    r=$(nice -n 19 python3 $F/tools/days.py hash "$p")
    feed=$([ $k = tape ] && echo v2v3-tape || echo v4-wide)
    echo -e "$(date -u +%FT%TZ)\t$d\t$feed\t$(echo "$r" | cut -f1)\t$(echo "$r" | cut -f2)\t$p" >> $O.tmp
    echo "$d $k $(echo "$r" | cut -c1-16)"
  done
done
mv $O.tmp $O
