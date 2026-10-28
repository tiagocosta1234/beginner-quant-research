"""PREREG_PHASE_ORB: 15-minute opening-range breakout in the daily trend's direction, only on high-volatility trend days. GC, SI, NQ, ES
(Databento 1m 2019-06..2026-09). Mirror = same fill minute and price, opposite side, same distances. Usage: python phase_orb.py"""
import numpy as np, pandas as pd

MK = {"GC": (0.10, 0.32, [("London", "Europe/London", "08:00", "16:00"), ("New York", "America/New_York", "09:30", "15:55")]),
      "SI": (0.005, 0.025, [("London", "Europe/London", "08:00", "16:00"), ("New York", "America/New_York", "09:30", "15:55")]),
      "NQ": (0.25, 1.1, [("New York", "America/New_York", "09:30", "15:55")]),
      "ES": (0.25, 0.74, [("New York", "America/New_York", "09:30", "15:55")])}


def walk(H, L, C, k0, side, entry, risk, cost, last):
    """From fill bar k0: SL first (fill bar included), TP from the next bar, else close of the last bar. Returns R net of cost."""
    sl = entry - side * risk; tp = entry + side * risk
    for k in range(k0, last + 1):
        if (L[k] <= sl) if side > 0 else (H[k] >= sl): return -1 - cost / risk
        if k > k0 and ((H[k] >= tp) if side > 0 else (L[k] <= tp)): return 1 - cost / risk
    return side * (C[last] - entry) / risk - cost / risk


rows = []
for sym, (tick, cost, sessions) in MK.items():
    g = pd.read_parquet(f"D:/finance/beginner-quant-research/futures/data/databento/futures_{sym}.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
    g.index = pd.DatetimeIndex(g.ts); g = g.drop(columns="ts"); g = g[~g.index.duplicated()].sort_index()
    td = (g.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    D = g.groupby(td).agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    tr = pd.concat([D.high - D.low, (D.high - D.close.shift()).abs(), (D.low - D.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean(); hv = (atr / atr.rolling(250).median()).shift(1) > 1.25
    s50 = D.close.rolling(50).mean(); sl20 = (s50 - s50.shift(20)) / s50.shift(20)
    c1, s1, d1 = D.close.shift(1), s50.shift(1), sl20.shift(1)
    trend = pd.Series(np.where((c1 < s1) & (d1 < -0.01), -1, np.where((c1 > s1) & (d1 > 0.01), 1, 0)), index=D.index)
    H, L, C = g.high.to_numpy(), g.low.to_numpy(), g.close.to_numpy()
    for ses, tz, op, endt in sessions:
        loc = g.index.tz_convert(tz).tz_localize(None); hm = loc.strftime("%H:%M"); day = loc.normalize()
        opm = int(op[:2]) * 60 + int(op[3:]); mins = loc.hour * 60 + loc.minute
        frame = pd.DataFrame({"day": day, "m": mins, "i": np.arange(len(g))})
        for dkey, f in frame.groupby("day"):
            tdk = dkey
            if tdk not in trend.index or pd.isna(hv.get(tdk, np.nan)): continue
            tsgn = int(trend[tdk]); phase = bool(hv[tdk]) and tsgn != 0
            if tsgn == 0: continue
            rng_ = f[(f.m >= opm) & (f.m < opm + 15)]; win = f[(f.m >= opm + 15) & (f.m < opm + 60)]
            endm = int(endt[:2]) * 60 + int(endt[3:]); sess = f[(f.m >= opm + 15) & (f.m < endm)]
            if len(rng_) < 12 or not len(win) or not len(sess): continue
            hi, lo = H[rng_.i].max(), L[rng_.i].min(); last = int(sess.i.iloc[-1])
            entry = lo - tick if tsgn < 0 else hi + tick; risk = (hi + tick) - (lo - tick)
            wi = win.i.to_numpy(); hit = (L[wi] <= entry) if tsgn < 0 else (H[wi] >= entry)
            if not hit.any() or risk <= 0: continue
            k0 = int(wi[hit.argmax()])
            own = walk(H, L, C, k0, tsgn, entry, risk, cost, last); mir = walk(H, L, C, k0, -tsgn, entry, risk, cost, last)
            rows.append(dict(sym=sym, ses=ses, day=dkey, phase=phase, side=tsgn, R=own, mirror=mir))
X = pd.DataFrame(rows); X.to_csv("PHASE_ORB_TRADES.csv", index=False)
rng = np.random.default_rng(20261027)
for lab, part in (("HIGH-VOL TREND DAYS (the registered rule)", X[X.phase]), ("trend days that are NOT high-vol (reported only)", X[~X.phase])):
    n = len(part); m = part.R.mean()
    flips = np.where(rng.random((20000, n)) < 0.5, part.R.to_numpy(), part.mirror.to_numpy()).mean(axis=1); p = float((flips >= m).mean())
    print("%s: n %d, wins %.1f%%, mean %+.3f R, total %+.1f R, mirror mean %+.3f, random-side P %.4f" % (lab, n, 100 * (part.R > 0).mean(), m, part.R.sum(), part.mirror.mean(), p))
    for sym, x in part.groupby("sym"): print("   %s: n %4d, mean %+.3f R | shorts %+.3f (%d), longs %+.3f (%d)" % (sym, len(x), x.R.mean(), x[x.side < 0].R.mean() if (x.side < 0).any() else np.nan,
                                              (x.side < 0).sum(), x[x.side > 0].R.mean() if (x.side > 0).any() else np.nan, (x.side > 0).sum()))
ph = X[X.phase]; okm = sum(ph[ph.sym == s].R.mean() > 0 for s in MK)
nn = len(ph); mm = ph.R.mean(); pp = float((np.where(rng.random((20000, nn)) < 0.5, ph.R.to_numpy(), ph.mirror.to_numpy()).mean(axis=1) >= mm).mean())
print("\nVERDICT:", "WORKS" if (mm > 0 and pp <= 0.05 and okm >= 3 and nn >= 150) else "NOT SHOWN", "(markets positive %d/4)" % okm)
