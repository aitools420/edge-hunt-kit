#!/usr/bin/env python3
"""analyze_fast.py — PREREG.md §5 (batch 1) / PREREG2.md §5 (batch 2). Per-cell statistics = callers-fill1 pass B's, VERBATIM:
analyze.py's block from `def se_iid` up to `ERAS = [` (se_*, summarize, drop5, small, cell) is exec()d from the byte-identical copy
here (sha256 asserted); only cell_rows is re-pointed at the cell's (delay, take-profit) position and cost view. Seed per cell =
20260930 + 11 × cell number (a cell that re-reads a pass-B cell uses pass B's cell number in the OLD view, so it must reproduce it).
Views per cell: REAL cost (headline, ex-G5 like pass B) · OLD cost (the engine's own numbers = what the explorer shows) ·
TIGHT (call and twins filled within 15 s of the entry moment) · PAIRED (same calls, this delay minus 1 min, real cost).
Writes results<1|2>.json, analysis<1|2>.json. Usage: analyze_fast.py 1|2"""
import collections, datetime as dt, hashlib, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import costs as C
BATCH = sys.argv[1]
SUF = os.environ.get("FAST_SUF", "")          # "_smoke" for the smoke test only
SEED, B, G5X = 20260930, 4000, 1900.0
SEAL = 1790467200
HOLDS = (75, 150, 300, 450, 900, 3600, 14400, 43200, 86400, 259200, 432000, 604800, 777600, 950400)
HL = ["1.25 min", "2.5 min", "5 min", "7.5 min", "15 min", "1 h", "4 h", "12 h", "24 h", "72 h", "5 d", "7 d", "9 d", "11 d"]
TPTAG = {"+50%": "50", "+25%": "25", "+100%": "100", "none": "none", "+150%": "150", "+200%": "200"}
RUN = {"50": "r1", "25": "r1", "100": "r1", "none": "r2", "150": "r2", "200": "r2"}
ERAS = ["pre-09-05 (backfilled V4)", "09-05→09-18 22:40 (locked-set V4)", "from 09-18 22:40 (every V4 pool)"]
TIGHT_S = 15
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
day = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")

src = open(os.path.join(HERE, "analyze.py")).read()
assert hashlib.sha256(src.encode()).hexdigest() == "9f136a7d68f738816eb51723718c96f089fba64fbc2600ca20ef62ea30d69024"
STATS = src[src.index("def se_iid("):src.index("ERAS = [")]
CELLS = json.load(open(os.path.join(HERE, "cells%s.json" % BATCH)))["cells"]
LEV = {int(k): v for k, v in json.load(open(os.path.join(HERE, "levels.json"))).items()}
need = sorted({(c["delaySec"], TPTAG[c["tp"]]) for c in CELLS} | {(60, TPTAG[c["tp"]]) for c in CELLS})
for d, t in list(need):
    if d != 60:
        need.append((60, t))
need = sorted(set(need))
print("keys", need, flush=True)

MPX = {}
for ln in open(os.path.join(HERE, "dials_fast%s_r1.ndjson" % SUF)):
    r = json.loads(ln); MPX[r["id"]] = r.get("mcapPxTs")

OLDCHK = collections.Counter()
def compact(p):
    if not p.get("fill"):
        return dict(fill=False)
    assert p["ets"] < SEAL
    sc = C.side_costs(p)
    h = []
    for x in p["h"]:
        if isinstance(x, dict):
            assert x["mts"] < SEAL
            o = C.old_n(p, x); OLDCHK["marks"] += 1
            if abs(o - x["n"]) > 2e-4:
                OLDCHK["mismatch"] += 1
            h.append((x["g"], x["n"], C.real_n(p, sc, x)))
        else:
            h.append(x)
    return dict(fill=True, v4=p["v4"], lag=p["lag"], h=h, tp=p["tp"], eusd=p.get("eusd"), drained=p.get("drained", False),
                hiIgn=p.get("hiIgn", 0), rug=p.get("rug"), kind=sc["kind"], flag=sc["flag"], hop=sc["hop"])

rows = {}
for run in sorted({RUN[t] for _, t in need}):
    keys = ["d%d_%s" % (d, t) for d, t in need if RUN[t] == run]
    for ln in open(os.path.join(HERE, "rows_fast%s_%s.ndjson" % (SUF, run))):
        r = json.loads(ln)
        assert r["ts"] < SEAL
        o = rows.get(r["id"])
        if o is None:
            o = rows[r["id"]] = {k: r[k] for k in ("id", "ts", "ca", "caller", "tier", "firstPrintLag")}
            o["L"] = LEV[r["id"]]; o["mcapPxTs"] = MPX.get(r["id"])
        for k in keys:
            x = r[k]; c = compact(x); c["twins"] = [compact(t) for t in x["twins"]]
            o[k] = c
    print("loaded", run, len(rows), dict(OLDCHK), flush=True)
