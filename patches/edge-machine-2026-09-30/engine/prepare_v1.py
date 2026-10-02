#!/usr/bin/env python3
"""prepare_v1.py - EDGE MACHINE v1: validate a batch's cells.json and split it into engine passes. No data is read.
cells.json = {"cells": [cell, ...], "pass_size": 40 (optional)}; cell = {
  "id": "D25H72T40X12",                       # [A-Za-z0-9._-]+, unique
  "params": {dial: value, ...},                # engine dials (engine_v1.js DIALS) + rngId / last72; omitted keys = the engine's BASE
  "filter": {"min_dip_sec": 1200, "min_sells": 10},   # optional token filter(s), applied as a SPLIT of "base" (both keys = both must hold)
  "base": "<id of an unfiltered cell in this file>",  # required with "filter", forbidden without it; params must equal the base's
  "stat_seed": 20262627,                       # optional bootstrap seed (default: from the id, batch-independent)
  "labels": {...}}                             # optional, copied to results.json
Writes <outdir>/engine_cells.json (what the engine runs: the unfiltered cells), <outdir>/cellmap.json (every analysis cell -> its engine
cell, filter, dials, seed), <outdir>/passes/pNN.txt.  Usage: prepare_v1.py <cells.json> <outdir>"""
import json, sys, os, re
DIALS = {'dip', 'W', 'L', 'age', 'lat', 'tp', 'hold', 'cool', 'mode', 'padMode', 'volMin', 'sdMin', 'buyMin', 'creator', 'th', 'range', 'dh',
         'band', 'quote', 'cap', 'rngId', 'last72'}                    # = engine_v1.js DIALS + the two it consumes before the check
BASE = dict(dip=0.20, W=3600, L=0, age=86400, lat=60, tp=1.30, hold=86400, cool=21600, mode='P')   # engine_v1.js BASE (the defaults)
FILTERS = {'min_dip_sec', 'min_sells'}
SEED = 20260927
def fnv(s):
    h = 0x811c9dc5
    for ch in s.encode(): h = ((h ^ ch) * 0x01000193) & 0xffffffff
    return h
def die(m): raise SystemExit('cells.json REFUSED: ' + m)
src, out = sys.argv[1], sys.argv[2]
cj = json.load(open(src)); cells = cj.get('cells') or die('no cells')
ps = int(cj.get('pass_size', 40))
ids = [c.get('id') for c in cells]
if len(set(ids)) != len(ids): die('duplicate ids')
by = {c['id']: c for c in cells}
emap, eng = {}, []
for c in cells:
    cid = c['id']
    if not isinstance(cid, str) or not re.fullmatch(r'[A-Za-z0-9._-]+', cid): die(f'bad id {cid!r}')
    extra = set(c) - {'id', 'params', 'filter', 'base', 'stat_seed', 'labels'}
    if extra: die(f'{cid}: unknown keys {sorted(extra)}')
    f = c.get('filter')
    if f is not None:
        if not f or set(f) - FILTERS: die(f'{cid}: filter keys must be from {sorted(FILTERS)}')
        b = by.get(c.get('base')) or die(f'{cid}: filter needs "base" = an unfiltered cell id in this file')
        if b.get('filter'): die(f'{cid}: base {b["id"]} is itself filtered')
        if 'params' in c and c['params'] != b.get('params', {}): die(f'{cid}: params differ from its base (a filter is a SPLIT of the base)')
        p = dict(BASE, **b.get('params', {}))
        if p['mode'] != 'P' or p['W'] != 3600: die(f'{cid}: token filters exist only for mode P, W 3600 (the engine writes tf there only)')
        ecell = b['id']
    else:
        if 'base' in c: die(f'{cid}: "base" without "filter"')
        p = c.get('params', {})
        bad = set(p) - DIALS
        if bad: die(f'{cid}: unknown dials {sorted(bad)}')
        full = dict(BASE, **p)
        if full['W'] not in (300, 3600, 86400): die(f'{cid}: W must be 300, 3600 or 86400 (900 has no activity-twin window in the engine)')
        if full['mode'] not in ('P', 'M'): die(f'{cid}: mode must be P or M')
        if not (0 < full['dip'] < 1): die(f'{cid}: dip is a fraction (0.25 = 25 %)')
        if not (full['tp'] > 1): die(f'{cid}: tp is a multiple (1.4 = +40 %)')
        if 'quote' in p and p['quote'] not in ('WETH', 'USDG'): die(f'{cid}: quote must be WETH or USDG')
        ecell = cid; eng.append(dict(id=cid, params=p))
    dials = dict(BASE, **(by[ecell].get('params', {})))
    seed = int(c['stat_seed']) if 'stat_seed' in c else SEED + (fnv(cid) % 100000) * 100
    emap[cid] = dict(engine_cell=ecell, filter=f, dials=dials, stat_seed=seed, labels=c.get('labels', {}))
os.makedirs(out + '/passes', exist_ok=True)
json.dump(dict(generated_from=os.path.abspath(src), cells=eng), open(out + '/engine_cells.json', 'w'), indent=1)
json.dump(emap, open(out + '/cellmap.json', 'w'), indent=1)
ids = sorted(c['id'] for c in eng)
for k in range(0, len(ids), ps):
    open(f'{out}/passes/p{k // ps + 1:02d}.txt', 'w').write('\n'.join(ids[k:k + ps]) + '\n')
print(f'{len(emap)} analysis cells, {len(eng)} engine cells, {(len(ids) + ps - 1) // ps} pass(es)')
