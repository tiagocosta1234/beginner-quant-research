"""FX3-TRENDBRACKET exactly as in PREREG_FX3_TRENDBRACKET.md.  python -m forex.ea_research.fx3_trendbracket [--hold]"""
import sys, numpy as np, pandas as pd
d = pd.read_parquet("forex/data_mt5/EURUSD_M1_rates.parquet", columns=["t","bo","bh","bl","bc","ao","ah","al","ac"]).sort_values("t")
d["dt"] = pd.to_datetime(d.t, unit="s"); d = d.set_index("dt")
H = d.resample("1h").agg(dict(bo="first", bh="max", bl="min", bc="last", ao="first", ah="max", al="min", ac="last")).dropna()
H["mo"] = (H.bo + H.ao) / 2; H["mc"] = (H.bc + H.ac) / 2; H["mh"] = H.bh + (H.ao - H.bo) / 2; H["ml"] = H.bl + (H.ao - H.bo) / 2
D = d.assign(m=(d.bc + d.ac) / 2).m.resample("1D").last().dropna(); D = D[D.index.dayofweek < 5]
e20, e50 = D.ewm(span=20).mean(), D.ewm(span=50).mean()
atr = (H.mh - H.ml).rolling(14).mean()
idx = H.index; arr = {k: H[k].to_numpy() for k in ["bo","bh","bl","bc","ao","ah","al","ac","mo","mc"]}
rows = []
for i in np.where((idx.hour == 10) & (idx.dayofweek <= 3) & (idx >= "2022-03-01") & (idx < "2026-10-01"))[0]:
    if i < 20 or i + 24 >= len(idx): continue
    day = idx[i].normalize(); prev = D[D.index < day]
    if len(prev) < 60: continue
    e2, e5, cl = e20[prev.index[-1]], e50[prev.index[-1]], prev.iloc[-1]
    side = 1 if (e2 > e5 and cl > e2) else -1 if (e2 < e5 and cl < e2) else 0
    a = atr.iloc[i - 1]
    if abs(arr["mc"][i - 1] - arr["mo"][i - 1]) > 1.5 * a: continue
    if (idx[i + 23] - idx[i]) > pd.Timedelta(hours=26): continue
    stop = max(20e-4, 2.0 * a); tp = 1.5 * stop
    def run(s):
        if s > 0:
            e = arr["ao"][i]; sl, tg = e - stop, e + tp
            for j in range(i, i + 24):
                if arr["bl"][j] <= sl: return -1.0, "stop"
                if arr["bh"][j] >= tg: return 1.5, "target"
            return (arr["bc"][i + 23] - e) / stop, "time"
        e = arr["bo"][i]; sl, tg = e + stop, e - tp
        for j in range(i, i + 24):
            if arr["ah"][j] >= sl: return -1.0, "stop"
            if arr["al"][j] <= tg: return 1.5, "target"
        return (e - arr["ac"][i + 23]) / stop, "time"
    rows.append((idx[i], side, run(1), run(-1)))
R = pd.DataFrame([(t, s, l[0], l[1], sh[0], sh[1]) for t, s, l, sh in rows], columns=["T","side","Rl","xlong","Rs","xshort"])
def sel(df, kind):
    if kind == "M": x = df[df.side != 0]; return np.where(x.side > 0, x.Rl, x.Rs), np.where(x.side > 0, x.xlong, x.xshort), x
    if kind == "R": x = df[df.side != 0]; return np.where(x.side > 0, x.Rs, x.Rl), np.where(x.side > 0, x.xshort, x.xlong), x
    x = df[df.side == 0]; return x.Rl.to_numpy(), x.xlong.to_numpy(), x
def tt(v): return v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
per = {"DEV": ("2022-03-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
rng = np.random.default_rng(3)
for p in (["DEV", "VAL"] + (["HOLD"] if "--hold" in sys.argv else [])):
    a, b = per[p]; df = R[(R["T"] >= a) & (R["T"] < pd.Timestamp(b) + pd.Timedelta(days=1))]
    print(f"== {p}: {len(df)} days, trend-trade days {(df.side != 0).sum()}")
    for k in "MRF":
        v, xx, x = sel(df, k); xs = pd.Series(xx)
        print(f" {k}: n {len(v)} mean R {v.mean():+.3f} t {tt(v):+.2f} hit {np.mean(v>0)*100:.0f}% | exits target {np.mean(xs=='target')*100:.0f}% stop {np.mean(xs=='stop')*100:.0f}% time {np.mean(xs=='time')*100:.0f}%")
    if p == "DEV":
        x = df[df.side != 0]; nm = []
        for _ in range(1000):
            s = rng.permutation(x.side.to_numpy()); nm.append(np.where(s > 0, x.Rl, x.Rs).mean())
        v, _, _ = sel(df, "M"); print(f" permutation null of M mean R: 5th {np.percentile(nm,5):+.3f} 50th {np.percentile(nm,50):+.3f} 95th {np.percentile(nm,95):+.3f}; M mean {v.mean():+.3f}")
