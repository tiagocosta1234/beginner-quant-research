"""DESCRIPTIVE ONLY (21 Oct, the trader: 'show me an image that compares my old setups to your suggestion'): his 50 replay entries and stops, MT5 broker bid / ask with the spread forced to 0.48,
the target he used (about 0.53 of the stop) against a target of 1.0 R and 1.5 R. Post-hoc on the same trades, not a rule. python manual_target_compare_chart.py -> MANUAL_TARGET_COMPARE.png"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from blind_score import load_days, score
S = 0.48
O = pd.read_csv("replay_mt5.csv"); h = O.hm - 120
A = pd.DataFrame(dict(date=O.day, ses=O.ses, side=O.side, hhmm=["%02d:%02d" % (x // 60, x % 60) for x in h], entry=np.nan, risk=O.risk, rew=O.rew, flag=0))
J = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"]) & (J.ses == "London") & (J.flag == 0) & (J.pre == 1)].copy()
J["risk"] = (J.entry - J.stop).abs(); J["rew"] = (J.target - J.entry).abs()
def reprice(days):
    out = {}
    for k, g in days.items():
        g = g.copy()
        for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): g[a] = g[b] + S
        g["mo"] = g.bo + S / 2; out[k] = g
    return out
dA, dJ = reprice(load_days("2025-04-14", "2025-05-12")), reprice(load_days("2026-01-02", "2026-01-30"))
def R(ratio):
    a, j = A.copy(), J.copy()
    if ratio: a["rew"] = ratio * a.risk; j["rew"] = ratio * j.risk
    return score(a, dA, lag=0).R_mine.to_numpy(), score(j, dJ, lag=1).R_mine.to_numpy()
res = {k: R(v) for k, v in (("old", None), ("r10", 1.0), ("r15", 1.5))}
nA, nJ = len(A), len(J)
col = {"old": "#7a7a7a", "r10": "#12805c", "r15": "#3b7dd8"}; lab = {"old": "old: target about 0.53 x stop", "r10": "suggestion: target 1.0 x stop", "r15": "target 1.5 x stop"}
rng = np.random.default_rng(5)
def ci(x): b = np.sort([rng.choice(x, len(x)).mean() for _ in range(4000)]); return b[100], b[3900]

fig, ax = plt.subplots(2, 2, figsize=(15, 9.6)); fig.patch.set_facecolor("white")
fig.suptitle("Your 12 EMA entries and stops (50 replay trades), MT5 broker bid/ask at a 0.48 spread: old 0.53 target vs wider targets\n(same entries, same stops; post-hoc on the same trades, descriptive, not a rule)", fontsize=13, y=0.995)

a = ax[0, 0]
for k in ("old", "r10", "r15"):
    c = np.cumsum(np.r_[res[k][0], res[k][1]]); a.plot(range(0, 51), np.r_[0, c], color=col[k], lw=2.4 if k != "r15" else 1.6, ls="-" if k != "r15" else "--", label="%s: %+.1f R" % (lab[k], c[-1]))
a.axvline(nA, color="k", lw=1, ls=":"); lo_, hi_ = a.get_ylim(); a.set_ylim(lo_ - 3.0, hi_)
a.text(nA / 2, lo_ - 2.8, "Apr-May 2025 (the rule was built on these)", ha="center", va="bottom", fontsize=9)
a.text(nA + nJ / 2, lo_ - 2.8, "Jan 2026 (blind)", ha="center", va="bottom", fontsize=9)
a.set_title("A. Running total of R, all 50 trades in order"); a.set_xlabel("trade number"); a.set_ylabel("cumulative R"); a.legend(loc="upper left", fontsize=9); a.grid(alpha=.25); a.axhline(0, color="k", lw=.6)

a = ax[0, 1]
for k in ("old", "r10", "r15"):
    c = np.cumsum(res[k][1]); a.plot(range(0, nJ + 1), np.r_[0, c], color=col[k], lw=2.4 if k != "r15" else 1.6, ls="-" if k != "r15" else "--", marker="o", ms=3.5, label="%s: %+.2f R" % (lab[k], c[-1]))
a.set_xticks(range(0, nJ + 1, 2)); a.set_title("B. Only the 20 blind January trades (the honest sample)"); a.set_xlabel("trade number (2 Jan to 30 Jan 2026)"); a.set_ylabel("cumulative R"); a.legend(loc="upper left", fontsize=9); a.grid(alpha=.25); a.axhline(0, color="k", lw=.6)

a = ax[1, 0]; groups = (("All 50", np.r_[0:nA + nJ]), ("Apr-May 2025 (30)", np.r_[0:nA]), ("Jan 2026 blind (20)", np.r_[nA:nA + nJ])); w = 0.26
for i, k in enumerate(("old", "r10", "r15")):
    allr = np.r_[res[k][0], res[k][1]]
    for g, (nm, idx) in enumerate(groups):
        x = allr[idx]; m = x.mean(); lo, hi = ci(x)
        a.bar(g + (i - 1) * w, m, w * 0.92, color=col[k], label=lab[k] if g == 0 else None)
        a.errorbar(g + (i - 1) * w, m, yerr=[[m - lo], [hi - m]], color="k", lw=1, capsize=3); a.text(g + (i - 1) * w, hi + 0.02, "%+.2f" % m, ha="center", fontsize=8.5)
a.set_xticks(range(3)); a.set_xticklabels([g[0] for g in groups]); a.axhline(0, color="k", lw=.8); a.set_ylabel("mean R per trade (bars: 95% bootstrap range)")
a.set_title("C. Average R per trade (the whiskers cross zero for 20 trades: not proven)"); a.set_ylim(-0.42, 1.18); a.legend(fontsize=9, loc="upper center", ncol=3); a.grid(alpha=.25, axis="y")

a = ax[1, 1]
rows = []
for (_, r), z in zip(J.iterrows(), res["old"][1]):
    g = dJ[pd.Timestamp(r.date).date()]; hm = int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 120 + 1; i0 = g.index[g.hm >= hm][0]; risk = r.risk
    seg = g.loc[i0:]; seg = seg[seg.hm < 19 * 60]
    if r.side == "L": ent = g.ao[i0]; fav = (seg.bh - ent).cummax() / risk; adv = (ent - seg.bl) / risk
    else: ent = g.bo[i0]; fav = (ent - seg.al).cummax() / risk; adv = (seg.ah - ent) / risk
    st = next((k for k, v in enumerate(adv.to_numpy()) if v >= 1.0), None)
    rows.append((str(r.date)[5:], z > 0, fav.iloc[:st].max() if st else fav.max()))
CAPV = 6.0
for i, (d, win, m) in enumerate(rows):
    a.bar(i, min(m, CAPV), color="#12805c" if win else "#c0392b", width=.75)
    if m > CAPV: a.text(i, CAPV + 0.1, "%.0f R" % m, ha="center", fontsize=8, rotation=90, va="bottom")
a.axhline(0.53, color=col["old"], lw=2, ls="--"); a.axhline(1.0, color=col["r10"], lw=2, ls="--")
from matplotlib.lines import Line2D; from matplotlib.patches import Patch
a.legend(handles=[Line2D([0], [0], color=col["old"], lw=2, ls="--", label="old target (0.53 R)"), Line2D([0], [0], color=col["r10"], lw=2, ls="--", label="suggested target (1.0 R)"), Patch(color="#12805c", label="won at the old target"), Patch(color="#c0392b", label="lost at the old target")], loc="upper center", ncol=2, fontsize=9)
a.set_xticks(range(len(rows))); a.set_xticklabels([r[0] for r in rows], rotation=70, fontsize=8); a.set_ylim(0, CAPV + 2.0)
a.set_ylabel("best run before the stop, in R"); a.set_title("D. Why: winners kept running, losers never got going (Jan 2026 blind)", fontsize=11.5)
a.grid(alpha=.25, axis="y"); plt.tight_layout(rect=(0, 0.02, 1, 0.965))
fig.text(0.5, 0.005, "Caveats: four target ratios were looked at on these same trades; Jan 2026 gold was a violent trend and crash; wins at wide targets include trades closed at 17:00. Only the 20 January trades were logged blind.", ha="center", fontsize=8.5, color="#444")
plt.savefig("MANUAL_TARGET_COMPARE.png", dpi=130); print("saved MANUAL_TARGET_COMPARE.png")
for k in ("old", "r10", "r15"): print(k, "sum all %+.2f | Apr-May %+.2f | Jan %+.2f" % (np.r_[res[k][0], res[k][1]].sum(), res[k][0].sum(), res[k][1].sum()))
