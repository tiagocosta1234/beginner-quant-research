"""Family K2 (confluence panel on hourly bars), exactly as registered in PREREG_CONFLUENCE_H1.md (the trader 2026-10-10: "(original wording omitted)").
   python -m mt5broker.ea_research.confluence_h1 --dry-run | --trials | --holdout
42 MT5, hourly mid bars from M1 bid/ask, four trials: S1/S4 hour x market seasonality, G1/G4 depth-3 boosting, walk-forward by year (test 2024, 2025).
--dry-run prints counts, the causality (truncation) tests and a hand check; NO P&L and no signal-vs-label statistic."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
CACHE = Path("D:/finance/tmp/confluence_h1_panel.parquet")
OUT_JSON = HERE / "CONFLUENCE_H1_STATE.json"
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
      "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
IDX = ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"]
MET = ["XAUUSD", "XAGUSD"]
OIL = ["WTI", "BRENT"]
CRY = ["BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"]
MARKETS = FX + IDX + MET + OIL + CRY
CLS = {**{m: 0 for m in FX}, **{m: 1 for m in IDX}, **{m: 2 for m in MET}, **{m: 3 for m in OIL}, **{m: 4 for m in CRY}}
CLS_NAME = {0: "FX", 1: "index", 2: "metal", 3: "oil", 4: "crypto"}
MID = {m: i for i, m in enumerate(MARKETS)}
USD_Q = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]; USD_B = ["USDJPY", "USDCAD", "USDCHF"]
PERIODS = {"DEV": ("2024-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2024-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
TARGET = 0.0005; SLIP = 1e-5
DROP: tuple = ()          # decision hours forced flat (variant b: 22, 23, 0 -- rollover); trials are then named with a trailing b
FAMILY = "confluence_h1"; T_BAR = 2.4; SUF = ""
FEATS = ["r1", "r2", "r4", "r8", "r24", "r72", "r120", "dday", "dpdc", "dpdh", "dpdl", "rng24", "rng120", "rsi14", "atrr", "sprs", "sprm", "hour", "dow", "month", "cls", "mid", "usd4", "usd24", "sp4", "sp24", "gold24", "ry_chg5", "ry_lvl", "xs8", "xs24"]
CORE = ["r120", "rng120", "atrr", "sig", "dpdc"]


# ---------------------------------------------------------------- bars and features
def load_bars(m: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo) & (d.ac >= d.bc) & (d.bc > 0)]
    hb = (d.t // 3600).to_numpy("int64"); g = d.groupby(hb, sort=True); f, l = g.first(), g.last()
    b = pd.DataFrame({"T": f.index.to_numpy() * 3600, "m": ((f.bo + f.ao) / 2).to_numpy(), "sp0": ((f.ao - f.bo) / ((f.bo + f.ao) / 2)).to_numpy(), "c": ((l.bc + l.ac) / 2).to_numpy(), "sp1": ((l.ac - l.bc) / ((l.bc + l.ac) / 2)).to_numpy(),
                      "h": ((g.bh.max() + g.ah.max()) / 2).to_numpy(), "l": ((g.bl.min() + g.al.min()) / 2).to_numpy(), "n": g.size().to_numpy()})
    dow = pd.to_datetime(b["T"], unit="s").dt.dayofweek.to_numpy(); b = b[(b.n >= 20) & (dow < 5) & (b.sp0 < 0.05) & (b.sp1 < 0.05)].reset_index(drop=True)
    bad = (np.log(b.c / b.m).abs() > 0.15) | (b.h < b.l); b = b[~bad].reset_index(drop=True)      # quote glitches
    return b


def _rsi(c: pd.Series, n: int) -> pd.Series:
    de = c.diff(); up = de.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean(); dn = (-de.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    r = 100 - 100 / (1 + up / dn); r[(dn == 0) & up.notna()] = 100.0; return r


def feats(b: pd.DataFrame) -> pd.DataFrame:
    """Per-market features at bar k use bars <= k only (truncation-tested). Rows are bars in order."""
    c, m, h, l = b.c, b.m, b.h, b.l; lr = np.log(c).diff(); sig = np.sqrt((lr ** 2).ewm(alpha=0.02, min_periods=100, adjust=False).mean())
    f = pd.DataFrame({"T": b["T"], "sig": sig}); date = (b["T"] // 86400).to_numpy()
    for L in (1, 2, 4, 8, 24, 72, 120): f[f"r{L}"] = np.log(c / c.shift(L)) / (sig * np.sqrt(L))
    s24 = sig * np.sqrt(24); dopen = m.groupby(date).transform("first"); f["dday"] = np.log(c / dopen) / s24
    day = pd.DataFrame({"d": date, "c": c, "h": h, "l": l}).groupby("d").agg(dc=("c", "last"), dh=("h", "max"), dl=("l", "min")).shift(1)
    pdc, pdh, pdl = (pd.Series(date).map(day[k]).to_numpy() for k in ("dc", "dh", "dl"))
    f["dpdc"] = np.log(c.to_numpy() / pdc) / s24.to_numpy(); f["dpdh"] = np.log(c.to_numpy() / pdh) / s24.to_numpy(); f["dpdl"] = np.log(c.to_numpy() / pdl) / s24.to_numpy()
    for L in (24, 120):
        lo, hi = l.rolling(L).min(), h.rolling(L).max(); f[f"rng{L}"] = ((c - lo) / (hi - lo)).where(hi > lo, 0.5).where(lo.notna())
    f["rsi14"] = _rsi(c, 14); pc = c.shift(1); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1, skipna=False); f["atrr"] = tr.rolling(6).mean() / tr.rolling(48).mean()
    f["sprs"] = b.sp1 / sig; f["sprm"] = b.sp1 / b.sp1.rolling(120).median()
    ts = pd.to_datetime(b["T"], unit="s"); f["hour"] = ts.dt.hour.to_numpy().astype(float); f["dow"] = ts.dt.dayofweek.to_numpy().astype(float); f["month"] = ts.dt.month.to_numpy().astype(float)
    mm = m.to_numpy(); f["nr"] = np.r_[mm[2:] / mm[1:-1] - 1.0, [np.nan, np.nan]]                                  # return of the position held through bar k+1
    lm = np.log(m); f["y1"] = ((lm.shift(-2) - lm.shift(-1)) / sig).to_numpy(); f["y4"] = ((lm.shift(-5) - lm.shift(-1)) / (sig * 2)).to_numpy()
    f["cs"] = (0.5 * b.sp0.shift(-1) + SLIP).to_numpy(); Ts = pd.Series(b["T"].to_numpy()); f["end1"] = Ts.shift(-2).to_numpy(); f["end4"] = Ts.shift(-5).to_numpy()
    return f


def context(frames: dict, grid: np.ndarray) -> pd.DataFrame:
    def lrr(mk):
        b = frames[mk]; return pd.Series(np.log(b.c).diff().to_numpy(), index=b["T"].to_numpy()).reindex(grid).fillna(0.0)
    usd = (sum(-lrr(x) for x in USD_Q) + sum(lrr(x) for x in USD_B)) / 7.0; ctx = pd.DataFrame(index=grid)
    for L in (4, 24): ctx[f"usd{L}"] = usd.rolling(L).sum()
    sp = lrr("SP")
    for L in (4, 24): ctx[f"sp{L}"] = sp.rolling(L).sum()
    ctx["gold24"] = lrr("XAUUSD").rolling(24).sum()
    ry = pd.read_csv("D:/finance/data_macro/DFII10.csv"); ry["observation_date"] = pd.to_datetime(ry.observation_date); ry = pd.to_numeric(ry.set_index("observation_date").DFII10, errors="coerce").dropna()
    days = pd.date_range("2021-11-01", "2026-10-31", freq="D"); ryd = ry.reindex(ry.index.union(days)).ffill().reindex(days)
    dayval = pd.DataFrame({"ry_lvl": ryd.shift(1), "ry_chg5": ryd.shift(1) - ryd.shift(6)}, index=days)                 # value known at the previous day's close
    dd = pd.to_datetime(grid, unit="s").normalize(); ctx["ry_lvl"] = dayval.ry_lvl.reindex(dd).to_numpy(); ctx["ry_chg5"] = dayval.ry_chg5.reindex(dd).to_numpy()
    return ctx


def build_panel(rebuild=False):
    if CACHE.exists() and not rebuild: return pd.read_parquet(CACHE), None
    frames = {m: load_bars(m) for m in MARKETS}; grid = np.array(sorted(set().union(*[set(b["T"]) for b in frames.values()])), dtype="int64"); ctx = context(frames, grid); parts = []
    for mk, b in frames.items():
        f = feats(b); f["mkt"] = mk; f["mid"] = float(MID[mk]); f["cls"] = float(CLS[mk]); f = f.join(ctx, on="T"); parts.append(f)
    P = pd.concat(parts, ignore_index=True)
    for L in (8, 24): P[f"xs{L}"] = P.groupby("T")[f"r{L}"].rank(pct=True)
    P = P.sort_values(["mkt", "T"]).reset_index(drop=True); P["date"] = pd.to_datetime(P["T"], unit="s").dt.normalize()
    for c in P.columns:
        if P[c].dtype == "float64" and c not in ("T", "end1", "end4"): P[c] = P[c].astype("float32")
    CACHE.parent.mkdir(parents=True, exist_ok=True); P.to_parquet(CACHE); return P, frames


# ---------------------------------------------------------------- models
def fit_model(kind: str, tr: pd.DataFrame, yc: str, rng=None):
    y = tr[yc].clip(-4, 4).to_numpy("float64")
    if rng is not None: y = tr.assign(_y=y).groupby("T")._y.transform(lambda s: rng.permutation(s.to_numpy())).to_numpy()      # labels permuted within hour (control)
    if kind == "seas":
        g = pd.DataFrame({"mkt": tr.mkt.to_numpy(), "hour": tr.hour.to_numpy(), "y": y}).groupby(["mkt", "hour"]).y.agg(["mean", "size"]); g["p"] = g["mean"] * g["size"] / (g["size"] + 200.0); return ("seas", g.p, None)
    from sklearn.ensemble import HistGradientBoostingRegressor
    cats = np.array([c == "mid" for c in FEATS]); m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=1000, l2_regularization=10.0, random_state=0, categorical_features=cats).fit(tr[FEATS].to_numpy("float32"), y)
    return ("gbm", m, None)


def predict(mod, df: pd.DataFrame) -> np.ndarray:
    kind, m, _ = mod
    if kind == "seas": return m.reindex(pd.MultiIndex.from_arrays([df.mkt.to_numpy(), df.hour.to_numpy()])).fillna(0.0).to_numpy("float64")
    return m.predict(df[FEATS].to_numpy("float32"))


def walk(P: pd.DataFrame, kind: str, h: int, years, shuffle_seed=None) -> pd.DataFrame:
    yc, ec = f"y{h}", f"end{h}"; ok = P[CORE].notna().all(axis=1) & P[yc].notna(); rows = []; rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    for Y in years:
        t0, t1, ta = (pd.Timestamp(f"{Y}-01-01"), pd.Timestamp(f"{Y}-12-31"), pd.Timestamp(f"{Y - 1}-01-01")); e0, ea = t0.timestamp(), ta.timestamp()
        keep = ~P.hour.isin(DROP) if DROP else True
        trB = P[ok & keep & (P[ec] < e0)]; trA = P[ok & keep & (P[ec] < ea)]
        mB = fit_model(kind, trB, yc, rng); mA = fit_model(kind, trA, yc, rng); okp = P[CORE].notna().all(axis=1)
        pa = predict(mA, P[okp & keep & (P.date >= ta) & (P.date < t0)]); s = max(float(np.std(pa)), 1e-9)
        te = P[okp & (P.date >= t0) & (P.date <= t1) & P.nr.notna()]; pr = predict(mB, te); z = pr / s
        rows.append(te[["T", "date", "mkt", "hour", "sig", "nr", "cs", yc]].assign(pred=pr, pos=np.sign(z) * np.clip(np.abs(z) - 1.0, 0.0, 1.0) * (~te.hour.isin(DROP)).to_numpy(), scale=s).rename(columns={yc: "y"}))
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- portfolio and statistics
def prep(R: pd.DataFrame):
    """Per-market arrays in time order: weight, bar return, entry cost, date code."""
    R = R.sort_values(["mkt", "T"]); codes, uniq = pd.factorize(R.date, sort=True); R = R.assign(dc=codes); out = []
    for mk, g in R.groupby("mkt", sort=False):
        w = np.where(g.sig.to_numpy() > 0, g.pos.to_numpy() * TARGET / np.where(g.sig.to_numpy() > 0, g.sig.to_numpy(), 1.0), 0.0); out.append((mk, w, g.nr.to_numpy("float64"), g.cs.to_numpy("float64"), g.dc.to_numpy(), g.hour.to_numpy()))
    return out, uniq


def pnl_daily(parts, nd, shifts=None, by_hour=False):
    gross = np.zeros(nd); net = np.zeros(nd); hr = np.zeros(24)
    for j, (mk, w, nr, cs, dc, hour) in enumerate(parts):
        if shifts is not None: w = np.roll(w, shifts[j])
        dw = np.abs(np.diff(w, prepend=0.0)); gx = w * nr; nt = gx - cs * dw
        gross += np.bincount(dc, weights=gx, minlength=nd); net += np.bincount(dc, weights=nt, minlength=nd)
        if by_hour: hr += np.bincount(hour.astype(int), weights=nt, minlength=24)
    return (gross, net, hr) if by_hour else (gross, net)


def stat(r: np.ndarray, idx=None) -> dict:
    r = pd.Series(r) if idx is None else pd.Series(r, index=idx); n = len(r)
    if n < 20 or r.std(ddof=1) == 0: return dict(n=n, sharpe=float("nan"), t=float("nan"), bp=float("nan"), pf=float("nan"), win=float("nan"), dd=float("nan"))
    sd = r.std(ddof=1); w, l_ = r[r > 0].sum(), -r[r < 0].sum(); eq = r.cumsum()
    return dict(n=n, sharpe=float(r.mean() / sd * np.sqrt(252)), t=float(r.mean() / (sd / np.sqrt(n))), bp=float(r.mean() * 1e4), pf=float(w / l_) if l_ > 0 else float("inf"), win=float((r > 0).mean()), dd=float((eq.cummax() - eq).max()))


def window(R: pd.DataFrame, per: str) -> pd.DataFrame:
    a, b = PERIODS[per]; return R[(R.date >= a) & (R.date <= b)]


def evaluate(R: pd.DataFrame, per: str, perm=0, seed=7, by_hour=False):
    W = window(R, per); parts, uniq = prep(W); nd = len(uniq); res = pnl_daily(parts, nd, by_hour=by_hour); g, n = res[0], res[1]
    out = dict(net=stat(n, uniq), gross=stat(g, uniq), g=g, n=n, uniq=uniq, hour=res[2] if by_hour else None)
    if perm:
        rng = np.random.default_rng(seed); obs = out["net"]["sharpe"]; null = []
        for _ in range(perm):
            sh = [int(rng.integers(120, max(121, len(p[1]) - 120))) for p in parts]; nn = pnl_daily(parts, nd, sh)[1]; null.append(nn.mean() / nn.std(ddof=1) * np.sqrt(252))
        out["p"] = (1 + sum(v >= obs for v in null)) / (1 + perm); out["null"] = float(np.mean(null))
    return out


def daily_ic(R: pd.DataFrame) -> tuple[float, float, int]:
    d = R.dropna(subset=["y"]).copy(); cnt = d.groupby("T").pred.transform("size"); d = d[cnt >= 20]
    rp = d.groupby("T").pred.rank(); ry = d.groupby("T").y.rank(); rp = rp - rp.groupby(d["T"]).transform("mean"); ry = ry - ry.groupby(d["T"]).transform("mean")
    num = (rp * ry).groupby(d["T"]).sum(); den = np.sqrt((rp ** 2).groupby(d["T"]).sum() * (ry ** 2).groupby(d["T"]).sum()); ic = (num / den).dropna()
    dayic = ic.groupby(pd.to_datetime(ic.index, unit="s").normalize()).mean(); return float(dayic.mean()), float(dayic.mean() / (dayic.std(ddof=1) / np.sqrt(len(dayic)))), len(dayic)


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},{FAMILY},{trial},{period},{s['n']},,,{s['bp']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def fmt(tag, s, g=None):
    return f"{tag:12s} days {s['n']:4d} | net Sharpe {s['sharpe']:+5.2f} | daily t {s['t']:+5.2f} | {s['bp']:+6.2f} bp/day | PF {s['pf']:4.2f} | win {100*s['win']:4.1f}% | maxDD {100*s['dd']:5.1f}%" + (f" | gross Sharpe {g:+5.2f}" if g is not None else "")


# ---------------------------------------------------------------- dry run
def dry_run():
    P, frames = build_panel(rebuild=True); pd.set_option("display.width", 200)
    print("== panel ==", P.shape, "| markets", P.mkt.nunique(), "| bars per market (min/median/max)", P.groupby("mkt").size().min(), int(P.groupby("mkt").size().median()), P.groupby("mkt").size().max(), "| features", len(FEATS))
    print("bars per market:", {m: len(frames[m]) for m in MARKETS})
    ok = P[CORE].notna().all(axis=1) & P.nr.notna() & P.y1.notna() & P.y4.notna(); print("usable rows", int(ok.sum()), "| first usable", P[ok].date.min().date(), "| last", P[ok].date.max().date())
    for per, (a, b) in PERIODS.items(): x = P[ok & (P.date >= a) & (P.date <= b)]; print(f"  {per:5s} market-bars {len(x):8d}  server dates {x.date.nunique():4d}  markets per bar-time {len(x)/max(1,x['T'].nunique()):5.1f}")
    print("training rows for the first fit (test 2024):", int((ok & (P.end1 < pd.Timestamp('2024-01-01').timestamp())).sum()), "| scale-model fit (test 2023):", int((ok & (P.end1 < pd.Timestamp('2023-01-01').timestamp())).sum()))
    print("NaN share per feature (usable rows):", {c: round(float(P.loc[ok, c].isna().mean()), 3) for c in FEATS if P.loc[ok, c].isna().mean() > 0.001})
    print("median relative spread at the first minute (bp):", {m: round(float(frames[m].sp0.median() * 1e4), 2) for m in ["EURUSD", "GBPJPY", "XAUUSD", "SP", "NSDQ", "WTI", "BTCUSD", "XRPUSD", "AUDNZD", "NIKKEI"]})
    print("hour-of-bar coverage (share of bars per server hour, all markets):", (P.hour.value_counts(normalize=True).sort_index() * 100).round(1).to_dict())
    rng = np.random.default_rng(1); bad = 0; chk = 0
    for _ in range(25):
        m = MARKETS[rng.integers(len(MARKETS))]; b = frames[m]; k = int(rng.integers(400, len(b) - 10)); ft = feats(b.iloc[:k + 1].reset_index(drop=True)).iloc[-1]; ff = feats(b).iloc[k]
        for c in ft.index:
            if c in ("nr", "y1", "y4", "cs", "end1", "end4"): continue
            a_, b_ = ft[c], ff[c]; chk += 1
            if not ((np.isnan(a_) and np.isnan(b_)) or abs(a_ - b_) < 1e-9 * max(1, abs(b_))): bad += 1; print("   NON-CAUSAL", m, int(b["T"].iloc[k]), c, a_, b_)
    print(f"causality test (truncated vs full bars, 25 random bars): {chk} comparisons, {bad} mismatches")
    grid = np.array(sorted(set().union(*[set(b["T"]) for b in frames.values()])), dtype="int64"); cx = context(frames, grid); cut = grid[len(grid) // 2]
    fr2 = {m: b[b["T"] <= cut].reset_index(drop=True) for m, b in frames.items()}; cx2 = context(fr2, grid[grid <= cut]); dif = (cx.loc[cx2.index] - cx2).abs().max().max()
    print(f"context truncation test: max difference {dif:.2e} (0 = no future data)")
    # hand check on gold from raw M1 minutes
    b = frames["XAUUSD"]; f = feats(b); k = len(b) - 40; T = int(b["T"].iloc[k]); d = pd.read_parquet(DATA / "XAUUSD_M1_rates.parquet", columns=["t", "bo", "ao", "bc", "ac"]); x = d[(d.t >= T) & (d.t < T + 3600)]
    print(f"hand check XAUUSD bar {T}: open mid table {b.m.iloc[k]:.3f} vs manual {((x.bo.iloc[0]+x.ao.iloc[0])/2):.3f} | close mid table {b.c.iloc[k]:.3f} vs manual {((x.bc.iloc[-1]+x.ac.iloc[-1])/2):.3f} | minutes {len(x)} vs n {b.n.iloc[k]}")
    c = b.c; lr_ = np.log(c).diff(); s2 = (lr_ ** 2).ewm(alpha=0.02, min_periods=100, adjust=False).mean().iloc[k]; r4 = np.log(c.iloc[k] / c.iloc[k - 4]) / (np.sqrt(s2) * 2)
    print(f"   r4 table {f.r4.iloc[k]:+.4f} vs manual {r4:+.4f} | nr (next bar return) table {f.nr.iloc[k]:+.6f} vs manual {b.m.iloc[k+2]/b.m.iloc[k+1]-1:+.6f} | cs table {f.cs.iloc[k]*1e4:.3f} bp vs manual {(0.5*b.sp0.iloc[k+1]+SLIP)*1e4:.3f} bp")
    print("no P&L, no signal-vs-label statistic computed")


# ---------------------------------------------------------------- trials
def accept(pool, years, p, ic) -> dict:
    a1 = pool["t"] >= T_BAR and pool["sharpe"] >= 1.0; a2 = years["DEV"]["sharpe"] > 0 and years["VAL"]["sharpe"] > 0 and years["VAL"]["sharpe"] >= 0.3; a3 = p <= 0.01; a4 = ic[0] > 0 and ic[1] >= 2
    return dict(a1=bool(a1), a2=bool(a2), a3=bool(a3), a4=bool(a4), passed=bool(a1 and a2 and a3 and a4))


def run_trials():
    P, _ = build_panel(); results = {}
    for kind, nm in (("seas", "S"), ("gbm", "G")):
        for h in (1, 4):
            tr = f"{nm}{h}{SUF}"; R = walk(P, kind, h, (2024, 2025)); results[tr] = report(tr, R)
    print("\n== controls (not trials) ==")
    R = walk(P, "gbm", 1, (2024, 2025), shuffle_seed=11); e = evaluate(R, "POOL"); ic = daily_ic(R); print(fmt("G1 shuffled", e["net"], e["gross"]["sharpe"]), f"| IC {ic[0]:+.4f} (t {ic[1]:+.2f})")
    base = R[["T", "date", "mkt", "hour", "sig", "nr", "cs"]].assign(pos=np.where(R.mkt.map(CLS) == 0, 0.0, 1.0)); e = evaluate(base, "POOL"); print(fmt("long-only drift", e["net"], e["gross"]["sharpe"]), "(+1 on every non-FX market in the same bars)")
    OUT_JSON.write_text(json.dumps(results, indent=1), encoding="utf-8"); print("\n== acceptance 1-4 ==", {k: v["acc"] for k, v in results.items()}); return results


def report(tr, R):
    print(f"\n=== {tr}: {len(R)} market-bars; positions non-zero {100*(R.pos!=0).mean():.1f}% ; long share of non-zero {100*(R.pos>0).sum()/max(1,(R.pos!=0).sum()):.0f}% ===", flush=True)
    sts = {}; ev = {}
    for per in ("DEV", "VAL", "POOL"):
        e = evaluate(R, per, perm=1000 if per == "POOL" else 0, by_hour=(per == "POOL")); ev[per] = e; sts[per] = e["net"]; print(fmt(f"{tr} {per}", e["net"], e["gross"]["sharpe"]), flush=True); ledger(tr, per, e["net"], f"net Sharpe {e['net']['sharpe']:+.2f}; gross Sharpe {e['gross']['sharpe']:+.2f}")
    p, nm = ev["POOL"]["p"], ev["POOL"]["null"]; ic = daily_ic(R)
    print(f"   permutation p (1000 circular shifts, POOL) {p:.4f}, null mean Sharpe {nm:+.2f} | mean daily cross-sectional rank IC {ic[0]:+.4f} (t {ic[1]:+.2f}, {ic[2]} days)")
    hr = ev["POOL"]["hour"]; top = np.argsort(-hr)[:3]; print("   net P&L by decision hour (share of total |P&L|), top 3:", {int(h): round(float(hr[h] / np.abs(hr).sum()), 3) for h in top}, "| worst:", {int(h): round(float(hr[h] / np.abs(hr).sum()), 3) for h in np.argsort(hr)[:2]})
    cl = {}
    for ci, nmc in CLS_NAME.items():
        sub = R[R.mkt.map(CLS) == ci]; cl[nmc] = round(evaluate(sub, "POOL")["net"]["sharpe"], 2) if len(sub) else float("nan")
    print("   POOL net Sharpe by class:", cl)
    acc = accept(sts["POOL"], sts, p, ic); print("   acceptance a1 (t>=2.4 & Sharpe>=1.0):", acc["a1"], "| a2 (both years>0, 2025>=0.3):", acc["a2"], "| a3 (perm p<=0.01):", acc["a3"], "| a4 (IC>0, t>=2):", acc["a4"], "=> PASSED" if acc["passed"] else "=> closed")
    ledger(tr, "PERM", dict(n=len(R), bp=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan")), f"perm p {p:.4f}; IC {ic[0]:.4f}; passed {acc['passed']}")
    return dict(acc=acc, pool=sts["POOL"], p=p, ic=ic)


def run_holdout():
    if not OUT_JSON.exists(): print("run --trials first"); return
    res = json.loads(OUT_JSON.read_text()); live = [k for k, v in res.items() if v["acc"]["passed"]]
    if not live: print("No trial passed acceptance 1-4: the 2026 hold-out stays CLOSED (registered rule)."); return
    P, _ = build_panel()
    for tr in live:
        R = walk(P, "seas" if tr.startswith("S") else "gbm", int(tr[1:2]), (2026,)); e = evaluate(R, "HOLD"); print(fmt(f"{tr} HOLD", e["net"], e["gross"]["sharpe"])); ledger(tr, "HOLD", e["net"], f"net Sharpe {e['net']['sharpe']:+.2f}")


def main():
    global DROP, FAMILY, T_BAR, SUF, OUT_JSON
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); ap.add_argument("--variant", default="a", choices=["a", "b"]); a = ap.parse_args()
    if a.variant == "b": DROP = (22, 23, 0); FAMILY = "confluence_h1b"; T_BAR = 2.6; SUF = "b"; OUT_JSON = HERE / "CONFLUENCE_H1B_STATE.json"
    if a.dry_run: dry_run()
    if a.trials: run_trials()
    if a.holdout: run_holdout()


if __name__ == "__main__":
    main()
