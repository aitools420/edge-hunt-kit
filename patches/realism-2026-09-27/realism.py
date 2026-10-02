"""realism.py - measured realism inputs for edge backtests (2026-09-27). Import it; do not re-derive the numbers.

    import sys; sys.path.insert(0, os.environ['KIT_ROOT'] + '/patches/realism-2026-09-27'); import realism as R
    c = R.cost_per_side(pool, tok, 'buy', clip_eth, engine_fee=r['ef'], engine_impact=imp)   # dict, c['total'] = fraction
    R.to_eth(usd, ts); R.eth_usd_at(ts); R.eth_gross(px_entry_usd, px_exit_usd, ts_entry, ts_exit)
    R.latency_sec('buy'|'copy'|'sell', q='median'|'p90', recent=False); R.fail_rate('buy'|'sell'); R.gas_pts(clip_eth)

INPUTS (all in this folder):
  pool_costs.json  per-V4-pool type + take (copied from ../blood-realcost-2026-09-27: Pons launch terms read on chain, receipts)
  pool_fees.json   the 63 'unknown' V4 pools (incl. all 20 Doppler Airlock pools the Blood rows name): LP fee + hook take from receipts
  v23_costs.json   V2/V3 real per-side cost from receipts of $20-200 swaps (fee + impact; impact per ETH by pool type and per coin)
  tax_table.json   per-coin transfer tax (buy/sell), measured or family-inferred, with 'unknown' + an expected value
  ethusd.json      ETH/USD from the V4 tape's own eth_usd field, 10-minute medians, 07-20..09-26
  latency.json     our bot's real signal->fill / trigger->fill / failure rate / gas
cost_per_side returns FRACTIONS (0.012 = 1.2 %) for ONE side. It never includes OUR own flat fee (engines charge that).
"""
import json, os, bisect
HERE = os.path.dirname(os.path.abspath(__file__))
def _j(n): return json.load(open(os.path.join(HERE, n)))
PC = _j('pool_costs.json'); POOLS = PC['pools']; K = PC['constants']
PF = _j('pool_fees.json')['pools']; V23 = _j('v23_costs.json'); TAX = _j('tax_table.json')['coins']
EU = _j('ethusd.json')['series']; LAT = _j('latency.json')
_EU_T = [t for t, _ in EU]; _EU_V = [v for _, v in EU]
V23_TYPE_FEE = {'v2': 0.003}
V23_IMP = V23['impact_per_eth_median']
V23_COIN = V23['per_coin']

def tax(tok, side):
    """(fraction, basis) token transfer tax on one side. Unknown coins get their family's expected value (prevalence x median)."""
    o = TAX.get((tok or '').lower())
    if not o: return 0.0, 'not in table (0 assumed)'
    if o['status'] == 'unknown': return float(o.get('expected_tax') or 0.0), 'unknown: family expected value'
    return float(o[side] or 0.0), o['basis']

def _v4(pool, engine_fee):
    """(lp, take, src) for a V4 pool id."""
    p = POOLS.get(pool)
    f = PF.get(pool)
    if f and f.get('status') == 'measured':
        return f['lp'], f['hook'], 'pool_fees.json receipt (%s)' % f['confidence']
    if not p:
        return (engine_fee or 0.01) + K['nohook_protocol_resid'], 0.0, 'FALLBACK not in pool_costs (engine fee + 0.04 %)'
    t = p['type']
    if t == 'pons':
        return 0.0, (p['take'] if p.get('take') is not None else K['pons_take_fallback']), 'pons launch terms' if p.get('take') is not None else 'FALLBACK pons 2.39 %'
    if t == 'nohook':
        lp = p.get('lp_receipt') if p.get('lp_receipt') is not None else (p.get('fee_key') if p.get('fee_key') is not None else engine_fee)
        return (lp or 0.0) + K['nohook_protocol_resid'], 0.0, 'nohook LP fee'
    if t == 'dynfee':
        lp = p.get('lp_receipt') if p.get('lp_receipt') is not None else (engine_fee if engine_fee is not None else K['dynfee_fallback_lp'])
        return lp, 0.0, 'dynamic fee (receipt)' if p.get('lp_receipt') is not None else 'dynamic fee FALLBACK'
    if t == 'otherhook':
        lp = p.get('lp_receipt') if p.get('lp_receipt') is not None else (p.get('fee_key') if p.get('fee_key') is not None else engine_fee)
        return (lp or 0.0), 0.0, 'other hook: LP fee only, hook take UNMEASURED'
    return (engine_fee or 0.01) + K['nohook_protocol_resid'], 0.0, 'FALLBACK unknown pool (engine fee + 0.04 %)'

