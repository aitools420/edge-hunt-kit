"""Python port of edge-round3-2026-09-27/guard.js acceptNew (the FIXED, non-absorbing guard, R-0105). Same constants."""
BAND, WINDOW, MIN, CONFIRM_RATIO = 20.0, 15, 5, 2.0

class G:
    __slots__ = ("med", "pend")
    def __init__(self):
        self.med = []; self.pend = None

def accept(T, px, usd):
    if not (px > 0) or not ((usd or 0) >= 1):
        return False
    if len(T.med) >= MIN:
        s = sorted(T.med); m = s[len(s) >> 1]
        side = -1 if px < m / BAND else (1 if px > m * BAND else 0)
        if side != 0:
            p = T.pend
            if p and p[0] == side and px <= p[1] * CONFIRM_RATIO and px >= p[1] / CONFIRM_RATIO:
                T.pend = None; T.med = [px] * MIN; return True
            T.pend = (side, px); return False
    T.pend = None
    T.med.append(px)
    if len(T.med) > WINDOW:
        T.med.pop(0)
    return True
