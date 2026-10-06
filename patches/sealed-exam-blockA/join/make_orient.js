// make_orient.js — join/orient_0927.json: the 09-27 join's own orientation ({poolId: tok}) for every pool it oriented by RULE or by
// its Initialize log (no named token), computed with the 09-27 pools.js on the 09-27 table, read-only.
const A = require('/home/green/projects/patches/v4-join-2026-09-27/pools.js');
const PA = A.load('/home/green/projects/patches/v4-join-2026-09-27'); const out = {}; const c = {};
for (const [id, a] of PA) { c[a.how] = (c[a.how] || 0) + 1; if (a.how !== 'births') out[id] = a.tok; }
require('fs').writeFileSync(process.argv[2], JSON.stringify(out)); console.log(JSON.stringify({ how: c, pinned: Object.keys(out).length }));
