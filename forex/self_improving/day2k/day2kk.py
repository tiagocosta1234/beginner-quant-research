"""DAY2K-K: which group of FX pairs / indices has a next-day direction we are 80% sure of? PREREG_DAY2K_K.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kk --dry-run | --calibrate | --run"""
import sys, warnings
import numpy as np, pandas as pd
from scipy.stats import binom
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from forex.self_improving.day2k import day2k as D, day2kb as B, day2ke as E

warnings.filterwarnings("ignore")
IDX = ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"]; MK = list(E.FX28) + IDX; N = len(MK)      # E.FX28 is fixed (D.PAIRS is widened to 46 markets by the round-C import)
FEATS = ["r1", "r2", "r5", "r10", "r20", "r60", "rng", "pos20", "dow", "mend", "c_idx", "c_usd", "c_all", "dgs2", "dfii", "gvz", "vix", "surp", "nh"]
EXIT = D.EXIT


def build(days_all, tag="K"):
    f = D.CACHE / f"day2kk_{tag}.npz"
    if f.exists(): z = np.load(f, allow_pickle=True); return z["days"], z["X"], z["Y"]
    full = D.trading_days("2021-01-01", "2026-01-31"); days = full[(full >= D.d64("2021-12-01")) & (full <= D.d64(D.VAL_HI))]
    X55 = np.full((len(full), N), np.nan); RNG = np.full_like(X55, np.nan); ATR = np.full_like(X55, np.nan)
    for mi, sym in enumerate(MK):
        A = D.load(sym); t = A["t"]; mid_o = (A["bo"] + A["ao"]) / 2; atr = D.atr20(A, full); ATR[:, mi] = atr
        i = np.searchsorted(t, full * 86400 + EXIT); ii = np.clip(i, 0, len(t) - 1); ok = (i < len(t)) & (t[ii] == full * 86400 + EXIT); X55[:, mi] = np.where(ok, mid_o[ii], np.nan)
        di = t // 86400; u, st = np.unique(di, return_index=True); hi = np.maximum.reduceat(A["bh"], st); lo = np.minimum.reduceat(A["bl"], st); r = pd.Series(hi - lo, index=u).reindex(full).to_numpy(); RNG[:, mi] = r / atr
        print("  daily", sym, flush=True)
    def ch(k):
        o = np.full_like(X55, np.nan); o[k:] = (X55[k:] - X55[:-k]) / ATR[k:]; return o
    r1, r2, r5, r10, r20, r60 = ch(1), ch(2), ch(5), ch(10), ch(20), ch(60)
    roll_hi = pd.DataFrame(X55).rolling(20, min_periods=15).max().to_numpy(); roll_lo = pd.DataFrame(X55).rolling(20, min_periods=15).min().to_numpy(); pos = (X55 - roll_lo) / np.where(roll_hi > roll_lo, roll_hi - roll_lo, np.nan)
    d64 = full.astype("datetime64[D]"); dow = ((full + 3) % 7).astype(float); me = (d64.astype("datetime64[M]") + 1).astype("datetime64[D]"); mend = (np.busday_count(d64, me) <= 2).astype(float)
    ii_ = [MK.index(s) for s in IDX]; c_idx = np.nanmean(r1[:, ii_], axis=1); usd = np.zeros(len(full))
    for p, sg in (("AUDUSD", -1), ("EURUSD", -1), ("GBPUSD", -1), ("NZDUSD", -1), ("USDCAD", 1), ("USDCHF", 1), ("USDJPY", 1)): usd += sg * np.nan_to_num(r1[:, MK.index(p)]) / 7
    c_all = np.nanmean(r1, axis=1)
    mac, _ = E.macro(full); ev = B.events(); sur, nh = B.cal_feats(ev, full); u_ = B.CCY.index("USD"); nxt = np.zeros(len(full));
    et, cw, e3 = ev["USD"]; nh_t = np.array([np.searchsorted(e3, (d + 1) * 86400 + 86399, side="right") - np.searchsorted(e3, (d + 1) * 86400, side="left") for d in full], float)
    sur_t = np.array([cw[np.searchsorted(et, d * 86400 + EXIT, side="right")] - cw[np.searchsorted(et, d * 86400, side="left")] for d in full], float)
    X = np.full((len(full), N, len(FEATS)), np.nan, np.float32)
    for k, a in enumerate([r1, r2, r5, r10, r20, r60, RNG, pos]): X[:, :, k] = a
    X[:, :, 8] = dow[:, None]; X[:, :, 9] = mend[:, None]; X[:, :, 10] = c_idx[:, None]; X[:, :, 11] = usd[:, None]; X[:, :, 12] = c_all[:, None]
    for k, nm in enumerate(["dgs2_1", "dfii_1", "gvz_1", "vix_1"]): X[:, :, 13 + k] = mac[nm][:, None]
    X[:, :, 17] = (-sur_t)[:, None]; X[:, :, 18] = nh_t[:, None]
    Y = np.full((len(full), N), np.nan); Y[:-1] = np.where(np.isfinite(X55[1:]) & np.isfinite(X55[:-1]), (X55[1:] > X55[:-1]).astype(float), np.nan)
    m = np.isin(full, days); np.savez_compressed(f, days=full[m], X=X[m], Y=Y[m]); return full[m], X[m], Y[m]


