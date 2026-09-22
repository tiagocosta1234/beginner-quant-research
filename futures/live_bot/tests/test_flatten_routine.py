"""Plain-Python tests for flatten_routine.py (no pytest dependency required).

Run with: python live_bot/tests/test_flatten_routine.py
Exits non-zero and prints FAIL lines if anything breaks.

Covers the naive-vs-aware datetime bug found 2026-09-20 during the first
real practice-mode run: `can_open_new_position()` raised
`TypeError: can't compare offset-naive and offset-aware datetimes` on every
single polling cycle, before the bot ever reached strategy evaluation. There
was no test for this method at all before this file.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.flatten_routine import CENTRAL_TZ, FlattenRoutine  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def _routine() -> FlattenRoutine:
    return FlattenRoutine(broker=None, account_config=None, pnl_tracker=None)


def test_can_open_new_position_does_not_raise():
    routine = _routine()
    # The regression: this used to raise TypeError before ever returning.
    # If it raises now, this whole test script crashes loudly rather than
    # reporting a quiet FAIL -- intentional, since a crash here means the
    # bot's main loop would crash on every cycle in production.
    result = routine.can_open_new_position()
    check("can_open_new_position_does_not_raise", isinstance(result, bool), f"result={result}")


def test_minutes_until_flatten_same_day():
    routine = _routine()
    now = dt.datetime(2026, 9, 21, 14, 0, tzinfo=CENTRAL_TZ)  # 2:00 PM CT
    minutes = routine._minutes_until_flatten(now)
    check("minutes_until_flatten_same_day", abs(minutes - 70.0) < 0.01, f"minutes={minutes}")


def test_minutes_until_flatten_rolls_to_tomorrow():
    routine = _routine()
    now = dt.datetime(2026, 9, 21, 16, 0, tzinfo=CENTRAL_TZ)  # 4:00 PM CT, past 3:10
    minutes = routine._minutes_until_flatten(now)
    check(
        "minutes_until_flatten_rolls_to_tomorrow",
        abs(minutes - 1390.0) < 0.01,
        f"minutes={minutes}",
    )


def test_minutes_until_flatten_across_month_boundary():
    routine = _routine()
    # Last day of a 31-day month, past flatten time: the original code's
    # `target_dt.replace(day=target_dt.day + 1)` would raise ValueError
    # here (day=32 is invalid). timedelta addition must not.
    now = dt.datetime(2026, 10, 31, 16, 0, tzinfo=CENTRAL_TZ)
    minutes = routine._minutes_until_flatten(now)
    check(
        "minutes_until_flatten_across_month_boundary",
        abs(minutes - 1390.0) < 0.01,
        f"minutes={minutes}",
    )


def test_within_10_minutes_of_flatten():
    routine = _routine()
    now = dt.datetime(2026, 9, 21, 15, 5, tzinfo=CENTRAL_TZ)  # 3:05 PM CT
    minutes = routine._minutes_until_flatten(now)
    check("within_10_minutes_of_flatten", minutes < 10, f"minutes={minutes}")


def test_trading_locked_blocks_new_entries():
    routine = _routine()
    routine.trading_locked_today = True
    check(
        "trading_locked_blocks_new_entries",
        routine.can_open_new_position() is False,
        "",
    )


def main() -> int:
    for fn in [
        test_can_open_new_position_does_not_raise,
        test_minutes_until_flatten_same_day,
        test_minutes_until_flatten_rolls_to_tomorrow,
        test_minutes_until_flatten_across_month_boundary,
        test_within_10_minutes_of_flatten,
        test_trading_locked_blocks_new_entries,
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
