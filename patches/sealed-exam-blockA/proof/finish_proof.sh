#!/bin/bash
# finish_proof.sh — after drive_proof.sh: the three row-by-row comparisons per rule, the JUDGE statistics of the Option A runs, and
# PROOF.md / PROOF.json (every number read from the files below, none typed by hand).
set -u
P=/home/green/projects/patches/sealed-exam-blockA/proof; T=/home/green/projects/patches/twinfix-2026-10-05/out; S=/home/green/projects/patches/sealed-exam-blockA/tools
cd $P
for k in st grid; do
  nice -n 19 python3 compare_A.py fix1 $T/${k}_rk_batch.ndjson.gz out/${k}_A_noskip_batch.ndjson.gz out/cmp_${k}_fix1.json > out/cmp_${k}_fix1.txt 2>&1; echo "fix1 $k exit $?"
  nice -n 19 python3 compare_A.py fix2 out/${k}_A_noskip_batch.ndjson.gz out/${k}_A_replay.ndjson.gz out/cmp_${k}_fix2.json > out/cmp_${k}_fix2.txt 2>&1; echo "fix2 $k exit $?"
  nice -n 19 python3 compare_A.py draws out/${k}_A_replay.ndjson.gz out/${k}_A_batch.ndjson.gz out/cmp_${k}_draws.json > out/cmp_${k}_draws.txt 2>&1; echo "draws $k exit $?"
done
for r in st_A_batch st_A_alone; do nice -n 19 python3 $S/stats_rule.py 1 out/$r.ndjson.gz out/stats_$r.json > /dev/null; done
for r in grid_A_batch grid_A_alone; do nice -n 19 python3 $S/stats_rule.py 2 out/$r.ndjson.gz out/stats_$r.json > /dev/null; done
python3 - <<'PY'
import json, re, os
P = '/home/green/projects/patches/sealed-exam-blockA/proof'; T = '/home/green/projects/patches/twinfix-2026-10-05/out'
J = lambda p: json.load(open(p))
def rep(lbl):
    m = re.search(r'RNG_REPLAY keys (\d+) signals (\d+) draws (\d+) miss (\d+) short (\d+) unusedKeys (\d+) unknownSignals (\d+)', open(f'{P}/runlogs/{lbl}.log').read())
    return dict(zip(('keys', 'signals', 'draws', 'miss', 'short', 'unusedKeys', 'unknownSignals'), map(int, m.groups()))) if m else None
