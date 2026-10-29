"""The combined time-of-day filter + VWAP-Z edge (Rounds 57-59), run as one Strategy in one
process, since both trade MNQ and two processes could open a double position.

Composition, not reimplementation: wraps one `RandomEntryAtrTrailStrategy` (`tod_filter=True`,
the Round 39 last-third-of-session variant) and one `VwapZScoreStrategy`, calls both every bar
and returns whichever fires; on the rare same-bar tie, TOD wins. Each source carries its own
`Signal.risk_dollars` (TOD_RISK, VWAPZ_RISK below), the one field neither wrapped class sets.

Sizing lesson (Round 69): every resolver first sized contracts against the tight initial stop
distance, while the stop actually sits at the wider trail distance (1.5x), so a "$2,400 risk"
trade could lose about $3,600. Contracts are now sized against the true stop distance, and a
pre-emptive daily stop (risk_governor rule 8) refuses an entry whose own worst case could cross
the day's ceiling. Over the full history the worst day under that rule stayed inside the cap.
The edge depends on a minority of large winning days (median day negative), and it did not
hold up out of sample.

One position at a time and the daily loss limit are enforced by main.py and the risk governor
for every strategy, so this file does not implement them.
"""

from __future__ import annotations

from typing import Any

from live_bot.random_entry_atr_trail_strategy import RandomEntryAtrTrailStrategy
from live_bot.strategy_interface import Signal, SignalAction, Strategy
from live_bot.vwap_zscore_strategy import VwapZScoreStrategy

TOD_RISK = 1680.0   # example sizing; set to your own risk
VWAPZ_RISK = 1200.0


class ManualStrategy(Strategy):
    """TOD filter + VWAP-Z combined, with per-source risk (see the module docstring)."""

    def __init__(self, tod: Strategy | None = None, vwapz: Strategy | None = None) -> None:
        # Injectable for testing the priority/tie-break logic in isolation
        # (see tests/test_manual_strategy.py); real use always takes the defaults.
        self._tod = tod if tod is not None else RandomEntryAtrTrailStrategy(tod_filter=True)
        self._vwapz = vwapz if vwapz is not None else VwapZScoreStrategy()

    def on_bar(self, bars: Any) -> Signal:
        # Both are called every bar regardless of which one's result is used --
        # RandomEntryAtrTrailStrategy's per-session state (_entered_today) is
        # meant to advance this way: its random pick for the day is drawn once
        # and consumed whether or not the trader ultimately takes it, matching Round
        # 57's backtest (sig_tod's one candidate per session is generated
        # independently of gating and only discarded afterward if it overlaps
        # an already-open position). VwapZScoreStrategy is fully stateless, so
        # calling it every bar has no side effect to worry about either way.
        tod_signal = self._tod.on_bar(bars)
        vwapz_signal = self._vwapz.on_bar(bars)

        if tod_signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            return Signal(
                action=tod_signal.action,
                initial_stop_distance_points=tod_signal.initial_stop_distance_points,
                trail_distance_points=tod_signal.trail_distance_points,
                risk_dollars=TOD_RISK,
                reason=f"[the trader/TOD ${TOD_RISK:.0f}] {tod_signal.reason}",
            )
        if vwapz_signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            return Signal(
                action=vwapz_signal.action,
                initial_stop_distance_points=vwapz_signal.initial_stop_distance_points,
                trail_distance_points=vwapz_signal.trail_distance_points,
                risk_dollars=VWAPZ_RISK,
                reason=f"[the trader/VWAP-Z ${VWAPZ_RISK:.0f}] {vwapz_signal.reason}",
            )
        return Signal(action=SignalAction.HOLD, reason="the trader: neither TOD nor VWAP-Z fired this bar")
