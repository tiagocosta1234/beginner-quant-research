# ROLL_2020_CHECK - where the 2020-21 CME futures switch contract, and whether earlier rounds were affected

Written 2026-10-18 14:53 local (local clock, second PC PC-2), found by the GN11 dry run. Data: `futures/data/databento/
futures_{NQ,ES}.F_1m.parquet` (one continuous series, no contract names). Output: `C:\work\scratch\roll_check.txt` (second PC).

## Facts
- **From mid-2022** both NQ and ES switch at 00:00 UTC on the Monday of the quarterly expiry week (jumps +26 .. +297 NQ points,
  +32 .. +71 ES points as rates rose): `gn5.roll_mondays` is right there.
- **ES 2020-09 .. 2022-03** switched at 00:00 UTC on the FRIDAY of the week before the expiry week (Thursday ~19:00-20:00 New
  York): -10.50 (2020-09-11), -8.50 (12-11), -9.50 (2021-03-12), -9.50 (06-11), -9.25 (09-10), -7.25 (12-10), -9.50 (2022-03-11).
  The March and June 2020 switches are not visible (small carry, crash volatility).
- **NQ 2020-21:** no jump at any 00:00 UTC minute near the rolls. At the Sunday re-open before the expiry week NQ moves against
  ES by -24.8 (2020-09-13), -11.7 (12-13), -17.6 (2021-03-14), -10.0 (06-13) points (other Sundays: median 5.8, 90th percentile
  17.9), so those rolls are at the Sunday re-open, i.e. Monday's trade date starts on the new contract; 2021-09, 2021-12 and
  2022-03 show nothing identifiable (switch hidden or carry near zero); 2020-03 and 2020-06 are swamped by the crash moves.

## Effect on earlier verdicts (re-run with the ES switch Fridays also skipped)
| test (2020-21 futures, out of time) | as run (roll Mondays skipped) | + ES switch Fridays skipped |
|---|---|---|
| GN6 X1 ES overnight-range breakout | +0.064 R (t 0.97), n 398 | +0.078 R (t 1.16), n 393 |
| GN9 L2 ES late-day continuation, big days | -0.396 (t -5.09), n 61 | -0.396 (t -4.90), n 59 |
| GN10 reversal, ES part | +0.384 (t 2.65), n 61 | +0.398 (t 2.58), n 59 |
No verdict changes. Intraday New York-session tests (GN7, GN8) cannot contain a switch. For NQ the switches that matter fall at the
Sunday re-open, before Monday's overnight range (GN5 O1) and inside Monday's day move (GN9 / GN10, roll Mondays skipped); an
unidentified NQ switch inside a weekday overnight session would touch about 4 trades a year, about 0.005 R on the means.

## Rule for future 2020-21 futures work
Skip both the roll Monday (`gn5.roll_mondays`) and, for ES in 2020-09 .. 2022-03, the Friday before it; for anything held across
a roll (weekly / monthly), skip the roll weeks or months (GN11 amendment 1), because NQ's 2020-21 switch minute is not reliably
identifiable.
