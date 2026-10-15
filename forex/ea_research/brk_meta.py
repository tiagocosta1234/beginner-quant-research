"""BRK-META exactly as in PREREG_BRK_META.md: walk-forward meta-labeling of the session breakouts of 46 MT5.
   python -m forex.ea_research.brk_meta --dry | (no flag) run"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t
from forex.ea_research.orb_refine import daily_table

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
FEATS = ["side", "hour", "mins_to_fill", "box_atr", "rel_vol_fill", "rel_vol_box", "atr_pct", "nr4", "trend_al", "dist_hi20", "dist_lo20",
         "prev_ret_al", "overnight_al", "dow", "mkt_mom20", "breadth", "c_crypto", "c_energy", "c_fx", "c_index", "c_metal"]


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    tz, op_s, cl_s = session(sym)
    lc = local_clock(t, tz)
    tv = pd.read_parquet(f"D:/finance/ticks_vol/{sym}.parquet", columns=["time", "tick_volume"])
    tv = tv[tv.time < end].drop_duplicates("time")
    vol = pd.Series(tv.tick_volume.to_numpy(float), index=tv.time.to_numpy()).reindex(t).to_numpy()
    cv = np.concatenate([[0.0], np.nancumsum(np.where(np.isnan(vol), 0, vol))])
    has = np.concatenate([[0], np.cumsum(~np.isnan(vol))])
    def vsum(a, b):
        return (cv[b] - cv[a]) if b > a and has[b] - has[a] >= (b - a) * 0.8 else np.nan
    dt = daily_table(D)
    rng_d = dt.h - dt.l
    nr4 = rng_d.shift(1) <= rng_d.shift(1).rolling(4).min()
    atr_pct = dt.atr_prev.rolling(250, min_periods=60).rank(pct=True)
    hi20, lo20 = dt.h.rolling(20).max().shift(1), dt.l.rolling(20).min().shift(1)
    prev_ret = dt.c.diff().shift(1)
    mid = (D["bo"] + D["ao"]) / 2
    rows, box_hist, prev_days = [], [], []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1:
            continue
        vb = vsum(i0, i1)
        box_ref = np.nanmedian(box_hist[-20:]) if np.sum(np.isfinite(box_hist[-20:])) >= 10 else np.nan
        box_hist.append(vb)
        prev = prev_days[-20:]
        prev_days.append(d)
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, kend, side, e, R)
        if x is None:
            continue
        sday = t[i0] // 86400
        if sday not in dt.index or not np.isfinite(dt.at[sday, "atr_prev"]):
            continue
        atr = dt.at[sday, "atr_prev"]
        tod = lc[k] - base
        ref = []
        for pdy in prev:
            j = np.searchsorted(lc, pdy * 86400 + tod)
            if j < len(t) and lc[j] - pdy * 86400 - tod < 60:
                ref.append(vsum(max(j - 4, 0), j + 1))
        vf_ref = np.nanmedian(ref) if np.sum(np.isfinite(ref)) >= 10 else np.nan
        vf = vsum(max(k - 4, 0), k + 1)
        cls = mclass(sym)
        rows.append(dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), sday=int(sday), t_entry=int(t[k]), X4=x[3],
                         side=side, hour=int(tod // 3600), mins_to_fill=(lc[k] - (base + op_s + 30 * M)) / 60, box_atr=(Hb - Lb) / atr,
                         rel_vol_fill=vf / vf_ref if vf_ref and vf_ref > 0 else np.nan, rel_vol_box=vb / box_ref if box_ref and box_ref > 0 else np.nan,
                         atr_pct=atr_pct.get(sday, np.nan), nr4=float(nr4.get(sday, False)),
                         trend_al=side * np.sign(dt.at[sday, "c_prev"] - dt.at[sday, "sma_prev"]),
                         dist_hi20=(hi20.get(sday, np.nan) - mid[k]) / atr, dist_lo20=(mid[k] - lo20.get(sday, np.nan)) / atr,
                         prev_ret_al=side * prev_ret.get(sday, np.nan) / atr, overnight_al=side * (mid[i0] - dt.at[sday, "c_prev"]) / atr,
                         dow=(int(sday) + 3) % 7, **{f"c_{c}": float(cls == c) for c in ("crypto", "energy", "fx", "index", "metal")}))
    df = pd.DataFrame(rows)
    if len(df):
        df["mkt_mom20"] = df.X4.rolling(20).mean().shift(1)
    return df


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        parts = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.concat([p for p in parts if len(p)], ignore_index=True).sort_values("t_entry").reset_index(drop=True)
    # breadth: number of markets that already broke the same way earlier this server day, / 46 (amended before P&L: the first draft divided by the day's total event count, which uses later events)
    df["breadth"] = 0.0
    for sd, g in df.groupby("sday"):
        idx = g.index.to_numpy()
        s = g.side.to_numpy()
        up_c, dn_c = np.cumsum(s > 0) - (s > 0), np.cumsum(s < 0) - (s < 0)
        df.loc[idx, "breadth"] = np.where(s > 0, up_c, dn_c) / len(SYMS)          # causal: earlier same-way breakouts / 46 markets
    return df[df.day >= "2022-01-01"].reset_index(drop=True)


def fit_predict(train, test, kind, rng=None):
    Xtr, Xte = train[FEATS].to_numpy(float), test[FEATS].to_numpy(float)
    y = train.X4.to_numpy(float)
    if rng is not None:                                                    # placebo: labels shuffled within each training year
        y = y.copy()
        for yr in np.unique(train.day.dt.year):
            m = (train.day.dt.year == yr).to_numpy()
            y[m] = rng.permutation(y[m])
    y = np.clip(y, -1.5, 4.0)
    if kind == "M1":
        from xgboost import XGBRegressor
        mdl = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_jobs=8, random_state=1)
        mdl.fit(Xtr, y)
        ptr, pte = mdl.predict(Xtr), mdl.predict(Xte)
    else:
        mu, sd = np.nanmean(Xtr, 0), np.nanstd(Xtr, 0) + 1e-9
        A, B = np.nan_to_num((Xtr - mu) / sd), np.nan_to_num((Xte - mu) / sd)
        A1, B1 = np.c_[np.ones(len(A)), A], np.c_[np.ones(len(B)), B]
        w = np.linalg.solve(A1.T @ A1 + 10.0 * np.eye(A1.shape[1]), A1.T @ y)
        ptr, pte = A1 @ w, B1 @ w
    return pte >= np.percentile(ptr, 80)


def walk(df, kind, rng=None):
    sel = []
    for y in (2023, 2024, 2025, 2026):
        tr, te = df[df.day.dt.year < y], df[df.day.dt.year == y]
        if len(te):
            sel.append(te[fit_predict(tr, te, kind, rng)])
    return pd.concat(sel)


def stats(x, a, b):
    s = x[(x.day >= a) & (x.day <= b)]
    return len(s), s.X4.mean(), nw_t(s.groupby("day").X4.mean().to_numpy())


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s | events {len(df)} | feature coverage: " + ", ".join(f"{f} {df[f].notna().mean():.2f}" for f in FEATS[:16]))
    print("breadth sample:", df.breadth.describe().round(3).to_dict())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = market(("NSDQ", END)), market(("NSDQ", cut))
    f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
    same = len(f) == len(p) and np.allclose(f[FEATS[:15]].fillna(-9).to_numpy(), p[FEATS[:15]].fillna(-9).to_numpy())
    print("truncation test (features):", "PASS" if same else "FAIL")
    sel = walk(df, "M2")
    print("selection counts per year (M2):", sel.groupby(sel.day.dt.year).size().to_dict(), "| of events:", df.groupby(df.day.dt.year).size().to_dict())


def run():
    df = collect(END)
    df.to_parquet("D:/finance/si_ledgers/BRK_META_events.parquet")
    DEVp, VALp, Y26 = ("2023-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
    base = [stats(df, *p) for p in (DEVp, VALp, Y26)]
    print(f"base (all events) DEV {base[0][1]:+.3f} VAL {base[1][1]:+.3f} 2026 {base[2][1]:+.3f}")
    for kind in ("M1", "M2"):
        sel = walk(df, kind)
        r = [stats(sel, *p) for p in (DEVp, VALp, Y26)]
        plc = [walk(df, kind, np.random.default_rng(s)) for s in (101, 102, 103)]
        pd_ = [stats(p_, *DEVp)[1] for p_ in plc]
        pv_ = [stats(p_, *VALp)[1] for p_ in plc]
        g = [r[0][1] >= 0.05 and r[0][2] >= 2.24, r[1][1] > 0 and r[1][2] >= 1.65, r[0][1] > max(pd_), r[0][1] - base[0][1] >= 0.05 and r[1][1] - base[1][1] >= 0.05]
        print(f"{kind}: DEV n{r[0][0]} {r[0][1]:+.3f} (t {r[0][2]:+.2f}) | VAL n{r[1][0]} {r[1][1]:+.3f} (t {r[1][2]:+.2f}) | 2026 n{r[2][0]} {r[2][1]:+.3f} | "
              f"placebo DEV {', '.join(f'{v:+.3f}' for v in pd_)} VAL {', '.join(f'{v:+.3f}' for v in pv_)} | gates {''.join('Y' if v else 'n' for v in g)} PASS {all(g)}")
        print("   selected by class (DEV):", sel[(sel.day >= DEVp[0]) & (sel.day <= DEVp[1])].mkt.map(mclass).value_counts().to_dict())
    from xgboost import XGBRegressor
    tr = df[df.day.dt.year < 2025]
    mdl = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_jobs=8, random_state=1).fit(tr[FEATS].to_numpy(float), np.clip(tr.X4, -1.5, 4))
    imp = sorted(zip(FEATS, mdl.feature_importances_), key=lambda z: -z[1])[:8]
    print("top features (model trained 2022-24):", ", ".join(f"{f} {v:.3f}" for f, v in imp))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
