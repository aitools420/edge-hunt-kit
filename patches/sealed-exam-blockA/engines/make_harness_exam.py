#!/usr/bin/env python3
"""make_harness_exam.py — harness copies of an engine (Option A or exam). Built on twinfix-2026-10-05/tools/make_harness.py.
Env-gated hooks; with none of the env vars set a copy behaves EXACTLY as its source. Every anchor must match exactly once.
  H1 ONLY_CELLS=<id,...>  keep only these cells (the exam cell ALONE)                       [twinfix H1, verbatim]
  H2 RNG_REPLAY=<file>    replay each signal's twin draws (key cell|sigTs|tok) from another run [twinfix H2, verbatim; PROOF ONLY]
  H3 EXAM_SEED=<int>      the twin-draw seed (mulberry32), default 20260927; must be an integer in 20260927..20260946
Flags pick the hooks: --h1 --h2 --h3. The exam's sensitivity harness is --h1 --h3 (no replay hook).
Usage: make_harness_exam.py <engine.js> <out.js> --h1 [--h2] [--h3]"""
import sys
SRC, OUT = sys.argv[1], sys.argv[2]
F = set(sys.argv[3:])
s = open(SRC).read()
CELLS = {'st': "const CELLS = []; for (const c of CONFIGS) for (const m of ['M', 'P']) CELLS.push({ id: c.id + m, cfg: c, mode: m });",
         'grid': "const CELLS = []; for (const d of DIPS) for (const L of LEVELS) CELLS.push({ id: `D${d}L${L}`, dip: d / 100, L, ...BASE });"}
kind = [k for k, a in CELLS.items() if s.count(a) == 1]
assert len(kind) == 1, 'CELLS anchor not found exactly once'
def one(a):
    assert s.count(a) == 1, f'anchor not found exactly once: {a[:60]}'
H1 = (" if (process.env.ONLY_CELLS) { const keep = new Set(process.env.ONLY_CELLS.split(',')); for (let i = CELLS.length - 1; i >= 0; i--) "
      "if (!keep.has(CELLS[i].id)) CELLS.splice(i, 1); if (CELLS.length !== keep.size) throw new Error('ONLY_CELLS: unknown cell'); }   // HARNESS H1 (test only)")
RNG = "const rng = mulberry32(SEED);"
H2 = """const RREP = process.env.RNG_REPLAY ? new Map(JSON.parse(fs.readFileSync(process.env.RNG_REPLAY, 'utf8'))) : null;   // HARNESS H2 (test only)
let SIGKEY = null, RPOS = 0; const RSTAT = { draws: 0, miss: 0, short: 0, used: new Set() };
const rng = RREP ? () => { RSTAT.draws++; const a = RREP.get(SIGKEY); if (!a || RPOS >= a.length) { RSTAT.miss++; return 0.5; } return a[RPOS++]; } : mulberry32(SEED);
function sigStart(key) { if (!RREP) return; if (SIGKEY !== null) { const a = RREP.get(SIGKEY); if (a && RPOS !== a.length) RSTAT.short++; } SIGKEY = key; RPOS = 0; RSTAT.used.add(key); }
if (RREP) process.on('exit', () => { if (SIGKEY !== null) { const a = RREP.get(SIGKEY); if (a && RPOS !== a.length) RSTAT.short++; }
  console.error(`RNG_REPLAY keys ${RREP.size} signals ${RSTAT.used.size} draws ${RSTAT.draws} miss ${RSTAT.miss} short ${RSTAT.short} unusedKeys ${[...RREP.keys()].filter(k => !RSTAT.used.has(k)).length} unknownSignals ${[...RSTAT.used].filter(k => !RREP.has(k)).length}`); });"""
SIG = "    w.pend.delete(c.id); inc(stats.trig, `${half}|${c.id}`);"
H2S = " sigStart(c.id + '|' + r.ts + '|' + tok);   // HARNESS H2"
SEEDC = "REPS = 3, SEED = 20260927, SLIP = 0.004,"
H3 = ("REPS = 3, SEED = (() => { const e = process.env.EXAM_SEED; if (e == null || e === '') return 20260927; const v = Number(e);   // HARNESS H3: declared SEED hook\n"
      "  if (!Number.isInteger(v) || v < 20260927 || v > 20260946) throw new Error('EXAM_SEED must be an integer in 20260927..20260946'); return v; })(), SLIP = 0.004,")
assert F & {'--h1', '--h2', '--h3'} and F <= {'--h1', '--h2', '--h3'}, 'flags: --h1 --h2 --h3'
if '--h1' in F:
    s = s.replace(CELLS[kind[0]], CELLS[kind[0]] + H1)
if '--h2' in F:
    one(RNG); one(SIG)
    s = s.replace(RNG, H2).replace(SIG, SIG + H2S)
if '--h3' in F:
    one(SEEDC)
    s = s.replace(SEEDC, H3)
    if '--h2' not in F: one(RNG)
if '--h3' in F:
    s = s.replace("const rng = mulberry32(SEED);", "const rng = mulberry32(SEED); if (process.env.EXAM_SEED) console.error('HARNESS H3 SEED', SEED);")
open(OUT, 'w').write(s)
print(kind[0], 'harness', sorted(F), 'written', OUT)
