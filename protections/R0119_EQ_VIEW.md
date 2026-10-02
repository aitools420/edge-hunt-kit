# R-0119: the `eq` view

Some V4 pools are quoted in a token other than ETH, WETH or USDG: stock tokens such as NVDA or GME, or memecoins. The tape prices those pools through that token's own ETH reference.
- When that reference jumps, `price_usd`, `usd` and `depth1_eth` jump with it.
- Both the $5 dust filter and the engine's depth exemption to its >20× rule (G5 / `depthok`) can then pass a bad print.
- One spot test booked a single +326,669 % trade this way.

For Blood cells in engine v1, TP and max hold cap every exit, so the damage is bounded. In our 9 candidates the largest single trade is +86.7 %. Even so, an "other"-quoted entry carries more pricing risk.

**Rule:** report the `eq` view beside every result:

    python3 protections/eq_view.py <batch outdir>           # JUDGE half; add --half FIT for FIT

- `eq` keeps only trades whose entry pool quote (`eQ` in `trades.ndjson.gz`) is ETH, WETH or USDG.
- If a cell's result depends on the other-quoted trades, say so.
- On the parity cells, the `eq` view moves means by +3 to +7 points: other-quoted trades are not what carries those cells.
