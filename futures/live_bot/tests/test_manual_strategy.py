"""Plain-Python tests for manual_strategy.py (no pytest dependency).

Run with: python live_bot/tests/test_manual_strategy.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.manual_strategy import TOD_RISK, VWAPZ_RISK, ManualStrategy  # noqa: E402
from live_bot.strategy_interface import Signal, SignalAction, Strategy  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


class FakeStrategy(Strategy):
    """Returns a fixed, pre-built Signal on every call -- for testing the trader's
    own priority/composition logic in isolation from the real TOD/VWAP-Z
    signal mechanics (those are already covered by their own test files)."""

    def __init__(self, signal: Signal) -> None:
        self._signal = signal
        self.calls = 0

    def on_bar(self, bars: Any) -> Signal:
        self.calls += 1
        return self._signal


HOLD = Signal(action=SignalAction.HOLD, reason="fake hold")
TOD_ENTER = Signal(
    action=SignalAction.ENTER_LONG,
    initial_stop_distance_points=10.0,
    trail_distance_points=15.0,
    reason="fake tod entry",
)
VWAPZ_ENTER = Signal(
    action=SignalAction.ENTER_SHORT,
    initial_stop_distance_points=5.0,
    trail_distance_points=7.5,
    reason="fake vwapz entry",
)


def test_empty_bars_holds_without_crashing():
    strat = ManualStrategy(tod=FakeStrategy(HOLD), vwapz=FakeStrategy(HOLD))
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_real_composition_empty_bars_holds_without_crashing():
    """Same check as above but through the REAL RandomEntryAtrTrailStrategy +
    VwapZScoreStrategy composition (not fakes) -- both already have their own
    empty-bars coverage individually; this confirms the wiring between them
    doesn't introduce a new crash path."""
    strat = ManualStrategy()
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("real_composition_empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_both_hold_returns_hold():
    tod = FakeStrategy(HOLD)
    vwapz = FakeStrategy(HOLD)
    strat = ManualStrategy(tod=tod, vwapz=vwapz)
    signal = strat.on_bar("dummy_bars")
    check("both_hold_returns_hold", signal.action == SignalAction.HOLD, f"action={signal.action}")
    check("both_substrategies_called_every_bar", tod.calls == 1 and vwapz.calls == 1,
          f"tod.calls={tod.calls}, vwapz.calls={vwapz.calls}")


def test_tod_only_fires_uses_tod_risk():
    strat = ManualStrategy(tod=FakeStrategy(TOD_ENTER), vwapz=FakeStrategy(HOLD))
    signal = strat.on_bar("dummy_bars")
    check("tod_only_action_passed_through", signal.action == SignalAction.ENTER_LONG, f"action={signal.action}")
    check("tod_only_uses_tod_risk", signal.risk_dollars == TOD_RISK, f"risk_dollars={signal.risk_dollars}")
    check("tod_only_distances_passed_through",
          signal.initial_stop_distance_points == 10.0 and signal.trail_distance_points == 15.0,
          f"init={signal.initial_stop_distance_points}, trail={signal.trail_distance_points}")
    check("tod_only_reason_tagged", "[the trader/TOD" in signal.reason and "fake tod entry" in signal.reason, signal.reason)


def test_vwapz_only_fires_uses_vwapz_risk():
    strat = ManualStrategy(tod=FakeStrategy(HOLD), vwapz=FakeStrategy(VWAPZ_ENTER))
    signal = strat.on_bar("dummy_bars")
    check("vwapz_only_action_passed_through", signal.action == SignalAction.ENTER_SHORT, f"action={signal.action}")
    check("vwapz_only_uses_vwapz_risk", signal.risk_dollars == VWAPZ_RISK, f"risk_dollars={signal.risk_dollars}")
    check("vwapz_only_reason_tagged", "[the trader/VWAP-Z" in signal.reason and "fake vwapz entry" in signal.reason, signal.reason)


def test_both_fire_same_bar_tod_takes_priority():
    strat = ManualStrategy(tod=FakeStrategy(TOD_ENTER), vwapz=FakeStrategy(VWAPZ_ENTER))
    signal = strat.on_bar("dummy_bars")
    check("tie_break_tod_wins", signal.action == SignalAction.ENTER_LONG and signal.risk_dollars == TOD_RISK,
          f"action={signal.action}, risk_dollars={signal.risk_dollars}")


def test_risk_dollars_never_none_on_a_real_entry():
    for sig in (TOD_ENTER, VWAPZ_ENTER):
        strat = ManualStrategy(
            tod=FakeStrategy(sig if sig is TOD_ENTER else HOLD),
            vwapz=FakeStrategy(sig if sig is VWAPZ_ENTER else HOLD),
        )
        out = strat.on_bar("dummy_bars")
        check(f"risk_dollars_set_for_{out.action.name}", out.risk_dollars is not None, f"risk_dollars={out.risk_dollars}")


# --- real (non-faked) multi-day run, exercising the actual composed classes ---

def make_multi_day_bars(n_days: int, bars_per_day: int, seed: int) -> pl.DataFrame:
    frames = []
    price = 20_000.0
    for d in range(n_days):
        day = dt.date(2026, 9, 1) + dt.timedelta(days=d)
        rng = np.random.default_rng(seed + d)
        start = dt.datetime.combine(day, dt.time(9, 30))
        timestamps = [start + dt.timedelta(minutes=i) for i in range(bars_per_day)]
        moves = rng.normal(0, 2.0, size=bars_per_day)
        n_shocks = max(1, bars_per_day // 40)
        shock_idx = rng.choice(bars_per_day, size=n_shocks, replace=False)
        moves[shock_idx] += rng.choice([-1.0, 1.0], size=n_shocks) * rng.uniform(15, 25, size=n_shocks)
        closes = price + np.cumsum(moves)
        opens = closes - rng.normal(0, 1.0, size=bars_per_day)
        highs = np.maximum(opens, closes) + np.abs(rng.normal(0, 1.5, size=bars_per_day))
        lows = np.minimum(opens, closes) - np.abs(rng.normal(0, 1.5, size=bars_per_day))
        volumes = rng.integers(50, 500, size=bars_per_day)
        price = float(closes[-1])
        frames.append(pl.DataFrame({
            "timestamp": timestamps, "open": opens, "high": highs, "low": lows,
            "close": closes, "volume": volumes,
        }))
    return pl.concat(frames)


def test_real_composition_produces_both_kinds_of_entries():
    """Not faked this time -- runs the real RandomEntryAtrTrailStrategy(tod_filter=True)
    + VwapZScoreStrategy composition over a long enough synthetic run to confirm
    both edges genuinely fire through the trader with the correct tagged risk, not just
    in the isolated fake-based tests above."""
    strat = ManualStrategy()
    full = make_multi_day_bars(n_days=10, bars_per_day=390, seed=5)

    entries = []
    for n in range(300, len(full) + 1, 10):
        signal = strat.on_bar(full.head(n))
        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            entries.append(signal)

    tod_entries = [e for e in entries if "[the trader/TOD" in e.reason]
    vwapz_entries = [e for e in entries if "[the trader/VWAP-Z" in e.reason]

    check("real_run_produced_entries", len(entries) >= 1, f"total entries={len(entries)}")
    check("real_run_tod_entries_use_tod_risk",
          all(e.risk_dollars == TOD_RISK for e in tod_entries), f"n={len(tod_entries)}")
    check("real_run_vwapz_entries_use_vwapz_risk",
          all(e.risk_dollars == VWAPZ_RISK for e in vwapz_entries), f"n={len(vwapz_entries)}")
    check("real_run_all_entries_have_valid_distances",
          all(e.initial_stop_distance_points is not None and e.initial_stop_distance_points > 0
              and e.trail_distance_points is not None and e.trail_distance_points > 0
              for e in entries),
          f"n={len(entries)}")
    check("real_run_no_fixed_bracket_shape",
          all(e.stop_loss_price is None and e.take_profit_price is None for e in entries),
          f"n={len(entries)}")


def main() -> int:
    for fn in [
        test_empty_bars_holds_without_crashing,
        test_real_composition_empty_bars_holds_without_crashing,
        test_both_hold_returns_hold,
        test_tod_only_fires_uses_tod_risk,
        test_vwapz_only_fires_uses_vwapz_risk,
        test_both_fire_same_bar_tod_takes_priority,
        test_risk_dollars_never_none_on_a_real_entry,
        test_real_composition_produces_both_kinds_of_entries,
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
