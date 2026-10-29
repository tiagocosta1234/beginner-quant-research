"""TRB-LUCK exactly as in PREREG_TRB_LUCK.md: is each year's hindsight-best breakout variant more than luck?
   python -m forex.ea_research.trb_luck --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research import trb
from forex.ea_research.trb_best import CACHE26

YEARS = (2022, 2023, 2024, 2025, 2026)
B = 500


def market(args):
    sym, nboot = args
    z = np.load(CACHE26 / f"{sym}.npz")
    days = pd.to_datetime(z["days"], unit="s")
    R = z["R"].reshape(len(days), -1).astype(np.float64)
    mask = ~np.isnan(R)
    Rf = np.where(mask, R, 0.0)
    all_mean = Rf.sum(0) / np.maximum(mask.sum(0), 1)
    out = {}
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 30)
    for y in YEARS:
        sel = days.year == y
        X, Mk = Rf[sel], mask[sel].astype(np.float64)
        n = Mk.sum(0)
        thr = 100 if y < 2026 else 75
        ok = n >= thr
        if not ok.any():
            continue
        mean_y = X.sum(0) / np.maximum(n, 1)
        obs = mean_y[ok].max()
        grand = X.sum() / Mk.sum()
        X1 = (X - mean_y * Mk) + grand * Mk
        X2 = (X - mean_y * Mk) + all_mean * Mk
        nd = X.shape[0]
        null1, null2 = np.empty(nboot), np.empty(nboot)
        for b in range(nboot):
            w = np.bincount(rng.integers(0, nd, nd), minlength=nd).astype(np.float64)
            cnt = w @ Mk
            good = cnt >= thr
            if not good.any():
                null1[b] = null2[b] = np.nan
                continue
            null1[b] = ((w @ X1)[good] / cnt[good]).max()
            null2[b] = ((w @ X2)[good] / cnt[good]).max()
        out[y] = (obs, null1, null2, grand)
    return sym, out


def main(dry):
    nboot = 5 if dry else B
    with ProcessPoolExecutor(8) as ex:
        res = dict(ex.map(market, [(s, nboot) for s in trb.SYMS]))
    rows = []
    for y in YEARS:
        obs = [v[y][0] for v in res.values() if y in v]
        n1 = np.nanmean(np.array([v[y][1] for v in res.values() if y in v]), axis=0)
        n2 = np.nanmean(np.array([v[y][2] for v in res.values() if y in v]), axis=0)
        grand = np.mean([v[y][3] for v in res.values() if y in v])
        o = float(np.mean(obs))
        rows.append(dict(year=y, markets=len(obs), observed_prize=o, grand_mean=grand, N1_median=np.median(n1), N1_p95=np.percentile(n1, 95), p_N1=np.mean(n1 >= o),
                         N2_median=np.median(n2), N2_p95=np.percentile(n2, 95), p_N2=np.mean(n2 >= o)))
    T = pd.DataFrame(rows)
    print(T.round(3).to_string(index=False))
    if not dry:
        T.to_csv("data/si_ledgers/TRB_LUCK.csv", index=False)
        inside = int((T.p_N2 > 0.05).sum())
        print(f"years with the prize inside N2 (p > 0.05): {inside} of {len(T)} -> " + ("LUCK explains the yearly best breakout" if inside >= 4 else ("evidence of year-specific breakout types" if inside <= 1 else "mixed")))


if __name__ == "__main__":
    main("--dry" in sys.argv)
