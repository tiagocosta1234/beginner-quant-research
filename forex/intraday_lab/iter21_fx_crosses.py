"""Iteration 21 (pre-registered in lab/PREREG.md): mean reversion of the 15 synthetic FX crosses of the 6 USD pairs.   python -m forex.intraday_lab.iter21_fx_crosses"""
from __future__ import annotations

from itertools import combinations, product

import numpy as np
import pandas as pd

from forex.intraday_lab.iter16_fx_xsection import COMM, SGN, load
from forex.intraday_lab.lab import FX


def main():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX]); l55 = np.log(P55.values) * sg; l00 = np.log(P00.values) * sg; spv = SP.values; idx = P00.index; n = len(idx)
    ph = np.where(idx < pd.Timestamp("2024-01-01"), 0, np.where(idx < pd.Timestamp("2025-01-01"), 1, 2)); crosses = list(combinations(range(6), 2)); rows = []; hits = []
    for W, th, H in product((24, 72, 168), (2.0, 3.0), (12, 48)):
        per = {c: {0: [], 1: [], 2: []} for c in crosses}
        for (i, j) in crosses:
            x55 = pd.Series(l55[:, i] - l55[:, j]); mu = x55.rolling(W, min_periods=W // 2).mean(); sd = x55.rolling(W, min_periods=W // 2).std(); z = ((x55 - mu) / sd).values; x00 = l00[:, i] - l00[:, j]
            t = W + 1
            while t < n - H:
                if np.isnan(z[t]) or np.isnan(x00[t]) or np.isnan(x00[t + H]) or np.isnan(spv[t, i]) or np.isnan(spv[t + H, i]) or np.isnan(spv[t, j]) or np.isnan(spv[t + H, j]) or abs(z[t]) < th or spv[t, i] > 3e-4 or spv[t, j] > 3e-4:
                    t += 1; continue
                pos = -np.sign(z[t]); ret = pos * (x00[t + H] - x00[t]); cost = 0.5 * (spv[t, i] + spv[t, j] + spv[t + H, i] + spv[t + H, j]) + 4 * COMM
                per[(i, j)][ph[t]].append(ret - cost); t += H
        r = dict(W=W, theta=th, H=H)
        for p, nm in enumerate(("dev", "val", "hold")):
            allv = np.concatenate([np.array(per[c][p]) for c in crosses]) if any(len(per[c][p]) for c in crosses) else np.array([])
            r[f"n_{nm}"] = len(allv); r[f"net_{nm}"] = allv.mean() * 1e4 if len(allv) else np.nan
            r[f"pos_{nm}"] = int(sum(1 for c in crosses if len(per[c][p]) >= 5 and np.mean(per[c][p]) > 0))
        dv = np.concatenate([np.array(per[c][p]) for c in crosses for p in (0, 1)]); r["t_devval"] = float(dv.mean() / (dv.std(ddof=1) / np.sqrt(len(dv)))) if len(dv) > 30 else np.nan
        rows.append(r)
        if r["net_dev"] > 0 and r["net_val"] > 0 and r["t_devval"] >= 3.0 and r["pos_dev"] >= 10 and r["pos_val"] >= 10:
            hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"data\scratch\lab\iter21_raw.csv", index=False); print(T.round(2).to_string(index=False)); print(f"\nPRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")
    for h in hits:
        print(h)


if __name__ == "__main__":
    main()
