"""PREREG_ML_DIRECTION.md: machine-learning P(long) for the one London-open trade a day (technical + fundamental features), strict walk-forward.
Usage (from edge_lab): python ml_direction.py      (writes ml_direction_features.parquet and ml_direction_oos.parquet next to it)"""
import glob, os, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")
DB = "D:/finance/beginner-quant-research/futures/data/databento/futures_%s.F_1m.parquet"
MAC = "D:/finance/data_macro/"
DLY = "D:/finance/beginner-quant-research/futures/data/daily/"
MK = {"MGC": ("GC", 0.32), "MNQ": ("NQ", 1.1), "MES": ("ES", 0.74), "SI": ("SI", 0.0112), "MYM": ("DOW", 4.4)}
COT = {"MGC": "GOLD - COMMODITY EXCHANGE", "MNQ": "NASDAQ MINI", "MES": "E-MINI S&P 500 -", "SI": "SILVER - COMMODITY", "MYM": "DJIA"}


def load_min(src):
    if src == "DOW":
        r = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/DOW_M1_rates.parquet").drop_duplicates("t").sort_values("t")
        r = r[(r.bo > 0) & (r.ao >= r.bo)]
        utc = pd.to_datetime(r.t, unit="s").pipe(lambda x: x - pd.Timedelta(hours=7)).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
        d = pd.DataFrame({k: ((r["b" + k[0]] + r["a" + k[0]]) / 2).to_numpy() for k in ("open", "high", "low", "close")}, index=utc.to_numpy())
        d["volume"] = np.nan
        d = d[~d.index.isna()]; d.index = pd.DatetimeIndex(d.index).tz_convert("UTC")
    else:
        d = pd.read_parquet(DB % src).sort_values("ts").set_index("ts")
        d = d[["open", "high", "low", "close"] + (["volume"] if "volume" in d.columns else [])]
        if "volume" not in d.columns: d["volume"] = np.nan
    d = d[~d.index.duplicated()].sort_index()
    d.index = d.index.tz_convert("Europe/London").tz_localize(None)
    return d[~d.index.duplicated()]


