# PREREG_SETTLE_TOM: settlement-window momentum (gold, silver) and turn-of-the-month (equity index)

Written Mon 26 Oct 2026 local (local clock), BEFORE any result of this test was computed. the trader: "TEST MORE LOCK IN".
Multiplicity note: this is the 9th test family run today; any pass goes to a pre-registered forward test on Practice, never straight to money.

## P1 (PRIMARY): gold settlement momentum
Lead (post-hoc, from PREREG_PUBLISHED_EFFECTS): GC's prior close -> 15:30 ET sign picked the side of 15:30-16:00 with P 0.0003 but a gross move too small to pay costs.
Hypothesis: the same hedging-demand momentum sits in the last 30 minutes before GC's own settlement (13:30 ET), when volume is high.
Rule: every weekday, at 13:00 ET take the side of sign(GC at 13:00 today - GC at 13:30 the prior trading day), exit 13:30 ET, no stop. Cost 0.32 points; $10 per point per micro.

## P2 (secondary): silver settlement momentum
Same with SI: settlement 13:25 ET; at 12:55 ET take the side of sign(12:55 today - 13:25 prior day), exit 13:25 ET. Cost 0.0112; $1000 per point per micro (SIL).

## P3 (PRIMARY): turn-of-the-month, equity index
Days = the last trading day of each month and the first 3 trading days of the next. Long ES and NQ from 09:30 ET to 15:55 ET on those days.
Costs ES 0.74, NQ 1.1. Baseline = the same trade on all other days.

## Data
Databento 1m 2019-06..2026-09-25, America/New_York, price = open of the first bar at or after the time (max 5 min late), ATR = prior 14-day ATR on NY-date bars.

## Bars (alpha 0.01 each)
- P1: mean net > 0 AND sign-flip P <= 0.01 (20,000 flips to the mirror, cost on both) AND mean net > 0 in at least 5 of 7 years 2020-2026.
- P3: TOM mean net > 0 AND TOM minus other-days mean > 0 with a month-block permutation P <= 0.01 (shuffle which months' TOM days are "TOM" vs a same-size random set of other days, 20,000) AND TOM mean net > 0 in at least 5 of 7 years.
Reported: per market, $ per micro per trade, trades per year, win rate, by year.
