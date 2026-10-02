#!/usr/bin/env node
// engine_v1.js — EDGE MACHINE FROZEN ENGINE v1 (patches/edge-machine-2026-09-30/engine). Research only, READ-ONLY on the estate.
// ONE engine for every Blood batch: batches change CELL PARAMETERS only; a code change is a NEW VERSION (engine_v2.js + a new MANIFEST).
// = ../../blood-lowfee-hunt-2026-09-29/engine_lf.js (sha256 676e05d0…) with BOTH sibling change sets merged in VERBATIM, plus the V1 items:
//  * from ../../blood-hunt3-2026-09-29/engine_h3.js (sha256 721ab624…), tagged H3: cell dial `quote` (the entry print's quote must equal
//    it; twins only from same-quote main pools), cell dial `cap` (max concurrent strategy positions; over it the signal is skipped and the
//    cell stays pending), eQ on booked rows, stats quoteSkip / sigQuote / capSkip / capSkipCoinHours / capLateTaken / peakHeld.
//    Entry delay is the existing dial `lat` (no code change in h3).
//  * from ../../blood-tokenfilter-2026-09-30/engine_tf.js (sha256 de26bea6…; its later DEVIATION D1, sha 00c4558a…, made the same 64-entry
//    ring compaction as V1 below, independently), tagged TOKF: per-pool cumulative sell-row counter, 61-minute
//    accepted-print ring, `tf` = {hiTs, nSell, ties, hiTsLast, nSellLast, hiMatch} on STRATEGY rows (mode P, W 3600). The F1 / F2 token
//    filters are NOT applied here (as in that batch): the reducer applies them as a SPLIT from `tf` (cells.json field `filter`), so a
//    filtered cell is exactly a subset of its base cell's trades.
//  * V1 (new here; results-neutral for every existing cell):
//    - cell dial `rngId` (default = the cell id) = the twin RNG seed key. A cell run under a new id with rngId = an old id draws the SAME
//      twins. Omitted -> identical to every parent: mulberry32(20260927 + fnv(cell id)).
//    - unknown cell dials are REFUSED (a mistyped dial used to be ignored silently).
//    - TOKF ring compaction at 64 stale entries instead of 4,096 (storage only: entries before tfH are never read again).
//    - the _meta line and stdout carry engine: 'v1'.
// What differs between the two parents: lf -> h3 adds quote / cap / eQ; lf -> tf adds the tf features. Neither touches fills, exits, the
// engine's own costs, the RNG, probes or the stream. Every SEAL refusal of the parents is kept (a RUN day >= 2026-09-27 or any row with
// ts >= 1790467200 throws).
// Known inherited property (NOT changed, stated): mainPoolC() caches a coin's main pool per MINUTE at its first call, so a twin profile can
// in principle depend on which other cells share the pass. The parents' identity checks (hunt 3 reproduced low-fee cells in a different
// pass composition exactly) and v1's own row-by-row parity check it: a 6-cell v1 pass reproduced every row and probe of the 40-cell hunt 2
// pass, the 36-cell hunt 3 pass and the 3-cell token-filter pass (parity/PARITY.md).
// Usage: node engine_v1.js <out.ndjson.gz> <meta.tsv> <scam.tsv> <poolfee.tsv> <creators.tsv> <cells.json>   env CELL_IDS, STOP_DAY
// ---- parent headers follow: engine_tf.js, then engine_h3.js -> engine_lf.js -> engine_sk2.js -> ... ----
// engine_tf.js — BLOOD TOKEN FILTERS (../blood-tokenfilter-2026-09-30/PREREG.md). = ../blood-hunt2-2026-09-29/engine_lf.js (sha256 676e05d0…)
// with ONLY (tagged TOKF): a per-pool cumulative SELL-row counter (every row reaching onRow, after r.pk; any size; guard-accepted or not),
// a 61-minute ring of accepted prints [ts, Float32 px, sell count at that print] per pool (pushed in update()), and, on the STRATEGY position
// only, the signal's tf = {hiTs, nSell, ties, hiTsLast, nSellLast, hiMatch}: the earliest accepted print on the main pool in the engine's own
// 1 h window (trigger minute + 59 before) at the window max, the sell rows after it up to and including the trigger. Written on S rows only.
//
// engine_h3.js — BLOOD HUNT 3 (live realism: entry delay × main-pool quote × capital cap; PREREG.md of blood-hunt3-2026-09-29).
// = ../blood-lowfee-hunt-2026-09-29/engine_lf.js (sha256 676e05d0…) with ONLY these changes (tagged H3):
//  * cell param `quote` ('WETH'): the signal (= main = entry) print's quote must be WETH (native ETH is mapped to WETH on read, as before);
//    otherwise the cell stays pending for the hour (as the band skip) and the skip is counted (quoteSkip). Twins are drawn only from
//    candidates whose own main pool is LOW AND WETH-quoted at that moment. Cells without `quote` use the unchanged twin filter.
//  * cell param `cap` (20): when the cell already holds `cap` strategy positions (the held set: from signal to exit), a new signal is SKIPPED
//    (no position, no twins, no cooldown; the cell stays pending, as the live feed re-fires) and counted: capSkip (events),
//    capSkipCoinHours (distinct coin-hours), capLateTaken (coin-hours skipped that later got a slot in the same hour).
//  * entry delay = the existing per-cell `lat` (fill = the last accepted print on the signal pool at or before sig + lat, depth-aware) - no
//    code change, only new values (120, 300, 600 s).
//  * booked rows carry eQ (the entry pool's quote); stats.peakHeld per cell (max concurrent strategy positions, both halves).
// ---- parent header follows ----
// engine_lf.js — BLOOD LOW-FEE HUNT (PREREG.md of blood-lowfee-hunt-2026-09-29). Research only, READ-ONLY.
// = ../blood-skeleton2-2026-09-27/engine_sk2.js (sha256 in PREREG.sha256) with ONLY these changes (tagged LOWFEE):
//  * cells.json = 108 cells dip x trading history x TP x max hold, each with band 'LOW'.
//  * POOL-FEE BAND exactly as ../blood-poolfee-2026-09-27/engine_pf.js exAnteTake(): the signal (= main = entry) pool's EX-ANTE per-side take
//    (Pons: launch terms, now from pons_fee_terms.json = all 8,909 Pons pools; static-fee V4: fee key; dynamic-fee V4: median of the pool's
//    last <= 5 own-swap estimates; no estimate / no key -> UNK; V2/V3 -> V23). LOW = V4 with take <= 1.000 %. A band cell trades only
//    signals whose main pool is LOW (the cell stays pending otherwise, as engine_pf), and draws BOTH twins only from candidates whose own
//    main pool is LOW at that moment.
//  * the 2,713 stock-token-quoted Pons pools are IN (Chef TG 14681): not dropped from the stream; they are in the pool table (poolfee_lf.tsv,
//    built by build_inputs.py) and are counted (stockRows); every booked row carries eStock / xStock.
//  * booked rows carry eBand / eTake / eTy (entry pool band at the fill); RSS guard 3.2 GB.
// engine_sk2.js — BLOOD SKELETON BATCH 2: the stage-1 corners + the dip-shape-history sweep + Chef's 5 x 5 volume x volatility grid
// (PREREG.md). Research only, READ-ONLY. Built on ../blood-skeleton1-2026-09-27/engine_sk.js (sha 0ab1b06c…). CHANGED here:
//  * cells come from cells.json (cells.py); env CELL_IDS = a file with the ids to run in THIS pass (passes split for RSS).
//  * each cell has its OWN twin RNG (mulberry32(SEED + fnv1a(cell id))) so a cell's twins do not depend on which pass it runs in.
//  * new coin filters: trading history (hours72 == 72, the grid's measurability rule, at T) and dip shape history (nrec7 >= N at the
//    signal: recovered dip episodes in the 7 days before, episodes on the coin's MAIN pool - PREREG §3); volume up to $10M, sd to 9 %.
//  * new dial: dip measured on the merged series of all the coin's pools (mode M, as engine_st: merged high over the window, the dip
//    print on any pool, entry at the coin's last print on any pool); the held mode is P (the main pool).
//  * LATENCY PROBES (realism): for every position, the pool state (last accepted print at or before t) at the realistic entry and exit
//    moments, written as separate {pr:[...]} lines; the analysis prices the typical / slow latency views from them.
//  * the 1-D levels, the held point and every exit/entry rule are UNCHANGED from batch 1 (the held cell must reproduce batch 1 exactly).
// Usage: node engine_sk2.js <out.ndjson.gz> <meta.tsv> <scam.tsv> <poolfee.tsv> <creators.tsv> <cells.json>   env CELL_IDS, STOP_DAY
// ---- parent header follows ----
// engine_wh.js — BLOOD 2-D GRID: DIP WINDOW x 72 h trading history, at dip 20 % and 25 % (PREREG.md). Research only, READ-ONLY.
// Built on ../blood-grid-depth-history-2026-09-27/engine_grid.js. CHANGED here (PREREG.md §2-§4):
//  * 32 cells = dip {20,25} % x window {5m,15m,1h,4h} (the MAIN pool's own high over the window) x trading history {all,>=24,>=48,72}.
//  * main-pool window high: per-minute maxima for W <= 1 h (current minute + W/60 - 1 before, as the parent's 1 h), per-10-minute
//    maxima for 4 h (the bucket containing sig - W included, as blood-established).
//  * activity twin's no-dip rule uses the CELL's window. * twins drawn WITHOUT replacement (min(3, pool) distinct coins).
//  * V4 entries with depth1_eth < 0.001 are SKIPPED at fill (strategy and twins alike; written as skipDepth rows, no cooldown).
// ---- parent header follows ----
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
const V4 = require('/home/green/projects/patches/v4-join-2026-09-27/v4tape.js');
const { acceptNew: accept } = require('./guard.js');
const [OUT, META, SCAM, POOLF, CREF, CELLSF] = process.argv.slice(2);
const PREPASS = process.env.PREPASS === '1';
const DAY = 86400, H = 3600, HOLE = 6 * H, LAT = 60, CUT = 1790467200;
const DATA0 = Date.parse('2026-09-08T00:00:00Z') / 1000;
const FIT0 = Date.parse('2026-09-11T00:00:00Z') / 1000, JUDGE0 = Date.parse('2026-09-17T00:00:00Z') / 1000;
const LAST = Date.parse('2026-09-25T20:00:00Z') / 1000;
const WINDOWS = [300, 3600, 86400];
const LARGEST = 'Pons', BUY_N = 4;                                                   // BUY_N = batch 1's pre-pass median (fixed there)
const LAST72 = Date.parse('2026-09-23T20:00:00Z') / 1000;                          // 72 h hold: every position can reach its max hold before the seal
const BASE = { dip: 0.20, W: 3600, L: 0, age: 24 * H, lat: 60, tp: 1.30, hold: 24 * H, cool: 6 * H, last: Infinity, mode: 'P' };
const EP_DIP = 0.20, EP_GAP = 6 * H, EP_REC = 1.20, EP_RECWIN = 24 * H, EP_LOOK = 7 * DAY;     // dip-history episodes (selection #1)
const PFT = JSON.parse(fs.readFileSync('/home/green/projects/patches/pons-feeterms-2026-09-27/pons_fee_terms.json', 'utf8')).pools;   // LOWFEE
const STOCKPONS = new Set(Object.entries(PFT).filter(([, v]) => v.in_pool_table === false).map(([k]) => k));   // LOWFEE: 2,713 stock-quoted Pons pools, now IN (counted only)
const ponsTake = new Map(Object.entries(PFT).filter(([, v]) => v.status === 'measured').map(([k, v]) => [k, (v.hookFeeBps + v.creatorTaxBps) / 1e4]));   // LOWFEE
const LAT_B = 43.8, LAT_B90 = 187.8, LAT_S = 3.3, LAT_S90 = 15.1;                  // realism latency.json defaults (buy / sell, median / p90 recent)
const fnv = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); } return h >>> 0; };
const DIALS = new Set(['dip', 'W', 'L', 'age', 'lat', 'tp', 'hold', 'cool', 'mode', 'padMode', 'volMin', 'sdMin', 'buyMin', 'creator', 'th', 'range', 'dh', 'band', 'quote', 'cap']);   // V1
const CJ = JSON.parse(fs.readFileSync(CELLSF, 'utf8'));
const WANT = process.env.CELL_IDS ? new Set(fs.readFileSync(process.env.CELL_IDS, 'utf8').split(/\s+/).filter(Boolean)) : null;
const CELLS = CJ.cells.filter(c => !WANT || WANT.has(c.id)).map(c => {
  const p = { ...c.params }; const last = p.last72 ? LAST72 : Infinity; delete p.last72;
  const rid = p.rngId != null ? String(p.rngId) : c.id; delete p.rngId;                                        // V1: twin RNG key
  for (const k of Object.keys(p)) if (!DIALS.has(k)) throw new Error(`unknown cell dial '${k}' in ${c.id}`);      // V1: refuse typos
  if (p.buyMin) p.buyMin = BUY_N;
  return { ...BASE, ...p, id: c.id, last, rng: mulberry32((20260927 + fnv(rid)) | 0) }; });   // V1: rid (= c.id unless rngId)
