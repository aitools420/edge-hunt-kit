#!/usr/bin/env python3
"""CALLERS DIAL BACKTEST engine = callers-v4-2026-09-27/engine.py EXTENDED (rules: PREREG.md, sha256 in PREREG.sha256).
Changes vs callers-v4 (PREREG §8): V4 = backfill-join ∪ v4-join (backfill row wins on a shared (blk, li), R-0114) with the
pre-registered lock-row detector on days without a backfill row; out-of-window booking rule; delay 1 min only; six holds
(15 m … 72 h); run-up / price-at-call watchers; dial inputs written to dials.ndjson (NO return field), returns to rows.ndjson.
RESEARCH ONLY: read-only outside this folder. SEALED: tape-2026-09-27 never opened; V4 days via v4tape.v4_path (refuses the sealed
day); any row with ts >= 1790467200 raises; no call at/after 2026-09-27T00:00Z is used.
Usage: engine.py [LAST_DAY]   (LAST_DAY < 2026-09-26 = smoke run, outputs *_smoke)
"""
import collections, datetime as dt, heapq, json, math, os, random, re, resource, subprocess, sys, time
import orjson
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/green/projects/patches/v4-join-2026-09-27")
import v4tape
from guard import G, accept

WLOGS = "/home/green/.openclaw/workspace/wick-engine/logs"
TAPE_DIR = os.path.join(WLOGS, "robinhood-tape")
ARCH = os.path.join(WLOGS, "archive")
V4_BIRTHS = os.path.join(WLOGS, "robinhood-v4-births.ndjson")
TOK_BIRTHS = os.path.join(WLOGS, "robinhood-token-births.json")
BF_DIR = "/home/green/projects/patches/v4-backfill-join-2026-09-29/out"
SEALED_FILE = "tape-2026-09-27.ndjson"
SEAL_TS = 1790467200
DATA_END = 1790463649
LAST_DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-09-26"
if LAST_DAY >= "2026-09-27":
    raise SystemExit("sealed")
OUT_SUFFIX = "" if LAST_DAY == "2026-09-26" else "_smoke"
if OUT_SUFFIX:
    DATA_END = int(dt.datetime.fromisoformat(LAST_DAY + "T23:59:59+00:00").timestamp())

SEED = 20260927
DELAYS = (60,)
HOLDS = (900, 3600, 14400, 43200, 86400, 259200)
TP = 1.50
TP_SALE_SEC = 60
MAX_LAG = 300
MIN_USD_V23 = 10.0
MIN_USD_V4 = 1.0
ACT_USD = 10.0
CLIP_USD = 50.0
GAS = 0.002
FEE_V23 = 0.01
FEE_DEFAULT = 0.01
K1 = math.sqrt(1.01) - 1
HI_X, RUG_X, CORR_SEC = 20.0, 0.05, 1800
POOL_FRESH = 1800
NCAND, K_TWIN, MIN_MATCH = 12, 3, 5
SMART_LAG, SMART_HOLD, SMART_STOP, SMART_FEE = 3600, 21600, 0.25, 2.0
AGE_EDGES = (3600, 6 * 3600, 86400, 7 * 86400)
ACT_EDGES = (3, 10, 50)
DYN = 8388608
RUNUP_SEC, AFTER_SEC = 3600, 360

T0 = time.time()
def log(*a):
    print("[%6.0fs rss %4dMB]" % (time.time() - T0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024), *a, flush=True)

def band(x, edges):
    for i, e in enumerate(edges):
        if x < e:
            return i
    return len(edges)

# ── backfill-join days: the unbroken run from its first day, snapshotted at start ─────────────────────────────────
def _bf_days():
    ds = sorted(m.group(1) for m in (re.match(r"^v4-swaps-(\d{4}-\d\d-\d\d)\.ndjson\.gz$", f) for f in os.listdir(BF_DIR)) if m)
    run = ds[:1]
    for d in ds[1:]:
        if (dt.date.fromisoformat(d) - dt.date.fromisoformat(run[-1])).days == 1:
            run.append(d)
        else:
            break
    return [d for d in run if d <= "2026-09-26"]
