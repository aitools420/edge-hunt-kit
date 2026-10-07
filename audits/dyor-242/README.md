# Audit rows for #242, ask 1: every trade of cells A and B

`audit242_rows.ndjson` has one JSON row per trade, for every trade in both cells. Nothing is pre-picked: 66 rows for A and 36 for B.

- **A:** 25 % dip, traded in every one of the prior 72 hours, take profit +30 %, 12 h max hold, LOW band.
- **B:** 30 % dip, every hour, take profit +50 %, 12 h max hold, LOW band.

These are the JUDGE trades behind #241. Signals run from 2026-09-17 16:28:29Z to 09-25 18:47:14Z, and the last exit is at 09-26 05:14:49Z. Nothing at or after the 09-27 00:00Z seal was read.

Other files:

| file | what it is |
|---|---|
| `check.py` | Recomputes n and the mean for each cell from the rows. Standard library only. It also re-derives every row's net return from that row's own price, cost and hop fields. |
| `clock_anchors.tsv` | The block-to-time anchors that our tape clock uses over these days (section 2). |
| `SHA256SUMS` | Hashes of the files above and of this README. |

Every row is public chain data: coin, pool, quote-token and hook addresses, transaction hashes, blocks, log indexes, prices and ticks. There is no trader or wallet field.

## 1. n and mean per cell, from the file

Output of `python3 check.py audit242_rows.ndjson`:

```
rows: 102
row arithmetic re-derived from the row fields; mismatches per field: none

cell A: dip 25 %, every hour, TP +30 %, 12 h, LOW band
  n 66 on 23 coins; exits {'tp': 33, 'time': 33}; duplicate (trigger tx, log index) keys: 0
  mean net per trade, % of the $50 clip, hop costed (R-0115):       +7.5612
  mean net per trade, % of the $50 clip, as #241 (no hop):          +8.5175
  same two views with the take-profit booked at its trigger print:  +9.0235 / +10.0441
  sum net ETH (R-0115 / #241): +0.091549 / +0.103158; mean gross +11.2071 %
  trades on non-ETH-quoted pools (hop costed): 30; dip below the cell depth when measured in the pool's own quote units: 3; sub-$1 swap after the priced print (entry / exit): 5 / 8

cell B: dip 30 %, every hour, TP +50 %, 12 h, LOW band
  n 36 on 19 coins; exits {'tp': 17, 'time': 19}; duplicate (trigger tx, log index) keys: 0
  mean net per trade, % of the $50 clip, hop costed (R-0115):       +17.5730
  mean net per trade, % of the $50 clip, as #241 (no hop):          +19.0935
  same two views with the take-profit booked at its trigger print:  +18.8934 / +20.4846
  sum net ETH (R-0115 / #241): +0.117551 / +0.127666; mean gross +22.1704 %
  trades on non-ETH-quoted pools (hop costed): 17; dip below the cell depth when measured in the pool's own quote units: 0; sub-$1 swap after the priced print (entry / exit): 1 / 2
```

### #241 figures against the corrected ones

| cell | #241 posted | the file, no hop (#241's cost model) | the file, hop costed (current) |
|---|---|---|---|
| A | +8.5, n 66 (range +2.2 to +14.9) | +8.5175, n 66 | **+7.5612**, n 66 (range +1.3 to +13.8) |
| B | +19.1, n 36 (range +2.0 to +36.1) | +19.0935, n 36 | **+17.5730**, n 36 (range +1.4 to +33.8) |

The ranges are the batches' own 95 % day-block bootstrap. `check.py` does not recompute them.

**Correction to #241.** #241 gave +8.5 and +19.1 as real-cost results, but they left one cost out. Here that is 1.0 point for A and 1.5 for B. We withdrew the figures on 09-29 (our retraction R-0115).

