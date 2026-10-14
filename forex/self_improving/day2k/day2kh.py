"""DAY2K-H: will the rest of the day be bullish or bearish? PREREG_DAY2K_H.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kh --dry-run | --calibrate | --run"""
import sys, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from forex.self_improving.day2k import day2k as D, day2kb as B, day2kc as C, day2ke as E

warnings.filterwarnings("ignore")
NAMES = C.NAMES; N = len(NAMES); CTX = ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "BTCUSD", "WTI", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]
OWN = ["m1", "m5", "m20", "am", "pdh", "pdl", "apos", "rr", "arng", "spr", "tvr", "dow"]
USD_PAIRS = [("AUDUSD", -1), ("EURUSD", -1), ("GBPUSD", -1), ("NZDUSD", -1), ("USDCAD", 1), ("USDCHF", 1), ("USDJPY", 1)]


def targets(days):
    """y_ret[d, market, ti] = (mid(21:55 bar open) - mid(T+60 bar open)) / ATR20, NaN when a bar is missing"""
    full = D.trading_days("2021-10-01", D.VAL_HI); out = np.full((len(days), N, 2), np.nan)
    for mi, sym in enumerate(NAMES):
        A = D.load(sym); t = A["t"]; atr = D.atr20(A, full)[np.isin(full, days)]; mid_o = (A["bo"] + A["ao"]) / 2
        for ti, T in enumerate(D.TS):
            e = np.searchsorted(t, days * 86400 + T + 60); x = np.searchsorted(t, days * 86400 + D.EXIT)
            ok = (e < len(t)) & (x < len(t)); ee, xx = np.clip(e, 0, len(t) - 1), np.clip(x, 0, len(t) - 1); ok &= (t[ee] == days * 86400 + T + 60) & (t[xx] == days * 86400 + D.EXIT)
            out[:, mi, ti] = np.where(ok, (mid_o[xx] - mid_o[ee]) / atr, np.nan)
    return out


def load_all():
    days, R, RES, S, FC = C.build_all(); yret = targets(days); gi = NAMES.index("XAUUSD")
    d2, R2, RES2, Fg, usd, mac, dates = E.data(); assert (d2 == days).all()
    spr = np.nanmedian(FC[:, :, 0, B.FI["spr"]], axis=0); keep = spr <= 0.02
    return days, S, FC, yret, Fg, usd, mac, keep, gi


def ctx_matrix(S, usd, ti):
    cols = [S[:, NAMES.index(m), ti, 2].astype(float) for m in CTX] + [usd[:, ti, 0], usd[:, ti, 1]]
    return np.column_stack(cols)


def gold_X(S, Fg, usd, mac, ti):
    return np.column_stack([E.X_for(Fg, usd, mac, ti), ctx_matrix(S, usd, ti)])


def pooled_X(FC, S, usd, ti, keep):
    d = FC.shape[0]; ctx = ctx_matrix(S, usd, ti); rows = []; idx = []
    for mi in range(N):
        if not keep[mi]: continue
        own = np.column_stack([FC[:, mi, ti, B.FI[c]].astype(float) for c in OWN] + [np.full(d, C.CODE[C.CLASS[NAMES[mi]]], float)])
        rows.append(np.column_stack([own, ctx])); idx.append(np.full(d, mi))
    return np.stack(rows, 1)                                                 # [day, market, feature]


def wf_prob(X, y, days, kind, leak=False):
    """X [rows, f], y [rows] 0/1/NaN, `days` per row; quarterly expanding refit from 2022-12-01; returns P(up) per row (NaN before scoring)"""
    if leak: X = np.column_stack([X, np.nan_to_num(y, nan=0.5)])
    p = np.full(len(y), np.nan); edges = sorted(set([B.SCORE_START] + [int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) for yy in range(2022, 2027) for mm in (3, 6, 9, 12) if int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) > B.SCORE_START] + [int(days.max()) + 1]))
    for a, b in zip(edges[:-1], edges[1:]):
        tr = (days < a) & np.isfinite(y); te = (days >= a) & (days < b)
        if te.sum() == 0 or tr.sum() < 200: continue
        if kind == "HGB": m = HistGradientBoostingClassifier(max_depth=2, max_iter=100, learning_rate=0.05, min_samples_leaf=60, l2_regularization=1.0, random_state=0).fit(X[tr], y[tr]); p[te] = m.predict_proba(X[te])[:, 1]
        else:
            Xt = np.nan_to_num(X[tr]); sc = StandardScaler().fit(Xt); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(Xt), y[tr]); p[te] = m.predict_proba(sc.transform(np.nan_to_num(X[te])))[:, 1]
    return p


