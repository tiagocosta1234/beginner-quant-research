"""Blue Guardian 2 Step Standard replay of the pair (the trader: "run the replay for Blue Guardian rules"). Rules read on help.blueguardian.com/en/articles/14062291 (2026-10-06):
  targets 8% (phase 1) and 4% (phase 2); max daily loss 4% of the initial balance, reset at 5 pm EST (= MT5 broker server midnight, so the pair's server days are the right days), limit measured from the HIGHER of balance and equity at the reset;
  max overall loss 8% static (equity incl. floating >= $92,000); minimum 3 trading days per phase where a trading day = a day with >= 0.5% profit ($500); no time limit assumed (not read); phase 2 starts 2 weekdays after phase 1 (assumed).
Not modelled: live-stage rules (news +/-5 min on XAUUSD, Guardian Shield at 2% floating loss, 30-day inactivity) and the 85% split / withdrawal timing.
Series: the pair at c = 1 frozen lots (pair_stress.build), c x (0.2056 Stochastic lots, 0.0699 XAU5min lots).  Tests: constant c, and a ladder (top, 2/3 at -1.5%, 0.4 at -3%, 0.2 at -5% from the phase start); base and stress (+$30 / lot / side).
  python -m forex.ea_batch.bg_replay
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_batch import pair_stress as PS

INITIAL = PS.INITIAL
LIM_DAY, LIM_ALL, DAYTARGET = 4_000.0, 8_000.0, 500.0


def frames(U, E, R, start):
    n = len(E); end = np.r_[start[1:], n]
    before = np.where(start > 0, R[np.maximum(start - 1, 0)], 0.0)
    eqprev = np.where(start > 0, E[np.maximum(start - 1, 0)], 0.0)
    v = np.add.reduceat(np.diff(R, prepend=0.0), start)
    low = np.minimum.reduceat(E, start)
    m_bal = np.minimum(low - before, v)                     # worst equity vs the balance at the day's open (static 8% test)
    m_ref = np.minimum(low - np.maximum(before, eqprev), v - 0.0)   # worst equity vs the higher of balance / equity at the reset (daily 4% test)
    return v, m_bal, m_ref


def run_attempt(v, mb, mr, i0, rule, n_end):
    """(outcome, trading days used) for a test starting on day index i0; outcome in pass / breach / open."""
    def phase(i, target):
        bal, tds = INITIAL, 0
        while i < n_end:
            f = rule((bal - INITIAL) / INITIAL)
            x = v[i] * f
            if mr[i] * f < -LIM_DAY or bal + mb[i] * f <= INITIAL - LIM_ALL:
                return "breach", i
            bal += x
            if x >= DAYTARGET:
                tds += 1
            if bal >= target and tds >= 3:
                return "pass", i
            i += 1
        return "open", n_end
    o1, i = phase(i0, INITIAL * 1.08)
    if o1 != "pass":
        return o1, i - i0
    o2, j = phase(i + 3, INITIAL * 1.04)
    return o2, j - i0


def ladder(top):
    return lambda dd: top if dd >= -0.015 else (top * 2 / 3 if dd >= -0.03 else (top * 0.4 if dd >= -0.05 else top * 0.2))


def evaluate(tag, v, mb, mr, days):
    bd = pd.bdate_range(days.min(), PS.END)
    V, B, Rr = (pd.Series(a, index=days).reindex(bd).fillna(0.0).values for a in (v, mb, mr))
    return bd, V, B, Rr


def run(tag, bd, V, B, Rr, rule):
    N = len(bd); yr = bd.year.values
    full, win = [], []
    for i in range(0, N - 70):
        o, d = run_attempt(V, B, Rr, i, rule, N)
        o62, d62 = run_attempt(V, B, Rr, i, rule, min(N, i + 62))
        full.append((o, d, yr[i])); win.append((o62, yr[i]))
    f = lambda rows, k, sel=lambda y: True, c=0: np.mean([r[c] == k for r in rows if sel(r[-1])])
    dd = [r[1] for r in full if r[0] == "pass"]
    b = lambda y: y >= 2024; a = lambda y: y <= 2023
    print(f"{tag:<26} no deadline: pass {f(full, 'pass'):4.0%} breach {f(full, 'breach'):4.0%} (median {np.median(dd) if dd else float('nan'):4.0f} days) | 2022-23 starts {f(full, 'pass', a):4.0%}/{f(full, 'breach', a):4.0%} | "
          f"2024+ {f(full, 'pass', b):4.0%}/{f(full, 'breach', b):4.0%} || within 62 days: {f(win, 'pass'):4.0%}/{f(win, 'breach'):4.0%} (2024+ {f(win, 'pass', b):4.0%})", flush=True)


def main():
    for label, kw in (("BASE", {}), ("STRESS +$30/lot/side", dict(extra_cost=30))):
        U, E, R, start, days = PS.build({"77900": 1.0, "mkt_xau5min": 1.0}, **kw)
        v, mb, mr = frames(U, E, R, start)
        bd, V, B, Rr = evaluate(label, v, mb, mr, days)
        print(f"\n===== {label}: worst day vs reset-reference at c=1: {-mr.min():,.0f}; worst vs balance: {-mb.min():,.0f}; days {len(days)} =====", flush=True)
        for c in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5):
            run(f"constant {c:.1f} x", bd, V, B, Rr, lambda dd, c=c: c)
        for top in (0.8, 1.0, 1.5, 2.0):
            run(f"ladder from {top:.1f} x", bd, V, B, Rr, ladder(top))


if __name__ == "__main__":
    main()
