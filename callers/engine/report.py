#!/usr/bin/env python3
"""report.py — writes results<1|2>.json (explorer shape = callers-fill1 pass B's records + extra keys) and report<.txt|2.txt> from
analysis<1|2>.json. Usage: report.py 1|2"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = sys.argv[1]
A = json.load(open(os.path.join(HERE, "analysis%s.json" % BATCH)))
R = A["records"]; O = {r["cell"]: r for r in A["records_oldcost"]}
X = lambda r: r["exG5"]
f1 = lambda v: "n/a" if v is None else "%+.1f" % v
def rng(ci): return "[n/a]" if not ci else "[%+.1f, %+.1f]" % tuple(ci)
def short(r):
    x = X(r)
    if not x["n"]:
        return "n 0"
    s = "%s %s n %d" % (f1(x["mean"]), rng(x["ci95"]), x["n"])
    return s + (" (thin)" if x["n"] < 30 else "")
DEF = ("Buy the coin of each credited Telegram call (first call of a coin per caller) at the set delay after the post (first accepted "
       "print at or after that moment, within 5 min), $50 clip; sell at the set take-profit or at the end of the hold, on the entry pool. "
       "REAL on-chain costs per pool: LP fee, Pons hook + creator tax (R-0111), Doppler take, transfer tax, ETH<->quote-token hop "
       "(R-0115), measured V2/V3 fee + impact, measured gas. No noxa.bot fee. d = call minus the mean of 3 random coins of the same age "
       "and activity band bought at the same moment, same exits and costs. Headline view = 5 broken-price positions removed (ex-G5).")
held = dict(callers="all", delay="1 min", take_profit="+50%", hold="1 h", clip_usd=50, twins="3 matched random coins", cost="real per pool")
res = dict(study="Callers fast entries (batch 1)" if BATCH == "1" else "Callers batch 2: no-dot lines (short stacked, long hold, least-covered pairs)",
           date="2026-10-02", status="explore days, 5th read (callers round 3, callers-v4, dial test, fill batch 1, this) — LEADS only, never an edge",
           prereg_sha256=open(os.path.join(HERE, "PREREG.sha256")).read(), K_cells=A["K"],
           K_running=796 + (48 if BATCH == "1" else 48 + A["K"]), definition=DEF, held=held,
           pass_label="fast-%s · pass B data (backfill 07-20..09-11 + 22 recovered calls), real per-pool cost" % BATCH,
           schema_note=("records = REAL-cost cells in callers-fill1 pass B's record shape (dial/level/level2/hold/tp/delay/exG5/...), plus "
                        "cost='real', coords_labels (every dial's label), oldCost (the same trades at the explorer's old cost), tight (call and "
                        "twins filled within 15 s of the entry moment), paired (same calls: this delay minus 1 min), family (Holm). "
                        "records_oldcost = the same cells at the OLD engine cost (cost='old'). rereadOf = a pass-B cell this re-reads (not new K)."),
           records=R, records_oldcost=A["records_oldcost"], coverage=A["coverage"], family=A["family"], bridge=A["bridge"],
           bridgeAllIdentical=A["bridgeAllIdentical"], oldCostCheck=A["oldCostCheck"],
           data_gate=dict(gate=A["gate"], cost_classification=A["costStat"]), engine=A["engine"],
           explorer_loader=("Reuse edge-explorer/build.py callers_fill(S): its per-record mapping (dial/level/level2 + hold/tp/delay -> coords, "
                            "exG5 view) reads these records unchanged. Two cautions: (1) callers_fill REPLACES S['measured'] - merge these points into "
                            "the pass-B points instead (keyed by coords), and keep cost='real' visible, because the pass-B points are at the OLD cost "
                            "(records_oldcost here are the same cells at that old cost, for a like-for-like view); (2) labels the explorer lacks: "
                            "delay '5 s' (a bound, not reachable), market cap '<$100k' (two bands merged); multi-dial cells carry coords_labels."))
json.dump(res, open(os.path.join(HERE, "results.json" if BATCH == "1" else "results2.json"), "w"), indent=1, default=str, ensure_ascii=False)

L = []
F = A["family"]
pos = [r for r in R if X(r)["n"] >= 30 and (X(r)["mean"] or -1) > 0]
lb = [r for r in R if X(r)["n"] >= 30 and X(r)["ci95"] and X(r)["ci95"][0] > 0]
def lab(r):
    f = r["filters"]; s = "%s %s %s" % (r["delay"], r["hold"], r["tp"])
    return s + "".join(" %s=%s" % (k, ("<$100k" if v == ["<$50k", "$50k–$100k"] else v[0]) if k == "mcap" else v) for k, v in f.items())
best = sorted([r for r in R if X(r)["n"] >= 30], key=lambda r: -X(r)["mean"])[:3]
bestlb = sorted([r for r in R if X(r)["n"] >= 30 and X(r)["ci95"]], key=lambda r: -X(r)["ci95"][0])[:3]
if BATCH == "1":
    L.append("CALLERS FAST ENTRIES — batch 1 (2026-10-02, owner request). 48 cells: delay 5 s/15 s/30 s/1 min × hold 15 min/1 h/24 h × TP +50/+25 × tier All/Good. "
             "Pass B's data and engine; REAL per-pool costs (no noxa fee). 5th read of these days: LEADS at most. % per trade, ex-G5, [95 % range, conservative], d = vs 3 random coins.")
else:
    L.append("CALLERS BATCH 2 — no-dot lines (2026-10-02, owner request). 151 cells: B2.1 first caller × short holds × 15 s/30 s/1 min × tier/mcap; "
             "B2.2 long holds 5–11 d × TP; B2.3 least-covered pairs. Same engine, data, REAL costs and statistics as batch 1. 5th read: LEADS at most.")
L.append("VERDICT: %d of %d cells (n ≥ 30) have a mean above 0; %d have a 95 %% lower bar above 0 (expected by chance %.1f); Holm passes: mean %d, d %d. "
         "Lower bar > 0 on d: %d." % (len(pos), F["canTell"], len(lb), F["expectedByChance_each"], F["holmPassMean"], F["holmPassD"], F["lowerBarAbove0_d"]))
L.append("BEST 3 by mean: " + " · ".join("%s: %s, %d coins, d %s %s" % (lab(r), short(r), X(r)["coins"], f1(X(r)["d"]), rng(X(r)["d_ci95"])) for r in best))
L.append("BEST 3 by lower bar: " + " · ".join("%s: %s" % (lab(r), short(r)) for r in bestlb))
L.append("CHECKS: bridge (re-read cells' OLD view = pass B's records): %s (%d cells) · old-cost recompute: %s marks, %s mismatches." % (
    "IDENTICAL" if A["bridgeAllIdentical"] else "DIFFERS", len(A["bridge"]), A["oldCostCheck"].get("marks"), A["oldCostCheck"].get("mismatch", 0)))
cov = A["coverage"]
L.append("COVERAGE (priced with a twin, all calls, 1 h): " + " · ".join("%s %s%% (direct %s%%, CallAnalyser %s%%; fill lag p50/p75/p90 %s s; filled within 15 s %d%%)" % (
    k.replace("|", " tp"), round(100 * v["share_1 h"]), round(100 * v["share_1 h_direct"]), round(100 * v["share_1 h_CallAnalyser"]),
    "/".join(str(x) for x in v["fillLag_p50_p75_p90"]), round(100 * v["tightFilled"] / max(1, v["filled"]))) for k, v in cov.items() if k.endswith("|50")))
g = A["gate"]; cs = A["costStat"]
v4 = g.get("call|v4", 0); cp = g.get("call|positions", 1)
unm = sum(v for k, v in g.items() if k.startswith("call|flag|") and "take_unmeasured" in k)
L.append("COSTS (call positions read by this batch): V4 %d%% of entries; per-pool class: %s; hook take unmeasured on %d%% of call entries; hop on %d%% (fallback cost on %d%%); "
         "coins not in the tax table (0 tax assumed): %d%% of positions." % (
             round(100 * v4 / cp), ", ".join("%s %d%%" % (k.split("|")[2], round(100 * v / cp)) for k, v in sorted(g.items(), key=lambda kv: -kv[1]) if k.startswith("call|cost|")),
             round(100 * unm / cp), round(100 * sum(v for k, v in g.items() if k.startswith("call|hop|")) / cp),
             round(100 * g.get("call|hop|fallback_other", 0) / cp), round(100 * cs.get("tax|not_in_table", 0) / max(1, cs.get("tax|in_table", 0) + cs.get("tax|not_in_table", 0)))))
L.append("DATA GATE: G1 coverage above · G4 V2/V3 entries on a print below the $50 clip: calls %d of %d positions · G5 drained pools %d, >20× prints ignored %d (calls) · "
         "G7 cells with n < 30: %d of %d · G9 sealed data never read (asserted in engine and analyzer) · G10 twins same rules and costs · G11 not modelled: see PREREG §3." % (
             g.get("call|v23_entry_print_below_clip", 0), cp, g.get("call|drained", 0), g.get("call|gt20x_ignored", 0), sum(1 for r in R if X(r)["n"] < 30), len(R)))
L.append("")
if BATCH == "1":
    L.append("PER GROUP (tier · TP · hold): real cost by delay 5 s | 15 s | 30 s | 1 min ; then old cost at 1 min (= explorer) ; cost change ; paired delay effect (same calls, real) 15 s − 1 min ; TIGHT 15 s")
    grp = collections.OrderedDict()
    for r in R:
        grp.setdefault((r["filters"].get("tier", "all"), r["tp"], r["hold"]), {})[r["delay"]] = r
    for (tier, tp, hold), d in grp.items():
        m = d["1 min"]; o = O[m["cell"]]
        cc = (X(m)["mean"] - X(o)["mean"]) if X(m)["mean"] is not None and X(o)["mean"] is not None else None
        pr = d["15 s"]["paired"]; tg = d["15 s"]["tight"]
        L.append("%-4s %-5s %-6s | 5 s %s | 15 s %s | 30 s %s | 1 min %s d %s | old 1 min %s | cost change %s | delay 15 s−1 min %s %s n %d (old cost %s) | tight 15 s %s n %d" % (
            tier, tp, hold, short(d["5 s"]), short(d["15 s"]), short(d["30 s"]), short(m), f1(X(m)["d"]), short(o), f1(cc),
            f1(pr["meanDiff"]), rng(pr["ci95"]), pr["n"], f1(pr["oldCostMeanDiff"]), f1(tg["mean"]), tg["n"]))
    L.append("")
    L.append("LANE SPLIT (direct group posts can reach 15 s; CallAnalyser reposts cannot today), All · +50 % · 1 h, real cost, ex-G5 mean/n:")
    for r in R:
        if not r["filters"] and r["tp"] == "+50%" and r["hold"] == "1 h":
            ln = X(r)["lane"]
            L.append("  %s: direct %s n %d · CallAnalyser %s n %d · eras %s" % (r["delay"], f1(ln["direct"].get("mean")), ln["direct"]["n"],
                     f1(ln["CallAnalyser"].get("mean")), ln["CallAnalyser"]["n"], " / ".join("%s n %d" % (f1(v.get("mean")), v["n"]) for v in X(r)["era"].values())))
else:
    L.append("PER GROUP (one line per branch × fixed settings; cells listed as setting: real-cost mean [range] n, d)")
    grp = collections.OrderedDict()
    for r in R:
        f = r["filters"]
        if r["group"].startswith("B2.1"):
            k = (r["group"], "first caller", r["delay"], "tier " + f.get("tier", "all") + (" mcap <$100k" if "mcap" in f else ""))
            v = r["hold"]
        elif r["group"].startswith("B2.2"):
            k = (r["group"], r["hold"], "first" if "first" in f else ("mcap " + f["mcap"][0] if "mcap" in f else "all callers"))
            v = r["tp"]
        else:
            k = (r["group"], r["delay"] if "delay" in r["group"] and "tier" not in r["group"] else ("tier " + f.get("tier", "")) if "tier" in r["group"] else ("age " + f.get("age", "")))
            v = r["hold"] if "hold" in r["group"] else (r["tp"] if "tp" in r["group"] else r["delay"])
        grp.setdefault(k, []).append((v, r))
    for k, lst in grp.items():
        L.append(" · ".join(k) + " | " + " | ".join("%s: %s d %s%s" % (v, short(r), f1(X(r)["d"]), " rereads pass B" if r.get("rereadOf") else "") for v, r in lst))
L.append("")
L.append("CELLS WITH MEAN > 0 (n ≥ 30): " + ("; ".join("%s %s, %d coins, d %s, med %s, drop-5 %s, no-repeats %s%s" % (
    lab(r), short(r), X(r)["coins"], f1(X(r)["d"]), f1(X(r)["median"]), f1(X(r)["drop5"].get("mean")), f1(X(r)["norepMean"]),
    " LOWER BAR > 0" if X(r)["ci95"][0] > 0 else "") for r in sorted(pos, key=lambda r: -X(r)["mean"])) or "none"))
CD = os.path.join(HERE, "runlogs", "costdecomp_b%s.txt" % BATCH)   # post-hoc diagnostic, not a registered metric
if os.path.exists(CD):
    cd = {ln[:28].strip(): ln for ln in open(CD) if ln.strip()}
    pick = lambda k: re.search(r"mean real-old ([+-][0-9.]+).*contribution ([+-][0-9.]+)", cd[k]).groups() if k in cd else ("?", "?")
    L.append("WHERE THE COST CHANGE COMES FROM (post-hoc diagnostic; 1 min · 1 h · +50 %%, call trades): all %s pts; Pons pools (45 %% of trades) %s each = %s of it; "
             "stock-token hop pools (30 %%) %s each; Doppler (5 %%) %s each; hookless pools %s; V3 %s." % (
                 pick("all")[0], pick("class pons")[0], pick("class pons")[1], pick("hop table")[0], pick("class doppler")[0], pick("class nohook")[0], pick("class v3:WETH")[0]))
SQ = os.path.join(HERE, "squares_b%s.json" % BATCH)            # squares.py run on this batch's results (read-only on the explorer's data.json)
if os.path.exists(SQ):
    q = json.load(open(SQ))
    for view, txt in (("real", "at REAL cost"), ("old", "at the explorer's OLD cost")):
        v = q[view]
        L.append("EXPLORER GRID (%s; data.json %s): %d points placeable (%s unplaceable), %d setting pairs that had no dot now have one, new dial levels %s; "
                 "red dial-pair squares %d -> %d; changes: %s." % (txt, "Callers tab", v["placed"], v["unplaced"] or "none", v["newSettingPairs"],
                 ", ".join("%s %s" % tuple(x) for x in v["newLevels"]) or "none", v["squaresRedBefore"], v["squaresRedAfter"],
                 "; ".join("%s %s -> %s" % (f["pair"], f["before"], f["after"]) for f in v["flips"]) or "none"))
open(os.path.join(HERE, "report.txt" if BATCH == "1" else "report2.txt"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
