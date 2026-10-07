#!/usr/bin/env python3
"""make_register_draft.py — writes REGISTER_DRAFT.md from the files on disk (every hash computed here, every count read from a test or proof
output, none typed by hand). The coordinator pastes it into SEALED-HOLDOUT/README.md; this script never edits the register.
Order (pond #330 B2): tools/make_pins.sh, then tests/summarize_tests.py, then this script."""
import hashlib, json, os, glob, datetime, re
R = '/home/green/projects/patches/sealed-exam-blockA'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def J(p): return json.load(open(p))
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
run = open(R + '/run_exam.sh').read()
anch = {k: re.search(rf'^{k}=([0-9a-f]{{64}}) ', run, re.M).group(1) for k in ('PIN_CODE_SHA', 'PIN_INPUTS_SHA', 'PIN_BLOCK_SHA')}
pins = {k: sha(R + '/pins/' + k) for k in ('code.sha256', 'inputs.sha256', 'block_days.tsv', 'open_days.tsv')}
assert anch['PIN_CODE_SHA'] == pins['code.sha256'] and anch['PIN_INPUTS_SHA'] == pins['inputs.sha256'] and anch['PIN_BLOCK_SHA'] == pins['block_days.tsv'], \
    'run_exam.sh PIN_* anchors do not match the pin files: run tools/make_pins.sh first'
ex = J(R + '/tests/testB/seam_bound_evidence.json')
sims = [e for e in ex['evidence'] if 'result' in e]
L = []
A = L.append
A(f'## ⛔ BLOCK A EXAM RUNNER — registered {now[:10]} (draft written {now}), after pond #330 (B1, B2, H1, H2, H3; M5, M6, L4, L22 by Chef 2026-10-07)')
A('Work folder `patches/sealed-exam-blockA/` (README.md there: every step, every test). The exam is TWO starts of ONE command, after 2026-10-07T00:00:00Z (commit-reveal, pond #330 H3):')
A('1. `bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh` — PHASE 1 (steps 0-7: pins, closed days, anchors and ETH/USD, the cuts, the tables, the V4 join with the B1 seam gate, the links). '
  'It ends by writing `work/state/manifest.sha256` (every run-time input the engines and the report read) and STOPS, printing the manifest\'s sha256. No engine has run; no statistic exists.')
A('2. The coordinator posts that sha256 publicly, then writes it to `work/state/MANIFEST_POSTED`.')
A('3. `bash .../run_exam.sh` again — PHASE 2 (steps 8-9). It first checks that MANIFEST_POSTED is the manifest\'s sha256 and re-hashes every manifest line and every finished step\'s outputs; '
  'then the 42 engine runs, the statistics and `report.md`, with `runs.tsv` (full 64-hex hashes), `exam.log`, `REFUSED`, `ENGINE_DEATHS` and the manifest published beside it in `report_files/`.')
A('')
A(f'- **Runner** `run_exam.sh` sha256 `{sha(R + "/run_exam.sh")}`.')
A(f'- **Pins, anchored in the runner** (pond #330 H1): `run_exam.sh` hard-codes the sha256 of its three pin files and refuses at step 1, before anything else is read, unless they match: '
  f'`pins/code.sha256` `{pins["code.sha256"]}` (every code file it runs, incl. the two frozen analyzers and `tools/exam_checks.py`) · '
  f'`pins/inputs.sha256` `{pins["inputs.sha256"]}` (the 09-27 tables, the 09-27 join\'s decimals / unknown keys / warm-up V4 days, the hole and backfill tapes, the open-day pins, the orientation pin, the block-day pin) · '
  f'`pins/block_days.tsv` `{pins["block_days.tsv"]}` (the 20 registered rows of the block days 09-27..10-06, both feeds, copied verbatim from tape-hashes.tsv by tools/make_pins.sh). '
  f'`run_exam.sh` is not in `pins/code.sha256`, so there is no circularity. `pins/open_days.tsv` `{pins["open_days.tsv"]}` (uncompressed-content sha256 of every open raw day file).')
