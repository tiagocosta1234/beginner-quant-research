"""Descriptive: the L1 London-open rule traded on ALL 46 symbols at once (and on the 7 yen pairs chosen out of time), daily book and MT5 broker cycles.
   PYTHONPATH=. python forex/ea_research/london_l1_book.py"""
import numpy as np, pandas as pd
from forex.ea_research.best3m_cycle import cycle
from forex.ea_research.analog import mclass
T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet")
X = T[(T.sess == "LON") & (T.trig == "TOUCH")].copy()
lt = pd.to_datetime(X.t_entry, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London")
X = X[(lt.dt.hour < 11).to_numpy() & (X.day <= "2026-10-02").to_numpy()]
YEN = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY"]
books = {"all 46 symbols": X, "no crypto / energy (38)": X[~X.mkt.map(mclass).isin(["crypto", "energy"])], "7 yen pairs (picked out of time)": X[X.mkt.isin(YEN)]}
starts_b = pd.bdate_range("2022-03-01", "2026-08-31")[::5]
for name, B in books.items():
    d = B.groupby("day").rh.agg(net="sum", n="size"); d["neg"] = B.rh.clip(upper=0).groupby(B.day).sum()
    d = d[d.index >= "2022-01-01"]
    yr = d.net.groupby(d.index.year).sum().round(0).to_dict(); tr = B.groupby(B.day.dt.year).rh.mean().round(3).to_dict()
    sh = d.net.mean() / d.net.std() * np.sqrt(252)
    print(f"\n{name}: {len(B)} trades, {d.n.mean():.1f} a day, {B.rh.mean():+.3f} R a trade, {d.net.mean():+.2f} R a day, Sharpe {sh:+.2f}; worst day {d.net.min():+.1f} R; R a trade by year {tr}; R by year {yr}")
    st = np.unique(np.searchsorted(d.index, starts_b))
    for X_ in (50, 100, 200):
        res = [cycle(d, i, X_, False) for i in st]; s = np.array([r[0] for r in res]); n = np.array([r[1] for r in res])
        print(f"   ${X_} a trade ({len(st)} MT5 broker cycles, optimistic daily line): pass in 30 d {np.mean((s == 1) & (n <= 30)):.1%}, in 60 d {np.mean((s == 1) & (n <= 60)):.1%}, ever {np.mean(s == 1):.1%} | breach ever {np.mean(s == 2):.1%}")
