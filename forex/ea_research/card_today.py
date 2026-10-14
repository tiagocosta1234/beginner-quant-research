"""READ-ONLY daily helper for the October sizing card (forex/mt5_SIZING_CARD_OCT.md): attaches to the MT5 broker terminal, never sends an order, never changes a setting.
   python -m forex.ea_research.card_today            -> counted profit, the day number, today's multiplier, lots, and the day's rules
Table = the capped DP (lambda 0.3) saved by dp_oct14_capped.py (D:/finance/tmp/dp_oct14_capped_lam0.3.npy)."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import numpy as np
import MetaTrader5 as mt5

TERMINAL = os.getenv("mt5_MT5_TERMINAL") or r"C:\Program Files\MT5 MT5 Terminal\terminal64.exe"
START, CAP, TARGET = 100_000.0, 2_000.0, 8_000.0
MULTS = (1.2, 1.8, 2.5)
LOTS = {1.2: (0.14, 0.05), 1.8: (0.22, 0.07), 2.5: (0.30, 0.10)}
DAYS = [date(2026, 10, d) for d in (15, 16, 19, 20, 21, 22, 23, 26, 27, 28, 29, 30)]
GRID0, STEP = -8000.0, 100.0


def main():
    pol = np.load("D:/finance/tmp/dp_oct14_capped_lam0.3.npy")
    if not mt5.initialize(path=TERMINAL, timeout=30000):
        raise SystemExit(f"cannot attach: {mt5.last_error()}")
    try:
        a = mt5.account_info()
        now = datetime.now(timezone.utc)
        deals = mt5.history_deals_get(now - timedelta(days=45), now + timedelta(days=1)) or []
        by_day = {}
        for d in deals:
            if d.type in (0, 1) and d.entry in (1, 2, 3):
                day = (datetime.fromtimestamp(d.time, timezone.utc) + timedelta(hours=3)).date()
                by_day[day] = by_day.get(day, 0.0) + d.profit + d.swap + d.commission
        counted = sum(min(v, CAP) if v > 0 else v for v in by_day.values())
        today = date.today()
        nxt = [i for i, d in enumerate(DAYS) if d >= today]
        print(f"login {a.login} | balance {a.balance:,.2f} | equity {a.equity:,.2f} | counted profit {counted:+,.2f} (target {TARGET:,.0f}, remaining {TARGET - counted:,.2f})")
        for p in mt5.positions_get() or []:
            print(f"  OPEN {p.symbol} {'BUY' if p.type == 0 else 'SELL'} {p.volume} @ {p.price_open} SL {p.sl} floating {p.profit:+,.2f}")
        if counted >= 8100:
            print("PASS LOCK RANGE: counted profit >= 8,100 -> the guard closes everything; do not trade further today.")
            return
        if a.equity < 97_500:
            print("TRIGGER: equity below 97,500 -> x1.2 until 22 Dec (ManualSDB 0.14 / XAU5 0.05). Do not chase.")
        if not nxt:
            print("The card window (15-30 Oct) is over: use x1.2 (0.14 / 0.05) unless you decided otherwise.")
            return
        j = nxt[0]
        ci = int(np.clip(round((counted - GRID0) / STEP), 0, pol.shape[1] - 1))
        m = MULTS[int(pol[j][ci])]
        d = DAYS[j]
        if d.weekday() == 2 and d.day == 28:
            m = min(m, 1.8)
            fomc = " (FOMC evening: capped at x1.8)"
        else:
            fomc = ""
        sdb, xau = LOTS[m]
        print(f"\nCARD DAY {j + 1}/12 ({d:%a %d %b}): counted {counted:+,.0f} -> trade x{m}{fomc}: ManualSDB {sdb:.2f} lot, XAU5 Entry_Amount {xau:.2f}, ManualDip 500 unchanged.")
        if d.weekday() == 4:
            print("FRIDAY: flatten the XAU5 positions before the weekend while above x1.2.")
        if m > 1.2 and j >= 9:
            print("late window: check the remaining distance before the day starts; the card never goes above x2.5.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
