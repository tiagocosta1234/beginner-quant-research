# N3: one-look 2026 confirmation of trend-filtered index nights: result (2026-10-10, local local clock)

Pre-registration `PREREG_TREND_NIGHTS_CONFIRM.md` (commit a0e8a77, before 2026 was looked at), script `trend_nights_confirm.py`, output `TREND_NIGHTS_CONFIRM_OUTPUT.txt`.

## Verdict: NOT confirmed
| 2026 (Jan-Sep, 184 nights) | mean bp/night | t | worst night |
|---|---|---|---|
| **PRIMARY: US equal-weight, above its 200-day mean** | **+0.81** (173 active nights) | **+0.19** | -189 bp |
| NSDQ, same rule | +2.50 | +0.41 | -292 bp |
| SP, same rule | +0.26 | +0.07 | -179 bp |
| US equal-weight, NO filter | +2.96 | +0.61 | -189 bp |
Pass required mean > 0 and t >= 1.65: failed. In 2026 the indices were above their 200-day mean on 173 of 184 nights, so the filter was almost always ON and added nothing (+0.8 bp vs +3.0 bp unfiltered). At MT5 broker's 1%-per-idea size (about 27,000 USD notional for a worst night of 1,000 USD) the 2026 result is +2.2 USD a night; daily correlation with the gold pair +0.03.

## Reading
The 2022-25 pattern (+5 bp a night in uptrends) did not repeat in 2026. With about 190 nights and a 55-70 bp nightly sd the test has little power, so this does not prove the effect is gone, but there is no evidence for it now and it stays out of the plan. The 2026 hold-out for overnight rules is now used.
