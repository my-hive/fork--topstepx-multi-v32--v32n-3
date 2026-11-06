"""v32n-3 exp2: quiet-morning directional breakout + chandelier trail (micros).

Hypothesis (1-min CME dev screen, 2010-2023, MES/MGC): sessions whose first 30
RTH minutes print an unusually narrow cash range (pilot < VOBP*price) while
their close sits on one side of the prior RTH close tend to drift that side
through midday (VWAP-band continuation earlier measured strongest). Capture via
6-bar breakout entries 10:00-13:59 while rolling 60-bar range stays compressed;
chandelier trail at sHA*price per contract gives the declared protective stop
dollars; time stop 14:00 CT. Fills = next-minute opens per evaluator contract.

Causality: decision at bar p uses bar p and earlier only; prev close = prior
session's final close. Constants frozen a priori; micros only; N micros sized
N*stop_dollars <= $300 per entry. No optimization performed on this variant.
"""

import numpy as np

VOBP = 0.0020   # pilot + 60-bar cash-range gate, fraction of price
sHA = 0.009     # chandelier stop distance, fraction of price
BREAK = 6       # breakout lookback in bars
FAR = 0.008     # skip chase if gap-to-prev-close already exceeds this
RISK_CAP = 300.0
NCAP = 6        # per-symbol micro contracts cap (exposure stays <= 2.4 std eq)
PV = {'MCL': 100.0, 'MES': 5.0, 'MGC': 10.0, 'MNQ': 2.0}


def _session(hh, ll, cc, ss, prev_close, pv):
    """One session: per-bar position target (fill next open) + entry risk $/ct."""
    n = len(ss)
    want = np.zeros(n, dtype=np.int64)
    risk = np.zeros(n)
    if prev_close is None:
        return want, risk
    pilot_lo = pilot_hi = None
    for p in range(n):
        if 34200 <= ss[p] < 36000:  # 09:30-09:59 CT opening pilot range
            pilot_lo = ll[p] if pilot_lo is None else min(pilot_lo, ll[p])
            pilot_hi = hh[p] if pilot_hi is None else max(pilot_hi, hh[p])
    if pilot_lo is None or pilot_hi is None or pilot_hi <= pilot_lo:
        return want, risk
    pilot = pilot_hi - pilot_lo
    # vectorized trailing windows (inclusive of current bar; masks handle warmup)
    r60 = np.full(n, np.inf)
    if n >= 60:
        r60[59:] = np.lib.stride_tricks.sliding_window_view(hh, 60).max(axis=1) \
                 - np.lib.stride_tricks.sliding_window_view(ll, 60).min(axis=1)
    brk_hi = np.full(n, np.inf)
    brk_lo = np.full(n, -np.inf)
    if n > BREAK:
        brk_hi[BREAK:] = np.lib.stride_tricks.sliding_window_view(hh, BREAK)[:-1].max(axis=1)
        brk_lo[BREAK:] = np.lib.stride_tricks.sliding_window_view(ll, BREAK)[:-1].min(axis=1)
    cur = 0
    ext = 0.0
    went = False
    for p in range(n):
        if ss[p] < 36000:            # before 10:00 CT: flat, no decisions
            continue
        if ss[p] >= 50400:           # at/after 14:00 CT: time stop
            if cur:
                cur = 0
                want[p] = 0
            continue
        if p < 60 or ss[p] - ss[p - 1] != 60:
            continue                 # warmup or data gap: hold/carry current
        want[p] = cur
        px = cc[p]
        if px <= 0:
            continue
        stop_d = sHA * px
        risk_pc = stop_d * pv
        if cur == 0 and not went and pilot < VOBP * px and risk_pc <= RISK_CAP:
            if r60[p] < VOBP * px and abs(px - prev_close) <= FAR * px:
                size = min(int(RISK_CAP // risk_pc), NCAP)
                if size >= 1:
                    if px > prev_close and px > brk_hi[p]:
                        cur, ext, went = size, px, True
                        want[p], risk[p] = cur, risk_pc
                    elif px < prev_close and px < brk_lo[p]:
                        cur, ext, went = -size, px, True
                        want[p], risk[p] = cur, risk_pc
        elif cur > 0:
            if hh[p] > ext:
                ext = hh[p]
            if ll[p] <= ext - stop_d:
                cur = 0
                want[p] = 0
        elif cur < 0:
            if ll[p] < ext:
                ext = ll[p]
            if hh[p] >= ext + stop_d:
                cur = 0
                want[p] = 0
    return want, risk


def _one(df, pv):
    h = df.high.to_numpy(float)
    l = df.low.to_numpy(float)
    c = df.close.to_numpy(float)
    sec = np.rint(df.ct_sec.to_numpy(float)).astype(np.int64)
    n = len(df)
    out = np.zeros(n, dtype=np.int64)
    risk = np.zeros(n)
    prev_close = None
    for wd in df.groupby('session', sort=False).indices.values():
        rth = (sec[wd] >= 34200) & (sec[wd] < 54600)
        if prev_close is not None and np.any(rth):
            idx = wd[rth]
            w, r = _session(h[idx], l[idx], c[idx], sec[idx], prev_close, pv)
            if w.size:
                out[idx] = w
                risk[idx] = r
        prev_close = c[wd[-1]]
    return out, risk


def signals(panel):
    result = {}
    for symbol, df in panel.items():
        if symbol in PV:
            result[symbol] = _one(df, PV[symbol])[0]
        else:
            result[symbol] = np.zeros(len(df), dtype=np.int64)
    return result


def entry_risk(panel):
    result = {}
    for symbol, df in panel.items():
        if symbol in PV:
            result[symbol] = _one(df, PV[symbol])[1]
        else:
            result[symbol] = np.zeros(len(df))
    return result
