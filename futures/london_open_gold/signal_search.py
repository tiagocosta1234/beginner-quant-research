"""PREREG_SIGNAL_SEARCH: 16-cell filter search on the london_open_indicator.pine London A+ rule. GC DEV 2019-09..2022-12 / TEST 2023-01..2026-09, one look; NQ and ES replication (secondary).
Usage (from london_open_gold): python signal_search.py"""
import itertools, numpy as np, pandas as pd

DB = "futures/data/databento/futures_%s.F_1m.parquet"
COST = {"GC": 0.292, "NQ": 0.860, "ES": 0.494}; TICK = {"GC": 0.1, "NQ": 0.25, "ES": 0.25}


def candidates(sym):
    d = pd.read_parquet(DB % sym, columns=["ts", "open", "high", "low", "close"]).drop_duplicates("ts")
    ts = pd.DatetimeIndex(pd.to_datetime(d.ts, utc=True))
    df = d.drop(columns=["ts"]).set_index(ts.tz_convert("Europe/London").tz_localize(None)).sort_index(); df = df[~df.index.duplicated()]
    df["ema1"] = df.close.ewm(span=12, adjust=False).mean()
    m15 = df.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
    h1 = df.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
    dly = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()          # London calendar days, only used for the prior-day trend
    up = (dly.close > dly.close.rolling(20).mean()).shift(1)
    O, H, L, C, E = (df[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")); TS = df.index.to_numpy()
    rows = []
    for day in pd.Index(df.index.normalize().unique()):
        if day < pd.Timestamp("2019-09-02") or day.weekday() >= 5: continue
        k15 = day + pd.Timedelta(hours=7, minutes=45)
        if k15 not in m15.index: continue
        i = m15.index.get_loc(k15)
        if i < 4: continue
        c, e, e4 = m15.iloc[i], e15.iloc[i], e15.iloc[i - 4]
        bias = 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0
        if bias == 0: continue
        a = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8))); b = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8, minutes=15)))
        end = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=16))); sig = None
        for j in range(max(a, 1), b):
            body = abs(C[j] - O[j]); wick = max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j])
            if bias * (C[j] - E[j]) > 0 and bias * (C[j - 1] - E[j - 1]) < 0 and body > wick: sig = j; break
        if sig is None or sig < 6: continue
        entry = C[sig]; stop = (L[sig - 5:sig + 1].min() - TICK[sym]) if bias > 0 else (H[sig - 5:sig + 1].max() + TICK[sym]); risk = abs(entry - stop)
        ok = (1.5 <= risk <= 6.0) if sym == "GC" else (0.000375 * entry <= risk <= 0.0015 * entry)
        if not ok: continue
        c1 = False
        for k in range(max(sig - 60, 2), sig):
            if bias > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
            if bias < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
        s0 = np.searchsorted(TS, np.datetime64(day)); s7 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7))); c2 = False
        if s7 > s0 + 30: c2 = bool(L[s7:sig + 1].min() < L[s0:s7].min()) if bias > 0 else bool(H[s7:sig + 1].max() > H[s0:s7].max())
        k1h = day + pd.Timedelta(hours=7); c3 = bool(k1h in h1.index and bias * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
        res = {}
        for lab, sd in (("g", bias), ("gm", -bias)):
            sl = entry - sd * risk; tp = entry + sd * risk; out = None
            for j in range(sig + 1, min(end + 1, len(C))):
                if j >= end: out = O[j]; break
                if (L[j] <= sl) if sd > 0 else (H[j] >= sl): out = sl; break
                if (H[j] >= tp) if sd > 0 else (L[j] <= tp): out = tp; break
            if out is None: out = C[min(end, len(C) - 1)]
            res[lab] = sd * (out - entry) / risk
        tr = up.get(day, np.nan)
        rows.append(dict(day=day, risk=risk, c1=c1, c2=c2, c3=c3, conf=int(c1) + int(c2) + int(c3), early=(sig - a) < 5,
                         trend=(np.nan if pd.isna(tr) else float((bias > 0) == bool(tr))), **res))
    R = pd.DataFrame(rows); cost = COST[sym]
    R["net"] = R.g - cost / R.risk; R["netm"] = R.gm - cost / R.risk; R["share"] = cost / R.risk
    return R


def cell(R, f1, f2, f3, f4):
    m = (R.c1 & R.c3) if f2 else (R.conf >= 2)
    if f1: m &= R.share <= 0.12
    if f3: m &= R.early
    if f4: m &= R.trend == 1.0
    return R[m]


rng = np.random.default_rng(20261027)
def pval(f):
    a, mm = f.net.to_numpy(), f.netm.to_numpy()
    return float((np.where(rng.random((20000, len(a))) < 0.5, a, mm).mean(axis=1) >= a.mean()).mean())


G = candidates("GC"); DEV = G[G.day < "2023-01-01"]; TEST = G[G.day >= "2023-01-01"]
print("GC candidates with hard rules + risk bounds: DEV %d, TEST %d" % (len(DEV), len(TEST)))
print("cell (F1 cost<=12%%, F2 strict C1&C3, F3 first 5 min, F4 with daily trend) -> DEV n / net R -> TEST n / net R")
table = []
for fl in itertools.product((0, 1), repeat=4):
    a, t = cell(DEV, *fl), cell(TEST, *fl)
    table.append((fl, len(a), a.net.mean() if len(a) else np.nan, len(t), t.net.mean() if len(t) else np.nan))
    print("  %s  DEV %3d %+.3f -> TEST %3d %+.3f" % (fl, *table[-1][1:]))
cand = [x for x in table if x[1] >= 60]
best = max(cand, key=lambda x: x[2]); fl = best[0]
print("\nDEV winner (n >= 60):", fl, "DEV n %d net %+.3f" % (best[1], best[2]))
dv = pd.DataFrame(table, columns=["fl", "nd", "dm", "nt", "tm"]).dropna(); print("DEV/TEST correlation of cell means over %d cells: %.2f" % (len(dv), dv.dm.corr(dv.tm)))
f = cell(TEST, *fl); P = pval(f) if len(f) > 5 else np.nan
yrs = f.groupby(f.day.dt.year).net.mean()
print("TEST (one look): n %d, wins %.0f%%, mean net R %+.3f, total %+.1f R, mirror %+.3f, random-side P %.3f | by year: %s" % (
    len(f), 100 * (f.net > 0).mean(), f.net.mean(), f.net.sum(), f.netm.mean(), P, "  ".join("%d %+.2f (%d)" % (y, v, (f.day.dt.year == y).sum()) for y, v in yrs.items())))
base = cell(TEST, 0, 0, 0, 0)
print("unfiltered A+ on TEST (reference): n %d, mean net R %+.3f" % (len(base), base.net.mean()))
ok = len(f) >= 50 and f.net.mean() > 0.05 and P <= 0.05 and (yrs > 0).sum() >= 3
print("VERDICT:", "SHOWN" if ok else "NOT SHOWN")
for sym in ("NQ", "ES"):
    X = candidates(sym); x = cell(X[X.day >= "2023-01-01"], *fl); xb = cell(X[X.day >= "2023-01-01"], 0, 0, 0, 0)
    print("replication %s TEST 2023-26: chosen cell n %d net %+.3f (P %.3f) | unfiltered A+ n %d net %+.3f" % (sym, len(x), x.net.mean() if len(x) else np.nan, pval(x) if len(x) > 5 else np.nan, len(xb), xb.net.mean()))
