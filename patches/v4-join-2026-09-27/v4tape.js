// v4tape.js — reader for the joined Uniswap V4 swap dataset, in the SAME row shape engine2.js reads from the V2/V3 tape
// ({ts, blk, li, tx, tok, sym, w, side, usd, px, kind, quote}; px is USD like the V2/V3 tape), plus the V4 extras.
// Also merges V2/V3 and V4 for one day in (ts, blk, li) order, so a backtest can read both rails together.
//
//   const V4 = require('/home/green/projects/patches/v4-join-2026-09-27/v4tape.js');
//   for await (const r of V4.readDay('2026-09-20')) ...            // V4 only
//   for await (const r of V4.mergedDay('2026-09-20')) ...          // V2/V3 tape + V4, one ordered stream
//   const deaths = V4.loadDeaths();                                  // Map pool -> death record (tok index: deaths.byTok)
//
// ⛔ SEALED HOLDOUT: days >= 2026-09-27 (and any row with ts >= 1790467200) are the final exam
// (patches/SEALED-HOLDOUT/README.md). They are refused unless opts.allowSealed === 'FINAL-EXAM', and even then only
// by a run registered in that README first.
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib'), readline = require('readline');
const DIR = path.join(__dirname, 'out');
const WE = '/home/green/.openclaw/workspace/wick-engine/logs';
const SEAL = 1790467200;
const SEAL_DAY = '2026-09-27';

function sealedCheck(day, opts) {
  if (day >= SEAL_DAY && (opts || {}).allowSealed !== 'FINAL-EXAM') throw new Error(`v4tape: ${day} is in the SEALED holdout (>= ${SEAL_DAY}) — refused`);
}
function v4Path(day, opts) {
  sealedCheck(day, opts);
  const p = path.join(day >= SEAL_DAY ? path.join(DIR, 'sealed') : DIR, `v4-swaps-${day}.ndjson.gz`);
  return fs.existsSync(p) ? p : null;
}
// the V2/V3 day files exactly as engine2.js resolve('tape', day) finds them: archive part(s) + live part
function v23Paths(day, kind = 'tape') {
  const parts = [];
  for (const m of fs.readdirSync(path.join(WE, 'archive'))) { const gz = path.join(WE, 'archive', m, `${kind}-${day}.ndjson.gz`); if (fs.existsSync(gz)) parts.push(gz); }
  const live = path.join(WE, kind === 'tape' ? 'robinhood-tape' : 'robinhood-livetape', `${kind}-${day}.ndjson`);
  if (fs.existsSync(live)) parts.push(live);
  return parts;
}
function lines(p) {
  const s = p.endsWith('.gz') ? fs.createReadStream(p).pipe(zlib.createGunzip()) : fs.createReadStream(p);
  return readline.createInterface({ input: s, crlfDelay: Infinity });
}
// V4 row -> engine2 shape (+ V4 extras kept under their own names). px/usd null when the quote could not be priced.
function toEngine(r) {
  return { ts: r.ts, blk: r.blk, li: r.li, tx: r.tx, tok: r.tok, sym: null, w: null, side: r.side, usd: r.usd, px: r.price_usd,
    kind: 'v4', quote: r.quote, pool: r.pool, price_eth: r.price_eth, price_quote: r.price_quote, amount_token: r.amount_token,
    amount_quote: r.amount_quote, liquidity: r.liquidity, depth1_eth: r.depth1_eth, depth5_eth: r.depth5_eth, pad: r.pad,
    birth_ts: r.birth_ts, src: r.src };
}
async function* readDay(day, opts = {}) {
  const p = v4Path(day, opts); if (!p) return;
  const lim = opts.allowSealed === 'FINAL-EXAM' ? Infinity : SEAL;
  for await (const ln of lines(p)) {
    if (!ln) continue; const r = JSON.parse(ln);
    if (r.ts >= lim) throw new Error('v4tape: sealed row in an unsealed file — refused');
    yield opts.raw ? r : toEngine(r);
  }
}
async function* readV23Day(day, opts = {}) {
  sealedCheck(day, opts);
  for (const p of v23Paths(day, opts.kind || 'tape'))
    for await (const ln of lines(p)) { if (!ln) continue; let r; try { r = JSON.parse(ln); } catch { continue; } if (r.ts >= SEAL && opts.allowSealed !== 'FINAL-EXAM') continue; yield r; }
}
// two-way merge by (ts, blk, li). The V2/V3 day is read into memory (it is small next to V4); V4 streams.
async function* mergedDay(day, opts = {}) {
  const a = []; for await (const r of readV23Day(day, opts)) a.push(r);
  const key = r => [r.ts, r.blk || 0, r.li || 0];
  const lt = (x, y) => { const p = key(x), q = key(y); for (let i = 0; i < 3; i++) if (p[i] !== q[i]) return p[i] < q[i]; return false; };
  a.sort((x, y) => (lt(x, y) ? -1 : lt(y, x) ? 1 : 0));
  let i = 0;
  for await (const r of readDay(day, opts)) { while (i < a.length && lt(a[i], r)) yield a[i++]; yield r; }
  while (i < a.length) yield a[i++];
}
function days(from, to) { const out = []; for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += 864e5) out.push(new Date(t).toISOString().slice(0, 10)); return out; }
function loadDeaths() {
  const m = new Map(); m.byTok = new Map();
  const buf = zlib.gunzipSync(fs.readFileSync(path.join(DIR, 'v4-pool-deaths.ndjson.gz'))).toString('utf8');
  for (const ln of buf.split('\n')) { if (!ln) continue; const r = JSON.parse(ln); m.set(r.pool, r); if (!m.byTok.has(r.tok)) m.byTok.set(r.tok, []); m.byTok.get(r.tok).push(r); }
  return m;
}
module.exports = { readDay, readV23Day, mergedDay, days, loadDeaths, v4Path, v23Paths, toEngine, SEAL, SEAL_DAY };
