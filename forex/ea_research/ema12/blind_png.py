"""Blind-replay chart as a PNG (the trader 26 Oct 2026: "fx replay only has forex data, lets do the first blind day through a generated png").
Draws ONLY candles whose label time is <= the cutoff (local clock), so nothing after the cutoff can leak: the last 15m / 1h candle is the
partial candle as it would look live. Data: MT5 XAUUSD M1 (server time Europe/Athens), mid of bid and ask. EMA12 on closes (TradingView
style, adjust=False). Panels: 1h (5 days), 15m (2 days), 1m (from 05:00 local). Lines: Asia high/low (00:00-07:00 local), prior-day high/low.
Usage (from ema12): python blind_png.py 2026-08-06 07:59   -> blind_png/2026-08-06_0759.png"""
import sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet"


def load(day, cutoff):
    r = pd.read_parquet(SRC)
    t = pd.to_datetime(r.t, unit="s")
    lo, hi = pd.Timestamp(day) - pd.Timedelta(days=12), pd.Timestamp(day) + pd.Timedelta(days=1)
    m = (t >= lo) & (t <= hi); r, t = r[m], t[m]
    idx = t.dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London").dt.tz_localize(None)
    d = pd.DataFrame({k: ((r["b" + k[0]] + r["a" + k[0]]) / 2).to_numpy() for k in ("open", "high", "low", "close")}, index=idx.to_numpy())
    d = d[~d.index.isna()]; d = d[~d.index.duplicated()].sort_index()
    return d[d.index <= cutoff]                                                  # the leak guard: nothing after the cutoff candle


def candles(ax, df, width=0.6):
    x = np.arange(len(df)); up = df.close >= df.open
    ax.vlines(x, df.low, df.high, color=np.where(up, "#26a69a", "#ef5350"), linewidth=0.8)
    ax.bar(x[up], (df.close - df.open)[up], width, df.open[up], color="#26a69a")
    ax.bar(x[~up], (df.open - df.close)[~up], width, df.close[~up], color="#ef5350")
    return x


