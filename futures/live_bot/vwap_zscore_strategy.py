"""VWAP Z-score mean reversion (MNQ), wired up as a real Strategy -- a THIRD
edge alongside `random_entry_atr_trail_strategy.py` (MNQ) and
`support_resistance_bounce_strategy.py` (MGC).

Source of truth: `futures/engine/round49_vwap_zscore.py` for the
signal mechanics, `futures/docs/TRADING_JOURNAL.md`'s 2026-09-21
entry for how this file's numbers were checked (a real Monte Carlo sizing
search: 70% probability of reaching the account's profit target before the
real Oct 30 withdrawal deadline is NOT reachable at any risk/trade -- P(success)
asymptotes around 50-52% even at deliberately unrealistic sizes, because past
~$1,400/trade every simulated path either hits the target or hits the
account's daily loss limit/trailing floor before day 20; there is no
"neither" outcome left for more size to convert into more success). Wiring
this up makes the edge deployable for Practice-mode rehearsal; it does not
change that math, and does not make 70% achievable by itself.

What the signal is, and why the entry looks the way it does:
  Session VWAP (typical price * volume, cumulative from session open, reset
  every session -- 100% causal by construction, only ever uses bars up to and
  including the current one) is compared to price via a Z-score: (close -
  vwap) / rolling_std(close - vwap, 60 bars, min 20 bars this session). An
  entry fires when that Z-score crosses +-2.5 AND the very next bar's close
  already reverses back toward VWAP (a simple, disclosed proxy for "a 1-minute
  market-structure shift," not a full MSS detector -- see round49's own
  docstring). Direction fades the extreme: Z <= -2.5 with a reversal up ->
  long; Z >= +2.5 with a reversal down -> short.

  Exit is the SAME validated ATR-trailing mechanism every other edge in this
  repo uses (`resolve_trailing_sequential`'s convention): initial stop = 1.0x
  ATR(14) on the latest fully-closed causal 15m bar, trailing by 1.5x that
  same distance, no fixed target -- a fixed return-to-1SD target was
  deliberately NOT implemented in the Round 49 research either (disclosed
  there as a time-boxing choice, not an oversight), so this file doesn't
  invent one live.

Why this class carries NO persistent state across `on_bar` calls (unlike
`support_resistance_bounce_strategy.py`, which has to track active levels
across time): a VWAP Z-score is a pure per-bar snapshot -- it has no notion of
a "level" that persists once confirmed, so there's nothing to remember between
polls. Every call recomputes session VWAP/Z fresh from whatever window
`bars` happens to be. This sidesteps the EXACT bug class Round "EDGE_AUDIT"
found in the MGC strategy (state keyed off array length/position instead of
timestamps, which silently breaks once main.py's rolling window starts
dropping old rows) by construction, not by a fix -- there's no length/position
state to get wrong here.  `main.py`'s default `bars_needed=500` (not MGC's
3000) is enough: a session resets VWAP/Z regardless of what came before it, so
this strategy only ever needs the CURRENT session's bars (<=~390 for MNQ RTH)
plus enough trailing history for a causal 15m ATR(14) (~225 minutes) -- 500 1m
bars covers both with room to spare.

This class does NOT decide position size in dollar terms, matching every
other Strategy in this repo (`strategy_interface.Signal`'s docstring): it only
proposes stop/trail DISTANCES via `initial_stop_distance_points` /
`trail_distance_points`, leaving `risk_dollars` at None.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy

STOP_ATR_MULT = 1.0
TRAIL_ATR_MULT = 1.5
ATR_PERIOD = 14
Z_THRESH = 2.5
ZSTD_WINDOW = 60
ZSTD_MIN_PERIODS = 20


class VwapZScoreStrategy(Strategy):
    """The Round 49 MNQ VWAP Z-score edge. See module docstring for what it is,
    why it's stateless, and what the real, checked odds against this account's
    actual deadline are (they are NOT good -- see the 2026-09-21 journal entry
    before enabling this for anything but a Practice-mode rehearsal).
    """

    def _causal_atr15(self, bars_1m: pd.DataFrame) -> float | None:
        """15m ATR(14) using only fully-closed 15m bars as of the latest 1m bar
        seen. Identical method to `random_entry_atr_trail_strategy.py`'s
        `_causal_atr15` -- reused verbatim (not re-derived) so this file can't
        drift into a subtly different, unvalidated ATR rule the way MGC's live
        strategy once did (EDGE_AUDIT finding #3)."""
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
        last_val = atr.dropna()
        if last_val.empty:
            return None
        return float(last_val.iloc[-1])

    def _session_vwap_z(self, bars_1m: pd.DataFrame) -> pd.Series:
        """Causal session VWAP Z-score, matching
        `round49_vwap_zscore.compute_session_vwap_z` exactly: cumulative
        typical-price*volume / cumulative volume, reset every calendar date
        (a session boundary proxy -- MNQ's data is RTH-only, so one calendar
        date == one session), Z-scored against its own rolling deviation
        std within that same session. `bars_1m` uses "volume" (the live
        broker's column name) where the offline research file uses "vol"
        (its own raw-data loader's column name) -- same quantity, different
        column name between the two data sources; not a logic change.
        """
        dates = pd.Series(bars_1m.index.date, index=bars_1m.index)
        tp = (bars_1m["high"] + bars_1m["low"] + bars_1m["close"]) / 3.0
        pv = tp * bars_1m["volume"]
        cum_pv = pv.groupby(dates).cumsum()
        cum_v = bars_1m["volume"].groupby(dates).cumsum().replace(0, np.nan)
        vwap = cum_pv / cum_v
        dev = bars_1m["close"] - vwap
        return dev.groupby(dates).transform(
            lambda s: s / s.rolling(ZSTD_WINDOW, min_periods=ZSTD_MIN_PERIODS).std()
        )

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) < 2:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        z = self._session_vwap_z(df)
        latest_z = z.iloc[-1]
        if pd.isna(latest_z):
            return Signal(
                action=SignalAction.HOLD,
                reason="Z-score not yet computable (need >=20 bars into this session)",
            )

        latest_close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])

        direction = None
        if latest_z <= -Z_THRESH and latest_close > prev_close:
            direction = 1
        elif latest_z >= Z_THRESH and latest_close < prev_close:
            direction = -1

        if direction is None:
            return Signal(action=SignalAction.HOLD, reason=f"no signal (Z={latest_z:.2f})")

        atr = self._causal_atr15(df)
        if atr is None or atr <= 0:
            return Signal(action=SignalAction.HOLD, reason="15m ATR(14) not yet computable (insufficient history)")

        stop_distance = STOP_ATR_MULT * atr
        trail_distance = TRAIL_ATR_MULT * stop_distance
        action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT

        return Signal(
            action=action,
            initial_stop_distance_points=stop_distance,
            trail_distance_points=trail_distance,
            reason=(
                f"VWAP Z-score mean reversion (Z={latest_z:.2f}, direction={direction:+d}), "
                f"ATR(15m,14)={atr:.2f}, stop_dist={stop_distance:.2f}, trail_dist={trail_distance:.2f}"
            ),
        )
