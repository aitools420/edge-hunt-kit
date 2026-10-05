#!/usr/bin/env python3
"""CALLERS FAST ENTRIES (2026-10-02, Chef TG 15728 + coordinator batch 2, TG 15735) — runs the dial test's engine.py (copied here
byte-identical from callers-fill1 pass B, sha256 311370c9…) with constant lines replaced, exactly as pass B's engine_fill.py does,
PLUS the minimum needed to book several take-profits in ONE stream pass (each (delay, take-profit) pair gets its own positions;
nothing else in the decision logic changes). Every replacement is asserted to occur exactly once.
  DELAYS (60,)          -> FAST_DELAYS (default 5,15,30,60)
  HOLDS  (6 holds)      -> 14 holds: 75,150,300,450,900,3600,14400,43200,86400,259200,432000,604800,777600,950400
  TP 1.50               -> per-position p.TP; FAST_TPS (e.g. 1.5,1.25,2.0 | inf,2.5,3.0)
  BF_DAYS               -> cut at 2026-09-11 (pass B's Amendment 1)
  DATA_END              -> pass B's Amendment 2 fix (a tagged full run keeps DATA_END 21:40:49)
  posdict / book        -> ALSO write clip (ETH), eDx, mDx unrounded (outputs only; the real-cost re-coster needs them)
  output                -> rows_fast<_smoke>_<FAST_TAG>.ndjson, keys d<delay>_<tp tag>
FAST_MUTANT=A|B (mutation test only): A = every call position starts at call+60 s whatever its delay; B = fills accepted 10 s early.
SEALED: the engine refuses LAST_DAY >= 2026-09-27, never opens tape-2026-09-27, and raises on any row ts >= 1790467200.
Usage: FAST_TPS=1.5,1.25,2.0 FAST_TAG=r1 engine_fast.py [LAST_DAY]"""
import hashlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "engine.py")
body = open(SRC).read()
assert hashlib.sha256(body.encode()).hexdigest() == "311370c9fbaf3fc4c5b3f0be5f628d98cc76d94ec670f46f425d94c11b91b950", "engine.py changed"
TPS = [float(x) for x in os.environ.get("FAST_TPS", "1.5,1.25,2.0").split(",")]
DEL = os.environ.get("FAST_DELAYS", "5,15,30,60")
TAG = os.environ.get("FAST_TAG", "r1")
HOL = "75,150,300,450,900,3600,14400,43200,86400,259200,432000,604800,777600,950400"
MUT = os.environ.get("FAST_MUTANT", "")
def tptag(v):
    return "none" if v == float("inf") else str(int(round((v - 1) * 100)))
