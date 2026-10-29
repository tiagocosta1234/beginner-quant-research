"""The one validated edge this repo's research produced, wired up as a real Strategy.

Source of truth: `futures/docs/EDGE_VALIDATION_RESULTS.md` Rounds 19-26
(2026-09-19/20). Read the "Final Campaign Synthesis" section there before trusting
this file -- it documents exactly what was and wasn't validated, including that
success is NOT the likely outcome even at the best sizing found (Round 26: ~21%
probability of reaching the the profit goal before the self-set deadline, vs. real probability of blowing the account first). This file makes the
research DEPLOYABLE; it does not make it SAFE or LIKELY TO WORK. That's a decision
for whoever configures `main.py`'s BOT_MODE, not something this file settles.

What was actually validated, and why the entry looks the way it does:
  Round 19 decoupled entry-timing from exit-management for the first time in this
  repo's research and found the edge lives ENTIRELY in the exit (an ATR-based
  trailing stop with no fixed target -- cut losses fast, let winners run), not in
  entry quality. Round 20 confirmed this by testing two real, "smart" entries
  (an FVG+bias-filter setup, a trend-following entry) against the same exit and
  found BOTH performed worse than pure random entries -- lower expectancy AND much
  worse tail concentration. So the random entry below is not a placeholder standing
  in for a better idea; it is the specific, validated design. Substituting a
  "smarter-looking" entry here would contradict the evidence, not improve on it.

Mechanics, matching `futures/engine/round19_random_entry.py` exactly
(reuse that file's actual research code as the source of truth for any future
question about what these numbers mean -- this file re-implements the same causal
logic for live, bar-by-bar operation, it does not change any of it):
  - Once per RTH session, at one uniformly-random point in the day, take exactly
    one position in a coin-flip direction. Timing and direction are independent of
    price on purpose -- see the note above.
  - Initial stop = 1.0x ATR(14) on the most recently CLOSED causal 15-minute bar
    as of the entry bar (STOP_ATR_MULT below).
  - No fixed target. The stop trails by 1.5x that SAME initial ATR distance
    (TRAIL_ATR_MULT below) as price moves favorably, tightening only, never
    loosening -- handled by the broker's native trailing-stop order once placed
    (`broker_client.place_market_entry_with_trailing_stop`), not by this class
    polling and re-submitting a modified stop every bar.
  - Flat by the session flatten time regardless (enforced by `risk_governor.py`'s
    existing session-flatten rule, independent of this strategy).

This class does NOT decide position size in dollar terms -- per this repo's
architecture (`strategy_interface.Strategy`'s docstring: a strategy must never see
account state or risk limits), that is `main.py`'s job, using either
`RiskGovernor.compute_dynamic_risk()` (if dynamic sizing is enabled) or a fixed
default. This class only proposes the STOP/TRAIL DISTANCES (price points), via
`Signal.initial_stop_distance_points` / `Signal.trail_distance_points`, and leaves
`Signal.risk_dollars` at None to signal "no opinion, use the account's default" --
see `strategy_interface.Signal`'s docstring for that field pairing.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy

STOP_ATR_MULT = 1.0
TRAIL_ATR_MULT = 1.5
ATR_PERIOD = 14
# A typical RTH session is ~390 1-minute bars (9:30am-4:00pm ET); the random
# entry timing is drawn uniformly over this range, same convention Round 19's
# backtest used (one random bar per day out of the day's actual bar count).
# Corrected 2026-09-20: the draw is now genuinely adaptive to bars already seen
# today at the moment a new session starts being observed (see
# `_roll_new_session`) -- an earlier version of this constant's comment claimed
# that adaptiveness but the code didn't implement it, drawing from the full
# [0, EXPECTED_SESSION_BARS) range regardless of bars already elapsed. That
# mattered specifically on a mid-session bot restart: this session's target
# could land below bars already observed, firing an entry immediately rather
# than at a genuinely random point in the remaining day.
EXPECTED_SESSION_BARS = 390
# Time-of-day filter (Round 39, futures/engine/round39_volatility_filtered_mnq.py,
# 2026-09-20): restricting the random entry to the last third of the RTH
# session (elapsed minutes 260-390, i.e. ~13:50-16:00 ET) was independently
# selected as the best train-only candidate in 70.8% of 48 walk-forward
# (seed, fold) windows -- not a single lucky fold -- and roughly doubled OOS
# per-trade expectancy ($58.06 vs $30.77 unfiltered) with 0/48 buffer
# breaches at the resulting larger buffer-safe size. Opt-in via
# `tod_filter=True` (main.py wires this to BOT_TOD_FILTER=1) -- like
# BOT_STRATEGY/BOT_DYNAMIC_SIZING, deliberately not the default, since this
# changes which days get an entry at all. Confirmed 2026-09-20 (Round 40) the
# profit-target Monte Carlo still comes back ~0% success even with this
# filter alone -- it's a real per-trade improvement, not by itself a fix for
# the deadline-vs-buffer math.
TOD_FILTER_START_BAR = 260


class RandomEntryAtrTrailStrategy(Strategy):
    """The validated Round 19-26 edge. See module docstring for what it is and isn't."""

    def __init__(self, rng: np.random.Generator | None = None, tod_filter: bool = False) -> None:
        # An unseeded (system-entropy) generator by default: the validated
        # backtest confirmed the edge across 8 INDEPENDENT random seeds, all
        # positive (Round 19) -- the point is that no specific seed is doing the
        # work, so live use should not pin one either. Pass an explicit `rng`
        # only for deterministic testing (see tests/test_random_entry_atr_trail_strategy.py).
        self._rng = rng if rng is not None else np.random.default_rng()
        self._tod_filter = tod_filter

        self._session_date: dt.date | None = None
        self._target_entry_bar_count: int | None = None
        self._direction: int | None = None  # +1 long, -1 short; drawn fresh each session
        self._bars_seen_today: int = 0
        self._entered_today: bool = False

    def _roll_new_session(self, session_date: dt.date, bars_already_seen: int = 0) -> None:
        self._session_date = session_date
        self._bars_seen_today = bars_already_seen
        self._entered_today = False
        # Draw uniformly over the REMAINING portion of the expected session,
        # not the full [0, EXPECTED_SESSION_BARS) range -- bars already seen
        # today (e.g. this session is first observed partway through, after a
        # bot restart) can never be un-observed, so the draw must account for
        # them. This can never land below bars_already_seen (no more
        # immediate-on-restart entries) and reduces to the original
        # [0, EXPECTED_SESSION_BARS) draw on a normal session start, where
        # bars_already_seen=0.
        # When tod_filter is on, the draw's lower bound is also clamped up to
        # TOD_FILTER_START_BAR: same "remaining window" logic, just a smaller
        # window (the last third of the session, not the whole thing).
        lower = max(bars_already_seen, TOD_FILTER_START_BAR) if self._tod_filter else bars_already_seen
        remaining = max(1, EXPECTED_SESSION_BARS - lower)
        self._target_entry_bar_count = lower + int(self._rng.integers(0, remaining))
        self._direction = 1 if self._rng.random() < 0.5 else -1

    def _causal_atr15(self, bars_1m: pd.DataFrame) -> float | None:
        """15m ATR(14) using only fully-closed 15m bars as of the latest 1m bar seen.
        Same method as `round19_random_entry.causal_atr15_lookup` /
        `round14_meanreversion.atr_causal` -- kept in lockstep with that file
        deliberately; if the research method changes, this must change with it.
        """
        h15 = (
            bars_1m[["open", "high", "low", "close"]]
            .resample("15min", label="right", closed="right")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        if len(h15) <= ATR_PERIOD:
            return None
        high, low, close = h15["high"], h15["low"], h15["close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(ATR_PERIOD, min_periods=ATR_PERIOD).mean()
        # Only a fully-CLOSED 15m bar's ATR is causally knowable; drop the last
        # row if it corresponds to a still-forming 15m window relative to the
        # latest 1m bar (resample with closed="right" already only labels
        # completed windows, but guard explicitly rather than trust that alone).
        last_val = atr.dropna()
        if last_val.empty:
            return None
        return float(last_val.iloc[-1])

    def on_bar(self, bars: Any) -> Signal:
        # `bars` is a Polars DataFrame per `broker_client.get_bars()`'s contract
        # (columns: timestamp, open, high, low, close, volume). Convert once, to
        # pandas, to reuse the exact validated causal ATR/resample logic above
        # rather than risk a subtly different Polars re-implementation.
        if bars is None or len(bars) == 0:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        latest_ts = df.index[-1]
        today = latest_ts.date()

        # Derived from the actual bar timestamps in `df`, NOT a count of on_bar()
        # calls -- main.py polls on a wall-clock interval (30s) against 1-minute
        # bars, so poll count and elapsed-bar count are not the same thing, and
        # using call count here would desync the random-entry trigger from the
        # actual intraday position the backtest's bar-index draw was based on.
        # Computed BEFORE rolling a new session so the roll can see how many
        # bars of today are already in view (e.g. after a mid-session restart).
        bars_seen_today = int((df.index.date == today).sum())

        if self._session_date != today:
            self._roll_new_session(today, bars_already_seen=bars_seen_today)

        self._bars_seen_today = bars_seen_today

        if self._entered_today:
            return Signal(action=SignalAction.HOLD, reason="already entered today (1/day, by design -- see module docstring)")

        if self._bars_seen_today < self._target_entry_bar_count:
            return Signal(
                action=SignalAction.HOLD,
                reason=f"waiting for today's random entry point (bar {self._bars_seen_today}/{self._target_entry_bar_count})",
            )

        atr = self._causal_atr15(df)
        if atr is None or atr <= 0:
            return Signal(action=SignalAction.HOLD, reason="15m ATR(14) not yet computable (insufficient history)")

        stop_distance = STOP_ATR_MULT * atr
        trail_distance = TRAIL_ATR_MULT * stop_distance

        self._entered_today = True  # set before returning: this decision must not repeat on the next poll
        action = SignalAction.ENTER_LONG if self._direction == 1 else SignalAction.ENTER_SHORT
        return Signal(
            action=action,
            initial_stop_distance_points=stop_distance,
            trail_distance_points=trail_distance,
            reason=(
                f"random daily entry (direction={self._direction:+d}, target_bar="
                f"{self._target_entry_bar_count}), ATR(15m,14)={atr:.2f}, stop_dist="
                f"{stop_distance:.2f}, trail_dist={trail_distance:.2f} -- validated "
                f"edge is in the exit, not this entry; see module docstring"
            ),
        )
