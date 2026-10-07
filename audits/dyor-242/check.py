#!/usr/bin/env python3
"""check.py - recompute n and mean per cell from audit242_rows.ndjson (Python 3 standard library only).

Also re-derives every row's net return from the row's own fields (prices, ETH/USD booking rates, per-side costs, gas,
hop legs), so the arithmetic from pool price to net can be checked without our code.
Usage: python3 check.py [audit242_rows.ndjson]"""
import json, sys, collections

path = sys.argv[1] if len(sys.argv) > 1 else 'audit242_rows.ndjson'
rows = [json.loads(l) for l in open(path) if l.strip()]
REL = 1e-9
bad = collections.Counter()


def close(a, b):
    return abs(a - b) <= REL * max(1.0, abs(a), abs(b))


for r in rows:
    # booked ETH prices = pool price in USD / the ETH/USD booking rate at that second
    e = r['entry_price_usd'] / r['eth_usd_booking_entry']
    x = r['exit_price_usd'] / r['eth_usd_booking_exit']
    bad['entry_price_eth_booked'] += not close(e, r['entry_price_eth_booked'])
    bad['exit_price_eth_booked'] += not close(x, r['exit_price_eth_booked'])
    gross = x / e
    bad['gross_multiple'] += not close(gross, r['gross_multiple'])
    bad['clip_eth'] += not close(r['clip_usd'] / r['eth_usd_booking_entry'], r['clip_eth'])
    # net without the quote-token hop (#241's view): buy side x (1 + costs) x (1 + impact), sell side x (1 - costs) / (1 + impact), minus gas
    tb, ts = r['take_buy'], r['take_sell']
    for t in (tb, ts):
        bad['side_total'] += not close(t['lp_fee'] + t['hook_or_creator_take'] + t['price_impact'] + t['token_tax'], t['total'])
    B = (1 + tb['total'] - tb['price_impact']) * (1 + tb['price_impact'])
    S = (1 - (ts['total'] - ts['price_impact'])) / (1 + ts['price_impact'])
    net241 = 100 * (gross * S / B - 1) - r['gas_pct_of_clip']
    bad['net_return_pct_as_241'] += not close(net241, r['net_return_pct_as_241'])
    # net with the ETH <-> quote-token hop on both legs (R-0115's view); no hop on ETH/WETH-quoted pools
    if r['hop_buy']:
        g = r['gas_pct_of_clip']
        net = (net241 + g + 100) * r['hop_sell_multiplier'] / r['hop_buy']['multiplier'] - 100 - g - r['hop_gas_pct_of_clip']
    else:
        net = net241
    bad['net_return_pct'] += not close(net, r['net_return_pct'])
    bad['net_return_eth'] += not close(r['clip_eth'] * r['net_return_pct'] / 100, r['net_return_eth'])
    bad['net_return_eth_as_241'] += not close(r['clip_eth'] * r['net_return_pct_as_241'] / 100, r['net_return_eth_as_241'])
    bad['gross_return_eth'] += not close(r['clip_eth'] * (r['gross_multiple'] - 1), r['gross_return_eth'])

print('rows:', len(rows))
print('row arithmetic re-derived from the row fields; mismatches per field:', dict(bad) if any(bad.values()) else 'none')
for cell in sorted({r['cell'] for r in rows}):
    rs = [r for r in rows if r['cell'] == cell]
    n = len(rs)
    m = lambda k: sum(r[k] for r in rs) / n
    keys = [(r['trigger_tx'], r['trigger_log_index']) for r in rs]
    d0 = rs[0]
    print()
    print(f"cell {cell}: dip {d0['cell_dip_pct']} %, every hour, TP +{d0['cell_take_profit_pct']} %, {d0['cell_max_hold_h']} h, LOW band")
    print(f"  n {n} on {len({r['coin'] for r in rs})} coins; exits {dict(collections.Counter(r['exit_reason'] for r in rs))}; "
          f"duplicate (trigger tx, log index) keys: {len(keys) - len(set(keys))}")
    print(f"  mean net per trade, % of the $50 clip, hop costed (R-0115):       {m('net_return_pct'):+.4f}")
    print(f"  mean net per trade, % of the $50 clip, as #241 (no hop):          {m('net_return_pct_as_241'):+.4f}")
    print(f"  same two views with the take-profit booked at its trigger print:  {m('net_return_pct_tp_at_trigger'):+.4f} / {m('net_return_pct_tp_at_trigger_as_241'):+.4f}")
    print(f"  sum net ETH (R-0115 / #241): {sum(r['net_return_eth'] for r in rs):+.6f} / {sum(r['net_return_eth_as_241'] for r in rs):+.6f}; "
          f"mean gross {m('gross_return_pct'):+.4f} %")
    print(f"  trades on non-ETH-quoted pools (hop costed): {sum(1 for r in rs if r['hop_buy'])}; "
          f"dip below the cell depth when measured in the pool's own quote units: {sum(r['native_dip_below_cell_depth'] for r in rs)}; "
          f"sub-$1 swap after the priced print (entry / exit): {sum(r['entry_later_pool_event_at_or_before_cutoff'] is not None for r in rs)} / "
          f"{sum(r['exit_later_pool_event_at_or_before_cutoff'] is not None for r in rs)}")
sys.exit(1 if any(bad.values()) else 0)
