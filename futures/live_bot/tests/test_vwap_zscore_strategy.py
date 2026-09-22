"""Plain-Python tests for vwap_zscore_strategy.py (no pytest dependency).

Run with: python live_bot/tests/test_vwap_zscore_strategy.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.strategy_interface import SignalAction  # noqa: E402
from live_bot.vwap_zscore_strategy import (  # noqa: E402
    STOP_ATR_MULT,
    TRAIL_ATR_MULT,
    Z_THRESH,
    VwapZScoreStrategy,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def make_session_bars(day: dt.date, n_bars: int, seed: int, start_price: float = 20_000.0) -> pl.DataFrame:
    """Synthetic 1-minute RTH bars with occasional large shocks superimposed on a
    small random walk -- a plain random walk rarely deviates far enough from its
    own slow-moving cumulative VWAP to cross a 2.5-sigma Z-score, so this
    strategy would never get real test coverage without deliberately injecting
    some larger moves (each followed, on average, by a real chance of the
    immediate one-bar reversal the entry condition also requires)."""
    rng = np.random.default_rng(seed)
    start = dt.datetime.combine(day, dt.time(9, 30))
    timestamps = [start + dt.timedelta(minutes=i) for i in range(n_bars)]
    moves = rng.normal(0, 2.0, size=n_bars)
    n_shocks = max(1, n_bars // 40)
    shock_idx = rng.choice(n_bars, size=n_shocks, replace=False)
    moves[shock_idx] += rng.choice([-1.0, 1.0], size=n_shocks) * rng.uniform(15, 25, size=n_shocks)
    closes = start_price + np.cumsum(moves)
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


def make_multi_day_bars(n_days: int, bars_per_day: int, seed: int) -> pl.DataFrame:
    frames = []
    price = 20_000.0
    for d in range(n_days):
        day = dt.date(2026, 9, 1) + dt.timedelta(days=d)
        bars = make_session_bars(day, bars_per_day, seed=seed + d, start_price=price)
        price = float(bars["close"][-1])
        frames.append(bars)
    return pl.concat(frames)


def test_empty_bars_holds_without_crashing():
    strat = VwapZScoreStrategy()
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_holds_with_insufficient_history_for_zscore():
    strat = VwapZScoreStrategy()
    day = dt.date(2026, 9, 21)
    bars = make_session_bars(day, 10, seed=1)  # well under ZSTD_MIN_PERIODS=20
    signal = strat.on_bar(bars)
    check(
        "holds_with_insufficient_history_for_zscore",
        signal.action == SignalAction.HOLD,
        f"action={signal.action}, reason={signal.reason}",
    )


def test_produces_valid_entries_over_multi_day_run():
    strat = VwapZScoreStrategy()
    full = make_multi_day_bars(n_days=6, bars_per_day=390, seed=3)

    entries = []
    for n in range(300, len(full) + 1, 10):
        signal = strat.on_bar(full.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries.append(signal)

    check("at_least_one_entry_over_multi_day_run", len(entries) >= 1, f"got {len(entries)} entries")

    if entries:
        all_valid_distances = all(
            e.initial_stop_distance_points is not None and e.initial_stop_distance_points > 0
            and e.trail_distance_points is not None and e.trail_distance_points > 0
            for e in entries
        )
        check("all_entries_have_valid_positive_distances", all_valid_distances, f"entries={len(entries)}")

        all_trail_ratio_correct = all(
            abs(e.trail_distance_points - (TRAIL_ATR_MULT / STOP_ATR_MULT) * e.initial_stop_distance_points) < 1e-6
            for e in entries
        )
        check("trail_distance_is_1point5x_stop_distance", all_trail_ratio_correct)

        all_trailing_shape = all(e.stop_loss_price is None and e.take_profit_price is None for e in entries)
        check("entries_use_trailing_shape_not_fixed_bracket", all_trailing_shape)

        def reason_z(reason: str) -> float:
            return float(reason.split("Z=")[1].split(",")[0])

        zs = [reason_z(e.reason) for e in entries]
        check(
            "long_entries_only_from_oversold_short_only_from_overbought",
            all(
                (z <= -Z_THRESH and e.action == SignalAction.ENTER_LONG)
                or (z >= Z_THRESH and e.action == SignalAction.ENTER_SHORT)
                for z, e in zip(zs, entries)
            ),
            f"zs={zs}, actions={[e.action for e in entries]}",
        )


def test_survives_rolling_window_like_main_py_hands_it():
    """This strategy carries no persistent state across on_bar calls -- every
    call recomputes session VWAP/Z fresh from whatever window it's handed, so
    it should be structurally immune to the rolling-window bug class Round
    "EDGE_AUDIT" found in the MGC strategy. Verify that empirically rather
    than just asserting it from the design: entries must keep occurring well
    past where a realistic rolling window starts dropping old bars."""
    strat = VwapZScoreStrategy()
    full = make_multi_day_bars(n_days=15, bars_per_day=390, seed=11)
    n_bars = len(full)
    window = 500

    entries_by_phase = {"growing": [], "rolling": []}
    for n in range(300, n_bars + 1, 15):
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


def test_new_session_z_resets_not_carried_over():
    """A session's Z-score must be computed against THAT session's own VWAP,
    not carried over from a prior session's cumulative VWAP -- otherwise the
    first bars of a new day would see an artificially large, stale deviation."""
    strat = VwapZScoreStrategy()
    day1 = dt.date(2026, 9, 21)
    day2 = dt.date(2026, 9, 22)
    day1_bars = make_session_bars(day1, 390, seed=41)
    day2_bars = make_session_bars(day2, 30, seed=42, start_price=float(day1_bars["close"][-1]))
    combined = pl.concat([day1_bars, day2_bars])

    # Z for the first few bars of day 2 should either be NaN (not enough of
    # today's own bars yet) or a small, plausible value -- never an extreme
    # inherited from day 1's cumulative deviation.
    df = combined.to_pandas().set_index("timestamp").sort_index()
    z_series = strat._session_vwap_z(df)
    day2_early_z = z_series[z_series.index.date == day2][:15]
    all_nan_or_small = all(pd.isna(v) or abs(v) < 10 for v in day2_early_z) if len(day2_early_z) else True
    check(
        "new_session_z_resets_not_carried_over",
        all_nan_or_small,
        f"day2_early_z={list(day2_early_z)}",
    )


def main() -> int:
    for fn in [
        test_empty_bars_holds_without_crashing,
        test_holds_with_insufficient_history_for_zscore,
        test_produces_valid_entries_over_multi_day_run,
        test_survives_rolling_window_like_main_py_hands_it,
        test_new_session_z_resets_not_carried_over,
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
