#!/usr/bin/env node
// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
// pass1.js — STREAM every v4 swap source into per-UTC-day TSV shards (unsorted, may hold duplicates).
// Sources (read-only): noxabot logs/uniswap-v4-tape.ndjson (locked set, 07-20→), -hole (09-04→09-10 backfill),
// -backfill (08-06 cohort), logs/v4-wide/uniswap-v4-wide-*.ndjson (EVERY v4 pool, 09-18→).
// blk = log blockNumber = L2 height (the writer stores parseInt(l.blockNumber)); ts from anchors.tsv by linear
// interpolation (validated in validate.py). Shard line: blk \t li \t ts \t tx \t pool \t a0 \t a1 \t sp \t lq \t tk \t src
// Usage: node pass1.js <shardDir>
'use strict';
const fs = require('fs'), path = require('path'), readline = require('readline');
const HERE = '/home/green/projects/patches/sealed-exam-blockA/work/v4join', SH = process.argv[2];
const CUT = 1791331200, JOIN0 = '2026-09-25';   // sealed-exam-blockA: the block's CUT and the join's first day
if (!SH) throw new Error('shard dir');
fs.mkdirSync(SH, { recursive: true });
const M = JSON.parse(fs.readFileSync(path.join(HERE, 'meta.json'), 'utf8'));
const mainPool = M.mainPool; M.pools = null;
// anchors
const A = fs.readFileSync(path.join(HERE, 'anchors.tsv'), 'utf8').trim().split('\n').map(l => l.split('\t').map(Number));
const AB = A.map(a => a[0]);
function blkTs(b) {
  let lo = 0, hi = AB.length - 1;
  if (b <= AB[0]) { lo = 0; hi = 1; } else if (b >= AB[hi]) { lo = hi - 1; } else {
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (AB[m] <= b) lo = m; else hi = m; }
  }
  hi = lo + 1;
  const [b0, t0] = A[lo], [b1, t1] = A[hi];
  return Math.round(t0 + (b - b0) * (t1 - t0) / (b1 - b0));
}
const streams = new Map();
function out(day) {
  let s = streams.get(day);
  if (!s) { s = { buf: [], fd: fs.openSync(path.join(SH, day + '.tsv'), 'a') }; streams.set(day, s); }
  return s;
}
function flush(s) { if (s.buf.length) { fs.writeSync(s.fd, s.buf.join('')); s.buf = []; } }
const stats = {};
async function run(file, src, wide) {
  const st = stats[src + ':' + path.basename(file)] = { lines: 0, swaps: 0, nopool: 0, bad: 0, afterCut: 0, beforeJoin0: 0 };
  const rl = readline.createInterface({ input: fs.createReadStream(file), crlfDelay: Infinity });
  for await (const ln of rl) {
    if (!ln) continue; st.lines++;
    let r; try { r = JSON.parse(ln); } catch { st.bad++; continue; }
    if (r.t !== 's') continue;
    const pool = wide ? r.id : mainPool[r.tok];
    if (!pool) { st.nopool++; continue; }
    st.swaps++;
    const ts = blkTs(r.blk), day = new Date(ts * 1000).toISOString().slice(0, 10);
    if (ts >= CUT) { st.afterCut++; continue; } if (day < JOIN0) { st.beforeJoin0++; continue; }   // sealed-exam-blockA range filter
    const s = out(day);
    s.buf.push(`${r.blk}\t${r.li}\t${ts}\t${r.tx}\t${pool}\t${r.a0}\t${r.a1}\t${r.sp}\t${r.lq}\t${r.tk}\t${src}\n`);
    if (s.buf.length >= 5000) flush(s);
  }
  console.log(src, path.basename(file), JSON.stringify(st));
}
(async () => {
  const L = '/home/green/projects/patches/sealed-exam-blockA/work/v4join/in';
  await run(path.join(L, 'uniswap-v4-tape.ndjson'), 'lock', false);
  await run(path.join(L, 'uniswap-v4-tape-hole.ndjson'), 'hole', false);
  await run(path.join(L, 'uniswap-v4-tape-backfill.ndjson'), 'bf', false);
  for (const f of fs.readdirSync(path.join(L, 'v4-wide')).filter(f => /^uniswap-v4-wide-\d{4}-\d\d-\d\d\.ndjson$/.test(f)).sort())
    await run(path.join(L, 'v4-wide', f), 'wide', true);
  for (const s of streams.values()) { flush(s); fs.closeSync(s.fd); }
  fs.writeFileSync(path.join(HERE, 'pass1_stats.json'), JSON.stringify(stats, null, 1));
  console.log('days', [...streams.keys()].sort().join(' '));
})();