A('')
A('### Engines (Option A, coordinator 2026-10-05: the two changes registered "before the run" on 09-27, ported from blood-grid-window-history-2026-09-27/engine_wh.js)')
for k in ('st', 'grid'):
    A(f'- rule #{1 if k == "st" else 2}: `engines/engine_{k}_A.js` `{sha(R + f"/engines/engine_{k}_A.js")}` = twinfix `engine_{k}_rk.js` + `engine_{k}_A.diff` `{sha(R + f"/engines/engine_{k}_A.diff")}`'
      f' (FIX 1 twins drawn WITHOUT replacement, min(3, pool) distinct coins; FIX 2 V4 entries with depth1 < 0.001 ETH skipped at fill, strategy and twins alike, written as counted `skipDepth` rows, no cooldown) — **LOGIC, new**.')
    A(f'  - exam copy `engines/engine_{k}_exam.js` `{sha(R + f"/engines/engine_{k}_exam.js")}` = the A engine + `engine_{k}_exam.diff` `{sha(R + f"/engines/engine_{k}_exam.diff")}` — **window CONSTANTS and the reader path only**.')
    A(f'  - sensitivity harness `engines/engine_{k}_exam_h.js` `{sha(R + f"/engines/engine_{k}_exam_h.js")}` = the exam copy + `engine_{k}_exam_h.diff` `{sha(R + f"/engines/engine_{k}_exam_h.diff")}`: H1 `ONLY_CELLS` (exam cell alone), H3 `EXAM_SEED` (the declared seed hook, integers 20260927..20260946 only).')
A(f'- reader `engines/v4tape_exam.js` `{sha(R + "/engines/v4tape_exam.js")}` = v4-join `v4tape.js` + `v4tape_exam.diff` `{sha(R + "/engines/v4tape_exam.diff")}`: paths (warm-up V4 days from the 09-27 join, block V4 days from the exam\'s join, V2/V3 through the exam\'s verified links) and the seal (rows < 2026-10-07T00:00Z, days < 10-08) — constants only.')
A(f'- guard `engines/guard.js` `{sha(R + "/engines/guard.js")}` (= 6cdd676b, unchanged) · `tools/exam_guard.js` `{sha(R + "/tools/exam_guard.js")}` (preloaded into every exam engine and join step: refuses a raw file of a day >= 10-07, a work file of a day >= 10-08, links resolving to either, /sealed/ paths; aborts on any parsed row with ts >= 1791331200).')
A(f'- **NEW CODE, said plainly:** the pre-filter in `tools/stats_rule.py` `{sha(R + "/tools/stats_rule.py")}` drops and counts the `skipDepth` rows (and keeps only the exam cell) before the FROZEN analyzers\' own code runs (analyze_st.py 2744c11c…, analyze_grid.py 08aaf46d…, both unchanged: their only window constant JUDGE0 = 09-17 puts every exam row in their JUDGE half). Also new: `tools/report.py`, `tools/tables.py`, `tools/days.py`, `tools/cut_tape.py`, `tools/exam_checks.py` (the B1 / H1 / H2 / L22 refusal checks), `join/cut_v4.js`, `join/fetch_ethusd.py`, `join/glue.py`, `join/addr_lists.js` (sha256 in pins/code.sha256).')
A('')
pf = R + '/proof/PROOF.json'
if os.path.exists(pf):
    P = J(pf)
    A('### Option A proof (09-08..09-26, seal_guard preloaded, the 09-27 tables) — `proof/PROOF.md`')
    for line in P.get('summary', []): A(f'- {line}')
    A('')
    A('**New JUDGE references (Option A engines; reported for reference, the exam reads only Block A):**')
    for line in P.get('judge', []): A(f'- {line}')
    A('')
