"""
Build M1 BID and ASK bars for US100.cash from MT5 MT5 tick history (read-only).

  python -m mt5broker.tick_bars US100.cash --start 2021-09-20

Why: the MT5 broker server serves M1 bars for US100.cash only from 2026-06-19, but tick history from
2021-10. Ticks carry bid AND ask, so the bars built here give real fills (a long buys the real
ask, a short covers at the real ask) instead of bid + the bar's minimum spread.
Window per weekday: 08:30-17:10 New York (server = NY + 7 h, forex/early_mt5/clock.py; the extra hour each
side lets the clock check catch any daylight-saving misalignment). Output:
  forex/early_mt5/data/<symbol>_M1_ticks.parquet   time (server wall-clock seconds, minute start), open/high/
      low/close (BID), ask_open/ask_high/ask_low/ask_close, spread (min ask-bid in the minute, points),
      spread_max (points), tick_volume (ticks in the minute)
  forex/early_mt5/specs/<symbol>_M1_ticks_manifest.json   days, rows, ticks, per-year counts, sha256, and a
      parity check of the BID bars against MT5's own M1 bars where both exist.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.clock import SERVER_MINUS_NY
from mt5broker.data_pull import attach

HERE = Path(__file__).resolve().parent
WIN_START, WIN_END = pd.Timedelta(hours=8, minutes=30), pd.Timedelta(hours=17, minutes=10)


def minute_bars(ticks: np.ndarray, point: float) -> pd.DataFrame:
    tk = pd.DataFrame({"t": ticks["time_msc"] // 1000, "bid": ticks["bid"], "ask": ticks["ask"]})
    tk = tk[(tk["bid"] > 0) & (tk["ask"] > 0)]
    if tk.empty:
        return pd.DataFrame()
    tk["m"] = tk["t"] // 60 * 60
    tk["sp"] = (tk["ask"] - tk["bid"]) / point
    g = tk.groupby("m", sort=True)
    out = pd.DataFrame({
        "open": g["bid"].first(), "high": g["bid"].max(), "low": g["bid"].min(), "close": g["bid"].last(),
        "ask_open": g["ask"].first(), "ask_high": g["ask"].max(), "ask_low": g["ask"].min(), "ask_close": g["ask"].last(),
        "spread": g["sp"].min().round().astype(int), "spread_max": g["sp"].max().round().astype(int),
        "tick_volume": g.size(),
    })
    out.index.name = "time"
    return out.reset_index()


def build(symbol: str, start: dt.date) -> tuple[pd.DataFrame, dict]:
    mt5 = attach()
    frames, per_day = [], {}
    try:
        mt5.symbol_select(symbol, True)
        point = mt5.symbol_info(symbol).point
        d = start
        t0 = time.time()
        while d <= dt.date.today():
            if d.weekday() < 5:
                srv0 = pd.Timestamp(d) + WIN_START + SERVER_MINUS_NY
                srv1 = pd.Timestamp(d) + WIN_END + SERVER_MINUS_NY
                a = dt.datetime(srv0.year, srv0.month, srv0.day, srv0.hour, srv0.minute, tzinfo=dt.timezone.utc)
                b = dt.datetime(srv1.year, srv1.month, srv1.day, srv1.hour, srv1.minute, tzinfo=dt.timezone.utc)
                ticks = None
                for attempt in range(3):
                    ticks = mt5.copy_ticks_range(symbol, a, b, mt5.COPY_TICKS_ALL)
                    if ticks is not None:
                        break
                    time.sleep(2)
                n = 0 if ticks is None else len(ticks)
                if n:
                    frames.append(minute_bars(ticks, point))
                    per_day[str(d)] = int(n)
            if d.day == 1 and d.weekday() < 5 or (d.day <= 3 and d.weekday() == 0):
                print(f"  {d:%Y-%m}: {len(per_day):,} days so far, {time.time() - t0:.0f}s", flush=True)
            d += dt.timedelta(days=1)
    finally:
        mt5.shutdown()
    bars = pd.concat(frames, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return bars, per_day


def parity_with_mt5_bars(bars: pd.DataFrame, symbol: str) -> dict:
    p = HERE / "data" / f"{symbol}_M1.parquet"
    if not p.exists():
        return {"available": False}
    m = pd.read_parquet(p).set_index("time")
    b = bars.set_index("time")
    both = b.index.intersection(m.index)
    if not len(both):
        return {"available": True, "overlap_minutes": 0}
    out = {"available": True, "overlap_minutes": int(len(both))}
    for c in ("open", "high", "low", "close"):
        diff = (b.loc[both, c] - m.loc[both, c]).abs()
        out[f"{c}_exact_share"] = float((diff < 1e-6).mean())
        out[f"{c}_max_abs_diff"] = float(diff.max())
    out["tick_volume_ratio_median"] = float((b.loc[both, "tick_volume"] / m.loc[both, "tick_volume"]).median())
    out["spread_min_equal_share"] = float((b.loc[both, "spread"] == m.loc[both, "spread"]).mean())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--start", default="2021-09-20")
    a = ap.parse_args()
    bars, per_day = build(a.symbol, dt.date.fromisoformat(a.start))
    (HERE / "data").mkdir(exist_ok=True)
    path = HERE / "data" / f"{a.symbol}_M1_ticks.parquet"
    bars.to_parquet(path, index=False)
    t = pd.to_datetime(bars["time"], unit="s")
    man = {"symbol": a.symbol, "source": "MT5 copy_ticks_range, COPY_TICKS_ALL, aggregated to M1 bid and ask OHLC",
           "window_ny": "08:30-17:10 (server = NY + 7 h)",
           "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "days_with_ticks": len(per_day), "first_day": min(per_day), "last_day": max(per_day),
           "ticks_total": int(sum(per_day.values())), "rows": int(len(bars)),
           "rows_per_year": {str(k): int(v) for k, v in t.dt.year.value_counts().sort_index().items()},
           "spread_points_median": float(bars["spread"].median()),
           "parity_vs_mt5_m1": parity_with_mt5_bars(bars, a.symbol),
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (HERE / "specs" / f"{a.symbol}_M1_ticks_manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in man.items() if k != "sha256"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
