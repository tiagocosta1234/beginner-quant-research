"""Equity curves (cumulative net bp, 1x notional, real bid/ask fills) of the 71 UT Bot cells that were profitable in both DEV and VAL. python -m forex.ea_research.utbot_equity"""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.argv = [sys.argv[0]]
from forex.ea_research import utbot as U

a = pd.read_csv("D:/finance/tmp/utbot_cells.csv"); a["var"] = "base"
b = pd.read_csv("D:/finance/tmp/utbot_variant_cells.csv")
R = pd.concat([a, b]); cells = R[(R.mu_DEV > 0) & (R.mu_VAL > 0)].sort_values(["sym", "tf", "var"]).reset_index(drop=True)
VAR = {"base": (1.0, False), "k2": (2.0, False), "k3": (3.0, False), "ha": (1.0, True)}
cache, curves, bh = {}, {}, {}
for r in cells.itertuples():
    if r.sym not in cache:
        d = pd.read_parquet(U.DATA + f"{r.sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
        d = d[(d.t < U.END_T) & (d.bo > 0) & (d.ao >= d.bo)]
        cache[r.sym] = pd.DataFrame({"t": d.t.to_numpy(), "bo": d.bo.to_numpy(), "ao": d.ao.to_numpy(), "mo": ((d.bo + d.ao) / 2).to_numpy(), "mh": ((d.bh + d.ah) / 2).to_numpy(), "ml": ((d.bl + d.al) / 2).to_numpy(), "mc": ((d.bc + d.ac) / 2).to_numpy()})
    bars = U.bars(cache[r.sym], U.TFS[r.tf])
    key, ha = VAR[r.var]
    sg = U.signals(bars, key, ha)
    t, bo, ao = bars.t.to_numpy(), bars.bo.to_numpy(), bars.ao.to_numpy()
    tx, sd, ret = U.trades_from(sg, t, bo, ao, U.allowed_next(t))
    s = pd.Series(np.cumsum(ret), index=pd.to_datetime(tx, unit="s"))
    curves[(r.sym, r.tf, r.var)] = s
    px = pd.Series((bo + ao) / 2, index=pd.to_datetime(t, unit="s"))
    bh[(r.sym, r.tf, r.var)] = (px / px.iloc[0] - 1) * 1e4
grid = pd.date_range("2021-12-01", "2025-12-31", freq="D")
M = pd.DataFrame({k: v[~v.index.duplicated(keep="last")].reindex(grid, method="ffill").fillna(0.0) for k, v in curves.items()})
# normalise each cell by its own total so that very different scales (BTC vs FX) are comparable in the overlay
Z = M / M.iloc[-1].abs().replace(0, np.nan)
val0, dev_end = pd.Timestamp("2024-01-01"), pd.Timestamp("2023-12-31")
fig, ax = plt.subplots(1, 2, figsize=(16, 6.2))
for c in Z.columns:
    ax[0].plot(Z.index, Z[c], lw=0.7, alpha=0.45)
ax[0].plot(Z.index, Z.mean(1), color="black", lw=2.4, label="average of the 71 cells")
ax[0].axvline(val0, color="gray", ls="--"); ax[0].text(val0, ax[0].get_ylim()[1] * 0.92, " VAL ->", color="gray")
ax[0].set_title("71 cells, each curve normalised to end at +1 (shape only)"); ax[0].legend(loc="upper left"); ax[0].grid(alpha=.25)
# unit-notional average in bp (equal weight, each cell 1x notional)
avg = M.mean(1)
ax[1].plot(avg.index, avg.values, color="#0969da", lw=2)
ax[1].axvline(val0, color="gray", ls="--")
ax[1].set_title("Equal-weight average of the 71 cells, cumulative net bp per cell at 1x notional"); ax[1].set_ylabel("bp"); ax[1].grid(alpha=.25)
fig.suptitle("UT Bot cells profitable in BOTH 2021-23 and 2024-25 (selected after the fact: in-sample by construction, selection bias)", fontsize=11)
fig.tight_layout(); fig.savefig("forex/ea_research/UTBOT_EQUITY_OVERVIEW.png", dpi=100); plt.close(fig)
n = len(M.columns); cols = 9; rows = int(np.ceil(n / cols))
fig, axs = plt.subplots(rows, cols, figsize=(22, 2.1 * rows), sharex=True)
for ax_, c in zip(axs.ravel(), M.columns):
    ax_.plot(M.index, M[c], color="#1a7f37", lw=1)
    ax_.plot(M.index, bh[c].reindex(grid, method="ffill").fillna(0.0), color="gray", lw=0.7, alpha=0.7)
    ax_.axvline(val0, color="gray", ls=":", lw=0.7)
    ax_.set_title(f"{c[0]} {c[1]} {c[2]}  {M[c].iloc[-1]:+,.0f}bp", fontsize=7.5); ax_.tick_params(labelsize=6)
for ax_ in axs.ravel()[n:]:
    ax_.axis("off")
fig.suptitle("Each cell: UT Bot net bp (green) vs buy-and-hold of the same symbol in bp (grey); dotted = start of validation", fontsize=11)
fig.tight_layout(); fig.savefig("forex/ea_research/UTBOT_EQUITY_CELLS.png", dpi=80); plt.close(fig)
beat = sum(M[c].iloc[-1] > bh[c].reindex(grid, method="ffill").fillna(0).iloc[-1] for c in M.columns)
print("cells", n, "| average total net bp per cell (2021-12..2025-12):", round(avg.iloc[-1]), "| cells that beat buy-and-hold over the whole period:", int(beat))
print("end value by cell class: indices/gold/crypto vs FX:", round(M[[c for c in M.columns if c[0] in ('SP','NSDQ','DOW','DAX','NIKKEI','ASX','XAUUSD','XAGUSD','BTCUSD','ETHUSD','SOLUSD','XRPUSD','BNBUSD')]].iloc[-1].mean()), round(M[[c for c in M.columns if c[0] not in ('SP','NSDQ','DOW','DAX','NIKKEI','ASX','XAUUSD','XAGUSD','BTCUSD','ETHUSD','SOLUSD','XRPUSD','BNBUSD')]].iloc[-1].mean()))
