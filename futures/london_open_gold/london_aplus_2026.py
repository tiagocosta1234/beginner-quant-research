"""27 Oct 2026, descriptive (not registered): the london_open_indicator.pine rule (A+ London 12 EMA, 1:1) on every 1-minute futures file on disk, 2026 only.
Rule = london_open_indicator.pine: 15m bias candle 07:45 London (close vs EMA12, EMA12 vs 4 candles earlier), first 1m candle opening 08:00-08:14 that freshly crosses the 1m EMA12 on the bias
side with body > biggest wick, entry at its close, stop beyond the last 6 candles + 1 tick, risk bounds 0.0375%..0.15% of price (= gold's 1.5..6 pt at ~4000), A+ = 2 of 3
(FVG in the last 60 min, Asia 00:00-07:00 sweep, 07:00 hourly candle vs its EMA12), 1R target, stop first on a tie, flat at 16:00 London.
Costs (points, round trip): GC/MGC 0.32, NQ/MNQ 1.1, ES/MES 0.74, MYM 4.4, SI 0.025 (earlier preregs); M2K, MCL, SIL, MBT, MET = 2 ticks + USD 1.20 / point value (assumption).
Data: Databento GC NQ ES SI (full 2026 to 25 Sep) and BrokerAPI 1m files (only 29 Jul..25 Sep 2026 exist). Usage: python london_aplus_2026.py"""
import numpy as np, pandas as pd

DB = "futures/data/databento/futures_%s.F_1m.parquet"
TX = "futures/data/%s_1MIN_BROKERAPI.csv"
SPEC = {  # name: (source, tick, cost points)
    "GC": ("db", 0.1, 0.32), "NQ": ("db", 0.25, 1.1), "ES": ("db", 0.25, 0.74), "SI": ("db", 0.005, 0.025),
    "MGC": ("tx", 0.1, 0.32), "MNQ": ("tx", 0.25, 1.1), "MES": ("tx", 0.25, 0.74), "MYM": ("tx", 1.0, 4.4),
    "M2K": ("tx", 0.1, 0.2 + 1.2 / 5), "MCL": ("tx", 0.01, 0.02 + 1.2 / 100), "SIL": ("tx", 0.005, 0.01 + 1.2 / 200),
    "MBT": ("tx", 5.0, 10 + 1.2 / 0.1), "MET": ("tx", 0.5, 1.0 + 1.2 / 0.1),
}
START = pd.Timestamp("2026-01-01")


def load(name, src):
    if src == "db":
        d = pd.read_parquet(DB % name, columns=["ts", "open", "high", "low", "close"]).drop_duplicates("ts")
        ts = pd.DatetimeIndex(pd.to_datetime(d.ts, utc=True))
    else:
        d = pd.read_csv(TX % name, usecols=["timestamp", "open", "high", "low", "close"]).drop_duplicates("timestamp")
        ts = pd.DatetimeIndex(pd.to_datetime(d.timestamp, utc=True))
    d = d.drop(columns=[c for c in ("ts", "timestamp") if c in d]).set_index(ts.tz_convert("Europe/London").tz_localize(None)).sort_index()
    return d[~d.index.duplicated()]


