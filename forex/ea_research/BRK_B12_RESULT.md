# BRK-B12 result (breakout day round 12, 2026-10-15 12:03): overnight range, initial balance, intermarket confirmation, DAX lead - none passes
Pre-registration `PREREG_BRK_B12.md`, engine `brk_b12.py` (truncation PASS), rows `D:\finance\si_ledgers\BRK_B12.parquet`. Hand check NSDQ 2024-06-12: overnight-range long filled 09:40 NY, +0.37 R.
US 30-minute session breakouts with no filter (reference): +0.114 / +0.073 / -0.079 R (DEV / VAL / 2026).

| cell | DEV | VAL | 2026 | control DEV / VAL / 2026 |
|---|---|---|---|---|
| O1 overnight-range breakout at the US cash open | +0.015 (t -0.11) | +0.056 | +0.006 | -0.010 / +0.028 / -0.068 |
| O2 initial balance (60-minute box), 46 markets | -0.041 (t -5.2) | -0.090 | -0.050 | -0.076 / -0.096 / -0.106 |
| O3 US index breakout confirmed by its partner index | +0.145 (t 2.07) | +0.047 | -0.094 | -0.054 / -0.012 / +0.021 |
| O4 US index breakout in the direction of the DAX breakout | +0.148 (t 1.15) | -0.068 | -0.057 | +0.006 / -0.015 / -0.026 |
0 of 4 pass. The intermarket-confirmed US breakout is the strongest 2022-24 number of the day (+0.145 R) and, like every index variant, turns negative in 2026.