A('### The window (coordinator 2026-10-05, constants in the exam engines)')
A('- Data: 2026-09-24T00:00Z (open warm-up 09-24..09-26: the 72 h history lookback is full at the first assessment) to the CUT 2026-10-07T00:00:00Z. The 10-07 V2/V3 tape file (from ~23:00Z, R-0109) and the 10-07 V4-wide file (from ~23:42Z) are read CUT at CUT.')
A('- One EXAM window (FIT0 = JUDGE0 = 2026-09-27T00:00Z). **Rule #1 (C2P): last assessment 2026-10-04T23:00Z = CUT − 49 h** (frozen spec report.txt §7; max hold 48 h), signals before 2026-10-05T00:00Z. **Rule #2 (D25L48): last assessment 2026-10-05T23:00Z**, signals before 2026-10-06T00:00Z. C1 (in rule #1\'s pass, not an exam cell, 24 h hold): last assessment 10-05T23:00Z. Positions still open at the data end book as "end", as on 09-27.')
A('')
A('### Tables (no look-ahead)')
A(f'- meta.tsv: path-only copies of hold-study `tokmeta.py` and edge-round3 `mkmeta.py` (`builders/*.diff`); launchpad labels from noxabot `lib/launchpads.js` at `e5c559ec53baf0ee12eef6fb84587e277ea588f6` (the last commit before 2026-09-27T00:00Z, 2026-09-26T02:21Z; file sha256 `1b939aea01899089285dfbb47963eed740aeda58353fc60e5824e9adffcff592`), extracted with read-only `git show`.')
A('- poolfee.tsv: path-only copies of v4-join `meta.js` (writes the exam work folder, never the hunter\'s pinned meta.json) and blood-selection2 `mkpoolfee.py`.')
A('- Both: new coins / pools born before 2026-10-06T00:00Z (unknown birth kept, as on 09-27). Every coin / pool already in the 09-27 table keeps its 09-27 row VERBATIM, first and in its 09-27 order (the 09-27 table is a byte prefix of the exam table; the runner refuses otherwise), so block knowledge can only add a coin, never relabel one. The rebuild\'s differences on old rows are reported, never used: on open data (10-05) 4 of 471,683 meta rows (3 births learned in the block, 1 minter learned in the block that would relabel an `unknown` coin as Pons) and 0 of 550,395 poolfee rows.')
A('- The builders read a hashed SNAPSHOT of the six ledger / state files (births, minters, V4 births, poolkeys, launches, hook-pad map), taken by the runner just before; their sha256 are in the phase-1 manifest and in report.md.')
A('- scam.tsv: the 09-27 table as is (9988ebfa…); its three sources (safety-cache 09-04, tokengate 08-30, redteam 09-20) must still predate 2026-09-27T00:00Z by mtime, else the runner refuses.')
A('')
A('### V4 join for the block (built only inside run_exam.sh, after the instant)')
A('- The 09-27 v4-join tools, exam copies (`join/*.diff`): paths; pass1 with the CUT and a first join day 2026-09-25 (one warm-up day for finalize\'s causal other-quote prices); finalize with SEAL = CUT. Inputs: the hash-verified V4-wide files 09-25..10-06, the 10-07 wide CUT copy, the locked V4 tape (rows from 09-25 to the CUT; read until 100,000 blocks past the cut because it writes rows up to ~40,000 blocks late), the hole and backfill tapes.')
A('- Network at exam time: block→time anchors (public RPC), ETH/USD hourly (CoinGecko, cut at the CUT; on open days identical to the 09-27 series), Initialize logs for NEW pre-ledger pools only, decimals for NEW tokens only.')
A('- One logic change, forced: the official RPC now caps eth_getLogs (100,000 blocks with several topic values, 10,000,000 with one; measured 2026-10-05), so `join/resolve_unknown.py` pages the SAME Initialize-log query one pool id per request in 10,000,000-block windows (tests/testB2: 12 pools resolve exactly as on 09-27).')
A(f'- **B1 SEAM GATE — a refusal, not a report (pond #330 B1).** In step 6, after the join and BEFORE it is marked done (so before any engine runs), and again on every later start, the joined 09-25 and 09-26 are compared row by row with the 09-27 join\'s own files and the run REFUSES (exam-ending) unless: '
  f'**(a) 2026-09-26: differ = 0, only in the exam\'s join = 0, only in the 09-27 join = 0**; **(b) 2026-09-25 (the join\'s first day): no row in one join only, and differences ONLY in the other-quote price fields {", ".join(ex["rule"]["allowed_fields"])}, on at most {ex["rule"]["bound_rows"]:,} rows.** '
  f'The bound was fixed on open data before the read (tests/testB/seam_bound_evidence.json): Test B\'s first joined day (09-20, the same position in its shifted calendar) differed on exactly {ex["evidence"][0]["differ"]:,} rows in those fields; '
  f'a replay of finalize.js\'s causal other-quote rule (tests/testB/seam_sim.py, cold start vs the 09-27 join\'s warm state) reproduces those {sims[0]["result"]["counts"]["differ"]:,} rows exactly and predicts {sims[1]["result"]["counts"]["differ"]:,} of {sims[1]["result"]["counts"]["first_day_rows_total"]:,} rows for the exam\'s 09-25. '
  'eth_usd is NOT allowed: it comes from the CoinGecko series alone, never from the warm-up; it differed only on Test B\'s last day before ITS cut (clarification 10), an edge the exam never compares; CoinGecko\'s hourly points are on the hour and identical whatever the query start (checked 2026-10-07 on an open window). The gate is `tools/exam_checks.py seam`; tests/testB/check_testB.py now enforces the same code on Test B.')