if (WANT && CELLS.length !== WANT.size) throw new Error('unknown cell id in CELL_IDS');
const DEPTH_FLOOR = 0.001, PBR = 30, PHR = 26;
const REPS = 3, SEED = 20260927, SLIP = 0.004, DRAIN = 0.05, MINUSD = 10, EWAIT = H, XWAIT = DAY;
const TPLAT = 60, CLIP = 50, S1 = Math.sqrt(1.01) - 1, X20 = 20, CORR_WIN = 30 * 60, DEPTH_OK_W = 0.10, V4_DEFAULT_FEE = 0.01;
const POOL_HL = 6 * H, POOL_X = 2, POOL_REF_AGE = H, REORDER = 2 * H;
const MR = 60, BR = 150, HR = 52, BS = 600, TR = 73;
const N10_EDGES = [1, 3, 10, 30, 100, 300], DEPTH_EDGES = [0.01, 0.03, 0.1, 0.3, 1];
const band = (x, e) => { let i = 0; while (i < e.length && x >= e[i]) i++; return i; };
const PONS_HOOK = '0xe5e702641ea86f4ae6cc3cdaed2b886f976be044';
const VENUE_LABEL = { doppler: 'Doppler', letscash: 'letscash', Klik: 'Klik', 'RWA Launchpad': 'RWA Launchpad' };
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const RUN = V4.days('2026-09-08', process.env.STOP_DAY || '2026-09-26');
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
const creOf = new Map(); { const cc = new Map(), rows = [];                       // creator: a person only if it made <= 50 tokens in the births file
  for (const ln of fs.readFileSync(CREF, 'utf8').split('\n')) { const a = ln.split('\t'); if (a.length < 4 || a[1] === '-') continue; rows.push(a); cc.set(a[1], (cc.get(a[1]) || 0) + 1); }
  for (const a of rows) if (cc.get(a[1]) <= 50 && padOf.has(a[0])) creOf.set(a[0], a[1]); }
