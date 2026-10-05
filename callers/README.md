# callers-kit — replay our Callers backtests

## What the Callers strategy is
- **The trade.** On Robinhood Chain, Telegram callers post the contract address of a coin they recommend. The Callers backtest **buys that coin a set delay after the post** (5 s, 15 s, 30 s or 1 min; pass B also tried 5, 15 and 60 min) with a $50 clip. It sells at a take-profit (+25 % … +200 %, or none) or at the end of a hold (75 s … 11 d), on the same pool it bought on.
- **The comparison.** Every call is compared with **3 random "twin" coins** of the same age and activity band, bought at the same moment, with the same exits and costs. `d` = call minus twins.
- **Which calls count.** Only the first call of a coin per caller is credited: 5,673 study rows out of 6,740 call events.
- **The entry price.** The entry is the **first accepted print of the coin at or after post + delay**. If that print is not within 300 s, there is no fill. Nothing after the fill print decides the entry.
- **Costs.**
  - The engine's own numbers ("OLD cost", the explorer's) use a 1 % fee per side on V2/V3, the pool's fee on V4, and 0.2 % gas.
  - `costs.py` re-costs the same trades at **real per-pool cost**: LP fee, Pons hook fee plus creator tax (R-0111), Doppler take, transfer tax, ETH↔quote hop (R-0115), measured V2/V3 fee and impact, and measured gas.
  - **No app or bot fee of any product is included, ours included.**
- **Status: explore days only.** The 07-08 → 09-26 window has been read five times. Every number here is a lead, not evidence of an edge.

