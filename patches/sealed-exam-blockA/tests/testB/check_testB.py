#!/usr/bin/env python3
"""check_testB.py — the checks on Test B's dry run (open days; plumbing only: JUDGE is spent, NO number here is compared with anything as
a test of a rule). Window: first assessment 2026-09-22T00:00Z; rule #1 (C2) last assessment 09-23T23:00Z, C1 and rule #2 last 09-24T23:00Z;
CUT 2026-09-26T00:00Z. Checks, per engine output: (1) no strategy row (booked, nofill, trunc, skipped) has an assessment hour or a signal
outside its window; (2) every booked exit and every trunc is before the cut, and the positions still open at the data end are booked
'end' AT the data end (the last row read, in the last hour before the cut); (3) no row at/after the cut was read (every day file's last
row < CUT, data end < CUT) and the guard never fired; plus the step outputs: tables (09-27 rows identical, cutoff applied), the join's
consistency with the 09-27 join on every joined day, the two cut rows in the test registry, and report.md's first line."""
import json, gzip, glob, os, sys, datetime
T = '/home/green/projects/patches/sealed-exam-blockA/tests/testB'; W = T + '/tree/work'
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
P = lambda s: int(datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp())
CUT, EXAM0 = P('2026-09-26T00:00:00Z'), P('2026-09-22T00:00:00Z')
LASTT = {'C1': P('2026-09-24T23:00:00Z'), 'C2': P('2026-09-23T23:00:00Z'), 'grid': P('2026-09-24T23:00:00Z')}
H = 3600; fails = []; out = {}
def fail(m): fails.append(m)
for fn in sorted(glob.glob(W + '/out/*.ndjson.gz')):
    L = os.path.basename(fn)[:-10]; kind = 'st' if 'rule1' in L else 'grid'
    c = dict(S=0, outside=0, end=0, end_not_at_data_end=0, exit_after_cut=0, trunc_end=0, trunc_hole=0, skip=0, sig_min=None, sig_max={}); meta = None
    with gzip.open(fn, 'rt') as f:
        for ln in f:
            j = json.loads(ln)
            if '_meta' in j: meta = j['_meta']; continue
            if j.get('exitTs') is not None and j['exitTs'] >= CUT: c['exit_after_cut'] += 1
            if j['kind'] != 'S': continue
            c['S'] += 1
            cfg = 'grid' if kind == 'grid' else j['cfg']
            Tv, sg = j['T'], j['sigTs']
            if not (EXAM0 <= Tv <= LASTT[cfg] and Tv <= sg < Tv + H and sg < LASTT[cfg] + H): c['outside'] += 1
            c['sig_min'] = sg if c['sig_min'] is None else min(c['sig_min'], sg)
            c['sig_max'][cfg] = max(c['sig_max'].get(cfg, 0), sg)
            if j.get('reason') == 'end': c['end'] += 1
            if j.get('trunc') == 'end': c['trunc_end'] += 1
            if j.get('trunc') == 'hole': c['trunc_hole'] += 1
            if j.get('skipDepth'): c['skip'] += 1
    with gzip.open(fn, 'rt') as f:                               # 'end' bookings must sit exactly at the data end
        for ln in f:
            j = json.loads(ln)
            if j.get('reason') == 'end' and meta and j['exitTs'] != meta['endTs']: c['end_not_at_data_end'] += 1
    c['sig_min'] = iso(c['sig_min']) if c['sig_min'] else None; c['sig_max'] = {k: iso(v) for k, v in c['sig_max'].items()}
    c['data_end'] = iso(meta['endTs']); c['v23_last'] = iso(max(v['last'] for v in meta['v23Files'].values() if v['last']))
    c['v4_last'] = iso(max(v['last'] for v in meta['v4Files'].values() if v['last'])); c['v23_days'] = sorted(meta['v23Files']); c['v4_days_with_rows'] = sorted(d for d, v in meta['v4Files'].items() if v['n'])
    if c['outside']: fail(f'{L}: {c["outside"]} strategy rows outside the window')
    if c['exit_after_cut']: fail(f'{L}: {c["exit_after_cut"]} exits at/after the cut')
    if c['end_not_at_data_end']: fail(f'{L}: end bookings not at the data end')
    if not (CUT - H <= meta['endTs'] < CUT): fail(f'{L}: data end {iso(meta["endTs"])} not in the last hour before the cut')
    if max(v['last'] for v in meta['v23Files'].values() if v['last']) >= CUT or max(v['last'] for v in meta['v4Files'].values() if v['last']) >= CUT: fail(f'{L}: a row at/after the cut')
    out[L] = c
runs = [ln.split('\t') for ln in open(W + '/runlogs/runs.tsv')]
for r in runs:
    if 'exit=0' not in r: fail(f'run {r[0]} exit not 0')
st = {k: json.load(open(f'{W}/state/{k}.json')) for k in ('table_meta', 'table_poolfee', 'cut_tape', 'cut_wide', 'cut_lock', 'unknown_split', 'unknown_merge', 'poolcounts')}
for k in ('table_meta', 'table_poolfee'):                      # every 09-27 row of the test window kept verbatim (a test-window cutoff drops the later ones)
    if st[k]['old_rows_kept_verbatim'] + st[k]['old_rows_dropped_by_cutoff'] != st[k]['old_rows']: fail(f'{k}: 09-27 rows not all accounted for')
cons = {os.path.basename(p)[8:-5]: json.load(open(p)) for p in sorted(glob.glob(W + '/state/consist_*.json'))}
reg = [ln for ln in open(T + '/tape-hashes-testB.tsv') if '-cutA' in ln]
if len(reg) != 2: fail(f'{len(reg)} cut rows in the test registry, want 2')
rep = open(T + '/tree/report.md').readline().strip() if os.path.exists(T + '/tree/report.md') else None
if not rep or not rep.startswith('VERDICT'): fail('report.md missing or its first line is not the verdict')
res = dict(fails=fails, runs=out, steps={k: {a: b for a, b in v.items() if not str(a).startswith('examples')} for k, v in st.items()},
           join_consistency={d: {k: v for k, v in c.items() if k not in ('examples', 'mine', 'orig')} for d, c in cons.items()}, registry_cut_rows=[r.strip() for r in reg], report_first_line=rep)
json.dump(res, open(T + '/check_testB.json', 'w'), indent=1)
print(json.dumps(res, indent=1)[:6000])
print('TEST B', 'PASS' if not fails else 'FAIL', fails)
sys.exit(1 if fails else 0)
