# PREREG GN12 - the post-release breakout on scheduled US event days (CPI, NFP, FOMC; Treasury auctions), Nasdaq and gold (4 trials)

Registered 2026-10-18 14:56 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "push it and keep testing the remaining 17". GN1-GN11 used 33 of the 40 variants of this research window.

## Why (information the chart does not contain: the event calendar)
- Scheduled releases are the moments when new information reaches gold and the Nasdaq; a trend that starts with the release
  could carry the rest of the session. Tested before: the release-surprise direction 5 / 15 / 60 minutes after the release
  (EVENTS 0/18, TICK_EVENTS 0/4: absorbed within about 10 seconds), session breakouts filtered by news days (round 15), the
  breakout of the range BEFORE the 08:30 data (BRK50 I32). Never tested: the breakout of the first 15 minutes AFTER the release,
  held to the session close, and anything on Treasury auction days.
- Calendars on the second PC: `forex/ea_research/EVENT_CALENDAR_2022_2026.csv` (CPI, NFP, FOMC), `futures/data/events/
  treasury_coupon_auctions.csv` (5-, 7-, 10-, 20-, 30-year auctions and reopenings; results at 13:00 New York).

## Rule (stop orders at the box edges, as GN8's FOLLOW; engine `brk_patterns.walk`)
| event | box (New York) | order window | exit Nasdaq / gold |
|---|---|---|---|
| CPI, NFP (08:30 release) | 08:30-08:44 | 08:45-10:59 | 15:55 / 13:25 |
| FOMC (14:00 statement, 14:30 press conference) | 14:00-14:44 | 14:45-15:29 | 15:55 / 15:55 |
| Treasury auction (13:00 result) | 13:00-13:14 | 13:15-14:29 | 15:55 / 15:55 |
Buy stop at the box high (ask), sell stop at the box low (bid); first fill wins; both in one minute = no trade; stop at the other
side of the box; no target; exit at the stated minute. R = |entry - stop|. A day with both kinds of event is used in both trials.
The box needs at least 12 of its 15 minutes; the order window at least 80% of its minutes.

## Trials (4)
- **K1** NSDQ on CPI / NFP / FOMC days. **K2** XAUUSD on CPI / NFP / FOMC days.
- **K3** NSDQ on Treasury auction days. **K4** XAUUSD on Treasury auction days.

## Controls
- Random entries on the same event days (5 a day: random minute in the order window, random side, stop W, same exit); information
  = trial mean - control mean (`gn2.info`).
- The same rule at the same clock times on the other business days (the event effect).

## Periods (MT5 broker bid / ask; no out-of-time source: CPI / NFP dates for 2020-21 are not on the second PC)
DEV 2022-01-03 .. 2024-12-31; VAL 2025; HOLD 2026-01-02 .. 2026-10-16 (opened once, only for a trial passing DEV and VAL).

## Acceptance (all required)
- DEV: n >= 80; mean net R > 0 with day-clustered t >= 2.24 (Bonferroni, 4 one-sided trials); information > 0 with t >= 1.65;
  mean above the same rule on the other days; positive in at least 2 of the 3 years.
- VAL: mean > 0 with t >= 1.65 and information > 0. HOLD: mean > 0 with t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25 days) at $250 / $500 a trade; usable only
  if P(pass) > P(breach) by 30 Jun 2027. Live note: MT5 broker widens spreads 10-15x at the release minute; every entry here is at least
  15 minutes later.

## Dry run (no P&L)
Event counts by year and type, trades by period, median box in spreads, truncation test (data cut 2023-06-30 12:00 New York),
hand check of one trade per trial.

## Honest prior
About 4% each. Releases are absorbed in seconds and news-day filters did not help; the one new element is holding the
post-release breakout to the close. Auctions move bonds far more than gold or the Nasdaq.

## Running count
GN1-GN11 33 + GN12 4 = 37 of 40 variants in this research window.