def cost_per_side(pool, tok, side, clip_eth, engine_fee=None, engine_impact=None):
    """One side's all-in cost (fraction), excluding OUR flat fee.
    pool: a V4 poolId (0x + 64 hex), or an engine pool key for V2/V3 ('v2:WETH', 'v3:WETH', 'v3:USDG', or 'v2'/'v3').
    engine_fee: the engine's own fee for this side (row 'ef'/'xf'), used for the V3 tier when the coin was not measured.
    engine_impact: the engine's own modelled impact (fraction). V4: used as is (the engines read real V4 depth).
                   V2/V3: the larger of it and the measured impact-per-ETH x clip is used."""
    tok = (tok or '').lower(); side = 'buy' if side == 'buy' else 'sell'
    tx, tsrc = tax(tok, side)
    if pool and pool.startswith('0x') and len(pool) == 66:
        lp, take, src = _v4(pool, engine_fee)
        imp = max(engine_impact or 0.0, 0.0)
        return dict(total=lp + take + imp + tx, lp=lp, take=take, impact=imp, tax=tx, src=src, tax_src=tsrc, venue='v4')
    kind = (pool or 'v3').split(':')[0]
    coin = V23_COIN.get('%s|%s' % (tok, pool if ':' in (pool or '') else (pool or 'v3') + ':WETH'))
    if kind == 'v2': fee = 0.003
    elif coin and coin.get('fee') is not None and coin['type'].startswith('v3'): fee = coin['fee']
    else: fee = engine_fee if engine_fee is not None else 0.01
    ipe = coin['impact_per_eth'] if (coin and coin.get('impact_per_eth') is not None) else V23_IMP.get('v2' if kind == 'v2' else ('v3:%g%%' % (fee * 100)), V23_IMP.get('v3:1%'))
    meas_imp = (ipe or 0.0) * (clip_eth or 0.0)
    imp = max(meas_imp, engine_impact or 0.0)
    return dict(total=fee + imp + tx, lp=fee, take=0.0, impact=imp, tax=tx, src='v23_costs.json (%s)' % ('coin measured' if coin else 'type median'),
                tax_src=tsrc, venue=kind, measured_impact=meas_imp)

def eth_usd_at(ts):
    """ETH/USD at ts from the V4 tape's eth_usd (linear between 10-minute medians; clamps outside 07-20..09-26)."""
    i = bisect.bisect_left(_EU_T, ts)
    if i <= 0: return _EU_V[0]
    if i >= len(_EU_T): return _EU_V[-1]
    t0, t1 = _EU_T[i - 1], _EU_T[i]; v0, v1 = _EU_V[i - 1], _EU_V[i]
    return v0 + (v1 - v0) * (ts - t0) / (t1 - t0)
def to_eth(usd, ts): return usd / eth_usd_at(ts)
def eth_gross(px_entry_usd, px_exit_usd, ts_entry, ts_exit):
    """Gross multiple of an ETH-in / ETH-out trade priced in USD: (exit/entry in USD) x ETHUSD(entry)/ETHUSD(exit)."""
    return (px_exit_usd / px_entry_usd) * eth_usd_at(ts_entry) / eth_usd_at(ts_exit)

def latency_sec(side, q='median', recent=False):
    """side 'buy' (robot signal->confirm), 'copy' (copy signal->fill), 'sell' (trigger->confirm). q 'median' | 'p90'."""
    d = LAT['defaults']; sfx = '_p90' if q == 'p90' else ''
    if side == 'sell': return d[('sell_sec_recent' if recent else 'sell_sec') + sfx]
    if side == 'copy': return d['copy_buy_sec' + sfx]
    return d['buy_sec' + sfx]
def fail_rate(side): return LAT['defaults']['buy_fail_rate' if side == 'buy' else 'sell_fail_gas_rate']
def gas_pts(clip_eth, round_trip=True):
    """Real gas per trade in pts of the clip (+ expected gas of failed attempts)."""
    d = LAT['defaults']; g = d['gas_eth_per_swap'] * (2 if round_trip else 1)
    g += d['buy_fail_rate'] * d['gas_eth_per_failed'] + (d['sell_fail_gas_rate'] * d['gas_eth_per_failed'] if round_trip else 0)
    return 100 * g / clip_eth

def _selftest():
    ok = 0
    # 1 a Pons pool: take = launch terms, no LP fee
    pid = next(k for k, v in POOLS.items() if v['type'] == 'pons' and v.get('take') == 0.02)
    c = cost_per_side(pid, '0x0', 'buy', 0.02, engine_impact=0.003); assert abs(c['total'] - 0.023) < 1e-9, c; ok += 1
    # 2 the Flap coin the audit found: ~3 %/side tax
    t, _ = tax('0x20024e485c0b22b42855589700721b28320a7777', 'sell'); assert 0.028 < t < 0.032, t; ok += 1
    # 3 a Doppler Airlock pool is no longer a fallback
    d = next(k for k, v in PF.items() if v.get('doppler_labelled') and v.get('status') == 'measured')
    c = cost_per_side(d, '0x0', 'buy', 0.02); assert 'receipt' in c['src'] and c['lp'] + c['take'] > 0, c; ok += 1
    # 4 a V3 1 % coin at $50: fee 1 % + small impact
    c = cost_per_side('v3:WETH', '0xnotacoin', 'sell', 0.019, engine_fee=0.01); assert 0.01 <= c['total'] < 0.013, c; ok += 1
    # 5 ETH/USD: ~2,400 on 09-16, ~2,690 on 09-26; to_eth round trip
    a, b = eth_usd_at(1789574400 + 43200), eth_usd_at(1790380800 + 43200); assert 2300 < a < 2500 and 2600 < b < 2800, (a, b); ok += 1
    assert abs(to_eth(100, 1790000000) * eth_usd_at(1790000000) - 100) < 1e-9; ok += 1
    # 6 ETH booking removes the ETH move: a coin flat in ETH while ETH rose 10 % is +10 % in USD, 0 in ETH
    ts0, ts1 = 1789574400 + 43200, 1790380800 + 43200; r = eth_usd_at(ts1) / eth_usd_at(ts0)
    assert abs(eth_gross(1.0, r, ts0, ts1) - 1.0) < 1e-9; ok += 1
    # 7 latency / failure / gas
    assert 20 < latency_sec('buy') < 90 and latency_sec('sell') < latency_sec('sell', 'p90') and 0 < fail_rate('buy') < 0.2; ok += 1
    assert 0 < gas_pts(0.02) < 0.5; ok += 1
    print(f'realism.py self-test: {ok}/9 PASS')
if __name__ == '__main__': _selftest()
