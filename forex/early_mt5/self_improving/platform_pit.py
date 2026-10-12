"""Point-in-time data platform for the self-improving trader (PREREG_SELF_IMPROVING.md).
One row per (market, day) at the decision bar; every feature uses closes up to and including that day only.
   python -m mt5broker.self_improving.platform_pit            (prints coverage)"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from mt5broker.ea_research import dip_addon as DA

DEC_HM = {"SP": 1559, "NSDQ": 1559, "DOW": 1559, "DAX": 1729}      # one minute before the cash close
MARKETS = tuple(DEC_HM)
DEV = ("2022-01-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30")
_RAW = {}


def raw(m):
    if m not in _RAW: _RAW[m] = DA.load(m)
    return _RAW[m]


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def table(m, placebo_seed=None):
    """Daily point-in-time table: t (epoch s of the bar), b (bid), a (ask) and the indicator columns every spec may use.
    placebo_seed: rebuild the bid path from 20-day-block permutations of the real log returns (spreads kept) -> a world without structure."""
    d = raw(m); s = d[d.hm == DEC_HM[m]].drop_duplicates("date").set_index("date")[["t", "bo", "ao"]].rename(columns={"bo": "b", "ao": "a"})
    if placebo_seed is not None:
        rng = np.random.default_rng(placebo_seed + zlib.crc32(m.encode()) % 1000); sp = (s.a - s.b).values / s.b.values; lr = np.log(s.b).diff().fillna(0.0).values[1:]
        blocks = [lr[i:i + 20] for i in range(0, len(lr), 20)]; order = rng.permutation(len(blocks)); new = np.concatenate([blocks[i] for i in order])
        b = s.b.iloc[0] * np.exp(np.concatenate([[0.0], np.cumsum(new)])); s = s.copy(); s["b"] = b; s["a"] = b * (1 + sp)
    c = s.b; r = c.pct_change(); sd20 = r.rolling(20, min_periods=15).std()
    out = s.copy(); out["sd"] = r.rolling(60, min_periods=40).std(); out["volhi"] = (sd20 > sd20.rolling(250, min_periods=120).median()).astype(float)
    out.loc[sd20.isna() | sd20.rolling(250, min_periods=120).median().isna(), "volhi"] = np.nan
    for n in (2, 3, 4): out[f"rsi{n}"] = rsi(c, n)
    for L in (5, 10, 20, 100, 200): out[f"sma{L}"] = c.rolling(L).mean()
    for k in (2, 3, 5, 7, 10): out[f"low{k}"] = (c <= c.rolling(k).min()).astype(float)
    for k in (20, 50, 100): out[f"hi{k}"] = (c >= c.rolling(k).max()).astype(float)
    return out


def tables(placebo_seed=None): return {m: table(m, placebo_seed) for m in MARKETS}


def drifts(tab):
    """v2 null baseline: mean daily simple return of each market through 2025-12-31 (HOLD not used)."""
    return {m: float(t.b.pct_change()[:'2025-12-31'].mean()) for m, t in tab.items()}


def window(lo_hi, idx): return (idx >= pd.Timestamp(lo_hi[0])) & (idx <= pd.Timestamp(lo_hi[1]))


if __name__ == "__main__":
    for m, t in tables().items():
        print(f"{m}: {len(t)} decision days {t.index[0].date()}..{t.index[-1].date()} | with RSI2+SMA200+vol {t[['rsi2', 'sma200', 'volhi']].notna().all(axis=1).sum()} | median spread {1e4 * ((t.a - t.b) / t.b).median():.2f} bp")