BF_DAYS = _bf_days()
BF_SET = set(BF_DAYS)
BF_END_TS = int(dt.datetime.fromisoformat(BF_DAYS[-1] + "T00:00:00+00:00").timestamp()) + 86400 if BF_DAYS else 0
BF_START_TS = int(dt.datetime.fromisoformat(BF_DAYS[0] + "T00:00:00+00:00").timestamp()) if BF_DAYS else 0
log("backfill days", len(BF_DAYS), BF_DAYS[:1], BF_DAYS[-1:], "BF_END_TS", BF_END_TS)

# ── static inputs ──────────────────────────────────────────────────────────
SNAP = json.load(open(os.path.join(HERE, "calls_snapshot.json")))
EVENTS = [e for e in SNAP["events"] if e["ts"] < SEAL_TS]
ROWSET = {e["id"] for e in SNAP["rows"] if e["ts"] < SEAL_TS}
CALLED = {e["ca"] for e in EVENTS}
log("events", len(EVENTS), "study rows", len(ROWSET))
CM = json.load(open(os.path.join(HERE, "calledmeta.json")))

POOLFEE, POOLVEN = {}, {}
birth = {}
with open(os.path.join(HERE, "poolfee.tsv")) as fh:
    for ln in fh:
        f = ln.rstrip("\n").split("\t")
        POOLFEE[f[0]] = int(f[1]) if f[1] else None
        if f[2]:
            POOLVEN[f[0]] = f[2]
        if f[3] and f[4]:
            bt = int(f[4]); tk = f[3]
            if tk not in birth or bt < birth[tk]:
                birth[tk] = bt
with open(V4_BIRTHS, "rb") as fh:
    for ln in fh:
        if b'"birthTs"' not in ln:
            continue
        try:
            r = orjson.loads(ln)
        except Exception:
            continue
        tk, bt = (r.get("tok") or "").lower(), r.get("birthTs")
        if tk and bt and (tk not in birth or bt < birth[tk]):
            birth[tk] = bt
pat = re.compile(rb'"(0x[0-9a-f]{40})":\{[^{}\[]*?"firstTs":(\d+)')
with open(TOK_BIRTHS, "rb") as fh:
    carry = b""
    while True:
        ch = fh.read(16 << 20)
        if not ch:
            break
        buf = carry + ch
        for m in pat.finditer(buf):
            tk = m.group(1).decode(); bt = int(m.group(2))
            if tk not in birth or bt < birth[tk]:
                birth[tk] = bt
        carry = buf[-8192:]
log("pools", len(POOLFEE), "births", len(birth))

STAT = collections.Counter()

def static_fee(pool):
    f = POOLFEE.get(pool)
    if f is None or f == DYN or f >= 1000000 or f < 0:
        return None
    return f / 1e6

# ── feeds ──────────────────────────────────────────────────────────────────
def tape_files():
    paths = {f: os.path.join(TAPE_DIR, f) for f in os.listdir(TAPE_DIR)
             if f.startswith("tape-") and f.endswith(".ndjson")}
    for m in sorted(os.listdir(ARCH)):
        d = os.path.join(ARCH, m)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.startswith("tape-") and f.endswith(".ndjson.gz") and f[:-3] not in paths:
                    paths[f[:-3]] = os.path.join(d, f)
    paths.pop(SEALED_FILE, None)
    for f in [f for f in paths if f >= SEALED_FILE]:     # sealed-period day files: dropped by NAME, never opened
        paths.pop(f)
    keep = []
    for f in sorted(paths):
        if f >= SEALED_FILE:
            raise SystemExit("sealed file in list: " + f)
        if f[5:15] <= LAST_DAY:
            keep.append(paths[f])
    return keep

def lines_of(p):
    if p.endswith(".gz"):
        pr = subprocess.Popen(["pigz", "-dc", p], stdout=subprocess.PIPE, bufsize=1 << 20)
        yield from pr.stdout
        pr.wait()
    else:
        with open(p, "rb") as fh:
            yield from fh

