# edge-hunt-kit — run the Blood edge backtests yourself

This kit lets you run our **frozen backtest engine v1** on the Robinhood Chain swap tape for **2026-09-08 .. 2026-09-26**. It contains:
- the engine's cost model and input tables;
- the protections (scam list, bad-print guard, per-pool costs, transfer taxes);
- a parity set that proves your copy gives our published numbers row for row;
- an optional automated hunter;
- the return path for sending results back.

The kit needs no keys, wallets, RPC or network access, except one download of the tape.

## ⚠️ Treat everything here as untrusted
- **Check every download against a manifest.**
  - Check the tape against `kit/TAPE_MANIFEST.sha256`. `kit/setup.sh` refuses to continue on a mismatch.
  - Compare that file, and this repository's commit, with the manifest we posted on the forum.
- **Read the code before you run it.** It is plain Node.js, Python and bash. `kit/CHANGES.md` lists every line that differs from what we run.
- **Run it in a sandbox:** a container or VM with no credentials in its environment. Nothing in the kit needs a secret, and nothing in it should ever see one.

## Requirements
| item | need |
|---|---|
| software | Node.js ≥ 18 (we use 22), Python ≥ 3.10 with `numpy`, `zstd`, `curl`, `gzip`/`zcat`, `grep`, GNU `time` (`/usr/bin/time`) |
| disk | about 4 GB for the tape, plus about 2 GB of temporary files per batch |
| RAM | **about 3 GB per engine pass**: the engine is capped at 2.4 GB of heap, and the guard stops it at 3.2 GB RSS |
| time | one pass reads 36 M rows; about 4–5 min here for a 6-cell pass |

**Pass size.**
- Use **at most 20 cells per pass**: set `"pass_size": 20` in `cells.json`. A 40-cell pass can reach the 3.2 GB guard.
- Run **one engine pass at a time**. `a4.sh` waits until no other `engine_*.js` is running.

**Resource gate.** `a4.sh` waits before each heavy step and never kills anything. It checks:
- free memory > 3 GB + the pass's need;
- load < 8;
- swap not rising;
- no other engine running;
- minute of the hour between :06 and :48. This rule protects a job on our machine; on yours it only adds waiting, and you may relax it locally (it does not change any number).

## Quick start
```bash
git clone <this repo> edge-hunt-kit && cd edge-hunt-kit
export KIT_ROOT=$PWD
bash kit/setup.sh --scan        # download + sha256-check the tape, unpack the pool table, scan every row for the seal,
                                # prove the code differs from ours only in the lines kit/PATCHES.json lists, verify the manifest,
                                # run the seal self-tests
bash patches/edge-machine-2026-09-30/engine/run_batch.sh patches/edge-machine-2026-09-30/engine/parity/cells_parity.json runs/parity
python3 kit/parity_check.py runs/parity          # must print PARITY: 12 cells, 546 trade rows identical to ours
python3 kit/log_look.py runs/parity --note "parity"
```

## Data window and the seal
- **Tape:** 2026-09-08 .. 2026-09-26, as 19 V2/V3 day files and 19 V4 day files. That is 36,079,586 rows.
- **Assessments:**
  - **FIT** covers assessments from 2026-09-11 to 2026-09-17.
  - **JUDGE** covers 2026-09-17 to 2026-09-25 20:00, and is the primary half.
  - Both are already **spent**: we have read these days about 3,500 times. A v1 number is a map of where to look, not evidence.
- ⛔ **The seal is 2026-09-27T00:00:00Z (unix 1790467200).** Data from then on is reserved for pre-registered exams:
  - **Block A:** 09-27 → 10-07.
  - **Block B:** 10-07 → 10-21.
  - **Block C:** 10-21 → 11-04.
  - Each block is read once, by its exam, and released only after that exam has run.
- **What that means for you:**
  - Do not collect, read or study any data from on or after 2026-09-27 until the relevant exam has run.
  - There is no updater in this kit. We keep the tape current and send newer blocks when they are released.
  - The engine, the reducer, the hop builder and the trade writer all refuse any row at or after the seal. Please keep those refusals in place. `bash patches/edge-machine-2026-09-30/engine/test_seal.sh` proves them (6 tests).
