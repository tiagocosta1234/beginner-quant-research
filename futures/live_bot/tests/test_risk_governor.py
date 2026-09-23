"""Plain-Python tests for risk_governor.py (no pytest dependency required).

Run with: python live_bot/tests/test_risk_governor.py
Exits non-zero and prints FAIL lines if anything breaks.
"""

from __future__ import annotations

import datetime as dt
import sys
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
    # Current real account state: balance 245,815.38, floor 240,877.88 -> buffer 4,937.50
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


def test_consistency_cap_blocks_oversized_single_day():
    config = AccountConfig(consistency_cap_pct=0.50)
    gov = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0)
    # Three prior profitable days totalling +9,000
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(+3_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=253_000.0)
    gov.record_fill(+3_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 23), opening_balance=256_000.0)
    gov.record_fill(+3_000.0)
    # Today: try to book +9,001, which would make today's share > 50% of total (9,000 prior + 9,001 today)
    gov.start_new_trading_day(dt.date(2026, 9, 24), opening_balance=259_000.0)
    gov.record_fill(+9_001.0)
    decision = gov.evaluate(dt.datetime(2026, 9, 24, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_blocks_oversized_single_day",
        LockoutReason.CONSISTENCY_CAP in decision.reasons and not decision.must_flatten_now,
        f"reasons={decision.reasons}, room={decision.consistency_room_left}",
    )


def test_consistency_cap_allows_compliant_day():
    config = AccountConfig(consistency_cap_pct=0.50)
    gov = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(+3_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 22), opening_balance=253_000.0)
    gov.record_fill(+2_000.0)  # today's share = 2,000 / 5,000 = 40% < 50%
    decision = gov.evaluate(dt.datetime(2026, 9, 22, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_allows_compliant_day",
        LockoutReason.CONSISTENCY_CAP not in decision.reasons,
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
    # Real account state: balance 245,815.38, floor 240,877.88 -> buffer 4,937.50
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
    # Real account state: buffer is only 4,937.50. Shrink it further with a loss
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
    # Real account state: below starting_balance (250,000), buffer = 4,937.50
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


def test_consistency_cap_not_applicable_on_first_profit_day():
    config = AccountConfig(consistency_cap_pct=0.50)
    gov = RiskGovernor(config, starting_balance=250_000.0, starting_high_water_mark=250_000.0)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=250_000.0)
    gov.record_fill(+4_000.0)  # first-ever profitable day: no prior profit to be a "share" of
    decision = gov.evaluate(dt.datetime(2026, 9, 21, 10, 0, tzinfo=CT))
    check(
        "consistency_cap_not_applicable_on_first_profit_day",
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


def main() -> int:
    for fn in [
        test_daily_loss_lockout_triggers,
        test_daily_loss_lockout_does_not_false_trigger,
        test_trailing_drawdown_breach,
        test_trailing_drawdown_not_breached_with_buffer_remaining,
        test_high_water_mark_rolls_forward_and_floor_trails,
        test_session_flatten_due_after_310pm_ct,
        test_consistency_cap_blocks_oversized_single_day,
        test_consistency_cap_allows_compliant_day,
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
        test_consistency_cap_not_applicable_on_first_profit_day,
        test_self_imposed_daily_stop_disabled_by_default,
        test_self_imposed_daily_stop_rejects_before_breach,
        test_self_imposed_daily_stop_accepts_when_room_remains,
        test_reconcile_balance_within_tolerance_ok,
        test_reconcile_balance_mismatch_forces_hard_breach,
        test_reconcile_balance_mismatch_is_sticky_across_new_trading_day,
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
