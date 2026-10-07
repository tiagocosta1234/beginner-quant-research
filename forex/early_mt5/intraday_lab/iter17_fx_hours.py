"""Iteration 17 (pre-registered in lab/PREREG.md): hour-of-day USD drift, consistent across 6 FX pairs.   python -m mt5broker.intraday_lab.iter17_fx_hours"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter16_fx_xsection import COMM, SGN, load
from mt5broker.intraday_lab.lab import FX, PHASES


def tstat(x):
    x = x[~np.isnan(x)]
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 30 and x.std(ddof=1) > 0 else np.nan


def main():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX]); lp = np.log(P00.values) * sg; spv = SP.values; idx = P00.index; n = len(idx)
    rows = []; hits = []; hr = idx.hour.values; dw = idx.dayofweek.values
    for h in range(24):
        for k in (1, 2, 4):
            t = np.flatnonzero((hr == h) & (dw < 5)); t = t[(t + k) < n]
            f = lp[t + k] - lp[t]; cost = 0.5 * spv[t] + 0.5 * spv[t + k] + 2 * COMM
            ok = ~np.isnan(f).any(axis=1) & ~np.isnan(cost).any(axis=1); t, f, cost = t[ok], f[ok], cost[ok]
            when = idx[t]; ph = np.where(when < pd.Timestamp("2024-01-01"), "dev", np.where(when < pd.Timestamp("2025-01-01"), "val", "hold"))
            if (ph == "dev").sum() < 100:
                continue
            d = np.sign(f[ph == "dev"].mean())
            net = d * f - cost; slot = net.mean(axis=1)
            r = dict(h=h, k=k, d=int(d), n_dev=int((ph == "dev").sum()), net_dev=slot[ph == "dev"].mean() * 1e4, t_dev=tstat(slot[ph == "dev"]), net_val=slot[ph == "val"].mean() * 1e4, t_val=tstat(slot[ph == "val"]),
                     net_hold=slot[ph == "hold"].mean() * 1e4, cost_bp=cost.mean() * 1e4)
            r["pos_dev"] = int((net[ph == "dev"].mean(axis=0) > 0).sum()); r["pos_val"] = int((net[ph == "val"].mean(axis=0) > 0).sum()); rows.append(r)
            if r["t_dev"] >= 3.5 and r["net_val"] > 0 and r["t_val"] >= 2.0 and r["pos_dev"] >= 4 and r["pos_val"] >= 4:
                hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter17_raw.csv", index=False)
    print(T.sort_values("t_dev", ascending=False).head(12).round(2).to_string(index=False))
    print(f"\ncells {len(T)}; net_dev > 0: {(T.net_dev > 0).mean():.0%}; net_val > 0 among them: {(T[T.net_dev > 0].net_val > 0).mean():.0%}; median cost bp {T.cost_bp.median():.2f}")
    print(f"PRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")
    for h in hits:
        print(h)


if __name__ == "__main__":
    main()