def rsi(s, n=14):
    dlt = s.diff(); up = dlt.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def market_days(name):
    src, cost = MK[name]
    d = load_min(src)
    d["ema1"] = d.close.ewm(span=12, adjust=False).mean()
    c15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = c15.ewm(span=12, adjust=False).mean(); r15 = rsi(c15)
    c1h = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = c1h.ewm(span=12, adjust=False).mean(); r1h = rsi(c1h)
    day = d.groupby(d.index.normalize()).agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"), v=("volume", "sum"))
    pc = day.c.shift(1)
    tr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1)
    day["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    for n in (20, 50, 200): day["sma%d" % n] = day.c.rolling(n).mean().shift(1)
    day["rsi_d"] = rsi(day.c).shift(1)
    day["pc"], day["ph"], day["pl"], day["po"] = day.c.shift(1), day.h.shift(1), day.l.shift(1), day.o.shift(1)
    day["c5"], day["c20"] = day.c.shift(6), day.c.shift(21)
    T = d.index.to_numpy(); O, H, L, C, V, E = (d[k].to_numpy() for k in ("open", "high", "low", "close", "volume", "ema1"))
    tod = (d.index.hour * 60 + d.index.minute).to_numpy()
    rows = []
    vol15 = []
    for dt in day.index:
        if dt.weekday() >= 5: continue
        dr = day.loc[dt]
        if not (dr.atr > 0) or np.isnan(dr.sma20): continue
        a = np.searchsorted(T, np.datetime64(dt)); b = np.searchsorted(T, np.datetime64(dt + pd.Timedelta(days=1)))
        t = tod[a:b]
        cw = np.flatnonzero((t >= 480) & (t < 495)) + a
        post = np.flatnonzero((t >= 495) & (t <= 960)) + a
        if len(cw) < 10 or len(post) < 60 or tod[post[-1]] < 955: continue
        co, ch, cl, cc = O[cw[0]], H[cw].max(), L[cw].min(), C[cw[-1]]
        rng = ch - cl; atr = dr.atr
        res = {}
        for side, lab in ((1, "RL"), (-1, "RS")):
            risk = max((cc - cl if side > 0 else ch - cc) + 0.5 * rng, 0.03 * atr)
            sl, tp = cc - side * risk, cc + side * risk
            hi, lo, op, tt = H[post], L[post], O[post], tod[post]
            end = np.flatnonzero(tt >= 960)
            ke = end[0] if len(end) else len(tt) - 1
            hs = np.flatnonzero((lo[:ke] <= sl) if side > 0 else (hi[:ke] >= sl))
            ht = np.flatnonzero((hi[:ke] >= tp) if side > 0 else (lo[:ke] <= tp))
            i_s = hs[0] if len(hs) else 10 ** 9; i_t = ht[0] if len(ht) else 10 ** 9
            px = sl if i_s <= i_t and i_s < 10 ** 9 else tp if i_t < 10 ** 9 else op[ke]
            res[lab] = side * (px - cc) / risk - cost / risk
        pre = np.flatnonzero(t < 480) + a
        asia = np.flatnonzero((t < 420)) + a
        h7 = np.flatnonzero((t >= 420) & (t < 480)) + a
        last60 = np.arange(max(cw[-1] - 59, a), cw[-1] + 1)
        k15 = dt + pd.Timedelta(hours=8); k15b = dt + pd.Timedelta(hours=7, minutes=45); k1h = dt + pd.Timedelta(hours=7)
        f = dict(date=dt, market=name, RL=res["RL"], RS=res["RS"], cdir=1 if cc > co else -1 if cc < co else (1 if dr.pc > dr.sma20 else -1),
                 c_ret=(cc - co) / atr, c_rng=rng / atr, c_loc=(cc - cl) / rng if rng > 0 else 0.5, c_body=abs(cc - co) / rng if rng > 0 else 0,
                 c_uw=(ch - max(co, cc)) / rng if rng > 0 else 0, c_lw=(min(co, cc) - cl) / rng if rng > 0 else 0,
                 c_vol=np.nansum(V[cw]), r_asia=(C[asia[-1]] - O[asia[0]]) / atr if len(asia) > 30 else np.nan,
                 r_h7=(C[h7[-1]] - O[h7[0]]) / atr if len(h7) > 30 else np.nan,
                 r_on=(cc - dr.pc) / atr, sw_hi=float(len(asia) > 30 and H[cw[0]:cw[-1] + 1].max() > H[asia].max()) if len(asia) > 30 else np.nan,
                 sw_lo=float(len(asia) > 30 and L[cw[0]:cw[-1] + 1].min() < L[asia].min()) if len(asia) > 30 else np.nan,
                 ema1_d=(cc - E[cw[-1]]) / atr, ema1_s=(E[cw[-1]] - E[max(cw[-1] - 15, a)]) / atr,
                 rv60=np.std(np.diff(C[last60])) * np.sqrt(60) / atr if len(last60) > 20 else np.nan,
                 d_ph=(cc - dr.ph) / atr, d_pl=(cc - dr.pl) / atr, d_pc=(cc - dr.pc) / atr,
                 pd_ret=(dr.pc - dr.po) / atr, pd_loc=(dr.pc - dr.pl) / (dr.ph - dr.pl) if dr.ph > dr.pl else 0.5,
                 r5=(dr.pc / dr.c5 - 1) if dr.c5 > 0 else np.nan, r20=(dr.pc / dr.c20 - 1) if dr.c20 > 0 else np.nan,
                 v_sma20=dr.pc / dr.sma20 - 1, v_sma50=dr.pc / dr.sma50 - 1 if dr.sma50 > 0 else np.nan, v_sma200=dr.pc / dr.sma200 - 1 if dr.sma200 > 0 else np.nan,
                 atr_p=atr / dr.pc, rsi_d=dr.rsi_d, dow=dt.weekday(), month=dt.month)
        if k15 in c15.index:
            i = c15.index.get_loc(k15); f.update(e15_d=(c15.iloc[i] - e15.iloc[i]) / atr, e15_s=(e15.iloc[i] - e15.iloc[max(i - 4, 0)]) / atr, rsi15=r15.iloc[i])
        if k15b in c15.index:
            i = c15.index.get_loc(k15b); cb, eb, e4 = c15.iloc[i], e15.iloc[i], e15.iloc[max(i - 4, 0)]
            f["aplus_bias"] = 1 if (cb > eb and eb > e4) else -1 if (cb < eb and eb < e4) else 0
        if k1h in c1h.index:
            i = c1h.index.get_loc(k1h); f.update(e1h_d=(c1h.iloc[i] - e1h.iloc[i]) / atr, rsi1h=r1h.iloc[i])
        f["x_ret0815"] = (cc - O[a]) / atr if a < cw[0] else np.nan
        rows.append(f)
    F = pd.DataFrame(rows)
    F["c_vol"] = F.c_vol / F.c_vol.rolling(20, min_periods=5).median().shift(1)
    return F


def daily_series():
    s = {}
    for f, col in (("DFII10.csv", "DFII10"), ("DGS10.csv", "DGS10"), ("DGS2.csv", "DGS2"), ("alt/DTWEXBGS.csv", "DTWEXBGS")):
        x = pd.read_csv(MAC + f, na_values=["."]).dropna(); x.index = pd.to_datetime(x.observation_date); s[col] = x[col].astype(float)
    for f in ("VIX", "VIX3M", "GVZ", "VXN", "OVX", "SKEW"):
        x = pd.read_csv(MAC + "cboe/%s.csv" % f); x.index = pd.to_datetime(x.date, format="%m/%d/%Y")
        s[f] = x[[c for c in x.columns if c in ("close", f.lower())][0]].astype(float)
    for f in ("6E", "CL", "HG", "ZN", "SI", "ES", "NQ", "YM", "GC"):
        x = pd.read_csv(DLY + "%s=F_yahoo_daily.csv" % f); x.index = pd.to_datetime(x.date); s["y_" + f] = x.close.astype(float)
    D = pd.DataFrame(s).sort_index()
    G = pd.DataFrame(index=D.index)
    G["ry"], G["ry_ch5"] = D.DFII10, D.DFII10.diff(5)
    G["y10"], G["y10_ch5"], G["y2"], G["s2s10"] = D.DGS10, D.DGS10.diff(5), D.DGS2, D.DGS10 - D.DGS2
    G["s2s10_ch5"] = G.s2s10.diff(5)
    G["usd_ch5"], G["usd_ch20"] = D.DTWEXBGS.pct_change(5, fill_method=None), D.DTWEXBGS.pct_change(20, fill_method=None)
    G["vix"], G["vix_term"], G["vix_ch5"] = D.VIX, D.VIX / D.VIX3M, D.VIX.diff(5)
    G["gvz"], G["vxn"], G["ovx"], G["skew"] = D.GVZ, D.VXN, D.OVX, D.SKEW
    for f in ("6E", "CL", "HG", "ZN", "SI", "ES", "NQ", "YM", "GC"):
        G["d1_" + f] = D["y_" + f].pct_change(fill_method=None); G["d5_" + f] = D["y_" + f].pct_change(5, fill_method=None)
    return G


def cot_series():
    out = {}
    for fpath in sorted(glob.glob(MAC + "cot/deacot20*/annual.txt")):
        c = pd.read_csv(fpath, usecols=[0, 2, 8, 9]); c.columns = ["name", "date", "nl", "ns"]
        for m, key in COT.items():
            sub = c[c.name.str.contains(key, case=False, regex=False)]
            if m == "MGC": sub = sub[~sub.name.str.contains("MICRO", case=False)]
            for r in sub.itertuples():
                out.setdefault(m, {})[pd.Timestamp(r.date)] = r.nl - r.ns
    res = {}
    for m, dct in out.items():
        s = pd.Series(dct).sort_index(); s = s[~s.index.duplicated()]
        z = (s - s.rolling(52, min_periods=20).mean()) / s.rolling(52, min_periods=20).std()
        x = pd.DataFrame({"cot_z": z, "cot_ch": s.diff() / s.rolling(52, min_periods=20).std()})
        x.index = x.index + pd.Timedelta(days=4)            # Tuesday data, released Friday: usable from the next Monday's session (+4 days is conservative)
        res[m] = x
    return res


def asof(frame, dates):
    left = pd.DataFrame({"date": pd.to_datetime(dates)}).reset_index()
    r = pd.merge_asof(left.sort_values("date"), frame.sort_index().rename_axis("k").reset_index(), left_on="date", right_on="k",
                      allow_exact_matches=False, direction="backward").sort_values("index")
    return r.drop(columns=["index", "date", "k"]).reset_index(drop=True)


def build():
    parts = [market_days(m) for m in MK]
    F = pd.concat(parts, ignore_index=True)
    X = F.pivot_table(index="date", columns="market", values="x_ret0815")
    for m in ("MGC", "MNQ", "MES", "SI"):
        F["xr_" + m] = F.date.map(X[m]) if m in X.columns else np.nan
    G = daily_series()
    F = pd.concat([F.reset_index(drop=True), asof(G, F.date)], axis=1)
    ev = set(pd.to_datetime(pd.read_csv(MAC + "event_calendar.csv").date))
    F["event"] = np.where(F.date >= "2022-01-01", F.date.isin(ev).astype(float), np.nan)
    cot = cot_series(); F["cot_z"] = np.nan; F["cot_ch"] = np.nan
    for m, x in cot.items():
        idx = F.market == m
        if idx.any():
            v = asof(x, F.loc[idx, "date"]); F.loc[idx, "cot_z"] = v.cot_z.to_numpy(); F.loc[idx, "cot_ch"] = v.cot_ch.to_numpy()
    for m in MK: F["is_" + m] = (F.market == m).astype(float)
    F["y"] = (F.RL > F.RS).astype(int); F["yr"] = F.date.dt.year
    return F


def platt_fit(p, y):
    lr = LogisticRegression(C=1e6); z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1); lr.fit(z, y); return lr


