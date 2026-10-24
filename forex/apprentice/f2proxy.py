"""PREREG_F2PROXY: 2R vs 1R target on a mechanical proxy of F1 entries. python f2proxy.py --dry-run | --run [--hold]"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D
HERE = os.path.dirname(os.path.abspath(__file__)); H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
KS = [1.0, 1.5, 2.0, 3.0]; COST = 0.4

def trades(upto):
    d = D.raw(); d = d[(d["lis"] >= "2019-10-01") & (d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1))].reset_index(drop=True)
    G = {k: g.reset_index(drop=True) for k, g in d.groupby(d["lis"].dt.normalize())}
    h1 = d.set_index("lis")["mc"].resample("1h", label="left", closed="left").last().dropna()
    dc = pd.Series({k: g[g["lis"] < k + H(22)]["mc"].iloc[-1] for k, g in G.items() if (g["lis"] < k + H(22)).any()}).sort_index()
    out = []
    for day, g in G.items():
        if day.weekday() >= 5 or day < pd.Timestamp("2020-01-01"): continue
        x = g[g["lis"] < day + H(21)]
        if len(x) < 900 or x["mc"].diff().abs().max() > 8: continue
        past = dc[dc.index < day]
        if len(past) < 21: continue
        dtr = np.sign(past.iloc[-1] - past.iloc[-20:].mean())
        hh = h1[h1.index < day + H(8)]
        if len(hh) < 30: continue
        e = hh.ewm(span=20, adjust=False).mean()
        up = hh.iloc[-1] > e.iloc[-1] and e.iloc[-1] > e.iloc[-5]; dn = hh.iloc[-1] < e.iloc[-1] and e.iloc[-1] < e.iloc[-5]
        side = "L" if (up and dtr > 0) else "S" if (dn and dtr < 0) else None
        if side is None: continue
        pre = x[x["lis"] < day + H(8)]; post = x[x["lis"] >= day + H(8)]
        if len(post) < 600 or len(pre) < 300: continue
        en = post["mo"].iloc[0]; L = side == "L"
        stp = pre["ml"].min() - 1.0 if L else pre["mh"].max() + 1.0
        risk = abs(en - stp)
        if risk < 5 or risk > 60: continue
        lo, hi, cl = post["ml"].values, post["mh"].values, post["mc"].values
        rec = {"date": day, "side": side, "risk": risk}
        for k in KS:
            tgt = en + k * risk if L else en - k * risk; r = None
            for i in range(len(lo)):
                if (L and lo[i] <= stp) or (not L and hi[i] >= stp): r = -1.0; break
                if (L and hi[i] >= tgt) or (not L and lo[i] <= tgt): r = k; break
            if r is None: r = ((cl[-1] - en) if L else (en - cl[-1])) / risk
            rec[k] = r - COST / risk
        out.append(rec)
    return pd.DataFrame(out)

def rep(t, lab):
    from math import erf, sqrt
    L = ["== %s: n %d (L %d / S %d), mean risk %.1f pts" % (lab, len(t), (t.side == "L").sum(), (t.side == "S").sum(), t.risk.mean())]
    for k in KS:
        r = t[k].values; tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))); p = 0.5 * (1 - erf(tt / sqrt(2)))
        L.append("   target %.1fR: win %4.1f%%  meanR %+.3f  t %+.2f  P %.4f  totalR %+.1f" % (k, 100 * (r >= k - COST / t.risk.values - 1e-9).mean(), r.mean(), tt, p, r.sum()))
    return L, t[2.0].mean(), t[1.0].mean()

def per(F, n): a, z = PER[n]; return F[(F.date >= a) & (F.date <= z)]

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        F = trades("2022-12-31"); dv = per(F, "DEV")
        print("DEV trades:", len(dv), "L/S", (dv.side == "L").sum(), (dv.side == "S").sum(), "risk median %.1f" % dv.risk.median(), "(no outcomes shown)")
    elif a[:1] == ["--run"]:
        F = trades("2025-12-31" if "--hold" in a else "2024-12-31"); lines = []
        for n in (["DEV", "VAL"] + (["HOLD"] if "--hold" in a else [])):
            o, m2, m1 = rep(per(F, n), n); lines += o
            if n == "VAL":
                from math import erf, sqrt
                r = per(F, "VAL")[2.0].values; tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))); p = 0.5 * (1 - erf(tt / sqrt(2)))
                lines.append("BAR: 2R mean > 1R mean: %s | 2R mean > 0 with P<=0.05: %s  ->  %s" % (m2 > m1, m2 > 0 and p <= 0.05, "PASS" if (m2 > m1 and m2 > 0 and p <= 0.05) else "FAIL"))
        print("\n".join(lines)); open(os.path.join(HERE, "F2PROXY_OUTPUT%s.txt" % ("_HOLD" if "--hold" in a else "")), "w").write("\n".join(lines) + "\n")
    else: sys.exit(__doc__)
