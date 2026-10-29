"""EURUSD-ML exactly as in PREREG_EURUSD_ML.md.  python -m forex.ea_research.eurusd_ml [--dry] [--hold]"""
import sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
END = pd.Timestamp("2026-10-01" if HOLD else "2026-01-01")
DATA = "forex/data_mt5/"
SLIP = 0.1
HOLD_S = 4 * 3600


class Px:
    def __init__(self, m):
        d = pd.read_parquet(DATA + f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "ao", "bc", "ac"]).sort_values("t")
        d = d[(d.t < END.timestamp()) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t")
        self.d = d
        self.ix = pd.Index(d.t.to_numpy())
        self.bo, self.ao = d.bo.to_numpy(), d.ao.to_numpy()
        self.mid = (d.bo + d.ao).to_numpy() / 2

    def idx(self, t):
        return self.ix.get_indexer(np.asarray(t))

    def m(self, t):
        i = self.idx(t)
        return np.where(i >= 0, self.mid[np.maximum(i, 0)], np.nan)


EU = Px("EURUSD")
# ---------------------------------------------------------------- slots
days = [d for d in pd.date_range("2022-03-01", END - pd.Timedelta(days=1), freq="D") if d.dayofweek < 5]
T = np.array([int(d.timestamp()) + h * 3600 + 300 for d in days for h in range(2, 19, 2)], dtype="int64")
iE, iX = EU.idx(T), EU.idx(T + HOLD_S)
ok = (iE >= 0) & (iX >= 0)
T, iE, iX = T[ok], iE[ok], iX[ok]
now = T - 60
pn = EU.m(now)
F = {}
for h in (1, 2, 3, 4, 8, 24):
    F[f"ret{h}"] = (pn / EU.m(now - h * 3600) - 1) * 1e4
hr = np.stack([EU.m(now - k * 3600) for k in range(0, 25)], 1)
lr = np.diff(np.log(hr), axis=1)
F["vol24"] = np.nanstd(lr, 1) * 1e4
F["vol4"] = np.nanstd(lr[:, -4:], 1) * 1e4
F["spread"] = (EU.ao[EU.idx(now).clip(0)] - EU.bo[EU.idx(now).clip(0)]) / pn * 1e4
F["hour"] = ((T // 3600) % 24).astype(float)
F["dow"] = pd.to_datetime(T, unit="s").dayofweek.to_numpy().astype(float)
# daily features (previous completed day)
d = EU.d.copy()
d.index = pd.to_datetime(d.t, unit="s")
spr = (d.ao - d.bo) / 2
mm = (d.bo + d.ao) / 2
Dd = pd.DataFrame({"o": mm.resample("1D").first(), "h": (d.bh + spr).resample("1D").max(), "l": (d.bl + spr).resample("1D").min(), "c": ((d.bc + d.ac) / 2).resample("1D").last()}).dropna()
Dd = Dd[Dd.index.dayofweek < 5]
Dd["atr"] = (Dd.h - Dd.l).rolling(14).mean()
Dd["e20"], Dd["e50"] = Dd.c.ewm(span=20).mean(), Dd.c.ewm(span=50).mean()
ch = Dd.c.diff()
g, l_ = ch.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(), (-ch.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
Dd["rsi2"] = 100 - 100 / (1 + g / l_.replace(0, np.nan))
Dd["cl"] = (Dd.c - Dd.l) / (Dd.h - Dd.l)
Dd["z"] = (Dd.c - Dd.e20) / Dd.atr
Dd["trend"] = np.sign(Dd.e20 - Dd.e50)
Dd["piv"] = (Dd.h + Dd.l + Dd.c) / 3
Dd["r1"], Dd["s1"] = 2 * Dd.piv - Dd.l, 2 * Dd.piv - Dd.h
prev = Dd.shift(1)
dates = pd.to_datetime(T, unit="s").normalize()
P = prev.reindex(dates, method="ffill")
for c in ["z", "trend", "rsi2", "cl"]:
    F[c] = P[c].to_numpy()
F["pivd"] = ((pn - P.piv.to_numpy()) / P.atr.to_numpy())
F["r1d"] = ((pn - P.r1.to_numpy()) / P.atr.to_numpy())
F["s1d"] = ((pn - P.s1.to_numpy()) / P.atr.to_numpy())
mon = dates - pd.to_timedelta(dates.dayofweek, unit="D")
wopen = Dd.o.reindex(mon, method="bfill").to_numpy()
F["weekly"] = (pn - wopen) / P.atr.to_numpy()
F["intraday"] = (pn / EU.m(np.array([int(x.timestamp()) + 3600 + 300 for x in dates])) - 1) * 1e4
# tick volume
vol = pd.read_parquet("data/ticks_vol/EURUSD.parquet").set_index("time").tick_volume
vol = vol[vol.index < END.timestamp()]
VT, VC = vol.index.to_numpy(), np.r_[0, np.cumsum(vol.to_numpy().astype(float))]
vsum = lambda a, b: VC[np.searchsorted(VT, b)] - VC[np.searchsorted(VT, a)]
for L in (3, 6):
    cur = vsum(now - L * 3600, now)
    bs = np.full((len(T), 20), np.nan)
    for r, t in enumerate(now):
        k, n = 1, 0
        while n < 20 and k < 40:
            tk = t - k * 86400
            if ((tk // 86400) + 3) % 7 < 5:
                bs[r, n] = vsum(tk - L * 3600, tk); n += 1
            k += 1
    F[f"volratio{L}"] = cur / np.nanmedian(bs, 1)
# cross-pair spread and other markets
oth = {m: Px(m) for m in ("GBPUSD", "AUDUSD", "NZDUSD")}
for L in (6, 24):
    r0 = pn / EU.m(now - L * 3600) - 1
    ro = np.mean([o.m(now) / o.m(now - L * 3600) - 1 for o in oth.values()], 0)
    F[f"xspr{L}"] = (r0 - ro) * 1e4
for m in ("SP", "NSDQ", "XAUUSD", "USDJPY"):
    o = Px(m)
    for h in (4, 24):
        F[f"{m}_{h}"] = (o.m(now) / o.m(now - h * 3600) - 1) * 1e4
# calendar
cal = pd.read_csv("data/data_macro/mt5_calendar.csv", encoding="latin-1")
cal = cal[(cal.importance == 3) & cal.currency.isin(["USD", "EUR"])]
cal["utc"] = pd.to_datetime(cal.time, format="%Y.%m.%d %H:%M:%S")
srv = pd.DatetimeIndex(np.sort(cal.utc.unique())).tz_localize("UTC").tz_convert("Europe/Athens").tz_localize(None)
ev = np.unique(srv.astype("datetime64[s]").astype("int64").to_numpy())
rx = (EU.m(ev + 600) / EU.m(ev - 60) - 1) * 1e4
kn = np.searchsorted(ev + 600, now, side="right") - 1
kk = np.maximum(kn, 0)
F["min_since"] = np.where(kn >= 0, np.minimum((T - ev[kk]) / 60, 1440), 1440)
F["last_rx"] = np.where(kn >= 0, rx[kk], 0.0)
nx = np.searchsorted(ev, T, side="left")
F["min_to_next"] = np.where(nx < len(ev), np.minimum((ev[np.minimum(nx, len(ev) - 1)] - T) / 60, 1440), 1440)
X = pd.DataFrame(F)
X["T"] = T
y = (EU.m(T + HOLD_S) / EU.m(T) - 1) * 1e4
netL = (EU.bo[iX] / EU.ao[iE] - 1) * 1e4 - 2 * SLIP
netS = (EU.bo[iE] / EU.ao[iX] - 1) * 1e4 - 2 * SLIP
bad_h = np.isin((T // 3600) % 24, (23, 0)) | np.isin(((T + HOLD_S) // 3600) % 24, (23, 0))
feat = [c for c in X.columns if c != "T"]
keep = ~bad_h & ~np.isnan(y)
X, y, netL, netS, T = X[keep].reset_index(drop=True), y[keep], netL[keep], netS[keep], T[keep]
print("samples", len(X), "features", len(feat), "span", pd.Timestamp(T.min(), unit="s").date(), pd.Timestamp(T.max(), unit="s").date())
if DRY:
    print(X[feat].describe().T[["count", "mean", "std", "min", "max"]].round(2).to_string())
    sys.exit()
# ---------------------------------------------------------------- walk-forward
months = pd.to_datetime(T, unit="s").to_period("M").astype(str).to_numpy()
starts = [pd.Timestamp(s).timestamp() for s in ("2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01", "2026-01-01")]
if not HOLD:
    starts = starts[:-1] + [pd.Timestamp("2026-01-01").timestamp()]
Xv = X[feat].to_numpy()


def make(kind):
    return Ridge(alpha=100.0) if kind == "ridge" else HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0, random_state=0)


def walk(kind, placebo_seed=None):
    pred = np.full(len(T), np.nan)
    rng = np.random.default_rng(placebo_seed) if placebo_seed is not None else None
    for a, b in zip(starts[:-1], starts[1:]):
        tr = (T + HOLD_S) < a
        te = (T >= a) & (T < b)
        if te.sum() == 0:
            continue
        ytr = y[tr].copy()
        if rng is not None:
            mo = months[tr]
            for u in np.unique(mo):
                ii = np.where(mo == u)[0]
                ytr[ii] = ytr[rng.permutation(ii)]
        A = Xv[tr]
        if kind == "ridge":
            mu, sd = np.nanmean(A, 0), np.nanstd(A, 0) + 1e-9
            f = lambda Z: np.nan_to_num((Z - mu) / sd)
            mod = make(kind).fit(f(A), ytr)
            pred[te] = mod.predict(f(Xv[te]))
        else:
            mod = make(kind).fit(A, ytr)
            pred[te] = mod.predict(Xv[te])
    return pred


def sim(pred, c):
    rows, end = [], -1
    for i in np.where(~np.isnan(pred))[0]:
        if T[i] >= end and abs(pred[i]) >= c:
            rows.append((T[i], netL[i] if pred[i] > 0 else netS[i]))
            end = T[i] + HOLD_S
    return pd.DataFrame(rows, columns=["T", "bp"])


def tt(v):
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 and v.std() > 0 else 0.0


def yr(df, a, b):
    t = pd.to_datetime(df["T"], unit="s")
    return df[(t >= a) & (t < b)].bp.to_numpy()


cells = [(k, c) for k in ("ridge", "gbm") for c in (1.0, 2.0)]


def evaluate(pred):
    out = {}
    for k, c in cells:
        out[(k, c)] = None
    return out


PRED = {k: walk(k) for k in ("ridge", "gbm")}
print(f"{'cell':14s}{'nDEV':>5s}{'netbp':>7s}{'tDEV':>6s}{'hit':>4s} | {'nVAL':>4s}{'netbp':>7s}{'tVAL':>6s} | yearly 23/24/25 | IC(oos) | pass")
res = {}
for k, c in cells:
    s = sim(PRED[k], c)
    a, v = yr(s, "2023-01-01", "2025-01-01"), yr(s, "2025-01-01", "2026-01-01")
    ys = [yr(s, f"{Y}-01-01", f"{Y + 1}-01-01").mean() if len(yr(s, f"{Y}-01-01", f"{Y + 1}-01-01")) > 5 else np.nan for Y in (2023, 2024, 2025)]
    m = ~np.isnan(PRED[k])
    ic = spearmanr(PRED[k][m], y[m])[0]
    good = len(a) >= 100 and a.mean() > 1.0 and tt(a) >= 3.4 and len(v) >= 40 and v.mean() > 0 and tt(v) >= 1.65 and all(np.nan_to_num(ys, nan=-1) > 0)
    res[(k, c)] = (tt(a), good)
    print(f"{k + ' c=' + str(c):14s}{len(a):5d}{a.mean():7.2f}{tt(a):6.2f}{(a > 0).mean() * 100:4.0f} | {len(v):4d}{v.mean():7.2f}{tt(v):6.2f} | " + "/".join(f"{x:+.1f}" for x in ys) + f" | {ic:+.3f} | {good}")
t0, t1 = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-01-01")
tm = pd.to_datetime(T, unit="s")
msk = (tm >= t0) & (tm < t1)
print(f"long-only drift yardstick (every slot): net {netL[msk].mean():+.2f} bp/4h; short-only {netS[msk].mean():+.2f}; hit-rate of prediction sign (gbm): {np.mean(np.sign(PRED['gbm'][msk]) == np.sign(y[msk])) * 100:.1f}%")
best = max(res, key=lambda z: res[z][0])
s = sim(PRED[best[0]], best[1])
s["hour"] = (s["T"] // 3600) % 24
print("by entry hour (best DEV cell %s):" % (best,), s.groupby("hour").bp.agg(["count", "mean"]).round(2).T.to_string())
pl = []
for seed in range(61, 66):
    b = -9
    for k in ("ridge", "gbm"):
        pr = walk(k, seed)
        for c in (1.0, 2.0):
            sp = sim(pr, c)
            a = yr(sp, "2023-01-01", "2025-01-01")
            if len(a) > 10:
                b = max(b, tt(a))
    pl.append(b)
    print("placebo seed", seed, "best DEV t", round(b, 2))
cap = max(pl)
passed = [c for c, v in res.items() if v[1] and v[0] > cap]
print("placebo max best t %.2f; real best t %.2f; PASSED all gates: %s" % (cap, max(v[0] for v in res.values()), passed))
if HOLD:
    for k, c in passed:
        sp = sim(PRED[k], c)
        h = yr(sp, "2026-01-01", "2026-10-01")
        print("HOLD", k, c, len(h), round(h.mean(), 2), round(tt(h), 2))
