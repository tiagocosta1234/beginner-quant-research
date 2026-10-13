"""READ-ONLY M1 export WITH tick_volume (and spread) from the portable tester terminal through the MetaTrader5 Python package
(the earlier MT5 broker minute files lack tick_volume). Same safety rules as ticks_pull.py: only initialize / terminal_info / account_info / symbols_get / symbol_info / copy_rates_range / shutdown; aborts if algo trading is allowed.
Run it ONLY when the live account is not running on this PC (main PC idle) and the trader is not trading by hand.
   python -m mt5broker.self_improving.hf.rates_pull [--symbols EURUSD,XAUUSD] [--start 2021-12-01] [--end 2026-08-15]
Output: D:\\finance\\ticks_vol\\<SYMBOL>.parquet with time (UTC s), tick_volume, spread, real_volume (bars only up to --end: the sealed HOLD is not exported)."""
import sys
ARGV = sys.argv[1:]

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

from mt5broker.self_improving import platform_v3 as P3

TERMINAL = r"D:\finance\mt5_mt5_tester\terminal64.exe"
OUT = Path("D:/finance/ticks_vol"); OUT.mkdir(parents=True, exist_ok=True)


def broker_name(base):
    for suf in ("+", "", ".", "-", "m"):
        if mt5.symbol_info(base + suf) is not None: return base + suf
    names = [s.name for s in mt5.symbols_get() if s.name.upper().startswith(base.upper())]
    return names[0] if names else None


def main():
    ap = argparse.ArgumentParser(); allsyms = ",".join(m for c in P3.CLASSES.values() for m in c["members"])
    ap.add_argument("--symbols", default=allsyms); ap.add_argument("--start", default="2021-12-01"); ap.add_argument("--end", default="2026-08-15"); a = ap.parse_args(ARGV)
    if not mt5.initialize(path=TERMINAL, portable=True, timeout=120000): raise SystemExit(f"initialize failed: {mt5.last_error()}")
    ti = mt5.terminal_info(); ai = mt5.account_info(); print(f"connected={ti.connected} trade_allowed={ti.trade_allowed} login={ai.login}", flush=True)
    if ti.trade_allowed: mt5.shutdown(); raise SystemExit("ABORT: algorithmic trading is allowed in this terminal")
    try:
        for base in a.symbols.split(","):
            f = OUT / f"{base}.parquet"
            if f.exists(): print(f"[{base}] exists"); continue
            sym = broker_name(base)
            if sym is None: print(f"[{base}] not found"); continue
            mt5.symbol_select(sym, True); parts = []; cur = pd.Timestamp(a.start); end = pd.Timestamp(a.end)
            while cur < end:
                nxt = min(cur + pd.offsets.MonthBegin(1), end); r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, cur.to_pydatetime().replace(tzinfo=dt.timezone.utc), nxt.to_pydatetime().replace(tzinfo=dt.timezone.utc))
                if r is not None and len(r): parts.append(pd.DataFrame({"time": r["time"].astype(np.int64), "tick_volume": r["tick_volume"].astype(np.int64), "spread": r["spread"].astype(np.int32), "real_volume": r["real_volume"].astype(np.int64)}))
                cur = nxt
            if parts: m = pd.concat(parts, ignore_index=True).drop_duplicates("time"); m.to_parquet(f, compression="zstd", index=False); print(f"[{base}] {len(m):,} minutes, tick_volume mean {m.tick_volume.mean():.1f}", flush=True)
            else: print(f"[{base}] no bars")
    finally: mt5.shutdown()


if __name__ == "__main__":
    main()
