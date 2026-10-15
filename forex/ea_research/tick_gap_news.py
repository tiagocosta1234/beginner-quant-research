"""Diagnostic: the tick replay of round 1's session breakouts (tick_gap.py) with a NEWS FLAT exit: on CPI / NFP days a position of a
London-session market (FX, metals; session 08:00-17:00 London) is closed at 13:25 London, before the 08:30 New York release.
New York sessions start after the release and are unchanged.   python -m forex.ea_research.tick_gap_news"""
import glob
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.ict2 import SYMS

LAT = 300
H, M = 3600, 60


def market(args):
    sym, news = args
    tz, op, cl = session(sym)
    if tz != "Europe/London":
        return []
    rows = []
    for f in sorted(glob.glob(f"D:/finance/ticks/{sym}/*.parquet")):
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
            day = pd.Timestamp(d * 86400, unit="s")
            base = d * 86400 * 1000
            a, b = np.searchsorted(lms, base + op * 1000), np.searchsorted(lms, base + (op + 30 * M) * 1000)
            w = np.searchsorted(lms, base + (op + 3 * H) * 1000)
            x_full = np.searchsorted(lms, base + cl * 1000)
            if b - a < 50 or w <= b or x_full >= len(lms) or lsec[min(x_full, len(lms) - 1)] // 86400 != d:
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
            e = ask[fi] if side > 0 else bid[fi] if fi < len(ms) else np.nan
            stop = lo if side > 0 else hi
            R = abs(e - stop)
            if not np.isfinite(e) or side * (e - stop) <= 0 or R < 2 * (ask[fi] - bid[fi]):
                continue
            res = {}
            for tag, x in (("hold", x_full), ("flat", np.searchsorted(lms, base + (13 * H + 25 * M) * 1000) if day.date() in news else x_full)):
                if fi >= x:
                    res[tag] = np.nan
                    continue
                hit = np.flatnonzero(bid[fi + 1:x] <= stop) if side > 0 else np.flatnonzero(ask[fi + 1:x] >= stop)
                if len(hit):
                    j = min(np.searchsorted(ms, ms[fi + 1 + hit[0]] + LAT), len(ms) - 1)
                    px = bid[j] if side > 0 else ask[j]
                else:
                    px = bid[x] if side > 0 else ask[x]
                res[tag] = side * (px - e) / R
            rows.append((sym, day, day.date() in news, res["hold"], res["flat"]))
    return rows


def main():
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
    news = set(pd.to_datetime(cal[cal.kind.isin(["CPI", "NFP"])].date).dt.date)
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(market, [(s, news) for s in SYMS]))
    T = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "day", "news", "hold", "flat"]).dropna()
    T["c"] = T.mkt.map(mclass)
    T.to_parquet("D:/finance/si_ledgers/TICK_GAP_NEWS.parquet")
    print(f"London-session markets on real ticks, {len(T)} breakouts ({int(T.news.sum())} on CPI / NFP days): hold {T.hold.mean():+.3f} R | news flat {T.flat.mean():+.3f} R | on news days {T[T.news].hold.mean():+.3f} -> {T[T.news].flat.mean():+.3f}")
    print(T.groupby("c")[["hold", "flat"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
