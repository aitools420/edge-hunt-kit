#!/usr/bin/env python3
"""make_register_draft.py — writes REGISTER_DRAFT.md from the files on disk (every hash computed here, none typed by hand) and the
proof / test outputs. The coordinator pastes it into SEALED-HOLDOUT/README.md before 2026-10-07T00:00Z; this script never edits the register."""
import hashlib, json, os, glob, datetime
R = '/home/green/projects/patches/sealed-exam-blockA'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def J(p): return json.load(open(p))
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
L = []
A = L.append
A(f'## ⛔ BLOCK A EXAM RUNNER — registered {now[:10]} (draft written {now}), before any sealed read')
A('Work folder `patches/sealed-exam-blockA/` (README.md there: every step, every test). The exam is ONE command, after 2026-10-07T00:00:00Z:')
A('`bash /home/green/projects/patches/sealed-exam-blockA/run_exam.sh` → `patches/sealed-exam-blockA/report.md`.')
A('')
A(f'- **Runner** `run_exam.sh` sha256 `{sha(R + "/run_exam.sh")}`.')
A(f'- **Pins the runner checks before anything runs** (it refuses on any difference): `pins/code.sha256` `{sha(R + "/pins/code.sha256")}` (every code file it runs, incl. the two frozen analyzers) · '
  f'`pins/inputs.sha256` `{sha(R + "/pins/inputs.sha256")}` (the 09-27 tables, the 09-27 join\'s decimals / unknown keys / warm-up V4 days, the hole and backfill tapes, the open-day pins) · '
  f'`pins/open_days.tsv` `{sha(R + "/pins/open_days.tsv")}` (uncompressed-content sha256 of every open raw day file, tape-hashes.tsv format).')
A('')
A('### Engines (Option A, coordinator 2026-10-05: the two changes registered "before the run" on 09-27, ported from blood-grid-window-history-2026-09-27/engine_wh.js)')
for k in ('st', 'grid'):
    A(f'- rule #{1 if k == "st" else 2}: `engines/engine_{k}_A.js` `{sha(R + f"/engines/engine_{k}_A.js")}` = twinfix `engine_{k}_rk.js` + `engine_{k}_A.diff` `{sha(R + f"/engines/engine_{k}_A.diff")}`'
      f' (FIX 1 twins drawn WITHOUT replacement, min(3, pool) distinct coins; FIX 2 V4 entries with depth1 < 0.001 ETH skipped at fill, strategy and twins alike, written as counted `skipDepth` rows, no cooldown) — **LOGIC, new**.')
    A(f'  - exam copy `engines/engine_{k}_exam.js` `{sha(R + f"/engines/engine_{k}_exam.js")}` = the A engine + `engine_{k}_exam.diff` `{sha(R + f"/engines/engine_{k}_exam.diff")}` — **window CONSTANTS and the reader path only**.')
    A(f'  - sensitivity harness `engines/engine_{k}_exam_h.js` `{sha(R + f"/engines/engine_{k}_exam_h.js")}` = the exam copy + `engine_{k}_exam_h.diff` `{sha(R + f"/engines/engine_{k}_exam_h.diff")}`: H1 `ONLY_CELLS` (exam cell alone), H3 `EXAM_SEED` (the declared seed hook, integers 20260927..20260946 only).')
