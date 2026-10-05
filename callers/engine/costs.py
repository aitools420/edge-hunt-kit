#!/usr/bin/env python3
"""costs.py — PREREG §3: re-cost every booked position (calls AND twins) at REAL per-pool cost, and recompute the engine's OLD cost
(which must reproduce the engine's own booked number, check_old()). Never includes noxa.bot's own fee (f-nonoxafee).

REAL cost, per side, on the SAME trades the engine booked (entry pool and exit mark unchanged):
  V4 pool: LP fee + launchpad take (Pons: hook + creator tax from launch terms, R-0111) + transfer tax (realism tax table)
           + ETH<->quote hop when the pool is not ETH/WETH-quoted (R-0115; hop_static.json) ; price impact = the engine's own
           depth model (unchanged) ; gas = realism.gas_pts (measured, incl. failed attempts) + half a swap's gas per hop leg.
  V2/V3:   realism.cost_per_side (measured fee tier per coin where held, else 1 % V3 / 0.3 % V2; measured impact per ETH × clip; tax)
           + USDG hop when the tape row's quote is USDG.
  Pool classification order: realism pool_fees.json (receipt-measured) > edge-machine pool_costs_v1.json > hook from the pool tables
  (poolfee_lf.tsv / backfill newPools / pass B's venue label): Pons -> launch terms (else 2.39 % fallback, flagged) · Doppler hook ->
  the median measured Doppler take (LP + hook, 20 receipt-measured pools) · no hook -> fee key + 0.04 % ·
  dynamic fee -> the engine's own per-pool estimate · other hook -> fee key (take unmeasured, flagged) · nothing -> engine fee + 0.04 %.
OLD cost = the engine's: V4 entry fee efee and exit fee mfee in the depth model, V2/V3 1 % + 1 %, gas 0.2 % of the clip."""
import gzip, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.environ["CALLERS_EDGE_PATCHES"]          # kit: the edge-hunt-kit's patches/ folder
sys.path.insert(0, P + "/realism-2026-09-27")
import realism as RZ
PONS = "0xe5e702641ea86f4ae6cc3cdaed2b886f976be044"
E0 = "0x" + "0" * 40
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
DYN = 8388608
RESID = 0.0004
GAS_OLD = 0.002
HOPGAS_ETH = 0.5 * RZ.LAT["defaults"]["gas_eth_per_swap"]
STAT = collections.Counter()

BASE = json.load(open(P + "/edge-machine-2026-09-30/engine/pool_costs_v1.json"))["pools"]
PFM = {k: v for k, v in RZ.PF.items() if v.get("status") == "measured"}
PF = {}
with gzip.open(P + "/edge-machine-2026-09-30/engine/inputs/poolfee_lf.tsv.gz", "rt") as fh:
    for ln in fh:
        a = ln.rstrip("\n").split("\t")
        PF[a[0]] = (int(a[2]) if a[2].lstrip("-").isdigit() else None, a[3])
NP = {k: (v[0].lower(), v[1].lower(), v[2], (v[3] or "").lower()) for k, v in json.load(gzip.open(os.path.join(HERE, "inputs", "newpools.json.gz"), "rt")).items()}
TERMS = {}
for f in (P + "/v4-real-cost-2026-09-27/pons_launches.json", P + "/blood-realcost-2026-09-27/pons_launches_extra.json",
          P + "/blood-skeleton1-2026-09-27/pons_launches_sk.json"):
    for k, v in json.load(open(f)).items():
        if "err" not in v and v.get("hookFeeBps") is not None:
            TERMS[k] = (v["hookFeeBps"] + v["creatorTaxBps"]) / 1e4
for k, v in json.load(open(P + "/pons-feeterms-2026-09-27/pons_fee_terms.json"))["pools"].items():
    if v.get("status") == "measured":
        TERMS[k] = (v["hookFeeBps"] + v["creatorTaxBps"]) / 1e4
