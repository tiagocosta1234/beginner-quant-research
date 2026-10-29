"""the trader 27 Oct 2026: "this strategy on the 5 minute on MGC has returned 8.22 R in 30 calendar days" (london_open_indicator.pine / SESSION_OPEN_5M_1TO1.pine
dashboard). Bar-for-bar replication of the indicator's DEFAULTS on GC 1m (Databento, = MGC price) 2019-06..2026-09 resampled to 5m:
London 08:00 London + New York 09:30 New York setup candle (5m), Candle direction (doji -> prior-day close above SMA20), r = max(|close -
extreme| + 0.5 x candle range, 0.03 x prior-day ATR14), entry at the candle close, 1R target, exit at TP / SL (same bar = SL) / the open
of the first bar at or after open + 60 min, cost 0.32 pt round trip (the indicator's MGC auto cost), one loss ends the day.
Descriptive, not a registered test. Usage: python open5m_history.py"""
import numpy as np, pandas as pd

g = pd.read_parquet("futures/data/databento/futures_GC.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
g.index = pd.DatetimeIndex(g.ts); g = g.drop(columns="ts"); g = g[~g.index.duplicated()].sort_index()
b5 = g.resample("5min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
# daily bars by CME trading day (17:00 New York roll) for ATR14 / SMA20 of PRIOR days
ny = g.index.tz_convert("America/New_York")
tday = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)       # 17:00 NY -> next trading day
D = g.groupby(tday).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
tr = pd.concat([D.high - D.low, (D.high - D.close.shift()).abs(), (D.low - D.close.shift()).abs()], axis=1).max(axis=1)
D["atr_prev"] = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)     # RMA like ta.atr, prior day only
D["trend_up"] = (D.close.shift(1) > D.close.rolling(20).mean().shift(1))
COST, TICK = 0.32, 0.1
b5["ny"] = b5.index.tz_convert("America/New_York").tz_localize(None); b5["ldn"] = b5.index.tz_convert("Europe/London").tz_localize(None)
b5["tday"] = (b5.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize().tz_localize(None)
idx_by_time = {t: i for i, t in enumerate(b5.index)}
O, H, L, C = (b5[k].to_numpy() for k in ("open", "high", "low", "close")); T = b5.index


def trade(i, end_ts, atr, trend):
    o, h, l, c = O[i], H[i], L[i], C[i]
    up, dn = c > o, c < o; long_ = up or (not dn and trend)
    r = max(abs(c - (l if long_ else h)) + 0.5 * (h - l), 0.03 * atr)
    sl = round((c - r if long_ else c + r) / TICK) * TICK; tp = round((c + r if long_ else c - r) / TICK) * TICK
    j = i + 1
    while j < len(T):
        if T[j] >= end_ts: x = O[j]; break
        if (L[j] <= sl) if long_ else (H[j] >= sl): x = sl; break
        if (H[j] >= tp) if long_ else (L[j] <= tp): x = tp; break
        j += 1
    else: return None
    return ((x - c) if long_ else (c - x)) / r - COST / r, long_


rows = []
for tdy, dd in b5.groupby("tday"):
    if tdy not in D.index or pd.isna(D.at[tdy, "atr_prev"]): continue
    atr, trend = D.at[tdy, "atr_prev"], bool(D.at[tdy, "trend_up"])
    res_lon = None
    for ses, col, hhmm, tz in (("London", "ldn", "08:00", "Europe/London"), ("New York", "ny", "09:30", "America/New_York")):
        m = dd[dd[col].dt.strftime("%H:%M") == hhmm]
        if not len(m): continue
        if ses == "New York" and res_lon is not None and res_lon <= 0: rows.append((tdy, ses, np.nan, "skipped")); continue
        t0 = m.index[0]; end_ts = t0 + pd.Timedelta(minutes=60)
        out = trade(idx_by_time[t0], end_ts, atr, trend)
        if out is None: continue
        rows.append((tdy, ses, out[0], "L" if out[1] else "S"))
        if ses == "London": res_lon = out[0]
R = pd.DataFrame(rows, columns=["day", "ses", "R", "side"]); T_ = R.dropna(subset=["R"])
T_.to_csv("OPEN5M_HISTORY_TRADES.csv", index=False)
print("GC/MGC 5m, %s .. %s: %d trades (%d London, %d New York, %d NY skipped after a London loss)" % (T_.day.min().date(), T_.day.max().date(), len(T_),
      (T_.ses == "London").sum(), (T_.ses == "New York").sum(), (R.side == "skipped").sum()))
print("ALL: wins %.1f%%, mean %+.3f R a trade, total %+.1f R" % (100 * (T_.R > 0).mean(), T_.R.mean(), T_.R.sum()))
for s in ("London", "New York"):
    x = T_[T_.ses == s].R; print("  %-8s n %4d, wins %.1f%%, mean %+.3f R" % (s, len(x), 100 * (x > 0).mean(), x.mean()))
print("by year:", "  ".join("%d %+.1fR (%d)" % (y, v.sum(), len(v)) for y, v in T_.groupby(T_.day.dt.year).R))
# every 30-calendar-day window
s = T_.set_index("day").R.groupby(level=0).sum(); s = s.reindex(pd.date_range(s.index.min(), s.index.max()), fill_value=0.0)
w = s.rolling(30).sum().dropna()
print("30-calendar-day windows: %d | median %+.1f R | best %+.1f R | worst %+.1f R | share >= +8.22 R: %.1f%% | share < 0: %.1f%%" % (
      len(w), w.median(), w.max(), w.min(), 100 * (w >= 8.22).mean(), 100 * (w < 0).mean()))
last = T_[T_.day > T_.day.max() - pd.Timedelta(days=30)]
print("last 30 days of my data (to %s): %d trades, %+.2f R" % (T_.day.max().date(), len(last), last.R.sum()))
