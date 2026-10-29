"""PREREG_FUNDAMENTALS_GOLD.md: macro biases (real yields, dollar, both; event days) on the frozen London first-15m indicator, GC.
Reuses edge_lab5.py's own functions so the trades are exactly that engine's. Usage (from edge_lab): python fundamentals_gold.py"""
import numpy as np, pandas as pd

src = open("edge_lab5.py", encoding="utf-8").read().split("rng = np.random.default_rng(20261026)")[0]
exec(src)

tick, pv = MARKETS["GC"]
df = pd.read_parquet("futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts").set_index("ts")
T = pd.DataFrame(run_variant(day_table(df[["open", "high", "low", "close"]]), tick, pv, "D1", 0.5, 1, {}), columns=["date", "side", "g", "a", "m"])
T["date"] = pd.to_datetime(T.date).dt.normalize(); T = T[T.date >= "2019-09-01"].reset_index(drop=True); T["yr"] = T.date.dt.year

ry = pd.read_csv("data/data_macro/DFII10.csv", na_values=["."]).dropna()
ry["d"] = pd.to_datetime(ry.observation_date); ry = ry.set_index("d")["DFII10"].astype(float)
eu = pd.read_csv("futures/data/daily/6E=F_yahoo_daily.csv")
eu["d"] = pd.to_datetime(eu.date); eu = eu.set_index("d")["close"].astype(float)
ev = pd.read_csv("data/data_macro/event_calendar.csv"); evd = set(pd.to_datetime(ev.date).dt.normalize())


def asof_prior(s, d):
    x = s[s.index < d]
    return x


def f1(d):
    x = asof_prior(ry, d).tail(6)
    if len(x) < 6: return 0
    ch = x.iloc[-1] - x.iloc[0]
    return 1 if ch < 0 else -1 if ch > 0 else 0


def f2(d):
    x = asof_prior(eu, d).tail(20)
    if len(x) < 20: return 0
    return 1 if x.iloc[-1] > x.mean() else -1


T["F1"] = [f1(d) for d in T.date]; T["F2"] = [f2(d) for d in T.date]
T["F3"] = np.where(T.F1 == T.F2, T.F1, 0)
rng = np.random.default_rng(20261026)
print("GC days %d (%s .. %s); indicator alone: mean net R %+.3f; by year %s" % (len(T), T.date.min().date(), T.date.max().date(), T.a.mean(),
      " ".join("%d %+.3f" % (y, g.a.mean()) for y, g in T.groupby("yr"))))


def report(name, r, yrs, pool_years, p):
    pos = int((yrs.loc[[y for y in yrs.index if y in pool_years]] > 0).sum()); need = 5 if len(pool_years) == 7 else 3
    ok = r.mean() > 0 and p <= 0.007 and pos >= need and len(r) >= 300
    print("%-26s n %4d  mean net R %+.3f  P %.4f  years>0 %d/%d  2026 %+.3f  -> %s" % (name, len(r), r.mean(), p, pos, len(pool_years),
          yrs.get(2026, np.nan), "FUNDAMENTALS HELP" if ok else "NOT SHOWN"))
    print("    by year: " + " ".join("%d %+.3f" % (y, v) for y, v in yrs.items()))


Y7 = list(range(2020, 2027))
for F in ("F1", "F2", "F3"):
    on = (T[F] != 0) & (T[F] == T.side)                     # filter: indicator side agrees with the bias
    r = T.a[on]; k = int(on.sum())
    draws = T.a.to_numpy()[np.argsort(rng.random((20000, len(T))), axis=1)[:, :k]].mean(axis=1)
    report(F + " filter", r, T[on].groupby("yr").a.mean(), Y7, float((draws >= r.mean()).mean()))
    has = T[F] != 0                                           # override: trade the bias side
    rr = np.where(T[F] == T.side, T.a, T.m)[has]
    flips = np.where(rng.random((20000, has.sum())) < 0.5, T.a[has].to_numpy(), T.m[has].to_numpy()).mean(axis=1)
    yo = pd.Series(rr, index=T.yr[has]).groupby(level=0).mean()
    report(F + " override", pd.Series(rr), yo, Y7, float((flips >= rr.mean()).mean()))
E = T[T.yr >= 2022]
on = ~E.date.isin(evd); r = E.a[on]; k = int(on.sum())
draws = E.a.to_numpy()[np.argsort(rng.random((20000, len(E))), axis=1)[:, :k]].mean(axis=1)
report("F4 skip event days", r, E[on].groupby("yr").a.mean(), list(range(2022, 2027)), float((draws >= r.mean()).mean()))
print("    event days themselves (2022+): n %d mean net R %+.3f" % ((~on).sum(), E.a[~on].mean()))