def ticks(ax, df, every, fmt):
    pos = [i for i, ts in enumerate(df.index) if (ts.minute % every == 0 if every < 60 else (ts.hour % (every // 60) == 0 and ts.minute == 0))]
    ax.set_xticks(pos); ax.set_xticklabels([df.index[i].strftime(fmt) for i in pos], fontsize=7)


def panel(ax, df, title, tick_every, fmt, levels):
    x = candles(ax, df)
    ax.plot(x, df.close.ewm(span=12, adjust=False).mean(), color="#2962ff", linewidth=1.2, label="EMA 12")
    lo, hi = df.low.min(), df.high.max(); pad = 0.08 * (hi - lo); ax.set_ylim(lo - pad, hi + pad)
    for y, lab, c in levels:                                     # only levels inside this panel's range (others would squash it)
        if np.isfinite(y) and lo - pad <= y <= hi + pad:
            ax.axhline(y, color=c, linestyle="--", linewidth=0.8); ax.text(len(df) - 0.5, y, " %s %.1f" % (lab, y), color=c, fontsize=7, va="center")
    ax.set_title(title, fontsize=9, loc="left"); ax.grid(alpha=0.2); ticks(ax, df, tick_every, fmt)
    ax.yaxis.tick_right(); ax.tick_params(axis="y", labelsize=7); ax.set_xlim(-1, len(df) + 6)


def main():
    argv = sys.argv[1:]; box = None
    if "--box" in argv:                                                # --box SIDE ENTRY STOP TARGET HH:MM (the trader: "draw the box on the png")
        i = argv.index("--box"); b = argv[i + 1:i + 6]; argv = argv[:i] + argv[i + 6:]
        box = (b[0], float(b[1]), float(b[2]), float(b[3]), b[4])
    day, hhmm = argv[0], argv[1]
    m1_from = argv[2] if len(argv) > 2 else "06:45"                    # 1m panel start (the trader 26 Oct: "zoom in on the 1 minute")
    m15_days = float(argv[3]) if len(argv) > 3 else 5                  # 15m panel days back ("zoom out on the 15 minute")
    cutoff = pd.Timestamp("%s %s" % (day, hhmm))
    d = load(day, cutoff)
    D = pd.Timestamp(day)
    rs = lambda rule: d.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    h1, m15 = rs("60min"), rs("15min")
    asia = d[(d.index >= D) & (d.index < D + pd.Timedelta(hours=7))]
    prev = d[d.index < D]; pday = prev[prev.index >= prev.index[-1].normalize()] if len(prev) else prev
    levels = [(asia.high.max() if len(asia) else np.nan, "Asia H", "#ff9800"), (asia.low.min() if len(asia) else np.nan, "Asia L", "#ff9800"),
              (pday.high.max() if len(pday) else np.nan, "PDH", "#9c27b0"), (pday.low.min() if len(pday) else np.nan, "PDL", "#9c27b0")]
    fig = plt.figure(figsize=(16, 11), facecolor="white")
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1.1, 1.6], hspace=0.35)
    panel(fig.add_subplot(gs[0]), h1[h1.index >= D - pd.Timedelta(days=5)], "1h", 360, "%a %H:%M", levels)
    panel(fig.add_subplot(gs[1]), m15[m15.index >= D - pd.Timedelta(days=m15_days)], "15m", 720, "%a %H:%M", levels)
    m1all = d[d.index >= D + pd.Timedelta(hours=5)]                    # EMA seeded from 05:00 as before, so the line does not change
    ema1 = m1all.close.ewm(span=12, adjust=False).mean()
    m1 = m1all[m1all.index >= pd.Timestamp("%s %s" % (day, m1_from))]
    ax1 = fig.add_subplot(gs[2]); panel(ax1, m1, "1m", 5, "%H:%M", levels)
    ax1.lines[0].set_ydata(ema1[m1.index].to_numpy())
    if box:
        from matplotlib.patches import Rectangle
        side, e, s, tg, t0 = box
        x0 = int(np.searchsorted(m1.index.to_numpy(), np.datetime64(pd.Timestamp("%s %s" % (day, t0))))); x1 = len(m1) + 4
        ax1.add_patch(Rectangle((x0 - 0.5, min(e, tg)), x1 - x0, abs(tg - e), color="#26a69a", alpha=0.18))
        ax1.add_patch(Rectangle((x0 - 0.5, min(e, s)), x1 - x0, abs(e - s), color="#ef5350", alpha=0.18))
        for y, lab, c in ((tg, "target", "#1b7f72"), (e, "entry", "#444444"), (s, "stop", "#c62828")):
            ax1.axhline(y, xmin=0, color=c, linewidth=0.9, alpha=0.8); ax1.text(x1, y, " %s %.2f" % (lab, y), color=c, fontsize=8, va="center")
        lo, hi = ax1.get_ylim(); ax1.set_ylim(min(lo, s, tg) - 1, max(hi, s, tg) + 1); ax1.set_xlim(-1, x1 + 10)
    last = d.iloc[-1]
    fig.suptitle("BLIND DAY  ·  XAUUSD  ·  %s  ·  last candle %s local  ·  close %.2f  (nothing after this minute is drawn)" % (
        D.strftime("%a %d %b %Y"), hhmm, last.close), fontsize=11, x=0.01, ha="left")
    os.makedirs("blind_png", exist_ok=True)
    out = "blind_png/%s_%s.png" % (day, hhmm.replace(":", ""))
    k = 1
    while True:                                                          # an image still open in the viewer is locked on Windows
        try: fig.savefig(out, dpi=110, bbox_inches="tight"); break
        except OSError: k += 1; out = "blind_png/%s_%s_v%d.png" % (day, hhmm.replace(":", ""), k)
    print(out, "last bar", d.index[-1], "close %.2f" % last.close)


if __name__ == "__main__":
    main()
