"""Would XAU5 alone (best size, weekend flat, guard 2,000) pass an MT5 broker account more often than the installed system (pair x1.5 + ManualDip 500, guard 1,500)? the trader 2026-10-12.
Same pass70 simulator, MIX of the MT5 12-month and FT 2022-26 pools, news flat CPI, for this account (+560 counted on 12 Oct) and for a fresh one.   python -m forex.ea_research.xau5_vs_installed"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI")); G.EV = EV
DA.RISK = 500.0; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75


def xau5(pool, R, guard, wk=True):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); t = {k: np.array(v, copy=True) for k, v in L.ea_trades(src, "xau5", CH["xau5"], lo).items()}
    k = R / np.median(np.abs(t["pl"][t["pl"] < 0]))
    if wk: t = L.flatten_weekends(t)
    t = G.news_flat(t, EV, G.bars); t = {kk: np.array(v, copy=True) for kk, v in t.items()}; t["q"] = t["q"] * k; t["pl"] = t["pl"] * k
    r = L.C.simulate(G.bars, t, lo, hi, None, guard); return dict(V=np.array(r["V"]), B=np.array(r["B"]), Hi=np.array(r["Hi"]), days=r["days"])


CONFIGS = {"INSTALLED: pair x1.5 + ManualDip, guard 1,500": lambda pool: G.add_dip(G.pair_series(pool, 1.5, 1.5, 1500.0), Dd, 1500.0),
           "XAU5 alone 250/trade (0.08 lot), weekend flat, guard 2,000": lambda pool: xau5(pool, 250, 2000.0),
           "XAU5 alone 300/trade (0.10 lot), weekend flat, guard 2,000": lambda pool: xau5(pool, 300, 2000.0),
           "XAU5 alone 500/trade (0.17 lot), weekend flat, guard 2,000": lambda pool: xau5(pool, 500, 2000.0)}
lines = []
for c0, lab in ((560.0, "THIS ACCOUNT (+560 counted on 12 Oct)"), (0.0, "FRESH account")):
    P.C0 = c0; lines.append(f"\n{lab}: P(pass) within 22 / 30 / 44 / 60 business days (MIX; gold-trend regime | 2022-26 history) and breach by 44 bd")
    for name, mk in CONFIGS.items():
        res = {pool: P.simulate([mk(pool)] * len(P.MULTS), P.I12, 90) for pool in ("MT5", "FT")}
        f = lambda n, code: 50 * sum(np.mean((res[p][0] == code) & (res[p][1] < n)) for p in res); g = lambda p, n: 100 * np.mean((res[p][0] == 1) & (res[p][1] < n))
        lines.append(f"  {name}\n     MIX {f(22, 1):4.1f}% / {f(30, 1):4.1f}% / {f(44, 1):4.1f}% / {f(60, 1):4.1f}%   | at 22 bd: gold-trend {g('MT5', 22):4.1f}%, 2022-26 {g('FT', 22):4.1f}%   | breach by 44 bd {f(44, 2):4.1f}% (60 bd {f(60, 2):4.1f}%)")
txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "XAU5_VS_INSTALLED_OUTPUT.txt"), "w").write(txt)
