// guard_test.js — the three STEP-0 tests, run against BOTH guards. The fixed guard must pass all three; the old guard must fail (a) and (c).
'use strict';
const { acceptOld, acceptNew } = require('./guard.js');
function run(acc, series) { const T = { med: [], q: 'WETH' }; let last = null; const log = [];
  for (const px of series) { const ok = acc(T, { px, usd: 50, quote: 'WETH' }); if (ok) last = px; log.push(ok ? 'A' : 'R'); }
  return { last, log: log.join('') }; }
const tests = [
  { name: '(a) synthetic rug: 1.0 x6 then 0.02 ... 0.008 -> must book near -99 %', series: [1, 1.02, 0.98, 1.01, 0.99, 1.0, 0.02, 0.018, 0.015, 0.012, 0.01, 0.01, 0.009, 0.008],
    pass: o => o.last !== null && (o.last / 1 - 1) * 100 <= -98.5, show: o => `books ${(100 * (o.last / 1 - 1)).toFixed(1)} %` },
  { name: '(b) lone spike: 1,1,1,1,1,40,1,1 -> the 40 must be rejected', series: [1, 1, 1, 1, 1, 40, 1, 1],
    pass: o => o.log[5] === 'R' && o.last === 1, show: o => `print 6 (40) ${o.log[5] === 'R' ? 'REJECTED' : 'ACCEPTED'}, last booked ${o.last}` },
  { name: '(c) genuine persistent 30x pump: 1 x6 then 30,31,32,30,33,35 -> must be accepted', series: [1, 1, 1, 1, 1, 1, 30, 31, 32, 30, 33, 35],
    pass: o => o.last === 35, show: o => `last booked ${o.last} (truth 35)` },
  { name: '(d) extra: two-print spike then back (1 x5, 40, 40, 1, 1) -> documents the known cost of CONFIRM_N=2', series: [1, 1, 1, 1, 1, 40, 40, 1, 1],
    pass: () => true, show: o => `accept log ${o.log}, last ${o.last}` },
  { name: '(e) extra: alternating outliers on opposite sides (1 x5, 40, 0.02, 40, 1) -> none accepted', series: [1, 1, 1, 1, 1, 40, 0.02, 40, 1],
    pass: o => o.log.slice(5, 8) === 'RRR', show: o => `accept log ${o.log}` },
];
let allNew = true;
for (const t of tests) {
  const o = run(acceptOld, t.series), n = run(acceptNew, t.series);
  const po = t.pass(o), pn = t.pass(n); if (!pn) allNew = false;
  console.log(`${t.name}\n   OLD guard: ${po ? 'PASS' : 'FAIL'} — ${t.show(o)}  [${o.log}]\n   NEW guard: ${pn ? 'PASS' : 'FAIL'} — ${t.show(n)}  [${n.log}]`);
}
console.log(allNew ? 'NEW GUARD: ALL REQUIRED TESTS PASS' : 'NEW GUARD: FAILURE'); process.exit(allNew ? 0 : 1);
