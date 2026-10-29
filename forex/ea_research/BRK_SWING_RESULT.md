# BRK-SWING result (breakout day round 17, 2026-10-15 12:23): holding breakouts for days, or aligning them with a fresh 20-day breakout, makes them worse
Pre-registration `PREREG_BRK_SWING.md`, engine `brk_swing.py` (truncation PASS; hand check NSDQ 2024-06-12: hold-to-close -0.07 R, 5-day swing +3.27 R, 10-day +0.89 R, fresh daily breakout up), rows `data\si_ledgers\BRK_SWING.parquet`.
| cell (net R) | DEV | VAL | 2026 | random control DEV / VAL / 2026 |
|---|---|---|---|---|
| S5 hold up to 5 days, 2-ATR trail after +1R | -0.083 | -0.169 | -0.064 | -0.127 / -0.208 / -0.212 |
| S10 hold up to 10 days | -0.085 | -0.224 | -0.115 | -0.128 / -0.233 / -0.254 |
| D20 aligned (fresh daily 20-day breakout, same side), hold to close | -0.130 | -0.199 | -0.135 | -0.094 / -0.119 / -0.155 |
0 of 3 pass. Longer holds keep the breakout's small advantage over random (+0.04..+0.15 R) but add more noise and the overnight rollover spreads; metals gain in 2025-26 (gold bull run: +0.27 / +0.57 R for 5 days) and lose elsewhere. Aligning the intraday breakout with a FRESH daily breakout is worse than random on every class except indices (+0.061 / +0.113 / +0.047): after a new 20-day high, intraday breakouts tend to exhaust.
