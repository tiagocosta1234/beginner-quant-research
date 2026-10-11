"""How much risk can ManualDip take next to the v5 pair? (the trader 2026-10-11). v5 = pair x1.5, guard 1,500, news flat, no-hedge off.
Two views of a combined day: NAIVE = pair day + dip day (the dip outside the guard); GUARDED = the guard also closes the dip, so a combined
day below the pair's guarded floor is cut at min(pair day, -1,500 - 100 slip) when the dip pushes it there. Tester showed ~75% of the
simulated dip profit: dip P&L x 0.75.   python -m mt5broker.ea_research.dip_size_grid"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from mt5broker.ea_research import clean_boot_lib as L, pass70 as P, dip_addon as DA
from mt5broker.ea_research.daystop_under_2000 import news_flat
from mt5broker.ea_research.event_macro import server_s
from mt5broker.ea_batch.mt5_mc_config import CH

P.C0 = 560.0; HZ = {"30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
EV = np.array(sorted(server_s(r.date, 8, 30) if r.kind in ("CPI", "NFP") else server_s(r.date, 14, 0) for r in cal.itertuples() if r.kind in ("CPI", "NFP", "FOMC")))
bars = L.bars(); base = {}
for pool in ("MT5", "FT"):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * 1.5, lo), L.ea_trades(src, "xau5", CH["xau5"] * 1.5, lo)), EV, bars)
    r = L.C.simulate(bars, tr, lo, hi, None, 1500.0); base[pool] = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
print("dip risk | view    || P(pass) MIX 30 Nov / 22 Dec / 31 Jan | breach | days < -1,900 MT5 / FT | dip USD/yr (x0.75)")
for risk in (0.0, 500.0, 1000.0, 1500.0, 2000.0, 3000.0):
    if risk:
        DA.RISK = risk; T, bb = DA.trades(); T, D = DA.day_arrays(T, bb); D = D * 0.75; dip_yr = T.pl.sum() * 0.75 / 4.75
    for view in (("naive", "guarded") if risk else ("-",)):
        res, over = {}, []
        for pool in ("MT5", "FT"):
            S = base[pool]
            if risk:
                X = D.reindex(S["days"]).fillna(0.0); V, B, Hi = S["V"] + X.V.values, S["B"] + X.B.values, S["Hi"] + X.Hi.values
                if view == "guarded":
                    floor = -1600.0; cut = B < floor
                    V = np.where(cut, np.minimum(S["V"], floor), V); B = np.where(cut, np.minimum(S["B"], floor), B)
                S = dict(V=V, B=B, Hi=Hi, days=S["days"])
            w = np.minimum(S["V"], S["B"]); over.append(int((w < -1900).sum()))
            st, day = P.simulate([S] * len(P.MULTS), P.I12, 80); res[pool] = (st, day)
        cells = [f"{50*(np.mean((res['MT5'][0]==1)&(res['MT5'][1]<n))+np.mean((res['FT'][0]==1)&(res['FT'][1]<n))):.1f}%" for n in HZ.values()]
        br = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT"))
        print(f"{risk:7.0f} | {view:7s} || " + " / ".join(cells) + f" | {br:.1f}% | {over[0]} / {over[1]} | {dip_yr if risk else 0:,.0f}")
