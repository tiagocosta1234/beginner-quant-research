"""PRESAMPLE3 exactly as in PREREG_PRESAMPLE3.md: the London-open breakout on five JPY crosses, 2020-01-02..2021-11-30, HistData, today's MT5 broker spreads.
   python -m forex.ea_research.presample3"""
import numpy as np
import pandas as pd

import forex.ea_research.presample as ps
from forex.ea_research.ict2 import nw_t
from forex.ea_research.presample2 import load_hd

CROSSES = ("EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CHFJPY")


def current_spread(sym):
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet")
    d = d[(d.t >= pd.Timestamp("2025-10-01").timestamp()) & (d.t < pd.Timestamp("2026-10-03").timestamp())]
    t = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London")
    h = t.dt.hour
    return float(np.median((d.ao - d.bo)[(h >= 8) & (h < 17)]))


def main():
    rng = np.random.default_rng(2022)
    res = {}
    for sym in CROSSES + ("USDJPY", "CADJPY"):
        fl = current_spread(sym)
        D = load_hd(sym, fl)
        df = ps.l1_usdjpy(D, rng)
        res[sym] = df
        yrs = {y: round(g.R.mean(), 3) for y, g in df.groupby(df.day.dt.year)}
        tag = "" if sym in CROSSES else "  (context, already tested)"
        print(f"{sym}: today's MT5 broker spread {fl:.4f} | n {len(df)} {df.R.mean():+.3f} R (t {ps.tstat(df.R):+.2f}) | random {df.C.mean():+.3f} | by year {yrs}{tag}")
    allp = pd.concat([res[s].assign(mkt=s) for s in CROSSES])
    allp.to_parquet("D:/finance/si_ledgers/PRESAMPLE3.parquet")
    dm = allp.groupby("day").R.mean()
    yrs = {y: round(g.mean(), 3) for y, g in dm.groupby(dm.index.year)}
    g = [dm.mean() > 0 and nw_t(dm.to_numpy()) >= 1.96, all(v > 0 for v in yrs.values())]
    print(f"J1 five JPY crosses pooled: days {len(dm)} {dm.mean():+.3f} R (daily t {nw_t(dm.to_numpy()):+.2f}) | by year {yrs} | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    book = pd.concat([res[s].assign(mkt=s) for s in res]).groupby("day").R.mean()
    print(f"context - all seven yen pairs at today's spreads: {book.mean():+.3f} R a day-trade (daily t {nw_t(book.to_numpy()):+.2f})")


if __name__ == "__main__":
    main()
