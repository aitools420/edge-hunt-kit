// guard.js — EDGE ROUND 3, STEP 0 (R-0105). The bad-print guard, old and fixed, as one module used by every engine in this folder.
// OLD  = theory-batch-2-2026-09-25/engine2.js:91-97 verbatim: reject a print outside median/20..median*20 of the last 15 ACCEPTED
//        prints; a rejected print never enters the median => ABSORBING: after a >95 % crash the coin is frozen at its pre-rug price.
// NEW  = NON-ABSORBING. Same band, same quote/usd checks. A print outside the band is held as PENDING (rejected). If the NEXT
//        out-of-band print of this coin is on the SAME side of the band and within CONFIRM_RATIO (2x) of the pending print, the new
//        level is CONFIRMED: this print is accepted and the reference is RESET to the new level (median window refilled with it).
//        An in-band print clears the pending state (so a lone outlier stays rejected). Prints failing the quote/usd checks do not
//        touch the pending state. Constants fixed here, before any strategy outcome was read: BAND 20, WINDOW 15, MIN 5,
//        CONFIRM_N 2 (the pending print + one confirming print), CONFIRM_RATIO 2.
'use strict';
const BAND = 20, WINDOW = 15, MIN = 5, CONFIRM_RATIO = 2;
function median(a) { const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; }
function acceptOld(T, r) {
  if (!(r.px > 0) || !((r.usd || 0) >= 1)) return false;
  if (r.quote !== T.q) return false;
  if (T.med.length >= MIN) { const m = median(T.med); if (r.px < m / BAND || r.px > m * BAND) return false; }
  T.med.push(r.px); if (T.med.length > WINDOW) T.med.shift();
  return true;
}
function acceptNew(T, r) {
  if (!(r.px > 0) || !((r.usd || 0) >= 1)) return false;
  if (r.quote !== T.q) return false;
  if (T.med.length >= MIN) {
    const m = median(T.med);
    const side = r.px < m / BAND ? -1 : r.px > m * BAND ? 1 : 0;
    if (side !== 0) {
      const p = T.pend;
      if (p && p.side === side && r.px <= p.px * CONFIRM_RATIO && r.px >= p.px / CONFIRM_RATIO) {
        T.pend = null; T.med = new Array(MIN).fill(r.px); T.confirms = (T.confirms || 0) + 1; return true;   // new level confirmed
      }
      T.pend = { side, px: r.px }; return false;                                                           // held, not accepted
    }
  }
  T.pend = null;
  T.med.push(r.px); if (T.med.length > WINDOW) T.med.shift();
  return true;
}
module.exports = { acceptOld, acceptNew, pick: g => (g === 'old' ? acceptOld : g === 'new' ? acceptNew : (() => { throw new Error('GUARD=old|new'); })()) };
