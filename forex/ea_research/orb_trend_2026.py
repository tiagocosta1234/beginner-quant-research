"""2026 (hold-out OPENED at the trader's request, exploratory): card breakouts, trend-direction filter, $1,000 risk per trade."""
import sys
sys.path.insert(0, r"D:\finance\beginner-quant-research")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from forex.ea_research.orb_refine import trades
END = pd.Timestamp("2026-10-03").timestamp()
out, curves = [], {}
for s in ("XAUUSD", "NSDQ"):
    df = trades(s, END)
    df = df[df.day >= "2026-01-01"].copy()
    df.to_parquet(f"D:/finance/si_ledgers/ORB_TREND_2026_{s}.parquet")
    for lab, x in (("trend", df[df.side == df.trend]), ("all", df)):
        x = x.sort_values("day").assign(usd=lambda z: z.R * 1000)
        eq = x.usd.cumsum()
        dd = (eq - eq.cummax()).min()
        streak = (x.R <= 0).astype(int).groupby((x.R > 0).cumsum()).sum().max()
        m = x.groupby(x.day.dt.to_period("M")).usd.sum()
        out.append(dict(sym=s, version=lab, trades=len(x), win=np.mean(x.R > 0), avgR=x.R.mean(), total=x.usd.sum(), maxDD=dd, worst=x.usd.min(), best=x.usd.max(),
                        lose_streak=int(streak), months_pos=f"{(m > 0).sum()}/{len(m)}"))
        curves[(s, lab)] = (x.day.values, eq.values)
        if lab == "trend":
            print(f"{s} trend-direction months ($):", " ".join(f"{p.strftime('%b')} {v:+,.0f}" for p, v in m.items()))
R = pd.DataFrame(out)
pd.set_option("display.width", 200)
print(R.round(3).to_string(index=False))
both = pd.concat([pd.read_parquet(f"D:/finance/si_ledgers/ORB_TREND_2026_{s}.parquet").query("side == trend") for s in ("XAUUSD", "NSDQ")]).sort_values("day")
both["usd"] = both.R * 1000
eqb = both.usd.cumsum()
print(f"COMBINED trend-direction: {len(both)} trades, total {both.usd.sum():+,.0f}, maxDD {(eqb - eqb.cummax()).min():+,.0f}, worst day {both.groupby('day').usd.sum().min():+,.0f}")
fig, ax = plt.subplots(figsize=(12, 6))
for (s, lab), (x, y) in curves.items():
    ax.plot(x, y, lw=2 if lab == "trend" else 1, ls="-" if lab == "trend" else "--",
            color={"XAUUSD": "#c9a227", "NSDQ": "#1f6feb"}[s], label=f"{s} {'trend-direction only' if lab == 'trend' else 'all breakouts (card as is)'}")
ax.plot(both.day.values, eqb.values, color="#2e7d32", lw=2.4, label="both, trend-direction only")
ax.axhline(0, color="#888", lw=0.8)
ax.set_title("2026 (Jan 2 - Oct 2) card breakouts at $1,000 risk per trade - HOLD-OUT opened, exploratory", fontsize=11)
ax.set_ylabel("cumulative P&L (USD, net of spread)"); ax.grid(alpha=0.25); ax.legend(fontsize=9)
plt.tight_layout(); plt.savefig("D:/finance/scratch/charts/ORB_TREND_2026.png", dpi=110)
print("chart D:/finance/scratch/charts/ORB_TREND_2026.png")
