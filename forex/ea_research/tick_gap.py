"""How optimistic is the M1 engine? (diagnostic) Round 1's session breakout (30-min box at each market's session open, OCO stop orders for 3 h,
stop at the other side, hold to the session close capped 22:55 server) replayed on MT5 REAL TICKS for all 46 markets, Oct 2025 - Oct 2026,
fills at the tick 300 ms after the trigger, and compared day by day with the M1 engine (BRK_EXITS, X4_noTP).
   python -m forex.ea_research.tick_gap"""
import glob
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.ict2 import SYMS

LAT = 300
H, M = 3600, 60


def market(sym):
    tz, op, cl = session(sym)
    rows = []
    for f in sorted(glob.glob(f"data/ticks/{sym}/*.parquet")):
        t = pd.read_parquet(f, columns=["time_msc", "bid", "ask"]).sort_values("time_msc")
        t = t[(t.bid > 0) & (t.ask >= t.bid)]
        if len(t) < 1000:
            continue
        ms = t.time_msc.to_numpy(np.int64)
        sec = ms // 1000
        lsec = local_clock(sec, tz)
        lms = ms - (sec - lsec) * 1000
        bid, ask = t.bid.to_numpy(), t.ask.to_numpy()
        for d in np.unique(lsec // 86400):
            base = d * 86400 * 1000
            a, b = np.searchsorted(lms, base + op * 1000), np.searchsorted(lms, base + (op + 30 * M) * 1000)
            w = np.searchsorted(lms, base + (op + 3 * H) * 1000)
            x = np.searchsorted(lms, base + cl * 1000)
            if b - a < 50 or w <= b or x >= len(lms) or lsec[min(x, len(lms) - 1)] // 86400 != d:
                continue
            srv_day = ms[b] // 86_400_000
            cap = np.searchsorted(ms, srv_day * 86_400_000 + (22 * H + 55 * M) * 1000)
            x = min(x, cap)
            if x >= len(ms) or (ms[x] // 1000 % 86400) // H in (23, 0):
                continue
            hi, lo = bid[a:b].max(), bid[a:b].min()
            up = np.flatnonzero(ask[b:w] >= hi)
            dn = np.flatnonzero(bid[b:w] <= lo)
            ku = b + up[0] if len(up) else None
            kd = b + dn[0] if len(dn) else None
            if (ku is None and kd is None) or (ku is not None and ku == kd):
                continue
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            fi = np.searchsorted(ms, ms[k] + LAT)
            if fi >= x:
                continue
            e = ask[fi] if side > 0 else bid[fi]
            stop = lo if side > 0 else hi
            R = abs(e - stop)
            if side * (e - stop) <= 0 or R < 2 * (ask[fi] - bid[fi]):
                continue
            hit = np.flatnonzero(bid[fi + 1:x] <= stop) if side > 0 else np.flatnonzero(ask[fi + 1:x] >= stop)
            if len(hit):
                j = min(np.searchsorted(ms, ms[fi + 1 + hit[0]] + LAT), len(ms) - 1)
                px = bid[j] if side > 0 else ask[j]
            else:
                px = bid[x] if side > 0 else ask[x]
            rows.append((sym, pd.Timestamp(d * 86400, unit="s"), side, side * (px - e) / R))
    return rows


def main():
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(market, SYMS))
    T = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "day", "side", "R_tick"])
    T.to_parquet("data/si_ledgers/TICK_GAP.parquet")
    mt5 = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    mt5 = mt5[forex.kind == "BRK"][["mkt", "day", "side", "X4_noTP"]]
    m = T.merge(mt5, on=["mkt", "day"], suffixes=("_t", "_m"))
    m = m[m.side_t == m.side_m]
    m["c"] = m.mkt.map(mclass)
    m["gap"] = m.R_tick - m.X4_noTP
    print(f"common trades (same side): {len(m)} on {m.mkt.nunique()} markets; mean M1 {m.X4_noTP.mean():+.3f} R, ticks {m.R_tick.mean():+.3f} R, gap {m.gap.mean():+.3f} (median {m.gap.median():+.4f})")
    print("by class:")
    print(m.groupby("c").agg(n=("gap", "size"), M1=("X4_noTP", "mean"), ticks=("R_tick", "mean"), gap=("gap", "mean"), gap_median=("gap", "median")).round(3).to_string())
    g = m.groupby("mkt").agg(n=("gap", "size"), M1=("X4_noTP", "mean"), ticks=("R_tick", "mean"), gap=("gap", "mean")).sort_values("gap")
    print("most optimistic M1 markets:", g.head(6).round(3).to_dict("index"))
    print("least:", g.tail(4).round(3).to_dict("index"))


if __name__ == "__main__":
    main()
