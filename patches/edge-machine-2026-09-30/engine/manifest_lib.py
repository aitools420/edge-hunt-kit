#!/usr/bin/env python3
"""manifest_lib.py - EDGE MACHINE v1, KIT LAYOUT (replaces the origin box's manifest_lib.py; see kit/CHANGES.md).
What MANIFEST.json pins, resolved under $KIT_ROOT instead of the origin box's absolute paths:
  code      every pipeline file in this folder (sha256 of the KIT file; code_original = the origin file's sha256, which kit/unpatch_check.py
            reproduces from the kit file by reversing kit/PATCHES.json)
  inputs    the frozen input tables (byte-identical to the origin) + the sha256 of each DECOMPRESSED table
  external  read-only files the pipeline imports or reads, as paths relative to $KIT_ROOT
  data      per day: the files engine_v1.js reads (V4 join file, V2/V3 day file), each with size + sha256 of the FILE, and the sha256 of
            the day's DECOMPRESSED content = the origin manifest's content hash (the same bytes the frozen engine read on the origin box)
engine_sha256 and cost_version are the ORIGIN manifest's labels: the engine file is byte-identical and every cost-model file is either
identical or differs only in the path lines listed in kit/PATCHES.json."""
import hashlib, os, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ['KIT_ROOT']; P = ROOT + '/patches'
CODE = ['engine_v1.js', 'guard.js', 'guard_test.js', 'hop.py', 'qpools.js', 'build_hop_v1.py', 'pool_costs_v1.py', 'reduce_v1.py', 'analyze_v1.py',
        'prepare_v1.py', 'a4.sh', 'run_pass_v1.sh', 'run_batch.sh', 'manifest_lib.py', 'verify_manifest.py', 'test_seal.sh']
INPUTS = ['inputs/meta.tsv.gz', 'inputs/scam.tsv.gz', 'inputs/poolfee_lf.tsv.gz', 'inputs/creators.tsv.gz', 'inputs/poolquote.tsv.gz', 'pool_costs_v1.json']
EXTERNAL = ['patches/v4-join-2026-09-27/v4tape.js', 'patches/v4-join-2026-09-27/pools.js', 'patches/v4-join-2026-09-27/meta.json',
            'patches/v4-join-2026-09-27/unknown_keys.json', 'patches/pons-feeterms-2026-09-27/pons_fee_terms.json',
            'patches/realism-2026-09-27/realism.py', 'patches/realism-2026-09-27/pool_costs.json', 'patches/realism-2026-09-27/pool_fees.json',
            'patches/realism-2026-09-27/v23_costs.json', 'patches/realism-2026-09-27/tax_table.json', 'patches/realism-2026-09-27/ethusd.json',
            'patches/realism-2026-09-27/latency.json', 'patches/blood-realcost-2026-09-27/recost.py', 'patches/blood-exitgrid-2026-09-27/analyze_xg.py',
            'patches/v4-real-cost-2026-09-27/pons_launches.json', 'patches/v4-real-cost-2026-09-27/m2b_rows.json',
            'patches/blood-realcost-2026-09-27/pons_launches_extra.json', 'patches/blood-skeleton1-2026-09-27/pons_launches_sk.json',
            'kit/kitpath.js']   # KIT: the node path rewrite is pinned too
DAYS = [f'2026-09-{d:02d}' for d in range(8, 27)]
WE = ROOT + '/tape/v23'; J = P + '/v4-join-2026-09-27/out'

def sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''): h.update(b)
    return h.hexdigest()
def sha_plain(path):
    h = hashlib.sha256()
    with gzip.open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def rel(p): return os.path.relpath(p, ROOT)
def day_parts(d):
    """the files engine_v1.js reads for day d, in its order = v4tape.js v4Path / v23Paths under the kit path rewrite"""
    parts = []
    p = f'{J}/v4-swaps-{d}.ndjson.gz'
    if os.path.exists(p): parts.append(p)
    if os.path.isdir(WE + '/archive'):
        for m in sorted(os.listdir(WE + '/archive')):
            g = f'{WE}/archive/{m}/tape-{d}.ndjson.gz'
            if os.path.exists(g): parts.append(g)
    l = f'{WE}/robinhood-tape/tape-{d}.ndjson'
    if os.path.exists(l): parts.append(l)
    return parts
def day_content(d):
    """sha256 of the V4 part's decompressed bytes + sha256 of the concatenated decompressed V2/V3 parts (same definition as the origin)"""
    ps = day_parts(d); v4 = [p for p in ps if p.startswith(J)]; v23 = [p for p in ps if not p.startswith(J)]
    hv = hashlib.sha256()
    for p in v4:
        with gzip.open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): hv.update(b)
    h2 = hashlib.sha256()
    for p in v23:
        with (gzip.open(p, 'rb') if p.endswith('.gz') else open(p, 'rb')) as f:
            for b in iter(lambda: f.read(1 << 20), b''): h2.update(b)
    return dict(v4=hv.hexdigest(), v23=h2.hexdigest())
