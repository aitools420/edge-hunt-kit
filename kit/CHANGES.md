# What differs from the copy we run, and why it cannot change a number

**The rule we held to:** nothing that computes is touched. Every difference is one of four kinds:
- (a) where a file is found;
- (b) the resource gate;
- (c) the manifest machinery that checks files;
- (d) the optional hunter's notification and explorer hooks.

Two checks prove this:
- `kit/unpatch_check.py` reverses every edit listed in `kit/PATCHES.json` and requires the result to have exactly the sha256 of our file. That sha256 is recorded in `engine/MANIFEST.json` as `code_original` / `external_original`.
- The parity run must reproduce our 12 published cells: identical `results.json` records and 546 identical trade rows.

## Byte-identical to ours (no change at all)
- **Engine:** `engine_v1.js` (sha256 `d1f23fed4ba60bc02eb27d5b2114a63b04015cb9c0ce252ee3efd9005de9db1c`), `guard.js`, `guard_test.js`, `qpools.js`, `prepare_v1.py`, `run_pass_v1.sh`.
- **Readers:** `patches/v4-join-2026-09-27/v4tape.js` and `pools.js`.
- **Every input table:**
  - `inputs/*.tsv.gz` and `pool_costs_v1.json`;
  - the decompressed `meta.json`, `unknown_keys.json` and `pons_fee_terms.json`;
  - the realism tables (`pool_costs.json`, `pool_fees.json`, `v23_costs.json`, `tax_table.json`, `ethusd.json`, `latency.json`);
  - `pons_launches*.json` and `m2b_rows.json`;
  - `analyze_xg.py`.
- **The tape:** the decompressed content of every day equals the content hash in our engine-v1 manifest.
  - 33 of the 38 files are our original `.gz` files.
  - The other 5 (V2/V3 days 09-16, 09-20, 09-23, 09-24, 09-26) were plain files on our side and were gzipped with `gzip -n`. The bytes after decompression are identical.

## (a) Paths: where a file is found
Our code used absolute paths of our machine:
- `<origin>/projects/patches/...` for code and tables;
- `<origin>/<workspace>/wick-engine/logs/archive/2026-09/tape-DAY.ndjson.gz` for the V2/V3 tape.

The kit keeps the same relative layout under `$KIT_ROOT`:
- `patches/...` for code and tables;
- `tape/v23/archive/2026-09/` for the V2/V3 tape;
- `patches/v4-join-2026-09-27/out/` for the V4 tape.

**Node: the preload `kit/kitpath.js`.** It is loaded through `NODE_OPTIONS=--require`, which `run_batch.sh` sets.
- It rewrites those two path prefixes to `$KIT_ROOT` in module resolution and in `fs.readFileSync / existsSync / readdirSync / statSync / createReadStream / openSync`.
- It only changes which file name is opened, and the file opened holds the same bytes. It does not touch a value, a row, an order or a random seed.
- It is why `engine_v1.js` can stay byte-identical.

**Python and shell: single-line edits.** Each is an exact whole-line replacement that matched exactly once, listed in `kit/PATCHES.json` with its reason:

| file | original line | kit line |
|---|---|---|
| `engine/reduce_v1.py`, `analyze_v1.py`, `pool_costs_v1.py` | `... P = '<origin>/projects/patches'` | `... P = os.environ['KIT_ROOT'] + '/patches'` |
| `engine/hop.py` | `P = '<origin>/projects/patches'` | same, from `KIT_ROOT` |
| `engine/build_hop_v1.py` | `J = '<origin>/.../v4-join-2026-09-27/out'` | `J = os.environ['KIT_ROOT'] + '/patches/v4-join-2026-09-27/out'` |
| `blood-realcost-2026-09-27/recost.py` | `P = '<origin>/...'; SP = '<an origin scratch folder>'` | `P` from `KIT_ROOT`; `SP` = a placeholder string. `reduce_v1.py` / `analyze_v1.py` execute only the part of `recost.py` above its `# --- loaders` marker, and `SP` is used only below it. |
| `realism-2026-09-27/realism.py` | a path in its docstring's usage example | the same example with `KIT_ROOT` (docstring: not executed) |
| `engine/parity/parity_table.py` | `P = '<origin>/...'` | `P` from `KIT_ROOT` (report helper) |
| `engine/test_seal.sh` | `require('<origin>/.../v4tape.js')` | `require(process.env.KIT_ROOT+'/patches/v4-join-2026-09-27/v4tape.js')` |
| `engine/run_batch.sh`, `engine/test_seal.sh` | `set -u` / the first variable line | the same line, plus: require `KIT_ROOT`, export it and `NODE_OPTIONS=--require kit/kitpath.js` |

