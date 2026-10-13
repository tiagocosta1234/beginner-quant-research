# M: turn of the month on MT5 broker index CFDs (SP, NSDQ, DOW, DAX): result (2026-10-10, local local clock)

Pre-registration `PREREG_TURN_OF_MONTH.md` (commit ac33c96, before any statistic), script `turn_of_month.py`, output `TURN_OF_MONTH_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: both trials fail; in 2022-25 the turn of the month was WORSE than ordinary days
| trial | DEV 2022-24 (36 months) | VAL 2025 (12) |
|---|---|---|
| M1 days -1 .. +3 | -2.1 bp, 47% of months up, t -0.06, worst -538 bp | +18.0 bp, t +0.44 |
| M2 days -4 .. +3 | +38.1 bp, 53% up, t +0.96, worst -636 bp | +53.8 bp, t +0.67 |
Diagnostic 2022-25, mean daily return on the window days (-1 .. +3) vs all other days: DAX -1.4 vs +5.6 bp, DOW -0.4 vs +3.6, NSDQ +2.8 vs +4.8, SP +1.2 vs +4.2 (Welch t -0.17 to -0.77). The classic effect is absent in this regime; M2's positive mean is the market's ordinary drift over 8 days.
