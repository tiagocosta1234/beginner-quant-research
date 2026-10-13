"""XAU5 (5-minute) alone: how to make the most money with a 2,000 USD daily guard? the trader 2026-10-12.
Objective = COUNTED profit per month (each day capped at +2,000, losses in full: MT5 broker counts at most 2,000 of profit a day), subject to survival: no floating day below -2,500 (MT5 broker hard breach) in
either pool. Levers: size (risk per trade = the median losing trade, approximation for a closed-source EA), cap on simultaneously open positions, XAU5 flat over weekends, CPI news flat on.
Guard day stop 2,000 (M1-close guard model). Pools: MT5 12 months (real ticks) and FT 2022-26.   python -m forex.ea_research.xau5_maxmoney"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI")); G.EV = EV
GUARD, CAP = 2000.0, 2000.0


def cap_open(t, n):
    o = np.argsort(t["in_s"], kind="stable"); keep = np.zeros(len(o), bool); open_out = []
    for i in o:
        open_out = [x for x in open_out if x > t["in_s"][i]]
        if len(open_out) < n: keep[i] = True; open_out.append(t["out_s"][i])
    return {k: np.array(v)[keep] for k, v in t.items()}


def build(pool, R, ncap, wkflat):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); t = L.ea_trades(src, "xau5", CH["xau5"], lo); t = {k: np.array(v, copy=True) for k, v in t.items()}
    k = R / np.median(np.abs(t["pl"][t["pl"] < 0]))                                       # size from the unfiltered losing-trade median
    if wkflat: t = L.flatten_weekends(t)
    t = G.news_flat(t, EV, G.bars)
    if ncap: t = cap_open(t, ncap)
    t = {kk: np.array(v, copy=True) for kk, v in t.items()}; t["q"] = t["q"] * k; t["pl"] = t["pl"] * k
    r = L.C.simulate(G.bars, t, lo, hi, None, GUARD); return pd.Series(np.array(r["V"])), np.array(r["B"]), len(t["pl"])


rows = []
for ncap in (0, 6, 4, 3):
    for wk in (False, True):
        for R in (250, 400, 600, 800, 1000, 1500):
            rec = dict(open_cap=ncap or "none", weekend_flat=wk, risk_per_trade=R, ok=True)
            for pool in ("MT5", "FT"):
                V, B, n = build(pool, R, ncap, wk); months = len(V) / 21.0; eq = V.cumsum()
                rec[f"{pool}_raw_mo"] = V.sum() / months; rec[f"{pool}_counted_mo"] = np.minimum(V, CAP).sum() / months; rec[f"{pool}_worst"] = B.min(); rec[f"{pool}_dd"] = (eq.cummax() - eq).max(); rec[f"{pool}_le2500"] = int((B <= -2500).sum()); rec[f"{pool}_trades"] = n
                rec["ok"] &= rec[f"{pool}_le2500"] == 0
            rows.append(rec)
R_ = pd.DataFrame(rows); cols = ["open_cap", "weekend_flat", "risk_per_trade", "ok", "mt5_raw_mo", "mt5_counted_mo", "mt5_worst", "mt5_dd", "mt5_le2500", "FT_counted_mo", "FT_worst", "FT_dd", "FT_le2500", "mt5_trades"]
print("XAU5 alone, guard 2,000, news flat on (per month = 21 trading days; counted = profit capped at +2,000/day):")
print(R_[cols].round(0).to_string(index=False))
ok = R_[R_.ok].sort_values("mt5_counted_mo", ascending=False); print("\nsurviving configs (no floating day <= -2,500 in either pool), best counted profit per month first:"); print(ok[cols].head(8).round(0).to_string(index=False))
open(os.path.join(os.path.dirname(__file__), "XAU5_MAXMONEY_OUTPUT.txt"), "w").write(R_[cols].round(0).to_string(index=False))
