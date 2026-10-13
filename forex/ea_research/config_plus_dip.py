"""Chosen config (x1.5, no-hedge off, guard 1,500, news flat) with and without the DA2 index dip add-on at 0.5% / 1.0% risk a signal day.
   Planning simulation, pass70 rules, start +560 (the trader 2026-10-11, for the 21:00 decision).   python -m forex.ea_research.config_plus_dip"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L, pass70 as P, dip_addon as DA
from forex.ea_research.daystop_under_2000 import news_flat
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

P.C0 = 560.0; HZ = {"30 Oct": 15, "30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
EV = np.array(sorted(server_s(r.date, 8, 30) if r.kind in ("CPI", "NFP") else server_s(r.date, 14, 0) for r in cal.itertuples() if r.kind in ("CPI", "NFP", "FOMC")))
base = {}
for pool in ("MT5", "FT"):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); bars = L.bars()
    tr = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * 1.5, lo), L.ea_trades(src, "xau5", CH["xau5"] * 1.5, lo)), EV, bars)
    r = L.C.simulate(bars, tr, lo, hi, None, 1500.0); base[pool] = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
for risk in (0.0, 500.0, 1000.0):
    res = {}; worst = []
    for pool in ("MT5", "FT"):
        S = base[pool]
        if risk:
            DA.RISK = risk; T, bars = DA.trades(); T, D = DA.day_arrays(T, bars); S = DA.combine(S, D)
        w = np.minimum(S["V"], S["B"]); worst.append(f"{pool} worst day {w.min():,.0f}, days < -1,900 {(w < -1900).sum()}")
        st, day = P.simulate([S] * len(P.MULTS), P.I12, 80); res[pool] = (st, day)
    cells = [f"{h} {50*(np.mean((res['MT5'][0]==1)&(res['MT5'][1]<n))+np.mean((res['FT'][0]==1)&(res['FT'][1]<n))):.1f}%" for h, n in HZ.items()]
    br = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT"))
    print(f"dip add-on risk {risk:5.0f}: " + " | ".join(cells) + f" | breach {br:.1f}% | " + " | ".join(worst))
