# CALL HISTORY — step 1 of the calls study (owner request) — SPEC, written before the build

Research dataset, read-only on the box. Writes only in this folder. No fee terms of any kind (f-nonoxafee): these are price paths.
Step 2 (winners vs rest) is pre-registered separately in `../callzone-2026-09-30/PREREG.md` and is NOT done here.

## What one row is
**One row = one call event** from the calls backtest's own per-call dump
`~/.openclaw/workspace/wick-engine/logs/calls-backtest-details.ndjson` (runId 919ef1f5b453507d, 6,807 events; built by
`~/projects/alphalens/calls_backtest.py` from `alphalens.db` call_events JOIN ca_resolutions, status resolved, chain robinhood).
The row keeps that dump's identity so it joins back by `id`: `id, ts, ca, chat, caller, mirrorOf, rankOnCa, callerRankOnCa, caInMsg`.
`mirrorOf` is the backtest's greedy 180 s cross-chat cluster rule (calls_backtest.py:55-79) — used as-is, not recomputed.

**In scope:** `ts + 86400 < 2026-09-27T00:00Z` (1790467200). Out-of-scope calls are counted, never read against the tape.

## Seal
No tape row with ts >= 1790467200 is read. Files for days >= 2026-09-27 are never opened (the filter step skips them, as
`real-trades-2026-09-30/filter.sh`). The parse step also refuses any row >= the seal, and every per-call window is
`[ts - 24 h, ts + 24 h)`, which ends before the seal for every in-scope call.
Known consequence: the V2/V3 full-tape file for day D runs from D-1 23:00 to ~D 23:00 (R-0109), so the hour
2026-09-26 23:00 -> 24:00 lives in `tape-2026-09-27` and is NOT read; for that hour V2/V3 has the livetape only.
Calls whose 24 h window reaches past the last full-tape row get flag `v23_tail_livetape_only` when their main pool is V2/V3.

## Sources (borrowed, not re-derived)
- **V2/V3** = full tape (`robinhood-tape/tape-*.ndjson` + `archive/2026-0[789]/tape-*.ndjson.gz`) U livetape
  (`robinhood-livetape/` + archive). Deduped on (tx, li), full-tape row kept (features.py rule). Livetape time = `bts` when present, else `ts`.
  Pool key = `v23:<kind>:<quote>` (recorder.js onTapeLine; the tape carries no pool address).
- **V4** = `v4-backfill-join-2026-09-29/out` (07-20 -> 09-11, every pool) U `v4-join-2026-09-27/out` (not `out/sealed`).
  Deduped on (blk, li), backfill row kept (= v4tape_bf.js prefer 'bf'). Price = row `price_usd`, size = row `usd`
  (the same converter maths as recorder.js's `CV.conv` / finalize.js day(); ETH/USD is CoinGecko hourly where the recorder uses the
  live on-chain ETH/USDG pool — a sub-1 % level difference that cancels in every % figure). Pool key = `v4:<pool id>`.
- Extraction = `real-trades-2026-09-30/filter.sh` logic (grep -F on the token list, days < 09-27, nice/ionice, A4 gate),
  changed only to write **gzip** output.
- Births: `robinhood-token-births.json` (V2/V3 firstTs, `source`), `robinhood-v4-births.ndjson` (pool birthTs, hook, venue),
  `v4-join-2026-09-27/unknown_keys.json` (pre-ledger pool keys incl. hook).

