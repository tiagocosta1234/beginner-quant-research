"""Plain-Python tests for risk_governor.py (no pytest dependency required).

Run with: python live_bot/tests/test_risk_governor.py
Exits non-zero and prints FAIL lines if anything breaks.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.risk_governor import AccountConfig, DynamicSizingConfig, LockoutReason, RiskGovernor  # noqa: E402

CT = AccountConfig().timezone

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def test_daily_loss_lockout_triggers():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-2_000.0)
    gov.record_fill(-3_100.0)  # total -5,100, breaches -5,000 DLL
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "daily_loss_lockout_triggers",
        LockoutReason.DAILY_LOSS_LIMIT in decision.reasons and decision.must_flatten_now,
        f"reasons={decision.reasons}",
    )


def test_daily_loss_lockout_does_not_false_trigger():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-1_200.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "daily_loss_lockout_does_not_false_trigger",
        LockoutReason.DAILY_LOSS_LIMIT not in decision.reasons and decision.can_open_new_position,
        f"reasons={decision.reasons}",
    )


def test_trailing_drawdown_breach():
    config = AccountConfig()
    # Example account state: balance 245,815.38, floor 240,877.88 -> buffer 4,937.50
    gov = RiskGovernor(config, starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    assert abs(gov.trailing_floor() - 240_877.88) < 0.01, gov.trailing_floor()
    gov.record_fill(-4_937.50)  # exactly wipes the buffer
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "trailing_drawdown_breach_at_exact_floor",
        LockoutReason.TRAILING_DRAWDOWN in decision.reasons and decision.must_flatten_now,
        f"balance={gov.current_balance}, floor={gov.trailing_floor()}",
    )


def test_trailing_drawdown_not_breached_with_buffer_remaining():
    config = AccountConfig()
    gov = RiskGovernor(config, starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-1_000.0)  # well inside the 4,937.50 buffer
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "trailing_drawdown_not_breached_with_buffer_remaining",
        LockoutReason.TRAILING_DRAWDOWN not in decision.reasons,
        f"buffer_left={decision.remaining_drawdown_buffer}",
    )


def test_high_water_mark_rolls_forward_and_floor_trails():
    config = AccountConfig()
    gov = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(+6_000.0)  # settle day at 256,000
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=256_000.0)
    check(
        "high_water_mark_rolls_forward",
        gov.high_water_mark == 256_000.0 and abs(gov.trailing_floor() - 246_000.0) < 0.01,
        f"hwm={gov.high_water_mark}, floor={gov.trailing_floor()}",
    )


def test_session_flatten_due_after_310pm_ct():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    before = gov.evaluate(dt.datetime(2026, 9, 21, 15, 5, tzinfo=CT))
    after = gov.evaluate(dt.datetime(2026, 9, 21, 15, 11, tzinfo=CT))
    check(
        "session_flatten_due_after_310pm_ct",
        LockoutReason.SESSION_FLATTEN not in before.reasons and LockoutReason.SESSION_FLATTEN in after.reasons,
        f"before={before.reasons}, after={after.reasons}",
    )


def _fifty_k_config(**overrides):
    """A $50K account with a $3,000 profit goal: starting_balance=$50,000, profit target=$3,000
    (profit_target_balance=$53,000), matching Broker's own worked example."""
    kwargs = dict(starting_balance=50_000.0, profit_target_balance=53_000.0, consistency_cap_pct=0.55)
    kwargs.update(overrides)
    return AccountConfig(**kwargs)


