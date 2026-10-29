"""(generated from london_aplus_2026.py) 27 Oct 2026, descriptive (not registered): the london_open_indicator.pine rule (A+ London 12 EMA, 1:1) on every 1-minute futures file on disk, 2026 only.
Rule = london_open_indicator.pine: 15m bias candle 07:45 London (close vs EMA12, EMA12 vs 4 candles earlier), first 1m candle opening 08:00-08:14 that freshly crosses the 1m EMA12 on the bias
side with body > biggest wick, entry at its close, stop beyond the last 6 candles + 1 tick, risk bounds 0.0375%..0.15% of price (= gold's 1.5..6 pt at ~4000), A+ = 2 of 3
(FVG in the last 60 min, Asia 00:00-07:00 sweep, 07:00 hourly candle vs its EMA12), 1R target, stop first on a tie, flat at 16:00 London.
Costs (points, round trip): GC/MGC 0.32, NQ/MNQ 1.1, ES/MES 0.74, MYM 4.4, SI 0.025 (earlier preregs); M2K, MCL, SIL, MBT, MET = 2 ticks + USD 1.20 / point value (assumption).
Data: Databento GC NQ ES SI (full 2026 to 25 Sep) and BrokerAPI 1m files (only 29 Jul..25 Sep 2026 exist). Usage: python london_aplus_2026.py"""
import numpy as np, pandas as pd

DB = "futures/data/databento/futures_%s.F_1m.parquet"
TX = "futures/data/merged_micros_2026-10-27/%s_1MIN_MERGED.csv"
SPEC = {  # name: (source, tick, cost points)
    "GC": ("db", 0.1, 0.32), "NQ": ("db", 0.25, 1.1), "ES": ("db", 0.25, 0.74), "SI": ("db", 0.005, 0.025),
    "MGC": ("tx", 0.1, 0.32), "MNQ": ("tx", 0.25, 1.1), "MES": ("tx", 0.25, 0.74), "MYM": ("tx", 1.0, 4.4),
    "M2K": ("tx", 0.1, 0.2 + 1.2 / 5), "MCL": ("tx", 0.01, 0.02 + 1.2 / 100), "SIL": ("tx", 0.005, 0.01 + 1.2 / 200),
    "MBT": ("tx", 5.0, 10 + 1.2 / 0.1), "MET": ("tx", 0.5, 1.0 + 1.2 / 0.1),
}
START = pd.Timestamp("2026-07-29")


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
        if src == "tx" and day < pd.Timestamp("2026-08-03"): continue   # 3 days EMA warm-up after the 29 Jul start                 # 3 days of EMA warm-up on the short BrokerAPI files
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
            res[lab] = sd * (out - entry) / risk
        rows.append(dict(day=day, t=df.index[sig], side='LONG' if bias>0 else 'SHORT', entry=entry, risk=risk, aplus=(int(c1) + int(c2) + int(c3)) >= 2, g=res['r'], gm=res['m']))
    return pd.DataFrame(rows), cand



# Realistic cost = all-in round-trip fee per contract (Broker micro schedule, MGC USD 1.92 and MNQ USD 1.22 from tie_check.py; the other micros assumed 1.22, MCL 1.62,
# SIL 1.92, MBT 2.50) / point value + ONE tick of slippage per round trip (market entry ~half a tick, stop-market exits ~1 tick on about half the trades, limit targets none).
PV = {"MGC": 10.0, "MNQ": 2.0, "MES": 5.0, "MYM": 0.5, "M2K": 5.0, "MCL": 100.0, "SIL": 1000.0, "MBT": 0.1}
FEE = {"MGC": 1.92, "MNQ": 1.22, "MES": 1.22, "MYM": 1.22, "M2K": 1.22, "MCL": 1.62, "SIL": 1.92, "MBT": 2.50}
TICK = {k: v[1] for k, v in SPEC.items()}
COST = {k: FEE[k] / PV[k] + TICK[k] for k in FEE}
rows = []
for n in COST:
    R, cand = run(n, "tx", TICK[n], 0.0); R["sym"] = n; R["cand"] = cand; rows.append(R)
T = pd.concat(rows); T.to_csv("MICROS_BACKTEST_TRADES.csv", index=False)
A = T[T.aplus].copy()
cp = A.sym.map(COST)
A["net"] = A.g - cp / A.risk; A["netm"] = A.gm - cp / A.risk; A["cpct"] = 100 * cp / A.risk
print("london_open_indicator.pine rule (A+ London 12 EMA, 1:1) on the merged 1m micro files, 3 Aug .. 27 Oct 2026. Realistic costs: Broker all-in fee + 1 tick per round trip.")
print("cost in points per round trip: " + "  ".join("%s %.3f" % (k, v) for k, v in COST.items()))
print("%-4s %5s | %4s %4s | %8s %9s | %s" % ("sym", "cands", "A+ n", "win%", "gross R", "net R", "cost as % of risk"))
for n, f in A.groupby("sym", sort=False):
    print("%-4s %5d | %4d %4.0f | %+8.3f %+9.3f | %.1f%%" % (n, T[T.sym == n].cand.iloc[0], len(f), 100 * (f.net > 0).mean(), f.g.mean(), f.net.mean(), f.cpct.mean()))
rng = np.random.default_rng(20261027)
def pooled(label, f):
    a, mm = f.net.to_numpy(), f.netm.to_numpy()
    p = float((np.where(rng.random((20000, len(a))) < 0.5, a, mm).mean(axis=1) >= a.mean()).mean())
    print("%-34s n %3d  win %3.0f%%  gross %+.3f  net %+.3f R  total %+.1f R  avg win %.2f avg loss %.2f  cost %.1f%% of risk | mirror %+.3f  random-side P %.3f" % (
        label, len(f), 100 * (f.net > 0).mean(), f.g.mean(), f.net.mean(), f.net.sum(), f.net[f.net > 0].mean(), f.net[f.net <= 0].mean(), f.cpct.mean(), f.netm.mean(), p))
print()
pooled("A+ all 8 micros", A)
pooled("A+ MGC MNQ MES MYM", A[A.sym.isin(["MGC", "MNQ", "MES", "MYM"])])
pooled("A+ MGC only", A[A.sym == "MGC"])
for m, g in A.groupby(A.day.dt.to_period("M")): print("  month %s: n %d, net %+.3f R" % (m, len(g), g.net.mean()))
