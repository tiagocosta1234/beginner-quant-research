"""
Pull D1 history and the swap/contract specs for several symbols from the MT5 MT5 terminal
(read-only; sends no orders).

  python -m mt5broker.d1_pull US100.cash GER40.cash XAUUSD EURUSD

Same attach + guard as data_pull. D1 bars are BID prices; the server day runs 00:00-24:00 server
time = 17:00-17:00 New York (forex/early_mt5/clock.py), so a bar's server date is the New York date of its close.
Saves
  forex/early_mt5/data/<symbol>_D1.parquet            (gitignored)
  forex/early_mt5/specs/<symbol>_D1_manifest.json     (committed: span, rows, gaps, the symbol's swap and contract
      specs at pull time, a parity check of the D1 closes against the tick-built M1 bars where both
      exist, sha256)
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

from mt5broker.clock import SERVER_MINUS_NY
from mt5broker.data_pull import attach

HERE = Path(__file__).resolve().parent
SPEC_FIELDS = ("point", "digits", "trade_contract_size", "currency_base", "currency_profit", "currency_margin",
               "swap_mode", "swap_long", "swap_short", "swap_rollover3days", "volume_min", "volume_step")


def pull(mt5, symbol: str, max_tries: int = 8) -> pd.DataFrame:
    if not mt5.symbol_select(symbol, True):
        raise SystemExit(f"{symbol} not available")
    a = dt.datetime(1990, 1, 1, tzinfo=dt.timezone.utc)
    b = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
    prev, r = None, None
    for attempt in range(max_tries):            # MT5 fetches history lazily: re-read until two reads agree
        r = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_D1, a, b)
        n = 0 if r is None else len(r)
        if prev is not None and n == prev and n > 0:
            break
        prev = n
        time.sleep(2.0 + attempt)
    if r is None or not len(r):
        return pd.DataFrame()
    return pd.DataFrame(r).drop_duplicates("time").sort_values("time").reset_index(drop=True)


def parity_with_ticks(d1: pd.DataFrame, symbol: str) -> dict:
    """D1 close vs the tick-built M1 bid close of the last minute before 17:00 New York, per server date."""
    p = HERE / "data" / f"{symbol}_M1_ticks_full.parquet"
    if not p.exists():
        return {"available": False}
    m = pd.read_parquet(p, columns=["time", "close"])
    t = pd.to_datetime(m["time"], unit="s")                       # server wall clock
    last = m.groupby(t.dt.normalize())["close"].last()             # server date -> last bid close
    d = pd.Series(d1["close"].to_numpy(), index=pd.to_datetime(d1["time"], unit="s").dt.normalize())
    both = d.index.intersection(last.index)
    if not len(both):
        return {"available": True, "overlap_days": 0}
    diff = (d.loc[both] - last.loc[both]).abs()
    tol = 1e-9 + 0.5 * float(d1["close"].iloc[-1]) * 1e-6
    return {"available": True, "overlap_days": int(len(both)), "close_exact_share": float((diff <= tol).mean()),
            "close_max_abs_diff": float(diff.max()), "close_median_abs_diff": float(diff.median())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    a = ap.parse_args()
    mt5 = attach()
    try:
        out = {}
        for s in a.symbols:
            t0 = time.time()
            df = pull(mt5, s)
            info = mt5.symbol_info(s)
            out[s] = (df, {k: getattr(info, k) for k in SPEC_FIELDS})
            print(f"{s}: {len(df)} D1 bars ({time.time() - t0:.0f}s)", flush=True)
    finally:
        mt5.shutdown()
    (HERE / "data").mkdir(exist_ok=True)
    for s, (df, spec) in out.items():
        if df.empty:
            print(f"{s}: no bars")
            continue
        path = HERE / "data" / f"{s}_D1.parquet"
        df.to_parquet(path, index=False)
        t = pd.to_datetime(df["time"], unit="s")
        gaps = t.diff().dt.days
        man = {"symbol": s, "timeframe": "D1", "price_side": "bid",
               "server_day": f"00:00-24:00 server = 17:00-17:00 New York (server = NY + {SERVER_MINUS_NY})",
               "pulled_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "rows": int(len(df)), "first_day": str(t.iloc[0].date()), "last_day": str(t.iloc[-1].date()),
               "bars_per_year": {str(k): int(v) for k, v in t.dt.year.value_counts().sort_index().items()},
               "gaps_over_5_days": int((gaps > 5).sum()), "spread_points_median": float(df["spread"].median()),
               "specs_at_pull": spec, "parity_vs_tick_bars": parity_with_ticks(df, s),
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (HERE / "specs" / f"{s}_D1_manifest.json").write_text(json.dumps(man, indent=1))
        print(json.dumps({k: v for k, v in man.items() if k not in ("sha256", "bars_per_year")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