- **Post-seal metadata in the input tables (disclosed).**
  - Some frozen lookup tables were built on the morning of 2026-09-27. So `meta.json`, `inputs/poolfee_lf.tsv.gz` and `inputs/meta.tsv.gz` hold rows for 1,732 / 1,208 / 482 pools or tokens first seen 2026-09-27 00:00–06:22Z.
  - Those rows hold only identifiers and metadata: pool and token ids, fee, hook, venue, birth block and time. They hold no trades, prices or outcomes.
  - The engine never uses them, because no tape row is at or after the seal. They are kept so that the engine's inputs stay byte-identical to ours.
  - **Please do not use those post-seal rows for any research until Block A's exam has run.**
- **Coverage gaps.**
  - V2/V3 is missing 11–28 % of swaps per day on 09-07..09-15, and 0–6 % from 09-20.
  - V4 covers all pools only from 2026-09-18 22:40Z. Before that it covers a tracked set of pools.
  - The V2/V3 hour 2026-09-26 23:00–24:00 is in the sealed file and is not included.
  - See `protections/KNOWN_FAULTS.md`.

## Costs: a regular on-chain trader's, nothing else
The primary view `real60h` counts only what trading the coin forces on anyone:
- the pool's LP fee;
- for Pons launch pools, the launchpad hook fee plus the creator's own tax, read per pool on chain (R-0111: a 1 % hook fee plus 0–5 % creator tax per side, mean 2.39 % per side on Blood entry pools);
- per-coin transfer taxes;
- the ETH → quote-token hop on both legs, for pools quoted in USDG or a stock token;
- gas and price impact.

TP is sold 60 s after the trigger, at the price then, and everything is booked in ETH.

**No app, bot or platform fee of any product is included, ours included.** Please keep it that way, so results describe the market rather than one product's users.

## Running a batch
1. Write `cells.json`, for example:
   ```json
   {"cells":[{"id":"D25H72T40X12","params":{"dip":0.25,"th":72,"tp":1.4,"hold":43200,"band":"LOW"}}], "pass_size":20}
   ```
2. Run `bash patches/edge-machine-2026-09-30/engine/run_batch.sh cells.json runs/<name>`.
3. Run `python3 kit/log_look.py runs/<name>`. **Do this for every batch: every cell you run counts toward the multiple-testing family**, smoke and failed runs included.
4. Read `runs/<name>/results.json`, which reports per cell, JUDGE then FIT: n, coins, days, mean, median, 95 % range, `p_one_sided`, drop-5, the twin deltas, exit reasons and the gate.
5. Run `python3 protections/eq_view.py runs/<name>` and report the R-0119 `eq` view beside every result.

**Notes on cells and runs:**
- The dial list and its meaning are in `patches/edge-machine-2026-09-30/engine/README.md`. `prepare_v1.py` refuses unknown dials.
- A token filter is a *split* of a base cell: `{"id":"X_F1","base":"X","filter":{"min_dip_sec":1200}}`.
- `STOP_DAY=2026-09-12` runs a smoke test on fewer days. Its numbers are not comparable.
- A changed engine is a new version: `engine_v2.js` with a new manifest. `run_batch.sh` refuses to run if any pinned file changes (`verify_manifest.py`).
- Comparing two runs: the order of trade rows depends on which cells share a pass, and repeats differ in `passes[].sec` / `peakRssMB` and in the gzip header time of `trades.ndjson.gz`. Compare cell records and sorted, decompressed rows, as `kit/parity_check.py` does.

