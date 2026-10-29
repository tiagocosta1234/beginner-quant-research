"""BRK_TWOWAY: predict break vs bounce at the first touch of the trader's London / New York 30-min boxes from 22 confluences and trade
both ways (FOLLOW the predicted breaks, FADE the predicted bounces) with a symmetric 1-box bracket.
Pre-registration: forex/ea_research/PREREG_BRK_TWOWAY.md.  --dry-run: counts, coverage, truncation test (no labels / P&L).  --run."""
import argparse, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk_confirm import srv, boxes, LIS
from forex.ea_research.orbx import ct, CRYPTO
from forex.ea_research.analog import mclass

DATA = "forex/data_mt5/"
CACHE = "data/scratch/brk_twoway_events.parquet"
DEV_Y, VAL_Y = (2022, 2023, 2024), 2025
FEATS = ["box_atr", "box_spread", "delay", "app5", "app30", "day_move", "pdx", "beyond_pd", "asia", "tr5", "tr20", "gap",
         "box_in_pd", "range_so_far", "sp_touch", "volreg", "weekday", "cls", "yday", "touch_body"]
CATS = ["weekday", "cls", "beyond_pd", "yday"]
CLS = {"fx": 0, "index": 1, "metal": 2, "energy": 3}


def daily(D):
    day = D["t"] // 86400
    mh, ml, mc = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, D["mc"]
    g = pd.DataFrame({"d": day, "h": mh, "l": ml, "c": mc}).groupby("d")
    X = pd.DataFrame({"h": g.h.max(), "l": g.l.min(), "c": g.c.last()})
    X = X[pd.to_datetime(X.index * 86400, unit="s").weekday < 5]
    rng = X.h - X.l
    out = pd.DataFrame(index=X.index)
    out["atr20"] = rng.shift(1).rolling(20, min_periods=15).mean()
    out["atr100"] = rng.shift(1).rolling(100, min_periods=60).mean()
    out["ph"], out["pl"], out["pc"] = X.h.shift(1), X.l.shift(1), X.c.shift(1)
    out["ret5"] = X.c.shift(1) - X.c.shift(6)
    out["sma20"] = X.c.shift(1).rolling(20, min_periods=15).mean()
    return out


