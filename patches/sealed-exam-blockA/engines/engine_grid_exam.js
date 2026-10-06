#!/usr/bin/env node
// sealed-exam-blockA Option A (coordinator 2026-10-05): + FIX 1 twins WITHOUT replacement, + FIX 2 V4 depth floor 0.001 ETH skipped at fill — both
//   ported from blood-grid-window-history-2026-09-27/engine_wh.js, the two changes the register added "before the run" on 09-27.
// engine_grid.js — BLOOD 2-D GRID: dip depth x 72 h trading history (PREREG.md). Research only, READ-ONLY on the estate.
// Built on ../blood-stress-2026-09-27/engine_st.js (ONE timestamp-merged V2/V3 + V4 stream per R-0109, depth-aware V4 pricing,
// fixed guard, FIX a/b/c, G5 >20x rule, one-pool dip = mode P, activity-matched twin). CHANGED here (PREREG.md §2-§3):
//  * 24 cells = dip {10,15,20,25,30,40} % under the MAIN pool's own 1 h high x trading history {all, >=24, >=48, 72} hours of the
//    prior 72 with a >= $10 accepted print (selection #2's definition + its measurability rule). Mode P only.
//  * base = selection #2's config: age >= 24 h, TP +30 % from the fill, max hold 24 h, no stop, 6 h COOLDOWN, $50, hourly assessment.
//  * twins: R (random) and A (activity-matched) x3 each, from the CELL's eligible set (same trading-history filter). No D twins, no
//    clip shadows.  * output gzipped.
// Usage: node engine_grid.js <out.ndjson.gz> <meta.tsv> <scam.tsv> <poolfee.tsv>      env STOP_DAY=YYYY-MM-DD for the smoke
'use strict';
const fs = require('fs'), zlib = require('zlib');
const V4 = require('/home/green/projects/patches/sealed-exam-blockA/engines/v4tape_exam.js');   // sealed-exam-blockA: exam reader (paths + seal constants)
const { acceptNew: accept } = require('./guard.js');
const [OUT, META, SCAM, POOLF] = process.argv.slice(2);
const DAY = 86400, H = 3600, HOLE = 6 * H, LAT = 60, CUT = 1791331200;   // sealed-exam-blockA: CUT = 2026-10-07T00:00:00Z
const DATA0 = Date.parse('2026-09-24T00:00:00Z') / 1000;   // sealed-exam-blockA: warm-up from the open days 09-24..09-26
const FIT0 = Date.parse('2026-09-27T00:00:00Z') / 1000, JUDGE0 = Date.parse('2026-09-27T00:00:00Z') / 1000;   // sealed-exam-blockA: ONE exam window from 09-27T00:00Z
const LAST = Date.parse('2026-10-05T23:00:00Z') / 1000;   // sealed-exam-blockA: rule #2 signals < 10-06T00:00Z
const DIPS = [10, 15, 20, 25, 30, 40], LEVELS = [0, 24, 48, 72];
const BASE = { age: 24 * H, tp: 1.30, hold: 24 * H, cool: 6 * H };
const CELLS = []; for (const d of DIPS) for (const L of LEVELS) CELLS.push({ id: `D${d}L${L}`, dip: d / 100, L, ...BASE });
const DEPTH_FLOOR = 0.001;                                                                 // sealed-exam-blockA Option A: FIX 2
const REPS = 3, SEED = 20260927, SLIP = 0.004, DRAIN = 0.05, MINUSD = 10, EWAIT = H, XWAIT = DAY;
const CLIP = 50, S1 = Math.sqrt(1.01) - 1, X20 = 20, CORR_WIN = 30 * 60, DEPTH_OK_W = 0.10, V4_DEFAULT_FEE = 0.01;
const POOL_HL = 6 * H, POOL_X = 2, POOL_REF_AGE = H, REORDER = 2 * H;
const MR = 60, BR = 150, HR = 52, BS = 600, TR = 73;
const N10_EDGES = [1, 3, 10, 30, 100, 300], DEPTH_EDGES = [0.01, 0.03, 0.1, 0.3, 1];
const band = (x, e) => { let i = 0; while (i < e.length && x >= e[i]) i++; return i; };
const PONS_HOOK = '0xe5e702641ea86f4ae6cc3cdaed2b886f976be044';
const VENUE_LABEL = { doppler: 'Doppler', letscash: 'letscash', Klik: 'Klik', 'RWA Launchpad': 'RWA Launchpad' };
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rng = mulberry32(SEED);
const RUN = V4.days('2026-09-24', process.env.STOP_DAY || '2026-10-07');   // sealed-exam-blockA: day files 09-24..10-07 (10-07 = the CUT copy)
for (const d of RUN) if (d >= V4.SEAL_DAY) throw new Error('sealed day in RUN: ' + d);
// ---- labels, births, V4 pool table (as engine_st) ----
const padOf = new Map(), birth = new Map(), v3 = new Set(); let metaLab = 0;
for (const ln of fs.readFileSync(META, 'utf8').split('\n')) { const a = ln.split('\t'); if (a.length < 4) continue;
  if (a[1] !== '-') birth.set(a[0], +a[1]); if (a[2] === 'v3-1pct') v3.add(a[0]);
  if (a[3] === 'unknown' || a[3] === 'unlabelled') continue; padOf.set(a[0], a[3]); metaLab++; }
