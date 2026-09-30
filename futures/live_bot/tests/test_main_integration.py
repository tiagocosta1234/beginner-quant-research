"""Integration tests for main.py's handle_entry_signal() -- the seam connecting a
Signal (from a Strategy) through sizing resolution and RiskGovernor gating to an
actual broker order call. Each piece (Strategy, RiskGovernor) is unit-tested in
isolation elsewhere in this directory; this file exists because their WIRING
together was never tested until now, and that is exactly where a real bug (the
poll-count-vs-bar-count mismatch caught while building
random_entry_atr_trail_strategy.py) previously hid.

No network calls, no real API key -- FakeBroker below stands in for BrokerClient
and just records what it was called with.

Run with: python live_bot/tests/test_main_integration.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.broker_client import BrokerConfig  # noqa: E402
from live_bot.main import handle_entry_signal  # noqa: E402
from live_bot.risk_governor import AccountConfig, DynamicSizingConfig, RiskGovernor  # noqa: E402
from live_bot.strategy_interface import Signal, SignalAction  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


class FakeBroker:
    """Records every call instead of touching a network. `has_open_position`
    and the trailing-stop response's `.success` are configurable per test."""

    def __init__(self, has_open_position: bool = False, trail_success: bool = True,
                 fill_price: float | None = None, modify_ok: bool = True, modify_raises: bool = False) -> None:
        self._has_open_position = has_open_position
        self._trail_success = trail_success
        self._fill_price = fill_price
        self._modify_ok = modify_ok
        self._modify_raises = modify_raises
        self.calls: list[tuple[str, dict]] = []

    async def has_open_position(self) -> bool:
        return self._has_open_position

    def get_contract_id(self) -> str:
        return "CON.F.US.MNQ.Z26"

    async def place_market_entry_with_trailing_stop(self, **kwargs):
        self.calls.append(("place_market_entry_with_trailing_stop", kwargs))
        entry_resp = SimpleNamespace(success=True)
        trail_resp = SimpleNamespace(success=self._trail_success)
        return entry_resp, trail_resp

    async def place_bracket_order(self, **kwargs):
        self.calls.append(("place_bracket_order", kwargs))
        return SimpleNamespace(success=True, entry_order_id=111, stop_order_id=222, target_order_id=333)

    async def get_entry_fill_price(self, order_id, since):
        self.calls.append(("get_entry_fill_price", {"order_id": order_id}))
        return self._fill_price

    async def modify_stop_price(self, order_id, stop_price):
        self.calls.append(("modify_stop_price", {"order_id": order_id, "stop_price": stop_price}))
        if self._modify_raises:
            raise RuntimeError("broker rejected the modify")
        return self._modify_ok

    async def flatten_all(self):
        self.calls.append(("flatten_all", {}))
        return SimpleNamespace(success=True)


def make_governor(dynamic_sizing: DynamicSizingConfig | None = None) -> RiskGovernor:
    import datetime as dt

    config = AccountConfig(max_single_trade_risk=600.0, dynamic_sizing=dynamic_sizing)
    gov = RiskGovernor(config, starting_balance=245_815.38, starting_high_water_mark=250_877.88)
    gov.start_new_trading_day(dt.date(2026, 9, 21), opening_balance=245_815.38)
    return gov


def trailing_signal(risk_dollars: float | None = 400.0) -> Signal:
    return Signal(
        action=SignalAction.ENTER_LONG,
        initial_stop_distance_points=20.0,
        trail_distance_points=30.0,
        risk_dollars=risk_dollars,
        reason="test trailing signal",
    )


def bracket_signal() -> Signal:
    return Signal(
        action=SignalAction.ENTER_LONG,
        stop_loss_price=19_980.0,
        take_profit_price=20_040.0,
        size=3,
        risk_dollars=400.0,
        reason="test bracket signal",
    )


def run_async(coro):
    return asyncio.run(coro)


