# PREREG GN3 - gold at the Shanghai open and Nasdaq through its overnight range: two session breakouts not yet tested

Registered 2026-10-18 11:02 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep going until you find an ultra profitable breakout idea" (gold and Nasdaq). GN1 / GN2 and the earlier breakout rounds
(`BREAKOUT_KNOWLEDGE.md`) covered the London and New York boxes, prior-period levels, patterns, filters and holds. Two session
structures with a flow story have not been tested on these markets:
- **Gold at the Shanghai Gold Exchange open (09:00 Beijing).** Chinese physical and investment demand was a main driver of the
  2024-26 gold rally and trades in Asian hours; the only Asian test so far was the 01:00-07:00 local range broken at the London
  open (BRK2 A_asia, 38 markets), not a break inside the Asian session.
- **Nasdaq breaking its overnight (Globex) range after the cash open.** The overnight high / low is a level every index-futures
  day trader watches; BRK50 tested yesterday's high / low, the London-hours range and the pre-data range, not the full
  18:00-09:30 New York overnight range broken during the cash session.

## Data and costs
MT5 broker M1 bid/ask 2021-12..2026-10-16 (`forex/data_mt5`), zero-spread minutes repaired (`brk_patterns.load`); long entries fill at the
ask, shorts at the bid, exits on the opposite side; no fill in the server 23:00-00:59 window; on the fill minute only the stop
counts (`brk_patterns.walk`). R = net P&L / (entry - stop distance).

## Trials (4)
- **A1 gold Shanghai breakout, both sides:** box 09:00-09:30 Asia/Shanghai (bid high / low); one-cancels-other stop orders
  09:30-11:30 Shanghai (buy at the box high when the ASK reaches it, sell at the box low when the BID reaches it; both in the
  same minute = no trade); stop at the other side of the box; exit 15:30 Shanghai (SGE day-session close, before London).
- **A2 gold Shanghai breakout, long only:** as A1, buy side only.
- **O1 Nasdaq overnight-range breakout, both sides:** range = bid high / low of NSDQ from 18:00 New York of the previous
  calendar day (Sunday for Monday) to 09:30 New York; OCO stop orders 09:30-12:00 New York; stop at the range midpoint; exit
  15:55 New York.
- **O2 Nasdaq overnight-range breakout, long only:** as O1, buy side only.
Days: Monday-Friday; box / range must have >= 80% of its minutes present; one trade per day per trial.

## Control
On every eligible day (filled or not), 5 random entries at uniformly random minutes of the same window with the same stop
distance and exit: random longs for A2 / O2; random side (50/50) for A1 / O1. Information = trial mean R - control mean R
(unconditional over eligible days; SE treats the two as independent).

## Periods
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for trials passing DEV and VAL; these session
structures were never computed on any period).

## Acceptance
- DEV: n >= 60; mean net R > 0 with day-clustered t >= 2.24 (Bonferroni, 4 one-sided trials at 5%); information > 0 with
  t >= 1.65; positive in >= 2 of the 3 DEV years.
- VAL: mean > 0, information > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment: every trial replayed from 95,472 (MT5 broker rules, `usdjpy_account_env.account`, 5-day block bootstrap of
  2022-25) at $250 and $500 a trade; usable only if P(pass) > P(breach) by 30 Jun 2027.

## Dry run (no P&L)
Counts per trial and period, median box / range width in spreads, truncation test, hand check of 2 trades per trial with the
server and local times.

## Honest prior
About 5-8%. Asian gold boxes are narrow (likely < 25 spreads on many days, where breakouts lose their cost); the Nasdaq
overnight range is wide (cost small), but breakout information on indices was about one spread in every earlier round.

## Running count
GN1 5 + GN2 4 + GN3 4 = 13 of 40 variants in this research window.

## Amendments
(none yet)
