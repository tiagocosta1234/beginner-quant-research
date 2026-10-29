"""Iteration 6, step 1: profile what the pair's EAs actually do, using DEV-period trades only (2022-2023), so the rules we then write can be tested honestly on VAL (2024) and HOLDOUT (2025-26).
For every trade entry we compute features at the last closed bar before the entry (5-minute bars for XAU5min, 60-minute bars for Stochastic Daily Breakout) and compare their distribution with ALL bars of the same period, separately for long and short entries (standardised difference d = (mean at entries - mean all) / sd all).
  python -m forex.intraday_lab.iter6_profile
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_batch import floating
from forex.intraday_lab.lab import Bars

EAS = {"mkt_xau5min": 5, "77900": 60}


def feats(b: Bars):
    atr = b.atr(14); s = pd.Series(b.mid); f = {}
    for k in (1, 3, 12, 48, 96):
        f[f"ret{k}"] = ((s - s.shift(k)) / pd.Series(atr)).values
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min(); f["rngpos96"] = ((s - ll) / (hh - ll)).values
    hh14 = pd.Series(b.bh).rolling(14).max(); ll14 = pd.Series(b.bl).rolling(14).min(); k = (s - ll14) / (hh14 - ll14) * 100; f["stoch_k"] = k.rolling(3).mean().values
    f["z20"] = ((s - s.rolling(20).mean()) / s.rolling(20).std()).values
    f["atr_pct"] = pd.Series(atr).rolling(500).rank(pct=True).values
    day_open = pd.Series(b.mid).groupby(b.day).transform("first").values; f["from_day_open"] = (b.mid - day_open) / atr
    f["hour"] = b.hour.astype(float); f["dow"] = ((b.t // 86400 + 4) % 7).astype(float)
    return f


def main():
    for ea, tf in EAS.items():
        b = Bars("XAUUSD", tf); f = feats(b); rows = []
        pos = []
        for y in (2022, 2023):
            d = pd.read_csv(f"forex/ea_batch/results_{y}/{ea}.csv")
            p, _ = floating.pair_positions(d, floating.prior_k("XAUUSD", pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")))
            pos.append(p)
        P = pd.concat(pos); te = (pd.to_datetime(P.te).astype("int64") // 10**9).values
        i = np.searchsorted(b.t, te, side="right") - 1                     # last bar that started at or before the entry
        i = i - 1                                                           # last CLOSED bar before the entry
        ok = i > 100; i = i[ok]; side = P.side.values[ok]
        dev = b.slice_idx("dev")
        print(f"\n=== {ea}: {len(i)} entries in DEV (long {(side > 0).sum()}, short {(side < 0).sum()}), {tf}-minute bars ===")
        for name, v in f.items():
            allv = v[dev]; allv = allv[np.isfinite(allv)]; mu, sd = allv.mean(), allv.std()
            for sname, sel in (("long", side > 0), ("short", side < 0)):
                x = v[i[sel]]; x = x[np.isfinite(x)]
                if len(x) < 8:
                    continue
                d = (x.mean() - mu) / sd; se = 1 / np.sqrt(len(x))
                rows.append(dict(ea=ea, feat=name, side=sname, n=len(x), entry_mean=round(float(x.mean()), 3), all_mean=round(float(mu), 3), d=round(float(d), 3), t=round(float(d / se), 2)))
        R = pd.DataFrame(rows)
        print(R.reindex(R.t.abs().sort_values(ascending=False).index).head(14).to_string(index=False))
        R.to_csv(f"data/scratch/lab/iter6_profile_{ea}.csv", index=False)
        # hour distribution of entries
        h = pd.Series(b.hour[i]).value_counts(normalize=True).sort_index(); print("entry hours (share):", {int(k): round(float(v), 2) for k, v in h[h >= 0.05].items()})
        dow = pd.Series(((b.t[i] // 86400 + 4) % 7)).value_counts(normalize=True).sort_index(); print("entry weekday share (0=Mon):", {int(k): round(float(v), 2) for k, v in dow.items()})


if __name__ == "__main__":
    main()
