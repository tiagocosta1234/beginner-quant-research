"""
Pull H1 history (and, if the server has it, M1 -- see forex/early_mt5/data_pull.py) plus the contract / margin / swap specs for crypto symbols from the MT5 MT5 terminal
(read-only; sends no orders). Crypto trades 24/7, so NO weekday filter is applied.

  python -m mt5broker.crypto_pull BTCUSD ETHUSD --start 2019-01-01

Same attach + account guard as data_pull. Saves
  forex/early_mt5/data/<symbol>_H1.parquet               (gitignored; BID OHLC, tick_volume, spread in points, MT5 server wall-clock seconds in `time`)
  forex/early_mt5/specs/<symbol>_H1_manifest.json        (committed: rows, first / last bar, per-year counts, gaps, sha256)
  forex/early_mt5/specs/<symbol>_crypto_specs_<date>.json (committed: contract size, lots, swap, margin fields, account leverage, trade sessions)
Bar `time` is kept as MT5 returns it (server clock; forex/early_mt5/clock.py: server = New York + 7 h). The MT5 broker commission (0.0325% a side, to be confirmed with a demo deal's
commission field) is NOT in these files; the research adds it.
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

HERE = Path(__file__).resolve().parent
SPEC_FIELDS = ("trade_contract_size", "volume_min", "volume_step", "volume_max", "point", "digits", "spread", "spread_float", "swap_mode",
               "swap_long", "swap_short", "swap_rollover3days", "trade_calc_mode", "trade_mode", "margin_initial", "margin_maintenance",
               "margin_hedged", "currency_base", "currency_profit", "currency_margin", "trade_stops_level", "trade_freeze_level", "session_deals")


def year_chunks(start: dt.date, end: dt.date):
    y = start.year
    while y <= end.year:
        a = dt.datetime(max(y, start.year) if y > start.year else start.year, 1 if y > start.year else start.month, 1 if y > start.year else start.day, tzinfo=dt.timezone.utc)
        b = dt.datetime(y + 1, 1, 1, tzinfo=dt.timezone.utc)
        yield a, b
        y += 1


def pull_h1(mt5, symbol: str, start: dt.date, max_tries: int = 6) -> pd.DataFrame:
    frames = []
    for a, b in year_chunks(start, dt.date.today() + dt.timedelta(days=1)):
        prev = None
        for attempt in range(max_tries):
            r = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, a, b)
            n = 0 if r is None else len(r)
            if prev is not None and n == prev and n > 0:
                break
            prev = n
            time.sleep(1.0 + attempt)
        if r is not None and len(r):
            df = pd.DataFrame(r)
            frames.append(df[(df["time"] >= int(a.timestamp())) & (df["time"] < int(b.timestamp()))])
        print(f"  {symbol} {a:%Y}: {0 if r is None else len(r):>6,} H1 bars (err {mt5.last_error()})", flush=True)
    return pd.concat(frames, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True) if frames else pd.DataFrame()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--start", default="2019-01-01")
    a = ap.parse_args()
    mt5 = attach()
    (HERE / "data").mkdir(exist_ok=True); (HERE / "specs").mkdir(exist_ok=True)
    try:
        acc = mt5.account_info()
        for sym in a.symbols:
            if not mt5.symbol_select(sym, True):
                print(f"{sym} not available"); continue
            info = mt5.symbol_info(sym)
            specs = {k: getattr(info, k, None) for k in SPEC_FIELDS}
            specs.update(symbol=sym, account_leverage=acc.leverage, account_currency=acc.currency, pulled_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
            (HERE / "specs" / f"{sym}_crypto_specs_{dt.date.today():%Y%m%d}.json").write_text(json.dumps(specs, indent=1, default=str))
            df = pull_h1(mt5, sym, dt.date.fromisoformat(a.start))
            if df.empty:
                print(f"{sym}: no H1 bars returned"); continue
            path = HERE / "data" / f"{sym}_H1.parquet"
            df.to_parquet(path, index=False)
            t = pd.to_datetime(df["time"], unit="s")
            gaps = t.diff().dt.total_seconds().div(3600)
            man = {"symbol": sym, "timeframe": "H1", "price_side": "bid", "time_field": "MT5 server wall-clock seconds", "rows": int(len(df)),
                   "first_server_time": str(t.iloc[0]), "last_server_time": str(t.iloc[-1]),
                   "bars_per_year": {str(k): int(v) for k, v in t.dt.year.value_counts().sort_index().items()},
                   "gaps_over_6h": int((gaps > 6).sum()), "max_gap_hours": float(gaps.max()), "spread_points_median": float(df["spread"].median()),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (HERE / "specs" / f"{sym}_H1_manifest.json").write_text(json.dumps(man, indent=1))
            print(json.dumps({k: v for k, v in man.items() if k != "sha256"}, indent=1))
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
