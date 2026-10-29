"""Chart: cumulative R of the 7 kept LON_PERSYM rules, HistData 2020-21 (out of time) + MT5 2022-26. PYTHONPATH=. python forex/ea_research/lon_persym_chart.py"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import forex.ea_research.orb11_entry as oe, forex.ea_research.orb11_entry_oot as oo
from forex.ea_research.lon_persym import london_spread, HD_OK
S = pd.read_csv("data/si_ledgers/LON_PERSYM.csv"); K = S[S.kept]
T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet"); T = T[(T.sess == "LON") & (T.trig != "CTRL")]
fig, axes = plt.subplots(len(K), 1, figsize=(11, 2.3 * len(K)), sharex=True)
load0 = oe.load
for ax, r in zip(axes, K.itertuples()):
    g = T[(T.mkt == r.mkt) & (T.trig == r.trig)]; g = g[oe.fmask(g, r.filt)]; mt5s = g.set_index("day")[r.exit].sort_index()
    parts = []
    if r.mkt != "DOW" and HD_OK(r.mkt):
        D = oo.load_hd(r.mkt, london_spread(r.mkt)); oe.load = lambda s, e, D=D: D
        X = pd.DataFrame(oe.market((r.mkt, oe.END)), columns=oe.COLS); X = X[(X.sess == "LON") & (X.trig == r.trig)]; X = X[oe.fmask(X, r.filt)]
        parts.append(X.set_index("day")[r.exit].sort_index()); oe.load = load0
    s = pd.concat(parts + [mt5s]); c = s.cumsum()
    ax.plot(c.index, c.values, color="#1f4e79", lw=1.2)
    for a, b, col in (("2020-01-01", "2021-11-30", "#f2dede"), ("2022-01-01", "2024-12-31", "#e8eef7"), ("2025-01-01", "2025-12-31", "#fff3cd"), ("2026-01-01", "2026-10-02", "#dff0d8")):
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=col, zorder=0)
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_title(f"{r.mkt}  London {r.trig} + {r.filt}, {'1:1' if r.exit == 'r1' else 'hold to 17:00'}  |  2022-24 {r.DEV:+.2f}  2025 {r.VAL:+.2f}  2026 {r.Y26:+.2f} R/trade", fontsize=9, loc="left")
    ax.set_ylabel("cum. R", fontsize=8); ax.tick_params(labelsize=8)
fig.suptitle("Best London-open breakout per symbol (chosen on 2022-24), cumulative R per trade, MT5 broker spreads\nred = 2020-21 out of time (HistData)   blue = 2022-24 (chosen here)   yellow = 2025   green = 2026", fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig("forex/ea_research/LON_PERSYM_EQUITY.png", dpi=110)
print("saved")
