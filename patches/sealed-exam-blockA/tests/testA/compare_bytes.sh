#!/bin/bash
# compare_bytes.sh <a.ndjson.gz> <b.ndjson.gz> — Test A's comparison: the sha256 of every line but the _meta line (run time, RSS),
# plus the _meta line without its two timing keys. Prints GREEN when both match, RED otherwise.
a=$(zcat "$1" | grep -v '^{"_meta"' | sha256sum | cut -c1-64); b=$(zcat "$2" | grep -v '^{"_meta"' | sha256sum | cut -c1-64)
ma=$(zcat "$1" | grep '^{"_meta"' | python3 -c "import json,sys;m=json.loads(sys.stdin.read())['_meta'];[m.pop(k,None) for k in ('sec','peakRssMB')];print(json.dumps(m,sort_keys=True))" | sha256sum | cut -c1-16)
mb=$(zcat "$2" | grep '^{"_meta"' | python3 -c "import json,sys;m=json.loads(sys.stdin.read())['_meta'];[m.pop(k,None) for k in ('sec','peakRssMB')];print(json.dumps(m,sort_keys=True))" | sha256sum | cut -c1-16)
na=$(zcat "$1" | wc -l); nb=$(zcat "$2" | wc -l)
if [ "$a" = "$b" ] && [ "$ma" = "$mb" ]; then echo "GREEN rows $na=$nb content $a meta $ma"; else echo "RED rows $na vs $nb content $a vs $b meta $ma vs $mb"; fi
