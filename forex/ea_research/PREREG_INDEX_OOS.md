# Pre-registration INDEX-OOS (breakout day, round 7; written 2026-10-15 11:53 local (commit time), before any code or result on these markets)
Rounds 1-6 on the 46 MT5 broker all pointed to stock indices (SP, NSDQ, DOW, DAX, NIKKEI, ASX). Every MT5 broker period (2022-24, 2025, 2026) has now been looked at for these index variants, so they are confirmed or rejected on markets NOT used today: the three stock indices in the MT5 broker M1 bid/ask files that MT5 broker does not list and that were never part of any breakout test here:
**UK100.cash** (FTSE 100, London 08:00-16:30), **FRA40.cash** (CAC 40, Paris 09:00-17:30), **US2000.cash** (Russell 2000, New York 09:30-16:00). Files `forex/data/<SYM>_M1_ticks_full.parquet` (bid OHLC + ask OHLC per minute, MT5 broker server clock = Europe/Athens like MT5 broker, from 2021-10 / 2022-01 to 2026-10-02). These are research data only (MT5 broker, not MT5 broker): a pass here says the effect is real, not that these symbols can be traded on MT5 broker.

## Hypotheses, frozen exactly as found on MT5 broker indices today
- **H1 session opening-range breakout, hold to the close:** 30-minute box from the session open, stop orders at the box (ask / bid), first fill, stop at the other side of the box, close at the session end (capped 22:55 server). MT5 broker indices: +0.049 / +0.057 / -0.038 R.
- **H2 = H1 in the daily-trend direction only** (side = sign(previous close - SMA20), server days). MT5 broker indices: +0.076 / +0.082 / -0.041.
- **H3 month opening range:** first 3 trading days' range, stop orders from day 4 to the 15th, stop at the other side, close on the month's last trading day 21:55 server. MT5 broker indices: +0.175 / +0.011 / +0.292.
Real bid/ask, stops on the executable side, stop first if both in a minute, gapped stops at the open; R >= 2 spreads.

## Test (all of 2022-01..2026-10-02 is out-of-sample for these three markets)
Pooled over the three markets: 1. mean R > 0 with t >= 2.13 (one-sided, Bonferroni 3; trade-level t for H3, daily-portfolio NW t for H1/H2); 2. positive in at least 2 of the 3 markets; 3. beats a random-entry control (same window, random side, same R and exit) by >= 0.03 R. Reported per market and per year.
## Honest prior
About 25% for H1/H2 (index intraday momentum is documented in the literature and showed on 6 MT5 broker indices), about 15% for H3 (small samples).
