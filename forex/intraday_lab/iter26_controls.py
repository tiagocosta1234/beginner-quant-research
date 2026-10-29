"""Iteration 26 (pre-registered in lab/PREREG.md): carry-only control, random-direction placebo and leave-one-currency-out for the swap-aware cross fade.   python -m forex.intraday_lab.iter26_controls"""
from __future__ import annotations

from itertools import combinations
from multiprocessing import Pool

import numpy as np
import pandas as pd

from forex.intraday_lab.iter16_fx_xsection import COMM, SGN, load
from forex.intraday_lab.iter23_cross_swap_rules import CELLS, nights, sharpe, swap_bp_table
from forex.intraday_lab.lab import FX

G = {}


def init():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX])
    G.update(l55=np.log(P55.values) * sg, l00=np.log(P00.values) * sg, spv=SP.values, idx=P00.index, swap_tab=swap_bp_table(np.nanmedian(P00.values, axis=0)))
    G["xs"] = {(i, j): pd.Series(G["l00"][:, i] - G["l00"][:, j]).ffill().values for i, j in combinations(range(6), 2)}; G["days"] = pd.bdate_range("2021-10-01", "2026-09-30")


def cell(W, th, H, thr, mode, seed, drop):
    l55, l00, spv, idx, st = G["l55"], G["l00"], G["spv"], G["idx"], G["swap_tab"]; n = len(idx); rng = np.random.default_rng(seed); out = []
    for (i, j) in combinations(range(6), 2):
        if drop is not None and drop in (i, j):
            continue
        x55 = pd.Series(l55[:, i] - l55[:, j]); mu = x55.rolling(W, min_periods=W // 2).mean(); sd = x55.rolling(W, min_periods=W // 2).std(); z = ((x55 - mu) / sd).values; x00 = l00[:, i] - l00[:, j]
        t = W + 1
        while t < n - H:
            if np.isnan(z[t]) or np.isnan(x00[t]) or np.isnan(x00[t + H]) or np.isnan(spv[[t, t + H]][:, [i, j]]).any() or abs(z[t]) < th or spv[t, i] > 3e-4 or spv[t, j] > 3e-4:
                t += 1; continue
            nn = nights(idx[t], idx[t + H]); swp = {}
            for p in (1, -1):
                swp[p] = nn * (st[(i, SGN[FX[i]] * p)] + st[(j, SGN[FX[j]] * (-p))])
            if mode == "fade":
                pos = -int(np.sign(z[t]))
            elif mode == "carry":
                pos = 1 if swp[1] >= swp[-1] else -1
            else:
                pos = int(rng.choice([1, -1]))
            if swp[pos] < thr:
                t += 1; continue
            gross = pos * (x00[t + H] - x00[t]); cost = 0.5 * (spv[t, i] + spv[t, j] + spv[t + H, i] + spv[t + H, j]) + 4 * COMM
            out.append((idx[t + H].normalize(), gross - cost + swp[pos] * 1e-4)); t += H
    return out


def ensemble(args):
    thr, mode, seed, drop = args
    ser = []
    for W, th, H in CELLS:
        df = pd.DataFrame(cell(W, th, H, thr, mode, seed, drop), columns=["d", "net"]); ser.append(df.groupby("d").net.sum().reindex(G["days"]).fillna(0.0))
    es = sum(ser) / len(CELLS)
    return dict(thr=thr, mode=mode, seed=seed, drop=drop, dev=sharpe(es.loc["2021-10-01":"2023-12-31"]), val=sharpe(es.loc["2024-01-01":"2024-12-31"]), hold_C=sharpe(es.loc["2025-01-01":"2026-09-30"]))


def main():
    jobs = []
    for thr in (-2.0, -4.0):
        jobs += [(thr, "fade", 0, None), (thr, "carry", 0, None)] + [(thr, "random", s, None) for s in range(10)] + [(thr, "fade", 0, k) for k in range(6)]
    with Pool(3, initializer=init) as p:
        R = pd.DataFrame(p.map(ensemble, jobs, chunksize=1))
    R.to_csv(r"data\scratch\lab\iter26_raw.csv", index=False); print(R.round(2).to_string(index=False))
    for thr in (-2.0, -4.0):
        f = R[(R.thr == thr) & (R["mode"] == "fade") & R["drop"].isna()].iloc[0]; c = R[(R.thr == thr) & (R["mode"] == "carry")].iloc[0]; pl = R[(R.thr == thr) & (R["mode"] == "random")]
        lo = R[(R.thr == thr) & (R["mode"] == "fade") & R["drop"].notna()]
        ga = c.dev < 0.5 * f.dev and c.val < 0.5 * f.val; gb = f.dev > pl.dev.max() and f.val > pl.val.max(); gc = int(((lo.dev >= 0.5) & (lo.val >= 0.5)).sum()) >= 5
        print(f"\nthr {thr}: fade DEV {f.dev:.2f} VAL {f.val:.2f} | carry-only DEV {c.dev:.2f} VAL {c.val:.2f} -> gate a {ga} | placebo max DEV {pl.dev.max():.2f} VAL {pl.val.max():.2f} mean {pl.dev.mean():.2f}/{pl.val.mean():.2f} -> gate b {gb} | leave-one-out ok {int(((lo.dev >= 0.5) & (lo.val >= 0.5)).sum())}/6 -> gate c {gc}")


if __name__ == "__main__":
    main()