def test_trailing_signal_places_correct_contract_count():
    broker = FakeBroker()
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    run_async(
        handle_entry_signal(
            trailing_signal(risk_dollars=400.0),
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    # risk_dollars=400, sized against trail_distance=30 points (not initial_stop_distance=20 --
    # fixed 2026-09-22, Round 69: contracts must be sized against the distance the stop is
    # actually placed at), MNQ point_value=$2 -> 400 // (30*2) = 6 contracts
    check(
        "trailing_signal_places_correct_contract_count",
        len(broker.calls) == 1 and broker.calls[0][0] == "place_market_entry_with_trailing_stop"
        and broker.calls[0][1]["size"] == 6 and broker.calls[0][1]["trail_price"] == 30.0,
        f"calls={broker.calls}",
    )


def test_dynamic_sizing_overrides_signal_risk_dollars():
    broker = FakeBroker()
    gov = make_governor(dynamic_sizing=DynamicSizingConfig(frac_below_start=0.04, risk_floor=25.0, risk_ceil=2_500.0))
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    # Real buffer here is 4,937.50; below starting_balance -> frac_below_start=0.04 -> ~197.50
    expected_risk = gov.compute_dynamic_risk()
    run_async(
        handle_entry_signal(
            trailing_signal(risk_dollars=400.0),  # the signal's own 400 should be IGNORED
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    expected_contracts = max(1, int(expected_risk // (30.0 * 2.0)))  # sized against trail_distance, not initial_stop_distance
    check(
        "dynamic_sizing_overrides_signal_risk_dollars",
        len(broker.calls) == 1 and broker.calls[0][1]["size"] == expected_contracts,
        f"expected_risk={expected_risk}, expected_contracts={expected_contracts}, calls={broker.calls}",
    )


def test_bracket_signal_uses_bracket_order_not_trailing():
    broker = FakeBroker()
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    run_async(
        handle_entry_signal(
            bracket_signal(),
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    check(
        "bracket_signal_uses_bracket_order_not_trailing",
        len(broker.calls) == 1 and broker.calls[0][0] == "place_bracket_order"
        and broker.calls[0][1]["stop_loss_price"] == 19_980.0
        and broker.calls[0][1]["take_profit_price"] == 20_040.0
        and broker.calls[0][1]["size"] == 3,
        f"calls={broker.calls}",
    )


def test_no_order_when_position_already_open():
    broker = FakeBroker(has_open_position=True)
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    run_async(
        handle_entry_signal(
            trailing_signal(),
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    check("no_order_when_position_already_open", len(broker.calls) == 0, f"calls={broker.calls}")


def test_no_order_when_risk_exceeds_cap():
    broker = FakeBroker()
    gov = make_governor()  # max_single_trade_risk=600.0
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    run_async(
        handle_entry_signal(
            trailing_signal(risk_dollars=5_000.0),  # well over the cap
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    check("no_order_when_risk_exceeds_cap", len(broker.calls) == 0, f"calls={broker.calls}")


def test_no_order_when_signal_has_neither_stop_shape():
    broker = FakeBroker()
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    bare_signal = Signal(action=SignalAction.ENTER_LONG, risk_dollars=400.0, reason="incomplete")
    run_async(
        handle_entry_signal(
            bare_signal,
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    check("no_order_when_signal_has_neither_stop_shape", len(broker.calls) == 0, f"calls={broker.calls}")


def test_flattens_immediately_if_trailing_stop_placement_fails():
    broker = FakeBroker(trail_success=False)  # entry "fills", but the protective stop fails
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="MNQ")
    run_async(
        handle_entry_signal(
            trailing_signal(),
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    call_names = [c[0] for c in broker.calls]
    check(
        "flattens_immediately_if_trailing_stop_placement_fails",
        call_names == ["place_market_entry_with_trailing_stop", "flatten_all"],
        f"calls={call_names}",
    )


def test_no_order_when_instrument_has_no_point_value():
    broker = FakeBroker()
    gov = make_governor()
    broker_config = BrokerConfig(mode="dry_run", instrument="ZZZ_UNKNOWN")
    run_async(
        handle_entry_signal(
            trailing_signal(),
            broker=broker, governor=gov, account_config=gov.config, broker_config=broker_config,
        )
    )
    check("no_order_when_instrument_has_no_point_value", len(broker.calls) == 0, f"calls={broker.calls}")


# --- stop re-anchored to the actual fill (2026-09-30) ---------------------------------

def reference_short_signal() -> Signal:
    """Today's real trade: short planned from the 09:30 open 30,701.50, stop 30,750.50 (49 pts)."""
    return Signal(
        action=SignalAction.ENTER_SHORT,
        stop_loss_price=30_750.50,
        take_profit_price=30_579.00,
        size=3,
        risk_dollars=300.0,
        entry_reference_price=30_701.50,
        reason="test POC short",
    )


def _run_bracket(signal, broker):
    import live_bot.main as M
    M.FILL_LOOKUP_DELAY_S = 0.0
    gov = make_governor()
    run_async(handle_entry_signal(signal, broker=broker, governor=gov, account_config=gov.config,
                                  broker_config=BrokerConfig(mode="dry_run", instrument="MNQ")))
    return [c for c in broker.calls if c[0] == "modify_stop_price"]


def test_stop_moves_with_an_adverse_fill():
    # filled 30,690.75 (10.75 pts worse for a short) -> stop 30,690.75 + 49 = 30,739.75, not 30,750.50
    mods = _run_bracket(reference_short_signal(), FakeBroker(fill_price=30_690.75))
    check("stop_moves_with_an_adverse_fill",
          len(mods) == 1 and mods[0][1] == {"order_id": 222, "stop_price": 30_739.75}, f"mods={mods}")


def test_stop_keeps_distance_on_a_favorable_fill():
    sig = Signal(action=SignalAction.ENTER_LONG, stop_loss_price=19_980.0, take_profit_price=20_040.0, size=3,
                 risk_dollars=400.0, entry_reference_price=20_000.0, reason="long")
    mods = _run_bracket(sig, FakeBroker(fill_price=19_998.50))
    check("stop_keeps_distance_on_a_favorable_fill",
          len(mods) == 1 and mods[0][1]["stop_price"] == 19_978.50, f"mods={mods}")


def test_no_modify_when_fill_equals_plan():
    mods = _run_bracket(reference_short_signal(), FakeBroker(fill_price=30_701.50))
    check("no_modify_when_fill_equals_plan", mods == [], f"mods={mods}")


def test_no_modify_without_reference_price():
    broker = FakeBroker(fill_price=19_990.0)
    mods = _run_bracket(bracket_signal(), broker)
    lookups = [c for c in broker.calls if c[0] == "get_entry_fill_price"]
    check("no_modify_without_reference_price", mods == [] and lookups == [], f"calls={broker.calls}")


def test_no_modify_when_fill_not_visible():
    broker = FakeBroker(fill_price=None)
    mods = _run_bracket(reference_short_signal(), broker)
    lookups = [c for c in broker.calls if c[0] == "get_entry_fill_price"]
    check("no_modify_when_fill_not_visible", mods == [] and len(lookups) == 5, f"calls={broker.calls}")


def test_rejected_modify_does_not_raise():
    ok = True
    try:
        _run_bracket(reference_short_signal(), FakeBroker(fill_price=30_690.75, modify_raises=True))
        _run_bracket(reference_short_signal(), FakeBroker(fill_price=30_690.75, modify_ok=False))
    except Exception as e:  # noqa: BLE001
        ok = False
    check("rejected_modify_does_not_raise", ok)


def main() -> int:
    for fn in [
        test_trailing_signal_places_correct_contract_count,
        test_dynamic_sizing_overrides_signal_risk_dollars,
        test_bracket_signal_uses_bracket_order_not_trailing,
        test_no_order_when_position_already_open,
        test_no_order_when_risk_exceeds_cap,
        test_no_order_when_signal_has_neither_stop_shape,
        test_flattens_immediately_if_trailing_stop_placement_fails,
        test_no_order_when_instrument_has_no_point_value,
        test_stop_moves_with_an_adverse_fill,
        test_stop_keeps_distance_on_a_favorable_fill,
        test_no_modify_when_fill_equals_plan,
        test_no_modify_without_reference_price,
        test_no_modify_when_fill_not_visible,
        test_rejected_modify_does_not_raise,
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
