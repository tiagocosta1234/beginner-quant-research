"""Can the -500 clip be made real? Per-leg intraday day-loss stop on the gold pair (x1.2 lots, MT5 broker ticks scaled to MT5, 2022-26), the trader 2026-10-11.
   python -m forex.ea_research.leg_daystop"""
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L
from forex.ea_batch.mt5_mc_config import CH
from forex.ea_research.book_variants import eta
from forex.ea_research.eval_cycles_all import cycles

lo, hi = L.day("2022-01-01"), L.day("2026-09-30"); B = L.bars(); legs = {}
for leg in ("sdb", "xau5"):
    tr = L.ea_trades("mt5broker", leg, CH[leg] * 1.2, lo)
    for stop in (None, 300, 500, 800, 1200):
        r = L.C.simulate(B, tr, lo, hi, None, stop); legs[(leg, stop)] = pd.Series(r["V"], index=pd.to_datetime(r["days"] * 86400, unit="s"))
for stop in (None, 300, 500, 800, 1200):
    p = legs[("sdb", stop)].add(legs[("xau5", stop)], fill_value=0.0); y = p.groupby(p.index.year).sum().round(-2).astype(int).to_dict()
    h = p[p.index >= "2026-01-01"]; C = cycles(p); eq = p.cumsum()
    print(f"stop per leg {str(stop):>5s}: by year {y} | max DD {(eq.cummax() - eq).max():,.0f} | evals 2022-26 pass/fail {(C.res=='pass').sum()}/{(C.res=='fail').sum()} | ETA 2026 regime 30Out/30Nov/22Dez {eta(h)[0]} | 2022-26 regime {eta(p)[0]}")
