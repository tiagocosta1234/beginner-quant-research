# INDEX-OOS result (breakout day round 7, 2026-10-15 11:54): today's index-breakout leads do NOT replicate on new indices
Pre-registration `PREREG_INDEX_OOS.md` (hypotheses frozen from MT5 broker indices before these markets were loaded), engine `index_oos.py`, rows `D:\finance\si_ledgers\INDEX_OOS.parquet`. Markets never used today: UK100 (FTSE), FRA40 (CAC 40), US2000 (Russell 2000), MT5 broker M1 bid/ask 2022-01..2026-10-02. Truncation PASS on all three; session clocks checked (fills at 08:30 London, 09:30 Paris, 10:00 New York).

| hypothesis | trades | mean R (t) | random control | per market | by year 2022 / 23 / 24 / 25 / 26 | gates |
|---|---|---|---|---|---|---|
| H1 session ORB, hold to close | 3,501 | -0.009 (-0.22) | -0.051 | FTSE +0.009, CAC -0.024, Russell -0.011 | +0.065 / +0.016 / -0.008 / -0.049 / -0.087 | nnY |
| H2 = H1 in the trend direction | 1,785 | +0.020 (+0.12) | -0.069 | +0.049 / +0.007 / +0.005 | +0.101 / +0.056 / -0.041 / +0.047 / -0.086 | nYY |
| H3 month opening range | 161 | +0.070 (+0.68) | +0.017 | -0.019 / +0.041 / +0.186 | -0.160 / +0.380 / +0.248 / +0.047 / -0.159 | nYY |
0 of 3 pass (none reaches t 2.13; the breakouts beat random entries by 0.04-0.09 R, as on MT5 broker, but the totals are near zero).

What it teaches: the index-breakout edge seen on the six MT5 broker indices is not a general property of stock indices. On new indices it is about zero, and it DECAYS through time in both data sets: MT5 broker indices hold-to-close +0.101 (2022) -> -0.038 (2026), new indices +0.065 (2022) -> -0.087 (2026). Intraday index momentum was strong in the 2022 high-volatility bear market and has faded since. This is the strongest evidence today against building the card on index breakouts.