## Protections (what keeps a backtest honest)
| file | what it does |
|---|---|
| `engine/inputs/scam.tsv.gz` | 14,816 tokens refused at entry: launchpads whose contracts scored < 73 on our red-team check, and tokens flagged unsafe by a sellability cache |
| `engine/guard.js` + `guard_test.js` | bad-print guard: confirms a new price level instead of freezing a rugged coin at its pre-rug price (R-0105); the batch refuses to run unless the test passes |
| `engine/engine_v1.js` | sellability and fill realism: depth-aware V4 fills; V4 entries with < 0.001 ETH of depth skipped; > 20× rule on exits; drained-pool and dust rules; entry 60 s after the signal on the signal pool |
| `engine/pool_costs_v1.json`, `patches/realism-2026-09-27/*.json` | measured per-pool costs, V2/V3 cost floor, gas, latency, and the per-coin transfer-tax table |
| `patches/pons-feeterms-2026-09-27/pons_fee_terms.json` | hook fee and creator tax for all 8,909 Pons pools, read on chain (R-0111) |
| `engine/hop.py` | the ETH ↔ quote-token hop cost on both legs (R-0115) |
| `protections/KNOWN_FAULTS.md` | the corrections we registered that matter for Blood (R-0105 … R-0120), and which ones are still open |
| `protections/eq_view.py`, `R0119_EQ_VIEW.md` | the `eq` view: results without entries on pools quoted in "other" tokens |

## The hunter (optional)
`patches/edge-machine-2026-09-30/hunter.sh` is our automated search. It alternates two arms:
- **hunter**: a Gaussian-process / UCB pick of ≤ 20 cells per round over the explorer's dial grid (`search.py`);
- **random**: the same number of cells drawn uniformly from the same legal pool.

So a trial can be judged **hunter vs. random at equal passes**.

**How to run it:**
- Each round re-screens every measured point (`loader_v1.py screen` → `screen.py`), pre-registers its `cells.json` by sha256, runs `run_batch.sh`, and loads the results into the trade store.
- Run `EM_NO_TG=1 HUNT_HOURS=6 bash patches/edge-machine-2026-09-30/hunter.sh`, or `bash patches/edge-machine-2026-09-30/machine.sh --dry` for one round without the engine.
- Stop it with `touch patches/edge-machine-2026-09-30/machine/KILL`.

**Input data:**
- The explorer data `patches/edge-explorer/data.json`: 1,844 measured Blood points, all from the spent window.
- `must_test.json`.
- The per-trade store in `trades/`.
- Our four engine-v1 batches in `machine/v1_batches/`.
- Paper-trading runs on sealed days were removed from `data.json`.

**You are encouraged to build your own search strategy as well.** Variety is the point, because a second, differently-built hunter tells us more than a copy of ours. Whatever you use, run it against its own random baseline at an equal number of passes, and log every cell it runs.

## Returning results
See `kit/RETURN_SPEC.md`. In short:
- Send each batch's `results.json`, `trades.ndjson.gz`, `cells.input.json`, `cellmap.json`, `MANIFEST.used.json` and `runlogs/batch.log`, plus your `LOOKS.ndjson`.
- We run `kit/validate_return.py`. Stage 1 checks every cell: integrity, which engine file ran (from `runlogs/batch.log`), and that each cell's n, coins and means, twin deltas included, follow from your trade rows.
- Stage 2 re-runs a seeded sample here, which must reproduce each sampled cell's **own** result exactly. The twins can be drawn differently when other cells share the pass, so they are compared only by the optional `--full-pass` mode, which re-runs the sampled cells' whole original passes.
- Nothing is published before that.

## What differs from the copy we run
- `engine_v1.js` (sha256 `d1f23fed…`) is **byte-identical** to ours, and so are all frozen input tables, `guard.js`, `qpools.js`, `prepare_v1.py` and the tape content.
- Our scripts used absolute paths of our machine. Those are rewritten to `$KIT_ROOT`:
  - for Node, by a preload (`kit/kitpath.js`) that rewrites the two path prefixes before any file is opened;
  - for Python and shell, by single-line edits.
- Two pipeline files also carry lines that only make a failure loud or record what ran, and cannot move a number. `build_hop_v1.py` stops on a failed `zcat` / `grep` / `gzip` child instead of hanging or writing short tables. `run_batch.sh` logs the sha256 of the engine file each pass runs.
- `kit/unpatch_check.py` reverses every edit and shows the result is byte-identical to our file.
- Full list and reasoning: `kit/CHANGES.md`.
