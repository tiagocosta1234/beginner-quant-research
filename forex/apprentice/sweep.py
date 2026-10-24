"""PREREG_SWEEP. python sweep.py --dry-run | --run [--hold]"""
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D
HERE = os.path.dirname(os.path.abspath(__file__)); H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
GRID = list(itertools.product(["PD", "PD+AS"], ["none", "trend"])); COST = 0.4
def build(upto):
    d = D.raw(); d = d[(d["lis"] >= "2019-10-01") & (d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1))].reset_index(drop=True)
    G = {k: g.reset_index(drop=True) for k, g in d.groupby(d["lis"].dt.normalize())}
    dc = pd.Series({k: g[g["lis"] < k + H(22)]["mc"].iloc[-1] for k, g in G.items() if (g["lis"] < k + H(22)).any()}).sort_index()
    days = sorted(G); out = []
    for i, day in enumerate(days):
        if day.weekday() >= 5 or day < pd.Timestamp("2020-01-01") or i == 0: continue
        g = G[day]; x = g[g["lis"] < day + H(21)]
        if len(x) < 900 or x["mc"].diff().abs().max() > 8: continue
        p = G[days[i - 1]]; pv = p[(p["lis"] >= days[i - 1] + H(8)) & (p["lis"] < days[i - 1] + H(22))]; past = dc[dc.index < day]
        if len(pv) < 300 or len(past) < 21: continue
        dtr = np.sign(past.iloc[-1] - past.iloc[-20:].mean()); asia = x[x["lis"] < day + H(8)]
        if len(asia) < 200: continue
        m = x[x["lis"] >= day + H(8)].set_index("lis")
        b = m.resample("15min", label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last"}).dropna()
        lo1, hi1, cl1 = m.ml.values, m.mh.values, m.mc.values; tix = m.index
        for lv, trn in GRID:
            sup = [pv.ml.min()] + ([asia.ml.min()] if lv == "PD+AS" else []); res = [pv.mh.max()] + ([asia.mh.max()] if lv == "PD+AS" else [])
            sig = None
            for k in range(len(b) - 1):
                t = b.index[k]
                if t > day + H(16, 30): break
                bl, bh, bc = b.ml.iloc[k], b.mh.iloc[k], b.mc.iloc[k]
                if any(bl < s < bc for s in sup) and (trn == "none" or dtr > 0): sig = ("L", k, bl - 1.0); break
                if any(bh > r > bc for r in res) and (trn == "none" or dtr < 0): sig = ("S", k, bh + 1.0); break
            if sig is None: continue
            side, k, stp = sig; t1 = b.index[k + 1]; en = b.mo.iloc[k + 1]; L = side == "L"; risk = (en - stp) if L else (stp - en)
            if risk < 3 or risk > 60: continue
            tgt = en + risk if L else en - risk; j0 = np.searchsorted(tix.values, t1.to_datetime64()); r = None
            for j in range(j0, len(lo1)):
                if (L and lo1[j] <= stp) or (not L and hi1[j] >= stp): r = -1.0; break
                if (L and hi1[j] >= tgt) or (not L and lo1[j] <= tgt): r = 1.0; break
            if r is None: r = ((cl1[-1] - en) if L else (en - cl1[-1])) / risk
            out.append({"date": day, "v": lv + "/" + trn, "side": side, "risk": risk, "R": r - COST / risk})
    return pd.DataFrame(out)
def stat(r):
    from math import erf, sqrt
    if len(r) < 2: return len(r), np.nan, np.nan, np.nan
    tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))); return len(r), r.mean(), 0.5 * (1 - erf(tt / sqrt(2))), (r > 0).mean()
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        F = build("2022-12-31"); dv = F[F.date <= "2022-12-31"]; print("DEV counts:", dv.groupby("v").size().to_dict(), "median risk %.1f" % dv.risk.median())
    elif a[:1] == ["--run"]:
        hold = "--hold" in a; F = build("2025-12-31" if hold else "2024-12-31"); lines = ["variant | DEV n meanR win | VAL n meanR P win | verdict"]; npass = 0
        for lv, trn in GRID:
            v = lv + "/" + trn; T = F[F.v == v]
            nd, md, _, wd = stat(T[(T.date >= PER["DEV"][0]) & (T.date <= PER["DEV"][1])].R.values)
            nv, mv, pv, wv = stat(T[(T.date >= PER["VAL"][0]) & (T.date <= PER["VAL"][1])].R.values)
            ok = nv >= 60 and mv > 0 and pv <= 0.0125 and md > 0; npass += ok; ex = ""
            if hold: nh, mh, ph, wh = stat(T[(T.date >= PER["HOLD"][0]) & (T.date <= PER["HOLD"][1])].R.values); ex = " | HOLD %d %+.3f P%.3f win %.0f%%" % (nh, mh, ph, 100 * wh)
            lines.append("%-14s | %4d %+.3f %.0f%% | %4d %+.3f P%.4f %.0f%% | %s%s" % (v, nd, md, 100 * wd, nv, mv, pv, 100 * wv, "PASS" if ok else "fail", ex))
        lines.append("PASSES: %d of 4" % npass); print("\n".join(lines)); open(os.path.join(HERE, "SWEEP_OUTPUT%s.txt" % ("_HOLD" if hold else "")), "w").write("\n".join(lines) + "\n")
    else: sys.exit(__doc__)
