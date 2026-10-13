"""
Extend the MT5 M1 bid/ask files (forex/data/<symbol>_M1_ticks_full.parquet) to now (read-only; sends no orders).

  python -m forex.data_update XAUUSD EURUSD US100.cash

Pulls only the ticks after the file's last minute from the MT5 MT5 terminal (copy_ticks_range, COPY_TICKS_ALL), aggregates them with the
SAME function that built the file (forex.tick_bars.minute_bars), drops the file's last minute (it may have been partial when pulled) and
re-derives it, appends, and rewrites the parquet and its manifest (rows, last_day, updated_utc, sha256). `time` stays MT5 server
wall-clock seconds (server = New York + 7 h, forex/clock.py). The newest minute can still be incomplete: it is replaced on the next update.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from forex.clock import SERVER_MINUS_NY
from forex.data_pull import attach
from forex.tick_bars import minute_bars

HERE = Path(__file__).resolve().parent
CHUNK = pd.Timedelta(hours=6)


def server_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="America/New_York").tz_localize(None) + SERVER_MINUS_NY


def update(symbol: str) -> dict:
    path = HERE / "data" / f"{symbol}_M1_ticks_full.parquet"
    old = pd.read_parquet(path)
    last = int(old["time"].max())
    keep = old[old["time"] < last]
    t0 = pd.Timestamp(last, unit="s")
    t1 = server_now()
    mt5 = attach()
    frames, n_ticks = [], 0
    try:
        mt5.symbol_select(symbol, True)
        point = mt5.symbol_info(symbol).point
        a = t0
        while a < t1:
            b = min(a + CHUNK, t1 + pd.Timedelta(minutes=1))
            ticks = None
            for attempt in range(4):
                ticks = mt5.copy_ticks_range(symbol, dt.datetime(a.year, a.month, a.day, a.hour, a.minute, tzinfo=dt.timezone.utc),
                                             dt.datetime(b.year, b.month, b.day, b.hour, b.minute, tzinfo=dt.timezone.utc), mt5.COPY_TICKS_ALL)
                if ticks is not None:
                    break
                time.sleep(2)
            if ticks is not None and len(ticks):
                n_ticks += len(ticks)
                frames.append(minute_bars(ticks, point))
            a = b
    finally:
        mt5.shutdown()
    if not frames:
        return dict(symbol=symbol, added=0, note="no new ticks")
    new = pd.concat(frames, ignore_index=True)
    new = new[new["time"] >= last]
    bars = pd.concat([keep, new[keep.columns]], ignore_index=True).drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    bars.to_parquet(path, index=False)
    mpath = HERE / "specs" / f"{symbol}_M1_ticks_full_manifest.json"
    man = json.loads(mpath.read_text())
    tt = pd.to_datetime(bars["time"], unit="s")
    man.update(rows=int(len(bars)), last_day=str(tt.iloc[-1].date()), updated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               ticks_added_in_last_update=int(n_ticks), rows_per_year={str(k): int(v) for k, v in tt.dt.year.value_counts().sort_index().items()},
               sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    mpath.write_text(json.dumps(man, indent=1))
    ny_last = pd.Timestamp(int(bars["time"].iloc[-1]), unit="s") - SERVER_MINUS_NY
    gaps = np.diff(bars["time"].to_numpy()[-(len(new) + 5):]) / 60.0
    return dict(symbol=symbol, rows_before=int(len(old)), rows_after=int(len(bars)), added=int(len(bars) - len(keep)), ticks=int(n_ticks), last_bar_ny=str(ny_last), largest_gap_min_in_new=float(gaps.max()) if len(gaps) else 0.0)


def main(argv=None) -> int:
    syms = (argv or sys.argv[1:]) or ["XAUUSD", "EURUSD", "US100.cash"]
    for s in syms:
        print(json.dumps(update(s)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
