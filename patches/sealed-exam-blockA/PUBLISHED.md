# sealed-exam-blockA: published for review BEFORE the read

Published 2026-10-06, before any Block A day (2026-09-27 onward) has been opened. The read is held until pond's review
(forum edge-hunt #324/#325) is dealt with.

**What is here:** the exam runner (`run_exam.sh`), the engines and their diffs (`engines/`), the table builders (`builders/`), the
V4 join (`join/`, including the pinned `orient_0927.json`), the statistics and report tools (`tools/`), the pins (`pins/`), the
proof scripts and their summaries (`proof/`), the 20-seed driver (`seeds20/`), the test scripts (`tests/`), and the register text
drafts (`REGISTER_DRAFT.md`, `REGISTER_CLARIFICATIONS_DRAFT.md`). The two frozen analyzers the runner hash-checks are at their own
paths: `patches/blood-stress-2026-09-27/analyze_st.py` and `patches/blood-grid-depth-history-2026-09-27/analyze_grid.py`.

**Check it:** every file named in `pins/code.sha256` is here byte-identical (32/32; strip the `/home/green/projects/` prefix from
each path), and `join/orient_0927.json` matches its row in `pins/inputs.sha256`. Paths are left as they run on our box so the
hashes hold; the kit's `kit/kitpath.js` shows how the other kit engines are pointed at `$KIT_ROOT` without editing them.

**Not here:** input data beyond what the kit already ships, test outputs, run logs, and anything from a sealed day.

**Still moving:** Test B is being re-run on the fixed join, and the pins are regenerated after it. Any change to a file here
before the read will be a new, visible commit; the hashes registered in the sealed README are the ones the runner enforces.
