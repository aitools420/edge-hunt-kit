#!/usr/bin/env node
// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
// finalize.js — pass 2. For each UTC day IN ORDER: GNU sort the day shard by (blk, li), dropping duplicate logs (the locked
// tape, the hole/backfill tapes and the wide files overlap), then normalise every swap and write out/v4-swaps-DAY.ndjson.gz.
// Days >= 2026-09-27T00:00Z (the SEALED final-exam holdout) go to out/sealed/ with sealed:true and never touch the
// unsealed per-pool death records. Causal only: a non-ETH/USDG quote is converted with that quote's LAST KNOWN price
// (from its own most-liquid ETH/WETH/USDG pool, updated within 24 h), never a later one.
// Usage: node finalize.js <shardDir>
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib'), { spawn } = require('child_process');
const HERE = '/home/green/projects/patches/sealed-exam-blockA/work/v4join', SH = process.argv[2], OUT = path.join(HERE, 'out'), SEALED_DIR = path.join(OUT, 'sealed');
const SEAL = 1791331200;                                 // sealed-exam-blockA: the Block A exam's CUT 2026-10-07T00:00:00Z — nothing at or after it exists here
const DEAD_SILENT_H = 24, DRAIN_FRAC = 0.01, Q_STALE = 24 * 3600;
fs.mkdirSync(SEALED_DIR, { recursive: true });
const { load, E0 } = require('./pools.js');
const P = load();
{ // keep only pools that actually have a swap (113,877 of ~663k) — the rest is dead weight in RAM
  const keep = new Set(fs.readFileSync(path.join(SH, '..', 'poolcounts.tsv'), 'utf8').split('\n').map(l => l.split('\t')[0]));
  for (const id of [...P.keys()]) if (!keep.has(id)) P.delete(id);
  for (const [id, p] of P) p.id = id;       // canonical id string: a key sliced from a sort chunk would pin the whole 64 KB chunk in RAM
}
const D = JSON.parse(fs.readFileSync(path.join(HERE, 'decimals.json'), 'utf8'));
const DEC = D.dec, SYM = D.sym;
// ETH/USD: CoinGecko hourly (independent of the chain), linear interpolation
const EU = JSON.parse(fs.readFileSync(path.join(HERE, 'ethusd_coingecko.json'), 'utf8')).prices.map(([t, p]) => [t / 1000, p]);
function ethUsd(ts) {
  let lo = 0, hi = EU.length - 1;
  if (ts <= EU[0][0]) return EU[0][1]; if (ts >= EU[hi][0]) return EU[hi][1];
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (EU[m][0] <= ts) lo = m; else hi = m; }
  return EU[lo][1] + (ts - EU[lo][0]) * (EU[hi][1] - EU[lo][1]) / (EU[hi][0] - EU[lo][0]);
}
const SRC = { lock: 'lock', hole: 'hole', bf: 'bf', wide: 'wide' };
const Q96 = 2 ** 96, S1 = Math.sqrt(1.01) - 1, S5 = Math.sqrt(1.05) - 1;
const OTHERQ = new Set(); for (const p of P.values()) if (p.q === 'other') OTHERQ.add(p.quote);
const QS = new Map();                                   // other-quote addr -> Map(pool -> {px, ts, dep})
function qPrice(q, ts) {
  const m = QS.get(q); if (!m) return null;
  let best = null;
  for (const v of m.values()) if (ts - v.ts <= Q_STALE && (!best || v.dep > best.dep)) best = v;
  return best ? best.px : null;
}
const r6 = x => x == null || !isFinite(x) ? null : +x.toPrecision(7);
const ST = new Map();                                    // pool -> death/coverage state (unsealed rows only)
const stats = { days: {}, noDec: 0, noQ: 0 };
const onchainEthUsd = [];                                 // validation: 1 / price_eth(USDG) on the top ETH/USDG pool
const REF_POOL = '0x24107d152f14a76d292123265ae3f3c71f863fc2f4ef7ba49d64e78d28ea379e';

