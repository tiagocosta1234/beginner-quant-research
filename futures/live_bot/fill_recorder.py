"""
FillRecorder: feed this bot's own closed trades into the RiskGovernor.

Why this exists (2026-09-30): RiskGovernor.record_fill() was never called, so the
governor's daily_realized_pnl / current_balance never moved. Once the live balance
became readable (broker_client._on_account_update fix, same day), every closed trade
would have looked like untracked account activity to reconcile_balance() and halted
the bot -- and the daily loss limit could not see realized losses at all.

How it works, each poll cycle, BEFORE main.py reconciles the balance:
  * A trade is "in flight" from the moment this bot places an entry (note_entry) or
    sees its own instrument's position open, until the position is flat again.
  * Once flat, the realized result is the change in the broker's live balance since
    the governor last recorded it. That delta is exact (it includes every fee the
    broker charged). It is only accepted as OUR fill if the broker's own trade
    history for this contract since the entry explains it: closing fills'
    profitAndLoss minus fees, within a tolerance (the broker's per-fill `fees`
    field was seen to understate the real charge by ~$0.50/contract on the first
    live trade: -$360.66 reported vs -$362.16 of balance change).
  * If the balance moved but our own trades do NOT explain it (e.g. a manual trade
    on the same account), nothing is recorded, and reconcile_balance() will flag the
    mismatch as before -- the safety check is kept, not bypassed.
  * While a closed trade is "settling" (flat, but the balance event or the closing
    fill has not arrived yet), `settling` is True and main.py skips reconciliation
    for at most max_wait_cycles polls, so a normal reporting lag is not mistaken
    for a breach.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Optional


class FillRecorder:
    def __init__(self, base_tolerance: float = 5.0, tolerance_per_contract: float = 2.0,
                 max_wait_cycles: int = 10, lookback: dt.timedelta = dt.timedelta(minutes=2),
                 logger: Optional[logging.Logger] = None) -> None:
        self.base_tolerance = base_tolerance
        self.tolerance_per_contract = tolerance_per_contract
        self.max_wait_cycles = max_wait_cycles
        self.lookback = lookback
        self.log = logger or logging.getLogger("FillRecorder")
        self.pending = False
        self.since: dt.datetime | None = None
        self.wait = 0
        self.flat_now = True

    @property
    def settling(self) -> bool:
        """Flat, but this bot's last trade has not been recorded yet."""
        return self.pending and self.flat_now

    def note_entry(self, now: dt.datetime) -> None:
        """Call right after this bot places an entry order."""
        if not self.pending:
            self.pending, self.since, self.wait = True, now, 0

    def _clear(self) -> None:
        self.pending, self.since, self.wait = False, None, 0

    async def update(self, broker: Any, governor: Any, now: dt.datetime) -> float | None:
        """Returns the realized P&L recorded this cycle, or None."""
        if await broker.has_open_position():
            self.flat_now = False
            if not self.pending:
                self.pending, self.since, self.wait = True, now, 0
            return None
        self.flat_now = True
        if not self.pending:
            return None

        live = broker.get_account_balance()
        trades = await broker.get_trades_since(self.since - self.lookback)
        closing = [t for t in trades if t.get("pnl") is not None]
        expected = sum(t["pnl"] for t in closing) - sum(t.get("fees") or 0.0 for t in trades)
        contracts = sum(abs(t.get("size") or 0) for t in closing)
        delta = None if live is None else live - governor.current_balance

        if delta is None or not closing or abs(delta) < 0.005:
            # balance event, closing fill, or both not reported yet -- or no order ever filled
            self.wait += 1
            if self.wait > self.max_wait_cycles:
                if closing or (delta is not None and abs(delta) >= 0.005):
                    self.log.error(
                        "FillRecorder: gave up after %d cycles (balance delta=%s, our closing fills=%d, "
                        "expected=$%.2f) -- leaving it to balance reconciliation.",
                        self.wait, None if delta is None else round(delta, 2), len(closing), expected)
                else:
                    self.log.info("FillRecorder: no fill after the noted entry; nothing to record.")
                self._clear()
            return None

        tolerance = self.base_tolerance + self.tolerance_per_contract * contracts
        if abs(delta - expected) <= tolerance:
            governor.record_fill(delta)
            self.log.info(
                "FillRecorder: recorded closed trade(s) realized=$%.2f (broker trades explain $%.2f over %d "
                "contracts, within $%.2f). Governor balance now $%.2f.",
                delta, expected, contracts, tolerance, governor.current_balance)
            self._clear()
            return delta

        self.log.error(
            "FillRecorder: balance moved $%.2f but this bot's own trades explain $%.2f (tolerance $%.2f) -- "
            "NOT recorded; balance reconciliation will treat it as untracked activity.",
            delta, expected, tolerance)
        self._clear()
        return None


def trading_date(now_ct: dt.datetime) -> dt.date:
    """Broker's trading day starts at 5:00 PM CT: from then on it is the next date."""
    return (now_ct + dt.timedelta(hours=7)).date()