All of these change only which file is opened or how the environment is wired. None changes a computation, and the parity run proves the result.

## (b) The resource gate
In `engine/a4.sh`, the origin read a live-feed status file on our machine (`ST=<origin>/.../status.json`). The kit reads `ST=${A4_STATUS_FILE:-/nonexistent}`, and a missing file passes the check, exactly as on the origin when that file is absent. The gate only decides **when** a step starts.

## (c) Manifest machinery (rewritten, not line-edited)
- **`engine/manifest_lib.py` and `engine/verify_manifest.py`** were rewritten for the kit layout.
  - The same four groups are checked: code, inputs, external and data. Paths are relative to `$KIT_ROOT`.
  - Each data file is checked by its file sha256, cached by size + mtime. `--content` also re-hashes the decompressed tape against our original content hashes.
  - `verify_manifest.py` also refuses if the engine would read any extra or missing day file.
  - Neither file is read by the engine or the analysis, except that `analyze_v1.py` copies the manifest's `engine_sha256`, `cost_version`, `manifest_sha256` and `data_window` into `results.json`.
- **`engine/MANIFEST.json` is the kit's own manifest.**
  - It carries **our labels unchanged**: `engine_sha256 d1f23fed…` and `cost_version v1-real60h-bc18611a45a4`. That way results from the kit and from our copy are labelled the same.
  - It also records our manifest's sha256 (`origin_manifest_sha256`).
  - Only `results.json`'s top-level `manifest_sha256` differs between a kit run and ours. No cell record and no trade row contains it.
- **`make_manifest.py` is not shipped.** It writes our layout's manifest. A new engine version is ours to register.
- **New files, kit only:** `kit/kitpath.js`, `setup.sh`, `seal_scan.py`, `unpatch_check.py`, `parity_check.py`, `validate_return.py`, `log_look.py`, `TAPE_MANIFEST.sha256`, `META_JSON.sha256`, and `protections/eq_view.py`.

## Docs
`engine/parity/PARITY.md` and `parity_table.json`: our temporary-folder paths were replaced by `<origin-scratch>`. The numbers are unchanged.

## (d) The optional hunter
- **Line edits:**
  - `search.py`, `screen.py` and `loader_v1.py` read `P` from `KIT_ROOT`.
  - `loader_v1.py` resolves batch folders in its ledger relative to its own folder.
  - `machine.sh` requires `KIT_ROOT` and has no default notification config: set `EM_TG_ENV` to your own `.env` to get one line per changed round.
  - `hunter.sh` rebuilds an explorer only if you set `EM_EXPLORER_DIR` to your own one.
- **Data:**
  - `edge-explorer/data.json`: the 21 paper-trading runs (`blood.dyor`, run on days at or after the seal) and their summary (`blood.seat_sum`) were removed. Nothing else was changed.
  - `trades/index.json`, `unrecoverable.json` and `must_test.json`: our absolute file paths in the informational `src` fields were shortened (`patches/...`, `origin-scratch:...`).
  - `machine/v1_ledger.json` lists our four engine-v1 batches with folders relative to `machine/v1_batches/`. Each folder holds that batch's `results.json` and `trades.ndjson.gz`.
- **Not shipped:**
  - `store.py` and `srcmap.py`, which rebuild the trade store from our temporary engine outputs. The store itself (`trades/`) is shipped.
- `SEARCH.md` and `DESIGN.md`: they describe our infrastructure. The method is documented in `search.py`'s and `screen.py`'s own headers.
  - Our explorer (`build.py`) and the test files.