def test_consistency_cap_matches_real_broker_example():
    """Replicates the usual worked example: "$50K account:
    $1,600 best day / $3,000 total profit = 53%" -- a compliant, PASSING case
    (53% < 55%). $1,400 prior + $1,600 today = exactly the $3,000 target."""
    gov = RiskGovernor(_fifty_k_config(), starting_balance=50_000.0, starting_high_water_mark=50_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=50_000.0)
    gov.record_fill(+1_400.0)
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=51_400.0)
    gov.record_fill(+1_600.0)  # 1600 / 3000 = 53.3%, under 55%
    decision = gov.evaluate(dt.datetime(2026, 9, 22, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_matches_real_broker_example",
        LockoutReason.CONSISTENCY_CAP not in decision.reasons,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_consistency_cap_catches_single_day_100pct_concentration():
    """REAL BUG this fix closes, confirmed empirically before the fix: a single
    day banking the ENTIRE profit target (zero prior profit, so this one day is
    100% of accumulated profit) must be flagged -- the old formula returned
    None (no constraint) whenever prior profit was <= 0, missing this exact
    case, the one the consistency limit most exists to catch."""
    gov = RiskGovernor(_fifty_k_config(), starting_balance=50_000.0, starting_high_water_mark=50_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=50_000.0)
    gov.record_fill(+3_500.0)  # the ENTIRE target, in one day, zero prior profit
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_catches_single_day_100pct_concentration",
        LockoutReason.CONSISTENCY_CAP in decision.reasons,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_consistency_cap_blocks_oversized_single_day_after_target_reached():
    config = _fifty_k_config(consistency_cap_pct=0.50)
    gov = RiskGovernor(config, starting_balance=50_000.0, starting_high_water_mark=50_000.0)
    # Three prior profitable days totalling +9,000 -- already well past the $3,000 target
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=50_000.0)
    gov.record_fill(+3_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=53_000.0)
    gov.record_fill(+3_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 23), opening_balance=56_000.0)
    gov.record_fill(+3_000.0)
    # Today: try to book +9,001, which would make today's share > 50% of total (9,000 prior + 9,001 today)
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=59_000.0)
    gov.record_fill(+9_001.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 24, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_blocks_oversized_single_day_after_target_reached",
        LockoutReason.CONSISTENCY_CAP in decision.reasons and not decision.must_flatten_now,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_consistency_cap_allows_compliant_day_after_target_reached():
    """Extends the real Broker example (1,400 + 1,600 = 3,000, 53.3%, compliant)
    with a THIRD day, confirming compliance correctly continues on a later day
    once the crossing itself was already legitimate -- day 1 here is
    deliberately kept below the target on its own (unlike the naive version of
    this test before the 2nd consistency fix, which had day 1 alone reach the
    entire $3,000 target from zero prior profit -- itself a violation the old,
    incomplete check couldn't see, which is exactly the bug that fix closed)."""
    gov = RiskGovernor(_fifty_k_config(), starting_balance=50_000.0, starting_high_water_mark=50_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=50_000.0)
    gov.record_fill(+1_400.0)  # below target alone -- rule doesn't bind yet
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=51_400.0)
    gov.record_fill(+1_600.0)  # crosses target compliantly: 1600/3000 = 53.3%
    gov.start_new_trading_day(dt.date(2026, 9, 23), opening_balance=53_000.0)
    gov.record_fill(+500.0)  # a further, small, compliant day: best day (1600) / total (3500) = 45.7%
    decision = gov.evaluate(dt.datetime(2026, 9, 23, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_allows_compliant_day_after_target_reached",
        LockoutReason.CONSISTENCY_CAP not in decision.reasons,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_consistency_cap_catches_a_past_day_still_dominating_a_smaller_total():
    """REAL BUG, second pass, confirmed against Round 85's actual real
    walk-forward data: a huge day (modeled here as +$11,731.20, matching the
    real Aug 27 day) followed by a small, individually-unremarkable POSITIVE
    day right after (+$1,376.00, matching the real Aug 28 day). The first
    consistency fix only ever checked TODAY's own contribution against prior
    days summed -- it had no way to see that the PAST day (Aug 27) remains the
    disqualifying one relative to a total that hasn't grown enough yet to
    dilute it. Confirmed broken before this fix: consistency_breached()
    returned False here even though the real ratio is 11731.20/13107.20 = 89.5%,
    far over the 55% cap."""
    gov = RiskGovernor(_fifty_k_config(), starting_balance=50_000.0, starting_high_water_mark=50_000.0)
    gov.start_new_trading_day(dt.date(2026, 8, 27), opening_balance=50_000.0)
    gov.record_fill(+11_731.20)
    gov.start_new_trading_day(dt.date(2026, 8, 28), opening_balance=61_731.20)
    gov.record_fill(+1_376.00)
    decision = gov.evaluate(dt.datetime(2026, 8, 28, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_catches_a_past_day_still_dominating_a_smaller_total",
        LockoutReason.CONSISTENCY_CAP in decision.reasons,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_unrealized_loss_alone_triggers_daily_loss_limit():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-3_000.0)  # realized alone does NOT breach the $5,000 DLL
    gov.update_unrealized_pnl(-2_500.0)  # but +this floating loss brings the day to -5,500
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "unrealized_loss_alone_triggers_daily_loss_limit",
        LockoutReason.DAILY_LOSS_LIMIT in decision.reasons and decision.must_flatten_now,
        f"daily_pnl={decision.daily_pnl}, reasons={decision.reasons}",
    )


def test_realized_only_does_not_false_trigger_when_floating_is_small():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-3_000.0)
    gov.update_unrealized_pnl(-500.0)  # total -3,500, still inside the $5,000 DLL
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "realized_only_does_not_false_trigger_when_floating_is_small",
        LockoutReason.DAILY_LOSS_LIMIT not in decision.reasons and decision.can_open_new_position,
        f"daily_pnl={decision.daily_pnl}, reasons={decision.reasons}",
    )


