# PREREG GN6 - is the overnight-range breakout a mechanism? S&P 500, Dow and gold, each with an out-of-time check

Registered 2026-10-18 11:15 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep going until you find an ultra profitable breakout idea". The Nasdaq overnight-range breakout (GN3 O1) is the most
consistent breakout found so far (+0.1 R a trade in 2020-23 and 2025, beats random entries every period) but failed both its
DEV bar and its 2020-21 out-of-time bar (GN5) and is closed. If the overnight high / low is a level that index and gold traders
act on, the same rule should work on the other US index and on gold's pre-New-York range. These are new markets for the rule
(never computed); a pass here would be evidence of a mechanism, and each market stands on its own bars.

## Data
MT5 broker M1 bid/ask 2021-12..2026-10-16 (DEV / VAL / HOLD), zero-spread minutes repaired. Out-of-time: Databento CME 1-minute
continuous futures (trade prices, never used for this rule): ES for the S&P 500, GC for gold, 2020-01-02..2021-12-31; the
MT5 broker cost model of GN5 (bid = trade, ask = trade + the market's MT5 broker median spread 2022-26, measured in the dry run and fixed
there before any OOT P&L). Roll handling: ES uses the quarterly roll Mondays of GN5; GC days are excluded if their range or
trade window contains a 1-minute jump > 0.3% at the 00:00 UTC contract switch or two opposite-sign jumps > 0.3% within 60
minutes (the continuous series flipping between contracts; list fixed in the dry run). No DOW futures on the second PC: the
Dow trial has no OOT check and can only become a candidate through DEV, VAL and HOLD.

## Trials (3), engine of `gn5.o1` with each market's times
- **X1 S&P 500 (MT5 broker SP):** range 18:00 New York of the previous calendar day to 09:30; OCO stops 09:30-12:00; stop at the range
  midpoint; exit 15:55 New York.
- **X2 Dow (MT5 broker DOW):** the same times.
- **X3 gold (MT5 broker XAUUSD):** range 18:00 New York of the previous calendar day to 08:20 New York (COMEX open); OCO stops
  08:20-11:00; stop at the midpoint; exit 13:25 New York (before the COMEX close).
Control: 5 random-side entries a day in the same window, same stop distance and exit.

## Periods and acceptance
- DEV (MT5 broker 2022-24): n >= 150; mean net R > 0 with day-clustered t >= 2.13 (Bonferroni, 3 one-sided trials); information over
  the control > 0 with t >= 1.65; positive in >= 2 of 3 years.
- VAL (MT5 broker 2025): mean > 0, information > 0, t >= 1.65.
- OOT (futures 2020-21, X1 and X3): mean > 0 with t >= 1.65 and both years > 0. Required for X1 and X3.
- HOLD (MT5 broker 2026-01-01..2026-10-16, one look, only for trials passing everything above): mean > 0, t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25 days) at $250 / $500 a trade, each
  market alone and the three plus Nasdaq O1 as one book (descriptive, O1 is closed); usable only if P(pass) > P(breach) by 30
  Jun 2027.

## Dry run (no P&L except the engine port check)
Counts per trial and period, median range width in spreads, MT5 broker median spreads for the cost model, the GC exclusion list,
hand checks, and the port check on 2022-24 (futures vs MT5 broker for SP and gold: same side on most common days, R correlation
>= 0.6), as in GN5.

## Honest prior
About 10%. Earlier rounds found breakout information on SP / DOW smaller than on Nasdaq (DOW negative in the session-box tests),
and gold breakouts at the New York open (I31 / I33) were noise.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 + GN5 1 + GN6 3 = 21 of 40 variants in this research window.

## Amendments
(none yet)
