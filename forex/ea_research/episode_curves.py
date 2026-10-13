"""Equity curves and pass-time curves for the installed system vs the +2000/-1500 lock at several sizes.  python -m forex.ea_research.episode_curves"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from forex.ea_research import improve_round as I, combo_grid as G, pass70 as P, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH
P.C0 = 0.0
def series(pool, m, Pc, Lc):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); ref = G.pair_series(pool, 1.5, 1.5, I.GUARD)["days"]
    if Pc is None and m == 1.5: return G.add_dip(G.pair_series(pool, 1.5, 1.5, I.GUARD), I.Dd, I.GUARD)
    tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * m, lo), L.ea_trades(src, "xau5", CH["xau5"] * m, lo)); tr = news_flat(tr, G.EV, bars); r = L.C.simulate(bars, tr, lo, hi, Pc, Lc)
    idx = pd.Index(r["days"]); f = lambda x: pd.Series(x, index=idx).reindex(ref).fillna(0.0).to_numpy(); return G.add_dip(dict(V=f(r["V"]), B=f(r["B"]), Hi=f(r["Hi"]), days=ref), I.Dd, I.GUARD)
cfg = [("installed x1.5 (no lock)", 1.5, None, None, "#444444"), ("lock +2000/-1500 at x1.5", 1.5, 2000.0, 1500.0, "#1f77b4"), ("lock +2000/-1500 at x3.5", 3.5, 2000.0, 1500.0, "#ff7f0e"), ("lock +2000/-1500 at x5", 5.0, 2000.0, 1500.0, "#d62728")]
fig, ax = plt.subplots(2, 2, figsize=(14, 9)); res = {n: {} for n, *_ in cfg}; S = {}
for j, pool in enumerate(("MT5", "FT")):
    for n, m, Pc, Lc, col in cfg:
        s = series(pool, m, Pc, Lc); S[(n, pool)] = s; V = np.asarray(s["V"], float); days = pd.to_datetime(np.asarray(s["days"]) * 86400, unit="s")
        ax[0, j].plot(days, np.cumsum(np.minimum(V, 2000.0)), label=n, color=col, lw=1.4); res[n][pool] = P.simulate([s] * len(P.MULTS), P.I12, 90)
    ax[0, j].axhline(8000, color="green", ls="--", lw=0.8); ax[0, j].axhline(-8000, color="red", ls="--", lw=0.8); ax[0, j].set_title(f"{pool} pool: cumulative counted profit (history order, 1 start)"); ax[0, j].set_ylabel("USD"); ax[0, j].legend(fontsize=8)
x = np.arange(1, 91)
for j, c in enumerate((1, 2)):
    for n, m, Pc, Lc, col in cfg:
        y = [50 * sum(np.mean((res[n][p][0] == c) & (res[n][p][1] < d)) for p in ("MT5", "FT")) for d in x]; ax[1, j].plot(x, y, label=n, color=col, lw=1.6)
    ax[1, j].set_xlabel("business days from a fresh start"); ax[1, j].set_ylabel("% of simulated starts"); ax[1, j].set_title(("PASSED (+8,000 counted)" if c == 1 else "BREACHED (-2,500 day or 92,000)") + " by day (MIX of MT5 broker and FT pools)"); ax[1, j].axvline(44, color="grey", ls=":", lw=0.8); ax[1, j].legend(fontsize=8)
plt.tight_layout(); out = os.path.join(os.path.dirname(__file__), "episode_curves.png"); plt.savefig(out, dpi=110); print(out)
for n, *_ in cfg: print(n, "| pass 22/44/90:", [round(50 * sum(np.mean((res[n][p][0] == 1) & (res[n][p][1] < d)) for p in ("MT5", "FT")), 1) for d in (22, 44, 90)], "| breach 90:", round(50 * sum(np.mean((res[n][p][0] == 2) & (res[n][p][1] < 90)) for p in ("MT5", "FT")), 1))
