#!/usr/bin/env python3
"""seal_scan.py <file> [<file> ...] -> one JSON line per file on stdout.
Parses EVERY line of every file (gzip / zstd / plain by extension) and reports: lines, empty lines, parse errors, rows, rows without a numeric
ts, min/max ts, and the count of rows with ts >= SEAL (2026-09-27T00:00:00Z = 1790467200). Also the key-set schemas seen (count per schema).
Exit code 3 if ANY file has a row with ts >= SEAL or a line that does not parse (both must be looked at before shipping)."""
import sys, json, gzip, io, collections
try:
    import orjson; loads = orjson.loads
except ImportError:
    loads = json.loads
SEAL = 1790467200

def opener(p):
    if p.endswith('.gz'): return gzip.open(p, 'rb')
    if p.endswith('.zst'):
        import zstandard; return io.BufferedReader(zstandard.ZstdDecompressor().stream_reader(open(p, 'rb')))
    return open(p, 'rb')

def scan(p):
    st = dict(file=p, lines=0, empty=0, parse_err=0, rows=0, no_ts=0, min_ts=None, max_ts=None, ge_seal=0, err_samples=[], ge_samples=[])
    schemas = collections.Counter()
    with opener(p) as fh:
        for ln in fh:
            st['lines'] += 1
            s = ln.strip()
            if not s: st['empty'] += 1; continue
            try: r = loads(s)
            except Exception:
                st['parse_err'] += 1
                if len(st['err_samples']) < 3: st['err_samples'].append(s[:160].decode('utf8', 'replace'))
                continue
            if not isinstance(r, dict): st['parse_err'] += 1; continue
            st['rows'] += 1
            schemas[tuple(sorted(r.keys()))] += 1
            t = r.get('ts')
            if not isinstance(t, (int, float)) or isinstance(t, bool): st['no_ts'] += 1; continue
            if st['min_ts'] is None or t < st['min_ts']: st['min_ts'] = t
            if st['max_ts'] is None or t > st['max_ts']: st['max_ts'] = t
            if t >= SEAL:
                st['ge_seal'] += 1
                if len(st['ge_samples']) < 3: st['ge_samples'].append(t)
    st['schemas'] = [[list(k), v] for k, v in schemas.most_common()]
    return st

bad = 0
for p in sys.argv[1:]:
    st = scan(p)
    if st['ge_seal'] or st['parse_err']: bad = 1
    print(json.dumps(st), flush=True)
sys.exit(3 if bad else 0)
