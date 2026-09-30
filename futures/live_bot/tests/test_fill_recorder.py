"""Plain-Python tests for fill_recorder.py (no pytest dependency).

Run with: python live_bot/tests/test_fill_recorder.py

Uses the numbers of the first real Practice trade (2026-09-30): balance
150,000.00 -> 149,637.84 (-362.16); broker fills: entry fees 1.08, exit
profitAndLoss -358.50 fees 1.08 (-360.66 explained). A real RiskGovernor is used,
so record_fill / reconcile_balance behave exactly as in main.py.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.fill_recorder import FillRecorder, trading_date  # noqa: E402
from live_bot.risk_governor import AccountConfig, RiskGovernor  # noqa: E402

CT = AccountConfig().timezone
RESULTS: list[tuple[str, bool, str]] = []
T0 = dt.datetime(2026, 9, 30, 8, 30, tzinfo=CT)
ENTRY = dict(pnl=None, fees=1.08, size=3, order_id=1)
EXIT = dict(pnl=-358.50, fees=1.08, size=3, order_id=2)


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


class FakeBroker:
    def __init__(self):
        self.position = False
        self.balance = 150_000.0
        self.trades: list[dict] = []

    async def has_open_position(self):
        return self.position

    def get_account_balance(self):
        return self.balance

    async def get_trades_since(self, since):
        return list(self.trades)


def gov():
    g = RiskGovernor(AccountConfig())
    g.start_new_trading_day(dt.date(2026, 9, 30), opening_balance=150_000.0)
    return g


def step(rec, b, g, minute):
    return asyncio.run(rec.update(b, g, T0 + dt.timedelta(minutes=minute)))


def main() -> int:
    # 1. normal trade: entry noted, position open, then flat with balance and fills reported
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    rec.note_entry(T0)
    b.position = True
    step(rec, b, g, 1)
    b.position, b.balance, b.trades = False, 149_637.84, [ENTRY, EXIT]
    got = step(rec, b, g, 2)
    check("real trade recorded at the exact balance change", got is not None and abs(got + 362.16) < 1e-6, repr(got))
    check("governor balance now equals the live balance", abs(g.current_balance - 149_637.84) < 1e-6, str(g.current_balance))
    check("daily realized P&L and loss streak updated", abs(g.daily_realized_pnl + 362.16) < 1e-6 and g.consecutive_losses == 1,
          f"{g.daily_realized_pnl} {g.consecutive_losses}")
    check("reconciliation passes afterwards", g.reconcile_balance(b.balance) and not rec.settling)

    # 2. balance event arrives late: settling (reconcile skipped) then recorded
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    rec.note_entry(T0)
    b.trades = [ENTRY, EXIT]
    first = step(rec, b, g, 1)
    check("late balance: nothing recorded yet, settling", first is None and rec.settling)
    b.balance = 149_637.84
    got = step(rec, b, g, 2)
    check("late balance: recorded once it arrives", got is not None and not rec.settling and g.reconcile_balance(b.balance))

    # 3. balance moved more than this bot's trades explain (e.g. a manual trade)
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    rec.note_entry(T0)
    b.balance, b.trades = 149_000.0, [ENTRY, EXIT]
    got = step(rec, b, g, 1)
    check("unexplained balance change is NOT recorded", got is None and abs(g.current_balance - 150_000.0) < 1e-6)
    check("...and reconciliation still flags it", not rec.settling and not g.reconcile_balance(b.balance))

    # 4. entry noted but no order ever filled: clears quietly after the wait, records nothing
    b, g, rec = FakeBroker(), gov(), FillRecorder(max_wait_cycles=3)
    rec.note_entry(T0)
    for m in range(1, 6):
        step(rec, b, g, m)
    check("no fill: nothing recorded, no longer settling", not rec.pending and abs(g.current_balance - 150_000.0) < 1e-6)

    # 5. trade opened and closed between two polls (never seen open) is still recorded
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    rec.note_entry(T0)
    b.balance, b.trades = 149_637.84, [ENTRY, EXIT]
    got = step(rec, b, g, 1)
    check("trade closed between polls is recorded via note_entry", got is not None)

    # 6. no entry noted, no position: never touches the governor (manual-trade safety intact)
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    b.balance, b.trades = 149_637.84, [ENTRY, EXIT]
    got = step(rec, b, g, 1)
    check("without our own entry or position nothing is recorded", got is None and not rec.settling)

    # 7. a winning trade and two trades in one flat-to-flat window
    b, g, rec = FakeBroker(), gov(), FillRecorder()
    rec.note_entry(T0)
    b.balance = 150_000.0 + 733.0 - 3.66 + 250.0 - 3.66
    b.trades = [ENTRY, dict(pnl=735.0, fees=1.08, size=3), ENTRY, dict(pnl=252.0, fees=1.08, size=3)]
    got = step(rec, b, g, 1)
    check("two trades in one window recorded together", got is not None and abs(g.current_balance - b.balance) < 1e-6, repr(got))

    # 8. Broker trading date rolls at 5 PM CT
    check("16:59 CT is still the same trading date", trading_date(dt.datetime(2026, 9, 30, 16, 59, tzinfo=CT)) == dt.date(2026, 9, 30))
    check("17:00 CT is the next trading date", trading_date(dt.datetime(2026, 9, 30, 17, 0, tzinfo=CT)) == dt.date(2026, 10, 1))

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