def test_unrealized_loss_alone_triggers_trailing_drawdown():
    config = AccountConfig()
    # Example account state: balance 245,815.38, floor 240,877.88 -> buffer 4,937.50
    gov = RiskGovernor(config, starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    # No realized loss at all yet, but an open position is $5,000 underwater --
    # exceeds the entire remaining buffer on paper, before any fill closes it.
    gov.update_unrealized_pnl(-5_000.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "unrealized_loss_alone_triggers_trailing_drawdown",
        LockoutReason.TRAILING_DRAWDOWN in decision.reasons and decision.must_flatten_now,
        f"equity={gov.current_equity()}, floor={gov.trailing_floor()}, reasons={decision.reasons}",
    )


def test_record_fill_clears_unrealized_pnl():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.update_unrealized_pnl(-1_800.0)
    gov.record_fill(-1_800.0)  # the position closes, realizing exactly what was floating
    check(
        "record_fill_clears_unrealized_pnl",
        gov.unrealized_pnl == 0.0 and gov.daily_realized_pnl == -1_800.0,
        f"unrealized_pnl={gov.unrealized_pnl}, daily_realized_pnl={gov.daily_realized_pnl}",
    )


def test_position_size_rejected_over_fixed_cap():
    gov = RiskGovernor(AccountConfig(max_single_trade_risk=600.0))
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    ok, reason = gov.check_position_size(601.0)
    check("position_size_rejected_over_fixed_cap", not ok and reason is not None, f"reason={reason}")


def test_position_size_accepted_within_cap_and_buffer():
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=600.0),
        starting_balance=245_815.38,
        starting_high_water_mark=250_877.88,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    ok, reason = gov.check_position_size(400.0)
    check("position_size_accepted_within_cap_and_buffer", ok and reason is None, f"reason={reason}")


def test_position_size_rejected_over_shrunk_buffer_even_under_fixed_cap():
    # Example account state: buffer is only 4,937.50. Shrink it further with a loss
    # so it drops below the (otherwise-fine) 600 fixed cap, and confirm the
    # dynamic buffer check catches what the fixed cap alone would miss.
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=600.0),
        starting_balance=245_815.38,
        starting_high_water_mark=250_877.88,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    gov.record_fill(-4_500.0)  # buffer now 437.50 -- well under the 600 fixed cap
    ok, reason = gov.check_position_size(600.0)
    check(
        "position_size_rejected_over_shrunk_buffer_even_under_fixed_cap",
        not ok and reason is not None,
        f"buffer_left={gov.remaining_drawdown_buffer()}, reason={reason}",
    )


def test_position_size_rejects_nonpositive_risk():
    gov = RiskGovernor(AccountConfig())
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    ok, reason = gov.check_position_size(0.0)
    check("position_size_rejects_nonpositive_risk", not ok and reason is not None, f"reason={reason}")


def test_consecutive_losses_lockout_triggers():
    gov = RiskGovernor(AccountConfig(consecutive_loss_limit=2))
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(-300.0)
    gov.record_fill(-300.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consecutive_losses_lockout_triggers",
        LockoutReason.CONSECUTIVE_LOSSES in decision.reasons
        and not decision.can_open_new_position
        and not decision.must_flatten_now,
        f"reasons={decision.reasons}, streak={gov.consecutive_losses}",
    )


def test_consecutive_losses_reset_by_a_win():
    gov = RiskGovernor(AccountConfig(consecutive_loss_limit=2))
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(-300.0)
    gov.record_fill(+150.0)  # win resets the streak
    gov.record_fill(-300.0)  # streak is 1 again, not 3
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consecutive_losses_reset_by_a_win",
        LockoutReason.CONSECUTIVE_LOSSES not in decision.reasons and gov.consecutive_losses == 1,
        f"reasons={decision.reasons}, streak={gov.consecutive_losses}",
    )


def test_consecutive_losses_not_extended_or_reset_by_breakeven():
    gov = RiskGovernor(AccountConfig(consecutive_loss_limit=2))
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(-300.0)  # streak 1
    gov.record_fill(0.0)  # BE fill -- streak stays 1, not reset and not incremented
    gov.record_fill(-300.0)  # streak 2 -- locks out
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consecutive_losses_not_extended_or_reset_by_breakeven",
        LockoutReason.CONSECUTIVE_LOSSES in decision.reasons and gov.consecutive_losses == 2,
        f"reasons={decision.reasons}, streak={gov.consecutive_losses}",
    )


def test_consecutive_losses_reset_on_new_trading_day():
    gov = RiskGovernor(AccountConfig(consecutive_loss_limit=2))
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(-300.0)
    gov.record_fill(-300.0)  # locked out today
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=249_400.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 22, 10, 0, tzinfo=CT))
    check(
        "consecutive_losses_reset_on_new_trading_day",
        LockoutReason.CONSECUTIVE_LOSSES not in decision.reasons and gov.consecutive_losses == 0,
        f"reasons={decision.reasons}, streak={gov.consecutive_losses}",
    )


