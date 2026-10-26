"""PREREG_WALKFORWARD_RECENCY.md: the frozen London first-15m indicator (Edge Lab 5 D1 buf0.5) with a "trade what has worked lately" filter.
Reuses edge_lab5.py's own functions (day_table, run_variant) so the trades are exactly that engine's. Usage (from edge_lab): python walkforward_recency.py"""
import numpy as np, pandas as pd

src = open("edge_lab5.py", encoding="utf-8").read().split("rng = np.random.default_rng(20261026)")[0]
exec(src)   # defines MARKETS, COMM, day_table, run_variant, ... (the part before the DEV-only run loop)

LOOKS = (20, 40, 60)
rows = []
for sym, (tick, pv) in MARKETS.items():
    df = pd.read_parquet(f"D:/finance/beginner-quant-research/futures/data/databento/futures_{sym}.F_1m.parquet").sort_values("ts").set_index("ts")
    df = df[["open", "high", "low", "close"]]
    days = day_table(df)
    for d, side, g, a, m in run_variant(days, tick, pv, "D1", 0.5, 1, {}):
        rows.append((sym, pd.Timestamp(d), a))
T = pd.DataFrame(rows, columns=["sym", "date", "r"]).sort_values(["sym", "date"]).reset_index(drop=True)
for n in LOOKS:
    T[f"trail{n}"] = T.groupby("sym")["r"].transform(lambda s: s.shift(1).rolling(n, min_periods=n).sum())
T = T[T.groupby("sym").cumcount() >= max(LOOKS)].copy()
T["yr"] = T.date.dt.year
rng = np.random.default_rng(20261026)
print("data: %s .. %s, %d market-days (%s)" % (T.date.min().date(), T.date.max().date(), len(T), ", ".join("%s %d" % (s, (T.sym == s).sum()) for s in MARKETS)))
print("baseline (always trade): mean net R %+.3f over %d trades; by year: %s" % (T.r.mean(), len(T),
      " ".join("%d %+.3f" % (y, g.r.mean()) for y, g in T.groupby("yr"))))
for n in LOOKS:
    on = T[f"trail{n}"] > 0
    obs = T.r[on].mean()
    # random filter: same number of on-days per market, random days
    draws = np.zeros(20000)
    for s in MARKETS:
        r = T.r[T.sym == s].to_numpy(); k = int(on[T.sym == s].sum())
        if k == 0: continue
        idx = np.argsort(rng.random((20000, len(r))), axis=1)[:, :k]
        draws += r[idx].sum(axis=1)
    p = float((draws / on.sum() >= obs).mean())
    yrs = T[on].groupby("yr").r.mean()
    pos = int((yrs.loc[[y for y in yrs.index if 2020 <= y <= 2026]] > 0).sum())
    ok = obs > 0 and p <= 0.0167 and pos >= 5
    print("\nR%d: trades %d of %d (%.0f%% of days on)  mean taken R %+.3f  (skipped %+.3f)  random-filter P %.4f  years>0 %d/7  -> %s" % (
        n, on.sum(), len(T), 100 * on.mean(), obs, T.r[~on].mean(), p, pos, "ADAPTATION WORKS" if ok else "NOT SHOWN"))
    print("    by year: " + " ".join("%d %+.3f (n %d)" % (y, g.r[on.loc[g.index]].mean(), on.loc[g.index].sum()) for y, g in T.groupby("yr")))
    print("    by market: " + " ".join("%s %+.3f (n %d, base %+.3f)" % (s, T.r[on & (T.sym == s)].mean(), (on & (T.sym == s)).sum(), T.r[T.sym == s].mean()) for s in MARKETS))