- **What was missing:** 30 of A's trades and 17 of B's trades entered pools quoted in something other than ETH or WETH: USDG, or a stock or other token (NVDA, SPCX, GME, ORBIO, GLD, SHROOM).
  - A real trade there first buys the quote token with ETH, then sells it back for ETH at exit.
  - #241's figures did not charge that second swap ("the hop").
- **What we did about it:** a re-score of the same trades charged the hop on both legs. Each leg goes through the quote token's cheapest direct ETH or WETH pool whose take is known exactly. The leg pays that pool's take, its depth impact at the size of the leg, and half a swap's gas. That re-score gave +7.6 for A and +17.6 for B.

Every row carries both views:
- `net_return_pct` / `net_return_eth` are the hop-costed view, and the current one.
- `net_return_pct_as_241` / `net_return_eth_as_241` are #241's view.

The rows reproduce the batches' stored means exactly: 8.5175 and 19.0935 with no hop, 7.5612 and 17.5730 with the hop. Nothing else enters those figures.

Following your note 1, each row also gives the take profit booked at its trigger print (`net_return_pct_tp_at_trigger` and `..._as_241`). Our notebook's "flatters by about a point" is +1.5 for A and +1.3 to +1.4 for B here. On time exits the two bookings are equal.

**How the rows were produced.** The engine's raw output files for the 09-29 batch had aged out of a scratch folder. We did not run the engine again. Instead:

1. **The trades:** we took the stored per-trade results of the published batches: coin, pool, signal second, entry second, exit second, reason and net return. The #241 view and the R-0115 view list the same 102 trades.
2. **Chain identifiers:** we looked up each trade's entry-pool swaps in the tape, following the engine's own rules.
3. **Re-scoring:** we re-scored each rebuilt trade with the published cost code. It reproduces its stored net return in both views to within 1e-6 points: 102 of 102.
4. **Field-by-field check:**
   - For all 36 B trades, and for 62 A trades whose signal is also a signal of a sister cell (TP +40), we also hold the engine's own rows from a later run of the same frozen engine over the same tape.
   - There, the dip, the 1-h high's timestamp, the entry price, the fill price and the engine fee match field by field.
   - For B, the exit price, the sale price and the trigger booking also match.
5. **The guard checks can fail:** changing one rule makes trades fail. Pricing the entry strictly before the 60 s second fails 4 trades. Admitting swaps under $1 fails 15.
6. **Pool ids:** 24 prints, all on one Uniswap pool (coin 0x4a6e…a8fb), come from our older locked-set collector, which could label a swap with the coin's main pool instead of the pool that emitted it. All 24 were confirmed (pool id and tick) against the raw PoolManager `Swap` logs. Every other print's pool id is the log's own.

## 2. The clock, and which block of the second (your check 2)

**Our timestamps are not block header times.** The tape gives each block a whole second.

- **How:** linear interpolation between RPC anchors 25,000 blocks apart, rounded to the nearest second, using JavaScript `Math.round`.
- **Accuracy:** against 500 held-out blocks, the error is median 0.66 s, p90 1.96 s and max 8.2 s.
- **Where:** the anchors for these days are in `clock_anchors.tsv`.
- **The formula:** for block b with anchors (b0, t0) ≤ b < (b1, t1), the second is `round(t0 + (b - b0) * (t1 - t0) / (b1 - b0))`.

Every `*_tape_ts` in the rows is that second. Every print in the file was re-checked against the formula.

**Entry.**
- `entry_ts` = `signal_ts` + 60.
- The engine prices the entry at the pool state after the last swap it accepted on the entry pool whose tape second is ≤ `entry_ts`. That is, as of the last block of that second.
- "Accepted" means $1 or more and inside the bad-print guard's 20× band. The band rejected nothing in these windows.
- `entry_cutoff_block` is that block: the last block whose tape second ≤ `entry_ts`.
- `entry_block` / `entry_tx` / `entry_log_index` is the swap whose post-swap price is the entry price. It is the trigger swap itself in 9 rows.
- In 96 rows no other swap on the pool lies between that swap and the cutoff block.
- In 6 rows a swap under $1 does. The engine's bad-print guard ignores swaps under $1. That later swap is listed in `entry_later_pool_event_at_or_before_cutoff`. Rebuilding from the pool's last event at the cutoff block gives that swap's price instead.

