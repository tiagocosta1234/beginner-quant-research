"""PREREG_PO3_SEARCH: 32-cell search of the claude.pine PO3 rule (Asia range sweep + reclaim) on GC, NQ, ES, SI, DEV < 2023 / TEST >= 2023, one look.
Usage: python po3_search.py"""
import itertools, numpy as np, pandas as pd

MK = {"GC": (0.10, 0.32), "SI": (0.005, 0.025), "NQ": (0.25, 1.1), "ES": (0.25, 0.74)}
SWP_ENDS, STOPS, TGTS, TRENDS = (300, 480), ("ext", "wide"), (0.5, 1.0, 1.5, 2.0), (False, True)
END = 660


def sim(O, H, L, C, start, side, e, sd, td, cost):
    sl = e - side * sd; tp = e + side * td
    for j in range(start, len(O)):
        if j >= END_IDX: x = O[j]; break
        if (L[j] <= sl) if side > 0 else (H[j] >= sl): x = sl; break
        if (H[j] >= tp) if side > 0 else (L[j] <= tp): x = tp; break
    else: x = C[-1]
    return (side * (x - e) - cost) / sd


trades = []
for sym, (tick, cost) in MK.items():
    g = pd.read_parquet(f"D:/finance/beginner-quant-research/futures/data/databento/futures_{sym}.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
    g.index = pd.DatetimeIndex(g.ts); g = g.drop(columns="ts"); g = g[~g.index.duplicated()].sort_index()
    b = g.resample("5min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    ny = b.index.tz_convert("America/New_York")
    b["tday"] = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None); b["hm"] = ny.hour * 60 + ny.minute
    ng = g.index.tz_convert("America/New_York"); tg = (ng + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    D = g.groupby(tg).agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    tr = pd.concat([D.high - D.low, (D.high - D.close.shift()).abs(), (D.low - D.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1); up = (D.close > D.close.rolling(20).mean()).shift(1)
    for td, d in b.groupby("tday"):
        if td not in atr.index or np.isnan(atr[td]) or pd.isna(up.get(td, np.nan)): continue
        acc = d[d.hm >= 1200]; day = d[d.hm < END]
        if len(acc) < 30 or len(day) < 60: continue
        rHi, rLo = acc.high.max(), acc.low.min(); rng = rHi - rLo
        if rng < 0.15 * atr[td]: continue
        O, H, L, C, HM = (day[k].to_numpy() for k in ("open", "high", "low", "close", "hm"))
        END_IDX = int(np.searchsorted(HM, END)) if (HM >= END).any() else len(HM)
        END_IDX = len(HM) if END_IDX == 0 else END_IDX
        for swp_end in SWP_ENDS:
            st, short, ext = 1, None, None
            for i in range(len(day)):
                if HM[i] < 120: continue
                if st == 1:
                    if HM[i] >= swp_end: break
                    u, dn = H[i] > rHi, L[i] < rLo
                    if u and dn: break
                    if not (u or dn): continue
                    st, short, ext = 2, u, (H[i] if u else L[i])
                ext = max(ext, H[i]) if short else min(ext, L[i])
                if (ext - rHi if short else rLo - ext) > rng: break
                if (C[i] < rHi) if short else (C[i] > rLo):
                    e = C[i]; side = -1 if short else 1
                    for stp in STOPS:
                        far = ext + 2 * tick + (0.25 * rng if stp == "wide" else 0) if short else ext - 2 * tick - (0.25 * rng if stp == "wide" else 0)
                        sd = abs(far - e)
                        if sd <= 0: continue
                        for m in TGTS:
                            r = sim(O, H, L, C, i + 1, side, e, sd, m * sd, cost); rm = sim(O, H, L, C, i + 1, -side, e, sd, m * sd, cost)
                            for tr_ in TRENDS:
                                if tr_ and ((side > 0) != bool(up[td])): continue
                                trades.append((sym, td, swp_end, stp, m, tr_, r, rm))
                    break
T = pd.DataFrame(trades, columns=["sym", "day", "swp", "stop", "tgt", "trend", "r", "rm"])
T["dev"] = T.day < "2023-01-01"
T.to_csv("PO3_SEARCH_TRADES.csv", index=False)
cells = T.groupby(["swp", "stop", "tgt", "trend"])
rows = []
for k, f in cells:
    a, t = f[f.dev], f[~f.dev]
    rows.append((k, len(a), a.r.mean(), len(t), t.r.mean() if len(t) else np.nan))
C_ = pd.DataFrame(rows, columns=["cell", "nDEV", "devR", "nTEST", "testR"])
C_ = C_[C_.nDEV >= 200].sort_values("devR", ascending=False)
print("cells with >= 200 DEV trades: %d of 32 | DEV/TEST correlation of cell means %.2f" % (len(C_), C_.devR.corr(C_.testR)))
print("top 5 on DEV -> TEST:")
for r in C_.head(5).itertuples(): print("  %-34s DEV %+.3f R (%d) -> TEST %+.3f R (%d)" % (r.cell, r.devR, r.nDEV, r.testR, r.nTEST))
best = C_.iloc[0].cell
f = T[(T.swp == best[0]) & (T.stop == best[1]) & (T.tgt == best[2]) & (T.trend == best[3]) & ~T.dev]
rng_ = np.random.default_rng(20261027); n = len(f); real = f.r.sum(); beat = 0; N = 20000
for _ in range(N // 1000):
    pick = rng_.integers(0, 2, size=(1000, n)).astype(bool)
    beat += (np.where(pick, f.r.to_numpy(), f.rm.to_numpy()).sum(axis=1) >= real).sum()
P = (beat + 1) / (N + 1); per = f.groupby("sym").r.agg(["mean", "size"])
print("CHOSEN %s -> TEST n %d, wins %.1f%%, mean %+.3f R, total %+.1f R, mirror mean %+.3f, random-side P %.4f" % (best, n, 100 * (f.r > 0).mean(), f.r.mean(), real, f.rm.mean(), P))
print("  per market: " + " | ".join("%s %+.3f (%d)" % (s, v["mean"], v["size"]) for s, v in per.iterrows()))
print("  by year: " + "  ".join("%d %+.1f" % (y, v.sum()) for y, v in f.groupby(f.day.dt.year).r))
ok = f.r.mean() > 0 and P <= 0.05 and (per["mean"] > 0).sum() >= 3 and n >= 150
print("VERDICT:", "SHOWN" if ok else "NOT SHOWN (markets positive %d/4)" % (per["mean"] > 0).sum())
