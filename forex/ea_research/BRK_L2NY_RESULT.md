# BRK-L2NY result (breakout day round 36, 2026-10-15 14:44, local clock): the London-morning range broken in New York = random entries
Pre-registration `PREREG_BRK_L2NY.md`, engine `brk_l2ny.py` (truncation PASS; fill-minute rule), rows `D:/finance/si_ledgers/BRK_L2NY.parquet`. Box 08:00-12:00 London, OCO stop orders 12:00-16:00, hold to 20:00 London, 46 markets.
| cell (net R, M1 bars) | DEV | VAL | 2026 | random control DEV / VAL / 2026 |
|---|---|---|---|---|
| N1 stop at the other side (n 32,464 / 11,940 / 8,675) | -0.054 (t -5.4) | -0.060 | -0.050 | -0.045 / -0.065 / -0.078 |
| N2 stop at the box middle (n 31,134 / 11,593 / 8,109) | -0.084 (t -6.4) | -0.129 | -0.076 | -0.067 / -0.105 / -0.113 |
0 of 2 pass. A wider (4-hour) box cuts the cost share but the breakout earns what a random entry earns (information -0.01..+0.03 R); indices about zero, every other class negative. On real ticks subtract about 0.03 R more.