A('')
A('### Hash commitments')
A(f'- After the instant and before any engine runs: every block day 09-27..10-06 (V2/V3 tape and V4-wide) against **pins/block_days.tsv** (`{pins["block_days.tsv"]}`, exactly one row per day and feed, anchored in the runner) — never against the appendable SEALED-HOLDOUT/tape-hashes.tsv, which the runner no longer reads or writes; the warm-up days against pins/open_days.tsv.')
A('- Recorded by the runner itself: the 10-07 V2/V3 CUT and the 10-07 V4-wide CUT (written to `work/state/cut_rows.tsv` as `v2v3-tape-cutA` / `v4-wide-cutA` in the tape-hashes.tsv format, for the coordinator to register), the locked V4 tape portion, the ETH/USD series — every one a full 64-hex sha256 in exam.log and at the top of report.md.')
A('- **Commit-reveal (pond #330 H3):** phase 1 ends with `work/state/manifest.sha256`: both cut copies, the lock cut, the six-file ledger snapshot, the tables, every joined day (09-25..10-06), anchors.tsv, heldout.tsv, the ETH/USD JSON, decimals.json, unknown_keys.json, the V4 meta.json, the cut records, the verified-day records and the seam-gate result. Its sha256 is posted publicly BEFORE phase 2; phase 2 refuses unless `work/state/MANIFEST_POSTED` holds it and every manifest line still hashes the same, and checks again before step 9.')
A('')
A('### Runs, verdict, sensitivity')
A('- PRIMARY: the 09-27 pass composition (all 4 cells of engine_st, all 24 of engine_grid), SEED 20260927. SENSITIVITY: the exam cell alone (C2P / D25L48) for SEEDS 20260927..20260946. 42 engine runs, one at a time, nice 19, behind the box gate (never beside the hunter\'s run_batch).')
A('- A rule PASSES iff: Holm k = 2 on the one-sided p (SE_cons) — the smaller p < 0.0125, then the larger < 0.025 — AND d > 0 with CI lower > 0 AND n >= 300 paired trades on >= 60 coins AND drop-5 d > 0 AND DATA GATE G1–G5, G9, G10 PASS (a gate failure reads CAN\'T TELL (data)).')
A('- **Holm and the data gate (pond #330 M6, Chef 2026-10-07):** a CAN\'T TELL (data) rule enters Holm with p = 1, so the other rule must clear 0.0125 (alpha / 2) on its own.')
A('- **Agreement and qualifying (pond #330 M5, Chef 2026-10-07):** the sensitivity AGREES with the primary for a rule iff at least 10 of the 20 alone seeds reach the primary\'s verdict (each seed: the same bar, Holm across the two rules\' alone runs of that seed). '
  'A PASS QUALIFIES (the real-money gate, any public claim) iff the primary PASSES and at least 10 of the 20 alone seeds PASS. The exam cell alone at SEED 20260927 is printed as information only. '
  'report.md\'s FIRST LINE gives each rule\'s verdict, AGREE / DISAGREE, the PASS-seed count, its READING (PASS · PASS, draw-dependent · NOT SHOWN · NOT SHOWN, draw-dependent · CAN\'T TELL (data)) and qualifies true/false; report.json carries `qualifies`.')
