# Pre-registration BRK-SWING (breakout day, round 17; written 2026-10-15 12:22 local (commit time), before any code or result)
Question: does the intraday breakout's small information grow if the position is held for days (trend persistence), or if the intraday breakout is aligned with a fresh daily breakout?
Entries = round 1's session stop-order breakouts on 46 markets (30-minute box, stop orders, first fill; initial stop at the other side of the box; R = that distance).
- **S5 hold up to 5 trading days:** after +1R the stop trails 2 x ATR14 (daily, previous day) behind the best price reached (executable side, updated every minute from the previous minute's best); exit at 21:55 server on the 5th server day at the latest. Rollover minutes included (as live); MT5 broker swap-free.
- **S10 the same, up to 10 trading days.**
- **D20 aligned:** the session breakout held to the session close (round 1 X4), taken only if the market made a fresh daily Donchian-20 breakout in the same direction within the last 3 server days (a close above the previous 20-day high for longs / below the 20-day low for shorts).
Random-entry control for each cell (same window, random side, same R, same exit rule).
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): 1. DEV mean >= +0.05 R and t >= 2.4 (daily portfolio NW lag 5 for S5/S10, lag 1 for D20; Bonferroni 3). 2. VAL mean > 0 and t >= 1.65. 3. Beats its control by >= 0.05 R in DEV and VAL.
Honest prior: about 7%.
