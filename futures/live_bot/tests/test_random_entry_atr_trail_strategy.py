"""Plain-Python tests for random_entry_atr_trail_strategy.py (no pytest dependency).

Run with: python live_bot/tests/test_random_entry_atr_trail_strategy.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.random_entry_atr_trail_strategy import (  # noqa: E402
    EXPECTED_SESSION_BARS,
    RandomEntryAtrTrailStrategy,
)
from live_bot.strategy_interface import SignalAction  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def make_session_bars(day: dt.date, n_bars: int, seed: int, start_price: float = 20_000.0) -> pl.DataFrame:
    """n_bars of synthetic 1-minute RTH bars for one day, a simple seeded random
    walk (enough OHLC variation for a real ATR(14) to be computable and non-zero)."""
    rng = np.random.default_rng(seed)
    start = dt.datetime.combine(day, dt.time(9, 30))
    timestamps = [start + dt.timedelta(minutes=i) for i in range(n_bars)]
    closes = start_price + np.cumsum(rng.normal(0, 3.0, size=n_bars))
    opens = closes - rng.normal(0, 1.0, size=n_bars)
    highs = np.maximum(opens, closes) + np.abs(rng.normal(0, 1.5, size=n_bars))
    lows = np.minimum(opens, closes) - np.abs(rng.normal(0, 1.5, size=n_bars))
    volumes = rng.integers(50, 500, size=n_bars)
    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


def test_holds_with_insufficient_history_for_atr():
    strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(1))
    day = dt.date(2026, 9, 21)
    # Only 50 bars -- well under the ~225 needed for a 15m ATR(14) to exist.
    bars = make_session_bars(day, 50, seed=1)
    signal = strat.on_bar(bars)
    check(
        "holds_with_insufficient_history_for_atr",
        signal.action == SignalAction.HOLD,
        f"action={signal.action}, reason={signal.reason}",
    )


def test_enters_exactly_once_per_session_with_valid_distances():
    strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(42))
    day = dt.date(2026, 9, 21)
    full_day = make_session_bars(day, EXPECTED_SESSION_BARS, seed=42)

    entries = []
    # Poll with a growing window, one bar at a time, across the whole session --
    # this is the shape main.py's real loop produces (each call sees more of the
    # same day than the last), just without the real 30s wall-clock delay.
    for n in range(200, EXPECTED_SESSION_BARS + 1, 5):
        signal = strat.on_bar(full_day.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries.append(signal)

    check(
        "enters_exactly_once_per_session",
        len(entries) == 1,
        f"got {len(entries)} entries: {[e.action for e in entries]}",
    )
    if entries:
        sig = entries[0]
        check(
            "entry_has_valid_stop_and_trail_distances",
            sig.initial_stop_distance_points is not None
            and sig.initial_stop_distance_points > 0
            and sig.trail_distance_points is not None
            and sig.trail_distance_points > 0,
            f"initial_stop_distance_points={sig.initial_stop_distance_points}, "
            f"trail_distance_points={sig.trail_distance_points}",
        )
        check(
            "entry_uses_trailing_shape_not_fixed_bracket",
            sig.stop_loss_price is None and sig.take_profit_price is None,
            f"stop_loss_price={sig.stop_loss_price}, take_profit_price={sig.take_profit_price}",
        )
        check(
            "trail_distance_is_1point5x_stop_distance",
            abs(sig.trail_distance_points - 1.5 * sig.initial_stop_distance_points) < 1e-6,
            f"stop={sig.initial_stop_distance_points}, trail={sig.trail_distance_points}",
        )


def test_holds_after_entry_for_rest_of_session():
    strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(7))
    day = dt.date(2026, 9, 21)
    full_day = make_session_bars(day, EXPECTED_SESSION_BARS, seed=7)

    entered = False
    post_entry_holds_ok = True
    for n in range(200, EXPECTED_SESSION_BARS + 1, 3):
        signal = strat.on_bar(full_day.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entered = True
        elif entered and signal.action != SignalAction.HOLD:
            post_entry_holds_ok = False
    check(
        "holds_after_entry_for_rest_of_session",
        entered and post_entry_holds_ok,
        f"entered={entered}, post_entry_holds_ok={post_entry_holds_ok}",
    )


def test_new_session_resets_and_can_enter_again():
    strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(99))
    day1 = dt.date(2026, 9, 21)
    day2 = dt.date(2026, 9, 22)
    day1_bars = make_session_bars(day1, EXPECTED_SESSION_BARS, seed=99)
    day2_bars = make_session_bars(day2, EXPECTED_SESSION_BARS, seed=100, start_price=float(day1_bars["close"][-1]))

    entries_day1 = 0
    for n in range(200, EXPECTED_SESSION_BARS + 1, 5):
        if strat.on_bar(day1_bars.head(n)).action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries_day1 += 1

    # Day 2: same shape, concatenated so the strategy sees continuous history
    # (as it would live), but a new calendar date should still reset the daily state.
    entries_day2 = 0
    combined = pl.concat([day1_bars, day2_bars])
    for n in range(EXPECTED_SESSION_BARS + 200, len(combined) + 1, 5):
        if strat.on_bar(combined.head(n)).action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries_day2 += 1

    check(
        "new_session_resets_and_can_enter_again",
        entries_day1 == 1 and entries_day2 == 1,
        f"entries_day1={entries_day1}, entries_day2={entries_day2}",
    )


def test_empty_bars_holds_without_crashing():
    strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(1))
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_mid_session_restart_never_targets_a_bar_already_passed():
    """Regression (2026-09-20 bug): if the bot's first on_bar call for a session
    arrives with bars already elapsed today (e.g. a restart partway through the
    session, since a CRITICAL health check causes main.py's poll loop to break
    and require a restart), the random entry target must never land below bars
    already seen. It used to be possible to draw from the full
    [0, EXPECTED_SESSION_BARS) range regardless of elapsed bars, causing a
    near-immediate, non-random entry the instant the session was first observed,
    despite a code comment claiming the draw already adapted to this.
    """
    day = dt.date(2026, 9, 21)
    bars_already_seen = 300  # simulate restarting partway through a ~390-bar day
    full_day = make_session_bars(day, EXPECTED_SESSION_BARS, seed=55)

    targets = []
    for seed in range(30):
        strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(seed))
        strat.on_bar(full_day.head(bars_already_seen))
        targets.append(strat._target_entry_bar_count)

    check(
        "mid_session_restart_target_never_below_bars_already_seen",
        all(t >= bars_already_seen for t in targets),
        f"bars_already_seen={bars_already_seen}, targets={targets}",
    )
    check(
        "mid_session_restart_target_not_degenerate",
        len(set(targets)) > 1,
        f"targets={targets}",
    )


def test_tod_filter_only_enters_in_last_third_of_session():
    """BOT_TOD_FILTER=1 (Round 39): entries must never fire before bar 260
    (~13:50 ET, the start of the last third of a 390-bar session)."""
    from live_bot.random_entry_atr_trail_strategy import TOD_FILTER_START_BAR

    entry_bars = []
    for seed in range(20):
        strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(seed), tod_filter=True)
        day = dt.date(2026, 9, 21)
        full_day = make_session_bars(day, EXPECTED_SESSION_BARS, seed=seed)
        for n in range(50, EXPECTED_SESSION_BARS + 1, 5):
            signal = strat.on_bar(full_day.head(n))
            if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
                entry_bars.append(strat._target_entry_bar_count)
                break

    check(
        "tod_filter_never_targets_before_last_third",
        len(entry_bars) > 0 and all(b >= TOD_FILTER_START_BAR for b in entry_bars),
        f"entry_bars={entry_bars}",
    )
    check(
        "tod_filter_targets_still_vary_not_degenerate",
        len(set(entry_bars)) > 1,
        f"entry_bars={entry_bars}",
    )


def test_no_tod_filter_by_default_can_target_before_last_third():
    """Sanity check that tod_filter really is opt-in: with it off (the default),
    targets are drawn from the full session and CAN land before bar 260 --
    otherwise the test above would be vacuous."""
    from live_bot.random_entry_atr_trail_strategy import TOD_FILTER_START_BAR

    any_early = False
    for seed in range(20):
        strat = RandomEntryAtrTrailStrategy(rng=np.random.default_rng(seed))  # tod_filter default False
        strat._roll_new_session(dt.date(2026, 9, 21))
        if strat._target_entry_bar_count < TOD_FILTER_START_BAR:
            any_early = True
            break
    check("tod_filter_off_by_default_allows_early_targets", any_early, "")


def main() -> int:
    for fn in [
        test_holds_with_insufficient_history_for_atr,
        test_enters_exactly_once_per_session_with_valid_distances,
        test_holds_after_entry_for_rest_of_session,
        test_new_session_resets_and_can_enter_again,
        test_empty_bars_holds_without_crashing,
        test_mid_session_restart_never_targets_a_bar_already_passed,
        test_tod_filter_only_enters_in_last_third_of_session,
        test_no_tod_filter_by_default_can_target_before_last_third,
    ]:
        fn()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    for name, ok, detail in RESULTS:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
