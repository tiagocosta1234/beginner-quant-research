"""Plain-Python tests for support_resistance_bounce_strategy.py (no pytest dependency).

Run with: python live_bot/tests/test_support_resistance_bounce_strategy.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.strategy_interface import SignalAction  # noqa: E402
from live_bot.support_resistance_bounce_strategy import (  # noqa: E402
    STOP_ATR_MULT,
    TRAIL_ATR_MULT,
    SupportResistanceBounceStrategy,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def make_mean_reverting_bars(n_bars: int, seed: int, start_price: float = 2_000.0) -> pl.DataFrame:
    """A mean-reverting (Ornstein-Uhlenbeck-style) synthetic 1-minute series, not a
    pure random walk -- mean reversion guarantees price genuinely revisits prior
    swing highs/lows (real touches), which this strategy needs to ever fire. A
    plain random walk would only touch old levels by chance and could produce a
    flaky test.
    """
    rng = np.random.default_rng(seed)
    theta, mean, sigma = 0.01, start_price, 1.2
    closes = np.empty(n_bars)
    closes[0] = start_price
    for i in range(1, n_bars):
        closes[i] = closes[i - 1] + theta * (mean - closes[i - 1]) + rng.normal(0, sigma)
    opens = closes - rng.normal(0, 0.3, size=n_bars)
    highs = np.maximum(opens, closes) + np.abs(rng.normal(0, 0.5, size=n_bars))
    lows = np.minimum(opens, closes) - np.abs(rng.normal(0, 0.5, size=n_bars))
    volumes = rng.integers(10, 200, size=n_bars)
    start = dt.datetime(2026, 9, 21, 0, 0)
    timestamps = [start + dt.timedelta(minutes=i) for i in range(n_bars)]
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


def test_empty_bars_holds_without_crashing():
    strat = SupportResistanceBounceStrategy()
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_holds_with_insufficient_history():
    strat = SupportResistanceBounceStrategy()
    bars = make_mean_reverting_bars(100, seed=1)  # well under 15m ATR(14)'s ~225min minimum
    signal = strat.on_bar(bars)
    check(
        "holds_with_insufficient_history",
        signal.action == SignalAction.HOLD,
        f"action={signal.action}, reason={signal.reason}",
    )


def test_produces_valid_entries_over_a_long_mean_reverting_run():
    strat = SupportResistanceBounceStrategy()
    n_bars = 4000  # ~2.8 days of 1m bars
    full = make_mean_reverting_bars(n_bars, seed=7)

    entries = []
    # Poll with a growing window, same shape main.py's real loop produces.
    for n in range(1000, n_bars + 1, 20):
        signal = strat.on_bar(full.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries.append(signal)

    check(
        "at_least_one_entry_over_long_mean_reverting_run",
        len(entries) >= 1,
        f"got {len(entries)} entries out of {n_bars} bars",
    )

    # No two entries should ever fire off the exact same confirmed level -- a
    # level is identified by (price, confirm_ts), both embedded in `reason`; a
    # duplicate here would mean a level fired twice, the Round 30b-class bug.
    def level_id(reason: str) -> tuple[str, str]:
        price_part = reason.split(" at ")[1]
        price = price_part.split(" (confirmed ")[0]
        confirm_ts = price_part.split(" (confirmed ")[1].split(")")[0]
        return (price, confirm_ts)

    level_ids = [level_id(e.reason) for e in entries]
    check(
        "no_level_fires_more_than_once",
        len(level_ids) == len(set(level_ids)),
        f"level_ids={level_ids}",
    )

    if entries:
        all_valid_distances = all(
            e.initial_stop_distance_points is not None
            and e.initial_stop_distance_points > 0
            and e.trail_distance_points is not None
            and e.trail_distance_points > 0
            for e in entries
        )
        check("all_entries_have_valid_positive_distances", all_valid_distances, f"entries={len(entries)}")

        all_trail_ratio_correct = all(
            abs(e.trail_distance_points - TRAIL_ATR_MULT / STOP_ATR_MULT * e.initial_stop_distance_points) < 1e-6
            for e in entries
        )
        check("trail_distance_is_1point5x_stop_distance", all_trail_ratio_correct)

        all_trailing_shape = all(e.stop_loss_price is None and e.take_profit_price is None for e in entries)
        check("entries_use_trailing_shape_not_fixed_bracket", all_trailing_shape)

        reasons_mention_support_or_resistance = all(
            ("support" in e.reason and e.action == SignalAction.ENTER_LONG)
            or ("resistance" in e.reason and e.action == SignalAction.ENTER_SHORT)
            for e in entries
        )
        check(
            "direction_matches_bounce_side_in_reason",
            reasons_mention_support_or_resistance,
            f"reasons={[e.reason for e in entries]}",
        )


def test_touched_level_is_consumed_not_reused():
    """A level that fires an entry must never fire again -- this is the exact
    property Round 30b's bug fix was about getting right offline; this test is
    the live-code equivalent check, using the same duplicate-(price, confirm_ts)
    detection as the previous test but on an independent seed.
    """
    strat = SupportResistanceBounceStrategy()
    n_bars = 4000
    full = make_mean_reverting_bars(n_bars, seed=13)

    entries = []
    for n in range(1000, n_bars + 1, 20):
        signal = strat.on_bar(full.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries.append(signal)

    def level_id(reason: str) -> tuple[str, str]:
        price_part = reason.split(" at ")[1]
        return (price_part.split(" (confirmed ")[0], price_part.split(" (confirmed ")[1].split(")")[0])

    level_ids = [level_id(e.reason) for e in entries]
    check(
        "touched_level_never_fires_twice_independent_seed",
        len(level_ids) == len(set(level_ids)),
        f"n_entries={len(entries)}, level_ids={level_ids}",
    )


def test_survives_rolling_window_like_main_py_hands_it():
    """Regression (2026-09-20 bug): main.py hands this strategy only the most
    recent ~3000 1-minute bars every poll cycle (a ROLLING window), not a
    continuously growing one. The old implementation resumed its swing-scan
    from a remembered array LENGTH, which silently stopped detecting new
    levels forever once real runtime exceeded that window -- no crash, no
    error, entries just stopped. Simulate the real rolling shape and assert
    entries keep occurring well past where the window starts rolling, not
    just during the initial growing phase.
    """
    strat = SupportResistanceBounceStrategy()
    n_bars = 9000  # 3x the rolling window, ~6.25 days
    window = 3000
    full = make_mean_reverting_bars(n_bars, seed=29)

    entries_by_phase = {"growing": [], "rolling": []}
    for n in range(1000, n_bars + 1, 25):
        start = max(0, n - window)
        bars = full.slice(start, n - start)
        signal = strat.on_bar(bars)
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            phase = "growing" if n <= window else "rolling"
            entries_by_phase[phase].append(signal)

    check(
        "entries_continue_after_window_starts_rolling",
        len(entries_by_phase["rolling"]) >= 1,
        f"growing={len(entries_by_phase['growing'])}, rolling={len(entries_by_phase['rolling'])}",
    )


def test_level_atr_is_frozen_at_confirmation_not_recomputed_live():
    """Regression (2026-09-20 bug): each level must freeze the ATR that was
    current AT ITS OWN confirmation bar and reuse that single value for both
    touch tolerance and eventual stop sizing -- not share one live-recomputed
    'current' ATR across every active level regardless of age.
    """
    strat = SupportResistanceBounceStrategy()
    n_bars = 2000
    full = make_mean_reverting_bars(n_bars, seed=21)
    strat.on_bar(full.head(1500))
    strat.on_bar(full.head(n_bars))

    if not strat._active_levels:
        check("level_atr_frozen_at_own_confirmation", False, "no active levels to check")
        return

    atr_series = strat._atr15_series()
    idx15 = strat._h15.index
    mismatches = []
    for lv in strat._active_levels:
        pos = idx15.get_loc(lv["confirm_ts"])
        expected_atr = float(atr_series.iloc[pos])
        if abs(lv["atr"] - expected_atr) > 1e-9:
            mismatches.append((str(lv["confirm_ts"]), lv["atr"], expected_atr))
    check("level_atr_frozen_at_own_confirmation", len(mismatches) == 0, f"mismatches={mismatches}")

    distinct_atrs = {round(lv["atr"], 6) for lv in strat._active_levels}
    check(
        "levels_have_varying_frozen_atr_not_one_shared_value",
        len(distinct_atrs) > 1,
        f"distinct_atrs={distinct_atrs}",
    )


def main() -> int:
    for fn in [
        test_empty_bars_holds_without_crashing,
        test_holds_with_insufficient_history,
        test_produces_valid_entries_over_a_long_mean_reverting_run,
        test_touched_level_is_consumed_not_reused,
        test_survives_rolling_window_like_main_py_hands_it,
        test_level_atr_is_frozen_at_confirmation_not_recomputed_live,
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