**Take-profit exit (`exit_reason` "tp").**
- **When it fires:** on the first swap of $1 or more after the fill, before the deadline, where `price_usd / (1 + w)` ≥ `tp_line_usd`.
  - `tp_line_usd` = `entry_fill_price_usd_engine` × 1.3 for A, or × 1.5 for B.
  - `w` = (50 / `entry_fill_price_usd_engine`) × `price_eth` × S1 / `depth1_eth`, with S1 = √1.01 − 1.
  - So it is the sale price after the impact of our own sale, against the entry fill. It is not the pool price against the entry pool price.
- **The trigger swap:** `tp_trigger_*`.
- **Booking:** 60 s later. `exit_ts` = `tp_trigger_tape_ts` + 60. The price is the pool state after the last swap of $1 or more with tape second ≤ `exit_ts`.
- **Cutoff:** `exit_cutoff_block` is the last block of that second.

**Time exit (`exit_reason` "time").**
- The deadline is `exit_ts` = `entry_ts` + 43,200.
- The price is the pool state after the last swap of $1 or more with tape second strictly before the deadline.
- `exit_cutoff_block` is the last block of second `exit_ts` − 1.
- In 10 rows a swap under $1 follows the priced swap before the cutoff. It is listed in `exit_later_pool_event_at_or_before_cutoff`.

No position exited on the drain rule or on a fallback price, and no exit used the over-20× price check.

## 3. The dip and the 1-h high (your check 1)

**Trigger swap.**
- The trigger is the first swap at `signal_ts` on the entry pool (`trigger_*`) whose dip from the pool's 1-h high reaches the cell depth.
- In these cells the trigger pool, the main pool and the entry pool are the same pool.
- `trigger_log_index` is the log index that `eth_getLogs` returns for the V4 `Swap` log. The tape writer stores `parseInt(log.logIndex, 16)`.
- No two rows in a cell share a (trigger tx, log index) key.

**What the engine measures.**
- It measures the dip in USD (`price_usd`), not in the pool's own units.
- **The 1-h high:** the largest `price_usd` among the pool's accepted swaps in minute buckets `floor(signal_ts/60) − 59` to `floor(signal_ts/60)`, up to and including the trigger swap. So the window runs from the start of the minute 59 minutes before the trigger's minute: 59 to 60 minutes back. The max is held as a 32-bit float (`high_1h_price_usd_engine`).
- `high_1h_*` is the earliest swap at that max.
- `dip_pct_engine_usd` = 1 − trigger price / high.

**Native-unit dips.**
- USD price = the pool's own price × the quote token's ETH price × ETH/USD, so the dip in the pool's own units differs.
- `dip_pct_pool_native` uses the same two swaps in `price_quote`.
- **In 3 A rows the native dip is below 25 %** (`native_dip_below_cell_depth`: true). Check 1 on the pool's own swaps will fail on these three. The cause is how our engine measures, not a bad row:
  - coin 0xdec8…56aa, ORBIO-quoted: 25.80 % in USD, 24.36 % native.
  - coin 0x9fa1…ffdc, ETH-quoted: 25.08 % in USD, 24.73 % native, because ETH/USD moved within the hour.
  - coin 0xf014…ebff, GME-quoted: 25.76 % in USD, 21.22 % native.

  No B row is affected.

## 4. Field reference

Each print (`trigger_`, `high_1h_`, `entry_`, `tp_trigger_`, `exit_`) carries these fields:

