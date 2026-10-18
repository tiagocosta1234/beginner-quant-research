# PREREG GN11 - out-of-time check of BRK-WEEK's two leads on 2020-21 CME futures: metals previous-week breakout, index month-opening-range breakout (2 trials)

Registered 2026-10-18 14:46 local (local clock, second PC PC-2), before any 2020-21 number of these rules was computed.
the trader: "push it and keep testing the remaining 17". GN1-GN10 used 31 of the 40 variants of this research window.

## Why
BRK-WEEK (breakout day round 4, 2026-10-15, MT5 broker 2022-26) left two leads that were never checked out of time
(BREAKOUT_KNOWLEDGE section 2; `BRK_WEEK_RESULT.md`):
- **Lead 2, metals previous-week breakout** (gold, silver): +0.131 R (t 1.79) / +0.361 (t 2.67) / +0.023 (2022-24 / 2025 / 2026),
  breakout minus random entry +0.04 / +0.15 / +0.08 R (random entries also earn: the gold bull drift).
- **Lead 1, index month-opening-range breakout:** +0.175 R (t 1.70, 204 trades) / +0.011 / +0.292, positive every year 2022-26.
The 2020-21 CME futures on the second PC (Databento GC, SI, NQ, ES 1-minute) were never used for either. This round only re-runs the
registered rules on those years: no new parameter.

## Rules (BRK-WEEK unchanged; engine `brk_week.trade` / `brk_exits.exits`, server clock, sessions 01:00-23:00 server)
- **W2 previous-week range:** last week's (Mon-Fri) bid high / low; stop orders Monday 01:05 -> Thursday 22:55 server; first fill
  wins (both in one minute = no trade); stop at last week's midpoint; exit at the open of Friday's 21:55 minute (E-close, X4).
- **W4 month opening range:** high / low of the first 3 trading days of the month; stop orders from day 4 01:05 to the 15th 22:55;
  stop at the other side of the range; exit at the open of the last trading day's 21:55 minute (held over weekends).
- R = |entry - stop|, skipped if R < 2 spreads. Control (as BRK-WEEK): one random minute in the order window, random side, the
  same R and exit.

## Trials (2), data and costs
- **M1** W2 on gold and silver futures (GC, SI) pooled: weeks from 2020-01-13 (the first whose previous week is in 2020) to
  2021-12-31.
- **M2** W4 on Nasdaq and S&P futures (NQ, ES) pooled: months January 2020 .. December 2021.
- MT5 broker cost model of GN5-GN10: bid = trade price, ask = trade + the MT5 broker median spread of the market over 2022-26 in the 01:00-23:00
  server session (XAUUSD for GC, XAGUSD for SI, NSDQ for NQ, SP for ES).
- Rolls (the files hold one continuous series without contract names): NQ / ES are back-adjusted (difference) at their known
  switch minute, 00:00 UTC on the Monday of the quarterly expiry week (`gn5.roll_mondays`); GC / SI weeks with a detected switch or
  flip minute between the order window start and the exit are skipped (`gn6.bad_minutes`). 2020-21 GC / SI roll gaps below the
  0.3% detector are a few tenths of a percent at most, about 0.01 R on a weekly trade.

## Acceptance (each trial on its own; one-sided out-of-time test)
- Mean net R (E-close) > 0 with Newey-West t (by entry week, lag 1, as BRK-WEEK) >= 1.65; the breakout beats its random control by
  >= +0.05 R; both years positive. n is what the calendar gives (about 150-190 metal weeks, about 40-45 index months; M2 is weak:
  power about 25% even if the lead is real).
- Account environment (if a trial passes): replay of its MT5 broker 2022-25 trades from 95,472 (MT5 broker rules) at $250 / $500 a trade.
- A pass makes the lead a candidate for the 2026 hold-out look in a later round; it does not make it tradeable.

## Dry run (no P&L)
Counts by year and market, detected NQ / ES roll gaps (size), skipped GC / SI weeks, MT5 broker median spreads, truncation test (data cut
2021-06-30), hand check of one trade of each cell.

## Honest prior
M1 about 10% (2020-21 had a gold boom and bust, both breakout-friendly, but the 2022-26 information over random entries was small).
M2 about 10% with low power.

## Running count
GN1-GN10 31 + GN11 2 = 33 of 40 variants in this research window.

## Amendments
1. (2026-10-18 14:50, after the dry run, before any P&L) The dry run shows the 2020-21 NQ / ES contract switch is NOT at 00:00 UTC on the
   expiry-week Monday (the jumps there are 0.0-1.0 point, ordinary minute moves). ES switched at 00:00 UTC on the FRIDAY of the
   week before the expiry week (-7.3 .. -10.5 points on 2020-09-11, 12-11, 2021-03-12, 06-11, 09-10, 12-10, 2022-03-11; the
   expiry-week Monday only from mid-2022); NQ's 2020-21 switch is not visible at any 00:00 UTC minute (Nasdaq-only jumps of -10 ..
   -18 points appear at some Sunday re-opens before the expiry week). Back-adjusting at the registered minute would fix nothing,
   so **M2 instead skips every month with a quarterly roll (March, June, September, December) for NQ and ES, with no
   back-adjustment**. This leaves about 32 trades: M2 stays a weak test. M1 (GC / SI weeks with a detected switch or flip skipped)
   is unchanged.
