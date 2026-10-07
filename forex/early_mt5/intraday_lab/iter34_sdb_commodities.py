"""Iteration 34 (pre-registered in intraday_lab/PREREG.md): the frozen SDB rule on seven more MT5 broker commodities.
   python -m mt5broker.intraday_lab.iter34_sdb_commodities --dry-run     (counts only)
   python -m mt5broker.intraday_lab.iter34_sdb_commodities               (the pre-registered run)"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.forward_test import config
from mt5broker.intraday_lab import sdb

DATA = Path(__file__).resolve().parents[1] / "data"
SYMS = ("XAGUSD", "USOIL.cash", "UKOIL.cash", "XCUUSD", "XPTUSD", "XPDUSD", "NATGAS.cash")
CONTRACT = {"XAGUSD": 5000.0, "XPTUSD": 100.0, "XPDUSD": 100.0, "XCUUSD": 25000.0, "USOIL.cash": 1000.0, "UKOIL.cash": 1000.0, "NATGAS.cash": 10000.0}   # ASSUMED, see PREREG
sdb.commission_price = lambda sym, price: 6.0 / CONTRACT.get(sym, 100.0)


def tstat(r):
    r = np.asarray(r, dtype=float)
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std(ddof=1) > 0 else float("nan")


def main():
    dry = "--dry-run" in sys.argv
    frames, dropped = [], []
    for s in SYMS:
        if not (DATA / f"{s}_M1_ticks_full.parquet").exists():
            dropped.append(s); continue
        t = sdb.simulate(s, **config.RULE)
        t["sym"] = s; t["when"] = pd.to_datetime(t.t_entry, unit="s"); frames.append(t)
        print(f"  {s}: {len(t)} trades", flush=True)
    if dropped:
        print("dropped (no data):", dropped)
    T = pd.concat(frames, ignore_index=True)
    months = 60.0
    if dry:
        print("trades by symbol:", T.groupby("sym").size().to_dict(), "| pooled", len(T), f"({len(T) / months:.1f} a month)")
        return
    ph = np.where(T.when < "2024-01-01", "dev", np.where(T.when < "2025-01-01", "val", "hold")); T["ph"] = ph; T["y"] = T.when.dt.year
    T.to_csv("D:/finance/scratch/lab/iter34_trades.csv", index=False)
    dv, vl = T[T.ph == "dev"], T[T.ph == "val"]
    print("per symbol: n | DEV mean (t) | VAL mean (t) | HOLD not shown")
    for s, g in T.groupby("sym"):
        d, v = g[g.ph == "dev"], g[g.ph == "val"]
        print(f"  {s:<12} n {len(g):3d} | DEV {d.R.mean():+.3f} ({tstat(d.R):+.2f}) | VAL {v.R.mean():+.3f} ({tstat(v.R):+.2f})")
    pos_d = int((dv.groupby("sym").R.mean() > 0).sum()); pos_v = int((vl.groupby("sym").R.mean() > 0).sum())
    yrs = T[T.y >= 2022].groupby("y").R.mean(); ypos = int((yrs > 0).sum())
    print(f"POOLED DEV n {len(dv)} mean {dv.R.mean():+.3f} t {tstat(dv.R):+.2f} | VAL n {len(vl)} mean {vl.R.mean():+.3f} t {tstat(vl.R):+.2f} | symbols positive DEV {pos_d} VAL {pos_v} of {T.sym.nunique()} | years positive {ypos}/5 {({int(k): round(float(v), 3) for k, v in yrs.items()})} | {len(T) / months:.1f} trades a month")
    need_d = int(np.ceil(0.7 * dv.sym.nunique())); need_v = int(np.ceil(0.7 * vl.sym.nunique()))      # amended in the dry run: copper / natural gas history starts late
    hit = dv.R.mean() > 0 and tstat(dv.R) >= 3.0 and vl.R.mean() > 0 and tstat(vl.R) >= 2.0 and pos_d >= need_d and pos_v >= need_v and ypos >= 4
    print("PRE-REGISTERED HIT:", bool(hit))
    if hit:
        h = T[T.ph == "hold"]; print("HOLD (printed because DEV and VAL passed):", f"n {len(h)} mean {h.R.mean():+.3f} t {tstat(h.R):+.2f}")


if __name__ == "__main__":
    main()