summ, judge, md = [], [], ['# Option A proof — 09-08..09-26, seal_guard preloaded, the 09-27 tables (twinfix inputs/)', '']
for k, r, cell in (('st', 1, 'C2P'), ('grid', 2, 'D25L48')):
    f1, f2, dr = J(f'{P}/out/cmp_{k}_fix1.json'), J(f'{P}/out/cmp_{k}_fix2.json'), J(f'{P}/out/cmp_{k}_draws.json')
    s1, tw1 = f1['strategy'], f1['twins']; t2 = f2['tallies']; sd = dr['strategy']; rp = rep(f'{k}_A_replay')
    summ.append(f"rule #{r} engine, FIX 1 alone (twin-cache engine vs Option A with FIX 2 off): strategy rows {s1['identical']}/{s1['keysA']} IDENTICAL in every field; "
                f"every twin draw is min(3, pool) DISTINCT coins (draw sizes 3/2/1: {tw1.get('B_size_3', 0)}/{tw1.get('B_size_2', 0)}/{tw1.get('B_size_1', 0)}, size or duplicate faults {tw1.get('B_size_not_min3pool', 0) + tw1.get('B_duplicate_coin', 0)}); "
                f"{tw1.get('same_signal_coin_identical', 0)} twin rows for the same signal and coin identical except the draw index, {tw1.get('same_signal_coin_DIFFERENT', 0)} different; unexplained {len(f1['unexplained'])}.")
    summ.append(f"rule #{r} engine, FIX 2 alone (FIX 1 on both sides, the SAME random numbers per signal replayed): strategy rows identical {t2.get('S_same', 0)} "
                f"(+{t2.get('S_same_trade_descriptor_differs', 0)} with only the twin-pool counts different); thin entries skipped {t2.get('S_thin_entry_skipped', 0)}; "
                f"rows that differ or appear later on the SAME coin after a skip {t2.get('S_differs_after_same_coin_skip', 0) + t2.get('S_only_A_after_same_coin_skip', 0) + t2.get('S_only_B_after_same_coin_skip', 0)}; "
                f"shadow rows of skipped entries {t2.get('S_shadow_of_thin_entry_gone', 0)}; UNEXPLAINED {t2.get('S_UNEXPLAINED', 0) + t2.get('S_only_A_UNEXPLAINED', 0) + t2.get('S_only_B_UNEXPLAINED', 0)}. "
                f"Twins: same signal and coin identical {t2.get('W_same_signal_coin_identical', 0)}, thin twin fills skipped {t2.get('W_thin_twin_skipped', 0)}, unexplained {t2.get('W_same_signal_coin_UNEXPLAINED', 0)}; "
                f"signals with the same drawn coins {t2.get('W_signal_coinset_same', 0)}, different only after a skip in the cell {t2.get('W_signal_coinset_differs_after_cell_skip', 0)}, unexplained {t2.get('W_signal_coinset_UNEXPLAINED', 0)}"
                + (f"; replay: {rp['signals']} signals, {rp['miss']} draws for signals new after a skip, {rp['short']} signals whose pool changed" if rp else '') + '.')
    summ.append(f"rule #{r} engine, draws only (replayed vs natural draws, both Option A): strategy rows {sd['identical']}/{sd['keysA']} IDENTICAL in every field.")
    import gzip
    def SR(fn):
        d = {}
        with gzip.open(fn, 'rt') as f:
            for ln in f:
                if f'"cell":"{cell}"' not in ln: continue
                j = json.loads(ln)
                if j['kind'] == 'S': d[(j['tok'], j['sigTs'], j.get('clip', 50))] = {k: v for k, v in j.items() if k != 'pair'}
        return d
    xa, xb, xc = SR(f'{T}/{k}_rk_batch.ndjson.gz'), SR(f'{P}/out/{k}_A_noskip_batch.ndjson.gz'), SR(f'{P}/out/{k}_A_batch.ndjson.gz')
    same_ab = sum(1 for q in xa if xb.get(q) == xa[q]); same_bc = sum(1 for q in xb if xc.get(q) == xb[q])
    nskip = sum(1 for v in xc.values() if v.get('skipDepth'))
    summ.append(f"the exam cell {cell} itself: strategy rows (FIT and JUDGE, every kind) twin-cache {len(xa)}, no-skip {len(xb)}, Option A {len(xc)}; identical twin-cache vs no-skip {same_ab}, "
                f"no-skip vs Option A {same_bc} (every field but the pair id, which other cells' re-entries shift); thin entries skipped in {cell}: {nskip}.")
    sb, sa = J(f'{P}/out/stats_{k}_A_batch.json'), J(f'{P}/out/stats_{k}_A_alone.json')
    for lab, s in (('primary pass (all cells), SEED 20260927', sb), ('exam cell alone, SEED 20260927', sa)):
        b, m = s['bar'], s['money_test']
        judge.append(f"rule #{r} {cell}, {lab}: heavy d vs ACTIVITY twin {b['d_mean']:+.2f} (CI {b['ci95'][0]:+.2f}..{b['ci95'][1]:+.2f}), SE_cons {b['se_cons']}, one-sided p {b['p_one_sided']}, "
                     f"n {b['n']} / {b['coins']} coins, drop-5 {b['drop5']:+.2f}; money test (raw heavy) {m['raw_heavy_mean']:+.2f} (CI {m['raw_heavy_ci95'][0]:+.2f}..{m['raw_heavy_ci95'][1]:+.2f}); "
                     f"gates {s['gate']['status']}; depth-floor skips in this cell {s['prefilter']['skipDepth_dropped']}")
    md += [f'## rule #{r} ({cell})', '', '```', open(f'{P}/out/cmp_{k}_fix1.txt').read().strip()[:3000], open(f'{P}/out/cmp_{k}_fix2.txt').read().strip()[:3000], open(f'{P}/out/cmp_{k}_draws.txt').read().strip()[:1500], '```', '']
ref = {1: J(f'{T}/d_st_rk_batch.json')['JUDGE_heavy_vs_A'], 2: J(f'{T}/d_grid_rk_batch.json')['JUDGE']['d_heavy_vs_A']}
for r in (1, 2):
    x = ref[r]; judge.append(f"for comparison, the twin-cache engine (_rk, registered 10-05) rule #{r}: {x['d_mean']:+.2f} (CI {x['ci95'][0]:+.2f}..{x['ci95'][1]:+.2f}), p {x['p_one_sided']}, n {x['n']}")
md = md[:2] + ['## Summary', ''] + [f'- {x}' for x in summ] + ['', '## New JUDGE references (Option A)', ''] + [f'- {x}' for x in judge] + [''] + md[2:]
open(f'{P}/PROOF.md', 'w').write('\n'.join(md) + '\n')
json.dump(dict(summary=summ, judge=judge), open(f'{P}/PROOF.json', 'w'), indent=1)
print('\n'.join(summ + judge))
PY
