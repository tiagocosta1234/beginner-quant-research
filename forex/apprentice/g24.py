"""PREREG_G24: 24 mechanical 1:1 variants. python g24.py --dry-run | --run [--hold]"""
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D
HERE = os.path.dirname(os.path.abspath(__file__)); H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
GRID = list(itertools.product(["LDN", "NY"], ["1h", "both"], ["range", "atr", "swing"], ["off", "on"])); COST = 0.4

def build(upto):
    d = D.raw(); d = d[(d["lis"] >= "2019-10-01") & (d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1))].reset_index(drop=True)
    G = {k: g.reset_index(drop=True) for k, g in d.groupby(d["lis"].dt.normalize())}
    hb = d.set_index("lis").resample("1h", label="left", closed="left").agg({"mh": "max", "ml": "min", "mc": "last"}).dropna()
    tr = np.maximum(hb.mh - hb.ml, np.maximum((hb.mh - hb.mc.shift()).abs(), (hb.ml - hb.mc.shift()).abs())); hb["atr"] = tr.rolling(14).mean()
    hb["ema"] = hb.mc.ewm(span=20, adjust=False).mean()
    dc = pd.Series({k: g[g["lis"] < k + H(22)]["mc"].iloc[-1] for k, g in G.items() if (g["lis"] < k + H(22)).any()}).sort_index()
    days = sorted(G); out = []
    for i, day in enumerate(days):
        if day.weekday() >= 5 or day < pd.Timestamp("2020-01-01") or i == 0: continue
        g = G[day]; x = g[g["lis"] < day + H(21)]
        if len(x) < 900 or x["mc"].diff().abs().max() > 8: continue
        pd_ = G[days[i - 1]]; pv = pd_[(pd_["lis"] >= days[i - 1] + H(8)) & (pd_["lis"] < days[i - 1] + H(22))]
        past = dc[dc.index < day]
        if len(past) < 21 or len(pv) < 300: continue
        dtr = np.sign(past.iloc[-1] - past.iloc[-20:].mean())
        asia = x[x["lis"] < day + H(8)]
        for slot, t0, w0 in (("LDN", H(8), H(0)), ("NY", H(14, 30), H(8))):
            post = x[x["lis"] >= day + t0]; win = x[(x["lis"] >= day + w0) & (x["lis"] < day + t0)]
            hh = hb[hb.index < day + t0 - H(0, 59)] if slot == "NY" else hb[hb.index < day + t0]
            if len(post) < 200 or len(win) < 60 or len(hh) < 30 or np.isnan(hh.atr.iloc[-1]): continue
            c, e = hh.mc.values, hh.ema.values
            s1 = "L" if (c[-1] > e[-1] and e[-1] > e[-5]) else "S" if (c[-1] < e[-1] and e[-1] < e[-5]) else None
            if s1 is None: continue
            en = post["mo"].iloc[0]; atr = hh.atr.iloc[-1]; L = s1 == "L"
            lv = [pv.mh.max(), pv.ml.min(), asia.mh.max(), asia.ml.min()] + ([win.mh.max(), win.ml.min()] if slot == "NY" else [])
            lvl_ok = any((0 <= en - v <= 0.5 * atr) if L else (0 <= v - en <= 0.5 * atr) for v in lv)
            hl, hhh = hh.ml.values, hh.mh.values; sw = None
            for j in range(len(hl) - 3, 2, -1):
                if L and hl[j] < hl[j - 1] and hl[j] < hl[j - 2] and hl[j] < hl[j + 1] and hl[j] < hl[j + 2]: sw = hl[j] - 1.0; break
                if not L and hhh[j] > hhh[j - 1] and hhh[j] > hhh[j - 2] and hhh[j] > hhh[j + 1] and hhh[j] > hhh[j + 2]: sw = hhh[j] + 1.0; break
            stops = {"range": (win.ml.min() - 1.0) if L else (win.mh.max() + 1.0), "atr": en - 1.5 * atr if L else en + 1.5 * atr, "swing": sw}
            lo, hi, cl = post.ml.values, post.mh.values, post.mc.values
            for sk, stp in stops.items():
                if stp is None: continue
                risk = (en - stp) if L else (stp - en)
                if risk < 5 or risk > 80: continue
                tgt = en + risk if L else en - risk; r = None
                for k in range(len(lo)):
                    if (L and lo[k] <= stp) or (not L and hi[k] >= stp): r = -1.0; break
                    if (L and hi[k] >= tgt) or (not L and lo[k] <= tgt): r = 1.0; break
                if r is None: r = ((cl[-1] - en) if L else (en - cl[-1])) / risk
                out.append({"date": day, "slot": slot, "side": s1, "both": s1 == ("L" if dtr > 0 else "S"), "stop": sk, "lvl": lvl_ok, "R": r - COST / risk})
    return pd.DataFrame(out)

def sel(F, v):
    slot, trn, stp, lvl = v; t = F[(F.slot == slot) & (F.stop == stp)]
    if trn == "both": t = t[t.both]
    if lvl == "on": t = t[t.lvl]
    return t

def stat(r):
    from math import erf, sqrt
    if len(r) < 2: return len(r), np.nan, np.nan
    tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))); return len(r), r.mean(), 0.5 * (1 - erf(tt / sqrt(2)))

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        F = build("2022-12-31"); dv = F[(F.date >= "2020-01-01") & (F.date <= "2022-12-31")]
        print("DEV trade counts per variant (no outcomes):"); print(" ".join("%s/%s/%s/%s:%d" % (v + (len(sel(dv, v)),)) for v in GRID))
    elif a[:1] == ["--run"]:
        hold = "--hold" in a; F = build("2025-12-31" if hold else "2024-12-31")
        P = {n: F[(F.date >= PER[n][0]) & (F.date <= PER[n][1])] for n in (["DEV", "VAL"] + (["HOLD"] if hold else []))}
        lines = ["variant (slot/trend/stop/level) | DEV n meanR | VAL n meanR P | verdict"]; npass = 0
        for v in GRID:
            nd, md, _ = stat(sel(P["DEV"], v).R.values); nv, mv, pv = stat(sel(P["VAL"], v).R.values)
            ok = nv >= 60 and mv > 0 and pv <= 0.05 / 24 and md > 0; npass += ok
            ex = ""
            if hold: nh, mh, ph = stat(sel(P["HOLD"], v).R.values); ex = " | HOLD %d %+.3f P%.3f" % (nh, mh, ph)
            lines.append("%-22s | %4d %+.3f | %4d %+.3f P%.4f | %s%s" % ("/".join(v), nd, md, nv, mv, pv, "PASS" if ok else "fail", ex))
        lines.append("PASSES: %d of 24 (bar: VAL mean > 0, P <= 0.0021, DEV mean > 0, VAL n >= 60)" % npass)
        print("\n".join(lines)); open(os.path.join(HERE, "G24_OUTPUT%s.txt" % ("_HOLD" if hold else "")), "w").write("\n".join(lines) + "\n")
    else: sys.exit(__doc__)