# tuple: (ts, feed, tok, px, src, usd, tx, D, L, fee, pool, eth_usd, pxusd, dec_used)
def gen_v23():
    for p in tape_files():
        STAT["v23_files"] += 1
        for ln in lines_of(p):
            try:
                r = orjson.loads(ln)
            except Exception:
                STAT["v23_bad"] += 1
                continue
            ts, px, tk = r.get("ts"), r.get("px"), r.get("tok")
            if not ts or not tk or not px or px <= 0:
                continue
            if ts >= SEAL_TS:
                raise SystemExit("sealed row reached")
            if ts > DATA_END:
                STAT["v23_past_end"] += 1
                continue
            usd = r.get("usd")
            if usd is None or usd < MIN_USD_V23:
                STAT["v23_small"] += 1
                continue
            STAT["v23_rows"] += 1
            yield (ts, 0, tk.lower(), px, "t:%s:%s" % (r.get("kind") or "?", r.get("quote") or "?"), usd, r.get("tx"),
                   None, None, FEE_V23, None, None, px, None)

# R-0114 lock-row detector state (per labelled pool: last liquidity seen; per token: its pools)
LASTL = {}
TOKP = collections.defaultdict(set)
def lock_suspect(r):
    """PREREG §2: labelled pool's last liquidity differs AND another pool of the token last showed exactly this liquidity."""
    pl, L = r["pool"], r.get("liquidity")
    last = LASTL.get(pl)
    if last is None or L is None or L == last:
        return None if last is None else False
    for p2 in TOKP.get(r["tok"], ()):
        if p2 != pl and LASTL.get(p2) == L:
            return True
    return False

def note_state(r):
    LASTL[r["pool"]] = r.get("liquidity")
    TOKP[r["tok"]].add(r["pool"])

def raw_rows(p):
    if not p:
        return
    for ln in lines_of(p):
        yield orjson.loads(ln)

def v4_day_rows(day):
    """union on (blk, li); backfill row wins; lock detector validated on shared keys, applied on days without a backfill file"""
    jp = v4tape.v4_path(day)               # refuses the sealed holdout
    bp = os.path.join(BF_DIR, "v4-swaps-%s.ndjson.gz" % day) if day in BF_SET else None
    if bp:
        A, B = raw_rows(bp), raw_rows(jp)
        a, b = next(A, None), next(B, None)
        while a is not None or b is not None:
            if b is None or (a is not None and (a["blk"], a["li"]) < (b["blk"], b["li"])):
                note_state(a); yield a; a = next(A, None)
            elif a is None or (b["blk"], b["li"]) < (a["blk"], a["li"]):
                STAT["v4_join_only_on_bf_day"] += 1
                note_state(b); yield b; b = next(B, None)
            else:
                if b.get("src") == "lock":
                    wrong = a["pool"] != b["pool"]
                    s = lock_suspect(b)
                    STAT["val_lock_rows"] += 1
                    STAT["val_lock_wrong"] += wrong
                    if s is None:
                        STAT["val_unjudgeable"] += 1; STAT["val_unjudgeable_wrong"] += wrong
                    elif s:
                        STAT["val_flag_tp" if wrong else "val_flag_fp"] += 1
                    elif wrong:
                        STAT["val_miss"] += 1
                STAT["v4_shared_key_bf_used"] += 1
                note_state(a); yield a
                a, b = next(A, None), next(B, None)
    else:
        for r in raw_rows(jp):
            if r.get("src") == "lock":
                STAT["lock_rows_nobf"] += 1
                if lock_suspect(r):
                    STAT["lock_dropped"] += 1
                    continue
            note_state(r); yield r

