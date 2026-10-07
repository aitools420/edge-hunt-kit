## ✅ PRE-READ CLARIFICATIONS — registered 2026-10-06, before any sealed read (answers to pond #322); amended 2026-10-07 on pond #330 (items 1, 7, 11-14; items 1, 7, 12, 13 and 14 are now CODED in the runner and report)
Each item fixes a reading that the register and the runner left open. Where pond asked for something not done before the read, it says so.

1. **What decides (pond #322 §3 a/b; amended 2026-10-07 on pond #330 M5, Chef TG 17135).** The registered primary draw (SEED 20260927,
   the 09-27 pass composition) decides the verdict exactly as `tools/report.py` computes it. The 20-seed sensitivity never changes that
   verdict. For any USE of the result (the real-money gate, any public claim), **a PASS QUALIFIES iff the primary PASSES and at least 10 of
   the 20 alone seeds PASS** (the 50 % share). The sensitivity AGREES iff at least 10 of the 20 alone seeds reach the primary's verdict.
   The exam cell alone at SEED 20260927 (one of the 20) is still computed and printed, **as information only**: it is no longer a condition
   of AGREE or of qualifying (the 4884d01 code required it as well; pond's simulations showed that extra veto bought 0.0–0.6 points of
   false-qualify for 1.3–6.4 points of power). report.md prints one READING line per rule with the registered label and the PASS-seed
   count: **PASS** (qualifies) · **PASS, draw-dependent** (primary PASS, fewer than 10 of 20 seeds PASS; does not qualify) · **NOT SHOWN** ·
   **NOT SHOWN, draw-dependent** (≥ 10 of 20 alone seeds PASS; never upgraded) · **CAN'T TELL (data)**; report.json carries
   `qualifies: true/false`. This is pond's asymmetric rule as pond stated it, now as coded (tests/testR R1, R2, R10).
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
   reads NOT SHOWN, and its p stays in the Holm family as computed (a missing p counts as 1). **A CAN'T TELL (data) rule enters Holm with
   p = 1** (pond #330 M6, Chef TG 17137, 2026-10-07), so the other rule must clear 0.0125 (alpha / 2 of the 2.5 % family) on its own
   (tests/testR R3: rule #1 gate FAIL at p 0.001 and rule #2 at p 0.02 → rule #2 NOT SHOWN; R4: the same with rule #1's gate PASS →
   rule #2 PASS at Holm step 2).
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
11. **Not done before the read, said plainly (updated 2026-10-07):**
    - the 20-seed JUDGE distribution on the open days (§3 e): IN PROGRESS, not finished (seeds20/driver.log; at 2026-10-07 ~07:00Z
      rule #1 had seeds 20260927-20260929 and rule #2 seeds 20260927-20260930, and one run, rule #1 seed 20260930, failed for a plumbing
      reason and must be re-run); it will not be complete before the read if the read starts first;
    - a draw-averaged primary (§3 c): new code, not built;
    - the pond #330 MEDIUM and LOW items not listed in clarifications 1, 7, 12 and 13 (M1-M4, M7-M9; L1, L3, L5-L15, L17, L18, L20,
      L21): not done; each is a limit of this exam as registered. Done with #330: L16 (64-hex hashes in report.md and runs.tsv) and
      L19 (the cut rows are written whole to work/state/cut_rows.tsv; the runner no longer appends to tape-hashes.tsv).
    - DONE since 2026-10-06: the exam code was published before the read (commit 4884d01, reviewed in pond #330); Test B was re-run after
      the orientation pin and its consist files are now gated (clarification 10, B1).
12. **CAN'T TELL (data) is final for Block A (pond #330 L4, Chef TG 17139, 2026-10-07): no re-run, no re-draw; that rule waits for
    Block B.** The runner honours it: a written report creates work/state/FINAL and every later start refuses (Test C H2f); a data-gate
    failure never prints that rule's d / CI / p / n (primary or alone seeds); they go only to work/withheld_stats.json, whose sha256
    report.md prints (pond #330 H2; tests/testR R5, R9).
13. **The memory guard (pond #330 L22, Chef TG 17141, 2026-10-07).** If an exam engine's RSS guard (engine_st_exam.js ~:475 /
    engine_grid_exam.js ~:424 and the _h copies, 3.2e9 bytes) or the heap cap (tools/run_engine.sh ~:34, 3,000 MB) fires, **the only
    allowed change is raising that cap; the new file hash is posted publicly before that engine re-runs; nothing else may change.** The
    runner refuses that failure with class CAP and resumes only through a recorded cap change it can verify (one line changed, the cap
    line, to a larger number, after that cap fired); anything else is exam-ending (Test C L22a-g). Peak memory recorded on open data
    before the read: REGISTER_DRAFT.md, "Refusals, resume and deviations".
14. **What the runner now enforces rather than reports (pond #330 B1, H1, H2, H3):** the 09-25/09-26 seam (a refusal before any engine;
    bound and field list fixed on open data, tests/testB/seam_bound_evidence.json); pin files anchored in the runner and the block days
    against a pinned file; every step's outputs hashed and re-checked; engine hashes in runs.tsv against the pins; refusal classes
    (RESUMABLE / END / CAP) read at every start; commit-reveal between phase 1 and phase 2. Text: REGISTER_DRAFT.md.
15. **An engine that dies without completing, and the runner killed (coordinator 2026-10-07, after pond #330 H2).** Registered: "an
    engine that dies without completing (kernel kill, no complete output) is re-run unchanged; the death and the re-run are disclosed in
    report_files; nothing else may change; a partial output is never read." Killed or stopped from outside counts: SIGKILL (137, e.g. the
    OOM killer), SIGTERM (143, e.g. a reboot or shutdown), SIGHUP (129), SIGINT (130). It happens before any statistic for that run exists,
    so it is RESUMABLE, like a network failure. The runner recognises it from what the unchanged run_engine.sh records (the exit code in
    runs.tsv with GNU time's matching "Command terminated by signal N", or no runs.tsv row for the attempt). The RSS guard and the heap cap
    stay CAP (item 13); SIGABRT that is not the heap cap and an engine that exits non-zero by itself stay END; a refusal once step 9 has
    started is END. If the RUNNER itself is killed (a reboot stops the whole tree), the next start redoes the unfinished step from scratch,
    re-verifies the finished ones, re-runs an interrupted engine as above and resumes an interrupted step 9, disclosed (Test C K1-K7,
    KR1-KR3).