const scamAt = (tok, ts) => { const s = scamF.get(tok); return s && s[1] <= ts && ts < s[2] ? s[0] : null; };
// OUTPUT (batch 2, DEVIATION D2b): synchronous gzip MEMBERS of ~8 MB (a multi-member .gz reads as one stream in zcat / python gzip). The async
// gzip stream could not drain while the main loop ran, and its backlog grew the process's external memory by ~1 GB.
const OUTFD = fs.openSync(OUT, 'w'); let OB = [], OBN = 0;
function flushOut() { if (!OB.length) return; fs.writeSync(OUTFD, zlib.gzipSync(Buffer.from(OB.join('')), { level: 1 })); OB = []; OBN = 0; }
const W_ = o => { const t = JSON.stringify(o) + '\n'; OB.push(t); OBN += t.length; if (OBN > 8e6) flushOut(); };
const gz = { end() { flushOut(); fs.closeSync(OUTFD); } };
const stats = { metaLab, v4LabAdded, rows: 0, rowsV4: 0, v4skipLiq0: 0, univRows: 0, univV4: 0, bad: 0, badV4: 0, exits: 0, trunc: 0, end: 0, holes: 0,
  holeAt: [], nofill: 0, assess: {}, cand: {}, drop: {}, eligL: {}, trig: {}, heldSkip: {}, coolSkip: {}, twinEmpty: {},
  wide0: null, creKnown: 0, creSoldSeen: 0, eligC: {}, pre: { buyers: {}, pad: {}, cre: {}, vol: {}, sd: {}, n: 0 }, rangeFail: {}, feeSrc: {}, g5: {}, v23Files: {}, v4Files: {}, reorder: { maxHeap: 0, lateRows: 0 }, mergedOutOfOrder: 0, v4OutOfOrder: 0,
  fixA: { checked: 0, unchecked: 0, dropped: 0, droppedV4: 0, droppedV23: 0 },
  fixB: { otherPoolPrintsSeen: 0, positionsWithOtherPool: 0 },
  fixC: { fired_depthok: 0, fired_corroborated: 0, blocked: 0, blockedPos: 0 }, matchLvl: {}, profCalls: 0, skipDepth: {}, twinDistinct: {}, ep: { n: 0, rec: 0 }, stockRows: 0, bandSkip: {}, sigBand: {}, twBandPool: {}, sigFail: {}, thDrop: {}, probes: { reg: 0, res: 0, endRes: 0, endNull: 0 }, cells: null,
  quoteSkip: {}, sigQuote: {}, capSkip: {}, capSkipCoinHours: {}, capLateTaken: {}, peakHeld: {} };   // H3
