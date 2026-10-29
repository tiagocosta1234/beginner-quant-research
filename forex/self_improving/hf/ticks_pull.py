"""READ-ONLY tick export from the portable tester terminal (data\\mt5_mt5_tester) through the MetaTrader5 Python package.
Uses ONLY initialize / terminal_info / account_info (login and server, no balance) / symbols_get / symbol_info / copy_ticks_range / shutdown. No order function is imported or called.
   python -m forex.self_improving.hf.ticks_pull --test            (one symbol, one hour)
   python -m forex.self_improving.hf.ticks_pull --symbols EURUSD,XAUUSD --start 2025-10-01 --end 2026-10-13
Output: data\\ticks\\<SYMBOL>\\<YYYY-MM>.parquet with time_msc (UTC ms), bid, ask, flags."""
import sys
ARGV = sys.argv[1:]

import argparse
import datetime as dt
import time
from pathlib import Path

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

TERMINAL = r"data\mt5_mt5_tester\terminal64.exe"
OUT = Path("data/ticks"); OUT.mkdir(parents=True, exist_ok=True)
SAFE = ("initialize", "terminal_info", "account_info", "symbols_get", "symbol_info", "copy_ticks_range", "shutdown", "last_error", "symbol_select")


def start():
    if not mt5.initialize(path=TERMINAL, portable=True, timeout=120000): raise SystemExit(f"initialize failed: {mt5.last_error()}")
    ti = mt5.terminal_info(); ai = mt5.account_info()
    print(f"terminal connected={ti.connected} trade_allowed={ti.trade_allowed} tradeapi_disabled={getattr(ti, 'tradeapi_disabled', '?')} | account login={ai.login} server={ai.server}", flush=True)
    if ti.trade_allowed: mt5.shutdown(); raise SystemExit("ABORT: algorithmic trading is allowed in this terminal; this tool only runs with it disabled")
    return ti, ai


def broker_name(base):
    for suf in ("+", "", ".", "-", "m"):
        if mt5.symbol_info(base + suf) is not None: return base + suf
    names = [s.name for s in mt5.symbols_get() if s.name.upper().startswith(base.upper())]
    return names[0] if names else None


def pull_range(sym, a, b):
    t = mt5.copy_ticks_range(sym, a, b, mt5.COPY_TICKS_ALL)
    if t is None or len(t) == 0: return None
    return pd.DataFrame({"time_msc": t["time_msc"].astype(np.int64), "bid": t["bid"], "ask": t["ask"], "flags": t["flags"].astype(np.int32)})


def pull_symbol(base, start_d, end_d):
    sym = broker_name(base)
    if sym is None: print(f"[{base}] not found on the server"); return
    mt5.symbol_select(sym, True); d = OUT / base; d.mkdir(exist_ok=True); cur = pd.Timestamp(start_d).replace(day=1); end = pd.Timestamp(end_d); tot = 0
    while cur < end:
        nxt = (cur + pd.offsets.MonthBegin(1)); f = d / f"{cur:%Y-%m}.parquet"
        if f.exists() and nxt <= end and nxt < pd.Timestamp.now(): cur = nxt; continue
        parts = []; day = cur
        while day < min(nxt, end):
            df = pull_range(sym, day.to_pydatetime().replace(tzinfo=dt.timezone.utc), (day + pd.Timedelta(days=1)).to_pydatetime().replace(tzinfo=dt.timezone.utc))
            if df is not None: parts.append(df)
            day += pd.Timedelta(days=1)
        if parts:
            m = pd.concat(parts, ignore_index=True); m = m[(m.bid > 0) & (m.ask >= m.bid)]; m.to_parquet(f, compression="zstd", index=False); tot += len(m); print(f"[{base}] {cur:%Y-%m}: {len(m):,} ticks, first {pd.to_datetime(m.time_msc.iloc[0], unit='ms')}, last {pd.to_datetime(m.time_msc.iloc[-1], unit='ms')}", flush=True)
        else: print(f"[{base}] {cur:%Y-%m}: no ticks", flush=True)
        cur = nxt
    print(f"[{base}] done: {tot:,} ticks", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--test", action="store_true"); ap.add_argument("--symbols", default="EURUSD"); ap.add_argument("--start", default="2025-10-01"); ap.add_argument("--end", default=str(dt.date.today())); a = ap.parse_args(ARGV)
    start()
    try:
        if a.test:
            sym = broker_name("EURUSD"); print("broker symbol:", sym); e = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2); df = pull_range(sym, e.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=1), e.replace(minute=0, second=0, microsecond=0))
            print("test ticks:", None if df is None else len(df)); print(df.head(3).to_string() if df is not None else "")
            old = pull_range(sym, dt.datetime(2025, 10, 6, 10, 0, tzinfo=dt.timezone.utc), dt.datetime(2025, 10, 6, 11, 0, tzinfo=dt.timezone.utc)); print("ticks on 2025-10-06 10-11 UTC:", None if old is None else len(old))
            old2 = pull_range(sym, dt.datetime(2025, 3, 6, 10, 0, tzinfo=dt.timezone.utc), dt.datetime(2025, 3, 6, 11, 0, tzinfo=dt.timezone.utc)); print("ticks on 2025-03-06 10-11 UTC:", None if old2 is None else len(old2))
        else:
            for b in a.symbols.split(","): pull_symbol(b, a.start, a.end)
    finally: mt5.shutdown()
