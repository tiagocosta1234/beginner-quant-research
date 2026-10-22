"""DESCRIPTIVE (22 Oct, the trader: 'from all recorded trades, whats the equity curve ... X-axis the number of trades, Y-axis the R return'): cumulative R over his 50 recorded trades in time order (30 Apr-May 2025 replay, 20 blind Jan 2026),
MT5 broker bid / ask at a 0.48 spread, entries and stops as he logged them: (1) the target as he logged it (about 0.53 R, the primary), (2) S1 = the same entries and stops with a 1.0 R target.
Post-hoc: S1 was looked at after these trades existed. python -B manual_equity_curve.py  ->  MANUAL_EQUITY_CURVE.png, MANUAL_EQUITY_CURVE.csv"""
import sys, io, contextlib, numpy as np, pandas as pd
sys.dont_write_bytecode = True
with contextlib.redirect_stdout(io.StringIO()):
    import manual_fixed_bracket as K
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
b, s1 = K.trades(), K.Zown
D = pd.DataFrame(dict(trade=np.arange(1, 51), date=b.date.astype(str).to_numpy(), side=b.side.to_numpy(), session=b.ses.to_numpy(), period=b.per.to_numpy(), R_logged=b.R_mine.to_numpy(), R_S1=s1.R_mine.to_numpy()))
D["cum_logged"] = D.R_logged.cumsum(); D["cum_S1"] = D.R_S1.cumsum()
D.round(4).to_csv("MANUAL_EQUITY_CURVE.csv", index=False)
def dd(c):
    x = np.concatenate([[0], c]); peak = np.maximum.accumulate(x); return (peak - x).max()
def streak(r):
    m = cur = 0
    for v in r:
        cur = cur + 1 if v < 0 else 0; m = max(m, cur)
    return m
for lab, col in (("as logged (target about 0.53 R)", "R_logged"), ("S1 (his stop, 1.0 R target)", "R_S1")):
    r = D[col].to_numpy(); cum = r.cumsum()
    print("%-32s final %+6.2f R | mean %+.3f R/trade | wins %d/50 | max drawdown %.2f R | longest losing streak %d | Apr-May 30: %+.2f R, Jan 20: %+.2f R" % (lab, cum[-1], r.mean(), (r > 0).sum(), dd(cum), streak(r), r[:30].sum(), r[30:].sum()))
SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
BLUE, ORANGE = "#2a78d6", "#eb6834"                                  # categorical slots 1 and 2 of the reference palette, in fixed order
fig, ax = plt.subplots(figsize=(9.2, 5.4), dpi=170); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
x = np.arange(0, 51)
for col, c, lab in (("cum_logged", BLUE, "As logged (target about 0.53 R)"), ("cum_S1", ORANGE, "S1: his stop, 1.0 R target")):
    y = np.concatenate([[0], D[col].to_numpy()]); ax.plot(x, y, color=c, lw=2, label=lab, solid_joinstyle="round", zorder=3)
    ax.plot([50], [y[-1]], marker="o", ms=8, color=c, mec=SURF, mew=2, zorder=4)
    ax.annotate("%+.1f R" % y[-1], (50, y[-1]), xytext=(8, 0), textcoords="offset points", va="center", ha="left", color=INK, fontsize=10, fontweight="bold")
ax.axhline(0, color=MUTED, lw=1, zorder=1)
ax.axvline(30.5, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
ymax = D[["cum_logged", "cum_S1"]].to_numpy().max()
ax.text(15.5, ymax * 1.07, "Apr-May 2025 replay (30 trades, in-sample)", ha="center", va="bottom", color=INK2, fontsize=9)
ax.text(40.5, ymax * 1.07, "Jan 2026 blind (20 trades)", ha="center", va="bottom", color=INK2, fontsize=9)
ax.set_xlim(0, 56); ax.set_ylim(min(-3.5, D[["cum_logged", "cum_S1"]].to_numpy().min() - 1), ymax * 1.18)
ax.set_xticks(range(0, 51, 5)); ax.set_xlabel("Trade number (time order, 50 recorded trades)", color=INK2, fontsize=10); ax.set_ylabel("Cumulative R", color=INK2, fontsize=10)
ax.grid(axis="y", color=GRID, lw=1, zorder=0); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(MUTED); ax.tick_params(colors=INK2, labelsize=9, length=0)
leg = ax.legend(loc="upper left", frameon=False, fontsize=10, bbox_to_anchor=(0.0, 0.93))
for t in leg.get_texts(): t.set_color(INK)
fig.suptitle("Cumulative R over his 50 recorded trades", x=0.07, y=0.985, ha="left", color=INK, fontsize=13, fontweight="bold")
fig.text(0.07, 0.925, "MT5 broker bid / ask, spread 0.48, entries and stops as he logged them. S1 was chosen after seeing these trades (post-hoc).", ha="left", color=INK2, fontsize=9)
fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.12); fig.savefig("MANUAL_EQUITY_CURVE.png", facecolor=SURF)
print("saved MANUAL_EQUITY_CURVE.png and .csv")
