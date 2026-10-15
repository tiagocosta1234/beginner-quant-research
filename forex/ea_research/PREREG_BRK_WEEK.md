# Pre-registration BRK-WEEK (breakout day, round 4; written 2026-10-15 11:46 local (commit time), before any code or result)
Clue from rounds 1-3: breakout entries beat random entries by 0.03-0.05 R, but the spread costs about 0.08-0.09 R on 30-minute boxes. Bigger boxes shrink the cost share. Release-surprise breakouts were already tested (EVENTS_RESULT 0/18, TICK_EVENTS 0/4) and are not repeated.

## Data and rules
46 MT5 broker, M1 bid/ask, server clock, data to 2026-10-02 (2026 non-clean look). Days = server days, Monday-Friday weeks for every market (crypto weekends ignored). Stop orders: buy stop at the level (ask reaches it; fill at the level or the minute's ask open if beyond), sell stop (bid); first fill wins; both in one minute = no trade. Stops checked on every minute, rollover minutes included (as live). Exits: E-close (no target, close at the stated time) and E-2R (target 2R); stop -1R.
- **W1 Monday range:** Monday's bid high/low (01:00-22:59). Orders Tuesday 01:05 -> Thursday 22:55. Stop = the other side of Monday's range. Close Friday 21:55.
- **W2 previous-week range:** last week's (Mon-Fri) bid high/low. Orders Monday 01:05 -> Thursday 22:55. Stop = last week's midpoint. Close Friday 21:55.
- **W4 month opening range:** the first 3 trading days of the month. Orders from day 4 01:05 to the 15th 22:55. Stop = the other side of the range. Close on the last trading day of the month 21:55 (held over weekends; MT5 broker swap-free).
R = |entry - stop|, skipped if R < 2 spreads. Control: a random minute in the same order window, random side, the same R and exit.

## Cells (6) = {W1, W2, W4} x {E-close, E-2R}; DEV 2022-24, VAL 2025.
Gates: 1. DEV mean >= +0.05 R and t >= 2.4 (portfolio by entry week, NW lag 1; Bonferroni 6). 2. VAL mean > 0 and t >= 1.65. 3. Beats its control by >= 0.05 R in DEV and VAL. By class and indices reported.
## Honest prior
About 8%: weekly/monthly breakouts are a slow trend-following rule; daily trend tests here (TREND_PORT) were weaker than buy-and-hold but not zero.
