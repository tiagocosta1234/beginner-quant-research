"""The second validated edge this repo's research produced (MGC/gold), wired up as
a real Strategy, mirroring how `random_entry_atr_trail_strategy.py` made the MNQ
edge deployable.

Source of truth: `futures/docs/EDGE_VALIDATION_RESULTS.md` Round 30/30b
(2026-09-20) for the edge itself, and Round 31/31b/31c-e for the sizing this file's
own docstring below references. Read those sections before trusting this file --
in particular Round 30b's bug-fix history (the original Round 30 signal generator
fired on every level touch with no one-position-at-a-time gating; this file's
level-consumption design below exists specifically to not repeat that bug live).

What was validated, and why the entry looks the way it does:
  Round 30 found a real edge fading price at confirmed swing support/resistance
  levels on MGC: detect a swing high/low on the 15m chart (a bar that is the
  local extreme across `swing_k` bars on each side, confirmed causally -- i.e.
  only knowable `swing_k` bars after the swing bar itself), then wait for price
  to later "touch" that level (within `tol_atr` x ATR(14,15m) of it) and enter
  in the BOUNCE direction: fade resistance (short on a touch from below), fade
  support (long on a touch from above). Exit uses the exact same ATR-trailing
  mechanism as the MNQ edge (round19_random_entry.py's resolve_trailing): initial
  stop = 1.0x ATR(14,15m) beyond the level, trailing by 1.5x that same distance,
  no fixed target. Round 30b fixed an overlap bug in how signals were resolved
  offline and found the edge survived it.

Parameters (swing_k=3, tol_atr=0.50) are the pair Round 30b's own per-fold
train-selection picked in 5 of 6 walk-forward folds (see
`round30b_sequential_results.csv`) -- the one dominant, most-representative
choice, not a cherry-pick; fold 0 (earliest, 2024 H1) alone preferred swing_k=8,
which this file does not use since live deployment needs one fixed parameter set
and the more recent folds are more representative of what's ahead.

Sizing: Round 31's combined-portfolio Monte Carlo (see EDGE_VALIDATION_RESULTS.md
Round 31) found that sizing each edge at its OWN individually-buffer-safe level
(MNQ $75, MGC $200) is too conservative to reach the account's profit target
before the real Oct 30 withdrawal deadline (0.4% success over the real ~20-day
window). Round 34's finer sweep (confirmed non-fluke across 10 MC seeds in
Round 33) refined this to MNQ $245 / MGC $650 per trade -- 87.8% success / 3.8%
ruin, the best real risk-adjusted point (success keeps climbing to ~89% around
3.5x the safe size, but ruin climbs faster from there). Round 31c/e's
out-of-sample check against the most recent walk-forward fold (2026-07-01 to
2026-09-16, real non-bootstrapped consecutive-20-day windows, no resampling,
at the earlier $600 MGC figure) found every one of 660 such windows both
cleared the profit target and stayed within the account buffer -- a small,
single-regime sample, so read as reassuring corroboration of the full-history
number, not a replacement for it. $650/trade is this file's implicit target via
`main.py`'s fixed-risk default or `BOT_DYNAMIC_SIZING`; this file itself
proposes no dollar amount (see `initial_stop_distance_points` below) -- same
separation of concerns as the MNQ strategy file.

Corrected 2026-09-20 (was previously wrong): `on_bar` IS called every poll cycle
regardless of open-position state -- neither `RiskGovernor.evaluate()`'s
`can_open_new_position` nor `FlattenRoutine.can_open_new_position()` check
`broker.has_open_position()`; only `handle_entry_signal()`, which runs AFTER
`on_bar` already returned, checks that (and only to suppress placing an order,
not to skip level detection). So this strategy DOES keep detecting and consuming
newly-confirming swing levels while a trade is open, the same as the offline
research (`round30_support_resistance.py`) does. A level touched while a
position is already open still gets consumed here (removed from
`_active_levels`) even though no order is placed for it -- matching Round 30b's
overlap-skip semantics (a signal during an open position is dropped, not queued
or reused later).
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
SWING_K = 3
TOL_ATR = 0.50
# Same 2000-bar-after-confirmation touch window round30_support_resistance.py's
# `touches()` used -- a level nobody has come back to test in ~33 hours of 1m
# bars is dropped rather than left live indefinitely (untested in the backtest
# beyond that window, so treated as expired here rather than assumed to still
# hold).
LEVEL_EXPIRY_BARS = 2000


class SupportResistanceBounceStrategy(Strategy):
    """The validated Round 30/30b MGC edge. See module docstring for parity
    notes with the offline research and what was corrected 2026-09-20.
    """

    def __init__(self) -> None:
        self._h15: pd.DataFrame | None = None
        # Timestamp (not array length/position) of the newest swing bar we've
        # already scanned for a confirmation. main.py hands this strategy a
        # ROLLING window of the most recent ~3000 1-minute bars, not a
        # continuously-growing one, so len(h15) plateaus once real runtime
        # exceeds that window -- resuming from a remembered LENGTH (as an
        # earlier version of this method did) makes the scan range collapse to
        # empty forever once that happens, silently killing new level
        # detection. Timestamps are stable under a rolling window; lengths and
        # positions are not.
        self._last_confirmed_ts: pd.Timestamp | None = None
        # Each entry: dict(confirm_ts, price, is_resistance)
        self._active_levels: list[dict] = []

    def _update_h15_and_levels(self, bars_1m: pd.DataFrame) -> None:
        h15 = (
            bars_1m[["open", "high", "low", "close"]]
            .resample("15min", label="right", closed="right")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        self._h15 = h15
        n15 = len(h15)
        if n15 <= 2 * SWING_K:
            return

        # Only scan the newly-confirmable range since the last update: a 15m bar
        # at position i is confirmed once bars i-SWING_K..i+SWING_K all exist, so
        # the newest confirmable index is n15-1-SWING_K.
        newly_confirmable_end = n15 - SWING_K  # exclusive
        hi = h15["high"].values
        lo = h15["low"].values
        idx15 = h15.index

        if self._last_confirmed_ts is None:
            start = SWING_K
        else:
            # Smallest i whose confirmation bar (idx15[i+SWING_K]) is strictly
            # after the last confirmation timestamp we've already scanned.
            # Works whether h15 has grown (position shifts, timestamp doesn't)
            # or rolled (old rows dropped off the front, same logic still
            # finds the right resume point in the new, shorter array).
            first_new_pos = int(idx15.searchsorted(self._last_confirmed_ts, side="right"))
            start = max(SWING_K, first_new_pos - SWING_K)

        # ATR series (one value per h15 bar, NaN during warmup) so each newly
        # confirmed level can freeze the ATR that was actually current AT its
        # own confirmation bar -- matching round30_support_resistance.py's
        # `atr_at(ts1[start_pos])`, which looks up ATR once per level at
        # confirmation and reuses that single frozen value as both the touch
        # tolerance and the eventual stop distance for that level's whole life.
        # Recomputing ATR fresh every bar (as an earlier version of this method
        # did, for both tolerance and stop sizing) is a different rule than what
        # was backtested, not just a parameter drift.
        atr_series = self._atr15_series()

        now_expiry_cutoff = bars_1m.index[-1]
        seen = {(lv["confirm_ts"], lv["is_resistance"]) for lv in self._active_levels}
        for i in range(start, newly_confirmable_end):
            window_hi = hi[i - SWING_K : i + SWING_K + 1]
            window_lo = lo[i - SWING_K : i + SWING_K + 1]
            confirm_pos = i + SWING_K if i + SWING_K < n15 else n15 - 1
            confirm_ts = idx15[confirm_pos]
            atr_at_confirm = atr_series.iloc[confirm_pos]
            self._last_confirmed_ts = confirm_ts
            if pd.isna(atr_at_confirm):
                # Not enough 15m history yet to know ATR at this bar -- skip;
                # matches the research pipeline never emitting a signal without
                # a valid ATR to size it.
                continue
            if hi[i] == window_hi.max() and (confirm_ts, True) not in seen:
                self._active_levels.append(
                    dict(confirm_ts=confirm_ts, price=float(hi[i]), is_resistance=True,
                         atr=float(atr_at_confirm))
                )
                seen.add((confirm_ts, True))
            if lo[i] == window_lo.min() and (confirm_ts, False) not in seen:
                self._active_levels.append(
                    dict(confirm_ts=confirm_ts, price=float(lo[i]), is_resistance=False,
                         atr=float(atr_at_confirm))
                )
                seen.add((confirm_ts, False))

        # Drop levels older than LEVEL_EXPIRY_BARS 1-minute bars past confirmation.
        cutoff = now_expiry_cutoff - pd.Timedelta(minutes=LEVEL_EXPIRY_BARS)
        self._active_levels = [lv for lv in self._active_levels if lv["confirm_ts"] >= cutoff]

    def _atr15_series(self) -> pd.Series:
        """Causal ATR(14) on the 15m series, one value per h15 bar (NaN during warmup)."""
        h15 = self._h15
        if h15 is None or len(h15) == 0:
            return pd.Series(dtype=float)
        high, low, close = h15["high"], h15["low"], h15["close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        return tr.rolling(ATR_PERIOD, min_periods=ATR_PERIOD).mean()

    def _causal_atr15(self) -> float | None:
        """Latest available ATR(14) -- used only as a 'do we have enough history
        yet' readiness gate. Touch tolerance and stop sizing use each level's own
        frozen-at-confirmation ATR (see `_update_h15_and_levels`), not this."""
        atr = self._atr15_series().dropna()
        if atr.empty:
            return None
        return float(atr.iloc[-1])

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) == 0:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        self._update_h15_and_levels(df)

        atr = self._causal_atr15()
        if atr is None or atr <= 0:
            return Signal(action=SignalAction.HOLD, reason="15m ATR(14) not yet computable (insufficient history)")

        latest_high = float(df["high"].iloc[-1])
        latest_low = float(df["low"].iloc[-1])

        # Only levels confirmed strictly before the latest bar can be touched by
        # it -- guards against a level and its own confirming bar being treated
        # as touching each other. Each level's OWN frozen-at-confirmation ATR
        # (not the current bar's) sets its touch tolerance, matching the
        # validated research.
        latest_ts = df.index[-1]
        touched = None
        for lv in self._active_levels:
            if lv["confirm_ts"] >= latest_ts:
                continue
            tol = TOL_ATR * lv["atr"]
            if lv["is_resistance"] and latest_high >= lv["price"] - tol:
                touched = lv
                break
            if not lv["is_resistance"] and latest_low <= lv["price"] + tol:
                touched = lv
                break

        if touched is None:
            return Signal(
                action=SignalAction.HOLD,
                reason=f"no level touch ({len(self._active_levels)} active levels, ATR(15m,14)={atr:.2f})",
            )

        # Consumed on touch, win or lose -- matches round30_support_resistance.py's
        # `touches()`, which breaks after a level's first touch and never re-fires it.
        self._active_levels.remove(touched)

        # Stop/trail sized off the level's own frozen ATR (at its confirmation
        # time), not the current bar's -- matches the validated research.
        stop_distance = STOP_ATR_MULT * touched["atr"]
        trail_distance = TRAIL_ATR_MULT * stop_distance
        direction = 1 if not touched["is_resistance"] else -1  # bounce off support = long, off resistance = short
        action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT

        return Signal(
            action=action,
            initial_stop_distance_points=stop_distance,
            trail_distance_points=trail_distance,
            reason=(
                f"swing {'support' if direction == 1 else 'resistance'} bounce at "
                f"{touched['price']:.2f} (confirmed {touched['confirm_ts']}), ATR(15m,14)="
                f"{atr:.2f}, stop_dist={stop_distance:.2f}, trail_dist={trail_distance:.2f}"
            ),
        )
