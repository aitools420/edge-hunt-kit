#!/usr/bin/env python3
"""CALLERS DIAL BACKTEST — per-cell statistics, coverage and data gate over rows.ndjson + levels.json. PREREG §4–6 + Amendment 2.
SE estimators are callers-v4 analyze.py's, verbatim (conservative SE = max of six). Deterministic (seed 20260930).
Writes analysis_full.json and results.json (explorer records, one per cell)."""
import collections, datetime as dt, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SUF = sys.argv[1] if len(sys.argv) > 1 else ""
SEED = 20260930
B = 4000
HOLDS = (900, 3600, 14400, 43200, 86400, 259200)
HL = ["15 min", "1 h", "4 h", "12 h", "24 h", "72 h"]
H1, H24 = 1, 4

rows = [json.loads(l) for l in open(os.path.join(HERE, "rows%s.ndjson" % SUF))]
LEV = {int(k): v for k, v in json.load(open(os.path.join(HERE, "levels%s.json" % SUF))).items()}
BANDS = json.load(open(os.path.join(HERE, "bands%s.json" % SUF)))
meta = json.load(open(os.path.join(HERE, "engine_meta%s.json" % SUF)))
UNRES = json.load(open(os.path.join(HERE, "unresolved_rh.json")))
day = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
booked = lambda h: isinstance(h, dict)
for r in rows:
    r["L"] = LEV[r["id"]]
# no-repeats: the first study row of each coin
firstrow = {}
for r in sorted(rows, key=lambda r: (r["ts"], r["id"])):
    firstrow.setdefault(r["ca"], r["id"])

G5X = 1900.0     # Amendment 3: ex-G5 view drops positions with booked zero-cost gain > +1,900 %
def cell_rows(sub, hi, exg5=False):
    out = []
    for r in sub:
        c = r["d60"]
        if not c["fill"] or not booked(c["h"][hi]):
            continue
        if exg5 and c["h"][hi]["g"] > G5X:
            continue
        tw = [t["h"][hi] for t in c["twins"] if t["fill"] and booked(t["h"][hi]) and not (exg5 and t["h"][hi]["g"] > G5X)]
        if not tw:
            continue
        ch = c["h"][hi]
        out.append(dict(r=r, ts=r["ts"], coin=r["ca"], day=day(r["ts"]), caller=r["caller"], cn=ch["n"], cg=ch["g"],
                        tn=float(np.mean([t["n"] for t in tw])), tp=c["tp"][hi]))
    return out

# ── standard errors: callers-v4 analyze.py verbatim ────────────────────────
def se_iid(v):
    return float(np.std(v, ddof=1) / math.sqrt(len(v))) if len(v) > 1 else float("nan")

def se_cluster(v, keys):
    n = len(v)
    if n < 2:
        return float("nan")
    m = v.mean(); g = collections.defaultdict(float)
    for x, k in zip(v, keys):
        g[k] += x - m
    G = len(g)
    if G < 2:
        return float("nan")
    return math.sqrt(sum(s * s for s in g.values()) * G / (G - 1)) / n

def se_pigeon(v, coins, days, rng):
    cu = {c: i for i, c in enumerate(sorted(set(coins)))}; du = {d: i for i, d in enumerate(sorted(set(days)))}
    ci = np.array([cu[c] for c in coins]); di = np.array([du[d] for d in days])
    ms = []
    for s in range(0, B, 500):
        wc = rng.poisson(1.0, size=(500, len(cu))); wd = rng.poisson(1.0, size=(500, len(du)))
        w = (wc[:, ci] * wd[:, di]).astype(float); sw = w.sum(1)
        ok = sw > 0
        ms.extend(((w[ok] @ v) / sw[ok]).tolist())
    return float(np.std(ms, ddof=1))

def se_block(v, rng):
    n = len(v); L = max(1, math.ceil(math.sqrt(n))); nb = math.ceil(n / L)
    starts = rng.integers(0, n - L + 1, size=(B, nb)) if n > L else np.zeros((B, nb), dtype=int)
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(B, -1)[:, :n]
    idx = np.minimum(idx, n - 1)
    return float(np.std(v[idx].mean(1), ddof=1))

