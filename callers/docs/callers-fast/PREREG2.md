# PRE-REGISTRATION — Callers batch 2: green dots where the explorer has none (2026-10-02, Chef TG 15735 via the coordinator)

> "additional back testing on Callers to see if we can get green dots on some of the lines that currently have no dots or orange
> [formula-only] dots, whatever you think has the best chance to get high gains in profit"

Written and hashed (PREREG.sha256, second block) BEFORE any return of batch 1 or batch 2 was computed. Same engine runs, data,
entry/exit/twin rules, cost models, statistics, views, STOP checks and box rules as PREREG.md §1–3, §5, §7–8 — only the cells
differ. Batch 1 ships first. 5th read of these days (with batch 1): leads only, never an edge.

## 1 · Pre-read audit of the explorer's best long-hold point (pass B, already published; read before this file)
"first caller or follower = follower > 24 h, hold 7 d, +50 %, 1 min": +7.46 [−6.7, +21.7], n 354, 199 coins.
Not one coin: the top coin holds 17 % of the summed return (without it +6.24), the top 5 hold 63 % (drop-5 +3.99). But d vs 3
random coins is only +1.64 [−13.4, +16.7] (drop-5 d −2.24), and 327 of its 354 trades are from before 09-05 (later eras −10.9
and −16.3): it is mostly the market's drift in the backfill weeks, not caller skill. ⇒ the long-hold branch is kept but SHRUNK
from the suggested 96 cells to 36, and its follower > 24 h variant is not added.

## 2 · Rules specific to this batch (ex-ante at the entry moment)
- Fastest delay = **15 s** (FEASIBILITY.md §4: the fastest that is both priceable and reachable; 5 s is a bound only).
- "First caller" = pass B's first-caller level (no earlier call of the coin by another caller): known at the post. ✔
- "Callers by our entry" is NOT used: it is counted at post + 60 s, so at a 15 s or 30 s entry it would use the future.
  (It also selects almost the same rows as "first": 1,437 vs 1,463 priced at 7.5 min in pass B.)
- Market cap: a row is in a market-cap cell only if its market-cap price was read at or before post + delay (pass B also used
  prices read up to 6 min after the post); "<$100k" = pass B's bands <$50k ∪ $50k–$100k.
- Caller tier: pass B's tier (judged only on earlier calls). Coin age: pass B's band.

## 3 · Cells (151, `cells2.json`, built by `cells.py`; cell numbers 1001+)
- **B2.1 stacked short-hold branch (60):** first caller × hold {1.25, 2.5, 5, 7.5, 15 min} × delay {15 s, 30 s, 1 min} ×
  {tier All · Elite · Good (market cap All), tier All × market cap <$100k}; take profit +50 %.
- **B2.2 long-hold branch (36):** delay 1 min; hold {5, 7, 9, 11 d} × take profit {none, +100, +150, +200 %} × {all callers,
  first caller} (32) + market cap {<$50k, $50k–$100k} × hold {7 d, 11 d}, no take profit (4).
- **B2.3 least-covered pairs at the held settings otherwise (55):** delay × hold: {15 s, 30 s} × {1.25, 2.5, 5, 7.5 min, 4 h,
  12 h, 72 h, 7 d} (16) + 1 min × {1.25, 2.5 min, 9 d, 11 d} (4) · delay × take profit at 1 h: {15 s, 30 s} × {+100, none, +150,
  +200} (8) + 1 min × {+150, +200} (2) · tier × delay at 1 h: {Elite, Other} × {15 s, 30 s} (4) · tier × hold at 1 min: {Elite,
  Good} × {15 min, 4 h, 7 d} (6) · coin age × hold at 1 min: 5 bands × {15 min, 4 h, 7 d} (15).
- 8 cells re-read a pass-B cell (flagged rereadOf; their OLD view must reproduce pass B — STOP check d).
- Not run, and why: delays 1.75 h / 2.5 h (pushing the delay axis UP, where every measured step loses — lowest chance of profit);
  TP +150 / +200 at short holds (a +150 % move inside 15 min is too rare to change a mean).

## 4 · Metrics and family
Per cell exactly as batch 1 (PREREG.md §5): real-cost ex-G5 headline with conservative 95 % range, n, coins, % of calls priced,
d vs 3 random coins, median, drop-5, no-repeats, era and lane splits; OLD, TIGHT, PAIRED views (PAIRED for 15 s / 30 s cells).
**Holm, one-sided α 0.025, across all 151 real-cost cells with n ≥ 30**, mean and d separately; lower bar > 0 count vs expected.
Family on these days after both batches: 796 + 48 + 151 = 995.

## 5 · Explorer placement
Every record carries `coords_labels` (delay, hold, tp, tier, first, mcap, age as labels). Labels the explorer does not have yet:
hold 1.25 / 2.5 min, 9 / 11 d exist as pushed levels; delay 15 s / 30 s exist; market cap "<$100k" does NOT (two bands merged) —
those 15 cells need a new level or stay unplaced. Multi-dial cells (first × tier, first × market cap) need the loader to place a
point by `coords_labels`, not by `dial`.