assert OLDCHK["marks"] > 0 and OLDCHK["mismatch"] == 0, OLDCHK
ROWS = sorted(rows.values(), key=lambda r: list(rows).index(r["id"]) if False else 0)
ROWS = [rows[i] for i in rows]          # file order (= the engine's study order = pass B's)

g = dict(np=np, math=math, collections=collections, Phi=Phi, B=B, SEED=SEED, HL=HL, HOLDS=HOLDS, ERAS=ERAS, G5X=G5X, SEEDC=[SEED])
exec(compile(STATS, "analyze.py[stats block, verbatim]", "exec"), g)
firstrow = {}
for r in sorted(ROWS, key=lambda r: (r["ts"], r["id"])):
    firstrow.setdefault(r["ca"], r["id"])
g["firstrow"] = firstrow
CUR = dict(key="d60_50", vi=1, tight=False)
booked = lambda h: isinstance(h, tuple)
def cell_rows(sub, hi, exg5=False):
    out = []; K, vi, tight = CUR["key"], CUR["vi"], CUR["tight"]
    for r in sub:
        c = r[K]
        if not c["fill"] or not booked(c["h"][hi]):
            continue
        if exg5 and c["h"][hi][0] > G5X:
            continue
        if tight and c["lag"] > TIGHT_S:
            continue
        tw = [t["h"][hi] for t in c["twins"] if t["fill"] and booked(t["h"][hi]) and not (exg5 and t["h"][hi][0] > G5X)
              and not (tight and t["lag"] > TIGHT_S)]
        if not tw:
            continue
        ch = c["h"][hi]
        out.append(dict(r=r, ts=r["ts"], coin=r["ca"], day=day(r["ts"]), caller=r["caller"], cn=ch[vi], cg=ch[0],
                        tn=float(np.mean([t[vi] for t in tw])), tp=c["tp"][hi]))
    return out
g["cell_rows"] = cell_rows

def match(r, f, delay):
    for k, v in f.items():
        if k == "tier" and r["tier"] != v: return False
        if k == "first" and r["L"]["first"] != v: return False
        if k == "age" and r["L"]["age"] != v: return False
        if k == "mcap" and not (r["L"]["mcap"] in v and r["mcapPxTs"] is not None and r["mcapPxTs"] <= r["ts"] + delay): return False
    return True

def p1(m, ci):
    if m is None or not ci: return None
    se = (ci[1] - ci[0]) / 3.92
    return 1 - Phi(m / se) if se > 0 else None

def lab_dial(c):
    f = c["filters"]; dims = [("first", "first"), ("tier", "tier"), ("mcap", "mcap"), ("age", "age")]
    parts = [k for k, _ in dims if k in f]
    lv = lambda k: ("<$100k" if f[k] == ["<$50k", "$50k–$100k"] else f[k][0]) if k == "mcap" else f[k]
    if not parts:
        return "delay", c["delay"], None
    if len(parts) == 1:
        return "delay×" + parts[0], c["delay"], lv(parts[0])
    return "×".join(parts), lv(parts[0]), lv(parts[1])

PB = {r["cell"]: r for r in json.load(open(os.path.join(HERE, "..", "results", "callers-fill1-2026-09-30-passB", "results.json")))["records"] if not r.get("alias")}
CMP = ("n", "coins", "callers", "days", "mean", "ci95", "median", "se", "seUsed", "d", "d_ci95", "d_se", "drop5", "hitShare", "tpShare",
       "zeroCostMean", "norep", "exOutage", "era", "lane", "exG5")
