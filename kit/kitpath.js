// kitpath.js — loaded with `node --require kit/kitpath.js` (run_batch.sh sets NODE_OPTIONS). PATH REWRITE ONLY.
// The frozen engine (engine_v1.js), qpools.js, v4tape.js and pools.js are shipped BYTE-IDENTICAL to the originals, and they contain
// absolute paths of the machine they were built on. This preload maps those two path prefixes to $KIT_ROOT before any file is opened:
//     <ORIG_PATCHES>/...  ->  $KIT_ROOT/patches/...
//     <ORIG_TAPE>/...     ->  $KIT_ROOT/tape/v23/...
// It hooks module resolution (require of an absolute path) and the fs calls those files use (readFileSync, existsSync, readdirSync,
// statSync, createReadStream, openSync). It never changes file CONTENT or any value the engine computes: a path that does not start with
// one of the two prefixes is passed through untouched, and the same bytes are read either way.
'use strict';
const fs = require('fs'), path = require('path'), Module = require('module');
const ROOT = process.env.KIT_ROOT && path.resolve(process.env.KIT_ROOT);
if (!ROOT) { console.error('kitpath.js: KIT_ROOT is not set'); process.exit(2); }
const MAP = [
  ['/home/green/projects/patches/', path.join(ROOT, 'patches') + '/'],
  ['/home/green/.openclaw/workspace/wick-engine/logs', path.join(ROOT, 'tape', 'v23')],
];
function remap(p) {
  if (typeof p !== 'string' || p.startsWith(ROOT + '/')) return p;   // already inside the kit (the kit may itself live under an origin prefix)
  for (const [a, b] of MAP) if (p.startsWith(a)) return b + p.slice(a.length);
  return p;
}
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) { return origResolve.call(this, remap(request), ...rest); };
for (const fn of ['readFileSync', 'existsSync', 'readdirSync', 'statSync', 'createReadStream', 'openSync']) {
  const orig = fs[fn];
  fs[fn] = function (p, ...rest) { return orig.call(fs, remap(p), ...rest); };
}
module.exports = { remap };