def summarize(vals, cr, seed):
    n = len(vals)
    if n == 0:
        return dict(n=0)
    v = np.array(vals, dtype=float)
    m = float(v.mean())
    if n < 3:
        return dict(n=n, mean=round(m, 2), median=round(float(np.median(v)), 2))
    order = np.argsort([x["ts"] for x in cr], kind="stable")
    rng = np.random.default_rng(seed)
    ses = dict(iid=se_iid(v), caller=se_cluster(v, [x["caller"] for x in cr]), coin=se_cluster(v, [x["coin"] for x in cr]),
               day=se_cluster(v, [x["day"] for x in cr]), pigeon=se_pigeon(v, [x["coin"] for x in cr], [x["day"] for x in cr], rng),
               block=se_block(v[order], rng))
    se = max(x for x in ses.values() if not math.isnan(x))
    return dict(n=n, mean=round(m, 2), median=round(float(np.median(v)), 2), se=round(se, 2),
                seWinner=max(ses, key=lambda k: -1 if math.isnan(ses[k]) else ses[k]),
                ci95=[round(m - 1.96 * se, 2), round(m + 1.96 * se, 2)], pOneSided=round(1 - Phi(m / se), 4) if se > 0 else None)

def drop5(cr):
    cm = collections.defaultdict(list)
    for x in cr:
        cm[x["coin"]].append(x["cn"])
    top = set(sorted(cm, key=lambda c: -np.mean(cm[c]))[:5])
    k = [x for x in cr if x["coin"] not in top]
    if not k:
        return dict(n=0)
    return dict(n=len(k), mean=round(float(np.mean([x["cn"] for x in k])), 2),
                d=round(float(np.mean([x["cn"] - x["tn"] for x in k])), 2))

def small(cr):
    if not cr:
        return dict(n=0)
    return dict(n=len(cr), mean=round(float(np.mean([x["cn"] for x in cr])), 2), d=round(float(np.mean([x["cn"] - x["tn"] for x in cr])), 2))

SEEDC = [SEED]
def cell(sub_all, hi, dial, level, level_rows, extra=True):
    """sub_all = study rows in the level; level_rows = count of study rows in the level (G1 denominator)"""
    SEEDC[0] += 11; s0 = SEEDC[0]
    cr = cell_rows(sub_all, hi)
    call = summarize([x["cn"] for x in cr], cr, s0)
    d = summarize([x["cn"] - x["tn"] for x in cr], cr, s0 + 1)
    nr = [x for x in cr if firstrow[x["coin"]] == x["r"]["id"]]
    rec = dict(dial=dial, level=level, hold=HL[hi], holdSec=HOLDS[hi], n=len(cr), coins=len({x["coin"] for x in cr}),
               callers=len({x["caller"] for x in cr}), days=len({x["day"] for x in cr}),
               mean=call.get("mean"), ci95=call.get("ci95"), median=call.get("median"), se=call.get("se"), seUsed=call.get("seWinner"),
               d=d.get("mean"), d_ci95=d.get("ci95"), d_se=d.get("se"),
               drop5=drop5(cr), hitShare=round(float(np.mean([x["cn"] > 0 for x in cr])), 3) if cr else None,
               tpShare=round(float(np.mean([x["tp"] for x in cr])), 3) if cr else None,
               zeroCostMean=round(float(np.mean([x["cg"] for x in cr])), 2) if cr else None,
               coverage=dict(rowsInLevel=level_rows, priced=len(cr), share=round(len(cr) / max(1, level_rows), 3)))
    if extra:
        nrc = summarize([x["cn"] for x in nr], nr, s0 + 2); nrd = summarize([x["cn"] - x["tn"] for x in nr], nr, s0 + 3)
        rec["norep"] = dict(n=len(nr), mean=nrc.get("mean"), ci95=nrc.get("ci95"), d=nrd.get("mean"), d_ci95=nrd.get("ci95"))
        xo = [x for x in cr if not x["r"]["L"]["outage"]]
        xoc = summarize([x["cn"] for x in xo], xo, s0 + 4); xod = summarize([x["cn"] - x["tn"] for x in xo], xo, s0 + 5)
        rec["exOutage"] = dict(n=len(xo), mean=xoc.get("mean"), ci95=xoc.get("ci95"), d=xod.get("mean"), d_ci95=xod.get("ci95"))
        rec["era"] = {e: small([x for x in cr if x["r"]["L"]["era"] == e]) for e in ERAS}
        rec["lane"] = {l: small([x for x in cr if x["r"]["L"]["lane"] == l]) for l in ("CallAnalyser", "direct")}
    xg = cell_rows(sub_all, hi, exg5=True)
    xgc = summarize([x["cn"] for x in xg], xg, s0 + 6); xgd = summarize([x["cn"] - x["tn"] for x in xg], xg, s0 + 7)
    xgn = [x for x in xg if firstrow[x["coin"]] == x["r"]["id"]]
    rec["exG5"] = dict(n=len(xg), coins=len({x["coin"] for x in xg}), mean=xgc.get("mean"), ci95=xgc.get("ci95"), median=xgc.get("median"),
                       d=xgd.get("mean"), d_ci95=xgd.get("ci95"), drop5=drop5(xg),
                       norepMean=round(float(np.mean([x["cn"] for x in xgn])), 2) if xgn else None,
                       hitShare=round(float(np.mean([x["cn"] > 0 for x in xg])), 3) if xg else None)
    if extra:
        rec["exG5"]["era"] = {e: small([x for x in xg if x["r"]["L"]["era"] == e]) for e in ERAS}
        rec["exG5"]["lane"] = {l: small([x for x in xg if x["r"]["L"]["lane"] == l]) for l in ("CallAnalyser", "direct")}
        xo = [x for x in xg if not x["r"]["L"]["outage"]]
        rec["exG5"]["exOutage"] = small(xo)
    ok = rec["n"] >= 30 and rec["coins"] >= 15
    rec["canTell"] = rec["n"] >= 30
    rec["lead"] = bool(ok and rec["ci95"] and rec["ci95"][0] > 0)
    rec["leadD"] = bool(ok and rec["d_ci95"] and rec["d_ci95"][0] > 0)
    X = rec["exG5"]; okx = X["n"] >= 30 and X["coins"] >= 15
    X["lead"] = bool(okx and X["ci95"] and X["ci95"][0] > 0); X["leadD"] = bool(okx and X["d_ci95"] and X["d_ci95"][0] > 0)
    if X["lead"] or X["leadD"]:
        X["leadNote"] = "carried by a few coins / repeats" if ((X["drop5"].get("mean") or -1) <= 0 or (X["norepMean"] or -1) <= 0) else "survives drop-5 and no-repeats"
    if rec["lead"] or rec["leadD"]:
        nm = rec.get("norep", {}).get("mean"); dm = rec["drop5"].get("mean")
        rec["leadNote"] = "carried by a few coins / repeats" if (dm is None or dm <= 0 or nm is None or nm <= 0) else "survives drop-5 and no-repeats"
    return rec