def _run_n_losing_days(gov, n, start_date, daily_loss=-300.0):
    day = start_date
    for _ in range(n):
        gov.start_new_trading_day(day, opening_balance=gov.current_balance)
        gov.record_fill(daily_loss)
        day = day + dt.timedelta(days=1)
    return day


def test_consecutive_losing_days_lockout_triggers():
    """Real gap this rule closes: consecutive_loss_limit (rule 6) resets every
    day, so it never sees a run of separate bad DAYS -- round83's real
    walk-forward found exactly this (5 losing days in a row, each individually
    safe, summing to more than the real $2,000 MLL)."""
    gov = RiskGovernor(AccountConfig(consecutive_losing_days_limit=5))
    next_day = _run_n_losing_days(gov, 5, dt.date(2026, 9, 18))
    gov.start_new_trading_day(next_day, opening_balance=gov.current_balance)  # rolls the 5th day in
    decision = gov.evaluate(dt.datetime(next_day.year, next_day.month, next_day.day, 10, 0, tzinfo=CT))
    check(
        "consecutive_losing_days_lockout_triggers",
        LockoutReason.CONSECUTIVE_LOSING_DAYS in decision.reasons
        and not decision.can_open_new_position
        and not decision.must_flatten_now,
        f"reasons={decision.reasons}, streak={gov.consecutive_losing_days}",
    )


def test_consecutive_losing_days_not_triggered_below_limit():
    gov = RiskGovernor(AccountConfig(consecutive_losing_days_limit=5))
    next_day = _run_n_losing_days(gov, 4, dt.date(2026, 9, 18))
    gov.start_new_trading_day(next_day, opening_balance=gov.current_balance)
    decision = gov.evaluate(dt.datetime(next_day.year, next_day.month, next_day.day, 10, 0, tzinfo=CT))
    check(
        "consecutive_losing_days_not_triggered_below_limit",
        LockoutReason.CONSECUTIVE_LOSING_DAYS not in decision.reasons and gov.consecutive_losing_days == 4,
        f"reasons={decision.reasons}, streak={gov.consecutive_losing_days}",
    )


def test_consecutive_losing_days_reset_by_a_winning_day():
    gov = RiskGovernor(AccountConfig(consecutive_losing_days_limit=5))
    next_day = _run_n_losing_days(gov, 4, dt.date(2026, 9, 18))
    gov.start_new_trading_day(next_day, opening_balance=gov.current_balance)
    gov.record_fill(+900.0)  # a winning day breaks the streak
    day_after = next_day + dt.timedelta(days=1)
    gov.start_new_trading_day(day_after, opening_balance=gov.current_balance)  # rolls the winning day in
    check(
        "consecutive_losing_days_reset_by_a_winning_day",
        gov.consecutive_losing_days == 0,
        f"streak={gov.consecutive_losing_days}",
    )


def test_consecutive_losing_days_unaffected_by_intraday_losses_within_the_day_cap():
    """Rule 6 (intraday) and rule 11 (cross-day) must stay independent: several
    losing FILLS within one day that nets negative should count as exactly ONE
    losing day here, not multiply-count."""
    gov = RiskGovernor(AccountConfig(consecutive_loss_limit=10, consecutive_losing_days_limit=5))
    day = dt.date(2026, 9, 18)
    for _ in range(5):
        gov.start_new_trading_day(day, opening_balance=gov.current_balance)
        gov.record_fill(-444.80)
        gov.record_fill(-444.80)  # two losing fills, one losing DAY
        day = day + dt.timedelta(days=1)
    gov.start_new_trading_day(day, opening_balance=gov.current_balance)
    decision = gov.evaluate(dt.datetime(day.year, day.month, day.day, 10, 0, tzinfo=CT))
    check(
        "consecutive_losing_days_unaffected_by_intraday_losses_within_the_day_cap",
        LockoutReason.CONSECUTIVE_LOSING_DAYS in decision.reasons and gov.consecutive_losing_days == 5,
        f"reasons={decision.reasons}, streak={gov.consecutive_losing_days}",
    )


