#!/usr/bin/env python3
"""set_constants.py <in> <out> <spec.json> — make a copy of a code file with exact, listed text replacements.
spec.json = {"note": "...", "pairs": [[old, new], ...]}. Every `old` must occur EXACTLY ONCE in the input (asserted), and every
`new` exactly once in the output. Used for: the Option A proof's no-skip variant (DEPTH_FLOOR 0), Test A (exam window constants set
back to the original 09-08..09-26 values), Test B (a dry-run window on open days), Test D (a deliberately broken window)."""
import json, sys
src, out, spec = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
s = open(src).read()
for old, new in spec['pairs']:
    n = s.count(old)
    assert n == 1, f'{sys.argv[3]}: anchor found {n} times in {src}: {old[:100]!r}'
    s = s.replace(old, new)
for old, new in spec['pairs']:
    assert s.count(new) >= 1, f'replacement missing: {new[:80]!r}'
open(out, 'w').write(s)
print(f"{len(spec['pairs'])} replacements -> {out}")