ERAS = ["pre-09-05 (backfilled V4)", "09-05→09-18 22:40 (locked-set V4)", "from 09-18 22:40 (every V4 pool)"]
DIALS = [("mcap", "Market cap at the call", BANDS["levels"] + ["unknown"]),
         ("runup", "Run-up in the hour before the call", ["<0", "0–50%", "50–200%", ">200%", "no print in the hour"]),
         ("first", "First caller vs follower", ["first", "follower ≤5 min", "follower 5–30 min", "follower 30–180 min",
                                                 "follower 3–24 h", "follower >24 h", "UNKNOWN (outage)"]),
         ("ncallers", "Callers who had called it by our entry", ["1", "2", "3+", "UNKNOWN (outage)"]),
         ("age", "Coin age at the call", ["<1 h", "1–6 h", "6–24 h", "1–7 d", ">7 d", "unknown"]),
         ("firstChat", "First chat vs follower (secondary)", ["first", "follower ≤5 min", "follower 5–30 min", "follower 30–180 min",
                                                              "follower 3–24 h", "follower >24 h", "UNKNOWN (outage)"]),
         ("nchats", "Chats that had called it by our entry (secondary)", ["1", "2", "3+", "UNKNOWN (outage)"])]

records = []
byL = collections.defaultdict(list)
for r in rows:
    for k, _, _ in DIALS:
        byL[(k, r["L"][k])].append(r)
# held-all reference + hold dial
for hi in range(len(HOLDS)):
    records.append(cell(rows, hi, "hold", HL[hi], len(rows)))
for k, name, levels in DIALS:
    for hi in (H1, H24):
        for lv in levels:
            sub = byL.get((k, lv), [])
            records.append(cell(sub, hi, k, lv, len(sub)))
for k in ("mcap", "runup"):
    levels = BANDS["levels"] if k == "mcap" else ["<0", "0–50%", "50–200%", ">200%", "no print in the hour"]
    for hi in range(len(HOLDS)):
        for lv in levels:
            sub = byL.get((k, lv), [])
            records.append(cell(sub, hi, "hold×" + k, lv, len(sub), extra=False))
