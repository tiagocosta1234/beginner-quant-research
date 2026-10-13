"""Mandatory daily loss stop L and daily profit stop P on the installed pair (SDB + XAU5 x size, CPI flat), grid L,P in {1000, 1500, 2000, 2500}; the day ends at the first of -L / +P (all positions closed, no more trades that day),
otherwise at midnight. Bootstrap of the daily series (pass70.simulate, MT5 broker breach rules: in-day low <= -2,500 or equity <= 92,000; counted profit cap 2,000/day; pass at +8,000 counted or the pass lock), fresh account, MIX of the MT5 broker and FT pools.
python -m forex.ea_research.day_stops_grid --size 1.5     (appends to D:/finance/si_ledgers/DAYSTOPS_<size>.csv)"""
import sys
ARGV = sys.argv[1:]
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import argparse
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH

H = 250; GRID = (1000.0, 1500.0, 2000.0, 2500.0); P.C0 = 0.0


def series(pool, m, Pc, Lc, ref):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * m, lo), L.ea_trades(src, "xau5", CH["xau5"] * m, lo)); tr = news_flat(tr, G.EV, bars); r = L.C.simulate(bars, tr, lo, hi, Pc, Lc)
    idx = pd.Index(r["days"]); f = lambda x: pd.Series(x, index=idx).reindex(ref).fillna(0.0).to_numpy()
    ev = np.array([e or "" for e in r["ev"]]); return dict(V=f(r["V"]), B=f(r["B"]), Hi=f(r["Hi"]), days=ref), (ev == "profit").mean() * 100, (ev == "loss").mean() * 100


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--size", type=float, required=True); a = ap.parse_args(ARGV); out = f"D:/finance/si_ledgers/DAYSTOPS_{a.size}.csv"; refs = {p: G.pair_series(p, 1.5, 1.5, 1500.0)["days"] for p in ("MT5", "FT")}
    for Lc in GRID:
        for Pc in GRID:
            st, dy, w, l = [], [], [], []
            for pool in ("MT5", "FT"):
                S, wp, wl = series(pool, a.size, Pc, Lc, refs[pool]); s, d = P.simulate([S] * len(P.MULTS), P.I12, H); st.append(s); dy.append(d); w.append(wp); l.append(wl)
            st = np.concatenate(st); dy = np.concatenate(dy); ps = st == 1; days = dy[ps] + 1
            row = dict(size=a.size, loss_stop=Lc, profit_stop=Pc, pass_pct=100 * ps.mean(), breach_pct=100 * (st == 2).mean(), open_pct=100 * (st == 0).mean(), median_bd=float(np.median(days)) if len(days) else np.nan, mean_bd=float(days.mean()) if len(days) else np.nan,
                       pass44=100 * np.mean(ps & (dy < 44)), days_profit_stop_mt5=w[0], days_loss_stop_mt5=l[0], days_profit_stop_FT=w[1], days_loss_stop_FT=l[1])
            pd.DataFrame([row]).to_csv(out, mode="a", header=not os.path.exists(out), index=False); print(row, flush=True)


if __name__ == "__main__":
    main()