const poolFee = new Map(), poolHook0 = new Set(), poolPons = new Set(); const v4lab = new Map(), v4birth = new Map();
for (const ln of fs.readFileSync(POOLF, 'utf8').split('\n')) { const a = ln.split('\t'); if (a.length < 6) continue;
  const [pool, tok, fee, hook, venue, bts] = a; const f = +fee;
  poolFee.set(pool, f >= 0 && f < 1e6 ? f / 1e6 : null);
  if (f === 0 && hook !== 'null') poolHook0.add(pool);
  if (hook === PONS_HOOK) poolPons.add(pool);
  const lab = hook === PONS_HOOK ? 'Pons' : hook === '0x75a54357d9c78a2db19004a5fdc76c50f9242aec' ? 'letscash' : hook === '0x745d717620052a97a22deee2e5eba59583f3e0cc' ? 'Klik'
    : hook === '0x48b8f6ad3a1b4aa477314c9a23035b8f84dde8cc' ? 'Clanker' : VENUE_LABEL[venue] || null;
  if (lab && !v4lab.has(tok)) v4lab.set(tok, lab);
  if (bts !== 'null' && bts) { const b = +bts; if (!v4birth.has(tok) || b < v4birth.get(tok)) v4birth.set(tok, b); } }
let v4LabAdded = 0;
for (const [tok, lab] of v4lab) if (!padOf.has(tok)) { padOf.set(tok, lab); v4LabAdded++; if (!birth.has(tok) && v4birth.has(tok)) birth.set(tok, v4birth.get(tok)); }
const scamF = new Map(); for (const ln of fs.readFileSync(SCAM, 'utf8').split('\n')) { const a = ln.split('\t'); if (a.length >= 4) scamF.set(a[0], [a[1], +a[2], +a[3]]); }
const scamAt = (tok, ts) => { const s = scamF.get(tok); return s && s[1] <= ts && ts < s[2] ? s[0] : null; };
const gz = zlib.createGzip({ level: 6 }); gz.pipe(fs.createWriteStream(OUT)); const W_ = o => gz.write(JSON.stringify(o) + '\n');
const stats = { metaLab, v4LabAdded, rows: 0, rowsV4: 0, v4skipLiq0: 0, univRows: 0, univV4: 0, bad: 0, badV4: 0, exits: 0, trunc: 0, end: 0, holes: 0,
  holeAt: [], nofill: 0, assess: {}, cand: {}, drop: {}, eligL: {}, trig: {}, heldSkip: {}, coolSkip: {}, twinEmpty: {},
  wide0: null, feeSrc: {}, g5: {}, v23Files: {}, v4Files: {}, reorder: { maxHeap: 0, lateRows: 0 }, mergedOutOfOrder: 0, v4OutOfOrder: 0,
  fixA: { checked: 0, unchecked: 0, dropped: 0, droppedV4: 0, droppedV23: 0 },
  fixB: { otherPoolPrintsSeen: 0, positionsWithOtherPool: 0 },
  fixC: { fired_depthok: 0, fired_corroborated: 0, blocked: 0, blockedPos: 0 }, matchLvl: {}, profCalls: 0, skipDepth: {}, twinDistinct: {} };
