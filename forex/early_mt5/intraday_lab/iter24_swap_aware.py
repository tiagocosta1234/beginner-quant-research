"""Iteration 24 (pre-registered in lab/PREREG.md): swap-aware selection of the cross fade.   python -m mt5broker.intraday_lab.iter24_swap_aware"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter16_fx_xsection import SGN, load
from mt5broker.intraday_lab.iter23_cross_swap_rules import CELLS, run_cell, sharpe, swap_bp_table
from mt5broker.intraday_lab.lab import FX


def main():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX]); l55 = np.log(P55.values) * sg; l00 = np.log(P00.values) * sg; spv = SP.values; idx = P00.index; n = len(idx)
    swap_tab = swap_bp_table(np.nanmedian(P00.values, axis=0)); x_ff = {(i, j): pd.Series(l00[:, i] - l00[:, j]).ffill().values for i, j in combinations(range(6), 2)}
    days = pd.bdate_range("2021-10-01", "2026-09-30"); all_trades = None; hits = []
    for thr in (None, 0.0, -2.0, -4.0):
        series, ntr = [], 0
        for W, th, H in CELLS:
            T = run_cell(l55, l00, x_ff, spv, idx, W, th, H, swap_tab, np.zeros(n), thr); df = pd.DataFrame(T, columns=["d", "ns", "sw"]); ntr += len(df)
            series.append(df.groupby("d").sw.sum().reindex(days).fillna(0.0))
        es = sum(series) / len(CELLS)
        if thr is None:
            all_trades = ntr
        r = dict(thr=thr, trades=ntr, kept=ntr / all_trades, dev=sharpe(es.loc["2021-10-01":"2023-12-31"]), val=sharpe(es.loc["2024-01-01":"2024-12-31"]), hold_CONTAMINATED=sharpe(es.loc["2025-01-01":"2026-09-30"]))
        ys = {y: sharpe(es.loc[f"{y}-01-01":f"{y}-12-31"]) for y in (2022, 2023, 2024, 2025, 2026)}; r["years"] = {k: round(v, 2) for k, v in ys.items()}
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
        if thr is not None and r["dev"] >= 0.5 and r["val"] >= 0.5 and sum(1 for v in ys.values() if v > 0) >= 4 and r["kept"] >= 0.25:
            hits.append(r)
    print(f"\nPRE-REGISTERED HITS (k = 3): {len(hits)}")


if __name__ == "__main__":
    main()
