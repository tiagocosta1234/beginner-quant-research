"""PREREG_ML8. python ml8.py --dry-run | --run"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, bias8 as B, dir8 as R
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__)); H = B.H; COST = 0.4
FE = R.FEATS + ["asia_rng", "pd_rng", "dow"]
def build(upto="2024-12-31"):
    raw = D.raw(); raw = raw[raw["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1)].reset_index(drop=True)
    SI, ES = R.load_x("SI", upto), R.load_x("ES", upto)
    dc = raw[raw["lis"].dt.hour < 22].groupby(raw["lis"].dt.normalize())["mc"].last()
    days = [x for x in dc.index if x.weekday() < 5 and x >= pd.Timestamp("2020-01-01")]; rows = []; Sh = []
    for day in days:
        x, ok = B.day_data(raw, day)
        if not ok: continue
        base, lv = B.pre(x[x["lis"] < day + H(8)], day); S = lv["S"]
        si, es = R.overnight(SI, day), R.overnight(ES, day); past = dc[dc.index < day].iloc[-21:]
        if np.isnan(si) or np.isnan(es) or len(past) < 21 or len(Sh) < 20: Sh.append(S); continue
        c759 = 1000.0 + base; ret = past.pct_change().dropna()
        f = {"date": day, "S": S, "on": (1000 - lv["asia_open"]) / S, "l30": (1000 - lv["o0730"]) / S, "pd": (lv["prev_close"] - lv["prev_open0800"]) / S,
             "asia_loc": (1000 - lv["asia_lo"]) / max(lv["asia_hi"] - lv["asia_lo"], 1e-9) - 0.5, "pd_loc": (1000 - lv["prev_lo"]) / max(lv["prev_hi"] - lv["prev_lo"], 1e-9) - 0.5,
             "trend20": (c759 / past.iloc[-20:].mean() - 1) / ret.iloc[-20:].std(), "si_on": si, "es_on": es, "vol": np.log(S / np.median(Sh[-20:])),
             "asia_rng": (lv["asia_hi"] - lv["asia_lo"]) / S, "pd_rng": (lv["prev_hi"] - lv["prev_lo"]) / S, "dow": day.weekday()}
        post = x[(x["lis"] >= day + H(8)) & (x["lis"] < day + H(17))]
        if len(post) < 500: Sh.append(S); continue
        o = post["mo"].iloc[0]; hi, lo, cl = post["mh"].values, post["ml"].values, post["mc"].values
        for m in (2, 4, 6):
            Dd = m * S
            for side in ("L", "S"):
                L = side == "L"; stp = o - Dd if L else o + Dd; tgt = o + Dd if L else o - Dd; r = None
                for i in range(len(hi)):
                    hs = lo[i] <= stp if L else hi[i] >= stp; ht = hi[i] >= tgt if L else lo[i] <= tgt
                    if hs: r = -1.0; break
                    if ht: r = 1.0; break
                if r is None: r = ((cl[-1] - o) if L else (o - cl[-1])) / Dd
                f["w%d%s" % (m, side)] = 1 if r == 1.0 and True else 0; f["r%d%s" % (m, side)] = r - COST / Dd
        rows.append(f); Sh.append(S)
    return pd.DataFrame(rows)
def binp(n, k, p): return sum(comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))
def run():
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    F = build(); dev = F[F.date <= "2022-12-31"].reset_index(drop=True); val = F[F.date >= "2023-01-01"].reset_index(drop=True)
    mu, sd = dev[FE].mean(), dev[FE].std().replace(0, 1); Xd, Xv = (dev[FE] - mu) / sd, (val[FE] - mu) / sd
    lines = ["DEV days %d, VAL days %d" % (len(dev), len(val))]; best = 0; cells = 0; passed = 0
    for m in (2, 4, 6):
        base = {s: val["w%d%s" % (m, s)].mean() for s in "LS"}
        lines.append("== stop = %dxS  (median stop %.1f pts) | VAL base win rate long %.1f%% short %.1f%%" % (m, (m * val.S).median(), 100 * base["L"], 100 * base["S"]))
        for name, mk in (("logit", lambda: LogisticRegression(C=1.0, max_iter=1000)), ("hgb", lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, random_state=0))):
            P = {}
            for s in "LS":
                mdl = mk().fit(Xd, dev["w%d%s" % (m, s)]); P[s] = mdl.predict_proba(Xv)[:, 1]
            pl, ps = P["L"], P["S"]; side = np.where(pl >= ps, "L", "S"); pbest = np.maximum(pl, ps)
            w = np.where(side == "L", val["w%dL" % m], val["w%dS" % m]); r = np.where(side == "L", val["r%dL" % m], val["r%dS" % m])
            bb = np.where(side == "L", base["L"], base["S"]).mean(); order = np.argsort(-pbest); out = []
            for q in (0.02, 0.05, 0.10, 0.20, 0.50, 1.0):
                n = max(int(round(q * len(val))), 1); ix = order[:n]; k = int(w[ix].sum())
                out.append("top%d%%: n %d win %.0f%% R %+.2f P %.3f" % (100 * q, n, 100 * k / n, r[ix].mean(), binp(n, k, bb)))
                if q == 0.10:
                    cells += 1; ok = k / n >= 0.60 and binp(n, k, bb) <= 0.05 / 6 and r[ix].mean() > 0; passed += ok; best = max(best, k / n)
            lines.append("  %-5s " % name + " | ".join(out))
    lines.append("CELLS PASSING (top-10%% win >= 60%% & Bonferroni P): %d of %d | best top-10%% win rate %.0f%% | 90%% reached: %s" % (passed, cells, 100 * best, best >= 0.9))
    print("\n".join(lines)); open(os.path.join(HERE, "ML8_OUTPUT.txt"), "w").write("\n".join(lines) + "\n")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]:
        F = build("2022-12-31"); print("DEV days %d; base win rates (m=2..6) long: %s" % (len(F[F.date <= "2022-12-31"]), "n/a (not shown)"))
    elif a[:1] == ["--run"]: run()
    else: sys.exit(__doc__)
