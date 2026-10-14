"""EURUSD-EA1 exactly as in PREREG_EURUSD_EA1.md.  python -m forex.ea_research.eurusd_ea1 [--dry] [--hold]"""
import sys, itertools, numpy as np, pandas as pd

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
END = "2026-10-01" if HOLD else "2026-01-01"
d = pd.read_parquet("forex/data_mt5/EURUSD_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t")
d["dt"] = pd.to_datetime(d.t, unit="s")
d = d.set_index("dt")
d = d[d.index < END]
H = d.resample("1h").agg(dict(bo="first", bh="max", bl="min", bc="last", ao="first", ah="max", al="min", ac="last")).dropna()
H["mo"] = (H.bo + H.ao) / 2
H["mc"] = (H.bc + H.ac) / 2
H["mh"] = H.bh + (H.ao - H.bo) / 2
H["ml"] = H.bl + (H.ao - H.bo) / 2
m = pd.DataFrame({"o": (d.bo + d.ao) / 2, "h": d.bh + (d.ao - d.bo) / 2, "l": d.bl + (d.ao - d.bo) / 2, "c": (d.bc + d.ac) / 2})
D = m.resample("1D").agg(dict(o="first", h="max", l="min", c="last")).dropna()
D = D[D.index.dayofweek < 5]
D["ema20"] = D.c.ewm(span=20).mean()
D["atr"] = (D.h - D.l).rolling(14).mean()
ch = D.c.diff()
gain = ch.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
loss = (-ch.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
D["rsi2"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
atrH = (H.mh - H.ml).rolling(14).mean()
idx = H.index
A = {k: H[k].to_numpy() for k in ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mo", "mc"]}


def bracket(i, side, stop, tp):
    """R of one trade entered at the open of bar i; tp == 0 means no target (hold to the close of the 24th bar)."""
    if side > 0:
        e = A["ao"][i]
        sl = e - stop
        tg = e + tp if tp else None
        for j in range(i, i + 24):
            if A["bl"][j] <= sl:
                return -1.0
            if tg is not None and A["bh"][j] >= tg:
                return tp / stop
        return (A["bc"][i + 23] - e) / stop
    e = A["bo"][i]
    sl = e + stop
    tg = e - tp if tp else None
    for j in range(i, i + 24):
        if A["ah"][j] >= sl:
            return -1.0
        if tg is not None and A["al"][j] <= tg:
            return tp / stop
    return (e - A["ac"][i + 23]) / stop


rows = []
for i in np.where((idx.hour == 10) & (idx.dayofweek <= 3) & (idx >= "2022-03-01"))[0]:
    if i < 30 or i + 24 >= len(idx) or (idx[i + 23] - idx[i]) > pd.Timedelta(hours=26):
        continue
    day = idx[i].normalize()
    pv = D[D.index < day]
    if len(pv) < 60:
        continue
    p = pv.iloc[-1]
    aH = atrH.iloc[i - 1]
    s = {}
    z = (p.c - p.ema20) / p.atr
    s["S1"] = np.sign(z) if abs(z) > 0.8 else 0
    s["S2"] = 1 if p.rsi2 < 10 else -1 if p.rsi2 > 90 else 0
    cl = (p.c - p.l) / (p.h - p.l) if p.h > p.l else 0.5
    s["S3"] = 1 if cl > 0.8 else -1 if cl < 0.2 else 0
    k2 = idx.get_indexer([day + pd.Timedelta(hours=2)], method="bfill")[0]
    r4 = (A["mc"][i - 1] / A["mo"][k2] - 1) if 0 <= k2 < i else 0.0
    s["S4"] = np.sign(r4) if abs(r4) > 2 * aH / A["mc"][i - 1] else 0
    r5 = A["mc"][i - 1] / A["mo"][i - 24] - 1
    s["S5"] = np.sign(r5) if abs(r5) > aH * np.sqrt(24) / A["mc"][i - 1] else 0
    s["S6"] = 0
    if idx[i].dayofweek >= 1:
        wk = idx[(idx >= day - pd.Timedelta(days=int(idx[i].dayofweek))) & (idx < day)]
        if len(wk):
            w = (A["mc"][i - 1] - A["mo"][idx.get_loc(wk[0])]) / p.atr
            s["S6"] = np.sign(w) if abs(w) > 1.0 else 0
    st1 = max(20e-4, 2 * aH)
    st2 = max(30e-4, 3 * aH)
    rows.append(dict(T=idx[i], **s, g1l=bracket(i, 1, st1, 1.5 * st1), g1s=bracket(i, -1, st1, 1.5 * st1),
                     g2l=bracket(i, 1, st2, 0), g2s=bracket(i, -1, st2, 0)))
R = pd.DataFrame(rows)
print("days", len(R), R["T"].min().date(), R["T"].max().date(), "| active share:", {k: round((R[k] != 0).mean(), 2) for k in ["S1", "S2", "S3", "S4", "S5", "S6"]})
if DRY:
    print(R.head(3).round(3).to_string())
    sys.exit()


def tt(v):
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 and v.std() > 0 else 0.0


per = {"DEV": ("2022-03-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def cell_r(df, sig, direction, geo):
    x = df[df[sig] != 0]
    sd = x[sig].to_numpy() * (1 if direction == "cont" else -1)
    return np.where(sd > 0, x[f"{geo}l"], x[f"{geo}s"]), x


cells = list(itertools.product(["S1", "S2", "S3", "S4", "S5", "S6"], ["cont", "fade"], ["g1", "g2"]))


def sl(p):
    return R[(R["T"] >= per[p][0]) & (R["T"] < pd.Timestamp(per[p][1]) + pd.Timedelta(days=1))]


print(f"{'cell':22s}{'nDEV':>5s}{'meanR':>7s}{'tDEV':>6s}{'hit':>5s} | {'nVAL':>4s}{'meanR':>7s}{'tVAL':>6s} | yearly 22/23/24/25 | pass")
res = {}
full = R.assign(y=R["T"].dt.year)
for c in cells:
    a, _ = cell_r(sl("DEV"), *c)
    b, _ = cell_r(sl("VAL"), *c)
    ys = []
    for y in (2022, 2023, 2024, 2025):
        v, _ = cell_r(full[full.y == y], *c)
        ys.append(v.mean() if len(v) > 5 else np.nan)
    ok = len(a) >= 100 and a.mean() > 0 and tt(a) >= 3.0 and len(b) >= 40 and b.mean() > 0 and tt(b) >= 1.65 and sum(np.nan_to_num(ys) > 0) >= 3
    res[c] = (tt(a), ok)
    print(f"{str(c):22s}{len(a):5d}{a.mean():7.3f}{tt(a):6.2f}{(a > 0).mean() * 100:5.0f} | {len(b):4d}{b.mean():7.3f}{tt(b):6.2f} | " + "/".join(f"{y:+.2f}" for y in ys) + f" | {ok}")
rng = np.random.default_rng(11)
mx = []
DV = sl("DEV")
for _ in range(500):
    mm = 0.0
    for c in cells:
        x = DV[DV[c[0]] != 0]
        sg = rng.permutation(x[c[0]].to_numpy()) * (1 if c[1] == "cont" else -1)
        v = np.where(sg > 0, x[f"{c[2]}l"], x[f"{c[2]}s"])
        mm = max(mm, abs(tt(v)))
    mx.append(mm)
ceil = np.percentile(mx, 95)
print("placebo max |t| over 24 cells (DEV): median %.2f, 95th %.2f; real best t %.2f" % (np.median(mx), ceil, max(v[0] for v in res.values())))
passed = [c for c, v in res.items() if v[1] and v[0] >= ceil]
print("PASSED all gates:", passed)
if HOLD:
    for c in passed:
        h, _ = cell_r(sl("HOLD"), *c)
        print("HOLD", c, len(h), round(h.mean(), 3), round(tt(h), 2))
