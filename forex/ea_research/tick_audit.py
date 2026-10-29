"""Audit of the M1 backtester against MT5 broker real ticks (the trader 2026-10-14: "you need to be backtesting properly").
   Re-runs the BRK breakout rules B1 (opening range) and B4 (previous-day high/low) on M1 for 2025-10-01..2025-12-31 (VAL period, unsealed),
   records every trade (entry minute, side, entry price, stop, exit minute), then replays each trade on the real ticks:
   fill at the first tick of the entry minute (ask for longs, bid for shorts), stop hit on the first tick through it (filled at that tick's price),
   exit at the first tick of the exit minute. Compares R per trade.   python -m forex.ea_research.tick_audit"""
import numpy as np
import pandas as pd

from forex.ea_research import breakouts as B
from forex.ea_research.crt import load

MKTS = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "SP", "NSDQ", "DAX", "BTCUSD")
A, Z = pd.Timestamp("2025-10-01").timestamp(), pd.Timestamp("2026-01-01").timestamp()


def m1_trades(sym):
    rec = []
    orig = B.sim

    def spy(D, k, side, e, stop, target, j):
        r = orig(D, k, side, e, stop, target, j)
        if r is not None and A <= D["t"][k] < Z:
            rec.append((int(D["t"][k]), side, e, stop, int(D["t"][j]), r[0]))
        return r
    B.sim = spy
    try:
        D = load(sym, Z)
        D["mo"] = (D["bo"] + D["ao"]) / 2
        D["h1"], D["days"] = B.h1_cache(D), B.day_table(D)
        tz, op, cl = B.session(sym)
        lc = B.local_clock(D["t"], tz)
        rows = []
        for d in np.unique(lc // 86400):
            if d * 86400 >= A - 86400:
                n0 = len(rec)
                B.range_break(D, lc, d, op, op + 30 * 60, op + 30 * 60, cl - 3600, cl, sym, "B1", rows)
                rec[n0:] = [x + ("B1",) for x in rec[n0:]]
        n0 = len(rec)
        B.pdhl(D, sym, rows)
        rec[n0:] = [x + ("B4",) for x in rec[n0:]]
    finally:
        B.sim = orig
    return [x for x in rec if len(x) == 7]


def ticks(sym):
    parts = [pd.read_parquet(f"data/ticks/{sym}/{m}.parquet") for m in ("2025-10", "2025-11", "2025-12")]
    d = pd.concat(parts).sort_values("time_msc")
    d = d[(d.bid > 0) & (d.ask >= d.bid)]
    return d.time_msc.to_numpy(), d.bid.to_numpy(), d.ask.to_numpy()


def replay(T, bid, ask, t_in, side, stop, t_out):
    i = np.searchsorted(T, t_in * 1000)
    j = np.searchsorted(T, t_out * 1000)
    if i >= len(T) or j >= len(T) or j <= i or T[i] >= (t_in + 60) * 1000:
        return None
    e = ask[i] if side > 0 else bid[i]
    risk = abs(e - stop)
    if not risk > 0 or side * (e - stop) <= 0:
        return None
    path = bid[i:j] if side > 0 else ask[i:j]
    hit = np.flatnonzero(path <= stop) if side > 0 else np.flatnonzero(path >= stop)
    x = path[hit[0]] if len(hit) else (bid[j] if side > 0 else ask[j])
    return side * (x - e) / risk


def main():
    out = []
    for s in MKTS:
        T, b, a = ticks(s)
        for (t_in, side, e, stop, t_out, r_m1, cell) in m1_trades(s):
            r_t = replay(T, b, a, t_in, side, stop, t_out)
            if r_t is not None:
                out.append((s, cell, r_m1, r_t))
        print(s, "done", flush=True)
    df = pd.DataFrame(out, columns=["mkt", "cell", "R_m1", "R_tick"])
    df.to_csv("data/si_ledgers/TICK_AUDIT_trades.csv", index=False)
    pd.set_option("display.width", 200)
    g = df.groupby(["cell", "mkt"]).agg(n=("R_m1", "size"), R_m1=("R_m1", "mean"), R_tick=("R_tick", "mean"),
                                        corr=("R_m1", lambda v: np.corrcoef(v, df.loc[v.index, "R_tick"])[0, 1] if len(v) > 2 else np.nan))
    print(g.round(3).to_string())
    for c, x in df.groupby("cell"):
        print(f"{c}: {len(x)} trades | mean R M1 {x.R_m1.mean():+.3f} | ticks {x.R_tick.mean():+.3f} | per-trade correlation {np.corrcoef(x.R_m1, x.R_tick)[0, 1]:.3f} | "
              f"median |difference| {np.median(np.abs(x.R_m1 - x.R_tick)):.3f} R")


if __name__ == "__main__":
    main()
