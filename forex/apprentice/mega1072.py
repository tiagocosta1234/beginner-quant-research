"""PREREG_MEGA1072. python mega1072.py --dry-run | --run [--hold]"""
import os, sys, itertools, numpy as np, pandas as pd
from math import erf, sqrt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D

HERE = os.path.dirname(os.path.abspath(__file__))
H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
COST = 0.4
WIN = {"LDN": (H(8), H(11, 45)), "NY": (H(14, 30), H(17, 30))}


def rules():
    R = []
    for w in WIN:
        for f, s in itertools.product((8, 12, 20), (26, 50)): R.append(("EMAX", w, f, s))
        for n, md in itertools.product((15, 30, 60), ("BRK", "FADE")): R.append(("ORB", w, n, md))
        for lv in ("PD", "AS"):
            for md in ("BRK", "FADE"): R.append(("LVL", w, lv, md))
        for t, md in itertools.product((0.5, 1.0), ("FOLLOW", "FADE")): R.append(("GAP", w, t, md))
        for lh, md in itertools.product(((30, 70), (25, 75), (20, 80)), ("FADE", "FOLLOW")): R.append(("RSI", w, lh, md))
        for k, md in itertools.product((2.0, 2.5), ("FADE", "BRK")): R.append(("BB", w, k, md))
        for n, md in itertools.product((20, 40), ("BRK", "FADE")): R.append(("DON", w, n, md))
        for t, md in itertools.product((0.0, 0.5), ("FOLLOW", "FADE")): R.append(("MOM", w, t, md))
        for k, md in itertools.product((1.0, 1.5), ("FADE", "FOLLOW")): R.append(("MEAN", w, k, md))
        for e in (20, 50): R.append(("PULL", w, e, None))
        for md in ("BRK", "FADE"): R.append(("NR7", w, None, md))
    for h in range(0, 21):
        for sd in "LS": R.append(("TIME", h, sd, None))
    return R


RULES = rules()
EXITS = list(itertools.product((0.75, 1.0, 1.5, 2.0), (1.0, 2.0)))


