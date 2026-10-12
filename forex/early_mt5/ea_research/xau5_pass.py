"""Pass rate of XAU5 (5-minute) alone with each trade risking 250 / 500 / 750 / 1,000 / 1,500 USD at its stop (approximation: size scaled so the MEDIAN losing trade equals the risk), guard day stop 1,500,
FRESH account, pass70 rules, MIX of the MT5 12-month and FT 2022-26 pools. the trader 2026-10-12: "ve o pass rate com o XAU5".   python -m mt5broker.ea_research.xau5_pass"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G, clean_boot_lib as L, pass70 as P, dip_addon as DA
from mt5broker.ea_research.event_macro import server_s
from mt5broker.ea_batch.mt5_mc_config import CH

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI")); G.EV = EV
P.C0 = 0.0; GUARD = 1500.0


def series(pool, R, news=True):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); t = L.ea_trades(src, "xau5", CH["xau5"], lo); k = R / np.median(np.abs(t["pl"][t["pl"] < 0])); t = dict(t); t["q"] = t["q"] * k; t["pl"] = t["pl"] * k
    if news: t = G.news_flat(t, EV, G.bars)
    r = L.C.simulate(G.bars, t, lo, hi, None, GUARD); return dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])


rows = []
for R in (250, 500, 750, 1000, 1500):
    res = {pool: P.simulate([series(pool, R)] * len(P.MULTS), P.I12, 90) for pool in ("MT5", "FT")}
    f = lambda n, code: 50 * sum(np.mean((res[p][0] == code) & (res[p][1] < n)) for p in res)
    g = lambda pool, n: 100 * np.mean((res[pool][0] == 1) & (res[pool][1] < n))
    S = series("MT5", R); w = np.minimum(S["V"], S["B"]); rows.append(dict(risk_per_trade=R, pass22=f(22, 1), pass30=f(30, 1), pass44=f(44, 1), breach44=f(44, 2), pass22_gold_trend=g("MT5", 22), pass22_2022_26=g("FT", 22), worst_day_mt5=round(w.min()), days_le_1500_mt5=int((w <= -1500).sum())))
R_ = pd.DataFrame(rows); txt = "XAU5 (5 min) alone, guard 1,500, fresh account, MIX of pools (percent), 22 bd = about 30 calendar days:\n" + R_.round(1).to_string(index=False)
print(txt); open(os.path.join(os.path.dirname(__file__), "XAU5_PASS_OUTPUT.txt"), "w").write(txt)
