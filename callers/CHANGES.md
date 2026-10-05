# CHANGES — every line in this kit that differs from what we ran

All edits are **path-only**: no constant, rule, seed or formula changed. Each edit was applied by `_build/patch_code.py`, which asserts
that the old text occurs exactly once, and then reverses every edit and checks that the result is byte-identical to our file
(sha256 below). `_build/` is our internal build folder and is not part of the kit.

## Code files edited

### `engine/engine_fast.py` (from `callers-fast-2026-10-02/engine_fast.py`)
- sha256 ours `4bc21eac5d997d0a5011c41d3dfb9a377a6e98a7dad19679a6919f0f366b99f7` → kit `41481370c1bc199c4e12e9882e7fe6eff9fb8d07b5248b38edf14039bb7f9922`
- old:
```
for a, b in REPL:
    assert body.count(a) == 1, a
```
- new:
```
# ── KIT PATH EDITS (callers kit 2026-10-05): engine.py stays byte-identical; its six machine paths are replaced in the exec'd text ──
REPL += [
    ('sys.path.insert(0, "/home/green/projects/patches/v4-join-2026-09-27")\n', 'sys.path.insert(0, HERE)\n'),
    ('WLOGS = "/home/green/.openclaw/workspace/wick-engine/logs"\n', 'WLOGS = os.environ["CALLERS_TAPE_ROOT"]\n'),
    ('TAPE_DIR = os.path.join(WLOGS, "robinhood-tape")\n', 'TAPE_DIR = os.environ["CALLERS_TAPE_LIVE"]\n'),
    ('V4_BIRTHS = os.path.join(WLOGS, "robinhood-v4-births.ndjson")\n', 'V4_BIRTHS = os.environ["CALLERS_BIRTHS"]\n'),
    ('TOK_BIRTHS = os.path.join(WLOGS, "robinhood-token-births.json")\n', 'TOK_BIRTHS = os.environ["CALLERS_TOK_BIRTHS"]\n'),
    ('BF_DIR = "/home/green/projects/patches/v4-backfill-join-2026-09-29/out"\n', 'BF_DIR = os.environ["CALLERS_BF_DIR"]\n'),
]
for a, b in REPL:
    assert body.count(a) == 1, a
```

### `engine/costs.py` (from `callers-fast-2026-10-02/costs.py`)
- sha256 ours `8aa2ae495467a27e678e60ea5d6fc596eb2313fa78f1927fa9a9c0917053801d` → kit `b96aa186f537e739b3b6d14029262cc27e3468ed199d043e99828ebfff844c66`
- old:
```
P = "/home/green/projects/patches"
```
- new:
```
P = os.environ["CALLERS_EDGE_PATCHES"]          # kit: the edge-hunt-kit's patches/ folder
```
- old:
```
json.load(open(P + "/v4-backfill-join-2026-09-29/state.json"))["newPools"]
```
- new:
```
json.load(gzip.open(os.path.join(HERE, "inputs", "newpools.json.gz"), "rt"))
```

### `engine/analyze_fast.py` (from `callers-fast-2026-10-02/analyze_fast.py`)
- sha256 ours `e1f3d35ff1b4230e2906802a901db171789bc0c34db35366b66a658c61fb8ab4` → kit `115bb0c8b81c89e00568d74e027947392d5ad81a18c4b32742a8382f9eac1b60`
- old:
```
json.load(open("/home/green/projects/patches/callers-fill1-2026-09-30/passB/results.json"))
```
- new:
```
json.load(open(os.path.join(HERE, "..", "results", "callers-fill1-2026-09-30-passB", "results.json")))
```

### `engine/cells.py` (from `callers-fast-2026-10-02/cells.py`)
- sha256 ours `82245a433f665ce3804594b7aa10f7aca4294357e9e7d8eeb0ff2a372a66b5d8` → kit `b04f11cf991f7d6460d2e99987e74b1af604de546e8e16cad9c34df761854b89`
- old:
```
json.load(open("/home/green/projects/patches/callers-fill1-2026-09-30/passB/results.json"))
```
- new:
```
json.load(open(os.path.join(HERE, "..", "results", "callers-fill1-2026-09-30-passB", "results.json")))
```

### `engine/v4tape.py` (from `v4-join-2026-09-27/v4tape.py`)
- sha256 ours `bb23f0ce976fa8ee24e6ee7174579f2627c46913b9de31d220d54b25c8255dd1` → kit `c95c83e2b49a01512bc5577152fee5613f7e63bbe523a3c937b5fe662ef8a6b2`
- old:
```
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
```
- new:
```
DIR = os.environ.get('CALLERS_V4_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
```
- old:
```
WE = '/home/green/.openclaw/workspace/wick-engine/logs'
```
- new:
```
WE = os.environ.get('CALLERS_TAPE_ROOT', '')
```

### `engine/report.py` (from `callers-fast-2026-10-02/report.py`)
- sha256 ours `3cec71b7be87b602bd641cca3c505d05a7548631afef74b936187b8bd9d5f4cd` → kit `3cec71b7be87b602bd641cca3c505d05a7548631afef74b936187b8bd9d5f4cd`
- **no edits** (byte-identical)

