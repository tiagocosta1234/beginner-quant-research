# BRK-B20 result (breakout day round 20, 2026-10-15 12:46): demanding more of the breakout changes nothing
Pre-registration `PREREG_BRK_B20.md`, engine `brk_b20.py` (truncation PASS), rows `D:\finance\si_ledgers\BRK_B20.parquet`.
| cell (net R, hold to close) | DEV | VAL | 2026 | control DEV / VAL / 2026 |
|---|---|---|---|---|
| U0 plain stop orders (reference) | -0.032 | -0.076 | -0.037 | -0.085 / -0.101 / -0.119 |
| U1 buffer 0.10 box | -0.031 | -0.074 | -0.038 | -0.092 / -0.094 / -0.117 |
| U2 buffer 0.25 box | -0.031 | -0.077 | -0.044 | -0.090 / -0.105 / -0.085 |
| U3 buffer 0.50 box | -0.033 | -0.066 | -0.048 | -0.078 / -0.083 / -0.093 |
| U4 box edge touched >= 3 times | -0.070 (993) | +0.055 (342) | +0.136 (250) | -0.108 / -0.182 / -0.135 |
| U5 box edge at the previous day's high/low | +0.080 (904) | -0.182 | -0.185 | -0.046 / -0.102 / -0.077 |
0 of 5 pass. The result per trade is the same whether the entry waits for 0, 0.1, 0.25 or 0.5 box of extra move: the breakout's small information is not in the first push beyond the level, so a "confirmation buffer" only moves the entry and the stop together. Tested and double levels are small, noisy samples whose signs flip between periods.