A(f'- reader `engines/v4tape_exam.js` `{sha(R + "/engines/v4tape_exam.js")}` = v4-join `v4tape.js` + `v4tape_exam.diff` `{sha(R + "/engines/v4tape_exam.diff")}`: paths (warm-up V4 days from the 09-27 join, block V4 days from the exam\'s join, V2/V3 through the exam\'s verified links) and the seal (rows < 2026-10-07T00:00Z, days < 10-08) — constants only.')
A(f'- guard `engines/guard.js` `{sha(R + "/engines/guard.js")}` (= 6cdd676b, unchanged) · `tools/exam_guard.js` `{sha(R + "/tools/exam_guard.js")}` (preloaded into every exam engine and join step: refuses a raw file of a day >= 10-07, a work file of a day >= 10-08, links resolving to either, /sealed/ paths; aborts on any parsed row with ts >= 1791331200).')
A(f'- **NEW CODE, said plainly:** the pre-filter in `tools/stats_rule.py` `{sha(R + "/tools/stats_rule.py")}` drops and counts the `skipDepth` rows (and keeps only the exam cell) before the FROZEN analyzers\' own code runs (analyze_st.py 2744c11c…, analyze_grid.py 08aaf46d…, both unchanged: their only window constant JUDGE0 = 09-17 puts every exam row in their JUDGE half). Also new: `tools/report.py`, `tools/tables.py`, `tools/days.py`, `tools/cut_tape.py`, `join/cut_v4.js`, `join/fetch_ethusd.py`, `join/glue.py`, `join/addr_lists.js` (sha256 in pins/code.sha256).')
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
A('- The builders read a hashed SNAPSHOT of the six ledger / state files (births, minters, V4 births, poolkeys, launches, hook-pad map), taken by the runner just before; their sha256 are in report.md.')
A('- scam.tsv: the 09-27 table as is (9988ebfa…); its three sources (safety-cache 09-04, tokengate 08-30, redteam 09-20) must still predate 2026-09-27T00:00Z by mtime, else the runner refuses.')
A('')
A('### V4 join for the block (built only inside run_exam.sh, after the instant)')
A('- The 09-27 v4-join tools, exam copies (`join/*.diff`): paths; pass1 with the CUT and a first join day 2026-09-25 (one warm-up day for finalize\'s causal other-quote prices); finalize with SEAL = CUT. Inputs: the hash-verified V4-wide files 09-25..10-06, the 10-07 wide CUT copy, the locked V4 tape (rows from 09-25 to the CUT; read until 100,000 blocks past the cut because it writes rows up to ~40,000 blocks late), the hole and backfill tapes.')
A('- Network at exam time: block→time anchors (public RPC), ETH/USD hourly (CoinGecko, cut at the CUT; on open days identical to the 09-27 series), Initialize logs for NEW pre-ledger pools only, decimals for NEW tokens only.')
A('- One logic change, forced: the official RPC now caps eth_getLogs (100,000 blocks with several topic values, 10,000,000 with one; measured 2026-10-05), so `join/resolve_unknown.py` pages the SAME Initialize-log query one pool id per request in 10,000,000-block windows (tests/testB2: 12 pools resolve exactly as on 09-27).')
A('- Plumbing check written into the run: the joined 09-25 and 09-26 are compared row by row with the 09-27 join\'s own files.')
A('')
A('### Hash commitments')
A('- After the instant and before any engine runs: every block day 09-27..10-06 (V2/V3 tape and V4-wide) against EVERY tape-hashes.tsv row for it — a missing row or any mismatch is a refusal; the warm-up days against pins/open_days.tsv.')
A('- Recorded by the runner itself: the 10-07 V2/V3 CUT and the 10-07 V4-wide CUT (appended to tape-hashes.tsv as `v2v3-tape-cutA` / `v4-wide-cutA`), the locked V4 tape portion, the ETH/USD series — all at the top of report.md; then every input\'s sha256.')
A('')
A('### Runs, verdict, sensitivity')
A('- PRIMARY: the 09-27 pass composition (all 4 cells of engine_st, all 24 of engine_grid), SEED 20260927. SENSITIVITY: the exam cell alone (C2P / D25L48) for SEEDS 20260927..20260946 (the first one is sensitivity (1)). 42 engine runs, one at a time, nice 19, behind the box gate (never beside the hunter\'s run_batch).')
A('- A rule PASSES iff: Holm k = 2 on the one-sided p (SE_cons) — the smaller p < 0.0125, then the larger < 0.025 — AND d > 0 with CI lower > 0 AND n >= 300 paired trades on >= 60 coins AND drop-5 d > 0 AND DATA GATE G1–G5, G9, G10 PASS (a gate failure reads CAN\'T TELL (data)).')
A('- The sensitivity AGREES with the primary for a rule iff (1) the exam cell alone at SEED 20260927 reaches the same verdict AND (2) at least 10 of the 20 alone seeds reach the same verdict (each seed: the same bar, Holm across the two rules\' alone runs of that seed). report.md\'s FIRST LINE gives both verdicts and AGREE / DISAGREE.')
A('- The money test (heavy-cost raw mean, CI) is reported, not the bar (R-0111: the heavy view\'s Pons take is too low).')
A('')
tf = R + '/tests/TESTS.json'
if os.path.exists(tf):
    A('### Tests (open data only; `tests/`)')
    for line in J(tf).get('summary', []): A(f'- {line}')
    A('')
A('### Every exam file (pins/code.sha256)')
for ln in open(R + '/pins/code.sha256'): A(f'- `{ln.strip()}`')
A('')
A('### Every pinned open input (pins/inputs.sha256)')
for ln in open(R + '/pins/inputs.sha256'): A(f'- `{ln.strip()}`')
open(R + '/REGISTER_DRAFT.md', 'w').write('\n'.join(L) + '\n')
print('REGISTER_DRAFT.md written', len(L), 'lines')
