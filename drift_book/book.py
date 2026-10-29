"""The drift book: long-only, inverse-volatility weights, a market is only held while it is above its 200-day average,
rebalanced once a week. Same rules as the pre-registered D2 book in forex/ea_research/swapfree_drift.py, written again
for daily closes so it can run on free data.

Three ways of paying for the overnight holding are compared:
  swap_free  only the trading cost of rebalancing (the swap-free MT5 account)
  cfd_swap   a normal CFD account: cash rate + broker markup a year on the gross position, charged per calendar day
  futures    the cash rate built into the futures price, plus a roll every quarter (dividends ignored)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VOL_DAYS = 60    # window for the volatility estimate
SMA_DAYS = 200   # trend filter length


@dataclass(frozen=True)
class Costs:
    trade_bps: float = 2.0       # cost per unit traded (half spread plus slippage), in basis points
    swap_markup: float = 0.025   # CFD swap above the cash rate, a year
    roll_months: tuple = (3, 6, 9, 12)  # futures roll months (rolled in the month before)


def target_weights(closes: pd.DataFrame, trend_filter: bool = True) -> pd.Series:
    """Weights decided with the closes up to and including the last row. They sum to 1 when every market is above
    its average; a market below it gets 0 and its share is not given to the others."""
    zero = pd.Series(0.0, index=closes.columns)
    if len(closes) < SMA_DAYS:
        return zero
    vol = np.log(closes).diff().iloc[-VOL_DAYS:].std()
    w = (1 / vol) / (1 / vol).sum()
    if trend_filter:
        w = w * (closes.iloc[-1] > closes.iloc[-SMA_DAYS:].mean())
    return w.fillna(0.0)


def last_day_of(index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    """Last trading day in each calendar period ("W" for weeks, "M" for months)."""
    return pd.DatetimeIndex(index.to_series().groupby(index.to_period(freq)).max().to_numpy())


def roll_days(index: pd.DatetimeIndex, months: tuple) -> pd.DatetimeIndex:
    """Last trading day of the month before each roll month."""
    before = [(m - 2) % 12 + 1 for m in months]
    last = last_day_of(index, "M")
    return last[last.month.isin(before)]


def backtest(prices: pd.DataFrame, cash: pd.Series, costs: Costs = Costs(), trend_filter: bool = True) -> pd.DataFrame:
    """Daily returns of the book as a fraction of its value, one column per way of paying for the holding.
    Positions are set at a week's last close and earn the returns from the next day on."""
    rets = prices.pct_change().fillna(0.0)
    rebal = set(last_day_of(prices.index, "W"))
    rolls = set(roll_days(prices.index, costs.roll_months))
    gap_days = prices.index.to_series().diff().dt.days.fillna(1).to_numpy()

    hold = pd.Series(0.0, index=prices.columns)  # value in each market, per 1 of book value at the last close
    rows = []
    for i, day in enumerate(prices.index):
        exposure = float(hold.sum())  # what was held overnight into this day
        gross = float((hold * rets.loc[day]).sum())
        hold = hold * (1 + rets.loc[day])
        nav = 1 + gross
        trade = 0.0
        if day in rebal:
            target = target_weights(prices.iloc[: i + 1], trend_filter) * nav
            trade = float((target - hold).abs().sum()) / nav
            hold = target
        hold = hold / nav
        rate = cash.loc[day] * gap_days[i] / 365
        trading = trade * costs.trade_bps / 1e4
        roll = 2 * float(hold.sum()) * costs.trade_bps / 1e4 if day in rolls else 0.0
        rows.append((day, gross, trading,
                     exposure * (rate + costs.swap_markup * gap_days[i] / 365),
                     exposure * rate + roll, float(hold.sum())))
    out = pd.DataFrame(rows, columns=["day", "gross", "trading", "swap", "futures_carry", "exposure"]).set_index("day")
    out["swap_free"] = out.gross - out.trading
    out["cfd_swap"] = out.swap_free - out.swap
    out["futures"] = out.swap_free - out.futures_carry
    return out


def stats(r: pd.Series) -> dict:
    """Annualised summary of a daily return series."""
    eq = (1 + r).cumprod()
    years = max((r.index[-1] - r.index[0]).days / 365.25, 1 / 365.25)
    sd = r.std() * np.sqrt(252)
    return {
        "return": eq.iloc[-1] ** (1 / years) - 1,
        "vol": sd,
        "sharpe": r.mean() * 252 / sd if sd > 0 else 0.0,
        "max_dd": float((eq / eq.cummax() - 1).min()),
    }