recs, olds, bridge = [], [], []
for c in CELLS:
    key = "d%d_%s" % (c["delaySec"], TPTAG[c["tp"]]); hi = HOLDS.index(c["holdSec"])
    sub = [r for r in ROWS if match(r, c["filters"], c["delaySec"])]
    dial, level, level2 = lab_dial(c)
    meta = dict(tp=c["tp"], delay=c["delay"], group=c["group"], cell=c["cell"], filters=c["filters"])
    # OLD view (engine numbers); a pass-B re-read uses pass B's seed and must reproduce its record
    CUR.update(key=key, vi=1, tight=False)
    g["SEEDC"][0] = SEED + 11 * ((c.get("rereadOf") or c["cell"]) - 1)
    ro = g["cell"](sub, hi, dial, level, len(sub), extra=True)
    if c.get("rereadOf"):
        pb = PB[c["rereadOf"]]
        diff = [k for k in CMP if json.dumps(ro.get(k), sort_keys=True) != json.dumps(pb.get(k), sort_keys=True)]
        bridge.append(dict(cell=c["cell"], passB_cell=c["rereadOf"], identical=not diff, differing=diff))
    # REAL view (headline)
    CUR.update(vi=2)
    g["SEEDC"][0] = SEED + 11 * (c["cell"] - 1)
    rr = g["cell"](sub, hi, dial, level, len(sub), extra=True)
    # TIGHT view and PAIRED delay effect (real cost, ex-G5)
    CUR.update(tight=True)
    ct = cell_rows(sub, hi, exg5=True)
    st = g["summarize"]([x["cn"] for x in ct], ct, SEED + 7 * c["cell"]); sd = g["summarize"]([x["cn"] - x["tn"] for x in ct], ct, SEED + 7 * c["cell"] + 1)
    tight = dict(n=len(ct), coins=len({x["coin"] for x in ct}), mean=st.get("mean"), ci95=st.get("ci95"), d=sd.get("mean"), d_ci95=sd.get("ci95"))
    CUR.update(tight=False)
    paired = None
    if c["delaySec"] != 60:
        k60 = "d60_%s" % TPTAG[c["tp"]]
        CUR.update(key=k60); a = {x["r"]["id"]: x for x in cell_rows(sub, hi, exg5=True)}
        CUR.update(key=key); b = {x["r"]["id"]: x for x in cell_rows(sub, hi, exg5=True)}
        both = [i for i in b if i in a]
        pr = [dict(b[i], cn=b[i]["cn"] - a[i]["cn"]) for i in both]
        sp = g["summarize"]([x["cn"] for x in pr], pr, SEED + 7 * c["cell"] + 2)
        po = [b[i]["r"][key]["h"][hi][1] - a[i]["r"][k60]["h"][hi][1] for i in both]
        paired = dict(n=len(pr), meanDiff=sp.get("mean"), ci95=sp.get("ci95"), oldCostMeanDiff=round(float(np.mean(po)), 2) if po else None)
    filled = sum(1 for r in sub if r[key]["fill"])
    for rec in (ro, rr):
        rec["level2"] = level2
        rec.update(meta)
        rec["coverage"]["pending"] = sum(1 for r in sub if r[key]["fill"] and r[key]["h"][hi] == "oow")
        rec["coverage"]["filled"] = filled
        rec["coverage"]["tightFilled"] = sum(1 for r in sub if r[key]["fill"] and r[key]["lag"] <= TIGHT_S)
        if level2 is None:
            rec.pop("level2")
        if c.get("rereadOf"):
            rec["rereadOf"] = dict(study="callers-fill1-2026-09-30/passB", cell=c["rereadOf"])
    lbl = dict(delay=c["delay"], hold=c["hold"], tp=c["tp"], tier=c["filters"].get("tier", "all"), first=c["filters"].get("first", "all"),
               mcap=("<$100k" if c["filters"].get("mcap") == ["<$50k", "$50k–$100k"] else (c["filters"]["mcap"][0] if "mcap" in c["filters"] else "all")),
               age=c["filters"].get("age", "all"))
    rr.update(cost="real", coords_labels=lbl, tight=tight, paired=paired,
              oldCost=dict(n=ro["exG5"]["n"], mean=ro["exG5"]["mean"], ci95=ro["exG5"]["ci95"], d=ro["exG5"]["d"], median=ro["exG5"]["median"]))
    ro.update(cost="old", coords_labels=lbl)
    recs.append(rr); olds.append(ro)
    print("cell", c["cell"], c["delay"], c["hold"], c["tp"], c["filters"], "real", rr["exG5"]["n"], rr["exG5"]["mean"], "old", ro["exG5"]["mean"], flush=True)

# family: Holm (one-sided, alpha 0.025 = a 95 % lower bar above 0) across every cell of this batch, headline view (real, ex-G5)
def holm(ps, alpha=0.025):
    idx = sorted(range(len(ps)), key=lambda i: (ps[i] is None, ps[i] if ps[i] is not None else 1))
    ok = [False] * len(ps); m = len(ps)
    for j, i in enumerate(idx):
        if ps[i] is None or ps[i] >= alpha / (m - j):
            break
        ok[i] = True
    return ok
