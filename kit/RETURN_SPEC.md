# Returning results

Nothing you send is published until we have re-run part of it here and got the same numbers.

## What to send, per batch
From each `run_batch.sh` output folder, send:
- `results.json`
- `trades.ndjson.gz`
- `cells.input.json`
- `cellmap.json`
- `MANIFEST.used.json`
- `runlogs/batch.log`

Leave out the large intermediates (`p*.ndjson.gz`, `p*.pkl`, `in/`, `hop/`, `pool_costs.json`). We rebuild them.

## What to send, once per delivery
- `$KIT_ROOT/LOOKS.ndjson`, written by `python3 kit/log_look.py <outdir>` after **every** batch. That includes smoke runs, failed runs and the cells you did not like.
- Every cell you ran counts toward the multiple-testing family. A result reported without its looks log cannot be weighed.
- If you used your own search or your own engine, describe it in a few lines and say how many cells it ran. A result from a different engine is reported as a different engine, never as v1.

## How we check it
We run `python3 kit/validate_return.py <batch folder> --sample K`. It works in two stages.

**Stage 1 covers every cell:**
- The batch must be frozen engine v1 with cost model `v1-real60h-bc18611a45a4`.
- The seal must be present in the data window, and no trade row may have a time at or after 2026-09-27T00:00:00Z.
- Every cell must be accounted for.
- n, coins and the mean recomputed from `trades.ndjson.gz` must equal `results.json`.

**Stage 2 covers a seeded random sample of K cells.** A filtered cell brings its base cell along. We re-run the sample here and require two things:
- Each cell's `results.json` record is identical.
- Its trade rows are identical byte for byte.

A batch that fails either stage is rejected as a whole, and we tell you which cell differed.

## What we report back
- The verdict.
- If accepted, the cell's numbers, labelled with your name, the engine (`v1`) and the family size from your looks log.
