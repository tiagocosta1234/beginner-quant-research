# PREREG GN4 - market-profile value-area breakouts on Nasdaq and gold (acceptance breakout and the "80% rule")

Registered 2026-10-18 11:06 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep going until you find an ultra profitable breakout idea" (gold and Nasdaq). Every level tested so far was a price
extreme (box, session, day, week, month high / low), a pivot formula or a TWAP band. Market-profile traders use a different
level: yesterday's VALUE AREA, the price band where the market spent 70% of its time. Two classic rules (Dalton, "Mind over
Markets"): (1) when price opens inside yesterday's value and is then ACCEPTED outside it (a 30-minute period closes beyond the
edge), it trends away; (2) the "80% rule": when price opens outside yesterday's value and is accepted back inside (two
consecutive 30-minute periods close inside), it crosses to the other side of the value area about 80% of the time.
Never tested in this repo.

## Profile construction (all known before today's session)
Yesterday's session minutes (mid close of each M1 bar): NSDQ 09:30-16:00 New York, gold 08:20-13:30 New York (COMEX day
session, the standard gold profile). 100 equal price bins across that session's range; POC = the bin with the most minutes
(ties: the one nearest the session mid); value area = grow from the POC, each step adding the neighbour bin with more minutes,
until >= 70% of the minutes are inside; VAH / VAL = the outer edges of the value area. Today's 30-minute periods start at the
session open (NSDQ 09:30, gold 08:20 New York); a period "closes" at the mid close of its last minute.

## Trials (4)
- **V1 NSDQ acceptance breakout:** today's open (first minute's mid at 09:30) inside [VAL, VAH]; the first period, among those
  ending by 12:00 New York, that closes above VAH (below VAL) -> buy at the ask (sell at the bid) at the next minute's open;
  stop at yesterday's POC; exit 15:55 New York.
- **V2 gold acceptance breakout:** the same with gold's session (periods ending by 11:20 New York), exit 13:25 New York.
- **V3 NSDQ 80% rule:** today's open above VAH (below VAL); the first time two consecutive periods (ending by 13:00 New York)
  both close inside [VAL, VAH] -> sell (buy) at the next minute's open; target = the opposite value-area edge (VAL for a sell,
  VAH for a buy); stop = today's session high (low) so far, at least 0.25 x the value-area width beyond the entry; exit at the
  target, the stop, or 15:55 New York.
- **V4 gold 80% rule:** the same with gold's session (periods ending by 12:20 New York), exit 13:25 New York.
One trade per day per trial; no fill in the server 23:00-00:59 window; entries and exits on the right side of the spread;
on the entry minute only the stop counts (`brk_patterns.walk`). R = net P&L / |entry - stop|.

## Control
On every day where the trial's opening condition holds (fired or not): 5 random entries at uniformly random minutes of the
trial's signal window, random side, with the trial-day's stop distance (V1 / V2: |entry - POC| at that minute, floored at
0.25 x value-area width; V3 / V4: 0.25 x value-area width) and, for V3 / V4, a target at the opposite value-area edge when it
lies on the profitable side (otherwise no target). Information = trial mean R - control mean R (unconditional).

## Periods
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for trials passing DEV and VAL).

## Acceptance
- DEV: n >= 60; mean net R > 0 with day-clustered t >= 2.24 (Bonferroni, 4 one-sided trials); information > 0 with
  t >= 1.65; positive in >= 2 of the 3 DEV years. For V3 / V4 also report the share of trades reaching the target (the rule
  claims ~80%).
- VAL: mean > 0, information > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25) at $250 / $500 a trade; usable only
  if P(pass) > P(breach) by 30 Jun 2027.

## Dry run (no P&L)
Counts, share of days opening inside / outside value, median value-area width in spreads, truncation test, hand check of one
profile (POC / VAH / VAL by hand from the minute histogram) and 2 trades per trial.

## Honest prior
About 5%. Value areas are another way of drawing levels; every level type tested so far gave breakout information of about
one spread. The 80% rule's "80%" is a claim about touching the other edge, not about profit after the stop and costs.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 = 17 of 40 variants in this research window.

## Amendments
(none yet)
