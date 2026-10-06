#!/usr/bin/env python3
"""make_A.py — Option A (coordinator 2026-10-05 ~22:00Z): port the two changes registered on 09-27 ("added before the run")
into the twin-cache-fixed exam engines, from blood-grid-window-history-2026-09-27/engine_wh.js (sha256 127218368d46c4c0…):
  FIX 1  twins drawn WITHOUT replacement: each twin type draws min(3, pool) DISTINCT coins (partial Fisher-Yates, same
         mulberry32 stream); `twinDistinct` counts the draw sizes.
  FIX 2  depth floor: a V4 fill whose pool depth1_eth < 0.001 is SKIPPED, strategy and twins alike: written as a `skipDepth`
         row, counted in `skipDepth`, the coin released with NO cooldown, nothing booked.
Every anchor must match EXACTLY once (asserted). This is LOGIC, not constants; the exam-window constants are a separate step.
Usage: make_A.py <engine_st_rk.js|engine_grid_rk.js> <out.js>"""
import sys
SRC, OUT = sys.argv[1], sys.argv[2]
s = open(SRC).read()
kind = 'st' if "for (const m of ['M', 'P'])" in s else 'grid'

def rep(a, b):
    global s
    n = s.count(a)
    assert n == 1, f'anchor found {n} times: {a[:90]!r}'
    s = s.replace(a, b)

TAG = 'sealed-exam-blockA Option A'
# header note
first = s.split('\n', 2)
s = first[0] + '\n' + f'// {TAG} (coordinator 2026-10-05): + FIX 1 twins WITHOUT replacement, + FIX 2 V4 depth floor 0.001 ETH skipped at fill — both\n' \
    '//   ported from blood-grid-window-history-2026-09-27/engine_wh.js, the two changes the register added "before the run" on 09-27.\n' + first[1] + '\n' + first[2]
# constant
if kind == 'st':
    rep("const CELLS = []; for (const c of CONFIGS) for (const m of ['M', 'P']) CELLS.push({ id: c.id + m, cfg: c, mode: m });",
        "const CELLS = []; for (const c of CONFIGS) for (const m of ['M', 'P']) CELLS.push({ id: c.id + m, cfg: c, mode: m });\n"
        f"const DEPTH_FLOOR = 0.001;                                                                 // {TAG}: FIX 2")
else:
    rep("const CELLS = []; for (const d of DIPS) for (const L of LEVELS) CELLS.push({ id: `D${d}L${L}`, dip: d / 100, L, ...BASE });",
        "const CELLS = []; for (const d of DIPS) for (const L of LEVELS) CELLS.push({ id: `D${d}L${L}`, dip: d / 100, L, ...BASE });\n"
        f"const DEPTH_FLOOR = 0.001;                                                                 // {TAG}: FIX 2")
# counters
if kind == 'st':
    rep("  shadow: { spawned: 0, noscale: 0 }, crossPoolDip: {}, matchLvl: {} };",
        "  shadow: { spawned: 0, noscale: 0 }, crossPoolDip: {}, matchLvl: {}, skipDepth: {}, twinDistinct: {} };")
else:
    rep("  fixC: { fired_depthok: 0, fired_corroborated: 0, blocked: 0, blockedPos: 0 }, matchLvl: {}, profCalls: 0 };",
        "  fixC: { fired_depthok: 0, fired_corroborated: 0, blocked: 0, blockedPos: 0 }, matchLvl: {}, profCalls: 0, skipDepth: {}, twinDistinct: {} };")
# FIX 2 at the top of fill()
SKIP = ("  if (r.kind === 'v4' && r.depth1_eth < DEPTH_FLOOR) {                           // FIX 2 depth floor: skip, no cooldown (engine_wh.js)\n"
        "    W_({ ...base(p), skipDepth: 1, eDepth1: r.depth1_eth, entryTs: r.ts }); inc(stats.skipDepth, `${p.cell}|${p.kind}${p.tw || ''}`); release(p, null); p.st = 'done'; return;\n"
        "  }\n")
rep("function fill(p, r, delay) {\n", "function fill(p, r, delay) {\n" + SKIP)
# a skipped fill ends the position at once (engine_wh.js clockTo / onPrint)
rep("    if (p.last && priceable(p.last)) fill(p, p.last, 0); else { p.st = 'EW'; p.eWait = p.sigTs + LAT + EWAIT; }",
    "    if (p.last && priceable(p.last)) { fill(p, p.last, 0); if (p.st === 'done') return true; } else { p.st = 'EW'; p.eWait = p.sigTs + LAT + EWAIT; }")
rep("    if (priceable(r)) fill(p, r, r.ts - (p.sigTs + LAT)); else p.last = r; return false;",
    "    if (priceable(r)) { fill(p, r, r.ts - (p.sigTs + LAT)); if (p.st === 'done') return true; } else p.last = r; return false;")
# FIX 1 draws
DRAW = ("    const draw = (pool, tw) => {                                                   // FIX 1 WITHOUT replacement: min(3, |pool|) distinct coins (engine_wh.js)\n"
        "      if (!pool.length) { inc(stats.twinEmpty, `${c.id}|${tw}`); return; }\n"
        "      const a = pool.slice(), m = Math.min(REPS, a.length);\n"
        "      for (let k = 0; k < m; k++) { const j = k + Math.floor(rng() * (a.length - k)); const t = a[j]; a[j] = a[k]; a[k] = t; mk(t, tw, k); }\n"
        "      inc(stats.twinDistinct, `${halfOf(w.T)}|${c.id}|${tw}${m}`);\n"
        "    };\n")
if kind == 'st':
    rep("    if (!cand.length) inc(stats.twinEmpty, `${c.id}|R`); else for (let k = 0; k < REPS; k++) mk(cand[Math.floor(rng() * cand.length)], 'R', k);\n"
        "    if (!poolA.length) inc(stats.twinEmpty, `${c.id}|A`); else for (let k = 0; k < REPS; k++) mk(poolA[Math.floor(rng() * poolA.length)], 'A', k);\n"
        "    if (!poolD.length) inc(stats.twinEmpty, `${c.id}|D`); else for (let k = 0; k < REPS; k++) mk(poolD[Math.floor(rng() * poolD.length)], 'D', k);\n",
        DRAW + "    draw(cand, 'R'); draw(poolA, 'A'); draw(poolD, 'D');\n")
else:
    rep("    if (!cand.length) inc(stats.twinEmpty, `${c.id}|R`); else for (let k = 0; k < REPS; k++) mk(cand[Math.floor(rng() * cand.length)], 'R', k);\n"
        "    if (!poolA.length) inc(stats.twinEmpty, `${c.id}|A`); else for (let k = 0; k < REPS; k++) mk(poolA[Math.floor(rng() * poolA.length)], 'A', k);\n",
        DRAW + "    draw(cand, 'R'); draw(poolA, 'A');\n")
open(OUT, 'w').write(s)
print(kind, 'Option A written', OUT)
