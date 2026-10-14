# PREREG DAY2K-I - index intraday momentum: does the first half hour predict the last half hour? (written 2026-10-14, the trader: "test the index intraday momentum")

Documented effect (Gao, Han, Li, Zhou 2018, "Market intraday momentum", SPY and other ETFs 1993-2013): the return of the first half hour of the cash session (including the overnight gap) and of the second-to-last half hour predict the sign of the last half hour. Tested here on the MT5 broker CFDs, with costs, out of sample.

## Definitions (local exchange time, converted to the server clock per day with the real DST rules)
US indices SP, NSDQ, DOW: New York time, cash session 09:30-16:00. DAX: Berlin time, session 09:00-17:30. Target window = last half hour: entry at the open of the bar starting at 15:30 NY (17:00 Berlin) on the executable side (long at ask, short at bid), exit at the open of the bar starting at 16:00 NY (17:30 Berlin) on the exit side; net return in basis points of the mid. Predictors (mid prices, all known at 15:30 / 17:00): P1 = close of the 09:59 bar - open of the 09:30 bar (DAX 09:29 close - 09:00 open); P2 = close of the 09:59 bar - close of the previous session's 15:59 bar (overnight + first half hour); P3 = close of the 15:29 bar - open of the 15:00 bar (DAX 16:59 close - 16:30 open). Trade = long if the predictor > 0, short if < 0 (continuation; the fade is its mirror and is reported, not a trial). One trade per instrument-day.

## Trials (15) and acceptance
4 instruments x 3 predictors = 12, plus the three predictors pooled over SP, NSDQ, DOW (a day's mean over the three) = 15. Bonferroni for 15, one-sided 5%: DEV (2021-12..2024) mean NET return > 0 with block-t (5-day blocks) >= 2.70 AND above the always-long yardstick of the same window; VAL 2025: mean net > 0 with block-t >= 1.65 and >= 200 days. HOLD 2026 sealed, opened once for a survivor.
Reported for every cell: gross (mid-to-mid) and net mean bp, hit rate, the Spearman correlation of the predictor with the target return, spread cost in bp, and the always-long yardstick. If a cell survives, the 1:1 view (stop = target = 1 x the 20-day mean of the 30-minute range) and the MT5 broker view at risk 2,000 are added.

## Gates
Positive control (oracle sign of the target) > +2 bp; placebo worlds: predictor permuted across days (seeds 171-173) must give 0 survivors; truncation: random days' predictors recomputed from bars before 15:30 / 17:00 are identical.

## Honest prior
In the literature the effect is about 1-2 bp per trade gross on SPY; the CFD round trip costs about 1-3 bp (SP spread about 1 point on 6,000), and the effect has weakened since 2013. P(survivor) under 10%. Even a real effect cannot give 2,000 risk a high win rate: a 30-minute window on a 1:1 trade is a near-coin flip around a small edge.

## Dry-run record (2026-10-14, before any cell result)
Days with all bars: SP/NSDQ/DOW 1,015 of 1,066, DAX 1,037. Round-trip spread cost: SP 1.42 bp, NSDQ 1.52, DOW 1.40, DAX 1.31; mean absolute last-half-hour move 12.7-21.7 bp. DST handling verified (09:30 NY = 15:30 server on 2023-03-13, when US DST had started and EU DST had not, and 16:30 server on 2023-03-28). Hand check of one SP day matches the bars. Truncation 40/40. No trial or threshold changed.
