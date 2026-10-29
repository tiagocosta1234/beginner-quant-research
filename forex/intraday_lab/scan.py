"""Edge scanner (iteration 2, pre-registered in lab/PREREG.md): gross predictive content of simple features on forward returns at 5 / 15 minutes, 11 symbols, DEV / VAL / HOLD.
  python -m forex.intraday_lab.scan 5 15
"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import ALL, Bars, commission_price

OUT = Path(r"data\scratch\lab")
HS = (3, 12, 48)


def features(b: Bars):
    c = b.mid; atr = b.atr(14); s = pd.Series(c)
    f = {}
    for k in (1, 3, 12, 48):
        f[f"ret{k}"] = ((s - s.shift(k)) / pd.Series(atr)).values
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min()
    f["rngpos"] = ((s - ll) / (hh - ll)).values
    return f, atr


def one(args):
    sym, tf = args
    b = Bars(sym, tf); f, atr = features(b)
    ph = {p: b.slice_idx(p) for p in ("dev", "val", "hold")}
    rows = []
    for h in HS:
        fwd = np.full(b.n, np.nan); ok = np.arange(b.n - h)
        fwd[ok] = (b.mid[ok + h] - b.mid[ok]) / atr[ok]
        gap = np.full(b.n, True); gap[ok] = (b.t[ok + h] - b.t[ok]) <= h * tf * 60 * 3; fwd[~gap] = np.nan
        # cost in ATR units for one round trip at the signal bar: spread + commission
        cost = ((b.ao - b.bo) + np.array([commission_price(sym, p) for p in (b.mid[0], )])[0] * 0 + commission_price(sym, float(np.nanmedian(b.mid)))) / atr
        for name, v in f.items():
            lo, hi = np.nanpercentile(v[ph["dev"]], [10, 90])
            for bucket, mask in (("low", v <= lo), ("high", v >= hi)):
                for p, ix in ph.items():
                    sel = ix[mask[ix] & np.isfinite(fwd[ix])][:: max(1, h)]
                    rows.append(dict(sym=sym, tf=tf, feat=name, bucket=bucket, h=h, phase=p, n=len(sel), mean=float(np.mean(fwd[sel])) if len(sel) else np.nan, sd=float(np.std(fwd[sel], ddof=1)) if len(sel) > 2 else np.nan, cost=float(np.nanmean(cost[sel])) if len(sel) else np.nan))
        hr = b.hour
        for hour in range(24):
            mask = hr == hour
            for p, ix in ph.items():
                sel = ix[mask[ix] & np.isfinite(fwd[ix])][:: max(1, h)]
                rows.append(dict(sym=sym, tf=tf, feat="hour", bucket=str(hour), h=h, phase=p, n=len(sel), mean=float(np.mean(fwd[sel])) if len(sel) else np.nan, sd=float(np.std(fwd[sel], ddof=1)) if len(sel) > 2 else np.nan, cost=float(np.nanmean(cost[sel])) if len(sel) else np.nan))
    return rows


def main(tfs):
    jobs = [(s, tf) for tf in tfs for s in ALL]
    with Pool(4) as p:
        res = p.map(one, jobs)
    pd.DataFrame([r for x in res for r in x]).to_csv(OUT / "scan_raw.csv", index=False)
    print("scan rows", sum(len(x) for x in res), flush=True)


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]])