dynfee = {}
def gen_v4():
    for day in v4tape.days("2026-07-20", LAST_DAY):
        if not v4tape.v4_path(day) and day not in BF_SET:
            continue
        STAT["v4_days"] += 1
        STAT["v4_days_bf"] += day in BF_SET
        isbf = day in BF_SET
        for r in v4_day_rows(day):
            ts = r["ts"]
            if ts >= SEAL_TS:
                raise SystemExit("sealed row reached")
            if ts > DATA_END:
                STAT["v4_past_end"] += 1
                continue
            pe, d1, usd = r.get("price_eth"), r.get("depth1_eth"), r.get("usd")
            if r.get("liquidity") == "0":
                STAT["v4_liq0"] += 1
                continue
            if not pe or pe <= 0 or not d1 or d1 <= 0 or usd is None:
                STAT["v4_unpriced"] += 1
                continue
            if usd < MIN_USD_V4:
                STAT["v4_small"] += 1
                continue
            pool = r["pool"]
            D = d1 / K1
            fee = static_fee(pool)
            if fee is None:
                if POOLFEE.get(pool) == DYN and usd >= ACT_USD:
                    try:
                        pq = r["price_quote"]; qeth = pe / pq
                        N, aq = r["amount_token"], r["amount_quote"] * qeth
                        if r["side"] == "buy":
                            f_ = 1 - (N * pe / (1 + N * pe / D)) / aq
                        else:
                            f_ = 1 - (aq / (pe * (1 + aq / D))) / N
                        if 0 <= f_ < 0.99:
                            dynfee[pool] = f_
                    except Exception:
                        pass
                fee = dynfee.get(pool, FEE_DEFAULT)
            STAT["v4_rows"] += 1
            STAT["v4_rows_bf" if isbf else "v4_rows_join"] += 1
            tk = r["tok"]
            dec_used = None
            if tk in CALLED:
                cm = CM.get(tk) or {}
                dec_used = cm.get("decJoin") if cm.get("decJoin") is not None else (
                    (cm.get("decExtra") or 18) if r.get("src") == "bfw" else 18)
            yield (ts, 1, tk, pe, pool, usd, r["tx"], D, float(r["liquidity"]), fee, pool, r["eth_usd"],
                   pe * (r["eth_usd"] or 0), dec_used)

# ── positions ──────────────────────────────────────────────────────────────
NH = len(HOLDS)
class Pos:
    __slots__ = ("tok", "start", "lag", "kind", "src", "v4", "ets", "epx", "eD", "efee", "eL", "eusd", "N", "clip",
                 "last", "tp_ts", "tp_mark", "rug", "highs", "nhi_ign", "nhi_ok", "Lmin", "stopped", "dead",
                 "fill_lag", "done", "lastM")
    def __init__(self, tok, start, lag, kind):
        self.tok = tok; self.start = start; self.lag = lag; self.kind = kind
        self.src = None; self.v4 = False; self.ets = None; self.epx = None; self.eD = None; self.efee = None
        self.eL = None; self.eusd = None; self.N = None; self.clip = None
        self.last = None; self.tp_ts = None; self.tp_mark = None; self.rug = None; self.highs = None
        self.nhi_ign = 0; self.nhi_ok = 0; self.Lmin = None; self.stopped = False; self.dead = False
        self.fill_lag = None; self.done = False; self.lastM = None

active = collections.defaultdict(list)
poolstate = {}
tokpools = collections.defaultdict(set)

def enter(p, row):
    ts, feed, tk, px, src, usd, tx, D, L, fee, pool, eu = row[:12]
    p.ets = ts; p.fill_lag = ts - p.start
    if feed == 1 and p.kind == "S":
        clip = CLIP_USD / eu
        best = None
        for pl in tokpools[tk]:
            st = poolstate.get(pl)
            if st is None or st[0] < ts - POOL_FRESH:
                continue
            c = clip * (1 - st[3])
            cost = st[3] + c / st[2]
            if best is None or cost < best[0]:
                best = (cost, pl, st)
        _, pl, st = best
        p.src = pl; p.v4 = True; p.epx = st[1]; p.eD = st[2]; p.efee = st[3]; p.eL = st[4]; p.eusd = st[5]
        p.clip = clip
        c = p.clip * (1 - p.efee)
        p.N = c / (p.epx * (1 + c / p.eD))
        p.Lmin = p.eL
        STAT["v4_entry_switched_pool"] += pl != pool
    else:
        p.src = src; p.v4 = feed == 1; p.epx = px; p.eusd = usd; p.efee = fee
    p.last = [None] * NH if p.kind == "S" else None

