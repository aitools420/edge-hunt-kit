#!/usr/bin/env node
// sealed-exam-blockA Option A (coordinator 2026-10-05): + FIX 1 twins WITHOUT replacement, + FIX 2 V4 depth floor 0.001 ETH skipped at fill — both
//   ported from blood-grid-window-history-2026-09-27/engine_wh.js, the two changes the register added "before the run" on 09-27.
// engine_st.js — BLOOD DIP LEAD: STRESS TEST (PREREG.md). Research only, READ-ONLY on the estate.
// Built on ../blood-established-2026-09-27/engine_bes.js (merged V2/V3 + V4, depth-aware V4 pricing, fixed guard, G5 >20x rule,
// FIX a/b/c). CHANGED here (PREREG.md):
//  * two configurations: C1 = selection #2 "all" (age >= 24 h, dip >= 20 % under the 1 h high, TP +30 %, hold 24 h, no cooldown);
//    C2 = established 1 h window (age >= 48 h, >= $10k 24 h volume, sd48 >= 3 %, trend arm A, dip >= 15 % under the 1 h high,
//    TP +15 %, hold 48 h, 6 h cooldown).
//  * two modes per config: M = the originals' merged-series dip, entry at the coin's last print (any pool);
//    P = S1 ONE-POOL: the dip print must be on the coin's MAIN pool and the 1 h high is that pool's own; entry on that pool.
//  * S1/R-0109: ONE global stream merged by timestamp across day boundaries (V2/V3 through a 2 h reorder heap), not per day file.
//  * S3 sellability flags at the fill; S4 activity-matched (A) and down-matched (D) twins beside the random (R) twins;
//    S6 hot flags (coin and launchpad 6 h vs prior 24 h volume); S7 $200/$500 V4 shadows (P mode, strategy + R twins).
// Usage: node engine_st.js <out.ndjson> <meta.tsv> <scam.tsv> <poolfee.tsv>      env STOP_DAY=YYYY-MM-DD for the smoke
'use strict';
const fs = require('fs');
const V4 = require('/home/green/projects/patches/sealed-exam-blockA/engines/v4tape_exam.js');   // sealed-exam-blockA: exam reader (paths + seal constants)
const { acceptNew: accept } = require('./guard.js');
const [OUT, META, SCAM, POOLF] = process.argv.slice(2);
const DAY = 86400, H = 3600, HOLE = 6 * H, LAT = 60, CUT = 1791331200;   // sealed-exam-blockA: CUT = 2026-10-07T00:00:00Z
const DATA0 = Date.parse('2026-09-24T00:00:00Z') / 1000;   // sealed-exam-blockA: warm-up from the open days 09-24..09-26
const FIT0 = Date.parse('2026-09-27T00:00:00Z') / 1000, JUDGE0 = Date.parse('2026-09-27T00:00:00Z') / 1000;   // sealed-exam-blockA: ONE exam window from 09-27T00:00Z
const CONFIGS = [
  { id: 'C1', age: 24 * H, vol: 0, sd: null, meas: false, trend: false, dip: 0.20, tp: 1.30, hold: 24 * H, cool: 0, last: Date.parse('2026-10-05T23:00:00Z') / 1000 },   // sealed-exam-blockA: C1 signals < 10-06T00:00Z
  { id: 'C2', age: 48 * H, vol: 10000, sd: 0.03, meas: true, trend: true, dip: 0.15, tp: 1.15, hold: 48 * H, cool: 6 * H, last: Date.parse('2026-10-04T23:00:00Z') / 1000 }];   // sealed-exam-blockA: rule #1 last assessment = CUT - 49 h
