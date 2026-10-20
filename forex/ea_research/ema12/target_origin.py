"""Where do his targets come from? (the trader 20 Oct: "check the past trades now, if you cant see where the target's coming from just assume it was a high or a low")
python target_origin.py     PRICES ONLY: side, entry, target and the entry minute of the 30 trades 14 Apr-12 May 2025 (replay_mt5.csv: distances, entry = MT5 broker mid at the entry minute) and the 20 London trades of Jan 2026
(BLIND_LOG_JAN2026.csv). No result is read. For each target: is it within TOL of an edge or the middle of a 1-minute / 5-minute FVG that was visible when the box was drawn (candles completed before the entry minute,
lookback 4 h), else of a recent high / low (extreme of the last 10..240 minutes, a 5-bar swing, the day's high / low so far, the previous day's high / low)? Placebo targets (mirror side, 0.7x, 1.3x, 1.6x the distance)
show how often a level matches by chance. Output TARGET_ORIGIN_OUTPUT.txt / TARGET_ORIGIN.csv."""
import numpy as np, pandas as pd
from blind_score import load_days, TOL as ENTRY_TOL
TOL, LB = 0.40, 240
def mid(g): g = g.copy(); g["mh"] = (g.bh + g.ah) / 2; g["ml"] = (g.bl + g.al) / 2; return g
def gaps(H, L, hm, lb, step):
    out = []; n = len(H)
    for k in range(max(1, n - 1 - lb), n - 1):
        if H[k - 1] < L[k + 1] and L[k + 1] - H[k - 1] >= 0.1: out.append(("bull", H[k - 1], L[k + 1], hm[k + 1] + step))      # zone, minute (server) at which the third candle ended
        if L[k - 1] > H[k + 1] and L[k - 1] - H[k + 1] >= 0.1: out.append(("bear", H[k + 1], L[k - 1], hm[k + 1] + step))
    return out
def fvg_match(zs, tp, t_entry):
    best = None
    for kind, lo, hi, t_end in zs:
        for nm, v in (("low edge", lo), ("high edge", hi), ("middle", (lo + hi) / 2)):
            d = abs(v - tp)
            if d <= TOL and (best is None or d < best[0]): best = (d, kind, nm, hi - lo, t_entry - t_end)
    return best
def bars5(g, i0):
    x = g.iloc[:i0].copy(); x["b"] = x.hm // 5 * 5; a = x.groupby("b").agg(H=("mh", "max"), L=("ml", "min"), n=("hm", "count"), last=("hm", "max")); a = a[a["last"] - a.index >= 4]    # complete bars only
    return a.H.to_numpy(), a.L.to_numpy(), a.index.to_numpy()
def hilo_match(g, i0, tp, short, prev):
    x = g.iloc[:i0]; hit = []
    for w in (10, 20, 30, 60, 120, 240):
        y = x.iloc[-w:]; lv = y.ml.min() if short else y.mh.max()
        if abs(lv - tp) <= TOL: hit.append("%dmin extreme" % w); break
    arr = (x.ml if short else x.mh).to_numpy()[-LB:]
    for k in range(5, len(arr) - 5):
        w = arr[k - 5:k + 6]
        if (arr[k] == w.min() if short else arr[k] == w.max()) and abs(arr[k] - tp) <= TOL: hit.append("5-bar swing"); break
    if len(x) and abs((x.ml.min() if short else x.mh.max()) - tp) <= TOL: hit.append("day extreme so far")
    if prev is not None and abs((prev.ml.min() if short else prev.mh.max()) - tp) <= TOL: hit.append("previous day extreme")
    return hit
