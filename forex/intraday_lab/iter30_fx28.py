"""Iteration 30 (pre-registered in intraday_lab/PREREG.md): frozen SDB rule + four frozen swing families on all 28 FX pairs.
   python -m forex.intraday_lab.iter30_fx28 --dry-run     (counts only, no P&L)
   python -m forex.intraday_lab.iter30_fx28               (the pre-registered run)"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from forex.forward_test import config as fcfg
from forex.intraday_lab import iter29_fx_swing as sw
from forex.intraday_lab import sdb

DATA = Path(__file__).resolve().parents[1] / "data"
OUTDIR = Path("data/scratch/lab")
PAIRS = ("EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD EURGBP EURJPY EURCHF EURAUD EURCAD EURNZD GBPJPY GBPCHF GBPAUD GBPCAD GBPNZD "
         "AUDJPY AUDCHF AUDCAD AUDNZD NZDJPY NZDCHF NZDCAD CADJPY CADCHF CHFJPY").split()
FAMS = ("DON20", "DON55", "PB", "MR", "SDB")
MONTHS = 60.0


def available():
    return [p for p in PAIRS if (DATA / f"{p}_M1_ticks_full.parquet").exists()]


def collect(pairs):
    rows = {f: [] for f in FAMS}
    for sym in pairs:
        a = sw.daily(sym)
        for fam, s in sw.signals(a).items():
            rows[fam] += [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in sw.trades(sym, a, s)]
        t = sdb.simulate(sym, **fcfg.RULE)
        for e, side, R in zip(t.t_entry, t.side, t.R):
            rows["SDB"].append((sym, pd.Timestamp(int(e), unit="s").normalize(), int(side), float(R), np.nan, np.nan))
        print(f"  {sym}: swing + SDB done", flush=True)
    return {f: pd.DataFrame(r, columns=["pair", "d", "side", "R", "gross_R", "cost_R"]) for f, r in rows.items()}


def main():
    dry = "--dry-run" in sys.argv
    pairs = available()
    print(f"pairs with data: {len(pairs)} of {len(PAIRS)}; missing: {sorted(set(PAIRS) - set(pairs))}")
    T = collect(pairs)
    if dry:
        for f, df in T.items():
            print(f"{f}: {len(df)} trades, {df.pair.nunique()} pairs, {len(df) / MONTHS:.1f} a month pooled")
        return
    OUTDIR.mkdir(parents=True, exist_ok=True)
    hits = []
    for fam, df in T.items():
        df["y"] = df.d.dt.year; df["ph"] = np.where(df.d < "2024-01-01", "dev", np.where(df.d < "2025-01-01", "val", "hold"))
        df.to_csv(OUTDIR / f"iter30_{fam}.csv", index=False)
        dv, vl = df[df.ph == "dev"], df[df.ph == "val"]
        pos_dev = int((dv.groupby("pair").R.mean() > 0).sum()); pos_val = int((vl.groupby("pair").R.mean() > 0).sum())
        yrs = df[df.y >= 2022].groupby("y").R.mean(); ypos = int((yrs > 0).sum())
        r_ = dict(family=fam, n=len(df), per_month=len(df) / MONTHS, mean_dev=dv.R.mean(), t_dev=sw.tstat(dv.R), mean_val=vl.R.mean(), t_val=sw.tstat(vl.R),
                  pairs_pos_dev=pos_dev, pairs_pos_val=pos_val, years_pos=ypos, by_year={int(k): round(float(v), 3) for k, v in yrs.items()})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r_.items()}, flush=True)
        sparse = fam == "SDB" and len(dv) / 2.25 < 100
        if r_["mean_dev"] > 0 and r_["t_dev"] >= 3.0 and r_["mean_val"] > 0 and r_["t_val"] >= 2.0 and pos_dev >= 19 and pos_val >= 19 and ypos >= 4 and not sparse:
            hits.append(r_)
    print(f"PRE-REGISTERED HITS (k = 5): {len(hits)}")
    for h in hits:
        x = pd.read_csv(OUTDIR / f"iter30_{h['family']}.csv"); x = x[x.ph == "hold"]
        print("HOLD (printed because DEV and VAL passed):", h["family"], f"n {len(x)} mean R {x.R.mean():.3f} t {sw.tstat(x.R):.2f}", "| trades a month", round(h["per_month"], 1))


if __name__ == "__main__":
    main()
