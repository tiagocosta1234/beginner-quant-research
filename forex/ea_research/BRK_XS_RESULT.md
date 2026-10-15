# BRK-XS result (breakout day round 6, 2026-10-15 11:52): cross-market selection does not pick better breakouts
Pre-registration `PREREG_BRK_XS.md`, engine `brk_xs.py` (events from BRK_META). Hand check NSDQ 2024-06-12: long, 20-day rank 1.00 (strongest of 46), breadth 0.587 (27 markets had already broken up), 44th breakout of the day.

| cell (hold to close, R per trade) | DEV | VAL | 2026 | indices DEV / VAL / 2026 |
|---|---|---|---|---|
| XS1 20-day relative strength (long top fifth, short bottom fifth) | -0.088 | -0.107 | -0.069 | +0.068 / +0.073 / +0.002 |
| XS2 60-day relative strength | -0.088 | -0.071 | -0.060 | +0.061 / +0.028 / -0.165 |
| XS3 crowd day (>= 7 markets already broke the same way) | -0.009 | -0.082 | -0.043 | +0.116 / +0.095 / -0.065 |
| XS4 first 5 breakouts of the day | -0.074 | -0.079 | -0.039 | -0.088 / -0.002 / +0.022 |
0 of 4 pass (all-market base: -0.032 / -0.076 / -0.037). Relative-strength selection makes the universe WORSE (strong markets' breakouts mean-revert intraday on FX, crypto and metals); crowd days are the least bad and the best for indices (+0.116 / +0.095), still negative in 2026.
