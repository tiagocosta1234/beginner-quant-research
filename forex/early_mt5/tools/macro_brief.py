"""Daily macro brief for the MT5 broker gold system: next US releases (server clock), which ones the guard flattens for, and the latest
rates / VIX read from D:/finance/data_macro. Read-only, no network.   python -m mt5broker.tools.macro_brief [--days 14]"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from mt5broker.tools.make_news_file import EVENTS, server_time

DATA = Path("D:/finance/data_macro")
FLAT_KINDS = {"CPI"}          # what ManualNews.csv holds today (make_news_file.py default); keep in sync with the live file
SERIES = {"VIXCLS": "VIX", "DGS10": "US 10y", "DGS2": "US 2y", "DFII10": "US 10y real"}


def last(name: str, back: int = 0):
    d = pd.read_csv(DATA / f"{name}.csv").dropna(); d.columns = ["date", "v"]; d["v"] = pd.to_numeric(d.v, errors="coerce"); d = d.dropna()
    return d.date.iat[-1], d.v.iat[-1], d.v.iat[-1 - back]


def main() -> int:
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 14
    now = pd.Timestamp.now(tz="Europe/Athens").tz_localize(None)       # the server clock is Europe/Athens
    print(f"MACRO BRIEF  server time {now:%Y-%m-%d %H:%M}   (next {days} days)")
    rows = sorted((server_time(d, t), k, d, t) for k, d, t in EVENTS)
    nxt = [r for r in rows if now <= r[0] <= now + pd.Timedelta(days=days)]
    for ts, k, d, t in nxt:
        left = ts - now
        flag = "guard closes all positions 2 min before, stays flat 5 min after" if k in FLAT_KINDS else "no flat: positions stay open"
        print(f"  {k:<4} {ts:%a %d %b %H:%M} server  (NY {d} {t})  in {left.days}d {left.seconds // 3600}h   {flag}")
    if not nxt: print("  no US release in the window")
    print("\nRATES / VOL (latest FRED rows on disk; refresh the CSVs before trusting a stale date)")
    vals = {}
    for s, label in SERIES.items():
        dt, v, v5 = last(s, 5); vals[s] = v; print(f"  {label:<12} {v:6.2f}   5-obs change {v - v5:+.2f}   ({dt})")
    print(f"  2s10s curve  {vals['DGS10'] - vals['DGS2']:+.2f}  ({'inverted' if vals['DGS10'] < vals['DGS2'] else 'positive'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
