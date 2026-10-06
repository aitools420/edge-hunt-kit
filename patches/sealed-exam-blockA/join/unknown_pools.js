#!/usr/bin/env node
// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
// unknown_pools.js — pre-pass: pool ids in the WIDE v4 files that the births ledger/poolkeys do not name.
// Also keeps any Initialize row the wide files carry for them (c0/c1/fee/ts/hook). Read-only; writes unknown_pools.json here.
'use strict';
const fs = require('fs'), path = require('path'), readline = require('readline');
const M = JSON.parse(fs.readFileSync(path.join('/home/green/projects/patches/sealed-exam-blockA/work/v4join', 'meta.json'), 'utf8'));
const WD = '/home/green/projects/patches/sealed-exam-blockA/work/v4join/in/v4-wide';
(async () => {
  const U = {};
  for (const f of fs.readdirSync(WD).filter(f => /^uniswap-v4-wide-\d{4}-\d\d-\d\d\.ndjson$/.test(f)).sort()) {
    const rl = readline.createInterface({ input: fs.createReadStream(path.join(WD, f)), crlfDelay: Infinity });
    for await (const ln of rl) {
      if (!ln) continue; const r = JSON.parse(ln);
      if (M.pools[r.id]) continue;
      const u = U[r.id] || (U[r.id] = { n: 0, first: r.blk, last: r.blk, init: null });
      if (r.t === 's') { u.n++; if (r.blk < u.first) u.first = r.blk; if (r.blk > u.last) u.last = r.blk; }
      if (r.t === 'i') u.init = { c0: r.c0, c1: r.c1, fee: r.fee, ts: r.ts, hook: r.hook, blk: r.blk };
    }
    console.log(f, Object.keys(U).length);
  }
  fs.writeFileSync(path.join('/home/green/projects/patches/sealed-exam-blockA/work/v4join', 'unknown_pools.json'), JSON.stringify(U));
  const arr = Object.entries(U).sort((a, b) => b[1].n - a[1].n);
  const tot = arr.reduce((s, x) => s + x[1].n, 0);
  console.log('unknown pools', arr.length, 'swaps', tot, 'with init', arr.filter(x => x[1].init).length, 'top10 share', arr.slice(0, 10).reduce((s, x) => s + x[1].n, 0) / tot, 'top200 share', arr.slice(0, 200).reduce((s, x) => s + x[1].n, 0) / tot);
})();
