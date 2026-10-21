"""ILLUSTRATION ONLY (21 Oct, the trader: 'pick a random setup from notion and duplicate it with the second one showing the new box'): one of his 51 Notion setups picked by a random number generator,
drawn twice on MT5 1-minute candles (shifted to his chart prices): the box as he took it (target about 0.53 R) and the duplicate with a 1.0 R target. Hindsight picture, not evidence.
python manual_random_setup_chart.py [row 0-50; omit = random]  -> MANUAL_RANDOM_SETUP.png"""
import sys, random, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from blind_score import load_days, run
# the pick: 5 Jan 2026 London long from the Notion row 'Replay jan 2026 · seg 5 Jan' (index 31 of 51 rows with a direction, drawn by SystemRandom)
DAY, SIDE, ENTRY, STOP, TARGET = "2026-01-05", "L", 4422.995, 4416.679, 4426.52
risk, rew_old = ENTRY - STOP, TARGET - ENTRY; rew_new = 1.0 * risk
days = load_days("2026-01-02", DAY); g = days[pd.Timestamp(DAY).date()].copy()
full = pd.concat([days[k] for k in sorted(days)]).reset_index(drop=True); full["mc"] = (full.bc + full.ac) / 2; full["mh"] = (full.bh + full.ah) / 2; full["ml"] = (full.bl + full.al) / 2; full["ema"] = full.mc.ewm(span=12, adjust=False).mean()
g = full[full.dt.dt.date == pd.Timestamp(DAY).date()].reset_index(drop=True)
g["lis"] = g.dt - pd.Timedelta(hours=2)                         # MT5 broker server clock -> local (= UTC in January)
g["hmL"] = g.lis.dt.hour * 60 + g.lis.dt.minute
i0 = g.index[g.hmL == 8 * 60 + 1][0]                             # signal candle 08:00, entry at the 08:01 open (as blind_score, lag 1)
off = ENTRY - g.mo[i0]; print("shift of the MT5 broker candles to his chart prices: %+.3f" % off)
def first_hit(rew):
    ent = g.ao[i0]; tp, sl = ent + rew, ent - risk
    for j in range(i0, len(g)):
        if g.bl[j] <= sl: return j, "STOP"
        if g.bh[j] >= tp: return j, "TARGET"
    return len(g) - 1, "open"
res = {k: first_hit(r) for k, r in (("old", rew_old), ("new", rew_new))}
Rold, Rnew = run(g, i0, "L", risk, rew_old, 19 * 60), run(g, i0, "L", risk, rew_new, 19 * 60)
print("old: %s at %s R %+.3f | new: %s at %s R %+.3f" % (res["old"][1], g.lis[res["old"][0]].strftime("%H:%M"), Rold, res["new"][1], g.lis[res["new"][0]].strftime("%H:%M"), Rnew))
w = g[(g.hmL >= 7 * 60 + 50) & (g.hmL <= 8 * 60 + 45)].copy()
x0 = (w.hmL - (8 * 60 + 1)).to_numpy()                           # minutes after the entry candle
def candles(a):
    for _, r in w.iterrows():
        x = r.hmL - (8 * 60 + 1); o, c, h, l = r.mo + off, r.mc + off, r.mh + off, r.ml + off
        a.plot([x, x], [l, h], color="#555", lw=.8, zorder=2); up = c >= o
        a.add_patch(Rectangle((x - .32, min(o, c)), .64, max(abs(c - o), .04), facecolor="#12805c" if up else "#c0392b", edgecolor="none", zorder=3))
    a.plot(w.hmL - (8 * 60 + 1), w.ema + off, color="#e0a800", lw=1.4, zorder=4, label="EMA 12")
