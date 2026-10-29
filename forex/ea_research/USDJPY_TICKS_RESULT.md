# USDJPY London breakout on MT5 broker REAL TICKS (2026-10-15 14:29, local clock; diagnostic): the last year is about break-even after real execution
Script `usdjpy_ticks.py`, rows `data/si_ledgers/USDJPY_TICKS.parquet`. MT5 broker USDJPY ticks 2025-10-01 .. 2026-10-12 (server clock -> London), box from tick bids 08:00-08:30, first trigger tick 08:30-11:00, fills at real ticks 300 ms later, stop at the other side of the box (filled at the tick 300 ms after it is touched), exit 17:00.
| version (262 trades) | mean R |
|---|---|
| real ticks, 300 ms in and out | -0.020 |
| real ticks, no latency | -0.011 |
| entry exactly at the level, stop fills at ticks +300 ms | -0.019 |
| entry and stop exactly at the levels (ideal) | +0.004 |
| the M1 engine on the same 255 days | +0.073 |
Same side on 99% of days, R correlation +0.979, but the ticks earn 0.05-0.08 R a trade LESS than the M1 engine (shorts -0.071, longs -0.038): about -0.03 R a trade of ordinary friction (variable spread at the moment of the breakout: median 0.8 pip at the fill vs 0.6 in the bars) plus a few days where a spread spike or a gap through the stop hit the real position but not the bar model (2025-11-13: a short at +2.6 R on M1 bars was stopped at -1.0 on ticks; three long stops filled at -1.5..-1.9 R).
Account effect with a 0.05 / 0.08 R haircut on every USDJPY trade (pair x1.2 + USDJPY $150): 22 Dec 32.3% / 31.2% (breach 4.7% / 5.1%) against 29.4% (3.0%) for the pair alone: +2-3 points of pass for +1.7-2.1 points of breach.
Reading: the USDJPY edge measured on M1 bars (+0.1..+0.2 R) shrinks to about +0.05..+0.15 R with real MT5 broker execution, and the most recent year on real ticks is about zero. It is real enough to keep watching, too thin to carry the account. This tick check is the lesson to apply to every tight-stop idea: test it on MT5 broker real ticks before believing the bars.

## Addendum 14:41: news flat (ManualORB now goes flat 5 min before CPI / NFP / FOMC and stops for the day)
USDJPY rule with an exit at 13:25 London on CPI / NFP days instead of 17:00 (M1 bars; 2020-21 at today's 0.006 spread, NFP days only): 2020-21 +0.204 -> +0.179 R; 2022-26 MT5 broker +0.133 -> +0.114 R (by year 2022 +0.32, 2023 -0.17, 2024 +0.13, 2025 +0.14, 2026 +0.16). It costs about 0.02 R a trade on the bars and removes the release-gap tail that the bars cannot see (NEWS_GAPS_RESULT: USDJPY NFP jumps past the stop within 10 s in 83% of releases, spread 8-10 pips).

## Addendum 14:48: news flat on REAL TICKS (post hoc, small sample)
USDJPY rule on MT5 broker ticks Oct 2025 - Oct 2026: holding to 17:00 -0.020 R a trade (262 trades); with the exit at 13:25 London on CPI / NFP days +0.018 R. On the 23 CPI / NFP days alone: -0.539 R holding through the release vs -0.098 with the early exit. The bars (previous addendum) cannot see the release gaps, so they showed news flat as a small cost; the ticks show it as the difference between losing and about break-even in the last year. ManualORB's news flat matches this.
