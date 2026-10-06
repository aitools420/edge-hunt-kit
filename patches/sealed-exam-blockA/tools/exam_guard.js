'use strict';
// exam_guard.js — sealed-exam-blockA. Preloaded (`node -r`) into every exam engine and every join step by run_exam.sh, OUTSIDE the
// engines: it changes no decision, it only refuses or aborts. Built on twinfix-2026-10-05/tools/seal_guard.js (same four checks),
// with the BLOCK B seal: any row with ts >= SEAL (2026-10-07T00:00:00Z) belongs to the next block and is never read.
//  1. STOP_DAY >= WORK_DAY -> exit 97 before the program loads.
//  2. Opening a file under a REAL data root whose NAME carries a day >= REAL_DAY -> exit 97 (the raw 10-07 files hold Block B rows;
//     only the runner's CUT copy, which lives in the work folder, may be read). Opening a file under the WORK folder whose name carries
//     a day >= WORK_DAY -> exit 97. Paths are resolved through symlinks first, so a work/tape link to a raw 10-07 file is refused too.
//     Any path containing /sealed/ -> exit 97.
//  3. Any JSON.parse result with a numeric ts >= SEAL -> exit 98 at once (process.exit, so no try/catch in the program can swallow it).
//  4. Every data file opened is appended to $SEAL_LOG (the proof of what was read).
// EXAM_GUARD_TEST_ROOT adds a throwaway REAL root for the synthetic self-test only (it can only add refusals).
const fs = require('fs'), path = require('path');
const SEAL = 1791331200, REAL_DAY = '2026-10-07', WORK_DAY = '2026-10-08';
const REAL = ['/home/green/.openclaw/workspace/wick-engine/logs/', '/home/green/projects/patches/v4-join-2026-09-27/out/', '/home/green/noxabot/logs/']
  .concat(process.env.EXAM_GUARD_TEST_ROOT ? [process.env.EXAM_GUARD_TEST_ROOT] : []);
const WORK = ['/home/green/projects/patches/sealed-exam-blockA/work/'];
const LOG = process.env.SEAL_LOG || null;
function die(code, msg) { try { fs.writeSync(2, `EXAM GUARD: ${msg}\n`); } catch (e) { /* ignore */ } process.exit(code); }
if (process.env.STOP_DAY && process.env.STOP_DAY >= WORK_DAY) die(97, `STOP_DAY ${process.env.STOP_DAY} is in the next block`);
const realOf = s => { try { return fs.realpathSync(s); } catch (e) { return s; } };
function check(p) {
  if (typeof p !== 'string' && !Buffer.isBuffer(p) && !(p instanceof URL)) return;   // numeric fds: opened earlier through a checked path
  const s = path.resolve(p instanceof URL ? p.pathname : String(p)), r = realOf(s);
  const dayGE = (q, d) => (path.basename(q).match(/\d{4}-\d{2}-\d{2}/g) || []).some(x => x >= d);
  let hit = false;
  for (const q of [s, r]) {
    if (q.includes('/sealed/')) die(97, `refused to open ${s} (${r}): a /sealed/ path`);
    if (REAL.some(x => q.startsWith(x))) { hit = true; if (dayGE(q, REAL_DAY)) die(97, `refused to open ${s} (${r}): a raw file of a day >= ${REAL_DAY}`); }
    if (WORK.some(x => q.startsWith(x))) { hit = true; if (dayGE(q, WORK_DAY)) die(97, `refused to open ${s} (${r}): a work file of a day >= ${WORK_DAY}`); }
  }
  if (hit && LOG) fs.appendFileSync(LOG, (s === r ? s : `${s} -> ${r}`) + '\n');
}
for (const fn of ['createReadStream', 'readFileSync', 'openSync', 'open', 'readFile']) {
  const orig = fs[fn]; fs[fn] = function (p, ...a) { check(p); return orig.call(this, p, ...a); };
}
const PARSE = JSON.parse;
JSON.parse = function (text, reviver) {
  const o = PARSE(text, reviver);
  if (o !== null && typeof o === 'object' && typeof o.ts === 'number' && o.ts >= SEAL) die(98, `a row with ts ${o.ts} >= ${SEAL} was parsed — run aborted`);
  return o;
};
