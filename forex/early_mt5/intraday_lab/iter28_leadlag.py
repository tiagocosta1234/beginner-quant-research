"""Iteration 28 (pre-registered in lab/PREREG.md): cross-asset lead-lag (indices / gold -> 6 FX pairs) on a 5-minute grid.   python -m mt5broker.intraday_lab.iter28_leadlag"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter16_fx_xsection import COMM, SGN
from mt5broker.intraday_lab.lab import DATA, FX

PRED = ("US100.cash", "US500.cash", "US30.cash", "GER40.cash", "XAUUSD")


def load(sym, grid):
    m = pd.read_parquet(DATA / f"{sym}_M1_ticks_full.parquet", columns=["time", "open", "ask_open"]); t = m.time.values
    keep = (t // 60) % 5 == 0; t = t[keep]; mid = ((m.open.values + m.ask_open.values) / 2)[keep]; sp = ((m.ask_open.values - m.open.values) / ((m.open.values + m.ask_open.values) / 2))[keep]
    idx = pd.to_datetime(t, unit="s"); a = pd.Series(mid, index=idx); b = pd.Series(sp, index=idx)
    return a[~a.index.duplicated()].reindex(grid).values, b[~b.index.duplicated()].reindex(grid).values


def tstat(x):
    return float(np.mean(x) / (np.std(x, ddof=1) / np.sqrt(len(x)))) if len(x) > 20 and np.std(x, ddof=1) > 0 else np.nan


def main():
    grid = pd.date_range("2021-10-01", "2026-10-02", freq="5min"); n = len(grid); ph = np.where(grid < pd.Timestamp("2024-01-01"), 0, np.where(grid < pd.Timestamp("2025-01-01"), 1, 2))
    P = {s: load(s, grid)[0] for s in PRED}; fx = {s: load(s, grid) for s in FX}; rows = []; hits = []
    for pname in PRED:
        lp = np.log(P[pname])
        for L in (5, 15, 60):
            g = L // 5; r = pd.Series(lp - np.roll(lp, g)).shift(1); sd = r.rolling(2016, min_periods=500).std().shift(1); s = (r / sd).values        # r[t] uses price up to t-1 grid step
            for H in (15, 60):
                h = H // 5
                for k, pair in enumerate(FX):
                    mid, sp = fx[pair]; f = np.log(mid) * SGN[pair]; fwd = np.full(n, np.nan); fwd[:-h] = f[h:] - f[:-h]; cost = np.full(n, np.nan); cost[:-h] = 0.5 * (sp[:-h] + sp[h:]) + 2 * COMM
                    sig = np.abs(s) >= 2; ok = sig & ~np.isnan(fwd) & ~np.isnan(cost) & ~np.isnan(s); cand = np.flatnonzero(ok); keep = []; last = -10**9
                    for c in cand:
                        if c >= last:
                            keep.append(c); last = c + h
                    keep = np.array(keep, dtype=int)
                    if len(keep) < 300:
                        continue
                    sgn = np.sign(s[keep]); gross = sgn * fwd[keep]; p_ = ph[keep]
                    d = np.sign(gross[p_ == 0].mean()) if (p_ == 0).sum() > 30 else 0
                    if d == 0:
                        continue
                    net = d * gross - cost[keep]; dv, vl = net[p_ == 0], net[p_ == 1]
                    rows.append(dict(pred=pname, L=L, H=H, pair=pair, d=int(d), n_dev=len(dv), gross_dev_bp=(d * gross[p_ == 0]).mean() * 1e4, cost_bp=cost[keep].mean() * 1e4, net_dev_bp=dv.mean() * 1e4, t_dev=tstat(dv), n_val=len(vl),
                                     gross_val_bp=(d * gross[p_ == 1]).mean() * 1e4 if len(vl) else np.nan, net_val_bp=vl.mean() * 1e4 if len(vl) else np.nan, t_val=tstat(vl) if len(vl) else np.nan))
                    r_ = rows[-1]
                    if r_["t_dev"] >= 3.6 and r_["n_dev"] >= 300 and r_["net_val_bp"] > 0 and r_["t_val"] >= 2.0:
                        hits.append(dict(r_, hold_net_bp=float(net[p_ == 2].mean() * 1e4) if (p_ == 2).any() else np.nan))
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter28_raw.csv", index=False)
    stab = T[(T.gross_dev_bp > 0) & (T.gross_val_bp > 0)]
    print(T.sort_values("t_dev", ascending=False).head(10).round(2).to_string(index=False))
    print(f"\ncells with enough trades: {len(T)} of 180; gross > 0 in both DEV and VAL: {len(stab)} ({len(stab) / len(T):.0%}); max gross / cost in DEV: {(T.gross_dev_bp / T.cost_bp).max():.2f}")
    print(f"PRE-REGISTERED HITS: {len(hits)}")
    for h in hits:
        print(h)


if __name__ == "__main__":
    main()
