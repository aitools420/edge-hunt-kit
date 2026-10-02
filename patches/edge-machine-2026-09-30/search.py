#!/usr/bin/env python3
"""search.py - EDGE MACHINE X step (DESIGN.md "X search = a fitted surface with uncertainty"): Bayesian optimisation over the Blood surface.
READ-ONLY outside its output dir. Reads no tape and no engine output: only the explorer's data.json (or the machine's merged view), the
screen's points.json / families.json, and must_test.json. Picks <= 20 engine-v1 cells; runs nothing.

  python3 search.py --round N [--out DIR] [--family-mode rep|weight]   fit + pick -> DIR/{cells.json, why.json, fit.json}
  python3 search.py snapshot --out FILE                               compact copy of the screen's verdicts (for round-to-round compare)
  python3 search.py summarize --round-dir DIR [--prev-dir DIR] [--dry] [--ran K]   -> DIR/summary.json + the ONE plain-English line

THE FIT.  Every real-cost measured point that screen.py RECOVERED (its trades are in the store), minus post-hoc views (R-0113 class) and
R-0115 un-hop-costed cells (mis-costed). ONE POINT PER A5 FAMILY (default --family-mode rep): the family's highest-ranked eligible member in
the screen's own order, so re-cuts of one trade set enter once. Its noise sd = half its COIN-CLUSTERED 95 % range / 1.96 (screen A1).
  --family-mode weight (option, not default): every eligible member enters, each with its noise variance x the family size, so a family
  still carries about one point of confidence but its exit-dial shape (TP / hold / delay re-cuts of the same entries) is kept.
Prior mean = beta0 + beta1 x the explorer's own formula (its barrier model, at REAL cost, ported from build.py's evalSide and checked
against the page's JS in test_search.py) if that raises the marginal likelihood with beta1 > 0, else a constant. Learned correction = a
Gaussian process, squared-exponential, ONE length-scale per dial (ARD): numeric dials on [0,1] over their level range (log where the dial
is log-spaced), categorical dials by an indicator distance (1 if different). Plus a learned between-test jitter (different tests, windows,
cost details). Hyper-parameters by maximum marginal likelihood (Adam, 3 restarts) with a weak log-normal prior on each length-scale.
⛔ The GP's sd understates the truth: every point read the same ~5-9 spent days. A peak is a CANDIDATE for V / D, never evidence.

THE PICK.  Candidates = the Blood moves in must_test.json that engine v1 can express (rule 0 sweeps and corners, rule 1 slices, rule 3b
extensions; rule 4 'between' levels are not on the explorer grid and rule 5 is an audit, not a backtest) + every one-dial-step neighbour
of the best surviving families (representative passes S1 and A1, top 10 by coin-clustered lower bar). Dropped: any cell with a dial
level engine v1 cannot express, any cell already measured at real cost (any test), any cell already run by the machine (the v1 ledger),
and any cell using a level that WAS measured at real cost but never reached N_FLOOR = 30 trades in any cell (it cannot reach S1's n;
today: volume $10M+/day, max n 5; dip 50 %, max n 19). The predicted best is taken over the same feasible, expressible set.
Acquisition = UCB = mean + KAPPA x sd, KAPPA = 2.0. Batch <= 20 in SLOTS (CONFIG QUOTA, Chef's loop = skeleton first): 5 = the best-UCB
rule-0 skeleton moves (sweeps / corners), 3 = the best-UCB rule-1 slices (a model point above the best measured), 12 = by acquisition from
any legal candidate (a slot a pool cannot fill passes to acquisition). Diversity, three layers: (1) kriging believer - after each pick the
GP takes the picked cell as observed at its own predicted mean, so its neighbours' sd and UCB shrink before the next pick; (2) at most
MAX_PER_POINT = 4 acquisition picks within one dial step of the same measured fit point - a higher-UCB cell refused by that cap is listed
as DISPLACED on the pick taken instead (why.json); (3) hard rule - no two picks within one dial step (explorer stepDist <= 1) UNLESS the
near-duplicate's UCB beats the best diverse alternative by more than GAP_SD = 1 x its own sd (then it is taken and the exception is written in why.json)."""
import json, os, sys, re, math, collections, subprocess, tempfile, datetime, random, glob
for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):   # a shared research box: never fan BLAS out over every core
    os.environ.setdefault(_v, '2')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.environ['KIT_ROOT'] + '/patches'
sys.path.insert(0, HERE)
import loader_v1 as L1
MACHINE = L1.MACHINE
CONFIG = dict(KAPPA=2.0, MAX_CELLS=20, PASS_SIZE=20, GAP_SD=1.0, FAMILY_MODE='rep', SURVIVE=('S1', 'A1'), N_SURVIVE=10,
              NOISE_FLOOR=0.5, LS_PRIOR_MU=0.0, LS_PRIOR_SD=1.5, LS_BOUNDS=(0.03, 30.0), ITERS=400, LR=0.05, RESTARTS=(0.3, 1.0, 3.0),
              SEED=12345, BEST_MOVE_PTS=2.0, N_FLOOR=30,
              # slots per round, filled in this order (coordinator 2026-09-30, Chef's loop = skeleton first): the best-UCB rule-0 skeleton moves
              # (sweeps / corners), then the best-UCB rule-1 slices, then the rest by acquisition from ANY legal candidate. A slot a pool cannot
              # fill passes on to acquisition. Sum must equal MAX_CELLS.
              QUOTA=(('skeleton', 5), ('slice', 3), ('acquisition', 12)),
              MAX_PER_POINT=4)   # at most this many ACQUISITION picks within one dial step of the same measured (fit) point
