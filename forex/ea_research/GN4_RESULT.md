# GN4 result - market-profile value-area rules on Nasdaq and gold: 0 of 4 pass (2026-10-18 11:09 local, local clock, second PC)

Pre-registration `PREREG_GN4.md` (7e754a98), engine `gn4.py` and dry run `GN4_DRYRUN.txt` (2ab1ee6d, before any P&L; profile
hand check: POC bin = the fullest bin, value areas hold 70-73% of the session's minutes), output `GN4_OUTPUT.txt`. Yesterday's
value area from minute mids (NSDQ 09:30-16:00, gold 08:20-13:30 New York); control = random-side entries in the same window
with the same stop distance (and target, for the 80% rule).

| trial | DEV n | DEV mean R (t) | control | information (t) | DEV years 22/23/24 | VAL 2025 n, mean R (t) | verdict |
|---|---|---|---|---|---|---|---|
| V1 NSDQ acceptance breakout (stop at POC) | 201 | +0.031 (+0.31) | -0.008 | +0.039 (+0.34) | +0.21/-0.05/-0.07 | 54, -0.107 (-0.66) | FAIL |
| V2 gold acceptance breakout | 194 | -0.081 (-0.82) | -0.072 | -0.008 (-0.08) | -0.08/+0.02/-0.19 | 44, +0.160 (+0.53) | FAIL |
| V3 NSDQ 80% rule | 117 | -0.056 (-0.94) | -0.022 | -0.033 (-0.40) | -0.01/-0.06/-0.10 | 44, -0.045 (-0.55) | FAIL |
| V4 gold 80% rule | 123 | -0.052 (-0.84) | -0.053 | +0.001 (+0.01) | -0.12/-0.03/-0.01 | 45, -0.196 (-2.08) | FAIL |

The 2026 hold-out stays sealed.

## What it says
- **Value areas are another way of drawing levels, and they carry no more information than the others.** The acceptance
  breakout beats random entries by +0.04 R on Nasdaq (2022 only) and -0.01 R on gold.
- **The "80% rule" reaches the other edge of the value area on 50% (Nasdaq) and 45% (gold) of trades, not 80%**, and loses
  after the stop and costs in every DEV year on both markets.
- NSDQ opens inside yesterday's value area on only ~30% of days; the overnight session usually moves it out.

## Account environment (2022-25, from 95,472, MT5 broker rules)
No trial passes in more than 0.3% of paths by 30 Jun 2027 (breach 0-62%). Not usable.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 = 17 of 40 variants in this research window.
