# EDGE MACHINE — frozen engine v1 (one engine, one cost model, hashed)

`engine_v1.js` = `engine_lf.js` + hunt 3's dials (`quote`, `cap`) + the token-filter features (`tf`), merged verbatim (header lists every diff).
One cost model, `real60h`: per-pool real costs (R-0111), ETH booking, TP sold 60 s after the trigger, ETH↔quote-token hop on both legs (R-0115).
`MANIFEST.json` pins every pipeline file, the frozen input tables (`inputs/`, `pool_costs_v1.json`), the external files the pipeline reads, and
the tape (per day: size+mtime, and a content hash). **`run_batch.sh` refuses on any mismatch** — a changed engine is `engine_v2.js` + a new manifest.

**Write `cells.json`:** `{"cells":[{"id":"D25H72T40X12","params":{"dip":0.25,"th":72,"tp":1.4,"hold":43200,"band":"LOW"}}, …], "pass_size":40}`.
Dials (omitted = engine default): `dip` (fraction under the main pool's high) `W` (window s: 300/3600/86400) `mode` (P main pool / M merged)
`tp` (multiple, 1.4 = +40 %) `hold` `cool` `age` (s) `lat` (entry delay s) `th` (hours of the prior 72 with a ≥ $10 trade) `band` (`LOW` = ≤ 1 %
a side) `quote` (`WETH`) `cap` (max open positions) `padMode` `volMin` `sdMin` `buyMin` `creator` `range` `dh` `L` `last72` `rngId` (twin RNG key).
Unknown dials are refused. Token filter = a SPLIT of a base cell: `{"id":"X_F1","base":"X","filter":{"min_dip_sec":1200}}` (or `min_sells`).
Optional `stat_seed` (bootstrap seed; default from the id) and `labels`. See `prepare_v1.py` for the full contract.

**Run:** `bash run_batch.sh cells.json <outdir>` (env `PASS_NEED` MB, `KEEP_INPUTS=1`, `STOP_DAY` for a smoke). Steps: manifest check → cells
check → inputs → guard test (G3) → engine passes one at a time, each behind `a4.sh` (avail > 3 GB + need, swap not rising, load < 8, no
bigdog, no other engine, not :49–:05; waits, never kills; the watchdog stops only its own engine) → hop tables → batch cost table → reduce → analyze.
`bash test_seal.sh` = the seal refusals (6 tests). Parity with the published hunts: `parity/PARITY.md`.

**Output** `<outdir>/results.json`: `engine_sha256`, `cost_version`, `data_window`, and per cell: `dials`, `filter`, then `JUDGE` (primary) and
`FIT`, each with `n coins n_days days`, `real60h.raw` {`mean median ci95 lower lower_explorer se_cons p_one_sided drop5_trades drop5_coins`
`win_share`}, `real60h.d_vs_A` / `d_vs_R` (twin delta `d_mean` + `ci95`), `real60` (no-hop view, every trade), `exit_reasons`,
`top_coin_share`, `hop_no_route_left_out`, `gate` (G1/G4/G5/G10). `<outdir>/trades.ndjson.gz`, one row per trade (JUDGE and FIT): `cell tok pair T
day half sigTs entryTs exitTs reason ret` (= ret_pct, real60h, null if no hop route) `ret_real60 twinA twinR ePk v4e fb stock pad eQ hopX tfDip
tfSell cost_version engine_sha256` — the `../trades/` store's row (`tok pair T day sigTs entryTs exitTs reason ret ePk v4e fb pad`, with `cell`
for its `pk`; no `eU`/`xU`) plus the version tags.

**Data window:** tape 2026-09-08 → 09-26 (one merged V2/V3 + V4 stream); assessments FIT 09-11 → 09-17, JUDGE 09-17 → 09-25 20:00 (primary).
Nothing ≥ 2026-09-27T00:00Z is read (engine, reducer, hop and trade writer all throw). These days are SPENT (≈3,500 reads): a v1 number is a
map, not evidence — only a VALIDATE / sealed read counts.
