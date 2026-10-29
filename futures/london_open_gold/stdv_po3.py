"""27 Oct 2026, descriptive (not registered). Replication of STDV_PO3.pine DEFAULTS on GC 1m (Databento) resampled to 5m, 2019-06..2026-09:
Asia range 20:00-00:00 New York, sweep inside 02:00-05:00, reclaim (close back inside) before 11:00 = entry at that close, stop = sweep extreme + 2 ticks,
target = STDV level projected from the OPPOSITE side of the range (k x range), min range 0.15 x prior daily ATR14, sweep depth <= 1 x range,
stop wins ties, trade followed to stop / 11:00 for the level-reach stats, cost 0.32 pt. Usage: python stdv_po3.py"""
import numpy as np, pandas as pd
g = pd.read_parquet("futures/data/databento/futures_GC.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
g.index = pd.DatetimeIndex(g.ts); g = g.drop(columns="ts"); g = g[~g.index.duplicated()].sort_index()
b = g.resample("5min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
ny = b.index.tz_convert("America/New_York")
b["tday"] = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
b["hm"] = ny.hour * 60 + ny.minute
ng = g.index.tz_convert("America/New_York"); tg = (ng + pd.Timedelta(hours=7)).normalize().tz_localize(None)
D = g.groupby(tg).agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
tr = pd.concat([D.high - D.low, (D.high - D.close.shift()).abs(), (D.low - D.close.shift()).abs()], axis=1).max(axis=1)
atr = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)
COST, TICK, KS = 0.32, 0.1, (1.0, 2.0, 2.5, 4.0)
rows = []; skipped = {"small": 0, "both": 0, "deep": 0, "noreclaim": 0, "nosweep": 0}
for td, d in b.groupby("tday"):
    if td not in atr.index or np.isnan(atr[td]): continue
    acc = d[d.hm >= 1200]; day = d[d.hm < 660]
    if len(acc) < 30 or len(day) < 60: continue
    rHi, rLo = acc.high.max(), acc.low.min(); rng = rHi - rLo
    if rng < 0.15 * atr[td]: skipped["small"] += 1; continue
    O, H, L, C, HM = (day[k].to_numpy() for k in ("open", "high", "low", "close", "hm"))
    st, short, ext = 1, None, None; res = None
    for i in range(len(day)):
        if HM[i] < 120: continue
        if st == 1:
            if HM[i] >= 300: skipped["nosweep"] += 1; break
            up, dn = H[i] > rHi, L[i] < rLo
            if up and dn: skipped["both"] += 1; break
            if not (up or dn): continue
            st, short, ext = 2, up, (H[i] if up else L[i])
        if st == 2:
            ext = max(ext, H[i]) if short else min(ext, L[i])
            if (ext - rHi if short else rLo - ext) > rng: skipped["deep"] += 1; break
            if (C[i] < rHi) if short else (C[i] > rLo):
                e = C[i]; sl = ext + 2 * TICK if short else ext - 2 * TICK; risk = abs(sl - e)
                lv = [(rLo - k * rng) if short else (rHi + k * rng) for k in KS]
                if risk <= 0 or not ((lv[0] < e) if short else (lv[0] > e)): break
                hit = [False] * 4; j = i + 1; stopped = False
                while j < len(day):
                    if HM[j] >= 660: break
                    if (H[j] >= sl) if short else (L[j] <= sl): stopped = True; break
                    for q in range(4):
                        if (L[j] <= lv[q]) if short else (H[j] >= lv[q]): hit[q] = True
                    j += 1
                exitpx = sl if stopped else (O[j] if j < len(day) else C[-1])
                res = dict(day=td, short=short, risk=risk, e=e, hit=hit, exitpx=exitpx, stopped=stopped, lv=lv, rng=rng)
                break
            continue
    if res: rows.append(res)
    elif st == 2: skipped["noreclaim"] += 1
R = pd.DataFrame(rows)
print("GC 5m %s..%s: %d trades (skipped: %s)" % (R.day.min().date(), R.day.max().date(), len(R), skipped))
print("shorts %d / longs %d" % (R.short.sum(), (~R.short).sum()))
H_ = np.array(R.hit.tolist())
print("reached before the stop: " + "  ".join("%.2f STDV %.1f%%" % (k, 100 * H_[:, q].mean()) for q, k in enumerate(KS)))
def netr(row, q):                          # target = STDV level q
    gross = abs(row.lv[q] - row.e) if row.hit[q] else ((row.e - row.exitpx) if row.short else (row.exitpx - row.e))
    return (gross - COST) / row.risk
for q, k in enumerate(KS):
    r = R.apply(lambda x: netr(x, q), axis=1)
    print("target %.1f STDV: wins %.1f%%, mean %+.3f R, total %+.1f R, median planned RR %.1f | by year %s" % (k, 100 * (r > 0).mean(), r.mean(), r.sum(),
          np.median([abs(x.lv[q] - x.e) / x.risk for x in R.itertuples()]), "  ".join("%d %+.0f" % (y, v.sum()) for y, v in r.groupby(R.day.dt.year))))
