# CALLERS FILL BATCH 1 — PRE-REGISTRATION (Chef TG 14949, 2026-09-30: "keep cooking on the callers data by backtesting anything that needs fill")

Written 2026-09-30 ~02:30Z, BEFORE any return in this folder was computed. Research only (AUTHORITY G12/G21/G23).
Writes only into `patches/callers-fill1-2026-09-30/`. sha256 of this file, `cells.json` and the scripts go into `PREREG.sha256`
before the smoke pass. Amendments are APPENDED below, dated, and never edit the text above them.

**Question.** Fill the explorer's Callers must-test queue (`must_test.json`, a copy of `edge-explorer/must_test.json`: 77 Callers
items — stage-1 sweeps and 2×2 corners, stage-2 2-D slices, stage-3 axis pushes) with measured cells, using the dial test's
engine and statistics UNCHANGED and only NEW SETTINGS added.
**Nothing found here is an edge.** Every day read here was already read by three studies (callers round 3, callers-v4, the callers
dial test of 2026-09-30); this is the FOURTH read of the same days. A good-looking cell is at most a LEAD for a later
pre-registered read on unseen data (`SEALED-HOLDOUT/README.md`).

## 0 · Known before writing (disclosed)
- I have read the dial test's `report.txt` in full: no LEAD in 144 cells; shorter holds less bad; calls worse than random coins from
  4 h on; direct-group calls ≈ 0, CallAnalyser reposts worse; coverage 48.5 % (era 09-05→09-18 at 7.5 %). I have also read the
  queue's per-item "best model / best measured" numbers. None of these numbers chooses a level below: every level comes from the
  queue or the brief, and every slice is a FULL grid of both dials' levels.
- I have NOT read any return by take-profit level, delay 5/60 min, hold < 15 min or > 72 h, caller tier or any 2-D combination
  other than the dial test's hold × mcap and hold × run-up crosses.
- Data on disk is the SAME as the dial test's: the V4 backfill join (`v4-backfill-join-2026-09-29/out`) still holds 47 days,
  2026-07-20 → 2026-09-04 (`coverage()` → `unbrokenToWide: false`). The backfill itself (`v4-backfill-2026-09-27/state.json`) is at
  cursor 61,351,699 of STOP_AT 66,590,240 (inside 2026-09-12, 02:12Z); raw days 09-05 → 09-11 exist in `~/noxabot/logs/archive/v4-wide/`
  but are NOT converted — converting is that folder's own step and is not run here (write-only-here rule). So coverage by era is
  expected to equal the dial test's.

## 1 · Engine — the dial test's `engine.py`, byte-identical (sha256 311370c9…), run through `engine_fill.py`
`engine_fill.py` reads `engine.py`, asserts its sha256, replaces exactly four constant lines (each asserted to occur once) and
exec()s it with this folder as its home. **No logic line changes.**
- `DELAYS = (60,)` → `(60, 300, 900, 3600)` — entry = first accepted print in [call + delay, call + delay + 5 min], else no fill
  (the engine's MAX_LAG window, unchanged). 15 min is included because it is a level of the explorer's delay dial (callers-v4
  measured it on the old ~15 %-coverage data) — without it the delay slices would skip a level of their own axis.
- `HOLDS` → `(300, 450, 900, 3600, 14400, 43200, 86400, 259200, 432000, 604800)` = 5 min, 7.5 min, 15 min, 1 h, 4 h, 12 h, 24 h,
  72 h, 5 d, 7 d. TP window = the hold (engine rule). The queue's 3.75-min push is replaced by 5 min, per the brief.
- `TP = 1.50` → one pass per take-profit: **1.25 (+25 %) · 1.50 (+50 %, held) · 2.00 (+100 %) · none (+inf: no take-profit, sold at
  the end of the hold or at the rug print)**. Four passes, each writing `rows_tp<x>.ndjson`, `dials_tp<x>.ndjson`, `engine_meta_tp<x>.json`.
- Everything else held exactly: all callers, $50 clip, the cost model (V4 pool LP fee incl. dynamic-fee inference + depth-aware
  impact + 0.2 pts gas; V2/V3 1 %/side + gas; hook/creator taxes NOT modelled, R-0111), cheapest-fresh-pool entry, the guard,
  drained-pool / >20× rule, <5 % rug exit, the twins (3 matched random coins, seed 20260927:<call id>, 12 candidates, same delay,
  same exits and costs), the union rule for V4 (backfill row wins on a shared key) and the pre-registered R-0114 lock-row detector.
- **Out-of-window = PENDING (brief: "counted, not booked").** A position is booked for hold H only if [entry, entry + H + 60 s] lies
  inside its source's coverage (≤ DATA_END 2026-09-26 21:40:49Z for every source; for a V4 entry on a backfill day, ≤ the end of the
  unbroken backfill run, 2026-09-05T00:00Z). Otherwise the engine books `"oow"`; each record counts these as `coverage.pending`.
  This matters most for 5 d / 7 d: they are booked mostly on calls before ~08-29 and in 09-18 → 09-19.
