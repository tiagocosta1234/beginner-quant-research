"""Tests for ote_fvg_strategy.py, against REAL BrokerAPI/BrokerAPI MNQ data --
matching this specific strategy's own campaign convention (round76/79/80 in
futures/engine all validate against real data, not synthetic bars,
since the entry logic's sweep/leg-lock/OTE-zone/FVG-confluence chain is
sensitive enough to real market structure that a synthetic random walk would
not exercise it meaningfully).

Run with: python live_bot/tests/test_ote_fvg_strategy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "futures" / "engine"))

from live_bot.strategy_interface import SignalAction  # noqa: E402
from live_bot.ote_fvg_strategy import (  # noqa: E402
    FIXED_STOP_POINTS,
    K_MIN,
    POINT_VALUE_MNQ,
    RISK_DOLLAR,
    RR,
    RTH_START,
    RTH_END,
    OteFvgStrategy,
)

RESULTS: list[tuple[str, bool, str]] = []
DATA_PATH = Path(__file__).resolve().parents[2] / "futures" / "data" / "MNQ_1MIN_BROKERAPI.csv"


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def _load_real_mnq_1m() -> pd.DataFrame:
    """Same loading logic as round11_fvg_bias.load_1m_brokerapi, inlined here
    (test-only cross-reference) rather than imported, matching this repo's
    live_bot/no-futures-import convention for shipped code -- only
    the reference detect_ote_signals import below (used to compute the
    expected answer) crosses that boundary, and only inside a test."""
    df = pd.read_csv(DATA_PATH)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.rename(columns={"volume": "vol"})
    df = df.set_index("ts").sort_index()[["open", "high", "low", "close", "vol"]]
    df = df[~df.index.duplicated(keep="first")]
    return df


def _to_polars_bars(df1m: pd.DataFrame) -> pl.DataFrame:
    """Shape main.py's broker.get_bars() hands a Strategy: timestamp/open/
    high/low/close/volume, polars, as vwap_zscore's and manual's own tests
    already assume."""
    out = df1m.reset_index().rename(columns={"ts": "timestamp", "vol": "volume"})
    return pl.from_pandas(out)


def test_empty_bars_holds_without_crashing():
    strat = OteFvgStrategy()
    empty = pl.DataFrame(
        schema={"timestamp": pl.Datetime, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Int64}
    )
    signal = strat.on_bar(empty)
    check("empty_bars_holds_without_crashing", signal.action == SignalAction.HOLD, f"action={signal.action}")


def test_holds_with_insufficient_history():
    strat = OteFvgStrategy()
    df1m = _load_real_mnq_1m()
    bars = _to_polars_bars(df1m.head(K_MIN + 10))  # under K_MIN + 50's guard
    signal = strat.on_bar(bars)
    check(
        "holds_with_insufficient_history",
        signal.action == SignalAction.HOLD,
        f"action={signal.action}, reason={signal.reason}",
    )


def test_port_matches_reference_detector_on_real_data():
    """The port's own detection methods (_resample_causal/_detect_fvgs/
    _detect_ote_signals) must produce EXACTLY the same signals as
    round76_ote_pdarray_formalized.py's originals on the same real data --
    this is the single most important test here, since ote_fvg_strategy.py
    is a from-scratch re-transcription (live_bot doesn't import
    futures), and nothing enforces the two staying in sync."""
    from round11_fvg_bias import load_1m_brokerapi, resample_causal, detect_fvgs  # noqa: E402
    from round76_ote_pdarray_formalized import detect_ote_signals  # noqa: E402

    mnq_1m = load_1m_brokerapi(str(DATA_PATH))
    ref_fvg = detect_fvgs(resample_causal(mnq_1m, "15min"))
    ref_sig = detect_ote_signals(mnq_1m, ref_fvg)

    strat = OteFvgStrategy()
    my_fvg = strat._detect_fvgs(strat._resample_causal(mnq_1m, "15min"))
    my_sig = strat._detect_ote_signals(mnq_1m, my_fvg)

    check(
        "ported_signal_count_matches_reference",
        len(my_sig) == len(ref_sig) and len(ref_sig) > 0,
        f"reference={len(ref_sig)}, ported={len(my_sig)}",
    )
    # Compare only ts/direction/entry, NOT stop: round76's own FIXED_STOP_POINTS
    # (still 20, historical reference) and this file's (10, Round 82's finding)
    # deliberately diverged 2026-09-24 -- see ote_fvg_strategy.py's module
    # docstring. Which bars fire and at what price must stay identical (stop
    # distance doesn't affect detection); the stop value itself legitimately
    # doesn't.
    cols = ["ts", "direction", "entry"]
    check(
        "ported_signals_identical_to_reference_on_detection_columns",
        ref_sig[cols].reset_index(drop=True).equals(my_sig[cols].reset_index(drop=True)),
    )
    return ref_sig


def test_on_bar_fires_on_a_known_real_signal_bar():
    """Feed on_bar() a real window ending EXACTLY at a known reference
    signal's timestamp; it must fire the matching entry with correctly
    computed stop/target/size. Then feed it a window ending one bar EARLIER
    (same signal not yet due); it must HOLD -- proves this isn't firing on
    every bar or by coincidence."""
    from round11_fvg_bias import load_1m_brokerapi, resample_causal, detect_fvgs  # noqa: E402
    from round76_ote_pdarray_formalized import detect_ote_signals  # noqa: E402

    mnq_1m = load_1m_brokerapi(str(DATA_PATH))
    ref_fvg = detect_fvgs(resample_causal(mnq_1m, "15min"))
    ref_sig = detect_ote_signals(mnq_1m, ref_fvg)
    if ref_sig.empty:
        check("on_bar_fires_on_a_known_real_signal_bar", False, "no reference signals to test against")
        return

    mid_idx = len(ref_sig) // 2
    target_ts = pd.Timestamp(ref_sig.iloc[mid_idx]["ts"])
    direction = int(ref_sig.iloc[mid_idx]["direction"])
    pos = mnq_1m.index.get_loc(target_ts)

    strat = OteFvgStrategy()
    window_up_to_signal = _to_polars_bars(mnq_1m.iloc[: pos + 1])
    signal = strat.on_bar(window_up_to_signal)

    expected_action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT
    check(
        "on_bar_fires_on_a_known_real_signal_bar",
        signal.action == expected_action,
        f"expected={expected_action}, got={signal.action}, reason={signal.reason}",
    )
    if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
        check(
            "fired_signal_uses_bracket_shape_not_trailing",
            signal.stop_loss_price is not None and signal.take_profit_price is not None
            and signal.initial_stop_distance_points is None and signal.trail_distance_points is None,
        )
        # Stop and target sit on opposite sides of entry, FIXED_STOP_POINTS and
        # RR*FIXED_STOP_POINTS away respectively, so they're (RR+1)*FIXED_STOP_POINTS apart.
        stop_to_target = abs(signal.take_profit_price - signal.stop_loss_price)
        check(
            "fixed_stop_and_rr_target_are_correctly_sized",
            abs(stop_to_target - (RR + 1) * FIXED_STOP_POINTS) < 1e-6,
            f"stop={signal.stop_loss_price}, target={signal.take_profit_price}, got_dist={stop_to_target}",
        )
        expected_contracts = max(1, int(RISK_DOLLAR // (FIXED_STOP_POINTS * POINT_VALUE_MNQ)))
        check(
            "size_computed_from_risk_dollar_not_default_1",
            signal.size == expected_contracts,
            f"expected={expected_contracts}, got={signal.size}",
        )
        check("risk_dollars_set_for_governor_gating", signal.risk_dollars == RISK_DOLLAR)
        expected_reward = RR * FIXED_STOP_POINTS * POINT_VALUE_MNQ * signal.size - 1.24 * signal.size - 2 * 0.25 * POINT_VALUE_MNQ * signal.size
        check(
            "expected_reward_dollars_set_for_preemptive_profit_cap_gating",
            signal.expected_reward_dollars is not None and abs(signal.expected_reward_dollars - expected_reward) < 1e-6,
            f"expected={expected_reward}, got={signal.expected_reward_dollars}",
        )

    # One bar earlier: the same eventual signal must not have fired yet.
    if pos > 0:
        window_before_signal = _to_polars_bars(mnq_1m.iloc[:pos])
        earlier_signal = strat.on_bar(window_before_signal)
        check(
            "does_not_fire_one_bar_before_the_real_signal",
            earlier_signal.action == SignalAction.HOLD,
            f"action={earlier_signal.action}, reason={earlier_signal.reason}",
        )


def test_on_bar_holds_on_a_real_signal_outside_ny_rth_hours():
    """Round 87's validated numbers are NY RTH-only (09:30-16:00) -- find a
    real reference signal that fires OUTSIDE that window and confirm on_bar()
    correctly holds rather than firing on it, using the exact same real-signal
    mechanics as the known-in-RTH-hours test above."""
    from round11_fvg_bias import load_1m_brokerapi, resample_causal, detect_fvgs  # noqa: E402
    from round76_ote_pdarray_formalized import detect_ote_signals  # noqa: E402

    mnq_1m = load_1m_brokerapi(str(DATA_PATH))
    ref_fvg = detect_fvgs(resample_causal(mnq_1m, "15min"))
    ref_sig = detect_ote_signals(mnq_1m, ref_fvg)
    out_of_hours = ref_sig[~ref_sig["ts"].dt.time.between(RTH_START, RTH_END, inclusive="left")]
    if out_of_hours.empty:
        check("on_bar_holds_on_a_real_signal_outside_ny_rth_hours", False, "no out-of-RTH reference signal found to test against")
        return

    target_ts = pd.Timestamp(out_of_hours.iloc[0]["ts"])
    pos = mnq_1m.index.get_loc(target_ts)
    strat = OteFvgStrategy()
    window = _to_polars_bars(mnq_1m.iloc[: pos + 1])
    signal = strat.on_bar(window)
    check(
        "on_bar_holds_on_a_real_signal_outside_ny_rth_hours",
        signal.action == SignalAction.HOLD and "RTH" in signal.reason,
        f"bar_time={target_ts.time()}, action={signal.action}, reason={signal.reason}",
    )


def main() -> int:
    if not DATA_PATH.exists():
        print(f"SKIPPED: real data file not found at {DATA_PATH}")
        return 0
    for fn in [
        test_empty_bars_holds_without_crashing,
        test_holds_with_insufficient_history,
        test_port_matches_reference_detector_on_real_data,
        test_on_bar_fires_on_a_known_real_signal_bar,
        test_on_bar_holds_on_a_real_signal_outside_ny_rth_hours,
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