const inc = (o, k, v = 1) => { o[k] = (o[k] || 0) + v; };
const halfOf = T => T < JUDGE0 ? 'FIT' : 'JUDGE';
// ---- pools ----
const pkIdx = new Map(), pkName = []; const pkOf = s => { let i = pkIdx.get(s); if (i == null) { i = pkName.length; pkIdx.set(s, i); pkName.push(s); } return i; };
const poolKey = r => r.kind === 'v4' ? 'v4:' + r.pool : r.kind + ':' + r.quote;
const toks = new Map(), poolEst = new Map(), padVol = new Map();
let WIDE0 = null;
function tracker(r) {
  let T = toks.get(r.tok);
  if (!T) { T = { q: r.quote, first: r.ts, last: r.ts, lastR: null, med: [], pend: null, confirms: 0,
    cov: (r.kind === 'v4' && r.src === 'wide') ? WIDE0 : DATA0, hasV4: false, hasV23: false, pools: new Map(),
    mId: new Int32Array(MR).fill(-1), mMax: new Float32Array(MR), mLast: new Float32Array(MR), mPk: new Int32Array(MR),
    bId: new Int32Array(BR).fill(-1), bMax: new Float32Array(BR), bLast: new Float32Array(BR), bPk: new Int32Array(BR),
    hId: new Int32Array(HR).fill(-1), hLast: new Float32Array(HR), hVol: new Float64Array(HR), h10: new Int32Array(TR).fill(-1),
    rec: [], q10: [], pc: null, mpc: null, prf: null }; toks.set(r.tok, T); }
  return T;
}
function mainPool(T, ts) {
  let best = -1, bv = -1;
  for (const [pk, P] of T.pools) { const v = P.vol * Math.pow(2, -(ts - P.vts) / POOL_HL); if (v > bv) { bv = v; best = pk; } }
  return best;
}
let ROWSEQ = 0;   // twinfix-2026-10-05 (Chef TG 16695, pond #297/#298): one row counter, ++ once at the top of onRow; a cache below hits only within the SAME row
function mainPoolC(T, ts) { const mi = Math.floor(ts / 60); if (!T.mpc || T.mpc.mi !== mi || T.mpc.seq !== ROWSEQ) T.mpc = { mi, seq: ROWSEQ, v: mainPool(T, ts) }; return T.mpc.v; }
function poolHigh1h(P, ts) {
  const mi = Math.floor(ts / 60); let hv = 0;
  for (let a = 0; a < MR; a++) { const m = mi - a, s = m % MR; if (P.mId[s] === m && P.mMax[s] > hv) hv = P.mMax[s]; }
  return hv;
}
function update(T, r) {
  const ts = r.ts, mi = Math.floor(ts / 60), ms = mi % MR, bi = Math.floor(ts / BS), bs = bi % BR, hi = Math.floor(ts / H), hs = hi % HR;
  T.last = ts; T.lastR = r; if (r.kind === 'v4') T.hasV4 = true; else T.hasV23 = true;
  if (T.mId[ms] !== mi) { T.mId[ms] = mi; T.mMax[ms] = 0; }
  if (r.px > T.mMax[ms]) { T.mMax[ms] = r.px; T.mPk[ms] = r.pk; } T.mLast[ms] = r.px;
  if (T.bId[bs] !== bi) { T.bId[bs] = bi; T.bMax[bs] = 0; }
  if (r.px > T.bMax[bs]) { T.bMax[bs] = r.px; T.bPk[bs] = r.pk; } T.bLast[bs] = r.px;
  if (T.hId[hs] !== hi) { T.hId[hs] = hi; T.hVol[hs] = 0; }
  T.hLast[hs] = r.px; T.hVol[hs] += r.usd || 0;
  if (r.usd >= MINUSD) T.h10[hi % TR] = hi;                                            // trading-history hour (>= $10 accepted print)
  const pad = padOf.get(r.tok); let PV = padVol.get(pad); if (!PV) { PV = { id: new Int32Array(HR).fill(-1), v: new Float64Array(HR) }; padVol.set(pad, PV); }
  if (PV.id[hs] !== hi) { PV.id[hs] = hi; PV.v[hs] = 0; } PV.v[hs] += r.usd || 0;
  let P = T.pools.get(r.pk);
  if (!P) { P = { vol: 0, vts: ts, lastPx: 0, lastTs: 0, lastR: null, mId: new Int32Array(MR).fill(-1), mMax: new Float32Array(MR), rs: [], lastSell10: -1, lastSell1: -1 }; T.pools.set(r.pk, P); }
  P.vol = P.vol * Math.pow(2, -(ts - P.vts) / POOL_HL) + (r.usd || 0); P.vts = ts; P.lastPx = r.px; P.lastTs = ts; P.lastR = r;
  if (P.mId[ms] !== mi) { P.mId[ms] = mi; P.mMax[ms] = 0; } if (r.px > P.mMax[ms]) P.mMax[ms] = r.px;
  if (r.side === 'sell') { P.lastSell1 = ts; if (r.usd >= MINUSD) P.lastSell10 = ts; }
  P.rs.push([ts, r.side === 'sell' ? 1 : 0, r.px]); if (P.rs.length > 80) P.rs.shift();
  if (r.usd >= MINUSD) { T.rec.push({ ts, px: r.px, tx: r.tx, pk: r.pk }); while (T.rec.length && T.rec[0].ts <= ts - CORR_WIN) T.rec.shift(); if (T.rec.length > 300) T.rec.shift();
    T.q10.push(ts); if (T.q10.length > 4000) T.q10.shift(); }
}
function hours72(T, t0) { const h0 = Math.floor(t0 / H); let n = 0; for (let k = 0; k < TR; k++) { const h = T.h10[k]; if (h >= h0 - 72 && h <= h0 - 1) n++; } return n; }
function n10(T, now) { while (T.q10.length && T.q10[0] <= now - H) T.q10.shift(); return T.q10.length; }
function priceAt(T, t, now) {
  const mNow = Math.floor(now / 60);
  for (let m = Math.floor(t / 60) - 1; m > mNow - MR; m--) { if (T.mId[m % MR] === m) return T.mLast[m % MR]; }
  const bNow = Math.floor(now / BS);
  for (let b = Math.floor(t / BS) - 1; b > bNow - BR; b--) { if (T.bId[b % BR] === b) return T.bLast[b % BR]; }
  const hNow = Math.floor(now / H);
  for (let h = Math.floor(t / H) - 1; h > hNow - HR; h--) { if (T.hId[h % HR] === h) return T.hLast[h % HR]; }
  return null;
}
function pCached(T, off, now) {
  const mi = Math.floor(now / 60);
  if (!T.pc || T.pc.mi !== mi || T.pc.seq !== ROWSEQ) T.pc = { mi, seq: ROWSEQ, v: new Map() };
  if (!T.pc.v.has(off)) T.pc.v.set(off, priceAt(T, now - off, now));
  return T.pc.v.get(off);
}
function hotOf(id, v, ts) {
  const h0 = Math.floor(ts / H); let a = 0, b = 0;
  for (let h = h0 - 6; h <= h0 - 1; h++) if (id[h % HR] === h) a += v[h % HR];
  for (let h = h0 - 30; h <= h0 - 7; h++) if (id[h % HR] === h) b += v[h % HR];
  return { hot: a / 6 > b / 24 ? 1 : 0 };
}
// ---- costs (as engine_st) ----
const feeV23 = (tok, r) => (v3.has(tok) || r.kind !== 'v2') ? 0.01 : 0.003;
function feeV4(r, count) {
  const f = poolFee.get(r.pool);
  if (f != null) { if (count) inc(stats.feeSrc, 'static'); return f; }
  const e = poolEst.get(r.pool);
  if (e && e.est.length) { if (count) inc(stats.feeSrc, 'measured'); const s = e.est.slice().sort((a, b) => a - b); return s[s.length >> 1]; }
  if (count) inc(stats.feeSrc, 'default1pct'); return V4_DEFAULT_FEE;
}
function measureFee(r) {
  let e = poolEst.get(r.pool); if (!e) { e = { lastPq: null, est: [] }; poolEst.set(r.pool, e); }
  if (e.lastPq > 0 && r.price_quote > 0 && r.amount_token > 0 && r.amount_quote > 0) {
    const ex = Math.sqrt(r.price_quote * e.lastPq), ratio = r.amount_quote / (r.amount_token * ex);
    const f = r.side === 'buy' ? ratio - 1 : 1 - ratio;
    if (f > -0.001 && f < 0.99) { e.est.push(Math.max(0, f)); if (e.est.length > 5) e.est.shift(); }
  }
  e.lastPq = r.price_quote;
}
const ethOf = r => r.price_eth > 0 ? r.px / r.price_eth : null;
function buyCost(tok, r, clip) {
  if (r.kind === 'v4') { const eu = ethOf(r); const u = (clip / eu) * S1 / r.depth1_eth; const f = feeV4(r, true);
    return { px: r.px * (1 + u) * (1 + f), u, f }; }
  const f = feeV23(tok, r); return { px: r.px * (r.side === 'sell' ? (1 + f) / (1 - f) : 1) * (1 + SLIP), u: null, f };
}
function sellAt(p, r, pxOverride) {
  if (r.kind === 'v4' && pxOverride == null) {
    const tokensEth = (p.clip / p.entryPx) * r.price_eth; const w = tokensEth * S1 / r.depth1_eth; const f = feeV4(r, false);
    return { px: r.px / (1 + w) * (1 - f), w, f };
  }
  const px = pxOverride != null ? pxOverride : r.px;
  const f = pxOverride != null || r.kind === 'v4' ? V4_DEFAULT_FEE : feeV23(p.tok, r);
  const cross = pxOverride != null ? true : r.side === 'buy';
  return { px: px * (cross ? (1 - f) / (1 + f) : 1) * (1 - SLIP), w: null, f };
}
const wOf = (p, r) => r.kind === 'v4' ? (p.clip / p.entryPx) * r.price_eth * S1 / r.depth1_eth : null;
const priceable = r => r.kind === 'v4' || r.usd >= MINUSD;
// ---- positions ----
const open = new Map(), held = new Map(CELLS.map(c => [c.id, new Set()])), cool = new Map(CELLS.map(c => [c.id, new Map()]));
let globalLast = 0, nextEvt = Infinity, nextAssess = FIT0, pid = 0;
const watch = new Map(); const eligAt = new Map(LEVELS.map(L => [L, []]));
function evtOf(p) { return p.st === 'E' ? p.sigTs + LAT : p.st === 'EW' ? p.eWait : p.st === 'O' ? p.deadline : p.st === 'X' ? p.due : p.xWait; }
function release(p, exitTs) { if (p.kind === 'S') { held.get(p.cell).delete(p.tok); if (exitTs != null) cool.get(p.cell).set(p.tok, exitTs); } }
function base(p) { return { kind: p.kind, tw: p.tw || null, cell: p.cell, dip: p.dipLv, L: p.L, pair: p.pair, rep: p.rep, tok: p.tok, pad: padOf.get(p.tok),
  T: p.T, sigTs: p.sigTs, sigK: p.sigK, dipPct: p.dipPct, src: p.srcCls, eligN: p.eligN, nA: p.nA, mlA: p.mlA, n10: p.n10, dband: p.dband,
  hot: p.hot, sigHot: p.sigHot, h72: p.h72 }; }
