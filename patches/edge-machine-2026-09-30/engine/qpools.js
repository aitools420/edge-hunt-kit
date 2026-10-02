// qpools.js <tokens.txt> <out.json>: every pool (the v4 join's own pool table, pools.js) whose TOKEN is one of the given quote tokens,
// with its quote class, fee key and hook. Read-only.
'use strict';
const fs = require('fs'); const { load } = require('/home/green/projects/patches/v4-join-2026-09-27/pools.js');
const want = new Set(fs.readFileSync(process.argv[2], 'utf8').split(/\s+/).filter(Boolean)); const P = load(); const out = {};
for (const [id, p] of P) if (want.has(p.tok)) out[id] = { tok: p.tok, q: p.q, quote: p.quote, fee: p.fee, hook: p.hook || null, venue: p.venue };
fs.writeFileSync(process.argv[3], JSON.stringify(out)); console.log('tokens', want.size, 'pools', Object.keys(out).length);
