"""First screen of PZ_StochEA.ex5 (Point Zero Trading, Arturo Lopez Perez; supplied by the trader from Downloads, 2026-10-06): the 2026 stage-1 screen of the campaign (real ticks, MT5 broker server, $100K, 2026.01.01-2026.09.30), DEFAULT inputs,
one run per market / timeframe from a list fixed before the first run:  XAUUSD H1 / M15 / H4, EURUSD H1, GBPUSD H1, USDJPY H1, US100.cash H1.
Reported: deals, net, the tester's maximal equity drawdown, the volumes traded (martingale shows as varying volumes), the largest volume. Strategy Tester only (AllowLiveTrading=0, AllowDllImport=0).
STOP THE EA BATCH FIRST.   python -m mt5broker.ea_batch.pz_stoch_test
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from mt5broker.ea_batch import run_batch as RB
from mt5broker.ea_batch.tester_run import run_test

OUT = Path(r"D:\finance\scratch\pz_stoch"); OUT.mkdir(parents=True, exist_ok=True)
MARKETS = (("XAUUSD", "H1"), ("XAUUSD", "M15"), ("XAUUSD", "H4"), ("EURUSD", "H1"), ("GBPUSD", "H1"), ("USDJPY", "H1"), ("US100.cash", "H1"))


def main():
    dst = RB.data_folder() / "MQL5" / "Experts" / "the trader" / "PZ_StochEA.ex5"
    dst.parent.mkdir(exist_ok=True)
    shutil.copy(Path(r"C:\Users\author\Downloads\PZ_StochEA.ex5"), dst)
    rows = []
    for sym, per in MARKETS:
        r = run_test(f"pz_{sym.replace('.', '')}_{per}", r"the trader\PZ_StochEA.ex5", sym, per, "2026.01.01", "2026.09.30", None, timeout=2400)
        d = r["deals"]
        row = dict(symbol=sym, period=per, note=r["note"], seconds=r["seconds"], deals=0 if d is None else len(d), net=r["net"], eq_dd=r["eq_dd"], bal_dd=r["bal_dd"])
        if d is not None and len(d):
            d.to_csv(OUT / f"{sym.replace('.', '')}_{per}.csv", index=False)
            v = d[d.direction == "in"].volume
            row.update(entries=len(v), vol_min=float(v.min()), vol_max=float(v.max()), vol_distinct=int(v.nunique()), win_pct=float((d[d.direction == 'out'].profit > 0).mean() * 100))
        rows.append(row); print(json.dumps({k: (round(x, 2) if isinstance(x, float) else x) for k, x in row.items()}, default=str), flush=True)
    pd.DataFrame(rows).to_csv(OUT / "pz_stoch_screen.csv", index=False)
    print("done", flush=True)


if __name__ == "__main__":
    main()
