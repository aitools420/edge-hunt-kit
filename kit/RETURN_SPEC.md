# Returning results

Nothing you send is published until we have re-run part of it here and got the same numbers.

## What to send, per batch
From each `run_batch.sh` output folder, send:
- `results.json`
- `trades.ndjson.gz`
- `cells.input.json`
- `cellmap.json`
- `MANIFEST.used.json`
- `runlogs/batch.log` (required: from the kit of 2026-10-05 on, it records the sha256 of the engine file each pass ran with)

Leave out the large intermediates (`p*.ndjson.gz`, `p*.pkl`, `in/`, `hop/`, `pool_costs.json`). We rebuild them.

## What to send, once per delivery
- `$KIT_ROOT/LOOKS.ndjson`, written by `python3 kit/log_look.py <outdir>` after **every** batch. That includes smoke runs, failed runs and the cells you did not like.
- Every cell you ran counts toward the multiple-testing family. A result reported without its looks log cannot be weighed.
- If you used your own search or your own engine, describe it in a few lines and say how many cells it ran. A result from a different engine is reported as a different engine, never as v1.

## How we check it
We run `python3 kit/validate_return.py <batch folder> --sample K`. It works in two stages.

**Stage 1 covers every cell:**
- The batch must be frozen engine v1 with cost model `v1-real60h-bc18611a45a4`.
- The engine that actually ran must be the frozen one. The `engine_sha256` in `results.json` is only a label that `analyze_v1.py` copies from `MANIFEST.json`, so we also require that every engine pass is labelled `v1` by the engine itself and that `runlogs/batch.log` records, for every pass, the sha256 of the frozen `engine_v1.js`. A batch log from a kit older than 2026-10-05 has no such hash and is refused: re-run with the current kit.
- The seal must be present in the data window, and no trade row may have a time at or after 2026-09-27T00:00:00Z.
- Every cell must be accounted for.
- n, coins and the mean recomputed from `trades.ndjson.gz` must equal `results.json`.
- The same holds for the twin deltas `real60h` `d_vs_A` and `d_vs_R`: n, coins, `d_mean` and `twin_mean`, recomputed from `ret` minus `twinA` / `twinR` in the trade rows. This checks consistency only. It does not show that the twins were drawn honestly, and `real60` `d_vs_A` is not checked, because the rows carry no `real60` twin value.

**Stage 2 covers a seeded random sample of K cells.** A filtered cell brings its base cell along. We re-run the sample here, on its own.
- The random and activity twins can come out differently when different cells share the engine pass (pond-reviewer, forum posts #284 and #298), so a re-run of a few cells can draw different twins. Stage 2 therefore compares each sampled cell's **own** result.
- **Trade rows:** identical once `pair`, `twinA` and `twinR` are removed and the rows are sorted.
- **`results.json` record:** identical once the twin-derived parts are removed: every `d_vs_*` block, the gate's `WR` and `WA` entries, and its `G5` and `G10` statuses (G5 reads the twins' `g5_fail`, G10 reads only the twins). The gate's `S` entry, its `g5_fail` included, and `G1` / `G4` are still compared.
- So in this mode the twin draws themselves are **not** re-verified.

**Optional, stronger: `--full-pass`.** We re-run each sampled cell's whole original pass: the same cells in the same composition, rebuilt the way `prepare_v1.py` splits your `cells.input.json`. Then every cell of those passes must be identical in full, twins, gate and `pair` included. It costs one engine pass (about one tape read) for each distinct pass in the sample.

A batch that fails either stage is rejected as a whole, and we tell you which cell differed.

## Comparing two runs yourself
- The order of trade rows depends on which cells share a pass: positions that leave at the same time can come out in a different order. Sort the rows before comparing them.
- Two runs of the same batch also differ in `results.json`'s `passes[].sec` and `peakRssMB`, and in the gzip header time of `trades.ndjson.gz`. Compare the cell records and the decompressed, sorted rows, as `kit/parity_check.py` does.

## What we report back
- The verdict.
- If accepted, the cell's numbers, labelled with your name, the engine (`v1`) and the family size from your looks log.
