"""Intraday lab (the trader /goal 2026-10-06: "not on daily timeframes, go for 1, 5 and 15 minute ... self-develop, learn from weaknesses / mistakes / flaws, note winning patterns").
Own EAs, vectorised, on MT5 1-minute BID / ASK bars (forex/early_mt5/data/<sym>_M1_ticks_full.parquet, 2021-09 .. 2026-10) resampled to 1 / 5 / 15 minutes.

EXECUTION   signal on the close of bar i, entry at the OPEN of bar i+1 on the ask (long) / bid (short); exits on the bid (long) / ask (short); stop and target are checked bar by bar on bid / ask highs and lows;
            stop first when both fall in one bar (conservative); a stop that gaps through is filled at the bar's open; time exit at the close of the last allowed bar. One position at a time per symbol.
COSTS       the real spread is inside bid / ask; commission USD 6 a lot round turn on FX and gold (MT5), none on the cash indices; optional extra slippage in spreads.
RESULT      per trade R = net P&L / stop distance; mean R, t-stat, profit factor, cost in R, by year.
PHASES      DEV 2021-10 .. 2023-12, VAL 2024, HOLDOUT 2025-01 .. 2026-10 (each candidate may touch the holdout ONCE; every use is written to lab/ledger.csv).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = Path(r"D:\finance\scratch\lab_cache"); CACHE.mkdir(parents=True, exist_ok=True)
FX = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF")
INDEX = ("US100.cash", "US30.cash", "US500.cash", "GER40.cash")
ALL = FX + ("XAUUSD",) + INDEX
PHASES = {"dev": ("2021-10-01", "2023-12-31"), "val": ("2024-01-01", "2024-12-31"), "hold": ("2025-01-01", "2026-10-02")}
POINT = {"EURUSD": 1e-5, "GBPUSD": 1e-5, "AUDUSD": 1e-5, "USDCAD": 1e-5, "USDCHF": 1e-5, "USDJPY": 1e-3, "XAUUSD": 1e-2, "US100.cash": 1e-2, "US30.cash": 1e-2, "US500.cash": 1e-2, "GER40.cash": 1e-2}


class Bars:
    def __init__(self, sym: str, tf: int):
        self.sym, self.tf = sym, tf
        f = CACHE / f"{sym}_{tf}.parquet"
        if f.exists():
            d = pd.read_parquet(f)
        else:
            m = pd.read_parquet(DATA / f"{sym}_M1_ticks_full.parquet")
            g = (m.time // (60 * tf)) * (60 * tf)
            d = m.groupby(g).agg(bo=("open", "first"), bh=("high", "max"), bl=("low", "min"), bc=("close", "last"), ao=("ask_open", "first"), ah=("ask_high", "max"), al=("ask_low", "min"), ac=("ask_close", "last"), sp=("spread", "median"))
            d.index.name = "t"; d = d.reset_index(); d.to_parquet(f)
        self.t = d.t.values.astype(np.int64)
        for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "sp"):
            setattr(self, c, d[c].values.astype(np.float64))
        self.n = len(d); self.hour = (self.t // 3600) % 24; self.minute = (self.t // 60) % 60; self.day = self.t // 86400
        self.mid = (self.bc + self.ac) / 2
        self.year = pd.to_datetime(self.t, unit="s").year.values
        self.point = POINT[sym]

    def slice_idx(self, phase: str):
        a, b = PHASES[phase]
        lo = int(pd.Timestamp(a).timestamp()); hi = int(pd.Timestamp(b).timestamp()) + 86400
        return np.flatnonzero((self.t >= lo) & (self.t < hi))

    def atr(self, n=14):
        pc = np.r_[self.bc[0], self.bc[:-1]]
        tr = np.maximum(self.bh - self.bl, np.maximum(np.abs(self.bh - pc), np.abs(self.bl - pc)))
        return pd.Series(tr).rolling(n, min_periods=n).mean().values


def commission_price(sym: str, price: float) -> float:
    """USD 6 a lot round turn expressed in price units of the quote currency."""
    if sym in INDEX:
        return 0.0
    if sym == "XAUUSD":
        return 6.0 / 100.0
    base = 6.0 / 100000.0
    return base * (price if sym in ("USDJPY", "USDCAD", "USDCHF") else 1.0)


def run(b: Bars, sig_i: np.ndarray, sig_dir: np.ndarray, stop: np.ndarray, tp_mult: float | np.ndarray, max_bars: int | np.ndarray, slip: float = 0.0, phase_mask: np.ndarray | None = None):
    """Simulate signals (indices into b) one position at a time. Returns arrays (R, entry bar, exit bar, year, cost_in_R)."""
    R, ent, ext, yrs, cst = [], [], [], [], []
    busy = -1; n = b.n
    tpm = np.broadcast_to(tp_mult, sig_i.shape); mb = np.broadcast_to(max_bars, sig_i.shape)
    for k in range(len(sig_i)):
        i = int(sig_i[k])
        if i + 1 >= n or i <= busy or stop[k] <= 0 or not np.isfinite(stop[k]):
            continue
        if phase_mask is not None and not phase_mask[i]:
            continue
        d = int(sig_dir[k]); j0 = i + 1; j1 = min(n, j0 + int(mb[k]))
        if b.t[j1 - 1] - b.t[j0] > 3 * 86400:        # never across a long gap
            j1 = j0 + int(np.searchsorted(b.t[j0:j1], b.t[j0] + 3 * 86400))
            if j1 <= j0 + 1:
                continue
        sp0 = (b.ao[j0] - b.bo[j0]) if d > 0 else 0.0
        pin = (b.ao[j0] + slip * (b.ao[j0] - b.bo[j0])) if d > 0 else (b.bo[j0] - slip * (b.ao[j0] - b.bo[j0]))
        sd = stop[k]
        if d > 0:
            sl = pin - sd; tp = pin + tpm[k] * sd
            hit_sl = b.bl[j0:j1] <= sl; hit_tp = b.bh[j0:j1] >= tp
        else:
            sl = pin + sd; tp = pin - tpm[k] * sd
            hit_sl = b.ah[j0:j1] >= sl; hit_tp = b.al[j0:j1] <= tp
        a = int(np.argmax(hit_sl)) if hit_sl.any() else 10**9; c = int(np.argmax(hit_tp)) if hit_tp.any() else 10**9
        if a == 10**9 and c == 10**9:
            jx = j1 - 1; px = b.bc[jx] if d > 0 else b.ac[jx]
        elif a <= c:
            jx = j0 + a
            op = b.bo[jx] if d > 0 else b.ao[jx]
            px = min(sl, op) if d > 0 else max(sl, op)
        else:
            jx = j0 + c; px = tp
        pnl = (px - pin) if d > 0 else (pin - px)
        com = commission_price(b.sym, pin)
        R.append((pnl - com) / sd); ent.append(j0); ext.append(jx); yrs.append(b.year[j0]); cst.append((com + (b.ao[j0] - b.bo[j0])) / sd)
        busy = jx
    return np.array(R), np.array(ent), np.array(ext), np.array(yrs), np.array(cst)


def stats(R: np.ndarray, yrs: np.ndarray | None = None, cst: np.ndarray | None = None) -> dict:
    n = len(R)
    if n < 2:
        return dict(n=n, mean=np.nan, t=np.nan, pf=np.nan, win=np.nan, cost=np.nan)
    w = R[R > 0].sum(); l = -R[R <= 0].sum()
    out = dict(n=n, mean=float(R.mean()), t=float(R.mean() / (R.std(ddof=1) / np.sqrt(n))) if R.std() > 0 else np.nan, pf=float(w / l) if l > 0 else np.inf, win=float((R > 0).mean()), cost=float(np.mean(cst)) if cst is not None else np.nan)
    return out