const pkQ = [], capSeen = new Set();                                               // H3: pool index -> quote; cap-skipped coin-hours
const inc = (o, k, v = 1) => { o[k] = (o[k] || 0) + v; };
const tfSell = new Map();                                                         // TOKF: pool key -> cumulative sell rows
function tfFeat(P, now, hv) {                                                     // TOKF: signal features from the ring (causal: rows <= now)
  const mi = Math.floor(now / 60), A = P.tf || [], h0 = P.tfH || 0; let mx = -Infinity, first = null, last = null, ties = 0;
  for (let i = h0; i < A.length; i++) { const e = A[i]; if (Math.floor(e[0] / 60) < mi - 59 || e[0] > now) continue; if (e[1] > mx) { mx = e[1]; first = e; last = e; ties = 1; } else if (e[1] === mx) { last = e; ties++; } }
  if (!first) return { hiTs: null, nSell: null, ties: 0, hiTsLast: null, nSellLast: null, hiMatch: false };
  const cur = tfSell.get(P.tfPk) || 0;
  return { hiTs: first[0], nSell: cur - first[2], ties, hiTsLast: last[0], nSellLast: cur - last[2], hiMatch: mx === hv };
}
stats.creKnown = creOf.size;
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
    hId: new Int32Array(HR).fill(-1), hLast: new Float32Array(HR), hVol: new Float64Array(HR), hMx: new Float32Array(HR), h10: new Int32Array(TR).fill(-1),
    epLast: -Infinity, epOpen: [], epRec: [], nrc: null,
    rec: [], q10: [], pc: null, mpc: null, prf: null, buys: [], creSold: false }; toks.set(r.tok, T); }
  return T;
}
function mainPool(T, ts) {
  let best = -1, bv = -1;
  for (const [pk, P] of T.pools) { const v = P.vol * Math.pow(2, -(ts - P.vts) / POOL_HL); if (v > bv) { bv = v; best = pk; } }
  return best;
}
function mainPoolC(T, ts) { const mi = Math.floor(ts / 60); if (!T.mpc || T.mpc.mi !== mi) T.mpc = { mi, v: mainPool(T, ts) }; return T.mpc.v; }
function poolHighs(P, ts) {                     // main-pool high over every window W (incl. the current print), keyed by W
  const mi = Math.floor(ts / 60), res = {}; let hv = 0, k = 0; const mins = [5, 15, 60];
  for (let a = 0; a < MR; a++) { const m = mi - a, s = m % MR; if (P.mId[s] === m && P.mMax[s] > hv) hv = P.mMax[s];
    while (k < mins.length && a + 1 === mins[k]) { res[mins[k] * 60] = hv; k++; } }
  const hi = Math.floor(ts / H), h0 = Math.floor((ts - 24 * H) / H); let dv = hv;   // 24 h: hourly maxima, the hour containing sig - 24 h included (edge to 1 h)
  for (let h = hi; h >= h0 && h > hi - PHR; h--) { const s = h % PHR; if (P.hId[s] === h && P.hMax[s] > dv) dv = P.hMax[s]; }
  res[24 * H] = dv; return res;
}
function coinHighs(T, ts) {                     // MERGED-series high (all the coin's accepted prints) over every window W, keyed by W (mode M)
  const mi = Math.floor(ts / 60), res = {}; let hv = 0, k = 0; const mins = [5, 15, 60];
  for (let a = 0; a < MR; a++) { const m = mi - a, s = m % MR; if (T.mId[s] === m && T.mMax[s] > hv) hv = T.mMax[s];
    while (k < mins.length && a + 1 === mins[k]) { res[mins[k] * 60] = hv; k++; } }
  const hi = Math.floor(ts / H), h0 = Math.floor((ts - 24 * H) / H); let dv = hv;   // 24 h: hourly maxima, edge to 1 h (as the pool version)
  for (let h = hi; h >= h0 && h > hi - HR; h--) { const s = h % HR; if (T.hId[s] === h && T.hMx[s] > dv) dv = T.hMx[s]; }
  res[24 * H] = dv; return res;
}
function poolHigh1h(P, ts) { const mi = Math.floor(ts / 60); let hv = 0; for (let a = 0; a < MR; a++) { const m = mi - a, s = m % MR; if (P.mId[s] === m && P.mMax[s] > hv) hv = P.mMax[s]; } return hv; }
function episodes(Tk, r, mp) {                 // dip-history episodes on the MAIN pool (PREREG §3); called after update() on every accepted print
  if (Tk.epOpen.length) { const keep = [];
    for (const e of Tk.epOpen) { if (r.ts - e.ts > EP_RECWIN) continue;
      if (r.pk === e.pk && r.px >= EP_REC * e.px) { Tk.epRec.push(e.ts); stats.ep.rec++; continue; } keep.push(e); }
    Tk.epOpen = keep; }
  if (r.pk !== mp || r.ts < Tk.epLast + EP_GAP) return;
  const hv = poolHigh1h(Tk.pools.get(r.pk), r.ts);
  if (hv > 0 && 1 - r.px / hv >= EP_DIP) { Tk.epLast = r.ts; Tk.epOpen.push({ ts: r.ts, px: r.px, pk: r.pk }); stats.ep.n++; }
  while (Tk.epRec.length && Tk.epRec[0] < r.ts - EP_LOOK - DAY) Tk.epRec.shift();
}
function nrec7(Tk, now) {                      // recovered episodes that STARTED in [now - 7 d, now) (recovery already seen: no look-ahead)
  if (Tk.nrc && Tk.nrc.ts === now) return Tk.nrc.v;
  let n = 0; for (const t of Tk.epRec) if (t >= now - EP_LOOK && t < now) n++;
  Tk.nrc = { ts: now, v: n }; return n;
}
function sigOk(Tk, c, now) {                   // filters tested AT THE SIGNAL (strategy and twins alike): range, dip history
  if (c.range && !rangeOk(Tk, c, now)) return false;
  if (c.dh && nrec7(Tk, now) < c.dh) return false;
  return true;
}
function buyersOf(Tk, now) { const s = new Set(); for (const [t, id] of Tk.buys) if (t > now - H && t <= now) s.add(id); return s.size; }
function coinStats(T, t0) {                    // (engine_bes verbatim) 24 h volume and sd of hourly log returns over the prior 48 h
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
function rangeOk(Tk, c, now) {                 // 24 h change of the coin's price ending at the window start: p(sig - W) / p(sig - W - 24 h) - 1
  const pw = pCached(Tk, c.W, now), p0 = pCached(Tk, c.W + 24 * H, now); if (!(pw > 0) || !(p0 > 0)) return false;
  const chg = pw / p0 - 1; return c.range === 'up' ? chg >= -0.09 : chg <= -0.30;
}
function update(T, r) {
  const ts = r.ts, mi = Math.floor(ts / 60), ms = mi % MR, bi = Math.floor(ts / BS), bs = bi % BR, hi = Math.floor(ts / H), hs = hi % HR;
  T.last = ts; T.lastR = r; if (r.kind === 'v4') T.hasV4 = true; else T.hasV23 = true;
  if (T.mId[ms] !== mi) { T.mId[ms] = mi; T.mMax[ms] = 0; }
  if (r.px > T.mMax[ms]) { T.mMax[ms] = r.px; T.mPk[ms] = r.pk; } T.mLast[ms] = r.px;
  if (T.bId[bs] !== bi) { T.bId[bs] = bi; T.bMax[bs] = 0; }
  if (r.px > T.bMax[bs]) { T.bMax[bs] = r.px; T.bPk[bs] = r.pk; } T.bLast[bs] = r.px;
  if (T.hId[hs] !== hi) { T.hId[hs] = hi; T.hVol[hs] = 0; T.hMx[hs] = 0; }
  if (r.px > T.hMx[hs]) T.hMx[hs] = r.px;
  T.hLast[hs] = r.px; T.hVol[hs] += r.usd || 0;
  if (r.usd >= MINUSD) T.h10[hi % TR] = hi;                                            // trading-history hour (>= $10 accepted print)
  const pad = padOf.get(r.tok); let PV = padVol.get(pad); if (!PV) { PV = { id: new Int32Array(HR).fill(-1), v: new Float64Array(HR) }; padVol.set(pad, PV); }
  if (PV.id[hs] !== hi) { PV.id[hs] = hi; PV.v[hs] = 0; } PV.v[hs] += r.usd || 0;
  let P = T.pools.get(r.pk);
  if (!P) { P = { vol: 0, vts: ts, lastPx: 0, lastTs: 0, lastR: null, mId: new Int32Array(MR).fill(-1), mMax: new Float32Array(MR), bId: new Int32Array(PBR).fill(-1), bMax: new Float32Array(PBR), rs: [], lastSell10: -1, lastSell1: -1, hId: new Int32Array(PHR).fill(-1), hMax: new Float32Array(PHR) }; T.pools.set(r.pk, P); }
  { if (!P.tf) { P.tf = []; P.tfH = 0; P.tfPk = r.pk; } P.tf.push([ts, Math.fround(r.px), tfSell.get(r.pk) || 0]);   // TOKF: accepted-print ring
    while (P.tfH < P.tf.length && Math.floor(P.tf[P.tfH][0] / 60) < mi - 60) P.tfH++; if (P.tfH > 64 && P.tfH > P.tf.length / 2) { P.tf = P.tf.slice(P.tfH); P.tfH = 0; } }
  P.vol = P.vol * Math.pow(2, -(ts - P.vts) / POOL_HL) + (r.usd || 0); P.vts = ts; P.lastPx = r.px; P.lastTs = ts; P.lastR = r;
  if (P.mId[ms] !== mi) { P.mId[ms] = mi; P.mMax[ms] = 0; } if (r.px > P.mMax[ms]) P.mMax[ms] = r.px;
  { const pbs = bi % PBR; if (P.bId[pbs] !== bi) { P.bId[pbs] = bi; P.bMax[pbs] = 0; } if (r.px > P.bMax[pbs]) P.bMax[pbs] = r.px; }
  { const phs = hi % PHR; if (P.hId[phs] !== hi) { P.hId[phs] = hi; P.hMax[phs] = 0; } if (r.px > P.hMax[phs]) P.hMax[phs] = r.px; }
  if (r.side === 'buy' && r.usd >= MINUSD) { T.buys.push([ts, r.kind === 'v4' || !r.w ? 'tx:' + r.tx : r.w]); while (T.buys.length && T.buys[0][0] <= ts - H) T.buys.shift(); if (T.buys.length > 3000) T.buys.shift(); }
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
  if (!T.pc || T.pc.mi !== mi) T.pc = { mi, v: new Map() };
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
function exAnteTake(pk) {   // LOWFEE: verbatim engine_pf.js (the per-side take a bot can know BEFORE buying, for the pool pk)
  if (pk == null || pk < 0) return { band: 'UNK', take: null, ty: 'no_main_pool' };
  const nm = pkName[pk]; if (!nm.startsWith('v4:')) return { band: 'V23', take: null, ty: 'v23' };
  const pool = nm.slice(3), bd = t => (t <= 0.01 + 1e-9 ? 'LOW' : 'HIGH');
  if (poolPons.has(pool)) { const t = ponsTake.get(pool); return t == null ? { band: 'UNK', take: null, ty: 'pons_noterms' } : { band: bd(t), take: t, ty: 'pons' }; }
  if (!poolFee.has(pool)) return { band: 'UNK', take: null, ty: 'no_pool_key' };
  const f = poolFee.get(pool); if (f != null) return { band: bd(f), take: f, ty: 'fee_key' };
  const e = poolEst.get(pool); if (e && e.est.length) { const s = e.est.slice().sort((a, b) => a - b); const m = s[s.length >> 1]; return { band: bd(m), take: m, ty: 'dyn_prior_swaps' }; }
  return { band: 'UNK', take: null, ty: 'dyn_no_estimate' };
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
const watch = new Map(); const eligAt = new Map(CELLS.map(c => [c.id, []]));
function evtOf(p) { return p.st === 'E' ? p.sigTs + p.lat : p.st === 'EW' ? p.eWait : p.st === 'O' ? p.deadline : p.st === 'X' ? p.due : p.xWait; }
function release(p, exitTs) { if (p.kind === 'S') { held.get(p.cell).delete(p.tok); if (exitTs != null) cool.get(p.cell).set(p.tok, exitTs); } }
function base(p) { return { u: p.uid, mode: p.mode, kind: p.kind, tw: p.tw || null, cell: p.cell, dip: p.dipLv, W: p.W, L: p.L, pair: p.pair, rep: p.rep, tok: p.tok, pad: padOf.get(p.tok),
  lat: p.lat, tp: p.tp, hold: p.hold, T: p.T, sigTs: p.sigTs, sigK: p.sigK, dipPct: p.dipPct, src: p.srcCls, eligN: p.eligN, nA: p.nA, mlA: p.mlA, n10: p.n10, dband: p.dband,
  hot: p.hot, sigHot: p.sigHot, h72: p.h72, ...(p.tf ? { tf: p.tf } : {}) }; }   // TOKF: tf on strategy rows only
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
      g5: g.g5, g5px: g.px, sellPx: s.px, on, reason: why, eBand: p.eBand, eTake: p.eTake, eTy: p.eTy, eStock: p.eStock, xStock: r.kind === 'v4' && STOCKPONS.has(r.pool) ? 1 : 0, eQ: p.eQ,   // LOWFEE, H3 eQ
      nPostSell: p.nPostSell, otherPool: p.otherPool, drainBlocked: p.drainBlocked, ...(p.tb ? { tb: p.tb } : {}), ...extra });
  if (p.otherPool > 0) stats.fixB.positionsWithOtherPool++;
  if (p.drainBlocked > 0) stats.fixC.blockedPos++;
  stats.exits++; release(p, ts); p.st = 'done';
}
function tbOf(p, r) { const g = g5price(p, r, r.ts); const s = sellAt(p, r, g.px); return { ts: r.ts, xP: r.px, xS: r.side, xU: r.usd, xK: r.kind, xPk: pkName[r.pk], xw: s.w, xf: s.f, g5: g.g5, g5px: g.px, sellPx: s.px }; }   // REALCOST PATCH: the sale the trigger print itself would give
function sellFlags(Tk, pk, ts) {
  const P = Tk.pools.get(pk); if (!P) return null;
  let ns = 0, nb = 0; const sp = [], bp = [];
  for (const [t, s, px] of P.rs) if (t > ts - H && t <= ts) { if (s) { ns++; sp.push(px); } else { nb++; bp.push(px); } }
  const med = a => { const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };
  return { s10h: P.lastSell10 > ts - H ? 1 : 0, ns, sbr: sp.length && bp.length ? med(sp) / med(bp) : null };
}
function fill(p, r, delay) {
  if (r.kind === 'v4' && r.depth1_eth < DEPTH_FLOOR) {                           // pre-registered depth floor: skip, no cooldown
    W_({ ...base(p), skipDepth: 1, eDepth1: r.depth1_eth, entryTs: r.ts }); inc(stats.skipDepth, `${p.kind}${p.tw || ''}`); release(p, null); p.st = 'done'; return;
  }
  p.st = 'O'; p.entryTs = r.ts > p.sigTs + p.lat ? r.ts : p.sigTs + p.lat; p.eDelay = delay; p.eP = r.px; p.eU = r.usd; p.eK = r.kind; p.ePk = r.pk;
  const b = buyCost(p.tok, r, p.clip); p.entryPx = b.px; p.eu = b.u; p.ef = b.f; p.ePons = r.kind === 'v4' && poolPons.has(r.pool) ? 1 : 0;
  p.eDepth1 = r.kind === 'v4' ? r.depth1_eth : null;
  { const x = exAnteTake(r.pk); p.eBand = x.band; p.eTake = x.take; p.eTy = x.ty; p.eStock = r.kind === 'v4' && STOCKPONS.has(r.pool) ? 1 : 0; }   // LOWFEE
  p.eQ = r.quote;                                                                   // H3
  p.deadline = p.entryTs + p.hold; p.line = p.entryPx * p.tp; p.nPostSell = 0; p.lastOk = r.px; p.last = r;
  p.otherPool = 0; p.drainBlocked = 0;
  p.sell = sellFlags(toks.get(p.tok), r.pk, Math.max(r.ts, p.entryTs));
}
function planExit(p, plan, why) {
  p.trig = why; if (why === 'time') exitProbes(p, plan);
  if (priceable(p.last)) { book(p, p.last, plan, why); return true; }
  p.st = 'XW'; p.xWait = plan + XWAIT; return false;
}
function clockTo(p, now) {
  if (p.st === 'E' && now > p.sigTs + p.lat) {
    if (p.last && priceable(p.last)) { fill(p, p.last, 0); if (p.st === 'done') return true; } else { p.st = 'EW'; p.eWait = p.sigTs + p.lat + EWAIT; }
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
    if (priceable(r)) { fill(p, r, r.ts - (p.sigTs + p.lat)); if (p.st === 'done') return true; } else p.last = r; return false;
  }
  if (r.pk !== p.ePk) { p.otherPool++; stats.fixB.otherPoolPrintsSeen++; return false; }        // FIX b: exits on the entry pool only
  if (r.side === 'sell') p.nPostSell++;
  if (r.usd >= MINUSD && r.px <= X20 * p.eP) p.lastOk = r.px;
  if (r.px < DRAIN * p.eP) {
    const dt = drainTest(p, r);
    if (dt) { stats.fixC['fired_' + dt]++; exitProbes(p, r.ts); book(p, r, r.ts, 'drain', { drainTest: dt }); return true; }
    p.drainBlocked++; stats.fixC.blocked++;
  }
  if (p.st === 'XW' && priceable(r)) { book(p, r, r.ts, p.trig); return true; }
  if (p.st === 'O' && ((r.kind !== 'v4' && r.usd >= MINUSD && r.px >= p.line) || (r.kind === 'v4' && r.px / (1 + wOf(p, r)) >= p.line))) { p.st = 'X'; p.due = r.ts + TPLAT; p.tb = tbOf(p, r); exitProbes(p, r.ts); }
  p.last = r; return false;
}
// PERF (batch 2, results-neutral): due positions come from a min-heap of event times instead of scanning every open position on every
// sweep (with 262 cells the open set is ~10x batch 1's). A position whose event is not due was a no-op in the old scan.
const EH = [];                                                                   // [evt, p]
function ehPush(x) { const a = EH; a.push(x); let i = a.length - 1; while (i > 0) { const j = (i - 1) >> 1; if (a[i][0] < a[j][0]) { [a[i], a[j]] = [a[j], a[i]]; i = j; } else break; } }
function ehPop() { const a = EH, t = a[0], x = a.pop(); if (a.length) { a[0] = x; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
  if (l < a.length && a[l][0] < a[m][0]) m = l; if (r < a.length && a[r][0] < a[m][0]) m = r; if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m; } } return t; }
