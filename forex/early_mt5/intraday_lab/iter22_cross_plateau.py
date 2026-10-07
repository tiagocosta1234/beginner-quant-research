"""Iteration 22 (pre-registered in lab/PREREG.md): plateau test of the synthetic-cross fade (W 168 h, 3 sigma, 48 h hold) with a daily-portfolio Sharpe.   python -m mt5broker.intraday_lab.iter22_cross_plateau"""
from __future__ import annotations

from itertools import combinations, product

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter16_fx_xsection import COMM, SGN, load
from mt5broker.intraday_lab.lab import FX


def trades(l55, l00, spv, idx, W, th, H):
    n = len(idx); out = []
    for (i, j) in combinations(range(6), 2):
        x55 = pd.Series(l55[:, i] - l55[:, j]); mu = x55.rolling(W, min_periods=W // 2).mean(); sd = x55.rolling(W, min_periods=W // 2).std(); z = ((x55 - mu) / sd).values; x00 = l00[:, i] - l00[:, j]
        t = W + 1
        while t < n - H:
            if np.isnan(z[t]) or np.isnan(x00[t]) or np.isnan(x00[t + H]) or np.isnan(spv[[t, t + H]][:, [i, j]]).any() or abs(z[t]) < th or spv[t, i] > 3e-4 or spv[t, j] > 3e-4:
                t += 1; continue
            pos = -np.sign(z[t]); gross = pos * (x00[t + H] - x00[t]); cost = 0.5 * (spv[t, i] + spv[t, j] + spv[t + H, i] + spv[t + H, j]) + 4 * COMM
            out.append((idx[t + H].normalize(), gross - cost, gross, cost, (i, j))); t += H
    return out


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 40 and x.std(ddof=1) > 0 else np.nan


def main():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX]); l55 = np.log(P55.values) * sg; l00 = np.log(P00.values) * sg; spv = SP.values; idx = P00.index
    days = pd.bdate_range("2021-10-01", "2026-10-02"); rows = []
    for W, th, H in product((120, 168, 240), (2.5, 3.0, 3.5), (36, 48, 72)):
        T = trades(l55, l00, spv, idx, W, th, H); df = pd.DataFrame(T, columns=["d", "net", "gross", "cost", "c"])
        day = df.groupby("d").net.sum().reindex(days).fillna(0.0); flip = (-df.gross - df.cost).groupby(df.d).sum().reindex(days).fillna(0.0)
        r = dict(W=W, theta=th, H=H, trades=len(df), gross_bp=df.gross.mean() * 1e4, cost_bp=df.cost.mean() * 1e4)
        for nm, a, b in (("dev", "2021-10-01", "2023-12-31"), ("val", "2024-01-01", "2024-12-31"), ("hold_CONTAMINATED", "2025-01-01", "2026-10-02")):
            r[f"sh_{nm}"] = sharpe(day.loc[a:b]); r[f"flip_{nm}"] = sharpe(flip.loc[a:b])
        rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter22_raw.csv", index=False); print(T.round(2).to_string(index=False))
    c = T[(T.W == 168) & (T.theta == 3.0) & (T.H == 48)].iloc[0]
    print(f"\nshare of 27 cells with Sharpe > 0: DEV {(T.sh_dev > 0).mean():.0%}, VAL {(T.sh_val > 0).mean():.0%}, both {((T.sh_dev > 0) & (T.sh_val > 0)).mean():.0%}; centre DEV {c.sh_dev:.2f} VAL {c.sh_val:.2f}")
    hit = ((T.sh_dev > 0).mean() >= 0.7) and ((T.sh_val > 0).mean() >= 0.7) and c.sh_dev >= 0.5 and c.sh_val >= 0.5
    print("PRE-REGISTERED PLATEAU HIT:", hit)


if __name__ == "__main__":
    main()
