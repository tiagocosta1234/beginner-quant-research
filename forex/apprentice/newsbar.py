"""PREREG_NEWSBAR. python newsbar.py --dry-run | --run [--hold]"""
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D
HERE = os.path.dirname(os.path.abspath(__file__)); H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
GRID = list(itertools.product(["CONT", "FADE"], ["FULL", "HALF"])); COST = 0.4
def build(upto):
    d = D.raw(); d = d[(d["lis"] >= "2020-01-01") & (d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1))].reset_index(drop=True)
    out = []
    for day, g in d.groupby(d["lis"].dt.normalize()):
        if day.weekday() >= 5: continue
        x = g[g["lis"] < day + H(21)]
        if len(x) < 900 or x["mc"].diff().abs().max() > 8 * 4: continue
        m = x.set_index("lis"); b = m.resample("15min", label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last"}).dropna()
        rng = b.mh - b.ml; ev = None
        for t in (day + H(12, 30), day + H(13, 30)):
            if t not in b.index: continue
            k = b.index.get_loc(t)
            if k < 20 or k + 1 >= len(b): continue
            if rng.iloc[k] >= 2.5 * rng.iloc[k - 20:k].mean(): ev = k; break
        if ev is None: continue
        o, h, l, c = b.mo.iloc[ev], b.mh.iloc[ev], b.ml.iloc[ev], b.mc.iloc[ev]
        if c == o: continue
        up = c > o; en = b.mo.iloc[ev + 1]; t1 = b.index[ev + 1]; mid = (h + l) / 2
        post = m[m.index >= t1]; lo1, hi1, cl1 = post.ml.values, post.mh.values, post.mc.values
        for dr, st in GRID:
            L = up if dr == "CONT" else (not up)
            if dr == "CONT": stp = ((l - 1.0) if st == "FULL" else (mid - 1.0)) if L else ((h + 1.0) if st == "FULL" else (mid + 1.0))
            else: stp = ((l - 1.0) if st == "FULL" else (mid - 1.0)) if L else ((h + 1.0) if st == "FULL" else (mid + 1.0))
            risk = (en - stp) if L else (stp - en)
            if risk < 3 or risk > 80: continue
            tgt = en + risk if L else en - risk; r = None
            for j in range(len(lo1)):
                if (L and lo1[j] <= stp) or (not L and hi1[j] >= stp): r = -1.0; break
                if (L and hi1[j] >= tgt) or (not L and lo1[j] <= tgt): r = 1.0; break
            if r is None: r = ((cl1[-1] - en) if L else (en - cl1[-1])) / risk
            out.append({"date": day, "v": dr + "/" + st, "R": r - COST / risk, "risk": risk})
    return pd.DataFrame(out)
def stat(r):
    from math import erf, sqrt
    if len(r) < 2: return len(r), np.nan, np.nan, np.nan
    tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))); return len(r), r.mean(), 0.5 * (1 - erf(tt / sqrt(2))), (r > 0).mean()
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        F = build("2022-12-31"); print("DEV counts:", F.groupby("v").size().to_dict(), "median risk %.1f" % F.risk.median())
    elif a[:1] == ["--run"]:
        hold = "--hold" in a; F = build("2025-12-31" if hold else "2024-12-31"); lines = ["variant | DEV n meanR win | VAL n meanR P win | verdict"]; npass = 0
        for dr, st in GRID:
            v = dr + "/" + st; T = F[F.v == v]
            nd, md, _, wd = stat(T[(T.date >= PER["DEV"][0]) & (T.date <= PER["DEV"][1])].R.values)
            nv, mv, pv, wv = stat(T[(T.date >= PER["VAL"][0]) & (T.date <= PER["VAL"][1])].R.values)
            ok = nv >= 40 and mv > 0 and pv <= 0.0125 and md > 0; npass += ok; ex = ""
            if hold: nh, mh, ph, wh = stat(T[(T.date >= PER["HOLD"][0]) & (T.date <= PER["HOLD"][1])].R.values); ex = " | HOLD %d %+.3f P%.3f" % (nh, mh, ph)
            lines.append("%-10s | %4d %+.3f %.0f%% | %4d %+.3f P%.4f %.0f%% | %s%s" % (v, nd, md, 100 * wd, nv, mv, pv, 100 * wv, "PASS" if ok else "fail", ex))
        lines.append("PASSES: %d of 4" % npass); print("\n".join(lines)); open(os.path.join(HERE, "NEWSBAR_OUTPUT%s.txt" % ("_HOLD" if hold else "")), "w").write("\n".join(lines) + "\n")
    else: sys.exit(__doc__)
