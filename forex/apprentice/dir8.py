"""PREREG_DIR8: logistic model on pre-08:00 features for the GC 08:00-12:00 direction, judged on both sides.
python dir8.py --dry-run | --run [--hold]"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, bias8 as B

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
PER = {"DEV": ("2020-01-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
FEATS = ["on", "l30", "pd", "asia_loc", "pd_loc", "trend20", "si_on", "es_on", "vol"]
H = B.H; TICK, COMM = 0.1, 0.15


def load_x(m, upto):
    d = pd.read_parquet(os.path.join(ROOT, "futures", "data", "databento", "futures_%s.F_1m.parquet" % m)).sort_values("ts")
    d["lis"] = d["ts"].dt.tz_convert("Europe/London").dt.tz_localize(None); d = d[d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1)]
    return {k: g for k, g in d.groupby(d["lis"].dt.normalize())}


def overnight(G, day):
    g = G.get(day)
    if g is None: return np.nan
    w = g[g["lis"] < day + H(8)]
    if len(w) < 60: return np.nan
    r = w["close"].iloc[-1] / w["open"].iloc[0] - 1
    return r if abs(r) <= 0.05 else np.nan


def build(upto):
    raw = D.raw(); raw = raw[raw["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1)].reset_index(drop=True)
    SI, ES = load_x("SI", upto), load_x("ES", upto)
    dc = raw[raw["lis"].dt.hour < 22].groupby(raw["lis"].dt.normalize())["mc"].last()  # daily 21:59-ish closes
    days = [x for x in dc.index if x.weekday() < 5 and x >= pd.Timestamp("2020-01-01")]
    rows = []; Shist = []
    for day in days:
        x, ok = B.day_data(raw, day)
        if not ok: continue
        pre = x[x["lis"] < day + H(8)]; base, lv = B.pre(pre, day); S = lv["S"]
        si, es = overnight(SI, day), overnight(ES, day)
        past = dc[dc.index < day].iloc[-21:]
        if np.isnan(si) or np.isnan(es) or len(past) < 21 or len(Shist) < 20: Shist.append(S); continue
        c759 = 1000.0 + base; ret = past.pct_change().dropna()
        f = {"date": day, "S": S,
             "on": (1000 - lv["asia_open"]) / S, "l30": (1000 - lv["o0730"]) / S, "pd": (lv["prev_close"] - lv["prev_open0800"]) / S,
             "asia_loc": (1000 - lv["asia_lo"]) / max(lv["asia_hi"] - lv["asia_lo"], 1e-9) - 0.5,
             "pd_loc": (1000 - lv["prev_lo"]) / max(lv["prev_hi"] - lv["prev_lo"], 1e-9) - 0.5,
             "trend20": (c759 / past.iloc[-20:].mean() - 1) / ret.iloc[-20:].std(), "si_on": si, "es_on": es,
             "vol": np.log(S / np.median(Shist[-20:]))}
        f["o800"] = x[x["lis"] == day + H(8)]["mo"].iloc[0]; f["c1159"] = x[x["lis"] == day + H(11, 59)]["mc"].iloc[0]
        f["y"] = int(f["c1159"] > f["o800"]); f["xf"] = x; rows.append(f); Shist.append(S)
    return pd.DataFrame(rows)


def per(F, name):
    a, z = PER[name]; return F[(F["date"] >= a) & (F["date"] <= z)].copy()


def trade_R(t, side):
    s = np.where(side == "L", 1, -1); return (s * (t["c1159"] - t["o800"]) - 2 * TICK - COMM) / t["S"]


def report(t, label):
    from math import comb, erf, sqrt
    n = len(t); hits = int(t["ok"].sum()); pb = sum(comb(n, j) for j in range(hits, n + 1)) / 2 ** n
    r = t["R"].values; tt = r.mean() / (r.std(ddof=1) / np.sqrt(n)); pt = 0.5 * (1 - erf(tt / sqrt(2)))
    out = ["== %s: n %d  hits %d (%.1f%%)  binomial P %.4f  | always-long %d (%.1f%%)  | mean R %+.3f  t %+.2f  P %.4f" % (
        label, n, hits, 100 * hits / n, pb, int(t["y"].sum()), 100 * t["y"].mean(), r.mean(), tt, pt)]
    for s in ("L", "S"):
        q = t[t["side"] == s]
        if len(q): out.append("   %s calls: n %d  hit %.1f%%  mean R %+.3f  (up-rate on these days %.1f%%)" % (s, len(q), 100 * q["ok"].mean(), q["R"].mean(), 100 * q["y"].mean()))
    return out, hits, pb, pt, r.mean()


def run(hold):
    from sklearn.linear_model import LogisticRegression
    F = build("2025-12-31" if hold else "2024-12-31"); dev, val = per(F, "DEV"), per(F, "VAL")
    lo, hi = dev[FEATS].quantile(0.01), dev[FEATS].quantile(0.99)
    def prep(t): z = t[FEATS].clip(lo, hi, axis=1); return (z - dev[FEATS].clip(lo, hi, axis=1).mean()) / dev[FEATS].clip(lo, hi, axis=1).std()
    m = LogisticRegression(C=1.0).fit(prep(dev), dev["y"]); lines = ["coefficients: " + "  ".join("%s %+.3f" % (f, c) for f, c in zip(FEATS, m.coef_[0])) + "  intercept %+.3f" % m.intercept_[0]]
    for t in (dev, val): t["p"] = m.predict_proba(prep(t))[:, 1]; t["side"] = np.where(t["p"] > 0.5, "L", "S"); t["ok"] = ((t["side"] == "L") & (t["y"] == 1)) | ((t["side"] == "S") & (t["y"] == 0)); t["R"] = trade_R(t, t["side"])
    o, *_ = report(dev, "DEV in-sample (fit here, inflated)"); lines += o
    o, hits, pb, pt, mr = report(val, "VAL"); lines += o
    sv = val[val["side"] == "S"]
    a = hits > val["y"].sum() and pb <= 0.05; b = len(sv) > 0 and sv["ok"].mean() > 0.5 and sv["R"].mean() > 0; c = mr > 0 and pt <= 0.05
    lines.append("BARS: (a) beats always-long and P<=0.05: %s | (b) shorts hit>50%% and mean R>0: %s | (c) mean R>0, P<=0.05: %s  ->  %s" % (a, b, c, "PASS" if a and b and c else "FAIL"))
    thr = np.median(np.abs(dev["p"] - 0.5)); q = val[np.abs(val["p"] - 0.5) > thr]
    o, *_ = report(q, "VAL top-half confidence (no bar)"); lines += o
    for f in FEATS:  # single-feature sign rules fitted on DEV
        sgn = np.sign(np.corrcoef(dev[f], dev["y"])[0, 1]); pv = np.where(sgn * val[f] > 0, 1, 0); lines.append("   single %-8s DEV sign %+d  VAL hit %.1f%%" % (f, sgn, 100 * (pv == val["y"]).mean()))
    br = [B.sim(r.xf, r.date, r.side, 2 * r.S, 1.5, "12:00")[1] / r.S for r in val.itertuples()]
    lines.append("   bracket stop 2S / target 3S on VAL: mean R(S units) %+.3f   | the trader's live bar: +0.5 R" % np.mean(br))
    if hold:
        hd = per(F, "HOLD"); hd["p"] = m.predict_proba(prep(hd))[:, 1]; hd["side"] = np.where(hd["p"] > 0.5, "L", "S")
        hd["ok"] = ((hd["side"] == "L") & (hd["y"] == 1)) | ((hd["side"] == "S") & (hd["y"] == 0)); hd["R"] = trade_R(hd, hd["side"]); o, *_ = report(hd, "HOLD 2025"); lines += o
    print("\n".join(lines)); open(os.path.join(HERE, "DIR8%s_OUTPUT.txt" % ("_HOLD" if hold else "")), "w").write("\n".join(lines) + "\n")
    pd.concat([dev.assign(period="DEV"), val.assign(period="VAL")]).drop(columns=["xf"]).to_csv(os.path.join(HERE, "DIR8_DAYS.csv"), index=False)


def dry():
    F = build("2022-12-31"); dev = per(F, "DEV")
    print("DEV days with all features: %d (of weekdays 2020-2022)" % len(dev))
    print(dev[FEATS].describe(percentiles=[.01, .5, .99]).T[["min", "1%", "50%", "99%", "max"]].round(3).to_string())
    # truncation causality: features of 5 days rebuilt from data cut at 07:59 must match
    raw = D.raw()
    for r in dev.sample(5, random_state=1).itertuples():
        x, _ = B.day_data(raw, r.date); b1, l1 = B.pre(x[x["lis"] < r.date + H(8)], r.date); b2, l2 = B.pre(x, r.date)
        assert l1 == l2 and abs(r.on - (1000 - l1["asia_open"]) / l1["S"]) < 1e-9
    print("truncation causality test passed on 5 days (features identical with and without post-08:00 bars)")


if __name__ == "__main__":
    a = sys.argv[1:]
    dry() if a[:1] == ["--dry-run"] else run("--hold" in a) if a[:1] == ["--run"] else sys.exit(__doc__)
