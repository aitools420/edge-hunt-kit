#!/usr/bin/env python3
"""parity_table.py - PARITY verdicts: engine v1 batch results vs the published numbers of the parent batches.
Pass rule (the task's): n EQUAL, |mean - published| <= 0.05, |lower - published| <= 0.3 (bootstrap noise), JUDGE half.
hunt 2 cells: view real60h (published primary). hunt 3 cells: view real60 = hop OFF (hunt 3 published before the hop was costed, R-0115);
v1's hop-costed real60h reported beside it. Token-filter cells: only if ../../../blood-tokenfilter-2026-09-30/results*.json exists.
Usage: parity_table.py <v1 results.json> [<row compare json> ...]  -> prints a markdown table + writes parity_table.json beside this file"""
import json, sys, os
P = os.environ['KIT_ROOT'] + '/patches'; HERE = os.path.dirname(os.path.abspath(__file__))
V = json.load(open(sys.argv[1]))['cells']
H2 = json.load(open(P + '/blood-hunt2-2026-09-29/results_raw.json'))['cells']; H3 = json.load(open(P + '/blood-hunt3-2026-09-29/results_raw.json'))['cells']
TFf = next((P + '/blood-tokenfilter-2026-09-30/' + f for f in ('results_raw.json', 'results.json') if os.path.exists(P + '/blood-tokenfilter-2026-09-30/' + f)), None)
TF = json.load(open(TFf))['cells'] if TFf else None
def pub(c):
    src = (V[c].get('labels') or {}).get('source', '')
    if src.startswith('hunt 2'): return 'hunt 2', 'real60h', H2[c]['JUDGE']['real60h']['raw']
    if src.startswith('hunt 3'): return 'hunt 3', 'real60', H3[c]['JUDGE']['real60']['raw']
    if src.startswith('token-filter'):
        if TF is None: return 'token filter', 'real60h', None
        J = TF.get(c, {}).get('JUDGE', {}); return 'token filter', 'real60h', (J.get('real60h') or {}).get('raw') or J.get('raw')
    return None, None, None
rows = []
for c, r in V.items():
    src, vw, p = pub(c); J = r.get('JUDGE', {}); m = (J.get(vw) or {}).get('raw', {}) if vw else {}; h = (J.get('real60h') or {}).get('raw', {})
    if p is None: rows.append(dict(cell=c, source=src, view=vw, verdict='NO PUBLISHED NUMBER (yet)', v1_n=m.get('n'), v1_mean=m.get('mean'), v1_lower=m.get('lower'))); continue
    ok_n = m.get('n') == p.get('n'); dm = None if m.get('mean') is None else round(m['mean'] - p['mean'], 4)
    dl = None if m.get('lower') is None else round(m['lower'] - p['ci95'][0], 4)
    ok = ok_n and dm is not None and abs(dm) <= 0.05 and dl is not None and abs(dl) <= 0.3
    rows.append(dict(cell=c, source=src, view=vw, pub_n=p['n'], pub_mean=p['mean'], pub_lower=p['ci95'][0], v1_n=m.get('n'), v1_mean=m.get('mean'), v1_lower=m.get('lower'),
                     d_mean=dm, d_lower=dl, verdict='PASS' if ok else 'FAIL', v1_real60h=dict(n=h.get('n'), mean=h.get('mean'), lower=h.get('lower')) if vw != 'real60h' else None))
cmp = [json.load(open(f)) for f in sys.argv[2:]]
json.dump(dict(results=sys.argv[1], rows=rows, row_compare=cmp), open(HERE + '/parity_table.json', 'w'), indent=1)
print('| cell | source · view | published n / mean / lower | v1 n / mean / lower | Δmean / Δlower | verdict | v1 hop-costed (real60h) |')
print('|---|---|---|---|---|---|---|')
for x in rows:
    pb = f"{x.get('pub_n')} / {x.get('pub_mean')} / {x.get('pub_lower')}" if 'pub_n' in x else '—'
    hh = f"n {x['v1_real60h']['n']} / {x['v1_real60h']['mean']} / {x['v1_real60h']['lower']}" if x.get('v1_real60h') else '(same view)'
    print(f"| {x['cell']} | {x['source']} · {x['view']} | {pb} | {x['v1_n']} / {x['v1_mean']} / {x['v1_lower']} | {x.get('d_mean')} / {x.get('d_lower')} | {x['verdict']} | {hh} |")
for c in cmp:
    print(f"\nrow compare {c['cells']}: rows v1 {c['rows_v1']} vs parent {c['rows_parent']}, identical {c['rows_identical']} (only v1 {c['only_v1']}, only parent {c['only_parent']}); "
          f"probes {c['probes_v1']} vs {c['probes_parent']}, identical {c['probes_identical']}")
