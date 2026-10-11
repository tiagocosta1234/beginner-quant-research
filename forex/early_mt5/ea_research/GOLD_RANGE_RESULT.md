# GR: gold range system at H1 / daily horizons (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_GOLD_RANGE.md` (commit 3853862), simulator `gold_range.py`, output `GOLD_RANGE_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: all three fail; gold mean reversion is closed for this campaign (as registered)
| variant | DEV trades | DEV mean R | DEV PF | DEV daily t | 2022-23 USD | VAL 2025 | corr with pair |
|---|---|---|---|---|---|---|---|
| GR1 daily, ranging regime (ER20 < 0.30), z 1.5 | 50 | -0.157 | 0.51 | -1.95 | -3,949 | -0.024 R (9 trades) | -0.08 |
| GR2 daily, no regime filter | 76 | -0.119 | 0.60 | -1.80 | -3,325 | -0.215 R | -0.08 |
| GR3 H1, ranging (ER100 < 0.25), z 2.0 | 511 | -0.008 | 0.98 | -0.20 | +4,636 | -0.153 R, -12,196 USD | -0.21 |
(500 USD risk per trade.)
## Reading
Together with GOLD_B G1 (M15), fading gold's stretches loses at every horizon tested (M15, H1, daily) in 2022-25. GR3 made money in 2022
only and lost every year since, and badly in 2025's trend. The negative correlation is real but there is no edge to collect with it:
gold in 2022-26 is a market where moves continue more often than they revert. No EA.