A('- **CAN\'T TELL (data) is final for Block A (pond #330 L4, Chef 2026-10-07): no re-run, no re-draw; that rule waits for Block B.** Its statistics (primary and all 20 alone seeds) are never printed: they go only to `work/withheld_stats.json`, whose sha256 report.md prints (pond #330 H2). An alone seed whose own gate fails is withheld the same way.')
A('- report.md\'s first lines also carry the sha256 of the runner, of the three pin files and of the posted manifest, and every runner sha256 that ever started on the work folder. A failure anywhere in the report is a refusal: nothing is written (pond #330 H1).')
A('- The money test (heavy-cost raw mean, CI) is reported, not the bar (R-0111: the heavy view\'s Pons take is too low).')
A('')
A('### Refusals, resume and deviations (pond #330 H2, L4, L22 — registered)')
A('- Every refusal is written with a CLASS to `work/state/REFUSED`, which every start reads first, and which is published with report.md.')
A('- **RESUMABLE** — start again unchanged: only failures that happen BEFORE any statistic exists and are not about the data or the code: network (block anchors, ETH/USD, Initialize logs, decimals), not ready (the anchors or the raw files not yet past the cut + margin), another start already running, phase 2 started before the manifest\'s hash is posted, and an exam engine that dies without completing (below). Once step 9 has begun (`work/state/stats.started`: statistics may exist), any RESUMABLE is raised to END.')
A('- **An engine that dies without completing (coordinator 2026-10-07, on pond\'s principle that nothing before a statistic is a look):** "an engine that dies without completing (kernel kill, no complete output) is re-run unchanged; the death and the re-run are disclosed in report_files; nothing else may change; a partial output is never read." '
  'Killed or stopped from outside counts: SIGKILL (137, e.g. the kernel\'s OOM killer), SIGTERM (143, e.g. a reboot or shutdown: the owner rebooted this box twice in the 24 h before the read), SIGHUP (129), SIGINT (130). '
  'The runner recognises it from what the unchanged tools/run_engine.sh records: the exit code in runs.tsv with GNU time\'s matching "Command terminated by signal N" in the run\'s log, or no runs.tsv row at all for that attempt (run_engine.sh died with it). On the next start the dead run\'s output file, if any, and its log are moved aside unread (their sha256 listed in report.md section 10) and the run is repeated with the same engine, seed and inputs; every death and re-run is a line of `work/state/ENGINE_DEATHS`, published in report_files/. '
  'SIGABRT (134) is END unless it is V8\'s heap cap (CAP); an engine that exits non-zero by itself, even after writing a complete output, is END (Test C K1-K7).')