## Cleaning = the live chart recorder (`~/projects/callcharts/recorder.js`), rule by rule
Line numbers are those of the version read at 07:10Z, kept on disk as `recorder.js.bak-poolrefresh-20260930T093324Z`; the 09:33Z
edit (pool refresh) moved later lines by ~+11 and changed no cleaning rule.
| rule | recorder.js | here |
|---|---|---|
| 1-minute candles per pool: [o,h,l,c,usd] | `bump()` L108-117 | same, rows in (ts, blk, li) order |
| drop prints with px <= 0 or usd < $5 | L22 `MIN_USD = 5`, L110 | same |
| main pool = most USD volume | `mainPool()` L185 (over its 7-day window) | most USD volume over the call's own `[ts - 24 h, ts + 24 h)` — **deviation**: "the last 7 days" has no meaning for history |
| price at call = close of the last candle at or before the call, only if that candle is <= 30 min before the call | `pxAt` L191 | same, else flag `no_price` — never guessed |
| peak = highest candle HIGH in minutes strictly AFTER the call's minute | L193 | same, limited to candles whose minute starts before ts + 24 h (a candle is a whole minute, so its last rows can be up to 59 s past 24 h — never past the seal, which is minute-aligned) |
| peak mins = max(0, round((peak minute - ts)/60)) | L194 | same |
| race = % from px at call, sampled every 1 min to 60, 5 min to 360, 30 min after; a point only if the last candle is >= call - 30 min | L203-206 | same, to 1440 min, from EACH call's own price (the recorder draws it from the coin's first call) |
| the peak point inserted into the race if not already there | L208-209 | same |

## Per-row outputs
`pool, pool_kind (v4|v23), venue (v4_pons | v4_other | v23 | null), pad, px_at_call, flags[], race, peak24 {pct, mins},
t10x_mins, pace_cross_mins` and at-call features.
- `t10x_mins` = first candle after the call's minute (same window as the peak) whose HIGH >= 10 x px_at_call; minutes as peak mins.
- `pace_cross_mins` = first race point with m > 0 whose pct > p(m) = 100*(10^sqrt(m/1440) - 1) — exactly the GUI's `in10()`
  (noxabot/public/calls-gui.html L206-207), on the 24 h race only.
- `venue`: main pool V4 with hook = PonsV2MemeHook 0xe5e70264... -> `v4_pons`; other V4 -> `v4_other`; V2/V3 -> `v23`; no main pool -> null.
- `pad`: the V4 births `venue` of the main pool when it names a launchpad (doppler, letscash, Klik, RWA Launchpad) or the hook label
  (Pons, letscash, Klik, Clanker — features.py HOOKLAB); else the token-births `source` when it is a pad (`noxa`, `robinfun`); else null.
- At-call features (all from rows with ts < call ts):
  `age_s` = ts - earliest birth (token-births firstTs, any V4 pool birthTs of the token); `age_src` birth | first_print (lower bound) | null.
  `move1h_pct` = px_at_call / (main-pool close at or before ts - 3600, only if that candle is <= 30 min older) - 1; null = no prior print.
  `vol1h_usd` = USD of $5+ prints on ALL the coin's pools in [ts - 3600, ts); `vol1h_main_usd` = main pool only.
  `depth1_eth` = the last V4 main-pool row's `depth1_eth` in the 24 h before the call (V4 only; V2/V3 null — not in the tape).
  `prior_calls` = events on the coin strictly earlier (any chat, mirrors included); `prior_chats_other` = distinct OTHER chats among them.

## Flags
- `no_price` — no candle within 30 min before the call (row kept, path fields null).
- `partial_v23` — main pool V2/V3 and call day < 2026-09-08 (those tape days are ~14 % samples, R-0098).
- `lock_pool` — any main-pool V4 row in the window from v4-join `src: lock` on 09-12 ... 09-18 (R-0114: can carry the wrong pool).
- `pre_v4_join` — window starts before 2026-07-20, where both joined V4 sources begin. V4 swaps before that exist in the raw
  locked tape (R-0106: collected, not absent) but are not joined into any source this build reads, so a V4 coin there reads as
  no_price or as its V2/V3 pool.
- `v4_locked_window` — window overlaps 09-12 00:00 ... 09-18 22:40Z, when the V4 source holds the locked pool set only.
- `v23_tail_livetape_only` — see Seal.

## Resources / hygiene
A4 gate (`edge-machine-2026-09-30/engine/a4.sh`) before each heavy step; nice 19 / ionice idle; `df -h /` > 60 GB before and during;
extracted rows gzip only; every intermediate deleted at the end (listed in REPORT.md). Budget 6 h.