def valid_print(p, row):
    ts, feed, tk, px, src, usd, tx, D = row[:8]
    x = px / p.epx
    if x < RUG_X:
        return True, True
    ok = True
    if x > HI_X:
        ok = False
        if p.v4 and D is not None and D >= p.N * px:
            ok = True
        elif p.highs:
            for (t0, tx0, px0) in p.highs:
                if t0 >= ts - CORR_SEC and tx0 != tx and px / 2 <= px0 <= px * 2:
                    ok = True; break
        if ok:
            p.nhi_ok += 1
        else:
            p.nhi_ign += 1
    if x > HI_X / 2 and usd >= ACT_USD:
        if p.highs is None:
            p.highs = collections.deque()
        p.highs.append((ts, tx, px))
        while p.highs and p.highs[0][0] < ts - CORR_SEC:
            p.highs.popleft()
    return ok, False

HMAX = HOLDS[-1]
def on_print(row):
    ts, feed, tk, px, src, usd, tx, D, L, fee = row[:10]
    lst = active.get(tk)
    if not lst:
        return
    keep = []
    for p in lst:
        if p.ets is None:
            if ts < p.start:
                keep.append(p); continue
            if ts - p.start > p.lag:
                p.dead = True; continue
            if p.kind == "F":
                p.ets = ts; p.fill_lag = ts - p.start; p.src = src; continue
            enter(p, row)
            keep.append(p); continue
        if src != p.src or ts <= p.ets:
            keep.append(p); continue
        if p.kind == "S":
            if p.v4 and L is not None and (p.Lmin is None or L < p.Lmin):
                p.Lmin = L
            ok, rug = valid_print(p, row)
            dt_ = ts - p.ets
            if ok:
                mark = (ts, px, D, fee, usd)
                for hi in range(NH):
                    if dt_ <= HOLDS[hi]:
                        p.last[hi] = mark
                if p.tp_ts is None:
                    if dt_ <= HMAX and px >= TP * p.epx:
                        p.tp_ts, p.tp_mark = ts, mark
                elif ts <= p.tp_ts + TP_SALE_SEC:
                    p.tp_mark = mark
                if rug and p.rug is None and (p.tp_ts is None or ts > p.tp_ts + TP_SALE_SEC or p.tp_ts == ts):
                    if p.tp_ts == ts:
                        p.tp_ts = None; p.tp_mark = None
                    p.rug = mark
            done = (p.rug is not None) or (p.tp_ts is not None and ts > p.tp_ts + TP_SALE_SEC) or \
                   (p.tp_ts is None and dt_ > HMAX)
        else:   # M — production tier method (print prices)
            dt_ = ts - p.ets
            if dt_ <= SMART_HOLD:
                p.lastM = px
                if px <= (1 - SMART_STOP) * p.epx:
                    p.stopped = True
            done = dt_ > SMART_HOLD or p.stopped
        if not done:
            keep.append(p)
        else:
            p.done = True
    if keep:
        active[tk] = keep
    else:
        del active[tk]

def value(p, mark):
    px = mark[1]
    g = 100.0 * (px / p.epx - 1)
    if p.v4:
        vv = p.N * (1 - mark[3]) * px
        proceeds = vv / (1 + vv / mark[2])
        n = 100.0 * (proceeds / p.clip - 1 - GAS)
    else:
        n = 100.0 * ((px / p.epx) * (1 - FEE_V23) * (1 - p.efee) - 1 - GAS)
    return g, n

def cov_end(p):
    """PREREG §2 out-of-window rule: the source's data coverage end for this position"""
    if p.v4 and BF_START_TS <= p.ets < BF_END_TS:
        return min(DATA_END, BF_END_TS)
    return DATA_END

def book(p, hi):
    if p.ets is None:
        return None
    H = HOLDS[hi]
    if p.ets + H + TP_SALE_SEC > cov_end(p):
        return "oow"
    entry_mark = (p.ets, p.epx, p.eD, p.efee, p.eusd)
    if p.rug is not None and p.rug[0] <= p.ets + H and (p.tp_ts is None or p.tp_ts > p.ets + H or p.tp_ts > p.rug[0]):
        m, how = p.rug, "rug"
    elif p.tp_ts is not None and p.tp_ts <= p.ets + H:
        m, how = p.tp_mark, "tp"
    else:
        m = p.last[hi] if p.last[hi] is not None else entry_mark
        how = "hold" if p.last[hi] is not None else "noprint"
    g, n = value(p, m)
    return dict(g=round(g, 4), n=round(n, 4), how=how, mts=m[0], mpx=m[1], musd=m[4],
                mD=None if m[2] is None else round(m[2], 6), mfee=m[3])

