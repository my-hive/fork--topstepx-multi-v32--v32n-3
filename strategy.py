"""v32n-3 exp3: quiet-open afternoon range-expansion breakout ladder (equity micros).

Economic idea: a compressed 09:30-10:29 CT opening range (OR width < QUIET x
price) on equity index micros, broken after 10:29 by a close beyond OR +/- 15%
of OR width, defines the day's directional pressure from late-positioned
participants; add ladder steps 25% of OR further against that pressure with
protective stops at OR mid and a 3x trailing 30-bar-range chandelier; flat
after 15:03 CT decisions.

Private next-open fill triage (stressed 2-tick slip + 1.5x fee) ranked this
family least-bad on MNQ (cost ratio 2.6% of mean daily |OC|/contract; MYM 5.8%,
M2K 6.7%); this run records honest evaluator numbers for MNQ+MYM+M2K.

Per-entry declared risk: size * stop_dollars <= $300 (RISK0/$200 initial,
RISK_ADD/$150 per add, six adds max). All decisions causal: bar-close data of
the current and prior bars only; position targets fill next minute open.
"""

import numpy as np

SYMS = {
    'M2K': {'pv': 5.0, 'quiet': 0.0025, 'nmax': 10},
    'MYM': {'pv': 0.5, 'quiet': 0.0025, 'nmax': 10},
    'MNQ': {'pv': 2.0, 'quiet': 0.0025, 'nmax': 10},
}
OR_START, OR_END = 34200, 37800     # 09:30 .. 10:29 CT
BUF = 0.15                          # breakout buffer, fraction of OR width
RISK0, RISK_ADD = 200.0, 150.0      # per-entry risk budgets ($)
RISK_CAP = 300.0
EXT_STEP = 0.25                      # add trigger progress, fraction of OR
ADDS_MAX = 6
T_LAST = 54240                      # last decision second (15:03 CT)
CHAND = 3.0                         # chandelier, multiples of trailing r30


def _session(h, l, c, sec, pv, quiet, nmax):
    n = len(sec)
    want = np.zeros(n, dtype=np.int64)
    risk = np.zeros(n)
    i0 = int(np.searchsorted(sec, OR_START))
    i1 = int(np.searchsorted(sec, OR_END))
    if i1 + 1 >= n or i1 - i0 < 20:
        return want, risk
    hi = h[i0:i1].max()
    lo = l[i0:i1].min()
    mid = 0.5 * (hi + lo)
    span = hi - lo
    if span <= 0 or span >= quiet * c[i1]:
        return want, risk
    mode = 0
    cur = 0
    last_fill = 0.0
    peak = 0.0
    trough = 0.0
    r30 = span / 3.0
    adds = 0
    for j in range(i1 + 1, n):
        t = sec[j]
        if j >= i1 + 31:
            r30 = float((h[j - 30:j] - l[j - 30:j]).mean())
        if t > T_LAST:
            cur = 0
            want[j] = 0
            continue
        px = c[j]
        if mode == 0:
            stop_px = mid
            risk_pc = abs(px - stop_px) * pv
            size = 0
            if px > hi + BUF * span:
                mode = 1
            elif px < lo - BUF * span:
                mode = -1
            if mode and RISK_CAP >= risk_pc >= 1e-12 and risk_pc <= RISK0:
                size = int(RISK0 // risk_pc)
            if mode and size >= 1:
                cur = size if mode > 0 else -size
                if abs(cur) > nmax:
                    cur = nmax if mode > 0 else -nmax
                last_fill = px
                peak, trough = h[j], l[j]
                adds = 1
                risk[j] = risk_pc
            if cur == 0:
                mode = 0
            want[j] = cur
            continue
        if mode > 0:
            peak = max(peak, h[j])
            stop_px = max(mid, peak - CHAND * r30) if r30 > 0 else mid
            if l[j] <= stop_px:
                cur = 0
            elif adds < ADDS_MAX and h[j] >= last_fill + EXT_STEP * span:
                risk_pc = max(px - stop_px, 0.0) * pv
                if 1e-9 <= risk_pc <= RISK_ADD:
                    nadd = int(RISK_ADD // risk_pc)
                    if nadd >= 1:
                        new = min(cur + nadd, nmax)
                        if new > cur:
                            cur = new
                            last_fill = px
                            adds += 1
                            risk[j] = risk_pc
        else:
            trough = min(trough, l[j])
            stop_px = min(mid, trough + CHAND * r30) if r30 > 0 else mid
            if h[j] >= stop_px:
                cur = 0
            elif adds < ADDS_MAX and l[j] <= last_fill - EXT_STEP * span:
                risk_pc = max(stop_px - px, 0.0) * pv
                if 1e-9 <= risk_pc <= RISK_ADD:
                    nadd = int(RISK_ADD // risk_pc)
                    if nadd >= 1:
                        new = max(cur - nadd, -nmax)
                        if new < cur:
                            cur = new
                            last_fill = px
                            adds += 1
                            risk[j] = risk_pc
        want[j] = cur
    return want, risk


def _one(df, meta):
    h = df.high.to_numpy(float)
    l = df.low.to_numpy(float)
    c = df.close.to_numpy(float)
    sec = np.rint(df.ct_sec.to_numpy(float)).astype(np.int64)
    n = len(df)
    out = np.zeros(n, dtype=np.int64)
    risk = np.zeros(n)
    for wd in df.groupby('session', sort=False).indices.values():
        rth = (sec[wd] >= OR_START) & (sec[wd] < 54600)
        idx = wd[rth]
        if len(idx) > 30:
            w, r = _session(h[idx], l[idx], c[idx], sec[idx],
                           meta['pv'], meta['quiet'], meta['nmax'])
            out[idx] = w
            risk[idx] = r
    return out, risk


def signals(panel):
    out = {}
    for symbol, df in panel.items():
        if symbol in SYMS:
            out[symbol] = _one(df, SYMS[symbol])[0]
        else:
            out[symbol] = np.zeros(len(df), dtype=np.int64)
    return out


def entry_risk(panel):
    out = {}
    for symbol, df in panel.items():
        if symbol in SYMS:
            out[symbol] = _one(df, SYMS[symbol])[1]
        else:
            out[symbol] = np.zeros(len(df))
    return out