def wf(X, Y, days, kind, leak=False, perm=None):
    nd, nm, nf = X.shape; Yp = Y[perm] if perm is not None else Y
    rowday = np.repeat(np.arange(nd), nm); Xf = X.reshape(-1, nf); yf = Yp.reshape(-1)
    if leak: Xf = np.column_stack([Xf, np.nan_to_num(yf, nan=0.5)])
    p = np.full(len(yf), np.nan); dd = days[rowday]
    edges = sorted(set([B.SCORE_START] + [int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) for yy in range(2022, 2027) for mm in (3, 6, 9, 12) if int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) > B.SCORE_START] + [int(days.max()) + 1]))
    for a, b in zip(edges[:-1], edges[1:]):
        tr = (dd < a - 1) & np.isfinite(yf); te = (dd >= a) & (dd < b)
        if te.sum() == 0: continue
        if kind == "HGB": m = HistGradientBoostingClassifier(max_depth=2, max_iter=100, learning_rate=0.05, min_samples_leaf=100, l2_regularization=1.0, random_state=0).fit(Xf[tr], yf[tr]); p[te] = m.predict_proba(Xf[te])[:, 1]
        else:
            Xt = np.nan_to_num(Xf[tr]); sc = StandardScaler().fit(Xt); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(Xt), yf[tr]); p[te] = m.predict_proba(sc.transform(np.nan_to_num(Xf[te])))[:, 1]
    return p.reshape(nd, nm), Yp


def claims(P, Yp, days, mi_class):
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); ok = np.isfinite(P) & np.isfinite(Yp); hit = np.where(ok, ((P > 0.5) == (Yp > 0.5)).astype(float), np.nan)
    dow = ((days + 3) % 7); groups = {MK[m]: (np.arange(len(days))[:, None], np.array([m])) for m in range(N)}; res = []
    def cell(name, mask_day, cols):
        mm = np.zeros(P.shape, bool); mm[np.ix_(mask_day, cols)] = True
        out = {}
        for lab, per in (("dev", dev), ("val", val)):
            s = mm & per[:, None] & ok; n = int(s.sum()); out[lab] = (n, float(hit[s].mean()) if n else np.nan)
        res.append((name, out))
    for m in range(N): cell(MK[m], np.ones(len(days), bool), [m])
    for cl, cols in (("fx", list(range(28))), ("index", list(range(28, N)))):   # 28 FX, then 6 indices
        for w in range(5): cell(f"{cl}-dow{w}", dow == w, cols)
    cl_ = [(n, o) for n, o in res if o["dev"][0] >= 40 and o["dev"][1] >= 0.80 and o["val"][0] >= 20 and o["val"][1] >= 0.75]
    return res, cl_, hit, ok


def reliability(P, Yp, days):
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); ok = np.isfinite(P) & np.isfinite(Yp); rows = []
    conf = np.abs(P - 0.5); hit = ((P > 0.5) == (Yp > 0.5)).astype(float)
    for lab, per in (("dev", dev), ("val", val)):
        s = ok & per[:, None]; thr_all = conf[s]
        for q in (1, 2, 5, 10, 20, 100):
            cut = np.percentile(thr_all, 100 - q) if q < 100 else -1; sel = s & (conf >= cut); rows.append(dict(period=lab, top_pct=q, n=int(sel.sum()), hit=float(hit[sel].mean()), mean_conf=float(conf[sel].mean() + 0.5)))
    return pd.DataFrame(rows)


