#!/usr/bin/env python3
"""parity_check.py <run_batch outdir> [<reference results.json> <reference trades.ndjson.gz>]
Compares a run of parity/cells_parity.json with the PUBLISHED engine-v1 parity outputs (default: the files in engine/parity/):
every cell's results.json record must be JSON-identical, and the trade rows (sorted, byte for byte) identical. Exit 0 = PARITY, 1 = differs."""
import sys, os, json, gzip
O = sys.argv[1]; KR = os.environ.get('KIT_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PD = os.path.join(KR, 'patches/edge-machine-2026-09-30/engine/parity')
RR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PD, 'results_v1_parity.json')
RT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(PD, 'trades_v1_parity.ndjson.gz')
a, b = json.load(open(os.path.join(O, 'results.json'))), json.load(open(RR))
ra = sorted(l.rstrip('\n') for l in gzip.open(os.path.join(O, 'trades.ndjson.gz'), 'rt'))
rb = sorted(l.rstrip('\n') for l in gzip.open(RT, 'rt'))
bad = 0
for c in sorted(set(a['cells']) | set(b['cells'])):
    same = json.dumps(a['cells'].get(c), sort_keys=True) == json.dumps(b['cells'].get(c), sort_keys=True)
    J = (a['cells'].get(c) or {}).get('JUDGE') or {}; raw = (J.get('real60h') or {}).get('raw') or {}
    print(f"{c:22s} record {'IDENTICAL' if same else 'DIFFERS  '}  JUDGE n {J.get('n')} mean {raw.get('mean')} lower {(raw.get('ci95') or [None])[0]}")
    bad += not same
rows_same = ra == rb
print(f"trade rows: run {len(ra)} vs reference {len(rb)} -> {'IDENTICAL (sorted, byte for byte)' if rows_same else 'DIFFER'}")
for k in ('engine_sha256', 'cost_version'): print(f'{k}: run {a[k][:24]} reference {b[k][:24]} ->', 'same' if a[k] == b[k] else 'DIFFERENT')
ok = not bad and rows_same and all(a[k] == b[k] for k in ('engine_sha256', 'cost_version'))
print('PARITY' if ok else 'NO PARITY'); sys.exit(0 if ok else 1)