def run(name, src, tick, cost):
    df = load(name, src)
    df["ema1"] = df.close.ewm(span=12, adjust=False).mean()
    m15 = df.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
    h1 = df.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
    O, H, L, C, E = (df[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")); TS = df.index.to_numpy()
    rows, cand = [], 0
    for day in pd.Index(df.index.normalize().unique()):
        if day < START or day.weekday() >= 5: continue
        if src == "tx" and day < pd.Timestamp("2026-08-03"): continue                 # 3 days of EMA warm-up on the short BrokerAPI files
        k15 = day + pd.Timedelta(hours=7, minutes=45)
        if k15 not in m15.index: continue
        i = m15.index.get_loc(k15)
        if i < 4: continue
        c, e, e4 = m15.iloc[i], e15.iloc[i], e15.iloc[i - 4]
        bias = 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0
        if bias == 0: continue
        a = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8)))
        b = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8, minutes=15)))
        end = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=16)))
        sig = None
        for j in range(max(a, 1), b):
            body = abs(C[j] - O[j]); wick = max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j])
            if bias * (C[j] - E[j]) > 0 and bias * (C[j - 1] - E[j - 1]) < 0 and body > wick: sig = j; break
        if sig is None or sig < 6: continue
        cand += 1
        entry = C[sig]
        stop = (L[sig - 5:sig + 1].min() - tick) if bias > 0 else (H[sig - 5:sig + 1].max() + tick)
        risk = abs(entry - stop)
        if not (0.000375 * entry <= risk <= 0.0015 * entry): continue
        lo60 = max(sig - 60, 2); c1 = False
        for k in range(lo60, sig):
            if bias > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
            if bias < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
        s0 = np.searchsorted(TS, np.datetime64(day)); s7 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7)))
        c2 = False
        if s7 > s0 + 30:
            c2 = bool(L[s7:sig + 1].min() < L[s0:s7].min()) if bias > 0 else bool(H[s7:sig + 1].max() > H[s0:s7].max())
        k1h = day + pd.Timedelta(hours=7)
        c3 = bool(k1h in h1.index and bias * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
        res = {}
        for lab, sd in (("r", bias), ("m", -bias)):                                  # real side and mirror
            sl = entry - sd * risk; tp = entry + sd * risk; out = None
            for j in range(sig + 1, min(end + 1, len(C))):
                if j >= end: out = O[j]; break
                if (L[j] <= sl) if sd > 0 else (H[j] >= sl): out = sl; break
                if (H[j] >= tp) if sd > 0 else (L[j] <= tp): out = tp; break
            if out is None: out = C[min(end, len(C) - 1)]
            res[lab] = sd * (out - entry) / risk - cost / risk
        rows.append(dict(day=day, aplus=(int(c1) + int(c2) + int(c3)) >= 2, r=res["r"], m=res["m"]))
    return pd.DataFrame(rows), cand


out = []
print("london_open_indicator.pine rule, 2026, 1-minute futures. A+ = hard rules + 2 of 3 confluence; B = hard rules only. Net R after costs, 1:1.")
print("%-4s %-9s %5s | %4s %5s %8s | %4s %5s %8s" % ("sym", "window", "cands", "A+ n", "win%", "mean R", "B n", "win%", "mean R"))
for name, (src, tick, cost) in SPEC.items():
    R, cand = run(name, src, tick, cost)
    if not len(R): print("%-4s no trades" % name); continue
    R["sym"], R["src"] = name, src; out.append(R)
    A = R[R.aplus]
    print("%-4s %-9s %5d | %4d %5.0f %+8.3f | %4d %5.0f %+8.3f" % (name, "2026" if src == "db" else "Aug-Sep", cand, len(A), 100 * (A.r > 0).mean() if len(A) else 0,
          A.r.mean() if len(A) else np.nan, len(R), 100 * (R.r > 0).mean(), R.r.mean()))
T = pd.concat(out)
T.to_csv("LONDON_APLUS_2026_TRADES.csv", index=False)
rng = np.random.default_rng(20261027)
def summarise(label, d):
    if len(d) < 5: print(label, "too few"); return
    a, mm = d.r.to_numpy(), d.m.to_numpy()
    p = float((np.where(rng.random((20000, len(a))) < 0.5, a, mm).mean(axis=1) >= a.mean()).mean())
    print("%-52s n %3d  win %3.0f%%  mean %+.3f R  total %+.1f R  mirror %+.3f  random-side P %.3f" % (label, len(a), 100 * (a > 0).mean(), a.mean(), a.sum(), mm.mean(), p))
A = T[T.aplus]
print()
summarise("A+ Databento GC NQ ES SI, Jan-Sep 2026", A[A.src == "db"])
summarise("A+ gold only (GC), Jan-Sep 2026", A[A.sym == "GC"])
summarise("A+ new underlyings (M2K MBT MCL MET MYM), Aug-Sep", A[A.sym.isin(["M2K", "MBT", "MCL", "MET", "MYM"])])
summarise("A+ everything except duplicates (Databento + new)", A[(A.src == "db") | A.sym.isin(["M2K", "MBT", "MCL", "MET", "MYM"])])
summarise("B (hard rules only) Databento, Jan-Sep 2026", T[T.src == "db"])