def test_dynamic_sizing_disabled_by_default():
    gov = RiskGovernor(AccountConfig(), starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    check(
        "dynamic_sizing_disabled_by_default",
        gov.compute_dynamic_risk() is None,
        "expected None when AccountConfig.dynamic_sizing is not set",
    )


def test_dynamic_sizing_below_start_uses_lower_fraction():
    config = AccountConfig(dynamic_sizing=DynamicSizingConfig(frac_below_start=0.04, frac_above_start=0.12))
    # Example account state: below starting_balance (250,000), buffer = 4,937.50
    gov = RiskGovernor(config, starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    expected = 0.04 * 4_937.50  # 197.50, between the default floor/ceil
    check(
        "dynamic_sizing_below_start_uses_lower_fraction",
        abs(gov.compute_dynamic_risk() - expected) < 0.01,
        f"got={gov.compute_dynamic_risk()}, expected={expected}",
    )


def test_dynamic_sizing_above_start_uses_higher_fraction():
    config = AccountConfig(dynamic_sizing=DynamicSizingConfig(frac_below_start=0.04, frac_above_start=0.12))
    # Above starting_balance (250,000): balance == HWM == 255,000 -> no drawdown from HWM,
    # so the full trailing_dd_amount (10,000 default) is the remaining buffer.
    gov = RiskGovernor(config, starting_balance=255_000.0, starting_high_water_mark=255_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=255_000.0)
    expected = 0.12 * 10_000.0  # 1,200.0
    check(
        "dynamic_sizing_above_start_uses_higher_fraction",
        abs(gov.compute_dynamic_risk() - expected) < 0.01,
        f"got={gov.compute_dynamic_risk()}, expected={expected}",
    )


def test_dynamic_sizing_respects_floor():
    # Tiny buffer -> fraction alone would propose less than the floor
    config = AccountConfig(dynamic_sizing=DynamicSizingConfig(frac_below_start=0.04, risk_floor=25.0))
    gov = RiskGovernor(config, starting_balance=245_200.0, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_200.0)
    # buffer = 245,200 - 240,877.88 = 4,322.12; 4% of that = 172.88, well above the floor,
    # so shrink the buffer further via a loss to actually test the floor kicking in.
    gov.record_fill(-3_700.0)  # buffer now ~622.12; 4% = ~24.88, below the 25.0 floor
    check(
        "dynamic_sizing_respects_floor",
        abs(gov.compute_dynamic_risk() - 25.0) < 0.01,
        f"got={gov.compute_dynamic_risk()}, buffer={gov.remaining_drawdown_buffer()}",
    )


def test_dynamic_sizing_respects_ceiling():
    config = AccountConfig(dynamic_sizing=DynamicSizingConfig(frac_above_start=0.50, risk_ceil=2_500.0))
    # Large buffer well above start -> 50% of it would blow past the ceiling
    gov = RiskGovernor(config, starting_balance=300_000.0, starting_high_water_mark=300_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=300_000.0)
    check(
        "dynamic_sizing_respects_ceiling",
        abs(gov.compute_dynamic_risk() - 2_500.0) < 0.01,
        f"got={gov.compute_dynamic_risk()}",
    )


def test_dynamic_sizing_suggestion_still_subject_to_check_position_size():
    # A generous dynamic suggestion must still be rejected by check_position_size()
    # if it exceeds the hard per-trade cap -- dynamic sizing proposes, it doesn't bypass.
    config = AccountConfig(
        max_single_trade_risk=100.0,
        dynamic_sizing=DynamicSizingConfig(frac_above_start=0.50, risk_ceil=2_500.0),
    )
    gov = RiskGovernor(config, starting_balance=300_000.0, starting_high_water_mark=300_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=300_000.0)
    suggested = gov.compute_dynamic_risk()
    ok, reason = gov.check_position_size(suggested)
    check(
        "dynamic_sizing_suggestion_still_subject_to_check_position_size",
        suggested > 100.0 and not ok and reason is not None,
        f"suggested={suggested}, ok={ok}, reason={reason}",
    )


def test_self_imposed_daily_stop_disabled_by_default():
    gov = RiskGovernor(AccountConfig(max_single_trade_risk=2_100.0))
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=247_937.86)
    gov.record_fill(-2_900.0)  # would breach a $3,000 stop if one were configured
    ok, reason = gov.check_position_size(1_500.0)
    check("self_imposed_daily_stop_disabled_by_default", ok and reason is None, f"reason={reason}")


def test_self_imposed_daily_stop_rejects_before_breach():
    # Round 69's exact rule: reject if today's P&L minus the proposed trade's own
    # risk would already be at or past -cap -- catches the trade BEFORE it can
    # push the day past the ceiling, not after.
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, self_imposed_daily_stop=3_000.0),
        starting_balance=247_937.86, starting_high_water_mark=250_877.88,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=247_937.86)
    gov.record_fill(-1_600.0)  # today's P&L: -1,600
    ok, reason = gov.check_position_size(1_500.0)  # -1,600 - 1,500 = -3,100 <= -3,000
    check("self_imposed_daily_stop_rejects_before_breach", not ok and reason is not None, f"reason={reason}")


def test_self_imposed_daily_stop_accepts_when_room_remains():
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, self_imposed_daily_stop=3_000.0),
        starting_balance=247_937.86, starting_high_water_mark=250_877.88,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=247_937.86)
    gov.record_fill(-500.0)  # today's P&L: -500
    ok, reason = gov.check_position_size(1_500.0)  # -500 - 1,500 = -2,000, still above -3,000
    check("self_imposed_daily_stop_accepts_when_room_remains", ok and reason is None, f"reason={reason}")


def test_max_daily_profit_disabled_by_default():
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    gov.record_fill(+5_000.0)  # would breach a $1,650 cap if one were configured
    ok, reason = gov.check_position_size(500.0)
    check("max_daily_profit_disabled_by_default", ok and reason is None, f"reason={reason}")


