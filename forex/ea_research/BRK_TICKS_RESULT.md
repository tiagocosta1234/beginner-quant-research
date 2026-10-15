# BRK-TICKS result (breakout day round 13, 2026-10-15 12:43): what the ticks do in the first 30 seconds does not tell real breakouts from false ones
Pre-registration `PREREG_BRK_TICKS.md`, engine `brk_ticks.py`, rows `D:\finance\si_ledgers\BRK_TICKS.parquet`. MT5 broker real ticks 2025-10..2026-09, 11,684 session breakouts (DEV 2025-10..2026-03: 5,938; VAL 2026-04..09: 5,746); entry 30 s after the touch. Hand check NSDQ 2025-10-08: touch 17:00:05.98 server (6 s after the box), +0.075 R in the first 30 s.
Median move in the 30 seconds after the touch: 0.0 R (price is back at the level).
| cell (net R, hold to close) | DEV | VAL |
|---|---|---|
| all breakouts, entered 30 s after the touch | -0.073 (t -3.2) | -0.058 |
| T1 fastest third (move in the first 30 s) | -0.116 | -0.049 |
| T2 most active third (ticks in the first 30 s vs normal) | -0.145 | -0.032 |
| T3 order flow into the level aligned (>= +0.2) | -0.060 | -0.026 |
| T4 spread not wider than normal at the touch | -0.078 | -0.039 |
0 of 4 pass. Terciles are flat or U-shaped (speed -0.050 / -0.094 / -0.052; activity -0.075 / -0.037 / -0.084): a breakout that rips through the level on heavy, fast ticks does NOT follow through better; the most active breakouts are among the worst (news spikes that reverse). By class over the 12 tick months: metals +0.102, indices +0.003, FX -0.072, crypto -0.119, energy -0.124.
