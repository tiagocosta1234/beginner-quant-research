# PREREG GN7 - the 5-minute opening-range breakout on high relative-volume days (real exchange volume), Nasdaq and gold

Registered 2026-10-18 11:18 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep going until you find an ultra profitable breakout idea". Every breakout round so far used price only (MT5 broker has no real
volume). The second PC holds Databento CME futures with exchange volume (NQ, GC, 2019-10..2026-09). The best-known published
breakout claim, Zarattini & Aziz's 5-minute opening-range breakout ("Can day trading really be profitable?", QQQ; and the
"stocks in play" follow-up), puts the edge on days when the opening volume is unusually high. The plain 5-minute ORB was tested
on MT5 broker (BRK_CLASSICS: about zero on MT5 broker indices, NSDQ +0.135 R); the high relative-volume subset was never computed.

## Data and costs
Databento CME 1-minute continuous futures, trade prices and volume: NQ (Nasdaq) and GC (gold), New York dates 2020-01-02 ..
2026-09-25. MT5 broker cost model of GN5 / GN6: bid = trade, ask = trade + MT5 broker median spread (NSDQ 1.67 points, XAUUSD 0.190 USD).
Roll handling: NQ roll Mondays excluded (GN5); GC days containing a contract switch or flip minute excluded (GN6 rule).
Live note: MT5 broker's MT5 offers tick volume, not exchange volume; a pass here would need a tick-volume replication on the main PC
before any use.

## Rule (Zarattini & Aziz, applied unchanged) and the volume condition
- First 5-minute candle of the session: NQ 09:30-09:35 New York, GC 08:20-08:25 New York (COMEX open). Close > open -> long,
  close < open -> short, equal -> no trade; market entry at the open of the next minute (09:35 / 08:25); stop at the candle's
  low (long) / high (short); target 10 x the risk; exit at 15:55 (NQ) / 13:25 (GC) New York.
- RVOL5 = volume of the first 5 minutes / mean volume of the same 5 minutes over the previous 14 trading days (only 2020+
  data; the first 14 days of 2020 are warm-up). **In-play day: RVOL5 >= 1.5.**

## Trials (2)
- **Q1 Nasdaq:** the rule on NQ in-play days.
- **Q2 gold:** the rule on GC in-play days.
Comparisons (reported, the first one decides with the mean): (a) a random-direction control on the same in-play days
(5 draws: random side at the same entry minute, same stop distance, target and exit); (b) the same rule on the other days.

## Periods
DEV 2020-2023 (futures), VAL 2024-2025 (futures), HOLD 2026-01-01..2026-09-25 (futures; also the MT5 broker hold-out months, so it is
opened only for a trial passing DEV and VAL).

## Acceptance
- DEV: n >= 80; mean net R > 0 with day-clustered t >= 1.96 (Bonferroni, 2 one-sided trials); information over the
  random-direction control > 0 with t >= 1.65; mean above the same rule on the other days; positive in >= 3 of the 4 years.
- VAL: mean > 0 with t >= 1.65, information > 0. HOLD: mean > 0 with t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2020-25 days) at $250 / $500 a trade; usable only
  if P(pass) > P(breach) by 30 Jun 2027.

## Dry run (no P&L)
Share of in-play days per year, counts per period, median risk in spreads, hand check of 2 trades with their RVOL5.

## Honest prior
About 7%. Exchange volume is new information to this research, but MT5 broker tick-volume filters (busy opening box, volume surge at
the breakout, BRK2 A_RV) did not help, and tick volume tracks exchange volume closely.

## Running count
GN1-GN6 21 + GN7 2 = 23 of 40 variants in this research window.

## Amendments
1. (2026-10-18 ~11:19 (committed 11:20:02; first written as 11:21, a guess), after the dry run, before any P&L) RVOL5 >= 1.5 selects only 3-6% of NQ days (39 DEV trades, below the
   n >= 80 bar); GC 13-20%. The in-play condition becomes RANK-based, as in the "stocks in play" paper (top names by relative
   volume): **in-play = RVOL5 at or above the 80th percentile of all earlier RVOL5 values of the same market since 2020
   (expanding window, at least 60 earlier values)**, i.e. each market's own top ~20% of days, known before the entry. Applied
   to both trials; nothing else changes.
