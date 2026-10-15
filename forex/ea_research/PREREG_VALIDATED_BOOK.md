# PREREG_VALIDATED_BOOK - the best account plan built ONLY from legs that survived an out-of-time test (written 2026-10-15, before any run; commit time = registration time)

## Legs (no new signals; each was validated elsewhere)
- D2 swap-free drift book (SWAPFREE_DRIFT_RESULT: OOT 2020-21 on two sources, HOLD 2026, real ticks), minute-level guarded series from d2_account.py at G = 75k / 100k.
- USDJPY London-open breakout (PRESAMPLE: 2020-21 OOT +0.26 R; USDJPY_TICKS: real execution costs 0.05-0.08 R a trade more than the M1 engine): MT5 broker M1 day series in R from BRK_EXITS (X4_noTP), with a haircut of 0.06 R on every trade day, at risk 150 / 300 USD a trade. Day low = min(R, 0) x risk (the stop; a gap through the stop is not modelled beyond the haircut).
- Index dip reversal DA (DIP_ADDON_RESULT: confirmed on 1990-2017 data and on MT5 broker 2022-26), day series from combo_grid.dip_days(500) (x0.75 as registered there).
- Not used: the gold EA pair (ManualSDB failed its pre-sample check on gold futures 2019-21, -0.16 R, t -1.63; XAU5 is closed-source and cannot be tested out of time), the breakout card legs (failed OOT).

## Combination and account rules
- Days 2022-02-15..2025-12-31 (the common span; 2026 as a sensitivity), legs added day by day; a shared day guard at -1,500: when the combined day low (sum of the legs' lows: pessimistic, they are not simultaneous) is <= -1,500 the day is booked at that low (D2's own guard behaviour is already inside its series).
- MT5 broker rules from 97,708.08 as in swapfree_mt5sim; 5-day block bootstrap, 20,000 paths; horizons 22 Dec, 31 Mar 27, 30 Jun 27, 31 Dec 27.
- Configurations: D2 100k alone; D2 100k + USDJPY 150; D2 100k + USDJPY 300; D2 100k + DA; D2 100k + USDJPY 150 + DA; D2 75k + USDJPY 300 + DA.
- Reported: daily correlations between legs, mean and sd of the combined day, the account table. A configuration is "better" than D2 alone only if pass rises by >= 2 points at 30 Jun 27 with breach not higher by more than 1 point.

## Honest expectation
USDJPY after the haircut is about +0.05 R a trade with large variance; DA is rare. Expect at most a few points.