def market(sym, cut=None, with_r=True):
    D = load(sym, cut); t = D["t"]; out = []
    data_end = cut if cut is not None else int(t[-1]) + 60      # amendment 1: a session counts as finished if it ended before the data end
    D["mc"] = (D["bc"] + D["ac"]) / 2
    mh, ml, mc = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, D["mc"]
    DY = daily(D); cls = CLS.get(mclass(sym), 0)
    for dnum in DY.index:
        day = pd.Timestamp(int(dnum) * 86400, unit="s")
        if day < pd.Timestamp("2022-01-01"):
            continue
        dv = DY.loc[dnum]; atr = dv.atr20
        if not (atr > 0):
            continue
        a0, a1, d0 = np.searchsorted(t, [srv(day, 1, 0, LIS), srv(day, 7, 0, LIS), srv(day, 0, 0, LIS)])
        for box, (b0, b1, e_end, x_end) in boxes(day).items():
            i0, i1, iw, ix = np.searchsorted(t, [b0, b1, e_end, x_end])
            if i1 - i0 < 24 or x_end > data_end or iw - i1 < 30 or ix - i1 < 60 or i0 < 31:
                continue
            hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
            if W <= 0:
                continue
            up = np.flatnonzero(D["ah"][i1:iw] >= hi); dn = np.flatnonzero(D["bl"][i1:iw] <= lo)
            ku = i1 + up[0] if len(up) else None; kd = i1 + dn[0] if len(dn) else None
            if (ku is None and kd is None) or (ku is not None and ku == kd):
                continue
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd; f = k + 1
            if f >= ix - 1:
                continue
            level = hi if side > 0 else lo
            spb = np.median(D["sp"][i0:i1])
            asia_hi = mh[a0:a1].max() if a1 > a0 else np.nan; asia_lo = ml[a0:a1].min() if a1 > a0 else np.nan
            pdr = dv.ph - dv.pl
            row = dict(sym=sym, day=day, box=box, side=side, t_touch=int(t[k]), level=level, W=W,
                       box_atr=W / atr, box_spread=W / max(spb, 1e-12), delay=int((t[k] - b1) // 60),
                       app5=side * (mc[k] - mc[k - 5]) / W, app30=side * (mc[k] - mc[k - 30]) / W,
                       day_move=side * (mc[k] - mc[d0]) / atr if d0 < k else np.nan,
                       pdx=((dv.ph - hi) if side > 0 else (lo - dv.pl)) / atr,
                       asia=((hi - asia_hi) if side > 0 else (asia_lo - lo)) / atr,
                       tr5=side * dv.ret5 / atr, tr20=side * (dv.pc - dv.sma20) / atr, gap=side * ((hi + lo) / 2 - dv.pc) / atr,
                       box_in_pd=((hi + lo) / 2 - dv.pl) / pdr if pdr > 0 else np.nan,
                       range_so_far=(mh[d0:k + 1].max() - ml[d0:k + 1].min()) / atr if d0 <= k else np.nan,
                       sp_touch=D["sp"][k] / max(spb, 1e-12), volreg=dv.atr20 / dv.atr100 if dv.atr100 > 0 else np.nan,
                       weekday=day.weekday(), cls=cls, touch_body=side * (mc[k] - (D["bo"][k] + D["ao"][k]) / 2) / W)
            row["beyond_pd"] = int(row["pdx"] < 0)
            # trades (labels are always computed: yday needs them; the dry run never prints them)
            ef = D["ao"][f] if side > 0 else D["bo"][f]
            exf, _ = walk(D, side, f, ix, ef - side * W, ef + side * W)
            row["R_follow"] = (exf - ef) * side / W
            row["y"] = int((exf - ef) * side >= 0.999 * W)
            s2 = -side; ed = D["ao"][f] if s2 > 0 else D["bo"][f]
            exd, _ = walk(D, s2, f, ix, ed - s2 * W, ed + s2 * W)
            row["R_fade"] = (exd - ed) * s2 / W
            out.append(row)
    T = pd.DataFrame(out)
    if len(T):
        T = T.sort_values(["box", "day"])
        T["yday"] = T.groupby("box").y.shift(1).fillna(-1).astype(int)   # previous trading day's label of the same box (known: its session ended)
    return T


def syms():
    return sorted(s for s in (os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet")) if s not in CRYPTO)


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    with Pool(4) as p:
        T = pd.concat(p.map(market, syms()), ignore_index=True)
    T["year"] = T.day.dt.year
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


# ---------------- models ----------------
class Count:
    def fit(self, X, y):
        self.rules = {}
        for c in FEATS:
            x = X[c]
            if c in CATS:
                r = y.groupby(x).mean(); r = r[y.groupby(x).size() >= 200]
                if len(r) >= 2 and r.max() - r.min() >= 0.02:
                    self.rules[c] = ("cat", r.idxmax(), r.idxmin())
            else:
                q = x.quantile([1 / 3, 2 / 3]).to_numpy()
                g = np.digitize(x, q); r = y.groupby(g).mean()
                if len(r) == 3 and r.max() - r.min() >= 0.02:
                    self.rules[c] = ("num", q, r.idxmax(), r.idxmin())
        return self

    def predict(self, X):
        s = np.zeros(len(X))
        for c, rule in self.rules.items():
            if rule[0] == "cat":
                s += (X[c] == rule[1]).to_numpy() * 1.0 - (X[c] == rule[2]).to_numpy() * 1.0
            else:
                g = np.digitize(X[c], rule[1]); s += (g == rule[2]) * 1.0 - (g == rule[3]) * 1.0
        return s


class GBM:
    def fit(self, X, y):
        from sklearn.ensemble import HistGradientBoostingClassifier
        self.m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200,
                                                l2_regularization=1.0, random_state=0,
                                                categorical_features=[FEATS.index(c) for c in CATS])
        self.m.fit(X[FEATS].to_numpy(float), y.to_numpy()); return self

    def predict(self, X):
        return self.m.predict_proba(X[FEATS].to_numpy(float))[:, 1]


def prep(X):
    X = X.copy()
    for c in CATS:
        X[c] = X[c].fillna(-1).astype(int)
    X["yday"] = X["yday"].replace(-1, 2)                       # categorical codes must be >= 0
    X["beyond_pd"] = X["beyond_pd"].clip(lower=0)
    return X


def trade(X, pred, lo, hi):
    take_f, take_d = pred >= hi, pred <= lo
    R = np.where(take_f, X.R_follow, np.where(take_d, X.R_fade, np.nan))
    return X.assign(R=R, leg=np.where(take_f, "follow", np.where(take_d, "fade", "")), pred=pred)[~np.isnan(R)]


def crossfit(E, Model, y=None):
    """DEV out-of-fold trades + the out-of-fold predictions for all DEV events"""
    y = E.y if y is None else y
    trades, oof = [], pd.Series(np.nan, index=E.index)
    for hold in DEV_Y:
        tr, te = E[E.year.isin([v for v in DEV_Y if v != hold])], E[E.year == hold]
        m = Model().fit(tr, y.loc[tr.index]); ptr = m.predict(tr); pte = m.predict(te)
        lo, hi = np.quantile(ptr, 0.2), np.quantile(ptr, 0.8)
        oof.loc[te.index] = pte
        trades.append(trade(te, pte, lo, hi))
    return pd.concat(trades), oof


def per_period(E, Model):
    dev = E[E.year.isin(DEV_Y)]
    m = Model().fit(dev, dev.y); p = m.predict(dev); lo, hi = np.quantile(p, 0.2), np.quantile(p, 0.8)
    return m, lo, hi


def dry_run():
    S = syms(); print("markets", len(S))
    with Pool(4) as p:
        T = pd.concat(p.map(market, S), ignore_index=True)
    T["year"] = T.day.dt.year
    print(T.groupby(["box", "year"]).size().unstack().to_string())
    print("events by class:", T.groupby(["box", "cls"]).size().to_dict())
    print("\nfeature coverage (share non-missing) and median:")
    for c in FEATS:
        print(f"  {c:13s} {T[c].notna().mean():.3f}  median {T[c].median():+.3f}  p5 {T[c].quantile(.05):+.3f}  p95 {T[c].quantile(.95):+.3f}")
    rng = np.random.default_rng(4)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = market(sym); cut = int(rng.uniform(full.t_touch.quantile(.3), full.t_touch.quantile(.9)))
        tr = market(sym, cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s")
        cols = ["day", "box", "side", "t_touch", "level"] + [c for c in FEATS if c != "yday"]
        a = full[full.day < cd][cols].reset_index(drop=True); b = tr[tr.day < cd][cols].reset_index(drop=True)
        same = len(a) == len(b) and np.allclose(a.drop(columns=["day", "box"]).to_numpy(float), b.drop(columns=["day", "box"]).to_numpy(float), equal_nan=True)
        yd = full[full.day < cd - pd.Timedelta(days=1)].yday.reset_index(drop=True).equals(tr[tr.day < cd - pd.Timedelta(days=1)].yday.reset_index(drop=True))
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')}, events before the cut day {len(a)} vs {len(b)}, features identical {same}, yday identical {yd}")
    for _, r in T.sample(3, random_state=5).iterrows():
        print(f"  {r.sym} {r.day.date()} {r.box} side {r.side:+d} touch {pd.Timestamp(r.t_touch, unit='s'):%H:%M} server level {r.level:.5g} W {r.W:.5g}"
              f" box_atr {r.box_atr:.2f} delay {r.delay} app5 {r.app5:+.2f} pdx {r.pdx:+.2f} asia {r.asia:+.2f} tr5 {r.tr5:+.2f}")


def run():
    from sklearn.metrics import roc_auc_score
    from forex.ea_research.usdjpy_account_env import account, HZ
    E0 = prep(build())
    print(f"events {len(E0)}, markets {E0.sym.nunique()}, {E0.day.min().date()}..{E0.day.max().date()}")
    for box in ("LDN", "NY"):
        E = E0[E0.box == box]
        for nm, P in (("DEV", E.year.isin(DEV_Y)), ("VAL", E.year == VAL_Y)):
            x = E[P]; print(f"{box} {nm} base: follow-win rate {x.y.mean():.3f}, always-FOLLOW {x.R_follow.mean():+.3f} R, always-FADE {x.R_fade.mean():+.3f} R (n {len(x)})")
    print()
    rows = []
    for box in ("LDN", "NY"):
        E = E0[E0.box == box]
        for mname, Model in (("COUNT", Count), ("GBM", GBM)):
            tr, oof = crossfit(E[E.year.isin(DEV_Y)], Model)
            mu, t = ct(tr)
            yrs = tr.groupby(tr.year).R.mean()
            pl = []
            for seed in (1, 2, 3):
                g = np.random.default_rng(seed); dev = E[E.year.isin(DEV_Y)]
                yp = dev.groupby(["sym", "year"]).y.transform(lambda s: pd.Series(g.permutation(s.to_numpy()), index=s.index))
                trp, _ = crossfit(dev, Model, yp); pl.append(trp.R.mean())
            dev = E[E.year.isin(DEV_Y)]
            auc_d = roc_auc_score(dev.y, oof.loc[dev.index])
            ok = len(tr) >= 1000 and mu > 0 and t >= 2.5 and mu > max(pl) and (yrs > 0).sum() >= 2
            m, lo, hi = per_period(E, Model)
            v = E[E.year == VAL_Y]; pv = m.predict(v); tv = trade(v, pv, lo, hi); mv, tvt = ct(tv)
            auc_v = roc_auc_score(v.y, pv)
            okv = ok and mv > 0 and tvt >= 1.65
            fl, fd = tr[tr.leg == "follow"], tr[tr.leg == "fade"]
            line = (f"{box:3s}-{mname:5s} | DEV n {len(tr)} net {mu:+.3f} t {t:+.2f} | follow leg n {len(fl)} win {(fl.R > 0).mean():.3f} {fl.R.mean():+.3f}"
                    f" | fade leg n {len(fd)} win {(fd.R > 0).mean():.3f} {fd.R.mean():+.3f} | placebo {'/'.join(f'{x:+.3f}' for x in pl)}"
                    f" | yrs {'/'.join(f'{x:+.2f}' for x in yrs)} | AUC {auc_d:.3f} -> {'PASS' if ok else 'FAIL'}"
                    f" | VAL n {len(tv)} {mv:+.3f} t {tvt:+.2f} AUC {auc_v:.3f}")
            if okv:
                h = E[E.year == 2026]; th = trade(h, m.predict(h), lo, hi); mh_, thh = ct(th)
                line += f" | HOLD n {len(th)} {mh_:+.3f} t {thh:+.2f} -> {'PASS' if mh_ > 0 and thh >= 1.65 else 'FAIL'}"
            else:
                line += " | HOLD sealed"
            print(line)
            # deciles of the out-of-fold prediction (DEV) and of VAL: follow-win rate
            dq = pd.qcut(oof.loc[dev.index].rank(method="first"), 10, labels=False)
            vq = pd.qcut(pd.Series(pv, index=v.index).rank(method="first"), 10, labels=False)
            rows.append((box, mname, dev.y.groupby(dq).mean().round(3).tolist(), v.y.groupby(vq).mean().round(3).tolist()))
            # account view (standing rule): NSDQ + XAUUSD, $250, DEV out-of-fold + VAL trades (2026 sealed)
            A = pd.concat([tr, tv]); A = A[A.sym.isin(["NSDQ", "XAUUSD"])]
            days = pd.bdate_range("2022-01-03", "2025-12-31"); H = max(HZ.values()); rng = np.random.default_rng(1618)
            R = A.groupby("day").R.sum().reindex(days); trd = R.notna().to_numpy(); r = R.fillna(0).to_numpy()
            s = rng.integers(0, len(r) - 5, size=(20000, H // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :H]
            st, ev, _ = account(r[bi], trd[bi], 250)
            print(f"     account NSDQ+XAU $250 ({len(A)} trades, {A.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st==1)&(ev<h_)):.1f}% / breach {100*np.mean((st==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    print("\nfollow-win rate by prediction decile (lowest -> highest):")
    for box, mname, dq, vq in rows:
        print(f"  {box}-{mname:5s} DEV oof {dq}\n  {'':10s}VAL     {vq}")
    try:
        from sklearn.inspection import permutation_importance
        for box in ("LDN", "NY"):
            E = E0[(E0.box == box) & E0.year.isin(DEV_Y)]; m = GBM().fit(E, E.y)
            pi = permutation_importance(m.m, E[FEATS].to_numpy(float), E.y.to_numpy(), n_repeats=3, random_state=0, scoring="roc_auc")
            imp = sorted(zip(FEATS, pi.importances_mean), key=lambda z: -z[1])[:8]
            print(f"\nGBM {box} permutation importance (AUC drop, DEV in-sample): " + ", ".join(f"{a} {b:+.4f}" for a, b in imp))
    except Exception as e:
        print("importance failed:", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
