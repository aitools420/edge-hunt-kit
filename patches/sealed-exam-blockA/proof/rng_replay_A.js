#!/usr/bin/env node
// rng_replay_A.js — twinfix tools/rng_replay.js for the Option A engines (draws WITHOUT replacement: min(3, pool) per twin type).
// rng_replay.js <batch.ndjson[.gz]> <cell> <out.json> — rebuild, from a BATCH run's own output, which values of the single global
// mulberry32(20260927) stream each signal consumed, and write the target cell's per-signal draws for the H2 harness.
// Draw order inside the engine: signals in pid (= `pair`) order; per signal R x3 if cand non-empty (eligN), A x3 if poolA non-empty (nA),
// D x3 if poolD non-empty (nD, engine_st only). Every signal has exactly one clip-50 S row carrying eligN/nA/nD (asserted).
'use strict';
const fs = require('fs'), zlib = require('zlib'), readline = require('readline');
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const [SRC, CELL, OUT] = process.argv.slice(2);
(async () => {
  const sig = new Map();
  const inp = SRC.endsWith('.gz') ? fs.createReadStream(SRC).pipe(zlib.createGunzip()) : fs.createReadStream(SRC);
  for await (const ln of readline.createInterface({ input: inp, crlfDelay: Infinity })) {
    if (!ln) continue; const j = JSON.parse(ln);
    if (j._meta || j.kind !== 'S' || (j.clip != null && j.clip !== 50) || j.noscale) continue;
    if (sig.has(j.pair)) throw new Error('two clip-50 S rows for pair ' + j.pair);
    sig.set(j.pair, [j.cell, j.sigTs, j.tok, Math.min(3, j.eligN || 0) + Math.min(3, j.nA || 0) + (j.nD != null ? Math.min(3, j.nD) : 0)]);   // Option A FIX 1: min(3, pool) draws per twin type
  }
  const pairs = [...sig.keys()].sort((a, b) => a - b);
  for (let i = 0; i < pairs.length; i++) if (pairs[i] !== i + 1) throw new Error(`pairs not contiguous at ${i}: ${pairs[i]}`);
  const rng = mulberry32(20260927), out = []; let total = 0;
  for (const p of pairs) { const [cell, ts, tok, n] = sig.get(p); const u = []; for (let k = 0; k < n; k++) u.push(rng()); total += n;
    if (cell === CELL || CELL === '*') out.push([cell + '|' + ts + '|' + tok, u]); }
  if (new Set(out.map(x => x[0])).size !== out.length) throw new Error('duplicate signal key');
  fs.writeFileSync(OUT, JSON.stringify(out));
  console.log(`signals ${pairs.length} draws ${total} target ${CELL} signals ${out.length} -> ${OUT}`);
})();
