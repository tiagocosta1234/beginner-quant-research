# PREREG GN1 - gold and Nasdaq breakouts, long-only in the 200-day uptrend, against a drift control

Registered 2026-10-18 10:49 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep working on getting profitable in gold and nasdaq breakout". What is already known for these two markets (MT5 broker bars):
NSDQ New York box breakout about +0.06 R in 2022-24 and ~0 in 2025, shorts negative every year (REELS_16_17, BRK_CONFIRM);
gold London breakout about 0, longs ahead of shorts (MANUAL_TRADES_REVIEW, BRK_CONFIRM by class); both markets drifted up in
2023-26, and the D2 book (long above the 200-day average) is the one validated edge (`D2_MT5RULE_RESULT.md`). Earlier trend filters
used 5- or 20-day trends; long-only breakouts gated by the 200-day regime, and held into the drift, have not been tested.
The trap is that a random long in an uptrend earns the drift too, so every trial is judged against a drift control.

## Markets, data, costs
XAUUSD and NSDQ, MT5 broker M1 bid/ask 2021-12..2026-10-16 (`forex/data_mt5`), zero-spread minutes repaired (`brk_patterns.load`).
Regime: the 16:00 New York mid close (NSDQ) / the 17:00 London mid close (XAUUSD) of the previous trading day above the
SMA200 of those closes (200 completed days required, so trades start about 2022-10).

## Trials (5)
- **G1 gold London long:** box 08:00-08:30 London (bid high / low); in the regime, a buy stop at the box high from 08:30 to
  11:00 (fills when the ASK reaches it); stop = box low; exit 17:00 London.
- **G2 gold London long, held overnight:** as G1, exit at the next trading day's 17:00 London (stop still live overnight).
- **G3 gold New York long:** box 09:30-10:00 New York; buy stop at the box high 10:00-12:00 NY; stop = box low; exit 16:00 NY.
- **N1 Nasdaq New York long:** NSDQ box 09:30-10:00 NY; buy stop 10:00-12:00 NY; stop = box low; exit 15:55 NY.
- **N2 Nasdaq New York long, held overnight:** as N1, exit at the next trading day's 15:55 NY.
Rules common to all: one trade per market per day; no fill in the server 23:00-00:59 window; on the fill minute only the stop
counts; gap rule = the open if beyond the stop; R = net P&L / (entry - stop).

## Drift control (the yardstick that decides)
For every trading day in the regime (whether or not the breakout fired): a long at a uniformly random minute of the same entry
window, at the ask, with the same stop DISTANCE as that day's box (entry - box width) and the same exit; 5 draws per day, seed
fixed. "Breakout information" = mean R of the breakout trades - mean R of the control trades on the same days (paired by day).

## Periods
DEV 2022-10..2024-12 (selection), VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for trials passing DEV and VAL; 2026
was seen for the two-sided, all-regime versions of these boxes, not for these long-only regime subsets).

## Acceptance
- DEV: n >= 150; mean net R > 0 with day-clustered t >= 2.33 (Bonferroni, 5 one-sided trials at 5%); breakout information > 0
  with paired t >= 2.0; positive in at least 2 of the 3 DEV calendar years (2022 is a partial year).
- VAL: mean > 0 and information > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): a full passer is replayed from 95,472 (MT5 broker rules, `usdjpy_account_env.account` pattern)
  at $250 / $500 a trade and as a gold + Nasdaq pair; usable only if P(pass) > P(breach) by 30 Jun 2027. The account view of
  every trial is printed regardless.

## Dry run (no P&L)
Counts per trial and period, share of days in the regime, truncation test (cut the data at random times: entries before the
cut day identical), hand check of 2 trades per trial.

## Honest prior
About 15%. The long-only regime gate will make the trades positive (the drift); whether a BREAKOUT beats a random long on the
same days is the open question, and earlier rounds found breakout information of +0.03-0.05 R, about one spread.

## Amendments
(none yet)
