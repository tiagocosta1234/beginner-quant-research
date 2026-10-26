"""PREREG_CLAUDE_FILTER step 2: compact charts of each logged trade drawn ONLY from bars up to the entry minute (load_fut(day, cutoff)),
3 trades per image: left 15m (2 days) with EMA12, right 1m 06:30..entry with EMA12, Asia high/low, prior-day high/low, entry / stop / target.
Usage (from ema12): python filter_charts.py  -> filter_charts/sheet_01.png ..."""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import blind_png as B

L = pd.read_csv("BLIND_LOG_FILTER.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])].reset_index(drop=True)
os.makedirs("filter_charts", exist_ok=True)


def candles(ax, df):
    x = np.arange(len(df)); up = (df.close >= df.open).to_numpy()
    ax.vlines(x, df.low, df.high, color=np.where(up, "#26a69a", "#ef5350"), linewidth=0.7)
    ax.bar(x[up], (df.close - df.open)[up], 0.6, df.open[up], color="#26a69a"); ax.bar(x[~up], (df.open - df.close)[~up], 0.6, df.close[~up], color="#ef5350")
    ax.plot(x, df.close.ewm(span=12, adjust=False).mean(), color="#2962ff", linewidth=1.1)
    return x


for s in range(0, len(L), 3):
    chunk = L.iloc[s:s + 3]
    fig, axes = plt.subplots(len(chunk), 2, figsize=(14, 4.0 * len(chunk)), gridspec_kw={"width_ratios": [1, 1.6]}, squeeze=False)
    for row, r in enumerate(chunk.itertuples()):
        cut = pd.Timestamp(f"{r.date} {r.hhmm}"); D = pd.Timestamp(r.date)
        d = B.load_fut(r.date, cut); assert d.index.max() <= cut
        m15 = d.resample("15min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        m15 = m15[m15.index >= D - pd.Timedelta(days=2)]
        candles(axes[row, 0], m15); axes[row, 0].set_title("15m  %s  (to %s)" % (r.date, r.hhmm), fontsize=9, loc="left")
        m1 = d[d.index >= D + pd.Timedelta(hours=6, minutes=30)]
        candles(axes[row, 1], m1)
        asia = d.loc[D:D + pd.Timedelta(hours=6, minutes=59)]; prev = d[d.index < D]; pday = prev[prev.index >= prev.index[-1].normalize()]
        lo, hi = min(m1.low.min(), r.stop, r.target), max(m1.high.max(), r.stop, r.target)
        for y, lab, c, ls in ((asia.high.max(), "Asia H", "#ff9800", "--"), (asia.low.min(), "Asia L", "#ff9800", "--"),
                              (pday.high.max(), "PDH", "#9c27b0", "--"), (pday.low.min(), "PDL", "#9c27b0", "--"),
                              (r.entry, "entry", "black", "-"), (r.stop, "stop", "#c62828", "-"), (r.target, "target", "#1b7f72", "-")):
            if lo - 2 <= y <= hi + 2:
                axes[row, 1].axhline(y, color=c, linestyle=ls, linewidth=0.9); axes[row, 1].text(len(m1) + 1, y, " %s %.1f" % (lab, y), fontsize=7, color=c, va="center")
        axes[row, 1].set_xlim(-1, len(m1) + 18)
        ticks = [i for i, t in enumerate(m1.index) if t.minute % 15 == 0]
        axes[row, 1].set_xticks(ticks); axes[row, 1].set_xticklabels([m1.index[i].strftime("%H:%M") for i in ticks], fontsize=7)
        axes[row, 1].set_title("#%d  %s  %s  1m to %s   entry %.1f  stop %.1f  target %.1f" % (s + row + 1, r.date, "LONG" if r.side == "L" else "SHORT", r.hhmm, r.entry, r.stop, r.target), fontsize=9, loc="left")
        for ax in axes[row]: ax.tick_params(labelsize=7); ax.grid(alpha=0.2); ax.yaxis.tick_right()
        axes[row, 0].set_xticks([])
    fig.tight_layout(); fig.savefig("filter_charts/sheet_%02d.png" % (s // 3 + 1), dpi=70); plt.close(fig)
print("sheets:", sorted(os.listdir("filter_charts")))
