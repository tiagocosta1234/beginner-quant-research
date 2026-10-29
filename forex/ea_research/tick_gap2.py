"""Does the breakout's 'information' (breakout minus random entry, ~+0.03-0.05 R on M1 bars) survive real ticks? (diagnostic)
Replays round 1's RANDOM-ENTRY controls (BRK_EXITS kind CTRL: same day, random minute in the order window, random side, R = box, hold to
the session close) on MT5 broker real ticks (market entry at the first tick 300 ms after the control's minute starts) and compares, on the tick
era, breakout minus control on ticks vs on M1 bars.   python -m forex.ea_research.tick_gap2"""
import glob
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.ict2 import SYMS

LAT = 300
H, M = 3600, 60


def market(args):
    sym, ctrl = args
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
            key = pd.Timestamp(d * 86400, unit="s")
            if key not in ctrl:
                continue
            t_entry, side = ctrl[key]
            base = d * 86400 * 1000
            a, b = np.searchsorted(lms, base + op * 1000), np.searchsorted(lms, base + (op + 30 * M) * 1000)
            x = np.searchsorted(lms, base + cl * 1000)
            if b - a < 50 or x >= len(lms) or lsec[min(x, len(lms) - 1)] // 86400 != d:
                continue
            cap = np.searchsorted(ms, (ms[b] // 86_400_000) * 86_400_000 + (22 * H + 55 * M) * 1000)
            x = min(x, cap)
            if x >= len(ms) or (ms[x] // 1000 % 86400) // H in (23, 0):
                continue
            box = bid[a:b].max() - bid[a:b].min()
            fi = np.searchsorted(ms, int(t_entry) * 1000 + LAT)
            if fi >= x or box <= 0:
                continue
            e = ask[fi] if side > 0 else bid[fi]
            stop = e - side * box
            hit = np.flatnonzero(bid[fi + 1:x] <= stop) if side > 0 else np.flatnonzero(ask[fi + 1:x] >= stop)
            if len(hit):
                j = min(np.searchsorted(ms, ms[fi + 1 + hit[0]] + LAT), len(ms) - 1)
                px = bid[j] if side > 0 else ask[j]
            else:
                px = bid[x] if side > 0 else ask[x]
            rows.append((sym, key, side, side * (px - e) / box))
    return rows


def main():
    mt5 = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    mt5 = mt5[forex.day >= "2025-10-01"]
    c = mt5[forex.kind == "CTRL"]
    jobs = [(s, {r.day: (r.t_entry, r.side) for r in c[c.mkt == s].itertuples()}) for s in SYMS]
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(market, jobs))
    C = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "day", "side", "C_tick"])
    C.to_parquet("data/si_ledgers/TICK_GAP_CTRL.parquet")
    B = pd.read_parquet("data/si_ledgers/TICK_GAP.parquet")
    cm = C.merge(c[["mkt", "day", "side", "X4_noTP"]], on=["mkt", "day", "side"])
    bm = B.merge(mt5[forex.kind == "BRK"][["mkt", "day", "side", "X4_noTP"]], on=["mkt", "day", "side"])
    print(f"controls on ticks: {len(cm)} | M1 {cm.X4_noTP.mean():+.3f} R, ticks {cm.C_tick.mean():+.3f} R, gap {(cm.C_tick - cm.X4_noTP).mean():+.3f}")
    print(f"breakouts on ticks: {len(bm)} | M1 {bm.X4_noTP.mean():+.3f} R, ticks {bm.R_tick.mean():+.3f} R, gap {(bm.R_tick - bm.X4_noTP).mean():+.3f}")
    print(f"breakout information (breakout minus random) in the tick era: M1 bars {bm.X4_noTP.mean() - cm.X4_noTP.mean():+.3f} R | real ticks {bm.R_tick.mean() - cm.C_tick.mean():+.3f} R")
    from forex.ea_research.analog import mclass
    for cl, g in bm.assign(c=bm.mkt.map(mclass)).groupby("c"):
        h = cm[cm.mkt.map(mclass) == cl]
        print(f"   {cl}: information M1 {g.X4_noTP.mean() - h.X4_noTP.mean():+.3f} | ticks {g.R_tick.mean() - h.C_tick.mean():+.3f}")


if __name__ == "__main__":
    main()