def smart_val(p):
    if p.stopped:
        return -100 * SMART_STOP - SMART_FEE
    x = p.lastM if p.lastM is not None else p.epx
    return 100.0 * (x / p.epx - 1) - SMART_FEE

# ── run-up / price-at-call watchers (PREREG §3 dials 1 and 3) ──────────────
LASTPX = {}                                   # source -> (ts, pxusd, feed, dec_used)   [accepted prints]
TOKSRC = collections.defaultdict(set)         # called token -> its sources
class W:
    __slots__ = ("t0", "T", "tend", "ref", "first_in", "last_in", "after")
    def __init__(self, T, ref):
        self.t0 = T - RUNUP_SEC; self.T = T; self.tend = T + AFTER_SEC; self.ref = ref
        self.first_in = {}; self.last_in = {}; self.after = None
WATCH = collections.defaultdict(list)
WBY = {}

def on_watch(row, gk):
    ts, tk = row[0], row[2]
    lst = WATCH.get(tk)
    if not lst:
        return
    rec = (ts, row[12], row[1], row[13])
    keep = []
    for w in lst:
        if ts <= w.t0:
            w.ref[gk] = rec
        elif ts < w.T:
            if gk not in w.first_in:
                w.first_in[gk] = rec
            w.last_in[gk] = rec
        elif ts <= w.tend:
            if w.after is None:
                w.after = rec
        if ts <= w.tend and w.after is None:
            keep.append(w)
    if keep:
        WATCH[tk] = keep
    else:
        del WATCH[tk]

def watch_out(w):
    if w is None:
        return dict(runupLevel=None)
    d = {}
    if w.last_in:
        src = max(w.last_in, key=lambda s: (w.last_in[s][0], s))
        pc = w.last_in[src]
        if src in w.ref:
            pr, kind = w.ref[src], "before"
        else:
            pr, kind = w.first_in[src], "firstInHour"
        d.update(ruSrcFeed=pc[2], pCall=pc[1], pCallTs=pc[0], pRef=pr[1], pRefTs=pr[0], pRefKind=kind,
                 runup=(pc[1] / pr[1] - 1) if pr[1] and pc[1] else None,
                 mcapPx=pc[1], mcapPxFrom="hour", mcapFeed=pc[2], mcapDec=pc[3], mcapPxTs=pc[0])
    else:
        d.update(runup=None, ruNone=True)
        if w.after is not None:
            a = w.after
            d.update(mcapPx=a[1], mcapPxFrom="after", mcapFeed=a[2], mcapDec=a[3], mcapPxTs=a[0])
    return d

# ── the pass ───────────────────────────────────────────────────────────────
win = collections.deque()
first_seen, first_src = {}, {}
last_called = {}
smart_by_caller = collections.defaultdict(list)
study = []
ev_i = 0
EV = EVENTS
PRE = sorted((e["ts"] - RUNUP_SEC, e["id"], e["ca"], e["ts"]) for e in EVENTS if e["id"] in ROWSET)
pre_i = 0

def age_of(tk, T):
    b = birth.get(tk); f = first_seen.get(tk)
    x = min(v for v in (b, f) if v is not None) if (b is not None or f is not None) else None
    return None if x is None else max(0, T - x)

def tier_at(caller, T):
    vals = []; coins = set()
    for (ca, p) in smart_by_caller.get(caller, ()):
        if p.ets is not None and p.ets + SMART_HOLD <= T:
            vals.append(smart_val(p)); coins.add(ca)
    n = len(vals)
    if n == 0:
        return "other", None, 0, "unrated"
    css = sorted(vals, reverse=True)
    mean = sum(vals) / n
    db = sum(css[1:]) / (n - 1) if n > 1 else mean
    w = n / (n + 8.0)
    if n >= 5:
        m = 1.0
        for x in vals:
            m *= (1 + x / 100)
        geo = 100 * (max(m, 1e-12) ** (1.0 / n) - 1)
        score = round(w * max(-30, min(40, geo)), 1)
    else:
        score = round(w * max(-15, min(15, db)), 1)
    tentative = n < 5 or len(coins) < 3
    t = "elite" if (score >= 3 and not tentative) else ("good" if score >= 0 else "other")
    return t, score, n, "rated"

