# PREREG GN13 - breakouts in the direction of the 10-year Treasury trend, Nasdaq, S&P and gold (3 trials; the last 3 variants)

Registered 2026-10-18 14:59 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "push it and keep testing the remaining 17". GN1-GN12 used 37 of the 40 variants of this research window.

## Why (information outside the MT5 broker charts: MT5 broker lists no bonds)
- Interest rates drive long-duration equities (the Nasdaq most) and gold (real yields). If a session breakout carries more when it
  goes the way the bond market is already moving, the bond trend is the filter.
- Tested before: alignment with MT5 broker partner markets (BRK50 I39-I42, a confirming / lagging partner market), dollar and real-yield
  filters on the ManualSDB gold EA (daily, not breakouts). Never: the bond trend on intraday breakouts.
- Data: Yahoo 10-year note futures daily closes (`futures/data/daily/ZN=F_yahoo_daily.csv`, to 2026-09-21). **Bond
  trend of day d: the ZN close of the last trading day before d above the mean of the 20 closes up to that day = bonds up
  (yields falling); below = bonds down (yields rising).** Known before the session.

## Rule (one-sided stop order in the bond-aligned direction; engine `brk_patterns.walk`)
- Indices (NSDQ, SP): box = bid high / low of 09:30-09:59 New York (>= 24 minutes); bonds-up day: buy stop at the box high, bonds-
  down day: sell stop at the box low; active 10:00-11:59 (>= 90 minutes); stop at the other side of the box; no target; exit 15:55.
- Gold (XAUUSD): box 08:20-08:49 New York (COMEX open; >= 24 minutes); bonds-up day: buy stop (gold rises when yields fall),
  bonds-down day: sell stop; active 08:50-10:59 (>= 100 minutes); stop at the other side; exit 13:25.
- R = |entry - stop|.

## Trials (3)
**B1** NSDQ, **B2** SP, **B3** XAUUSD.

## Controls
- Random entries in the ALIGNED direction on the same days (5 a day: random minute in the order window, stop W, same exit):
  information = trial - control isolates the breakout's timing from the bond-aligned drift (`gn2.info`).
- The MISALIGNED one-sided order on the same days (the contrast: aligned should beat misaligned).

## Periods
- DEV MT5 broker 2022-01-03 .. 2024-12-31; VAL MT5 broker 2025.
- OOT: CME futures 2020-01-02 .. 2021-12-31 (NQ, ES, GC; MT5 broker cost model of GN5-GN12); NQ / ES roll Mondays skipped and, for ES, the
  2020-21 switch Fridays (`ROLL_2020_CHECK.md`); GC days with a switch or flip minute between box start and exit skipped.
- HOLD: MT5 broker 2026-01-02 .. 2026-09-22; opened once, only for a trial passing DEV, VAL and OOT.

## Acceptance (all required)
- DEV: n >= 80; mean net R > 0 with day-clustered t >= 2.13 (Bonferroni, 3 one-sided trials); information > 0 with t >= 1.65;
  aligned mean above the misaligned mean; positive in at least 2 of the 3 years.
- VAL: mean > 0 with t >= 1.65 and information > 0. OOT: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25 days) at $250 / $500 a trade; usable only
  if P(pass) > P(breach) by 30 Jun 2027. Live note: the trader can read the ZN close by hand; an EA would need a daily file.

## Dry run (no P&L)
Share of bonds-up days by year, trades by period, port check 2022-24 (MT5 broker vs futures: same day-side agreement >= 80%, R correlation
>= 0.6), truncation test (data and ZN cut on 2023-06-30), hand check of one trade per trial.

## Honest prior
About 4% each. The bond trend mostly moves with the equity trend (in 2022 both fell), so "aligned" is close to "with the trend",
which helped only indices before (BRK-VOLREG V5); gold rose with rising yields from 2023 on, so its link to real yields broke.

## Running count
GN1-GN12 37 + GN13 3 = 40 of 40 variants: this research window closes after GN13.