function hpush(p) { if (p.st === 'done') return; const e = evtOf(p); if (e === p.hev) return; p.hev = e; ehPush([e, p]); if (e < nextEvt) nextEvt = e; }
function dropOpen(p) { const ps = open.get(p.tok); if (!ps) return; const k = ps.indexOf(p); if (k >= 0) ps.splice(k, 1); if (!ps.length) open.delete(p.tok); }
function sweep() {
  const now = globalLast, due = [];
  while (EH.length && EH[0][0] <= now) { const [e, p] = ehPop(); if (p.st === 'done' || e !== p.hev) continue; due.push(p); }
  for (const p of due) { if (p.st === 'done') { dropOpen(p); continue; }
    clockTo(p, now); if (p.st === 'done') { dropOpen(p); continue; } p.hev = NaN; hpush(p); }
  nextEvt = EH.length ? EH[0][0] : Infinity;
}
let uidc = 0;
function addPos(p) { p.uid = ++uidc; entryProbes(p); (open.get(p.tok) || open.set(p.tok, []).get(p.tok)).push(p); hpush(p); }
function onHole() {
  for (const [, ps] of open) for (const p of ps) { if (p.st === 'done') continue; W_({ ...base(p), trunc: 'hole', at: globalLast, st: p.st }); stats.trunc++; release(p, null); }
  open.clear(); EH.length = 0; watch.clear(); for (const k of eligAt.keys()) eligAt.set(k, []); stats.holes++; stats.holeAt.push(globalLast); nextEvt = Infinity;
}
const srcCls = Tk => Tk.hasV4 && Tk.hasV23 ? 'both' : Tk.hasV4 ? 'v4' : 'v23';
// MEMORY (batch 2, DEVIATION D2, results-neutral): drop entries no future query can read. Every reader looks back from a moment >= T:
// q10 / buys / rs within 1 h, rec within 30 min; the caches are keyed by an exact earlier time. rs keeps its 80-entry cap (the newest 80 are
// the same whether or not older ones were dropped).
function prune(Tk, T) {                        // margin 6 h (= HOLE): a fill or exit can be evaluated at a moment slightly before the stream clock
  const t0 = T - HOLE;
  while (Tk.q10.length && Tk.q10[0] <= t0 - H) Tk.q10.shift();
  while (Tk.buys.length && Tk.buys[0][0] <= t0 - H) Tk.buys.shift();
  while (Tk.rec.length && Tk.rec[0].ts <= t0 - CORR_WIN) Tk.rec.shift();
  for (const P of Tk.pools.values()) { let k = 0; while (k < P.rs.length && P.rs[k][0] <= t0 - H) k++; if (k) P.rs.splice(0, k); }
  if (Tk.last < t0) { Tk.prf = null; Tk.pc = null; Tk.mpc = null; Tk.nrc = null; }
}
function assess(T) {
  watch.clear(); for (const k of eligAt.keys()) eligAt.set(k, []);
  if (T > LAST) return;
  const half = halfOf(T); inc(stats.assess, half);
  for (const [tok, Tk] of toks) {
    prune(Tk, T);
    if (Tk.last < T - H || !Tk.lastR) continue;
    const sc = srcCls(Tk); const b = birth.get(tok), age = T - (b != null ? b : Tk.first);
    inc(stats.cand, `${half}|${sc}`);
    if (age < H) { inc(stats.drop, `${half}|age<1h`); continue; }
    if (scamAt(tok, T)) { inc(stats.drop, `${half}|scam`); continue; }
    const meas24 = (T - 24 * H >= Tk.cov) || (b != null && b >= Tk.cov), meas49 = (T - 49 * H >= Tk.cov) || (b != null && b >= Tk.cov);
    const pad = padOf.get(tok), cre = creOf.get(tok);
    let cs = null, nb = null; const CS = () => cs || (cs = coinStats(Tk, T)), NB = () => nb != null ? nb : (nb = buyersOf(Tk, T));
    let h72 = null; const TH = () => h72 != null ? h72 : (h72 = ((T - 72 * H >= Tk.cov) || (b != null && b >= Tk.cov)) ? hours72(Tk, T) : -1);   // -1 = unmeasurable (the grid's rule)
    Tk.sc = sc; Tk.h72 = null;
    if (PREPASS && half === 'FIT' && age >= BASE.age) {                  // distributions over HELD-eligible coin-hours (no outcomes)
      const P = stats.pre; P.n++; inc(P.buyers, String(Math.min(NB(), 200))); inc(P.pad, pad); inc(P.cre, !cre ? 'unknown' : Tk.creSold ? 'sold' : 'notsold');
      inc(P.vol, !meas24 ? 'unmeas' : CS().vol >= 1e5 ? '>=100k' : cs.vol >= 1e4 ? '10k-100k' : '<10k');
      inc(P.sd, !meas49 ? 'unmeas' : CS().sd == null ? 'nret<24' : cs.sd >= 0.05 ? '>=5%' : cs.sd >= 0.03 ? '3-5%' : '<3%');
      continue;
    }
    const pend = new Set();
    for (const c of CELLS) {
      if (T > c.last || age < c.age) continue;
      if (c.padMode === 'L' && pad !== LARGEST) continue;
      if (c.padMode === 'X' && pad === LARGEST) continue;
      if (c.volMin && (!meas24 || CS().vol < c.volMin)) continue;
      if (c.sdMin && (!meas49 || CS().sd == null || cs.sd < c.sdMin)) continue;
      if (c.buyMin && NB() < c.buyMin) continue;
      if (c.creator && (!cre || (c.creator === 'notsold' && Tk.creSold))) continue;
      if (c.th && TH() < c.th) { inc(stats.thDrop, `${half}|${c.id}|${h72 < 0 ? 'unmeas' : 'h72'}`); continue; }
      inc(stats.eligC, `${half}|${c.id}|${sc}`); eligAt.get(c.id).push(tok); pend.add(c.id);
    }
    if (pend.size) watch.set(tok, { T, pend });
  }
}
function profile(Tt, now) {                    // activity-twin matching variables at the signal moment (cached per exact timestamp)
  if (Tt.prf && Tt.prf.ts === now) return Tt.prf.v;
  stats.profCalls++;
  const mp = mainPoolC(Tt, now), P = mp >= 0 ? Tt.pools.get(mp) : null;
  const lr = P ? P.lastR : null;
  const dband = !lr ? -2 : lr.kind === 'v4' ? band(lr.depth1_eth, DEPTH_EDGES) : -1;
  const hs = P ? poolHighs(P, now) : null, dd = {};
  for (const W of WINDOWS) { const hv = hs ? hs[W] : 0; dd[W] = hv > 0 && P.lastPx > 0 ? 1 - P.lastPx / hv : null; }
  const nn = n10(Tt, now);
  const v = { n10: nn, nb: band(nn, N10_EDGES), dband, kindV4: lr && lr.kind === 'v4' ? 1 : 0, dd, mp };
  Tt.prf = { ts: now, v }; return v;
}
const CELLS_BY_ID = new Map(CELLS.map(c => [c.id, c]));
const GROUPS = []; { const g = new Map();                                          // cells grouped by (dip series, window), sorted by dip depth
  for (const c of CELLS) { const k = c.mode + '|' + c.W; if (!g.has(k)) g.set(k, { mode: c.mode, W: c.W, cells: [] }); g.get(k).cells.push(c); }
  for (const x of g.values()) { x.cells.sort((a, b) => a.dip - b.dip); GROUPS.push(x); } }
