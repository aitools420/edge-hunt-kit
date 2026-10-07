# sealed-exam-blockA: published for review BEFORE the read

Published 2026-10-06, before any Block A day (2026-09-27 onward) has been opened. The read is held until pond's review
(forum edge-hunt #324/#325) is dealt with.

**What is here:** the exam runner (`run_exam.sh`), the engines and their diffs (`engines/`), the table builders (`builders/`), the
V4 join (`join/`, including the pinned `orient_0927.json`), the statistics and report tools (`tools/`), the pins (`pins/`), the
proof scripts and their summaries (`proof/`), the 20-seed driver (`seeds20/`), the test scripts (`tests/`), and the register text
drafts (`REGISTER_DRAFT.md`, `REGISTER_CLARIFICATIONS_DRAFT.md`). The two frozen analyzers the runner hash-checks are at their own
paths: `patches/blood-stress-2026-09-27/analyze_st.py` and `patches/blood-grid-depth-history-2026-09-27/analyze_grid.py`.

**Check it:** every file named in `pins/code.sha256` is here byte-identical (33/33; strip the `/home/green/projects/` prefix from
each path), and `join/orient_0927.json` matches its row in `pins/inputs.sha256`. Paths are left as they run on our box so the
hashes hold; the kit's `kit/kitpath.js` shows how the other kit engines are pointed at `$KIT_ROOT` without editing them.

**Not here:** input data beyond what the kit already ships, test outputs, run logs, and anything from a sealed day.

**Final commit before the read (2026-10-07), answering pond's review (forum edge-hunt #330):** B1 (the 09-25/09-26 seam check now
REFUSES, tools/exam_checks.py), B2 (one final re-pin; the register draft is generated and asserts the runner's pin anchors), H1
(run_exam.sh hard-codes the sha256 of pins/code.sha256, pins/inputs.sha256 and the new pins/block_days.tsv, the 20 sealed day rows),
H2 (refusal classes RESUMABLE / END / CAP, step outputs hashed and re-checked, engine hashes checked against the pins, a data-gate
failure's statistics go only to a hashed side file), H3 (two starts: phase 1 ends with a manifest whose sha256 is posted before phase 2
may run). Also adopted: M5, M6, L4, L22, L16, L19, and an engine death (kernel kill, or a reboot's SIGTERM/SIGHUP/SIGINT) is re-run
unchanged and disclosed. Test evidence: tests/TESTS.md, tests/testC/testC.log (68/68), tests/testR/ (12/12), tests/mutation_check.log
(30/30), tests/testB/check_testB.json, tests/testB/seam_bound_evidence.json. The engines, the reader, the join, the builders,
stats_rule.py and both frozen analyzers are unchanged from 4884d01. Any later change before the read will be another visible commit.
