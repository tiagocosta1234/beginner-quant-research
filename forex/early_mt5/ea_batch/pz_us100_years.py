"""PZ_StochEA on US100.cash H1 in the years before 2026 (the 2026 screen was the only positive of seven: +$54 at 0.01 lot, 3,483 trades, profit factor 1.55, median hold 1 minute, edge all on the long side).
Default inputs, real ticks, $100K, same as the screen; years 2022-2025. Also reports the edge per trade in index points and what an extra 0.5 / 1.0 point of slippage per trade would leave of it.
STOP THE EA BATCH FIRST.   python -m mt5broker.ea_batch.pz_us100_years
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch.tester_run import run_test

OUT = r"D:\finance\scratch\pz_stoch"


def main():
    for year in (2025, 2024, 2023, 2022):
        r = run_test(f"pz_US100_H1_{year}", r"the trader\PZ_StochEA.ex5", "US100.cash", "H1", f"{year}.01.01", f"{year}.12.31", None, timeout=2400)
        d = r["deals"]
        if d is None or not len(d):
            print(year, "no deals", r["note"], flush=True); continue
        d.to_csv(f"{OUT}\\US100cash_H1_{year}.csv", index=False)
        o = d[d.direction == "out"]; net = o.profit + o.commission + o.swap
        n = len(net); pts = net / 0.01                      # US100: $0.01 per index point at 0.01 lot
        print(f"{year}: {n} trades, net {net.sum():+.2f} ($ at 0.01 lot), tester max equity drawdown {r['eq_dd']:.2f}, edge {pts.mean():+.2f} index points a trade (t {pts.mean() / (pts.std() / np.sqrt(n)):+.1f}); "
              f"after +0.5 / +1.0 / +1.5 points slippage a trade: {pts.mean() - 0.5:+.2f} / {pts.mean() - 1.0:+.2f} / {pts.mean() - 1.5:+.2f}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