LOGD = {'age', 'hold', 'delay', 'win'}          # log-spaced numeric dials; vol: log10(max(v, 100)); tp: log(1 + v/100)

# ============================================================== data
def load_S():
    mv = MACHINE + '/data_merged.json'
    S, _ = L1.blood(mv if os.path.exists(mv) else None); return S
def _erf(x):                                    # the PAGE's erf (Abramowitz-Stegun 7.1.26), so the prior is the explorer's number exactly
    s = -1 if x < 0 else 1; x = abs(x); t = 1 / (1 + 0.3275911 * x)
    return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x))
def phi(x): return 0.5 * (1 + _erf(x / math.sqrt(2)))
MULT = {'hit', 'die', 'sig', 'fee', 'il'}
def formula(S, lv, basis='real'):
    """= build.py's model(S, st0, lv, 'raw', basis).E for a barrier strategy (evalSide, side 's'); dials with no effect entry add nothing"""
    V, I = S['vars'], S['inputs']; A = collections.defaultdict(float); A.update(hit=1.0, die=1.0, sig=1.0, fee=1.0, il=1.0)
    for i, var in enumerate(V):
        l = lv[i]
        if l == var['held']: continue
        eff = var['eff'][l] if l < len(var['eff']) else None
        if eff is None: continue
        for f, e in eff.items():
            m = re.fullmatch(r'(.*)_(s|t)', f); fld = f
            if m:
                fld = m.group(1)
                if m.group(2) != 's': continue
            elif (f + '_s') in eff: continue
            if fld in MULT: A[fld] *= e[0]
            else: A[fld] += e[0]
    lvl = lambda vid: V[[v['id'] for v in V].index(vid)]['levels'][lv[[v['id'] for v in V].index(vid)]]['v']
    TP, H, refH = lvl('tp'), lvl('hold'), S['refH']
    cid = 'cost_real' if basis == 'real' and 'cost_real' in I else ('cost_heavy' if basis == 'heavy' and 'cost_heavy' in I else 'cost')
    sigma = I['sigma']['v'] * A['sig']; a = math.log(1 + TP / 100)
    Pb = 2 * (1 - phi(a / (sigma * math.sqrt(H))))
    Pdie = min(0.9, max(0.0, I['die']['v'] * (H / refH) * A['die']))
    Ptp = max(0.0, min(0.99 - Pdie, Pb * A['hit'])); Pn = 1 - Ptp - Pdie
    eg = I['edge']['v'] * (H / refH) ** I['k']['v']; cst = I[cid]['v'] + A['cost']
    return Pn * eg - cst + A['shift']

def dial_kinds(V):
    return ['num' if all(isinstance(L.get('v'), (int, float)) for L in v['levels']) else 'cat' for v in V]
def feats(V, lvs):
    kinds = dial_kinds(V); lvs = np.asarray(lvs); X = np.zeros(lvs.shape, float)
    for j, (v, k) in enumerate(zip(V, kinds)):
        if k == 'cat': X[:, j] = lvs[:, j]; continue
        vals = np.array([L['v'] for L in v['levels']], float)
        if v['id'] == 'vol': t = np.log10(np.maximum(vals, 100.0))
        elif v['id'] == 'tp': t = np.log1p(vals / 100)
        elif v['id'] in LOGD: t = np.log(np.maximum(vals, 1e-6))
        else: t = vals
        t = (t - t.min()) / ((t.max() - t.min()) or 1.0); X[:, j] = t[lvs[:, j]]
    return X, kinds
def dist_stack(X1, X2, kinds, dims):
    return np.stack([(X1[:, None, j] != X2[None, :, j]).astype(float) if kinds[j] == 'cat' else (X1[:, None, j] - X2[None, :, j]) ** 2 for j in dims])

