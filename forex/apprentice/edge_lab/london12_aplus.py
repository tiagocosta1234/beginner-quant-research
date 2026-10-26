"""PREREG_LONDON12_APLUS.md: the frozen A+ London 12 EMA demo plan as a mechanical backtest on Databento GC 1-minute.
Usage (from edge_lab): python london12_aplus.py"""
import numpy as np, pandas as pd

COST, TICK = 0.32, 0.1
df = pd.read_parquet("D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts")
df = df[["ts", "open", "high", "low", "close"]].drop_duplicates("ts")
df["lon"] = pd.to_datetime(df.ts, utc=True).dt.tz_convert("Europe/London").dt.tz_localize(None)
df = df.set_index("lon").sort_index()
df["ema1"] = df.close.ewm(span=12, adjust=False).mean()
m15 = df.close.resample("15min", label="left", closed="left").last().dropna()
e15 = m15.ewm(span=12, adjust=False).mean()
h1 = df.close.resample("60min", label="left", closed="left").last().dropna()
e1h = h1.ewm(span=12, adjust=False).mean()
O, H, L, C, E, T = (df[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")), None, None, None, None, None
O, H, L, C, E = (df[k].to_numpy() for k in ("open", "high", "low", "close", "ema1"))
TS = df.index.to_numpy()

rows = []
for day in pd.Index(df.index.normalize().unique()):
    if day.weekday() >= 5 or day < pd.Timestamp("2019-09-02"): continue
    k15 = day + pd.Timedelta(hours=7, minutes=45)
    if k15 not in m15.index: continue
    i = m15.index.get_loc(k15)
    if i < 4: continue
    c, e, e4 = m15.iloc[i], e15.iloc[i], e15.iloc[i - 4]
    bias = 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0
    if bias == 0: continue
    a = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7, minutes=59)))
    b = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8, minutes=15)))
    end = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=16)))
    sig = None
    for j in range(max(a, 1), b):
        body = abs(C[j] - O[j]); wick = max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j])
        if bias * (C[j] - E[j]) > 0 and bias * (C[j - 1] - E[j - 1]) < 0 and body > wick:
            sig = j; break
    if sig is None or sig < 6: continue
    entry = C[sig]
    stop = (L[sig - 5:sig + 1].min() - TICK) if bias > 0 else (H[sig - 5:sig + 1].max() + TICK)
    risk = abs(entry - stop)
    if not (1.5 <= risk <= 6.0): continue
    # confluence
    lo60 = max(sig - 60, 2); c1 = False
    for k in range(lo60, sig):
        if bias > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
        if bias < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
    s0 = np.searchsorted(TS, np.datetime64(day)); s7 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7)))
    c2 = False
    if s7 > s0 + 30:
        if bias > 0: c2 = L[s7:sig + 1].min() < L[s0:s7].min()
        else: c2 = H[s7:sig + 1].max() > H[s0:s7].max()
    k1h = day + pd.Timedelta(hours=7)
    c3 = bool(k1h in h1.index and bias * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
    res = {}
    for name, kk in (("T1", 1.0), ("T15", 1.5)):
        for sd, lab in ((bias, ""), (-bias, "_m")):
            sl = entry - sd * risk; tp = entry + sd * kk * risk; out = None
            for j in range(sig + 1, min(end + 1, len(C))):
                if j >= end: out = O[j]; break
                if (L[j] <= sl) if sd > 0 else (H[j] >= sl): out = sl; break
                if (H[j] >= tp) if sd > 0 else (L[j] <= tp): out = tp; break
            if out is None: out = C[min(end, len(C) - 1)]
            res[name + lab] = sd * (out - entry) / risk - COST / risk
    rows.append(dict(date=day, yr=day.year, bias=bias, risk=risk, c1=c1, c2=c2, c3=c3, aplus=(int(c1) + int(c2) + int(c3)) >= 2, **res))   # Amendment 1: int(), numpy bool + bool is OR

R = pd.DataFrame(rows)
rng = np.random.default_rng(20261026)
print("GC days with a valid hard-rule trade: %d (%s .. %s); A+ %d; confluence hit rates C1 %.0f%% C2 %.0f%% C3 %.0f%%" % (
    len(R), R.date.min().date(), R.date.max().date(), R.aplus.sum(), 100 * R.c1.mean(), 100 * R.c2.mean(), 100 * R.c3.mean()))
for label, sub, primary in (("A+ ", R[R.aplus], True), ("B (hard only)", R, False)):
    for t in ("T1", "T15"):
        a, mm = sub[t].to_numpy(), sub[t + "_m"].to_numpy()
        if len(a) < 5: print(label, t, "too few trades"); continue
        p = float((np.where(rng.random((20000, len(a))) < 0.5, a, mm).mean(axis=1) >= a.mean()).mean())
        yrs = sub.groupby("yr")[t].mean(); pos = int((yrs.loc[[y for y in yrs.index if 2020 <= y <= 2026]] > 0).sum())
        ok = primary and a.mean() > 0 and p <= 0.025 and pos >= 5 and len(a) >= 100
        print("%-14s %-3s n %4d  win %3.0f%%  mean net R %+.3f  P %.4f  years>0 %d/7  2026 %+.3f (n %d)  %s" % (
            label, t, len(a), 100 * (a > 0).mean(), a.mean(), p, pos, yrs.get(2026, np.nan), (sub.yr == 2026).sum(),
            ("-> PASS" if ok else "-> NOT SHOWN") if primary else "(secondary)"))
        print("      by year: " + " ".join("%d %+.3f (%d)" % (y, v, (sub.yr == y).sum()) for y, v in yrs.items()))
