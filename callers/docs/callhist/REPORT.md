# CALL HISTORY — step 1 of the calls study — REPORT (2026-09-30, built 07:11Z → 10:22Z)
owner request (+15143 venue/pad, 15159 after-day-7, 15185 coord). Read-only research. Nothing was written outside this
folder. No noxa.bot fee appears anywhere; these are price paths. No row with ts ≥ 2026-09-27T00:00Z was read. Step 2 (winners vs rest)
was NOT done.
(Saved verbatim by the parent session from the subagent's final message — the harness blocked the subagent's own write.)

Output: calls.ndjson.gz — 6,669 rows, one per in-scope call event, joinable to calls-backtest-details.ndjson by `id`.
What one row is, and every rule: SPEC.md. It also records four additions and one deviation made during the build.

## 1 · Counts
- Call events in the backtest dump: 6,807.
- In scope (call + 24 h < seal): 6,669, on 3,081 coins.
- Out of scope (after 2026-09-26 00:00Z): 138, counted and not read.
- Priced (a candle ≤ 30 min before the call): 4,679.
- no_price: 1,990.
  - 788 had no $5+ print within ±24 h.
  - 1,202 had prints, but none within 30 min before the call.
- no_price by call period:
  - before 07-21: 676/1,659 (41 %)
  - 07-21…09-07: 829/3,938 (21 %)
  - 09-08…09-11: 33/335 (10 %)
  - 09-12…09-18 (V4 = locked set only): 403/450 (90 %)
  - 09-19…09-25: 49/287 (17 %)
- Flags, all rows:
  - partial_v23: 2,627 (1,761 priced)
  - pre_v4_join: 1,659
  - other_quote: 1,036
  - v4_locked_window: 598
  - liq0_dropped: 45
  - quote_ref_jump: 8
  - lock_pool: 2
  - v23_tail_livetape_only: 0
- Venue (priced): v4_pons 1,511 · v4_other 1,355 · v23 1,813.
- Pad (priced): Pons 1,511 · letscash 75 · RWA Launchpad 7 · doppler 6 · Clanker 6 · robinfun 3 · Klik 1 · null 3,070.
- Age source:
  - birth ledger: 6,402
  - first print (lower bound): 137
  - none: 130
  - Negative age on 220 rows (104 priced): the ledger's earliest pool is younger than a pool that was already trading. Treat these ages as unknown.

## 2 · 10x in 24 h and the pace line
Columns: n · reached 10x · crossed pace (any minute) · crossed pace (m ≥ 15) · median 24 h peak
- All priced: 4,679 · 148 · 2,333 · 1,487 · +54.5 %
- Same, without quote_ref_jump: 4,671 · 141 · 2,325 · 1,479 · +54.3 %
- Priced, not partial_v23: 2,918 · 101 · 1,534 · 935 · +59.2 %
- First calls, priced, non-mirror: 2,058 · 90 (4.4 %) · 1,279 · 803 · +64.1 %
- Same, not partial_v23: 1,411 · 65 · 921 · 564 · +69.0 %
- Same, also without quote_ref_jump: 1,407 · 62 · 917 · 560 · +68.7 %
- First calls by venue:
  - v4_pons: 766 · 32 · 336 (m ≥ 15)
  - v4_other: 628 · 33 · 222
  - v23: 664 · 25 · 245
- "Crossed pace" is the GUI's in10() test on the 24 h race. "m ≥ 15" is the prereg's Z2.
- 7 of the 8 quote_ref_jump rows were 10x "winners". In the pool's own quote token they moved only +0.2…+193 %.

## 3 · Data faults found
1. Liquidity-0 V4 prints (the ONE cleaning rule that differs from the recorder).
   - Their price is the tick-bound value (3.4e50 USD), but their USD size is real, so the $5 floor lets them through.
   - Effect before the fix: peaks of 1e41–1e55 % and 7 fake 10x first calls.
   - Fix: dropped (10,802 rows), as the v4-join README and features.py already do. 45 rows flagged liq0_dropped.
   - The live recorder has the same exposure: PURSER's chart shows a 2.8e34 high.
2. Other-quote reference jumps: 8 of 1,036 other-quote rows have a USD peak more than 3x the quote-terms peak (flag quote_ref_jump). The late-peak version flags 6 (late_quote_ref_jump).
3. The call list lags: the local alphalens.db behind the dump misses 33 of 288 NAS-DB events on 09-23…09-30.
   - 30 of the 33 are CallAnalyserRobinhood public-scrape calls on coins the local DB has not resolved.
   - Recent calls are likely under-counted by about 10 %.
4. 39 % of the priced rows before 09-08 are on sampled V2/V3 days (R-0098).

## 4 · Spot checks vs callcharts/pub/*.json
First pass: only 2 of 93 same-pool events matched. The two causes are in the recorder:
(a) Its V4 clock is 23–55 min early on 09-23…09-26.
  - It anchors block→time only on the last ~2 days of tape plus the chain head, then extrapolates further back.
  - 58,291 of 68,251 recorder candles (85 %) have an exact O/H/L/C twin in ours at a shifted time.
  - The shift falls smoothly from 55 min (09-23 06h) to 23 min (09-26 18h). V2/V3 candles match at offset 0.
  - RPC check: block 70528562 = 1790168059; the v4-join says 1790168060.
  - ⇒ noxa.bot/calls/gui is wrong for V4 calls older than ~2 days.
(b) It prices historical V4 rows at a single ETH/USD (≈2,672).