def blockt(x, b=5):
    x = x[np.isfinite(x)]; n = len(x) // b
    if n < 10: return np.nan
    m = x[:n * b].reshape(n, b).mean(1); return float(m.mean() / (m.std(ddof=1) / np.sqrt(n)))


def evaluate(name, p, y, ret, dayidx, days):
    """p/y/ret per row, dayidx = row -> day index; per-day mean of correct (pooled) then block t"""
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); ok = np.isfinite(p) & np.isfinite(y)
    corr = np.where(ok, ((p > 0.5) == (y > 0.5)).astype(float), np.nan); sgn = np.where(ok, np.where(p > 0.5, 1.0, -1.0) * ret, np.nan); out = {}
    for lab, m in (("dev", dev), ("val", val)):
        rm = m[dayidx] & ok; dc = pd.Series(corr[rm]).groupby(dayidx[rm]).mean().reindex(np.where(m)[0]).to_numpy(); ds = pd.Series(sgn[rm]).groupby(dayidx[rm]).mean().reindex(np.where(m)[0]).to_numpy()
        out[lab] = dict(hit=float(np.nanmean(corr[rm])), t=blockt(dc - 0.5), upr=float(np.nanmean(y[rm])), auc=float(roc_auc_score(y[rm] > 0.5, p[rm])) if len(np.unique(y[rm])) > 1 else np.nan, ret=float(np.nanmean(sgn[rm])), n=int(rm.sum()))
    return out


def yardsticks(days, S, FC, yret, keep, ti, pooled):
    ys = {}; m1 = FC[:, :, ti, B.FI["m1"]]; m20 = FC[:, :, ti, B.FI["m20"]]; am = FC[:, :, ti, B.FI["am"]]
    for nm, sig in (("always-up", np.ones_like(m1)), ("yesterday", np.sign(m1)), ("trend20", np.sign(m20)), ("am-continue", np.sign(am)), ("am-fade", -np.sign(am))):
        ys[nm] = sig
    return ys


