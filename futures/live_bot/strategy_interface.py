"""Minimal interface a trading strategy plugs into.

Whatever strategy survives walk-forward validation (see
futures/docs/EDGE_VALIDATION_RESULTS.md for the current state of that
search — as of 2026-09-18, nothing has passed yet) should be implemented as a
subclass of `Strategy` below and dropped into main.py in place of
`NoOpStrategy`. This file intentionally contains no real trading logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class SignalAction(Enum):
    HOLD = auto()
    ENTER_LONG = auto()
    ENTER_SHORT = auto()
    EXIT = auto()


@dataclass
class Signal:
    action: SignalAction
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    size: int = 1
    reason: str = ""
    # Dollar risk this signal intends to take if filled and stopped out (size *
    # |entry - stop| * the instrument's point value). Only the strategy knows
    # this at signal time -- main.py can't derive it for a market entry, since
    # the fill price isn't known until after the order is placed. Required for
    # ENTER_LONG/ENTER_SHORT (main.py refuses to place a bracket order without
    # it, same as it already does for stop_loss_price/take_profit_price), so
    # RiskGovernor.check_position_size() can gate every entry before it happens.
    risk_dollars: float | None = None
    # Alternative to stop_loss_price/take_profit_price for a trailing-stop exit
    # (no fixed target): the price-point DISTANCE the stop should trail behind
    # the current favorable price, and the price-point distance from entry to
    # the INITIAL stop (used only to size the position from risk_dollars, since
    # a trailing exit has no fixed price to anchor the risk calculation to). A
    # strategy sets these two INSTEAD OF stop_loss_price/take_profit_price, not
    # alongside them -- main.py branches on which pair is populated. See
    # `random_entry_atr_trail_strategy.py` for the one strategy that uses this
    # shape; every earlier strategy in this repo's research used a fixed
    # stop/target instead.
    initial_stop_distance_points: float | None = None
    trail_distance_points: float | None = None
    # Dollar profit this signal intends to realize if filled and its target is
    # hit (the mirror image of risk_dollars). Added 2026-09-24 so
    # RiskGovernor.check_position_size() can PREEMPTIVELY refuse an entry whose
    # own best case would breach max_daily_profit (rule 12), the same way
    # risk_dollars already lets it preemptively refuse one whose own worst case
    # would breach self_imposed_daily_stop (rule 8) -- a reactive-only check
    # (react after a fill already breached the cap) was proven insufficient in
    # the backtest engine (round76's resolve_outcomes_gated) after two
    # individually-compliant wins the same real day still summed past a
    # $1,650 cap. Optional: only strategies with a fixed target (the bracket
    # shape) can know this before a fill; trailing-stop strategies leave it
    # None, and max_daily_profit then falls back to reactive-only enforcement
    # for them.
    expected_reward_dollars: float | None = None
    # The price the strategy planned the entry at -- the one its stop_loss_price
    # was measured from (e.g. the 09:30 bar's open). When set, main.py moves the
    # stop after the market entry fills so it keeps the planned distance from the
    # ACTUAL fill: added 2026-09-30 after a short planned at 30,701.50 filled at
    # 30,690.75 and the stop, left at the planned price, turned a $294 risk into
    # a $358.50 loss. None = the stop stays exactly where the strategy put it.
    entry_reference_price: float | None = None


class Strategy(ABC):
    """Subclass this. `on_bar` is called once per new closed bar for the configured
    instrument/timeframe; it must be a pure function of `bars` and the strategy's
    own internal state — it must NOT place orders, check account balance, or know
    about risk limits. All of that lives in risk_governor.py / main.py, so a
    strategy bug can never bypass the risk governance layer.
    """

    @abstractmethod
    def on_bar(self, bars: Any) -> Signal:
        """Given the latest bars (most recent last), return a Signal.

        `bars` shape depends on broker_client.get_bars()'s return type (currently
        whatever brokerapi_py's `data.get_bars()` returns — verify and, if useful,
        wrap it in a small typed struct here once that's confirmed against a real
        connection).
        """
        raise NotImplementedError


class NoOpStrategy(Strategy):
    """Always holds. Exists only to prove the pipeline runs end-to-end with zero
    trading risk — this is NOT a real strategy and must be replaced before any
    practice or live run is expected to actually trade.
    """

    def on_bar(self, bars: Any) -> Signal:
        return Signal(action=SignalAction.HOLD, reason="NoOpStrategy: pipeline smoke test only")
