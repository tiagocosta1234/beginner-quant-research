"""PREREG_ML_DIRECTION2.md: same 81 features, pure direction label from a symmetric bracket (k x prior daily ATR) after 08:15.
Usage (from edge_lab): python ml_direction2.py"""
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, log_loss
import ml_direction as M

KS = (0.15, 0.25, 0.50)


def labels(name):
    src, cost = M.MK[name]
    d = M.load_min(src)
    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    tr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    T = d.index.to_numpy(); H, L, C, O = (d[k].to_numpy() for k in ("high", "low", "close", "open"))
    tod = (d.index.hour * 60 + d.index.minute).to_numpy()
    out = []
    for dt in day.index:
        if dt.weekday() >= 5 or not (atr.get(dt, np.nan) > 0): continue
        a = np.searchsorted(T, np.datetime64(dt)); b = np.searchsorted(T, np.datetime64(dt + pd.Timedelta(days=1)))
        t = tod[a:b]
        cw = np.flatnonzero((t >= 480) & (t < 495)) + a
        post = np.flatnonzero((t >= 495) & (t <= 960)) + a
        if len(cw) < 10 or len(post) < 60 or tod[post[-1]] < 955: continue
        e = C[cw[-1]]; hi, lo, op, tt = H[post], L[post], O[post], tod[post]
        end = np.flatnonzero(tt >= 960); ke = end[0] if len(end) else len(tt) - 1
        rec = dict(date=dt, market=name)
        for k in KS:
            X = k * atr[dt]
            up = np.flatnonzero(hi[:ke] >= e + X); dn = np.flatnonzero(lo[:ke] <= e - X)
            iu = up[0] if len(up) else 10 ** 9; idn = dn[0] if len(dn) else 10 ** 9
            if iu < idn: g = 1.0; y = 1
            elif idn < iu: g = -1.0; y = 0
            elif iu == idn and iu < 10 ** 9: g = -1.0; y = 0          # same bar: stop first for a long = the down move counts first
            else: g = (op[ke] - e) / X; y = int(op[ke] > e)
            rec["g%s" % k] = g; rec["y%s" % k] = y; rec["c%s" % k] = cost / X
        out.append(rec)
    return pd.DataFrame(out)


def main():
    F = pd.read_parquet("ml_direction_features.parquet")
    Lb = pd.concat([labels(m) for m in M.MK], ignore_index=True)
    F = F.merge(Lb, on=["date", "market"], how="inner")
    feats = [c for c in F.columns if c not in ("date", "market", "RL", "RS", "y", "yr", "cdir", "x_ret0815") and not c.startswith(("g0", "y0", "c0"))]
    print("rows %d, features %d; up-first rate k0.15 %.3f k0.25 %.3f k0.5 %.3f" % (len(F), len(feats), F["y0.15"].mean(), F["y0.25"].mean(), F["y0.5"].mean()))
    rng = np.random.default_rng(20261026)
    ud = np.unique(F.date.to_numpy())
    for k in KS:
        yk, gk, ck = "y%s" % k, "g%s" % k, "c%s" % k
        recs = []
        for Y in range(2021, 2027):
            tr, te = F[F.yr < Y], F[F.yr == Y]
            keep = [c for c in feats if tr[c].notna().any()]
            Xtr, Xte = tr[keep].to_numpy(float), te[keep].to_numpy(float)
            r = te[["date", "market", "yr", yk, gk, ck]].copy()
            for mdl in ("M1", "M3"):
                r[mdl] = M.fit_predict(mdl, Xtr, tr[yk].to_numpy(), tr.yr.to_numpy(), Xte)
            r["base"] = tr[yk].mean()
            recs.append(r)
        P = pd.concat(recs, ignore_index=True)
        P.to_parquet("ml_direction2_oos_k%s.parquet" % k)
        di = np.searchsorted(ud, P.date.to_numpy())
        print("\n=== bracket k = %.2f x ATR%s ===" % (k, " (PRIMARY)" if k == 0.25 else ""))
        for mdl in ("M1", "M3"):
            p = P[mdl].to_numpy(); side = np.where(p >= 0.5, 1, -1)
            R = side * P[gk].to_numpy() - P[ck].to_numpy(); Mi = -side * P[gk].to_numpy() - P[ck].to_numpy()
            pv = float((np.where(rng.random((20000, len(R))) < 0.5, R, Mi).mean(axis=1) >= R.mean()).mean())
            auc = roc_auc_score(P[yk], p)
            bs = []
            for _ in range(300):
                w = np.bincount(rng.integers(0, len(ud), len(ud)), minlength=len(ud))[di]
                bs.append(roc_auc_score(P[yk], p, sample_weight=w))
            lo, hi = np.percentile(bs, [2.5, 97.5])
            yrs = pd.Series(R, index=P.yr.to_numpy()).groupby(level=0).mean(); pos = int((yrs > 0).sum())
            hit = ((side > 0) == (P[yk].to_numpy() == 1)).mean()
            ok = mdl == "M1" and k == 0.25 and R.mean() > 0 and pv <= 0.01 and lo > 0.5 and pos >= 4
            print("%s  n %d  AUC %.4f (%.4f..%.4f)  direction hit %.1f%%  logloss %.4f vs base %.4f  mean net R %+.4f  random-side P %.4f  years>0 %d/6  %s" % (
                mdl, len(P), auc, lo, hi, 100 * hit, log_loss(P[yk], np.clip(p, 1e-4, 1 - 1e-4)), log_loss(P[yk], np.clip(P.base, 1e-4, 1 - 1e-4)),
                R.mean(), pv, pos, ("-> MODEL WORKS" if ok else "-> NOT SHOWN") if (mdl == "M1" and k == 0.25) else "(secondary)"))
            print("      by year: " + " ".join("%d %+.3f" % (y, v) for y, v in yrs.items()))
            print("      by market: " + " ".join("%s %+.3f" % (m, v) for m, v in pd.Series(R, index=P.market.to_numpy()).groupby(level=0).mean().items()))
            conf = (p >= 0.55) | (p <= 0.45)
            if conf.sum():
                print("      confident days only (P>=.55 or <=.45): n %d, hit %.1f%%, mean net R %+.4f" % (conf.sum(), 100 * ((side > 0) == (P[yk].to_numpy() == 1))[conf].mean(), R[conf].mean()))
            if mdl == "M1":
                for a, b in ((0, .45), (.45, .5), (.5, .55), (.55, 1.01)):
                    s = (p >= a) & (p < b)
                    if s.sum(): print("      P %.2f-%.2f: n %4d  realized up-first %.3f" % (a, min(b, 1), s.sum(), P[yk].to_numpy()[s].mean()))


if __name__ == "__main__":
    main()