function g5price(p, r, ts) {
  const P = r.px;
  if (!(P > X20 * p.eP)) return { px: null, g5: null };
  if (r.kind === 'v4' && wOf(p, r) <= DEPTH_OK_W) return { px: null, g5: 'depthok' };
  const T = toks.get(p.tok); const seen = new Map();
  for (const q of T.rec) if (q.pk === p.ePk && q.ts > ts - CORR_WIN && q.ts <= ts) { if (!seen.has(q.tx) || seen.get(q.tx) < q.px) seen.set(q.tx, q.px); }
  const v = [...seen.values()].sort((a, b) => b - a);
  const C2 = v.length >= 2 ? v[1] : null;
  if (C2 != null && C2 >= P / 2) return { px: P, g5: 'corroborated' };
  if (C2 != null) return { px: Math.min(P, C2), g5: 'c2' };
  return { px: p.lastOk, g5: 'lastok' };
}
function book(p, r, ts, why, extra) {
  const g = g5price(p, r, ts); if (g.g5) inc(stats.g5, `${p.kind}|${g.g5}`);
  const s = sellAt(p, r, g.px);
  const on = 100 * (s.px / p.entryPx - 1) - 0.2;
  W_({ ...base(p), entryTs: p.entryTs, eDelay: p.eDelay, ePk: pkName[p.ePk], eP: p.eP, eU: p.eU, eK: p.eK, entryPx: p.entryPx, eu: p.eu, ef: p.ef, ePons: p.ePons,
      eDepth1: p.eDepth1, sell: p.sell, exitTs: ts, xP: r.px, xU: r.usd, xK: r.kind, xPk: pkName[r.pk], xw: s.w, xPons: r.kind === 'v4' && poolPons.has(r.pool) ? 1 : 0,
      g5: g.g5, g5px: g.px, sellPx: s.px, on, reason: why, nPostSell: p.nPostSell, otherPool: p.otherPool, drainBlocked: p.drainBlocked, ...extra });
  if (p.otherPool > 0) stats.fixB.positionsWithOtherPool++;
  if (p.drainBlocked > 0) stats.fixC.blockedPos++;
  stats.exits++; release(p, ts); p.st = 'done';
}
function sellFlags(Tk, pk, ts) {
  const P = Tk.pools.get(pk); if (!P) return null;
  let ns = 0, nb = 0; const sp = [], bp = [];
  for (const [t, s, px] of P.rs) if (t > ts - H && t <= ts) { if (s) { ns++; sp.push(px); } else { nb++; bp.push(px); } }
  const med = a => { const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };
  return { s10h: P.lastSell10 > ts - H ? 1 : 0, ns, sbr: sp.length && bp.length ? med(sp) / med(bp) : null };
}
function fill(p, r, delay) {
  if (r.kind === 'v4' && r.depth1_eth < DEPTH_FLOOR) {                           // FIX 2 depth floor: skip, no cooldown (engine_wh.js)
    W_({ ...base(p), skipDepth: 1, eDepth1: r.depth1_eth, entryTs: r.ts }); inc(stats.skipDepth, `${p.cell}|${p.kind}${p.tw || ''}`); release(p, null); p.st = 'done'; return;
  }
  p.st = 'O'; p.entryTs = r.ts > p.sigTs + LAT ? r.ts : p.sigTs + LAT; p.eDelay = delay; p.eP = r.px; p.eU = r.usd; p.eK = r.kind; p.ePk = r.pk;
  const b = buyCost(p.tok, r, p.clip); p.entryPx = b.px; p.eu = b.u; p.ef = b.f; p.ePons = r.kind === 'v4' && poolPons.has(r.pool) ? 1 : 0;
  p.eDepth1 = r.kind === 'v4' ? r.depth1_eth : null;
  p.deadline = p.entryTs + p.hold; p.line = p.entryPx * p.tp; p.nPostSell = 0; p.lastOk = r.px; p.last = r;
  p.otherPool = 0; p.drainBlocked = 0;
  p.sell = sellFlags(toks.get(p.tok), r.pk, Math.max(r.ts, p.entryTs));
}
function planExit(p, plan, why) {
  p.trig = why;
  if (priceable(p.last)) { book(p, p.last, plan, why); return true; }
  p.st = 'XW'; p.xWait = plan + XWAIT; return false;
}
function clockTo(p, now) {
  if (p.st === 'E' && now > p.sigTs + LAT) {
    if (p.last && priceable(p.last)) { fill(p, p.last, 0); if (p.st === 'done') return true; } else { p.st = 'EW'; p.eWait = p.sigTs + LAT + EWAIT; }
  }
  if (p.st === 'EW' && now > p.eWait) { W_({ ...base(p), nofill: 1 }); stats.nofill++; release(p, null); p.st = 'done'; return true; }
  if (p.st === 'O' && now >= p.deadline) { if (planExit(p, p.deadline, 'time')) return true; }
  if (p.st === 'X' && now > p.due) { if (planExit(p, p.due, 'tp')) return true; }
  if (p.st === 'XW' && now > p.xWait) { book(p, p.last, p.xWait, 'fb', { fb: 1 }); return true; }
  return false;
}
function drainTest(p, r) {
  if (r.kind === 'v4' && wOf(p, r) <= DEPTH_OK_W) return 'depthok';
  const T = toks.get(p.tok), tx = new Set();
  for (const q of T.rec) if (q.pk === p.ePk && q.ts > r.ts - CORR_WIN && q.ts <= r.ts && q.px < 2 * DRAIN * p.eP) tx.add(q.tx);
  return tx.size >= 2 ? 'corroborated' : null;
}
function onPrint(p, r) {
  if (clockTo(p, r.ts)) return true;
  if (p.st === 'E' || p.st === 'EW') {
    if (p.tgt != null && r.pk !== p.tgt) return false;                                 // mode P: entry on the target pool only
    if (p.st === 'E') { p.last = r; return false; }
    if (priceable(r)) { fill(p, r, r.ts - (p.sigTs + LAT)); if (p.st === 'done') return true; } else p.last = r; return false;
  }
  if (r.pk !== p.ePk) { p.otherPool++; stats.fixB.otherPoolPrintsSeen++; return false; }        // FIX b: exits on the entry pool only
  if (r.side === 'sell') p.nPostSell++;
  if (r.usd >= MINUSD && r.px <= X20 * p.eP) p.lastOk = r.px;
  if (r.px < DRAIN * p.eP) {
    const dt = drainTest(p, r);
    if (dt) { stats.fixC['fired_' + dt]++; book(p, r, r.ts, 'drain', { drainTest: dt }); return true; }
    p.drainBlocked++; stats.fixC.blocked++;
  }
  if (p.st === 'XW' && priceable(r)) { book(p, r, r.ts, p.trig); return true; }
  if (p.st === 'O' && ((r.kind !== 'v4' && r.usd >= MINUSD && r.px >= p.line) || (r.kind === 'v4' && r.px / (1 + wOf(p, r)) >= p.line))) { p.st = 'X'; p.due = r.ts + LAT; }
  p.last = r; return false;
}
function sweep() {
  let nx = Infinity;
  for (const [tok, ps] of open) {
    for (let k = ps.length - 1; k >= 0; k--) { const p = ps[k]; if (p.st === 'done' || clockTo(p, globalLast)) { ps.splice(k, 1); continue; } const e = evtOf(p); if (e < nx) nx = e; }
    if (!ps.length) open.delete(tok);
  }
  nextEvt = nx;
}
function addPos(p) { (open.get(p.tok) || open.set(p.tok, []).get(p.tok)).push(p); const e = evtOf(p); if (e < nextEvt) nextEvt = e; }
function onHole() {
  for (const [, ps] of open) for (const p of ps) { if (p.st === 'done') continue; W_({ ...base(p), trunc: 'hole', at: globalLast, st: p.st }); stats.trunc++; release(p, null); }
  open.clear(); watch.clear(); for (const k of eligAt.keys()) eligAt.set(k, []); stats.holes++; stats.holeAt.push(globalLast); nextEvt = Infinity;
}
const srcCls = Tk => Tk.hasV4 && Tk.hasV23 ? 'both' : Tk.hasV4 ? 'v4' : 'v23';
function assess(T) {
  watch.clear(); for (const k of eligAt.keys()) eligAt.set(k, []);
  if (T > LAST) return;
  const half = halfOf(T); inc(stats.assess, half);
  for (const [tok, Tk] of toks) {
    if (Tk.last < T - H || !Tk.lastR) continue;
    const sc = srcCls(Tk); const b = birth.get(tok), age = T - (b != null ? b : Tk.first);
    inc(stats.cand, `${half}|${sc}`);
    if (age < BASE.age) { inc(stats.drop, `${half}|age`); continue; }
    if (scamAt(tok, T)) { inc(stats.drop, `${half}|scam`); continue; }
    const h72 = hours72(Tk, T), meas = (T - 72 * H >= Tk.cov) || (b != null && b >= Tk.cov);
    Tk.h72 = h72; Tk.meas = meas; Tk.sc = sc;
    const pend = new Set();
    for (const L of LEVELS) {
      if (L > 0 && !meas) { inc(stats.drop, `${half}|L${L}|unmeasurable|${sc}`); continue; }
      if (L > 0 && h72 < L) { inc(stats.drop, `${half}|L${L}|h72`); continue; }
      inc(stats.eligL, `${half}|L${L}|${sc}`); eligAt.get(L).push(tok);
      for (const c of CELLS) if (c.L === L) pend.add(c.id);
    }
    if (pend.size) watch.set(tok, { T, pend });
  }
}
function profile(Tt, now) {                    // activity-twin matching variables at the signal moment (cached per exact timestamp)
  if (Tt.prf && Tt.prf.ts === now && Tt.prf.seq === ROWSEQ) return Tt.prf.v;            // twinfix: same second AND same row
  stats.profCalls++;
  const mp = mainPoolC(Tt, now), P = mp >= 0 ? Tt.pools.get(mp) : null;
  const lr = P ? P.lastR : null;
  const dband = !lr ? -2 : lr.kind === 'v4' ? band(lr.depth1_eth, DEPTH_EDGES) : -1;
  const hv = P ? poolHigh1h(P, now) : 0, dd1h = hv > 0 && P.lastPx > 0 ? 1 - P.lastPx / hv : null;
  const nn = n10(Tt, now);
  const v = { n10: nn, nb: band(nn, N10_EDGES), dband, kindV4: lr && lr.kind === 'v4' ? 1 : 0, dd1h, mp };
  Tt.prf = { ts: now, seq: ROWSEQ, v }; return v;
}
const CELLS_BY_ID = new Map(CELLS.map(c => [c.id, c]));
function onWatchedPrint(tok, r, w, mp) {
  if (r.pk !== mp) return;                                                          // mode P: the dip must print on the MAIN pool
  const Tk = toks.get(tok), half = halfOf(w.T);
  const hv = poolHigh1h(Tk.pools.get(r.pk), r.ts); if (!(hv > 0)) return;
  const dd = 1 - r.px / hv;
  let sp = null, sH = null;
  for (const id of [...w.pend]) {
    const c = CELLS_BY_ID.get(id);
    if (dd < c.dip) continue;
    if (held.get(c.id).has(tok)) { inc(stats.heldSkip, c.id); continue; }
    const lc = cool.get(c.id).get(tok); if (lc != null && r.ts < lc + c.cool) { inc(stats.coolSkip, c.id); continue; }
    w.pend.delete(c.id); inc(stats.trig, `${half}|${c.id}`);
    const cand = eligAt.get(c.L).filter(t => { if (held.get(c.id).has(t)) return false; const l2 = cool.get(c.id).get(t); return !(l2 != null && r.ts < l2 + c.cool); });
    held.get(c.id).add(tok);
    if (!sp) { sp = profile(Tk, r.ts); sH = hotOf(Tk.hId, Tk.hVol, r.ts); }
    const noDip = q => q.dd1h != null && q.dd1h < c.dip / 2;
    const others = cand.filter(t => t !== tok);
    let poolA = others.filter(t => { const q = profile(toks.get(t), r.ts); return q.nb === sp.nb && q.dband === sp.dband && noDip(q); }), mlA = 1;
    if (!poolA.length) { poolA = others.filter(t => { const q = profile(toks.get(t), r.ts); return q.nb === sp.nb && q.kindV4 === sp.kindV4 && noDip(q); }); mlA = poolA.length ? 2 : 0; }
    inc(stats.matchLvl, `${half}|${c.id}|A${mlA}`);
    const id2 = ++pid, com = { cell: c.id, dipLv: c.dip * 100, L: c.L, hold: c.hold, tp: c.tp, clip: CLIP, pair: id2, T: w.T, st: 'E', sigTs: r.ts, sigK: r.kind,
      dipPct: 100 * dd, eligN: cand.length, nA: poolA.length, mlA, sigHot: sH.hot };
    addPos({ ...com, kind: 'S', rep: null, tok, last: r, tgt: r.pk, srcCls: Tk.sc, n10: sp.n10, dband: sp.dband, hot: sH.hot, h72: Tk.h72 });
    const mk = (t, tw, k) => { const Tt = toks.get(t), q = profile(Tt, r.ts);
      addPos({ ...com, kind: 'W', tw, rep: k, tok: t, last: q.mp >= 0 ? Tt.pools.get(q.mp).lastR : null, tgt: q.mp, srcCls: Tt.sc, n10: q.n10, dband: q.dband,
        hot: hotOf(Tt.hId, Tt.hVol, r.ts).hot, h72: Tt.h72 }); };
    const draw = (pool, tw) => {                                                   // FIX 1 WITHOUT replacement: min(3, |pool|) distinct coins (engine_wh.js)
      if (!pool.length) { inc(stats.twinEmpty, `${c.id}|${tw}`); return; }
      const a = pool.slice(), m = Math.min(REPS, a.length);
      for (let k = 0; k < m; k++) { const j = k + Math.floor(rng() * (a.length - k)); const t = a[j]; a[j] = a[k]; a[k] = t; mk(t, tw, k); }
      inc(stats.twinDistinct, `${halfOf(w.T)}|${c.id}|${tw}${m}`);
    };
    draw(cand, 'R'); draw(poolA, 'A');
  }
}
function onRow(r) {
  ROWSEQ++;                                                                         // twinfix: every row starts with no valid cache
  if (!(r.tok && r.ts)) return;
  if (globalLast && r.ts - globalLast >= HOLE) onHole();
  while (r.ts >= nextAssess) {
    globalLast = Math.max(globalLast, nextAssess - 1); if (globalLast >= nextEvt) sweep();
    if (nextAssess >= FIT0 && nextAssess - globalLast < HOLE) assess(nextAssess); else { watch.clear(); for (const k of eligAt.keys()) eligAt.set(k, []); }
    nextAssess += H;
  }
  if (r.ts > globalLast) { globalLast = r.ts; if (globalLast >= nextEvt) sweep(); }
  if (!padOf.has(r.tok)) return;
  stats.univRows++; if (r.kind === 'v4') stats.univV4++;
  if (r.kind === 'v4') measureFee(r);
  const Tk = tracker(r);
  r.pk = pkOf(poolKey(r));
  const mp = mainPool(Tk, r.ts);                                                  // FIX a
  if (mp >= 0 && mp !== r.pk) {
    const M = Tk.pools.get(mp);
    if (M.lastTs >= r.ts - POOL_REF_AGE && M.lastPx > 0) {
      stats.fixA.checked++; const ratio = r.px / M.lastPx;
      if (ratio > POOL_X || ratio < 1 / POOL_X) { stats.fixA.dropped++; if (r.kind === 'v4') stats.fixA.droppedV4++; else stats.fixA.droppedV23++; return; }
    } else stats.fixA.unchecked++;
  }
  if (!accept(Tk, r)) { stats.bad++; if (r.kind === 'v4') stats.badV4++; return; }
  update(Tk, r);
  const ps = open.get(r.tok);
  if (ps) { for (let k = ps.length - 1; k >= 0; k--) { if (ps[k].st === 'done' || onPrint(ps[k], r)) ps.splice(k, 1); else { const e = evtOf(ps[k]); if (e < nextEvt) nextEvt = e; } } if (!ps.length) open.delete(r.tok); }
  const w = watch.get(r.tok);
  if (w && r.ts - w.T >= H) watch.delete(r.tok);
  else if (w && w.pend.size) onWatchedPrint(r.tok, r, w, mp);
}
// ---- R-0109: ONE stream merged by timestamp across day boundaries (as engine_st) ----
const keyLt = (x, y) => x.ts !== y.ts ? x.ts < y.ts : (x.blk || 0) !== (y.blk || 0) ? (x.blk || 0) < (y.blk || 0) : (x.li || 0) < (y.li || 0);
class Heap { constructor() { this.a = []; } get size() { return this.a.length; } top() { return this.a[0]; }
  push(x) { const a = this.a; a.push(x); let i = a.length - 1; while (i > 0) { const j = (i - 1) >> 1; if (keyLt(a[i], a[j])) { [a[i], a[j]] = [a[j], a[i]]; i = j; } else break; } }
  pop() { const a = this.a, t = a[0], x = a.pop(); if (a.length) { a[0] = x; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
    if (l < a.length && keyLt(a[l], a[m])) m = l; if (r < a.length && keyLt(a[r], a[m])) m = r; if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m; } } return t; } }
