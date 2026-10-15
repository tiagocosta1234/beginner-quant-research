# Pre-registration BRK-CAL (breakout day, round 32; written 2026-10-15 14:06 local, local clock, before any result)
Question: do calendar days with known flows change session breakouts? (Round 15 tested news days and weekdays.) Trades = round 1's session breakouts held to the close (BRK_EXITS.parquet, column X4_noTP, 46 markets; random-entry rows as control).
- **C1 turn of the month, indices:** index breakouts on the last trading day of a month and the first three trading days of the next (pension and fund flows; the classic turn-of-month effect).
- **C2 after US options expiry, indices:** index breakouts on the Monday-Wednesday after the third Friday of the month (dealer gamma released after pinning, so moves should extend).
- **C3 first trading day of the month, all markets.**
Day definitions use the market's trading days in the data (local session day).
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): 1. DEV mean >= +0.05 R and t >= 2.39 (daily NW lag 1; Bonferroni 3). 2. VAL mean > 0 and t >= 1.65. 3. Beats the same markets' other days by >= 0.05 R in DEV and in VAL.
Honest prior: about 4%.
