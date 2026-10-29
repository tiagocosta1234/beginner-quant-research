"""BRK-VOLREG exactly as in PREREG_BRK_VOLREG.md: volume and volatility-regime filters on the session breakout of 46 markets.
   python -m forex.ea_research.brk_volreg --dry | (no flag) run"""
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
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
INDICES = ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX")


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    tz, op_s, cl_s = session(sym)
    lc = local_clock(t, tz)
    tv = pd.read_parquet(f"data/ticks_vol/{sym}.parquet", columns=["time", "tick_volume"])
    tv = tv[tv.time < end].drop_duplicates("time")
    vol = pd.Series(tv.tick_volume.to_numpy(float), index=tv.time.to_numpy()).reindex(t).to_numpy()
    cv = np.concatenate([[0.0], np.nancumsum(np.where(np.isnan(vol), 0, vol))])          # prefix sums
    has = np.concatenate([[0], np.cumsum(~np.isnan(vol))])
    def vsum(a, b):
        return (cv[b] - cv[a]) if has[b] - has[a] >= (b - a) * 0.8 and b > a else np.nan
    dt = daily_table(D)
    rng_d = dt.h - dt.l
    nr4 = (rng_d.shift(1) <= rng_d.shift(1).rolling(4).min())
    atr_pct = dt.atr_prev.rolling(250, min_periods=60).rank(pct=True)
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
        box_ref = np.nanmedian(box_hist[-20:]) if len(box_hist) >= 10 else np.nan
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
        tod = lc[k] - base
        vf = vsum(max(k - 4, 0), k + 1)
        ref = []
        for pdy in prev:
            j = np.searchsorted(lc, pdy * 86400 + tod)
            if j < len(t) and lc[j] - pdy * 86400 - tod < 60:
                ref.append(vsum(max(j - 4, 0), j + 1))
        vf_ref = np.nanmedian(ref) if np.sum(np.isfinite(ref)) >= 10 else np.nan
        sday = t[i0] // 86400
        tr = np.sign(dt.at[sday, "c_prev"] - dt.at[sday, "sma_prev"]) if sday in dt.index else np.nan
        rows.append(dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), side=side, t_entry=int(t[k]), X4=x[3], X2=x[1],
                         rel_vol_fill=vf / vf_ref if vf_ref and vf_ref > 0 else np.nan,
                         rel_vol_box=vb / box_ref if box_ref and box_ref > 0 else np.nan,
                         atr_pct=atr_pct.get(sday, np.nan), nr4=bool(nr4.get(sday, False)), trend=tr))
    df = pd.DataFrame(rows)
    for f in ("rel_vol_fill", "rel_vol_box"):
        df[f + "_hi"] = df[f] > df[f].rolling(250, min_periods=60).quantile(0.67).shift(1)
    return df


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        parts = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.concat(parts, ignore_index=True)
    return df[df.day >= DEV[0]]


def cells(df):
    return {"V1_vol_surge": df[df.rel_vol_fill_hi], "V2_busy_box": df[df.rel_vol_box_hi], "V3_high_vol": df[df.atr_pct >= 0.67],
            "V4_NR4": df[df.nr4], "V5_trend_dir": df[df.side == df.trend], "V6_trend_and_vol": df[(df.side == df.trend) & df.rel_vol_fill_hi]}


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s | base events {len(df)} | feature coverage: " + ", ".join(f"{c} {df[c].notna().mean():.2f}" for c in ("rel_vol_fill", "rel_vol_box", "atr_pct", "trend")))
    for k, v in cells(df).items():
        print(f"  {k}: DEV {((v.day >= DEV[0]) & (v.day <= DEV[1])).sum()} VAL {((v.day >= VAL[0]) & (v.day <= VAL[1])).sum()} 2026 {(v.day >= Y26[0]).sum()}")
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "NSDQ"):
        f, p = market((s, END)), market((s, cut))
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        same = len(f) == len(p) and np.allclose(f.X4, p.X4) and np.allclose(f.rel_vol_fill.fillna(-1), p.rel_vol_fill.fillna(-1)) and (f.rel_vol_fill_hi == p.rel_vol_fill_hi).all()
        bad += int(not same)
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.mkt == "NSDQ") & (df.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12:", x[["side", "X4", "rel_vol_fill", "rel_vol_box", "atr_pct", "nr4", "trend"]].round(3).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_VOLREG.parquet")
    rng = np.random.default_rng(11)
    base = df[(df.day >= DEV[0]) & (df.day <= DEV[1])]
    print(f"base (all events) X4: DEV {base.X4.mean():+.3f} VAL {df[(df.day >= VAL[0]) & (df.day <= VAL[1])].X4.mean():+.3f} 2026 {df[df.day >= Y26[0]].X4.mean():+.3f}")
    rows = []
    for name, c in cells(df).items():
        r = dict(cell=name)
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = c[(c.day >= a) & (c.day <= b)]
            r[f"n {lab}"], r[f"X4 {lab}"], r[f"t {lab}"], r[f"X2 {lab}"] = len(s), s.X4.mean(), nw_t(s.groupby("day").X4.mean().to_numpy()), s.X2.mean()
        nd = r["n DEV"]
        p95 = np.percentile([base.X4.to_numpy()[rng.choice(len(base), nd, replace=False)].mean() for _ in range(1000)], 95)
        g = [r["X4 DEV"] >= 0.05 and r["t DEV"] >= 2.4, r["X4 VAL"] > 0 and r["t VAL"] >= 1.65, r["X4 DEV"] > p95]
        r["random95"], r["gates"], r["PASS"] = p95, "".join("Y" if v else "n" for v in g), all(g)
        ix = c[c.mkt.isin(INDICES)]
        r["indices DEV/VAL/2026"] = " / ".join(f"{ix[(ix.day >= a) & (ix.day <= b)].X4.mean():+.3f}" for a, b in (DEV, VAL, Y26))
        rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 260)
    print(R.round(3).to_string(index=False))
    R.to_csv("data/si_ledgers/BRK_VOLREG_cells.csv", index=False)
    print("\nby class, X4 DEV / VAL:")
    for name, c in cells(df).items():
        c = c.assign(cl=c.mkt.map(mclass))
        print(f"  {name}: " + " | ".join(f"{cl} {g[g.day <= DEV[1]].X4.mean():+.3f}/{g[(g.day >= VAL[0]) & (g.day <= VAL[1])].X4.mean():+.3f}" for cl, g in c.groupby("cl")))
    # monotonic check: X4 by tercile of each continuous feature (DEV)
    print("\nX4 by feature tercile (DEV, all markets):")
    for f in ("rel_vol_fill", "rel_vol_box", "atr_pct"):
        b = base.dropna(subset=[f])
        q = pd.qcut(b[f], 3, labels=["low", "mid", "high"])
        print(f"  {f}: " + " ".join(f"{k} {v:+.3f}" for k, v in b.groupby(q, observed=True).X4.mean().items()))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
