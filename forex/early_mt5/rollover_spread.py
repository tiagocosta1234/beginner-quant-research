"""
Measure the real bid/ask spread of the swap-free daily window (read-only; sends no orders). The window is one MT5
server day (D1 bar): enter 5-10 minutes after the instrument's own first tick of the server day, exit 5-10 minutes
before its own last tick (indices re-open at 18:00 New York, forex at 17:00; the instrument's own clock is used, so no
fixed time is assumed). Samples every 13th weekday from 2024-10-01 to 2026-09-30 per symbol (about 40 days), takes the
median tick spread in each 5-minute sample, and saves the median and 90th percentile (price units and as a share of
price) to forex/early_mt5/specs/rollover_spreads.json.

  python -m mt5broker.rollover_spread SYMBOL [SYMBOL ...]      (defaults to mt5broker.universe.ALL)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.data_pull import attach
from mt5broker.universe import ALL

HERE = Path(__file__).resolve().parent
START, END, STEP = dt.date(2024, 10, 1), dt.date(2026, 9, 30), 13


def sample_days():
    d, k, out = START, 0, []
    while d <= END:
        if d.weekday() < 5:
            if k % STEP == 0:
                out.append(d)
            k += 1
        d += dt.timedelta(days=1)
    return out


def day_ticks(mt5, symbol, d: dt.date):
    """All ticks of server day d (00:00-24:00 server time)."""
    a = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)
    t = mt5.copy_ticks_range(symbol, a, a + dt.timedelta(days=1), mt5.COPY_TICKS_ALL)
    if t is None or len(t) == 0:
        return None
    return t[(t["bid"] > 0) & (t["ask"] > 0)]


def window_spreads(t):
    """(entry spread, entry mid, exit spread) from one day's ticks, or None."""
    ms = t["time_msc"]
    t0, t1 = ms[0], ms[-1]
    if t1 - t0 < 3600_000:
        return None
    a = t[(ms >= t0 + 300_000) & (ms <= t0 + 600_000)]
    b = t[(ms >= t1 - 600_000) & (ms <= t1 - 300_000)]
    if len(a) == 0 or len(b) == 0:
        return None
    return float(np.median(a["ask"] - a["bid"])), float(np.median((a["ask"] + a["bid"]) / 2)), float(np.median(b["ask"] - b["bid"]))


def main() -> int:
    syms = sys.argv[1:] or ALL
    path = HERE / "specs" / "rollover_spreads.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    mt5 = attach()
    try:
        days = sample_days()
        for s in syms:
            t0 = time.time()
            mt5.symbol_select(s, True)
            r = {"in": [], "out": [], "px": []}
            for d in days:
                t = day_ticks(mt5, s, d)
                w = window_spreads(t) if t is not None else None
                if w:
                    r["in"].append(w[0]); r["px"].append(w[1]); r["out"].append(w[2])
            if r["in"] and r["out"]:
                px = float(np.median(r["px"]))
                res[s] = dict(n_in=len(r["in"]), n_out=len(r["out"]), spread_in_med=float(np.median(r["in"])), spread_in_p90=float(np.quantile(r["in"], 0.9)),
                              spread_out_med=float(np.median(r["out"])), spread_out_p90=float(np.quantile(r["out"], 0.9)), price_med=px,
                              in_pct=float(np.median(r["in"]) / px), out_pct=float(np.median(r["out"]) / px))
            else:
                res[s] = dict(n_in=len(r["in"]), n_out=len(r["out"]), note="no ticks")
            print(f"{s:12s} in {res[s].get('in_pct', float('nan')) * 1e4:6.2f} bp  out {res[s].get('out_pct', float('nan')) * 1e4:6.2f} bp  "
                  f"(n {len(r['in'])}/{len(r['out'])}, {time.time() - t0:.0f}s)", flush=True)
            path.write_text(json.dumps(res, indent=1))
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