# ============================================================== GP (numpy only: scikit-learn / scipy are not installed on this box)
class GP:
    def __init__(self, X, y, s2, H, kinds, cfg):
        self.X, self.y, self.s2, self.H, self.kinds, self.cfg = X, y, s2, H, kinds, cfg
        self.dims = [j for j in range(X.shape[1]) if len(np.unique(X[:, j])) > 1]     # a dial with no variation cannot be learned
        self.D = dist_stack(X, X, kinds, self.dims)
    def lml(self, th, grad=True):
        c = self.cfg; nd = len(self.dims); ls = np.exp(th[:nd]); sf2 = np.exp(2 * th[nd]); sj2 = np.exp(2 * th[nd + 1])
        Kf = sf2 * np.exp(-0.5 * np.tensordot(1 / ls ** 2, self.D, 1)); n = len(self.y)
        K = Kf + np.diag(self.s2 + sj2)
        Lc = np.linalg.cholesky(K); Li = np.linalg.inv(Lc); Ki = Li.T @ Li
        KH = Ki @ self.H; A = self.H.T @ KH; beta = np.linalg.solve(A, KH.T @ self.y)
        r = self.y - self.H @ beta; al = Ki @ r
        pri = -0.5 * np.sum(((th[:nd] - c['LS_PRIOR_MU']) / c['LS_PRIOR_SD']) ** 2)
        val = -0.5 * r @ al - np.log(np.diag(Lc)).sum() - 0.5 * n * math.log(2 * math.pi)
        self.state = dict(ls=ls, sf2=sf2, sj2=sj2, Ki=Ki, al=al, beta=beta, Ainv=np.linalg.inv(A), lml=val)
        if not grad: return val + pri
        W = np.outer(al, al) - Ki; g = np.zeros_like(th)
        WK = W * Kf
        g[:nd] = 0.5 * np.einsum('dij,ij->d', self.D, WK) / ls ** 2          # dK/dlog(ls_j) = Kf * D_j / ls_j^2
        g[:nd] += -(th[:nd] - c['LS_PRIOR_MU']) / c['LS_PRIOR_SD'] ** 2
        g[nd] = WK.sum(); g[nd + 1] = sj2 * np.trace(W)
        return val + pri, g
    def fit(self):
        c = self.cfg; nd = len(self.dims); sd = float(np.std(self.y)) or 1.0; best = None
        lo, hi = np.log(c['LS_BOUNDS'][0]), np.log(c['LS_BOUNDS'][1])
        for l0 in c['RESTARTS']:
            th = np.concatenate([np.full(nd, math.log(l0)), [math.log(sd), math.log(0.5 * sd)]])
            m = np.zeros_like(th); v = np.zeros_like(th)
            for t in range(1, c['ITERS'] + 1):
                try: f, g = self.lml(th)
                except np.linalg.LinAlgError: break
                m = 0.9 * m + 0.1 * g; v = 0.999 * v + 0.001 * g * g
                th = th + c['LR'] * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8)
                th[:nd] = np.clip(th[:nd], lo, hi); th[nd + 1] = max(th[nd + 1], math.log(1e-3))
            f = self.lml(th, grad=False)
            if best is None or f > best[0]: best = (f, th.copy())
        self.obj, self.th = best; self.lml(self.th, grad=False); return self
    def believe(self, Xa, Ha, ya, s2a):
        """kriging believer: the same fitted GP (hyper-parameters fixed) with pseudo-observations at their own predicted means added"""
        g = GP.__new__(GP); g.__dict__.update(self.__dict__)
        g.X = np.vstack([self.X, Xa]); g.H = np.vstack([self.H, Ha]); g.y = np.concatenate([self.y, ya]); g.s2 = np.concatenate([self.s2, s2a])
        g.D = dist_stack(g.X, g.X, g.kinds, g.dims); g.lml(self.th, grad=False); return g
    def predict(self, Xs, Hs, chunk=4000):
        s = self.state; mu, var = [], []
        for a in range(0, len(Xs), chunk):
            Ds = dist_stack(Xs[a:a + chunk], self.X, self.kinds, self.dims)
            ks = s['sf2'] * np.exp(-0.5 * np.tensordot(1 / s['ls'] ** 2, Ds, 1)); h = Hs[a:a + chunk]
            kK = ks @ s['Ki']; R = h - kK @ self.H
            mu.append(h @ s['beta'] + ks @ s['al'])
            var.append(s['sf2'] - np.sum(kK * ks, 1) + np.sum((R @ s['Ainv']) * R, 1))
        return np.concatenate(mu), np.sqrt(np.maximum(np.concatenate(var), 0))

# ============================================================== training set, candidates
def training(S, cfg):
    PT = {p['pk']: p for p in json.load(open(HERE + '/points.json'))['points']}
    FA = json.load(open(HERE + '/families.json'))['families']
    def ok(p): return (p and p['recovered'] and p['cost'] == 'real' and not p['posthoc'] and not p['r0115'] and p.get('A1')
                       and p['mean'] is not None and p['A1'].get('coin_boot_ci'))
    rows = []
    for f in FA:
        mem = [PT[k] for k in f['members'] if ok(PT.get(k))]
        if not mem: continue
        use = mem[:1] if cfg['FAMILY_MODE'] == 'rep' else mem
        for p in use:
            lo, hi = p['A1']['coin_boot_ci']; s = max((hi - lo) / 3.92, cfg['NOISE_FLOOR'])
            rows.append(dict(pk=p['pk'], lv=[int(x) for x in p['pk'].split('|')[0].split(',')], y=p['mean'], s2=s * s * (len(mem) if cfg['FAMILY_MODE'] == 'weight' else 1),
                             family=f['family'], test=p['test'], n=p['n']))
    return rows, PT, FA