## Names are included as-is
- Caller and group names are published **unchanged**, as they are in our call list (owner's decision, 2026-10-05). The kit carries no free-text message content.
- Each call says where we read it:
  - `source_type: "repost"` / `public_source: true`: the call was reposted by the public aggregator channel `CallAnalyserRobinhood`. In the engine's tables (`levels.json`, `results*.json`) this lane is labelled `CallAnalyser`.
  - `source_type: "group"` / `public_source: false`: a direct post in a group, read by our bot. Lane `direct` in the engine's tables.

## Data window and the seal
- **Calls:** 2026-07-08 08:26Z → 2026-09-26 23:29Z. The engine's data end is **2026-09-26 23:00:49Z** (`DATA_END` = 1790463649, the last row of `tape-2026-09-26`). Earlier versions of this README, the comment in `engine/engine_fast.py`, `docs/callers-fast/PREREG.md` and `docs/callers-fill1/PREREG.md` label it "21:40:49Z": that label is wrong, the number the code uses is right (see `CHANGES.md`, Corrections). A position whose hold runs past it is booked `"oow"` (out of window), never guessed.
- ⛔ **Nothing at or after 2026-09-27T00:00:00Z (unix 1790467200) is in this kit or may be read by it.**
  - Every row of `calls.ndjson.gz` and `engine/calls_snapshot.json` is before the seal (the build asserts it).
  - Pools and birth records at or after the seal were dropped from the input tables (see `CHANGES.md`).
  - The engine:
    - refuses `LAST_DAY >= 2026-09-27`;
    - drops any `tape-*` file named on or after 2026-09-27 without opening it;
    - reads V4 days through `v4tape.v4_path`, which refuses the sealed days;
    - raises on any tape row with `ts >= 1790467200`;
    - ignores any call at or after the seal.
  - Please keep these refusals in place. Data after the seal is reserved for pre-registered exams; see the edge-hunt-kit README.

## Files
| file | what it is |
|---|---|
| `calls.ndjson.gz` | one row per call event (6,742) — the field list is below |
| `engine/engine.py` | the Callers engine, **byte-identical** to ours (sha256 `311370c9…`) |
| `engine/engine_fast.py` | the wrapper we ran for results.json / results2.json: sets delays, holds and take-profits, and adds our six path edits to the text it `exec()`s |
| `engine/guard.py` | bad-print guard (R-0105), Python port of the edge kit's `guard.js` |
| `engine/v4tape.py` | V4 day reader. Its `out/` folder is set by `CALLERS_V4_OUT` |
| `engine/calls_snapshot.json` | the engine's input call list: `events` (6,740), `rows` (5,673 credited study rows), `credited`, plus counts |
| `engine/calledmeta.json` | token decimals per called coin, used by the price-at-call watcher |
| `engine/inputs/poolfee.tsv.gz` | per V4 pool: fee key, venue, token, birth ts (pass B's table) |
| `engine/inputs/births_min.ndjson.gz` | first-seen time per token (ages → twin matching, age bands) |
| `engine/inputs/newpools.json.gz` | V4 pool currencies, fee and hook, for the re-coster |
| `engine/costs.py`, `engine/hop_static.json` | real-cost re-coster, and its static ETH↔quote hop cost per quote token |
| `engine/analyze.py`, `engine/analyze_fast.py`, `engine/report.py` | per-cell statistics (`analyze.py`'s stats block is exec()d verbatim, sha asserted) → `analysis<1\|2>.json` → `results.json` / `results2.json` |
| `engine/cells.py`, `engine/cells1.json`, `engine/cells2.json` | the pre-registered cells of batch 1 (48) and batch 2 (151) |
| `engine/levels.json`, `engine/bands.json` | per study row: the dial levels (first caller / follower, age band, market-cap band, lane …) and the market-cap band edges |
| `results/callers-fast-2026-10-02/` | `results.json` (batch 1: fast entries), `results2.json` (batch 2), the two text reports, engine metas, and the smoke run's `dials_fast_smoke_r1.ndjson` |
| `results/callers-fill1-2026-09-30-passB/` | pass B `results.json` and `cells.json`, plus `ref_rows_d60_tp50.ndjson.gz`: the call and twin positions at the 1-min entry and TP +50 %, row by row, for parity |
| `docs/` | pre-registrations and feasibility notes of both studies, and the call-history spec and report. Every file registered by hash is unedited; three unregistered notes carry edited attribution lines (`CHANGES.md`, Corrections). `docs/callers-fast/FEASIBILITY.registered.md` is the FEASIBILITY.md text as first registered (sha256 `567dd65b…`); `FEASIBILITY.md` is the later version the FINAL block hashes |
| `run_kit.sh` | sets the paths and runs `engine_fast.py` |
| `CHANGES.md` | every line that differs from what we ran, and how each derived table was built |
| `MANIFEST.sha256` | sha256 of every file in the kit |

### `calls.ndjson.gz` fields
- **Identity:**
  - `id` — the call event id. It joins to `engine/calls_snapshot.json`, `levels.json` and every result row.
  - `ts` — the post's Telegram message time, unix seconds.
  - `ca` — the token address.
  - `chat`, `caller` — the names as stored in the call-history build.
  - `caller_engine` — the caller name as the engine reads it. Our normalised form strips emoji and brackets, so it differs on 2,614 rows. **The engine keys a caller's track record on this field.**
  - `mirrorOf` — the event id of the call this one mirrors (the 180 s cross-chat rule), else null.
  - `mirror`, `multi` — the engine's flags: a mirrored post, and a message naming several coins. Mirrored and multi-coin posts do not build a caller's track record.
- **Rank:**
  - `rankOnCa`, `callerRankOnCa` — the order of this call among all calls of the coin, and among this caller's calls of it.
  - `caInMsg` — the number of contract addresses in the message.
- **At the call** (from the call-history build; rows before the call only):
  - `pool` — the main pool over the call ± 24 h. `v23:<kind>:<quote>` or a V4 pool id.
  - `pool_kind`, `venue`, `pad`, `quote`.
  - `px_at_call` — the main pool's close at or before the call, USD, null if older than 30 min.
  - `flags` — data-coverage flags, defined in `docs/callhist/SPEC.md`. `quote_ref_jump` was removed, because it is derived from the 24 h peak, which is an outcome.
- **Membership:**
  - `in_callhist` — the row is in the call-history build. 73 engine events are not: that build's 24 h window had to end before the seal, plus 22 events were recovered later.
  - `engine_event` — the engine reads this call (6,740 events).
  - `engine_study_row` — the engine buys this call (5,673 credited rows).
  - `recovered` — on engine-only rows that were recovered from a pool address.
- **Source:** `source_type` (`repost` / `group`) and `public_source` (true for reposts). 3,448 rows are reposts and 3,294 are group posts.
- **Dropped as outcomes:** `race`, `peak24`, `t10x_mins`, `pace_cross_mins`, `main_vol_usd_48h`, `late`, `post_candles` and the `coord*` counts (±60 s / ±5 min windows reach past the call). **The engine reads none of these.** It reads only `id, ts, ca, caller, chat, mirror, multi` from `calls_snapshot.json`.

## How to run

### Requirements
- Python ≥ 3.10 with `orjson` and `numpy`, plus `pigz` and `gzip`.
- What our runs used (the runs did not log it; read from the machine's installs, all dated before the runs): CPython 3.12.3, orjson 3.11.7, numpy 2.4.4. `PYTHONHASHSEED` was not set.
- RAM: **about 1.5 GB** for a full pass of our complete data (41 min here). On the public tape alone, a 6-day pass took 0.4 GB and 42 s here.

### Steps
1. Set up the **edge-hunt-kit** first (`kit/setup.sh`). The Callers engine reads **its tape** and nothing else of it:
   - V2/V3 `tape/v23/archive/2026-09/tape-*.ndjson.gz`;
   - V4 `patches/v4-join-2026-09-27/out/v4-swaps-*.ndjson.gz`;
   - for the re-coster, its `patches/` tables (pool costs, Pons terms, realism, …).

   This kit does not copy the tape.
2. Run the engine:
   ```bash
   export EDGE_KIT_ROOT=/path/to/edge-hunt-kit
   FAST_TPS=1.5,1.25,2.0 FAST_TAG=r1 bash run_kit.sh          # batch-1 take-profits (+50/+25/+100) -> engine/rows_fast_r1.ndjson, dials_fast_r1.ndjson
   FAST_TPS=inf,2.5,3.0  FAST_TAG=r2 bash run_kit.sh          # batch-2 take-profits (none/+150/+200) -> engine/rows_fast_r2.ndjson
   FAST_TPS=1.5 FAST_DELAYS=60 FAST_TAG=t bash run_kit.sh 2026-09-13   # smaller "smoke" run: data to 09-13 only, outputs *_smoke_t*
   ```
3. Run the analysis:
   ```bash
   cd engine
   CALLERS_EDGE_PATCHES=$EDGE_KIT_ROOT/patches OMP_NUM_THREADS=1 python3 analyze_fast.py 1 && python3 report.py 1   # -> results.json
   CALLERS_EDGE_PATCHES=$EDGE_KIT_ROOT/patches OMP_NUM_THREADS=1 python3 analyze_fast.py 2 && python3 report.py 2   # -> results2.json
   ```
   Your files are written in `engine/`. Our published ones are in `results/`.
   - `analyze_fast.py` stops if the re-coster's OLD cost does not reproduce the engine's own booked number on every mark.
   - Its `bridge` block compares the cells that re-read pass B against `results/…passB/results.json`. On the public tape the bridge will **not** be identical (see the next section).

## ⚠️ What the public tape can and cannot reproduce
- **The public tape covers only 2026-09-08 → 09-26.** Our results read 07-08 → 09-26:
  - the V2/V3 tape from July;
  - a **V4 backfill** (every V4 pool, 07-20 → 09-11, about 15 GB) that has **not been released**.
- Only **1,068 of the 5,673 study rows (19 %)** are on or after 09-08, and 753 are on or after 09-12. ⇒ **`results.json`, `results2.json` and pass B cannot be reproduced number for number from the public tape.** A run on it is a new, smaller read of the 09-08 → 09-26 calls.
- **Row-level parity holds for calls from 09-12 on.** Compare against `results/…passB/ref_rows_d60_tp50.ndjson.gz` (key `d60_50` in your rows; hold index map: ours `(300, 450, 900, 3600, 14400, 43200, 86400, 259200, 432000, 604800)` inside the engine's 14 holds).
  - We ran the kit's engine on exactly the public tape files for 09-08 → 09-13; their sha256 matches `kit/TAPE_MANIFEST.sha256`.
  - Calls from 09-12 00:00Z, entry plus 6 min ending before the run's data end: **179 calls**.
    - The fill matches on all 179.
    - Entry, pool and price match on all 14 filled calls, and so do their twins.
    - **84 of 85 booked marks are identical.** The one difference is the run's own cut-off: per R-0109, the 23:00–24:00 hour of 09-13 is in `tape-2026-09-14`, which this run did not read.
- **What differs by construction when you start at 09-08:**
  - **`tier`, `score`, `nRec`** (a caller's track record, built only from that caller's earlier calls): 14 of those 179 calls differ, and so does any cell filtered by tier.
  - **Days 09-08 → 09-11:** our run used the backfill (every V4 pool) there, and the public tape has the tracked-pool set only. So V4 fills differ on those days. On 09-11, 58 of its 77 calls filled differently.
  - **State that carries over from earlier prints:** the bad-print guard window, the dynamic-fee estimate per pool, and the R-0114 lock-row detector. All of these start empty, so the first prints of a pool or token can be judged differently.

## Known limits (read before trusting any cell)
- **Repost timing lag.** A repost's time is the aggregator's repost, not the original call.
  - We read that channel from its public web page: ingest lag p50 82 s, p90 170 s.
  - So even the 1-min entry is not reachable live for reposts. The 15–30 s entries are reachable only for direct group posts (median ingest lag 1 s).
  - Reposts also come after the coin is already trading: 65 % have a print within 60 s, against 31 % for direct posts.
  - See `docs/callers-fast/FEASIBILITY.md`.
- **V2/V3 before 2026-09-08 is a sample:** about 14 % of each day (R-0098). It also drops 11–28 % of swaps a day on 09-07 → 09-15.
- **V4 coverage:**
  - every pool 07-20 → 09-11 (backfill; not in the public tape);
  - the **locked/tracked pool set only** 09-12 → 09-18 22:40Z, where a lock row can carry the wrong pool (R-0114; the engine's pre-registered detector drops suspects);
  - every pool after 09-18 22:40Z;
  - V4 swaps before 07-20 are not joined.

  A missing print can only make a fill later or absent, never earlier. Coverage at 1 h is about 56 % of calls (direct 38 %, reposts 68 %).
- **Prints:**
  - V2/V3 prints under $10 and V4 prints under $1 are ignored.
  - Exits more than 20× the entry need confirmation (or V4 depth).
  - A drop below 0.05× is a rug.
  - The headline view drops the 5 broken-price positions (`exG5`).
  - Small and drained-pool prints are still a known source of error (R-0105, R-0107).
- **Hop costs** are static medians per quote token (tables 08-17 → 09-26), not a route at each trade's moment (`docs/callers-fast/PREREG.md` §3).
- **Not included:**
  - the V4 backfill and the pre-09-08 V2/V3 tape (owner's call whether to release them as further tape releases);
  - the hop tables `hop_static.json` was built from (`*.pkl`, 3 files);
  - pass B's own `engine_fill.py` / `analyze_fill.py`. Pass B is reproduced by the fast engine's 1-min positions (row-identical, our `bridge_rows.py` check) and by the re-read cells in `analyze_fast.py`.
