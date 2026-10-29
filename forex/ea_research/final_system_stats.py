"""Full statistics of the FINAL system to be deployed (the trader 2026-10-11 ~20:30): ManualSDB 0.18 + XAU5 0.06 (x1.5), no-hedge OFF,
guard day stop 1,500, news flat on CPI only, ManualDip 500 USD day risk (x0.75 of the simulated P&L, as the real-tick tester showed).
Pools: MT5 = last 12 months on MT5 broker real ticks, FT = 2022-26 (MT5 broker trades at MT5 broker prices). pass70 rules, start +560 counted on 2026-10-12.
   python -m forex.ea_research.final_system_stats"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, clean_boot_lib as L, dip_addon as DA
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

cal = pd.read_csv("data/data_macro/event_calendar.csv")
G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
P.C0 = 560.0; GUARD = 1500.0
def pf(x): return x[x > 0].sum() / -x[x < 0].sum()
DA.RISK = 500.0; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75
res = {}
for pool in ("MT5", "FT"):
    src, a, b = L.POOLS[pool]; lo = L.day(a)
    S = G.add_dip(G.pair_series(pool, 1.5, 1.5, GUARD), Dd, GUARD)
    v = pd.Series(S["V"], index=pd.to_datetime(S["days"] * 86400, unit="s")); w = np.minimum(S["V"], S["B"]); m = v.resample("ME").sum(); eq = v.cumsum()
    nt = {leg: len(L.ea_trades(src, leg, CH[leg] * 1.5, lo)["pl"]) for leg in ("sdb", "xau5")}
    td = T[(T.date >= a) & (T.date <= b)]
    print(f"\n=== {pool} ({a} .. {b}) ===")
    print(f"days {len(v)} | mean/day {v.mean():.0f} USD | mean/month {m.mean():,.0f} (median {m.median():,.0f}; best {m.max():,.0f}; worst {m.min():,.0f}) | months positive {100*(m > 0).mean():.0f}%")
    print(f"daily PF {pf(v):.2f} | winning days {100*(v > 0).mean():.0f}% of days, losing {100*(v < 0).mean():.0f}% | trades: SDB {nt['sdb']}, XAU5 {nt['xau5']}, ManualDip {len(td)}")
    print(f"worst day {w.min():,.0f} | days <= -1,500 {(w <= -1500).sum()} | days <= -1,900 {(w <= -1900).sum()} | days <= -2,000 {(w <= -2000).sum()} | best day {v.max():,.0f} | max drawdown {(eq.cummax() - eq).max():,.0f}")
    if pool == "FT": print("by year (USD):", v.groupby(v.index.year).sum().round(-2).astype(int).to_dict())
    st, day = P.simulate([S] * len(P.MULTS), P.I12, 120); res[pool] = (st, day)
print("\n=== test from +560 counted on Mon 2026-10-12 ===")
for h, n in {"30 Oct": 15, "13 Nov": 25, "30 Nov": 36, "15 Dec": 47, "22 Dec": 52, "31 Jan": 79, "end Mar": 120}.items():
    e = np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n)); f = np.mean((res["FT"][0] == 1) & (res["FT"][1] < n))
    be = np.mean((res["MT5"][0] == 2) & (res["MT5"][1] < n)); bf = np.mean((res["FT"][0] == 2) & (res["FT"][1] < n))
    print(f"by {h:7s}: P(pass) MIX {50*(e+f):5.1f}%  (gold trending {100*e:4.0f}% / 2022-26 {100*f:4.0f}%) | breach {50*(be+bf):.1f}%")
dd = np.concatenate([np.where(res[p][0] == 1, res[p][1] + 1, 9999) for p in ("MT5", "FT")]); med = int(np.median(dd))
print(f"median pass: business day {med} = {np.busday_offset('2026-10-12', med - 1, roll='forward')} | still open after 120 bd: {100*np.mean(dd == 9999):.0f}%")