def platt_apply(lr, p):
    z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1); return lr.predict_proba(z)[:, 1]


def gbm(): return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.03, max_iter=300, min_samples_leaf=50, l2_regularization=1.0, random_state=7)


def gbm_fp(Xa, ya, Xb):
    """Amendment 1: fit on the columns that are not entirely missing in THIS fit's data, predict Xb on the same columns."""
    ok = ~np.all(np.isnan(Xa), axis=0)
    return gbm().fit(Xa[:, ok], ya).predict_proba(Xb[:, ok])[:, 1]


def fit_predict(kind, Xtr, ytr, yrtr, Xte):
    ok = ~np.all(np.isnan(Xtr), axis=0); Xtr, Xte = Xtr[:, ok], Xte[:, ok]
    if kind == "M1":
        last = yrtr.max()
        cal = platt_fit(gbm_fp(Xtr[yrtr < last], ytr[yrtr < last], Xtr[yrtr == last]), ytr[yrtr == last])
        return platt_apply(cal, gbm_fp(Xtr, ytr, Xte))
    if kind == "M2":
        med = np.nanmedian(Xtr, axis=0); mtr, mte = np.isnan(Xtr), np.isnan(Xte)
        A = np.where(mtr, med, Xtr); B = np.where(mte, med, Xte)
        A = np.hstack([A, mtr.astype(float)]); B = np.hstack([B, mte.astype(float)])
        sc = StandardScaler().fit(A); m = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(A), ytr)
        return m.predict_proba(sc.transform(B))[:, 1]
    if kind == "M3":
        m = xgb.XGBClassifier(max_depth=3, learning_rate=0.03, n_estimators=300, subsample=0.8, colsample_bytree=0.8, random_state=7, verbosity=0)
        return m.fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def main():
    if os.path.exists("ml_direction_features.parquet"):          # Amendment 1: reuse the features built by the first (crashed) run
        F = pd.read_parquet("ml_direction_features.parquet")
    else:
        F = build(); F.to_parquet("ml_direction_features.parquet")
    feats = [c for c in F.columns if c not in ("date", "market", "RL", "RS", "y", "yr", "cdir", "x_ret0815")]
    print("features %d, rows %d, markets %s, %s .. %s, long-win base rate %.3f" % (len(feats), len(F), dict(F.market.value_counts()), F.date.min().date(), F.date.max().date(), F.y.mean()))
    out = []
    for Y in range(2021, 2027):
        tr, te = F[F.yr < Y], F[F.yr == Y]
        if len(te) == 0: continue
        keep = [c for c in feats if tr[c].notna().any()]            # Amendment 1: drop columns that are all missing in this training window
        Xtr, Xte = tr[keep].to_numpy(float), te[keep].to_numpy(float)
        rec = te[["date", "market", "RL", "RS", "y", "yr", "cdir"]].copy()
        for k in ("M1", "M2", "M3"):
            rec[k] = fit_predict(k, Xtr, tr.y.to_numpy(), tr.yr.to_numpy(), Xte)
        rec["M4"] = np.nan
        for m in MK:
            a, b = tr.market == m, te.market == m
            if a.sum() > 300 and b.sum() > 0 and tr[a].yr.nunique() >= 2:
                rec.loc[b.to_numpy(), "M4"] = fit_predict("M1", Xtr[a.to_numpy()], tr.y[a].to_numpy(), tr.yr[a].to_numpy(), Xte[b.to_numpy()])
        rec["base_rate"] = tr.y.mean()
        out.append(rec); print("  fitted test year %d (train %d rows, test %d)" % (Y, len(tr), len(te)), flush=True)
    P = pd.concat(out, ignore_index=True); P.to_parquet("ml_direction_oos.parquet")
    report(P)
    # the most recent day in the data, as the daily output would look
    last = F[F.date == F.date.max()] if True else None
    full = gbm().fit(F[feats].to_numpy(float), F.y.to_numpy())
    print("\nexample output (model fitted on everything, last day in the data; uncalibrated):")
    for m in MK:
        r = F[F.market == m].iloc[-1:]
        p = full.predict_proba(r[feats].to_numpy(float))[0, 1]
        print("  %s %s: %.0f%% long / %.0f%% short" % (m, r.date.iloc[0].date(), 100 * p, 100 * (1 - p)))


