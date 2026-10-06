#!/usr/bin/env node
// cut_v4.js <anchors.tsv> <in.ndjson> <out.ndjson> <cut_unix> <from_unix> [margin_blocks=100000] — NEW CODE (sealed-exam-blockA).
// Copies the rows of a raw V4 log file (locked tape or a v4-wide day file) whose time is in [from, cut) — time from the block with
// pass1.js's OWN interpolation (blkTs below is pass1's, verbatim) — reading ONLY each row's "blk" field (regex, no JSON parse).
// It stops at the first row whose block is >= BLK_CUT + margin: the locked tape writes rows up to ~40,000 blocks (~67 min) late
// (measured on the open days 09-10..09-26: max 39,994), so 100,000 blocks of margin catch every late row before the cut.
// Exit 3 (NOT READY) if the file ends before that row: the writer has not passed the margin yet; the runner waits and retries.
// Prints {read, kept, inversions, maxLateBlocks, lateKeptAfterCutRow, sha256, bytes}. The kept content's sha256 is the exam's record.
'use strict';
const fs = require('fs'), crypto = require('crypto');
const [ANCH, IN, OUT, CUTS, FROMS, MARGS] = process.argv.slice(2);
const CUT = +CUTS, FROM = +FROMS, MARGIN = MARGS ? +MARGS : 100000;
const A = fs.readFileSync(ANCH, 'utf8').trim().split('\n').map(l => l.split('\t').map(Number));
const AB = A.map(a => a[0]);
function blkTs(b) {                                       // pass1.js, verbatim
  let lo = 0, hi = AB.length - 1;
  if (b <= AB[0]) { lo = 0; hi = 1; } else if (b >= AB[hi]) { lo = hi - 1; } else {
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (AB[m] <= b) lo = m; else hi = m; }
  }
  hi = lo + 1;
  const [b0, t0] = A[lo], [b1, t1] = A[hi];
  return Math.round(t0 + (b - b0) * (t1 - t0) / (b1 - b0));
}
let lo = AB[0], hi = AB[AB.length - 1];                   // BLK_CUT = the first block whose time is >= CUT (blkTs is non-decreasing)
if (blkTs(hi) < CUT) { console.log(JSON.stringify({ notReady: 'anchors end before the cut' })); process.exit(3); }
while (lo < hi) { const m = Math.floor((lo + hi) / 2); if (blkTs(m) >= CUT) hi = m; else lo = m + 1; }
const BLK_CUT = lo, BLK_STOP = BLK_CUT + MARGIN;
const fd = fs.openSync(IN, 'r'), out = fs.openSync(OUT, 'w'), h = crypto.createHash('sha256');
const RX = /"blk":(\d+)/;
let buf = Buffer.alloc(0), pos = 0, read = 0, kept = 0, bytes = 0, inv = 0, maxLate = 0, maxBlk = 0, sawCutRow = false, lateKept = 0, stopped = false;
const chunk = Buffer.alloc(1 << 22);
outer: for (;;) {
  const n = fs.readSync(fd, chunk, 0, chunk.length, pos); if (n <= 0) break; pos += n;
  buf = Buffer.concat([buf, chunk.subarray(0, n)]);
  let st = 0, i;
  while ((i = buf.indexOf(10, st)) >= 0) {
    const line = buf.subarray(st, i + 1); st = i + 1;
    const m = RX.exec(line.subarray(0, Math.min(line.length, 200)).toString('latin1'));
    if (!m) continue;
    const b = +m[1]; read++;
    if (b >= BLK_STOP) { stopped = true; break outer; }
    if (b < maxBlk) { inv++; if (maxBlk - b > maxLate) maxLate = maxBlk - b; } else maxBlk = b;
    const t = blkTs(b);
    if (t >= CUT) { sawCutRow = true; continue; }
    if (t < FROM) continue;
    if (sawCutRow) lateKept++;
    fs.writeSync(out, line); h.update(line); kept++; bytes += line.length;
  }
  buf = buf.subarray(st);
}
fs.closeSync(fd); fs.closeSync(out);
const res = { in: IN, BLK_CUT, BLK_STOP, read, kept, bytes, inversions: inv, maxLateBlocks: maxLate, lateKeptAfterCutRow: lateKept, sha256: h.digest('hex'), stopped };
console.log(JSON.stringify(res));
process.exit(stopped ? 0 : 3);
