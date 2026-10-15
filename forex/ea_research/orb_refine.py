"""ORB-REFINE exactly as in PREREG_ORB_REFINE.md: the card's gold London and Nasdaq New York breakouts, six refinements.
   python -m forex.ea_research.orb_refine --dry     counts, truncation test, hand check (no P&L of the cells)
   python -m forex.ea_research.orb_refine           real run"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import sim

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H, M = 3600, 60
CFG = {
    "XAUUSD": dict(tz="Europe/London", b0=8 * H, b1=8 * H + 30 * M, until=11 * H, ex=14 * H, half=False, lo=0.0012, hi=0.0036, skip=0.0048),
    "NSDQ": dict(tz="America/New_York", b0=9 * H + 30 * M, b1=10 * H, until=12 * H, ex=15 * H + 30 * M, half=True, lo=0.0017, hi=0.0034, skip=None),
}
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (2022, 2023, 2024, 2025)


def daily_table(D):
    """server days (bars 01:00-22:59 mid): previous-day close, ATR14 and SMA20 known at each day's start."""
    t = D["t"]
    day, sod = t // 86400, t % 86400
    ok = (sod >= H) & (sod < 23 * H)
    df = pd.DataFrame({"day": day[ok], "h": D["mh"][ok], "l": D["ml"][ok], "c": D["mc"][ok]})
    g = df.groupby("day").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), n=("c", "size"))
    g = g[g.n >= 300]
    tr = np.maximum(g.h - g.l, np.maximum((g.h - g.c.shift()).abs(), (g.l - g.c.shift()).abs()))
    g["atr_prev"] = tr.rolling(14).mean().shift(1)
    g["sma_prev"] = g.c.rolling(20).mean().shift(1)
    g["c_prev"] = g.c.shift(1)
    return g


def trades(sym, end=END):
    c = CFG[sym]
    D = load(sym, end)
    t = D["t"]
    lc = local_clock(t, c["tz"])
    dt = daily_table(D)
    days = np.unique(lc // 86400)
    rows = []
    for n_, d in enumerate(days):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + c["b0"]), np.searchsorted(lc, base + c["b1"])
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or lc[i0] > base + c["b0"] + 5 * M:
            continue
        sday = t[i0] // 86400
        if sday not in dt.index or not np.isfinite(dt.at[sday, "atr_prev"]):
            continue
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        box = Hb - Lb
        px = (D["bo"][i1] + D["ao"][i1]) / 2
        if not box > 0 or (c["skip"] and box > c["skip"] * px):
            continue
        dist = float(np.clip(box / 2 if c["half"] else box, c["lo"] * px, c["hi"] * px))
        w1 = np.searchsorted(lc, base + c["until"])
        ke = np.searchsorted(lc, base + c["ex"])
        if ke >= len(t) or lc[ke] // 86400 != d:
            ke -= 1
        if w1 <= i1 or ke <= i1:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if ku is None and kd is None or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        if k >= ke:
            continue
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        r = sim(D, k, side, e, e - side * dist, e + side * 2 * dist, ke)
        sp = D["ao"][k] - D["bo"][k]
        ef = (Hb - sp) if side > 0 else (Lb + sp)                      # fade: opposite quote at the trigger level
        rf = sim(D, k, -side, ef, ef + side * dist, ef - side * 2 * dist, ke)
        if r is None:
            continue
        mid = (D["bo"] + D["ao"]) / 2
        if sym == "XAUUSD":
            j0 = np.searchsorted(lc, base)                              # 00:00 London
            ov = np.sign(mid[i0] - mid[j0]) if j0 < i0 else 0.0
        else:
            prev = days[n_ - 1] if n_ > 0 else None
            j0 = np.searchsorted(lc, prev * 86400 + 16 * H) - 1 if prev is not None else -1
            ov = np.sign(mid[i0] - mid[j0]) if 0 <= j0 < i0 else 0.0
        rows.append(dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), side=side, R=r[0], gR=r[1],
                         Rf=rf[0] if rf is not None else np.nan, gRf=rf[1] if rf is not None else np.nan,
                         trend=np.sign(dt.at[sday, "c_prev"] - dt.at[sday, "sma_prev"]), ov=ov,
                         box_rel=box / dt.at[sday, "atr_prev"], fast=(lc[k] - (base + c["b1"])) <= 15 * M,
                         t_entry=int(t[k]), e=e, dist=dist, Hb=Hb, Lb=Lb))
    df = pd.DataFrame(rows)
    df["small"] = df.box_rel < df.box_rel.rolling(250, min_periods=50).median().shift(1)
    df["mom"] = df.R.rolling(20).mean().shift(1)
    return df


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else 0.0