DOPPLER = "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544"
_dm = sorted(v["lp"] + v["hook"] for v in PFM.values() if v.get("doppler_labelled"))
DOPPLER_MED = (_dm[len(_dm) // 2 - 1] + _dm[len(_dm) // 2]) / 2 if len(_dm) % 2 == 0 else _dm[len(_dm) // 2]
VEN = {}
with open(os.path.join(HERE, "poolfee.tsv")) as fh:          # pass B's own pool table (fee key, venue) — the engine's source
    for ln in fh:
        a = ln.rstrip("\n").split("\t")
        VEN[a[0]] = (int(a[1]) if a[1].lstrip("-").isdigit() else None, a[2])
PQ = {}
with gzip.open(P + "/edge-machine-2026-09-30/engine/inputs/poolquote.tsv.gz", "rt") as fh:
    for ln in fh:
        a = ln.rstrip("\n").split("\t")
        PQ[a[0]] = (a[2], a[3], a[4])
HS = json.load(open(os.path.join(HERE, "hop_static.json")))
HOPT, HOPFB, HOPU = HS["tokens"], HS["fallback_other"], HS["usdg"]

def pool_fee(pool):
    """-> (static per-side fraction or None = use the engine's own fee at that side, kind, flag)"""
    m = PFM.get(pool)
    if m:
        return m["lp"] + m["hook"], "receipt", None
    b = BASE.get(pool)
    if b:
        t = b["type"]
        if t == "pons":
            return (b["take"], "pons", None) if b.get("take") is not None else (0.0239, "pons", "pons_no_terms")
        if t == "nohook":
            lp = b.get("lp_receipt") if b.get("lp_receipt") is not None else b.get("fee_key")
            return (None if lp is None else lp + RESID), "nohook", None
        if t == "dynfee":
            return b.get("lp_receipt"), "dynfee", None
        if t == "otherhook":
            lp = b.get("lp_receipt") if b.get("lp_receipt") is not None else b.get("fee_key")
            return lp, "otherhook", "take_unmeasured"
    fee, hook = (PF[pool] if pool in PF else ((NP[pool][2], NP[pool][3]) if pool in NP else (None, None)))
    if hook is None and fee is None:
        if pool not in VEN:
            return None, "unknown", "unknown_pool"
        fee, ven = VEN[pool]                                       # venue label only, no hook address
        if ven == "doppler":
            return DOPPLER_MED, "doppler", "doppler_median_take"
        if ven == "v4-nohook" and fee is not None and fee != DYN and fee < 1000000:
            return fee / 1e6 + RESID, "nohook", None
        if ven == "pons":
            return 0.0239, "pons", "pons_no_terms"
        if fee is None or fee == DYN or fee >= 1000000:
            return None, "otherhook", "venue_%s_dynfee_take_unmeasured" % (ven or "none")
        return fee / 1e6, "otherhook", "venue_%s_take_unmeasured" % (ven or "none")
    if hook == DOPPLER:
        return DOPPLER_MED, "doppler", "doppler_median_take"
    if hook == PONS:
        return (TERMS[pool], "pons", None) if pool in TERMS else (0.0239, "pons", "pons_no_terms")
    if hook in ("null", "", E0):
        if fee is None or fee == DYN or fee >= 1000000:
            return None, "nohook", "nohook_badfee"
        return fee / 1e6 + RESID, "nohook", None
    if fee == DYN:
        return None, "dynfee", None
    return (None if fee is None or fee >= 1000000 else fee / 1e6), "otherhook", "take_unmeasured"

def quote_of(pool, tok):
    """V4 pool -> None (ETH/WETH-quoted) or (quote address, class)"""
    q = PQ.get(pool)
    if q:
        return q[0], q[1]
    if pool in NP:
        c0, c1 = NP[pool][0], NP[pool][1]
        other = c1 if c0 == tok else c0
        if other in (E0, WETH):
            return None
        return other, ("USDG" if other == USDG else "other")
    return None

def hop_cost(qaddr):
    if qaddr == USDG:
        return HOPU["buy"], HOPU["sell"], "usdg"
    h = HOPT.get(qaddr)
    if h:
        return h["buy"], h["sell"], "table"
    return HOPFB["buy"], HOPFB["sell"], "fallback_other"

def side_costs(p):
    """per-position real cost inputs (computed once per position)"""
    tok = p["tok"]
    if p["v4"]:
        pool = p["src"]
        f, kind, flag = pool_fee(pool)
        q = quote_of(pool, tok)
        hb, hs, hsrc = hop_cost(q[0]) if q else (0.0, 0.0, None)
        tb, _ = RZ.tax(tok, "buy"); ts, _ = RZ.tax(tok, "sell")
        clip = p["clip"]
        STAT["v4"] += 1; STAT["v4|" + kind] += 1; STAT["v4|flag|%s" % flag] += 1; STAT["hop|%s" % hsrc] += 1
        STAT["tax>0"] += (tb > 0 or ts > 0)
        STAT["tax|in_table" if tok in RZ.TAX else "tax|not_in_table"] += 1
        return dict(v4=True, f=f, tb=tb, ts=ts, hb=hb, hs=hs, clip=clip,
                    gas=RZ.gas_pts(clip) + (100.0 * 2 * HOPGAS_ETH / clip if q else 0.0), kind=kind, flag=flag, hop=hsrc)
    _, kind, quote = p["src"].split(":")
    clip = 50.0 / RZ.eth_usd_at(p["ets"])
    key = "%s:%s" % (kind, quote)
    # AMENDMENT 1 (PREREG.sha256): realism's linear impact (measured impact per ETH x clip) is bounded the constant-product way,
    # u / (1 + u), so a coin whose one measured swap implies > 100 % impact cannot book a cost above 100 % (seen in the smoke:
    # impact_per_eth 5,718 -> 114x per side -> a +2.3M % "return"). For the normal u ~ 0.2 % the change is < 0.0004 pts.
    def _side(side):
        c = RZ.cost_per_side(key, tok, side, clip, engine_fee=0.01)
        u = c["impact"]
        return c["lp"] + c["take"] + c["tax"] + u / (1 + u)
    cb, cs = _side("buy"), _side("sell")
    hb, hs, hsrc = hop_cost(USDG) if quote == "USDG" else (0.0, 0.0, None)
    STAT["v23"] += 1; STAT["v23|" + key] += 1; STAT["hop|%s" % hsrc] += 1
    STAT["tax|in_table" if tok in RZ.TAX else "tax|not_in_table"] += 1
    return dict(v4=False, cb=cb, cs=cs, hb=hb, hs=hs, clip=clip,
                gas=RZ.gas_pts(clip) + (100.0 * 2 * HOPGAS_ETH / clip if hsrc else 0.0), kind=key, flag=None, hop=hsrc)

def real_n(p, sc, h):
    """REAL after-cost % for position p booked at mark h (book() dict)"""
    if sc["v4"]:
        fb = sc["f"] if sc["f"] is not None else p["efee"]
        fs = sc["f"] if sc["f"] is not None else h["mfee"]
        clip = sc["clip"]
        c = clip * (1 - fb) * (1 - sc["hb"])
        N = c / (p["epx"] * (1 + c / p["eDx"])) * (1 - sc["tb"])
        vv = N * (1 - sc["ts"]) * (1 - fs) * h["mpx"]
        proceeds = vv / (1 + vv / h["mDx"]) * (1 - sc["hs"])
        return 100.0 * (proceeds / clip - 1) - sc["gas"]
    return 100.0 * ((h["mpx"] / p["epx"]) * (1 - sc["cb"]) * (1 - sc["cs"]) * (1 - sc["hb"]) * (1 - sc["hs"]) - 1) - sc["gas"]

def old_n(p, h, mutate=False):
    """the engine's own value(), recomputed from the written fields (check_old compares it to the engine's booked n)"""
    if p["v4"]:
        clip = p["clip"]
        c = clip * (1 - p["efee"])
        N = c / (p["epx"] * (1 + c / p["eDx"]))
        vv = N * (1 - h["mfee"]) * h["mpx"]
        proceeds = vv / (1 + vv / h["mDx"]) if not mutate else vv
        return 100.0 * (proceeds / clip - 1 - GAS_OLD)
    return 100.0 * ((h["mpx"] / p["epx"]) * (1 - 0.01) * (1 - p["efee"]) - 1 - GAS_OLD)
