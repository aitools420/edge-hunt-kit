'use strict';
// seal_guard.js — preloaded by run_engine.sh (`node -r`), OUTSIDE the engines; it changes no decision, it only refuses or aborts.
// Block A seal = any row with ts >= 1790467200 (2026-09-27T00:00:00Z). Four checks:
//  1. STOP_DAY >= 2026-09-27 -> exit 97 before the engine loads.
//  2. Opening a tape file (under the two tape roots) whose NAME carries a day >= 2026-09-27, or any path under /sealed/ -> exit 97 BEFORE it is opened.
//  3. Any JSON.parse result with a numeric ts >= 1790467200 -> exit 98 at once. process.exit is not an exception, so v4tape.readV23Day's
//     try/catch (which would otherwise SKIP such a row silently) cannot swallow it.
//  4. Every tape file opened is appended to $SEAL_LOG (the proof of what was read).
// SEAL_TEST_ROOT adds a throwaway root for the synthetic self-test only (never a real tape path).
const fs = require('fs'), path = require('path');
const SEAL = 1790467200, SEAL_DAY = '2026-09-27';
const ROOTS = ['/home/green/.openclaw/workspace/wick-engine/logs/', '/home/green/projects/patches/v4-join-2026-09-27/out/']
  .concat(process.env.SEAL_TEST_ROOT ? [process.env.SEAL_TEST_ROOT] : []);
const LOG = process.env.SEAL_LOG || null;
function die(code, msg) { try { fs.writeSync(2, `SEAL GUARD: ${msg}\n`); } catch (e) { /* ignore */ } process.exit(code); }
if (process.env.STOP_DAY && process.env.STOP_DAY >= SEAL_DAY) die(97, `STOP_DAY ${process.env.STOP_DAY} is sealed`);
function check(p) {
  if (typeof p !== 'string' && !Buffer.isBuffer(p) && !(p instanceof URL)) return;   // numeric fds: opened earlier through a checked path
  const s = path.resolve(p instanceof URL ? p.pathname : String(p));
  if (!ROOTS.some(r => s.startsWith(r))) return;
  const days = path.basename(s).match(/\d{4}-\d{2}-\d{2}/g) || [];
  if (s.includes('/sealed/') || days.some(d => d >= SEAL_DAY)) die(97, `refused to open sealed file ${s}`);
  if (LOG) fs.appendFileSync(LOG, s + '\n');
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