def process_pre(item):
    t0, eid, ca, T = item
    ref = {s: LASTPX[s] for s in TOKSRC.get(ca, ()) if s in LASTPX}
    w = W(T, ref)
    WATCH[ca].append(w); WBY[eid] = w

def process_event(e):
    T = e["ts"]; ca = e["ca"]
    if not e["mirror"] and not e["multi"]:
        p = Pos(ca, T, SMART_LAG, "M")
        active[ca].append(p)
        smart_by_caller[e["caller"]].append((ca, p))
    if e["id"] in ROWSET:
        tier, score, n_rec, rated = tier_at(e["caller"], T)
        bT = T // 600
        cnt = collections.Counter()
        for b, c in win:
            if bT - 6 <= b <= bT:
                cnt.update(c)
        a_self = cnt.get(ca, 0)
        age_self = age_of(ca, T)
        ab = band(max(1, a_self), ACT_EDGES)
        gb = band(age_self if age_self is not None else 0, AGE_EDGES)
        cands = []
        for tk, a in cnt.items():
            if tk == ca:
                continue
            lc = last_called.get(tk)
            if lc is not None and lc >= T - 86400:
                continue
            ag = age_of(tk, T)
            cands.append((tk, band(a, ACT_EDGES), band(ag if ag is not None else 0, AGE_EDGES)))
        lvl = 0
        pool = sorted(tk for tk, x, y in cands if x == ab and y == gb)
        if len(pool) < MIN_MATCH:
            lvl = 1; pool = sorted(tk for tk, x, y in cands if x == ab)
        if len(pool) < MIN_MATCH:
            lvl = 2; pool = sorted(tk for tk, x, y in cands)
        rng = random.Random("%d:%d" % (SEED, e["id"]))
        rng.shuffle(pool)
        pool = pool[:NCAND]
        rec = dict(id=e["id"], ts=T, ca=ca, caller=e["caller"], chat=e["chat"], tier=tier, score=score, nRec=n_rec,
                   rated=rated, actSelf=a_self, ageSelf=age_self, actBand=ab, ageBand=gb, matchLevel=lvl,
                   nPool=len(pool), nUniverse=len(cands), call={}, cand={}, seenBefore=ca in first_seen,
                   seenSrcBefore=first_src.get(ca))
        fpos = Pos(ca, T, 86400, "F"); active[ca].append(fpos); rec["first"] = fpos
        for d in DELAYS:
            p = Pos(ca, T + d, MAX_LAG, "S"); active[ca].append(p); rec["call"][d] = p
            lst = []
            for tk in pool:
                q = Pos(tk, T + d, MAX_LAG, "S"); active[tk].append(q); lst.append(q)
            rec["cand"][d] = lst
        study.append(rec)
    last_called[ca] = T

guards = {}
stream = heapq.merge(gen_v23(), gen_v4(), key=lambda r: r[0])
nprint = 0; cur_b = None
for row in stream:
    ts, feed, tk, px, src, usd = row[0], row[1], row[2], row[3], row[4], row[5]
    while pre_i < len(PRE) and PRE[pre_i][0] <= ts:
        process_pre(PRE[pre_i]); pre_i += 1
    while ev_i < len(EV) and EV[ev_i]["ts"] <= ts:
        process_event(EV[ev_i]); ev_i += 1
    gk = src if feed == 1 else (tk + "|" + src)
    T_ = guards.get(gk)
    if T_ is None:
        T_ = guards[gk] = G()
    if not accept(T_, px, usd):
        STAT["guard_rejected_%d" % feed] += 1
        continue
    STAT["accepted_%d" % feed] += 1
    if feed == 1:
        poolstate[row[10]] = (ts, px, row[7], row[9], row[8], usd)
        tokpools[tk].add(row[10])
    if tk in CALLED:
        LASTPX[gk] = (ts, row[12], feed, row[13]); TOKSRC[tk].add(gk)
        on_watch(row, gk)
    if usd >= ACT_USD:
        b = int(ts) // 600
        if b != cur_b:
            win.append((b, collections.Counter())); cur_b = b
            while win and win[0][0] < b - 7:
                win.popleft()
        win[-1][1][tk] += 1
    if tk not in first_seen:
        first_seen[tk] = ts; first_src[tk] = "v4" if feed == 1 else "v23"
    on_print(row)
    nprint += 1
    if nprint % 5000000 == 0:
        log("prints", nprint, time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts)), "events", ev_i, "activeToks",
            len(active), "guards", len(guards), dict(STAT))
