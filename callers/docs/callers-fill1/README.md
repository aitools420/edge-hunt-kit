# Callers fill batch 1 (2026-09-30, owner request)

Fills the explorer's Callers must-test queue (77 items) with measured cells. Same engine, data, bands, rules and statistics as
`patches/callers-dials-2026-09-30`; only new settings are added (PREREG.md). **4th read of these days: LEADS at most, never an edge.**

## Two passes of the same pre-registration (Amendments 1–2 in PREREG.md)
- **Pass A** (this folder): the registered data — V4 backfill 07-20 → 09-04 (47 days), the frozen call set (5,659 rows). Reproduces the
  dial test exactly at its settings (`check_repro.py`: 0 differing rows). `results.json` here; grid points the dial test already read are
  ALIAS records pointing at the dial test.
- **Pass B** (`passB/`): same cells, scripts, bands and seeds + backfill days 09-05 → 09-11 (54 days) + 22 recovered calls
  (`passB/build_snapshot_B.py`, `map_pools.py`, `pool_map.json`; 5,673 rows). `passB/results.json`; here the dial test's grid points are
  COMPUTED (flag `dialtestPoint: true`, they are re-reads, not new K), so every slice is complete in one file.
  **For the explorer, load `passB/results.json`** (more data, complete grids); pass A is the strict-prereg record.
- `void_dataend/`: two runs voided by the Amendment 2 wrapper bug (DATA_END), kept unopened.

## Files
| file | what |
|---|---|
| `PREREG.md`, `PREREG.sha256` | the pre-registration and the hashes recorded before any pass (+ appended amendments, if any) |
| `cells.json` | the pre-registered cell list (652 cells + alias labels), built by `make_cells.py` from `must_test.json` |
| `engine.py`, `analyze.py`, `guard.py` | the dial test's files, byte-identical (sha256 in PREREG.sha256) |
| `engine_fill.py` | runs `engine.py` with four constant lines replaced (delays, holds, take profit, output tag); no logic change |
| `analyze_fill.py` | exec()s `analyze.py`'s statistics block verbatim; per-cell records → `analysis_fill.json`, `results.json` |
| `check_repro.py` | STOP check: the +50 % pass reproduces the dial test's positions and dial file exactly |
| `summarize.py` | prints the per-dial / per-slice numbers behind `report.txt` |
| `rows_tp{25,50,100,none}.ndjson`, `dials_tp*.ndjson`, `engine_meta_tp*.json` | engine outputs, one pass per take-profit |
| `report.txt`, `RERUN.md` | the report (both passes); how to re-run once the V4 backfill reaches 09-18 |
| `run_A.sh`, `passB/run_B.sh` | the drivers (A4 gate before every heavy step, two engine runs at a time) |

## results.json — record schema (for the explorer builder)
`records` is a list; every record has EXACTLY the dial test's fields (n, coins, callers, days, mean, ci95, median, se, seUsed, d,
d_ci95, d_se, drop5, hitShare, tpShare, zeroCostMean, coverage, norep, exOutage, era, lane, exG5{…}, canTell, lead, leadD, leadNote)
plus these keys:

| key | meaning |
|---|---|
| `dial` | `"hold"`, `"tp"`, `"delay"`, `"tier"`, `"src"` for a 1-D cell; `"hold×mcap"` / `"hold×runup"` for the dial test's crosses (pushed to the new holds); `"<x>×<y>"` for a 2-D slice or corner, in the queue's x × y order (e.g. `"mcap×age"`, `"hold×tp"`, `"delay×hold"`, `"tier×src"`) |
| `level` | 1-D: the dial's level. 2-D `x×y`: **x's level**. `hold×mcap` / `hold×runup`: the band / run-up level (the dial test's format — the hold is in `hold`) |
| `level2` | 2-D `x×y` only: **y's level** (absent on 1-D and on `hold×mcap` / `hold×runup`) |
| `hold` | the hold the cell was booked at, ALWAYS present: `5 min · 7.5 min · 15 min · 1 h · 4 h · 12 h · 24 h · 72 h · 5 d · 7 d` |
| `tp` | take profit, ALWAYS present: `+25% · +50% · +100% · none` |
| `delay` | entry delay after the post, ALWAYS present: `1 min · 5 min · 15 min · 60 min` |
| `group` | `1-D · cross-ext · slice · corner` |
| `cell`, `filters` | cell number in `cells.json`; the row filters applied (`{"mcap": ">$1M", "src": "CallAnalyser"}` …) |
| `coverage.pending` | filled calls whose hold would need data past the source's coverage end (DATA_END or the backfill run end): counted, not booked |
| `alias`, `aliasOf` | ALIAS records only: a grid point already read — `aliasOf.study = "callers-dials-2026-09-30"` (+ its dial/level/hold) or `"callers-fill1-2026-09-30"` (+ `cell`). Numbers are copied from that record; aliases are NOT in K |

Level names: mcap `<$50k · $50k–$100k · $100k–$250k · $250k–$1M · >$1M`; runup `<0 · 0–50% · 50–200% · >200% · no print in the hour`;
first `first · follower ≤5 min · follower 5–30 min · follower 30–180 min · follower 3–24 h · follower >24 h`; ncallers `1 · 2 · 3+`;
age `<1 h · 1–6 h · 6–24 h · 1–7 d · >7 d`; tier `elite · good · other`; src `direct · CallAnalyser`.
Explorer → key map: Hold=hold, Take profit=tp, Delay after the call=delay, Market cap at the call=mcap, Run-up in the hour before the
call=runup, First caller or follower=first, Callers by our entry=ncallers, Coin age at the call=age, Caller tier=tier (Other=`other`),
Call source=src (CallAnalyser repost=`CallAnalyser`, Direct group post=`direct`).
Headline view = `exG5` (Amendment 3 of the dial test: positions booked > +1,900 % removed); the raw view is the top-level fields.
`coverage` (top level) = priced share per take-profit, per delay, per era at 1 h / 72 h / 7 d, with pending counts; besides the three
registered eras it has two coverage-only eras, `coverage-era 09-05→09-12 (backfill days 09-05..09-11)` and `coverage-era 09-12→09-18 22:40`.
Top-level `pass_label` says which pass a file is.
