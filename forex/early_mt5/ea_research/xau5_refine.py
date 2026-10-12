"""Refinement of xau5_maxmoney: smaller sizes and 1-2 open positions, weekend flat on, guard 2,000, news flat on.   python -m mt5broker.ea_research.xau5_refine"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G, clean_boot_lib as L
from mt5broker.ea_research.event_macro import server_s
from mt5broker.ea_batch.mt5_mc_config import CH

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI")); G.EV = EV
CAP = 2000.0


def cap_open(t, n):
    o = np.argsort(t["in_s"], kind="stable"); keep = np.zeros(len(o), bool); open_out = []
    for i in o:
        open_out = [x for x in open_out if x > t["in_s"][i]]
        if len(open_out) < n: keep[i] = True; open_out.append(t["out_s"][i])
    return {k: np.array(v)[keep] for k, v in t.items()}


def build(pool, R, ncap, guard, wk=True):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); t = {k: np.array(v, copy=True) for k, v in L.ea_trades(src, "xau5", CH["xau5"], lo).items()}
    k = R / np.median(np.abs(t["pl"][t["pl"] < 0]))
    if wk: t = L.flatten_weekends(t)
    t = G.news_flat(t, EV, G.bars)
    if ncap: t = cap_open(t, ncap)
    t = {kk: np.array(v, copy=True) for kk, v in t.items()}; t["q"] = t["q"] * k; t["pl"] = t["pl"] * k
    r = L.C.simulate(G.bars, t, lo, hi, None, guard); return pd.Series(np.array(r["V"])), np.array(r["B"]), len(t["pl"])


rows = []
for guard in (2000.0,):
    for ncap in (0, 2, 1):
        for R in (100, 150, 200, 250, 300, 350):
            rec = dict(guard=int(guard), open_cap=ncap or "none", risk=R, ok=True)
            for pool in ("MT5", "FT"):
                V, B, n = build(pool, R, ncap, guard); mo = len(V) / 21.0; eq = V.cumsum()
                rec.update({f"{pool}_raw": V.sum() / mo, f"{pool}_counted": np.minimum(V, CAP).sum() / mo, f"{pool}_worst": B.min(), f"{pool}_dd": (eq.cummax() - eq).max(), f"{pool}_trades": n, f"{pool}_posmonths": 100 * (V.groupby(np.arange(len(V)) // 21).sum() > 0).mean()})
                rec["ok"] &= bool((B <= -2500).sum() == 0)
            rows.append(rec)
R_ = pd.DataFrame(rows); print(R_.round(0).to_string(index=False)); open(os.path.join(os.path.dirname(__file__), "XAU5_REFINE_OUTPUT.txt"), "w").write(R_.round(0).to_string(index=False))