REPL = [
    ("DELAYS = (60,)\n", "DELAYS = (%s,)\n" % DEL),
    ("HOLDS = (900, 3600, 14400, 43200, 86400, 259200)\n", "HOLDS = (%s,)\n" % HOL),
    ("TP = 1.50\n", "TP = None\nTPS_ = (%s,)\nTPTAG_ = %r\n" % (", ".join("float('inf')" if v == float("inf") else repr(v) for v in TPS),
                                                              {repr(v): tptag(v) for v in TPS})),
    ("BF_DAYS = _bf_days()\n", "BF_DAYS = [d for d in _bf_days() if d <= '2026-09-11']\n"),
    ("if OUT_SUFFIX:\n    DATA_END = ", "if LAST_DAY != \"2026-09-26\":\n    DATA_END = "),
    ('OUT_SUFFIX = "" if LAST_DAY == "2026-09-26" else "_smoke"\n',
     'OUT_SUFFIX = ("" if LAST_DAY == "2026-09-26" else "_smoke") + %r\n' % ("_" + TAG + (("_mut" + MUT) if MUT else ""))),
    ('"fill_lag", "done", "lastM")\n', '"fill_lag", "done", "lastM", "TP")\n'),
    ("self.fill_lag = None; self.done = False; self.lastM = None\n", "self.fill_lag = None; self.done = False; self.lastM = None; self.TP = None\n"),
    ("if dt_ <= HMAX and px >= TP * p.epx:", "if dt_ <= HMAX and px >= p.TP * p.epx:"),
    ("""        for d in DELAYS:
            p = Pos(ca, T + d, MAX_LAG, "S"); active[ca].append(p); rec["call"][d] = p
            lst = []
            for tk in pool:
                q = Pos(tk, T + d, MAX_LAG, "S"); active[tk].append(q); lst.append(q)
            rec["cand"][d] = lst
""", """        for d in DELAYS:
          for tpv in TPS_:
            p = Pos(ca, T + d, MAX_LAG, "S"); p.TP = tpv; active[ca].append(p); rec["call"][(d, tpv)] = p
            lst = []
            for tk in pool:
                q = Pos(tk, T + d, MAX_LAG, "S"); q.TP = tpv; active[tk].append(q); lst.append(q)
            rec["cand"][(d, tpv)] = lst
"""),
    ("""    for d in DELAYS:
        x = posdict(rec["call"][d])
        tw = []
        for q in rec["cand"][d]:""", """    for (d, tpv) in [(d, t) for d in DELAYS for t in TPS_]:
        x = posdict(rec["call"][(d, tpv)])
        tw = []
        for q in rec["cand"][(d, tpv)]:"""),
    ('        row["d%d" % d] = x\n', '        row["d%d_%s" % (d, TPTAG_[repr(tpv)])] = x\n'),
    ("return dict(fill=True, tok=p.tok, lag=p.fill_lag,", "return dict(fill=True, clip=p.clip, eDx=p.eD, tok=p.tok, lag=p.fill_lag,"),
    ("mD=None if m[2] is None else round(m[2], 6), mfee=m[3])", "mD=None if m[2] is None else round(m[2], 6), mfee=m[3], mDx=m[2])"),
    ("params=dict(DELAYS=DELAYS, HOLDS=HOLDS, TP=TP,", "params=dict(DELAYS=DELAYS, HOLDS=HOLDS, TP=[repr(v) for v in TPS_],"),
    ('out = open(os.path.join(HERE, "rows%s.ndjson" % OUT_SUFFIX), "w")', 'out = open(os.path.join(HERE, "rows_fast%s.ndjson" % OUT_SUFFIX), "w")'),
    ('dout = open(os.path.join(HERE, "dials%s.ndjson" % OUT_SUFFIX), "w")', 'dout = open(os.path.join(HERE, "dials_fast%s.ndjson" % OUT_SUFFIX), "w")'),
    ('json.dump(meta, open(os.path.join(HERE, "engine_meta%s.json" % OUT_SUFFIX), "w"), indent=1)',
     'json.dump(meta, open(os.path.join(HERE, "engine_meta_fast%s.json" % OUT_SUFFIX), "w"), indent=1)'),
]
if MUT == "A":
    REPL.append(('p = Pos(ca, T + d, MAX_LAG, "S"); p.TP = tpv;', 'p = Pos(ca, T + 60, MAX_LAG, "S"); p.TP = tpv;'))
elif MUT == "B":
    REPL.append(("            if ts < p.start:\n                keep.append(p); continue\n",
                 "            if ts < p.start - 10:\n                keep.append(p); continue\n"))
elif MUT:
    raise SystemExit("unknown mutant")
# ── KIT PATH EDITS (callers kit 2026-10-05): engine.py stays byte-identical; its six machine paths are replaced in the exec'd text ──
REPL += [
    ('sys.path.insert(0, "/home/green/projects/patches/v4-join-2026-09-27")\n', 'sys.path.insert(0, HERE)\n'),
    ('WLOGS = "/home/green/.openclaw/workspace/wick-engine/logs"\n', 'WLOGS = os.environ["CALLERS_TAPE_ROOT"]\n'),
    ('TAPE_DIR = os.path.join(WLOGS, "robinhood-tape")\n', 'TAPE_DIR = os.environ["CALLERS_TAPE_LIVE"]\n'),
    ('V4_BIRTHS = os.path.join(WLOGS, "robinhood-v4-births.ndjson")\n', 'V4_BIRTHS = os.environ["CALLERS_BIRTHS"]\n'),
    ('TOK_BIRTHS = os.path.join(WLOGS, "robinhood-token-births.json")\n', 'TOK_BIRTHS = os.environ["CALLERS_TOK_BIRTHS"]\n'),
    ('BF_DIR = "/home/green/projects/patches/v4-backfill-join-2026-09-29/out"\n', 'BF_DIR = os.environ["CALLERS_BF_DIR"]\n'),
]
for a, b in REPL:
    assert body.count(a) == 1, a
    body = body.replace(a, b)
g = {"__name__": "__main__", "__file__": SRC}
exec(compile(body, SRC + " [fast settings %s %s]" % (TAG, MUT), "exec"), g)