const W = H;                                                                                // both configs: the 1 h window
const CELLS = []; for (const c of CONFIGS) for (const m of ['M', 'P']) CELLS.push({ id: c.id + m, cfg: c, mode: m });
const DEPTH_FLOOR = 0.001;                                                                 // sealed-exam-blockA Option A: FIX 2
const TREND = 1.10, REPS = 3, SEED = 20260927, SLIP = 0.004, DRAIN = 0.05, MINUSD = 10, EWAIT = H, XWAIT = DAY;
const CLIP = 50, SHADOW = [200, 500], S1 = Math.sqrt(1.01) - 1, X20 = 20, CORR_WIN = 30 * 60, DEPTH_OK_W = 0.10, V4_DEFAULT_FEE = 0.01;
const POOL_HL = 6 * H, POOL_X = 2, POOL_REF_AGE = H, REORDER = 2 * H;
const MR = 60, BR = 150, HR = 52, BS = 600;
const N10_EDGES = [1, 3, 10, 30, 100, 300], DEPTH_EDGES = [0.01, 0.03, 0.1, 0.3, 1];
const band = (x, e) => { let i = 0; while (i < e.length && x >= e[i]) i++; return i; };
const PONS_HOOK = '0xe5e702641ea86f4ae6cc3cdaed2b886f976be044';
const VENUE_LABEL = { doppler: 'Doppler', letscash: 'letscash', Klik: 'Klik', 'RWA Launchpad': 'RWA Launchpad' };
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rng = mulberry32(SEED);
const RUN = V4.days('2026-09-24', process.env.STOP_DAY || '2026-10-07');   // sealed-exam-blockA: day files 09-24..10-07 (10-07 = the CUT copy)
for (const d of RUN) if (d >= V4.SEAL_DAY) throw new Error('sealed day in RUN: ' + d);
// ---- labels, births, V4 pool table (as engine_bes) ----
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
const out = fs.createWriteStream(OUT); const W_ = o => out.write(JSON.stringify(o) + '\n');
const stats = { metaLab, v4LabAdded, rows: 0, rowsV4: 0, v4skipLiq0: 0, univRows: 0, univV4: 0, bad: 0, badV4: 0, exits: 0, trunc: 0, end: 0, holes: 0,
  holeAt: [], nofill: 0, assess: {}, cand: {}, drop: {}, eligSrc: {}, trig: {}, trendFail: {}, heldSkip: {}, coolSkip: {}, notMain: {}, twinEmpty: {},
  wide0: null, feeSrc: {}, g5: {}, v23Files: {}, v4Files: {}, reorder: { maxHeap: 0, lateRows: 0 }, mergedOutOfOrder: 0, v4OutOfOrder: 0,
  fixA: { checked: 0, unchecked: 0, dropped: 0, droppedV4: 0, droppedV23: 0 },
  fixB: { otherPoolPrintsSeen: 0, positionsWithOtherPool: 0 },
  fixC: { fired_depthok: 0, fired_corroborated: 0, blocked: 0, blockedPos: 0 },
  shadow: { spawned: 0, noscale: 0 }, crossPoolDip: {}, matchLvl: {}, skipDepth: {}, twinDistinct: {} };
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
    hId: new Int32Array(HR).fill(-1), hLast: new Float32Array(HR), hVol: new Float64Array(HR), rec: [], q10: [], pc: null, mpc: null }; toks.set(r.tok, T); }
  return T;
}
function mainPool(T, ts) {
  let best = -1, bv = -1;
  for (const [pk, P] of T.pools) { const v = P.vol * Math.pow(2, -(ts - P.vts) / POOL_HL); if (v > bv) { bv = v; best = pk; } }
  return best;
}
let ROWSEQ = 0;   // twinfix-2026-10-05 (Chef TG 16695, pond #297/#298): one row counter, ++ once at the top of onRow; a cache below hits only within the SAME row
function mainPoolC(T, ts) { const mi = Math.floor(ts / 60); if (!T.mpc || T.mpc.mi !== mi || T.mpc.seq !== ROWSEQ) T.mpc = { mi, seq: ROWSEQ, v: mainPool(T, ts) }; return T.mpc.v; }
function poolHigh1h(P, ts) {                   // max accepted price on ONE pool over the last 60 minute buckets incl. the current one
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
function trendOk(T, cfg, now) {                // arm A of blood-established, W = 1 h
  if (!cfg.trend) return true;
  const pw = pCached(T, W, now); if (!(pw > 0)) return false;
  const p0 = pCached(T, 24 * H, now); if (!(p0 > 0)) return false;
  return p0 <= TREND * pw;
}
function high1hMerged(T, ts) {                 // merged-series 1 h high and the pool that printed it (as engine_bes, W = 1 h)
  const mi = Math.floor(ts / 60); let hv = 0, hp = -1;
  for (let a = 0; a < MR; a++) { const m = mi - a, s = m % MR; if (T.mId[s] === m && T.mMax[s] > hv) { hv = T.mMax[s]; hp = T.mPk[s]; } }
  return [hv, hp];
}
function coinStats(T, t0) {
  const h0 = Math.floor(t0 / H); let vol = 0;
  for (let h = h0 - 24; h <= h0 - 1; h++) if (T.hId[h % HR] === h) vol += T.hVol[h % HR];
  let prev = null; const ret = [];
  for (let h = h0 - 49; h <= h0 - 1; h++) {
    const c = T.hId[h % HR] === h ? T.hLast[h % HR] : prev;
    if (c != null && prev != null && c > 0 && prev > 0) ret.push(Math.log(c / prev));
    if (c != null) prev = c;
  }
  let sd = null;
  if (ret.length >= 24) { const m = ret.reduce((a, b) => a + b, 0) / ret.length; sd = Math.sqrt(ret.reduce((a, b) => a + (b - m) * (b - m), 0) / (ret.length - 1)); }
  return { vol, sd, nret: ret.length };
}
function hotOf(id, v, ts) {                    // S6: 6 complete clock hours before the signal hour vs the 24 before those (hourly rates)
  const h0 = Math.floor(ts / H); let a = 0, b = 0;
  for (let h = h0 - 6; h <= h0 - 1; h++) if (id[h % HR] === h) a += v[h % HR];
  for (let h = h0 - 30; h <= h0 - 7; h++) if (id[h % HR] === h) b += v[h % HR];
  return { hot: a / 6 > b / 24 ? 1 : 0, v6: a, v24p: b };
}
// ---- costs (as engine_bes) ----
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
  if (r.kind === 'v4') { const eu = ethOf(r); const u = (clip / eu) * S1 / r.depth1_eth; const f = feeV4(r, clip === CLIP);
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
const cellById = new Map(CELLS.map(c => [c.id, c]));
let globalLast = 0, nextEvt = Infinity, nextAssess = FIT0, pid = 0;
const watch = new Map(); const eligAt = new Map(CONFIGS.map(c => [c.id, []]));
function evtOf(p) { return p.st === 'E' ? p.sigTs + LAT : p.st === 'EW' ? p.eWait : p.st === 'O' ? p.deadline : p.st === 'X' ? p.due : p.xWait; }
function release(p, exitTs) { if (p.kind === 'S' && p.clip === CLIP) { held.get(p.cell).delete(p.tok); if (exitTs != null) cool.get(p.cell).set(p.tok, exitTs); } }
function base(p) { return { kind: p.kind, tw: p.tw || null, cell: p.cell, cfg: p.cfgId, mode: p.mode, clip: p.clip, pair: p.pair, rep: p.rep, tok: p.tok, pad: padOf.get(p.tok),
  v3: v3.has(p.tok) ? 1 : 0, T: p.T, sigTs: p.sigTs, sigU: p.sigU, sigK: p.sigK, sigPk: p.sigPk, hiPk: p.hiPk, dipPct: p.dipPct, src: p.srcCls, eligN: p.eligN,
  nA: p.nA, nD: p.nD, mlA: p.mlA, n10: p.n10, dband: p.dband, r6: p.r6, dd1h: p.dd1h, hot: p.hot, padHot: p.padHot, cvol: p.cvol, csd: p.csd, sigHot: p.sigHot, sigPadHot: p.sigPadHot }; }
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
  const g = g5price(p, r, ts); if (g.g5) inc(stats.g5, `${p.kind}|${p.clip}|${g.g5}`);
  const s = sellAt(p, r, g.px);
  const on = 100 * (s.px / p.entryPx - 1) - 0.2;
  W_({ ...base(p), entryTs: p.entryTs, eDelay: p.eDelay, ePk: pkName[p.ePk], eP: p.eP, eS: p.eS, eU: p.eU, eK: p.eK, entryPx: p.entryPx, eu: p.eu, ef: p.ef, eHook0: p.eHook0, ePons: p.ePons,
      eDepth1: p.eDepth1, eEthUsd: p.eEthUsd, sell: p.sell,
      exitTs: ts, xPlan: p.xPlan == null ? null : p.xPlan, xP: r.px, xS: r.side, xU: r.usd, xK: r.kind, xPk: pkName[r.pk],
      xw: s.w, xf: s.f, xHook0: r.kind === 'v4' && poolHook0.has(r.pool) ? 1 : 0, xPons: r.kind === 'v4' && poolPons.has(r.pool) ? 1 : 0, g5: g.g5, g5px: g.px, sellPx: s.px, on,
      reason: why, trig: p.trig || null, nPost: p.nPost, nPostSell: p.nPostSell, minPost: p.minPost === Infinity ? null : p.minPost, maxPost: p.maxPost,
      otherPool: p.otherPool, drainBlocked: p.drainBlocked, ...extra });
  if (p.clip === CLIP && p.otherPool > 0) stats.fixB.positionsWithOtherPool++;
  if (p.clip === CLIP && p.drainBlocked > 0) stats.fixC.blockedPos++;
  stats.exits++; release(p, ts); p.st = 'done';
}
function sellFlags(Tk, pk, ts) {               // S3: what the entry pool's own prints said about selling it, at the fill
  const P = Tk.pools.get(pk); if (!P) return null;
  let ns = 0, nb = 0; const sp = [], bp = [];
  for (const [t, s, px] of P.rs) if (t > ts - H && t <= ts) { if (s) { ns++; sp.push(px); } else { nb++; bp.push(px); } }
  const med = a => { const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };
  let anySell10 = 0; for (const [, Q] of Tk.pools) if (Q.lastSell10 > ts - H) { anySell10 = 1; break; }
  return { s10h: P.lastSell10 > ts - H ? 1 : 0, s1h: P.lastSell1 > ts - H ? 1 : 0, s1d: P.lastSell1 > ts - DAY ? 1 : 0, ns, nb,
    sbr: sp.length && bp.length ? med(sp) / med(bp) : null, anyPoolS10h: anySell10 };
}
function fill(p, r, delay) {
  if (r.kind === 'v4' && r.depth1_eth < DEPTH_FLOOR) {                           // FIX 2 depth floor: skip, no cooldown (engine_wh.js)
    W_({ ...base(p), skipDepth: 1, eDepth1: r.depth1_eth, entryTs: r.ts }); inc(stats.skipDepth, `${p.cell}|${p.kind}${p.tw || ''}`); release(p, null); p.st = 'done'; return;
  }
  p.st = 'O'; p.entryTs = r.ts > p.sigTs + LAT ? r.ts : p.sigTs + LAT; p.eDelay = delay; p.eP = r.px; p.eS = r.side; p.eU = r.usd; p.eK = r.kind; p.ePk = r.pk;
  const b = buyCost(p.tok, r, p.clip); p.entryPx = b.px; p.eu = b.u; p.ef = b.f; p.eHook0 = r.kind === 'v4' && poolHook0.has(r.pool) ? 1 : 0; p.ePons = r.kind === 'v4' && poolPons.has(r.pool) ? 1 : 0;
  p.eDepth1 = r.kind === 'v4' ? r.depth1_eth : null; p.eEthUsd = r.kind === 'v4' ? ethOf(r) : null;
  p.deadline = p.entryTs + p.hold; p.line = p.entryPx * p.tp; p.nPost = 0; p.nPostSell = 0; p.minPost = Infinity; p.maxPost = 0; p.lastOk = r.px; p.last = r;
  p.otherPool = 0; p.drainBlocked = 0;
  if (p.clip === CLIP) p.sell = sellFlags(toks.get(p.tok), r.pk, Math.max(r.ts, p.entryTs));
  if (p.clip === CLIP && r.kind === 'v4' && p.mode === 'P' && (p.kind === 'S' || p.tw === 'R')) for (const c of SHADOW) {       // S7 shadows
    const u = (c / ethOf(r)) * S1 / r.depth1_eth;
    if (!(u <= DEPTH_OK_W)) { stats.shadow.noscale++; W_({ ...base(p), clip: c, noscale: 1, u }); continue; }
    const q = { ...p, clip: c, st: 'E' }; fill(q, r, delay); q.entryTs = p.entryTs; q.deadline = p.deadline; q.sell = p.sell; stats.shadow.spawned++; addPos(q);
  }
}
function planExit(p, plan, why) {
  p.xPlan = plan; p.trig = why;
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
    if (p.tgt != null && r.pk !== p.tgt) return false;                                 // P mode: the entry is on the target pool only
    if (p.st === 'E') { p.last = r; return false; }
    if (priceable(r)) { fill(p, r, r.ts - (p.sigTs + LAT)); if (p.st === 'done') return true; } else p.last = r; return false;
  }
  if (r.pk !== p.ePk) { p.otherPool++; if (p.clip === CLIP) stats.fixB.otherPoolPrintsSeen++; return false; }        // FIX b
  p.nPost++; if (r.side === 'sell') p.nPostSell++; if (r.px < p.minPost) p.minPost = r.px; if (r.px > p.maxPost) p.maxPost = r.px;
  if (r.usd >= MINUSD && r.px <= X20 * p.eP) p.lastOk = r.px;
  if (r.px < DRAIN * p.eP) {
    const dt = drainTest(p, r);
    if (dt) { if (p.clip === CLIP) stats.fixC['fired_' + dt]++; p.xPlan = null; book(p, r, r.ts, 'drain', { drainTest: dt, trigBefore: p.st }); return true; }
    p.drainBlocked++; if (p.clip === CLIP) stats.fixC.blocked++;
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
  const half = halfOf(T); inc(stats.assess, half);
  for (const [tok, Tk] of toks) {
    if (Tk.last < T - H || !Tk.lastR) continue;
    const sc = srcCls(Tk); const b = birth.get(tok), age = T - (b != null ? b : Tk.first);
    let cs = null; const pend = new Set();
    for (const cfg of CONFIGS) {
      if (T > cfg.last) continue;
      const k = `${cfg.id}|${half}`; inc(stats.cand, `${k}|${sc}`);
      if (age < cfg.age) { inc(stats.drop, `${k}|age`); continue; }
      if (scamAt(tok, T)) { inc(stats.drop, `${k}|scam`); continue; }
      if (cfg.meas && !((T - 49 * H >= Tk.cov) || (b != null && b >= Tk.cov))) { inc(stats.drop, `${k}|unmeasurable|${sc}`); continue; }
      if (cfg.vol > 0 || cfg.sd != null) {
        if (!cs) cs = coinStats(Tk, T);
        if (cs.vol < cfg.vol) { inc(stats.drop, `${k}|vol24`); continue; }
        if (cs.sd == null) { inc(stats.drop, `${k}|sd_nret<24`); continue; }
        if (cs.sd < cfg.sd) { inc(stats.drop, `${k}|sd48`); continue; }
      }
      inc(stats.eligSrc, `${k}|${sc}`); eligAt.get(cfg.id).push(tok);
      for (const c of CELLS) if (c.cfg === cfg) pend.add(c.id);
    }
    if (!pend.size) continue;
    if (!cs) cs = coinStats(Tk, T);
    Tk.cs = cs; Tk.sc = sc;
    watch.set(tok, { T, pend });
  }
}
function profile(Tt, now, cfg) {               // S4 matching variables of a coin at the signal moment
  const mp = mainPoolC(Tt, now), P = mp >= 0 ? Tt.pools.get(mp) : null;
  const lr = P ? P.lastR : null;
  const dband = !lr ? -2 : lr.kind === 'v4' ? band(lr.depth1_eth, DEPTH_EDGES) : -1;
  const hv = P ? poolHigh1h(P, now) : 0, dd1h = hv > 0 && P.lastPx > 0 ? 1 - P.lastPx / hv : null;
  const p6 = pCached(Tt, 6 * H, now), r6 = p6 > 0 && Tt.lastR ? Tt.lastR.px / p6 - 1 : null;
  return { n10: n10(Tt, now), nb: band(n10(Tt, now), N10_EDGES), dband, kindV4: lr && lr.kind === 'v4' ? 1 : 0, dd1h, r6, mp };
}
function onWatchedPrint(tok, r, w, mp) {
  const Tk = toks.get(tok), half = halfOf(w.T);
  let hvM = null, hvP = null;
  for (const c of CELLS) {
    if (!w.pend.has(c.id)) continue;
    const cfg = c.cfg; let hv, hp;
    if (c.mode === 'M') { if (!hvM) hvM = high1hMerged(Tk, r.ts); [hv, hp] = hvM; }
    else {
      if (r.pk !== mp) { continue; }                                                  // S1: the dip must print on the MAIN pool
      if (hvP == null) hvP = poolHigh1h(Tk.pools.get(r.pk), r.ts); hv = hvP; hp = r.pk;
    }
    if (!(hv > 0) || 1 - r.px / hv < cfg.dip) continue;
    if (held.get(c.id).has(tok)) { inc(stats.heldSkip, c.id); continue; }
    const lc = cool.get(c.id).get(tok); if (lc != null && r.ts < lc + cfg.cool) { inc(stats.coolSkip, c.id); continue; }
    if (!trendOk(Tk, cfg, r.ts)) { inc(stats.trendFail, `${half}|${c.id}`); continue; }
    w.pend.delete(c.id); inc(stats.trig, `${half}|${c.id}`);
    inc(stats.crossPoolDip, `${half}|${c.id}|${hp !== r.pk ? 'cross' : 'same'}`);
    const cand = eligAt.get(cfg.id).filter(t => { if (held.get(c.id).has(t)) return false; const l2 = cool.get(c.id).get(t); if (l2 != null && r.ts < l2 + cfg.cool) return false; return trendOk(toks.get(t), cfg, r.ts); });
    held.get(c.id).add(tok);
    const sp = profile(Tk, r.ts, cfg);
    const sH = hotOf(Tk.hId, Tk.hVol, r.ts), pv = padVol.get(padOf.get(tok)), sPH = pv ? hotOf(pv.id, pv.v, r.ts) : { hot: null };
    // S4 twin pools. A: same $10+-trade-count band AND same main-pool depth band, no dip (1 h drawdown on its main pool < dip/2).
    // Fallback (matchLvl 2): same count band and same venue kind. D: fell >= dip over 6 h (and > -60 %), no dip now.
    const prof = new Map(); for (const t of cand) if (t !== tok) prof.set(t, profile(toks.get(t), r.ts, cfg));
    const noDip = q => q.dd1h != null && q.dd1h < cfg.dip / 2;
    let poolA = [...prof].filter(([, q]) => q.nb === sp.nb && q.dband === sp.dband && noDip(q)).map(x => x[0]), mlA = 1;
    if (!poolA.length) { poolA = [...prof].filter(([, q]) => q.nb === sp.nb && q.kindV4 === sp.kindV4 && noDip(q)).map(x => x[0]); mlA = poolA.length ? 2 : 0; }
    const poolD = [...prof].filter(([, q]) => q.r6 != null && q.r6 <= -cfg.dip && q.r6 > -0.6 && noDip(q)).map(x => x[0]);
    inc(stats.matchLvl, `${half}|${c.id}|A${mlA}`);
    const id = ++pid, com = { cell: c.id, cfgId: cfg.id, mode: c.mode, hold: cfg.hold, tp: cfg.tp, clip: CLIP, pair: id, T: w.T, st: 'E', sigTs: r.ts, sigU: r.usd, sigK: r.kind,
      sigPk: pkName[r.pk], hiPk: hp >= 0 ? pkName[hp] : null, dipPct: 100 * (1 - r.px / hv), eligN: cand.length, nA: poolA.length, nD: poolD.length, mlA,
      sigHot: sH.hot, sigPadHot: sPH.hot };
    addPos({ ...com, kind: 'S', rep: null, tok, last: r, tgt: c.mode === 'P' ? r.pk : null, srcCls: Tk.sc, cvol: Tk.cs.vol, csd: Tk.cs.sd,
      n10: sp.n10, dband: sp.dband, r6: sp.r6, dd1h: sp.dd1h, hot: sH.hot, padHot: sPH.hot });
    const mk = (t, tw, k) => { const Tt = toks.get(t), q = prof.get(t) || profile(Tt, r.ts, cfg), tH = hotOf(Tt.hId, Tt.hVol, r.ts), tpv = padVol.get(padOf.get(t));
      const tgt = c.mode === 'P' ? q.mp : null, last = c.mode === 'P' ? (q.mp >= 0 ? Tt.pools.get(q.mp).lastR : null) : Tt.lastR;
      addPos({ ...com, kind: 'W', tw, rep: k, tok: t, last, tgt, srcCls: Tt.sc, cvol: Tt.cs ? Tt.cs.vol : null, csd: Tt.cs ? Tt.cs.sd : null,
        n10: q.n10, dband: q.dband, r6: q.r6, dd1h: q.dd1h, hot: tH.hot, padHot: tpv ? hotOf(tpv.id, tpv.v, r.ts).hot : null }); };
    const draw = (pool, tw) => {                                                   // FIX 1 WITHOUT replacement: min(3, |pool|) distinct coins (engine_wh.js)
      if (!pool.length) { inc(stats.twinEmpty, `${c.id}|${tw}`); return; }
      const a = pool.slice(), m = Math.min(REPS, a.length);
      for (let k = 0; k < m; k++) { const j = k + Math.floor(rng() * (a.length - k)); const t = a[j]; a[j] = a[k]; a[k] = t; mk(t, tw, k); }
      inc(stats.twinDistinct, `${halfOf(w.T)}|${c.id}|${tw}${m}`);
    };
    draw(cand, 'R'); draw(poolA, 'A'); draw(poolD, 'D');
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
// ---- R-0109: ONE stream merged by timestamp across day boundaries ----
const keyLt = (x, y) => x.ts !== y.ts ? x.ts < y.ts : (x.blk || 0) !== (y.blk || 0) ? (x.blk || 0) < (y.blk || 0) : (x.li || 0) < (y.li || 0);
class Heap { constructor() { this.a = []; } get size() { return this.a.length; } top() { return this.a[0]; }
  push(x) { const a = this.a; a.push(x); let i = a.length - 1; while (i > 0) { const j = (i - 1) >> 1; if (keyLt(a[i], a[j])) { [a[i], a[j]] = [a[j], a[i]]; i = j; } else break; } }
  pop() { const a = this.a, t = a[0], x = a.pop(); if (a.length) { a[0] = x; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
    if (l < a.length && keyLt(a[l], a[m])) m = l; if (r < a.length && keyLt(a[r], a[m])) m = r; if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m; } } return t; } }
async function* v23All() {                     // every day file in order, through a REORDER-second reorder heap
  const hp = new Heap(); let maxSeen = 0, lastOut = 0;
  for (const d of RUN) {
    const f = { n: 0, minTs: Infinity, maxTs: 0, first: null, last: null };
    for await (const r of V4.readV23Day(d)) {
      if (r.ts >= CUT) throw new Error('sealed row read — refused');
      f.n++; if (f.first == null) f.first = r.ts; f.last = r.ts; if (r.ts < f.minTs) f.minTs = r.ts; if (r.ts > f.maxTs) f.maxTs = r.ts;
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
    if (dd !== day) { if (day) console.log(`${day} rows ${stats.rows} v4 ${stats.rowsV4} toks ${toks.size} exits ${stats.exits} open ${[...open.values()].reduce((a, b) => a + b.length, 0)} ${((Date.now() - t0) / 1000).toFixed(0)}s rss ${(process.memoryUsage().rss / 1e6).toFixed(0)}MB`); day = dd; }
  }
  sweep();
  for (const [, ps] of open) for (const p of ps) {
    if (p.st === 'done' || clockTo(p, globalLast) || p.st === 'done') continue;
    if (p.st === 'E' || p.st === 'EW') { W_({ ...base(p), trunc: 'end', st: p.st }); stats.trunc++; continue; }
    book(p, p.last, globalLast, 'end', { fb: 2 }); stats.end++;
  }
  W_({ _meta: { ...stats, pools: pkName.length, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 } });
  out.end(); console.log(JSON.stringify({ ...stats, v23Files: undefined, v4Files: undefined, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 }));
})();
