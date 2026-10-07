"""Iteration 19 (pre-registered in lab/PREREG.md): volatility-regime filter (2-component mixture) on the gold pair, constant-risk daily P&L.   python -m mt5broker.intraday_lab.iter19_regime"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from mt5broker.intraday_lab.lab import DATA

PH = [("2022-23", "2022-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"), ("2025-26", "2025-01-01", "2026-10-02")]


def gold_daily():
    m = pd.read_parquet(DATA / "XAUUSD_M1_ticks_full.parquet", columns=["time", "high", "low", "close"]); idx = pd.to_datetime(m.time.values, unit="s")
    h = pd.Series(m.high.values, index=idx).resample("1D").max(); l = pd.Series(m.low.values, index=idx).resample("1D").min(); c = pd.Series(m.close.values, index=idx).resample("1D").last()
    d = pd.DataFrame({"h": h, "l": l, "c": c}).dropna(); d["rng"] = d.h - d.l; return d


def features(d):
    r = d.rng; ret = np.log(d.c).diff()
    f1 = np.log(r.rolling(5).mean() / r.rolling(60).mean()); a20 = r.rolling(20).mean(); f2 = np.log(a20 / a20.rolling(250, min_periods=120).median()); f3 = np.log(ret.rolling(20).std())
    return {"ATR5/ATR60": f1.shift(1), "ATR20 vs 250d median": f2.shift(1), "20d realised vol": f3.shift(1)}


def calm_flags(x: pd.Series, days):
    """1.0 on days the lower-mean mixture component is active; the mixture is fitted on information before the block (expanding window, refit every 21 days)."""
    out = pd.Series(np.nan, index=days); xs = x.dropna()
    for i in range(0, len(days), 21):
        t0 = days[i]; hist = xs[xs.index < t0]
        if len(hist) < 150:
            continue
        g = GaussianMixture(2, random_state=0, n_init=3).fit(hist.values.reshape(-1, 1)); calm = int(np.argmin(g.means_.ravel()))
        blk = days[i:i + 21]; v = x.reindex(blk)
        lab = g.predict(v.fillna(hist.median()).values.reshape(-1, 1)); out.loc[blk] = (lab == calm).astype(float)
    return out


def main():
    J = json.load(open(r"D:\finance\scratch\curves2\pair_stats.json")); days = pd.DatetimeIndex(pd.to_datetime(J["days"])); pnl = pd.Series(J["const"], index=days)
    d = gold_daily(); d.index = d.index.normalize(); F = features(d); rows = []; hits = []
    for name, x in F.items():
        calm = calm_flags(x, days)
        ok = calm.notna(); r = dict(feature=name, removed=float(calm[ok].mean()))
        for ph, a, b in PH:
            s = pnl.loc[a:b][ok.loc[a:b]]; c = calm.loc[a:b][ok.loc[a:b]] == 1.0
            on, off = s[~c], s[c]
            r[f"on_{ph}"] = float(on.mean()) if len(on) else np.nan; r[f"off_{ph}"] = float(off.mean()) if len(off) else np.nan; r[f"n_off_{ph}"] = int(len(off))
        s = pnl[ok]; c = calm[ok] == 1.0; on, off = s[~c], s[c]; se = np.sqrt(on.var(ddof=1) / len(on) + off.var(ddof=1) / len(off)); r["t_pooled"] = float((on.mean() - off.mean()) / se)
        rows.append(r)
        if all(r[f"on_{ph}"] > r[f"off_{ph}"] for ph, _, _ in PH) and r["t_pooled"] >= 2.5 and r["removed"] <= 0.40:
            hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter19_raw.csv", index=False); print(T.round(2).T.to_string()); print(f"\nPRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")


if __name__ == "__main__":
    main()
