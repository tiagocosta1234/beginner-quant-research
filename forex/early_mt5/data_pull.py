"""
Pull M1 history for one symbol from the MT5 MT5 terminal (read-only; sends no orders).

  python -m mt5broker.data_pull US100.cash --start 2019-01-01

Attaches to the terminal's logged-in session (same guard as mt5_check: the terminal's
login/server must equal forex/early_mt5/.env), downloads M1 bars month by month, retrying a month
until two consecutive reads agree (MT5 fetches history from the server lazily), and saves
  forex/early_mt5/data/<symbol>_M1.parquet            (gitignored; bars as MT5 returns them)
  forex/early_mt5/specs/<symbol>_M1_manifest.json     (committed: rows, span, gaps, sha256, pull time)
Bar `time` is kept exactly as MT5 returns it (server wall-clock seconds); the conversion to
New York time is established separately and explicitly (see forex/early_mt5/clock.py), never assumed here.
MT5 bars are BID prices; `spread` is in points (1 point = symbol_info.point).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"


def attach():
    import MetaTrader5 as mt5
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
    login, server = os.getenv("MT5BROKER_MT5_LOGIN"), os.getenv("MT5BROKER_MT5_SERVER")
    if not mt5.initialize(path=os.getenv("MT5BROKER_MT5_TERMINAL") or TERMINAL, timeout=90_000):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    acc = mt5.account_info()
    if acc is None or acc.login != int(login) or acc.server != server:
        mt5.shutdown()
        raise SystemExit("The terminal is not logged into the account in forex/early_mt5/.env; stopping.")
    return mt5


def month_starts(start: dt.date, end: dt.date):
    d = dt.date(start.year, start.month, 1)
    while d <= end:
        yield d
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def pull(symbol: str, start: dt.date, max_tries: int = 6) -> pd.DataFrame:
    mt5 = attach()
    try:
        if not mt5.symbol_select(symbol, True):
            raise SystemExit(f"{symbol} not available")
        info = mt5.symbol_info(symbol)
        term = mt5.terminal_info()
        print(f"{symbol}: point {info.point}, digits {info.digits}; terminal max bars {term.maxbars:,}")
        frames = []
        today = dt.date.today()
        for m in month_starts(start, today):
            a = dt.datetime(m.year, m.month, 1, tzinfo=dt.timezone.utc)
            nm = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
            b = dt.datetime(nm.year, nm.month, 1, tzinfo=dt.timezone.utc)
            prev = None
            for attempt in range(max_tries):
                r = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, a, b)
                n = 0 if r is None else len(r)
                if prev is not None and n == prev and n > 0:
                    break
                prev = n
                time.sleep(1.0 + attempt)
            if r is not None and len(r):
                df = pd.DataFrame(r)
                df = df[(df["time"] >= int(a.timestamp())) & (df["time"] < int(b.timestamp()))]
                frames.append(df)
            print(f"  {m:%Y-%m}: {0 if r is None else len(r):>7,} bars  (err {mt5.last_error()})", flush=True)
        out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(out):
            out = out.drop_duplicates("time").sort_values("time").reset_index(drop=True)
        return out, info
    finally:
        mt5.shutdown()


def manifest(df: pd.DataFrame, path: Path, symbol: str, info) -> dict:
    t = pd.to_datetime(df["time"], unit="s")
    gaps = t.diff().dt.total_seconds().div(60)
    per_year = t.dt.year.value_counts().sort_index()
    return {
        "symbol": symbol, "timeframe": "M1", "price_side": "bid", "time_field": "MT5 server wall-clock seconds",
        "point": info.point, "digits": info.digits,
        "pulled_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rows": int(len(df)), "first_server_time": str(t.iloc[0]), "last_server_time": str(t.iloc[-1]),
        "bars_per_year": {str(k): int(v) for k, v in per_year.items()},
        "gaps_over_3_days": int((gaps > 3 * 1440).sum()),
        "zero_tick_volume_share": float((df["tick_volume"] == 0).mean()),
        "real_volume_nonzero_share": float((df["real_volume"] > 0).mean()),
        "spread_points_median": float(df["spread"].median()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--start", default="2019-01-01")
    a = ap.parse_args()
    df, info = pull(a.symbol, dt.date.fromisoformat(a.start))
    if df.empty:
        print("No bars returned.")
        return 1
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "specs").mkdir(exist_ok=True)
    path = HERE / "data" / f"{a.symbol}_M1.parquet"
    df.to_parquet(path, index=False)
    man = manifest(df, path, a.symbol, info)
    (HERE / "specs" / f"{a.symbol}_M1_manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in man.items() if k != "sha256"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
