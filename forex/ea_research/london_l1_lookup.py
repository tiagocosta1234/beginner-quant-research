"""Descriptive: the one London-open rule that passed a pre-registered out-of-time check (L1: box 08:00-08:30 London, first touch until 11:00,
stop at the other side, hold to 17:00) on every MT5 broker symbol, by year. Rows from ORB11_ENTRY (TOUCH, hold). PYTHONPATH=. python forex/ea_research/london_l1_lookup.py"""
import numpy as np, pandas as pd
from forex.ea_research.breakouts import local_clock
from forex.ea_research.analog import mclass
T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet")
X = T[(T.sess == "LON") & (T.trig == "TOUCH")].copy()
lt = pd.to_datetime(X.t_entry, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London")
X = X[(lt.dt.hour < 11).to_numpy()]
X["yr"] = X.day.dt.year
g = X.groupby(["mkt", "yr"]).rh.mean().unstack()[[2022, 2023, 2024, 2025, 2026]]
n = X.groupby("mkt").size(); allm = X.groupby("mkt").rh.mean()
t = X.groupby("mkt").rh.apply(lambda s: s.mean() / s.std() * np.sqrt(len(s)))
S = g.assign(n=n, all=allm, t=t, pos_years=(g > 0).sum(axis=1), cls=lambda d: d.index.map(mclass)).sort_values("t", ascending=False)
pd.set_option("display.width", 250)
print(S.round(3).to_string())
print(f"\nsymbols positive 2022-26 overall: {int((S['all'] > 0).sum())} of {len(S)}; positive in all 5 years: {int((S.pos_years == 5).sum())}; by class mean R:", X.assign(cls=X.mkt.map(mclass)).groupby("cls").rh.mean().round(3).to_dict())