def analyse(g, prev, i0, entry, tp, short):
    zs1 = gaps(g.mh.to_numpy()[:i0], g.ml.to_numpy()[:i0], g.hm.to_numpy()[:i0], LB, 1)
    H5, L5, b5 = bars5(g, i0); zs5 = gaps(H5, L5, b5, LB // 5, 5)
    t_entry = int(g.hm[i0]); return fvg_match(zs1, tp, t_entry), fvg_match(zs5, tp, t_entry), hilo_match(g, i0, tp, short, prev)
rows = []
O = pd.read_csv("replay_mt5.csv"); days = load_days("2025-04-14", "2026-01-30"); keys = sorted(days)
def prev_of(d): ks = [k for k in keys if k < d]; return mid(days[ks[-1]]) if ks else None
for _, r in O.iterrows():
    d = pd.Timestamp(r.day).date(); g = mid(days[d]); i0 = g.index[g.hm >= r.hm][0]; ent = g.mo[i0]; short = r.side == "S"; tp = ent - r.rew if short else ent + r.rew
    rows.append(dict(set="Apr-May 2025", date=str(d), ses=r.ses, side=r.side, entry=ent, target=tp, dist=r.rew, g=g, prev=prev_of(d), i0=i0))
J = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"])]
for _, r in J.iterrows():
    d = pd.Timestamp(r.date).date(); g = mid(days[d]); hm = int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 121; i0 = g.index[g.hm >= hm][0]
    if abs(g.mo[i0] - r.entry) > ENTRY_TOL:
        near = range(max(i0 - 5, 0), min(i0 + 6, len(g))); b = min(near, key=lambda i: abs(g.mo[i] - r.entry))
        if abs(g.mo[b] - r.entry) <= ENTRY_TOL: i0 = b
    rows.append(dict(set="Jan 2026", date=str(d), ses=r.ses, side=r.side, entry=r.entry, target=r.target, dist=abs(r.target - r.entry), g=g, prev=prev_of(d), i0=i0))
out = []
for q in rows:
    short = q["side"] == "S"; f1, f5, hl = analyse(q["g"], q["prev"], q["i0"], q["entry"], q["target"], short)
    pl = {}
    for nm, lv in (("mirror", q["entry"] + q["dist"] if short else q["entry"] - q["dist"]), ("0.7x", q["entry"] + (-0.7 if short else 0.7) * q["dist"]), ("1.3x", q["entry"] + (-1.3 if short else 1.3) * q["dist"]), ("1.6x", q["entry"] + (-1.6 if short else 1.6) * q["dist"])):
        a1, a5, ah = analyse(q["g"], q["prev"], q["i0"], q["entry"], lv, short if nm != "mirror" else not short); pl[nm] = (a1 is not None, a5 is not None, bool(ah))
    kind = "FVG 1m" if f1 else ("FVG 5m" if f5 else "High/Low (assumed)")
    out.append(dict(set=q["set"], date=q["date"], ses=q["ses"], side=q["side"], dist=round(q["dist"], 2), tipo=kind, f1=f1, f5=f5, hl=";".join(hl), pl=pl))
Z = pd.DataFrame(out); n = len(Z)
print("%d trades (30 Apr-May 2025 in-sample, 20 Jan 2026 blind log); tolerance %.2f; FVG lookback 4 h; prices only, no results used\n" % (n, TOL))
print("per trade (matched FVG: kind, which level, width, minutes since it formed):")
for _, z in Z.iterrows():
    m = z.f1 or z.f5; tf = "1m" if z.f1 else "5m"
    print("  %s %s %-6s %s target %5.2f away | %-18s%s | hi/lo: %s" % (z.set[:7], z.date, z.ses, z.side, z.dist, z.tipo, (" [%s %s %s, width %.2f, %d min old]" % (tf, m[1], m[2], m[3], m[4])) if m else "", z.hl or "-"))
print("\ncounts (target matched within %.2f):" % TOL)
for lab, sub in (("all 50", Z), ("Apr-May 2025 (30)", Z[Z.set == "Apr-May 2025"]), ("Jan 2026 (20)", Z[Z.set == "Jan 2026"])):
    k1 = sub.f1.notna().sum(); k5 = (sub.f5.notna() & sub.f1.isna()).sum(); kh = ((sub.f1.isna()) & (sub.f5.isna()) & (sub.hl != "")).sum(); k0 = ((sub.f1.isna()) & (sub.f5.isna()) & (sub.hl == "")).sum()
    print("  %-18s n %2d | on a 1-min FVG %2d | only on a 5-min FVG %2d | no FVG but on a recent high/low %2d | neither (assumed high/low) %2d" % (lab, len(sub), k1, k5, kh, k0))
print("\nchance level: share of PLACEBO levels (same trades) that match an FVG / a high-low (real targets: FVG 1m %.0f%%, FVG 1m or 5m %.0f%%, hi/lo %.0f%%)" % (100 * Z.f1.notna().mean(), 100 * (Z.f1.notna() | Z.f5.notna()).mean(), 100 * (Z.hl != "").mean()))
for nm in ("mirror", "0.7x", "1.3x", "1.6x"):
    a = np.array([[p[nm][0], p[nm][1], p[nm][2]] for p in Z.pl]); print("  %-7s 1-min FVG %3.0f%% | 1m or 5m FVG %3.0f%% | high/low %3.0f%%" % (nm, 100 * a[:, 0].mean(), 100 * (a[:, 0] | a[:, 1]).mean(), 100 * a[:, 2].mean()))
W = np.array([(z.f1 or z.f5)[3] for _, z in Z.iterrows() if (z.f1 or z.f5)]); R = np.array([(z.f1 or z.f5)[3] / z.dist for _, z in Z.iterrows() if (z.f1 or z.f5)])
if len(W): print("\nwidth of the matched FVGs (points): min %.2f, 25%% %.2f, median %.2f, 75%% %.2f, max %.2f | width / target distance: median %.2f" % (W.min(), *np.quantile(W, [.25, .5, .75]), W.max(), np.median(R)))
Z.drop(columns=["f1", "f5", "pl"]).to_csv("TARGET_ORIGIN.csv", index=False)
