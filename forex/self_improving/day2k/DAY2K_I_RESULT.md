# DAY2K-I result (2026-10-14): index intraday momentum (first half hour -> last half hour) - no net edge

Pre-registration `PREREG_DAY2K_I.md` (commit 1f233cbe), engine `day2ki.py`, cells `D:\finance\si_ledgers\DAY2KI_cells.csv`. SP, NSDQ, DOW (New York 09:30-16:00) and DAX (Berlin 09:00-17:30), exchange time converted to the server clock per day with the real DST rules; entry at the open of the last-half-hour bar on the executable side, exit at the session-end bar open; costs included. HOLD sealed.

## Gates
Oracle +12..+18 bp; truncation 40/40; DST check; placebos 171-173: 0 survivors (best t 1.03 / 0.40 / 1.33).

## Result (15 cells)
S1 survivors **0**. In 2021-24 the first half hour's move REVERSES into the close instead of continuing: continuation gross -1.2 bp (SP), -1.6 (NSDQ), -0.8 (DOW), +0.6 (DAX), -1.4 (US pool); with a round-trip spread of 1.3-1.5 bp the continuation loses 1.5-2.3 bp net (NSDQ t -2.1). Fading it would earn +0.8..+1.6 bp gross, about zero after the same spread. The second-to-last half hour (P3) continues in the direction the literature reports (gross +0.9 SP, +0.9 NSDQ, +1.5 DOW, +0.4 DAX) but net -0.3..+0.8 bp in 2021-24 and -0.5..-2.8 bp in 2025 (DOW t -2.5). Hit rates 43-52%, Spearman correlations of the predictor with the last-half-hour return -0.04..+0.06.

## Reading
The published intraday momentum effect is about 1-2 bp per trade gross; on MT5 broker's CFDs the round trip costs 1.3-1.5 bp, so even where the sign matches there is no net edge, and the first-half-hour version has the opposite sign in this sample. A 30-minute window is also too short to carry a 2,000 USD risk with a meaningful target. Closed.