def cells(df):
    out = {}
    out["A_trend"] = df[df.side == df.trend].assign(Rc=lambda x: x.R)
    out["B_small"] = df[df.small].assign(Rc=lambda x: x.R)
    out["C_overnight"] = df[df.side == df.ov].assign(Rc=lambda x: x.R)
    out["D_fast"] = df[df.fast].assign(Rc=lambda x: x.R)
    out["E_regime_skip"] = df[df.mom > 0].assign(Rc=lambda x: x.R)
    f = df[df.mom.notna() & df.Rf.notna()].copy()
    f["Rc"] = np.where(f.mom > 0, f.R, f.Rf)
    out["F_regime_flip"] = f
    return out


def per(x, a, b):
    return x[(x.day >= a) & (x.day <= b)]


def dry():
    for s in CFG:
        df = trades(s)
        df = df[df.day >= DEV[0]]
        print(f"{s}: base trades DEV {len(per(df, *DEV))} VAL {len(per(df, *VAL))} | long share {np.mean(df.side > 0):.2f} | fast share {df.fast.mean():.2f} | "
              f"median stop {np.median(df.dist / df.e) * 100:.3f}% of price | cells: " + ", ".join(f"{k} {len(per(v, *DEV))}" for k, v in cells(df).items()))
        cut = pd.Timestamp("2024-03-13 12:00").timestamp()
        full, part = trades(s), trades(s, cut)
        f, p = full[full.t_entry < cut - 86400].reset_index(drop=True), part[part.t_entry < cut - 86400].reset_index(drop=True)
        same = len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all() and np.allclose(f.box_rel, p.box_rel)
        print(f"   truncation test: {'PASS' if same else 'FAIL'}")
        x = df[df.day == "2024-06-12"]
        if len(x):
            x = x.iloc[0]
            print(f"   hand check {s} 2024-06-12: box {x.Lb:.2f}-{x.Hb:.2f}, side {x.side:+d}, fill {x.e:.2f} at {pd.Timestamp(x.t_entry, unit='s')} server, stop dist {x.dist:.2f}, trend {x.trend:+.0f}, overnight {x.ov:+.0f}, fast {x.fast}")


def run():
    rng = np.random.default_rng(7)
    res = []
    for s in CFG:
        df = trades(s)
        df = df[df.day >= DEV[0]]
        df.to_parquet(f"D:/finance/si_ledgers/ORB_REFINE_{s}.parquet")
        b = per(df, *DEV)
        print(f"\n=== {s} base card trade (all days): ", end="")
        for y in YEARS:
            x = df[df.day.dt.year == y]
            print(f"{y} n{len(x)} {x.R.mean():+.3f}R win {np.mean(x.R > 0):.0%} | ", end="")
        print(f"\n    DEV {b.R.mean():+.3f}R (gross {b.gR.mean():+.3f}) t {tstat(b.R):+.2f} | VAL {per(df, *VAL).R.mean():+.3f}R t {tstat(per(df, *VAL).R):+.2f}")
        for name, cdf in cells(df).items():
            dv, vl = per(cdf, *DEV), per(cdf, *VAL)
            if name == "F_regime_flip":
                bb = b[b.mom.notna() & b.Rf.notna()]
                nflip = int((per(cdf, *DEV).mom <= 0).sum())
                sims = []
                for _ in range(1000):
                    idx = rng.choice(len(bb), nflip, replace=False)
                    v = bb.R.to_numpy().copy(); v[idx] = bb.Rf.to_numpy()[idx]; sims.append(v.mean())
            else:
                sims = [b.R.to_numpy()[rng.choice(len(b), len(dv), replace=False)].mean() for _ in range(1000)] if len(dv) <= len(b) else [np.nan]
            p95 = np.nanpercentile(sims, 95)
            yrs = [cdf[cdf.day.dt.year == y].Rc.mean() for y in YEARS]
            g = [dv.Rc.mean() >= 0.10 and tstat(dv.Rc) >= 2.65, vl.Rc.mean() > 0 and tstat(vl.Rc) >= 1.65, sum(v > 0 for v in yrs) >= 3, dv.Rc.mean() > p95, len(dv) >= 100]
            res.append(dict(mkt=s, cell=name, nD=len(dv), mD=dv.Rc.mean(), tD=tstat(dv.Rc), nV=len(vl), mV=vl.Rc.mean(), tV=tstat(vl.Rc),
                            y22=yrs[0], y23=yrs[1], y24=yrs[2], y25=yrs[3], placebo95=p95, gates="".join("Y" if v else "n" for v in g), PASS=all(g)))
    R = pd.DataFrame(res)
    R.to_csv("D:/finance/si_ledgers/ORB_REFINE_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n" + R.round(3).to_string(index=False))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
