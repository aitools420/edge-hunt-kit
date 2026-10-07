# sealed-exam-blockA — the one-shot Block A exam runner

Rules #1 (C2P, `engine_st`) and #2 (D25L48, `engine_grid`) of `patches/SEALED-HOLDOUT/README.md`, read once on the sealed
Block A. Built 2026-10-05/06 on OPEN data only: no row with ts >= 2026-09-27T00:00Z was read, analysed or computed from.

**The command: TWO starts after 2026-10-07T00:00:00Z (commit-reveal, pond #330 H3):**

    bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh     # PHASE 1 (steps 0-7): ends by printing the manifest sha256, then STOPS
    # post that sha256 publicly, then:  echo <sha256> > /home/green/projects/patches/sealed-exam-blockA/work/state/MANIFEST_POSTED
    bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh     # PHASE 2 (steps 8-9): re-checks the manifest, runs the engines, writes report.md

It writes `report.md` here (first line: both verdicts, AGREE / DISAGREE, the PASS-seed count, the READING and `qualifies`; next lines:
the sha256 of the runner, the three pin files and the posted manifest), publishes `runs.tsv`, `exam.log`, `REFUSED` and the manifest in
`report_files/`, and keeps everything else under `work/`. Expect about 10–14 h in all: phase 1 waits until 03:00Z (cut + 3 h) and joins
the V4 block (~1–2 h); phase 2 runs 42 engines one at a time behind the box gate. Every refusal has a CLASS in `work/state/REFUSED`
(pond #330 H2): RESUMABLE (network / not ready / an engine that dies without completing — a kernel OOM kill, or SIGTERM / SIGHUP /
SIGINT e.g. from a reboot — all before any statistic exists: start again unchanged; a dead engine is re-run unchanged, its death and
re-run disclosed in report_files/, its partial output never read; if the runner itself is killed, e.g. by a reboot, the next start
redoes the unfinished step and re-verifies the finished ones, and an interrupted step 9 is resumed and disclosed), CAP (an engine's memory cap: resume only after a recorded, posted cap raise, L22), END (everything else: never again
on this work folder; going on is a labelled deviation). Finished steps are re-verified by the hashes taken when they finished. **No setting can change between starts.**

Before running it, the coordinator pastes `REGISTER_DRAFT.md` into the register. The 20 block-day rows (09-27..10-06, both feeds) are
already PINNED in `pins/block_days.tsv` (copied from `tape-hashes.tsv` by `tools/make_pins.sh`, sha256 hard-coded in the runner); the
runner no longer reads or writes `SEALED-HOLDOUT/tape-hashes.tsv` (it writes its two cut rows to `work/state/cut_rows.tsv`).

## What the runner does, step by step (`run_exam.sh`)

| step | what | refuses / waits when |
|---|---|---|
| 0 | clock | REFUSES before 2026-10-07T00:00:00Z, before creating or reading anything |
| 1 | the three pin files against the sha256 hard-coded in the runner (H1); then `tools/exam_checks.py codecheck` on `pins/code.sha256` (every code file incl. the two frozen analyzers; a file may differ only through a recorded L22 cap change) and `sha256sum -c pins/inputs.sha256` (09-27 tables, 09-27 join decimals / unknown keys / warm-up V4 days, hole + backfill tapes, open-day pins); guard_test.js (G3); scam sources' mtime | any hash differs; G3 fails; a scam source changed after 09-27 |
| 1b | waits until 2026-10-07T03:00Z (cut + 3 h) | — (logged every 10 min) |
| 2 | every block day 09-27..10-06, V2/V3 tape and V4-wide: the ONE file the reader finds, uncompressed content sha256 against its ONE row in pins/block_days.tsv (hash-checked); warm-up days against pins/open_days.tsv | a missing row, a missing or ambiguous file, any mismatch |
| 3 | block→time anchors (public RPC, `join/anchors.py`); ETH/USD hourly (CoinGecko range API, points < CUT only) | fetch fails; anchors end < cut + 2 h; ETH/USD not hourly or not covering the window |
| 4 | the cuts: 10-07 V2/V3 tape (rows ts < CUT, read to cut + 1 h), 10-07 V4-wide and the locked V4 tape (rows with anchor time < CUT, read to 100,000 blocks past the cut block; only the `blk` / `ts` field of later rows is looked at); hashes (full 64-hex in exam.log); the two cut rows written to work/state/cut_rows.tsv (`v2v3-tape-cutA`, `v4-wide-cutA`) | waits (10 min, up to 12 h) while a file has not yet passed the margin; refuses on a tool error |
| 5 | snapshot + sha256 of the six ledger / state files the builders read (work/ledgers); tables (below) | label commit or file hash differs; the 09-27 table is not a byte prefix of the exam table |
| 6 | the V4 join (below), then a row-by-row comparison of the joined 09-25 and 09-26 with the 09-27 join's own files and the B1 SEAM GATE (`tools/exam_checks.py seam`, before the join is marked done and on every later start) | any step fails; pass1 sees a row at/after the cut; a block day has no joined file; 09-26 differs at all, or 09-25 differs outside the five other-quote price fields or on more than 5,878 rows (END) |
| 7 | V2/V3 links for the engines: work/tape → the verified day files + the 10-07 CUT copy; END OF PHASE 1: `work/state/manifest.sha256` written, its sha256 printed, STOP | — |
| 8 | PHASE 2: MANIFEST_POSTED = the manifest's sha256, every manifest line and every finished step re-hashed; then 42 engine runs, one at a time, nice 19 + ionice idle, behind the box gate, `tools/exam_guard.js` preloaded; a finished run is reused only if its runs.tsv engine hash is its pin and its output content matches runs.tsv | not posted yet (RESUMABLE); any mismatch (END); a run stopped by its RSS guard / heap cap (CAP); an engine killed or stopped from outside without completing — exit 137/143/129/130 with GNU time's matching "Command terminated by signal N", or no runs.tsv row (RESUMABLE: re-run unchanged, disclosed in ENGINE_DEATHS, partial output moved aside unread); any other failed run (END) |
| 9 | everything re-checked again; statistics (`tools/stats_rule.py`; a stats file is reused only if computed from exactly that output) and `report.md` (`tools/report.py`: any failure writes nothing); work/state/FINAL; report_files/ | any check or step fails (END); a later start after FINAL (END) |

## The policy, point by point, and how it is implemented

1. **Window.** Data 2026-09-24T00:00Z → CUT 2026-10-07T00:00:00Z (1791331200). One exam window: first assessment 09-27T00:00Z
   (FIT0 = JUDGE0). **Rule #1: last assessment 2026-10-04T23:00Z = CUT − 49 h** (the frozen spec, report.txt §7, coordinator
   decision 10-05; max hold 48 h), so signals < 10-05T00:00Z. **Rule #2: last assessment 10-05T23:00Z**, signals < 10-06T00:00Z.
   C1 (in rule #1's pass, not an exam cell): last assessment 10-05T23:00Z. Positions open at the data end book as `end`.
   The warm-up 09-24..09-26 makes the 72 h history lookback exactly full at 09-27T00:00Z (the first V4 row of 09-24 is at
   00:00:00Z). The 10-07 V2/V3 file holds 10-06 from ~23:00Z (R-0109); the 10-07 V4-wide file holds 10-06 from ~23:42Z (measured on
   the open 09-25 file: 09-24T23:42:42Z → 09-25T23:42:57Z); both are read CUT at CUT. Block days are verified against
   tape-hashes.tsv (`tools/days.py`).
2. **Engines.** Two steps, each with its own diff:
   - `engines/engine_{st,grid}_A.js` = the twin-cache engines + **Option A** (coordinator 10-05): FIX 1 twins drawn WITHOUT
     replacement (min(3, pool) distinct coins, partial Fisher–Yates on the same stream) and FIX 2 the V4 depth floor (an entry whose
     pool depth1 < 0.001 ETH is skipped at fill, strategy and twins alike, as a counted `skipDepth` row, no cooldown) — ported
     verbatim from `blood-grid-window-history-2026-09-27/engine_wh.js` (`engines/make_A.py`, `engine_*_A.diff`). This is LOGIC.
   - `engines/engine_{st,grid}_exam.js` = the A engines + window CONSTANTS and the reader's path (`engine_*_exam.diff`, generated
     by `tools/set_constants.py` from `exam_constants_*.json`, every anchor asserted once).
   - `engines/v4tape_exam.js` = v4-join `v4tape.js` + paths and seal constants (`v4tape_exam.diff`): warm-up V4 days from the 09-27
     join, block V4 days from the exam join, V2/V3 through `work/tape`; it refuses days >= 10-08 and rows >= CUT.
   - The analyzers are NOT copied: their only window constant (JUDGE0 = 09-17) puts every exam row in their JUDGE half, so the frozen
     files run unchanged (hash-checked). **New code (stated plainly):** the pre-filter in `tools/stats_rule.py` drops and counts the
     `skipDepth` rows before the frozen analyzers' own code runs.