def test_max_daily_profit_rejects_new_entry_once_cap_reached():
    """the trader's exact instruction: "we cant have days above $1650" -- $1,650 =
    0.55 x a $3,000 profit goal, the theoretical max a single day can be
    and still be consistency-compliant right at the target."""
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, max_daily_profit=1_650.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    gov.record_fill(+1_650.0)  # already at the cap
    ok, reason = gov.check_position_size(500.0)
    check("max_daily_profit_rejects_new_entry_once_cap_reached", not ok and reason is not None, f"reason={reason}")


def test_max_daily_profit_accepts_when_room_remains():
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, max_daily_profit=1_650.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    gov.record_fill(+800.0)  # under the cap
    ok, reason = gov.check_position_size(500.0)
    check("max_daily_profit_accepts_when_room_remains", ok and reason is None, f"reason={reason}")


def test_max_daily_profit_cannot_shrink_a_single_fill_that_already_overshot():
    """Real, disclosed limit: this rule can only ever act BETWEEN trades (same
    structural limit as rule 8's loss-side version) -- it cannot retroactively
    shrink a single fill that already landed above the cap in one shot, e.g. a
    fixed-target strategy whose own take-profit is bigger than the cap."""
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=5_000.0, max_daily_profit=1_650.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    gov.record_fill(+3_155.20)  # one fill, already nearly double the cap -- already happened
    ok, reason = gov.check_position_size(500.0)  # the NEXT proposed entry is correctly blocked
    check(
        "max_daily_profit_cannot_shrink_a_single_fill_that_already_overshot",
        not ok and gov.daily_realized_pnl == 3155.20,
        f"reason={reason}, daily_realized_pnl={gov.daily_realized_pnl}",
    )


def test_max_daily_profit_preemptively_refuses_a_trade_whose_win_would_breach_it():
    """REAL FIX 2026-09-24: the reactive-only check above was proven
    insufficient in the backtest engine (round76) once two individually-
    compliant wins the same real day still summed past $1,650, since the
    first alone never triggered the reactive halt. This mirrors rule 8's own
    loss-side principle: refuse a trade whose own BEST case could breach the
    cap, checked BEFORE it happens."""
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, max_daily_profit=1_650.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    gov.record_fill(+1_155.20)  # one compliant win booked, still under the cap
    # A second trade whose own full win ($1,155.20) would push today to $2,310.40 -- over the cap
    ok, reason = gov.check_position_size(300.0, proposed_reward_dollars=1_155.20)
    check(
        "max_daily_profit_preemptively_refuses_a_trade_whose_win_would_breach_it",
        not ok and reason is not None,
        f"reason={reason}",
    )


def test_max_daily_profit_allows_a_trade_whose_win_stays_under_the_cap():
    gov = RiskGovernor(
        AccountConfig(max_single_trade_risk=2_100.0, max_daily_profit=1_650.0),
        starting_balance=50_000.0, starting_high_water_mark=50_000.0,
    )
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=50_000.0)
    ok, reason = gov.check_position_size(300.0, proposed_reward_dollars=1_155.20)  # first trade of the day
    check("max_daily_profit_allows_a_trade_whose_win_stays_under_the_cap", ok and reason is None, f"reason={reason}")


def test_consistency_cap_not_applicable_before_reaching_target():
    """$4,000 profit on a $250K account (default profit_target_balance=$265,000,
    i.e. a $15,000 target) is nowhere near the target -- the rule correctly does
    not bind yet. Distinct from the OLD (buggy) reasoning this test used to
    encode ("no prior profit to compare against") -- see
    consistency_cap_catches_single_day_100pct_concentration for the real gap
    that reasoning was hiding."""
    config = AccountConfig(consistency_cap_pct=0.50)
    gov = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(+4_000.0)  # nowhere near the $15,000 target yet
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_not_applicable_before_reaching_target",
        decision.consistency_room_left is None and LockoutReason.CONSISTENCY_CAP not in decision.reasons,
        f"room={decision.consistency_room_left}, reasons={decision.reasons}",
    )


def test_reconcile_balance_within_tolerance_ok():
    gov = RiskGovernor(AccountConfig(), starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 23), opening_balance=245_815.38)
    ok = gov.reconcile_balance(245_815.38 + 10.0)  # inside the $25 default tolerance
    decision = gov.evaluate(dt.datetime(2026, 9, 23, 10, 0, tzinfo=CT))
    check(
        "reconcile_balance_within_tolerance_ok",
        ok and not gov.balance_reconciliation_mismatch
        and LockoutReason.BALANCE_RECONCILIATION_MISMATCH not in decision.reasons,
        f"diff={gov.last_reconciliation_diff}, reasons={decision.reasons}",
    )