def report(P):
    rng = np.random.default_rng(20261026)
    print("\nOUT-OF-SAMPLE 2021-2026 (each year predicted by a model fitted only on earlier years)")
    print("%-28s %6s %7s %18s %9s %8s %9s %s" % ("model", "n", "AUC", "AUC 95%", "logloss", "vs base", "mean R", "random-side P / years>0"))
    days = P.date.dt.normalize().to_numpy(); ud = np.unique(days); di = np.searchsorted(ud, days)
    for k in ("M1", "M2", "M3", "M4", "cdir", "long"):
        Q = P if k not in ("M4",) else P[P.M4.notna()]
        if k == "cdir": side = Q.cdir.to_numpy(); p = None
        elif k == "long": side = np.ones(len(Q)); p = None
        else: p = Q[k].to_numpy(); side = np.where(p >= 0.5, 1, -1)
        R = np.where(side > 0, Q.RL, Q.RS); M = np.where(side > 0, Q.RS, Q.RL)
        pv = float((np.where(rng.random((20000, len(R))) < 0.5, R, M).mean(axis=1) >= R.mean()).mean())
        yrs = pd.Series(R, index=Q.yr.to_numpy()).groupby(level=0).mean(); pos = int((yrs > 0).sum())
        if p is not None:
            auc = roc_auc_score(Q.y, p)
            qd = di[Q.index] if k == "M4" else di
            bs = []
            for _ in range(300):
                pick = rng.integers(0, len(ud), len(ud)); w = np.bincount(pick, minlength=len(ud))[qd]
                if w.sum() > 0 and len(np.unique(Q.y.to_numpy()[w > 0])) > 1: bs.append(roc_auc_score(Q.y, p, sample_weight=w))
            lo, hi = np.percentile(bs, [2.5, 97.5])
            ll = log_loss(Q.y, np.clip(p, 1e-4, 1 - 1e-4)); llb = log_loss(Q.y, np.clip(Q.base_rate, 1e-4, 1 - 1e-4))
            ok = k == "M1" and R.mean() > 0 and pv <= 0.01 and lo > 0.5 and pos >= 4
            print("%-28s %6d %7.4f %8.4f..%7.4f %9.4f %+8.4f %+9.4f  %.4f / %d of %d  %s" % (k + (" (PRIMARY)" if k == "M1" else ""), len(Q), auc, lo, hi, ll, llb - ll, R.mean(), pv, pos, len(yrs),
                  ("-> MODEL WORKS" if ok else "-> NOT SHOWN") if k == "M1" else ""))
        else:
            print("%-28s %6d %7s %18s %9s %8s %+9.4f  %.4f / %d of %d" % ("baseline " + ("candle colour (indicator)" if k == "cdir" else "always long"), len(Q), "", "", "", "", R.mean(), pv, pos, len(yrs)))
        print("      by year: " + " ".join("%d %+.3f" % (y, v) for y, v in yrs.items()))
        if k == "M1":
            mk = pd.Series(R, index=Q.market.to_numpy()).groupby(level=0).mean()
            print("      by market: " + " ".join("%s %+.3f" % (m, v) for m, v in mk.items()))
            print("      calibration (P(long) bucket: n, realized long-win rate):")
            for a, b in ((0, .40), (.40, .45), (.45, .50), (.50, .55), (.55, .60), (.60, 1.01)):
                s = (p >= a) & (p < b)
                if s.sum(): print("        %.2f-%.2f: n %4d  realized %.3f  mean R of the model side %+.3f" % (a, min(b, 1), s.sum(), Q.y.to_numpy()[s].mean(), R[s].mean()))


if __name__ == "__main__":
    main()