3. **Tables (no look-ahead).** `builders/` = path-only copies of `tokmeta.py`, `mkmeta.py`, `mkpoolfee.py`; `join/meta.js` =
   path-only copy (it writes `work/v4join/meta.json`, never the hunter's pinned file). Labels from `lib/launchpads.js` at
   `e5c559ec` (last commit before the seal, 09-26T02:21Z; sha256 1b939aea…; identical to the working tree and to what tokmeta.py
   read on 09-27), via read-only `git log`/`git show`. `tools/tables.py`: every 09-27 row is kept VERBATIM (the rebuild's
   differences are reported, never used — deviation 4); new rows kept if born before 2026-10-06T00:00Z or of unknown birth (as on
   09-27); the 09-27 rows first, in their order, so the 09-27 table is a byte prefix of the exam table (checked) and no old coin can be
   relabelled. The builders read a hashed SNAPSHOT of the ledgers (work/ledgers), so the recorded hashes are exactly what was read. scam.tsv = the 09-27 table (9988ebfa…), its three
   sources' mtimes re-checked.
4. **V4 join.** `join/` = the 09-27 v4-join tools (`make_join.py`, `*.diff`): paths; pass1 with the CUT and a first join day 09-25
   (a range filter: rows at/after the cut counted — there must be none — and rows before 09-25 dropped); finalize with SEAL = CUT.
   New glue (the 09-27 run's hand steps, not kept): `glue.py` (new-unknown-pool split/merge, poolcounts, consistency compare),
   `addr_lists.js` (decimals' inputs), `cut_v4.js`, `fetch_ethusd.py`. Built only inside run_exam.sh after the instant.
5. **Runs.** PRIMARY: `engine_st_exam.js` (4 cells) and `engine_grid_exam.js` (24 cells), SEED 20260927. SENSITIVITY: the exam
   cell alone (`engine_*_exam_h.js`, H1 ONLY_CELLS + H3 EXAM_SEED, the only seed hook) for SEEDS 20260927..20260946 (the first is
   sensitivity (1)). Verdict, Holm k = 2 and the AGREE rule: see `tools/report.py` header and REGISTER_DRAFT.md.

## Tests (open data only, seal_guard preloaded on every engine run) — results in `tests/` and `proof/`

(see "Test results" below)

## Deviations from the brief (each decided or forced, none silent)

1. **Option A (coordinator decision, 2026-10-05).** The register's 09-27 additions "skip V4 entries with depth1 < 0.001 ETH" and
   "draw twins WITHOUT replacement" need engine LOGIC, which the twin-cache engines did not have. They are ported from engine_wh.js
   into `engine_*_A.js` (logic diff `engine_*_A.diff`); the exam engines are the A engines + constants only. The pre-filter that drops
   `skipDepth` rows before the frozen analyzers is new code (`tools/stats_rule.py`). Proven in `proof/` (PROOF.md).
2. **Rule #1's window (coordinator decision, 2026-10-05):** last assessment 10-04T23:00Z = CUT − 49 h (frozen spec), not 10-05T23:00Z.
3. **Test A's reference:** the stored twinfix outputs can no longer be reproduced byte for byte, because Option A changes logic. Test A
   compares the exam engines (constants set back) with the Option A engines' own outputs on 09-08..09-26; the chain to the stored
   twinfix outputs is the Option A proof (FIX 1 and FIX 2 attributed row by row against twinfix's `_rk` outputs).
4. **09-27 rows are kept verbatim, not taken from the rebuild.** On open data (2026-10-05) the rebuilt meta.tsv differs from the
   09-27 table on 4 of 471,683 old rows, every one because a ledger learned something AFTER the seal: 3 coins with birth `-` on 09-27
   whose first pool came during the block (birth became 09-28 / 10-01 / 10-05), and 1 coin `unknown` on 09-27 whose minter the
   minters ledger learned later (it would now read `Pons` and enter the universe). poolfee: 0 of 550,395 differ. Taking those rows
   from the rebuild would put block knowledge into old coins, so `tools/tables.py` keeps every 09-27 row verbatim (the 09-27 table is
   a byte prefix of the exam table; the runner checks it) and reports every rebuild difference by kind in report.md §9.
5. **The analyzers are not copied:** their only window constant (JUDGE0 = 09-17) already puts every exam row in their JUDGE half, so
   the frozen files run unchanged; the brief's "constants-only diff for the analyzers" is an empty diff.
6. **The 10-07 files and the locked tape** are cut by the runner itself and their hashes recorded at run time (coordinator decision);
   the cut waits until 03:00Z (READY_AT) so the writers are past the cut by the margin (V2/V3: 1 h; V4: 100,000 blocks ≈ 2.8 h).
7. **The V4 join starts at 09-25, not 09-27:** finalize prices "other"-quote pools causally from the last 24 h, so one full day of
   warm-up rows is joined first; the joined 09-25 and 09-26 are not used by the engines (they read the 09-27 join's own files for
   09-24..09-26) and are compared row by row with them as a plumbing check.
8. **Glue the 09-27 join did by hand** (poolcounts, decimals' address lists, new-unknown-pool split/merge) is new code in
   `join/glue.py` and `join/addr_lists.js`; only NEW pre-ledger pools and NEW tokens go to the network.

9. **resolve_unknown.py is paged.** Found by test B2 on 2026-10-05: the official RPC now refuses `eth_getLogs` over more than
   100,000 blocks when a topic position holds several values and over more than 10,000,000 blocks with one value, so the 09-27
   tool's full-range batch query fails today. The exam copy sends the SAME query one pool id at a time in 10,000,000-block windows,
   walking back from the pool's last swap; parsing and output are unchanged. Test B2: 12 pools (incl. the 6 earliest-initialised)
   resolve to keys identical to the 09-27 file; decimals.js (unchanged logic) returns the 09-27 decimals for 6 tokens.

## Risks for the exam

- **Network at exam time:** public RPC (anchors, decimals), the official RPC (Initialize logs of new pre-ledger pools), CoinGecko
  (ETH/USD). A network failure in phase 1 is a RESUMABLE refusal (start again; finished steps are kept, re-verified by their hashes).
- **The block-day rows are pinned** in pins/block_days.tsv (all 20 registered by 2026-10-07T06:12Z); the runner refuses any block day whose content differs.
- **The locked V4 tape writes rows up to ~40,000 blocks late** (measured on the open days); the cut reads to 100,000 blocks past the
  cut block. A larger lateness on 10-07 would drop a few duplicate lock rows (the wide feed carries the same swaps).
- **Ledger and state files are read as they are at run time** (births, minters, v4 births, poolkeys, launches, hook-pad map): their
  sha256 are recorded in report.md, but they are not pre-registered (they grow every minute); since pond #330 H3 they are in the phase-1
  manifest whose sha256 is posted before any engine runs.
- **The 42 engine runs take ~6–10 h** behind the gate (load often 7–9 on this box); the report is ready ~10–14 h after the start.
- **RAM:** finalize holds the pool table (~2–4 GB); it runs behind the gate (MemAvailable > 4 GB, no other engine, not beside the
  hunter's run_batch).
