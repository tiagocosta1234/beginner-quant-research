"""Iteration 8 (pre-registered in lab/PREREG.md): volatility-targeted sizing of the pair vs fixed lots.   python -m mt5broker.intraday_lab.iter8_volscale"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import bg_replay as BG, pair_ladder as PL, pair_stress as PS, snowball_capital as SC, snowball_multi as SM

W = {"77900": 1.508, "mkt_xau5min": 1.431}


def gold_atr20(days):
    m = pd.read_parquet("forex/early_mt5/data/XAUUSD_M1_ticks_full.parquet"); idx = pd.to_datetime(m.time, unit="s")
    h = pd.Series(m.high.values, index=idx).resample("1D").max(); l = pd.Series(m.low.values, index=idx).resample("1D").min()
    a = (h - l).dropna().rolling(20).mean().shift(1)
    return a.reindex(pd.DatetimeIndex(days).normalize()).ffill().bfill().values


def summarize(tag, v, mb, days):
    s = pd.Series(v, index=days); y = s.groupby(days.year).sum(); eq = np.cumsum(v); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    sh = v.mean() / v.std() * np.sqrt(252)
    print(f"{tag:<14} yearly P&L {[int(x) for x in y.values]} | Sharpe {sh:.2f} | max closed drawdown {dd:,.0f} | worst day {mb.min():,.0f}", flush=True)


def main():
    U, E, R, start, days = PS.build(W)
    v0, mb0, mr0 = BG.frames(U, E, R, start)
    atr = gold_atr20(days); g = 1.0 / atr; k = v0.std() / (v0 * g).std()
    G = g * k
    v1, mb1, mr1 = v0 * G, mb0 * G, mr0 * G
    print(f"scale factor range (vol-scaled / fixed): min {G.min():.2f} max {G.max():.2f}; by year mean: {pd.Series(G, index=days).groupby(days.year).mean().round(2).to_dict()}\n", flush=True)
    summarize("fixed lots", v0, mb0, days); summarize("vol-scaled", v1, mb1, days)
    # 2-Step ladder LB replay: base = loaded lots (c = 1.5 equals series scale 1 here)
    LB = PL.LADDERS["LB 1.5 / 1.0 / 0.6 / 0.3 at -2 / -4 / -6%"]
    print("\nMT5BROKER 2-Step, ladder LB, no deadline, all weekday starts 2022-26:")
    for tag, v, m in (("fixed lots", v0, mb0), ("vol-scaled", v1, mb1)):
        PL.run(tag, v, m, days, LB, 1.5)
        PL.run(tag + " const", v, m, days, lambda dd: 1.5, 1.5)
    # snowball odds
    # the snowball model's ladders are multiples of the frozen lot (c = 1), so rebuild the series at c = 1 and scale it with the same factor
    U1, E1, R1, s1, days1 = PS.build({"77900": 1.0, "mkt_xau5min": 1.0}); v0, mb0, mr0 = BG.frames(U1, E1, R1, s1)
    G = gold_atr20(days1); G = (1.0 / G) * (v0.std() / (v0 / gold_atr20(days1)).std()); v1, mb1, mr1 = v0 * G, mb0 * G, mr0 * G; days = days1
    bd = pd.bdate_range(days.min(), PS.END); fut = pd.bdate_range("2026-10-13", "2027-12-31"); H = len(fut)
    inflow = {int(np.searchsorted(fut, mth)): 50.0 for mth in pd.date_range("2026-11-01", "2027-12-01", freq="MS")}; contrib = 550 + 50 * len(inflow)
    SM.FIRMS["BG"].rule = BG.ladder(1.0); SM.FIRMS["MT5"].rule = lambda dd: 0.8
    print("\nCapital-first snowball (EUR 550 + EUR 50 / month, start 2026-10-13), 300 bootstrap paths:")
    for tag, v, mb, mr in (("fixed lots", v0, mb0, mr0), ("vol-scaled", v1, mb1, mr1)):
        V, MB, MR = (pd.Series(a, index=days).reindex(bd).fillna(0.0).values for a in (v, mb, mr))
        T = np.isin(bd, days[np.abs(v0) > 0]).astype(int); N = len(bd)
        for fs in (0.5, 1.0):
            var = SC.Var("v", True, fs, 1.0); rng = np.random.default_rng(347)
            paths = [np.concatenate([np.arange(x, x + 20) % N for x in rng.integers(0, N, H // 20 + 1)])[:H] for _ in range(300)]
            res = [SC.snowball(V[i], MB[i], MR[i], T[i], var, 550.0, inflow) for i in paths]
            net = np.array([r["manual"] + r["cash"] - contrib for r in res]); cap = np.array([r["cap"] for r in res])
            print(f"  {tag:<11} live {fs}x: P(live >= $500K) {np.mean(cap >= 5e5):4.0%}  P(>= $1M) {np.mean(cap >= 1e6):4.0%} | net mean {net.mean():>8,.0f} median {np.median(net):>7,.0f} P(net<0) {np.mean(net < 0):4.0%}", flush=True)


if __name__ == "__main__":
    main()