while pre_i < len(PRE):
    process_pre(PRE[pre_i]); pre_i += 1
while ev_i < len(EV):
    process_event(EV[ev_i]); ev_i += 1
log("stream done", nprint, dict(STAT))

# ── emit ───────────────────────────────────────────────────────────────────
def posdict(p):
    if p.ets is None:
        return dict(fill=False)
    return dict(fill=True, tok=p.tok, lag=p.fill_lag, v4=p.v4, src=p.src, ets=p.ets, epx=p.epx, eusd=p.eusd,
                eD=None if p.eD is None else round(p.eD, 6), efee=p.efee, eL=p.eL,
                drained=bool(p.v4 and p.eL and p.Lmin is not None and p.Lmin <= 0.05 * p.eL),
                hiIgn=p.nhi_ign, hiOk=p.nhi_ok, rug=p.rug is not None,
                h=[book(p, i) for i in range(NH)],
                tp=[p.tp_ts is not None and p.tp_ts <= p.ets + H for H in HOLDS])

out = open(os.path.join(HERE, "rows%s.ndjson" % OUT_SUFFIX), "w")
dout = open(os.path.join(HERE, "dials%s.ndjson" % OUT_SUFFIX), "w")
for rec in study:
    base = {k: rec[k] for k in ("id", "ts", "ca", "caller", "chat", "tier", "score", "nRec", "rated", "actSelf", "ageSelf",
                                "actBand", "ageBand", "matchLevel", "nPool", "nUniverse", "seenBefore", "seenSrcBefore")}
    fp = rec["first"]
    base["firstPrintLag"] = fp.fill_lag
    base["firstPrintSrc"] = None if fp.src is None else ("v23" if fp.src.startswith("t:") else "v4")
    base["everSeen"] = rec["ca"] in first_seen
    base["inV4Meta"] = rec["ca"] in tokpools
    base["birthKnown"] = rec["ca"] in birth
    dd = dict(base); dd.update(watch_out(WBY.get(rec["id"])))
    dout.write(json.dumps(dd) + "\n")
    row = dict(base)
    for d in DELAYS:
        x = posdict(rec["call"][d])
        tw = []
        for q in rec["cand"][d]:
            if q.ets is None:
                continue
            tw.append(posdict(q))
            if len(tw) >= K_TWIN:
                break
        x["twins"] = tw
        row["d%d" % d] = x
    out.write(json.dumps(row) + "\n")
out.close(); dout.close()
meta = dict(stat=dict(STAT), prints=nprint, dataEnd=DATA_END, lastDay=LAST_DAY, v23Files=len(tape_files()),
            bfDays=[BF_DAYS[0], BF_DAYS[-1], len(BF_DAYS)] if BF_DAYS else None, bfEndTs=BF_END_TS,
            studyRows=len(study), sec=round(time.time() - T0),
            maxRssMB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
            params=dict(DELAYS=DELAYS, HOLDS=HOLDS, TP=TP, MAX_LAG=MAX_LAG, MIN_USD_V23=MIN_USD_V23, MIN_USD_V4=MIN_USD_V4,
                        CLIP_USD=CLIP_USD, GAS=GAS, FEE_V23=FEE_V23, HI_X=HI_X, RUG_X=RUG_X, CORR_SEC=CORR_SEC,
                        NCAND=NCAND, K_TWIN=K_TWIN, SEED=SEED, RUNUP_SEC=RUNUP_SEC, AFTER_SEC=AFTER_SEC))
json.dump(meta, open(os.path.join(HERE, "engine_meta%s.json" % OUT_SUFFIX), "w"), indent=1)
log("done", meta)