def lab(V, i, l): return V[i]['levels'][l]['label']
def thin_levels(S, cfg):
    """feasibility: a dial level that WAS measured at real cost but never reached N_FLOOR trades in any cell cannot give an S1-eligible cell
    (a filter only removes trades; exits add no entries) - e.g. volume $10M+/day: at most 5 trades in any measured cell. -> {(i, l): max n}"""
    V = S['vars']; maxn = collections.defaultdict(int)
    for m in S['measured']:
        if m.get('cost') != 'real': continue
        for i, l in enumerate(m['lv']):
            if l != V[i]['held']: maxn[(i, l)] = max(maxn[(i, l)], m['n'])
    return {k: n for k, n in maxn.items() if n < cfg['N_FLOOR']}
def where(V, lv): return {V[i]['name']: lab(V, i, l) for i, l in enumerate(lv) if l != V[i]['held']}
def step_dist(V, a, b, kinds):
    return sum((abs(x - y) if k == 'num' else 1) for x, y, k in zip(a, b, kinds) if x != y)
def candidates(S, PT, FA, cfg, measured, ledger):
    V = S['vars']; held = [v['held'] for v in V]; kinds = dial_kinds(V)
    name2i = {v['name']: i for i, v in enumerate(V)}; labs = [[L['label'] for L in v['levels']] for v in V]
    C = collections.OrderedDict(); src_count = collections.Counter(); skipped = collections.Counter(); not_grid = []
    def put(lv, why, src):
        C.setdefault(tuple(lv), []).append(why); src_count[src] += 1
    def w(i, l): x = list(held); x[i] = l; return x
    MT = json.load(open(P + '/edge-explorer/must_test.json'))
    for it in MT['items']:
        if it.get('strategy') != 'Blood': continue
        k, rule = it['kind'], str(it['rule']); tag = f"must-test rule {rule} {k}: {it['x']}" + (f" × {it['y']}" if it.get('y') else '')
        if k == 'sweep':
            i = name2i[it['x']]
            for s in it['fill']: put(w(i, labs[i].index(s)), tag, f'rule {rule} {k}')
        elif k == 'corners':
            i, j = name2i[it['x']], name2i[it['y']]
            for s in it['fill']:
                s = s[1:-1]; hit = [(a, b) for a in labs[i] for b in labs[j] if s == f'{a}, {b}']
                if len(hit) != 1: skipped['unparsed corner'] += 1; continue
                x = w(i, labs[i].index(hit[0][0])); x[j] = labs[j].index(hit[0][1]); put(x, tag, f'rule {rule} {k}')
        elif k == 'slice':
            i, j = name2i[it['x']], name2i[it['y']]
            for a, La in enumerate(V[i]['levels']):
                for b, Lb in enumerate(V[j]['levels']):
                    if La.get('proposed') or Lb.get('proposed'): continue
                    x = w(i, a); x[j] = b; put(x, tag + f" (gap {it.get('gap')})", f'rule {rule} {k}')
        elif k == 'extend':
            i = name2i[it['x']]
            for s in it['proposed']: put(w(i, labs[i].index(s)), tag, f'rule {rule} {k}')
        elif k == 'peak': not_grid.append(dict(request=it['request'], why="'between' levels are not on the explorer's level grid, so no measured record could place there"))
        elif k == 'audit': skipped['rule 5 audit (not a backtest)'] += 1
    # neighbours of the best surviving families
    surv = []
    for f in FA:
        p = PT.get(f['representative'])
        if p and p['S1']['pass_'] and (p.get('A1') or {}).get('pass_'): surv.append((p['A1']['coin_boot_lower'], f['family'], p))
    surv.sort(key=lambda x: -x[0])
    for lower, fid, p in surv[:cfg['N_SURVIVE']]:
        lv0 = [int(x) for x in p['pk'].split('|')[0].split(',')]
        for i, v in enumerate(V):
            opts = [lv0[i] - 1, lv0[i] + 1] if kinds[i] == 'num' else [l for l in range(len(v['levels'])) if l != lv0[i]]
            for l in opts:
                if 0 <= l < len(v['levels']):
                    x = list(lv0); x[i] = l; put(x, f"neighbour of surviving family {fid} (coin-clustered lower {lower:+.2f}; {p['test'][:40]})", 'surviving-family neighbour')
    thin = thin_levels(S, cfg); out = []
    dup = {(i, l) for i, v in enumerate(V) for l, L_ in enumerate(v['levels']) if L_['label'] in [x['label'] for x in v['levels'][:l]]}
    for lv, why in C.items():
        if any((i, l) in dup for i, l in enumerate(lv)): skipped['uses a repeated level label (an explorer proposal artefact; its first copy is the level)'] += 1; continue
        if not L1.expressible(V, list(lv)): skipped['a dial level engine v1 cannot express'] += 1; continue
        th_ = [f"{V[i]['id']}={lab(V, i, l)} (max n {thin[(i, l)]})" for i, l in enumerate(lv) if (i, l) in thin]
        if th_: skipped[f"uses a level never measured at n >= {cfg['N_FLOOR']}: " + ', '.join(th_)] += 1; continue
        if lv in measured: skipped['already measured at real cost'] += 1; continue
        if lv in ledger: skipped['already run by the machine'] += 1; continue
        out.append(dict(lv=list(lv), serves=sorted(set(why))))
    return out, dict(sources=dict(src_count), skipped=dict(skipped), surviving_families=[dict(family=f, coin_boot_lower=lo, pk=p['pk']) for lo, f, p in surv[:cfg['N_SURVIVE']]],
                     not_on_grid=not_grid)