def main():
    a = sys.argv[1:]; days, X, Y = build(None); pd.set_option("display.width", 220); nd = len(days)
    if "--dry-run" in a:
        print("days", nd, "markets", N, "features", len(FEATS), "| rows with a label:", int(np.isfinite(Y).sum()), "| up-rate:", round(float(np.nanmean(Y)), 3), "| feature coverage:", {FEATS[k]: round(float(np.isfinite(X[:, :, k]).mean()), 2) for k in range(len(FEATS))})
        full = D.trading_days("2021-01-01", "2026-01-31"); rng = np.random.default_rng(10); bad = n = 0
        for _ in range(25):
            mi = int(rng.integers(N)); di = int(rng.integers(100, nd - 2)); A = D.load(MK[mi]); cut = int(days[di]) * 86400 + EXIT; m = A["t"] < cut; Bz = {k: v[m] for k, v in A.items()}; t = Bz["t"]
            def x55(d):
                i = np.searchsorted(t, d * 86400 + EXIT); ii = np.clip(i, 0, len(t) - 1); return (Bz["bo"][ii] + Bz["ao"][ii]) / 2 if i < len(t) and t[ii] == d * 86400 + EXIT else np.nan
            a_ = D.atr20(Bz, full); j = int(np.searchsorted(full, days[di])); prev = [d for d in full if d < days[di]][-1]
            if not np.isfinite(x55(prev)): continue
            Xr1 = X[di, mi, 0]
            # r1 at the decision day uses X55 of day d, which is the 21:55 open: it is NOT in bars strictly before cut, so recompute with the d-1 value and compare r1 of the previous day
            r1_prev = (x55(prev) - x55([d for d in full if d < prev][-1])) / a_[np.searchsorted(full, prev)]; n += 1; bad += int(not np.isclose(np.nan_to_num(r1_prev, nan=-99), np.nan_to_num(X[di - 1, mi, 0], nan=-99), atol=1e-4) and np.isfinite(X[di - 1, mi, 0]))
        print(f"truncation test (previous day's 1-day change from bars before the decision): {n - bad}/{n} identical"); return
    mc = None
    if "--calibrate" in a:
        for kind in ("LOGIT",):
            P, Yp = wf(X, Y, days, kind, leak=True); ev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); ok = np.isfinite(P) & np.isfinite(Yp) & ev[:, None]; print("POSITIVE CONTROL (label leaked) hit rate:", round(float(((P[ok] > 0.5) == (Yp[ok] > 0.5)).mean()), 3), flush=True)
        for kind in ("LOGIT", "HGB"):
            for sd in (191, 192, 193, 194, 195):
                perm = np.random.default_rng(sd).permutation(nd); P, Yp = wf(X, Y, days, kind, perm=perm); res, cl, hit, ok = claims(P, Yp, days, mc); print(f"placebo {kind} {sd}: claims {len(cl)} | cells with DEV hit >= 0.80 and n >= 40: {sum(1 for n, o in res if o['dev'][0] >= 40 and o['dev'][1] >= 0.8)} | best DEV hit {max(o['dev'][1] for n, o in res if o['dev'][0] >= 40):.3f}", flush=True)
        return
    if "--run" in a:
        out = {}
        for kind in ("LOGIT", "HGB"):
            P, Yp = wf(X, Y, days, kind); res, cl, hit, ok = claims(P, Yp, days, mc); rel = reliability(P, Yp, days); out[kind] = (res, cl)
            print(f"\n=== {kind} ===\nRELIABILITY (hit rate of the most confident predictions; chance 0.5):"); print(rel.round(3).to_string(index=False))
            r2 = [(n, o) for n, o in res if o["dev"][0] >= 40]; r2.sort(key=lambda z: -z[1]["dev"][1])
            print("top 8 groups by DEV' hit rate (n>=40):"); [print(f"  {n:12s} DEV' n {o['dev'][0]:4d} hit {o['dev'][1]:.3f} | VAL n {o['val'][0]:4d} hit {o['val'][1]:.3f}") for n, o in r2[:8]]
            print(f"groups with DEV' hit >= 0.80 (n>=40): {sum(1 for n, o in res if o['dev'][0] >= 40 and o['dev'][1] >= 0.8)} | CLAIMS (also VAL n>=20 and hit>=0.75): {len(cl)}", [n for n, o in cl])
            print(f"pooled hit DEV' {np.nanmean(hit[(days >= B.SCORE_START)[:, None] & (days <= D.d64(D.DEV_HI))[:, None] & ok]):.3f}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
