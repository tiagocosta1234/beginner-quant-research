"""
Build 24/7 M1 BID and ASK bars for a crypto symbol from MT5 MT5 tick history (read-only; sends no orders). Same bar format as forex/early_mt5/tick_bars.py (minute_bars) but EVERY day
(Sunday and Saturday included) and an optional end date, with progress per month and a resumable monthly cache.

  python -m mt5broker.crypto_tick_bars BTCUSD --start 2026-06-01                 (a quick test: a few months)
  python -m mt5broker.crypto_tick_bars BTCUSD --start 2021-07-01 --end 2026-10-03

Server days are 00:00-24:00 server time (= 17:00-17:00 New York, forex/early_mt5/clock.py). Output:
  forex/early_mt5/data/<symbol>_M1_ticks247.parquet   time (server seconds, minute start), open/high/low/close (BID), ask_open/ask_high/ask_low/ask_close, spread (min ask-bid in the minute, points),
                                          spread_max, tick_volume (ticks in the minute)
  forex/early_mt5/data/_cache/<symbol>_<YYYY-MM>.parquet   one file per month (a re-run skips complete months, so an interrupted pull can be resumed)
  forex/early_mt5/specs/<symbol>_M1_ticks247_manifest.json   days, rows, ticks, per-year counts, gaps, sha256
Memory: one server day of BTC ticks is a few hundred thousand rows; days are aggregated one at a time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

from mt5broker.data_pull import attach
from mt5broker.tick_bars import minute_bars

HERE = Path(__file__).resolve().parent


def day_bars(mt5, symbol: str, d: dt.date, point: float):
    a = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)
    b = a + dt.timedelta(days=1)
    ticks = None
    for attempt in range(3):
        ticks = mt5.copy_ticks_range(symbol, a, b, mt5.COPY_TICKS_ALL)
        if ticks is not None:
            break
        time.sleep(2)
    n = 0 if ticks is None else len(ticks)
    return (minute_bars(ticks, point) if n else pd.DataFrame()), n


def build(symbol: str, start: dt.date, end: dt.date) -> tuple[pd.DataFrame, dict]:
    mt5 = attach()
    cache = HERE / "data" / "_cache"; cache.mkdir(parents=True, exist_ok=True)
    per_day, frames = {}, []
    try:
        mt5.symbol_select(symbol, True)
        point = mt5.symbol_info(symbol).point
        d, t0 = start, time.time()
        while d <= end:
            m_first = d.replace(day=1)
            m_last = (m_first + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
            f = cache / f"{symbol}_{m_first:%Y-%m}.parquet"
            complete = m_last < dt.date.today() and m_first >= start.replace(day=1) and m_last <= end
            if complete and f.exists():
                frames.append(pd.read_parquet(f)); d = m_last + dt.timedelta(days=1); print(f"  {m_first:%Y-%m}: cached", flush=True); continue
            month = []
            dd = max(d, m_first)
            while dd <= min(m_last, end):
                bars, n = day_bars(mt5, symbol, dd, point)
                if n:
                    month.append(bars); per_day[str(dd)] = n
                dd += dt.timedelta(days=1)
            if month:
                mb = pd.concat(month, ignore_index=True)
                if complete:
                    mb.to_parquet(f, index=False)
                frames.append(mb)
            print(f"  {m_first:%Y-%m}: {sum(per_day.get(str(x), 0) for x in pd.date_range(m_first, m_last).date):,} ticks, {len(per_day):,} days so far, {time.time() - t0:.0f}s", flush=True)
            d = m_last + dt.timedelta(days=1)
    finally:
        mt5.shutdown()
    bars = pd.concat(frames, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return bars, per_day


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--start", default="2021-07-01")
    ap.add_argument("--end", default=str(dt.date.today()))
    a = ap.parse_args()
    bars, per_day = build(a.symbol, dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))
    if bars.empty:
        print("No ticks returned."); return 1
    (HERE / "data").mkdir(exist_ok=True); (HERE / "specs").mkdir(exist_ok=True)
    path = HERE / "data" / f"{a.symbol}_M1_ticks247.parquet"
    bars.to_parquet(path, index=False)
    t = pd.to_datetime(bars["time"], unit="s"); gaps = t.diff().dt.total_seconds().div(60)
    man = {"symbol": a.symbol, "source": "MT5 copy_ticks_range, COPY_TICKS_ALL, aggregated to M1 bid and ask OHLC, all 7 days", "window": "server days 00:00-24:00 (17:00-17:00 NY)",
           "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "days_with_ticks": len(per_day), "first_day": min(per_day), "last_day": max(per_day),
           "ticks_total": int(sum(per_day.values())), "rows": int(len(bars)), "rows_per_year": {str(k): int(v) for k, v in t.dt.year.value_counts().sort_index().items()},
           "gaps_over_60min": int((gaps > 60).sum()), "max_gap_min": float(gaps.max()), "spread_points_median": float(bars["spread"].median()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (HERE / "specs" / f"{a.symbol}_M1_ticks247_manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in man.items() if k != "sha256"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