def test_reconcile_balance_mismatch_forces_hard_breach():
    gov = RiskGovernor(AccountConfig(), starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 23), opening_balance=245_815.38)
    # A real untracked move (e.g. a manual trade) -- live balance is $500 lower
    # than what this governor ever recorded via record_fill().
    ok = gov.reconcile_balance(245_815.38 - 500.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 23, 10, 0, tzinfo=CT))
    check(
        "reconcile_balance_mismatch_forces_hard_breach",
        not ok and gov.balance_reconciliation_mismatch
        and LockoutReason.BALANCE_RECONCILIATION_MISMATCH in decision.reasons
        and decision.must_flatten_now and not decision.can_open_new_position,
        f"diff={gov.last_reconciliation_diff}, reasons={decision.reasons}",
    )


def test_reconcile_balance_mismatch_is_sticky_across_new_trading_day():
    gov = RiskGovernor(AccountConfig(), starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=245_815.38)
    gov.reconcile_balance(245_815.38 - 500.0)  # trips the mismatch
    gov.start_new_trading_day(dt.date(2026, 9, 23))  # new session, no restart
    decision = gov.evaluate(dt.datetime(2026, 9, 23, 10, 0, tzinfo=CT))
    check(
        "reconcile_balance_mismatch_is_sticky_across_new_trading_day",
        gov.balance_reconciliation_mismatch and LockoutReason.BALANCE_RECONCILIATION_MISMATCH in decision.reasons,
        f"reasons={decision.reasons}",
    )


def test_state_persists_prior_days_pnl_and_losing_streak_across_restart():
    """Real gap found 2026-09-24: prior_days_pnl/consecutive_losing_days lived
    only in memory, so a process restart silently reset rule 11's (5-losing-day
    circuit breaker) counter to 0 and forgot every prior day's PnL rule 3
    (consistency cap) needs. Simulates two real restarts (fresh RiskGovernor
    instances, same state_file) across three losing days and confirms both
    survive intact -- not just that the file exists."""
    state_path = Path(tempfile.mkdtemp()) / "state.json"
    config = AccountConfig()

    gov1 = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0, state_file=state_path)
    gov1.start_new_trading_day(dt.date(2026, 9, 1), opening_balance=250_000.0)
    gov1.record_fill(-500.0)
    gov1.start_new_trading_day(dt.date(2026, 9, 2), opening_balance=249_500.0)  # rolls day 1 in
    gov1.record_fill(-300.0)
    gov1.start_new_trading_day(dt.date(2026, 9, 3), opening_balance=249_200.0)  # rolls day 2 in

    # Restart #1: brand new instance, same state_file, live balance re-seeded.
    gov2 = RiskGovernor(config, starting_balance=249_200.0, starting_high_water_mark=250_000.0, state_file=state_path)
    gov2.record_fill(-100.0)
    gov2.start_new_trading_day(dt.date(2026, 9, 4), opening_balance=249_100.0)  # rolls day 3 in

    # Restart #2: confirm it keeps accumulating, not just surviving one hop.
    gov3 = RiskGovernor(config, starting_balance=249_100.0, starting_high_water_mark=250_000.0, state_file=state_path)
    check(
        "state_persists_prior_days_pnl_and_losing_streak_across_restart",
        gov3.consecutive_losing_days == 3
        and gov3.prior_days_pnl == {
            dt.date(2026, 9, 1): -500.0,
            dt.date(2026, 9, 2): -300.0,
            dt.date(2026, 9, 3): -100.0,
        }
        and gov3.current_trading_date == dt.date(2026, 9, 4),
        f"consecutive_losing_days={gov3.consecutive_losing_days}, prior_days_pnl={gov3.prior_days_pnl}, "
        f"current_trading_date={gov3.current_trading_date}",
    )


def test_state_persists_todays_pnl_and_streak_across_a_same_day_restart():
    """Deeper version of the same real gap: main.py calls start_new_trading_day()
    unconditionally on every process startup, even mid-day, and that method used
    to unconditionally reset daily_realized_pnl/consecutive_losses -- meaning a
    same-day restart quietly forgot the day's trading SO FAR, undermining rules
    1/6/12 for the rest of that day. Confirms a restart followed by the exact
    call main.py makes (same session_date) preserves both instead of zeroing them."""
    state_path = Path(tempfile.mkdtemp()) / "state.json"
    config = AccountConfig()

    gov1 = RiskGovernor(config, starting_balance=250_000.0, state_file=state_path)
    gov1.start_new_trading_day(dt.date(2026, 9, 10), opening_balance=250_000.0)
    gov1.record_fill(-200.0)  # one loss today, before the "restart"

    # Restart mid-day: fresh instance, live balance re-seeded, same state_file.
    gov2 = RiskGovernor(config, starting_balance=249_800.0, state_file=state_path)
    gov2.start_new_trading_day(dt.date(2026, 9, 10))  # main.py's real call shape: same date as before restart

    check(
        "state_persists_todays_pnl_and_streak_across_a_same_day_restart",
        gov2.daily_realized_pnl == -200.0 and gov2.consecutive_losses == 1 and gov2.current_balance == 249_800.0,
        f"daily_realized_pnl={gov2.daily_realized_pnl}, consecutive_losses={gov2.consecutive_losses}, "
        f"current_balance={gov2.current_balance}",
    )