| field | what it is |
|---|---|
| `block`, `tx`, `log_index` | the swap's block, transaction and log index |
| `tape_ts` | the tape second |
| `side` | the side as seen from the coin |
| `usd` | the swap's USD size |
| `price_quote`, `tick`, `liquidity` | the pool's own price after the swap: quote token per coin, decimals applied, from `sqrtPriceX96`, rounded to 6 significant figures. The tick and the in-range liquidity are exact. |
| `price_eth` | `price_quote` × the quote token's ETH price |
| `price_usd` | `price_eth` × ETH/USD |
| `depth1_eth` | the ETH that moves the price 1 % at that liquidity |

Where the conversions come from:
- **ETH or WETH:** the quote's ETH price is 1.
- **USDG:** taken as $1, with ETH/USD from CoinGecko.
- **Stock and other quotes:** that quote's deepest ETH, WETH or USDG pool, last value at or before the swap.
- **ETH/USD:** CoinGecko, hourly.

`entry_price` and `exit_price` are the `price_usd` the engine used.

| field | meaning |
|---|---|
| `pool_id`, `pool_quote`, `pool_quote_token`, `pool_hook`, `pool_fee_key`, `pad` | The V4 PoolId, the quote, the quote token's address (null for ETH/WETH), the hook, the fee field of the pool key (0 on the launchpad hook's pools; 8388608 = dynamic), and the coin's launchpad label. |
| `signal_hour_ts` | The hour in which the coin was eligible: it traded at least $10 in each of the prior 72 hours. |
| `entry_fill_price_usd_engine`, `entry_impact_engine`, `entry_fee_engine` | The engine's own fill: entry price × (1 + impact) × (1 + pool fee key). Impact = (50 / ETH/USD) × S1 / `depth1_eth`. These set the TP line and the token amount for the sale's impact only. The net (below) is built from pool prices and per-side costs. |
| `exit_sell_price_usd_engine`, `exit_impact_engine`, `exit_fee_engine` | The same for the sale. Impact uses the ETH value of the tokens held. |
| `take_buy`, `take_sell` | The per-side cost charged, as fractions: `lp_fee`, `hook_or_creator_take`, `price_impact`, `token_tax`, `total` and `source`. Details below the table. |
| `hop_buy`, `hop_sell`, `hop_sell_multiplier`, `hop_gas_pct_of_clip` | Null on ETH/WETH pools. Otherwise: the quote-token leg's pool, its take (fee key + 0.04 % on hookless pools, launch terms on the launchpad hook), its impact and its multiplier on each leg, and half a swap's gas per leg. The hop pool's state is its last swap at or before the minute floor of `entry_ts` / `exit_ts`, at most 24 h old, priced within 10 % of the quote's reference. |
| `eth_usd_booking_entry`, `eth_usd_booking_exit`, `clip_eth` | ETH/USD used for booking: linear between 10-minute medians of the tape's ETH/USD. `clip_eth` = 50 / ETH/USD at entry. |
| `entry_price_eth_booked`, `exit_price_eth_booked`, `gross_multiple`, `gross_return_pct`, `gross_return_eth` | Booked ETH prices = `price_usd` / booking ETH/USD. Gross = exit / entry. This differs from the ratio of `price_eth` by at most 0.04 % on ETH-quoted pools, because the two ETH/USD series differ. |
| `gas_pct_of_clip` | Measured gas for a round trip, plus the expected gas of failed attempts, as % of the clip. |
| `net_return_pct_as_241` | 100 × (gross × S / B − 1) − gas, where B = (1 + total_buy − impact_buy)(1 + impact_buy) and S = (1 − (total_sell − impact_sell)) / (1 + impact_sell). |
| `net_return_pct` | (net_241 + gas + 100) × `hop_sell_multiplier` / `hop_buy.multiplier` − 100 − gas − `hop_gas_pct_of_clip`. On ETH/WETH pools it equals net_241. |
| `net_return_eth`, `net_return_eth_as_241` | `clip_eth` × net % / 100 |

