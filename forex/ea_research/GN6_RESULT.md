# GN6 result - the overnight-range breakout on S&P 500, Dow and gold: 0 of 3; not a mechanism (2026-10-18 11:18 local, local clock, second PC)

Pre-registration `PREREG_GN6.md` (86afd0ff), engine `gn6.py` and dry run `GN6_DRYRUN.txt` (c2887915, before any P&L; port checks
futures vs MT5 broker on 2022-24: same side on 99% of days, R correlation 0.94 for SP and 0.87 for gold), output `GN6_OUTPUT.txt`.

| trial | DEV 2022-24 n, mean R (t) | info vs random (t) | years 22/23/24 | longs / shorts | VAL 2025 | OOT futures 2020-21 | verdict |
|---|---|---|---|---|---|---|---|
| X1 S&P 500 (MT5 broker SP; ES) | 675, +0.033 (+0.53) | +0.047 (+0.68) | +0.09/+0.03/-0.02 | +0.097 / -0.038 | +0.056 (+0.50) | +0.064 (t +0.97), +0.061 / +0.066 | FAIL |
| X2 Dow (MT5 broker DOW; no futures) | 708, -0.097 (-1.76) | -0.114 (-1.84) | -0.01/-0.17/-0.10 | -0.045 / -0.161 | +0.079 (+0.71) | - | FAIL |
| X3 gold (MT5 broker XAUUSD; GC), range to 08:20 NY | 618, +0.069 (+1.10) | +0.054 (+0.82) | +0.14/+0.06/+0.02 | +0.157 / -0.036 | +0.093 (+1.04) | +0.000 (t 0.00), +0.044 / -0.036 | FAIL |

The 2026 hold-out stays sealed for all three.

## What it says
- **The Nasdaq overnight-range result does not generalise.** The S&P 500 earns a third of Nasdaq's figure, the Dow loses, and
  gold earns +0.07 R on MT5 broker but exactly zero on 2020-21 futures. In every market the longs carry the result and the shorts lose:
  what the overnight range adds is mostly the uptrend, not a level traders act on.
- So the Nasdaq O1 figure (+0.1 R) is most likely a Nasdaq-specific trend effect of 2020-23 plus noise, consistent with its
  failed DEV and OOT bars (GN3, GN5).

## Account environment (2022-25, from 95,472, MT5 broker rules)
Best single row X3 gold at $500 a trade: 0.1% / 27% by 30 Nov, 0.4% / 37% by 22 Dec, 12.2% / 63% by 30 Jun 2027. The four
overnight-range markets as one book at $150 a trade (3,551 trades, +0.036 R): 10.8% / 46% by 30 Jun 2027. Breach exceeds pass
everywhere. Not usable.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 + GN5 1 + GN6 3 = 21 of 40 variants in this research window.