- **Reproduction check (a STOP condition):** in the TP 1.50 pass, every study row's delay-60 call and twin positions at the six old
  holds must equal the dial test's `rows.ndjson` exactly (fill, entry, and every booked hold), and `dials_tp50.ndjson` must equal the
  dial test's `dials.ndjson` (sha256 f7eca215…). If either differs, the batch stops and the difference is reported, not analysed.

## 2 · Data and the SEAL — unchanged from the dial test PREREG §2
V2/V3 tape + archive (tape-2026-09-27 never opened; sealed day files dropped by name); V4 = backfill join ∪ v4-join; DATA_END =
1790463649; no row with ts ≥ 1790467200 and no call at/after 2026-09-27T00:00Z is read (the readers raise). The backfill-day list is
snapshotted by each pass; all four passes must see the same list (asserted in the analysis).

## 3 · Dials (row levels are the dial test's `levels.json`, sha256 c0dc14b5…, reused, never re-cut)
- Market cap at the call: the frozen bands (`bands.json` sha256 9ac4bfb2…): <$50k · $50k–$100k · $100k–$250k · $250k–$1M · >$1M.
- Run-up in the hour before the call: <0 · 0–50 % · 50–200 % · >200 % · no print in the hour.
- First caller / follower (unit = caller): first · follower ≤5 min · 5–30 min · 30–180 min · 3–24 h · >24 h (outage rows UNKNOWN,
  Amendment 2 — they fall out of every grid cell of this dial).
- Callers by our entry: 1 · 2 · 3+ (outage rows UNKNOWN). **Frozen at post + 60 s for every delay** (the dial as registered; with a
  5/15/60-min delay it is NOT re-counted at the later entry).
- Coin age at the call: <1 h · 1–6 h · 6–24 h · 1–7 d · >7 d (unknown excluded from grids).
- **Caller tier (new here):** the engine's `tier_at(caller, call time)` stored on each row — the production tier method judged ONLY on
  that caller's EARLIER calls whose 6-h tier position had closed before this call (callers-v4's method, unchanged): elite · good ·
  other (a caller with no closed earlier call is "other").
- **Call source (new here):** direct (any chat but CallAnalyserRobinhood) · CallAnalyser (repost). Amendment 2 lane rule.
- Hold, take profit, delay: the engine settings above.

## 4 · Cells — `cells.json` (built by `make_cells.py` from `must_test.json` + `bands.json` only; sha256 in PREREG.sha256)
**652 new cells.** Held unless the cell sets it: hold 1 h · take profit +50 % · delay 1 min · all callers / all coins.
A grid point that equals a dial-test cell (take profit +50 %, delay 1 min, the same filter and hold) is NOT re-read (79 such points),
and a point shared by two slices is read once; both kinds appear in `results.json` as ALIAS records pointing at the one read.
1. **1-D (26):** hold 5 min · 7.5 min · 5 d · 7 d; delay 5 / 15 / 60 min, take profit +25 % / +100 % / none, caller tier elite / good /
   other, call source direct / CallAnalyser — each at 1 h and 24 h (as the dial test swept its dials).
2. **The dial test's crosses pushed (40):** hold × mcap and hold × run-up at the four new holds (5 min, 7.5 min, 5 d, 7 d) × 5 levels.
   This includes the queue's stage-3 push "hold 5 d / 7 d at mcap >$1M" and "hold below 15 min at the held settings".
3. **31 slices, full grids** (queue stage 2), everything else held: mcap×age 25 · hold×tp 24 · mcap×first 30 · first×age 30 ·
   mcap×ncallers 15 · first×ncallers 18 · ncallers×age 15 · mcap×runup 25 · runup×first 30 · runup×ncallers 15 · runup×age 25 ·
   mcap×tp 15 · runup×tp 15 · first×tp 18 · ncallers×tp 9 · age×tp 15 · ncallers×hold 24 · delay×hold 24 · delay×tp 9 · delay×mcap 15 ·
   delay×runup 15 · delay×first 18 · delay×ncallers 9 · delay×age 15 · first×hold 48 · tier×age 15 · tier×mcap 15 · src×tp 6 · tier×tp 9 ·
   tier×first 18 · tier×ncallers 9 (new points per slice after removing dial-test and shared points; full level lists in `cells.json`).
