"""Replay the daily card (gold London leg, Nasdaq NY leg) on the MT5 broker terminal's own M1 bars, 2026-09-01 .. today (read-only)."""
import os
import sys
sys.path.insert(0, r".")
import MetaTrader5 as mt5, numpy as np, pandas as pd
from datetime import datetime
from forex.ea_research.breakouts import local_clock
from forex.ea_research.ict2 import sim
H, M = 3600, 60
mt5.initialize(path=os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe")
def bars(sym):
    r = pd.DataFrame(mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, datetime(2026, 7, 15), datetime(2026, 10, 16)))
    pt = mt5.symbol_info(sym).point
    sp = r.spread * pt
    D = dict(t=r.time.to_numpy(np.int64), bo=r.open.to_numpy(), bh=r.high.to_numpy(), bl=r.low.to_numpy(), bc=r.close.to_numpy())
    D["ao"], D["ah"], D["al"], D["ac"] = D["bo"] + sp.to_numpy(), D["bh"] + sp.to_numpy(), D["bl"] + sp.to_numpy(), D["bc"] + sp.to_numpy()
    return D
G, N = bars("XAUUSD+"), bars("NSDQ+")
mt5.shutdown()
def leg(D, tz, b0, b1, until, ex, half, lo, hi, skip, trendf):
    t = D["t"]; lc = local_clock(t, tz); mid_c = (D["bc"] + D["ac"]) / 2
    days = np.unique(lc // 86400); out = []
    closes = {}
    for d in days:
        j = np.searchsorted(lc, d * 86400 + (16 * H if tz == "America/New_York" else 17 * H)) - 1
        if j >= 0 and lc[j] // 86400 == d: closes[d] = mid_c[j]
    cs = pd.Series(closes).sort_index(); trend = np.sign(cs - cs.rolling(20).mean()).shift(1)
    for d in days:
        if d * 86400 < pd.Timestamp("2026-09-01").timestamp(): continue
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + b0), np.searchsorted(lc, base + b1)
        w1, ke = np.searchsorted(lc, base + until), np.searchsorted(lc, base + ex)
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1: continue
        ke = min(ke, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); box = Hb - Lb
        px = (D["bo"][i1] + D["ao"][i1]) / 2
        day = pd.Timestamp(base, unit="s").date()
        if skip and box > skip * px: out.append((day, "skip (box too wide)", np.nan)); continue
        dist = float(np.clip(box / 2 if half else box, lo * px, hi * px))
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        tr = trend.get(d, np.nan)
        if trendf:
            if tr > 0: kd = None
            elif tr < 0: ku = None
        if (ku is None and kd is None) or (ku is not None and ku == kd): out.append((day, "no fill", np.nan)); continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        r = sim(D, k, side, e, e - side * dist, e + side * 2 * dist, ke)
        out.append((day, ("LONG" if side > 0 else "SHORT"), r[0] if r else np.nan))
    return pd.DataFrame(out, columns=["day", "trade", "R"])
g = leg(G, "Europe/London", 8 * H, 8 * H + 30 * M, 11 * H, 14 * H, False, 0.0012, 0.0036, 0.0048, False)
n_all = leg(N, "America/New_York", 9 * H + 30 * M, 10 * H, 12 * H, 15 * H + 30 * M, True, 0.0017, 0.0034, None, False)
n_tr = leg(N, "America/New_York", 9 * H + 30 * M, 10 * H, 12 * H, 15 * H + 30 * M, True, 0.0017, 0.0034, None, True)
tab = g.merge(n_all, on="day", how="outer", suffixes=("_gold", "_nq")).merge(n_tr.rename(columns={"trade": "trade_nqT", "R": "R_nqT"}), on="day", how="outer")
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 100)
print(tab.round(2).to_string(index=False))
for lab, c in (("gold London", "R_gold"), ("Nasdaq NY (both sides)", "R_nq"), ("Nasdaq NY trend-only", "R_nqT")):
    x = tab[c].dropna()
    print(f"{lab}: {len(x)} trades, total {x.sum():+.2f} R (= ${x.sum() * 1000:+,.0f} at $1,000/trade), wins {int((x > 0).sum())}, losses {int((x <= 0).sum())}")
