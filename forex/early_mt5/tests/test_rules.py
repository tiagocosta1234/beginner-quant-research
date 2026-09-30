"""Tests for forex/early_mt5/rules.py against MT5 broker's own published definitions and examples.
Run: python -m pytest forex/early_mt5/tests -q   (or python forex/early_mt5/tests/test_rules.py)"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mt5broker.rules import PHASE1, PHASE2, ChallengeRules, ChallengeState, mt5broker_day  # noqa: E402

UTC = dt.timezone.utc
PRAGUE = ZoneInfo("Europe/Prague")


def at(y, m, d, h, mi=0, tz=PRAGUE):
    return dt.datetime(y, m, d, h, mi, tzinfo=tz)


def test_limits_for_100k():
    assert PHASE1.target_balance == 110_000 and PHASE2.target_balance == 105_000
    assert PHASE1.max_loss_floor == 90_000 and PHASE1.daily_loss_amount == 5_000


def test_mt5broker_published_200k_daily_example():
    # academy.mt5broker.com: day 1 limit 190,000; balance 204,000 at midnight -> 194,000; 202,000 -> 192,000
    s = ChallengeState(ChallengeRules(target_pct=0.10, initial=200_000))
    s.on_update(at(2026, 10, 1, 9), 200_000, 200_000)
    assert s.daily_floor() == 190_000
    s.on_update(at(2026, 10, 2, 0, 1), 204_000, 204_000)
    assert s.daily_floor() == 194_000
    s.on_update(at(2026, 10, 3, 0, 1), 202_000, 202_000)
    assert s.daily_floor() == 192_000


def test_daily_breach_is_on_equity_intraday():
    s = ChallengeState(PHASE1)
    assert s.on_update(at(2026, 10, 1, 15), 100_000, 95_500) is None
    assert s.on_update(at(2026, 10, 1, 16), 100_000, 94_999) == "max_daily_loss"
    # a breach is permanent even if equity recovers
    assert s.on_update(at(2026, 10, 1, 17), 100_000, 101_000) == "max_daily_loss"


def test_floor_is_the_tighter_of_daily_and_static():
    s = ChallengeState(PHASE1)
    s.on_update(at(2026, 10, 1, 9), 100_000, 100_000)
    s.on_update(at(2026, 10, 2, 0, 5), 93_000, 93_000)   # day 2 starts at 93,000 -> daily floor 88,000
    assert s.daily_floor() == 88_000 and s.floor() == 90_000   # the static 90,000 binds
    assert s.on_update(at(2026, 10, 2, 10), 93_000, 89_999) == "max_loss"


def test_overnight_position_judged_against_new_day():
    # up on the day: balance 103,000 at midnight -> new limit 98,000; an open loser at -5,500 floating breaches
    s = ChallengeState(PHASE1)
    s.on_update(at(2026, 10, 1, 9), 100_000, 100_000)
    s.on_update(at(2026, 10, 1, 23), 103_000, 99_000)      # still day 1: floor 95,000, fine
    assert s.breach is None
    assert s.on_update(at(2026, 10, 2, 0, 1), 103_000, 97_500) == "max_daily_loss"


def test_day_rolls_at_prague_midnight_not_utc():
    # 22:30 UTC in summer is 00:30 Prague -> already the next MT5 broker day
    assert mt5broker_day(dt.datetime(2026, 7, 1, 22, 30, tzinfo=UTC)) == dt.date(2026, 7, 2)
    # in winter (CET, UTC+1) 22:30 UTC is 23:30 Prague -> same day
    assert mt5broker_day(dt.datetime(2026, 12, 1, 22, 30, tzinfo=UTC)) == dt.date(2026, 12, 1)


def test_trading_day_counts_openings_in_prague_days():
    s = ChallengeState(PHASE1)
    for t in (at(2026, 10, 1, 15), at(2026, 10, 1, 20), at(2026, 10, 2, 15), at(2026, 10, 5, 15)):
        s.on_position_opened(t)
    assert s.objectives(111_000, 0)["min_trading_days"] is False      # 3 days
    s.on_position_opened(at(2026, 10, 6, 15))
    assert s.objectives(111_000, 0)["min_trading_days"] is True


def test_target_needs_balance_and_flat():
    s = ChallengeState(PHASE1)
    for d in (1, 2, 5, 6):
        s.on_position_opened(at(2026, 10, d, 15))
    assert s.objectives(110_500, 1)["passed"] is False               # a position still open
    assert s.objectives(110_000, 0)["passed"] is False               # must EXCEED the target
    assert s.objectives(110_000.01, 0)["passed"] is True


def test_naive_timestamp_rejected():
    try:
        mt5broker_day(dt.datetime(2026, 10, 1, 12))
    except ValueError:
        return
    raise AssertionError("naive timestamp accepted")


def test_state_round_trips():
    s = ChallengeState(PHASE2)
    s.on_update(at(2026, 10, 1, 9), 100_000, 100_000)
    s.on_position_opened(at(2026, 10, 1, 15))
    s2 = ChallengeState.from_dict(s.to_dict())
    assert s2.to_dict() == s.to_dict() and s2.rules.target_pct == 0.05


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed")
