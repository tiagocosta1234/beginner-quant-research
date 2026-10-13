"""Read-only snapshot of the real MT5 broker account for the simulations: balance, equity, open positions, closed-deal P&L by server day, counted profit under the 2,000/day cap.
   python -m forex.ea_research.live_state          (attaches to the MT5 broker terminal read-only; never sends an order)"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

TERMINAL = os.getenv("mt5_MT5_TERMINAL") or r"C:\Program Files\MT5 MT5 Terminal\terminal64.exe"
START, CAP = 100_000.0, 2_000.0


def main():
    if not mt5.initialize(path=TERMINAL, timeout=30000):
        raise SystemExit(f"cannot attach: {mt5.last_error()}")
    try:
        a = mt5.account_info(); pos = mt5.positions_get() or []
        print(f"login {a.login} | balance {a.balance:,.2f} | equity {a.equity:,.2f} | floating {a.equity - a.balance:+,.2f} | margin free {a.margin_free:,.0f}")
        print(f"counted profit so far (balance - 100,000): {a.balance - START:+,.2f}; equity - 100,000: {a.equity - START:+,.2f}")
        for p in pos:
            print(f"  OPEN {p.symbol} {'BUY' if p.type == 0 else 'SELL'} {p.volume} @ {p.price_open} SL {p.sl} TP {p.tp} floating {p.profit:+,.2f} magic {p.magic} since {datetime.fromtimestamp(p.time, timezone.utc):%m-%d %H:%M} UTC")
        now = datetime.now(timezone.utc); deals = mt5.history_deals_get(now - timedelta(days=30), now + timedelta(days=1)) or []
        by_day = {}
        for d in deals:
            if d.type in (0, 1) and d.entry in (1, 2, 3):                       # closing deals
                day = (datetime.fromtimestamp(d.time, timezone.utc) + timedelta(hours=3)).date()   # MT5 broker server clock = UTC+3 (summer)
                by_day[day] = by_day.get(day, 0.0) + d.profit + d.swap + d.commission
        counted = 0.0
        for day in sorted(by_day):
            v = by_day[day]; c = min(v, CAP) if v > 0 else v; counted += c
            print(f"  {day}: closed P&L {v:+,.2f} | counted {c:+,.2f}" + ("  (cap would remove %.2f)" % (v - CAP) if v > CAP else ""))
        print(f"counted closed profit {counted:+,.2f}; target 8,000 -> remaining {8000 - counted:,.2f}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
