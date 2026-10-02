#!/usr/bin/env python3
"""log_look.py <run_batch outdir> [--note TEXT] - append ONE line per batch to $KIT_ROOT/LOOKS.ndjson: every cell you ran counts toward the
multiple-testing family, the bad ones included. Logs the cells file's sha256, every cell id with its dials/filter, smoke (STOP_DAY) or full,
and whether results exist. Run it after every batch, also failed and smoke ones; send LOOKS.ndjson back with your results."""
import sys, os, json, hashlib, datetime
O = os.path.abspath(sys.argv[1]); KR = os.environ['KIT_ROOT']
note = sys.argv[sys.argv.index('--note') + 1] if '--note' in sys.argv else ''
cf = os.path.join(O, 'cells.input.json'); cj = json.load(open(cf))
log = open(os.path.join(O, 'runlogs/batch.log')).read() if os.path.exists(os.path.join(O, 'runlogs/batch.log')) else ''
rec = dict(at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), outdir=O,
           cells_sha256=hashlib.sha256(open(cf, 'rb').read()).hexdigest(), n_cells=len(cj['cells']),
           cells=[dict(id=c['id'], params=c.get('params'), filter=c.get('filter'), base=c.get('base')) for c in cj['cells']],
           smoke='SMOKE: STOP_DAY' in log, finished=os.path.exists(os.path.join(O, 'results.json')), note=note)
with open(os.path.join(KR, 'LOOKS.ndjson'), 'a') as f: f.write(json.dumps(rec) + '\n')
print(f"logged {rec['n_cells']} cell(s) -> {KR}/LOOKS.ndjson (smoke {rec['smoke']}, finished {rec['finished']})")
