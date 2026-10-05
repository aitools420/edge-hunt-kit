# PRE-REGISTRATION — Callers FAST ENTRIES, batch 1 (2026-10-02, Chef TG 15728 "test much faster entries (15–30 s after the call)")

Written and hashed (PREREG.sha256) BEFORE any return of this study was computed. The engine run r1 was started at 12:53Z, before
this file was hashed; none of its output was opened before the hash (the only reads before the hash are the smoke run on
07-08 → 07-21, used to test the code and the mutation checks). Research only; writes only in this folder.

## 0 · Status, stated up front
- **5th read of these days** (callers round 3, callers-v4, the dial test, callers-fill1, this). Family on these days before this
  batch: K = 796. Nothing here can be an edge; a cell whose 95 % lower bar is above 0 AND survives Holm is a LEAD to pre-register
  for a fresh sealed block, nothing more.
- ⛔ Sealed holdout: nothing with ts ≥ 2026-09-27T00:00Z is read. The engine refuses LAST_DAY ≥ 09-27, never opens
  tape-2026-09-27, raises on any row ts ≥ 1790467200; the analyzer asserts every entry and exit ts < 1790467200.
- ⛔ No noxa.bot fee anywhere (f-nonoxafee). Local files only; no RPC at all in this study.

## 1 · Data and engine (= callers-fill1 pass B, byte for byte)
- Call set, levels, bands, pool table: pass B's `calls_snapshot.json` (5,673 study rows), `calledmeta.json`, `levels.json`,
  `bands.json`, `poolfee.tsv` (symlink) — sha256 below. V4 = backfill-join 07-20 → 09-11 (pass B's cut, Amendment 1) ∪ v4-join;
  V2/V3 = the robinhood tape; DATA_END 2026-09-26 21:40:49Z (pass B's Amendment 2).
- `engine.py` byte-identical to pass B's (sha256 311370c9…). `engine_fast.py` exec()s it with asserted text replacements only:
  delays (5, 15, 30, 60 s); 14 holds (75 s … 11 d — a superset of pass B's 10); several take-profits booked in one stream pass
  (each (delay, take-profit) gets its own positions; the take-profit test reads `p.TP` instead of the global `TP`); output also
  carries the clip in ETH and unrounded depths (outputs only). Run r1 = TP +50 / +25 / +100, run r2 = TP none / +150 / +200.

## 2 · Entry, exit, twins (pass B's rules at every delay)
Buy at the first accepted print of the coin at or after post + d (d = 5, 15, 30, 60 s), within 300 s, else no fill; V4 entries at
the cheapest fresh pool's state at that print; $50 clip; sell at the take-profit (booked within 60 s after the trigger) or at the
end of the hold, on the entry pool; 3 matched random coins (same age and activity band, not called in 24 h) bought the same way at
the same moment, same exits, same costs. FEASIBILITY.md §3–4: 5 s is priced as a BOUND (not reachable with today's executor).

## 3 · Costs — two models on the SAME trades (`costs.py`)
- **REAL (headline):** per side = LP fee + launchpad take (Pons: hook + creator tax from launch terms, R-0111; Doppler: the
  median receipt-measured LP + hook take, 1.7 %) + transfer tax (realism tax table) + ETH↔quote-token hop when the pool is not
  ETH/WETH-quoted (R-0115: `hop_static.json` = per quote token, the median over 3-hourly moments of the cheapest router route for a
  0.02 ETH leg, from the estate's existing hop tables; tokens with no route → the median over 'other' tokens, 2.8 %/leg; USDG
  0.06 %/leg) ; price impact = the engine's own depth model ; V2/V3 = realism `cost_per_side` (measured fee tier per coin where held,
  else 1 % V3 / 0.3 % V2, measured impact per ETH × clip, tax) + USDG hop for USDG-quoted tape rows ; gas = realism `gas_pts`
  (measured, incl. failed attempts) + half a swap's gas per hop leg. Pool classification order in `costs.py`.
- **OLD (= what the explorer's Callers points show):** the engine's own booked number (V4 engine fee in the depth model,
  V2/V3 1 % + 1 %, gas 0.2 % of the clip). The old-cost formula in `costs.py` must reproduce the engine's number on every mark.
- NOT modelled (named, G11): hook take on 'other hook' pools (counted per cell group), Doppler sell-side quote take, tax changes
  over a coin's life, coins missing from the tax table (0 assumed; share reported), MEV / sandwiches / competing bots at a fast
  entry, the price of a failed buy (only its gas), ETH booking of V2/V3 trades (USD, as the engine).

## 4 · Cells (48, `cells1.json`, built by `cells.py`)
delay {5 s, 15 s, 30 s, 1 min} × hold {15 min, 1 h (held), 24 h} × take profit {+50 % (held), +25 %} × caller tier {All, Good}
— Good = the explorer's best tier at the held settings (pass B: +1.8 vs Elite −6.3, Other −1.9). Everything else held (all
market caps, run-ups, first/follower, callers count, ages, sources). The 12 one-minute cells are the BRIDGE; 9 of them are cells
pass B computed (their OLD view must reproduce pass B exactly) and are flagged rereadOf.

## 5 · Per-cell metrics (pass B's, verbatim code) and family
- `analyze_fast.py` exec()s analyze.py's statistics block (sha256 9f136a7d…) unchanged: n, coins, callers, days, mean, 95 %
  range = mean ± 1.96 × conservative SE (max of iid, caller, coin, day, coin×day bootstrap, block bootstrap; B 4,000), median,
  d vs 3 matched random coins (same SE), drop-5 coins, no-repeats, hit share, TP share, era and lane (direct / CallAnalyser)
  splits, ex-outage, ex-G5 view (positions with zero-cost gain > +1,900 % removed — pass B's Amendment 3; the HEADLINE view).
  Coverage: share of the level's study rows priced (call booked with ≥ 1 booked twin), filled, pending, tight-filled.
- Added views: OLD cost (same code); TIGHT (call and twins filled within 15 s of post + d); PAIRED (same calls booked at this
  delay and at 1 min: mean difference at real cost, with its range; and at old cost).
- Family: **Holm, one-sided α 0.025** (= a 95 % lower bar above 0), across all 48 real-cost cells with n ≥ 30, separately for
  the mean and for d. Reported: count of cells with lower bar > 0 vs expected by chance (0.025 × cells with n ≥ 30).
- Seeds: 20260930 + 11 × cell number (pass B's convention); a re-read uses pass B's cell number in its OLD view.
- Decomposition reported per group: explorer value (old cost, 1 min) → cost change (real − old at 1 min, same trades) →
  delay change (real at d − real at 1 min; and the paired, same-calls version).

## 6 · What would count (decided now)
- "Faster entry turns a red square green": a dial-pair square involving delay is red while the best (and the median of the
  best) of its tested setting pairs is < 0. Reported: every fast cell whose real-cost ex-G5 mean is > 0 (would colour its
  setting pair green), and whether its lower bar is > 0. A positive mean alone is NOT evidence (5th read, multiple tests).
- A delay effect is "shown" only if the PAIRED range excludes 0.

## 7 · STOP checks — any RED ⇒ no results published, report the failure
a. `check_delay.py` GREEN on the full run (C1 first-print rule, C2 ets ≥ post + d and lag in [0, 300], C3 cross-delay order,
   C4 take-profit copies share the entry). Mutation test (done on the smoke run, logs in runlogs/): mutant A (every call starts at
   post + 60 s) → RED, mutant B (fills 10 s early) → RED; unmutated → GREEN.
b. `bridge_rows.py r1 50 25 100` and `bridge_rows.py r2 none`: this run's 1-minute positions identical to pass B's, row for row,
   every field pass B wrote (holds mapped by value).
c. Old-cost recompute = engine number on every booked mark (`analyze_fast.py` asserts; `check_old.py` mutant → RED, done on smoke).
d. The 9 re-read cells' OLD-view records identical to pass B's records (every statistic field).

## 8 · Box rules
A4 gate before every heavy pass (`a4.sh`: available > 3 GB, swap-used not rising > 64 MB over 60 s, load < 8, no bigdog); one
heavy pass at a time; wall-clock budget ≤ 6 h for both batches (start 12:40Z); big intermediates (rows_fast_*.ndjson) deleted at
the end (rebuildable with `run_full.sh`).
