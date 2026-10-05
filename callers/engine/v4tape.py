"""v4tape.py — Python reader for the joined Uniswap V4 swap dataset; same interface as v4tape.js.

    import sys; sys.path.insert(0, '/home/green/projects/patches/v4-join-2026-09-27'); import v4tape
    for r in v4tape.read_day('2026-09-20'): ...          # V4 rows in the V2/V3 tape's shape (px = USD, kind='v4') + V4 extras
    for r in v4tape.merged_day('2026-09-20'): ...        # V2/V3 tape + V4, ordered by (ts, blk, li)
    deaths = v4tape.load_deaths()                        # {pool: record}

SEALED HOLDOUT: days >= 2026-09-27 are refused unless allow_sealed='FINAL-EXAM' (patches/SEALED-HOLDOUT/README.md).
"""
import gzip, json, os, heapq
from datetime import date, timedelta

DIR = os.environ.get('CALLERS_V4_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
WE = os.environ.get('CALLERS_TAPE_ROOT', '')
SEAL = 1790467200
SEAL_DAY = '2026-09-27'


def _check(day, allow_sealed):
    if day >= SEAL_DAY and allow_sealed != 'FINAL-EXAM':
        raise PermissionError(f'v4tape: {day} is in the SEALED holdout (>= {SEAL_DAY}) — refused')


def v4_path(day, allow_sealed=None):
    _check(day, allow_sealed)
    p = os.path.join(os.path.join(DIR, 'sealed') if day >= SEAL_DAY else DIR, f'v4-swaps-{day}.ndjson.gz')
    return p if os.path.exists(p) else None


def v23_paths(day, kind='tape'):
    parts = []
    for m in sorted(os.listdir(os.path.join(WE, 'archive'))):
        gz = os.path.join(WE, 'archive', m, f'{kind}-{day}.ndjson.gz')
        if os.path.exists(gz): parts.append(gz)
    live = os.path.join(WE, 'robinhood-tape' if kind == 'tape' else 'robinhood-livetape', f'{kind}-{day}.ndjson')
    if os.path.exists(live): parts.append(live)
    return parts


def to_engine(r):
    return {'ts': r['ts'], 'blk': r['blk'], 'li': r['li'], 'tx': r['tx'], 'tok': r['tok'], 'sym': None, 'w': None,
            'side': r['side'], 'usd': r['usd'], 'px': r['price_usd'], 'kind': 'v4', 'quote': r['quote'], 'pool': r['pool'],
            'price_eth': r['price_eth'], 'price_quote': r['price_quote'], 'amount_token': r['amount_token'],
            'amount_quote': r['amount_quote'], 'liquidity': r['liquidity'], 'depth1_eth': r['depth1_eth'],
            'depth5_eth': r['depth5_eth'], 'pad': r['pad'], 'birth_ts': r['birth_ts'], 'src': r['src']}


def read_day(day, raw=False, allow_sealed=None):
    p = v4_path(day, allow_sealed)
    if not p: return
    lim = float('inf') if allow_sealed == 'FINAL-EXAM' else SEAL
    with gzip.open(p, 'rt') as f:
        for ln in f:
            r = json.loads(ln)
            if r['ts'] >= lim: raise PermissionError('v4tape: sealed row in an unsealed file — refused')
            yield r if raw else to_engine(r)


def read_v23_day(day, kind='tape', allow_sealed=None):
    _check(day, allow_sealed)
    for p in v23_paths(day, kind):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as f:
            for ln in f:
                try: r = json.loads(ln)
                except Exception: continue
                if r.get('ts', 0) >= SEAL and allow_sealed != 'FINAL-EXAM': continue
                yield r


def merged_day(day, allow_sealed=None):
    k = lambda r: (r['ts'], r.get('blk') or 0, r.get('li') or 0)
    a = sorted(read_v23_day(day, allow_sealed=allow_sealed), key=k)
    yield from heapq.merge(a, read_day(day, allow_sealed=allow_sealed), key=k)


def days(frm, to):
    d, e = date.fromisoformat(frm), date.fromisoformat(to)
    while d <= e:
        yield d.isoformat(); d += timedelta(days=1)


def load_deaths():
    with gzip.open(os.path.join(DIR, 'v4-pool-deaths.ndjson.gz'), 'rt') as f:
        return {r['pool']: r for r in map(json.loads, f)}
