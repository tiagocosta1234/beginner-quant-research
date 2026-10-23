"""PREREG_TRENDOPEN.md: with the 30-minute trend, after a pullback, at the London open, on Databento GC 1-minute. One trade a day, the trader-style bracket.
Usage: python forex/apprentice/trendopen.py --dry-run   (counts only, no P&L)
       python forex/apprentice/trendopen.py dev         (DEV 2020-2022, the primary look)
       python forex/apprentice/trendopen.py val         (VAL 2023-2025, one look, only after DEV passes)"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K, manual_read_baselines as B

HERE = os.path.dirname(os.path.abspath(__file__))
RESERVED = [("2023-11-28", "2023-12-27"), ("2025-02-28", "2025-03-29"), ("2025-04-01", "2025-05-31"), ("2024-09-01", "2024-11-30"), ("2024-06-01", "2024-08-31")]
SEEN = set(pd.read_csv(os.path.join(HERE, "state_t", "order.csv"))["date"])
DAY0 = pd.Timestamp("2000-01-03")


def frames(years):
    d = D.raw(); d = d[(d["lis"] >= pd.Timestamp("%d-01-01" % years[0]) - pd.Timedelta(days=1)) & (d["lis"] < pd.Timestamp("%d-01-01" % (years[-1] + 1)) + pd.Timedelta(days=1))]
    d = d.reset_index(drop=True); key = d["lis"].values
    for day in pd.bdate_range("%d-01-02" % years[0], "%d-12-31" % years[-1]):
        ds = str(day.date())
        if ds in SEEN or any(a <= ds <= b for a, b in RESERVED): continue
        lo, hi = np.searchsorted(key, np.datetime64(day - pd.Timedelta(hours=4))), np.searchsorted(key, np.datetime64(day + pd.Timedelta(hours=21)))
        x = d.iloc[lo:hi].copy().reset_index(drop=True)
        if not len(x): continue
        w = x[(x["lis"] >= day + pd.Timedelta(hours=6)) & (x["lis"] < day + pd.Timedelta(hours=20))]
        if len(w[w["lis"] < day + pd.Timedelta(hours=8, minutes=16)]) < 120 or (w["mo"] - w["mc"].shift()).abs().max() > 8: continue
        x["ema"] = x["mc"].ewm(span=12, adjust=False).mean()
        tr = np.maximum(x["mh"] - x["ml"], np.maximum((x["mh"] - x["mc"].shift()).abs(), (x["ml"] - x["mc"].shift()).abs()))
        x["atr"] = tr.rolling(14).mean().shift(1); x["vmed"] = x["v"].rolling(60).median().shift(1)
        i6 = int(np.argmax(x["lis"] >= day + pd.Timedelta(hours=6))); base = x["mo"][i6] - 1000.0
        for k in ("mo", "mh", "ml", "mc", "ema"): x[k] = x[k] - base
        x["lis"] = x["lis"] - (day - DAY0)
        yield ds, day.year, x[["lis", "mo", "mh", "ml", "mc", "v", "ema", "atr", "vmed"]].reset_index(drop=True), i6


def signal(y):
    for m in range(7 * 60 + 59, 8 * 60 + 15):
        hit = np.where(y["lis"] == DAY0 + pd.Timedelta(minutes=m))[0]
        if not len(hit): continue
        i = int(hit[0])
        if i < 31: continue
        r = y.iloc[i]; atr = r.atr
        if not atr == atr or atr <= 0: continue
        t30 = r.mc - y["mc"][i - 30]
        if abs(t30) < atr: continue
        L = t30 > 0
        if not any(((y["mc"][k] < y["mo"][k]) if L else (y["mc"][k] > y["mo"][k])) for k in range(i - 3, i)): continue
        body = (r.mc - r.mo) if L else (r.mo - r.mc)
        if body < 0.8 * atr: continue
        cw = (r.mh - r.mc) if L else (r.mc - r.ml)
        if cw > 0.5 * body: continue
        if (L and r.mc <= r.ema) or (not L and r.mc >= r.ema): continue
        if abs(r.mo - y["ema"][i - 1]) > 1.5 * atr: continue
        return i, ("L" if L else "S")
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    years = {"dev": [2020, 2021, 2022], "val": [2023, 2024, 2025], "--dry-run": [2020, 2021, 2022, 2023, 2024, 2025]}[mode]
    rows, ndays = [], 0
    for ds, yr, y, i6 in frames(years):
        ndays += 1; s = signal(y)
        if s is None: continue
        i, side = s; sig = D.hm(y["lis"][i])
        if mode == "--dry-run":
            rows.append({"date": ds, "year": yr, "side": side, "signal": sig}); continue
        b = K.manual_bracket(y, i, i6, side); c = y["mc"][i]
        td = b["D"] if b else 2.5 * y["atr"][i]; sd = td / 0.53
        a, mi = B.pair(y, side, sig, sd, td)
        a1, m1 = B.pair(y, side, sig, sd, sd)
        rows.append({"date": ds, "year": yr, "side": side, "signal": sig, "R": a, "mirror": mi, "R_1to1": a1, "mirror_1to1": m1})
    t = pd.DataFrame(rows)
    print("%s: days %d, trades %d" % (mode, ndays, len(t)))
    if mode == "--dry-run":
        print(t.groupby("year").size().to_string()); print(t["side"].value_counts().to_string()); print(t["signal"].value_counts().sort_index().to_string()); return
    out = []
    for name, a, m in (("primary (the trader bracket)", "R", "mirror"), ("secondary 1:1", "R_1to1", "mirror_1to1")):
        obs, mir, exc, p = B.signflip(t[a].values, t[m].values)
        out.append("%-24s n %d  mean R %+.3f (se %.3f)  mirror %+.3f  excess %+.3f  wins %.1f%%  P %.4f" % (name, len(t), obs, t[a].std() / np.sqrt(len(t)), mir, exc, 100 * (t[a] > 0).mean(), p))
    for yr, g in t.groupby("year"): out.append("  %d: n %d  mean R %+.3f  1:1 %+.3f" % (yr, len(g), g.R.mean(), g.R_1to1.mean()))
    for sd, g in t.groupby("side"): out.append("  %s: n %d  mean R %+.3f  1:1 %+.3f" % (sd, len(g), g.R.mean(), g.R_1to1.mean()))
    obs, mir, exc, p = B.signflip(t.R.values, t.mirror.values)
    bar = (obs >= 0.05 and p <= 0.01) if mode == "dev" else (obs > 0 and p <= 0.05)
    out.append("%s VERDICT: mean R %+.3f, P %.4f -> %s" % (mode.upper(), obs, p, "PASS" if bar else "FAIL"))
    txt = "\n".join(out); print(txt)
    open(os.path.join(HERE, "TRENDOPEN_%s_OUTPUT.txt" % mode.upper()), "w").write(txt + "\n"); t.to_csv(os.path.join(HERE, "TRENDOPEN_%s_TRADES.csv" % mode.upper()), index=False)


if __name__ == "__main__":
    main()