async function* v23All() {
  const hp = new Heap(); let maxSeen = 0, lastOut = 0;
  for (const d of RUN) {
    const f = { n: 0, first: null, last: null };
    for await (const r of V4.readV23Day(d)) {
      if (r.ts >= CUT) throw new Error('sealed row read — refused');
      f.n++; if (f.first == null) f.first = r.ts; f.last = r.ts;
      if (r.ts < lastOut) stats.reorder.lateRows++;
      hp.push(r); if (r.ts > maxSeen) maxSeen = r.ts; if (hp.size > stats.reorder.maxHeap) stats.reorder.maxHeap = hp.size;
      while (hp.size && hp.top().ts <= maxSeen - REORDER) { const x = hp.pop(); lastOut = x.ts; yield x; }
    }
    stats.v23Files[d] = f;
  }
  while (hp.size) yield hp.pop();
}
async function* v4All() {
  let last = 0;
  for (const d of RUN) { const f = { n: 0, first: null, last: null };
    for await (const r of V4.readDay(d)) { if (r.ts >= CUT) throw new Error('sealed row read — refused'); f.n++; if (f.first == null) f.first = r.ts; f.last = r.ts;
      if (r.ts < last) stats.v4OutOfOrder++; last = r.ts; yield r; }
    stats.v4Files[d] = f; }
}
async function* streamAll() {
  const a = v23All()[Symbol.asyncIterator](), b = v4All()[Symbol.asyncIterator]();
  let x = await a.next(), y = await b.next();
  while (!x.done || !y.done) {
    if (y.done || (!x.done && !keyLt(y.value, x.value))) { yield x.value; x = await a.next(); } else { yield y.value; y = await b.next(); }
  }
}
(async () => {
  const t0 = Date.now(); let peak = 0, lastTs = 0, day = null;
  for await (const r of streamAll()) {
    if (r.ts >= CUT) throw new Error('sealed row read — refused');
    if (r.kind === 'v4') {
      stats.rowsV4++;
      if (r.src === 'wide' && WIDE0 == null) { WIDE0 = r.ts; stats.wide0 = r.ts; }
      if (r.liquidity === '0' || !(r.depth1_eth > 0) || !(r.price_eth > 0)) { stats.v4skipLiq0++; continue; }
      if (r.quote === 'ETH') r.quote = 'WETH';
    }
    if (r.ts < lastTs) stats.mergedOutOfOrder++; lastTs = r.ts;
    stats.rows++; onRow(r);
    if (stats.rows % 1000000 === 0) { const rss = process.memoryUsage().rss; if (rss > peak) peak = rss; if (rss > 3.2e9) throw new Error('RSS guard ' + rss); }
    const dd = new Date(r.ts * 1000).toISOString().slice(0, 10);
    if (dd !== day) { if (day) console.log(`${day} rows ${stats.rows} v4 ${stats.rowsV4} toks ${toks.size} exits ${stats.exits} open ${[...open.values()].reduce((a, b) => a + b.length, 0)} prof ${stats.profCalls} ${((Date.now() - t0) / 1000).toFixed(0)}s rss ${(process.memoryUsage().rss / 1e6).toFixed(0)}MB`); day = dd; }
  }
  sweep();
  for (const [, ps] of open) for (const p of ps) {
    if (p.st === 'done' || clockTo(p, globalLast) || p.st === 'done') continue;
    if (p.st === 'E' || p.st === 'EW') { W_({ ...base(p), trunc: 'end', st: p.st }); stats.trunc++; continue; }
    book(p, p.last, globalLast, 'end', { fb: 2 }); stats.end++;
  }
  W_({ _meta: { ...stats, pools: pkName.length, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 } });
  gz.end(); console.log(JSON.stringify({ ...stats, v23Files: undefined, v4Files: undefined, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 }));
})();