print("cells", len(records))

# ── coverage (G1) by era / month, 1 min / 1 h, with and without unresolved RH calls in the denominator ──────────────
def cov(sub, hi=H1):
    c = collections.Counter(); who = collections.Counter()
    for r in sub:
        x = r["d60"]; c["rows"] += 1
        if x["fill"]:
            c["fill"] += 1
            h = x["h"][hi]
            if booked(h):
                c["priced"] += 1; c["priced_" + ("v4" if x["v4"] else "v23")] += 1
            else:
                c["outOfWindow"] += 1
        else:
            fl = r.get("firstPrintLag")
            if fl is None:
                who["no accepted print in 24 h: has a V4 pool in our data" if r["inV4Meta"] else "no accepted print in 24 h: no V4 pool and not on the V2/V3 tape"] += 1
            elif fl <= 60:
                who["traded before entry, no print in the 5-min window"] += 1
            else:
                who["first print later than the entry window"] += 1
    c = dict(c); c["pricedShare"] = round(c.get("priced", 0) / max(1, c["rows"]), 3)
    return dict(counts=c, unpricedWho=dict(who.most_common()))
def unres_in(f):
    return sum(1 for u in UNRES if f(u["ts"]))
coverage = {}
def era_of(t):
    return "pre-09-05 (backfilled V4)" if t < 1788566400 else ("09-05→09-18 22:40 (locked-set V4)" if t < 1789771200 else "from 09-18 22:40 (every V4 pool)")
groups = {"ALL": (rows, lambda t: True)}
for e in ERAS:
    groups[e] = ([r for r in rows if r["L"]["era"] == e], (lambda e: lambda t: era_of(t) == e)(e))
