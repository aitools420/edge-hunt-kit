#!/usr/bin/env python3
"""cells.py — the pre-registered cell lists (PREREG.md §4 = batch 1, PREREG2.md §4 = batch 2). Deterministic; writes cells1.json,
cells2.json. A cell = (delay s, hold s, take profit, filters). Filters: tier (elite|good|other), first ('first'), mcap (a list of pass-B
bands, applied EX-ANTE: only rows whose mcap price was read at or before the entry moment), age (a pass-B age band).
Cells already read by callers-fill1 pass B (same delay/hold/tp/filters, no mcap filter) are flagged rereadOf = pass B cell no.: they are
computed (the old-cost view must reproduce pass B) but are NOT counted in K."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PB = json.load(open(os.path.join(HERE, "..", "results", "callers-fill1-2026-09-30-passB", "results.json")))["records"]
HL = {75: "1.25 min", 150: "2.5 min", 300: "5 min", 450: "7.5 min", 900: "15 min", 3600: "1 h", 14400: "4 h", 43200: "12 h",
      86400: "24 h", 259200: "72 h", 432000: "5 d", 604800: "7 d", 777600: "9 d", 950400: "11 d"}
DL = {5: "5 s", 15: "15 s", 30: "30 s", 60: "1 min"}
PBDL = {"1 min": 60, "5 min": 300, "15 min": 900, "60 min": 3600}
pbkey = {}
for r in PB:
    if r.get("alias") or not r.get("filters") is not None:
        continue
    f = r["filters"]
    pbkey.setdefault((PBDL.get(r["delay"]), r["hold"], r["tp"], json.dumps(f, sort_keys=True)), r["cell"])

def mk(group, delay, hold, tp, **filt):
    f = {k: v for k, v in filt.items() if v is not None}
    c = dict(group=group, delay=DL[delay], delaySec=delay, hold=HL[hold], holdSec=hold, tp=tp, filters=f)
    if "mcap" not in f:
        k = (delay, HL[hold], tp, json.dumps({k: v for k, v in f.items()}, sort_keys=True))
        if k in pbkey:
            c["rereadOf"] = pbkey[k]
    return c

# ── batch 1: fast entries ──────────────────────────────────────────────────
C1 = []
for tier in (None, "good"):
    for tp in ("+50%", "+25%"):
        for hold in (900, 3600, 86400):
            for d in (5, 15, 30, 60):
                C1.append(mk("fast", d, hold, tp, tier=tier))

# ── batch 2 ────────────────────────────────────────────────────────────────
F = 15          # fastest delay that is both priceable and reachable (FEASIBILITY.md §4)
LT100 = ["<$50k", "$50k–$100k"]
C2 = []
# B2.1 stacked short-hold branch: first caller, delay {15 s, 30 s, 1 min}, tier {all, elite, good} (mcap all) + tier all × mcap <$100k
for hold in (75, 150, 300, 450, 900):
    for d in (F, 30, 60):
        for tier, mc in ((None, None), ("elite", None), ("good", None), (None, LT100)):
            C2.append(mk("B2.1 short stacked", d, hold, "+50%", first="first", tier=tier, mcap=mc))
# B2.2 long-hold branch (delay 1 min)
for hold in (432000, 604800, 777600, 950400):
    for tp in ("none", "+100%", "+150%", "+200%"):
        for first in (None, "first"):
            C2.append(mk("B2.2 long", 60, hold, tp, first=first))
for hold in (604800, 950400):
    for mc in (["<$50k"], ["$50k–$100k"]):
        C2.append(mk("B2.2 long", 60, hold, "none", mcap=mc))
# B2.3 least-covered pairs at the held settings otherwise (1 min, 1 h, +50 %, all)
for d in (F, 30):
    for hold in (75, 150, 300, 450, 14400, 43200, 259200, 604800):
        C2.append(mk("B2.3 delay×hold", d, hold, "+50%"))
for hold in (75, 150, 777600, 950400):
    C2.append(mk("B2.3 delay×hold", 60, hold, "+50%"))
for d in (F, 30):
    for tp in ("+100%", "none", "+150%", "+200%"):
        C2.append(mk("B2.3 delay×tp", d, 3600, tp))
for tp in ("+150%", "+200%"):
    C2.append(mk("B2.3 delay×tp", 60, 3600, tp))
for tier in ("elite", "other"):
    for d in (F, 30):
        C2.append(mk("B2.3 tier×delay", d, 3600, "+50%", tier=tier))
for tier in ("elite", "good"):
    for hold in (900, 14400, 604800):
        C2.append(mk("B2.3 tier×hold", 60, hold, "+50%", tier=tier))
for age in ("<1 h", "1–6 h", "6–24 h", "1–7 d", ">7 d"):
    for hold in (900, 14400, 604800):
        C2.append(mk("B2.3 age×hold", 60, hold, "+50%", age=age))
for i, c in enumerate(C1):
    c["cell"] = i + 1
for i, c in enumerate(C2):
    c["cell"] = 1001 + i
json.dump(dict(batch=1, cells=C1, K=sum(1 for c in C1 if "rereadOf" not in c)), open(os.path.join(HERE, "cells1.json"), "w"), indent=1, ensure_ascii=False)
json.dump(dict(batch=2, cells=C2, K=sum(1 for c in C2 if "rereadOf" not in c)), open(os.path.join(HERE, "cells2.json"), "w"), indent=1, ensure_ascii=False)
print("batch1", len(C1), "K", sum(1 for c in C1 if "rereadOf" not in c), "| batch2", len(C2), "K", sum(1 for c in C2 if "rereadOf" not in c))
print("batch1 re-reads", [(c["delay"], c["hold"], c["tp"], c["filters"], c["rereadOf"]) for c in C1 if "rereadOf" in c])
print("batch2 re-reads", [(c["delay"], c["hold"], c["tp"], c["filters"], c["rereadOf"]) for c in C2 if "rereadOf" in c])
