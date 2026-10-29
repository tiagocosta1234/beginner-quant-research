"""EURUSD-OF exactly as in PREREG_EURUSD_OF.md.  python -m forex.ea_research.eurusd_of [--dry] [--hold]"""
import sys, itertools, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
CUT_MS = int(pd.Timestamp("2026-10-14" if HOLD else "2026-08-16").timestamp() * 1000)   # server-clock epoch (naive treated as UTC), same convention as the M1 files
SLIP = 0.1
MONTHS = ["2025-10", "2025-11", "2025-12"] + [f"2026-{m:02d}" for m in range(1, 11 if HOLD else 9)]
# ------------------------------------------------------------------ M1 fills
d = pd.read_parquet("forex/data_mt5/EURUSD_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
d = d[(d.t >= 1759276800) & (d.t * 1000 < CUT_MS)]
IX = pd.Index(d.t.to_numpy())
BO, AO, MID = d.bo.to_numpy(), d.ao.to_numpy(), (d.bo + d.ao).to_numpy() / 2


def idx(t):
    return IX.get_indexer(np.atleast_1d(np.asarray(t)))


def mid(t):
    i = idx(t)
    return np.where(i >= 0, MID[np.maximum(i, 0)], np.nan)


# ------------------------------------------------------------------ minute grid from ticks
M0 = 1759276800 // 60
M1 = CUT_MS // 60000
NM = M1 - M0 + 1
acc = {k: np.zeros(NM) for k in ("n", "up", "dn", "aon", "bon")}
last_mid = np.full(NM, np.nan)
for mo in MONTHS:
    t = pd.read_parquet(f"data/ticks/EURUSD/{mo}.parquet")
    t = t[t.time_msc < CUT_MS]
    ms = t.time_msc.to_numpy() // 60000 - M0
    b, a, f = t.bid.to_numpy(), t.ask.to_numpy(), t["flags"].to_numpy().astype(int)
    md = (a + b) / 2
    dm = np.r_[0.0, np.diff(md)]
    for key, v in (("n", np.ones(len(t))), ("up", (dm > 0) * 1.0), ("dn", (dm < 0) * 1.0),
                   ("aon", (((f & 4) > 0) & ((f & 2) == 0)) * 1.0), ("bon", (((f & 2) > 0) & ((f & 4) == 0)) * 1.0)):
        acc[key] += np.bincount(ms, weights=v, minlength=NM)[:NM]
PRE = {k: np.r_[0.0, np.cumsum(v)] for k, v in acc.items()}


def win(key, m, W):
    return PRE[key][m - M0] - PRE[key][m - M0 - W]


# ------------------------------------------------------------------ slots
ms_all = np.arange(M0 + 120, M1 - 130)
t_all = ms_all * 60
hr, mn = (t_all // 3600) % 24, ms_all % 60
wd = ((t_all // 86400) + 3) % 7
sel = np.isin(mn, (15, 30, 45)) & (hr >= 2) & (hr <= 20) & (wd < 5)
ms_s, T = ms_all[sel], t_all[sel]
feats = {}
for W in (5, 15, 60):
    n, up, dn = win("n", ms_s, W), win("up", ms_s, W), win("dn", ms_s, W)
    aon, bon = win("aon", ms_s, W), win("bon", ms_s, W)
    feats[f"I{W}"] = np.where((n >= 30) & (up + dn > 0), (up - dn) / np.maximum(up + dn, 1), np.nan)
    feats[f"Q{W}"] = np.where((n >= 30) & (aon + bon > 0), (aon - bon) / np.maximum(aon + bon, 1), np.nan)
    for k in ("I", "Q"):   # AMENDMENT A1: causal z-score against the previous 1000 slots (about 15 trading days)
        sr = pd.Series(feats[f"{k}{W}"])
        mu, sd = sr.rolling(1000, min_periods=300).mean().shift(1), sr.rolling(1000, min_periods=300).std().shift(1)
        feats[f"z{k}{W}"] = ((sr - mu) / sd).to_numpy()
    feats[f"n{W}"] = n
per = {"DEV": (pd.Timestamp("2025-10-01").timestamp(), pd.Timestamp("2026-03-01").timestamp()),
       "VAL": (pd.Timestamp("2026-03-01").timestamp(), pd.Timestamp("2026-06-01").timestamp()),
       "TEST": (pd.Timestamp("2026-06-01").timestamp(), pd.Timestamp("2026-08-16").timestamp()),
       "HOLD": (pd.Timestamp("2026-08-16").timestamp(), pd.Timestamp("2026-10-14").timestamp())}
HS = (15, 30, 60)
NET = {}
for H in HS:
    te, tx = T, T + H * 60
    iE, iX = idx(te), idx(tx)
    ok = (iE >= 0) & (iX >= 0) & ~np.isin((te // 3600) % 24, (23, 0)) & ~np.isin((tx // 3600) % 24, (23, 0)) & (((tx // 60) % 60) >= 5)
    L = np.where(ok, (BO[np.maximum(iX, 0)] / AO[np.maximum(iE, 0)] - 1) * 1e4 - 2 * SLIP, np.nan)
    S = np.where(ok, (BO[np.maximum(iE, 0)] / AO[np.maximum(iX, 0)] - 1) * 1e4 - 2 * SLIP, np.nan)
    y = np.where(ok, (mid(tx) / mid(te) - 1) * 1e4, np.nan)
    NET[H] = (L, S, y, ok)
print("minutes", NM, "slots", len(T), "span", pd.Timestamp(T.min(), unit="s").date(), pd.Timestamp(T.max(), unit="s").date(),
      "| tradable per H:", {H: int(NET[H][3].sum()) for H in HS})
if DRY:
    mm = (acc["n"] > 0)
    mt = pd.Series(np.where(mm, 1, np.nan))
    chk_m = np.arange(M0 + 5000, M0 + 5000 + 20000, 997)
    print("tick-derived n per minute vs M1 bar present (should agree where bars exist):",
          [(int(acc['n'][m - M0]), bool(idx(m * 60)[0] >= 0)) for m in chk_m[:8]])
    for k in ("zI5", "zQ5", "zI60", "zQ60"):
        v = feats[k][~np.isnan(feats[k])]
        print(k, "active|z|>=1.5:", round(np.mean(np.abs(v) >= 1.5), 2), "mean", round(v.mean(), 3), "sd", round(v.std(), 3))
    # 1-minute return consistency between tick-derived and M1 mid (clock check)
    sm = ms_s[:2000]
    print("clock check: corr(sign of I5, sign of M1 5-min return before the slot) =",
          round(float(np.corrcoef(np.sign(np.nan_to_num(feats['I5'][:2000])), np.sign(np.nan_to_num(mid(T[:2000] - 60) / mid(T[:2000] - 360) - 1)))[0, 1]), 3))
    sys.exit()


def tt(v):
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 and v.std() > 0 else 0.0


def sim(sig, H, lo=None, hi=None):
    L, S, _, ok = NET[H]
    rows, end = [], -1
    for i in np.where(sig != 0)[0]:
        if not ok[i] or T[i] < end:
            continue
        if lo is not None and not (lo <= T[i] < hi):
            continue
        rows.append((T[i], L[i] if sig[i] > 0 else S[i]))
        end = T[i] + H * 60
    return pd.DataFrame(rows, columns=["T", "bp"])


def part(df, p):
    a, b = per[p]
    return df[(df["T"] >= a) & (df["T"] < b)].bp.to_numpy()


cells = list(itertools.product(("I", "Q"), (5, 15, 60), ("cont", "fade"), HS))
sigs = {}
for f_, W, dr, H in cells:
    v = feats[f"z{f_}{W}"]
    s = np.where(np.abs(np.nan_to_num(v)) >= 1.5, np.sign(np.nan_to_num(v)), 0) * (1 if dr == "cont" else -1)
    sigs[(f_, W, dr, H)] = s
print(f"{'cell':22s}{'nDEV':>5s}{'net':>6s}{'tDEV':>6s} | {'nVAL':>4s}{'net':>6s}{'tVAL':>6s} | {'nTEST':>5s}{'net':>6s}{'tTEST':>6s} | pass")
res = {}
for c in cells:
    s = sim(sigs[c], c[3])
    a, v, tst = part(s, "DEV"), part(s, "VAL"), part(s, "TEST")
    good = len(a) >= 100 and a.mean() > 1.0 and tt(a) >= 3.6 and len(v) >= 40 and v.mean() > 0 and tt(v) >= 1.65 and len(tst) >= 40 and tst.mean() > 0 and tt(tst) >= 1.65
    res[c] = (tt(a), good)
    print(f"{str(c[:2]) + c[2] + str(c[3]):22s}{len(a):5d}{a.mean() if len(a) else 0:6.2f}{tt(a):6.2f} | {len(v):4d}{v.mean() if len(v) else 0:6.2f}{tt(v):6.2f} | {len(tst):5d}{tst.mean() if len(tst) else 0:6.2f}{tt(tst):6.2f} | {good}")
rng = np.random.default_rng(31)
mx = []
for _ in range(300):
    m_ = 0.0
    for c in cells:
        s0 = sigs[c]
        act = np.where(s0 != 0)[0]
        s = np.zeros(len(s0))
        s[act] = rng.permutation(s0[act])
        a = part(sim(s, c[3], *per["DEV"]), "DEV")
        if len(a) > 10:
            m_ = max(m_, abs(tt(a)))
    mx.append(m_)
ceil = np.percentile(mx, 95)
print("placebo max |t| over 36 rule cells (DEV): median %.2f, 95th %.2f; real best t %.2f" % (np.median(mx), ceil, max(v[0] for v in res.values())))
passed_rules = [c for c, v in res.items() if v[1] and v[0] > ceil]
print("RULE CELLS PASSED:", passed_rules)
# ------------------------------------------------------------------ ML cells
retf = {W: (mid(T - 60) / mid(T - 60 - W * 60) - 1) * 1e4 for W in (5, 15, 60)}
spr = (AO[np.maximum(idx(T - 60), 0)] - BO[np.maximum(idx(T - 60), 0)]) / mid(T - 60) * 1e4
XF = np.column_stack([feats["I5"], feats["I15"], feats["I60"], feats["Q5"], feats["Q15"], feats["Q60"], feats["n5"] / np.maximum(feats["n60"], 1),
                      retf[5], retf[15], retf[60], spr, (T // 3600) % 24])
day = T // 86400


def ml(H, seed=None):
    L, S, y, ok = NET[H]
    pred = np.full(len(T), np.nan)
    rng = np.random.default_rng(seed) if seed is not None else None
    for tr_hi, te_lo, te_hi in ((per["VAL"][0], per["VAL"][0], per["VAL"][1]), (per["TEST"][0], per["TEST"][0], per["TEST"][1])):
        tr = ok & (T + H * 60 < tr_hi) & ~np.isnan(y)
        te = (T >= te_lo) & (T < te_hi)
        ytr = y[tr].copy()
        if rng is not None:
            dd = day[tr]
            for u in np.unique(dd):
                ii = np.where(dd == u)[0]
                ytr[ii] = ytr[rng.permutation(ii)]
        mod = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0, random_state=0).fit(XF[tr], ytr)
        pred[te] = mod.predict(XF[te])
    return pred


def ml_eval(pred, H):
    s = np.where(np.abs(np.nan_to_num(pred)) >= 1.0, np.sign(np.nan_to_num(pred)), 0)
    tr_ = sim(s, H)
    return part(tr_, "VAL"), part(tr_, "TEST")


print("ML cells (VAL / TEST need mean > 0.5 bp, t >= 2.5, n >= 100):")
ml_pass = []
for H in HS:
    v, tst = ml_eval(ml(H), H)
    good = len(v) >= 100 and v.mean() > 0.5 and tt(v) >= 2.5 and len(tst) >= 100 and tst.mean() > 0.5 and tt(tst) >= 2.5
    print(f"  H={H}: VAL n {len(v)} net {v.mean() if len(v) else 0:.2f} t {tt(v):.2f} | TEST n {len(tst)} net {tst.mean() if len(tst) else 0:.2f} t {tt(tst):.2f} | {good}")
    if good:
        ml_pass.append(H)
pl = []
for seed in (71, 72, 73):
    for H in HS:
        v, tst = ml_eval(ml(H, seed), H)
        pl.append((seed, H, len(v), round(tt(v), 2), round(tt(tst), 2)))
print("ML placebo worlds (seed, H, nVAL, tVAL, tTEST):", pl)
print("ML PASSED:", ml_pass)
if HOLD and (passed_rules or ml_pass):
    print("HOLD cells: open only for the audited survivors")
