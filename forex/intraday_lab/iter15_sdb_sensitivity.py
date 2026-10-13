"""Iteration 15 (pre-registered in lab/PREREG.md): parameter sensitivity of the Stochastic Daily Breakout on gold - plateau or spike?   python -m forex.intraday_lab.iter15_sdb_sensitivity"""
from __future__ import annotations

from itertools import product
from multiprocessing import Pool

import numpy as np
import pandas as pd

from forex.intraday_lab import sdb

_M1 = None


def init():
    global _M1
    _M1 = sdb.load_m1("XAUUSD")


def one(par):
    K, S, B, E = par
    T = sdb.simulate("XAUUSD", _M1, K=K, S=S, bp=B, expiry=E)
    if not len(T):
        return dict(K=K, S=S, B=B, E=E, n=0)
    ph = np.where(T.year <= 2023, "dev", np.where(T.year == 2024, "val", "hold"))
    r = dict(K=K, S=S, B=B, E=E, n=len(T), mean=T.R.mean(), t=T.R.mean() / (T.R.std(ddof=1) / np.sqrt(len(T))))
    for p in ("dev", "val", "hold"):
        x = T.R[ph == p]; r[p] = x.mean() if len(x) else np.nan; r[f"n_{p}"] = len(x)
    return r


def main():
    grid = list(product((15, 23, 31), (5, 7, 9), (7, 9, 12), (6, 9, 12)))
    with Pool(4, initializer=init) as p:
        D = pd.DataFrame(p.map(one, grid))
    D.to_csv(r"D:\finance\scratch\lab\iter15_raw.csv", index=False)
    a = D[(D.K == 23) & (D.S == 7) & (D.B == 9) & (D.E == 9)].iloc[0]
    print(f"author's set: n {int(a.n)}, mean R {a['mean']:.3f} (t {a.t:.2f}); DEV {a.dev:.3f} VAL {a.val:.3f} HOLD {a.hold:.3f}")
    print(f"\n81 combinations: share with mean R > 0: overall {(D['mean'] > 0).mean():.0%}, DEV {(D.dev > 0).mean():.0%}, VAL {(D.val > 0).mean():.0%}, HOLD {(D.hold > 0).mean():.0%}, all three {((D.dev > 0) & (D.val > 0) & (D.hold > 0)).mean():.0%}")
    D["rank"] = D["mean"].rank(ascending=False)
    print(f"author's overall rank: {int(D.loc[a.name, 'rank'])} of 81 (top {D.loc[a.name, 'rank'] / 81:.0%}); median mean R {D['mean'].median():.3f}, best {D['mean'].max():.3f}, worst {D['mean'].min():.3f}; median trades {D.n.median():.0f}")
    print("\nmean R by single parameter (average over the others):")
    for c in ("K", "S", "B", "E"):
        print(c, D.groupby(c)["mean"].mean().round(3).to_dict())
    print("\nTop 5 / bottom 3 combinations:"); print(D.sort_values("mean", ascending=False).head(5)[["K", "S", "B", "E", "n", "mean", "t", "dev", "val", "hold"]].round(3).to_string(index=False)); print(D.sort_values("mean").head(3)[["K", "S", "B", "E", "n", "mean", "t", "dev", "val", "hold"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