def pick(cands, g, Xc, Hc, cfg, V, fit_lv):
    """greedy UCB batch in slots (cfg QUOTA): skeleton = candidates serving must-test rule 0 (sweeps / corners), slice = rule 1 slices,
    acquisition = any legal candidate. Within every slot: kriging believer (each pick is fed back as observed at its own predicted mean, noise =
    the median fit-point noise, so its neighbours' sd and UCB shrink before the next pick) + the one-step rule (a cell within one dial step of
    an already-picked cell is taken only if its UCB beats the best diverse cell by more than GAP_SD x its own sd). Acquisition slot only: at most
    MAX_PER_POINT picks within one dial step of the same measured fit point; a higher-UCB cell refused by that cap is recorded as DISPLACED on
    the pick taken instead. -> [(k, note, ucb_at_pick, slot, displaced)], mu, sd (the pre-batch prediction)"""
    kinds = dial_kinds(V); k0 = cfg['KAPPA']; s2b = float(np.median(g.s2))
    A = np.array([c['lv'] for c in cands]); F = np.array(fit_lv); num = np.array([k == 'num' for k in kinds])
    dd = np.where(num, np.abs(A[:, None, :] - F[None, :, :]), (A[:, None, :] != F[None, :, :])).sum(2)
    near_pts = [set(np.nonzero(dd[k] <= 1)[0].tolist()) for k in range(len(cands))]
    pools = dict(skeleton={k for k, c in enumerate(cands) if any(x.startswith('must-test rule 0 ') for x in c['serves'])},
                 slice={k for k, c in enumerate(cands) if any(x.startswith('must-test rule 1 ') for x in c['serves'])},
                 acquisition=set(range(len(cands))))
    assert sum(n for _, n in cfg['QUOTA']) == cfg['MAX_CELLS']
    mu, sd = g.predict(Xc, Hc); cur = g; left = set(range(len(cands))); chosen = []; m1, s1 = mu, sd
    cnt = collections.Counter(); shown = set(); carry = 0
    for slot, quota in cfg['QUOTA']:
        n = quota + (carry if slot == 'acquisition' else 0); got = 0
        while got < n and (pools[slot] & left):
            ucb = m1 + k0 * s1
            order = sorted(pools[slot] & left, key=lambda k: -ucb[k]); displaced = []
            if slot == 'acquisition':
                ok = [k for k in order if all(cnt[P] < cfg['MAX_PER_POINT'] for P in near_pts[k])]
                if not ok: break
                for k in order:
                    if k == ok[0]: break
                    if k not in shown:
                        full = [P for P in near_pts[k] if cnt[P] >= cfg['MAX_PER_POINT']]
                        displaced.append(dict(id=L1.cell_id(L1.cell_params(V, cands[k]['lv'])), ucb=round(float(ucb[k]), 2), where=where(V, cands[k]['lv']),
                                              why=f"would be pick {cfg['MAX_PER_POINT'] + 1} within one dial step of measured point " + '; '.join(
                                                  ', '.join(f'{a} {b}' for a, b in where(V, fit_lv[P]).items()) for P in full[:2])))
                        shown.add(k)
                order = ok
            near = lambda k: any(step_dist(V, cands[k]['lv'], cands[c[0]]['lv'], kinds) <= 1 for c in chosen)
            best = order[0]; div = next((k for k in order if not near(k)), None); note = None
            if div is None: take = best; note = 'no diverse cell left in this slot'
            elif div == best: take = best
            elif ucb[best] - ucb[div] > cfg['GAP_SD'] * s1[best]:
                take = best; note = f'within one dial step of a picked cell, taken because its UCB beats the best diverse cell by {ucb[best] - ucb[div]:.2f} > {cfg["GAP_SD"]} sd ({s1[best]:.2f})'
            else: take = div
            if slot == 'acquisition':
                for P in near_pts[take]: cnt[P] += 1
            chosen.append((take, note, float(ucb[take]), slot, displaced)); left.discard(take); got += 1
            cur = cur.believe(Xc[[take]], Hc[[take]], np.array([m1[take]]), np.array([s2b]))
            m1, s1 = cur.predict(Xc, Hc)
        carry += n - got if slot != 'acquisition' else 0
    return chosen, mu, sd

