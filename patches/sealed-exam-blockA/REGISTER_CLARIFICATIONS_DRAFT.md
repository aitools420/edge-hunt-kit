## ✅ PRE-READ CLARIFICATIONS — registered 2026-10-06, before any sealed read (answers to pond #322; nothing here changes code)
Each item fixes a reading that the register and the runner left open. Where pond asked for something not done before the read, it says so.

1. **What decides (pond #322 §3 a/b).** The registered primary draw (SEED 20260927, the 09-27 pass composition) decides the verdict exactly
   as `tools/report.py` computes it. The 20-seed sensitivity never changes that verdict. For any USE of the result (the real-money gate,
   any public claim), a PASS counts only if report.md says the sensitivity AGREES; a PASS with DISAGREE is read as **"PASS, draw-dependent"**
   and does not qualify. A NOT SHOWN is never upgraded by the seeds; if ≥ 10 of 20 alone seeds pass, it is labelled "NOT SHOWN,
   draw-dependent". (This is pond's asymmetric rule, adopted as a reading rule; the computation is unchanged.)
2. **The other cells of the two passes (§3 f).** The primary passes run all 4 cells of the rule #1 engine and all 24 of the rule #2 engine,
   only to keep the 09-27 pass composition (one shared random stream). Only C2P and D25L48 are analysed (`tools/stats_rule.py` keeps the exam
   cell only). The other cells' rows stay inside the engine output files, whose sha256 are recorded in report.md. They are never analysed,
   posted or used. Any later use of them counts as a Block A read for that hypothesis.
3. **Signals, not entries (§4 a).** Every window bound is on the ASSESSMENT (signal) time. The entry follows by the engine's own fill rule (up
   to its 1 h fallback). A position still open at the data end books as `end`.
4. **Last assessment (§4 b).** Both rules use the BLOCK EDGES rule registered 2026-10-05 ~19:05Z: last assessment = CUT − (max hold + 1 h).
   Rule #1 (48 h hold): 2026-10-04T23:00Z. Rule #2 (24 h hold): 2026-10-05T23:00Z. The frozen grid's own constant (09-25T20:00Z) sat 28 h
   before its seal; so, beside the verdict and NOT part of it, rule #2's signals from 2026-10-05T20:00Z onward and its `end` rows are
   reported separately by a descriptive script outside the pinned runner.
5. **Data end (§4 c).** CUT = 2026-10-07T00:00:00Z for both rules. The V2/V3 rows of 10-06 23:00–24:00Z are in the 10-07 file. The runner
   reads it at 03:00Z (cut + 3 h), keeps rows with ts < CUT, and records the sha256 of exactly what it kept (row `v2v3-tape-cutA`). The
   file itself is still open then; the hashed cut copy is what is registered. The V4-wide 10-07 file is handled the same way (`v4-wide-cutA`).
6. **Start (§4 d).** The run reads from 2026-09-24T00:00Z with no carried state. 72 h of warm-up make the V4 history, the 72 h lookback,
   the fee estimates and the main-pool state full at the first assessment, 2026-09-27T00:00Z. No signal before 09-27 is assessed, so none
   sets held-set or cooldown state.
7. **What PASS means (§7).** As registered: Holm k = 2 on the one-sided p (normal approximation on SE_cons) AND d > 0 AND the lower bound >
   0, where the lower bound is the frozen analyzer's 2.5th percentile of its day-block bootstrap (unchanged code). n = PAIRED trades (a
   strategy trade with a booked activity twin): ≥ 300, on ≥ 60 coins. Plus drop-5 d > 0 and the data gate. A rule short of n or coins
   reads NOT SHOWN, and its p stays in the Holm family as computed (a missing p counts as 1).
8. **Error budget (§8).** Nominal: 2.5 % one-sided family-wise per block (Holm k = 2), about 7.3 % over Blocks A–C if each is read once at
   that level. pond's simulation suggests the real rate may be 1.5–2× nominal on lumpy days. Recorded as a caveat; no change.
9. **The two 09-27 additions, verbatim (§2 a/b).** Rule #1's section (registered ~08:35Z): "skip V4 entries with depth1 < 0.001 ETH
   (strategy and twins alike)". Rule #2's section (registered ~09:25Z): "skip V4 entries with depth1 < 0.001 ETH; draw twins WITHOUT
   replacement" (both rules). The earliest surviving copy of the register file is the 2026-10-02 08:29Z backup. The port's source,
   `blood-grid-window-history-2026-09-27/engine_wh.js`, sha256 `127218368d46c4c078d3b01eaf6f9cc08862e10d21cb32f2e1548556c56e5a96`,
   was last written 2026-09-27T08:55:47Z, before rule #2's registration. **Principle (§2 d): the registered text governs and the code is
   corrected toward it** (Option A). On the open days the two additions changed 0 strategy rows of either exam cell (proof/PROOF.md), so
   the frozen-code reading can differ only through twin draws. It is not run as a separate sensitivity.
10. **Pool orientation pinned (§6 e) — a CODE change, found by Test B on 2026-10-06.** The join's fallback rule (a pool with no named token
    takes as its quote the currency seen in more pools) counts over the WHOLE table, so the larger exam table flipped 45 of the 663,994 pools
    both tables know (on 09-20..09-24, 4,480–14,509 joined rows a day differed from the 09-27 join, 4,300–10,725 of them in token, side and amounts; the rest in price only, from the test join's shorter warm-up). Fix:
    `join/pools.js` (via `join/make_join.py`) keeps the 09-27 orientation for all 113,599 pools the 09-27 table oriented by rule or by
    Initialize log (`join/orient_0927.json`, made by `join/make_orient.js` with the 09-27 pools.js, read-only, sha256 in pins/inputs.sha256).
    Flips after the pin: 0. New pools keep the unchanged rule. Test B re-run on the fixed join (2026-10-06 08:57Z): 09-21..09-24 now
    IDENTICAL row for row to the 09-27 join (0 differing rows; before the pin 4,480–10,725 a day). Two explained edges remain: the join's
    FIRST day (09-20, 5,878 rows: causal other-quote prices with a short warm-up) and the last hour before the CUT (09-25, 69,729 rows:
    ETH/USD is linear between hourly points and the exam keeps only points before the CUT, so the last hour holds the last price where
    the 09-27 join interpolated toward a point after it — the exam is the stricter, it never looks past the CUT).
11. **Not done before the read, said plainly:**
    - the 20-seed JUDGE distribution (§3 e): ~38 engine runs, about 10 h on this box;
    - a draw-averaged primary (§3 c): new code, not built;
    - publishing the exam code to the public kit before the read (§1, §5 a): the owner's decision.
