"""PRESAMPLE exactly as in PREREG_PRESAMPLE.md: 2020-01..2021-11 Dukascopy check of L1 (USDJPY London session breakout, hold to 17:00)
and L2 (the card's Nasdaq leg, trend direction only).   python -m forex.ea_research.presample"""
import zlib

import numpy as np
import pandas as pd

from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import sim

H, M = 3600, 60


def mt5_floor(sym, tz, a_h, b_h):
    """MT5 broker's median spread for the market during the session in 2022 (cost floor)."""
    D = load(sym, pd.Timestamp("2023-01-01").timestamp())
    t = pd.to_datetime(D["t"], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert(tz)
    h = t.hour + t.minute / 60
    m = (h >= a_h) & (h < b_h) & (D["t"] >= pd.Timestamp("2022-01-01").timestamp())
    return float(np.median((D["ao"] - D["bo"])[m]))


def load_duka(name, tz, floor):
    d = pd.read_parquet(f"data/data_histdata/{name}.parquet").sort_values("t_utc").drop_duplicates("t_utc")
    d = d[(d.t_utc >= pd.Timestamp("2020-01-02").timestamp()) & (d.t_utc < pd.Timestamp("2021-12-01").timestamp())]   # amendment A2: HistData, prereg window
    D = {k: d[k].to_numpy(float) for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}
    sp = np.maximum(D["ao"] - D["bo"], floor)                    # floor the ask at bid + MT5 broker's median spread
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        D[a] = np.maximum(D[a], D[b] + sp)
    D["t"] = d.t_utc.to_numpy(np.int64)
    loc = pd.to_datetime(D["t"], unit="s").tz_localize("UTC").tz_convert(tz).tz_localize(None)
    D["lc"] = (loc.values.astype("datetime64[s]").astype(np.int64))
    return D


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def l1_usdjpy(D, rng):
    lc, rows = D["lc"], []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + 8 * H), np.searchsorted(lc, base + 8 * H + 30 * M)
        w1, xe = np.searchsorted(lc, base + 11 * H), np.searchsorted(lc, base + 17 * H)
        if xe >= len(lc) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30:
            continue
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= xe or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, xe, side, e, R)
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        xc = exits(D, kc, xe, sc, ec, R)
        if x:
            rows.append(dict(day=pd.Timestamp(base, unit="s"), side=side, R=x[3], C=xc[3] if xc else np.nan))
    return pd.DataFrame(rows)


def l2_nasdaq(D, rng):
    lc = D["lc"]
    mid_c = (D["bc"] + D["ac"]) / 2
    days = np.unique(lc // 86400)
    closes = {}
    for d in days:                                                # NY close (last bar before 16:00 NY)
        j = np.searchsorted(lc, d * 86400 + 16 * H) - 1
        if j >= 0 and lc[j] // 86400 == d and lc[j] >= d * 86400 + 15 * H:
            closes[d] = mid_c[j]
    cs = pd.Series(closes).sort_index()
    trend = np.sign(cs - cs.rolling(20).mean()).shift(1)          # previous close vs its SMA20, known at the open
    rows = []
    for d in days:
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + 9 * H + 30 * M), np.searchsorted(lc, base + 10 * H)
        w1, xe = np.searchsorted(lc, base + 12 * H), np.searchsorted(lc, base + 15 * H + 30 * M)
        if xe >= len(lc) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30:
            continue
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        px = (D["bo"][i1] + D["ao"][i1]) / 2
        dist = float(np.clip((Hb - Lb) / 2, 0.0017 * px, 0.0034 * px))
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        if k >= xe:
            continue
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        r = sim(D, k, side, e, e - side * dist, e + side * 2 * dist, xe)
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        rc = sim(D, kc, sc, ec, ec - sc * dist, ec + sc * 2 * dist, xe)
        x4 = exits(D, k, xe, side, e, abs(e - (Lb if side > 0 else Hb)))
        if r:
            rows.append(dict(day=pd.Timestamp(base, unit="s"), side=side, trend=trend.get(d, np.nan), R=r[0], C=rc[0] if rc else np.nan,
                             X4_box=x4[3] if x4 else np.nan))
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(2020)
    fj = mt5_floor("USDJPY", "Europe/London", 8, 17)
    fn = mt5_floor("NSDQ", "America/New_York", 9.5, 16)
    print(f"MT5 2022 median session spreads used as floors: USDJPY {fj:.4f}, NSDQ {fn:.2f}")
    J = load_duka("USDJPY", "Europe/London", fj)
    N = load_duka("NSXUSD", "America/New_York", fn)
    print("price check: USDJPY median", round(np.median(J["bc"]), 3), "| Nasdaq-100 median", round(np.median(N["bc"]), 1))
    l1 = l1_usdjpy(J, rng); l2all = l2_nasdaq(N, rng)
    l2 = l2all[l2all.side == l2all.trend]
    pd.concat([l1.assign(lead="L1"), l2all.assign(lead="L2all")]).to_parquet("data/si_ledgers/PRESAMPLE.parquet")
    for name, df, col in (("L1 USDJPY London breakout, hold to 17:00", l1, "R"), ("L2 card Nasdaq leg, trend direction only", l2, "R")):
        yrs = {y: round(g[col].mean(), 3) for y, g in df.groupby(df.day.dt.year)}
        g = [df[col].mean() > 0 and tstat(df[col]) >= 1.96, all(v > 0 for v in yrs.values())]
        print(f"{name}: n {len(df)} mean {df[col].mean():+.3f} R (t {tstat(df[col]):+.2f}) | random control {df.C.mean():+.3f} | by year {yrs} | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    print(f"context - Nasdaq card leg without the trend filter: n {len(l2all)} {l2all.R.mean():+.3f} (t {tstat(l2all.R):+.2f}) | Nasdaq session breakout, box stop, hold to close: {l2all.X4_box.mean():+.3f} (t {tstat(l2all.X4_box.dropna()):+.2f})")


if __name__ == "__main__":
    main()
