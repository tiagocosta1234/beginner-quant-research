"""Free daily data for the drift book: Yahoo Finance's public chart endpoint, cached as CSV under data/drift_book/.

Everything is converted to USD. The book's universe is the same five markets as the MT5 version (S&P 500, Nasdaq-100,
DAX, Nikkei 225, gold), but on index levels and an ETF instead of broker CFD quotes, so the numbers will not match it exactly.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CACHE = Path("data/drift_book")
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={a}&period2={b}&interval=1d"

# market -> (Yahoo symbol, FX symbol used to convert to USD, how to apply it)
MARKETS = {
    "SP500": ("^GSPC", None, None),
    "NASDAQ100": ("^NDX", None, None),
    "DAX": ("^GDAXI", "EURUSD=X", "mul"),   # EUR -> USD: multiply by EURUSD
    "NIKKEI": ("^N225", "JPY=X", "div"),     # JPY -> USD: divide by USDJPY
    "GOLD": ("GLD", None, None),             # gold ETF: no futures roll jumps
}
CASH_RATE = "^IRX"  # 13-week T-bill yield, in percent a year


def fetch(sym: str, start: str = "2009-01-01") -> pd.Series:
    """Daily closes for one symbol, indexed by the exchange's local date."""
    a = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    b = int(time.time())
    req = urllib.request.Request(URL.format(sym=urllib.request.quote(sym), a=a, b=b), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 0)
    days = [datetime.fromtimestamp(t + off, tz=timezone.utc).date() for t in res["timestamp"]]
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(days), name=sym, dtype=float)
    return s[~s.index.duplicated(keep="last")].dropna()


def cached(sym: str, refresh: bool = False) -> pd.Series:
    path = CACHE / (sym.replace("^", "").replace("=", "_") + ".csv")
    if path.exists() and not refresh:
        return pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    s = fetch(sym)
    path.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(path)
    return s


def to_usd(local: pd.Series, fx: pd.Series, how: str) -> pd.Series:
    """Convert a local-currency price series with the last FX close at or before each date."""
    rate = fx.reindex(local.index, method="ffill")
    return (local * rate if how == "mul" else local / rate).dropna()


def load(refresh: bool = False) -> tuple[pd.DataFrame, pd.Series]:
    """USD closes of the five markets (forward-filled over each market's own holidays) and the cash rate as a fraction a year."""
    cols = {}
    for name, (sym, fx, how) in MARKETS.items():
        s = cached(sym, refresh)
        cols[name] = to_usd(s, cached(fx, refresh), how) if fx else s
    prices = pd.DataFrame(cols).sort_index().ffill().dropna()
    cash = (cached(CASH_RATE, refresh) / 100).reindex(prices.index, method="ffill").fillna(0.0)
    return prices, cash
