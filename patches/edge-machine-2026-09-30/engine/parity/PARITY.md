# PARITY — engine v1 reproduces the published numbers (2026-09-30)

Engine `engine_v1.js` sha256 `d1f23fed4ba60bc02eb27d5b2114a63b04015cb9c0ce252ee3efd9005de9db1c` · cost version `v1-real60h-bc18611a45a4` ·
MANIFEST sha256 `2f45130ff8a6c8be…`. One clean `run_batch.sh` run (01:48Z → 02:26Z), ONE engine pass of the 6 engine cells; the 6 token-filter
cells are splits of the 3 hunt-2 cells (no extra engine work). Rule: n equal · |Δmean| ≤ 0.05 · |Δlower| ≤ 0.3. JUDGE half. `lower` = the
95 % range's lower end (`ci95[0]`, what the explorer draws as `raw_ci`). Each cell uses its source batch's own bootstrap seed
(`stat_seed` = 20260927 + 100 × its index in that batch's cells.json), so the ranges reproduce exactly rather than within noise.

| cell | source · view | published n / mean / lower | v1 n / mean / lower | Δmean / Δlower | verdict | v1 hop-costed (real60h) |
|---|---|---|---|---|---|---|
| D25H72T40X12 (25 %·every h·LOW·TP+40·12 h) | hunt 2 · real60h | 63 / 12.05 / 4.38 | 63 / 12.05 / 4.38 | 0 / 0 | **PASS** | (same view) |
| D27.5H72T40X12 | hunt 2 · real60h | 46 / 13.71 / 4.12 | 46 / 13.71 / 4.12 | 0 / 0 | **PASS** | (same view) |
| D30H72T50X12 | hunt 2 · real60h | 36 / 17.57 / 1.41 | 36 / 17.57 / 1.41 | 0 / 0 | **PASS** | (same view) |
| D25H72T50X12QW (WETH-quoted only) | hunt 3 · real60, hop OFF | 34 / 19.56 / 6.41 | 34 / 19.56 / 6.41 | 0 / 0 | **PASS** | n 34 / 19.56 / 6.41 (no hop trades) |
| D25H72T30X12L300 (entry delay 300 s) | hunt 3 · real60, hop OFF | 64 / 8.61 / 2.26 | 64 / 8.61 / 2.26 | 0 / 0 | **PASS** | n 64 / **7.66 / 1.36** |
| D30H72T50X12C20 (cap 20) | hunt 3 · real60, hop OFF | 36 / 19.09 / 2.08 | 36 / 19.09 / 2.08 | 0 / 0 | **PASS** | n 36 / **17.57 / 1.47** |
| D25H72T40X12_F1 (slow dip ≥ 20 min) | token filter · real60h | 54 / 12.97 / 4.87 | 54 / 12.97 / 4.87 | 0 / 0 | **PASS** | (same view) |
| D25H72T40X12_F2 (≥ 10 sell swaps) | token filter · real60h | 55 / 11.63 / 2.48 | 55 / 11.63 / 2.48 | 0 / 0 | **PASS** | (same view) |
| D27.5H72T40X12_F1 | token filter · real60h | 37 / 15.84 / 5.21 | 37 / 15.84 / 5.21 | 0 / 0 | **PASS** | (same view) |
| D27.5H72T40X12_F2 | token filter · real60h | 41 / 13.54 / 3.09 | 41 / 13.54 / 3.09 | 0 / 0 | **PASS** | (same view) |
| D30H72T50X12_F1 | token filter · real60h | 26 / 26.09 / 9.26 | 26 / 26.09 / 9.26 | 0 / 0 | **PASS** | (same view) |
| D30H72T50X12_F2 | token filter · real60h | 32 / 20.66 / 4.98 | 32 / 20.66 / 4.98 | 0 / 0 | **PASS** | (same view) |

Also identical (not required): drop-5-coins, d vs the activity twin and its range (e.g. D25H72T40X12 +15.30 [6.56, 24.04], drop-5-coins +4.60).
**Row level, not only summaries:** every engine row and latency probe of the parity cells equals the parents' own engine output, field by
field (multiset; `u`/`pair` counters replaced by the signal key; fields the parent does not write — `tf`, `eQ` — dropped for that parent only):
hunt 2 `p1.ndjson.gz` (40-cell pass) 873/873 rows, 3,492/3,492 probes · hunt 3 `p1.ndjson.gz` (36-cell pass) 819/819, 3,276/3,276 (incl. `eQ`) ·
token-filter `base.ndjson.gz` (3-cell pass) 873/873, 3,492/3,492 (incl. every `tf` feature). ⇒ a cell's rows do not depend on its pass-mates.
Hop tables rebuilt by the batch: 370 pools of 8 quote tokens, array-identical to hunt 2's for every pool.

**Hunt 3 with the hop ON (R-0115):** the any-quote cells fall by ~1–1.5 (L300 8.61 → 7.66, lower 2.26 → 1.36; C20 19.09 → 17.57, lower 2.08 → 1.47);
the WETH-only cell is unchanged (no quote hop). Hunt 3's published figures remain un-hop-costed; the v1 number is the real60h one.

**What this parity does NOT exercise:** the cap never bound (peak 7 open positions < 20, as hunt 3 found), so the cap-SKIP branch ran zero
times; the quote-skip branch did run (3,157 skips). Only mode P / W 3600 / LOW-band cells were reproduced.
**Timing note:** v1's first (pre-final) run computed the filtered numbers ~01:43Z, ~6 min before the token-filter batch wrote its own
results (01:49Z); they stayed in my scratchpad, were not shared, and that batch's thresholds were hashed in its PREREG hours earlier.

## Runtime (this box, under the A4 gate)
| step | wall | peak RSS |
|---|---|---|
| engine pass p01 (6 cells, 36.0 M rows) | 4:08 (first run 4:22) | 2.85 GB (/usr/bin/time) · 2.92 GB (engine's own sample) — guard 3.2 GB |
| hop tables (zcat + grep of 19 V4 days) | ~1–4 min, IO-bound | < 1 GB |
| cost table · reduce · analyze | < 1 min each (reduce 0.8 s, 195 MB) | < 0.3 GB |
| whole batch incl. A4 waits | 38:11 (21 min of it waiting for memory / the :49–:05 heater window) | |
⚠️ v1's pass sits ~100 MB above the parents' (tf ring always on): a 40-cell pass may approach the 3.2 GB guard — use `pass_size` ≤ 20 until measured.

## Reproduce (from `engine/`)
```
python3 verify_manifest.py && bash test_seal.sh                               # manifest OK, 6/6 seal + dial refusals
bash run_batch.sh parity/cells_parity.json <OUT>                              # the whole pipeline -> <OUT>/results.json
OLD=<origin-scratch>; TFO=<origin-scratch>/tf
python3 parity/compare_rows_v1.py <OUT>/p01.ndjson.gz $OLD/h2/p1.ndjson.gz D25H72T40X12 D27.5H72T40X12 D30H72T50X12 > parity/rows_vs_hunt2.json
python3 parity/compare_rows_v1.py <OUT>/p01.ndjson.gz $OLD/h3/p1.ndjson.gz D25H72T50X12QW D25H72T30X12L300 D30H72T50X12C20 > parity/rows_vs_hunt3.json
python3 parity/compare_rows_v1.py <OUT>/p01.ndjson.gz $TFO/base.ndjson.gz D25H72T40X12 D27.5H72T40X12 D30H72T50X12 > parity/rows_vs_tokenfilter.json
python3 parity/parity_table.py <OUT>/results.json parity/rows_vs_*.json          # this table (published = each batch's results_raw.json)
```
This run's `<OUT>` = `<origin-scratch>/ev1/parity_final` (scratch; the
parents' engine outputs above are in other sessions' /tmp scratchpads and will age out). Kept here: `results_v1_parity.json`,
`trades_v1_parity.ndjson.gz` (546 trade rows, JUDGE + FIT), `rows_vs_*.json`, `parity_table.json`.
