"""Best odds to pass inside ONE MONTH (the trader: "now best odds to pass in a month?").  The pair (Stochastic Daily Breakout + XAUUSD 5 minute), replayed on MT5 broker rules, test started on every weekday 2022-2026.
Month = 22 trading days. Measured per start: 2-Step phase 1 (+10%, >= 4 trading days, 5% daily, static 10% floor) passed within 22 days; the whole 2-Step (phase 1, two weekdays, phase 2 +5%) within 44 days; 1-Step (+10%, 3% daily,
10% trailing EOD floor, best day <= 50%) within 22 days. Not passed and not breached inside the window = "open" (a 2-Step has no deadline, so open costs nothing but time). Scales: constant multiples of the frozen lot (c = 1.5 is
the loaded 0.31 / 0.10) and the LB-shaped ladder (1 : 2/3 : 0.4 : 0.2 at -2 / -4 / -6% from the phase start) from a top scale. Also with a worse broker (+$30 / lot / side) and Prague-midnight days.
  python -m mt5broker.ea_batch.pass_month
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import pair_stress as PS

INITIAL = PS.INITIAL
MONTH = 22


def two_step(pnl, mm, ent, days, rule, base):
    """(phase-1 outcome, whole outcome) in the given window."""
    def phase(i, target):
        bal, tds = INITIAL, set()
        while i < len(days):
            d = days[i]; f = rule((bal - INITIAL) / INITIAL) / base
            v = pnl.get(d, 0.0) * f; m = min(mm.get(d, 0.0) * f, v)
            if d in ent:
                tds.add(d)
            if m < -5_000 or bal + m < 90_000:
                return "breach", i + 1
            bal += v
            if bal > target and len(tds) >= 4:
                return "pass", i + 1
            i += 1
        return "open", i
    o1, i = phase(0, 110_000.0)
    if o1 != "pass":
        return o1, o1
    o2, _ = phase(i + 2, 105_000.0)
    return "pass", o2


def one_step(pnl, mm, days, rule, base):
    bal = hwm = INITIAL; pos = best = 0.0
    for d in days:
        f = rule((bal - INITIAL) / INITIAL) / base
        v = pnl.get(d, 0.0) * f; m = min(mm.get(d, 0.0) * f, v)
        hwm = max(hwm, bal)
        if m < -3_000 or bal + m <= hwm - 10_000:
            return "breach"
        bal += v
        if v > 0:
            pos += v; best = max(best, v)
        if bal > 110_000 and best <= 0.5 * pos:
            return "pass"
    return "open"


def run(tag, v, m, days, rule, base):
    bd = pd.bdate_range(days.min(), PS.END)
    V = pd.Series(v, index=days).reindex(bd).fillna(0.0); M = pd.Series(m, index=days).reindex(bd).fillna(0.0)
    pnl, mm = V.to_dict(), M.to_dict(); ent = set(days[np.abs(v) > 0])
    r = []
    for i in range(0, len(bd) - 2 * MONTH - 5):
        p1, _ = two_step(pnl, mm, ent, list(bd[i:i + MONTH]), rule, base)
        _, full = two_step(pnl, mm, ent, list(bd[i:i + 2 * MONTH]), rule, base)
        r.append((p1, full, one_step(pnl, mm, list(bd[i:i + MONTH]), rule, base), bd[i].year))
    def f(col, k, sel=lambda y: True):
        x = [t[col] == k for t in r if sel(t[3])]
        return np.mean(x) if x else float("nan")
    a, b = (lambda y: True), (lambda y: y >= 2024)
    print(f"{tag:<34} 2-Step ph1<=22d: pass {f(0, 'pass'):4.0%} breach {f(0, 'breach'):4.0%} (2024+ starts {f(0, 'pass', b):4.0%}/{f(0, 'breach', b):4.0%}) | "
          f"whole 2-Step<=44d: {f(1, 'pass'):4.0%} / {f(1, 'breach'):4.0%} (2024+ {f(1, 'pass', b):4.0%}) | 1-Step<=22d: {f(2, 'pass'):4.0%} / {f(2, 'breach'):4.0%} (2024+ {f(2, 'pass', b):4.0%})", flush=True)


def main():
    for label, kw in (("BASE", {}), ("STRESS (+$30 lot/side, Prague day)", dict(extra_cost=30, shift_h=1))):
        print(f"\n===== {label} =====", flush=True)
        b = PS.build({"77900": 1.0, "mkt_xau5min": 1.0}, **kw)
        v, m, _ = PS.day_frames(*b, None)
        for c in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
            run(f"constant {c:.1f} x", v, m, b[4], lambda dd, c=c: c, 1.0)
        for top in (1.5, 2.0, 3.0, 4.0):
            rule = lambda dd, top=top: top if dd >= -0.02 else (top * 2 / 3 if dd >= -0.04 else (top * 0.4 if dd >= -0.06 else top * 0.2))
            run(f"ladder from {top:.1f} x", v, m, b[4], rule, 1.0)


if __name__ == "__main__":
    main()
