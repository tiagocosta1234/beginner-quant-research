"""Draws what daily-trend-claude.pine shows on micro gold (MGC 1m, merged BrokerAPI data) for the latest setup, plus a table of the recent candidates. Usage: python preview_dt_claude.py"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

d = pd.read_csv("D:/finance/beginner-quant-research/futures/data/merged_micros_2026-10-27/MGC_1MIN_MERGED.csv", usecols=["timestamp", "open", "high", "low", "close"])
d.index = pd.to_datetime(d.timestamp, utc=True).dt.tz_convert("Europe/London").dt.tz_localize(None)
d = d.drop(columns="timestamp").sort_index(); d = d[~d.index.duplicated()]
d["ema"] = d.close.ewm(span=12, adjust=False).mean()
m15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
h1 = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
dly = d.close.resample("1D").last().dropna(); up = (dly > dly.rolling(20).mean()).shift(1)
COST, TICK, MAXSHARE = 0.292, 0.1, 0.12
O, H, L, C, E = (d[k].to_numpy() for k in ("open", "high", "low", "close", "ema")); TS = d.index.to_numpy()
out = []
for day in pd.Index(d.index.normalize().unique()):
    if day < pd.Timestamp("2026-08-05") or day.weekday() >= 5: continue
    k = day + pd.Timedelta(hours=7, minutes=45)
    if k not in m15.index: continue
    i = m15.index.get_loc(k)
    if i < 4: continue
    bias = 1 if (m15.iloc[i] > e15.iloc[i] and e15.iloc[i] > e15.iloc[i - 4]) else -1 if (m15.iloc[i] < e15.iloc[i] and e15.iloc[i] < e15.iloc[i - 4]) else 0
    if not bias: continue
    a = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8))); b = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8, minutes=15)))
    end = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=16))); sig = None
    for j in range(max(a, 1), b):
        if bias * (C[j] - E[j]) > 0 and bias * (C[j - 1] - E[j - 1]) < 0 and abs(C[j] - O[j]) > max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j]):
            sig = j; break
    if sig is None or sig < 6: continue
    e = C[sig]; stop = (L[sig - 5:sig + 1].min() - TICK) if bias > 0 else (H[sig - 5:sig + 1].max() + TICK); r = abs(e - stop)
    c1 = any((bias > 0 and H[q - 2] < L[q] and L[sig] <= L[q] and H[sig] >= H[q - 2]) or (bias < 0 and L[q - 2] > H[q] and H[sig] >= H[q] and L[sig] <= L[q - 2]) for q in range(max(sig - 60, 2), sig))
    s0 = np.searchsorted(TS, np.datetime64(day)); s7 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7)))
    c2 = s7 > s0 + 30 and (bool(L[s7:sig + 1].min() < L[s0:s7].min()) if bias > 0 else bool(H[s7:sig + 1].max() > H[s0:s7].max()))
    k1 = day + pd.Timedelta(hours=7); c3 = bool(k1 in h1.index and bias * (h1.loc[k1] - e1h.loc[k1]) > 0)
    conf = int(c1) + int(c2) + int(c3); trend = up.get(day, np.nan)
    if not (1.5 <= r <= 6): reason = "risk %.1f outside 1.5-6" % r
    elif COST / r > MAXSHARE: reason = "cost %.0f%% of risk" % (100 * COST / r)
    elif pd.isna(trend) or (bias > 0) != bool(trend): reason = "against the daily trend"
    elif conf < 2: reason = "confluence %d/3" % conf
    else: reason = ""
    sl, tp = e - bias * r, e + bias * r; x = None; j = sig + 1
    while j < min(end + 1, len(C)):
        if j >= end: x = O[j]; break
        if (L[j] <= sl) if bias > 0 else (H[j] >= sl): x = sl; break
        if (H[j] >= tp) if bias > 0 else (L[j] <= tp): x = tp; break
        j += 1
    exit_i = min(j, len(C) - 1); net = (bias * (x - e) - COST) / r if x is not None else np.nan
    out.append(dict(day=day, sig=sig, bias=bias, e=e, sl=sl, tp=tp, r=r, conf=conf, ok=(reason == ""), reason=reason, exit_i=exit_i, net=net))
R = pd.DataFrame(out); taken = R[R.ok]
last = taken.iloc[-1]; day = last.day
w0 = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=7, minutes=30))); w1 = min(int(last.exit_i) + 25, len(C) - 1)
fig = plt.figure(figsize=(13, 7.2), facecolor="#111827"); ax = fig.add_axes([0.04, 0.08, 0.66, 0.84], facecolor="#111827")
xs = np.arange(w0, w1 + 1)
for x in xs:
    col = "#22c55e" if C[x] >= O[x] else "#ef4444"
    ax.plot([x, x], [L[x], H[x]], color=col, lw=0.8)
    ax.add_patch(Rectangle((x - 0.35, min(O[x], C[x])), 0.7, max(abs(C[x] - O[x]), 0.02), color=col))
ax.plot(xs, E[w0:w1 + 1], color="#fb923c", lw=1.2)
ta_ = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8))); tb_ = np.searchsorted(TS, np.datetime64(day + pd.Timedelta(hours=8, minutes=15)))
ax.axvspan(ta_, tb_, color="#3b82f6", alpha=0.12)
s, xe = int(last.sig), int(last.exit_i)
ax.add_patch(Rectangle((s, min(last.e, last.tp)), xe - s, abs(last.tp - last.e), color="#22c55e", alpha=0.22))
ax.add_patch(Rectangle((s, min(last.e, last.sl)), xe - s, abs(last.sl - last.e), color="#ef4444", alpha=0.22))
for y, c, t in ((last.e, "white", "ENTRY %.1f" % last.e), (last.tp, "#22c55e", "TP %.1f  +%.1f pts, 1R" % (last.tp, last.r)), (last.sl, "#ef4444", "SL %.1f  -%.1f pts" % (last.sl, last.r))):
    ax.plot([s, xe], [y, y], color=c, lw=1.8)
    ax.text(xe + 0.5, y, t, color="white", fontsize=9, va="center", bbox=dict(boxstyle="round", fc=c if c != "white" else "#6b7280", ec="none", alpha=0.9))
side = "SHORT" if last.bias < 0 else "LONG"
ax.text(s - 1, last.tp - 1.0 if last.bias < 0 else last.tp + 1.0, "A+ London %s 1:1  conf %d/3" % (side, last.conf), color="white", fontsize=10, ha="right",
        bbox=dict(boxstyle="round", fc="#dc2626" if last.bias < 0 else "#16a34a"))
ax.text(xe, last.tp if last.net > 0 else last.sl, "%+.2fR" % last.net, color="white", fontsize=10, ha="right", va="bottom",
        bbox=dict(boxstyle="round", fc="#16a34a" if last.net > 0 else "#dc2626"))
step = max(1, (w1 - w0) // 8); ax.set_xticks(xs[::step]); ax.set_xticklabels([d.index[x].strftime("%H:%M") for x in xs[::step]], color="#9ca3af", fontsize=8)
ax.tick_params(axis="y", colors="#9ca3af"); [sp.set_color("#374151") for sp in ax.spines.values()]; ax.grid(color="#1f2937", lw=0.6)
ax.set_title("daily-trend-claude | MGC 1m | %s (London time) | blue band = 08:00-08:15 trigger window, orange = EMA12" % day.strftime("%a %d %b %Y"), color="#e5e7eb", fontsize=10, loc="left")
tb = fig.add_axes([0.72, 0.08, 0.26, 0.84], facecolor="#0b1220"); tb.axis("off")
n = len(taken); wr = (taken.net > 0).mean() * 100; tot = taken.net.sum(); l30 = taken[taken.day > taken.day.max() - pd.Timedelta(days=30)]
rows = [("daily-trend-claude", "MGC"), ("London today", "%s %.1f" % (side, last.e)), ("Candidates / trades", "%d / %d" % (len(R), n)), ("Win rate", "%.0f%%" % wr),
        ("Net R, loaded", "%+.2fR (%d)" % (tot, n)), ("Expectancy / trade", "%+.3fR" % (tot / n)), ("Net R, last 30d", "%+.2fR (%d)" % (l30.net.sum(), len(l30))),
        ("Risk per trade", "$500"), ("Backtest (GC 23-26)", "post-hoc lead, not proven")]
y = 0.97
for a_, b_ in rows:
    tb.text(0.02, y, a_, color="#9ca3af", fontsize=9, transform=tb.transAxes); tb.text(0.98, y, b_, color="white", fontsize=9, ha="right", transform=tb.transAxes); y -= 0.05
y -= 0.02; tb.text(0.02, y, "Recent candidates (Aug - 27 Oct)", color="#e5e7eb", fontsize=9, transform=tb.transAxes); y -= 0.045
for r_ in R.tail(11).itertuples():
    if r_.ok: txt = "%s %s %+.2fR" % (r_.day.strftime("%d %b"), "S" if r_.bias < 0 else "L", r_.net)
    else: txt = "%s %s skip: %s" % (r_.day.strftime("%d %b"), "S" if r_.bias < 0 else "L", r_.reason)
    tb.text(0.02, y, txt, color=("#22c55e" if r_.ok and r_.net > 0 else "#ef4444" if r_.ok else "#6b7280"), fontsize=8, transform=tb.transAxes); y -= 0.04
fig.savefig("preview_dt_claude.png", dpi=110, facecolor=fig.get_facecolor())
print("saved; taken", n, "candidates", len(R), "last", day.date(), "%+.2fR" % last.net, "| win %.0f%% total %+.1fR" % (wr, tot))
