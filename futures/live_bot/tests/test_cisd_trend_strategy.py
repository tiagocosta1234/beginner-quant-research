"""Tests for cisd_trend_strategy.py, using real MNQ 5-min bar windows ending
exactly at timestamps where the validated offline backtest (Round 9b,
EDGE_VALIDATION_RESULTS.md, script inputs regenerated 2026-09-19) found a real
CISD+1H-trend signal. This checks that the LIVE code path (on_bar(), fed one
Polars/pandas-shaped bar window at a time) reproduces the OFFLINE backtest's
signals -- the specific risk flagged when this strategy was written: two
implementations of "the same" logic silently diverging is worse than either
implementation being wrong on its own, since it would pass a naive smoke test.

Run with: python live_bot/tests/test_cisd_trend_strategy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from live_bot.cisd_trend_strategy import CISDTrendConfig, CISDTrendStrategy  # noqa: E402
from live_bot.strategy_interface import SignalAction  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def load_fixture(name: str) -> pd.DataFrame:
    df = pd.read_csv(FIXTURES / name, parse_dates=["timestamp"])
    return df


# Config matching the validated backtest exactly: swing_k=4, ema_span=20,
# max_lookforward=20, displacement filter 0.5 -- see EDGE_VALIDATION_RESULTS.md Round 9b.
MNQ_CONFIG = CISDTrendConfig(
    swing_k=4, ema_span=20, stop_buffer_points=5.0, target_r_multiple=3.0,
    risk_dollars=150.0, point_value=2.0, max_lookforward_bars=20, displacement_body_ratio_min=0.5,
)


def test_reproduces_known_long_signal():
    bars = load_fixture("cisd_long.csv")
    strat = CISDTrendStrategy(MNQ_CONFIG)
    signal = strat.on_bar(bars)
    # Known from the offline backtest: dir=1, entry=18680.0, extreme=18657.75
    expected_entry = 18680.0
    expected_extreme = 18657.75
    expected_stop = expected_extreme - MNQ_CONFIG.stop_buffer_points
    expected_risk_pts = expected_entry - expected_stop
    expected_target = expected_entry + expected_risk_pts * MNQ_CONFIG.target_r_multiple
    ok = (
        signal.action == SignalAction.ENTER_LONG
        and abs(signal.stop_loss_price - expected_stop) < 0.01
        and abs(signal.take_profit_price - expected_target) < 0.01
        and signal.size >= 1
    )
    check("reproduces_known_long_signal", ok,
          f"action={signal.action}, stop={signal.stop_loss_price}, target={signal.take_profit_price}, "
          f"size={signal.size}, reason={signal.reason}")


def test_reproduces_known_short_signal():
    bars = load_fixture("cisd_short.csv")
    strat = CISDTrendStrategy(MNQ_CONFIG)
    signal = strat.on_bar(bars)
    expected_entry = 18614.75
    expected_extreme = 18710.5
    expected_stop = expected_extreme + MNQ_CONFIG.stop_buffer_points
    expected_risk_pts = expected_stop - expected_entry
    expected_target = expected_entry - expected_risk_pts * MNQ_CONFIG.target_r_multiple
    ok = (
        signal.action == SignalAction.ENTER_SHORT
        and abs(signal.stop_loss_price - expected_stop) < 0.01
        and abs(signal.take_profit_price - expected_target) < 0.01
        and signal.size >= 1
    )
    check("reproduces_known_short_signal", ok,
          f"action={signal.action}, stop={signal.stop_loss_price}, target={signal.take_profit_price}, "
          f"size={signal.size}, reason={signal.reason}")


def test_holds_when_no_signal_present():
    bars = load_fixture("cisd_hold.csv")
    strat = CISDTrendStrategy(MNQ_CONFIG)
    signal = strat.on_bar(bars)
    check("holds_when_no_signal_present", signal.action == SignalAction.HOLD,
          f"action={signal.action}, reason={signal.reason}")


def test_one_trade_per_day_cap():
    bars = load_fixture("cisd_long.csv")
    strat = CISDTrendStrategy(MNQ_CONFIG)
    first = strat.on_bar(bars)
    second = strat.on_bar(bars)  # identical bars, same day -- must not fire twice
    check("one_trade_per_day_cap",
          first.action == SignalAction.ENTER_LONG and second.action == SignalAction.HOLD,
          f"first={first.action}, second={second.action}, second.reason={second.reason}")


def test_empty_bars_holds_without_crashing():
    strat = CISDTrendStrategy(MNQ_CONFIG)
    signal = strat.on_bar(pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"]))
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def main() -> int:
    for fn in [
        test_reproduces_known_long_signal,
        test_reproduces_known_short_signal,
        test_holds_when_no_signal_present,
        test_one_trade_per_day_cap,
        test_empty_bars_holds_without_crashing,
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