def load(upto):
    d = D.raw()
    d = d[(d["lis"] >= "2019-10-01") & (d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1))].reset_index(drop=True)
    bad = set()
    for k, g in d.groupby(d["lis"].dt.normalize()):
        gg = g[g["lis"] < k + H(21)]
        if len(gg) < 900 or gg["mc"].diff().abs().max() > 8: bad.add(k)
    b = d.set_index("lis").resample("15min", label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last"}).dropna()
    c = b.mc
    for sp in (8, 12, 20, 26, 50): b["e%d" % sp] = c.ewm(span=sp, adjust=False).mean()
    dl = c.diff()
    up = dl.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    b["rsi"] = 100 - 100 / (1 + up / dn)
    b["bbm"] = c.rolling(20).mean(); b["bbs"] = c.rolling(20).std()
    for n in (20, 40):
        b["dh%d" % n] = b.mh.rolling(n).max().shift(1); b["dl%d" % n] = b.ml.rolling(n).min().shift(1)
    h1 = d.set_index("lis").resample("1h", label="left", closed="left").agg({"mh": "max", "ml": "min", "mc": "last"}).dropna()
    tr = np.maximum(h1.mh - h1.ml, np.maximum((h1.mh - h1.mc.shift()).abs(), (h1.ml - h1.mc.shift()).abs()))
    b["atr1"] = tr.rolling(14).mean().shift(1).reindex(b.index, method="ffill")
    b["rng"] = b.mh - b.ml
    dcl = pd.Series({k: g[g["lis"] < k + H(22)]["mc"].iloc[-1] for k, g in d.groupby(d["lis"].dt.normalize()) if (g["lis"] < k + H(22)).any()}).sort_index()
    return b, bad, dcl


def sig(rule, a, ctx, w0, w1):
    st, wn, p1, p2 = rule
    C, O, Hh, Lo = a["C"], a["O"], a["H"], a["L"]
    n = len(C)
    if st == "TIME":
        i = a["hour_idx"].get(wn)
        return (i, p1) if i is not None and i < n else None
    for i in range(max(w0, 20), min(w1 + 1, n - 1)):
        s = None
        if st == "EMAX":
            f, sl = a["e%d" % p1], a["e%d" % p2]
            if f[i - 1] <= sl[i - 1] and f[i] > sl[i]: s = "L"
            elif f[i - 1] >= sl[i - 1] and f[i] < sl[i]: s = "S"
        elif st == "ORB":
            nb = p1 // 15
            if i < w0 + nb: continue
            hi_r, lo_r = Hh[w0:w0 + nb].max(), Lo[w0:w0 + nb].min()
            if C[i] > hi_r: s = "L" if p2 == "BRK" else "S"
            elif C[i] < lo_r: s = "S" if p2 == "BRK" else "L"
        elif st == "LVL":
            hi_l, lo_l = (ctx["pdh"], ctx["pdl"]) if p1 == "PD" else (ctx["ash"], ctx["asl"])
            if p2 == "BRK":
                if C[i] > hi_l and C[i - 1] <= hi_l: s = "L"
                elif C[i] < lo_l and C[i - 1] >= lo_l: s = "S"
            else:
                if Hh[i] > hi_l and C[i] < hi_l: s = "S"
                elif Lo[i] < lo_l and C[i] > lo_l: s = "L"
        elif st == "GAP":
            if i != max(w0, 20): continue
            g = (O[w0] - ctx["pc"]) / a["atr1"][w0]
            if abs(g) > p1: s = ("L" if g > 0 else "S") if p2 == "FOLLOW" else ("S" if g > 0 else "L")
            return (w0, s) if s else None
        elif st == "RSI":
            lo_t, hi_t = p1
            r = a["rsi"]
            if p2 == "FADE":
                if r[i] < lo_t: s = "L"
                elif r[i] > hi_t: s = "S"
            else:
                if r[i - 1] <= hi_t < r[i]: s = "L"
                elif r[i - 1] >= lo_t > r[i]: s = "S"
        elif st == "BB":
            m_, sd_ = a["bbm"][i], a["bbs"][i]
            if C[i] > m_ + p1 * sd_: s = "S" if p2 == "FADE" else "L"
            elif C[i] < m_ - p1 * sd_: s = "L" if p2 == "FADE" else "S"
        elif st == "DON":
            if C[i] > a["dh%d" % p1][i]: s = "L" if p2 == "BRK" else "S"
            elif C[i] < a["dl%d" % p1][i]: s = "S" if p2 == "BRK" else "L"
        elif st == "MOM":
            if i != max(w0, 20): continue
            mm = C[w0 - 1] - C[w0 - 17]
            if abs(mm) > p1 * a["atr1"][w0]: s = ("L" if mm > 0 else "S") if p2 == "FOLLOW" else ("S" if mm > 0 else "L")
            return (w0, s) if s else None
        elif st == "MEAN":
            dv = (C[i] - a["cmean"][i]) / a["atr1"][i]
            if dv > p1: s = "S" if p2 == "FADE" else "L"
            elif dv < -p1: s = "L" if p2 == "FADE" else "S"
        elif st == "PULL":
            e = a["e%d" % p1]
            if ctx["dtr"] > 0 and Lo[i] <= e[i] < C[i]: s = "L"
            elif ctx["dtr"] < 0 and Hh[i] >= e[i] > C[i]: s = "S"
        elif st == "NR7":
            if a["rng"][i] < a["rng"][i - 6:i].min():
                col = "L" if C[i] > O[i] else "S" if C[i] < O[i] else None
                if col: s = col if p2 == "BRK" else ("S" if col == "L" else "L")
        if s: return (i + 1, s)
    return None


def build(upto):
    b, bad, dcl = load(upto)
    res = []
    days = sorted(set(b.index.normalize()))
    for k, day in enumerate(days):
        if day.weekday() >= 5 or day < pd.Timestamp("2020-01-01") or day in bad or k == 0: continue
        x = b[(b.index >= day) & (b.index < day + H(21))]
        if len(x) < 60: continue
        pv = b[(b.index >= days[k - 1] + H(8)) & (b.index < days[k - 1] + H(22))]
        asia = x[x.index < day + H(8)]
        past = dcl[dcl.index < day]
        if len(pv) < 40 or len(asia) < 20 or len(past) < 21: continue
        a = {c: x[c].values for c in x.columns}
        a["C"], a["O"], a["H"], a["L"] = x.mc.values, x.mo.values, x.mh.values, x.ml.values
        a["cmean"] = x.mc.expanding().mean().values
        idx = x.index.values
        a["hour_idx"] = {}
        for h in range(0, 21):
            j = int(np.searchsorted(idx, (day + H(h)).to_datetime64()))
            if j < len(x) and x.index[j] == day + H(h): a["hour_idx"][h] = j
        ctx = {"pdh": pv.mh.max(), "pdl": pv.ml.min(), "ash": asia.mh.max(), "asl": asia.ml.min(), "pc": pv.mc.iloc[-1], "dtr": np.sign(past.iloc[-1] - past.iloc[-20:].mean())}
        for ri, rule in enumerate(RULES):
            if rule[0] == "TIME": w0 = w1 = 0
            else:
                w0 = int(np.searchsorted(idx, (day + WIN[rule[1]][0]).to_datetime64()))
                w1 = int(np.searchsorted(idx, (day + WIN[rule[1]][1]).to_datetime64(), side="right")) - 1
            sg = sig(rule, a, ctx, w0, w1)
            if sg is None: continue
            e, side = sg
            if e >= len(x) - 2 or np.isnan(a["atr1"][e]): continue
            en = a["O"][e]
            L = side == "L"
            Hs, Ls = a["H"][e:], a["L"][e:]
            cl_end = a["C"][-1]
            for xi, (m, rr) in enumerate(EXITS):
                risk = m * a["atr1"][e]
                if risk < 3 or risk > 80: continue
                stp = en - risk if L else en + risk
                tgt = en + rr * risk if L else en - rr * risk
                si = np.flatnonzero(Ls <= stp)[:1] if L else np.flatnonzero(Hs >= stp)[:1]
                ti = np.flatnonzero(Hs >= tgt)[:1] if L else np.flatnonzero(Ls <= tgt)[:1]
                if len(si) and (not len(ti) or si[0] <= ti[0]): r = -1.0
                elif len(ti): r = rr
                else: r = ((cl_end - en) if L else (en - cl_end)) / risk
                res.append((day, ri * 8 + xi, r - COST / risk))
    return pd.DataFrame(res, columns=["date", "vid", "R"])


def stat(r):
    if len(r) < 3: return len(r), np.nan, np.nan, np.nan
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
    return len(r), r.mean(), t, 0.5 * (1 - erf(t / sqrt(2)))


def name(vid):
    rl = RULES[vid // 8]
    m, rr = EXITS[vid % 8]
    return "%s/%s/%s/%s stop%.2fATR R%g" % (rl[0], rl[1], rl[2], rl[3], m, rr)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        print("rules", len(RULES), "variants", len(RULES) * 8)
        F = build("2022-12-31")
        dv = F[(F.date >= PER["DEV"][0]) & (F.date <= PER["DEV"][1])]
        c = dv.groupby("vid").size()
        print("DEV trades per variant: min %d median %d max %d; variants with >= 100 DEV trades: %d" % (c.min(), c.median(), c.max(), (c >= 100).sum()), "(no outcomes shown)")
    elif a[:1] == ["--run"]:
        hold = "--hold" in a
        F = build("2025-12-31" if hold else "2024-12-31")
        rows = []
        for vid, g in F.groupby("vid"):
            nd, md, td, pdv = stat(g[(g.date >= PER["DEV"][0]) & (g.date <= PER["DEV"][1])].R.values)
            nv, mv, tv, pv = stat(g[(g.date >= PER["VAL"][0]) & (g.date <= PER["VAL"][1])].R.values)
            rows.append((vid, nd, md, nv, mv, tv, pv))
        T = pd.DataFrame(rows, columns=["vid", "nd", "md", "nv", "mv", "tv", "pv"]).dropna()
        N = len(RULES) * 8
        ok = T[(T.nv >= 100) & (T.mv > 0) & (T.pv <= 0.05 / N) & (T.md > 0)]
        L = ["variants with enough trades: %d of %d | VAL t >= 2: %d (luck alone: ~%d) | VAL mean R > 0: %d | PASSES (P <= %.1e, DEV>0, n>=100): %d" % (len(T), N, (T.tv >= 2).sum(), round(0.023 * len(T)), (T.mv > 0).sum(), 0.05 / N, len(ok)), "top 15 by VAL t (n>=100):"]
        for _, r in T[T.nv >= 100].sort_values("tv", ascending=False).head(15).iterrows():
            L.append("  %-46s DEV n%4d %+.3f | VAL n%4d %+.3f t%+.2f P%.4f" % (name(int(r.vid)), r.nd, r.md, r.nv, r.mv, r.tv, r.pv))
        L.append("best per style (VAL t, n>=100):")
        T["st"] = T.vid.map(lambda v: RULES[int(v) // 8][0])
        for s, g in T[T.nv >= 100].groupby("st"):
            r = g.sort_values("tv", ascending=False).iloc[0]
            L.append("  %-5s %-46s VAL %+.3f t%+.2f (DEV %+.3f)" % (s, name(int(r.vid)), r.mv, r.tv, r.md))
        if hold:
            for _, r in ok.iterrows():
                g = F[(F.vid == r.vid) & (F.date >= PER["HOLD"][0]) & (F.date <= PER["HOLD"][1])].R.values
                nh, mh, th, ph = stat(g)
                L.append("HOLD %s n%d mean %+.3f P%.3f" % (name(int(r.vid)), nh, mh, ph))
        print("\n".join(L))
        open(os.path.join(HERE, "MEGA1072_OUTPUT%s.txt" % ("_HOLD" if hold else "")), "w").write("\n".join(L) + "\n")
    else:
        sys.exit(__doc__)
