# The daily card replayed on the last six weeks (2026-09-01 .. 2026-10-15, MT5 broker terminal M1 bars, read-only)
Script `card_recent.py` (bid bars + the bar's recorded spread as the ask). Card rules: gold London (box 08:00-08:30, stop = box clipped 0.12-0.36% of price, skip > 0.48%, 2R, exit 14:00 London); Nasdaq New York (box 09:30-10:00, stop = half box clipped 0.17-0.34%, 2R, orders to 12:00, exit 15:30 NY), with and without the trend filter.
| leg | trades | total R | at $1,000 / trade | wins / losses |
|---|---|---|---|---|
| Gold London | 32 | -4.53 | -$4,529 | 10 / 22 |
| Nasdaq NY, both sides | 32 | +5.86 | +$5,859 | 14 / 18 |
| Nasdaq NY, trend direction only | 14 | -2.59 | -$2,595 | 5 / 9 |
Six weeks are far too few to judge (a 2R system with no edge swings +/- 6R in 30 trades); the numbers show the size of normal swings, not an edge. 14 Oct (CPI selloff): the Nasdaq leg would have been short at the box low for +2R (the trend filter, long-only that day, would have skipped it).

## Addendum 14:37: the same six weeks on the live terminal's REAL TICKS (read-only paper log `forex/forward_test/card_paper.py`, 300 ms latency)
| leg | trades | M1 bars | real ticks |
|---|---|---|---|
| Gold London | 32 | -4.53 R | **-11.74 R** |
| Nasdaq NY, both sides | 31-32 | +5.86 R | +4.92 R |
| Nasdaq NY, trend side only | 12-14 | -2.59 R | -2.11 R |
Both columns include 15 Oct (gold: +0.56 R on the bars was a still-open position at 13:17; on ticks the trade was stopped at -1.26 R). Gold agrees on 30 of the other 31 days; the difference is 4 Sep (US jobs report): the long was still open at 13:30 London when gold fell $60 in 8 seconds (4,470 -> 4,410) through the 4,461 stop, a real fill near 4,408 = -5.8 R, which the M1 engine books as -1 R at the stop. A tight-stop position held through a major US release can lose several R in one gap: the card's news rule (flat before CPI / NFP / FOMC) is not optional. Log: `forex/forward_test/log/card_paper.csv` (gold and Nasdaq legs, one row per leg and day; the Nasdaq rows carry the daily-trend side).
