"""Descriptive check of the Algovibes claim (video Y8Y_fjHFJoM, 2026-10-16): the Nasdaq opening-range breakout made money 2021-25 for every opening range 5-60 min.
Our version on MT5 NSDQ M1 bid/ask: box = first N minutes after 09:30 New York, first 5-minute close outside the box until 12:00 NY, entry next bar (ask/bid), stop at the opposite side,
target 1 R, flat at 16:00 NY (same rules as reel 16 trader 1, forex/ea_research/reels_16_17.py). 2026 is never loaded (cut). DESCRIPTIVE: not a candidate test.
python -m forex.ea_research.orb_video_check"""
import numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts, NYZ
from forex.ea_research.orbx import ct
from forex.ea_research.reels_16_17 import day_list
CUT = int(pd.Timestamp("2026-01-01").timestamp())
def orb(D, day, N):
    t = D["t"]; mc = (D["bc"] + D["ac"]) / 2
    b0 = ts(day.year, day.month, day.day, 9, 30, NYZ); b1 = b0 + N * 60
    w1, x1 = ts(day.year, day.month, day.day, 12, 0, NYZ), ts(day.year, day.month, day.day, 16, 0, NYZ)
    i0, i1, iw, ix = np.searchsorted(t, [b0, b1, w1, x1])
    if i1 - i0 < 0.8 * N or ix >= len(t) or iw - i1 < 30: return None
    hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); j = (t[i1:iw] - b1) // 300
    for c in range(int((w1 - b1) // 300)):
        sel = np.flatnonzero(j == c)
        if len(sel) < 3: continue
        cl = mc[i1 + sel[-1]]
        if cl > hi or cl < lo:
            side = 1 if cl > hi else -1; k = int(np.searchsorted(t, b1 + (c + 1) * 300))
            if k >= ix - 1: return None
            e1 = D["ao"][k] if side > 0 else D["bo"][k]; stop = lo if side > 0 else hi; risk = abs(e1 - stop)
            if side * (e1 - stop) <= 0: return None
            ex, _ = walk(D, side, k, ix, stop, e1 + side * risk); pts = (ex - e1) * side
            return dict(day=day, side=side, risk=risk, R=pts / risk, spread=float(D["ao"][k] - D["bo"][k]))
    return None
if __name__ == "__main__":
    D = load("NSDQ", cut=CUT); days = [d for d in day_list(D["t"]) if pd.Timestamp("2022-01-01") <= d < pd.Timestamp("2026-01-01")]
    print("NSDQ ORB, MT5 broker bid/ask, 2022-2025 only (2026 never loaded). R per trade net of the real spread, day-clustered t.")
    print("%-10s %-6s %5s %8s %6s %6s | %s" % ("box (min)", "all n", "R", "t", "win", "spr/R", "by year: n, mean R"))
    for N in (5, 15, 30, 60):
        x = pd.DataFrame([r for r in (orb(D, d, N) for d in days) if r])
        mu, t = ct(x); yr = x.groupby(x.day.dt.year).R.agg(["size", "mean"])
        print("%-10d %-6d %+5.3f %+8.2f %5.0f%% %6.3f | %s" % (N, len(x), mu, t, 100 * (x.R > 0).mean(), (x.spread / x.risk).median(), "  ".join(f"{y}: {int(r['size'])} {r['mean']:+.3f}" for y, r in yr.iterrows())))