def test_missing_state_file_starts_fresh_without_crashing():
    state_path = Path(tempfile.mkdtemp()) / "does_not_exist_yet.json"
    gov = RiskGovernor(AccountConfig(), state_file=state_path)
    check(
        "missing_state_file_starts_fresh_without_crashing",
        gov.prior_days_pnl == {} and gov.consecutive_losing_days == 0 and gov.current_trading_date is None,
        f"prior_days_pnl={gov.prior_days_pnl}, consecutive_losing_days={gov.consecutive_losing_days}",
    )


def test_corrupt_state_file_fails_safe_to_fresh_start():
    state_path = Path(tempfile.mkdtemp()) / "corrupt.json"
    state_path.write_text("{not valid json at all")
    gov = RiskGovernor(AccountConfig(), state_file=state_path)
    check(
        "corrupt_state_file_fails_safe_to_fresh_start",
        gov.prior_days_pnl == {} and gov.consecutive_losing_days == 0 and gov.current_trading_date is None,
        f"prior_days_pnl={gov.prior_days_pnl}, consecutive_losing_days={gov.consecutive_losing_days}",
    )


def main() -> int:
    for fn in [
        test_daily_loss_lockout_triggers,
        test_daily_loss_lockout_does_not_false_trigger,
        test_trailing_drawdown_breach,
        test_trailing_drawdown_not_breached_with_buffer_remaining,
        test_high_water_mark_rolls_forward_and_floor_trails,
        test_session_flatten_due_after_310pm_ct,
        test_consistency_cap_matches_real_broker_example,
        test_consistency_cap_catches_single_day_100pct_concentration,
        test_consistency_cap_blocks_oversized_single_day_after_target_reached,
        test_consistency_cap_allows_compliant_day_after_target_reached,
        test_consistency_cap_catches_a_past_day_still_dominating_a_smaller_total,
        test_unrealized_loss_alone_triggers_daily_loss_limit,
        test_realized_only_does_not_false_trigger_when_floating_is_small,
        test_unrealized_loss_alone_triggers_trailing_drawdown,
        test_record_fill_clears_unrealized_pnl,
        test_position_size_rejected_over_fixed_cap,
        test_position_size_accepted_within_cap_and_buffer,
        test_position_size_rejected_over_shrunk_buffer_even_under_fixed_cap,
        test_position_size_rejects_nonpositive_risk,
        test_consecutive_losses_lockout_triggers,
        test_consecutive_losses_reset_by_a_win,
        test_consecutive_losses_not_extended_or_reset_by_breakeven,
        test_consecutive_losses_reset_on_new_trading_day,
        test_dynamic_sizing_disabled_by_default,
        test_dynamic_sizing_below_start_uses_lower_fraction,
        test_dynamic_sizing_above_start_uses_higher_fraction,
        test_dynamic_sizing_respects_floor,
        test_dynamic_sizing_respects_ceiling,
        test_dynamic_sizing_suggestion_still_subject_to_check_position_size,
        test_consistency_cap_not_applicable_before_reaching_target,
        test_self_imposed_daily_stop_disabled_by_default,
        test_self_imposed_daily_stop_rejects_before_breach,
        test_self_imposed_daily_stop_accepts_when_room_remains,
        test_max_daily_profit_disabled_by_default,
        test_max_daily_profit_rejects_new_entry_once_cap_reached,
        test_max_daily_profit_accepts_when_room_remains,
        test_max_daily_profit_cannot_shrink_a_single_fill_that_already_overshot,
        test_max_daily_profit_preemptively_refuses_a_trade_whose_win_would_breach_it,
        test_max_daily_profit_allows_a_trade_whose_win_stays_under_the_cap,
        test_reconcile_balance_within_tolerance_ok,
        test_reconcile_balance_mismatch_forces_hard_breach,
        test_reconcile_balance_mismatch_is_sticky_across_new_trading_day,
        test_consecutive_losing_days_lockout_triggers,
        test_consecutive_losing_days_not_triggered_below_limit,
        test_consecutive_losing_days_reset_by_a_winning_day,
        test_consecutive_losing_days_unaffected_by_intraday_losses_within_the_day_cap,
        test_state_persists_prior_days_pnl_and_losing_streak_across_restart,
        test_state_persists_todays_pnl_and_streak_across_a_same_day_restart,
        test_missing_state_file_starts_fresh_without_crashing,
        test_corrupt_state_file_fails_safe_to_fresh_start,
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
