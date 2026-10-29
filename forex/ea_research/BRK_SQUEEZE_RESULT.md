# BRK-SQUEEZE result (breakout day round 26, 2026-10-15 13:43, local clock): squeeze breakouts are no better than random entries
Pre-registration `PREREG_BRK_SQUEEZE.md`, engine `brk_squeeze.py` (truncation PASS), rows `data\si_ledgers\BRK_SQUEEZE.parquet`. TTM squeeze = Bollinger(20, 2) inside Keltner(20, 1.5 ATR), 6 bars or more, 46 markets.
| cell (net R) | DEV | VAL | 2026 | random control DEV / VAL / 2026 |
|---|---|---|---|---|
| Q1 M15 squeeze range break (n 31,167 / 11,131 / 7,829) | -0.103 (t -9.5) | -0.100 | -0.108 | -0.092 / -0.117 / -0.095 |
| Q2 M15 squeeze release, TTM direction (n 29,890 / 10,757 / 7,399) | -0.128 (t -9.7) | -0.150 | -0.105 | -0.114 / -0.114 / -0.129 |
| Q3 H1 squeeze range break (n 7,598 / 2,731 / 2,025) | -0.043 (t -2.7) | -0.061 | -0.048 | -0.059 / -0.045 / -0.052 |
0 of 3 pass. A squeeze breakout earns what a random entry earns (information -0.02..+0.02 R): the "coil before the move" adds nothing on MT5 broker; the loss is the spread paid on small M15 ranges. On H1 the cost share falls and the loss shrinks to the random level.
Observation, post hoc (not a test): H1 squeeze breaks on energy +0.056 / +0.109 / +0.350 (n about 300 / 110 / 80) and metals +0.104 / +0.088 / -0.055.
