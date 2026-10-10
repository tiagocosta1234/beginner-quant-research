"""Family K (confluence panel), exactly as registered in PREREG_CONFLUENCE_PANEL.md (the trader 2026-10-10: "(original wording omitted)").
   python -m mt5broker.ea_research.confluence_panel --dry-run | --trials | --holdout
29 MT5, daily bars from 2020, six trials: C1a/C1b hand-built confluence count (no fitting), C2a/C2b ridge, C3a/C3b depth-3 boosting, walk-forward by year.
--dry-run prints counts, the causality (truncation) test and a hand check, NO P&L and no label-vs-signal statistics."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
LEDGER = HERE / "LEDGER.csv"
OUT_JSON = HERE / "CONFLUENCE_PANEL_STATE.json"
START = pd.Timestamp("2020-01-01")
FX_MAJ = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
FX_CRS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "CHFJPY", "EURGBP", "EURJPY", "GBPJPY"]
IDX = ["US100.cash", "US500.cash", "US30.cash", "GER40.cash", "JP225.cash", "AUS200.cash"]
MET = ["XAUUSD", "XAGUSD"]
OIL = ["UKOIL.cash", "USOIL.cash"]
CRY = ["BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"]
MARKETS = FX_MAJ + FX_CRS + IDX + MET + OIL + CRY
CLS = {**{m: 0 for m in FX_MAJ + FX_CRS}, **{m: 1 for m in IDX}, **{m: 2 for m in MET}, **{m: 3 for m in OIL}, **{m: 4 for m in CRY}}
CLS_NAME = {0: "FX", 1: "index", 2: "metal", 3: "oil", 4: "crypto"}
COST_BP = {**{m: 0.6 for m in FX_MAJ}, **{m: 1.2 for m in FX_CRS}, **{m: 2.0 for m in IDX}, "XAUUSD": 1.2, "XAGUSD": 3.0, **{m: 4.0 for m in OIL}, **{m: 8.0 for m in CRY}}
USD_Q = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]   # USD is the quote: USD proxy return = -logret
USD_B = ["USDJPY", "USDCAD", "USDCHF"]             # USD is the base: +logret
G_TYPE = {**{m: "risk" for m in IDX + CRY}, **{m: "rate" for m in MET}, **{m: "usdq" for m in USD_Q}, **{m: "usdb" for m in USD_B}}
PERIODS = {"PRE": ("2021-01-01", "2022-12-31"), "DEV": ("2023-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2023-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30"),
           "Y2023": ("2023-01-01", "2023-12-31"), "Y2024": ("2024-01-01", "2024-12-31"), "Y2025": ("2025-01-01", "2025-12-31")}
TARGET_VOL = 0.0020
FEATS = ["r1", "r3", "r5", "r10", "r20", "r60", "r120", "dsma20", "dsma50", "dsma200", "cross", "ibs", "rng20", "rng55", "rsi2", "rsi14", "atrr", "atrp", "nr7", "rngatr", "gap", "streak",
         "body", "upw", "lw", "dow", "month", "tom", "cls", "usd5", "usd20", "usd60", "risk5", "risk20", "riskvol", "gold20", "ry_lvl", "ry_chg5", "ry_chg20", "xs20", "xs60"]
CORE = ["r120", "dsma200", "cross", "atrp", "sig"]


# ---------------------------------------------------------------- data
def load_market(m: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_D1.parquet", columns=["time", "open", "high", "low", "close"])
    d["date"] = pd.to_datetime(d.time, unit="s").dt.normalize()
    d = d[(d.date >= START) & (d.date.dt.dayofweek < 5)].drop_duplicates("date", keep="last").sort_values("date")
    d = d.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"}).set_index("date")[["o", "h", "l", "c"]].astype(float)
    bad = ~((d.l <= np.minimum(d.o, d.c) * 1.0000001) & (d.h >= np.maximum(d.o, d.c) * 0.9999999) & (d.h / d.l < 3) & (d.l > 0))    # data integrity: keep only bars AFTER the last inconsistent one (only LTCUSD 2020 is affected)
    return d[d.index > bad[bad].index.max()] if bad.any() else d


def _rsi(c: pd.Series, n: int) -> pd.Series:
    de = c.diff(); up = de.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean(); dn = (-de.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    r = 100 - 100 / (1 + up / dn); r[(dn == 0) & up.notna()] = 100.0
    return r


def feats(d: pd.DataFrame) -> pd.DataFrame:
    """Per-market features. Every value at date t uses bars up to and including t only (checked by truncation in --dry-run)."""
    c, o, h, l = d.c, d.o, d.h, d.l
    lr = np.log(c).diff(); sig = np.sqrt((lr ** 2).ewm(alpha=0.06, min_periods=40, adjust=False).mean())
    f = pd.DataFrame(index=d.index); f["sig"] = sig
    for L in (1, 3, 5, 10, 20, 60, 120): f[f"r{L}"] = np.log(c / c.shift(L)) / (sig * np.sqrt(L))
    for L in (20, 50, 200): f[f"dsma{L}"] = (c / c.rolling(L).mean() - 1) / (sig * np.sqrt(L))
    f["cross"] = (c.rolling(50).mean() / c.rolling(200).mean() - 1) / (sig * np.sqrt(100))
    rg = h - l; f["ibs"] = ((c - l) / rg).where(rg > 0, 0.5)
    for L in (20, 55):
        lo, hi = l.rolling(L).min(), h.rolling(L).max(); f[f"rng{L}"] = ((c - lo) / (hi - lo)).where(hi > lo, 0.5).where(lo.notna())
    f["rsi2"] = _rsi(c, 2); f["rsi14"] = _rsi(c, 14)
    pc = c.shift(1); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1, skipna=False)
    a5, a14, a50 = tr.rolling(5).mean(), tr.rolling(14).mean(), tr.rolling(50).mean()
    f["atrr"] = a5 / a50; f["atrp"] = (a14 / c).rolling(252, min_periods=120).rank(pct=True)
    mn7 = rg.rolling(7).min(); f["nr7"] = (rg <= mn7).astype(float).where(mn7.notna()); f["rngatr"] = rg / a14; f["gap"] = (o - pc) / (pc * sig)
    s = np.sign(c.diff()); grp = (s != s.shift()).cumsum(); f["streak"] = ((s.groupby(grp).cumcount() + 1) * s).clip(-6, 6).where(c.diff().notna())
    r_ = rg.where(rg > 0)
    f["body"] = ((c - o) / r_).fillna(0.0); f["upw"] = ((h - pd.concat([o, c], axis=1).max(axis=1)) / r_).fillna(0.0); f["lw"] = ((pd.concat([o, c], axis=1).min(axis=1) - l) / r_).fillna(0.0)
    f["dow"] = d.index.dayofweek.astype(float); f["month"] = d.index.month.astype(float); f["tom"] = ((d.index.day >= 28) | (d.index.day <= 3)).astype(float)
    return f


def context(frames: dict[str, pd.DataFrame], cal: pd.DatetimeIndex) -> pd.DataFrame:
    def lrr(m): return np.log(frames[m].c).diff().reindex(cal).fillna(0.0)
    usd = (sum(-lrr(m) for m in USD_Q) + sum(lrr(m) for m in USD_B)) / 7.0                 # equal weight over the 7 USD pairs
    ctx = pd.DataFrame(index=cal)
    for L in (5, 20, 60): ctx[f"usd{L}"] = usd.rolling(L).sum()
    sp = lrr("US500.cash")
    for L in (5, 20): ctx[f"risk{L}"] = sp.rolling(L).sum()
    sg = np.sqrt((sp ** 2).ewm(alpha=0.06, min_periods=40, adjust=False).mean()); ctx["riskvol"] = sg.rolling(252, min_periods=120).rank(pct=True)
    ctx["gold20"] = lrr("XAUUSD").rolling(20).sum()
    ry = pd.read_csv("D:/finance/data_macro/DFII10.csv"); ry["observation_date"] = pd.to_datetime(ry.observation_date); ry = pd.to_numeric(ry.set_index("observation_date").DFII10, errors="coerce").dropna()
    ryc = ry.reindex(ry.index.union(cal)).ffill().reindex(cal).shift(1)       # value known at the previous weekday's close
    ctx["ry_lvl"] = ryc; ctx["ry_chg5"] = ryc - ryc.shift(5); ctx["ry_chg20"] = ryc - ryc.shift(20)
    return ctx


def build_panel(hmax: int = 5) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    frames = {m: load_market(m) for m in MARKETS}
    cal = pd.DatetimeIndex(sorted(set().union(*[set(f.index) for f in frames.values()]))); ctx = context(frames, cal); parts = []
    for m, d in frames.items():
        f = feats(d); f["mkt"] = m; f["cls"] = float(CLS[m]); c = d.c; lc = np.log(c)
        f["nr"] = c.shift(-1) / c - 1.0
        for h in (1, 5):
            f[f"y{h}"] = (lc.shift(-h) - lc) / (f.sig * np.sqrt(h)); f[f"end{h}"] = pd.Series(d.index, index=d.index).shift(-h)
        f["end1"] = pd.Series(d.index, index=d.index).shift(-1)
        f = f.join(ctx, how="left"); parts.append(f.reset_index(names="date"))
    P = pd.concat(parts, ignore_index=True)
    P["xs20"] = P.groupby("date").r20.rank(pct=True); P["xs60"] = P.groupby("date").r60.rank(pct=True)
    return P.sort_values(["date", "mkt"]).reset_index(drop=True), frames


# ---------------------------------------------------------------- C1 confluence count
def c1_components(P: pd.DataFrame) -> pd.DataFrame:
    A = np.sign(P.r120); B = np.sign(P.cross)
    C = np.where(P.r5 <= -1.0, 1.0, np.where(P.r5 >= 1.0, -1.0, 0.0)); D = np.where(P.rsi2 < 10, 1.0, np.where(P.rsi2 > 90, -1.0, 0.0)); E = np.where(P.ibs < 0.2, 1.0, np.where(P.ibs > 0.8, -1.0, 0.0))
    g = P.mkt.map(G_TYPE).fillna("none")
    G = np.select([g == "risk", g == "rate", g == "usdq", g == "usdb"], [np.sign(P.risk20), -np.sign(P.ry_chg20), -np.sign(P.usd20), np.sign(P.usd20)], 0.0)
    X = pd.DataFrame(dict(A=A, B=B, C=C, D=D, E=E, G=G), index=P.index).fillna(0.0)
    X["score"] = X.sum(axis=1); return X


def c1_positions(P: pd.DataFrame, hold5: bool) -> pd.Series:
    sc = c1_components(P).score; sg = np.where(sc.abs() >= 3, np.sign(sc), 0.0); s = pd.Series(sg, index=P.index)
    if not hold5: return s
    s = s.replace(0.0, np.nan); out = s.groupby(P.mkt).transform(lambda x: x.ffill(limit=4)); return out.fillna(0.0)


# ---------------------------------------------------------------- models
def _mats(df: pd.DataFrame, kind: str, ref=None):
    if kind == "gbm": return df[FEATS].to_numpy("float64")
    num = [c for c in FEATS if c not in ("dow", "month", "cls")]; X = df[num].to_numpy("float64")
    mu, sd = ref if ref is not None else (np.nanmean(X, 0), np.nanstd(X, 0) + 1e-9); Z = np.nan_to_num((X - mu) / sd, nan=0.0)
    oh = np.concatenate([(df.dow.to_numpy()[:, None] == np.arange(5)).astype(float), (df.month.to_numpy()[:, None] == np.arange(1, 13)).astype(float), (df.cls.to_numpy()[:, None] == np.arange(5)).astype(float)], 1)
    return np.concatenate([Z, oh], 1), (mu, sd)


def fit_model(kind: str, tr: pd.DataFrame, ycol: str, shuffle_rng=None):
    y = tr[ycol].clip(-4, 4).to_numpy("float64")
    if shuffle_rng is not None:                                         # labels permuted within date (control)
        y = tr.assign(_y=y).groupby("date")._y.transform(lambda s: shuffle_rng.permutation(s.to_numpy())).to_numpy()
    if kind == "gbm":
        from sklearn.ensemble import HistGradientBoostingRegressor
        m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=200, min_samples_leaf=300, l2_regularization=10.0, random_state=0).fit(_mats(tr, "gbm"), y); return ("gbm", m, None)
    from sklearn.linear_model import Ridge
    X, ref = _mats(tr, "ridge"); m = Ridge(alpha=1000.0).fit(X, y); return ("ridge", m, ref)


def predict(mod, df: pd.DataFrame) -> np.ndarray:
    kind, m, ref = mod
    return m.predict(_mats(df, "gbm")) if kind == "gbm" else m.predict(_mats(df, "ridge", ref)[0])


def walk(P: pd.DataFrame, kind: str, h: int, years, shuffle_seed=None) -> pd.DataFrame:
    yc, ec = f"y{h}", f"end{h}"; ok = P[CORE].notna().all(axis=1); rows = []; rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    for Y in years:
        t0, t1, ta = pd.Timestamp(f"{Y}-01-01"), pd.Timestamp(f"{Y}-12-31"), pd.Timestamp(f"{Y - 1}-01-01")
        trB = P[ok & P[yc].notna() & (P[ec] < t0)]; trA = P[ok & P[yc].notna() & (P[ec] < ta)]
        mB = fit_model(kind, trB, yc, rng); mA = fit_model(kind, trA, yc, rng)
        pa = predict(mA, P[ok & (P.date >= ta) & (P.date < t0)]); s = max(float(np.std(pa)), 1e-9)
        te = P[ok & (P.date >= t0) & (P.date <= t1) & P.nr.notna()]; pr = predict(mB, te)
        rows.append(te[["date", "mkt", "sig", "nr", yc]].assign(pred=pr, pos=np.clip(pr / (2 * s), -1, 1), scale=s).rename(columns={yc: "y"}))
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- portfolio and statistics
def mats(R: pd.DataFrame):
    """R: columns date, mkt, pos, sig, nr -> matrices over the sorted dates (T x M)."""
    dates = pd.DatetimeIndex(sorted(R.date.unique())); mk = [m for m in MARKETS if m in set(R.mkt)]
    pv = lambda col: R.pivot(index="date", columns="mkt", values=col).reindex(index=dates, columns=mk)
    pos = pv("pos").fillna(0.0).to_numpy(); sig = pv("sig").to_numpy(); nr = pv("nr").fillna(0.0).to_numpy()
    W = np.where(np.isfinite(sig) & (sig > 0), pos * TARGET_VOL / np.where(sig > 0, sig, 1.0), 0.0)
    cost = np.array([COST_BP[m] * 1e-4 for m in mk]); return dates, mk, W, nr, cost


def daily_pnl(W, NR, cost, shift=None):
    if shift is not None: W = np.column_stack([np.roll(W[:, j], shift[j]) for j in range(W.shape[1])])
    dW = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, W.shape[1])))); gross = (W * NR).sum(1); net = gross - (dW * cost).sum(1); return gross, net


def stat(r: pd.Series) -> dict:
    n = len(r)
    if n < 20 or r.std(ddof=1) == 0: return dict(n=n, sharpe=float("nan"), t=float("nan"), bp=float("nan"), pf=float("nan"), win=float("nan"), dd=float("nan"))
    sd = r.std(ddof=1); w, l_ = r[r > 0].sum(), -r[r < 0].sum(); eq = r.cumsum()
    return dict(n=n, sharpe=float(r.mean() / sd * np.sqrt(252)), t=float(r.mean() / (sd / np.sqrt(n))), bp=float(r.mean() * 1e4), pf=float(w / l_) if l_ > 0 else float("inf"), win=float((r > 0).mean()), dd=float((eq.cummax() - eq).max()))


def portfolio(R: pd.DataFrame, subset=None):
    if subset is not None: R = R[R.mkt.isin(subset)]
    dates, mk, W, NR, cost = mats(R); g, n = daily_pnl(W, NR, cost); return pd.Series(g, dates), pd.Series(n, dates), (dates, mk, W, NR, cost)


def sl(s: pd.Series, per: str) -> pd.Series:
    a, b = PERIODS[per]; return s[(s.index >= a) & (s.index <= b)]


def perm_p(dates, W, NR, cost, per: str, n_perm=1000, seed=7) -> tuple[float, float]:
    a, b = PERIODS[per]; ix = (dates >= a) & (dates <= b); W_, N_ = W[ix], NR[ix]; T = len(W_)
    def sh(x): return np.nan if x.std(ddof=1) == 0 else x.mean() / x.std(ddof=1) * np.sqrt(252)
    obs = sh(daily_pnl(W_, N_, cost)[1]); rng = np.random.default_rng(seed); cnt = 0; null = []
    for _ in range(n_perm):
        sh_ = rng.integers(20, T - 20, W_.shape[1]); v = sh(daily_pnl(W_, N_, cost, sh_)[1]); null.append(v); cnt += v >= obs
    return (1 + cnt) / (1 + n_perm), float(np.mean(null))


def daily_ic(R: pd.DataFrame) -> tuple[float, float, int]:
    ic = []
    for _, g in R.groupby("date"):
        if len(g) >= 10: ic.append(g.pred.rank().corr(g.y.rank()))
    ic = pd.Series(ic).dropna(); return float(ic.mean()), float(ic.mean() / (ic.std(ddof=1) / np.sqrt(len(ic)))), len(ic)


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},confluence_panel,{trial},{period},{s['n']},,,{s['bp']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def fmt(tag, s, g=None):
    return f"{tag:14s} days {s['n']:4d} | net Sharpe {s['sharpe']:+5.2f} | daily t {s['t']:+5.2f} | {s['bp']:+6.2f} bp/day | PF {s['pf']:4.2f} | win {100*s['win']:4.1f}% | maxDD {100*s['dd']:5.1f}%" + (f" | gross Sharpe {g:+5.2f}" if g is not None else "")


# ---------------------------------------------------------------- dry run
def dry_run():
    P, frames = build_panel(); pd.set_option("display.width", 200)
    print("== panel ==", P.shape, "dates", P.date.min().date(), "->", P.date.max().date(), "| markets", P.mkt.nunique(), "| features", len(FEATS))
    first = {m: frames[m].index[0].date() for m in MARKETS}; print("first bar per market (those after 2020-01-02):", {m: str(d) for m, d in first.items() if d > dt.date(2020, 1, 3)})
    ok = P[CORE].notna().all(axis=1)
    print("rows", len(P), "| with all core features", int(ok.sum()), "| first usable date", P[ok].date.min().date())
    for per, (a, b) in PERIODS.items(): x = P[ok & (P.date >= a) & (P.date <= b) & P.nr.notna()]; print(f"  {per:6s} market-days {len(x):6d}  dates {x.date.nunique():4d}  markets/day {len(x)/max(1,x.date.nunique()):5.1f}")
    print("NaN share per feature (usable rows):", {c: round(float(P.loc[ok, c].isna().mean()), 3) for c in FEATS if P.loc[ok, c].isna().mean() > 0.001})
    # data sanity: biggest daily moves and zero-range bars
    for m in MARKETS:
        d = frames[m]; lr = np.log(d.c).diff().abs(); bad = int(((d.h < d.l) | (d.c > d.h * 1.0000001) | (d.c < d.l * 0.9999999) | (d.c <= 0)).sum())
        if lr.max() > 0.2 or bad: print(f"  CHECK {m}: max |daily log move| {lr.max():.3f} on {lr.idxmax().date()} | inconsistent bars {bad}")
    # causality: recompute every feature on truncated data and compare with the full-data value at that row
    rng = np.random.default_rng(1); bad = 0; chk = 0
    for _ in range(40):
        m = MARKETS[rng.integers(len(MARKETS))]; d = frames[m]; k = int(rng.integers(300, len(d) - 10)); ft = feats(d.iloc[:k + 1]).iloc[-1]; ff = feats(d).iloc[k]
        for c in ft.index:
            a, b = ft[c], ff[c]; chk += 1
            if not ((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9 * max(1, abs(b))): bad += 1; print("   NON-CAUSAL", m, d.index[k].date(), c, a, b)
    print(f"causality test (truncated vs full data, 40 random rows x {len(ft)} features): {chk} comparisons, {bad} mismatches")
    # context features use only data up to t: shifting the future must not change them
    cal = pd.DatetimeIndex(sorted(set().union(*[set(f.index) for f in frames.values()]))); cx = context(frames, cal); cut = cal[800]
    fr2 = {m: f[f.index <= cut] for m, f in frames.items()}; cx2 = context(fr2, cal[cal <= cut]); dif = (cx.loc[cx2.index] - cx2).abs().max().max()
    print(f"context truncation test: max difference {dif:.2e} (must be 0 up to rounding; 0 means no future data in the context features)")
    # hand check of three numbers on gold
    d = frames["XAUUSD"]; f = feats(d); t = d.index[-3]; c = d.c
    r5 = np.log(c.loc[t] / c.iloc[c.index.get_loc(t) - 5]); lr = np.log(c).diff(); s2 = (lr ** 2).ewm(alpha=0.06, min_periods=40, adjust=False).mean().loc[t]
    print(f"hand check XAUUSD {t.date()}: r5 table {f.loc[t,'r5']:+.4f} vs manual {r5 / (np.sqrt(s2) * np.sqrt(5)):+.4f} | ibs table {f.loc[t,'ibs']:.4f} vs manual {(d.c.loc[t]-d.l.loc[t])/(d.h.loc[t]-d.l.loc[t]):.4f} | rsi2 {f.loc[t,'rsi2']:.2f}")
    X = c1_components(P[ok]); print("C1 components, share non-zero:", {k: round(float((X[k] != 0).mean()), 3) for k in "ABCDEG"}); print("C1 score distribution (usable rows):", X.score.value_counts().sort_index().to_dict())
    for hold5 in (False, True):
        pp = c1_positions(P, hold5); z = pp[ok]; print(f"C1{'b' if hold5 else 'a'} position-days: long {int((z>0).sum())}, short {int((z<0).sum())}, flat {int((z==0).sum())} ({100*(z!=0).mean():.1f}% of market-days)")
    tr = P[ok & P.y1.notna() & (P.end1 < pd.Timestamp("2023-01-01"))]; print(f"first walk-forward fit (test 2023): {len(tr)} training rows, {tr.date.nunique()} dates; scale-model fit (test 2022): {int((ok & P.y1.notna() & (P.end1 < pd.Timestamp('2022-01-01'))).sum())} rows")
    print("matrix shapes: ridge", _mats(tr.head(50), "ridge")[0].shape, "gbm", _mats(tr.head(50), "gbm").shape, "| no P&L, no signal-vs-label statistic computed")


# ---------------------------------------------------------------- trials
def accept(poolst, years, perm, ic, pre=None) -> dict:
    a1 = poolst["t"] >= 2.4 and poolst["sharpe"] >= 1.0; a2 = all(years[y]["sharpe"] > 0 for y in years) and years["Y2025"]["sharpe"] >= 0.3 and (pre is None or pre["sharpe"] > 0); a3 = perm <= 0.01; a4 = True if ic is None else (ic[0] > 0 and ic[1] >= 2)
    return dict(a1=bool(a1), a2=bool(a2), a3=bool(a3), a4=bool(a4), passed=bool(a1 and a2 and a3 and a4))


def run_trials():
    P, frames = build_panel(); ok = P[CORE].notna().all(axis=1); results = {}; store = {}
    base = P[ok & P.nr.notna()]
    # ---- C1
    X = c1_components(base); print("\n== C1 dose-response (diagnostic, not a trial): mean y by score; usable rows ==")
    for per in ("PRE", "DEV", "VAL"):
        a, b = PERIODS[per]; m = (base.date >= a) & (base.date <= b); dd = pd.DataFrame(dict(score=X.score[m], y1=base.y1[m], y5=base.y5[m]))
        g = dd.groupby("score").agg(n=("y1", "size"), y1=("y1", "mean"), y5=("y5", "mean")); print(per); print(g.round(3).T.to_string())
    for tr, hold5 in (("C1a", False), ("C1b", True)):
        pos = c1_positions(P, hold5)[ok & P.nr.notna()]; R = base[["date", "mkt", "sig", "nr", "y1"]].assign(pos=pos.to_numpy(), pred=pos.to_numpy(), y=base.y1.to_numpy())
        results[tr] = report(tr, R, None, pre=True, store=store)
    # ---- C2 / C3
    for kind, name in (("ridge", "C2"), ("gbm", "C3")):
        for h, sfx in ((1, "a"), (5, "b")):
            tr = f"{name}{sfx}"; R = walk(P, kind, h, (2023, 2024, 2025)); results[tr] = report(tr, R, (R.pred, R.y), pre=False, store=store)
    # ---- controls (not trials)
    print("\n== controls (not trials) ==")
    R = walk(P, "gbm", 1, (2023, 2024, 2025), shuffle_seed=11); g, n, _ = portfolio(R); ic = daily_ic(R)
    print(fmt("C3 shuffled", stat(sl(n, "POOL")), stat_g(g)), f"| IC {ic[0]:+.4f} (t {ic[1]:+.2f})")
    drift = base.assign(pos=np.where(base.cls == 0, 0.0, 1.0))[["date", "mkt", "sig", "nr", "pos"]]; g, n, _ = portfolio(drift)
    print(fmt("long-only drift", stat(sl(n, "POOL")), stat_g(g)), "(+1 on every non-FX market: the beta/drift of 2023-25, a yardstick for the P&L above)")
    # ---- permutation importance for C3a on 2025
    ok_ = ok & P.y1.notna(); trB = P[ok_ & (P.end1 < pd.Timestamp("2025-01-01"))]; mod = fit_model("gbm", trB, "y1"); te = P[ok_ & (P.date >= "2025-01-01") & (P.date <= "2025-12-31")]
    def mse(df): p = predict(mod, df); return float(np.mean((np.clip(df.y1, -4, 4) - p) ** 2))
    b0 = mse(te); rng = np.random.default_rng(3); imp = {}
    for c in FEATS:
        tt = te.copy(); tt[c] = rng.permutation(tt[c].to_numpy()); imp[c] = mse(tt) - b0
    print("\nC3a permutation importance 2025 (increase in MSE when the feature is shuffled; top 12):", {k: round(v, 5) for k, v in sorted(imp.items(), key=lambda kv: -kv[1])[:12]})
    OUT_JSON.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("\n== acceptance 1-4 ==", {k: v["acc"] for k, v in results.items()})
    return results


def stat_g(g: pd.Series) -> float: return stat(sl(g, "POOL"))["sharpe"]


def report(tr, R, icpair, pre, store):
    g, n, (dates, mk, W, NR, cost) = portfolio(R); out = {}; years = {}
    print(f"\n=== {tr}: {len(R)} market-days; markets {R.mkt.nunique()}; positions non-zero {100*(R.pos!=0).mean():.1f}% ; long share of non-zero {100*(R.pos>0).sum()/max(1,(R.pos!=0).sum()):.0f}% ===", flush=True)
    for per in (("PRE",) if pre else ()) + ("DEV", "VAL", "POOL", "Y2023", "Y2024", "Y2025"):
        st = stat(sl(n, per)); sg = stat(sl(g, per))["sharpe"]; print(fmt(f"{tr} {per}", st, sg), flush=True)
        if per in ("Y2023", "Y2024", "Y2025"): years[per] = st
        out[per] = st;
        if per in ("PRE", "DEV", "VAL", "POOL"): ledger(tr, per, st, f"net Sharpe {st['sharpe']:+.2f}; gross Sharpe {sg:+.2f}")
    p, nm = perm_p(dates, W, NR, cost, "POOL"); ic = daily_ic(R) if icpair is not None else None
    print(f"   permutation p (1000 circular shifts, POOL) {p:.4f}, null mean Sharpe {nm:+.2f}" + (f" | mean daily rank IC {ic[0]:+.4f} (t {ic[1]:+.2f}, {ic[2]} days)" if ic else ""))
    cl = {}
    for ci, nmx in CLS_NAME.items():
        sub = [m for m in MARKETS if CLS[m] == ci and m in set(R.mkt)]; _, nn, _ = portfolio(R, sub); cl[nmx] = stat(sl(nn, "POOL"))["sharpe"]
    print("   POOL net Sharpe by class:", {k: round(v, 2) for k, v in cl.items()})
    acc = accept(out["POOL"], years, p, ic, out.get("PRE")); print("   acceptance a1 (t>=2.4 & Sharpe>=1.0):", acc["a1"], "| a2 (every year>0, 2025>=0.3):", acc["a2"], "| a3 (perm p<=0.01):", acc["a3"], "| a4 (IC>0, t>=2):", acc["a4"], "=> PASSED" if acc["passed"] else "=> closed")
    ledger(tr, "PERM", dict(n=len(n), bp=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan")), f"perm p {p:.4f}; IC {None if ic is None else round(ic[0], 4)}; passed {acc['passed']}")
    store[tr] = (R, n); return dict(acc=acc, pool=out["POOL"], p=p, ic=ic)


def run_holdout():
    if not OUT_JSON.exists(): print("run --trials first"); return
    res = json.loads(OUT_JSON.read_text()); live = [k for k, v in res.items() if v["acc"]["passed"]]
    if not live: print("No trial passed acceptance 1-4: the 2026 hold-out stays CLOSED (registered rule)."); return
    P, _ = build_panel(); ok = P[CORE].notna().all(axis=1)
    for tr in live:
        if tr.startswith("C1"): pos = c1_positions(P, tr == "C1b")[ok & P.nr.notna()]; b = P[ok & P.nr.notna()]; R = b[["date", "mkt", "sig", "nr"]].assign(pos=pos.to_numpy())
        else: R = walk(P, "gbm" if tr.startswith("C3") else "ridge", 1 if tr.endswith("a") else 5, (2026,))
        g, n, _ = portfolio(R); st = stat(sl(n, "HOLD")); print(fmt(f"{tr} HOLD", st, stat(sl(g, "HOLD"))["sharpe"])); ledger(tr, "HOLD", st, f"net Sharpe {st['sharpe']:+.2f}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dry_run: dry_run()
    if a.trials: run_trials()
    if a.holdout: run_holdout()


if __name__ == "__main__":
    main()
