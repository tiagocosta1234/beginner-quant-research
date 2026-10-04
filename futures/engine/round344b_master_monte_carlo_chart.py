"""Round 344b (descriptive chart, no ledger row): Monte Carlo fan chart of the deployed 1-Step plan (S01 TABLE), every start day x 20 coin draws, real MT5 broker fills.
Writes Knowledge_Base/charts/round344_master_monte_carlo.png."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/beginner-quant-research/futures/engine"); sys.path.insert(0, "/home/user/beginner-quant-research")
import round344_risk_management_25 as Q
from mt5broker import onestep as OS
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

cal, Rd, keys = Q.build(); ctx = Q.Ctx(keys); pol = OS.Policy()
fn = Q.scheme_fns(ctx, pol)["S01 TABLE"]; small = ctx.std(1.5); H = Q.H
def path(start, sides):
    st = dict(bal=OS.INITIAL, hwm=OS.INITIAL, day=0, loss_streak=0, win_streak=0); pos = best = 0.0; b = [OS.INITIAL]
    for j in range(start, start + H):
        st["hwm"] = max(st["hwm"], st["bal"]); st["day"] = j - start
        floor = max(max(st["hwm"], OS.INITIAL) - OS.TRAIL, st["bal"] - OS.DAILY_LOSS)
        risk, key = (250.0, small) if st["bal"] > OS.TARGET else fn(st)
        if key is not None and risk > 0:
            risk = min(risk, 0.9 * (st["bal"] - floor))
            if risk >= OS.MIN_RISK_USD:
                pnl = risk * Rd[j, 0 if sides[j] > 0 else 1, key]; st["bal"] += pnl
                if pnl > 0: pos += pnl; best = max(best, pnl)
                if st["bal"] > OS.TARGET and best <= 0.5 * pos:
                    b.append(st["bal"]); return np.array(b), "pass"
        b.append(st["bal"])
    stuck = 0.9 * (st["bal"] - (max(st["hwm"], OS.INITIAL) - OS.TRAIL)) < OS.MIN_RISK_USD
    return np.array(b), ("stuck" if stuck else "open")

rng = np.random.default_rng(344); n = len(cal)
sides_all = np.where(rng.random((20, n)) < 0.5, 1, -1)
starts = np.arange(0, n - H + 1)
P, O = [], []
for s in starts:
    for sd in sides_all:
        b, o = path(s, sd); P.append(b); O.append(o)
O = np.array(O)
L = np.full((len(P), H + 1), np.nan)
for i, b in enumerate(P):
    L[i, :len(b)] = b; L[i, len(b):] = b[-1]          # a passed account is frozen at its final balance
share = {k: (O == k).mean() for k in ("pass", "stuck", "open")}
days = np.array([len(b) - 1 for b, o in zip(P, O) if o == "pass"])
print(len(P), share, "median days", np.median(days))

BLUE, ORANGE, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig = plt.figure(figsize=(13, 7.2), facecolor=SURF)
gs = fig.add_gridspec(2, 3, width_ratios=[2.3, 1, 0.02], height_ratios=[1, 1], wspace=0.32, hspace=0.45)
ax = fig.add_subplot(gs[:, 0]); ax.set_facecolor(SURF)
x = np.arange(H + 1)
pick = rng.choice(len(P), 400, replace=False)
for i in pick:
    ax.plot(x[:len(P[i])], P[i] / 1000, color=BLUE if O[i] == "pass" else ORANGE, lw=0.6, alpha=0.28)
q10, q50, q90 = np.nanpercentile(L, [10, 50, 90], axis=0)
ax.fill_between(x, q10 / 1000, q90 / 1000, color=INK2, alpha=0.08, lw=0)
ax.plot(x, q50 / 1000, color=INK, lw=2)
ax.axhline(110, color=INK, lw=1, ls=(0, (4, 3))); ax.axhline(90, color=INK, lw=1, ls=(0, (4, 3)))
ax.text(56.5, 110.5, "target $110K", va="bottom", ha="right", color=INK, fontsize=9)
ax.text(56.5, 89.5, "max-loss floor $90K (trails up with the best day-start balance)", va="top", ha="right", color=INK, fontsize=9)
ax.text(1, q50[8] / 1000 + 0.6, "median account", color=INK, fontsize=9)
ax.text(31, 101.0, "10th-90th percentile band", color=INK2, fontsize=8.5)
ax.set_xlim(0, 57); ax.set_ylim(87, 113)
ax.set_xlabel("trading day of the test"); ax.set_ylabel("balance ($K)")
ax.grid(axis="y", color=GRID, lw=0.6); ax.spines[["top", "right"]].set_visible(False)
ax.set_title("400 of %s simulated MT5 1-Step $100K tests" % f"{len(P):,}", loc="left", color=INK, fontsize=12, fontweight="bold")
ax.plot([], [], color=BLUE, lw=2, label="passed"); ax.plot([], [], color=ORANGE, lw=2, label="did not pass in 57 days")
ax.legend(loc="lower left", frameon=False, fontsize=9)

ab = fig.add_subplot(gs[0, 1]); ab.set_facecolor(SURF)
labels = ["passed", "stuck: no room\nleft to risk $250", "still open\nat day 57"]; vals = [share["pass"], share["stuck"], share["open"]]
bars = ab.barh(labels[::-1], [v * 100 for v in vals[::-1]], color=[ORANGE, ORANGE, BLUE], height=0.6)
for bb, v in zip(bars, vals[::-1]):
    ab.text(bb.get_width() + 1.5, bb.get_y() + bb.get_height() / 2, f"{v*100:.1f}%", va="center", color=INK, fontsize=10)
ab.set_xlim(0, 70); ab.set_title("outcome", loc="left", color=INK, fontsize=11, fontweight="bold")
ab.spines[["top", "right", "bottom"]].set_visible(False); ab.set_xticks([]); ab.tick_params(axis="y", length=0)

ah = fig.add_subplot(gs[1, 1]); ah.set_facecolor(SURF)
ah.hist(days, bins=np.arange(0.5, 58.5, 3), color=BLUE, edgecolor=SURF, linewidth=2)
ah.axvline(np.median(days), color=INK, lw=1.2, ls=(0, (4, 3)))
ah.text(np.median(days) + 1, ah.get_ylim()[1] * 0.88, f"median {np.median(days):.0f} days", color=INK, fontsize=9)
ah.set_title("days to pass (passed runs)", loc="left", color=INK, fontsize=11, fontweight="bold")
ah.set_xlabel("trading days"); ah.spines[["top", "right"]].set_visible(False); ah.set_yticks([]); ah.spines["left"].set_visible(False)
fig.text(0.07, 0.015, "Deployed policy table, coin-flip US100.cash ticket at 09:30 NY, real MT5 broker bid/ask fills, $1,000 max risk. Every start day Oct 2021 - Jul 2026 x 20 coin draws. "
         "Rules: +10% target, 3% daily loss, 10% EOD trailing loss, best-day rule. Round 344, S01.", color=INK2, fontsize=8)
out = "/home/user/beginner-quant-research/Knowledge_Base/charts/round344_master_monte_carlo.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURF); print(out)
