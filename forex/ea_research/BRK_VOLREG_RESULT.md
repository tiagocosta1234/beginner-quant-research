# BRK-VOLREG result (breakout day round 3, 2026-10-15 11:45): volume and volatility regime do not separate good breakouts from bad
Pre-registration `PREREG_BRK_VOLREG.md`, engine `brk_volreg.py`, rows `D:\finance\si_ledgers\BRK_VOLREG.parquet`. Base = round 1's 54,006 session stop-order breakouts, exit hold-to-close (X4): DEV -0.032 / VAL -0.076 / 2026 -0.037 R. Tick-volume coverage 97%. Truncation PASS; hand check NSDQ 2024-06-12 X4 -0.072 (as round 1), relative breakout volume 1.03, trend +1.

| cell (X4, R per trade) | DEV | VAL | 2026 | indices DEV / VAL / 2026 |
|---|---|---|---|---|
| V1 volume surge at the breakout (top tercile) | -0.036 | -0.019 | -0.047 | +0.048 / +0.069 / -0.079 |
| V2 busy opening box | -0.047 | +0.007 | +0.036 | +0.038 / +0.018 / -0.034 |
| V3 high-volatility regime (ATR rank >= 0.67) | -0.005 | -0.035 | -0.007 | +0.049 / +0.030 / -0.025 |
| V4 NR4 the day before | -0.029 | -0.037 | -0.110 | +0.105 / +0.032 / -0.164 |
| V5 trend direction, every market | -0.036 | -0.109 | -0.061 | +0.076 / +0.082 / -0.041 |
| V6 trend direction and volume surge | -0.107 | -0.066 | -0.097 | +0.062 / +0.077 / -0.135 |
0 of 6 pass.

By tercile (DEV, all markets): breakout-minute volume low / mid / high = -0.028 / -0.033 / -0.036 (flat: "volume confirms the breakout" does not hold on MT5 broker tick volume); box volume -0.010 / -0.030 / -0.056 (busy openings are WORSE); ATR rank -0.038 / -0.064 / -0.005 (high-volatility regimes are the least bad, not positive). The trend filter helps only on indices; on FX it makes 2025 worse (-0.137).
