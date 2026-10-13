"""
Real bid/ask spread of US100.cash around the 09:30 ET open, from MT5 tick history (read-only),
compared with the M1 bars' `spread` field the backtest uses.

  python -m forex.spread_probe [--days 74]

For each RTH date present in forex/data/US100.cash_M1.parquet (most recent N), fetches ticks
09:29:30-09:31:00 ET and records: the spread of the first tick at/after 09:30:00, the median and max
spread over 09:30:00-09:30:59, and the 09:30 bar's recorded spread. Saves
forex/specs/US100.cash_open_spread.json. Server wall clock = NY + 7 h (forex/clock.py); MT5's
tick-range arguments are server wall-clock times passed as UTC-stamped datetimes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mt5 import clock
from forex.data_pull import attach

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=74)
    a = ap.parse_args()
    raw = pd.read_parquet(HERE / "data" / "US100.cash_M1.parquet")
    ny = clock.server_to_ny(raw["time"].to_numpy())
    bars = pd.DataFrame({"spread": raw["spread"].to_numpy(), "open": raw["open"].to_numpy()}, index=ny)
    opens = bars[bars.index.time == dt.time(9, 30)]
    dates = opens.index.normalize().unique()[-a.days:]
    mt5 = attach()
    rows = []
    try:
        for d in dates:
            srv = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30) + clock.SERVER_MINUS_NY
            f = dt.datetime(srv.year, srv.month, srv.day, srv.hour, srv.minute, tzinfo=dt.timezone.utc) - dt.timedelta(seconds=30)
            t = mt5.copy_ticks_range("US100.cash", f, f + dt.timedelta(seconds=90), mt5.COPY_TICKS_ALL)
            if t is None or len(t) == 0:
                continue
            tk = pd.DataFrame(t)
            tk["ts"] = pd.to_datetime(tk["time_msc"], unit="ms") - clock.SERVER_MINUS_NY
            tk = tk[(tk["bid"] > 0) & (tk["ask"] > 0)]
            sp = tk["ask"] - tk["bid"]
            open_ts = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)
            first = tk[tk["ts"] >= open_ts].head(1)
            minute = tk[(tk["ts"] >= open_ts) & (tk["ts"] < open_ts + pd.Timedelta(minutes=1))]
            bar = opens.loc[open_ts] if open_ts in opens.index else None
            rows.append(dict(date=str(d.date()), ticks_in_minute=int(len(minute)),
                             first_tick_spread=float((first["ask"] - first["bid"]).iloc[0]) if len(first) else None,
                             first_tick_bid_minus_bar_open=float(first["bid"].iloc[0] - bar["open"]) if len(first) and bar is not None else None,
                             minute_median_spread=float((minute["ask"] - minute["bid"]).median()) if len(minute) else None,
                             minute_max_spread=float((minute["ask"] - minute["bid"]).max()) if len(minute) else None,
                             pre_open_max_spread=float(sp[tk["ts"] < open_ts].max()) if (tk["ts"] < open_ts).any() else None,
                             bar_spread=float(bar["spread"]) / 100 if bar is not None else None))
    finally:
        mt5.shutdown()
    df = pd.DataFrame(rows)
    summary = {c: {"median": float(df[c].median()), "p90": float(df[c].quantile(0.9)), "max": float(df[c].max())}
               for c in ("first_tick_spread", "minute_median_spread", "minute_max_spread", "pre_open_max_spread",
                         "bar_spread", "first_tick_bid_minus_bar_open")}
    out = {"symbol": "US100.cash", "units": "index points", "days": int(len(df)), "summary": summary, "rows": rows}
    (HERE / "specs" / "US100.cash_open_spread.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"days": len(df), **summary}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
