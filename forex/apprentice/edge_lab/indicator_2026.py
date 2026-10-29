"""DESCRIPTIVE (the trader 26 Oct: "backtest our indicator through the 4 symbols in 2026"): the frozen London first-15m indicator
(Edge Lab 5 D1, buffer 0.5, 1:1) on MGC / MNQ / MES (Databento GC / NQ / ES 1m, micro costs) and MYM (MT5 US30 1m mid, MYM costs), 2026 only.
2026 was already seen in aggregate by earlier tests today, so this has no pass / fail bar. Usage (from edge_lab): python indicator_2026.py"""
import numpy as np, pandas as pd

src = open("edge_lab5.py", encoding="utf-8").read().split("rng = np.random.default_rng(20261026)")[0]
exec(src)
START = pd.Timestamp("2026-01-01")
SPEC = {"MGC": ("GC", 0.1, 10.0), "MNQ": ("NQ", 0.25, 2.0), "MES": ("ES", 0.25, 5.0), "MYM": ("DOW", 1.0, 0.5)}


def load(src_sym):
    if src_sym == "DOW":
        raw = pd.read_parquet("forex/data_mt5/DOW_M1_rates.parquet").drop_duplicates("t").sort_values("t")
        raw = raw[(raw.bo > 0) & (raw.ao >= raw.bo)]
        utc = pd.to_datetime(raw.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
        df = pd.DataFrame({k: ((raw["b" + k[0]] + raw["a" + k[0]]) / 2).to_numpy() for k in ("open", "high", "low", "close")}, index=utc.to_numpy())
        df = df[~df.index.isna()]; df.index = pd.DatetimeIndex(df.index).tz_convert("UTC")
    else:
        df = pd.read_parquet(f"futures/data/databento/futures_{src_sym}.F_1m.parquet").sort_values("ts").set_index("ts")
        df = df[["open", "high", "low", "close"]]
    df = df[~df.index.duplicated()].sort_index()
    return df[df.index >= (START - pd.Timedelta(days=60)).tz_localize("UTC")]   # 60 days of lead-in for ATR14 / SMA20


rng = np.random.default_rng(20261026)
allrows = []
print("%-4s %4s %5s %9s %8s %8s %9s  %s" % ("sym", "n", "win", "mean R", "total R", "max DD", "P(side)", "first .. last"))
for name, (s, tick, pv) in SPEC.items():
    rows = [r for r in run_variant(day_table(load(s)), tick, pv, "D1", 0.5, 1, {}) if pd.Timestamp(r[0]) >= START]
    a = np.array([r[3] for r in rows]); m = np.array([r[4] for r in rows])
    p = float((np.where(rng.random((20000, len(a))) < 0.5, a, m).mean(axis=1) >= a.mean()).mean())
    cum = np.cumsum(a); dd = (cum - np.maximum.accumulate(np.r_[0, cum][1:])).min()
    print("%-4s %4d %4.0f%% %+9.3f %+8.1f %8.1f %9.3f  %s .. %s" % (name, len(a), 100 * (a > 0).mean(), a.mean(), a.sum(), dd, p,
          pd.Timestamp(rows[0][0]).date(), pd.Timestamp(rows[-1][0]).date()))
    allrows += [(name, pd.Timestamp(r[0]), r[3]) for r in rows]
D = pd.DataFrame(allrows, columns=["sym", "date", "r"])
D["mon"] = D.date.dt.to_period("M")
print("\nby month (mean net R; n):")
piv = D.pivot_table(index="mon", columns="sym", values="r", aggfunc="mean")
cnt = D.pivot_table(index="mon", columns="sym", values="r", aggfunc="count")
for mon in piv.index:
    print("  %s  " % mon + "  ".join("%s %+.2f (%d)" % (c, piv.loc[mon, c], cnt.loc[mon, c]) for c in SPEC if c in piv.columns and not np.isnan(piv.loc[mon, c])))
day = D[D.date <= "2026-09-25"].groupby("date").r.mean()
print("\nportfolio (the forward test's metric: mean of the 4 symbols each day, to 25 Sep): days %d, mean daily R %+.3f, total %+.1f, best month %s, worst month %s" % (
    len(day), day.mean(), day.sum(), day.groupby(day.index.to_period("M")).mean().idxmax(), day.groupby(day.index.to_period("M")).mean().idxmin()))
print("portfolio by month: " + " ".join("%s %+.3f" % (k, v) for k, v in day.groupby(day.index.to_period("M")).mean().items()))
