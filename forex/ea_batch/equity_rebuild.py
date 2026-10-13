"""Round 347c -- rebuild an EA's intraday EQUITY (floating losses included) from its deal list and MT5 broker's own XAUUSD 1-minute bid/ask bars.

WHY: closed-deal daily P&L hides floating losses, so a replay that only looks at closed trades can call an attempt safe while the account's equity crossed the loss limit
in the middle of the day. The tester reports one number for this (Equity Drawdown Maximal); this module recovers WHEN it happened, per day, so a replay can test the limits
against equity the way MT5 broker and Broker do ("equity cannot drop below the floor at any moment").

METHOD (all at the tested lot, 0.01; scale linearly for other lots):
  * pair each 'out' deal with the open 'in' deal whose entry price reproduces its profit exactly: profit = side * (exit - entry) * volume * 100 (XAUUSD: 100 oz per lot). That also
    gives the side (buy / sell), which the deal list does not record. The largest residual is reported; it must be at rounding level.
  * for each minute a position is open, its floating P&L is marked at the bar's WORST price: bid low for a buy, ask high for a sell (conservative: a hedged book cannot hit both
    extremes in the same minute). The entry bar is marked at the close (so the spread cost shows) and the exit bar carries only the realized result.
  * equity(minute) = realized so far (profit + commission + swap) + floating. Per day, m = the lowest equity of the day relative to the day's opening balance; v = the day's
    realized P&L. m <= v by construction.
  * VALIDATION: the maximal peak-to-trough equity drawdown of the rebuilt curve against the tester's own "Equity Drawdown Maximal". Two marks are computed, the worst-price one
    above and a close-price one; the tester (ticks) must fall between them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CONTRACT = 100.0        # XAUUSD: ounces per lot


def pair_positions(deals: pd.DataFrame) -> pd.DataFrame:
    """One row per position: te, tx, entry/exit price, volume, side (+1 buy, -1 sell), residual of the profit match."""
    d = deals.copy()
    d["t"] = pd.to_datetime(d.time.astype(str).str.replace(".", "-", regex=False))
    open_pos, out = [], []
    for r in d.itertuples():
        if r.direction == "in":
            open_pos.append((r.t, r.price, r.volume))
            continue
        best = None
        for j, (te, pe, v) in enumerate(open_pos):
            for side in (1, -1):
                res = abs(r.profit - side * (r.price - pe) * v * CONTRACT)
                if best is None or res < best[0] - 1e-12:
                    best = (res, j, side)
        if best is None:
            continue
        res, j, side = best
        te, pe, v = open_pos.pop(j)
        out.append(dict(te=te, tx=r.t, pe=pe, px=r.price, v=v, side=side, resid=res))
    return pd.DataFrame(out)


def rebuild(deals: pd.DataFrame, bars: pd.DataFrame, start: str, end: str):
    """(per-day frame with v / m_worst / m_close at the tested lot, validation dict). `bars` is indexed by minute timestamp (server clock), as in forex/data/XAUUSD_M1_ticks_full.parquet."""
    pos = pair_positions(deals)
    bx = bars.loc[pd.Timestamp(start): pd.Timestamp(end) + pd.Timedelta(days=1)]
    ts = bx.index.values
    n = len(bx)
    low, high, close = bx["low"].values, bx["ask_high"].values, bx["close"].values        # bid low / ask high for the worst marks
    ask_close = bx["ask_close"].values
    real = np.zeros(n + 1)
    d = deals.copy()
    d["t"] = pd.to_datetime(d.time.astype(str).str.replace(".", "-", regex=False))
    d["net"] = d.profit + d.commission + d.swap
    idx = np.clip(np.searchsorted(ts, d.t.values.astype("datetime64[ns]")), 0, n - 1)
    np.add.at(real, idx, d.net.values)
    R = np.cumsum(real[:n])                                                              # realized so far, per minute
    Fw, Fc = np.zeros(n), np.zeros(n)
    for p in pos.itertuples():
        i0 = int(np.clip(np.searchsorted(ts, np.datetime64(p.te)), 0, n - 1)); i1 = int(np.clip(np.searchsorted(ts, np.datetime64(p.tx)), 0, n - 1))
        k = p.v * CONTRACT
        if p.side == 1:
            Fc[i0:i1] += (close[i0:i1] - p.pe) * k
            if i1 - i0 > 1:
                Fw[i0 + 1:i1] += (low[i0 + 1:i1] - p.pe) * k
            Fw[i0] += (close[i0] - p.pe) * k
        else:
            Fc[i0:i1] += (p.pe - ask_close[i0:i1]) * k
            if i1 - i0 > 1:
                Fw[i0 + 1:i1] += (p.pe - high[i0 + 1:i1]) * k
            Fw[i0] += (p.pe - ask_close[i0]) * k
    eq_w, eq_c = R + Fw, R + Fc
    day = pd.DatetimeIndex(ts).normalize()
    df = pd.DataFrame({"day": day, "R": R, "ew": eq_w, "ec": eq_c})
    g = df.groupby("day")
    realized_by_day = pd.Series(d.net.values, index=d.t.dt.normalize()).groupby(level=0).sum()
    days = g.ew.min().index
    cum = realized_by_day.cumsum()
    union = days.union(cum.index)
    b0 = cum.reindex(union).ffill().fillna(0.0).shift(1).fillna(0.0).reindex(days)      # realized strictly before each day = the balance change at its open
    v = realized_by_day.reindex(days).fillna(0.0)
    out = pd.DataFrame({"v": v, "m_worst": g.ew.min() - b0.values, "m_close": g.ec.min() - b0.values}, index=days)
    out["m_worst"] = np.minimum(out.m_worst, out.v); out["m_close"] = np.minimum(out.m_close, out.v)

    def maxdd(eq):
        e = np.concatenate([[0.0], eq])
        return float((np.maximum.accumulate(e) - e).max())
    val = dict(positions=len(pos), max_resid=float(pos.resid.max()) if len(pos) else float("nan"), buys=int((pos.side == 1).sum()), sells=int((pos.side == -1).sum()),
               net=float(d.net.sum()), dd_close=maxdd(eq_c), dd_worst=maxdd(eq_w))
    return out, val
