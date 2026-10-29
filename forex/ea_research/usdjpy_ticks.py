"""USDJPY London-open breakout replayed on MT5 REAL TICKS (Oct 2025 - Oct 2026; diagnostic): box = bid high / low 08:00-08:30 London,
first tick in 08:30-11:00 with ask >= high (buy) or bid <= low (sell), filled at the first tick 300 ms later (ask for a buy, bid for a sell),
stop at the other side of the box (filled at the first tick through it, 300 ms later), exit at 17:00 London (first tick at or after it).
Compared day by day with the M1 engine (BRK_EXITS, X4_noTP).   python -m forex.ea_research.usdjpy_ticks"""
import glob

import numpy as np
import pandas as pd

LAT = 300   # ms


def load():
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/ticks/USDJPY/*.parquet"))])
    t = t.sort_values("time_msc").drop_duplicates("time_msc")
    ms = t.time_msc.to_numpy(np.int64)
    srv = pd.to_datetime(ms, unit="ms")
    lon = srv.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert("Europe/London").tz_localize(None)
    lms = (lon.values.astype("datetime64[ms]").astype(np.int64))
    return ms, lms, t.bid.to_numpy(), t.ask.to_numpy()


def main():
    ms, lms, bid, ask = load()
    day_ms = 86_400_000
    rows = []
    for d in np.unique(lms // day_ms):
        base = d * day_ms
        a, b = np.searchsorted(lms, base + 8 * 3_600_000), np.searchsorted(lms, base + 8 * 3_600_000 + 30 * 60_000)
        w, x = np.searchsorted(lms, base + 11 * 3_600_000), np.searchsorted(lms, base + 17 * 3_600_000)
        if b - a < 100 or x >= len(lms) or lms[x] // day_ms != d:
            continue
        hi, lo = bid[a:b].max(), bid[a:b].min()
        up = np.flatnonzero(ask[b:w] >= hi)
        dn = np.flatnonzero(bid[b:w] <= lo)
        ku = b + up[0] if len(up) else None
        kd = b + dn[0] if len(dn) else None
        if ku is None and kd is None:
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        f = np.searchsorted(ms, ms[k] + LAT)
        if f >= x:
            continue
        e = ask[f] if side > 0 else bid[f]
        stop = lo if side > 0 else hi
        R = abs(e - stop)
        if side * (e - stop) <= 0:
            continue
        hit = np.flatnonzero(bid[f + 1:x] <= stop) if side > 0 else np.flatnonzero(ask[f + 1:x] >= stop)
        if len(hit):
            j = np.searchsorted(ms, ms[f + 1 + hit[0]] + LAT)
            px = bid[j] if side > 0 else ask[j]
        else:
            px = bid[x] if side > 0 else ask[x]
        rows.append((pd.Timestamp(d * 86400, unit="s"), side, side * (px - e) / R, (ask[f] - bid[f]), R))
    T = pd.DataFrame(rows, columns=["day", "side", "R", "spread", "Rpx"])
    mt5 = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    mt5 = mt5[(forex.mkt == "USDJPY") & (forex.kind == "BRK")][["day", "side", "X4_noTP"]]
    m = T.merge(mt5, on="day", suffixes=("_tick", "_m1"))
    print(f"ticks: {len(T)} trades {T.day.min().date()}..{T.day.max().date()}, mean {T.R.mean():+.3f} R, win {np.mean(T.R > 0):.0%}, median spread at fill {T.spread.median():.4f}, median R {T.Rpx.median():.3f}")
    print(f"common days with the M1 engine: {len(m)}; same side {np.mean(m.side_tick == m.side_m1):.0%}; R correlation {np.corrcoef(m.R, m.X4_noTP)[0, 1]:+.3f}; "
          f"mean R ticks {m.R.mean():+.3f} vs M1 {m.X4_noTP.mean():+.3f} (difference {m.R.mean() - m.X4_noTP.mean():+.3f})")
    T.to_parquet("data/si_ledgers/USDJPY_TICKS.parquet")


if __name__ == "__main__":
    main()
