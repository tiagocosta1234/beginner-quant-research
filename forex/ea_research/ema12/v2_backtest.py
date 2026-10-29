"""PREREG_READ_V2.md descriptive backtests (they never change the verdict).
(a) v2 applied to his 88 past blind trades, MT5 broker bid/ask (as trade_forensics.py): stop = max(his stop, 5 x noise); target R:R clamped to
    [1.0, 1.5]; a trade that would have been refused as a chase (> 3 x noise in his direction over the last 5 minutes) is dropped.
(b) Mechanical sides on GC futures 2019-07..2026-09 (the 40 v2 test days excluded so nothing about them is seen): last visible candle
    08:14, fill at the 08:15 open one tick worse; sides = the indicator's candle colour (08:00-08:14), the 15m EMA12 bias at 07:45
    (close vs EMA and EMA slope over 4 bars; no bias = no trade), and a random side; brackets = "tight" (3 x noise, 1:1), "v2 1:1"
    (5 x noise), "v2 1.5R" (5 x noise, 1.5 R); v2 rows also skip chases. Cost 0.32 pt (MGC round trip) in R; random-side P vs the mirror.
Usage (from ema12): python v2_backtest.py"""
import numpy as np, pandas as pd
import spot_vs_futures as V

rng = np.random.default_rng(20261026)


def pval(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float((np.where(rng.random((20000, len(a))) < 0.5, a, b).mean(axis=1) >= a.mean()).mean())


# ---------------------------------------------------------------- (a) his trades
L = pd.read_csv("BLIND_LOOK2_FOR_SCORE.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])]
F = pd.read_csv("TRADE_FORENSICS.csv"); noise = dict(zip(F.date, F.noise)); chase = dict(zip(F.date, F.chase))
cache = {}
own, mir, kept_dates = [], [], []
for r in L.itertuples():
    nz = noise.get(r.date)
    if nz is None or nz != nz: continue
    if chase.get(r.date, 0) > 3: continue                                    # v2 refuses the chase
    sd = 1 if r.side == "L" else -1; s0, t0 = abs(r.entry - r.stop), abs(r.target - r.entry)
    sdist = max(s0, 5 * nz); tdist = sdist * min(1.5, max(1.0, t0 / s0))
    s = cache.setdefault(r.date, V.spot_day(r.date))
    t = pd.Timestamp(f"{r.date} {r.hhmm}"); after = s[(s.index >= t + pd.Timedelta(minutes=1)) & (s.index <= pd.Timestamp(f"{r.date} 17:00"))]
    for side, acc in ((sd, own), (-sd, mir)):
        fill = after.ao.iloc[0] if side > 0 else after.bo.iloc[0]
        acc.append(V.play(after, side, sdist, tdist, "bh" if side > 0 else "ah", "bl" if side > 0 else "al", fill, 0.0)[0])
    kept_dates.append(r.date)
own, mir = np.array(own), np.array(mir)
print("(a) v2 on his past blind trades (in-sample what-if, MT5 broker bid/ask): kept %d of %d trades (chases dropped)" % (len(own), len(L)))
print("    his side: wins %.0f%%, mean R %+.3f | mirror: mean R %+.3f | random-side P %.3f" % (100 * (own > 0).mean(), own.mean(), mir.mean(), pval(own, mir)))
yr = pd.Series(own, index=[d[:7] if d >= "2026-07" else d[:4] + (" Jan" if d < "2026-02" else " Feb-Jul") for d in kept_dates])
print("    by block: " + "  ".join("%s %+.3f (%d)" % (k, v.mean(), len(v)) for k, v in yr.groupby(level=0)))
print("    as he actually traded (no v2), same trades: mean R %+.3f" % F[F.date.isin(kept_dates)].R.mean())

# ---------------------------------------------------------------- (b) mechanical sides on futures
import blind_png as B
test_days = set(pd.read_csv("BLIND_V2_2025.csv").date)
g = pd.read_parquet("futures/data/databento/futures_GC.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
g.index = pd.DatetimeIndex(g.ts.dt.tz_convert("Europe/London").dt.tz_localize(None)); g = g[~g.index.duplicated()].drop(columns="ts")
O, H, Lo, C = (g[k].to_numpy() for k in ("open", "high", "low", "close")); T = g.index.to_numpy()
c15 = g.close.resample("15min", label="left", closed="left").last().dropna(); e15 = c15.ewm(span=12, adjust=False).mean()
COST = 0.32
res = {}
for day in pd.Index(g.index.normalize().unique()):
    ds = day.strftime("%Y-%m-%d")
    if day.weekday() >= 5 or ds in test_days or day < pd.Timestamp("2019-07-01"): continue
    i7, i8, i815, i17 = (np.searchsorted(T, np.datetime64(day + pd.Timedelta(hours=h, minutes=m))) for h, m in ((7, 0), (8, 0), (8, 15), (17, 0)))
    if i8 - i7 < 50 or i815 - i8 < 12 or i17 >= len(T) or pd.Timestamp(T[i17]).normalize() != day: continue
    nz = float(np.median(H[i7:i8] - Lo[i7:i8]))
    if not nz > 0: continue
    k15 = day + pd.Timedelta(hours=7, minutes=45)
    if k15 not in c15.index: continue
    j = c15.index.get_loc(k15); c, e, e4 = c15.iloc[j], e15.iloc[j], e15.iloc[j - 4]
    sides = {"candle colour": 1 if C[i815 - 1] > O[i8] else -1 if C[i815 - 1] < O[i8] else 0,
             "15m EMA bias": 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0,
             "random": 1 if rng.random() < 0.5 else -1}
    last5 = C[i815 - 1] - C[i815 - 6]
    for sname, sd in sides.items():
        if sd == 0: continue
        for bname, (k, rr, chase_rule) in {"tight 3x 1:1": (3, 1.0, False), "v2 5x 1:1": (5, 1.0, True), "v2 5x 1.5R": (5, 1.5, True)}.items():
            if chase_rule and sd * last5 > 3 * nz: continue
            out = []
            for side in (sd, -sd):
                fill = O[i815] + side * 0.1; sdist = k * nz; sl, tp = fill - side * sdist, fill + side * rr * sdist; R = None
                for x in range(i815, i17 + 1):
                    if (Lo[x] <= sl) if side > 0 else (H[x] >= sl): R = -1 - 0.1 / sdist; break
                    if (H[x] >= tp) if side > 0 else (Lo[x] <= tp): R = rr; break
                if R is None: R = side * (C[i17] - fill) / sdist
                out.append(R - (COST - 0.2) / sdist)                         # the ticks are in the prices; the rest of the cost here
            res.setdefault((sname, bname), []).append((day.year, out[0], out[1]))
print("\n(b) mechanical sides on GC 2019-07..2026-09 (40 test days excluded), MGC costs; mean R per trade, random-side P")
for (sname, bname), v in sorted(res.items()):
    a = np.array([x[1] for x in v]); m = np.array([x[2] for x in v]); yrs = pd.Series(a, index=[x[0] for x in v]).groupby(level=0).mean()
    print("  %-14s %-12s n %4d  wins %3.0f%%  mean R %+.3f  P %.3f  years>0 %d/%d" % (sname, bname, len(a), 100 * (a > 0).mean(), a.mean(), pval(a, m), (yrs > 0).sum(), len(yrs)))
