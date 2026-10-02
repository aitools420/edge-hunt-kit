# Known data and method faults that matter for Blood backtests

These are corrections we registered after finding that something we had believed was wrong. Each entry gives the claim we withdrew and what is true instead. The text is copied from our corrections register; references to internal files are removed, and the numbers are unchanged.

Faults that frozen engine v1 already handles are marked **handled in v1**. Faults you must still account for yourself are marked **open**.

---

**R-0105 · bad-print guard froze rugged coins (handled in v1: `guard.js` + `guard_test.js`)**
- *Withdrawn:* "The older tape-backtest Blood figures are honest after-cost results."
- *True:* The old guard rejected any print outside median÷20…median×20, and a rejected print never entered the rolling median. After any crash of more than 95 %, every later print was rejected for good, and the coin was booked at its last pre-crash price. On a minimal series, a −99.2 % rug booked at 0.0 %.
- Engine v1 uses the new guard, which confirms a new price level instead of freezing. `guard_test.js` must print `NEW GUARD: ALL REQUIRED TESTS PASS`; `run_batch.sh` refuses to run otherwise.

**R-0107 · a print is not a fill (handled in v1: depth-aware V4 pricing, dust floor, drained-pool rule)**
- *Withdrawn:* "A print on the swap tape is a price a $10–100 trade could have filled at."
- *True:* 42 % of entry and exit prices in the early Blood backtests came from trades under $5. Drained or dust pools printed absurd values: twin exits of +385,000 % to +1,800,000 %, for example $0.012 → $219 on a $2.72 trade.
- A print only says what a trade of that size paid. A $10–100 clip needs depth-aware pricing, or at least a print-size floor and a drained-pool rule fixed before any outcome is read.

**R-0109 · day files are offset by one hour (handled in v1: one timestamp-merged stream)**
- *Withdrawn:* "`tape-YYYY-MM-DD` holds that UTC day's swaps."
- *True:* Each V2/V3 day file runs from about 23:00 UTC on the previous day to about 23:00 on its own day.
- Engine v1 merges V2/V3 and V4 into one stream ordered by `(ts, blk, li)` across day boundaries.
- Because `tape-2026-09-27` is sealed, the V2/V3 hour 2026-09-26 23:00–24:00 is not in the kit.

**R-0111 · Pons pools cost much more than 1 % a side (handled in v1: per-pool cost tables)**
- *Withdrawn:* "A Pons (V4 hook) pool costs about 1 % per side on top of the swap."
- *True:* The real take is a 1 % hook fee plus the creator's own tax of 0–5 % per side, set per pool at launch. The mean is 2.39 % per side on the Blood entry pools, and none of it appears in the Swap event.
- The fee terms read on chain matched the take actually paid on 144 of 145 real $20–200 swaps.
- A $50 round trip on the typical Blood entry pool costs 5.69 % (CI 5.35..6.03).
- Engine v1 reads these terms from `pons_fee_terms.json` and `pool_costs_v1.json`.

**R-0112 · "replicated" was the same trades (method)**
- *Withdrawn:* "The busy-coin dip lead (25 %|72|1 h, 20 %|72|1 h) replicated in the window × history grid."
- *True:* That grid's 1 h / 72 cells are the same trades as the depth × history grid's cells. Matching them is not independent evidence.
- **Lesson:** before calling a result a replication, check that the trade sets differ.

**R-0113 · a post-hoc fee split (method)**
- *Withdrawn:* "The top Blood dot is +16.54/trade (95 % lower +6.4, n 30) on low-fee pools at 40 % dip / 48+ h history."
- *True:* That came from a post-hoc split that counted every non-Pons V4 pool as low and ignored the LP fee. Under the pre-registered ≤ 1 %-a-side band (engine v1's `band: LOW`), the same setup is +4.6 (−7.7..+16.9), n 47.

**R-0114 · some V4 "lock" rows carry the wrong pool (OPEN: present in the shipped V4 files)**
- *Withdrawn:* "Every row of the V4 join carries the pool that emitted the swap."
- *True:* Rows with `src: lock` are labelled with the token's main pool. A swap on another pool of the same token therefore gets the wrong pool, orientation and price (up to 3×10¹¹× off) and a flipped side.
- This affects 3,355 rows on days up to 2026-09-18, and about 67 a day after.
- Engine v1's bad-print guard and its 2× main-pool rule reject many such prints. How much any result moved has not been measured.

**R-0115 · the quote-token hop was not costed (handled in v1: `hop.py`, view `real60h`)**
- *Withdrawn:* "The low-fee hunt's leaders are +19.1/trade and +8.5 after all costs."
- *True:* The ETH → stock-token hop on stock-quoted Pons pools was not costed. Costed on both legs, the two leaders are +17.6 (lower +1.4) and +7.6 (lower +1.3).
- Hop costs: USDG hop 0.05 %/side; stock tokens median 0.34 %, mean 1.5 %, up to 5 %.

**R-0116 · the early-September V4 rows are not fresh days (method)**
- *Withdrawn:* "Backfilled V4 data for 09-08…09-16 gives fresh days that no test has read."
- *True:* 09-09 → 09-17 is the FIT window that every hunt already read and printed beside JUDGE. What is new there is V4 trades, not days.
- The only truly fresh data is the sealed holdout.

**R-0119 · pools quoted in an "other" token can fool the >20× rule (OPEN: report an `eq` view)**
- *Withdrawn:* "Engine v1's G5 >20× rule (with its depthok exemption) stops a bad print from booking an impossible exit."
- *True:* For V4 pools quoted in a token other than ETH, WETH or USDG, prices go through that token's ETH reference. When that reference jumps, `price_usd`, `usd` and `depth1_eth` all jump with it, so the $5 dust filter and depthok both pass.
- In one test, the "AI" token's reference jumped about 2,500× in one print. One trade was booked at +326,669 % and carried a whole cell (+48.7 → −4.3 without other-quoted pools).
- The 9 edge-machine candidates were checked: TP and max-hold cap every exit, and the largest single trade is +86.7 %.
- **Rule:** with every result, also report the `eq` view. Drop trades whose entry pool's quote (`eQ` in `trades.ndjson.gz`) is not ETH/WETH/USDG, then compare the two views. See `protections/R0119_EQ_VIEW.md`.

**R-0120 · cell labels (method)**
- *Withdrawn:* "The old-weeks stable cells K3, K5, K6 are all-pools cells."
- *True:* K3 is LOW-take pools only (≤ 1 % a side, trading history 48, dip 30 %). K5 is all pools, trading history 72, dip 25 %. K6 is all pools, trading history 72, buyers in the last hour, dip 20 %.
- **Lesson:** read a cell's dials from its `cells.json`, never from a summary label.

---

## Data coverage you must not mistake for "nothing happened"
- **V2/V3:** the files from 2026-09-07 to 2026-09-15 are missing 11–28 % of swaps per day. From 2026-09-20 the gap is 0–6 %. The cause was a lookup cap in the collector.
- **V4:** all pools are recorded only from 2026-09-18 22:40Z. Before that, only a fixed set of tracked pools (`src: lock`) plus gap-fill rows (`src: hole`) were recorded.