# ============================================================== main search
def run_search(rnd, out, cfg):
    S = load_S(); V = S['vars']; kinds = dial_kinds(V)
    rows, PT, FA = training(S, cfg)
    X, _ = feats(V, [r['lv'] for r in rows]); y = np.array([r['y'] for r in rows]); s2 = np.array([r['s2'] for r in rows])
    fx = np.array([formula(S, r['lv']) for r in rows])
    fits = {}
    for name, H in (('constant', np.ones((len(y), 1))), ('formula', np.column_stack([np.ones(len(y)), fx]))):
        g = GP(X, y, s2, H, kinds, cfg).fit(); fits[name] = g
    use = 'formula' if fits['formula'].state['lml'] > fits['constant'].state['lml'] and fits['formula'].state['beta'][1] > 0 else 'constant'
    g = fits[use]
    measured = {tuple(m['lv']) for m in S['measured'] if m.get('cost') == 'real'}
    ledger = set()
    for b in L1._ledger()['batches']:
        for cid, rec in json.load(open(b['dir'] + '/results.json'))['cells'].items():
            try: ledger.add(tuple(L1.lv_of_dials(V, rec['dials'])))
            except L1.NotExpressible: pass
    cands, cinfo = candidates(S, PT, FA, cfg, measured, ledger)
    if not cands: raise SystemExit('no legal candidate cell')
    Xc, _ = feats(V, [c['lv'] for c in cands]); fc = np.array([formula(S, c['lv']) for c in cands])
    Hc = np.ones((len(cands), 1)) if use == 'constant' else np.column_stack([np.ones(len(cands)), fc])
    chosen, mu, sd = pick(cands, g, Xc, Hc, cfg, V, [r['lv'] for r in rows]); ucb = mu + cfg['KAPPA'] * sd
    if cfg.get('ARM') == 'random':   # HUNTER v0 baseline arm (Chef TG 15778): the same number of cells, uniformly from the SAME legal pool, seeded
        rng = random.Random(cfg['ARM_SEED'])
        chosen = [(k, None, float(ucb[k]), 'random', []) for k in rng.sample(range(len(cands)), min(cfg['MAX_CELLS'], len(cands)))]
    # predicted best over everything the fit can see (training cells + candidates)
    Ht = np.ones((len(y), 1)) if use == 'constant' else np.column_stack([np.ones(len(y)), fx])
    mt, st = g.predict(X, Ht)
    allv = [(float(mt[i]), float(st[i]), rows[i]['lv'], 'measured cell') for i in range(len(rows))] + [(float(mu[i]), float(sd[i]), cands[i]['lv'], 'candidate') for i in range(len(cands))]
    thin = thin_levels(S, cfg)
    allv = [t for t in allv if not any((i, l) in thin for i, l in enumerate(t[2])) and L1.expressible(V, t[2])]   # the best a v1 cell could re-measure at n >= N_FLOOR
    bm = max(allv, key=lambda t: t[0]); bl = max(allv, key=lambda t: t[0] - 2 * t[1])
    tr_lv = [r['lv'] for r in rows]
    def nearest(lv):
        d = [(step_dist(V, lv, t, kinds), i) for i, t in enumerate(tr_lv)]; dd, i = min(d)
        return dict(steps=dd, test=rows[i]['test'], mean=rows[i]['y'], n=rows[i]['n'], where=where(V, rows[i]['lv']))
    cells, why = [], []
    for rank, (k, note, ucb_pick, slot, displaced) in enumerate(chosen, 1):
        c = cands[k]; params = L1.cell_params(V, c['lv']); cid = L1.cell_id(params)
        cells.append(dict(id=cid, params=params, labels=dict(where(V, c['lv']), search=f'search.py round {rnd} pick {rank}')))
        why.append(dict(rank=rank, slot=slot, id=cid, where=where(V, c['lv']), lv=c['lv'], params=params, pred_mean=round(float(mu[k]), 2), pred_sd=round(float(sd[k]), 2),
                        ucb=round(float(ucb[k]), 2), ucb_at_pick=round(ucb_pick, 2), prior_formula=round(float(fc[k]), 2), serves=c['serves'], diversity_exception=note, displaced=displaced, nearest_fit_point=nearest(c['lv'])))
    nd = len(g.dims); ls = g.state['ls']
    lsd = [dict(dial=V[j]['id'], name=V[j]['name'], kind=kinds[j], length_scale=round(float(ls[q]), 3), relevance=round(float(1 / ls[q] ** 2), 3)) for q, j in enumerate(g.dims)]
    lsd.sort(key=lambda d: -d['relevance'])
    fit = dict(round=rnd, arm=cfg.get('ARM', 'hunter'), arm_seed=cfg.get('ARM_SEED'), generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), config=cfg,
               n_train=len(rows), n_families=len({r['family'] for r in rows}), y_mean=round(float(y.mean()), 2), y_sd=round(float(y.std()), 2),
               mean_model=use, beta=[round(float(b), 3) for b in g.state['beta']],
               lml={k: round(float(v.state['lml']), 2) for k, v in fits.items()}, formula_beta=[round(float(b), 3) for b in fits['formula'].state['beta']],
               signal_sd=round(math.sqrt(g.state['sf2']), 2), jitter_sd=round(math.sqrt(g.state['sj2']), 2),
               length_scales=lsd, not_learned=[V[j]['id'] for j in range(len(V)) if j not in g.dims],
               length_scale_units='numeric dials: fraction of the dial\'s full level range (log where log-spaced); categorical: 1 = "different level". '
                                  'Long (>> 1) = the surface barely moves with that dial; short = it matters.',
               predicted_best=dict(mean=round(bm[0], 2), sd=round(bm[1], 2), where=where(V, bm[2]), lv=bm[2], kind=bm[3]),
               predicted_best_lower=dict(mean=round(bl[0], 2), sd=round(bl[1], 2), lower=round(bl[0] - 2 * bl[1], 2), where=where(V, bl[2]), lv=bl[2], kind=bl[3]),
               candidates=len(cands), candidate_info=cinfo, picked=len(cells),
               slots=dict(collections.Counter(w['slot'] for w in why)), displaced=sum(len(w['displaced']) for w in why),
               caveat='every fitted point read the same spent EXPLORE days: the GP sd understates the truth and a predicted peak is a candidate for V / D, never evidence')
    os.makedirs(out, exist_ok=True)
    cj = dict(arm=cfg.get('ARM', 'hunter'), arm_seed=cfg.get('ARM_SEED'), note=f'EDGE MACHINE search.py round {rnd} ({cfg.get("ARM", "hunter")} arm): pre-registered by this file BEFORE any of these cells is run (hash it before the batch)', cells=cells, pass_size=cfg['PASS_SIZE'])
    with tempfile.TemporaryDirectory() as td:                      # engine v1's own contract check (reads no data)
        json.dump(cj, open(td + '/c.json', 'w'))
        r = subprocess.run([sys.executable, HERE + '/engine/prepare_v1.py', td + '/c.json', td + '/o'], capture_output=True, text=True)
        if r.returncode: raise SystemExit('prepare_v1.py REFUSED the picked cells: ' + (r.stderr or r.stdout)[-500:])
    json.dump(cj, open(out + '/cells.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(why, open(out + '/why.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(fit, open(out + '/fit.json', 'w'), indent=1, ensure_ascii=False, default=float)
    print(f"search round {rnd}: {len(rows)} fit points ({fit['n_families']} families, mode {cfg['FAMILY_MODE']}), mean model {use}, "
          f"{len(cands)} legal candidates -> {len(cells)} picked -> {out}")
    print('length-scales (most relevant first):', ', '.join(f"{d['dial']} {d['length_scale']}" for d in lsd[:8]))
    return fit, why

# ============================================================== round bookkeeping
def snapshot(out):
    PT = json.load(open(HERE + '/points.json'))['points']; CA = json.load(open(HERE + '/candidates.json')); FA = json.load(open(HERE + '/families.json'))['families']
    snap = dict(n_points=len(PT), s1=sorted(p['pk'] for p in PT if p['S1']['pass_']), all_pass=sorted(p['pk'] for p in PT if p.get('all_pass')),
                candidates={c['pk']: dict(test=c['test'], labels=c['labels'], mean=c['mean'], lower=c['lower'], trade_set=c.get('trade_set')) for c in CA},
                families=len(FA), trade_sets=len({c.get('trade_set') for c in CA}))
    json.dump(snap, open(out, 'w'), indent=0, ensure_ascii=False); return snap
def short(labels): return ', '.join(f'{k.lower()} {v}' for k, v in labels.items() if k not in ('Dip measured on',)) or 'the held settings'
def jscore(batch_dir):
    """HUNTER v0: J = min(lower 95 % bound, mean without the 5 best coins) on JUDGE real60h; gates n >= 40 trades and >= 8 coins (else J = None)."""
    p = os.path.join(batch_dir or '', 'results.json')
    if not batch_dir or not os.path.exists(p): return []
    out = []
    for cid, c in json.load(open(p))['cells'].items():
        r = ((c.get('JUDGE') or {}).get('real60h') or {}).get('raw') or {}
        ok = (r.get('n') or 0) >= 40 and (r.get('coins') or 0) >= 8 and r.get('lower') is not None and r.get('drop5_coins') is not None
        out.append(dict(id=cid, n=r.get('n'), coins=r.get('coins'), mean=r.get('mean'), lower=r.get('lower'), drop5=r.get('drop5_coins'),
                        J=round(min(r['lower'], r['drop5_coins']), 2) if ok else None, labels=c.get('labels')))
    return out
def summarize(rd, prev, dry, ran, cfg=CONFIG, batch_dir=None):
    cur = json.load(open(rd + '/screen_post.json')) if os.path.exists(rd + '/screen_post.json') else json.load(open(rd + '/screen_pre.json'))
    fit = json.load(open(rd + '/fit.json')); rnd = fit['round']
    s = dict(round=rnd, dry=dry, cells_run=ran, cells_picked=fit['picked'], generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
             candidates=len(cur['candidates']), s1=len(cur['s1']), all_pass=len(cur['all_pass']), families=cur['families'], trade_sets=cur['trade_sets'],
             predicted_best=fit['predicted_best'])
    pb = fit['predicted_best']
    if prev and os.path.exists(prev + '/summary.json'):
        pc = json.load(open(prev + '/screen_post.json')) if os.path.exists(prev + '/screen_post.json') else json.load(open(prev + '/screen_pre.json'))
        pf = json.load(open(prev + '/fit.json'))['predicted_best']
        new_c = [k for k in cur['candidates'] if k not in pc['candidates']]; lost = [k for k in pc['candidates'] if k not in cur['candidates']]
        moved = pf['lv'] != pb['lv'] or abs(pf['mean'] - pb['mean']) >= cfg['BEST_MOVE_PTS']
        s.update(prev_round=json.load(open(prev + '/summary.json'))['round'], new_candidates=new_c, lost_candidates=lost,
                 new_s1=len(set(cur['s1']) - set(pc['s1'])), new_all_pass=len(set(cur['all_pass']) - set(pc['all_pass'])),
                 new_families=cur['families'] - pc['families'], best_moved=moved, prev_best=pf)
        s['changed'] = bool(new_c or lost or moved)
        parts = [f"candidates {len(cur['candidates'])}"]
        if new_c: parts.append('NEW: ' + '; '.join(short(cur['candidates'][k]['labels']) + f" {cur['candidates'][k]['mean']:+.1f} (lower {cur['candidates'][k]['lower']:+.1f})" for k in new_c[:2]) + (f' +{len(new_c) - 2} more' if len(new_c) > 2 else ''))
        if lost: parts.append(f'{len(lost)} lost')
        best = f"predicted best {short(pb['where'])} {pb['mean']:+.1f} ± {pb['sd']:.1f}" + (f" (was {short(pf['where'])} {pf['mean']:+.1f})" if moved else ' (unchanged)')
    else:
        s.update(prev_round=None, changed=False, note='first round: this is the baseline, nothing to compare against')
        parts = [f"candidates {len(cur['candidates'])} in {cur['trade_sets']} independent trade sets (baseline round)"]
        best = f"predicted best {short(pb['where'])} {pb['mean']:+.1f} ± {pb['sd']:.1f}"
    act = f'ran {ran} new cells' if ran else f"picked {fit['picked']} cells" + (' (dry run, not run)' if dry else ', none run')
    arm = fit.get('arm', 'hunter'); js = jscore(batch_dir); jv = [x['J'] for x in js if x['J'] is not None]
    s.update(arm=arm, J_cells=js, J_best=max(jv) if jv else None, J_pos=sum(1 for v in jv if v > 0), J_scored=len(jv))
    run_best = {}                                                  # running best J per arm over every round so far (this one included)
    for d in glob.glob(os.path.join(os.path.dirname(rd), 'round_*', 'summary.json')) + [None]:
        t = s if d is None else (json.load(open(d)) if os.path.abspath(os.path.dirname(d)) != os.path.abspath(rd) else None)
        if t and t.get('J_best') is not None:
            a = t.get('arm', 'hunter'); run_best[a] = max(run_best.get(a, -1e9), t['J_best'])
    s['J_running_best'] = run_best
    jtxt = f"{arm} arm; robust score J (worse of lower bound and without-5-best-coins): best {s['J_best']:+.1f}, {s['J_pos']} of {s['J_scored']} above 0" if jv else f"{arm} arm"
    if run_best: jtxt += '; running best ' + ' vs '.join(f"{a} {v:+.1f}" for a, v in sorted(run_best.items()))
    s['line'] = f"Edge machine round {rnd}: {act}; {jtxt}; " + '; '.join(parts) + f"; {best} — same spent days, so candidates, not evidence."
    json.dump(s, open(rd + '/summary.json', 'w'), indent=1, ensure_ascii=False)
    open(rd + '/line.txt', 'w').write(s['line'] + '\n'); print(s['line']); return s

if __name__ == '__main__':
    a = sys.argv[1:]
    def opt(k, d=None): return a[a.index(k) + 1] if k in a else d
    if a and a[0] == 'snapshot': snapshot(opt('--out'))
    elif a and a[0] == 'summarize': summarize(opt('--round-dir'), opt('--prev-dir'), '--dry' in a, int(opt('--ran', 0)), batch_dir=opt('--batch-dir'))
    else:
        cfg = dict(CONFIG); cfg['FAMILY_MODE'] = opt('--family-mode', cfg['FAMILY_MODE'])
        cfg['ARM'] = opt('--arm', 'hunter'); assert cfg['ARM'] in ('hunter', 'random'), '--arm hunter|random'
        cfg['ARM_SEED'] = int(opt('--seed', 0)) if cfg['ARM'] == 'random' else None
        n = int(opt('--cells', cfg['MAX_CELLS']))                    # HUNTER v0: batch size; slots keep their 5:3:12 proportions
        if n != cfg['MAX_CELLS']:
            sk, sl = round(n * 5 / 20), round(n * 3 / 20)
            cfg.update(MAX_CELLS=n, QUOTA=(('skeleton', sk), ('slice', sl), ('acquisition', n - sk - sl)), MAX_PER_POINT=max(4, n // 10))
        cfg['PASS_SIZE'] = int(opt('--pass-size', cfg['PASS_SIZE']))
        rnd = int(opt('--round', 0)); run_search(rnd, opt('--out', f'{MACHINE}/round_{rnd}'), cfg)
