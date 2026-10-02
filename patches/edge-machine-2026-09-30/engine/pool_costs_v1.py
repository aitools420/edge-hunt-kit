#!/usr/bin/env python3
"""pool_costs_v1.py - EDGE MACHINE v1: the batch's per-pool cost table = the FROZEN v1 table (pool_costs_v1.json here = hunt 3's final
table = the low-fee hunt's = hunt 2's: 5,830 pools, verified identical on every common pool) + every V4 pool this batch touches that it
lacks, classified exactly as ../../blood-hunt3-2026-09-29/pool_costs_h3.py (itself = pool_costs_lf.py <- pool_costs_sk2.py). Deterministic:
a pool gets the same row in any batch. NO RPC: a Pons pool with no launch terms in the held files STOPS the batch (as the hunts did).
Usage: pool_costs_v1.py <out.json> <poolfee_lf.tsv> <pass.ndjson.gz> [...]"""
import json, gzip, sys, statistics, collections, os
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'
OUTF, PF = sys.argv[1], sys.argv[2]
PONS = '0xe5e702641ea86f4ae6cc3cdaed2b886f976be044'
base = json.load(open(HERE + '/pool_costs_v1.json'))
touched = set()
for f in sys.argv[3:]:
  with gzip.open(f, 'rt') as fh:
    for ln in fh:
        if ln.startswith('{"pr":'):
            a = json.loads(ln)['pr']
            if len(a) > 6 and a[6] and a[6].startswith('v4:'): touched.add(a[6][3:])
            continue
        j = json.loads(ln)
        for pk in (j.get('ePk'), j.get('xPk'), (j.get('tb') or {}).get('xPk')):
            if pk and pk.startswith('v4:'): touched.add(pk[3:])
miss = sorted(touched - set(base['pools']))
pf = {}
for ln in open(PF):
    a = ln.rstrip('\n').split('\t')
    if len(a) >= 5 and a[0] in touched: pf[a[0]] = (int(a[2]) if a[2].lstrip('-').isdigit() else None, a[3], a[4])
RC = P + '/v4-real-cost-2026-09-27'
L = {k: v for k, v in json.load(open(RC + '/pons_launches.json')).items() if 'err' not in v}
X0 = {k: v for k, v in json.load(open(P + '/blood-realcost-2026-09-27/pons_launches_extra.json')).items() if 'err' not in v}
X0.update({k: v for k, v in json.load(open(P + '/blood-skeleton1-2026-09-27/pons_launches_sk.json')).items() if 'err' not in v})
X0.update({k: dict(hookFeeBps=v['hookFeeBps'], creatorTaxBps=v['creatorTaxBps']) for k, v in json.load(open(P + '/pons-feeterms-2026-09-27/pons_fee_terms.json'))['pools'].items() if v.get('status') == 'measured'})
need = [p for p in miss if p in pf and pf[p][1] == PONS and p not in L and p not in X0]
print('touched', len(touched), 'missing from the v1 table', len(miss), 'pons needing terms', len(need), flush=True)
if need: raise SystemExit('V1: %d Pons pools lack launch terms - no RPC here; stop and report (a new terms read = a new table version)' % len(need))
rec = collections.defaultdict(list)
for r in json.load(open(RC + '/m2b_rows.json'))['rows']:
    if r.get('type') != 'pons' and r.get('lp_fee_pips') is not None: rec[r['pool']].append(r['lp_fee_pips'] / 1e6)
out = dict(base['pools']); add = collections.Counter()
for p in miss:
    if p not in pf: out[p] = dict(type='unknown', fallback='unknown_pool'); add['unknown'] += 1; continue
    fee, hook, ven = pf[p]
    if hook == PONS:
        s = L.get(p) or X0.get(p)
        out[p] = dict(type='pons', lp=0.0, take=(s['hookFeeBps'] + s['creatorTaxBps']) / 1e4, take_src='launches()', fallback=None) if s else dict(type='pons', lp=0.0, take=None, fallback='pons_no_terms')
    elif hook == 'null':
        out[p] = dict(type='nohook', fee_key=None if fee is None else fee / 1e6, lp_receipt=statistics.median(rec[p]) if p in rec else None, take=0.0, fallback=None)
    elif fee == 8388608:
        out[p] = dict(type='dynfee', lp_receipt=statistics.median(rec[p]) if p in rec else None, take=0.0, fallback=None, venue=ven)
    else:
        out[p] = dict(type='otherhook', fee_key=None if fee is None or fee >= 1e6 else fee / 1e6, lp_receipt=statistics.median(rec[p]) if p in rec else None, take=0.0,
                      fallback='otherhook_take_unmeasured', venue=ven, hook=hook)
    add[out[p]['type'] + ('' if out[p].get('fallback') is None else '|' + out[p]['fallback'])] += 1
json.dump(dict(constants=base['constants'], pools=out, added_here=dict(add), added_pools=miss, base='pool_costs_v1.json'), open(OUTF, 'w'), indent=0)
print('added', dict(add))