The per-side costs in `take_buy` / `take_sell`:
- **Launchpad hook pools** (91 rows): hook 1 % plus a creator rate of 0 bps, from the launch terms. LP fee is 0.
- **Hookless pools:**
  - The LP fee is measured from receipts where we have them, else taken from the fee key, plus 0.04 %.
  - So the 0.3 % fee-key pool (6 rows, receipts 0.3499 %) is charged 0.3899 % a side, and the 0.9 % pool (3 rows, fee key) 0.94 %. Your check 4 reads the Swap event's fee field and will see 0.30 % and 0.90 %.
- **Dynamic-fee pool** (2 rows): 0.7 %, from receipts.
- **Impact:** the engine's depth impact.
- **Token tax:** 0 on all 102 rows.

## 5. What is not supplied, and why

- **Per-side take from the nearest swaps' fee events.** We charged launch terms and receipt-measured LP fees (section 4), not the rate read from the hook's fee events on the swaps nearest the entry and exit. Your check 4 reads those.
- **The block of the hop pool's state.** The hop tables keep each quote pool's time, price and depth, not its block. Each row gives the hop pool, its take, its impact and its multiplier.
- **Raw `sqrtPriceX96`.** It is not in our tape. The exact `tick` and `liquidity` are given instead, and prices are rounded to 6 significant figures.
- **FIT-window trades.** #241's figures are JUDGE only. A has 3 FIT trades and B has 1; they are not included.
- **Twin draws.** Not asked for.

## 6. Where each field comes from

Paths are in the kit repo. `engine_v1.js` there (sha256 d1f23fed…) is the batch's engine with only added dials. A parity run with it reproduced every raw row of the batch's pass for the cells they shared, cell B among them, field by field.

| what | file:line |
|---|---|
| Rows the engine drops before anything else: liquidity 0, no depth, no ETH price | `patches/edge-machine-2026-09-30/engine/engine_v1.js:684` |
| Bad-print guard: swaps under $1 rejected, 20× band | `patches/edge-machine-2026-09-30/engine/guard.js:20-37` (the call is `engine_v1.js:630`) |
| Per-minute highs, held as 32-bit floats; 1-h high over 60 minute buckets | `engine_v1.js:268` (the pool's arrays), `199-207` (`poolHighs`) |
| Dip and trigger: dip = 1 − price / high, fires when dip ≥ the cell depth; LOW band check | `engine_v1.js:560-568` |
| Signal moment, dip, earliest swap at the high | `engine_v1.js:588-591`; `tfFeat` at `168` |
| Entry at signal + 60 s, from the last accepted swap; same-second swaps are included | `engine_v1.js:409-410` (clock), `429` (pending entry), `391-400` (fill) |
| Fill and sale prices, depth impact, pool fee | `engine_v1.js:306` (`feeV4`), `332-348` (`buyCost`, `sellAt`, `wOf`) |
| Take profit on the fill-adjusted sale price, booked 60 s later | `engine_v1.js:441`, `415`, `120` (`TPLAT`) |
| Time exit at entry + 43,200 s | `engine_v1.js:400`, `414` |
| Exits on the entry pool only | `engine_v1.js:432` |
| Net from pool prices and per-side costs; ETH booking | `patches/edge-machine-2026-09-30/engine/reduce_v1.py:50-56`, `87-97` |
| Hop legs | `reduce_v1.py:35-43`, `124-125`; `patches/edge-machine-2026-09-30/engine/hop.py:22`, `45-47`, `71-111` |
| Per-side costs, ETH/USD booking, gas | `patches/realism-2026-09-27/realism.py:35-56` (`_v4`), `57-78` (`cost_per_side`), `80-86`, `99-104`; the inputs are in the same folder (`pool_costs.json`, `pool_fees.json`, `tax_table.json`, `ethusd.json`, `latency.json`) |
| Launchpad hook launch terms | `patches/pons-feeterms-2026-09-27/pons_fee_terms.json` |
| Tape rows | the public tape release, `v4-swaps-2026-09-17` to `-26` |

The batches ran `reduce_h2.py`. `reduce_v1.py` is the same code, except that it keeps no-route trades with NaN hop views. No trade here has a missing route.