// ---- latency probes: the pool (or, in mode M, the coin) state = its last accepted print at or before t ----
const probesPool = new Map(), probesCoin = new Map();
function probe(map, key, t, u, k) { let a = map.get(key); if (!a) map.set(key, a = { mn: Infinity, a: [] }); a.a.push([t, u, k]); if (t < a.mn) a.mn = t; stats.probes.reg++; }
function resolveProbes(map, key, now, lastR, atEnd) {
  const A = map.get(key); if (!A) return;
  if (!atEnd && !(A.mn < now)) return;
  const keep = []; let mn = Infinity;
  for (const x of A.a) {
    if (!atEnd && !(x[0] < now)) { keep.push(x); if (x[0] < mn) mn = x[0]; continue; }
    if (lastR) W_({ pr: [x[1], x[2], x[0], lastR.ts, lastR.px, lastR.kind === 'v4' ? lastR.price_eth : null, pkName[lastR.pk], lastR.kind] });
    else { W_({ pr: [x[1], x[2], x[0], null] }); stats.probes.endNull++; }
    stats.probes[atEnd ? 'endRes' : 'res']++;
  }
  if (keep.length) { A.a = keep; A.mn = mn; } else map.delete(key);
}
function entryProbes(p) {                       // realistic entry moment: a delay <= 60 s is a latency assumption -> replaced by our bot's
  const e = p.sigTs + (p.lat <= 60 ? LAT_B : p.lat), e90 = p.sigTs + (p.lat <= 60 ? LAT_B90 : p.lat);   // measured latency; a longer delay is a deliberate wait
  if (p.tgt == null) { probe(probesCoin, p.tok, e, p.uid, 'e'); probe(probesCoin, p.tok, e90, p.uid, 'e90'); }
  else { const k = p.tok + '|' + p.tgt; probe(probesPool, k, e, p.uid, 'e'); probe(probesPool, k, e90, p.uid, 'e90'); }   // V2/V3 pool keys (kind:quote) are per COIN
}
function exitProbes(p, t0) { const k = p.tok + '|' + p.ePk; probe(probesPool, k, t0 + LAT_S, p.uid, 'x'); probe(probesPool, k, t0 + LAT_S90, p.uid, 'x90'); }
function onWatchedPrint(tok, r, w, mp) {
  const Tk = toks.get(tok), half = halfOf(w.T);
  let hsP = null, hsM = null, sp = null, sH = null, sb = null;   // LOWFEE: sb
  for (const G of GROUPS) {
    let hv;
    if (G.mode === 'P') { if (r.pk !== mp) continue;                              // mode P: the dip must print on the MAIN pool, its own high
      if (!hsP) hsP = poolHighs(Tk.pools.get(r.pk), r.ts); hv = hsP[G.W]; }
    else { if (!hsM) hsM = coinHighs(Tk, r.ts); hv = hsM[G.W]; }                  // mode M: merged high of all pools, the dip print on any pool
    if (!(hv > 0)) continue;
    const dd = 1 - r.px / hv;
    for (const c of G.cells) {
      if (c.dip > dd) break;
      if (!w.pend.has(c.id)) continue;
      if (held.get(c.id).has(tok)) { inc(stats.heldSkip, c.id); continue; }
      const lc = cool.get(c.id).get(tok); if (lc != null && r.ts < lc + c.cool) { inc(stats.coolSkip, c.id); continue; }
      if (!sigOk(Tk, c, r.ts)) { inc(stats.sigFail, `${half}|${c.id}`); continue; }   // range / dip history at the signal; the cell stays pending
      if (!sb) sb = exAnteTake(r.pk);                                              // LOWFEE: the signal (= main = entry) pool's ex-ante band
      if (c.band && sb.band !== c.band) { inc(stats.bandSkip, `${half}|${c.id}|${sb.band}|${sb.ty}`); continue; }   // LOWFEE: the cell stays pending (engine_pf)
      if (c.quote && r.quote !== c.quote) { inc(stats.quoteSkip, `${half}|${c.id}|${/^(WETH|USDG)$/.test(r.quote) ? r.quote : STOCKPONS.has(pkName[r.pk].slice(3)) ? 'stock' : 'other'}`); continue; }   // H3: stays pending
      const chk = c.id + '|' + tok + '|' + w.T;                                     // H3: capital cap
      if (c.cap && held.get(c.id).size >= c.cap) { inc(stats.capSkip, `${half}|${c.id}`); if (!capSeen.has(chk)) { capSeen.add(chk); inc(stats.capSkipCoinHours, `${half}|${c.id}`); } continue; }
      if (c.cap && capSeen.has(chk)) inc(stats.capLateTaken, `${half}|${c.id}`);
      inc(stats.sigQuote, `${half}|${c.id}|${/^(WETH|USDG)$/.test(r.quote) ? r.quote : STOCKPONS.has(pkName[r.pk].slice(3)) ? 'stock' : 'other'}`);   // H3
      w.pend.delete(c.id); inc(stats.trig, `${half}|${c.id}`); inc(stats.sigBand, `${half}|${sb.band}|${sb.ty}|${STOCKPONS.has(pkName[r.pk].slice(3)) ? 'stock' : 'nonstock'}`);
      const cand0 = eligAt.get(c.id).filter(t => { if (held.get(c.id).has(t)) return false; const l2 = cool.get(c.id).get(t); if (l2 != null && r.ts < l2 + c.cool) return false;
        return !(c.range || c.dh) || sigOk(toks.get(t), c, r.ts); });
      const cand = c.quote ? cand0.filter(t => { const mp2 = profile(toks.get(t), r.ts).mp; return (!c.band || exAnteTake(mp2).band === c.band) && mp2 >= 0 && pkQ[mp2] === c.quote; })   // H3
        : !c.band ? cand0 : cand0.filter(t => exAnteTake(profile(toks.get(t), r.ts).mp).band === c.band);   // LOWFEE: twins from the SAME band
      inc(stats.twBandPool, `${half}|${c.id}|n`); inc(stats.twBandPool, `${half}|${c.id}|cand0`, cand0.length); inc(stats.twBandPool, `${half}|${c.id}|cand`, cand.length);
      held.get(c.id).add(tok);
      if (held.get(c.id).size > (stats.peakHeld[c.id] || 0)) stats.peakHeld[c.id] = held.get(c.id).size;   // H3
      if (!sp) { sp = profile(Tk, r.ts); sH = hotOf(Tk.hId, Tk.hVol, r.ts); }
      const noDip = q => q.dd[c.W] != null && q.dd[c.W] < c.dip / 2;
      const others = cand.filter(t => t !== tok);
      let poolA = others.filter(t => { const q = profile(toks.get(t), r.ts); return q.nb === sp.nb && q.dband === sp.dband && noDip(q); }), mlA = 1;
      if (!poolA.length) { poolA = others.filter(t => { const q = profile(toks.get(t), r.ts); return q.nb === sp.nb && q.kindV4 === sp.kindV4 && noDip(q); }); mlA = poolA.length ? 2 : 0; }
      inc(stats.matchLvl, `${half}|${c.id}|A${mlA}`);
      const id2 = ++pid, com = { cell: c.id, mode: c.mode, dipLv: c.dip * 100, W: c.W, L: c.L, lat: c.lat, hold: c.hold, tp: c.tp, clip: CLIP, pair: id2, T: w.T, st: 'E', sigTs: r.ts, sigK: r.kind,
        dipPct: 100 * dd, eligN: cand.length, nA: poolA.length, mlA, sigHot: sH.hot };
      const tf = c.mode === 'P' && c.W === 3600 ? tfFeat(Tk.pools.get(r.pk), r.ts, hv) : null;   // TOKF
      addPos({ ...com, kind: 'S', tf, rep: null, tok, last: r, tgt: c.mode === 'P' ? r.pk : null, srcCls: Tk.sc, n10: sp.n10, dband: sp.dband, hot: sH.hot, h72: null });
      const mk = (t, tw, k) => { const Tt = toks.get(t), q = profile(Tt, r.ts);
        const tgt = c.mode === 'P' ? q.mp : null, last = c.mode === 'P' ? (q.mp >= 0 ? Tt.pools.get(q.mp).lastR : null) : Tt.lastR;
        addPos({ ...com, kind: 'W', tw, rep: k, tok: t, last, tgt, srcCls: Tt.sc, n10: q.n10, dband: q.dband,
          hot: hotOf(Tt.hId, Tt.hVol, r.ts).hot, h72: null }); };
      const draw = (pool, tw) => {                                                 // WITHOUT replacement: min(3, |pool|) distinct coins, the CELL's own RNG
        if (!pool.length) { inc(stats.twinEmpty, `${c.id}|${tw}`); return; }
        const a = pool.slice(), m = Math.min(REPS, a.length);
        for (let k = 0; k < m; k++) { const j = k + Math.floor(c.rng() * (a.length - k)); const t = a[j]; a[j] = a[k]; a[k] = t; mk(t, tw, k); }
        inc(stats.twinDistinct, `${halfOf(w.T)}|${c.id}|${tw}${m}`);
      };
      draw(cand, 'R'); draw(poolA, 'A');
    }
  }
}
function onRow(r) {
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
  if (r.kind !== 'v4' && r.side === 'sell' && r.w && !Tk.creSold) { const cr = creOf.get(r.tok); if (cr && r.w.toLowerCase() === cr) { Tk.creSold = true; stats.creSoldSeen++; } }
  r.pk = pkOf(poolKey(r)); pkQ[r.pk] = r.quote;                                   // H3
  if (r.side === 'sell') tfSell.set(r.pk, (tfSell.get(r.pk) || 0) + 1);                 // TOKF: every row onRow receives, any size
  const mp = mainPool(Tk, r.ts);                                                  // FIX a
  if (mp >= 0 && mp !== r.pk) {
    const M = Tk.pools.get(mp);
    if (M.lastTs >= r.ts - POOL_REF_AGE && M.lastPx > 0) {
      stats.fixA.checked++; const ratio = r.px / M.lastPx;
      if (ratio > POOL_X || ratio < 1 / POOL_X) { stats.fixA.dropped++; if (r.kind === 'v4') stats.fixA.droppedV4++; else stats.fixA.droppedV23++; return; }
    } else stats.fixA.unchecked++;
  }
  if (!accept(Tk, r)) { stats.bad++; if (r.kind === 'v4') stats.badV4++; return; }
  { const P0 = Tk.pools.get(r.pk), pkk = r.tok + '|' + r.pk; if (P0 && probesPool.has(pkk)) resolveProbes(probesPool, pkk, r.ts, P0.lastR, false);   // state BEFORE this print
    if (probesCoin.has(r.tok)) resolveProbes(probesCoin, r.tok, r.ts, Tk.lastR, false); }
  update(Tk, r);
  const ps = open.get(r.tok);
  if (ps) { for (let k = ps.length - 1; k >= 0; k--) { if (ps[k].st === 'done' || onPrint(ps[k], r)) ps.splice(k, 1); else hpush(ps[k]); } if (!ps.length) open.delete(r.tok); }
  const w = watch.get(r.tok);
  if (w && r.ts - w.T >= H) watch.delete(r.tok);
  else if (w && w.pend.size) onWatchedPrint(r.tok, r, w, mp);
  episodes(Tk, r, mp);
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
      if (STOCKPONS.has(r.pool)) stats.stockRows++;                                // LOWFEE: IN the universe (Chef TG 14681), counted
      if (r.src === 'wide' && WIDE0 == null) { WIDE0 = r.ts; stats.wide0 = r.ts; }
      if (r.liquidity === '0' || !(r.depth1_eth > 0) || !(r.price_eth > 0)) { stats.v4skipLiq0++; continue; }
      if (r.quote === 'ETH') r.quote = 'WETH';
    }
    if (r.ts < lastTs) stats.mergedOutOfOrder++; lastTs = r.ts;
    stats.rows++; onRow(r);
    if (stats.rows % 1000000 === 0) { const rss = process.memoryUsage().rss; if (rss > peak) peak = rss; if (rss > 3.2e9) throw new Error('RSS guard ' + rss); }   // LOWFEE: 3.2 GB (skeleton 2's; fixed from the smoke)
    const dd = new Date(r.ts * 1000).toISOString().slice(0, 10);
    if (dd !== day) { if (day) console.log(`${day} rows ${stats.rows} v4 ${stats.rowsV4} toks ${toks.size} exits ${stats.exits} open ${[...open.values()].reduce((a, b) => a + b.length, 0)} prof ${stats.profCalls} ${((Date.now() - t0) / 1000).toFixed(0)}s rss ${(process.memoryUsage().rss / 1e6).toFixed(0)}MB heap ${(process.memoryUsage().heapUsed / 1e6).toFixed(0)} ext ${(process.memoryUsage().external / 1e6).toFixed(0)}`); day = dd; }
  }
  sweep();
  for (const [, ps] of open) for (const p of ps) {
    if (p.st === 'done' || clockTo(p, globalLast) || p.st === 'done') continue;
    if (p.st === 'E' || p.st === 'EW') { W_({ ...base(p), trunc: 'end', st: p.st }); stats.trunc++; continue; }
    book(p, p.last, globalLast, 'end', { fb: 2 }); stats.end++;
  }
  for (const [tok, Tk] of toks) { for (const [pk, P] of Tk.pools) if (probesPool.has(tok + '|' + pk)) resolveProbes(probesPool, tok + '|' + pk, Infinity, P.lastR, true);
    if (probesCoin.has(tok)) resolveProbes(probesCoin, tok, Infinity, Tk.lastR, true); }
  for (const k of [...probesPool.keys()]) resolveProbes(probesPool, k, Infinity, null, true);
  for (const k of [...probesCoin.keys()]) resolveProbes(probesCoin, k, Infinity, null, true);
  stats.cells = CELLS.map(c => c.id);
  W_({ _meta: { engine: 'v1', ...stats, pools: pkName.length, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 } });
  gz.end(); console.log(JSON.stringify({ engine: 'v1', ...stats, v23Files: undefined, v4Files: undefined, endTs: globalLast, sec: (Date.now() - t0) / 1000, peakRssMB: peak / 1e6 }));
})();
