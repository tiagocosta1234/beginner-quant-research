# N2: overnight try-everything grid (480 variants): result (2026-10-10, local local clock)

Pre-registration `PREREG_OVERNIGHT_GRID.md` (commit 3026a17, before the run), script `overnight_grid.py`, output `OVERNIGHT_GRID_DEV_OUTPUT.txt`. 8 markets (US equal-weight, SP, NSDQ, DOW, DAX, NIKKEI, ASX, gold) x 3 entry/exit timings x 10 filters x weekends in/out = 480 variants on MT5 broker bid/ask, DEV 2022-24.

## Verdict: no variant beats selection luck; under the registered rule the family is closed and 2026 stays unopened
- DEV t: median +0.64, 74% of variants positive, 5.0% at t >= 2, best +2.78 (NSDQ, enter 5 min before the close, exit 5 min after the open, only when NSDQ is above its 200-day mean, weekends included).
- Reality check: the best t the same 480-variant search finds when no variant has any edge is +2.26 (median) and +3.34 (95th percentile); the real best +2.78 has p = 0.19. Nothing is above the null's 95th percentile, so no variant goes to the hold-out.

## What is consistent (indicated, NOT established)
- The 200-day trend filter on US indices is the strongest filter (median DEV t +1.41 against +0.50 without it) and stays positive in 2025: NSDQ +6.7 bp per night (t +1.73), SP +5.0 (t +1.77), US equal-weight +5.0 (t +1.74), after +5.4 / +3.3 / +3.4 in DEV. This matches the literature: the overnight premium lives in rising markets, and it would have kept you out of most of 2022.
- Gold nights are the best market (median DEV t +1.50; Mon-Thu nights +4.7 to +6.0 bp, and +5.5 to +7.9 bp in 2025). The gold pair already holds gold through many nights, so this is mostly exposure we already have.
- ASX nights are negative (median t -0.43); "below the 200-day mean" is worthless on US indices.

## For the test
Even the best variant is about +5 bp a night with a sd of about 60-70 bp. At MT5 broker's 1%-per-idea size (worst night <= 1,000 USD, about 30,000 USD of NSDQ) it adds about 15 USD a night. To add 500 USD a night it would need about 1 million USD of NSDQ, where one bad night (-3%) loses about 30,000 USD. The overnight cannot pass the test fast at any size. Its best use, if it confirms later (forward or 2027 data), is a small, separate leg in a trend regime.
