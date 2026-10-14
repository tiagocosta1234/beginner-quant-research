# DAY2K-D result (2026-10-14): gold long OR short, one 1:1 / 2,000 USD trade a day - no survivor, one LEAD

Pre-registration `PREREG_DAY2K_D.md` (commit 48858d5c), engine `day2kd.py`, cells `D:\finance\si_ledgers\DAY2KD_cells.csv`. XAUUSD+ only, the side chosen each day. HOLD unopened.

## Gates
Oracle side +0.43..+0.86 R, ML label leak +0.44..+0.85 R; placebo worlds rules 121-123 and ML 131-133: 0 survivors each (best DEV t 1.31).

## Result (28 cells)
S1 survivors **0**. But the cells are not noise-shaped: all 12 continuation cells (trade in the direction of the 5-day, 1-day or morning move) are positive in DEV (+0.002..+0.055 R) and 9 of 12 in VAL; the 12 fade cells are their mirror (negative). ML cells: -0.075..+0.028 DEV, nothing.
Best cell M1-cont-T1635-k0.7 (at 16:35 server, trade gold in the direction of its last 24 h, stop = target = 0.7 x ATR20, close at 21:55): DEV +0.055 R, t +2.67 (bar 2.91); VAL +0.032 R, t +0.96 (bar 1.65); by year 2022 +0.058, 2023 +0.039, 2024 +0.071, 2025 +0.032; long on 53% of days (so it is not the gold drift: always-long is +0.016 DEV / +0.021 VAL at the same T,k); MT5 broker rolling starts 94% pass / 6% breach, median 54 days (in-sample, best of 28 cells: optimistic).
Caveats: (1) selected as the best of 28 after seeing them; (2) at 16:35 with k0.7 only about 17% of days reach the stop or the target by 21:55: the daily result is mostly a partial R, NOT +/-2,000; (3) it is gold short-term momentum, the same character as the live XAU5 trend follower, so it probably correlates with the live pair; (4) the effect is small (+0.03..+0.07 R per trade, about +60..140 USD on 2,000 risk).

## What would confirm it
The 2026 HOLD (about 190 days) cannot confirm an effect this small (SE about 0.07 R, a true +0.05 R shows at t 0.7) and the protocol keeps it for development passers. Real confirmation needs more independent data: gold before 2020 (needs the trader's OK under the 2020 rule) or the forward record. Logged as a lead in the ledger, not as an edge.
