# BRK-IMOM result (breakout day round 28, 2026-10-15 13:52, local clock): no intraday momentum from the opening move to the last half hour
Pre-registration `PREREG_BRK_IMOM.md` (amendment A1 before any P&L: every reference time one minute before the close, because 16:00 NY is 23:00 server), engine `brk_imom.py` (truncation PASS), rows `D:\finance\si_ledgers\BRK_IMOM.parquet`. Net bp per trade (one spread), trade = the last half hour of the session in the direction of the first half-hour move away from the previous close (Gao, Han, Li and Zhou 2018).
| cell, INDEX class (primary) | DEV | VAL | 2026 | long-only same half hour DEV / VAL / 2026 |
|---|---|---|---|---|
| G1 direction of the first half hour (n 3,706 / 1,181 / 860) | -1.80 bp (t -3.6) | -1.47 | -1.22 | -1.42 / -0.56 / -0.94 |
| G2 first half hour and 12th half hour agree (n 1,886 / 618 / 450) | -1.27 bp (t -1.7) | -2.31 | -1.47 | -1.52 / -0.26 / -1.54 |
0 of 2 pass. By index (G1, DEV / VAL / 2026 bp): SP -1.5 / -0.5 / -1.3, NSDQ -2.3 / -0.9 / +1.2, DOW -1.8 / -1.0 / -1.7, DAX -1.2 / -0.6 / -1.0, NIKKEI -2.3 / -3.0 / -3.3, ASX -1.8 / -3.4 / -1.2: the gross effect is about zero and the half-hour spread decides. Descriptive classes: FX -0.5..-1.8 bp, metals -3..-10 bp, energy -4..-12 bp, crypto -22..-88 bp (spreads), none above its long-only or random yardstick by a usable margin.
Reading: the published 1993-2013 S&P effect is not present in MT5 broker index CFDs 2022-2026 at the last-half-hour horizon.
