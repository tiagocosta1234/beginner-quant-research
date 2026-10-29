"""Average monthly return, in % of a 100,000 USD MT5 Pro account, of each strategy ALONE as sized in the installed system (and S3 at 0.2 / 0.3 NQ), guard day stop 1,500, CPI news flat on the gold legs.
the trader 2026-10-12. Raw = P&L; counted = profit capped at +2,000 a day (what MT5 broker counts), losses in full.   python -m forex.ea_research.strategies_monthly"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import nq3 as N, combo_grid as G, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
cx = N.Ctx(); T3 = pd.DataFrame(N.s3(cx)); DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75
GUARD = 1500.0; ACC = 100000.0
rows = []


def add(name, pool, S):
    d = pd.to_datetime(np.asarray(S["days"]) * 86400, unit="s"); V = pd.Series(np.asarray(S["V"], float), index=d); mo = V.groupby(V.index.to_period("M")).sum(); co = np.minimum(V, 2000.0).groupby(V.index.to_period("M")).sum()
    rows.append(dict(strategy=name, window="last 12 months (real ticks)" if pool == "MT5" else "2022-2026", raw_pct_mo=100 * mo.mean() / ACC, counted_pct_mo=100 * co.mean() / ACC, median_pct=100 * mo.median() / ACC, best=100 * mo.max() / ACC, worst=100 * mo.min() / ACC, pos_months=100 * (mo > 0).mean(), usd_mo=mo.mean()))


for pool in ("MT5", "FT"):
    zero = G.pair_series(pool, 0, 0, GUARD)
    add("ManualSDB 0.18 lot", pool, G.pair_series(pool, 1.5, 0, GUARD)); add("XAU5 0.06 lot", pool, G.pair_series(pool, 0, 1.5, GUARD)); add("ManualDip 500 USD/day", pool, G.add_dip(zero, Dd, GUARD))
    add("SDB + XAU5 (the pair)", pool, G.pair_series(pool, 1.5, 1.5, GUARD)); add("INSTALLED: pair + ManualDip", pool, G.add_dip(G.pair_series(pool, 1.5, 1.5, GUARD), Dd, GUARD))
    for nq in (0.2, 0.3): add(f"S3 overnight ORB {nq} NQ", pool, G.add_dip(zero, N.daily_series(T3, N.PT * nq), GUARD))
R = pd.DataFrame(rows)
for w, g in R.groupby("window"):
    print(f"\n=== {w}: average per month, % of 100,000 USD (guard 1,500) ==="); print(g.drop(columns="window").round(2).to_string(index=False))
open(os.path.join(os.path.dirname(__file__), "STRATEGIES_MONTHLY_OUTPUT.txt"), "w").write(R.round(2).to_string(index=False))
