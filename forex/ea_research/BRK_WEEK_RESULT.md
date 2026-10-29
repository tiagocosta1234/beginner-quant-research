# BRK-WEEK result (breakout day round 4, 2026-10-15 11:47): bigger boxes cut the cost, not the noise; two small leads
Pre-registration `PREREG_BRK_WEEK.md`, engine `brk_week.py`, rows `data\si_ledgers\BRK_WEEK.parquet`. Truncation PASS (40-day margin); hand check XAUUSD W1 week of 2022-10-17: short filled Wed 2022-10-19 09:52 server, closed Friday at -0.45 R.

| cell (R per trade) | DEV | VAL | 2026 | control DEV / VAL / 2026 | indices DEV / VAL / 2026 |
|---|---|---|---|---|---|
| W1 Monday range, close Fri | +0.009 | -0.125 | -0.045 | -0.024 / -0.087 / -0.030 | +0.038 / -0.079 / -0.124 |
| W1 ..., 2R | -0.001 | -0.110 | -0.048 | -0.023 / -0.086 / -0.035 | +0.009 / -0.041 / -0.111 |
| W2 previous-week range, close Fri | +0.000 | -0.101 | -0.049 | -0.023 / -0.020 / -0.046 | +0.044 / -0.032 / -0.145 |
| W2 ..., 2R | -0.012 | -0.084 | -0.078 | -0.022 / -0.020 / -0.056 | +0.051 / -0.025 / -0.117 |
| W4 month opening range, close month end | +0.065 | -0.140 | +0.231 | +0.030 / -0.131 / -0.090 | +0.175 / +0.011 / +0.292 |
| W4 ..., 2R | +0.008 | -0.053 | +0.215 | -0.024 / -0.077 / -0.118 | +0.140 / +0.098 / +0.247 |
0 of 6 pass.

What it teaches:
- **The cost mechanism is confirmed:** random entries cost about -0.02 R here against -0.08 to -0.09 R on 30-minute boxes; but the breakout's own information does not grow with the box, so the result is about zero instead of negative.
- **Lead 1, index month-opening-range breakout (close at month end):** +0.175 R (t 1.70, 204 trades) / +0.011 (67) / +0.292 (t 1.44, 52); positive every year (2022 +0.216, 2023 +0.202, 2024 +0.102, 2025 +0.011, 2026 +0.292) and in 5 of 6 indices (DAX -0.016); control -0.028 / -0.128 / +0.017.
- **Lead 2, metals previous-week breakout:** +0.131 (t 1.79) / +0.361 (t 2.67) / +0.023, but random entries on metals also earn (+0.092 / +0.209 / -0.052: the gold bull drift), so the breakout adds only +0.04 / +0.15 / +0.08 R.
