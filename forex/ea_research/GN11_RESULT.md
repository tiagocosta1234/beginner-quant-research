# GN11 result - BRK-WEEK's two leads fail out of time on 2020-21 futures (0 of 2)

Run 2026-10-18 14:51 local (local clock, second PC PC-2). Pre-registration `PREREG_GN11.md` (commit 8f72522b, amendment 1 before any
P&L), engine `gn11.py` (BRK-WEEK's `trade` / `exits` unchanged), dry run `GN11_DRYRUN.txt`, output `GN11_OUTPUT.txt`.
Net R a trade, hold to the Friday / month-end close with the registered stop (E-close), MT5 broker cost model on CME futures.

| trial | 2020-21 futures | random control | breakout - control | 2020 / 2021 | MT5 broker 2022-24 / 2025 / 2026 (BRK-WEEK) | verdict |
|---|---|---|---|---|---|---|
| M1 metals previous-week breakout (GC + SI) | +0.044 R, n 143, NW t +0.01 | +0.003 | +0.041 | +0.125 / -0.020 | +0.131 / +0.361 / +0.023 | FAIL |
| M2 index month-opening-range breakout (NQ + ES, roll months skipped) | +0.033 R, n 32, NW t +0.14 | +0.182 | -0.149 | +0.237 / -0.170 | +0.175 / +0.011 / +0.292 | FAIL |

## What it shows
- **Metals:** gold's previous-week breakout lost (-0.03 R) while random gold entries in the same windows earned +0.16 (the 2020
  boom); silver's +0.11 sits next to a -0.15 control. There is no breakout information out of time, as in 2022-26 (+0.04 R over
  random). Lead 2 is closed.
- **Indices:** with the quarterly roll months removed only 32 trades remain; the breakout earned less than random entries
  (+0.03 vs +0.18). Weak test, wrong sign. Lead 1 is closed.
- **Data finding (amendment 1):** in 2020-21 the Databento continuous ES series switched contract at 00:00 UTC on the Friday of the
  week BEFORE the expiry week (-7 .. -10 points), and NQ's switch is not at any 00:00 UTC minute; the expiry-week Monday rule
  (`gn5.roll_mondays`) holds only from mid-2022. Earlier rounds that skipped roll Mondays in 2020-21 are re-checked in
  `ROLL_2020_CHECK.md`.

## Running count
GN1-GN11: 33 of 40 variants of this research window used, 0 passes.
