"""PREREG_DOW_US30.md: the frozen London first-15m indicator and the A+ London 12 EMA plan on MT5 US30 (stand-in for MYM), MYM costs.
Usage (from edge_lab): python dow_us30.py"""
import numpy as np, pandas as pd

src = open("edge_lab5.py", encoding="utf-8").read().split("rng = np.random.default_rng(20261026)")[0]
exec(src)                                   # day_table, run_variant (Edge Lab 5 engine)
TICK, PV, COST = 1.0, 0.5, 4.4              # MYM: 1 point a side + USD 1.20 at USD 0.50 a point = 4.4 points round trip

raw = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/DOW_M1_rates.parquet").drop_duplicates("t").sort_values("t")
raw = raw[(raw.bo > 0) & (raw.ao >= raw.bo)]
utc = pd.to_datetime(raw.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
df = pd.DataFrame({"open": ((raw.bo + raw.ao) / 2).to_numpy(), "high": ((raw.bh + raw.ah) / 2).to_numpy(),
                   "low": ((raw.bl + raw.al) / 2).to_numpy(), "close": ((raw.bc + raw.ac) / 2).to_numpy()}, index=utc.to_numpy())
df = df[~df.index.isna()]; df.index = pd.DatetimeIndex(df.index).tz_convert("UTC"); df = df[~df.index.duplicated()].sort_index()
rng = np.random.default_rng(20261026)


def summarize(label, a, m, yrs_index, primary):
    a, m = np.asarray(a), np.asarray(m)
    p = float((np.where(rng.random((20000, len(a))) < 0.5, a, m).mean(axis=1) >= a.mean()).mean())
    yrs = pd.Series(a, index=yrs_index).groupby(level=0).mean()
    pos = int((yrs.loc[[y for y in yrs.index if 2022 <= y <= 2026]] > 0).sum())
    ok = primary and a.mean() > 0 and p <= 0.025 and pos >= 3 and len(a) >= 100
    print("%-32s n %4d  win %3.0f%%  mean net R %+.3f  P %.4f  years>0 %d/5  2026 %+.3f  %s" % (label, len(a), 100 * (a > 0).mean(), a.mean(), p, pos,
          yrs.get(2026, np.nan), ("-> PASS" if ok else "-> NOT SHOWN") if primary else "(secondary)"))
    print("      by year: " + " ".join("%d %+.3f (%d)" % (y, v, (np.asarray(yrs_index) == y).sum()) for y, v in yrs.items()))


# ---- Test 1: the indicator
rows = run_variant(day_table(df), TICK, PV, "D1", 0.5, 1, {})
R1 = pd.DataFrame(rows, columns=["date", "side", "g", "a", "m"]); R1 = R1[pd.to_datetime(R1.date) >= "2022-01-01"]
print("US30 days %d (%s .. %s), price %.0f .. %.0f" % (len(R1), R1.date.min().date(), R1.date.max().date(), df.close.iloc[0], df.close.iloc[-1]))
summarize("Test 1 indicator (track A)", R1.a, R1.m, pd.to_datetime(R1.date).dt.year.to_numpy(), True)

# ---- Test 2: A+ London 12 EMA (same rules as london12_aplus.py, Dow stop band 0.06%-0.24% of price)
lon = df.index.tz_convert("Europe/London").tz_localize(None)
d2 = df.copy(); d2.index = lon; d2 = d2[~d2.index.duplicated()]
d2["ema1"] = d2.close.ewm(span=12, adjust=False).mean()
m15 = d2.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
h1 = d2.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
O, H, L, C, E = (d2[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")); TS = d2.index.to_numpy()
out = []
for day in pd.Index(d2.index.normalize().unique()):
    if day.weekday() >= 5 or day < pd.Timestamp("2022-01-01"): continue
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
    if not (0.0006 * entry <= risk <= 0.0024 * entry): continue
    c1 = False
    for k in range(max(sig - 60, 2), sig):
        if bias > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
        if bias < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
    s0 = np.searchsorted(TS, np.datetime64(day)); s7 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7)))
    c2 = bool(s7 > s0 + 30 and ((L[s7:sig + 1].min() < L[s0:s7].min()) if bias > 0 else (H[s7:sig + 1].max() > H[s0:s7].max())))
    k1h = day + pd.Timedelta(hours=7)
    c3 = bool(k1h in h1.index and bias * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
    res = {}
    for name, kk in (("T1", 1.0), ("T15", 1.5)):
        for sd, lab in ((bias, ""), (-bias, "_m")):
            sl = entry - sd * risk; tp = entry + sd * kk * risk; px = None
            for j in range(sig + 1, min(end + 1, len(C))):
                if j >= end: px = O[j]; break
                if (L[j] <= sl) if sd > 0 else (H[j] >= sl): px = sl; break
                if (H[j] >= tp) if sd > 0 else (L[j] <= tp): px = tp; break
            if px is None: px = C[min(end, len(C) - 1)]
            res[name + lab] = sd * (px - entry) / risk - COST / risk
    out.append(dict(yr=day.year, aplus=(int(c1) + int(c2) + int(c3)) >= 2, c1=c1, c2=c2, c3=c3, risk=risk, **res))
R2 = pd.DataFrame(out)
print("A+ 12 EMA: hard-rule trades %d, A+ %d, C1 %.0f%% C2 %.0f%% C3 %.0f%%, median risk %.0f points" % (
    len(R2), R2.aplus.sum(), 100 * R2.c1.mean(), 100 * R2.c2.mean(), 100 * R2.c3.mean(), R2.risk.median()))
A = R2[R2.aplus]
summarize("Test 2 A+ 12 EMA, 1:1", A.T1, A.T1_m, A.yr.to_numpy(), True)
summarize("A+ 12 EMA, 1.5R", A.T15, A.T15_m, A.yr.to_numpy(), False)
summarize("12 EMA hard rules only, 1:1", R2.T1, R2.T1_m, R2.yr.to_numpy(), False)
