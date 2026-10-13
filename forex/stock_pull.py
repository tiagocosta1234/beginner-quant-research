"""
Pull MT5 broker stock-CFD tick history and build M1 BID / ASK bars (read-only; sends no orders).  (Round 347j, the trader: "sure" to testing stocks on MT5)

  python -m forex.stock_pull NVDA AAPL --start 2021-10-01          # resumable: one part file per symbol and month
  python -m forex.stock_pull NVDA --start 2025-10-01 --end 2025-10-31 --probe   # timing only, writes nothing

Same bar builder as forex.tick_bars / forex.data_update (forex.tick_bars.minute_bars), so the stock files are comparable with the index files: time = MT5 server wall-clock seconds (New York + 7 h),
open / high / low / close = BID, ask_open / ask_high / ask_low / ask_close = ASK, spread, spread_max, tick_volume.

Differences from data_pull.attach(): that guard stops unless the terminal's login equals forex/.env. The terminal that is up here is the EA batch's tester terminal (MT5-Demo server, a different login) and it is
restarted by the batch for every EA run, so this script (a) does NOT compare logins -- it only reads market data from the MT5-Demo server, no credentials are used or entered, and (b) reconnects and
retries when the batch swaps the terminal under it ("No IPC connection"). Output goes to D: (the project's drive): parts in D:/finance/scratch/stock_parts, the joined file in forex/data (which resolves to D:).
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from forex.tick_bars import minute_bars

HERE = Path(__file__).resolve().parent
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
PARTS = Path("D:/finance/scratch/stock_parts")


def connect(mt5, tries: int = 40) -> bool:
    for _ in range(tries):
        if mt5.initialize(path=TERMINAL, timeout=60_000) and mt5.account_info() is not None:
            return True
        mt5.shutdown(); time.sleep(3)
    return False


def month_ticks(mt5, symbol: str, a: dt.datetime, b: dt.datetime, tries: int = 15):
    """Ticks of [a, b) with reconnects; two reads of a lazily-downloaded month must agree in length."""
    prev = None
    for attempt in range(tries):
        tk = mt5.copy_ticks_range(symbol, a, b, mt5.COPY_TICKS_ALL)
        if tk is None:
            mt5.shutdown(); time.sleep(3); connect(mt5); mt5.symbol_select(symbol, True); continue
        n = len(tk)
        if prev is not None and n == prev:
            return tk
        prev = n
        time.sleep(1.0)
    return tk if tk is not None else np.array([])


def months(start: dt.date, end: dt.date):
    d = dt.date(start.year, start.month, 1)
    while d <= end:
        nm = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield d, nm
        d = nm


def pull(symbols, start: dt.date, end: dt.date, probe: bool = False) -> None:
    import MetaTrader5 as mt5
    if not connect(mt5):
        raise SystemExit("could not attach to the MT5 terminal")
    PARTS.mkdir(parents=True, exist_ok=True)
    try:
        for sym in symbols:
            if not mt5.symbol_select(sym, True):
                print(f"{sym}: not available"); continue
            point = mt5.symbol_info(sym).point
            ok = False
            for _ in range(3):                                   # fast skip of symbols the terminal does not serve at all ("Terminal: Call failed" on every request)
                probe_a = dt.datetime(2026, 3, 10, tzinfo=dt.timezone.utc)
                if mt5.copy_ticks_range(sym, probe_a, probe_a + dt.timedelta(hours=24), mt5.COPY_TICKS_ALL) is not None:
                    ok = True; break
                time.sleep(2)
            if not ok:
                print(f"{sym}: the terminal does not serve its history right now ({mt5.last_error()}); skipped", flush=True); continue
            for m0, m1 in months(start, end):
                f = PARTS / f"{sym}_{m0:%Y-%m}.parquet"
                if f.exists() and not probe:
                    continue
                a = dt.datetime(m0.year, m0.month, 1, tzinfo=dt.timezone.utc); b = dt.datetime(m1.year, m1.month, 1, tzinfo=dt.timezone.utc)
                t0 = time.time()
                tk = month_ticks(mt5, sym, a, b)
                bars = minute_bars(tk, point) if len(tk) else pd.DataFrame()
                print(f"{sym} {m0:%Y-%m}: {len(tk):>9,} ticks -> {len(bars):>6,} minute bars ({time.time() - t0:.0f}s)", flush=True)
                if not probe:
                    bars.to_parquet(f, index=False)
            if not probe:
                parts = sorted(PARTS.glob(f"{sym}_*.parquet"))
                df = pd.concat([pd.read_parquet(p) for p in parts if p.stat().st_size > 0], ignore_index=True)
                if len(df):
                    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
                    df.to_parquet(HERE / "data" / f"{sym}_M1_ticks_full.parquet", index=False)
                    print(f"{sym}: {len(df):,} minute bars {pd.to_datetime(df.time.min(), unit='s')} .. {pd.to_datetime(df.time.max(), unit='s')} saved", flush=True)
    finally:
        mt5.shutdown()


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("symbols", nargs="+"); ap.add_argument("--start", default="2021-10-01"); ap.add_argument("--end", default=dt.date.today().isoformat()); ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    pull(a.symbols, dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end), a.probe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