def main():
    a = sys.argv[1:]; days, S, FC, yret, Fg, usd, mac, keep, gi = load_all(); pd.set_option("display.width", 220)
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI))
    if "--dry-run" in a:
        print("markets in the pooled model:", int(keep.sum()), "| gold rows with a target:", [int(np.isfinite(yret[:, gi, ti]).sum()) for ti in range(2)], "| pooled rows:", [int(np.isfinite(yret[:, keep, ti]).sum()) for ti in range(2)])
        print("up-rate of gold (rest of day) T10:05 / T16:35:", [round(float(np.nanmean(yret[:, gi, ti] > 0)), 3) for ti in range(2)], "| pooled:", [round(float(np.nanmean(yret[:, keep, ti] > 0)), 3) for ti in range(2)])
        rng = np.random.default_rng(8); bad = n = 0; full = D.trading_days("2021-10-01", D.VAL_HI)
        for _ in range(30):
            mi = int(rng.integers(N)); di = int(rng.integers(150, len(days))); ti = int(rng.integers(2)); A = D.load(NAMES[mi]); cut = int(days[di]) * 86400 + D.TS[ti]
            m = A["t"] < cut; Bz = {k: v[m] for k, v in A.items()}; atr = D.atr20(Bz, full); sc = D.scores_for(Bz, full, atr); j = int(np.searchsorted(full, days[di])); n += 1
            bad += int(not np.isclose(np.nan_to_num(sc[j, ti, 2], nan=-99), np.nan_to_num(S[di, mi, ti, 2], nan=-99), atol=1e-4))
        print(f"truncation test (cross-market morning move from bars before T): {n - bad}/{n} identical"); return
    results = []
    for ti, T in enumerate(D.TS):
        tn = f"T{T // 3600:02d}{(T % 3600) // 60:02d}"
        yg = np.where(np.isfinite(yret[:, gi, ti]), (yret[:, gi, ti] > 0).astype(float), np.nan); Xg = gold_X(S, Fg, usd, mac, ti)
        Xp = pooled_X(FC, S, usd, ti, keep); nd, nm, nf = Xp.shape; Xpf = Xp.reshape(-1, nf); retp = yret[:, keep, ti].reshape(-1); yp = np.where(np.isfinite(retp), (retp > 0).astype(float), np.nan)
        dayrow = np.repeat(np.arange(nd), nm); dayg = np.arange(nd)
        for kind in ("LOGIT", "HGB"):
            for world, seed in ([("real", None)] + ([("leak", None)] if "--calibrate" in a else []) + ([("p161", 161), ("p162", 162), ("p163", 163)] if "--calibrate" in a else [])):
                if "--calibrate" not in a and world != "real": continue
                perm = np.random.default_rng(seed).permutation(nd) if seed else None
                for scope in ("gold", "pooled"):
                    if scope == "gold": X, y, r, di, dd = Xg, yg, yret[:, gi, ti], dayg, days
                    else: X, y, r, di, dd = Xpf, yp, retp, dayrow, days[dayrow]
                    yy = y.copy()
                    if perm is not None:
                        if scope == "gold": yy = y[perm]
                        else: yy = y.reshape(nd, nm)[perm].reshape(-1)
                    p = wf_prob(X, yy, dd, kind, leak=(world == "leak")); ev = evaluate(f"{scope}-{tn}-{kind}", p, yy, r, di, days)
                    base = {}
                    if world == "real":
                        ys = yardsticks(days, S, FC, yret, keep, ti, scope == "pooled")
                        for nmy, sig in ys.items():
                            s_ = sig[:, gi] if scope == "gold" else sig[:, keep].reshape(-1)
                            hit_ = np.where(np.isfinite(y) & np.isfinite(s_) & (s_ != 0), ((s_ > 0) == (y > 0.5)).astype(float), np.nan); dm = dev[di] if True else None
                            base[nmy] = float(np.nanmean(hit_[(dev[di]) & np.isfinite(hit_)]))
                    results.append(dict(scope=scope, T=tn, model=kind, world=world, dev_hit=ev["dev"]["hit"], dev_t=ev["dev"]["t"], dev_up=ev["dev"]["upr"], dev_auc=ev["dev"]["auc"], dev_ret=ev["dev"]["ret"], val_hit=ev["val"]["hit"], val_t=ev["val"]["t"], val_up=ev["val"]["upr"], val_auc=ev["val"]["auc"], val_ret=ev["val"]["ret"], base=base))
    R_ = pd.DataFrame(results); R_["best_base"] = R_.base.apply(lambda d: max(d.values()) if d else np.nan)
    R_["S1"] = (R_.dev_t >= 2.5) & (R_.dev_hit > R_.best_base) & (R_.val_hit > 0.5) & (R_.val_t >= 1.65) & (R_.val_hit > R_.val_up)
    if "--calibrate" in a:
        L = R_[R_.world == "leak"]; print("POSITIVE CONTROL (label leaked): dev hit", L.dev_hit.round(3).tolist())
        for w in ("p161", "p162", "p163"): q = R_[R_.world == w]; print(f"placebo {w}: S1-like survivors {int(((q.dev_t >= 2.5) & (q.val_t >= 1.65) & (q.val_hit > 0.5)).sum())} | best dev t {q.dev_t.max():.2f} best val t {q.val_t.max():.2f}")
        return
    R_.drop(columns=["base"]).to_csv(D.CACHE / "DAY2KH_cells.csv", index=False)
    print(R_.drop(columns=["base", "world"]).round(3).to_string(index=False)); print("S1 survivors:", int(R_.S1.sum()))
    for _, r in R_.iterrows(): print(f"  yardsticks DEV' hit {r.scope}-{r['T']}-{r.model}:", {k: round(v, 3) for k, v in r.base.items()})


if __name__ == "__main__":
    main()