## ADDITION 2026-09-30 ~08:15Z — after day 7 (owner request, "are there any coins that pump crazy after 7 days?")
Added after the first build, before its report; the 24 h fields above are unchanged by it (checked by diffing the two builds).
Per row, only when `ts + 7 d < seal`, a `late` object from the SAME main pool and the same cleaned candles, rows < seal only:
- `days_seen` = (seal − ts) / 1 d — days of data after the call before the seal.
- `last_print_days` = days from the call to the coin's last $5+ print (any pool) before the seal.
- `prints_after_d7` = $5+ prints on any pool from call + 7 d to the seal; `dead_by_d7` = that count is 0.
- `px_d7` = last main-pool close at or before call + 7 d (any age; `px_d7_age_min` states the age); null if no candle after the call.
- `peak_after_d7` = highest main-pool candle HIGH from call + 7 d up to the seal: `{pct_vs_call, pct_vs_d7, day, candle_usd, candle_close_vs_high}`;
  null if no candle. The last two are sanity fields: one $5 print on a drained pool can make any number (R-0107). `px_d7_candle_usd` likewise.
- `late.flags`: `late_partial_v23` (V2/V3 main pool and call + 7 d < 09-08: part of the window is on ~14 % sample days, R-0098);
  `late_v4_locked_window` (V4 main pool and the window starts before 09-18 22:40Z: 09-12..09-18 holds the locked pool set only, so a
  V4 coin outside that set shows NO trades there — it can look dead and then "revive").
Deviation note: rows kept in memory now run from the first late-eligible call to the seal; `depth1_eth` is capped to the 24 h before
the call so that this cannot change it.

## ADDITION 2026-09-30 ~08:20Z — other-quote guard (coordinator; found by spot-skeleton-2026-09-30 PREREG A5)
A V4 pool quoted in a token other than ETH/WETH/USDG is priced (price_usd, usd) through a causal ETH reference of that quote token, and
that reference can jump — the "AI" token's jumped ~2,500x in ONE print at 2026-08-28 22:17:23Z, inflating price AND usd (so the $5 floor
does not catch it). Per row: flag `other_quote` when the main pool's quote is not ETH/WETH/USDG; for those rows the price at the call and
the 24 h peak are recomputed on the pool's OWN `price_quote` (same rows, same candles, same rules) -> `peak24_quote_terms`; when the
USD peak multiple (1 + pct) exceeds 3x the quote-terms multiple, flag `quote_ref_jump` — that row's peak (and so t10x / pace) is not
to be trusted. The same test runs on the after-day-7 peak (vs px_d7) -> `late.flags: late_quote_ref_jump`,
`peak_after_d7.pct_vs_d7_quote_terms`. Phase 1 now also carries `quote` and `price_quote`. Every row also gets `quote` (the main pool's quote label).

## ADDITION 2026-09-30 ~08:35Z — coord (coordinator, owner request)
`coord` = number of OTHER distinct chats with a call on the same token within +/-60 s of this call, mirror events (mirrorOf set) excluded;
`coord_5m` the same within +/-5 min. From the call list only (all 6,807 events). ⚠️ The backtest's mirror rule marks every other-chat event
within 180 s after a cluster origin as a mirror, so with mirrors excluded `coord` is structurally zero (two non-mirror events in different
chats are > 180 s apart). `coord_incl_mirrors` / `coord_5m_incl_mirrors` count them too, so the question can still be read.

## DEVIATION 2026-09-30 ~09:30Z — liquidity-0 V4 prints are dropped (found in this build, before the report)
Recorder-identical cleaning let V4 rows with liquidity "0" through: their price is the tick-bound value (3.4e50 USD) while their usd size
is real, so the $5 floor passes them. In the first builds they produced 24 h peaks of 1e41 %–1e55 % and counted as 10x calls. The v4-join
README states "rows with liquidity '0' have a meaningless price" and features.py skips them. They are now dropped before the candles
(identified by `depth1_eth == 0`), counted per row as `liq0_dropped` (flag + count, main pool, call ± 24 h). The live recorder has the
same exposure (1 of 206 current charts, PURSER, carries a 2.8e34 high). This is the ONLY cleaning rule that differs from recorder.js.
