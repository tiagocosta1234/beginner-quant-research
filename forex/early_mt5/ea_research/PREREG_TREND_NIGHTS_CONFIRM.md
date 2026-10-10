# Pre-registration: confirmation of "index nights in an uptrend" on the untouched 2026 hold-out (family N3, ONE primary test)

Written 2026-10-10 (time = the commit adding this file), BEFORE 2026 is looked at for any overnight rule. the trader: "testa as noites dos indices com filtro de tendencia". The pattern came from the 480-variant grid (`OVERNIGHT_GRID_RESULT.md`): it was chosen after seeing DEV 2022-24 and VAL 2025, so those years are no longer evidence. The only clean test is 2026-01-01 .. 2026-09-30, which no overnight rule has used.

## Primary test (fixed now; one look)
US-EW|T5|trend200|all: equal weight SP + NSDQ + DOW, buy 5 minutes before the 16:00 ET close, sell 5 minutes after the 09:30 ET open of the next business day (weekends included), only when the equal-weight entry price is above its 200-day mean of entry prices; MT5 broker bid/ask + 0.1 bp per side (code `overnight_grid.py`, unchanged).
Chosen as the primary because it is the least cherry-picked member (the equal-weight US basket rather than the single best index, NSDQ).
Pass: 2026 mean net bp per calendar night > 0 AND one-sided t >= 1.65 (5%).
Reported alongside, not tests: NSDQ and SP with the same rule; the same basket WITHOUT the filter (to see whether the filter adds anything in 2026); the number of active nights; worst night; correlation of its daily P&L with the gold pair (x1.2, 2026); USD per night at MT5 broker's 1%-per-idea size (worst historical night <= 1,000 USD).

## Honest prior
About 35% (consistent in DEV and VAL, supported by the literature, but 2026 has only about 190 nights and the effect is about +5 bp against a 55-70 bp sd: the test's power is low, so a fail does not prove absence; a pass is still only one confirmation).