4. **Corners the queue names that no slice covers (13):** tier×hold (other, 15 min) (other, 72 h) · age×hold (>7 d, 15 min) (>7 d, 72 h) ·
   tier×delay (other, 60 min) · delay×src (60 min, CallAnalyser) · tier×runup (other, no print) · tier×src (other, CallAnalyser) ·
   mcap×src (>$1M, CallAnalyser) · runup×src (no print, CallAnalyser) · first×src (follower >24 h, CallAnalyser) ·
   ncallers×src (3+, CallAnalyser) · age×src (>7 d, CallAnalyser). Every other corner lies in a slice or is a 1-D cell.
5. Queue sweeps (delay 60 min; take profit +25 %, +100 %) are 1-D cells above (asserted by `make_cells.py`).
**Family count K: dial test 144 + this batch 652 = 796 cells read on these days.** At a 95 % two-sided range, ~2.5 % of cells
(~16 of 652) are expected to show a lower bar > 0 by chance even with no effect anywhere (cells are correlated, so the count is
lumpy); a cell with a lower bar > 0 is therefore reported with its checks, never as a finding.

## 5 · Per-cell metrics — the dial test's `analyze.py` statistics, VERBATIM
`analyze_fill.py` exec()s the dial test's statistics block from the copied `analyze.py` (sha256 9f136a7d…): `se_iid`, `se_cluster`,
`se_pigeon`, `se_block`, `summarize` (conservative SE = max of iid, caller, coin, day, coin×day pigeonhole, moving block; B = 4,000),
`drop5`, `small` and `cell()` (n, coins, callers, days, mean after costs with 95 % range, d = call − twin with range, median, drop-5,
no-repeats, hit / TP share, zero-cost mean, G1 coverage, ex-outage, era split, lane split, **the ex-G5 view — Amendment 3: any call
or twin position booked > +1,900 % zero-cost at that hold removed, both views in every record**, lead / leadD flags and leadNote).
The only re-pointing: `cell_rows` reads the cell's (take profit, delay) position instead of the fixed `d60`, and `HL`/`HOLDS` are the
ten holds. Seed per cell = 20260930 + 11 × cell number (the dial test's +11 rule, made order-independent). `extra=True` on every cell
(era and source split everywhere).

## 6 · What gets reported (the dial test's §6 rule)
A cell with n ≥ 30 on ≥ 15 coins whose 95 % lower bar (mean or d) is > 0, in EITHER view, is listed with n, drop-5, no-repeats,
era split and source split, and marked "carried by a few coins / repeats" when drop-5 or no-repeats is ≤ 0. Headline view = ex-G5
(as the dial test's answers), raw view always stated alongside. Cells with n < 30: "can't tell". One line per dial / slice:
direction across levels and the best cell with its range. **None of it is an edge (4th read of these days).**

## 7 · Predictions (before any return)
1. Holds of 5 / 7.5 min are about as bad as 15 min (costs dominate); 5 d / 7 d are worse than 72 h, and worse than twins.
2. Take profit "none" is worst at long holds; +25 % lifts the hit share but not the mean above 0.
3. Delay 60 min does not rescue the calls (d stays ≤ 0).
4. Caller tier "elite" is not distinguishable from "other" (R-0088).
5. Of 652 cells, a handful show a lower bar > 0 by chance; none survives drop-5, no-repeats AND a same-sign era split.

## 8 · Resources and rules
A4 gate (`a4.sh`) before every engine pass and before the analysis; passes run one at a time at `nice 19 / ionice idle`; the other
research engine on the box is waited for, never killed. No RPC (supply is cached in the dial test's call set; no new coin). No git
tree-rewriting command. Nothing outside this folder is written.

## Amendment 1 · 2026-09-30 ~02:35Z — coordinator instructions, recorded BEFORE any return of this batch was read
Two instructions arrived while pass A's first two engine runs (+50 %, +25 %) were streaming; no row, cell or number of this batch
had been opened (only the smoke reproduction check, which compares positions for equality and prints no return).
1. **The V4 backfill days 2026-09-05 → 09-11 are being converted now** (by the coordinator, into `v4-backfill-join-2026-09-29/out/`).
   ⇒ **PASS A** ("A · 47 backfill days", 07-20 → 09-04) = this PREREG exactly as registered, finished as is. The +50 % / +25 % runs
   snapshotted 47 days at start; the +100 % / none runs are pinned to the same 47 by a fifth constant replacement in `engine_fill.py`
   (`BF_DAYS = _bf_days()` → cut at `FILL_BF_MAX`; default = no cut). The driver that would have launched them unpinned was stopped
   (my own process, exact PID) before they started. The analysis asserts all four runs saw the same days.
   ⇒ **PASS B** ("B · backfill through 09-11 + recovered calls", folder `passB/`) = the SAME prereg re-run: same 652 cells, same
   scripts, same frozen bands (`bands.py` reuses `bands.json`, never re-cuts), same seeds; data = every unbroken converted backfill
   day (expected 07-20 → 09-11) + the call-set data fix below. The dial test's registered pool-fee rule (`prep_pools.py`: v4-join
   meta + unknown_keys + the backfill's `state.json` newPools) is re-run against the join's current `state.json` so pools born on the
   new days get their PoolKey fee. Pass B's out-of-window end for backfill-day V4 entries moves to 2026-09-12T00:00Z (the engine's rule).
   The 79 grid points that pass A aliases to the dial test are COMPUTED in pass B (the dial test never read pass B's data); they are
   re-reads of registered points, not new family members: **K stays 796.**
   Coverage is reported by the registered eras AND with 2026-09-05 → 09-12 00:00Z as its own era (coverage/era reporting only; the
   per-record era labels stay as registered so the passes compare line by line).
2. **Data fix — unresolved Robinhood calls** (Chef declined the NAS restart that fixes it at source). Rule = the staged mapper
   `calls-fixes-2026-09-30/stage/noxabot/lib/births-pools.js` (= alphalens ca_extractor `_rh_tokens()`): a key is a pool when it is a
   `tokens[<token>].pools[].addr` of `robinhood-token-births.json`. `map_pools.py` re-derived it independently: 22 pool keys → 22 tokens,
   **all 22 agree with the audit's `unresolved_rh_pool_keys.json`**. Found by counting only (no price read):
   - **20 of the 30 pool-address events are ALREADY in the frozen study** (same event id, already under the right token — the box-side
     remap worked for them). The dial test's "43 unresolved" therefore double-counted 20; its "with unresolved" coverage was too low.
   - **10 pool-address events are genuinely missing** → added under their token.
   - **12 events on 10 keys that are themselves RH V4 TOKENS** (field `tok` of our V4 births ledger) with no resolution row
     (resolver starvation, 09-24 → 09-26, all CallAnalyser) → added under that key. This is the sibling of the pool fix (same cause:
     the NAS resolver could not see our own tables), declared here and reported separately.
   - 1 key (0xec6766…) is in none of our RH tables → stays unresolved.
   `passB/build_snapshot_B.py` = frozen events + 22 recovered events; the production credit rules re-applied over the combined set
   (mirror 180 s rule recomputed — it flips 2 existing events to mirrors; multi-CA from the DB). Study rows 5,659 → 5,673 (+18, −4),
   11 new coins. Supply/decimals for the 12 recovered coins not in the cached `supply.json`: ONE Multicall3 read on the public keyless
   lane at the cache's own block (`passB/fetch_supply_B.py`). Pass A keeps the frozen call set (its reproduction check needs it).
- Erratum to Amendment 1 (02:36Z, still before any return): 11 (not 12) pass-B coins lacked supply; PublicNode answered 403 five
  times, so the read went to the other keyless lane the dial test used (Uniblock, same block): 7 RPC calls in all. All 11 read
  1e27 supply / 18 decimals.

## Amendment 2 · 2026-09-30 ~03:05Z — wrapper bug found by the registered STOP check; no return read
`check_repro.py` FAILED on pass A's first two runs: 7 of 5,659 rows and 1 dial row differed from the dial test. Cause (mine, in
`engine_fill.py`): the output tag made `OUT_SUFFIX` non-empty, and the engine's next line `if OUT_SUFFIX:` is its SMOKE switch — so
DATA_END became 2026-09-26 23:59:59 instead of 21:40:49 (the seal itself held: nothing ≥ 09-27T00:00Z was read). The smoke check
could not see it (smoke sets DATA_END that way by design). Fix: one more constant-line replacement, `if OUT_SUFFIX:` →
`if LAST_DAY != "2026-09-26":` — the engine's own smoke rule, unchanged in meaning. The two void runs are moved to `void_dataend/`
unopened except for the equality check; pass A is re-run in full (all four take-profits), and must pass `check_repro.py` before
analysis. Pass B uses the fixed wrapper too.
