# Can a Callers entry at 5 s, 15 s or 30 s after the call be priced honestly? (feasibility, written BEFORE any result)

Chef TG 15728: "Callers: test much faster entries (15–30 s after the call), since delay is the red axis."
§1–§4 were written 2026-10-02 ~13:00–13:20Z, before any return of this study was computed. They use only timing fields
(when prints happened), never a return. §5 (coverage at each delay) is filled from the engine run's fill/timing fields only,
and is marked as such.

## 1 · Time resolution of the call
- A call's time is the Telegram **message date** (both lanes stamp the message, not our ingest — calls audit §6), integer
  seconds. All 6,740 events in the frozen call set have integer `ts`.
- 61 % of study rows (3,444 of 5,673) are **CallAnalyser reposts**: their time is the aggregator's repost, not the KOL's call.
  The other 39 % (2,229) are direct group posts read by our bot.

## 2 · Time resolution of the swap tape
- V2/V3 tape and V4 rows both carry the **block timestamp** (integer seconds) plus block number and log index. Robinhood Chain
  makes ~3 blocks a second, so several blocks share one timestamp.
- So both clocks tick in whole seconds. A delay of d seconds is known to ±1 s: ±20 % at 5 s, ±7 % at 15 s, ±3 % at 30 s.
  Assumption: Telegram's server clock and the chain's block clock agree to within ~1 s (not measured here).
- Completeness (what can be priced at all): V4 is complete for 07-20 → 09-11 (backfill, pass B's data), locked-set only for
  09-12 → 09-18 22:40, complete again after. V2/V3 is a ~14 % sample of each day before 09-08 (R-0098) and drops 11–28 %
  of swaps a day on 09-07 → 09-15. A missing print can only make a fill LATER (or absent), never earlier.

## 3 · The pricing rule, and why it has no look-ahead
- Rule (unchanged from callers-fill1 pass B, applied at each delay): buy at the **first accepted print of the coin at or
  after post + d**, if it comes within 300 s (else no fill). On V4 the entry is priced at the cheapest fresh pool's state at
  that print. The 3 random twins are bought the same way at the same moment. Exits are on the same pool.
- Nothing after the fill print is used to decide the entry, so there is no look-ahead into the outcome.
- What it does NOT promise: that the fill happened AT post + d. If the coin is quiet, the "15 s" fill can be the same print as
  the "1 min" fill. Measured on pass B's own 1-min entries (timing fields only): fill lag after post + 60 s p50 4 s, p75 21 s,
  p90 81 s; 70 % within 15 s. So the study reports, beside every cell, a **TIGHT view** (call and twins filled within 15 s of
  the entry moment) and a **PAIRED view** (the same calls at this delay minus at 1 min), so a delay effect is not confused
  with a sample change.
- First accepted print of the coin after the post (pass B rows, timing only): within 0 s (same second) 15.6 % · 5 s 31.5 % ·
  15 s 41.0 % · 30 s 46.7 % · 60 s 51.5 % · 300 s 58.3 % · never in 24 h 13.8 %. Direct-lane calls are much quieter
  (5 s 14 % · 60 s 31 % · 300 s 40 %) than CallAnalyser reposts (5 s 43 % · 60 s 65 % · 300 s 70 %) — reposts come after
  the coin is already trading.
- Two dials of pass B are NOT ex-ante at a fast entry and are handled in PREREG2: "callers by our entry" is counted at post +
  60 s (look-ahead for a 15 s entry → not used), and the market-cap price may be read up to 6 min after the post (→ a row is
  kept in a market-cap cell only if its price was read at or before the entry moment).

## 4 · Is a 15 s entry physically possible?
- **Direct group posts (39 %): yes.** Our bot receives them with a median 1 s ingest lag (p99 16 s, calls audit §6). A buy
  confirms on Robinhood Chain in a median 1.1 s over all time, 5.7 s in September (p90 7.5 s) (realism latency.json,
  submit → confirm). So call + 15 s is reachable with a fast path; call + 30 s comfortably.
- **5 s: only at the edge.** 1 s ingest + 5.7 s September confirm already exceeds 5 s; it needed July's 1.1 s confirms. And
  ±1 s timestamp resolution is ±20 % of the delay. 5 s is therefore priced and reported as a **bound** ("what if we were
  instant"), not as a reachable setting; the fastest honest delay used to build batch 2 is **15 s**.
- **CallAnalyser reposts (61 %): not with today's lane.** We scrape the public page: ingest lag p50 82 s, p90 170 s, p99 60 min.
  Even the explorer's existing 1-min entries are not reachable on this lane today; a 15 s entry would need a live Telegram
  client subscribed to the channel (not built). Every cell reports the direct / CallAnalyser split.
- Our own robots' history is slower than any of this (signal → confirmed median 44 s, p25 21 s, mostly July): reaching 15 s is a
  build, not a setting.

## 5 · Coverage at each delay (filled 13:40Z from the engine run's fill / timing / booked-or-not fields; no return read — `cov_only.py`)
Take profit +50 %, all 5,673 study rows. "Priced" = call booked at that hold with ≥ 1 booked twin (pass B's definition).

| delay | calls | filled (≤ 300 s) | filled within 15 s of the moment | priced 15 min | priced 1 h | priced 24 h | fill lag p50 / p75 / p90 | priced 1 h: direct · CallAnalyser |
|---|---|---|---|---|---|---|---|---|
| 5 s | 5673 | 58.2 % | 41.4 % | 56.5 % | 56.4 % | 54.9 % | 4 / 21 / 73 s | 38.3 % · 68.1 % |
| 15 s | 5673 | 58.2 % | 41.6 % | 56.5 % | 56.4 % | 54.9 % | 4 / 19 / 78 s | 38.3 % · 68.1 % |
| 30 s | 5673 | 58.2 % | 41.4 % | 56.4 % | 56.3 % | 54.8 % | 4 / 19 / 77 s | 38.3 % · 68.0 % |
| 60 s | 5673 | 57.8 % | 40.6 % | 55.9 % | 55.9 % | 54.4 % | 4 / 21 / 81 s | 37.6 % · 67.7 % |

- **Fast entries lose no coverage:** 56.4 % of calls are priced at 1 h at 5 s / 15 s, vs 55.9 % at 1 min (pass B's figure).
  The explorer's "~55 %" stands at every delay. Direct posts are priced far less often (38 %) than CallAnalyser reposts (68 %).
- **The fast fills are really different fills:** of calls filled at both, the 15 s entry fills on an EARLIER print than the 1-min
  entry for 84.9 % (5 s 87.0 %, 30 s 80.2 %); the rest are quiet coins whose first print comes after post + 60 s.
- Fill lag after the entry moment: median 4 s at every delay; 41 % of calls fill within 15 s of the moment (the TIGHT view).

## Verdict
- **15 s and 30 s: priceable honestly** (1-s clocks, first print at/after the moment, no look-ahead, same coverage as 1 min),
  and **reachable for direct group posts**; **not reachable for CallAnalyser reposts** with today's scrape lane (nor is 1 min).
- **5 s: priceable but only as a bound** (±1 s = ±20 %; beyond September's confirm time).
