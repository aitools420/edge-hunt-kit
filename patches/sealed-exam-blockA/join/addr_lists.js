#!/usr/bin/env node
// addr_lists.js <work> — NEW CODE (sealed-exam-blockA): decimals.js's two inputs (the 09-27 run built them by hand, not kept): the quote
// currencies and the tokens of every pool with at least one swap in the shards (poolcounts.tsv), from the exam pool table (pools.js).
// Out: <work>/addr_quotes.json and <work>/addr_toks.json as [[address, pools], ...]. decimals.js then fetches only what the
// 09-27 decimals.json (copied in by the runner) does not already hold.
'use strict';
const fs = require('fs'), path = require('path');
const W = process.argv[2];
const { load } = require('./pools.js');
const P = load(W);
const keep = new Set(fs.readFileSync(path.join(W, 'poolcounts.tsv'), 'utf8').split('\n').map(l => l.split('\t')[0]).filter(Boolean));
const q = new Map(), t = new Map(); let n = 0, miss = 0;
for (const id of keep) { const p = P.get(id); if (!p) { miss++; continue; } n++; q.set(p.quote, (q.get(p.quote) || 0) + 1); t.set(p.tok, (t.get(p.tok) || 0) + 1); }
const srt = m => [...m].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
fs.writeFileSync(path.join(W, 'addr_quotes.json'), JSON.stringify(srt(q)));
fs.writeFileSync(path.join(W, 'addr_toks.json'), JSON.stringify(srt(t)));
console.log(JSON.stringify({ poolsWithSwaps: keep.size, inPoolTable: n, notInPoolTable: miss, quotes: q.size, toks: t.size }));
