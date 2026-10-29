"""Iteration 20 (pre-registered in lab/PREREG.md): filters for the Stochastic Daily Breakout on gold across the 81-neighbour grid.   python -m forex.intraday_lab.iter20_sdb_filters"""
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
        return pd.DataFrame()
    T["K"], T["S"], T["B"], T["E"] = K, S, B, E
    return T


FILTERS = {"skip Mon": lambda T: T.dow != 0, "skip Tue": lambda T: T.dow != 1, "skip Wed": lambda T: T.dow != 2, "skip Thu": lambda T: T.dow != 3, "skip Fri": lambda T: T.dow != 4,
           "long only": lambda T: T.side > 0, "short only": lambda T: T.side < 0, "hour 10-13 only": lambda T: T.hr.between(10, 13), "hour outside 10-13": lambda T: ~T.hr.between(10, 13),
           "skip first 2 weeks of the month": lambda T: T.dom > 14}


def main():
    grid = list(product((15, 23, 31), (5, 7, 9), (7, 9, 12), (6, 9, 12)))
    with Pool(3, initializer=init) as p:
        A = pd.concat(p.map(one, grid), ignore_index=True)
    ts = pd.to_datetime(A.t_entry, unit="s"); A["dow"] = ts.dt.dayofweek; A["hr"] = ts.dt.hour; A["dom"] = ts.dt.day
    A["ph"] = np.where(A.year <= 2023, "dev", np.where(A.year == 2024, "val", "hold")); A.to_parquet(r"data\scratch\lab\iter20_trades.parquet")
    au = A[(A.K == 23) & (A.S == 7) & (A.B == 9) & (A.E == 9)]; rows = []; hits = []
    for name, f in FILTERS.items():
        r = dict(filter=name); good = {}
        for ph in ("dev", "val", "hold"):
            ok = []
            for key, g in A[A.ph == ph].groupby(["K", "S", "B", "E"]):
                m = f(g); k, e = g.R[m], g.R[~m]
                if len(k) >= 5 and len(e) >= 5:
                    ok.append(k.mean() > e.mean())
            good[ph] = float(np.mean(ok)) if ok else np.nan; r[f"share_{ph}"] = good[ph]
        m = f(au); k, e = au.R[m], au.R[~m]; r["kept_share_trades"] = float(m.mean()); r["author_kept"] = float(k.mean()); r["author_excl"] = float(e.mean())
        r["author_t"] = float((k.mean() - e.mean()) / np.sqrt(k.var(ddof=1) / len(k) + e.var(ddof=1) / len(e))) if len(k) > 5 and len(e) > 5 else np.nan
        rows.append(r)
        if all(good[ph] >= 0.7 for ph in good) and r["author_t"] >= 2.0 and r["kept_share_trades"] >= 0.6:
            hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"data\scratch\lab\iter20_raw.csv", index=False); print(T.round(3).to_string(index=False)); print(f"\nPRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")
    for h in hits:
        print(h)


if __name__ == "__main__":
    main()