### `engine/engine.py` — NOT edited (byte-identical, sha256 `311370c9fbaf3fc4c5b3f0be5f628d98cc76d94ec670f46f425d94c11b91b950`)
It still contains three absolute paths of our machine (lines 14, 18, 23) and three paths built from them (lines 19, 21, 22).
`engine_fast.py` replaces those six lines in the text it
`exec()`s, through the `REPL +=` block shown above, so `engine.py` keeps the sha256 that `engine_fast.py` asserts. Running `engine.py`
directly (without `engine_fast.py`) will therefore NOT work in the kit, and is not needed.
`engine/v4tape.py` keeps one absolute path in its docstring (line 3, a usage example — not executed).

## Byte-identical copies (sha256 = ours)

- `engine/engine.py` `311370c9fbaf3fc4c5b3f0be5f628d98cc76d94ec670f46f425d94c11b91b950`
- `engine/guard.py` `b4a7de4c4b0db638ab4acbc12241ebb414b219d54e6829a48f164e8674332dd5`
- `engine/analyze.py` `9f136a7d68f738816eb51723718c96f089fba64fbc2600ca20ef62ea30d69024`
- `engine/report.py` `3cec71b7be87b602bd641cca3c505d05a7548631afef74b936187b8bd9d5f4cd`
- `engine/calls_snapshot.json` `bb23c1b1bd07bcca291881cbc4a19cebb4e340a4ae32da0c95dc358a2ad87f40`
- `engine/calledmeta.json` `d680df8b0a548afc078a58868765843d1bcf696ba542390833c4a9e737c8a615`
- `engine/levels.json` `0a8811729500a87192619e31f3dc30e7f453949acb20276fdcdd173ebc3fe0a7`
- `engine/bands.json` `9ac4bfb244a3a4130130d2bbb49fc2d9f8f23ba26c3642b3a3affe809a0b50bc`
- `engine/cells1.json` `f6fb1382fce7ba8771b00f263dfd173e281bf1281392f8825d45c239532336e8`
- `engine/cells2.json` `0a3c87dd07b22e1ff28bb02e4453d1af49c6b1c394f21761fdf5a7e080c04b88`
- `engine/hop_static.json` `8143b44d271b7c385f0cf649cf7a867399126209251151e2554d18ef7e464821`
- `engine/PREREG.sha256` `5cad2a24bc4d988e1abfbfab13bd066d592c7a785ae74d8753d6f01df5c099ea`
- everything under `results/` except `ref_rows_d60_tp50.ndjson.gz`, and everything under `docs/`
- `engine/hop_static.json` still names the three hop-table files it was built from by our absolute paths (field `tables`). Only
  `tokens`, `fallback_other` and `usdg` are read by `costs.py`; the tables themselves are not in the kit (see README, *not included*).

## Derived input files (not copies) — built by `_build/build_kit.py` from our files, read-only

| kit file | built from | what changed |
|---|---|---|
| `engine/inputs/poolfee.tsv.gz` | pass B's `poolfee.tsv` (pool, fee key, venue, token, pool birth ts) | gzipped; **1,732 rows of pools born at/after the seal dropped** (792,976 kept). A pool born after the seal holds no pre-seal trade, so the engine cannot read them. `run_kit.sh` unpacks it to `engine/poolfee.tsv` (the name the engine opens). |
| `engine/inputs/births_min.ndjson.gz` | the three birth sources the engine reads (`poolfee.tsv` cols 4–5, our live `robinhood-v4-births.ndjson`, our live `robinhood-token-births.json`) | one line per token = the engine's own rule (minimum over all three sources, the token-births file parsed with the engine's own regex and 16 MB chunking), **pre-seal records only** (76,241 records at/after the seal dropped; 762,978 tokens). Checked: 0 called tokens have only post-seal birth records, so no study row's age changes; a twin candidate is always already seen on the tape, so `min(birth, first_seen)` is unchanged too. The engine reads it through `V4_BIRTHS` (`CALLERS_BIRTHS`); `TOK_BIRTHS` points at `token_births_empty.json` (`{}`), so the merged file is read once. The raw files are not shipped: they also hold creator wallets and post-seal records. |
| `engine/inputs/token_births_empty.json` | — | `{}` (see the row above) |
| `engine/inputs/newpools.json.gz` | `v4-backfill-join-2026-09-29/state.json` → `newPools` | only that key (pool → currency0, currency1, fee, hook, birth block), read by `costs.py`. All 131,312 pools were born at or before block 73,495,000 (the last pre-seal V4 row), so none was dropped. |
| `calls.ndjson.gz` | `callhist-2026-09-30/calls.ndjson.gz` ∪ the engine's `calls_snapshot.json` events, joined on `id` | see README §calls.ndjson.gz: outcome fields dropped, two flags added. |
| `results/callers-fill1-2026-09-30-passB/ref_rows_d60_tp50.ndjson.gz` | pass B `rows_tp50.ndjson` (93 MB) | slim copy for row-level parity: the call and its twins at the 1-min entry, TP +50 %; per hold `[how, g, n, mts, mpx]` (holds 5 min, 7.5 min, 15 min, 1 h, 4 h, 12 h, 24 h, 72 h, 5 d, 7 d) or `"oow"`/`null`. |

## Files added by the kit

- `run_kit.sh`, `.gitignore`, `README.md`, `CHANGES.md`, `MANIFEST.sha256`, `engine/inputs/token_births_empty.json`.