fig, ax = plt.subplots(1, 2, figsize=(16, 7.4), sharey=True); fig.patch.set_facecolor("white")
fig.suptitle("Random setup from Notion: Mon 5 Jan 2026, London, Long, entry 4422.995 (blind replay trade)\nleft: the box as you took it   |   right: the duplicate with the new 1.0 R target", fontsize=13)
for a, which in zip(ax, ("old", "new")):
    candles(a); end = res[which][0]; xe = g.hmL[end] - (8 * 60 + 1); rew = rew_old if which == "old" else rew_new; xe = max(xe, 3)
    a.add_patch(Rectangle((0, ENTRY), xe, rew, facecolor="#12805c", alpha=.22, zorder=1)); a.add_patch(Rectangle((0, ENTRY - risk), xe, risk, facecolor="#c0392b", alpha=.22, zorder=1))
    a.hlines(ENTRY, 0, xe, color="#222", lw=1.4, zorder=5); a.hlines(STOP, 0, xe, color="#c0392b", lw=1.4, zorder=5); a.hlines(ENTRY + rew, 0, xe, color="#12805c", lw=1.8, zorder=5)
    a.text(xe + .5, ENTRY + rew, "target %.3f  (+%.2f = %.2f R)" % (ENTRY + rew, rew, rew / risk), va="center", fontsize=10, color="#12805c", fontweight="bold", bbox=dict(facecolor="white", alpha=.88, edgecolor="none", pad=1.5), zorder=8)
    a.text(xe + .5, ENTRY, "entry %.3f" % ENTRY, va="center", fontsize=10, bbox=dict(facecolor="white", alpha=.88, edgecolor="none", pad=1.5), zorder=8); a.text(xe + .5, STOP, "stop %.3f  (-%.2f = 1 R)" % (STOP, risk), va="center", fontsize=10, color="#c0392b", bbox=dict(facecolor="white", alpha=.88, edgecolor="none", pad=1.5), zorder=8)
    if which == "new": a.hlines(TARGET, 0, xe, color="#7a7a7a", lw=1.4, ls="--", zorder=5); a.text(xe + .5, TARGET, "old target %.3f (0.56 R, hit 08:%02d)" % (TARGET, g.hmL[res['old'][0]] - 480), va="center", fontsize=9.5, color="#555", bbox=dict(facecolor="white", alpha=.88, edgecolor="none", pad=1.5), zorder=8)
    ttl = "OLD box: target 0.56 R | hit %s at %s | R %+.2f" if which == "old" else "NEW box: target 1.0 R | hit %s at %s | R %+.2f"
    a.set_title(ttl % (res[which][1].lower(), g.lis[end].strftime("%H:%M"), Rold if which == "old" else Rnew), fontsize=12, color="#12805c" if (Rold if which == "old" else Rnew) > 0 else "#c0392b")
    a.set_xlim(-10, 44); a.set_xticks(range(-10, 45, 5)); a.set_xticklabels([(pd.Timestamp("2026-01-05 08:01") + pd.Timedelta(minutes=m)).strftime("%H:%M") for m in range(-10, 45, 5)], fontsize=9)
    a.set_xlabel("local time, 1-minute candles"); a.grid(alpha=.2); a.axvline(0, color="#999", lw=.8, ls=":")
ax[0].set_ylim(STOP - 1.5, ENTRY + rew_new + 2.2); ax[0].set_ylabel("price (his chart prices)"); ax[0].legend(loc="upper left", fontsize=9)
fig.text(0.5, 0.012, "Picked with a random number generator among the 51 Notion rows with a direction. Candles from MT5 broker's feed (bid / ask mid), shifted by %+.2f to match your chart prices.\nTradingView's 1-minute history here only reaches back to 19 Oct, so this is rendered, not a TradingView drawing. R on MT5 broker bid/ask with the spread of the day.\nA box drawn after the move is an illustration, not evidence; one trade says nothing about the edge." % off, ha="center", fontsize=8.5, color="#444")
plt.tight_layout(rect=(0, 0.07, 1, 0.94)); plt.savefig("MANUAL_RANDOM_SETUP.png", dpi=125); print("saved")