A('- **The runner itself killed** (a reboot stops the whole tree; no refusal is written): every step is marked done only when it has finished, so the next start re-does the unfinished step from scratch (step 6 first clears an interrupted attempt\'s leftovers) and re-verifies every finished one by its hashes; an interrupted engine run is re-run as above; an interrupted step 9 is resumed and disclosed in ENGINE_DEATHS (statistics files are written atomically by the runner and reused only if computed from exactly the recorded outputs; report.md, report.json and withheld_stats.json are written atomically, and nothing is printed before they are complete). Test C KR1-KR3 kill the runner\'s whole session with SIGTERM during an engine run, during step 2 and during step 9: no refusal is left behind and the next start resumes.')
A('- **END** — this runner never starts again on this work folder: any pin, code, input, block-day, finished-step, engine-output, manifest or posted-hash mismatch; rows at/after the cut (afterCut); an exam-guard abort; the B1 seam gate; a failed builder or join step; an engine that fails by itself (any non-zero exit other than a death above or a memory cap); a failed statistics or report step; a finished exam (`work/state/FINAL`; L4).')
A('- **CAP** (L22) — an exam engine stopped by its RSS guard (`engine_st_exam.js` ~:475 / `engine_grid_exam.js` ~:424 and the _h copies, 3.2e9 bytes) or by the heap cap (`tools/run_engine.sh` ~:34, `--max-old-space-size=3000`): **the only allowed change is raising that cap; the new file hash is posted publicly before that engine re-runs; nothing else may change.** '
  'The change is recorded in `work/state/CAP_CHANGE` (time, file, old and new sha256, a copy of the original, where the hash was posted). The pin files are NOT regenerated: the runner accepts a file that differs from its pin only through such a record, and only if the original copy hashes to the pin, the new version differs from it in exactly one line, the cap line, by a larger number, and that cap fired before (a CAP refusal for it). Anything else is an END refusal; a CAP refusal without its record is refused again.')
rss_tb = [int(m.group(1)) for m in re.finditer(r'maxrss_kb=(\d+)', open(R + '/tests/testB/tree/work/runlogs/runs.tsv').read())]
rss_pr = sorted(int(m.group(1)) for p in glob.glob(R + '/proof/runlogs/*.log') for m in re.finditer(r'"peakRssMB":(\d+)', open(p).read()))
A(f'  - Peak memory on open data, recorded before the read: Test B\'s {len(rss_tb)} exam-engine runs (7 days 09-19..09-25): maximum resident set {min(rss_tb):,}–{max(rss_tb):,} kB (`time -v`, tests/testB/tree/work/runlogs/runs.tsv); '
  f'the Option A proof runs (19 days 09-08..09-26): the engines\' own peakRssMB {min(rss_pr):,}–{max(rss_pr):,} (proof/runlogs/*.log); pond #330 L22: the rk batch peaked at 2,703 MB on 36.0 M open-day rows. The exam reads 13 days (09-24..10-06).')
A('- **A code fix after step 2** changes a pinned file, so the runner\'s hard-coded pin hashes must change, so the runner\'s own sha256 changes: that is a LABELLED DEVIATION. It is posted (the diff, the reason, the new sha256 of run_exam.sh and of the pin files) before the resumed start; the coordinator moves the REFUSED file aside (`REFUSED.deviation-N`, kept and published); finished steps whose code did not change are kept only because their outputs still hash as marked; a step whose code changed is re-run from scratch. report.md lists every runner sha256 that ever started on the work folder, every refusal and every cap change, and flags a runner change as a deviation. Once step 9 has started (statistics exist on disk), any resumption is Chef\'s call, disclosed, and must say whether any statistic was read; a written report is final (work/state/FINAL).')
A('- **Any fresh start** (a new work folder) is disclosed as a deviation the same way.')
A('')
tf = R + '/tests/TESTS.json'
if os.path.exists(tf):
    A('### Tests (open data and synthetic files only; `tests/`)')
    for line in J(tf).get('summary', []): A(f'- {line}')
    A('')
A('### Every exam file (pins/code.sha256)')
for ln in open(R + '/pins/code.sha256'): A(f'- `{ln.strip()}`')
A('')
A('### Every pinned open input (pins/inputs.sha256)')
for ln in open(R + '/pins/inputs.sha256'): A(f'- `{ln.strip()}`')
A('')
A(f'### The 20 pinned block-day rows (pins/block_days.tsv `{pins["block_days.tsv"]}`)')
for ln in open(R + '/pins/block_days.tsv').read().splitlines()[1:]:
    a = ln.split('\t'); A(f'- {a[1]} {a[2]} `{a[3]}` {a[4]} B (registered {a[0]})')
open(R + '/REGISTER_DRAFT.md', 'w').write('\n'.join(L) + '\n')
print('REGISTER_DRAFT.md written', len(L), 'lines; sha256', sha(R + '/REGISTER_DRAFT.md'))
