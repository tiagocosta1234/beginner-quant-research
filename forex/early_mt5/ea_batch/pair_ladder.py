"""De-risk ladders and constant scales for the pair on MT5 2-Step (the trader: "this is for a 2 step account").

A daily guard does nothing for 2-Step breaches (they come from the slow slide to the static -10% floor, not from one bad day: see pair_stress.py), so the lever tested here is the SIZE after a drawdown. The ladders are
fixed before looking at results. Base series: the loadable lots 0.31 / 0.10 (= 1.5 x frozen); a ladder multiplies the NEXT day's P&L and worst equity by (lots at that step) / (lots at 1.5 x). The step is chosen from the balance
at the end of the previous day relative to the phase's start balance (dd = (balance - start) / $100K):
  L0   constant 1.5 x
  LA   dd >= -3%: 1.5 x | -3% .. -6%: 1.0 x | < -6%: 0.5 x
  LB   dd >= -2%: 1.5 x | -2% .. -4%: 1.0 x | -4% .. -6%: 0.6 x | < -6%: 0.3 x
  LC   LA, and once the phase is +6% or more ahead: 1.0 x (protect the finish)
  K    constant scales 0.4 / 0.5 / 0.6 / 0.8 / 1.0 (no ladder), for comparison
Rules: MT5 2-Step, +10% then +5%, 5% daily loss, static 10% floor, >= 4 trading days per phase, Phase 2 two weekdays after Phase 1, no deadline; a test from every weekday 2022-2026.
The real lots for the steps: Stochastic 0.31 / 0.21 / 0.10 (1.5 / 1.0 / 0.5 x), XAU5min 0.10 / 0.07 / 0.03.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import pair_stress as PS

INITIAL = PS.INITIAL
LADDERS = {
    "L0 constant 1.5": lambda dd: 1.5,
    "LA 1.5 / 1.0 / 0.5 at -3% / -6%": lambda dd: 1.5 if dd >= -0.03 else (1.0 if dd >= -0.06 else 0.5),
    "LB 1.5 / 1.0 / 0.6 / 0.3 at -2 / -4 / -6%": lambda dd: 1.5 if dd >= -0.02 else (1.0 if dd >= -0.04 else (0.6 if dd >= -0.06 else 0.3)),
    "LC LA + 1.0 once +6% ahead": lambda dd: 1.0 if dd >= 0.06 else (1.5 if dd >= -0.03 else (1.0 if dd >= -0.06 else 0.5)),
}


def attempt2(pnl, mm, ent, days, rule, base):
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
        return o1, None
    o2, j = phase(i + 2, 105_000.0)
    return o2, (j + i + 2 - (i + 2)) if o2 == "pass" else None


def run(tag, v, m, days, rule, base, step=2):
    bd = pd.bdate_range(days.min(), PS.END)
    V = pd.Series(v, index=days).reindex(bd).fillna(0.0); M = pd.Series(m, index=days).reindex(bd).fillna(0.0)
    pnl, mm = V.to_dict(), M.to_dict(); ent = set(days[np.abs(v) > 0])
    res = []
    for i in range(0, len(bd) - 60, step):
        res.append(attempt2(pnl, mm, ent, list(bd[i:]), rule, base) + (bd[i].year,))
    f = lambda k, sel=lambda y: True: np.mean([r[0] == k for r in res if sel(r[2])])
    dd = [r[1] for r in res if r[0] == "pass"]
    print(f"{tag:<46} all: pass {f('pass'):4.0%} breach {f('breach'):4.0%} (median {np.median(dd):4.0f} trading days) | 2022-23 starts: {f('pass', lambda y: y <= 2023):4.0%} / {f('breach', lambda y: y <= 2023):4.0%} | 2024+ starts: {f('pass', lambda y: y >= 2024):4.0%} / {f('breach', lambda y: y >= 2024):4.0%}", flush=True)


def main():
    Wr = {"77900": 0.31 / PS.LOT["77900"], "mkt_xau5min": 0.10 / PS.LOT["mkt_xau5min"]}
    b = PS.build(Wr)
    v, m, _ = PS.day_frames(*b, None)
    print("series at the loadable lots (0.31 / 0.10); 'pass / breach' per start group", flush=True)
    for name, rule in LADDERS.items():
        run(name, v, m, b[4], rule, 1.5)
    for c in (0.4, 0.5, 0.6, 0.8, 1.0):
        run(f"K constant {c}", v, m, b[4], lambda dd, c=c: c, 1.5)
    # ladders under stress (+$30/lot/side, Prague day)
    bs = PS.build(Wr, extra_cost=30, shift_h=1)
    vs, ms, _ = PS.day_frames(*bs, None)
    print("-- with +$30/lot/side and Prague-midnight days --", flush=True)
    for name in ("L0 constant 1.5", "LA 1.5 / 1.0 / 0.5 at -3% / -6%", "LB 1.5 / 1.0 / 0.6 / 0.3 at -2 / -4 / -6%", "LC LA + 1.0 once +6% ahead"):
        run(name, vs, ms, bs[4], LADDERS[name], 1.5)
    run("K constant 0.5", vs, ms, bs[4], lambda dd: 0.5, 1.5)


if __name__ == "__main__":
    main()
