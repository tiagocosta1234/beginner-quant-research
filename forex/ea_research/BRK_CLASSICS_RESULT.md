# BRK-CLASSICS result (breakout day round 8, 2026-10-15 11:57): the named breakout strategies do not pass either
Pre-registration `PREREG_BRK_CLASSICS.md`, engine `brk_classics.py`, rows `data\si_ledgers\BRK_CLASSICS.parquet`. Truncation PASS; hand check NSDQ 2024-06-12 (CPI day): 5-minute ORB long at 09:35 NY +0.94 R, gap-go long +0.48 R, gap-fade short stopped -1 R, Williams 0.5 long -0.27 R, Williams 0.25 long +0.47 R.

| cell (R per trade) | DEV | VAL | 2026 | random control DEV / VAL / 2026 | notes |
|---|---|---|---|---|---|
| C1 Larry Williams volatility breakout k 0.5 | -0.034 (t -4.8) | +0.016 | -0.071 | -0.064 / -0.017 / -0.102 | indices +0.057 / +0.125 / -0.031 |
| C2 Williams k 0.25 | -0.046 | -0.071 | -0.075 | -0.063 / -0.072 / -0.116 | indices +0.039 / +0.067 / -0.009 |
| C3 5-minute ORB (Zarattini et al. 2023), MT5 broker indices | +0.014 (t 0.28) | +0.007 | -0.065 | -0.020 / -0.049 / -0.007 | NSDQ +0.135, DAX +0.073, SP -0.031, DOW -0.019, NIKKEI -0.067, ASX -0.131; by year +0.106 (2022), -0.041, -0.026, +0.007, -0.065 |
| C3 out-of-sample on FTSE / CAC / Russell | -0.057 (t -0.99, 3,293 trades) | | | -0.044 | by year +0.016, -0.100, -0.030, -0.077, -0.106 |
| C4 cash-gap continuation (indices, gap >= 0.3 ATR) | +0.021 | -0.119 | +0.014 | +0.002 / +0.054 / -0.032 | |
| C5 cash-gap fade to the previous close | -0.044 | +0.094 (t 2.23) | -0.042 | +0.004 / -0.015 / +0.027 | signs flip between periods |
| C6 Crabel inside-day breakout | -0.040 | +0.014 | +0.006 | -0.040 / -0.016 / -0.041 | |
0 of 6 pass. The published 5-minute ORB holds only on NSDQ (the QQQ it was found on), mostly in 2022, and loses on the other indices and out of sample. Every classic shows the same two facts as rounds 1-7: a breakout beats a random entry by a few hundredths of R, and indices were positive in 2022-25 and not in 2026.
