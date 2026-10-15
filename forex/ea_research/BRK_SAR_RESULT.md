# BRK-SAR result (breakout day round 18, 2026-10-15 12:29): stop-and-reverse is the worst breakout trade of the day; streaks mean nothing
Pre-registration `PREREG_BRK_SAR.md` (written before the run, committed with it), engine `brk_sar.py`, rows `D:\finance\si_ledgers\BRK_SAR.parquet`.
| cell (net R) | DEV | VAL | 2026 | control / reference |
|---|---|---|---|---|
| SAR: reverse when the first breakout's stop is hit, hold to close | -0.201 (t -12.4, 21,086) | -0.230 | -0.242 | random entry after the stop-out -0.074 / -0.099 / -0.120 |
| STREAK: breakout only if yesterday's breakout in that market won | -0.057 | -0.074 | -0.022 | all breakouts -0.032 / -0.076 / -0.037; after a losing day -0.021 / -0.077 / -0.043 |
0 of 2 pass. A day whose first breakout fails is a two-sided chop day: the reverse breakout fails too, and far more often than a random entry (-0.20 R vs -0.07 R). Yesterday's result says nothing about today's breakout.
