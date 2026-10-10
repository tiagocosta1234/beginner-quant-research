# Item B (the trader 2026-10-09 "(original wording omitted)"): three gold-only trials, all fail (ledger 54 -> 57)

Pre-registration `PREREG_GOLD_B.md` (19:58 local, before any run), runner `gold_b.py`, outputs `GOLD_B_G1_OUTPUT.txt`, `GOLD_B_G23_OUTPUT.txt`, ledger rows `gold_b` (G1, G2, G3, DIAG-G1-noslip). Bonferroni bar daily t >= 2.5. No hold-out was run (DEV failed in every trial).

## G1 - gold range fade (M15, Bollinger 20/2 close outside the band while ADX14 < 20, target SMA20, stop 1.5 ATR, 0.25 USD slippage per side): FAILS, strongly negative
| period | trades | mean R | PF | daily t | win |
|---|---|---|---|---|---|
| DEV 2022-24 | 1,151 | -0.247 | 0.63 | -8.85 | 39.3% |
| VAL 2025 | 372 | -0.151 | 0.75 | -3.63 | 41.7% |
Diagnostic (not a trial): with zero slippage (only the bar spread, ~0.22 USD) DEV is -0.063 R (PF 0.89, t -3.5) and VAL -0.085 R: even before slippage fading the bands in quiet gold has a NEGATIVE gross edge, i.e. quiet-regime band breaks tend to continue. Slippage is heavy in R terms in 2022-24 (average ATR14 M15 of 2.1-3.0 USD vs 5.6 in 2025 and 11.3 in 2026). Correlation with the live pair over the last 12 months: -0.10 (so a mirrored breakout version might look diversifying, but the -0.063 R above already includes the spread and a mirror pays the spread too plus slippage, so its edge would have to come from a gross effect smaller than the costs; not worth a trial). Verdict: closed.

## G2 / G3 - SDB entries confirmed by a USD proxy / the 10-year real yield: FAIL, no information
SDB trade stream on MT5 broker data 2022-26 = 198 trades (110 in DEV, 45 in 2025, 43 in 2026), mean +35.3 bp.
| | DEV conf. vs unconf. (mean bp) | VAL conf. vs unconf. | pooled 2022-25 diff, permutation p |
|---|---|---|---|
| G2 USD proxy (EURUSD, USDJPY 5-day change) | +36.4 (65) vs -14.4 (45), diff +50.8 | +6.8 (27) vs +63.2 (18), diff **-56.4** | +19.9 bp, p = 0.26 |
| G3 real yield (DFII10 5-day change) | +28.9 (60) vs -0.2 (50), diff +29.1 | -25.1 (23) vs +86.3 (22), diff **-111.4** | -12.3 bp, p = 0.66 |
In both filters the DEV edge flips sign in 2025 and the pooled permutation test is nowhere near 0.05. Descriptive, non-overlapping 5-session windows (247): corr(gold's NEXT 5-day return, previous 5-day real-yield change) = -0.033; with the USD proxy -0.103 (noise level at this size, ~0.12). The slow fundamentals carry no usable timing information for gold at the weekly horizon either. Power note: ~155 trades in the pooled sample can only show differences of ~50 bp or more, so these results say "not shown", but the sign flip between DEV and VAL is the usual signature of noise. Verdict: closed.

## B4 - data
Read-only export from the portable MT5 broker copy (not the live terminal) into `forex/early_mt5/data_mt5`: XAGUSD, DAX, NIKKEI, ASX, BRENT, WTI M1 bid/ask bars (1.5-1.7M bars each, 2021-12..2026-10-03). Silver was already tested with the frozen SDB (fails); the other five are available for future registered trials. FRED DFII10 saved to `D:\finance\data_macro\DFII10.csv`.

## What B means for the account
Nothing new around the gold pair: the pair is still the only edge, no complement or filter was found, and the 57 registered trials in total (54 earlier + these 3) have not produced a second source of edge outside gold. The honest way to raise P(pass) is size and time, not a new entry rule.
