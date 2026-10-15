# BRK-FLAG result (breakout day round 22, 2026-10-15 12:50): bull / bear flag breakouts are WORSE than random entries
Pre-registration `PREREG_BRK_FLAG.md`, engine `brk_flag.py` (truncation PASS), rows `D:\finance\si_ledgers\BRK_FLAG.parquet`. 15,406 mechanically defined M5 flags on 46 markets (impulse >= 1.5 ATR in 6 bars, tight flag of 6-18 bars, stop at the flag's other side; median flagpole target 2.7 R).
| exit (net R) | DEV | VAL | 2026 | random control DEV / VAL / 2026 |
|---|---|---|---|---|
| F1 flagpole target | -0.137 (t -8.2) | -0.156 | -0.161 | -0.089 / -0.084 / -0.087 |
| F2 hold to the close | -0.150 (t -7.2) | -0.119 | -0.170 | -0.073 / -0.055 / -0.065 |
0 of 2 pass. Every class loses except indices (about zero). On 5-minute bars a strong impulse followed by a tight pause is more often the END of the move than a continuation: the flag breakout loses 0.05-0.10 R a trade MORE than a random entry with the same stop.
