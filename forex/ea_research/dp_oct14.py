"""Dynamic sizing from the LIVE state of 2026-10-14.
   python -m forex.ea_research.dp_oct14
Same model as dp_sizing.py (DP over days left x counted profit; empirical guarded days of the pair at x1.2/1.8/2.5/3.5/5.0; block-bootstrap evaluation on the 12-month MT5 broker pool and the 2022-26 pool),
restarted from counted profit -374.30 (balance 99,625.70) with 12 trading days left (Thu 15 Oct .. Fri 30 Oct) and x1.2 afterwards to 22 Dec (49 trading days). Floating +217 on the open XAU5 short is not counted."""
from __future__ import annotations

import numpy as np

from forex.ea_research import dp_sizing as D

D.H1, D.H2, D.C0 = 12, 49, -374.30
MU = D.MULTS
pools = {"MT5": D.load("MT5"), "FT": D.load("FT")}


def ev(policy):
    out = {}
    for nm, pool in (("12M", "MT5"), ("2022-26", "FT")):
        r = D.simulate(pools, pool, policy, H=D.H2)
        out[nm] = r
    return out


def line(tag, o):
    m = [(o["12M"][i] + o["2022-26"][i]) / 2 * 100 for i in range(4)]
    return (f"{tag:34s} 30 Oct pass {m[0]:5.1f}% (12M {o['12M'][0]*100:4.1f} / 22-26 {o['2022-26'][0]*100:4.1f}) breach {m[1]:4.1f}% | 22 Dec pass {m[2]:5.1f}% breach {m[3]:4.1f}")


print("mean day USD by multiplier (12M pool):", [round(float(s["V"].mean())) for s in pools["MT5"]], "| 2022-26 pool:", [round(float(s["V"].mean())) for s in pools["FT"]])
print("\nCONSTANT sizes (state: counted -374, 12 days left)")
for a, m in enumerate(MU):
    print(line(f"x{m}", ev(a)))


def table(mid, low, hi_lo, hi_hi, final_push=True):
    """Operable table: x`mid` while counted profit in [low, hi_lo); x1.2 below `low` and in [hi_lo, hi_hi) until the last 3 days (then `mid` again); beyond hi_hi x1.2."""
    pol = np.zeros((D.H1, len(D.GRID)), int)
    for j in range(D.H1):
        for ci, c in enumerate(D.GRID):
            if c < low:
                a = 0
            elif c < hi_lo:
                a = mid
            elif c < hi_hi:
                a = mid if (final_push and j >= D.H1 - 3) else 0
            else:
                a = 0
            pol[j][ci] = a
    return pol


print("\nOPERABLE TABLES")
for tag, pol in (("T1: x1.8 mid, x1.2 <-1000, >6000", table(1, -1000.0, 6000.0, 7000.0)),
                 ("T2: x2.5 mid, x1.2 <-1000, >6000", table(2, -1000.0, 6000.0, 7000.0)),
                 ("T3: x1.8 mid, x1.2 <-1500, >5500", table(1, -1500.0, 5500.0, 7000.0)),
                 ("T4: x1.8 everywhere >= -1000", table(1, -1000.0, 99999.0, 99999.0))):
    print(line(tag, ev(pol)))
print("\nDP OPTIMUM (designed on the 50/50 mix, evaluated on both pools)")
sp = [pools["MT5"], pools["FT"]]
saved = {}
for lam in (0.3, 1.0, 3.0):
    pol, W = D.dp(sp, (0.5, 0.5), lam)
    saved[lam] = pol
    print(line(f"DP lambda {lam}", ev(pol)))
pol = saved[1.0]
print("\nDP lambda 1.0 policy: multiplier by day (rows) and counted profit (columns)")
cols = (-2000, -1000, 0, 1000, 2000, 3000, 4000, 5000, 6000, 7000)
print("            " + " ".join(f"{c:>7d}" for c in cols))
for j in range(D.H1):
    print(f"day {j + 1:2d}/{D.H1}   " + " ".join(f"{('x' + str(MU[pol[j][int(round((c - D.GRID[0]) / D.STEP))]])):>7s}" for c in cols))