pm = [p1(r["exG5"]["mean"], r["exG5"]["ci95"]) if r["exG5"]["n"] >= 30 else None for r in recs]
pd = [p1(r["exG5"]["d"], r["exG5"]["d_ci95"]) if r["exG5"]["n"] >= 30 else None for r in recs]
hm, hd = holm(pm), holm(pd)
for r, a, b, x, y in zip(recs, pm, pd, hm, hd):
    r["family"] = dict(pMean=None if a is None else round(a, 5), pD=None if b is None else round(b, 5), holmMean=x, holmD=y)
K = len(recs)
fam = dict(K=K, alpha_one_sided=0.025, lowerBarAbove0_mean=sum(1 for r in recs if r["exG5"]["n"] >= 30 and r["exG5"]["ci95"] and r["exG5"]["ci95"][0] > 0),
           lowerBarAbove0_d=sum(1 for r in recs if r["exG5"]["n"] >= 30 and r["exG5"]["d_ci95"] and r["exG5"]["d_ci95"][0] > 0),
           expectedByChance_each=round(0.025 * sum(1 for r in recs if r["exG5"]["n"] >= 30), 2), holmPassMean=sum(hm), holmPassD=sum(hd),
           canTell=sum(1 for r in recs if r["exG5"]["n"] >= 30))

# coverage per delay × take profit (priced = booked call with >= 1 booked twin), all rows
cov = {}
for d, t in need:
    k = "d%d_%s" % (d, t)
    o = dict(rows=len(ROWS), filled=sum(1 for r in ROWS if r[k]["fill"]), tightFilled=sum(1 for r in ROWS if r[k]["fill"] and r[k]["lag"] <= TIGHT_S))
    CUR.update(key=k, vi=2, tight=False)
    for hl in ("15 min", "1 h", "24 h", "7 d"):
        hi = HL.index(hl); o["priced_" + hl] = len(cell_rows(ROWS, hi)); o["share_" + hl] = round(o["priced_" + hl] / len(ROWS), 3)
        o["pending_" + hl] = sum(1 for r in ROWS if r[k]["fill"] and r[k]["h"][hi] == "oow")
    lags = sorted(r[k]["lag"] for r in ROWS if r[k]["fill"])
    o["fillLag_p50_p75_p90"] = [lags[len(lags) // 2], lags[3 * len(lags) // 4], lags[int(0.9 * len(lags))]] if lags else None
    for lane in ("direct", "CallAnalyser"):
        sub = [r for r in ROWS if r["L"]["lane"] == lane]; hi = HL.index("1 h")
        o["share_1 h_" + lane] = round(len(cell_rows(sub, hi)) / max(1, len(sub)), 3)
    cov["%ds|%s" % (d, t)] = o

# data gate ingredients over every position the batch reads
gate = collections.Counter()
for d, t in need:
    k = "d%d_%s" % (d, t)
    for r in ROWS:
        x = r[k]
        for who, p in ([("call", x)] if x["fill"] else []) + [("twin", tw) for tw in x["twins"] if tw["fill"]]:
            gate["%s|positions" % who] += 1
            gate["%s|v4" % who] += p["v4"]
            if not p["v4"] and (p["eusd"] or 0) < 50: gate["%s|v23_entry_print_below_clip" % who] += 1
            gate["%s|drained" % who] += bool(p["drained"]); gate["%s|gt20x_ignored" % who] += p["hiIgn"] > 0
            gate["%s|cost|%s" % (who, p["kind"])] += 1
            if p["flag"]: gate["%s|flag|%s" % (who, p["flag"])] += 1
            if p["hop"]: gate["%s|hop|%s" % (who, p["hop"])] += 1
meta = {run: json.load(open(os.path.join(HERE, "engine_meta_fast%s_%s.json" % (SUF, run)))) for run in sorted({RUN[t] for _, t in need})}
out = dict(batch=BATCH, K=K, family=fam, bridge=bridge, bridgeAllIdentical=all(b["identical"] for b in bridge), oldCostCheck=dict(OLDCHK),
           coverage=cov, gate=dict(gate), costStat=dict(C.STAT), records=recs, records_oldcost=olds,
           engine={k: dict(bfDays=v["bfDays"], dataEnd=v["dataEnd"], sec=v["sec"], maxRssMB=v["maxRssMB"], prints=v["prints"], params=v["params"]) for k, v in meta.items()})
json.dump(out, open(os.path.join(HERE, "analysis%s%s.json" % (BATCH, SUF)), "w"), indent=1, default=str, ensure_ascii=False)
print("bridge", bridge, "family", fam, flush=True)