With (a) and (b) reproduced on our rows:
- PRISM 6895567 (v2): 0.0187103 / +35.4 % @560 — ours identical; the dataset is identical too.
- MUSEPAD 6909150 (v3): 0.000248339 / +12.2 % @3 — ours identical; the dataset is identical too.
- AGI 6894748 (V4): recorder 0.00236969 / +51.1 % @772; ours 0.00237097 / +51.1 % @773. The dataset on the true clock: 0.00242636 / +48.2 % @819.
- QUANTA 6905316 (V4): recorder 5.04966e-5 / +2907 % @1235; ours 5.0427e-5 / +2909 % @1235. Dataset: 4.48921e-5 / +3310 % @1276.
- QUANTA 6909155 (V4): recorder 0.000591872 / +156.6 % @50; ours 0.000592609 / +156.1 % @50. Dataset: 0.000861077 / +77.8 % @91.

V4 overall: 7 of 24 events match within 0.2 % and ±1 min; the rest are within about 1–10 %, from clock-model residue. Three pool mismatches come from the main-pool window (±24 h here vs 7 days in the recorder). Two events are recorder-only (fault 3).

## 5 · After day 7 (owner request)
- 6,428 calls have call + 7 d before the seal; 4,481 of them are priced and have a late block.
- 1,965 coins (first call) have ≥ 7 d of data.
  - Dead by day 7 (no $5+ print on any pool after day 7): 298.
  - New high after day 7 above the first-24 h peak: 193 (114 without partial_v23).
  - Same, on a sane candle: 74 (49 without partial_v23). "Sane" = the candle traded ≥ $100, closed ≥ half its high, the day-7 price came from a ≥ $100 candle, and there is no quote jump.
  - Of the 193, 63 are ≥ 10x the call price.
- Caveats:
  - 2,644 late windows carry late_v4_locked_window: in 09-12…09-18, a V4 coin outside the locked set shows no trades.
  - 1,720 carry late_partial_v23.
- Top 10 by the rise from day 7 to the later high (sane candles only):
  1. 0xfe7e19cb (The Hood, V4/SPCX, 07-21): +23,529 % (quote terms +19,211 %) on day 42 — other_quote
  2. 0x65fa36fe (The Hood, V4/ETH, 08-15): +16,918 % on day 18.5
  3. 0x4b1c1725 (The Hood, v23, 07-19): +16,836 % on day 49 — partial_v23
  4. 0xb5d553cc (The Hood, V4/TSLA, 07-21): +12,238 % (quote terms +10,471 %) on day 42 — other_quote
  5. 0xc69130b6 (CallAnalyser, Pons, 09-19): +8,413 % on day 7.6
  6. 0x69c68e4c (Freshgemscalls, V4/AAPL, 07-27): +8,353 % on day 37 — other_quote
  7. 0xa26992c4 (CallAnalyser, Pons, 09-01): +7,072 % on day 9.4
  8. 0x18e67423 (The Hood, V4/ETH, 08-06): +5,801 % on day 29
  9. 0x39dbed3a (FireStartoor, v23, 07-13): +4,949 % on day 54 — partial_v23
  10. 0x6b1497cd (CallAnalyser, Pons, 09-03): +3,414 % on day 18.5
- The raw top 10 is led by a TSM-quoted quote-jump row (+39.3M %, but +43 % in its own quote) and by a $7.74 candle.
- These are price paths only: no fee, depth or fill is modelled.

## 6 · coord (owner request)
- First calls (3,081, non-mirror) with coord ≥ 1: 0. With coord_5m ≥ 1: 14.
- This is structural. The mirror rule marks every other-chat call within 180 s of an origin as a mirror, so excluding mirrors empties the ±60 s window.
- Counting mirrors too: coord_incl_mirrors ≥ 1 on 9 first calls; coord_5m_incl_mirrors ≥ 1 on 34.

## 7 · How the build changed
- v1 → v2: the last candle of each 24 h window is now a whole minute.
  - Changed: race on 246 rows, peak24 on 1, main_vol on 301, post_candles on 180.
  - depth1_eth changed on 6 rows (now capped to the 24 h before the call).
- v2 → v3: new fields and flags only (checked by diff).
- v3 → v4 (liquidity-0 drop): changed peak24 on 8 rows, t10x on 8, pace on 2, px_at_call on 1, vol1h on 494.
- v4 → final: only the late block changed.

## 8 · Resources and disk
- The A4 gate ran before every heavy step (39 polls, 9 GO), with nice 19 / ionice idle.
- Peak RSS 2.16 GB.
- One ungated step: births.py at 07:13Z (4.7 s, 1.2 GB); it is logged.
- Disk: 106 GB free at the start, never below 96 GB. Tape extracts were kept gzip only.
- Wall clock: 07:11 → 10:22Z.
- One keyless RPC read (a block timestamp).

## 9 · Deleted intermediates
- work/f/ (8.8 GB of gzip tape rows from 273 source files)
- work/b/ (3.0 GB, 64 buckets)
- work/calls_v1…v4.ndjson.gz
- births.json, toks.txt, tape_last.json (a copy is kept in evidence/), cc_tmp.py, filter.pid, and the phase logs
Kept: SPEC.md, calls.ndjson.gz, the code (build.py, filter_gz.sh, births.py, spotcheck*.py, candlecheck.py, report_stats.py) and evidence/.
Re-running the spot checks means rebuilding work/b: births.py → filter_gz.sh → build.py 1 → build.py 2, about 25 min behind the gate.