// read sort's stdout with REAL backpressure (a readline for-await queued a whole 2.5M-line wide day in RAM → heap OOM)
function eachLine(file, onLine, flush, gz) {
  return new Promise((resolve, reject) => {
    const p = spawn('sort', ['-s', '-t', '\t', '-k1,1n', '-k2,2n', '-u', '-S', '300M', '-T', path.dirname(file), file], { env: { ...process.env, LC_ALL: 'C' } });
    p.stderr.on('data', d => process.stderr.write(d));
    let rest = '';
    p.stdout.setEncoding('utf8');
    p.stdout.on('data', chunk => {
      const parts = (rest + chunk).split('\n'); rest = parts.pop();
      for (const ln of parts) if (ln) onLine(ln);
      if (!flush()) { p.stdout.pause(); gz.once('drain', () => p.stdout.resume()); }
    });
    p.stdout.on('end', () => { if (rest) onLine(rest); resolve(); });
    p.on('error', reject);
  });
}
async function day(d) {
  const sealed = Date.parse(d + 'T00:00:00Z') / 1000 >= SEAL;
  const gz = zlib.createGzip({ level: 6 });
  const ws = fs.createWriteStream(path.join(sealed ? SEALED_DIR : OUT, `v4-swaps-${d}.ndjson.gz`));
  gz.pipe(ws);
  const s = stats.days[d] = { rows: 0, pools: new Set(), toks: new Set(), bySrc: {}, byQ: {}, priced: 0, sealed };
  let buf = [];
  await eachLine(path.join(SH, d + '.tsv'), ln => {
    const f = ln.split('\t');
    const blk = +f[0], li = +f[1], ts = +f[2], tx = f[3];
    const p = P.get(f[4]); if (!p) return;
    const pool = p.id, src = SRC[f[10]];
    const a0 = Number(f[5]), a1 = Number(f[6]), sqrtP = Number(f[7]) / Q96, L = Number(f[8]), tick = +f[9];
    const dT = DEC[p.tok], dQ = p.quote === E0 ? 18 : DEC[p.quote];
    const decT = dT == null ? 18 : dT, decQ = dQ == null ? 18 : dQ;
    if (dT == null || dQ == null) stats.noDec++;
    const aTok = p.tokIs0 ? a0 : a1, aQ = p.tokIs0 ? a1 : a0;       // SWAPPER deltas: + received, - paid (lib/v4.js)
    const Praw = sqrtP * sqrtP;
    const pq = p.tokIs0 ? Praw * 10 ** (decT - decQ) : 10 ** (decT - decQ) / Praw;
    const depRaw = p.tokIs0 ? L * sqrtP : L / sqrtP;                  // quote units per unit of (sqrt(1+k)-1)
    const dep1q = depRaw * S1 / 10 ** decQ, dep5q = depRaw * S5 / 10 ** decQ;
    const eu = ethUsd(ts);
    let qeth = p.q === 'ETH' || p.q === 'WETH' ? 1 : p.q === 'USDG' ? 1 / eu : qPrice(p.quote, ts);
    if (qeth == null) stats.noQ++;
    const amtT = Math.abs(aTok) / 10 ** decT, amtQ = Math.abs(aQ) / 10 ** decQ;
    const pe = qeth != null ? pq * qeth : null;
    const row = { ts, blk, li, tx, tok: p.tok, pool, quote: p.q === 'other' ? (SYM[p.quote] || p.quote) : p.q, quote_addr: p.q === 'other' ? p.quote : undefined,
      price_quote: r6(pq), price_eth: r6(pe), price_usd: pe != null ? r6(pe * eu) : null,
      side: aTok > 0 ? 'buy' : aTok < 0 ? 'sell' : 'none', amount_token: r6(amtT), amount_quote: r6(amtQ),
      usd: qeth != null ? +(amtQ * qeth * eu).toFixed(2) : null, eth_usd: +eu.toFixed(2),
      liquidity: f[8], tick, depth1_eth: qeth != null ? r6(dep1q * qeth) : null, depth5_eth: qeth != null ? r6(dep5q * qeth) : null,
      pad: p.venue, pad_key: p.padKey || undefined, hook: p.hook || undefined, launcher: p.launcher || undefined,
      birth_ts: p.birthTs || null, src, dec_assumed: (dT == null || dQ == null) ? true : undefined, sealed: sealed ? true : undefined };
    buf.push(JSON.stringify(row));
    s.rows++; s.pools.add(pool); s.toks.add(p.tok); s.bySrc[src] = (s.bySrc[src] || 0) + 1; s.byQ[p.q] = (s.byQ[p.q] || 0) + 1; if (pe != null) s.priced++;
    // other-quote reference prices (causal): this pool prices a currency that other pools use as their quote
    if (OTHERQ.has(p.tok) && pe != null && pe > 0 && L > 0) {
      let m = QS.get(p.tok); if (!m) QS.set(p.tok, m = new Map());
      m.set(pool, { px: pe, ts, dep: dep1q * qeth });
    }
    if (pool === REF_POOL && pe > 0 && ts % 600 < 60) onchainEthUsd.push([ts, 1 / pe, eu]);
    if (!sealed) {                                                   // death/coverage state — UNSEALED rows only
      let t = ST.get(pool);
      if (!t) ST.set(pool, t = { first: ts, n: 0, nb: 0, peakPx: 0, peakTs: 0, peakL: 0, lowRunTs: null, srcs: new Set() });
      t.n++; if (aTok > 0) t.nb++; t.last = ts; t.srcs.add(src);
      if (pe != null) { t.lastPx = pe; if (pe > t.peakPx) { t.peakPx = pe; t.peakTs = ts; } }
      t.lastPq = pq; t.lastL = L; t.lastDep1 = qeth != null ? dep1q * qeth : null; t.lastDep5 = qeth != null ? dep5q * qeth : null;
      if (L > t.peakL) t.peakL = L;
      if (L <= t.peakL * DRAIN_FRAC) { if (t.lowRunTs == null) t.lowRunTs = ts; } else t.lowRunTs = null;
    }
  }, () => { if (buf.length < 2000) return true; const ok = gz.write(buf.join('\n') + '\n'); buf = []; return ok; }, gz);
  if (buf.length) gz.write(buf.join('\n') + '\n');
  gz.end(); await new Promise(r => ws.on('close', r));
  s.pools = s.pools.size; s.toks = s.toks.size;
  console.log(d, JSON.stringify(s), 'rss', (process.memoryUsage().rss / 1e6) | 0, 'MB');
}
(async () => {
  const days = fs.readdirSync(SH).filter(f => /^\d{4}-\d\d-\d\d\.tsv$/.test(f)).map(f => f.slice(0, 10)).sort()
    .filter(d => !process.env.DAYS || process.env.DAYS.split(',').includes(d));
  for (const d of days) await day(d);
  // death records — built from UNSEALED rows only, judged against the seal time as the data end
  const dz = zlib.createGzip(); const dw = fs.createWriteStream(path.join(OUT, 'v4-pool-deaths.ndjson.gz')); dz.pipe(dw);
  const dc = { pools: 0, dead: 0, drained: 0 };
  for (const [pool, t] of ST) {
    const p = P.get(pool), silentH = (SEAL - t.last) / 3600, dead = silentH >= DEAD_SILENT_H;
    const drained = t.lowRunTs != null;
    dc.pools++; if (dead) dc.dead++; if (drained) dc.drained++;
    dz.write(JSON.stringify({ pool, tok: p.tok, quote: p.q === 'other' ? (SYM[p.quote] || p.quote) : p.q, pad: p.venue, birth_ts: p.birthTs || null,
      first_ts: t.first, last_ts: t.last, n_swaps: t.n, n_buys: t.nb, srcs: [...t.srcs],
      peak_price_eth: r6(t.peakPx), peak_ts: t.peakTs, last_price_eth: r6(t.lastPx), last_price_quote: r6(t.lastPq),
      last_liquidity: String(t.lastL), peak_liquidity_ratio: t.peakL > 0 ? r6(t.lastL / t.peakL) : null,
      last_depth1_eth: r6(t.lastDep1), last_depth5_eth: r6(t.lastDep5),
      silent_h: +silentH.toFixed(2), dead, dead_ts: dead ? t.last : null,
      liq_drained: drained, drain_ts: t.lowRunTs,
      book_price_eth: drained ? 0 : (dead ? r6(t.lastPx) : null),
      book_rule: drained ? 'liquidity <1% of its peak at the last swaps: nothing to sell into, book 0 from drain_ts'
        : dead ? `no swap for >=${DEAD_SILENT_H} h before the seal: book last_price_eth, capped by last_depth*` : 'alive at the seal' }) + '\n');
  }
  dz.end(); await new Promise(r => dw.on('close', r));
  fs.writeFileSync(path.join(HERE, 'finalize_stats.json'), JSON.stringify({ ...stats, deaths: dc, qRefs: QS.size, otherQuotes: OTHERQ.size }, null, 1));
  fs.writeFileSync(path.join(HERE, 'onchain_ethusd.tsv'), onchainEthUsd.map(x => x.join('\t')).join('\n') + '\n');
  console.log('deaths', JSON.stringify(dc), 'noDec', stats.noDec, 'noQ', stats.noQ);
})();
