"""Second look at where his targets come from: sharper than target_origin.py (which matches ANY FVG of the last 4 h and so matches placebo levels as often as real targets). PRICES ONLY, no results.
python target_origin2.py
(1) Is the target on a level of the NEAREST (or the nearest 2) UNFILLED 1-minute FVG in the trade direction (unfilled = no candle since its formation overlapped the zone), real target against the same placebo levels as before?
(2) Widths of all 1-minute FVGs that were visible, against the widths of the ones his targets sit on."""
import numpy as np, pandas as pd
from blind_score import load_days, TOL as ENTRY_TOL
TOL, LB, MINW = 0.40, 240, 0.10
def mid(g): g = g.copy(); g["mh"] = (g.bh + g.ah) / 2; g["ml"] = (g.bl + g.al) / 2; return g
def zones(g, i0):
    H, L = g.mh.to_numpy(), g.ml.to_numpy(); out = []
    for k in range(max(1, i0 - 1 - LB), i0 - 1):
        for kind, lo, hi in (("bull", H[k - 1], L[k + 1]), ("bear", H[k + 1], L[k - 1])):
            if hi - lo >= MINW and (H[k - 1] < L[k + 1] if kind == "bull" else L[k - 1] > H[k + 1]):
                later = slice(k + 2, i0); filled = bool(((L[later] <= hi) & (H[later] >= lo)).any()); out.append((kind, lo, hi, filled))
    return out
def levels(zs, entry, short, nearest):
    cand = [z for z in zs if not z[3] and ((z[2] <= entry) if short else (z[1] >= entry))]
    cand.sort(key=lambda z: -z[2] if short else z[1]); res = []
    for z in cand[:nearest]: res += [z[2], z[1], (z[1] + z[2]) / 2] if short else [z[1], z[2], (z[1] + z[2]) / 2]
    return res, len(cand)
rows = []; O = pd.read_csv("replay_mt5.csv"); days = load_days("2025-04-14", "2026-01-30")
for _, r in O.iterrows():
    d = pd.Timestamp(r.day).date(); g = mid(days[d]); i0 = g.index[g.hm >= r.hm][0]; ent = g.mo[i0]; short = r.side == "S"
    rows.append(dict(g=g, i0=i0, entry=ent, dist=r.rew, short=short, tp=ent - r.rew if short else ent + r.rew))
J = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"])]
for _, r in J.iterrows():
    d = pd.Timestamp(r.date).date(); g = mid(days[d]); hm = int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 121; i0 = g.index[g.hm >= hm][0]
    if abs(g.mo[i0] - r.entry) > ENTRY_TOL:
        b = min(range(max(i0 - 5, 0), min(i0 + 6, len(g))), key=lambda i: abs(g.mo[i] - r.entry))
        if abs(g.mo[b] - r.entry) <= ENTRY_TOL: i0 = b
    rows.append(dict(g=g, i0=i0, entry=r.entry, dist=abs(r.target - r.entry), short=r.side == "S", tp=r.target))
n = len(rows); res = {k: [] for k in ("real", "mirror", "0.7x", "1.3x", "1.6x")}; none_ = 0; allw, matw = [], []; cnt = []
for q in rows:
    zs = zones(q["g"], q["i0"]); allw += [z[2] - z[1] for z in zs]; cnt.append(len(zs)); s, e, dd = q["short"], q["entry"], q["dist"]
    lv1, c1 = levels(zs, e, s, 1); lv2, c2 = levels(zs, e, s, 2); none_ += c1 == 0
    tps = {"real": q["tp"], "mirror": e + dd if s else e - dd, "0.7x": e + (-0.7 if s else 0.7) * dd, "1.3x": e + (-1.3 if s else 1.3) * dd, "1.6x": e + (-1.6 if s else 1.6) * dd}
    for k, tp in tps.items():
        lvm, _ = levels(zs, e, (not s) if k == "mirror" else s, 1); lvm2, _ = levels(zs, e, (not s) if k == "mirror" else s, 2)
        res[k].append((any(abs(v - tp) <= TOL for v in lvm), any(abs(v - tp) <= TOL for v in lvm2)))
    for z in zs:
        if any(abs(v - q["tp"]) <= TOL for v in (z[1], z[2], (z[1] + z[2]) / 2)): matw.append(z[2] - z[1])
print("%d trades; unfilled-FVG test (tolerance %.2f, lookback 4 h)" % (n, TOL))
print("trades with no unfilled FVG on the target side at all: %d | median FVGs visible per trade (all, filled or not): %d" % (none_, int(np.median(cnt))))
print("share of targets on a level (near edge, far edge or middle) of the NEAREST unfilled 1-min FVG / of the nearest TWO:")
for k in res: a = np.array(res[k]); print("  %-7s nearest %3.0f%% | nearest two %3.0f%%" % (k + (" (his)" if k == "real" else " (placebo)"), 100 * a[:, 0].mean(), 100 * a[:, 1].mean()))
aw, mw = np.array(allw), np.array(matw)
print("\nwidths (points) of ALL 1-min FVGs visible (n %d): 25%% %.2f, median %.2f, 75%% %.2f | of the FVG levels his targets sit on (n %d, one trade can match several): 25%% %.2f, median %.2f, 75%% %.2f" % (len(aw), *np.quantile(aw, [.25, .5, .75]), len(mw), *np.quantile(mw, [.25, .5, .75])))
print("share of visible FVGs narrower than 1.0 point: %.0f%% | of the ones his targets sit on: %.0f%%" % (100 * (aw < 1).mean(), 100 * (mw < 1).mean()))