for m in sorted({r["L"]["month"] for r in rows}):
    groups[m] = ([r for r in rows if r["L"]["month"] == m], (lambda m: lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m") == m)(m))
groups["ex-outage"] = ([r for r in rows if not r["L"]["outage"]], lambda t: True)
for lab, (sub, f) in groups.items():
    c = cov(sub); u = unres_in(f) if lab != "ex-outage" else None
    c["unresolvedRhEvents"] = u
    if u is not None:
        c["pricedShareWithUnresolved"] = round(c["counts"].get("priced", 0) / max(1, c["counts"]["rows"] + u), 3)
    c["pricedShare_24h"] = cov(sub, H24)["counts"]["pricedShare"]
    c["pricedShare_72h"] = cov(sub, 5)["counts"]["pricedShare"]
    coverage[lab] = c

# ── data gate ingredients (1-min entries, calls and twins) ─────────────────
g4 = collections.Counter(); g5 = collections.Counter(); fees = collections.defaultdict(list)
for r in rows:
    x = r["d60"]
    for who, p in ([("call", x)] if x["fill"] else []) + [("twin", t) for t in x["twins"]]:
        v = "v4" if p["v4"] else "v23"
        g4[(who, v, "entries")] += 1
        if not p["v4"] and (p["eusd"] or 0) < 50:
            g4[(who, v, "entry_print_below_clip")] += 1
        if p["v4"]:
            fees[who].append(p["efee"])
        g5[(who, "positions")] += 1
        g5[(who, "drained_95pct")] += p.get("drained", False)
        g5[(who, "gt20x_ignored")] += p["hiIgn"] > 0
        g5[(who, "rug_lt5pct_exit")] += p["rug"]
        g5[(who, "booked_gt20x_any_hold")] += any(booked(h) and h["g"] > 1900 for h in p["h"])
feeMean = {w: round(100 * float(np.mean(L)), 2) for w, L in fees.items() if L}
drift = {e: dict(rows=len(groups[e][0]), coins=len({r["ca"] for r in groups[e][0]}),
                 twinUniverseMedian=float(np.median([r["nUniverse"] for r in groups[e][0]])) if groups[e][0] else None,
                 matchLevels=dict(collections.Counter(r["matchLevel"] for r in groups[e][0])))
         for e in ERAS}

A = dict(meta=meta, prereg=open(os.path.join(HERE, "PREREG.sha256")).read(), bands=BANDS, K=len(records), records=records,
         coverage=coverage, g4={"|".join(k): v for k, v in g4.items()}, g5={"|".join(k): v for k, v in g5.items()},
         v4EntryFeeMeanPct=feeMean, drift=drift)
json.dump(A, open(os.path.join(HERE, "analysis_full%s.json" % SUF), "w"), indent=1, default=str)

# ── explorer-ready results.json ────────────────────────────────────────────
DEF = ("Buy the coin of each credited Telegram call (first call of a coin per caller) 1 min after the post, $50 clip; sell at "
       "+50% take-profit or at the end of the hold. After real on-chain costs (pool fee, V4 price impact, gas; hook/creator taxes "
       "not modelled). d = call minus the mean of 3 random coins of the same age and activity band bought at the same moment.")
res = dict(study="Callers dial backtest (1-D skeleton + hold×mcap, hold×run-up)", date="2026-09-30",
           status="explore days, already read by callers round 3 and callers-v4 — LEADS only, never an edge",
           prereg_sha256=A["prereg"], bands=BANDS, K_cells=len(records), definition=DEF,
           held=dict(callers="all", delay="1 min", take_profit="+50%", clip_usd=50, twins="3 matched random coins"),
           records=records, coverage=coverage, data_gate=dict(g4=A["g4"], g5=A["g5"], v4_entry_fee_mean_pct=feeMean,
           lock_detector={k: v for k, v in meta["stat"].items() if k.startswith(("val_", "lock_"))}, drift=drift),
           engine=meta)
json.dump(res, open(os.path.join(HERE, "results%s.json" % SUF), "w"), indent=1, default=str)

def line(r):
    if r["n"] < 3:
        return "  %-28s %-6s n=%d" % (r["level"], r["hold"], r["n"])
    s = "  %-28s %-6s n=%4d c=%4d | mean %+7.2f [%+7.2f,%+7.2f] | d %+7.2f [%+7.2f,%+7.2f] | d5 %s | norep %s | hit %.2f tp %.2f | cov %.2f" % (
        r["level"], r["hold"], r["n"], r["coins"], r["mean"], r["ci95"][0], r["ci95"][1], r["d"], r["d_ci95"][0], r["d_ci95"][1],
        r["drop5"].get("mean"), (r.get("norep") or {}).get("mean"), r["hitShare"], r["tpShare"], r["coverage"]["share"])
    X = r["exG5"]
    if X["n"] >= 3:
        s += " || exG5 n=%d mean %+.2f [%+.2f,%+.2f] d %+.2f [%+.2f,%+.2f] med %+.2f d5 %s nr %s hit %.2f%s" % (X["n"], X["mean"], X["ci95"][0], X["ci95"][1],
             X["d"], X["d_ci95"][0], X["d_ci95"][1], X["median"], X["drop5"].get("mean"), X["norepMean"], X["hitShare"],
             ("  <<xLEAD%s %s" % ("" if X["lead"] else "(d)", X["leadNote"])) if (X["lead"] or X["leadD"]) else "")
        if "lane" in X:
            s += " | xlane CA %s/%s dir %s/%s | xExOut %s/%s | xera %s" % (X["lane"]["CallAnalyser"].get("mean"), X["lane"]["CallAnalyser"]["n"],
                 X["lane"]["direct"].get("mean"), X["lane"]["direct"]["n"], X["exOutage"].get("mean"), X["exOutage"]["n"],
                 " ".join("%s/%s" % (v.get("mean"), v["n"]) for v in X["era"].values()))
    if False:
        s += " | exOut %s/%s" % (r["exOutage"].get("mean"), r["exOutage"]["n"])
        s += " | lane CA %s/%s dir %s/%s" % (r["lane"]["CallAnalyser"].get("mean"), r["lane"]["CallAnalyser"]["n"],
                                           r["lane"]["direct"].get("mean"), r["lane"]["direct"]["n"])
        s += " | era " + " ".join("%s/%s" % (v.get("mean"), v["n"]) for v in r["era"].values())
    if r["lead"] or r["leadD"]:
        s += "  <<LEAD%s %s" % ("" if r["lead"] else "(d)", r["leadNote"])
    return s
cur = None
for r in records:
    if r["dial"] != cur:
        cur = r["dial"]; print("==", cur)
    print(line(r))
print(json.dumps({k: dict(v["counts"], unres=v["unresolvedRhEvents"], withUnres=v.get("pricedShareWithUnresolved"),
                          s24=v["pricedShare_24h"], s72=v["pricedShare_72h"]) for k, v in coverage.items()}, indent=0))
